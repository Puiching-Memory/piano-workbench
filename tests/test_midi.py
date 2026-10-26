import tempfile
import unittest
from pathlib import Path

import mido

from piano_workbench.common import WorkbenchError
from piano_workbench.demo import make_demo_midi
from piano_workbench.midi import bake_pedal, midi_info, read_performance


def fixture(path, messages):
    midi=mido.MidiFile(type=1,ticks_per_beat=480)
    meta=mido.MidiTrack([mido.MetaMessage('set_tempo',tempo=500000),
                         mido.MetaMessage('set_tempo',tempo=1000000,time=240),
                         mido.MetaMessage('end_of_track',time=240)])
    track=mido.MidiTrack(); previous=0
    for tick,msg in sorted(messages,key=lambda x:x[0]):
        track.append(msg.copy(time=tick-previous)); previous=tick
    track.append(mido.MetaMessage('end_of_track',time=max(0,480-previous)))
    midi.tracks.extend([meta,track]); midi.save(path)


class MidiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()

    def test_channel_pedal_retrigger_and_metadata(self):
        source=self.root/'input.mid'; output=self.root/'baked.mid'
        fixture(source,[
            (0,mido.Message('control_change',channel=0,control=64,value=127)),
            (0,mido.Message('control_change',channel=0,control=67,value=25)),
            (0,mido.Message('program_change',program=7)),
            (0,mido.Message('note_on',channel=0,note=60,velocity=71)),
            (0,mido.Message('note_on',channel=1,note=60,velocity=43)),
            (120,mido.Message('note_off',channel=0,note=60)),
            (120,mido.Message('note_off',channel=1,note=60)),
            (360,mido.Message('note_on',channel=0,note=60,velocity=54)),
            (420,mido.Message('note_on',channel=0,note=60,velocity=0)),
            (480,mido.Message('control_change',channel=0,control=64,value=0)),
        ])
        unchanged=source.read_bytes(); report=bake_pedal(source,output)
        _,events,notes,_=read_performance(output)
        self.assertEqual(source.read_bytes(),unchanged)
        self.assertEqual([(n.channel,n.start,n.end,n.velocity) for n in notes],
                         [(0,0,360,71),(1,0,120,43),(0,360,480,54)])
        self.assertEqual(report['notes_extended'],2)
        self.assertEqual(report['same_pitch_retrigger_clips'],1)
        self.assertFalse(any(m.type=='control_change' and m.control==64 for _,m in events))
        self.assertTrue(any(m.type=='control_change' and m.control==67 and m.value==25 for _,m in events))
        self.assertTrue(any(m.type=='program_change' and m.program==7 for _,m in events))
        self.assertEqual([m.tempo for _,m in events if m.type=='set_tempo'],[500000,1000000])
        self.assertAlmostEqual(midi_info(output)['duration_seconds'],0.75)
        # Note-off is at tick 480: 240 ticks at each of two tempos, not 0.5 seconds.
        self.assertAlmostEqual(midi_info(output)['last_note_off_seconds'],0.75)
        with self.assertRaises(WorkbenchError): bake_pedal(source,output)

    def test_open_pedal_closes_at_end(self):
        source=self.root/'open.mid'
        fixture(source,[(0,mido.Message('control_change',control=64,value=127)),
                        (0,mido.Message('note_on',note=60,velocity=60)),
                        (120,mido.Message('note_off',note=60))])
        report=bake_pedal(source,self.root/'out.mid')
        self.assertEqual(report['unclosed_pedals_closed_at_end'],1)
        self.assertEqual(read_performance(self.root/'out.mid')[2][0].end,480)

    def test_unclosed_and_unmatched_notes_rejected(self):
        for name,msgs in [('unclosed',[(0,mido.Message('note_on',note=60,velocity=60))]),
                          ('unmatched',[(120,mido.Message('note_off',note=60))])]:
            with self.subTest(name=name):
                source=self.root/f'{name}.mid'; fixture(source,msgs)
                with self.assertRaises(WorkbenchError): read_performance(source)

    def test_demo_reproducibility_and_timing(self):
        a=make_demo_midi(self.root/'a.mid'); b=make_demo_midi(self.root/'b.mid')
        self.assertEqual(a.read_bytes(),b.read_bytes())
        info=midi_info(a)
        self.assertEqual(info['notes'],56)
        self.assertEqual(info['sustain_messages'],16)
        self.assertEqual(info['tempo_changes'],2)
        self.assertAlmostEqual(info['duration_seconds'],16*60/96+16*60/84,places=4)
        report=bake_pedal(a,self.root/'demo-baked.mid')
        self.assertTrue(report['onsets_pitches_channels_velocities_unchanged'])

    def test_smpte_timebase_is_not_misread_as_ppq(self):
        source=make_demo_midi(self.root/'smpte.mid')
        data=bytearray(source.read_bytes())
        # MIDI header division -25 fps, 40 ticks/frame; not ticks per beat.
        data[12:14]=bytes([0xE7,40]); source.write_bytes(data)
        with self.assertRaisesRegex(WorkbenchError,'SMPTE'):
            read_performance(source)


if __name__=='__main__': unittest.main()
