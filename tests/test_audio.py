import math
import shutil
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from piano_workbench.audio import choose_gains, compare
from piano_workbench.common import WorkbenchError


class GainTests(unittest.TestCase):
    def test_crest_heavy_variant_lowers_entire_group(self):
        measurements=[{'integrated_lufs':-30,'true_peak_dbtp':-2},
                      {'integrated_lufs':-20,'true_peak_dbtp':-9}]
        target,gains=choose_gains(measurements,-23,-1.5)
        self.assertLess(target,-29.5)
        for m,g in zip(measurements,gains):
            self.assertLessEqual(m['true_peak_dbtp']+g,-1.5)
            self.assertAlmostEqual(m['integrated_lufs']+g,target)
        self.assertAlmostEqual(gains[0]-gains[1],10)

    def test_invalid_numeric_options(self):
        with self.assertRaises(WorkbenchError): choose_gains([{'integrated_lufs':-20,'true_peak_dbtp':-5}],math.nan)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg/ffprobe not installed')
class AudioIntegrationTests(unittest.TestCase):
    def test_gain_only_matching_and_portable_safe_page(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); rate=44100
            t=np.arange(rate*9)/rate
            # Distinct phrase envelopes exercise gating while preserving the same performance.
            envelope=.3+.6*(np.sin(2*np.pi*t/3)**2)
            audio=(np.sin(2*np.pi*220*t)+.25*np.sin(2*np.pi*440*t))*envelope*.22
            paths=[]
            for label,gain in [('quiet',.2),('loud',1)]:
                path=root/f'{label}.wav'
                with wave.open(str(path),'wb') as f:
                    f.setparams((1,2,rate,0,'NONE','not compressed'))
                    f.writeframes(np.rint(audio*gain*32767).astype('<i2').tobytes())
                paths.append((label,path))
            original={p:p.read_bytes() for _,p in paths}
            report=compare(paths,root/'comparison',title='</title><script>alert(1)</script> __DATA__',mp3=False)
            self.assertEqual([p.read_bytes() for _,p in paths],[original[p] for _,p in paths])
            for item in report['variants']:
                self.assertAlmostEqual(item['matched']['integrated_lufs'],report['effective_target_lufs'],delta=.1)
                self.assertAlmostEqual(item['matched']['loudness_range_lu'],item['raw']['loudness_range_lu'],delta=.1)
            data=(root/'comparison/index.html').read_text(encoding='utf-8')
            self.assertNotIn('<script>alert(1)</script>',data)
            self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;',data)
            self.assertIn('quiet.flac',data)
            self.assertNotIn(str(root),data)
            self.assertIn(' __DATA__',data)  # title marker remains plain text
            with self.assertRaises(WorkbenchError): compare(paths,root/'comparison')
            with self.assertRaises(WorkbenchError): compare([('../escape',paths[0][1])],root/'invalid')
            self.assertFalse((root/'invalid').exists())


if __name__=='__main__': unittest.main()
