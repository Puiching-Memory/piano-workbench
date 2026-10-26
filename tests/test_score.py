import importlib.util
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

from piano_workbench.common import WorkbenchError
from piano_workbench.demo import make_demo_xml


HAS_SCORE=all(importlib.util.find_spec(n) is not None for n in ['music21','verovio','reportlab','svglib'])


@unittest.skipUnless(HAS_SCORE,'Install .[score] for engraving integration')
class ScoreIntegrationTests(unittest.TestCase):
    def test_polyphonic_events_and_visible_fragments_preserved(self):
        from piano_workbench.score import engrave
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=make_demo_xml(root/'composition.musicxml')
            tree=ET.parse(source); measure=tree.getroot().find('part/measure')
            backup=ET.SubElement(measure,'backup'); ET.SubElement(backup,'duration').text='1920'
            note=ET.SubElement(measure,'note'); pitch=ET.SubElement(note,'pitch')
            ET.SubElement(pitch,'step').text='G'; ET.SubElement(pitch,'octave').text='4'
            ET.SubElement(note,'duration').text='960'; ET.SubElement(note,'voice').text='0'
            ET.SubElement(note,'type').text='half'
            tree.write(source,encoding='utf-8',xml_declaration=True)
            report=engrave(source,root/'score')
            self.assertTrue(report['note_event_equivalence'])
            self.assertEqual(report['events_checked'],57)
            self.assertEqual(report['pitched_fragments_in_xml'],report['visible_note_groups_in_svg'])
            xml=ET.parse(root/'score/score.engraved.musicxml')
            self.assertTrue(all(int(n.text)>0 for n in xml.findall('.//voice')))
            self.assertTrue((root/'score/score.pdf').read_bytes().startswith(b'%PDF'))

    def test_grace_notes_require_editor_review(self):
        from piano_workbench.score import engrave
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=make_demo_xml(root/'composition.musicxml')
            tree=ET.parse(source); note=tree.getroot().find('part/measure/note')
            note.remove(note.find('duration')); note.insert(0,ET.Element('grace'))
            tree.write(source,encoding='utf-8',xml_declaration=True)
            with self.assertRaisesRegex(WorkbenchError,'grace'):
                engrave(source,root/'score')
            self.assertFalse((root/'score').exists())


if __name__=='__main__': unittest.main()
