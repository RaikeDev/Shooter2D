from motion import *
SECTION_COUNT=20
RING_KNIVES=np.linspace(0,math.tau,SECTION_COUNT,endpoint=False)
SUPPORT=np.stack((np.cos(RING_KNIVES),np.sin(RING_KNIVES)),axis=1)
# Vertex at the intersection of adjoining fixed-direction supporting lines.
PAIR=np.stack((SUPPORT,np.roll(SUPPORT,-1,axis=0)),axis=1)
INVERSE=np.linalg.inv(PAIR)
WAIST_CUT=2.265
COAT_LEVELS=np.array([0.,.16,.34,.55,.73,.89,1.])
CLEARANCE=.046
CROWN=['#2c231e','#503c30','#6a503c']
FUR=['#514031','#8b6e50','#b99a74']
SLEEVE_N=12

def crop_top(V,N,height=WAIST_CUT):
 # Clip each original weighted polygon in bind space, retaining its normals.
 out=[];norms=[]
 for tri,ns in zip(V.reshape(-1,3,3),N.reshape(-1,3,3)):
  pn=[]
  for i,(p,n) in enumerate(zip(tri,ns)):
   q,m=tri[i-1],ns[i-1]
   inp,inq=p[2]>=height,q[2]>=height
   if inp!=inq:
    u=(height-q[2])/(p[2]-q[2])
    pn.append((mix(q,p,u),mix(m,n,u)))
   if inp:pn.append((p,n))
  for i in range(1,len(pn)-1):
   for pt,normal in (pn[0],pn[i],pn[i+1]):
    out.append(pt);norms.append(normal)
 return np.array(out).reshape(-1,3),np.array(norms).reshape(-1,3)

def hat_model(n,V):
 q=V.copy()
 if n.startswith(('ushanka.crown','ushanka.fold.light')):
  h=np.clip((q[:,2]-4.42)/.36,0,1)
  q[:,2]-=.055*h
  q[:,1]*=.952
  q[:,0]-=.030*h
 elif n in ('ushanka.fur-band','ushanka.band.light'):
  # Thick front lap, leaving the facial planes in their original place.
  front=ease_array((q[:,0]-.04)/.24)
  q[:,0]+=.062*front
  q[:,2]+=(q[:,2]-4.436)*.39-.027*front
  q[:,1]*=1.035
 elif n.startswith(('ushanka.flap','ushanka.wear')):
  q[:,1]*=1.095
  q[:,2]-=.017*ease_array((4.46-q[:,2])/.42)
  q[:,0]+=.019
 return q

def ease_array(x):
 x=np.clip(x,0,1)
 return x*x*(3.-2.*x)

def clipped_slice(vtx,low,high):
 vtx=np.asarray(vtx).reshape(-1,3)
 pool=[vtx[(vtx[:,2]>=low)&(vtx[:,2]<=high)]]
 a=vtx.reshape(-1,3,3)
 b=np.roll(a,1,axis=1)
 for z in (low,high):
  keep=(a[:,:,2]>=z)!=(b[:,:,2]>=z)
  p,q=a[keep],b[keep]
  if len(p):
   s=(z-p[:,2])/(q[:,2]-p[:,2])
   pool.append(p+(q-p)*s[:,None])
 return np.concatenate(pool)

def polygon_tri(near,far,k):
 l=(k+1)%len(near)
 return [near[k],far[k],near[l],near[l],far[k],far[l]]

def normals_tris(V):
 a,b,c=V.reshape(-1,3,3).transpose(1,0,2)
 n=np.cross(b-a,c-a)
 size=np.linalg.norm(n,axis=1)
 n=n/np.maximum(size[:,None],1e-9)
 return np.repeat(n,3,axis=0)

def make_skirt(j,parts,tag=4):
 p=j['pelvis'];F=hips(j)
 leg={}
 for side in ('L','R'):
  leg[side]=np.concatenate([(P-p)@F for n,P,*_ in parts if n in ('thigh.'+side,'shin.'+side,'boot-cuff.'+side)])
 depth0=float(np.clip((2.21-p[2])/1.16,0,1))
 gain=ease(depth0)
 local_knees=[(j['knee.'+s]-p)@F for s in ('L','R')]
 front=max(k[0] for k in local_knees)
 lower=.94-.50*gain-.076*max(0,front-.42)
 lower=max(.385,lower)
 levels=.263-(.263+lower)*COAT_LEVELS
 side_limits=[]
 # Each plane ring encloses both adjacent slabs, so the panels stay in front of the posed thighs.
 for lo,hi in zip(levels[1:],levels[:-1]):
  bank=[]
  for s in ('L','R'):
   section=clipped_slice(leg[s],lo,hi)
   if len(section):bank.append((section[:,:2]@SUPPORT.T).max(0)+CLEARANCE)
   else:bank.append(np.full(SECTION_COUNT,-10.))
  side_limits.append(bank)
 rings=[]
 for i,(z,u) in enumerate(zip(levels,COAT_LEVELS)):
  base=-.010*SUPPORT[:,0]+np.hypot((.407+.073*u)*SUPPORT[:,0],(.565+.048*u)*SUPPORT[:,1])
  hints=[base]
  for k in (i-1,i):
   if 0<=k<len(side_limits):hints.extend(side_limits[k])
  support=np.max(hints,axis=0)
  xy=np.einsum('nij,nj->ni',INVERSE,np.column_stack((support,np.roll(support,-1))))
  rings.append(np.column_stack((xy,np.full(SECTION_COUNT,z)))@F.T+p)
 groups={}
 for i,(top,bottom) in enumerate(zip(rings,rings[1:])):
  for k in range(SECTION_COUNT):
   # A slightly darker channel defines the front seam and the lower edge.
   col=7 if (k in (1,18) and i>=1) or (i==len(rings)-2 and k not in (0,19)) else 0
   groups.setdefault(col,[]).extend(polygon_tri(top,bottom,k))
 return [('skirt.shell.'+str(col),A,normals_tris(A),col,tag) for col,points in groups.items() for A in (np.array(points),)]

def sleeve_centers(j,s):
 sh,el,wr=[j[x+'.'+s] for x in ('shoulder','elbow','wrist')]
 u=unit(el-sh);v0=unit(wr-el)
 # A short quadratic bend preserves the elbow volume and avoids an external elbow part.
 p=el-.149*u;q=el+.147*v0
 centers=[sh-.017*u,sh+.145*u,sh+.410*u,p]
 centers.extend(((1-t)**2*p+2*(1-t)*t*el+t*t*q) for t in (.25,.50,.75))
 centers.extend([q,el+.385*v0,el+.582*v0,wr+.012*v0])
 return np.array(centers),u,v0
SLEEVE_RADII=np.array([.176,.194,.177,.163,.159,.158,.153,.146,.139,.126,.121])
ARM_RADII=np.array([.107,.128,.117,.108,.106,.104,.101,.096,.087,.064,.054])
def sleeve(j,side,proxy=False):
 rows,upper,lower=sleeve_centers(j,side)
 radii=ARM_RADII if proxy else SLEEVE_RADII
 d=unit(j['shoulder.L']-j['shoulder.R'])
 tors=unit(j['neck']-j['chest'])
 bend=lower-upper
 mag=norm(bend)
 ring=[]
 for i,(pt,r) in enumerate(zip(rows,radii)):
  if i==0:t=upper
  elif i==len(rows)-1:t=lower
  else:t=unit(rows[i+1]-rows[i-1])
  X=d-t*(d@t)
  if norm(X)<.17:X=tors-t*(tors@t)
  X=unit(X);Y=np.cross(t,X)
  ring.append(np.array([pt+r*(X*math.cos(k)+Y*math.sin(k)) for k in np.linspace(0,math.tau,SLEEVE_N,endpoint=False)]))
 faces={}
 for i,(aa,bb) in enumerate(zip(ring,ring[1:])):
  for k in range(SLEEVE_N):
   normal=unit((aa[k]+bb[k]-rows[i]-rows[i+1])*.5)
   fold=not proxy and mag>.87 and 3<=i<=6 and normal@unit(bend)>.58
   tint=7 if fold and i in (4,6) else 0
   faces.setdefault(tint,[]).extend(polygon_tri(aa,bb,k))
 return [(('arm.proxy.' if proxy else 'sleeve.')+side+'.'+str(col),A,normals_tris(A),col,1)
         for col,points in faces.items() for A in (np.array(points).reshape(-1,3,3)[:,[0,2,1],:].reshape(-1,3),)]

# Tapered seamless fabric around both segments, with the inner crease in the shading.
TETS=np.array([[0,1,3,7],[0,3,2,7],[0,2,6,7],[0,6,4,7],[0,4,5,7],[0,5,1,7]])
CUBE=np.array([[0,0,0],[1,0,0],[0,1,0],[1,1,0],[0,0,1],[1,0,1],[0,1,1],[1,1,1]])
STEP=.046
def field_seg(P,u,length,rad0,rad1,origin):
 y=P-origin
 ix=np.clip(y@u/length,0,1)
 return np.linalg.norm(y-ix[...,None]*length*u,axis=-1)-mix(rad0,rad1,ix)
def sleeve_field(j,side):
 sh,el,wr=[j[k+'.'+side] for k in ('shoulder','elbow','wrist')]
 u=unit(el-sh);w=unit(wr-el)
 def f(P,clip=True):
  a=field_seg(P,u,B['upper_arm'],.176,.152,sh)
  b=field_seg(P,w,B['forearm'],.152,.103,el)
  s=np.maximum(0.,1.-np.abs(a-b)/.071)
  full=np.minimum(a,b)-.01775*s*s
  return np.maximum(full,(P-wr)@w+.032) if clip else full
 return sh,el,wr,u,w,f
def isosurface(lo,hi,f,step=STEP):
 lo=np.floor(lo/step)*step
 hi=np.ceil(hi/step)*step
 shape=(np.rint((hi-lo)/step).astype(int)+1)
 xyz=np.indices(shape,dtype=float).transpose(1,2,3,0)*step+lo
 val=f(xyz)
 w=np.stack([val[ox:shape[0]-1+ox,oy:shape[1]-1+oy,oz:shape[2]-1+oz] for ox,oy,oz in CUBE],axis=-1)
 ids=np.argwhere((w.min(-1)<=0)&(w.max(-1)>0))
 p=lo+ids[:,None,:]*step+CUBE[None,:,:]*step
 h=w[tuple(ids.T)]
 triangles=[]
 for tet in TETS:
  U=p[:,tet];V=h[:,tet]
  patterns=(V<=0)@np.array([1,2,4,8])
  for code in range(1,15):
   use=patterns==code
   if not use.any():continue
   ins=[i for i in range(4) if code>>i&1]
   out=[i for i in range(4) if code>>i&1==0]
   A=U[use];B=V[use]
   def edge(i,j):
    u=B[:,i]/(B[:,i]-B[:,j])
    return A[:,i]+u[:,None]*(A[:,j]-A[:,i])
   if len(ins)==2:
    a,b,c,d=(edge(i,j) for i in ins for j in out)
    triangles.extend([np.stack((a,b,d),axis=1),np.stack((a,d,c),axis=1)])
   else:
    samples=[edge(i,j) for i in ins for j in out]
    triangles.append(np.stack(samples,axis=1))
 return np.concatenate(triangles)
def sleeve_fabric(j,s):
 sh,el,wr,u,w,f=sleeve_field(j,s)
 p=np.array([sh,el,wr])
 surface=lambda Q:f(Q,False)
 triangles=isosurface(p.min(0)-.22,p.max(0)+.22,surface)
 # Trim the tube at the cuff with an open cut, keeping the cloth surface only.
 cut=.035
 sl=(wr-triangles)@w>=cut
 full=triangles[sl.all(1)]
 edge=triangles[sl.any(1)&~sl.all(1)]
 if len(edge):
  z=-w
  X=unit(np.cross(z,v(0,1,0) if abs(z[1])<.8 else v(1,0,0)))
  M=np.column_stack((X,np.cross(z,X),z))
  q=(edge.reshape(-1,3)-wr)@M
  cut_vertices,_=crop_top(q,np.zeros_like(q),cut)
  full=np.concatenate((full,(cut_vertices@M.T+wr).reshape(-1,3,3)))
 triangles=full
 flat=triangles.mean(1)
 V=triangles.reshape(-1,3)
 de=np.eye(3)*.001
 N=np.stack([surface(V+d)-surface(V-d) for d in de],axis=1)
 N=N/np.maximum(np.linalg.norm(N,axis=1,keepdims=True),1e-9)
 diff=w-u
 bend=norm(diff)
 if bend>.9:
  inner=unit(diff)
  dirt=((flat-el)@inner>.07)&(np.linalg.norm(flat-el,axis=1)<.18)&((flat-el)@w<.05)
 else:dirt=np.zeros(len(flat),dtype=bool)
 results=[]
 for k,col in [(~dirt,0),(dirt,7)]:
  if k.any():results.append(('sleeve.'+s+'.'+str(col),triangles[k].reshape(-1,3),N.reshape(-1,3,3)[k].reshape(-1,3),col,1))
 return results

def cuff(j,s):
 wr,el=j['wrist.'+s],j['elbow.'+s]
 axis=unit(wr-el)
 X=np.cross(v(0,0,1),axis)
 if norm(X)<.1:X=np.cross(v(0,1,0),axis)
 X=unit(X);Y=np.cross(axis,X)
 rings=[]
 for l,r in [(-.13,.127),(-.055,.111),(.006,.095)]:
  rings.append(np.array([wr+l*axis+r*(math.cos(a)*X+math.sin(a)*Y) for a in np.linspace(0,math.tau,12,endpoint=False)]))
 V=np.array([p for a,b in zip(rings,rings[1:]) for k in range(12) for p in polygon_tri(a,b,k)]).reshape(-1,3,3)[:,[0,2,1],:].reshape(-1,3)
 return ('cuff.'+s,V,normals_tris(V),2,3)
