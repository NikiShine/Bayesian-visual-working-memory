#!/usr/bin/env python
# encoding: utf-8
"""
datagenerator.py

Created by Loic Matthey on 2011-06-10.
Copyright (c) 2011 Gatsby Unit. All rights reserved.
"""

# from scaledimage import *
import pylab as plt
import matplotlib.ticker as plttic
import numpy as np

from populationcode import *
from randomnetwork import *

class DataGenerator:
    def __init__(self, N, T, random_network, type_Z = 'binary', time_weights=None, sigma_y = 0.05, weighting_alpha=0.3, weighting_beta = 1.0, weight_prior='uniform'):
        '''
                       N:   number of datapoints
                       T:   number of patterns per datapoint
            time_weights:   [alpha_t ; beta_t] for all t=1:T
                 sigma_y:   Noise on the memory markov chain
        '''
        
        self.N = N
        
        # For now, assume T is known and fixed
        self.T = T
        
        # Use this random network to construct the data
        self.random_network = random_network
        
        # Number of feature populations
        self.R = random_network.R
        
        self.sigma_y = sigma_y
        
        assert self.random_network.network_initialised, "Initialise the possible orientations in the Random Network first"
        
        # Initialise the weights for time decays if needed
        if time_weights is None:
            self.initialise_time_weights(prior=weight_prior, weighting_alpha=weighting_alpha, weighting_beta=weighting_beta)
        else:
            self.time_weights = time_weights
        
        # Build the dataset
        self.build_dataset(type_Z = type_Z)
        
        
    
    def initialise_time_weights(self, prior='uniform', weighting_alpha=0.3, weighting_beta=1.0, primacy_weighting=2.):
        '''
            Initialises the weights used for mixing through time in the final 'memory'
            
            Could be:
                - Uniform
                - Prior for primacy
                
            format: [alpha_t ; beta_t], alpha_t mix the past, beta_t mix the current pattern
        '''
        self.time_weights = np.zeros((2, self.T))
        
        if prior == 'uniform':
            self.time_weights[0] = weighting_alpha*np.ones(self.T)
            self.time_weights[1] = weighting_beta*np.ones(self.T)
        elif prior == 'primacy':
            self.time_weights[0] = weighting_alpha*np.ones(self.T)
            self.time_weights[1] = weighting_beta*np.ones(self.T)
            self.time_weights[1,0] *= primacy_weighting
        elif prior =='recency':
            self.time_weights[0] = weighting_alpha*np.ones(self.T)
            self.time_weights[1] = weighting_beta*(np.ones(self.T) + 0.2*np.arange(self.T))
        else:
            raise ValueError('Prior for time weights unknown')
        
    
    def build_dataset(self, type_Z = 'binary'):
        '''
            Creates the dataset
                For each datapoint, choose T possible orientations ('binary' 1-of-K code or 'discrete' Z=k),
                then combine them together, with time decay
            
            Z_true:             N x T x R
            Y :                 N x M
            all_Y:              N x T x M
            chosen_orientation: N x T x R
        '''
        
        ## Create Z, assigning a feature to each time for each datapoint
        
        if type_Z == 'binary':
            self.Z_true = np.zeros((self.N, self.T, self.R, self.random_network.K))
        elif type_Z == 'discrete':
            self.Z_true = np.zeros((self.N, self.T, self.R), dtype='int')
        else:
            raise ValueError('Type_Z unknown')
        
        self.chosen_orientations = np.zeros((self.N, self.T, self.R), dtype='int')
        
        # Initialise Y (keep intermediate y_t as well)
        self.all_Y = np.zeros((self.N, self.T, self.random_network.M))
        self.Y = np.zeros((self.N, self.random_network.M))
        
        assert self.T <= self.random_network.possible_objects_indices.size, "Unique objects needed"
        
        #print self.time_weights
        
        for i in np.arange(self.N):
            
            # Choose T random orientations, uniformly
            self.chosen_orientations[i] = np.random.permutation(self.random_network.possible_objects_indices)[:self.T]
            
            if type_Z == 'binary':
                # Activate those features for the current datapoint
                for r in np.arange(self.R):
                    self.Z_true[i, np.arange(self.T), r, self.chosen_orientations[i][:,r]] = 1.0
            elif type_Z == 'discrete':
                self.Z_true[i] = self.chosen_orientations[i]
        
            # Get the 'x' samples (here from the population code, with correlated covariance, but whatever)
            x_samples = self.random_network.sample_network_response(self.chosen_orientations[i].T)
            x_samples_sum = np.sum(x_samples, axis=0)
            
            # Combine them together
            for t in np.arange(self.T):
                self.Y[i] = self.time_weights[0, t]*self.Y[i].copy() + self.time_weights[1, t]*x_samples_sum[t] + self.sigma_y*np.random.randn(self.random_network.M)
                self.all_Y[i, t] = self.Y[i]
            
            
        
        
    
    def plot_data(self, nb_to_plot=-1):
        '''
            Show all datapoints
        '''
        if nb_to_plot < 0:
            nb_to_plot = self.N
        
        f = plt.figure()
        N_sqrt = np.sqrt(nb_to_plot).astype(np.int32)
        for i in np.arange(N_sqrt):
            for j in np.arange(N_sqrt):
                subax = f.add_subplot(N_sqrt, N_sqrt, N_sqrt*i+j)
                subax.plot(np.linspace(0., np.pi, self.random_network.M, endpoint=False), self.Y[N_sqrt*i+j])
                subax.xaxis.set_major_locator(plttic.NullLocator())
                subax.yaxis.set_major_locator(plttic.NullLocator())
        
    
    
    # def show_features(self):
    #         '''
    #             Show all features
    #         '''
    #         f = plt.figure()
    #         
    #         for k in np.arange(self.K):
    #             subaxe=f.add_subplot(1, self.K, k)
    #             scaledimage(self.features[k], ax=subaxe)
    
    



if __name__ == '__main__':
    N = 100
    T = 2
    K = 6
    M = 30
    D = 30
    R = 2
    
    random_network = RandomNetwork.create_instance_uniform(K, M, D=D, R=R, W_type='identity', W_parameters=[0.1, 0.5])
    
    data_gen = DataGenerator(N, T, random_network, type_Z='binary', weighting_alpha=0.8, weighting_beta = 1.0, weight_prior='recency')
    
    data_gen.plot_data(16)
    
    #print data_gen.X.shape
    
    #data_gen.view_data()
    
    #data_gen.view_features()
    
    plt.show()