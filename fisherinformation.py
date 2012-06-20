#!/usr/bin/env python
# encoding: utf-8
"""
fisherinformation.py

Created by Loic Matthey on 2012-06-03.
Copyright (c) 2012 Gatsby Unit. All rights reserved.
"""

import pylab as plt
import numpy as np

from utils import *
from statisticsmeasurer import *
from randomfactorialnetwork import *

def main():
    pass

if __name__ == '__main__':
    '''
        Compute and plot the Fisher Information for a RandomFactorialNetwork
    '''

    ###
    
    if False:
        ## Small tries firsts

        N_sqrt = 30.
        
        sigma_x_2 = (0.5)**2.
        kappa1 = 3.0
        kappa2 = 5.0

        # Get the mu and gamma (means of receptive fields)
        coverage_1D = np.linspace( -np.pi + np.pi/N_sqrt, np.pi + np.pi/N_sqrt, N_sqrt, endpoint=False)
        means = np.array(cross(2*[coverage_1D.tolist()]))

        mu = means[:, 0]
        gamma = means[:, 1]

        precision = 9
        stim_space = np.linspace(-np.pi, np.pi, precision, endpoint=False)
        stim_space = np.array(cross(stim_space, stim_space))

        ## Check that \sum_i f_i() is ~constant
        print np.mean(np.sum(np.exp(kappa1*np.cos(stim_space[:, 0] - mu[:, np.newaxis]) + kappa2*np.cos(stim_space[:, 1] - gamma[:, np.newaxis])), axis=0))
        print np.std(np.sum(np.exp(kappa1*np.cos(stim_space[:, 0] - mu[:, np.newaxis]) + kappa2*np.cos(stim_space[:, 1] - gamma[:, np.newaxis])), axis=0))
        IF_perneuron_multstim = np.exp(kappa1*np.cos(stim_space[:, 0] - mu[:, np.newaxis]) + kappa2*np.cos(stim_space[:, 1] - gamma[:, np.newaxis]))
        sum_IF_perneuron_multstim = np.mean(IF_perneuron_multstim, axis=1)
        
        plt.figure()
        plt.plot(sum_IF_perneuron_multstim)
        plt.ylim((0, 1.1*sum_IF_perneuron_multstim.max()))
        plt.title('Fisher Information constant for all neurons, when averaging over stimuli')

        ## Show how the FI is different per neuron, for a given stimulus
        stim = np.array([0., 0.])
        IF_perneuron = np.sin(stim[0] - mu[:, np.newaxis])**2.*np.exp(2.*kappa1*np.cos(stim[1] - mu[:, np.newaxis]) + 2.*kappa2*np.cos(stim[0] - gamma[:, np.newaxis]))


        plt.figure()
        plt.imshow(np.reshape(IF_perneuron, (N_sqrt, N_sqrt)), interpolation='nearest')
        plt.colorbar()
        plt.title('Local effects of Fisher Information')

    
    if False:
        ### Now check the dependence on N_sqrt
        sigma_x_2 = (0.5)**2.
        kappa1 = 3.0
        kappa2 = 5.0

        all_N_sqrt = np.arange(1, 21)
        all_FI_11 = np.zeros(all_N_sqrt.size)
        all_FI_12 = np.zeros(all_N_sqrt.size)
        all_FI_22 = np.zeros(all_N_sqrt.size)
        all_FI_11_limN = np.zeros(all_N_sqrt.size)
        all_FI_22_limN = np.zeros(all_N_sqrt.size)

        for i, N_sqrt in enumerate(all_N_sqrt):
            # Get the mu and gamma (means of receptive fields)
            coverage_1D = np.linspace( -np.pi + np.pi/N_sqrt, np.pi + np.pi/N_sqrt, N_sqrt, endpoint=False)
            means = np.array(cross(2*[coverage_1D.tolist()]))

            mu = means[:, 0]
            gamma = means[:, 1]

            precision = 1.
            stim_space = np.linspace(0, 2.*np.pi, precision, endpoint=False)
            stim_space = np.array(cross(stim_space, stim_space))

            # Full FI
            all_FI_11[i] = 1./sigma_x_2 * kappa1**2.*np.mean(np.sum(np.sin(stim_space[:, 0] - mu[:, np.newaxis])**2.*np.exp(2.*kappa1*np.cos(stim_space[:, 0] - mu[:, np.newaxis]) + 2.*kappa2*np.cos(stim_space[:, 1] - gamma[:, np.newaxis])), axis=0))

            all_FI_12[i] = 1./sigma_x_2 * kappa1*kappa2*np.mean(np.sum(np.sin(stim_space[:, 0] - mu[:, np.newaxis])*np.sin(stim_space[:, 1] - gamma[:, np.newaxis])*np.exp(2.*kappa1*np.cos(stim_space[:, 0] - mu[:, np.newaxis]) + 2.*kappa2*np.cos(stim_space[:, 1] - gamma[:, np.newaxis])), axis=0))
            
            all_FI_22[i] = 1./sigma_x_2 * kappa2**2.*np.mean(np.sum(np.sin(stim_space[:, 1] - gamma[:, np.newaxis])**2.*np.exp(2.*kappa1*np.cos(stim_space[:, 0] - mu[:, np.newaxis]) + 2.*kappa2*np.cos(stim_space[:, 1] - gamma[:, np.newaxis])), axis=0))

            # Large N limit
            density = N_sqrt**2./(4.*np.pi**2.)
            all_FI_11_limN[i] = 1./sigma_x_2*density*2.*np.pi**2.*kappa1**2.0*scsp.i0(2*kappa2)*(scsp.i0(2*kappa1) - scsp.iv(2, 2*kappa1))
            all_FI_22_limN[i] = 1./sigma_x_2*density*2.*np.pi**2.*kappa2**2.0*scsp.i0(2*kappa1)*(scsp.i0(2*kappa2) - scsp.iv(2, 2*kappa2))


        plt.plot(all_N_sqrt**2., all_FI_11, all_N_sqrt**2., all_FI_11_limN, all_N_sqrt**2., all_FI_12, all_N_sqrt**2., all_FI_22, all_N_sqrt**2., all_FI_22_limN)
        plt.xlabel('Number of neurons')
        plt.ylabel('Fisher Information')
        
        
        

    if False:
        ####
        # Getting the 'correct' Fisher information: check the FI for an average object
        N_sqrt = 20.

        # sigma_x_2 = (0.5)**2.
        kappa1 = 0.8
        kappa2 = 0.8
        alpha = 1.0

        # Get the mu and gamma (means of receptive fields)
        coverage_1D = np.linspace( -np.pi + np.pi/N_sqrt, np.pi + np.pi/N_sqrt, N_sqrt, endpoint=False)
        means = np.array(cross(2*[coverage_1D.tolist()]))

        mu = means[:, 0]
        gamma = means[:, 1]

        R = 2
        sigma_x = 3.0
        sigma_y = 1.0

        precision = 2.
        stim_space = np.linspace(0, 2.*np.pi, precision, endpoint=False)
        stim_space = np.array(cross(stim_space, stim_space))

        density = N_sqrt**2./(4.*np.pi**2.)

        T_all = np.arange(1, 5)
        FI_Tt = np.zeros((T_all.size, T_all.size))
        all_FI_11_Tt = np.zeros((T_all.size, T_all.size))
        covariance_all = np.zeros((T_all.size, T_all.size, int(N_sqrt**2.), int(N_sqrt**2.)))
        for i, T in enumerate(T_all):
            time_weights_parameters = dict(weighting_alpha=alpha, weighting_beta=1.0, specific_weighting=0.1, weight_prior='uniform')
            rn = RandomFactorialNetwork.create_full_conjunctive(int(N_sqrt**2.), R=R, sigma=sigma_x, scale_moments=(1.0, 0.1), ratio_moments=(1.0, 0.2))
            data_gen_noise = DataGeneratorRFN(3000, T, rn, sigma_y=sigma_y, sigma_x=sigma_x, time_weights_parameters=time_weights_parameters, cued_feature_time=T-1)
            stat_meas = StatisticsMeasurer(data_gen_noise)
            covariance = stat_meas.model_parameters['covariances'][2][-1]
                
            for j, t in enumerate(xrange(T)):
                
                covariance_all[i, j] = covariance

                # Full FI
                all_FI_11_Tt[i, j] = alpha**(2.*T-2.*t)*1./sigma_x**2. * kappa1**2.*np.mean(np.sum(np.sin(stim_space[:, 0] - mu[:, np.newaxis])*np.exp(kappa1*np.cos(stim_space[:, 0] - mu[:, np.newaxis]) + kappa2*np.cos(stim_space[:, 1] - gamma[:, np.newaxis]))*np.linalg.solve(covariance, np.sin(stim_space[:, 0] - mu[:, np.newaxis])*np.exp(kappa1*np.cos(stim_space[:, 0] - mu[:, np.newaxis]) + kappa2*np.cos(stim_space[:, 1] - gamma[:, np.newaxis]))), axis=0))
                # all_FI_11_Tt[i, j] = alpha**(2.*T-2.*t + 2.)*1./sigma_x_2 * kappa1**2.*np.mean(np.sum(np.sin(stim_space[:, 0] - mu[:, np.newaxis])*np.exp(kappa1*np.cos(stim_space[:, 0] - mu[:, np.newaxis]) + kappa2*np.cos(stim_space[:, 1] - gamma[:, np.newaxis]))*np.sin(stim_space[:, 0] - mu[:, np.newaxis])*np.exp(kappa1*np.cos(stim_space[:, 0] - mu[:, np.newaxis]) + kappa2*np.cos(stim_space[:, 1] - gamma[:, np.newaxis])), axis=0))

                # FI_Tt[i, j] = alpha**(2.*T-2.*t)*1./sigma_x**2.*density*2.*np.pi**2.*kappa1**2.0*scsp.i0(2*kappa2)*(scsp.i0(2*kappa1) - scsp.iv(2, 2*kappa1))        

        all_FI_11_Tt[all_FI_11_Tt == 0.0] = np.nan

        plt.figure()
        plt.imshow(all_FI_11_Tt, interpolation='nearest', origin='left')
        plt.colorbar()

    if True:
        # Do the optimisation
        target_experimental_precisions  = np.array([5.0391, 3.4834, 2.9056, 2.2412, 1.7729])

        N_sqrt = 20.

        # sigma_x_2 = (0.5)**2.
        kappa1 = 0.8
        kappa2 = kappa1
        
        # Get the mu and gamma (means of receptive fields)
        coverage_1D = np.linspace( -np.pi + np.pi/N_sqrt, np.pi + np.pi/N_sqrt, N_sqrt, endpoint=False)
        means = np.array(cross(2*[coverage_1D.tolist()]))
        mu = means[:, 0]
        gamma = means[:, 1]

        sigma_x = 3.0
        sigma_y = 0.0

        precision = 1.0
        stim_space = np.linspace(0, 2.*np.pi, precision, endpoint=False)
        stim_space = np.array(cross(stim_space, stim_space))

        T_all = np.arange(1, 6)
            
        covariances_all = np.zeros((T_all.size, int(N_sqrt**2.), int(N_sqrt**2.)))

        for i, T in enumerate(T_all):
            time_weights_parameters = dict(weighting_alpha=1.0, weighting_beta=1.0, specific_weighting=0.1, weight_prior='uniform')
            rn = RandomFactorialNetwork.create_full_conjunctive(int(N_sqrt**2.), R=2, sigma=sigma_x, scale_moments=(1.0, 0.1), ratio_moments=(1.0, 0.2))
            data_gen_noise = DataGeneratorRFN(3000, T, rn, sigma_y=sigma_y, sigma_x=sigma_x, time_weights_parameters=time_weights_parameters, cued_feature_time=T-1)
            stat_meas = StatisticsMeasurer(data_gen_noise)
            covariances_all[i] = stat_meas.model_parameters['covariances'][2][-1]
        

        def compute_FI(sigma_x, kappa1, kappa2, T_all, stim_space, mu, gamma, covariances_all):
            FI_T = np.zeros(T_all.size)

            # Full FI
            for i, T in enumerate(T_all):
                FI_T[i] = 1./sigma_x**2. * kappa1**2.*np.mean(np.sum(np.sin(stim_space[:, 0] - mu[:, np.newaxis])*np.exp(kappa1*np.cos(stim_space[:, 0] - mu[:, np.newaxis]) + kappa2*np.cos(stim_space[:, 1] - gamma[:, np.newaxis]))*np.linalg.solve(covariances_all[i], np.sin(stim_space[:, 0] - mu[:, np.newaxis])*np.exp(kappa1*np.cos(stim_space[:, 0] - mu[:, np.newaxis]) + kappa2*np.cos(stim_space[:, 1] - gamma[:, np.newaxis]))), axis=0))
                # all_FI_11_Tt[i, j] = alpha**(2.*T-2.*t + 2.)*1./sigma_x_2 * kappa1**2.*np.mean(np.sum(np.sin(stim_space[:, 0] - mu[:, np.newaxis])*np.exp(kappa1*np.cos(stim_space[:, 0] - mu[:, np.newaxis]) + kappa2*np.cos(stim_space[:, 1] - gamma[:, np.newaxis]))*np.sin(stim_space[:, 0] - mu[:, np.newaxis])*np.exp(kappa1*np.cos(stim_space[:, 0] - mu[:, np.newaxis]) + kappa2*np.cos(stim_space[:, 1] - gamma[:, np.newaxis])), axis=0))

                # FI_Tt[i, j] = alpha**(2.*T-2.*t)*1./sigma_x**2.*density*2.*np.pi**2.*kappa1**2.0*scsp.i0(2*kappa2)*(scsp.i0(2*kappa1) - scsp.iv(2, 2*kappa1))

            return FI_T


        def MSE_from_experimental(computed_FI, target_experimental_precisions):
            
            return np.sum((target_experimental_precisions - computed_FI)**2.)

        def MSE_powerlaw_experimental(computed_FI, target_experimental_precisions):
            
            return np.sum((fit_powerlaw(np.arange(1, 6), target_experimental_precisions) - fit_powerlaw(np.arange(1, 6), computed_FI))**2.)


        #### See effect of sigma_x
        sigma_x_space = np.linspace(0.05, 10.0, 100.)

        sigma_x_MSE_experimental = np.zeros_like(sigma_x_space)
        FI_all = np.zeros((sigma_x_space.size, T_all.size))
        for i, sigma_x in enumerate(sigma_x_space):
            FI_all[i] = compute_FI(sigma_x, kappa1, kappa2, T_all, stim_space, mu, gamma, covariances_all)
            
            # sigma_x_MSE_experimental[i] = MSE_from_experimental(FI_all[i], target_experimental_precisions)

            sigma_x_MSE_experimental[i] = MSE_powerlaw_experimental(FI_all[i], target_experimental_precisions)

        plt.figure()
        plt.semilogy(sigma_x_space, sigma_x_MSE_experimental)

        # Show the best sigma
        best_sigma_x_ind = np.argmin(sigma_x_MSE_experimental)

        print "Best sigma_x : %.2f. MSE: %.2f" % (sigma_x_space[best_sigma_x_ind], sigma_x_MSE_experimental[best_sigma_x_ind])

        plt.figure()
        plt.plot(T_all, FI_all[best_sigma_x_ind])
        plt.plot(T_all, target_experimental_precisions)
        plt.legend(['Model', 'Experimental'])

        plt.figure()
        plt.imshow(FI_all.T, norm=plt.matplotlib.colors.LogNorm())

        f = plt.figure()
        ax = f.add_subplot(111, projection='3d')
        X, Y = np.meshgrid(sigma_x_space, T_all)
        ax.plot_surface(X, Y, np.log(FI_all.T))









    plt.show()

