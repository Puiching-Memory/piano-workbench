import os
import tempfile
import unittest
import wave
from pathlib import Path

import mido
import numpy as np

from piano_workbench.common import WorkbenchError
from piano_workbench.demo import make_demo_midi
from piano_workbench.render import render_midi


class RenderInputTests(unittest.TestCase):
    def test_drum_notes_not_silently_rendered_as_piano(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); midi=mido.MidiFile(); track=mido.MidiTrack()
            track.extend([mido.Message('note_on',channel=9,note=36,velocity=60),mido.Message('note_off',channel=9,note=36,time=480)])
            midi.tracks.append(track); midi.save(root/'drums.mid'); (root/'dummy.sf2').write_bytes(b'not loaded')
            with self.assertRaisesRegex(WorkbenchError,'Drum-channel'):
                render_midi(root/'drums.mid',root/'dummy.sf2',root/'out.wav')
            self.assertFalse((root/'out.wav').exists())


@unittest.skipUnless(os.environ.get('PIANO_WORKBENCH_TEST_SF2'),'Set PIANO_WORKBENCH_TEST_SF2 for instrument integration')
class RenderIntegrationTests(unittest.TestCase):
    def test_tempo_controller_and_output_integrity(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=make_demo_midi(root/'demo.mid')
            report=render_midi(source,os.environ['PIANO_WORKBENCH_TEST_SF2'],root/'piano.wav',
                               preset=int(os.environ.get('PIANO_WORKBENCH_TEST_PRESET','0')),rate=8000,tail=.25)
            self.assertEqual(report['midi']['notes'],56)
            self.assertEqual(report['control_messages_forwarded'],16)
            self.assertAlmostEqual(report['duration_seconds'],16*60/96+16*60/84+.25,delta=1/8000)
            with wave.open(str(root/'piano.wav')) as f:
                self.assertEqual((f.getnchannels(),f.getsampwidth(),f.getframerate()),(2,2,8000))
                data=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2')
            self.assertGreater(int(np.max(np.abs(data))),0)
            self.assertLess(int(np.max(np.abs(data))),32767)


if __name__=='__main__': unittest.main()
