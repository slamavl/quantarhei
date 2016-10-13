# -*- coding: utf-8 -*-

import numpy

from ...core.managers import BasisManaged
from ...utils.types import BasisManagedComplexArray

class RelaxationTensor(BasisManaged):

    data = BasisManagedComplexArray("data")
    
    def __init__(self):
        
        # Set the currently used basis
        cb = self.manager.get_current_basis()
        self.set_current_basis(cb)
        # unless it is the basis outside any context
        if cb != 0:
            self.manager.register_with_basis(cb,self)
            
        self._data_initialized = False
        self.name = ""
            
            
    def secularize(self):
        """Secularizes the relaxation tensor


        """
        if self.as_operators:
            raise Exception("Cannot be secularized in an opeator form")
            
        else:
            N = self.data.shape[0]
            for ii in range(N):
                for jj in range(N):
                    for kk in range(N):
                        for ll in range(N):
                            if not (((ii == jj) and (kk == ll)) 
                                or ((ii == kk) and (jj == ll))) :
                                    self.data[ii,jj,kk,ll] = 0
                                        
                                        
    def transform(self, SS, inv=None):
        """Transformation of the tensor by a given matrix
        
        
        This function transforms the Operator into a different basis, using
        a given transformation matrix.
        
        Parameters
        ----------
         
        SS : matrix, numpy.ndarray
            transformation matrix
            
        inv : matrix, numpy.ndarray
            inverse of the transformation matrix
            
        """        
        

        if not self._data_initialized:
            return
        print("%%%%%%%%%%% TRANSFORMING %%%%%%%%%%")
        
        if (self.manager.warn_about_basis_change):
                print("\nQr >>> Relaxation tensor '%s' changes basis" %self.name)
           
        if inv is None:
            S1 = numpy.linalg.inv(SS)
        else:
            S1 = inv
        dim = SS.shape[0]
        
        for c in range(dim):
            for d in range(dim):
                self._data[:,:,c,d] = \
                numpy.dot(S1,numpy.dot(self._data[:,:,c,d],SS))
                
        for a in range(dim):
            for b in range(dim):
                self._data[a,b,:,:] = \
                numpy.dot(S1,numpy.dot(self._data[a,b,:,:],SS))
        
#        RR = numpy.zeros((dim,dim,dim,dim), dtype=numpy.complex128)
#        rr = 0.0 + 0.0j
#        for ag in range(dim):
#            for bg in range(dim):
#                for cg in range(dim):
#                    for dg in range(dim):
#                        rr = 0.0
#                        for a in range(dim):
#                            for b in range(dim):
#                                for c in range(dim):
#                                    for d in range(dim):
#                                        rr += S1[ag,a]*SS[b,bg]*self._data[a,b,c,d]*SS[c,cg]*S1[dg,d]
#                        RR[ag,bg,cg,dg] = rr
#                        
#        self._data = RR
