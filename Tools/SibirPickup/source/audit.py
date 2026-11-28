import numpy as np

def crosses(tri, edges):
 T=tri
 if not len(T):return np.zeros(0,dtype=bool)
 U=T[:,1]-T[:,0];V=T[:,2]-T[:,0]
 starts=edges;ds=np.roll(edges,-1,axis=1)-starts
 h=np.cross(ds,V[:,None,:])
 de=np.sum(h*U[:,None,:],axis=2)
 w=starts-T[:,None,0]
 z=np.cross(w,U[:,None,:])
 with np.errstate(divide='ignore',invalid='ignore'):
  a=np.sum(w*h,axis=2)/de
  b=np.sum(ds*z,axis=2)/de
  t=np.sum(z*V[:,None,:],axis=2)/de
 return ((abs(de)>1e-10)&(a>=-1e-7)&(b>=-1e-7)&(a+b<=1.+1e-7)&(t>1e-7)&(t<1.-1e-7)).any(1)
def count(Q,R):
 A=np.asarray(Q).reshape(-1,3,3);B=np.asarray(R).reshape(-1,3,3)
 if not len(A) or not len(B):return 0
 Alo,Ahi=A.min(1),A.max(1);Blo,Bhi=B.min(1),B.max(1)
 a_use=((Alo<=Bhi.max(0))&(Ahi>=Blo.min(0))).all(1)
 b_use=((Blo<=Ahi.max(0))&(Bhi>=Alo.min(0))).all(1)
 A,Alo,Ahi=A[a_use],Alo[a_use],Ahi[a_use]
 B,Blo,Bhi=B[b_use],Blo[b_use],Bhi[b_use]
 if not len(A) or not len(B):return 0
 ids=np.ones((len(A),len(B)),dtype=bool)
 for k in range(3):
  ids &= (Alo[:,k,None]<=Bhi[None,:,k])&(Blo[None,:,k]<=Ahi[:,k,None])
 i,j=np.where(ids)
 a,b=A[i],B[j]
 return int((crosses(a,b)|crosses(b,a)).sum())
