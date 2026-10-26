import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from piano_workbench.common import WorkbenchError
from piano_workbench.demo import make_demo_midi
from piano_workbench.pipeline import run_pipeline


class PipelineTests(unittest.TestCase):
    def test_midi_only_path_never_loads_duet(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=make_demo_midi(root/'source.mid')
            with patch('piano_workbench.pipeline.transcribe',side_effect=AssertionError('model must not load')):
                report=run_pipeline(source,root/'out',[],skip_score=True)
            self.assertFalse(report['score_generated'])
            self.assertEqual((root/'out/performance.mid').read_bytes(),source.read_bytes())
            self.assertTrue((root/'out/performance_pedal_baked.mid').is_file())
            with self.assertRaises(WorkbenchError): run_pipeline(source,root/'out',[],skip_score=True)

    def test_failed_stage_keeps_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=make_demo_midi(root/'source.mid')
            with patch('piano_workbench.pipeline.transcribe',side_effect=WorkbenchError('fixture failure')):
                with self.assertRaises(WorkbenchError): run_pipeline(source,root/'out',[])
            self.assertIn('transcription',(root/'out/failure.json').read_text())


if __name__=='__main__': unittest.main()
