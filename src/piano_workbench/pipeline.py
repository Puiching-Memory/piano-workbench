import importlib.util
import shutil
import time
from pathlib import Path

from .audio import compare
from .common import WorkbenchError, new_directory, require_file, write_json
from .midi import bake_pedal, midi_info
from .render import render_midi


DUET_REVISION = 'c98699c021affd3778434c3e7a5cd82214052418'


def transcribe(source, output, *, model='Wayne42/DuET', device=None, revision=None):
    require_file(source)
    if Path(output).exists(): raise WorkbenchError('DuET output must be a new directory.')
    if importlib.util.find_spec('duet') is None:
        raise WorkbenchError('Install PyTorch for your hardware, then pip install ".[transcription]". See docs/windows.md.')
    from duet import DuET
    engine=DuET.from_pretrained(model,device=device,revision=revision)
    if Path(source).suffix.lower() in {'.mid','.midi'}:
        report=engine.transcribe(source,output)
        shutil.copy2(source,Path(output)/'performance.mid')
    else:
        report=engine.transcribe_audio(source,output)
    # Upstream owns this directory and report; keep our metadata separate.
    write_json(Path(output)/'workbench-input.json',{
        'input':Path(source).name,'performance_midi':'performance.mid',
        'dependency_revision_tested':DUET_REVISION,
        'note':'DuET project calls Transkun for audio input. Performance MIDI is retained for auditioning; score MIDI uses score timing.'})
    return report


def run_pipeline(source, output, sf2s, *, model='Wayne42/DuET', device=None,
                 revision=None, skip_score=False, engraving=False, bank=0,preset=0,target=-23):
    source=require_file(source)
    if skip_score and source.suffix.lower() not in {'.mid','.midi'}:
        raise WorkbenchError('--skip-score accepts performance MIDI only. Audio input requires DuET transcription.')
    if skip_score and engraving:
        raise WorkbenchError('--engrave cannot be combined with --skip-score.')
    for sf2 in sf2s: require_file(sf2)
    out=new_directory(output)
    started=time.monotonic(); stage='input'
    try:
        if skip_score:
            performance=out/'performance.mid'; shutil.copy2(source,performance)
        else:
            stage='transcription'
            transcribe(source,out/'transcription',model=model,device=device,revision=revision)
            performance=out/'transcription'/'performance.mid'
        stage='pedal-compatibility'
        bake_pedal(performance,out/'performance_pedal_baked.mid')
        info=midi_info(performance)
        if engraving:
            stage='engraving'
            from .score import engrave
            engrave(out/'transcription'/'score.musicxml',out/'engraving')
        rendered=[]
        if sf2s:
            stage='rendering'; (out/'renders').mkdir()
            for index,sf2 in enumerate(sf2s):
                label=f'piano-{index+1}'
                destination=out/'renders'/f'{label}.wav'
                render_midi(performance,sf2,destination,bank=bank,preset=preset)
                rendered.append((label,destination))
            stage='comparison'
            compare(rendered,out/'listening',title='Piano Workbench audition',target=target)
        manifest={'status':'complete','input':source.name,'midi':info,
                  'elapsed_seconds':time.monotonic()-started,'score_generated':not skip_score,
                  'engraving_generated':engraving,'rendered_variants':len(rendered),
                  'performance_used_for_audio':'original performance MIDI, not score MIDI or pedal-baked MIDI',
                  'fl_studio':'Optional external/manual stage; docs/fl-studio.md',
                  'verification':'File/timing/loudness checks only; no reference-score accuracy or subjective-quality claim.'}
        write_json(out/'workflow.json',manifest)
        return manifest
    except Exception as exc:
        write_json(out/'failure.json',{'status':'failed','stage':stage,'error':str(exc),
                                     'completed_files_retained':True})
        raise
