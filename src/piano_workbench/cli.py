import argparse
import importlib.metadata
import json
import shutil
import sys
from pathlib import Path

from . import __version__
from .common import WorkbenchError, new_directory, write_json


def parser():
    p=argparse.ArgumentParser(prog='piano-workbench',description='DuET companion: original-performance auditioning, DAW pedal compatibility and fair audio comparisons.')
    p.add_argument('--version',action='version',version=__version__)
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor',help='Check dependencies without loading/downloading models')
    info=sub.add_parser('inspect',help='Inspect MIDI timing, notes and controllers'); info.add_argument('input',type=Path)
    pedal=sub.add_parser('bake-pedal',help='Approximate sustain with note lengths for DAW import')
    pedal.add_argument('input',type=Path); pedal.add_argument('--output',type=Path,required=True)
    render=sub.add_parser('render',help='Render original MIDI using an explicitly selected SF2 preset')
    render.add_argument('input',type=Path); render.add_argument('--sf2',type=Path,required=True)
    render.add_argument('--output',type=Path,required=True); render.add_argument('--bank',type=int,default=0)
    render.add_argument('--preset',type=int,default=0); render.add_argument('--tail',type=float,default=6)
    render.add_argument('--gain-db',type=float,default=-12)
    comp=sub.add_parser('compare',help='Match audio with constant gain and create a local A/B page')
    comp.add_argument('--audio',action='append',required=True,metavar='LABEL=PATH')
    comp.add_argument('--output',type=Path,required=True); comp.add_argument('--title',default='Piano audition')
    comp.add_argument('--target-lufs',type=float,default=-23); comp.add_argument('--peak-ceiling',type=float,default=-1.5)
    comp.add_argument('--no-mp3',action='store_true')
    score=sub.add_parser('engrave',help='Normalize score display, verify note events and export SVG/PDF')
    score.add_argument('input',type=Path); score.add_argument('--output',type=Path,required=True)
    for command in ['transcribe','run']:
        q=sub.add_parser(command,help='Call upstream DuET' if command=='transcribe' else 'Run transcription, optional engraving and SF2 auditioning')
        q.add_argument('input',type=Path); q.add_argument('--output',type=Path,required=True)
        q.add_argument('--model',default='Wayne42/DuET'); q.add_argument('--device',choices=['cpu','cuda'])
        q.add_argument('--model-revision',default=None)
        if command=='run':
            q.add_argument('--sf2',type=Path,action='append',default=[])
            q.add_argument('--bank',type=int,default=0); q.add_argument('--preset',type=int,default=0)
            q.add_argument('--skip-score',action='store_true'); q.add_argument('--engrave',action='store_true')
            q.add_argument('--target-lufs',type=float,default=-23)
    demo=sub.add_parser('demo',help='Create an original eight-bar MIDI/MusicXML fixture; no model needed')
    demo.add_argument('--output',type=Path,required=True)
    return p


def doctor():
    packages={}
    for name in ['piano-workbench','numpy','mido','tinysoundfont','duet-score','transkun','torch','music21','verovio','reportlab','svglib']:
        try: packages[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: packages[name]=None
    return {'python':sys.version.split()[0],'packages':packages,
            'ffmpeg_on_path':shutil.which('ffmpeg') is not None,
            'ffprobe_on_path':shutil.which('ffprobe') is not None,
            'note':'Checks installation only. Does not validate GPU execution, download weights or contact a service.'}


def main(argv=None):
    p=parser(); a=p.parse_args(argv)
    try:
        if a.command=='doctor': result=doctor()
        elif a.command=='inspect':
            from .midi import midi_info
            result=midi_info(a.input)
        elif a.command=='bake-pedal':
            from .midi import bake_pedal
            result=bake_pedal(a.input,a.output)
        elif a.command=='render':
            from .render import render_midi
            result=render_midi(a.input,a.sf2,a.output,bank=a.bank,preset=a.preset,tail=a.tail,gain_db=a.gain_db)
        elif a.command=='compare':
            from .audio import compare
            variants=[]
            for value in a.audio:
                if '=' not in value: raise WorkbenchError('Use --audio LABEL=PATH for each variant.')
                label,path=value.split('=',1); variants.append((label,Path(path)))
            result=compare(variants,a.output,title=a.title,target=a.target_lufs,ceiling=a.peak_ceiling,mp3=not a.no_mp3)
        elif a.command=='engrave':
            from .score import engrave
            result=engrave(a.input,a.output)
        elif a.command=='transcribe':
            from .pipeline import transcribe
            result=transcribe(a.input,a.output,model=a.model,device=a.device,revision=a.model_revision)
        elif a.command=='run':
            from .pipeline import run_pipeline
            result=run_pipeline(a.input,a.output,a.sf2,model=a.model,device=a.device,revision=a.model_revision,
                                skip_score=a.skip_score,engraving=a.engrave,bank=a.bank,preset=a.preset,target=a.target_lufs)
        elif a.command=='demo':
            from .demo import make_demo_midi,make_demo_xml
            from .midi import midi_info
            out=new_directory(a.output)
            make_demo_midi(out/'performance.mid'); make_demo_xml(out/'composition.musicxml')
            result={'source':'Original synthetic eight-bar fixture; not a transcription result',
                    'license':'MIT for this generated MIDI/MusicXML fixture',
                    'midi':midi_info(out/'performance.mid')}
            write_json(out/'fixture.json',result)
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
        return 0
    except (WorkbenchError,OSError,ValueError,ImportError,RuntimeError) as exc:
        print(f'piano-workbench: {exc}',file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
