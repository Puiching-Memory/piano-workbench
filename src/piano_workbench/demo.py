"""An original, deterministic eight-bar fixture; no commercial recording."""

from pathlib import Path
import xml.etree.ElementTree as ET

import mido

from .common import new_file


MELODY = [[64,67,69,67],[65,69,72,69],[62,65,69,67],[64,67,72,71],
          [69,72,74,72],[67,71,74,71],[65,69,67,65],[64,62,60,60]]
CHORDS = [[36,43,48],[33,40,45],[38,45,50],[31,38,43],
          [33,40,45],[31,38,43],[29,36,41],[36,43,48]]


def make_demo_midi(destination):
    destination=new_file(destination)
    midi=mido.MidiFile(type=1,ticks_per_beat=480)
    meta=mido.MidiTrack([
        mido.MetaMessage('track_name',name='Original eight-bar workbench fixture'),
        mido.MetaMessage('time_signature',numerator=4,denominator=4),
        mido.MetaMessage('key_signature',key='C'),
        mido.MetaMessage('set_tempo',tempo=mido.bpm2tempo(96)),
        mido.MetaMessage('set_tempo',tempo=mido.bpm2tempo(84),time=16*480),
        mido.MetaMessage('end_of_track',time=16*480),
    ])
    events=[]
    for bar,(melody,chord) in enumerate(zip(MELODY,CHORDS)):
        start=bar*4*480
        events.append((start,0,mido.Message('control_change',control=64,value=100)))
        events.append((start+1800,0,mido.Message('control_change',control=64,value=0)))
        for j,pitch in enumerate(melody):
            onset=start+j*480+(j%2)*9
            events.append((onset,2,mido.Message('note_on',note=pitch,velocity=58+(bar%3)*6-j*2)))
            events.append((onset+350,1,mido.Message('note_off',note=pitch,velocity=0)))
        for pitch in chord:
            events.append((start,2,mido.Message('note_on',note=pitch,velocity=43+bar%3*3)))
            events.append((start+1080,1,mido.Message('note_off',note=pitch,velocity=0)))
    track,previous=mido.MidiTrack(),0
    for tick,_,msg in sorted(events,key=lambda x:x[:2]):
        track.append(msg.copy(time=tick-previous)); previous=tick
    track.append(mido.MetaMessage('end_of_track',time=32*480-previous))
    midi.tracks.extend([meta,track])
    with destination.open('xb') as f: midi.save(file=f)
    return destination


def make_demo_xml(destination):
    destination=new_file(destination)
    root=ET.Element('score-partwise',version='4.0')
    work=ET.SubElement(root,'work'); ET.SubElement(work,'work-title').text='Eight bars for Piano Workbench'
    ids=ET.SubElement(root,'identification'); c=ET.SubElement(ids,'creator',type='composer'); c.text='Original synthetic example'
    parts=ET.SubElement(root,'part-list')
    for pid,name in [('P1','Upper'),('P2','Lower')]:
        sp=ET.SubElement(parts,'score-part',id=pid); ET.SubElement(sp,'part-name').text=name
    names={0:('C',None),2:('D',None),4:('E',None),5:('F',None),7:('G',None),9:('A',None),11:('B',None)}
    for index,pid in enumerate(['P1','P2']):
        part=ET.SubElement(root,'part',id=pid)
        for bar in range(8):
            measure=ET.SubElement(part,'measure',number=str(bar+1))
            if bar==0:
                attrs=ET.SubElement(measure,'attributes'); ET.SubElement(attrs,'divisions').text='480'
                key=ET.SubElement(attrs,'key'); ET.SubElement(key,'fifths').text='0'
                time=ET.SubElement(attrs,'time'); ET.SubElement(time,'beats').text='4'; ET.SubElement(time,'beat-type').text='4'
                clef=ET.SubElement(attrs,'clef'); ET.SubElement(clef,'sign').text='G' if index==0 else 'F'; ET.SubElement(clef,'line').text='2' if index==0 else '4'
            pitches=MELODY[bar] if index==0 else CHORDS[bar]
            for j,pitch in enumerate(pitches):
                n=ET.SubElement(measure,'note')
                if index==1 and j: ET.SubElement(n,'chord')
                p=ET.SubElement(n,'pitch'); step,_=names[pitch%12]
                ET.SubElement(p,'step').text=step; ET.SubElement(p,'octave').text=str(pitch//12-1)
                ET.SubElement(n,'duration').text='480' if index==0 else '1920'
                ET.SubElement(n,'type').text='quarter' if index==0 else 'whole'
    with destination.open('xb') as f: ET.ElementTree(root).write(f,encoding='utf-8',xml_declaration=True)
    return destination
