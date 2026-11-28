"""Shared character meshes for sleeves and hands."""
import math

import numpy as np

from dress import geometry
from motion import norm, unit, v
from skin import cuff, normals_tris, sleeve_fabric

INNER_SLEEVE_COMPRESSION = .77
INNER_SLEEVE_BLEND_START = .20
T = np.linspace(0, math.tau, 12, endpoint=False)
W = np.cos(T)
H = np.sin(T)


def tapered(points, widths, direction):
    rings=[]
    normals=[]
    for i,(p,(w,h)) in enumerate(zip(points,widths)):
        axis = unit(points[min(i+1,len(points)-1)]-points[max(i-1,0)])
        outward = unit(direction-axis*(direction@axis))
        up = np.cross(axis,outward)
        rings.append(p+(W[:,None]*outward)*w+(H[:,None]*up)*h)
        normals.append((W[:,None]*outward)/w + (H[:,None]*up)/h)
    a,b,c,d=(rings[:-1],rings[1:],np.roll(rings[:-1],-1,axis=1),np.roll(rings[1:],-1,axis=1))
    f,g,h,k=(normals[:-1],normals[1:],np.roll(normals[:-1],-1,axis=1),np.roll(normals[1:],-1,axis=1))
    vertices=np.stack((a,c,b,b,c,d),axis=2).reshape(-1,3)
    n=np.stack((f,h,g,g,h,k),axis=2).reshape(-1,3)
    n/=np.linalg.norm(n,axis=1,keepdims=True)
    return vertices,n

def finger_shell(grip,M,closure=1.):
    across = [-.119,-.088,-.055,-.029,.000,.027,.053,.080,.104]
    angles = np.deg2rad([156,127,97,65,34,3,-27,-56,-83])
    if closure < 1.:
        angles[1:] += (1.-closure) * np.deg2rad([2,4,8,13,20,26,34,40])
    def point(x,a,r):
        return (np.array([x,r*np.cos(a),r*np.sin(a)]) @ M.T) + grip
    def quad(pts,n):
        return ([pts[i] for i in (0,1,2,2,1,3)],[n[i] for i in (0,1,2,2,1,3)])
    Vs,Ns=[],[]
    outer,inner=[],[]
    for i,x in enumerate(across):
        groove = .006 if i in (2,4,6) else 0
        r=.090 - groove- (.010 if i==8 else 0)
        outer.append([point(x,a,r-(.013 if k==len(angles)-1 else .004 if k in (0,len(angles)-2) else 0)) for k,a in enumerate(angles)])
        inner.append([point(x,a,.041) for a in angles])
    out,inside=np.array(outer),np.array(inner)
    normals=(np.column_stack((np.zeros_like(angles),np.cos(angles),np.sin(angles))) @ M.T)
    for i in range(len(across)-1):
        for k in range(len(angles)-1):
            for surface,n in ((out,normals),(inside,-normals)):
                a,b=surface[i,k:k+2];c,d=surface[i+1,k:k+2]
                if surface is out:
                    delta_r=(np.linalg.norm(c-a-(across[i+1]-across[i])*M[:,0]) * np.sign(
                        (c-grip)@n[k]-(a-grip)@n[k]))
                    slope=delta_r/(across[i+1]-across[i])
                    normal0=unit(n[k]-.68*slope*M[:,0])
                    normal1=unit(n[k+1]-.68*slope*M[:,0])
                    V,N=quad([a,b,c,d],[normal0,normal1,normal0,normal1])
                else:
                    V,N=quad([a,b,c,d],[n[k],n[k+1],n[k],n[k+1]])
                Vs.extend(V);Ns.extend(N)
        for k in (0,len(angles)-1):
            n=M@v(0,math.sin(angles[k]),-math.cos(angles[k]))*(1 if k==0 else -1)
            V,N=quad([out[i,k],inside[i,k],out[i+1,k],inside[i+1,k]],[n]*4)
            Vs.extend(V);Ns.extend(N)
    for i,sign in ((0,-1),(-1,1)):
        for k in range(len(angles)-1):
            V,N=quad([out[i,k],out[i,k+1],inside[i,k],inside[i,k+1]],[M[:,0]*sign]*4)
            Vs.extend(V);Ns.extend(N)
    return np.array(Vs),np.array(Ns)

def make_hand(pose,M,fore,closure=1.):
    # Thumb toward the head, back of the right hand toward the outside.
    # Rotate the hand frame by half a turn instead of mirroring the geometry.
    M=M @ np.diag((-1.,1.,-1.))
    q,d,n=M.T
    grip=pose['j']['grip.R']
    w=pose['j']['wrist.R']
    def loc(x,y,z):
        return grip + M @ v(x,y,z)
    hand = unit(grip-w)
    wrist= tapered([w-.084*fore,w-.033*fore,w+.028*hand,w+.071*hand],
                    [(.059,.049),(.054,.044),(.051,.041),(.057,.043)],q)
    palm= tapered([w+.045*hand,w+.091*hand,loc(-.049,-.108,.010),
                  loc(-.027,-.073,.023),loc(-.009,-.056,.033)],
                  [(.055,.041),(.079,.047),(.102,.038),(.112,.036),(.105,.028)],q)
    fingers=finger_shell(grip,M,closure)
    thumb=tapered([loc(-.096,-.120,-.018),loc(-.131,-.093,-.049),
                  loc(-.123,-.055,-.077),loc(-.084,-.019,-.071),loc(-.058,.012,-.047)],
                  [(.032,.030),(.038,.033),(.035,.031),(.029,.028),(.022,.021)],q)
    return [('hand.R.'+name,V,N,mat,tag) for name,(V,N),mat,tag in
            [('wrist',wrist,5,8),('palm',palm,5,7),('fingers',fingers,21,9),('thumb',thumb,5,10)]]

def close_sleeve(j,inward_side=None):
    elbow=j['elbow.R']
    wrist=j['wrist.R']
    axis=unit(wrist-elbow)
    parts=[]
    for name,vertices,normals,material,tag in sleeve_fabric(j,'R'):
        along=(vertices-elbow)@axis
        if inward_side is None:
            center_y=elbow[1]+along*axis[1]
            inward=np.maximum(vertices[:,1]-center_y,0.)
        else:
            sleeve_center=elbow+along[:,None]*axis
            inward=np.maximum((vertices-sleeve_center)@inward_side,0.)
        # Flatten the inner surface against the coat. Keep the cuff and
        # the outside silhouette at their original thickness.
        fit=np.clip((along+INNER_SLEEVE_BLEND_START)/.14,0,1)*np.clip((norm(wrist-elbow)-along-.04)/.14,0,1)
        y_shift=INNER_SLEEVE_COMPRESSION*inward*fit
        points=vertices.copy()
        if inward_side is None:
            points[:,1]-=y_shift
        else:
            points-=y_shift[:,None]*inward_side
        changed=np.repeat((y_shift.reshape(-1,3)>0).any(1),3)
        fitted=normals.copy()
        smooth=normals_tris(points[changed])
        facing=np.where((smooth*normals[changed]).sum(axis=1)<0,-1.,1.)
        fitted[changed]=smooth*facing[:,None]
        parts.append((name,points,fitted,material,tag))
    return parts


def posed_geometry(new,M,fore,body_pose,closure=1.,inward_side=None):
    before=[p for p in geometry(body_pose) if not p[0].startswith(('hand.R','palm.R','hatchet.','sleeve.R.','cuff.R'))]
    j=new['j']
    garment_j=j | {'wrist.R': j['wrist.R']-.072*fore}
    before.extend(close_sleeve(garment_j,inward_side))
    before.append(cuff(garment_j,'R'))
    before.extend(make_hand(new,M,fore,closure))
    wl,el=j['wrist.L'],j['elbow.L']
    left_axis=unit(j['hand.L']-wl)
    left_fore=unit(wl-el)
    side=v(0,1,0)
    wrist,N=tapered([wl-.028*left_fore,wl+.030*left_axis,wl+.105*left_axis,wl+.143*left_axis],
                    [(.062,.049),(.055,.044),(.053,.043),(.061,.045)],side)
    before.append(('hand.L.wrist',wrist,N,5,11))
    return before
