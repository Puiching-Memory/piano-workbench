"""Optional engraving, separate from the upstream DuET model and inference."""

import io
from collections import defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

from .common import WorkbenchError, new_directory, require_file, write_json


def engrave(source, output):
    require_file(source)
    try:
        import verovio
        from music21 import chord, clef, converter, key, metadata, meter, note, stream
        from reportlab.pdfgen import canvas
        from reportlab.graphics import renderPDF
        from reportlab.lib.pagesizes import A4
        from svglib.svglib import svg2rlg
    except ImportError as exc:
        raise WorkbenchError('Engraving requires: pip install ".[score]"') from exc
    original = converter.parse(Path(source))
    if not original.parts:
        raise WorkbenchError('No score parts found in MusicXML.')
    def signature(score):
        return sorted((i,int(p.midi),round(float(n.offset),8),round(float(n.duration.quarterLength),8))
                      for i,part in enumerate(score.parts)
                      for n in part.stripTies().flatten().notes for p in n.pitches)
    display = stream.Score()
    display.metadata = metadata.Metadata(title='Piano transcription',composer='Automatic notation · review before use')
    for i, old in enumerate(original.parts):
        part = stream.Part(id=f'P{i+1}')
        part.partName = 'Upper' if i == 0 else 'Lower' if i == 1 else f'Part {i+1}'
        part.insert(0,clef.TrebleClef() if i == 0 else clef.BassClef())
        last_key, last_meter = None, None
        for measure in old.getElementsByClass('Measure'):
            for ks in measure.getElementsByClass(key.KeySignature):
                if ks.sharps != last_key:
                    part.insert(measure.offset,key.KeySignature(ks.sharps)); last_key=ks.sharps
            for ts in measure.getElementsByClass(meter.TimeSignature):
                if ts.ratioString != last_meter:
                    part.insert(measure.offset,meter.TimeSignature(ts.ratioString)); last_meter=ts.ratioString
        grouped = defaultdict(list)
        for n in old.stripTies().flatten().notes:
            if n.duration.isGrace:
                raise WorkbenchError('This engraver does not revoice grace notes. Open the original XML in a notation editor.')
            grouped[n.offset,n.duration.quarterLength].extend(n.pitches)
        for (offset,duration),pitches in sorted(grouped.items()):
            n = chord.Chord(pitches) if len(pitches)>1 else note.Note(pitches[0])
            n.duration.quarterLength=duration
            part.insert(offset,n)
        display.insert(0,part)
    display.makeNotation(inPlace=True)
    out = new_directory(output)
    xml_path = out/'score.engraved.musicxml'
    display.write('musicxml',fp=xml_path)
    tree=ET.parse(xml_path)
    for part in tree.getroot().findall('part'):
        # music21 may export voice id 0 or object-derived identifiers. Verovio
        # expects positive layer numbers; otherwise it can silently omit notes.
        voice_ids=sorted({v.text for v in part.findall('.//voice')})
        voice_map={name:str(i+1) for i,name in enumerate(voice_ids)}
        for voice in part.findall('.//voice'):
            voice.text=voice_map[voice.text]
        previous={}
        for measure in part.findall('measure'):
            measure.attrib.pop('implicit',None)
            for attrs in measure.findall('attributes'):
                for n in list(attrs):
                    if n.tag not in {'divisions','key','time','clef'}: continue
                    value=ET.tostring(n,encoding='unicode').strip()
                    if previous.get(n.tag)==value: attrs.remove(n)
                    else: previous[n.tag]=value
                if not len(attrs): measure.remove(attrs)
    tree.write(xml_path,encoding='utf-8',xml_declaration=True)
    before,after=signature(original),signature(converter.parse(xml_path))
    if before != after:
        raise WorkbenchError('Engraving changed pitch/onset/duration/staff events. Keep the original XML; inspect the incomplete output.')
    toolkit=verovio.toolkit()
    toolkit.setOptions({'pageWidth':2100,'pageHeight':2970,'scale':40,
                        'pageMarginTop':80,'pageMarginBottom':80,'pageMarginLeft':70,
                        'pageMarginRight':70,'breaks':'auto','header':'none','footer':'none'})
    if not toolkit.loadFile(str(xml_path)):
        raise WorkbenchError('Verovio could not load the normalized MusicXML.')
    pages=toolkit.getPageCount()
    if pages < 1: raise WorkbenchError('Engraving produced no pages.')
    pdf=canvas.Canvas(str(out/'score.pdf'),pagesize=A4)
    pdf.setTitle('Piano Workbench - notation preview')
    visible_notes=0
    for index in range(1,pages+1):
        svg=toolkit.renderToSVG(index)
        visible_notes+=sum('note' in node.get('class','').split() for node in ET.fromstring(svg).iter())
        (out/f'page-{index:02d}.svg').write_text(svg,encoding='utf-8')
        drawing=svg2rlg(io.BytesIO(svg.encode()))
        if drawing is None: raise WorkbenchError('SVG-to-PDF conversion failed.')
        width,height=A4
        scale=min((width-30)/drawing.width,(height-70)/drawing.height)
        pdf.setFont('Helvetica',12)
        pdf.drawString(20,height-20,'Piano Workbench - notation preview')
        pdf.setFont('Helvetica',8)
        pdf.drawRightString(width-20,14,f'{index} / {pages}')
        pdf.drawString(20,14,'Automatic engraving - review against the source performance')
        pdf.saveState(); pdf.translate((width-drawing.width*scale)/2,height-40-drawing.height*scale)
        pdf.scale(scale,scale); renderPDF.draw(drawing,pdf,0,0); pdf.restoreState(); pdf.showPage()
    pdf.save()
    expected_fragments=len(tree.getroot().findall('.//note/pitch'))
    if visible_notes != expected_fragments:
        raise WorkbenchError(f'Renderer omitted or duplicated note fragments: XML={expected_fragments}, SVG={visible_notes}. Inspect the incomplete output.')
    report={'pages':pages,'note_event_equivalence':True,'events_checked':len(before),
            'pitched_fragments_in_xml':expected_fragments,'visible_note_groups_in_svg':visible_notes,
            'engine':'music21 + Verovio + svglib/ReportLab',
            'limitation':'Display voices regrouped; preserve original XML. Not an accuracy check and not preservation of all articulations/lyrics/layout.'}
    write_json(out/'engraving.json',report)
    return report
