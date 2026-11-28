from pathlib import Path
import json,math
import numpy as np
from bisect import bisect_right
DATA = Path(__file__).resolve().parents[1] / 'data'
import humanoid_rig as rig
src=json.loads((DATA/'carry-motion.json').read_text())
pfs=src['pickup']['frames'];wfs=src['walk']['frames']
start=pfs[-1]
t_lift=next(float(x['time_s']) for x in pfs if x['attached']);t_setup=float(pfs[-1]['time_s'])
cam0=math.radians(60);yaw=math.radians(-45)
v=lambda *x:np.array(x,dtype=float)
def norm(x):return float(np.linalg.norm(x))
def unit(x):return x/norm(x)
def mix(x,y,u):return x*(1-u)+y*u
def ease(u):
 u=float(np.clip(u,0,1));return u*u*u*(10-15*u+6*u*u)
def herm(p0,p1,m0,m1,u):
 return ((2*u**3-3*u*u+1)*p0+(-2*u**3+3*u*u)*p1+(u**3-2*u*u+u)*m0+(u**3-u*u)*m1)
def Rz(t):
 c,s=math.cos(t),math.sin(t)
 return np.array([[c,-s,0],[s,c,0],[0,0,1]])
def Ry(t):
 c,s=math.cos(t),math.sin(t)
 return np.array([[c,0,s],[0,1,0],[-s,0,c]])
cam=np.array([[1,0,0],[0,-math.sin(cam0),-math.cos(cam0)],[0,-math.cos(cam0),math.sin(cam0)]])@Rz(yaw)
ppu=32
scale=26
speed=5.
stride=src['walk']['distance_B']
distance=stride*norm(cam[:2]@v(1,0,0))*scale/ppu
cycle_time=distance/speed
shift_time=.16;step_time=.36;bridge_time=shift_time+step_time
t_land=t_setup+bridge_time
t_end=t_land+cycle_time*.5
phase_end=.50
B=src['profile']['bones']
def parse(f):
 return {'j':{k:np.asarray(q,dtype=float) for k,q in f['joints_world_B'].items()},
    'R':np.array(f['item_basis']), 'g':np.array(f['item_position_B']),
    'digits':{k:np.array(q) for k,q in f['digits_world_B'].items()},'palm':np.array(f['palm_world_B']),
    'closure':float(f['digit_closure']),'contacts':list(f['foot_contacts']),'held':bool(f['attached']),
    'mode':f['pose']}
P=[parse(f) for f in pfs];W=[parse(f) for f in wfs]
ts=np.array([f['time_s'] for f in pfs]);phases=np.array([f['phase'] for f in wfs])
def basis(x,y,z=None):
 x=unit(x)
 y=unit(y-x*(x@y))
 return np.column_stack([x,y,np.cross(x,y)])
def rotation_mix(A,B,u):
 if u<=0:return A
 if u>=1:return B
 D=B@A.T;phi=math.acos(np.clip((np.trace(D)-1)*.5,-1,1))
 if phi<1e-7:return A
 S=(D-D.T)/(2.*math.sin(phi))
 M=np.eye(3)+math.sin(phi*u)*S+(1-math.cos(phi*u))*(S@S)
 return M@A
def torso(j):
 y=unit(j['shoulder.L']-j['shoulder.R'])
 z=unit(j['neck']-j['chest'])
 x=unit(np.cross(y,z))
 return np.column_stack([x,y,np.cross(x,y)])
def hips(j):
 Y=unit(j['hip.L']-j['hip.R']);Z=v(0,0,1);X=unit(np.cross(Y,Z))
 return np.column_stack([X,Y,Z])

def transform(f,delta):
 return f|{'j':{k:q+delta for k,q in f['j'].items()}, 'digits':{k:p+delta for k,p in f['digits'].items()},
            'palm':f['palm']+delta,'g':f['g']+delta}
S=P[-1]
walk_anchor=W[18]['j']['ankle.L']
delta=S['j']['ankle.L']-walk_anchor
W=[transform(f,delta) for f in W]
# The export root moves along the direction of travel. It stays centred on its own path.
for f in W:f['j']['root'][1]=0
F=W[36]
def pitch(j,side):
 u=unit(j['toe.'+side]-j['heel.'+side])
 return math.atan2(u[2],u[0])
def shape_joints(A,F,u,*,pelvis=None,root=None,feet=None,split=None):
 if u<=0 and pelvis is None:return A
 if u>=1 and pelvis is None:return F
 j={}
 jA,jB=A['j'],F['j']
 p=mix(jA['pelvis'],jB['pelvis'],u) if pelvis is None else pelvis
 H=rotation_mix(hips(jA),hips(jB),u)
 C=rotation_mix(torso(jA),torso(jB),u)
 for k in ('chest','neck','head','shoulder.L','shoulder.R','hip.L','hip.R'):
  bA,bB,b=(hips(jA),hips(jB),H) if k.startswith('hip.') else (torso(jA),torso(jB),C)
  j[k]=p+b@mix(bA.T@(jA[k]-jA['pelvis']),bB.T@(jB[k]-jB['pelvis']),u)
 j['root']=mix(jA['root'],jB['root'],u) if root is None else root
 j['pelvis']=p
 for side in ('L','R'):
  if feet is None:
   # Rotate the rigid foot about whichever point is planted in both frames.
   ids=[k+'.'+side for k in ('ankle','heel','toe')]
   fA,fB=(A['contacts'][0 if side=='L' else 1],F['contacts'][0 if side=='L' else 1])
   anchor='toe' if fA in ('flat','toe') and fB in ('flat','toe') else 'heel'
   angleA,angleB=pitch(jA,side),pitch(jB,side)
   anch=anchor+'.'+side
   p0,p1=jA[anch],jB[anch]
   new_angle=mix(angleA,angleB,u)
   for id0 in ids:j[id0]=mix(p0,p1,u)+Ry(-new_angle)@mix(Ry(angleA)@(jA[id0]-p0),Ry(angleB)@(jB[id0]-p1),u)
  else:
   for k in ('heel','toe','ankle'):j[k+'.'+side]=feet[side][k]
 def solve(k0,k1,k2,L1,L2):
  # Endpoint reference poles preserve the elbow / knee plane at the splice.
  aa,bb=jA[k1]-jA[k0],jB[k1]-jB[k0]
  qa=unit(jA[k2]-jA[k0]);qb=unit(jB[k2]-jB[k0])
  bend=mix(unit(aa-qa*(aa@qa)),unit(bb-qb*(bb@qb)),u)
  j[k1]=np.asarray(rig.solve_two_bone(j[k0],j[k2],L1,L2,j[k0]+bend))
 for s in ('L','R'):
  solve('hip.'+s,'knee.'+s,'ankle.'+s,B['thigh'],B['shin'])
  if s=='L':
   j['wrist.L']=j['shoulder.L']+mix(jA['wrist.L']-jA['shoulder.L'],jB['wrist.L']-jB['shoulder.L'],u)
   j['hand.L']=j['wrist.L']+unit(mix(jA['hand.L']-jA['wrist.L'],jB['hand.L']-jB['wrist.L'],u))*B['hand']
 # Relative position and wrist orientation preserve the existing displacement of the axe.
 pg=(j['shoulder.R']+mix(A['g']-jA['shoulder.R'],F['g']-jB['shoulder.R'],u)) if split else mix(A['g'],F['g'],u)
 held=A['held']
 R=rotation_mix(A['R'],F['R'],u)
 hand_direction=unit(mix(jA['hand.R']-jA['wrist.R'],jB['hand.R']-jB['wrist.R'],u))
 if held:
  j['wrist.R']=pg-hand_direction*.25
  j['hand.R']=j['wrist.R']+hand_direction*.50
 else:
  j['wrist.R']=mix(jA['wrist.R'],jB['wrist.R'],u)
  j['hand.R']=j['wrist.R']+hand_direction*.50
 for s in ('L','R'):solve('shoulder.'+s,'elbow.'+s,'wrist.'+s,B['upper_arm'],B['forearm'])
 j['grip.R']=(j['wrist.R']+j['hand.R'])*.5
 j['axe.head']=pg+.65*R[:,0];j['axe.butt']=pg-.34*R[:,0]
 ds={}
 pr=pg if held else j['grip.R']
 for name,points in A['digits'].items():
  other=F['digits'][name]
  p0=points-(A['g'] if held else jA['grip.R']);p1=other-(F['g'] if held else jB['grip.R'])
  J0=p0@A['R'];J1=p1@F['R']
  chain=[pr+R@mix(J0[0],J1[0],u)]
  for a0,b0 in zip(np.diff(J0,axis=0),np.diff(J1,axis=0)):
   chain.append(chain[-1]+R@unit(mix(a0,b0,u))*mix(norm(a0),norm(b0),u))
  ds[name]=np.array(chain)
 palm=pr+R@mix(A['R'].T@(A['palm']-(A['g'] if held else jA['grip.R'])),
               F['R'].T@(F['palm']-(F['g'] if held else jB['grip.R'])),u)
 locks={'flat':{'heel','toe'},'heel':{'heel'},'toe':{'toe'},'swing':set()}
 contact_type={frozenset(x):k for k,x in locks.items()}
 contacts=[contact_type[frozenset(locks[x]&locks[y])] for x,y in zip(A['contacts'],F['contacts'])]
 return {'j':j,'R':R,'g':pg,'digits':ds,'palm':palm,'held':held,'closure':mix(A['closure'],F['closure'],u),
         'mode':A['mode'] if u<.5 else F['mode'],'contacts':contacts}

def interpolate(seq,vals,t):
 i=np.searchsorted(vals,t,side='right')-1
 if i<0:return seq[0]
 if i>=len(vals)-1:return seq[-1]
 u=(t-vals[i])/(vals[i+1]-vals[i])
 return shape_joints(seq[i],seq[i+1],float(u))
def planted(s):
 return {k:S['j'][k+'.'+s].copy() for k in ('ankle','heel','toe')}
def rigid(s,yaw,anch,key):
 f=planted(s)
 return {k:anch+Ry(-yaw)@(q-f[key]) for k,q in f.items()}
foot_target=F['j']
p_der=(W[37]['j']['pelvis']-W[35]['j']['pelvis'])/(2./72*cycle_time)
L_end=pitch(foot_target,'L')
L_vel=(pitch(W[37]['j'],'L')-pitch(W[35]['j'],'L'))/(2./72*cycle_time)
R_end=pitch(foot_target,'R')
end_heel=foot_target['heel.R']
p_mid=v(.004,.142,2.229)
start_root=F['j']['root'][0]
v_end=stride/cycle_time

def bridge(t):
 t=float(np.clip(t,0,bridge_time))
 J0=S['j'];all_u=t/bridge_time
 if t<=shift_time:
  u=ease(t/shift_time)
  p=mix(J0['pelvis'],p_mid,u)
  feet={x:planted(x) for x in ('L','R')}
  root=v(0,0,0)
  c=['flat','flat']
 else:
  u=(t-shift_time)/step_time
  tlocal=t-shift_time
  p=herm(p_mid,F['j']['pelvis'],np.zeros(3),p_der*step_time,u)
  # Forward displacement accelerates to the gait's running-time root speed.
  root=v(herm(0.,start_root,0.,v_end*step_time,u),0,0)
  s0=.59
  q=max(0,(u-s0)/(1-s0))
  exponent=L_vel*step_time*(1-s0)/L_end
  L_th=L_end*q**exponent
  lf=rigid('L',L_th,J0['toe.L'],'toe')
  # The swing starts with the back of the right boot rising, then brings the heel down.
  phi=mix(0,R_end,ease(u))-math.radians(28)*math.sin(math.pi*u)**2
  xy=mix(J0['heel.R'],end_heel,ease(u))
  xy[2]=.197*math.sin(math.pi*u)**2+max(0.,-.65*math.sin(phi))
  rf=rigid('R',phi,xy,'heel')
  feet={'L':lf,'R':rf}
  c=['flat' if u<=s0 else 'toe','swing' if u<1 else 'heel']
 if t>=bridge_time-1e-12:return F
 # Let the upper body meet the gait's motion as well as its position.
 lead=ease((t-(bridge_time-.09))/.09)
 preview_phase=.50+max(-.12,(t-bridge_time)*lead/cycle_time)
 end_pose=interpolate(W,phases,preview_phase)
 res=shape_joints(S,end_pose,ease(all_u),pelvis=p,root=root,feet=feet,split=True)
 # Let the carried volume follow a small lateral arc while the weight shifts.
 shift=v(0,-.062*math.sin(math.pi*all_u)**2,0)
 j=res['j']
 bend=j['elbow.R'].copy()
 for k in ('wrist.R','hand.R','grip.R','axe.head','axe.butt'):
  j[k]=j[k]+shift
 sh=j['shoulder.R']
 j['elbow.R']=np.asarray(rig.solve_two_bone(sh,j['wrist.R'],B['upper_arm'],B['forearm'],bend))
 res['g']=res['g']+shift;res['digits']={k:p+shift for k,p in res['digits'].items()}
 res['palm']=res['palm']+shift
 return res|{'contacts':c,'mode':'Перенос веса' if t<=shift_time else 'Первый шаг'}
def animate(t):
 if t<=0:return P[0]
 if t<t_setup:return interpolate(P,ts,t)
 if t<t_land:return bridge(t-t_setup)
 return interpolate(W,phases,min(1,.50+(t-t_land)/cycle_time))
