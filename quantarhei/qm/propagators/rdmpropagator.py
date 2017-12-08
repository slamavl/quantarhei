# -*- coding: utf-8 -*-
"""
*******************************************************************************

    REDUCED DENSITY MATRIX PROPAGATOR

*******************************************************************************

Propagator of the Reduced density matrix dynamics

Created on Mon Apr 13 18:27:07 2015

author: Tomas Mancal, Charles University

"""

import numpy

#import scipy.integrate
import numpy.linalg

#import cu.oqs.cython.propagators as prop

from ..hilbertspace.hamiltonian import Hamiltonian
from ..hilbertspace.operators import Operator
from ...core.time import TimeAxis
from ...core.time import TimeDependent
from ...core.saveable import Saveable
from ..liouvillespace.redfieldtensor import RelaxationTensor
from ..hilbertspace.operators import ReducedDensityMatrix, DensityMatrix
from .dmevolution import ReducedDensityMatrixEvolution
from ...core.matrixdata import MatrixData

import quantarhei as qr


class ReducedDensityMatrixPropagator(MatrixData, Saveable): 
    """
    
    Reduced Density Matrix Propagator calculates the evolution of the
    reduced density matrix based on the Hamiltonian and optionally
    a relaxation tensor. Relaxation tensor may be constant or time
    dependent. 
    
    """
    
    def __init__(self, timeaxis=None, Ham=None, RTensor="",
                 Efield="", Trdip=""):
        """
        
        Creates a Reduced Density Matrix propagator which can propagate
        a given initial density matrix with the given Hamiltonian and 
        relaxation tensor.Time axis of the propagation is specied by 
        the second argument.
        
        The constructor accepts only numpy.ndarray object, so the
        following code will fail, becuase it submits normal Python arrays.         
        
        >>> pr = RDMPropagator([[0.0, 0.0],[0.0, 1.0]],[0,1,2,3,4,5])
        Traceback (most recent call last):
            ...
        Exception
        
        The correct way to construct the propagator is the following:

        >>> h = numpy.array([[0.0, 0.0],[0.0,1.0]])
        >>> HH = Hamiltonian(data=h)
        >>> times = TimeAxis(0,1000,1)
        >>> pr = RDMPropagator(HH,times)
        
        """
        self.has_Trdip = False
        self.has_Efield = False
        
        if not ((timeaxis is None) and (Ham is None)):
            
            if isinstance(Ham,Hamiltonian):
                self.Hamiltonian = Ham
            else:
                raise Exception
            
            if isinstance(timeaxis,TimeAxis):
                self.TimeAxis = timeaxis
            else:
                raise Exception
            
            if isinstance(RTensor,RelaxationTensor):
                self.RelaxationTensor = RTensor
                self.has_relaxation = True
            elif RTensor == "":
                self.has_relaxation = False
            else:
                raise Exception
    
            if Trdip != "":            
                if isinstance(Trdip,Operator):
                    self.Trdip = Trdip
                    self.has_Trdip = True
                else:
                    raise Exception
    
            if Efield != "":
                if isinstance(Efield,numpy.ndarray):
                    self.Efield = Efield
                    self.has_Efield = True 
            
            self.Odt = self.TimeAxis.data[1]-self.TimeAxis.data[0]
            self.dt = self.Odt
            self.Nref = 1
            
            self.Nt = self.TimeAxis.data.shape[0]
            
            N = self.Hamiltonian.data.shape[0]
            self.N = N
            self.data = numpy.zeros((self.Nt,N,N),dtype=numpy.complex64)
            self.propagation_name = ""
        
            self.verbose = False

        
    def setDtRefinement(self, Nref):
        """
        The TimeAxis object specifies at what times the propagation
        should be stored. We can tell the propagator to use finer
        time step for the calculation by setting the refinement. The
        refinement is an integer by which the TimeAxis time step should
        be devided to get the finer time step. In the code below, we
        have dt = 10 in the TimeAxis, but we want to calculate with
        dt = 1
        
        >>> HH = numpy.array([[0.0, 0.0],[0.0,1.0]])
        >>> times = numpy.linspace(0,1000,10)
        >>> pr = RDMPropagator(HH,times)
        >>> pr.setDtRefinement(10)
        
        """
        self.Nref = Nref
        self.dt = self.Odt/self.Nref
        
        
    def propagate(self, rhoi, method="short-exp", mdata=None, name=""):
        """
        
        >>> T0   = 0
        >>> Tmax = 100
        >>> dt   = 1
        >>> Nref = 30


        >>> initial_dm = [[1.0, 0.0, 0.0],
        ...               [0.0, 0.0, 0.0],
        ...               [0.0, 0.0, 0.0]]

        >>> Hamiltonian = [[0.0, 0.1, 0.0],
        ...                [0.1, 0.0, 0.1],
        ...                [0.0, 0.1, 0.1]]        
        
        >>> HH = numpy.array(Hamiltonian)
        >>> times = numpy.linspace(T0,Tmax,(Tmax-T0)/dt+1)
        
        >>> pr = RDMPropagator(HH,times)
        >>> pr.setDtRefinement(Nref)

        >>> rhoi = numpy.array(initial_dm)  

        >>> pr.propagate(rhoi,method="primitive")
        
        
        """
        self.propagation_name = name
        
        if not (isinstance(rhoi, ReducedDensityMatrix) 
             or isinstance(rhoi, DensityMatrix)):
            raise Exception("First argument has be of"+
            "the ReducedDensityMatrix type")
                    
        if self.has_relaxation:
            
            if isinstance(self.RelaxationTensor, TimeDependent):
                #
                # Time-dependent relaxation tensor
                #

                if (self.has_Efield and self.has_Trdip):
                    
                    #
                    #  Propagation with external field 
                    #
                    if method == "short-exp":
                        return \
                        self.__propagate_short_exp_with_TD_relaxation_field(\
                        rhoi,L=4)
                    elif method == "short-exp-2":
                        return \
                        self.__propagate_short_exp_with_TD_relaxation_field(\
                        rhoi,L=2)
                    elif method == "short-exp-4":
                        return \
                        self.__propagate_short_exp_with_TD_relaxation_field(\
                        rhoi,L=4)
                    elif method == "short-exp-6":
                        return \
                        self.__propagate_short_exp_with_TD_relaxation_field(\
                        rhoi,L=6)            
                    else:
                        raise Exception("Unknown propagation method: "+method)
                    
                    
                else:

                    #
                    #  Without external field
                    #
                    if method == "short-exp":
                        return self.__propagate_short_exp_with_TD_relaxation(\
                        rhoi,L=4)
                    elif method == "short-exp-2":
                        return self.__propagate_short_exp_with_TD_relaxation(\
                        rhoi,L=2)
                    elif method == "short-exp-4":
                        return self.__propagate_short_exp_with_TD_relaxation(\
                        rhoi,L=4)
                    elif method == "short-exp-6":
                        return self.__propagate_short_exp_with_TD_relaxation(\
                        rhoi,L=6)            
                    else:
                        raise Exception("Unknown propagation method: "+method)

                
            else: 
                #
                # Constant relaxation tensor
                #                
                if (self.has_Efield and self.has_Trdip):
                    
                    #
                    # External field
                    #
                    if method == "short-exp":
                        return \
                        self.__propagate_short_exp_with_relaxation_field(
                        rhoi,L=4)
                    elif method == "short-exp-2":
                        return \
                        self.__propagate_short_exp_with_relaxation_field(
                        rhoi,L=2)
                    elif method == "short-exp-4":
                        return \
                        self.__propagate_short_exp_with_relaxation_field(
                        rhoi,L=4)
                    elif method == "short-exp-6":
                        return \
                        self.__propagate_short_exp_with_relaxation_field(
                        rhoi,L=6)            
                    else:
                        raise Exception("Unknown propagation method: "+method)                
                
                else:
            
                    #
                    # No external field
                    #
                    if method == "primitive":
                        return self.__propagate_primitive_with_relaxation(rhoi)
                    elif method == "Runge-Kutta":
                        return self.__propagate_Runge_Kutta(rhoi)
                    elif method == "diagonalization":
                        return self.__propagate_diagonalization(rhoi)
                    elif method == "short-exp":
                        return self.__propagate_short_exp_with_relaxation(
                        rhoi,L=4)
                    elif method == "short-exp-2":
                        return self.__propagate_short_exp_with_relaxation(
                        rhoi,L=2)
                    elif method == "short-exp-4":
                        return self.__propagate_short_exp_with_relaxation(
                        rhoi,L=4)
                    elif method == "short-exp-6":
                        return self.__propagate_short_exp_with_relaxation(
                        rhoi,L=6)            
                    else:
                        raise Exception("Unknown propagation method: "+method)   
            
        else:
            #
            # No relaxation
            #
                
            if method == "primitive":
                return self.__propagate_primitive(rhoi)
            elif method == "Runge-Kutta":
                return self.__propagate_Runge_Kutta(rhoi)
            elif method == "diagonalization":
                return self.__propagate_diagonalization(rhoi)
                    
                    
            elif method == "short-exp":
                return self.__propagate_short_exp(rhoi,L=4)
            elif method == "short-exp-2":
                return self.__propagate_short_exp(rhoi,L=2)
            elif method == "short-exp-4":
                return self.__propagate_short_exp(rhoi,L=4)
            elif method == "short-exp-6":
                return self.__propagate_short_exp(rhoi,L=6)            
            else:
                raise Exception
        
            
        
    def __propagate_primitive(self,rhoi):
        
        pr = ReducedDensityMatrixEvolution(self.TimeAxis,rhoi)


        """
                Primitive intergration
        """            
        rhoPrim = rhoi.data
        HH = self.Hamiltonian.data  
        
        
        indx = 0
        for ii in self.TimeAxis.time: 

            for jj in range(0,self.Nref):   
                
                drho  = -1j*(  numpy.dot(HH,rhoPrim) \
                             - numpy.dot(rhoPrim,HH) )
                             
                rhoPrim = rhoPrim + drho*self.dt

            pr.data[indx,:,:] = rhoPrim            
            
            indx += 1            
            
        return pr

        
    def __propagate_primitive_with_relaxation(self,rhoi):
        
        pr = ReducedDensityMatrixEvolution(self.TimeAxis,rhoi)


        """
                Primitive intergration
        """            
        rhoPrim = rhoi.data
        HH = self.Hamiltonian.data        
        RR = self.RelaxationTensor.data        
        
        indx = 0
        for ii in self.TimeAxis.data: 

            for jj in range(0,self.Nref):   
                
                drho  = -1j*(  numpy.dot(HH,rhoPrim) \
                             - numpy.dot(rhoPrim,HH) ) \
                        + numpy.tensordot(RR,rhoPrim)
                             
                rhoPrim = rhoPrim + drho*self.dt

            pr.data[indx,:,:] = rhoPrim            
            
            indx += 1            
            
        return pr
        
        
    def __propagate_Runge_Kutta(self,rhoi):
        print("Runge-Kutta")
        """
              Runge-Kutta integration
        """
        indx = 0
        for ii in self.timeaxis: 

            self.rho[:,:,indx] = rhoi            
            
            indx += 1  
 
    def __propagate_short_exp(self,rhoi,L=4):
        """
              Short exp integration
        """
        
        pr = ReducedDensityMatrixEvolution(self.TimeAxis,rhoi)
        rho1 = rhoi.data
        rho2 = rhoi.data
        
        HH = self.Hamiltonian.data        
        
        indx = 1
        for ii in self.TimeAxis.time[1:self.Nt]:
            
            pref = (self.dt/ll)            
            
            for jj in range(0,self.Nref):
                
                for ll in range(1,L+1):
                    
                    rho1 = -1j*pref*(numpy.dot(HH,rho1) \
                             - numpy.dot(rho1,HH) )
                             
                    rho2 = rho2 + rho1
                rho1 = rho2    
                
            pr.data[indx,:,:] = rho2                        
            indx += 1             
            
        return pr
 
 
    def __propagate_short_exp_with_relaxation(self, rhoi, L=4):
        """Integration by short exponentional expansion
        
        Integration by expanding exponential to Lth order
              
              
        """
        
        try:
            if self.RelaxationTensor.as_operators:
                return self.__propagate_short_exp_with_rel_operators(rhoi, L=L)
        except:
            raise Exception("Operator propagation failed")
        
        
        pr = ReducedDensityMatrixEvolution(self.TimeAxis, rhoi,
                                           name=self.propagation_name)
        
        rho1 = rhoi.data
        rho2 = rhoi.data
        
        HH = self.Hamiltonian.data        
        RR = self.RelaxationTensor.data
            
        indx = 1
        for ii in range(1, self.Nt): 
            
            for jj in range(0, self.Nref):
                
                for ll in range(1, L+1):
                    
                    rho1 =  - (1j*self.dt/ll)*(numpy.dot(HH,rho1) 
                                             - numpy.dot(rho1,HH)) \
                           + (self.dt/ll)*numpy.tensordot(RR,rho1)
                             
                             
                    rho2 = rho2 + rho1
                rho1 = rho2    
                
            pr.data[indx,:,:] = rho2 
            indx += 1             
            
        return pr  
        
    def __propagate_short_exp_with_rel_operators(self, rhoi, L=4):
        """Integration by short exponentional expansion
        
        Integration by expanding exponential to Lth order. 
              
            
        """

        pr = ReducedDensityMatrixEvolution(self.TimeAxis, rhoi,
                                           name=self.propagation_name)
        
        rho1 = rhoi.data
        rho2 = rhoi.data
        
        HH = self.Hamiltonian.data  
        
        if self.verbose:
            print("PROPAGATION (short exponential with "+
                  "relaxation in operator form): order ", L)
        
        try:
            Km = self.RelaxationTensor.Km # real
            Lm = self.RelaxationTensor.Lm # complex
            Ld = self.RelaxationTensor.Ld # complex - get by transposition
            Kd = numpy.zeros(Km.shape, dtype=numpy.float64)
            Nm = Km.shape[0]
            for m in range(Nm):
                Kd[m, :, :] = numpy.transpose(Km[m, :, :])
        except:
            raise Exception("Tensor is not in operator form")
            
        indx = 1

        # loop over time
        for ii in range(1, self.Nt):
            if self.verbose:
                print(" time step ", ii, "of", self.Nt)
            
            # steps in between saving the results
            for jj in range(0, self.Nref):
                
                # L interations to get short exponential expansion
                for ll in range(1, L+1):
                    
                    rhoY =  - (1j*self.dt/ll)*(numpy.dot(HH,rho1) 
                                             - numpy.dot(rho1,HH))
                    
                    #rhoX = numpy.zeros(rho1.shape, dtype=numpy.complex128)
                    for mm in range(Nm):
                        
                       rhoY += (self.dt/ll)*(
                        numpy.dot(Km[mm,:,:],numpy.dot(rho1, Ld[mm,:,:]))
                       +numpy.dot(Lm[mm,:,:],numpy.dot(rho1, Kd[mm,:,:]))
                       -numpy.dot(numpy.dot(Kd[mm,:,:],Lm[mm,:,:]), rho1)
                       -numpy.dot(rho1, numpy.dot(Ld[mm,:,:],Km[mm,:,:]))
                       )
                             
                    rho1 = rhoY #+ rhoX
                    
                    rho2 = rho2 + rho1
                rho1 = rho2    
                
            pr.data[indx,:,:] = rho2 
            indx += 1             
         
        if self.verbose:    
            print("...DONE")

        return pr


    def _propagate_short_exp_with_rel_operators(self, rhoi, L=4):
        """Integration by short exponentional expansion
        
        Integration by expanding exponential to Lth order. 
              
            
        """

        pr = ReducedDensityMatrixEvolution(self.TimeAxis, rhoi,
                                           name=self.propagation_name)
        
        rho1_r = numpy.real(rhoi.data)
        rho2_r = numpy.real(rhoi.data)
        rho1_i = numpy.imag(rhoi.data)
        rho2_i = numpy.imag(rhoi.data)
        
        HH = self.Hamiltonian.data  
        
        if self.verbose:
            print("PROPAGATION (short exponential with "+
                  "relaxation in operator form): order ", L)
        
        try:
            Km = self.RelaxationTensor.Km # real
            Lm_r = numpy.real(self.RelaxationTensor.Lm) # complex
            Lm_i = numpy.imag(self.RelaxationTensor.Lm)
            #Ld = self.RelaxationTensor.Ld # complex - get by transposition
            Ld_r = numpy.transpose(Lm_r)
            Ld_i = -numpy.transpose(Lm_i)
            Kd = numpy.zeros(Km.shape, dtype=qr.REAL)
            Nm = Km.shape[0]
            for m in range(Nm):
                Kd[m, :, :] = numpy.transpose(Km[m, :, :])
        except:
            raise Exception("Tensor is not in operator form")
            
        indx = 1

        # loop over time
        for ii in range(1, self.Nt):
            if self.verbose:
                print(" time step ", ii, "of", self.Nt)
            
            # steps in between saving the results
            for jj in range(0, self.Nref):
                
                # L interations to get short exponential expansion
                for ll in range(1, L+1):

                    rhoY_r =  (self.dt/ll)*(numpy.dot(HH,rho1_i) 
                                          - numpy.dot(rho1_i,HH))
                    rhoY_i = -(self.dt/ll)*(numpy.dot(HH,rho1_r) 
                                          - numpy.dot(rho1_r,HH))
                    
                    for mm in range(Nm):
                        
                       rhoY_r += (self.dt/ll)*(
                        numpy.dot(Km[mm,:,:], 
                                  numpy.dot(rho1_r, Ld_r[mm,:,:])
                                 -numpy.dot(rho1_i, Ld_i[mm,:,:]))
                       +numpy.dot(numpy.dot(Lm_r[mm,:,:],rho1_r)
                                 -numpy.dot(Lm_i[mm,:,:],rho1_i),
                                  Kd[mm,:,:]))
                       rhoP_r = -numpy.dot(Kd[mm,:,:],
                                           numpy.dot(Lm_r[mm,:,:], rho1_r)
                                          -numpy.dot(Lm_i[mm,:,:], rho1_i))
                       rhoY_r += (self.dt/ll)*(rhoP_r 
                                             + numpy.transpose(rhoP_r))
                       
                       rhoY_i += (self.dt/ll)*(
                        numpy.dot(Km[mm,:,:],
                                  numpy.dot(rho1_r, Ld_i[mm,:,:])
                                 +numpy.dot(rho1_i, Ld_r[mm,:,:]))
                       +numpy.dot(numpy.dot(rho1_r, Lm_i[mm,:,:])
                                 +numpy.dot(rho1_i, Lm_r[mm,:,:]),
                                  Kd[mm,:,:]))
                       rhoP_i = -numpy.dot(Kd[mm,:,:], 
                                           numpy.dot(Lm_r[mm,:,:], rho1_i)
                                          +numpy.dot(Lm_i[mm,:,:], rho1_r))
                       rhoY_i += -(self.dt/ll)*(rhoP_i
                                              + numpy.transpose(rhoP_i))

                             
                    rho1_r = rhoY_r 
                    rho1_i = rhoY_i
                    
                    rho2_r +=  rho1_r
                    rho2_i +=  rho1_i
                    
                rho1_r = rho2_r
                rho1_i = rho2_i
                
            pr.data[indx,:,:] = rho2_r + 1j*rho2_i 
            indx += 1             
         
        if self.verbose:    
            print("...DONE")

        return pr


    def __propagate_short_exp_with_TD_relaxation(self,rhoi,L=4):
        """
              Short exp integration
        """

        try:
            if self.RelaxationTensor.as_operators:
                return self.__propagate_short_exp_with_TDrel_operators(rhoi, L=L)
        except:
            raise Exception("Operator propagation failed")
        
        pr = ReducedDensityMatrixEvolution(self.TimeAxis,rhoi)
        
        rho1 = rhoi.data
        rho2 = rhoi.data
        
        HH = self.Hamiltonian.data        

        if self.RelaxationTensor._has_cutoff_time:
            cutoff_indx = \
            self.TimeAxis.nearest(self.RelaxationTensor.cutoff_time)
        else:
            cutoff_indx = self.TimeAxis.length
            
        indx = 1
        indxR = 1
        for ii in self.TimeAxis.data[1:self.Nt]:

            RR = self.RelaxationTensor.data[indxR,:,:]        
            
            for jj in range(0,self.Nref):
                for ll in range(1,L+1):
                    
                    rho1 =  - (1j*self.dt/ll)*(numpy.dot(HH,rho1) \
                             - numpy.dot(rho1,HH) ) \
                           + (self.dt/ll)*numpy.tensordot(RR,rho1)
                             
                             
                    rho2 = rho2 + rho1
                rho1 = rho2    
                
            pr.data[indx,:,:] = rho2
            
            indx += 1
            if indxR < cutoff_indx-1:                      
                indxR += 1             
            
        return pr     


    def __propagate_short_exp_with_TDrel_operators(self, rhoi, L=4):
        """
              Short exp integration
        """

        pr = ReducedDensityMatrixEvolution(self.TimeAxis, rhoi,
                                           name=self.propagation_name)
        
        rho1 = rhoi.data
        rho2 = rhoi.data
        
        HH = self.Hamiltonian.data  

        if self.RelaxationTensor._has_cutoff_time:
            cutoff_indx = \
            self.TimeAxis.nearest(self.RelaxationTensor.cutoff_time)
        else:
            cutoff_indx = self.TimeAxis.length

        try:
            Km = self.RelaxationTensor.Km
            Kd = numpy.zeros(Km.shape, dtype=numpy.float64)
            Nm = Km.shape[0]
            for m in range(Nm):
                Kd[m, :, :] = numpy.transpose(Km[m, :, :])
        except:
            raise Exception("Tensor is not in operator form")
                        
        indx = 1
        indxR = 1
        for ii in range(1, self.Nt): 

            Lm = self.RelaxationTensor.Lm[indxR,:,:,:]
            Ld = self.RelaxationTensor.Ld[indxR,:,:,:]
       
            for jj in range(0, self.Nref):
                
                for ll in range(1, L+1):
                    
                    rhoY =  - (1j*self.dt/ll)*(numpy.dot(HH,rho1) 
                                             - numpy.dot(rho1,HH))
                    
                    rhoX = numpy.zeros(rho1.shape, dtype=numpy.complex128)
                    for mm in range(Nm):
                        
                       rhoX += (self.dt/ll)*(
                        numpy.dot(Km[mm,:,:],numpy.dot(rho1, Ld[mm,:,:]))
                       +numpy.dot(Lm[mm,:,:],numpy.dot(rho1, Kd[mm,:,:]))
                       -numpy.dot(numpy.dot(Kd[mm,:,:],Lm[mm,:,:]), rho1)
                       -numpy.dot(rho1, numpy.dot(Ld[mm,:,:],Km[mm,:,:]))
                       )
                             
                    rho1 = rhoY + rhoX
                    
                    rho2 = rho2 + rho1
                rho1 = rho2    
                
            pr.data[indx,:,:] = rho2 
            indx += 1             
            if indxR < cutoff_indx-1:                      
                indxR += 1             
            
        return pr
        
        
    def __propagate_diagonalization(self,rhoi):
        pass
        
        
        
    def __propagate_short_exp_with_TD_relaxation_field(self,rhoi,L=4):
        """
              Short exp integration
        """
        
        pr = ReducedDensityMatrixEvolution(self.TimeAxis,rhoi)
        
        rho1 = rhoi.data
        rho2 = rhoi.data
        
        HH = self.Hamiltonian.data    
        MU = self.Trdip.data
        
        indx = 1
        for ii in self.TimeAxis.time[1:self.Nt]:

            RR = self.RelaxationTensor.data[indx,:,:]        
            EE = self.Efield[indx]
            
            for jj in range(0,self.Nref):
                for ll in range(1,L+1):
                    
                    rho1 =  - (1j*self.dt/ll)*(numpy.dot(HH,rho1) \
                             - numpy.dot(rho1,HH) ) \
                           + (self.dt/ll)*numpy.tensordot(RR,rho1) \
                            + (1j*self.dt/ll)*( numpy.dot(MU,rho1) \
                             - numpy.dot(rho1,MU) )*EE
                             
                             
                    rho2 = rho2 + rho1
                rho1 = rho2    
                
            pr.data[indx,:,:] = rho2                        
            indx += 1             
            
        return pr         
        
        
    def __propagate_short_exp_with_relaxation_field(self,rhoi,L=4):
        """
              Short exp integration
        """
        
        pr = ReducedDensityMatrixEvolution(self.TimeAxis,rhoi)
        
        rho1 = rhoi.data
        rho2 = rhoi.data
        
        HH = self.Hamiltonian.data        
        RR = self.RelaxationTensor.data        
        MU = self.Trdip.data
        
        indx = 1
        for ii in self.TimeAxis.time[1:self.Nt]:
            
            EE = self.Efield[indx]
            
            for jj in range(0,self.Nref):
                for ll in range(1,L+1):
                    
                    rho1 =  - (1j*self.dt/ll)*(numpy.dot(HH,rho1) \
                             - numpy.dot(rho1,HH) ) \
                           + (self.dt/ll)*numpy.tensordot(RR,rho1) \
                            + (1j*self.dt/ll)*( numpy.dot(MU,rho1) \
                             - numpy.dot(rho1,MU) )*EE                             
                             
                    rho2 = rho2 + rho1
                rho1 = rho2    
                
            pr.data[indx,:,:] = rho2                        
            indx += 1             
            
        return pr