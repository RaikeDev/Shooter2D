"""Bake full character poses for the pistol pickup test onto native sprites."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5
import argparse
import hashlib
import json
import math
import multiprocessing as mp
import re
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

TOOL = Path(__file__).resolve().parent
PROJECT = TOOL.parents[1]
DATA = TOOL / 'data'
sys.path.insert(0, str(TOOL / 'source'))

import renderer as rig_art
from audit import count
from dress import PXY, SIZE
from motion import B, W, Rz, Ry, animate, basis, cam0, ease, interpolate, mix, norm, phases, rig, rotation_mix, t_lift, t_setup, torso, unit, v
import pixels
from skin import normals_tris

PISTOL = json.loads((DATA / 'pistol.json').read_text())
REACH = json.loads((DATA / 'reach-reference.json').read_text())
START = animate(t_setup)
LOW = animate(t_lift)
GROUND = np.diag((1., -math.sin(cam0), math.sin(cam0)))
GROUND[1,2] = -math.cos(cam0)
GROUND[2,1] = -math.cos(cam0)
PIXELS_PER_B = 26
PIVOT = (56, 89)
WIDTH = HEIGHT = 112
PICKUP_HEIGHT = 132
STRIDE_SCALE = .76
PICKUP_DIRECTIONS = 32
PICKUP_PHASES = 23
GRAB = 11
PICKUP_FPS = 24
ROOT_SCALE = 32
pixels.F = 2
pixels.H = SIZE * pixels.F
raw_weld = pixels.weld
welded = {}
def cached_weld(vertices, normals):
    key = id(vertices)
    if key not in welded:
        welded[key] = raw_weld(vertices,normals)
    return welded[key]
pixels.weld = cached_weld


def pose_arm(body, wrist_offset, elbow_offset, *, closed=1.):
    j = dict(body['j'])
    shoulder = j['shoulder.R']
    wrist = shoulder + wrist_offset
    elbow = np.asarray(rig.solve_two_bone(shoulder,wrist,B['upper_arm'],B['forearm'],shoulder+elbow_offset))
    fore = unit(wrist-elbow)
    # The hand continues the forearm. The transverse axis shapes the fingers.
    transverse = np.cross(fore, v(0.,1.,0.))
    if norm(transverse)<.05:
        transverse = np.cross(fore,v(1.,0.,0.))
    hand = basis(transverse,fore)
    grip = wrist + .218 * fore
    j.update({'elbow.R':elbow,'wrist.R':wrist,'hand.R':wrist+B['hand']*fore,'grip.R':grip})
    pose = body | {'j':j, 'g':grip, 'R':hand}
    inward=unit(j['shoulder.L']-shoulder)
    meshes=rig_art.posed_geometry(pose,hand,fore,body,closed,inward)
    return pose, [m for m in meshes if not m[0].startswith('hatchet.')]


FREE_WRIST = np.asarray(REACH['ready_wrist_B'])
FREE_ELBOW = np.asarray(REACH['ready_elbow_B'])
PISTOL_WRIST = v(.64,-.24,-.60)
PISTOL_ELBOW = v(.08,-.55,-.63)
CONTACT_WRIST = np.asarray(REACH['contact_wrist_B'])
CONTACT_ELBOW = np.asarray(REACH['contact_elbow_B'])


def pistol_mesh(pose):
    j=pose['j']
    forward=torso(j)[:,0]
    frame=basis(forward,v(0.,1.,0.))
    faces=((0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3))
    triangle_indices=[i for a,b,c,d in faces for i in (a,b,c,a,c,d)]
    groups=[]
    for item,material in zip(PISTOL['rigid_parts'],(11,9,10),strict=True):
        pts=np.asarray(item['vertices_local_B'],dtype=float)[triangle_indices] @ frame.T + j['grip.R']
        groups.append((item['name'],pts,normals_tris(pts),material,6))
    return groups


def walk_body(phase):
    if phase is None:
        return START
    body=interpolate(W,phases,phase)
    j=dict(body['j'])
    root_x=j['root'][0]
    pelvis_delta=(j['pelvis'][0]-root_x)*(STRIDE_SCALE-1.)
    for key in ('pelvis','hip.L','hip.R','chest','neck','head','shoulder.L','shoulder.R',
                'elbow.L','wrist.L','hand.L'):
        j[key]=j[key]+v(pelvis_delta,0.,0.)
    for side in 'LR':
        ankle='ankle.'+side
        shift=(j[ankle][0]-root_x)*(STRIDE_SCALE-1.)
        for k in ('heel','toe','ankle'):
            j[k+'.'+side]=j[k+'.'+side]+v(shift,0.,0.)
        hip,knee='hip.'+side,'knee.'+side
        j[knee]=np.asarray(rig.solve_two_bone(j[hip],j[ankle],B['thigh'],B['shin'],j[knee]))
    return body | {'j':j}


def locomotion(look, phase):
    body=walk_body(phase)
    rotation=torso(body['j'])@torso(START['j']).T
    if look=='unarmed':
        swing=0. if phase is None else math.radians(9.)*math.sin(2.*math.pi*phase)
        rotation=rotation@Ry(swing)
        pose,meshes=pose_arm(body,rotation@FREE_WRIST,rotation@FREE_ELBOW,closed=.37)
    else:
        pose,meshes=pose_arm(body,rotation@PISTOL_WRIST,rotation@PISTOL_ELBOW)
        meshes.extend(pistol_mesh(pose))
    return pose,meshes


def pickup_body(amount):
    if amount<=0:
        return START
    first,last=START['j'],LOW['j']
    j=dict(first)
    j['pelvis']=mix(first['pelvis'],last['pelvis'],amount)
    before,after=torso(first),torso(last)
    tilt=rotation_mix(before,after,amount)
    for key in ('chest','neck','head','shoulder.L','shoulder.R'):
        offset=mix(before.T@(first[key]-first['pelvis']),after.T@(last[key]-last['pelvis']),amount)
        j[key]=j['pelvis']+tilt@offset
    for s in 'LR':
        hip='hip.'+s
        j[hip]=j['pelvis']+mix(first[hip]-first['pelvis'],last[hip]-last['pelvis'],amount)
    sh='shoulder.L'
    upper=unit(mix(first['elbow.L']-first[sh],last['elbow.L']-last[sh],amount))
    lower=unit(mix(first['wrist.L']-first['elbow.L'],last['wrist.L']-last['elbow.L'],amount))
    j['elbow.L']=j[sh]+B['upper_arm']*upper
    j['wrist.L']=j['elbow.L']+B['forearm']*lower
    j['hand.L']=j['wrist.L']+B['hand']*lower
    for key in ('pelvis','chest','head','neck','hip.L','hip.R','shoulder.L',
                'shoulder.R','elbow.L','wrist.L','hand.L'):
        j[key]=j[key]+v(0,0,-.125*amount)
    for side in 'LR':
        hip,knee,ankle=(k+'.'+side for k in ('hip','knee','ankle'))
        j[knee]=np.asarray(rig.solve_two_bone(j[hip],j[ankle],B['thigh'],B['shin'],j[knee]))
    return START | {'j':j}


def pickup(index):
    if index<=GRAB:
        u=ease(index/GRAB)
        from_wrist,from_elbow=FREE_WRIST,FREE_ELBOW
        close=mix(.37,1.,ease((index/GRAB-.58)/.42))
    else:
        u=1.-ease((index-GRAB)/(PICKUP_PHASES-GRAB-1))
        from_wrist,from_elbow=PISTOL_WRIST,PISTOL_ELBOW
        close=1.
    body=pickup_body(u)
    out=unit(body['j']['shoulder.R']-body['j']['shoulder.L'])
    allowance=.11*math.sin(math.pi*u)**2
    wrist=mix(from_wrist,CONTACT_WRIST,u)+allowance*out
    elbow=mix(from_elbow,CONTACT_ELBOW,u)+allowance*out
    return pose_arm(body,wrist,elbow,closed=close)


def audit(pose,parts):
    def vertices(prefix):
        return np.concatenate([p[1] for p in parts if p[0].startswith(prefix)])
    skirt=vertices('skirt.shell')
    legs=vertices(('thigh.','shin.','boot-cuff.'))
    coat=vertices(('coat.body','skirt.shell'))
    j=pose['j']
    sleeve=vertices('sleeve.R.').reshape(-1,3,3)
    fore=sleeve[sleeve[:,:,2].mean(1)<j['elbow.R'][2]]
    return {'knee_hem_pairs':count(legs,skirt),'forearm_coat_pairs':count(fore,coat),
            'hand_coat_pairs':count(vertices('hand.R.'),coat)}


def image(pose,parts,camera,height=HEIGHT):
    color,tag=pixels.buffers(pose,parts,camera,PXY)
    def samples(data):
        return data.reshape(SIZE,2,SIZE,2).transpose(0,2,1,3).reshape(-1,4)
    cols=samples(color)
    solid=cols>=0
    active=solid.sum(1)>=2
    y,x=np.nonzero(solid)
    palette=pixels.colors.reshape(-1,3)
    votes=np.zeros((SIZE*SIZE,len(palette)),dtype=np.uint8)
    np.add.at(votes,(y,cols[y,x]),1)
    selection=votes.argmax(1)
    rgba=np.zeros((SIZE*SIZE,4),dtype=np.uint8)
    rgba[active,:3]=palette[selection[active]]
    rgba[active,3]=255
    rgba=rgba.reshape(SIZE,SIZE,4)
    crop=rgba[:height,24:136]
    if np.count_nonzero(crop[:,:,3])!=np.count_nonzero(rgba[:,:,3]):
        raise ValueError('Clipped frame at the fixed ground pivot.')
    return crop


def render(job):
    kind, idx=job
    welded.clear()
    if kind=='pickup':
        pose,parts=pickup(idx)
        directions=PICKUP_DIRECTIONS
    else:
        pose,parts=locomotion(kind,None if idx==0 else (idx-1)/8)
        directions=128
    checks=audit(pose,parts)
    frames=[]
    sockets=[]
    for direction in range(directions):
        camera=GROUND@Rz(2.*math.pi*direction/directions)
        try:
            frames.append(image(pose,parts,camera,PICKUP_HEIGHT if kind=='pickup' else HEIGHT))
        except ValueError as error:
            raise ValueError(f'{kind} phase {idx}, direction {direction}: {error}') from error
        grip=(pose['j']['grip.R']-pose['j']['root'])@camera[:2].T*PIXELS_PER_B/ROOT_SCALE
        sockets.append({'x':round(float(grip[0]),7),'y':round(-float(grip[1]),7)})
    return kind,idx,frames,sockets,checks


def packed(frames, directory, manifest):
    """Trim fixed-pivot frames and pack losslessly into binary-alpha pages."""
    directory.mkdir(parents=True,exist_ok=True)
    tex=directory/'Textures'
    tex.mkdir(exist_ok=True)
    table=[]
    pages=[]
    pixels_array=np.zeros((2048,1792,4),dtype=np.uint8)
    x=y=row=used_w=used_h=0
    digest=hashlib.sha256()
    def finish_page():
        if not used_h:
            return
        page=Image.fromarray(pixels_array[:used_h,:used_w])
        path=tex/f'sibir128-atlas-{len(pages)}.png'
        page.save(path,optimize=True)
        pages.append({'file':f'Textures/{path.name}','width':used_w,'height':used_h})
    for art in frames:
        digest.update(art.tobytes())
        yy,xx=np.nonzero(art[:,:,3])
        left,top=min(int(xx.min()),PIVOT[0]),min(int(yy.min()),PIVOT[1])
        right,bottom=max(int(xx.max())+1,PIVOT[0]+1),max(int(yy.max())+1,PIVOT[1]+1)
        w,h=right-left,bottom-top
        if x+w+4>pixels_array.shape[1]:
            y+=row
            x=row=0
        if y+h+4>pixels_array.shape[0]:
            finish_page()
            pixels_array.fill(0)
            x=y=row=used_w=used_h=0
        pixels_array[y+2:y+h+2,x+2:x+w+2]=art[top:bottom,left:right]
        table.append({'page':len(pages),'x':x+2,'y':y+2,'w':w,'h':h,'pivotX':56-left,
                      'pivotY':89-top,'trimX':left,'trimY':top})
        x+=w+4
        row=max(row,h+4)
        used_w=max(x,used_w)
        used_h=max(y+row,used_h)
    finish_page()
    manifest.update({'schemaVersion':1,'canvasWidth':WIDTH,'canvasHeight':frames[0].shape[0],'rootX':56,'rootY':89,
                     'pixelsPerUnit':ROOT_SCALE,'pixelsPerB':PIXELS_PER_B,'groundVerticalScale':math.sin(cam0),
                     'cycleTravelB':STRIDE_SCALE*float(W[-1]['j']['root'][0]-W[0]['j']['root'][0]),'sourceHash':digest.hexdigest(),
                     'pages':pages,'frames':table})
    (directory/'sibir128.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n')
    # Production input textures must preserve the exact exported pixels and pivot.
    page_data=[np.asarray(Image.open(directory/p['file']).convert('RGBA')) for p in pages]
    for outer,frame in zip(frames,table,strict=True):
        x,y,w,h,tx,ty=(frame[k] for k in ('x','y','w','h','trimX','trimY'))
        reconstructed=np.zeros_like(outer)
        reconstructed[ty:ty+h,tx:tx+w]=page_data[frame['page']][y:y+h,x:x+w]
        np.testing.assert_array_equal(reconstructed,outer)


def metadata(folder, asset_root):
    template=(PROJECT/'Assets/Sibir128/Textures/sibir128-atlas-0.png.meta').read_text()
    texture=template[template.index('TextureImporter:'):]
    for p in (folder,*sorted(folder.rglob('*'))):
        if p.suffix=='.meta':
            continue
        meta=Path(str(p)+'.meta')
        if meta.exists():
            continue
        ident=uuid5(NAMESPACE_URL,'shooter2d/pistol-pickup-art/'+str(p.relative_to(asset_root))).hex
        settings=('folderAsset: yes\nDefaultImporter:\n  externalObjects: {}\n' if p.is_dir() else
                  texture if p.suffix=='.png' else 'TextScriptImporter:\n  externalObjects: {}\n')
        meta.write_text('fileFormatVersion: 2\nguid: '+ident+'\n'+settings)


def review(sets, report_root):
    canvas=Image.new('RGB',(960,752),'#233139')
    draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf',18)
    for row,(kind,ids) in enumerate([('unarmed',[1,3,5,7]),('pistol',[1,3,5,7]),('pickup',[0,6,GRAB,17])]):
        draw.text((18,row*244+6),{'unarmed':'Ходьба без оружия','pistol':'Ходьба с пистолетом','pickup':'Наклон, захват и подъём'}[kind],font=font,fill='#e9e4dd')
        for col,idx in enumerate(ids):
            art=Image.fromarray(sets[kind][idx][2][28 if kind=='pickup' else 112])
            art=art.resize((art.width*2,art.height*2),Image.Resampling.NEAREST)
            canvas.paste(art,(col*230+15,row*244),art)
    canvas.save(report_root/'pistol-pickup-frames.png')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--probe',action='store_true')
    parser.add_argument('--asset-root',type=Path,default=PROJECT/'Assets')
    parser.add_argument('--report-root',type=Path,default=PROJECT/'Docs/SibirPistolPickup')
    args=parser.parse_args()
    assets=args.asset_root.resolve()
    looks=assets/'Resources/Sibir128Looks'
    reports=args.report_root.resolve()
    jobs=[(k,i) for k,n in (('unarmed',9),('pistol',9),('pickup',PICKUP_PHASES)) for i in range(n)]
    if args.probe:
        for k,i in jobs:
            pose,parts=pickup(i) if k=='pickup' else locomotion(k,None if i==0 else (i-1)/8)
            print(k,i,audit(pose,parts),pose['j']['grip.R'].round(3).tolist(),flush=True)
        return
    sets={k:{} for k in ('unarmed','pistol','pickup')}
    with ProcessPoolExecutor(max_workers=4,mp_context=mp.get_context('fork')) as pool:
        for result in pool.map(render,jobs,chunksize=1):
            kind,idx,_,_,check=result
            sets[kind][idx]=result
            print(kind,idx,check,flush=True)
    for kind,group in sets.items():
        assert not any(row[4]['knee_hem_pairs'] for row in group.values()),kind
        frames=[art for idx in sorted(group) for art in group[idx][2]]
        n=PICKUP_DIRECTIONS if kind=='pickup' else 128
        common={'directionCount':n,'directionStepDegrees':360/n}
        if kind=='pickup':
            common.update({'grabPhase':GRAB,'grips':[g for i in sorted(group) for g in group[i][3]],
                           'animations':[{'name':'pickup','phaseCount':PICKUP_PHASES,'fps':PICKUP_FPS,'loop':False,
                                          'frameIds':list(range(len(frames)))}]})
            scene_assets=looks/'pistol-pickup'
        else:
            common['animations']=[{'name':'idle','phaseCount':1,'fps':0,'loop':True,'frameIds':list(range(128))},
                                  {'name':'walk','phaseCount':8,'fps':8,'loop':True,
                                   'frameIds':list(range(128,len(frames)))}]
            scene_assets=looks/kind
        packed(frames,scene_assets,common)
        metadata(scene_assets,assets)
        # Clean only obsolete atlas pages from this exporter.
        current={Path(p['file']).name for p in common['pages']}
        for page in (scene_assets/'Textures').glob('sibir128-atlas-*.png'):
            if page.name not in current:
                page.unlink()
                Path(str(page)+'.meta').unlink(missing_ok=True)
    reports.mkdir(parents=True,exist_ok=True)
    (assets/'Sibir128').mkdir(parents=True,exist_ok=True)
    Image.fromarray(sets['unarmed'][0][2][112]).save(assets/'Sibir128/PistolPickupTestIdle.png')
    review(sets,reports)
    (reports/'pistol-art-check.json').write_text(json.dumps({kind:[row[4] for row in group.values()]
                                                        for kind,group in sets.items()},indent=2)+'\n')


if __name__=='__main__':
    main()
