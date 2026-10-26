"""Sample-timed SF2 rendering with original tempo/controller events."""

import math
import tempfile
import wave
from pathlib import Path

import mido
import numpy as np
from tinysoundfont import Synth

from .common import WorkbenchError, new_file, require_file, sha256, write_json
from .midi import midi_info, read_performance


def render_midi(source, sf2, destination, *, bank=0, preset=0, rate=44100, tail=6.0, gain_db=-12.0):
    source, sf2 = require_file(source), require_file(sf2)
    destination = new_file(destination)
    report_path = new_file(destination.with_suffix('.render.json'))
    if source.resolve() == destination.resolve() or sf2.resolve() == destination.resolve():
        raise WorkbenchError('Output must not replace an input.')
    if rate < 8000 or rate > 192000 or not math.isfinite(tail) or tail < 0 or tail > 60:
        raise WorkbenchError('Use a sample rate of 8000..192000 Hz and a tail of 0..60 seconds.')
    if not math.isfinite(gain_db) or gain_db < -96 or gain_db > 12:
        raise WorkbenchError('Synth gain must be finite and between -96 and +12 dB.')
    midi, events, notes, _ = read_performance(source)
    if any(n.channel == 9 for n in notes):
        raise WorkbenchError('Drum-channel notes found. Export piano-only MIDI before rendering.')
    if any(m.type == 'control_change' and m.control in {0, 32} for _, m in events):
        raise WorkbenchError('Bank-select controllers conflict with the explicitly selected SF2 bank; remove them first.')
    synth = Synth(gain=gain_db, samplerate=rate)
    sfid = synth.sfload(str(sf2), max_voices=512)
    try:
        preset_name = synth.sfpreset_name(sfid, bank, preset)
        if preset_name is None:
            raise WorkbenchError(f'SF2 has no bank {bank}, preset {preset} (indices are zero-based).')
        for channel in range(16):
            synth.program_select(channel, sfid, bank, preset)
        with tempfile.TemporaryDirectory(prefix='piano-render-') as temp:
            raw_path = Path(temp)/'audio.f32'
            peak, frames, elapsed = 0.0, 0, 0.0
            control_messages, pitch_bends, program_changes = 0, 0, 0
            def generate(count, handle):
                nonlocal peak, frames
                while count:
                    block = min(count, rate)
                    samples = np.frombuffer(synth.generate(block), dtype=np.float32)
                    if not np.isfinite(samples).all():
                        raise WorkbenchError('Synth produced non-finite samples.')
                    peak = max(peak, float(np.max(np.abs(samples))))
                    handle.write(samples.astype('<f4', copy=False).tobytes())
                    frames += block
                    count -= block
            with raw_path.open('wb') as raw:
                # mido's iterator applies the complete merged tempo map, in seconds.
                for msg in midi:
                    elapsed += msg.time
                    target = round(elapsed*rate)
                    generate(max(0, target-frames), raw)
                    if msg.type == 'note_on' and msg.velocity:
                        if not synth.noteon(msg.channel, msg.note, msg.velocity):
                            raise WorkbenchError('SoundFont voice allocation failed.')
                    elif msg.type == 'note_off' or (msg.type == 'note_on' and not msg.velocity):
                        synth.noteoff(msg.channel, msg.note)
                    elif msg.type == 'control_change':
                        synth.control_change(msg.channel, msg.control, msg.value)
                        control_messages += 1
                    elif msg.type == 'pitchwheel':
                        synth.pitchbend(msg.channel, msg.pitch+8192)
                        pitch_bends += 1
                    elif msg.type == 'program_change':
                        program_changes += 1
                for channel in range(16):
                    synth.control_change(channel, 64, 0)
                synth.notes_off()
                generate(round(tail*rate), raw)
            if peak <= 0:
                raise WorkbenchError('Rendered audio is silent.')
            # Apply at most one constant safety attenuation, never per-block limiting.
            safety_gain = min(1.0, 0.95/peak)
            if frames*4 > 0xFFFFFFFF-36:
                raise WorkbenchError('Output exceeds the RIFF/WAV 4 GiB limit; split the performance.')
            with raw_path.open('rb') as raw, destination.open('xb') as f:
                with wave.open(f, 'wb') as wav:
                    wav.setparams((2, 2, rate, 0, 'NONE', 'not compressed'))
                    for block in iter(lambda: raw.read(rate*2*4), b''):
                        data = np.frombuffer(block, dtype='<f4')*safety_gain
                        wav.writeframesraw(np.rint(np.clip(data,-1,1)*32767).astype('<i2').tobytes())
        report = {'engine': 'TinySoundFont via tinysoundfont 0.3.7',
                  'midi': midi_info(source), 'soundfont': sf2.name, 'soundfont_sha256': sha256(sf2),
                  'preset_name': preset_name, 'bank': bank, 'preset': preset,
                  'sample_rate': rate, 'channels': 2, 'format': 'PCM16 WAV',
                  'duration_seconds': frames/rate, 'release_tail_seconds': tail,
                  'synth_gain_db': gain_db, 'peak_before_safety_gain': peak,
                  'constant_safety_gain': safety_gain, 'peak_after_safety_gain': peak*safety_gain,
                  'control_messages_forwarded': control_messages, 'pitch_bends_forwarded': pitch_bends,
                  'program_changes_overridden': program_changes,
                  'processing': 'Original MIDI timing, velocity and controllers; explicit SF2 preset overrides program changes. No added EQ/reverb/compression.',
                  'output_sha256': sha256(destination)}
        write_json(report_path, report)
        return report
    finally:
        synth.sfunload(sfid)
