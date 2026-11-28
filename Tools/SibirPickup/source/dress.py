from motion import *
import skin
import hem

source=json.loads((DATA/'source-stance.json').read_text())
rest=rig.model('ready')
restJ={k:np.array(q) for k,q in rest['joints'].items()}
parts=source['looks']['axe']
remap=np.array([[1,0,0],[0,0,1],[0,-1,0]])
def world(buf):return np.asarray(buf).reshape(-1,3)@remap
def foot_frame(j,s):
 x=unit(j['toe.'+s]-j['heel.'+s]);y=v(0,1,0)
 return basis(x,y)
def bone_frame(j,bind,kind=''):
 p=j[bind]
 key,_,side=bind.partition('.')
 if key=='ankle':R=foot_frame(j,side)
 elif key in ('hip','knee','shoulder','elbow','wrist','hand'):
  child={'hip':'knee','knee':'ankle','shoulder':'elbow','elbow':'wrist','wrist':'hand','hand':'hand'}
  if key=='wrist' and kind.startswith('cuff.'):z=unit(p-j['elbow.'+side])
  elif key=='hand':z=unit(p-j['wrist.'+side])
  else:z=unit(j[child[key]+'.'+side]-p)
  x=v(1,0,0)-z*z[0]
  if norm(x)<1e-6:x=v(0,1,0)-z*z[1]
  x=unit(x);y=np.cross(z,x)
  R=np.column_stack([x,y,z])
 elif key in ('head','neck','chest'):R=torso(j)
 elif key=='pelvis':R=hips(j)
 else:R=np.eye(3)
 return p,R
palette=[
 ['#251f20','#493b34','#695447'], # coat
 skin.CROWN, # hat
 skin.FUR, # fur
 ['#282629','#464440','#5d564e'], # trousers
 ['#261e20','#453932','#604c40'], # boots
 ['#9a6050','#c58a68','#e1a784'], # skin
 ['#766e68','#a69e90','#c9c0ac'], # beard
 ['#342b2b','#57443a','#7c624e'], # folds
 ['#67422e','#a87549','#cb9a66'], # wood
 ['#454b51','#74818a','#a9bdc2'], # metal
 ['#342e2c','#716858','#939589'], # trim
 ['#262126','#262126','#3a2c2c'], # outline
]
colors=np.array([[[int(c[i:i+2],16) for i in (1,3,5)] for c in row] for row in palette],dtype=np.uint8)
def style(name):
 if name.startswith(('eye','neck','sole')):return 11
 if name.startswith(('sideburn','beard','moustache','brow')):return 6
 if name.startswith(('free-','nose','head','ear','mouth')):return 5
 if name.startswith(('thigh','shin')):return 3
 if name.startswith('boot'):return 4
 if name.startswith('ushanka') and not name.startswith('ushanka.crown') and name!='ushanka.fold.light':return 2
 if name.startswith('ushanka'):return 1
 if name.startswith(('collar','cuff')):return 2
 if name=='buckle':return 10
 if name.startswith(('coat.fold','closure','seam','lower-sleeve.R.crease','lower-sleeve.L.crease','fastener','elbow.wear','pocket','belt')):return 7
 return 0

def tag(name):
 if name.startswith(('boot','sole')):return 2
 if name.startswith('cuff.'):return 3
 if name.startswith(('coat.hem','coat.body','coat.fold','pocket','closure')):return 4
 if name.startswith('hatchet.handle'):return 5
 if name.startswith('hatchet.'):return 6
 if name in ('hand.R','palm.R'):return 7
 return 1
axe_src=rig.model('ready')
ax=v(*axe_src['axe_axis']);blade=v(*axe_src['blade_axis'])
base_axe=np.column_stack((ax,np.cross(blade,ax),blade))
groups=[]
for p in parts:
 n,b=p['name'],p['bind'];q,N=world(p['positions']),world(p['normals'])
 if n.startswith(('gripping','grip-','upper-sleeve','lower-sleeve','elbow.skin','elbow.wear')) or n=='coat.hem' or n.startswith('cuff.'):continue
 if n.startswith('ushanka.'):
  q=skin.hat_model(n,q)
 if b in ('pelvis','chest') and n.startswith(('coat','closure','fastener','pocket','back.seam')):
  q,N=skin.crop_top(q,N)
  if not len(q):continue
 if n.startswith('hatchet.'):
  q=(q-restJ['grip.R'])@base_axe;N=N@base_axe
  groups.append((n,b,q,N,8 if n=='hatchet.handle' else 9,tag(n),None))
  continue
 if b.startswith('ankle.'):
  j0=restJ[b]
  q[:,0]=np.clip(q[:,0],j0[0]-.15,j0[0]+.50)
  q[:,2]-=.025
 is_coat=b in ('chest','pelvis') and n.startswith(('coat','closure','fastener','belt','buckle','back.seam','pocket'))
 if is_coat:
  w=np.clip((q[:,2]-1.90)/(2.9-1.90),0,1)
  w=w*w*(3-2*w)
  start=restJ['pelvis'];pc,br=bone_frame(restJ,'chest')
  c=(q-pc)@br
  groups.append((n,b,q,N,style(n),tag(n),(w,c,q-start, N@br)))
  continue
 p0,M=bone_frame(restJ,b,n)
 local=(q-p0)@M
 N=N@M
 if n.startswith('cuff.'):
  local[:,:2]*=.86
  local[:,2]*=.86
 groups.append((n,b,local,N,style(n),tag(n),None))

def hull_3d_link(a,b,r0,r1,N=6):
 d=unit(b-a)
 v0=unit(np.cross(d,v(.11,.20,1.) if abs(d[2])<.94 else v(0,1,0)))
 w=np.cross(d,v0);out=[];normals=[]
 for k in range(N):
  X,Y=(v0*math.cos(p)+w*math.sin(p) for p in (k*math.tau/N,(k+1)*math.tau/N))
  A,C,D,E=(a+r0*X,a+r0*Y,b+r1*X,b+r1*Y)
  out.extend((A,C,D,D,C,E,a,C,A,b,D,E));normals.extend((X,Y,X,X,Y,Y,-d,-d,-d,d,d,d))
 return np.array(out),np.array(normals)
light=unit(v(.31,.28,.91))
PXY=v(80,89)
SIZE=184

def geometry(f):
 j=f['j'];squat=float(np.clip((2.28-j['pelvis'][2])/1.21,0,1))
 Jpel=j['pelvis'];H=hips(j);C=torso(j)
 overall=[]
 for n,b,q,N,col,t,cloth in groups:
  if b=='grip.R':
   R=f['R'];P=f['g'];V=q@R.T+P;N=N@R.T
  elif cloth is not None:
   strength,localC,localH,NC=cloth
   wc=strength[:,None]
   # Lower edge follows the pelvis and rises slightly as the coat folds over the thighs.
   below=np.clip((2.03-q[:,2])/1.06,0,1)
   lower=localH.copy()
   lower[:,2]+=squat*.32*below
   lower[:,0]+=squat*.13*below*np.clip((q[:,0]+.18)/.5,0,1)
   V=(lower@H.T+Jpel)*(1-wc)+(localC@C.T+j['chest'])*wc
   N=(N@H.T)*(1-wc)+(NC@C.T)*wc
  else:
   P,R=bone_frame(j,b,n)
   V=q@R.T+P;N=N@R.T
  if cloth is not None and n.startswith(('coat','closure','fastener','pocket','back.seam')):
   # Keep the original upper garment behind the flexible skirt at the waist.
   V,N=skin.crop_top(V,N,Jpel[2]+.205+.032*squat)
   if not len(V):continue
  overall.append((n,V,N,col,t))
 # Pose the same finger chains around the shared grip, then rasterize.
 D=f['digits'];p=f['palm'];w=j['wrist.R']
 a,b=D['index'][0],D['little'][0]
 links=[(w,p,.074,.069,'palm.R'),(p,(a+b)*.5,.068,.028,'palm.R'),(a,b,.028,.024,'palm.R')]
 for ps in D.values():
  links.extend((a0,b0,.025,.022,'hand.R') for a0,b0 in zip(ps[:-1],ps[1:]))
 for a,b,r0,r1,n in links:
  if norm(b-a)<1e-6:continue
  V,N=hull_3d_link(a,b,r0,r1)
  overall.append((n,V,N,5,7))
 overall.extend(hem.make_skirt(j,overall))
 for side in ('L','R'):
  overall.extend(skin.sleeve_fabric(j,side))
  overall.append(skin.cuff(j,side))
 return overall
