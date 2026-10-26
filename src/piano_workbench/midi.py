"""Inspect MIDI and optionally approximate CC64 using note lengths for DAWs."""

from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

import mido

from .common import WorkbenchError, new_file, require_file, sha256, write_json


@dataclass
class Note:
    channel: int
    pitch: int
    start: int
    end: int
    velocity: int


def read_performance(path):
    midi = mido.MidiFile(require_file(path))
    if midi.type == 2:
        raise WorkbenchError('Type-2 asynchronous MIDI is unsupported; export type 0 or 1.')
    if midi.ticks_per_beat <= 0:
        raise WorkbenchError('SMPTE time-division MIDI is unsupported; export a positive PPQ timebase.')
    events, tick = [], 0
    for msg in mido.merge_tracks(midi.tracks):
        tick += msg.time
        events.append((tick, msg))
    active, notes = defaultdict(deque), []
    for tick_at, msg in events:
        if msg.type == 'note_on' and msg.velocity > 0:
            if any(start == tick_at for start, _ in active[msg.channel, msg.note]):
                raise WorkbenchError('Duplicate same-key note-on at the same tick; resolve it before processing.')
            active[msg.channel, msg.note].append((tick_at, msg.velocity))
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            pending = active[msg.channel, msg.note]
            if not pending:
                raise WorkbenchError(f'Unmatched note-off at tick {tick_at}: channel {msg.channel}, pitch {msg.note}.')
            start, velocity = pending.popleft()
            if tick_at <= start:
                raise WorkbenchError(f'Nonpositive note duration at tick {start}.')
            notes.append(Note(msg.channel, msg.note, start, tick_at, velocity))
    if any(active.values()):
        raise WorkbenchError('Unclosed note-on events; repair the MIDI before processing.')
    if not notes:
        raise WorkbenchError('MIDI contains no positive-velocity notes.')
    return midi, events, sorted(notes, key=lambda n: (n.start, n.channel, n.pitch)), tick


def midi_info(path):
    midi, events, notes, last_tick = read_performance(path)
    tempo, previous_tick, seconds = 500000, 0, 0.0
    last_note_tick = max(n.end for n in notes)
    last_note_seconds = None
    for tick, msg in events:
        if last_note_seconds is None and last_note_tick <= tick:
            last_note_seconds = seconds + mido.tick2second(last_note_tick-previous_tick, midi.ticks_per_beat, tempo)
        seconds += mido.tick2second(tick-previous_tick, midi.ticks_per_beat, tempo)
        previous_tick = tick
        if msg.type == 'set_tempo':
            tempo = msg.tempo
    return {
        'file': Path(path).name, 'sha256': sha256(path), 'notes': len(notes),
        'ticks_per_beat': midi.ticks_per_beat, 'duration_seconds': seconds,
        'last_note_off_seconds': last_note_seconds,
        'channels': sorted({n.channel for n in notes}),
        'pitch_range': [min(n.pitch for n in notes), max(n.pitch for n in notes)],
        'velocity_range': [min(n.velocity for n in notes), max(n.velocity for n in notes)],
        'sustain_messages': sum(m.type == 'control_change' and m.control == 64 for _, m in events),
        'tempo_changes': sum(m.type == 'set_tempo' for _, m in events),
    }


def bake_pedal(source, destination):
    destination = new_file(destination)
    report_path = new_file(destination.with_suffix('.pedal.json'))
    midi, events, notes, end_tick = read_performance(source)
    down, spans = {}, defaultdict(list)
    for tick, msg in events:
        if msg.type == 'control_change' and msg.control in {120, 123}:
            raise WorkbenchError('CC120/123 all-notes/sounds-off requires manual resolution before pedal baking.')
        if msg.type != 'control_change' or msg.control != 64:
            continue
        if msg.value >= 64:
            down.setdefault(msg.channel, tick)
        elif msg.channel in down:
            spans[msg.channel].append((down.pop(msg.channel), tick))
    open_pedals = len(down)
    for channel, start in down.items():
        spans[channel].append((start, end_tick))
    signature = [(n.channel, n.pitch, n.start, n.velocity) for n in notes]
    extended, clipped = 0, 0
    for n in notes:
        for start, end in spans[n.channel]:
            if start <= n.end < end:
                n.end = end
                extended += 1
                break
    grouped = defaultdict(list)
    for n in notes:
        grouped[n.channel, n.pitch].append(n)
    for group in grouped.values():
        for n, following in zip(group, group[1:]):
            if n.end > following.start:
                n.end = following.start
                clipped += 1
    if any(n.end <= n.start for n in notes):
        raise WorkbenchError('Retrigger clipping would create a zero-length note; resolve duplicates first.')
    # Preserve tempo, meter, key, other controllers and all other non-note events.
    output_events = []
    for index, (tick, msg) in enumerate(events):
        if msg.type in {'note_on', 'note_off', 'end_of_track'}:
            continue
        if msg.type == 'control_change' and msg.control == 64:
            continue
        output_events.append((tick, 1, index, msg.copy(time=0)))
    for index, n in enumerate(notes):
        output_events.append((n.start, 2, index, mido.Message('note_on', channel=n.channel, note=n.pitch, velocity=n.velocity)))
        output_events.append((n.end, 0, index, mido.Message('note_off', channel=n.channel, note=n.pitch, velocity=0)))
    out = mido.MidiFile(type=0, ticks_per_beat=midi.ticks_per_beat)
    track, previous = mido.MidiTrack(), 0
    for tick, _, _, msg in sorted(output_events, key=lambda x: x[:3]):
        track.append(msg.copy(time=tick-previous))
        previous = tick
    track.append(mido.MetaMessage('end_of_track', time=max(0, end_tick-previous)))
    out.tracks.append(track)
    with destination.open('xb') as f:
        out.save(file=f)
    _, _, check_notes, _ = read_performance(destination)
    if signature != [(n.channel, n.pitch, n.start, n.velocity) for n in check_notes]:
        raise WorkbenchError('Pedal conversion changed note onsets, pitches, channels or velocities.')
    report = {'input': Path(source).name, 'output': destination.name,
              'source_sha256': sha256(source), 'notes': len(notes),
              'onsets_pitches_channels_velocities_unchanged': True,
              'notes_extended': extended, 'same_pitch_retrigger_clips': clipped,
              'sustain_intervals': sum(map(len, spans.values())),
              'unclosed_pedals_closed_at_end': open_pedals,
              'limitation': 'CC64 note-length approximation; no half-pedal, physical resonance or pedal-noise synthesis. Other messages retained.'}
    write_json(report_path, report)
    return report
