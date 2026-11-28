import numpy as np
from PIL import Image
from dress import PXY, SIZE, light
from art import colors, styled
F=4
H=SIZE*F

def weld(V,N):
    tri=V.reshape(-1,3,3)
    a,b,c=tri.transpose(1,0,2)
    face=np.cross(b-a,c-a)
    _,idx=np.unique(np.round(V,5),axis=0,return_inverse=True)
    accum=np.zeros((idx.max()+1,3))
    np.add.at(accum,idx,np.repeat(face,3,axis=0))
    avg=accum[idx]
    avg/=np.maximum(np.linalg.norm(avg,axis=1,keepdims=True),1e-12)
    return np.where((np.sum(avg*N,axis=1)>.35)[:,None],avg,N)

def buffers(pose, parts, camera, pivot=PXY, detailed=True):
    zr=np.full((H,H),-np.inf)
    color=np.full((H,H),-1,dtype=np.int8)
    tag=np.zeros((H,H),dtype=np.uint8)
    for name,mesh,N,mat,label in parts:
        if not name.startswith(('hatchet.','sole','buckle','hand.R.','hand.L.')):
            N=weld(mesh,N)
        P=(mesh-pose['j']['root'])@camera.T
        P[:,:2]=F*(P[:,:2]*26+pivot)
        tri=P.reshape(-1,3,3)
        lo=np.clip(np.floor(tri[:,:,:2].min(1)).astype(int),0,H)
        hi=np.clip(np.ceil(tri[:,:,:2].max(1)).astype(int),0,H)
        width,height=(hi-lo).T
        lens=width*height
        owner=np.repeat(np.arange(len(tri)),lens)
        offs=np.arange(len(owner))-np.repeat(np.cumsum(lens)-lens,lens)
        y=lo[owner,1]+offs//width[owner];x=lo[owner,0]+offs%width[owner]
        A=tri[owner,0]
        U=tri[owner,1]-A; V=tri[owner,2]-A
        det=U[:,0]*V[:,1]-U[:,1]*V[:,0]
        dx=x+.5-A[:,0];dy=y+.5-A[:,1]
        with np.errstate(divide='ignore',invalid='ignore'):
            u=(dx*V[:,1]-dy*V[:,0])/det
            w=(U[:,0]*dy-U[:,1]*dx)/det
            inside=(abs(det)>=1e-9)&(u>=-1e-8)&(w>=-1e-8)&(u+w<=1+1e-8)
        t=A[inside,2]+u[inside]*U[inside,2]+w[inside]*V[inside,2]
        x,y,owner,u,w=x[inside],y[inside],owner[inside],u[inside],w[inside]
        number=y*H+x
        order=np.lexsort((owner,-t,number))
        if len(order)==0:
            continue
        front=order[np.r_[True,np.diff(number[order])!=0]]
        keep=front[t[front]>zr[y[front],x[front]]]
        x,y,t,u,w,owner=x[keep],y[keep],t[keep],u[keep],w[keep],owner[keep]
        nn=N.reshape(-1,3,3)[owner]
        n=nn[:,0]*(1-u[:,None]-w[:,None])+nn[:,1]*u[:,None]+nn[:,2]*w[:,None]
        lit=(n@light)/np.maximum(np.linalg.norm(n,axis=1),1e-12)
        shade=(lit>-.04).astype(int)+(lit>.47).astype(int)
        if name=='hatchet.cutting-edge':
            shade=np.maximum(shade,1)
        zr[y,x]=t
        material=np.full(len(shade),mat,dtype=np.int8)
        if detailed and len(shade):
            tri_world=mesh.reshape(-1,3,3)[owner]
            hits=tri_world[:,0]*(1-u[:,None]-w[:,None])+tri_world[:,1]*u[:,None]+tri_world[:,2]*w[:,None]
            material,shade=styled(name,hits,n,material,shade,pose['j'],mesh.mean(axis=0))
        color[y,x]=3*material+shade
        tag[y,x]=label
    return color,tag

def image(pose,parts,camera,pivot=PXY,detailed=True):
    col,tag=buffers(pose,parts,camera,pivot,detailed)
    N=F*F
    def fold(a):
        return a.reshape(SIZE,F,SIZE,F).transpose(0,2,1,3).reshape(SIZE*SIZE,N)
    c=fold(col);t=fold(tag)
    occupied=c>=0
    fine=(np.isin(t,(2,5,6,7,8,9,10,11))&occupied).sum(1)>=4
    opaque=occupied.sum(1)>=np.where(fine,4,8)
    counts=np.zeros((SIZE*SIZE,len(colors)*3),dtype=np.uint8)
    yy,xx=np.nonzero(occupied)
    np.add.at(counts,(yy,c[yy,xx]),1)
    p=counts.argmax(1).reshape(SIZE,SIZE)
    op=opaque.reshape(SIZE,SIZE)
    tags=np.zeros((SIZE*SIZE,12),dtype=np.uint8)
    np.add.at(tags,(yy,t[yy,xx]),1)
    ids=tags.argmax(1).reshape(SIZE,SIZE)
    # Suppress a stray isolated shade only when two adjacent samples on that same material agree.
    pp=np.pad(p,1,constant_values=-10)
    opad=np.pad(op,1,constant_values=False)
    neigh=np.stack((pp[1:-1,:-2],pp[1:-1,2:],pp[:-2,1:-1],pp[2:,1:-1]))
    on=np.stack((opad[1:-1,:-2],opad[1:-1,2:],opad[:-2,1:-1],opad[2:,1:-1]))
    alone=~((neigh==p)&on).any(0)
    for n in neigh:
        majority=((neigh==n)&on).sum(0)
        fix=op & alone & (p//3==n//3) & (majority>=2) & ~np.isin(ids,(5,6,7,8,9,10,11))
        p[fix]=n[fix]
    rgba=np.zeros((SIZE,SIZE,4),dtype=np.uint8)
    rgba[:,:,:3][op]=colors.reshape(-1,3)[p[op]]
    rgba[:,:,3][op]=255
    return Image.fromarray(rgba),np.where(op,ids,0)
