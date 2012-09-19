#!/usr/bin/env python
# encoding: utf-8


import pymc
import numpy as np
import scipy.special as scsp

## Try with 1D model
def population_code_response(theta, N=100, kappa=0.1, amplitude=1.0):

    pref_angles = np.linspace(-np.pi, np.pi, N, endpoint=False)

    return amplitude*np.exp(kappa*np.cos(theta - pref_angles))/(2.*np.pi*scsp.i0(kappa))

N     = 50
kappa = 3.0
sigma = 0.1
amplitude = 1.0
            

## Generate dataset
M = 30
stimuli_used = 1.4*np.ones(M)
# stimuli_used = np.random.rand(M)*np.pi/2.

dataset = np.zeros((M, N))
for i, stim in enumerate(stimuli_used):
    dataset[i] = population_code_response(stim, N=N, kappa=kappa, amplitude=amplitude) + sigma*np.random.randn(N)


## Now build the model
# mu_theta = pymc.Uniform('mu', lower=-np.pi, upper=np.pi)
# kappa_theta = pymc.Uniform('kappa', lower=0.0, upper=100.0)

theta = pymc.CircVonMises('theta', mu=0.0, kappa=0.001)
# theta = pymc.CircVonMises('theta', mu=mu_theta, kappa=kappa_theta)
# theta = pymc.CircVonMises('theta', mu=mu_theta, kappa=5.)
# theta = pymc.Uniform('theta', lower=-np.pi, upper=np.pi)

@pymc.deterministic
def deterministic_popresponse(theta=theta, N=N, kappa=kappa):
    """
        Get an angle, returns the population response.

        Dimension N
    """
    # Maybe enforce that theta \in [0, 2pi]...
    pref_angles = np.linspace(-np.pi, np.pi, N, endpoint=False)

    return np.exp(kappa*np.cos(theta - pref_angles))/(2.*np.pi*scsp.i0(kappa))

print stimuli_used[0]
memory = pymc.MvNormal('m_0', mu=deterministic_popresponse, tau=1./sigma**0.5*np.eye(N), value=dataset[0], observed=True)


