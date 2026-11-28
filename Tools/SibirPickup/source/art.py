import numpy as np
from motion import hips, torso, unit
from dress import colors as base_colors

accent_rows = [
    ('#302620','#443226','#503c30'), # crown seam
    ('#413027','#5d4536','#765944'), # worn crown panel
    ('#4c392c','#765b43','#a1805a'), # shadowed fur and cuff edge
    ('#372b27','#594538','#76604c'), # garmented seam and pocket lip
    ('#4b4034','#796650','#9b8566'), # subdued metal fittings
    ('#6c655a','#9a9182','#c2b9a7'),
    ('#393a35','#55574e','#77796c'),
    ('#8d948a','#b1b6ac','#d9ded3'),
    ('#4e3625','#7c5033','#ac774c'),
    ('#a05e4c','#cf8e70','#e9b69a'), # beard within existing palette range
]
colors = np.concatenate((base_colors,np.array(
    [[[int(c[i:i + 2],16) for i in (1,3,5)] for c in row] for row in accent_rows],dtype=np.uint8)))

def styled(name, vertices, normals, mat, shade, joints, part_origin):
    if name.startswith('ushanka.crown'):
        x,y,z=((vertices-joints['head'])@torso(joints)).T
        stroke=(abs(y+.018+.24*x*x)<.025)&(z>.255)&(x>-.32)&(x<.24)
        panel=(y>.025)&(y<.245)&(z>.29)&(x>-.265)&(x<.13-.24*y)
        worn=(x>.115)&(x<.227)&(y<-.095)&(y>-.249)&(z>.30)
        rim=(x>.15)&(x<.28)&(z>.205)&(z<.28)&(y>-.26)&(y<.12)
        mat[panel|worn|rim]=13
        mat[stroke]=12
        shade[stroke]=1
    elif name.startswith(('ushanka.fur-band','ushanka.band.light','ushanka.flap')):
        x,y,z=((vertices-joints['head'])@torso(joints)).T
        lower=(z<.092)&((x>.07)|(abs(y)>.276))
        short_tuft=(x>.175)&(x<.265)&(y<-.14)&(y>-.32)&(z<.164)
        mat[lower|short_tuft]=14
        tip=(z>.132)&(z<.19)&(y<-.06)&(y>-.27)&(x>.17)
        shade[tip]=np.minimum(shade[tip]+1,2)
    elif name.startswith(('skirt.shell','coat.body')):
        x,y,z=((vertices-joints['pelvis'])@hips(joints)).T
        front=x>.24
        yr=abs(y)
        if name.startswith('skirt.shell'):
            y_center=yr-.34
            pocket_z=z+.147+.38*y_center
            pocket=(yr>.205)&(yr<.502)&(x>.19)
            lip=pocket&(pocket_z<.016)&(pocket_z>-.043)
            pocket_shadow=pocket&(pocket_z<=-.042)&(pocket_z>-.092)
            mat[lip]=15
            shade[lip]=np.maximum(shade[lip],2)
            mat[pocket_shadow]=0
            shade[pocket_shadow]=0
            overlap=front&(yr<.039)&(z<.12)&(z>-.62)
            mat[overlap]=15
            shade[overlap]=np.minimum(shade[overlap],1)
        else:
            seam=front&(abs(y+.041)<.032)&(z>.23)&(z<.98)
            mat[seam]=15
            shade[seam]=np.minimum(shade[seam]+1,2)
            lap=(yr>.25)&(yr<.52)&(x>.27)&(abs(z-(.60+.63*yr))<.042)
            mat[lap]=15
            shade[lap]=np.minimum(shade[lap],1)
    elif name.startswith(('fastener','buckle')) and name!='buckle-inset':
        mat[:]=16
        shade[:]=np.maximum(shade,1)
    elif name=='belt':
        x,y,z=((vertices-joints['pelvis'])@hips(joints)).T
        matte=abs(y+.19)<.040
        loop=matte&(z>-.05)&(z<.12)&(x>.20)
        mat[loop]=15
        shade[loop]=np.maximum(shade[loop],1)
    elif name.startswith('collar.'):
        x,y,z=((vertices-joints['pelvis'])@hips(joints)).T
        shaded_edge=(z<1.14+.43*abs(y))&(x>.19)
        mat[shaded_edge]=14
        shade[shaded_edge]=np.minimum(shade[shaded_edge],1)
    elif name.startswith('sleeve.'):
        side=name.split('.')[1]
        arm=unit(joints['elbow.'+side]-joints['shoulder.'+side])
        track=(vertices-joints['shoulder.'+side])@arm
        coat_top=(normals[:,2]>.57)&(normals[:,0]>-.49)
        seam=(track>.235)&(track<.282)&coat_top
        mat[seam]=15
        shade[seam]=np.minimum(shade[seam],1)
    elif name.startswith('cuff.'):
        side=name[-1]
        axis=unit(joints['wrist.'+side]-joints['elbow.'+side])
        track=(vertices-part_origin)@axis
        rim=(track>track.max()-.028)
        mat[rim]=14
        shade[rim]=np.minimum(shade[rim],1)
    elif name.startswith(('beard.','moustache')):
        x,y,z=((vertices-joints['head'])@torso(joints)).T
        cluster=(x>.20)&(z<-.19)&(y<.105)&(y>-.19)
        mat[cluster]=17
        shade[cluster]=np.maximum(shade[cluster],1)
    elif name=='head':
        x,y,z=((vertices-joints['head'])@torso(joints)).T
        cheek=(x>.15)&(abs(y)>.085)&(abs(y)<.19)&(z<.055)&(z>-.09)
        shade[cheek]=np.minimum(shade[cheek],1)
    elif name=='hatchet.handle':
        mat[:]=20
    elif name=='hatchet.blade' and mat[0]==18:
        shade[:]=np.minimum(shade,1)
    elif '.toe-wear' in name:
        shade[:]=np.minimum(np.maximum(shade,1),2)
    return mat, shade
