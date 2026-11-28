"""Shared 3D construction rig for orthographic humanoid sprite authoring.
Units are shoulder-joint separation B. This constructs references, not clinical
anatomy or finished character art. The same solver is used for every profile.
"""
import json,math
from pathlib import Path
HERE=Path(__file__).parent

def add(a,b):return tuple(x+y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def mul(a,k):return tuple(x*k for x in a)
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def length(a):return math.sqrt(dot(a,a))
def unit(a):
 n=length(a)
 if n<1e-9:raise ValueError('Cannot normalize a zero vector')
 return mul(a,1/n)
def rotate(a,t):return (a[0]*math.cos(t)-a[1]*math.sin(t),a[0]*math.sin(t)+a[1]*math.cos(t),a[2])
def solve_two_bone(start,end,l1,l2,pole):
 delta=sub(end,start);d=length(delta)
 if not abs(l1-l2)+1e-7<d<l1+l2-1e-7:raise ValueError(f'Unreachable limb target: {d:g}')
 u=unit(delta);q=sub(pole,start);v=unit(sub(q,mul(u,dot(q,u))))
 a=(l1*l1-l2*l2+d*d)/(2*d);h=math.sqrt(max(0,l1*l1-a*a))
 return add(start,add(mul(u,a),mul(v,h)))

POSES={
 'ready':dict(yaw=0,hip_x=-.06,right=(.22,-.56,2.24),left=(-.03,.53,2.23),axe=(1,0,-.15)),
 'windup':dict(yaw=-.25,hip_x=-.13,right=(-.48,-.82,3.5),left=(.45,.7,2.95),axe=(-.45,-.3,.6)),
 'strike':dict(yaw=.18,hip_x=.05,right=(1.02,-.16,2.92),left=(-.12,.85,2.8),axe=(.7,.25,-.1)),
 'recover':dict(yaw=.07,hip_x=-.03,right=(.78,-.5,2.74),left=(.18,.72,2.85),axe=(.5,.15,.35)),
}

def load_profile(name='adult'):
 return json.loads((HERE/'profiles'/f'{name}.json').read_text())

def model(pose='ready',profile=None,walk_phase=None,targets=None):
 p=POSES[pose].copy();p.update(targets or {});pr=profile or load_profile();b=pr['bones'];height=pr['heights'];wide=pr['widths']
 # All paired limb lengths come from the same profile fields.
 sc=(p['hip_x']+.06,0,height['shoulder']);hc=(p['hip_x'],0,height['hip'])
 sl=add(sc,rotate((0,wide['shoulder']/2,0),p['yaw']));sr=add(sc,rotate((0,-wide['shoulder']/2,0),p['yaw']))
 hl=add(hc,(0,wide['hips']/2,0));hr=add(hc,(0,-wide['hips']/2,0))
 feet=p.get('feet',[(.2,.28,.08),(-.3,-.28,.08)])
 motion=None
 if walk_phase is not None:
  stride=p.get('stride',.5);duty=.6;motion={'root_travel_B_per_cycle':stride/duty,'stance_fraction':duty}
  feet=[]
  for side,offset in [(1,0),(-1,.5)]:
   phase=(walk_phase+offset)%1
   if phase<duty:x=stride/2-stride*phase/duty;z=.08
   else:
    q=(phase-duty)/(1-duty);ease=q*q*(3-2*q)
    x=-stride/2+stride*ease;z=.08+.18*math.sin(math.pi*q)
   feet.append((x,.28*side,z))
 fl,fr=feet
 # Targets are expressed relative to the profile shoulder height so a size
 # profile can change the stance without copying the action or solver.
 canonical_sc=(p['hip_x']+.06,0,3.65)
 canonical_sl=add(canonical_sc,rotate((0,.5,0),p['yaw']));canonical_sr=add(canonical_sc,rotate((0,-.5,0),p['yaw']))
 arm_ratio=(b['upper_arm']+b['forearm'])/1.5
 wl=add(sl,mul(sub(p['left'],canonical_sl),arm_ratio));wr=add(sr,mul(sub(p['right'],canonical_sr),arm_ratio))
 el=solve_two_bone(sl,wl,b['upper_arm'],b['forearm'],add(sc,(-.5,.5,-1.0)))
 er=solve_two_bone(sr,wr,b['upper_arm'],b['forearm'],add(sc,(-.5,-.5,-1.0)))
 kl=solve_two_bone(hl,fl,b['thigh'],b['shin'],(.9,.3,1))
 kr=solve_two_bone(hr,fr,b['thigh'],b['shin'],(.9,-.3,1))
 # The hand continues the forearm. A power-grip shaft crosses its long axis.
 forward_r=unit(sub(wr,er));forward_l=unit(sub(wl,el))
 desired=unit(p['axe']);axe_axis=unit(sub(desired,mul(forward_r,dot(desired,forward_r))))
 grip=add(wr,mul(forward_r,b['hand']*.5))
 blade_desired=(1,0,0);blade_axis=unit(sub(blade_desired,mul(axe_axis,dot(blade_desired,axe_axis))))
 joints={'root':(0,0,0),'pelvis':hc,'chest':add(sc,(0,0,-.3)),'neck':add(sc,(0,0,.3)),
  'head':add(sc,(.05,0,.65)),
  'shoulder.L':sl,'elbow.L':el,'wrist.L':wl,'hand.L':add(wl,mul(forward_l,b['hand'])),
  'shoulder.R':sr,'elbow.R':er,'wrist.R':wr,'hand.R':add(wr,mul(forward_r,b['hand'])),
  'hip.L':hl,'knee.L':kl,'ankle.L':fl,'heel.L':add(fl,(-.15,0,-.08)),'toe.L':add(fl,(b['foot']-.15,0,-.08)),
  'hip.R':hr,'knee.R':kr,'ankle.R':fr,'heel.R':add(fr,(-.15,0,-.08)),'toe.R':add(fr,(b['foot']-.15,0,-.08)),
  'grip.R':grip,'axe.head':add(grip,mul(axe_axis,.65)),'axe.butt':add(grip,mul(axe_axis,-.2))}
 result={'pose':pose,'profile':pr['name'],'joints':joints,'hand_forward.R':forward_r,'axe_axis':axe_axis,'blade_axis':blade_axis,'locomotion':motion}
 validate(result,pr);return result

CHAINS={'arm.L':['shoulder.L','elbow.L','wrist.L','hand.L'],'arm.R':['shoulder.R','elbow.R','wrist.R','hand.R'],
 'leg.L':['hip.L','knee.L','ankle.L'],'leg.R':['hip.R','knee.R','ankle.R']}

def validate(m,pr):
 b=pr['bones'];j=m['joints'];errors=[]
 for side in ['L','R']:
  for a,c,key in [('shoulder','elbow','upper_arm'),('elbow','wrist','forearm'),('wrist','hand','hand'),('hip','knee','thigh'),('knee','ankle','shin'),('heel','toe','foot')]:
   actual=length(sub(j[f'{a}.{side}'],j[f'{c}.{side}']))
   if abs(actual-b[key])>1e-7:errors.append(f'{side} {key}: {actual}')
  a=unit(sub(j[f'shoulder.{side}'],j[f'elbow.{side}']));c=unit(sub(j[f'wrist.{side}'],j[f'elbow.{side}']))
  flex=180-math.degrees(math.acos(max(-1,min(1,dot(a,c)))))
  if not pr['limits']['elbow_flexion_deg'][0]<=flex<=pr['limits']['elbow_flexion_deg'][1]:errors.append(f'Elbow flexion {flex}')
 if abs(dot(m['hand_forward.R'],m['axe_axis']))>1e-7:errors.append('Axe shaft does not cross the hand')
 if length(sub(j['grip.R'],j['wrist.R']))>b['hand']:errors.append('Grip outside hand')
 if errors:raise ValueError('; '.join(errors))
 return True

def project(point,scale=22,origin=(48,48)):
 return (origin[0]+point[0]*scale,origin[1]-point[1]*scale)

def project_camera(point,scale=26,origin=(42,82),elevation_deg=60,heading_deg=-20):
 """Orthographic oblique view of the same 3D rig; 90 degrees is overhead.
 Camera looks from negative world Y. Heading rotates the whole posed subject,
 including feet and equipped item; it does not change anatomy or joint targets.
 """
 if not 0<elevation_deg<=90:raise ValueError('Camera elevation must be in (0, 90]')
 x,y,z=rotate(point,math.radians(heading_deg));e=math.radians(elevation_deg)
 return (origin[0]+x*scale,origin[1]-(y*math.sin(e)+z*math.cos(e))*scale)

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--pose',choices=POSES,default='ready');parser.add_argument('--profile',default='adult');parser.add_argument('--walk-phase',type=float);args=parser.parse_args()
 print(json.dumps(model(args.pose,load_profile(args.profile),args.walk_phase),indent=2))
