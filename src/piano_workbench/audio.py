"""Measure gated loudness and match with constant gain, never a compressor."""

import html
import json
import math
import re
from pathlib import Path

from .common import WorkbenchError, executable, new_directory, require_file, run_process, sha256, write_json


def measure(path):
    path = require_file(path)
    ffmpeg, ffprobe = executable('ffmpeg'), executable('ffprobe')
    probe = json.loads(run_process([ffprobe,'-v','error','-select_streams','a:0',
                                   '-show_entries','stream=sample_rate,channels:format=duration',
                                   '-of','json',path]).stdout)
    if not probe.get('streams'):
        raise WorkbenchError(f'No audio stream: {path.name}')
    stream = probe['streams'][0]
    if int(stream['channels']) not in {1, 2}:
        raise WorkbenchError('Comparison supports mono/stereo audio; explicitly downmix multichannel input first.')
    result = run_process([ffmpeg,'-nostdin','-v','info','-i',path,'-map','0:a:0',
                          '-af','loudnorm=I=-23:TP=-1.5:LRA=50:print_format=json','-f','null','-'])
    # Only the INPUT measurements are used. The filter's hypothetical dynamic
    # output is discarded and is never used to write a deliverable.
    found = re.findall(r'\{[^{}]*"input_i"[^{}]*\}', result.stderr, re.S)
    if not found:
        raise WorkbenchError(f'FFmpeg did not report loudness for {path.name}.')
    raw = json.loads(found[-1])
    values = {key: float(raw['input_'+key]) for key in ['i','tp','lra','thresh']}
    if not all(math.isfinite(v) for v in values.values()):
        raise WorkbenchError(f'{path.name} is silent or too short to measure gated loudness.')
    return {'integrated_lufs': values['i'], 'true_peak_dbtp': values['tp'],
            'loudness_range_lu': values['lra'], 'gating_threshold_lufs': values['thresh'],
            'duration_seconds': float(probe['format']['duration']),
            'sample_rate': int(stream['sample_rate']), 'channels': int(stream['channels'])}


def choose_gains(measurements, target=-23.0, ceiling=-1.5):
    if not measurements or not math.isfinite(target) or not math.isfinite(ceiling):
        raise WorkbenchError('Provide measurements and finite target/ceiling values.')
    if not -70 <= target <= -5 or not -12 <= ceiling <= 0:
        raise WorkbenchError('Target must be -70..-5 LUFS and ceiling -12..0 dBTP.')
    # Lower the SAME target for the whole group if a crest-heavy variant needs
    # more peak headroom. Never squash that variant to reach a louder target.
    effective = min(target, *(m['integrated_lufs']+ceiling-m['true_peak_dbtp'] for m in measurements))
    effective -= 0.02  # margin for measurement rounding and quantization
    return effective, [effective-m['integrated_lufs'] for m in measurements]


def compare(variants, output, *, title='Piano audition', target=-23.0, ceiling=-1.5, mp3=True):
    if not variants:
        raise WorkbenchError('At least one LABEL=audio-file variant is required.')
    labels = [label for label,_ in variants]
    if len(labels) != len(set(labels)):
        raise WorkbenchError('Variant labels must be unique.')
    for label,path in variants:
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}', label):
            raise WorkbenchError('Labels must be 1..64 ASCII letters, numbers, underscores or hyphens.')
        require_file(path)
    measured = [measure(path) for _,path in variants]
    if len({m['channels'] for m in measured}) != 1:
        raise WorkbenchError('All compared files must have the same channel count.')
    effective, gains = choose_gains(measured,target,ceiling)
    out = new_directory(output)
    entries = []
    for (label,path), raw, gain in zip(variants,measured,gains):
        destination = out/f'{label}.flac'
        run_process([executable('ffmpeg'),'-nostdin','-n','-v','error','-i',path,'-map','0:a:0',
                     '-map_metadata','-1','-af',f'volume={gain:.8f}dB','-ar','44100',
                     '-c:a','flac','-sample_fmt','s32',destination])
        checked = measure(destination)
        if abs(checked['integrated_lufs']-effective) > 0.15 or checked['true_peak_dbtp'] > ceiling+0.05:
            raise WorkbenchError(f'Gain matching verification failed for {label}. See generated audio before retrying.')
        if abs(checked['loudness_range_lu']-raw['loudness_range_lu']) > 0.3:
            raise WorkbenchError(f'Unexpected LRA change for {label}; investigate sample-rate/gating effects.')
        if mp3:
            run_process([executable('ffmpeg'),'-nostdin','-n','-v','error','-i',destination,
                         '-map_metadata','-1','-c:a','libmp3lame','-b:a','320k',out/f'{label}.mp3'])
        entries.append({'label':label,'input':Path(path).name,'input_sha256':sha256(path),
                        'raw':raw,'constant_gain_db':gain,'matched':checked,
                        'lossless':destination.name,'playback':f'{label}.mp3' if mp3 else destination.name})
    report = {'title':title,'requested_target_lufs':target,'effective_target_lufs':effective,
              'true_peak_ceiling_dbtp':ceiling,'matching':'constant gain only; no compressor or limiter',
              'target_lowered_for_headroom':effective < target-0.021,
              'note':'Source performance/timbre may differ; matching does not establish transcription accuracy or subjective quality.',
              'variants':entries}
    write_json(out/'comparison.json',report)
    write_preview(out,report)
    return report


def write_preview(out, report):
    safe_title = html.escape(report['title'])
    entries = report['variants']
    data = json.dumps([{'label':e['label'],'src':e['playback']} for e in entries],ensure_ascii=True).replace('<','\\u003c')
    buttons = '\n'.join(f'<button type="button" data-index="{i}" aria-pressed="{str(i==0).lower()}">{html.escape(e["label"])}</button>' for i,e in enumerate(entries))
    links = '\n'.join(f'<li><a href="{e["lossless"]}">{html.escape(e["label"])} · FLAC</a> <span>{e["matched"]["integrated_lufs"]:.2f} LUFS</span></li>' for e in entries)
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title><style>
body{margin:0;background:#f3f2ed;color:#18312f;font:17px/1.8 system-ui,"Microsoft YaHei",sans-serif}main{max-width:900px;margin:60px auto;padding:0 24px}h1{line-height:1.25;font-size:36px}section{background:#fff;padding:28px;border-radius:18px;margin:30px 0}audio{width:100%}.choices{display:flex;flex-wrap:wrap;gap:12px;margin-top:22px}button{font:inherit;padding:10px 20px;border:1px solid #b7c9be;background:#fff;border-radius:8px;cursor:pointer}button[aria-pressed=true]{background:#176e60;color:#fff}a{color:#176e60}p,small,span{color:#526961}li{margin:8px 0}button:focus-visible,a:focus-visible{outline:3px solid #bf6935;outline-offset:3px}@media(max-width:500px){main{margin-top:28px}h1{font-size:29px}section{padding:18px}}</style>
<main><p>PIANO WORKBENCH / 固定增益对照</p><h1>__TITLE__</h1>
<p>目标约 __TARGET__ LUFS。各版本只调整固定增益，保留原有动态；峰值余量不足时统一降低整组目标。</p>
<section><h2 id="selected">__LABEL__</h2><audio controls preload="metadata" id="player" src="__SRC__"></audio><div class="choices">__BUTTONS__</div><p id="status" role="status" aria-live="polite">切换版本保留播放位置和播放状态。建议使用耳机试听。</p></section>
<ul>__LINKS__</ul><p><a href="comparison.json">参数与测量记录</a></p><small>相同响度有助于比较音色，不代表音符识别准确，也不替代主观听音。波形未作为实测曲线展示。</small></main>
<script>const variants=__DATA__;const player=document.getElementById('player');const title=document.getElementById('selected');const status=document.getElementById('status');let revision=0;document.querySelectorAll('[data-index]').forEach(button=>{button.addEventListener('click',()=>{const v=variants[Number(button.dataset.index)],t=player.currentTime,playing=!player.paused,current=++revision;player.pause();player.src=v.src;title.textContent=v.label;document.querySelectorAll('[data-index]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));player.addEventListener('loadedmetadata',()=>{if(current!==revision)return;player.currentTime=Math.max(0,Math.min(t,Number.isFinite(player.duration)?player.duration:t));if(playing)player.play().catch(()=>{status.textContent='请点击播放继续试听。';});},{once:true});});});player.addEventListener('error',()=>{status.textContent='无法播放音频：请下载 FLAC，或通过本地 HTTP 服务打开此目录。';});</script></html>'''
    values={'__TITLE__':safe_title,'__TARGET__':f'{report["effective_target_lufs"]:.2f}',
            '__LABEL__':html.escape(entries[0]['label']),'__SRC__':entries[0]['playback'],
            '__BUTTONS__':buttons,'__LINKS__':links,'__DATA__':data}
    # One substitution pass: user titles containing a marker cannot inject a template.
    page = re.sub('|'.join(map(re.escape,values)),lambda m:values[m[0]],page)
    (Path(out)/'index.html').write_text(page,encoding='utf-8')
