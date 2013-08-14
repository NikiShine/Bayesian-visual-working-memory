#!/usr/bin/env python
# encoding: utf-8

import numpy as np
import matplotlib.pyplot as plt

from experimentlauncher import *

from datagenerator import *
from hierarchicalrandomnetwork import *
from randomfactorialnetwork import *
from statisticsmeasurer import *
from slicesampler import *
from utils import *
from dataio import *
from gibbs_sampler_continuous_fullcollapsed_randomfactorialnetwork import *
from launchers import *

plt.rcParams['font.size'] = 17

set_colormap = plt.cm.cubehelix

def do_plots_population_codes():
    
    # plt.set_cmap('cubehelix')

    if True:
        # Plot conj coverage for abstract

        M = int(17**2.)
        rcscale = 8.
        # plt.rcParams['font.size'] = 17

        selected_neuron = M/2+3

        plt.ion()

        rn = RandomFactorialNetwork.create_full_conjunctive(M, rcscale=rcscale)
        ax = rn.plot_coverage_feature_space(alpha_ellipses=0.3, facecolor='b', lim_factor=1.1, nb_stddev=1.1)
        ax = rn.plot_coverage_feature_space(alpha_ellipses=0.3, facecolor='b', lim_factor=1.1, nb_stddev=1.1, specific_neurons=[selected_neuron], ax=ax)

        ax.set_xticks((-np.pi, -np.pi / 2, 0, np.pi / 2., np.pi))
        ax.set_xticklabels((r'$-\pi$', r'$-\frac{\pi}{2}$', r'$0$', r'$\frac{\pi}{2}$', r'$\pi$'))
        ax.set_yticks((-np.pi, -np.pi / 2, 0, np.pi / 2., np.pi))
        ax.set_yticklabels((r'$-\pi$', r'$-\frac{\pi}{2}$', r'$0$', r'$\frac{\pi}{2}$', r'$\pi$'))

        ax.set_xlabel('')
        ax.set_ylabel('')

        set_colormap()

        ax.get_figure().canvas.draw()

        # To be run in ETS_TOOLKIT=qt4 mayavi2
        rn.plot_neuron_activity_3d(selected_neuron, precision=100, weight_deform=0.0, draw_colorbar=False)
        try:
            import mayavi.mlab as mplt

            mplt.view(0.0, 45.0, 45.0, [0., 0., 0.])
            mplt.draw()
        except:
            pass


    if True:
        # Plt feat coverage for abstract
        M = 50
        selected_neuron = M/4

        rn = RandomFactorialNetwork.create_full_features(M, scale=0.01, ratio=5000, nb_feature_centers=1)
        # rn = RandomFactorialNetwork.create_full_features(M, autoset_parameters=True, nb_feature_centers=1)
        # ax = rn.plot_coverage_feature_space(nb_stddev=0.7, alpha_ellipses=0.2)
        ax = rn.plot_coverage_feature_space(nb_stddev=2.0, alpha_ellipses=0.3, facecolor='r', lim_factor=1.1)
        ax = rn.plot_coverage_feature_space(nb_stddev=2.0, alpha_ellipses=0.4, facecolor='r', lim_factor=1.1, specific_neurons=[selected_neuron], ax=ax)
        
        ax.set_xticks((-np.pi, -np.pi / 2, 0, np.pi / 2., np.pi))
        ax.set_xticklabels((r'$-\pi$', r'$-\frac{\pi}{2}$', r'$0$', r'$\frac{\pi}{2}$', r'$\pi$'))
        ax.set_yticks((-np.pi, -np.pi / 2, 0, np.pi / 2., np.pi))
        ax.set_yticklabels((r'$-\pi$', r'$-\frac{\pi}{2}$', r'$0$', r'$\frac{\pi}{2}$', r'$\pi$'))

        ax.set_xlabel('')
        ax.set_ylabel('')

        ax.get_figure().canvas.draw()

        if False:
            rn.plot_neuron_activity_3d(selected_neuron, precision=100, weight_deform=0.0, draw_colorbar=False)
            try:
                import mayavi.mlab as mplt

                mplt.view(0.0, 45.0, 45.0, [0., 0., 0.])
                mplt.draw()
            except:
                pass

    if True:
        # Plot mixed coverage

        autoset_parameters = False
        M = 300

        # %run experimentlauncher.py --code_type mixed --inference_method none --rc_scale 1.9 --rc_scale2 0.1 --feat_ratio -150
        conj_params = dict(scale_moments=[1.7, 0.001], ratio_moments=[1.0, 0.0001])
        feat_params = dict(scale=0.01, ratio=-8000, nb_feature_centers=1)

        rn = RandomFactorialNetwork.create_mixed(M, ratio_feature_conjunctive=0.2, conjunctive_parameters=conj_params, feature_parameters=feat_params, autoset_parameters=autoset_parameters)

        ax = rn.plot_coverage_feature_space(nb_stddev=2.0, alpha_ellipses=0.2, specific_neurons=np.arange(60, 180, 4), facecolor='r', lim_factor=1.1)
        ax = rn.plot_coverage_feature_space(nb_stddev=2.0, alpha_ellipses=0.2, specific_neurons=np.arange(180, 300, 4), facecolor='r', ax=ax, lim_factor=1.1)
        ax = rn.plot_coverage_feature_space(alpha_ellipses=0.2, specific_neurons=np.arange(60), facecolor='b', ax=ax, lim_factor=1.1)
        
        ax.set_xlabel('')
        ax.set_ylabel('')

        ax.get_figure().canvas.draw()

    if False:
        # Plot hierarchical coverage

        M = 100
        hrn_feat = HierarchialRandomNetwork(M, normalise_weights=1, type_layer_one='feature', optimal_coverage=True, M_layer_one=100, distribution_weights='exponential', threshold=1.0, output_both_layers=True)

        hrn_feat.plot_coverage_feature(nb_layer_two_neurons=3, facecolor_layerone='r', lim_factor=1.1)



    return locals()


def fisher_information_1obj_2d():
    # %run experimentlauncher.py --action_to_do launcher_do_fisher_information_estimation --subaction rcscale_dependence --M 100 --N 500 --sigmax 0.1 --sigmay 0.0001 --label fi_compare_paper --num_samples 100
    # Used the boxplot. And some
    
    # plt.rcParams['font.size'] = 16

    plt.figure()
    b = plt.boxplot([FI_rc_curv_all[rc_scale_i], FI_rc_samples_all[rc_scale_i].flatten(), FI_rc_precision_all[rc_scale_i], FI_rc_theo_all[rc_scale_i, 0], FI_rc_theo_all[rc_scale_i, 1]])
    
    for key in ['medians', 'boxes', 'whiskers', 'caps']:
        for line in b[key]:
            line.set_linewidth(2)

    # plt.boxplot([FI_rc_curv_all[rc_scale_i], FI_rc_precision_all[rc_scale_i], FI_rc_theo_all[rc_scale_i, 0], FI_rc_theo_all[rc_scale_i, 1]])
    plt.title('Comparison Curvature vs samples estimate. Rscale: %d' % rc_scale)
    plt.xticks([1, 2, 3, 4, 5], ['Curvature', 'Samples', 'Precision', 'Theo', 'Theo large N'], rotation=45)
    # plt.xticks([1, 2, 3, 4], ['Curvature', 'Precision', 'Theo', 'Theo large N'], rotation=45)

    dataio.save_current_figure('FI_rc_comparison_curv_samples_%d-{label}_{unique_id}.pdf' % rc_scale)


def posterior_plots():
    '''
        Do the plots showing how the recall works.

        Put 3 objects, show the datapoint, the full posterior, the cued posterior and a sample from it
    '''

    # Conjunctive population
    all_parameters = dict(alpha=1.0, T=3, N=10, M=25**2, sigmay=0.001, sigmax=0.5, stimuli_generation='constant', R=2, rc_scale=5.0, rc_scale2=1, feat_ratio=20., autoset_parameters=True, code_type='conj', enforce_first_stimulus=True, stimuli_generation_recall='random')
    # all_parameters = dict(alpha=1.0, T=3, N=10, M=10**2, sigmay=0.001, sigmax=0.1, stimuli_generation='constant', R=2, rc_scale=5.0, feat_ratio=20., autoset_parameters=True, code_type='conj')

    all_parameters['sigmax'] = 0.6


    plt.rcParams['font.size'] = 18

    if False:
        (random_network, data_gen, stat_meas, sampler) = init_everything(all_parameters)

        data_gen.show_datapoint(n=1)
        sampler.plot_likelihood_variation_twoangles(n=1, interpolation='bilinear')
        sampler.plot_likelihood_correctlycuedtimes(n=1)
        sampler.plot_likelihood_correctlycuedtimes(n=1, should_exponentiate=True)

    # Feature population
    all_parameters['code_type'] = 'feat'
    all_parameters['M'] = 75*2
    all_parameters['sigmax'] = 0.1

    
    # print random_network.neurons_sigma[0,0], random_network.neurons_sigma[0,1]

    if False:
        (random_network, data_gen, stat_meas, sampler) = init_everything(all_parameters)

        data_gen.show_datapoint(n=1)
        sampler.plot_likelihood_variation_twoangles(n=1, interpolation='bilinear')
        sampler.plot_likelihood_correctlycuedtimes(n=1)
        sampler.plot_likelihood_correctlycuedtimes(n=1, should_exponentiate=True)

    # Mixed population
    all_parameters['code_type'] = 'mixed'
    all_parameters['M'] = 200
    all_parameters['sigmax'] = 0.15
    all_parameters['rc_scale'] = 2.5
    all_parameters['rc_scale2'] = stddev_to_kappa(np.pi)
    all_parameters['ratio_conj'] = 0.5
    all_parameters['feat_ratio'] = stddev_to_kappa(2.*np.pi/int(all_parameters['M']*all_parameters['ratio_conj']/2.))/stddev_to_kappa(np.pi)
    
    
    if True:
        (random_network, data_gen, stat_meas, sampler) = init_everything(all_parameters)

        data_gen.show_datapoint(n=1)
        sampler.plot_likelihood_variation_twoangles(n=1, interpolation='bilinear')
        sampler.plot_likelihood_correctlycuedtimes(n=1)
        sampler.plot_likelihood_correctlycuedtimes(n=1, should_exponentiate=True)


    return locals()


def compare_fishertheo_precision():
    '''
        Small try to compare the Fisher Info with the precision of samples,
        for different values of M/rc_scale for a conjunctive network

        (not sure if used in paper)
    '''

    arguments_dict = dict(action_to_do='launcher_do_compare_fisher_info_theo', N=500, sigmax=0.5, sigmay=0.0001, num_samples=100, label='sigmax{sigmax:.2f}', autoset_parameters=False)

    arguments_dict['do_precision'] = True

    # Run the Experiment
    experiment_launcher = ExperimentLauncher(run=True, arguments_dict=arguments_dict)

    return experiment_launcher.all_vars


def plot_experimental_mixture():
    '''
        Cheat and get data from Bays 2008 from figure...
    '''

    nontargets_experimental = [dict(mean=(1., 0.0), high=(1, 0.0), low=(1, 0.0)),
                               dict(mean=(2., 0.028789279477880285), high=(2, 0.037857142857142805), low=(2.0110497237569063, 0.018571428571428558)),
                               dict(mean=(4., 0.11428571428571427), low=(3.9999999999999996, 0.10214285714285715), high=(4, 0.12714285714285717)),
                               dict(mean=(6.0, 0.2857142857142857), low=(6, 0.2628571428571429), high=(6, 0.3107142857142857))
                               ]

    random_experimental = [dict(mean=(1.0, 0.011275727401285185), high=(1, 0.028457857985477633), low=(1, -0.005906403182907263)),
                           dict(mean=(2.0, 0.04962594977981958), high=(2.0, 0.059935228130335055), low=(2.0, 0.03862938620593646)),
                           dict(mean=(4.0, 0.15725569501535036), high=(4.0, 0.17993610738648436), low=(4.0, 0.13526110244066858)),
                           dict(mean=(6.0, 0.13567435283083845), high=(6., 0.15354376863839858), low=(6., 0.11780493702327834))]

    # Fill up the rest of the fields and construct the target response rates
    targets_experimental = []

    for i in xrange(len(nontargets_experimental)):
        nontargets_experimental[i]['std'] = np.mean((nontargets_experimental[i]['high'][1] - nontargets_experimental[i]['mean'][1], nontargets_experimental[i]['mean'][1] - nontargets_experimental[i]['low'][1]))

        random_experimental[i]['std'] = np.mean((random_experimental[i]['high'][1] - random_experimental[i]['mean'][1], random_experimental[i]['mean'][1] - random_experimental[i]['low'][1]))

        targets_experimental.append(dict(mean=(i+1.0, 1.0 - nontargets_experimental[i]['mean'][1] - random_experimental[i]['mean'][1])))

    print targets_experimental

    # Construct arrays
    items_space = np.array([1, 2, 4, 6])
    nontargets_experimental_arr = np.array([nontarget_curr['mean'][1] for nontarget_curr in nontargets_experimental])
    nontargets_experimental_arr_std = np.array([nontarget_curr['std'] for nontarget_curr in nontargets_experimental])
    random_experimental_arr = np.array([random_curr['mean'][1] for random_curr in random_experimental])
    random_experimental_arr_std = np.array([random_curr['std'] for random_curr in random_experimental])
    targets_experimental_arr = np.array([target_curr['mean'][1] for target_curr in targets_experimental])

    f, ax = plt.subplots()
    ax = plot_mean_std_area(items_space, targets_experimental_arr, np.zeros(items_space.size), ax_handle=ax, linewidth=2)
    ax = plot_mean_std_area(items_space, nontargets_experimental_arr, nontargets_experimental_arr_std, ax_handle=ax, linewidth=2)
    ax = plot_mean_std_area(items_space, random_experimental_arr, random_experimental_arr_std, ax_handle=ax, linewidth=2)
    ax.set_xlim((1.0, 6))
    ax.set_ylim((0.0, 1.0))
    # ax.set_yticks((0.0, 0.25, 0.5, 0.75, 1.0))
    ax.set_yticks((0.0, 0.2, 0.4, 0.6, 0.8, 1.0))
    ax.set_xticks((1, 2, 3, 4, 5, 6))
    # plt.legend(['Target', 'Non-target', 'Random'], loc='upper right', fancybox=True, borderpad=0.3)

    return locals()


def plot_marginalfisherinfo_1d():
    N     = 50
    kappa = 6.0
    sigma = 0.5
    amplitude = 1.0
    min_distance = 0.0001

    dataio = DataIO(label='compute_fimarg', calling_function='')
    additional_comment = ''

    def population_code_response(theta, pref_angles=None, N=100, kappa=0.1, amplitude=1.0):
        if pref_angles is None:
            pref_angles = np.linspace(0., 2*np.pi, N, endpoint=False)

        return amplitude*np.exp(kappa*np.cos(theta - pref_angles))/(2.*np.pi*scsp.i0(kappa))

    pref_angles = np.linspace(-np.pi, np.pi, N, endpoint=False)

    ## Estimate likelihood
    num_points = 500
    # num_points_space = np.arange(50, 1000, 200)
    # effects_num_points = []

    # all_angles = np.linspace(0., 2.*np.pi, num_points, endpoint=False)
    all_angles = np.linspace(-np.pi, np.pi, num_points, endpoint=False)

    theta1_space = np.array([0.])
    theta2_space = all_angles

    def enforce_distance(theta1, theta2, min_distance=0.1):
        return np.abs(wrap_angles(theta1 - theta2)) > min_distance


    min_distance_space = np.array([np.pi/30., np.pi/10., np.pi/4.])
    
    inv_FI_search = np.zeros((min_distance_space.size))
    FI_search = np.zeros((min_distance_space.size))
    FI_search_inv = np.zeros((min_distance_space.size))
    inv_FI_1_search = np.zeros((min_distance_space.size))
    inv_FI_search_full = np.zeros((min_distance_space.size, theta1_space.size, theta2_space.size))

    search_progress = progress.Progress(min_distance_space.size)

    for m, min_distance in enumerate(min_distance_space):
        
        if search_progress.percentage() % 5.0 < 0.0001:
            print "%.2f%%, %s left - %s" % (search_progress.percentage(), search_progress.time_remaining_str(), search_progress.eta_str())

        inv_FI_all = np.ones((theta1_space.size, theta2_space.size))*np.nan
        FI_all = np.ones((theta1_space.size, theta2_space.size, 2, 2))*np.nan
        inv_FI_1 = np.ones(theta1_space.size)*np.nan
        FI_all_inv = np.ones((theta1_space.size, theta2_space.size, 2, 2))*np.nan

        # Check inverse FI for given min_distance and kappa
        for i, theta1 in enumerate(theta1_space):
            der_1 = kappa*np.sin(pref_angles - theta1)*population_code_response(theta1, pref_angles=pref_angles, N=N, kappa=kappa, amplitude=amplitude)

            for j, theta2 in enumerate(theta2_space):
                
                if enforce_distance(theta1, theta2, min_distance=min_distance):
                    # Only compute if theta1 different enough of theta2
                    
                    der_2 = kappa*np.sin(pref_angles - theta2)*population_code_response(theta2, pref_angles=pref_angles, N=N, kappa=kappa, amplitude=amplitude)
                    
                    # FI for 2 objects
                    FI_all[i, j, 0, 0] = np.sum(der_1**2.)/(2.*sigma**2.)
                    FI_all[i, j, 0, 1] = np.sum(der_1*der_2)/(2.*sigma**2.)
                    FI_all[i, j, 1, 0] = np.sum(der_1*der_2)/(2.*sigma**2.)
                    FI_all[i, j, 1, 1] = np.sum(der_2**2.)/(2.*sigma**2.)
                    FI_all_inv[i, j] = np.linalg.inv(FI_all[i, j])

                    # Inv FI for 2 objects
                    inv_FI_all[i, j] = (2.*sigma**2.)/(np.sum(der_1**2.) - np.sum(der_1*der_2)**2./np.sum(der_2**2.))

            inv_FI_search_full[m, i] = inv_FI_all[i]

            # FI for 1 object
            inv_FI_1[i] = sigma**2./np.sum(der_1**2.)

        # inv_FI_search[m, k] = np.mean(inv_FI_all)
        inv_FI_search[m] = np.mean(np.ma.masked_invalid(inv_FI_all))
        FI_search[m] = np.mean(np.ma.masked_invalid(FI_all[..., 0, 0]))
        FI_search_inv[m] = np.mean(np.ma.masked_invalid(FI_all_inv[..., 0, 0]))

        inv_FI_1_search[m] = np.mean(inv_FI_1)

        search_progress.increment()

    print "FI_2obj_invtheo: ", inv_FI_search
    print "inv(FI_2obj_theo): ", FI_search_inv
    print "FI_2obj_theo[0,0]^-1 (wrong): ", 1./FI_search
    print "FI_1obj_theoinv: ", inv_FI_1_search
    print "2 obj effects: ", inv_FI_search/inv_FI_1_search

    plt.rcParams['font.size'] = 16

    left = 0.75
    f, axes = plt.subplots(ncols=min_distance_space.size)
    min_distance_labels = ['\\frac{\pi}{30}', '\\frac{\pi}{10}', '\\frac{\pi}{4}']
    titles_positions = [0.5, 0.4, 0.6]
    for m, min_distance in enumerate(min_distance_space):
        axes[m].bar(left/2., inv_FI_search[m]/inv_FI_1_search[0], width=left)
        axes[m].bar(left*2., inv_FI_1_search[m]/inv_FI_1_search[0], width=left, color='r')
        # axes[m].plot(left+np.arange(2), 0.5*inv_FI_search[m]*np.ones(2), 'r:')
        axes[m].set_xlim((0.0, left*3.5))
        # axes[m].set_ylim((0., 0.2))
        axes[m].set_xticks((left, left*5./2.))
        axes[m].set_xticklabels(("$\\tilde{I_F}^{-1}$", "${I_F^{(1)}}^{-1}$"))
        axes[m].set_yticks((0, 1, 2, 3))
        # axes[m].set_title('$min(\\theta_i - \\theta_j) = %s$' % min_distance_labels[m])
        axes[m].text(0.5, 1.05, '$min(\\theta_i - \\theta_j) = %s$' % min_distance_labels[m], transform=axes[m].transAxes, horizontalalignment='center', fontsize=18) 

    # plt.figure()
    # plt.bar(xrange(3), np.array(zip(FI_search_inv, inv_FI_1_search)))

    # plt.figure()
    # plt.semilogy(min_distance_space, (inv_FI_search/inv_FI_1_search)[:, 1:], linewidth=2)
    # plt.plot(np.linspace(0.0, 1.6, 100), np.ones(100)*2.0, 'k:', linewidth=2)
    # plt.xlabel('Minimum distance')
    # plt.ylabel('$\hat{I_F}^{-1}/{I_F^{(1)}}^{-1}$')

    return locals()


if __name__ == '__main__':

    all_vars = {}

    # all_vars = do_plots_population_codes()
    # all_vars = posterior_plots()
    # all_vars = compare_fishertheo_precision()
    # all_vars = plot_experimental_mixture()
    all_vars = plot_marginalfisherinfo_1d()

    variables_to_reinstantiate = ['data_gen', 'sampler', 'stat_meas', 'random_network', 'args', 'constrained_parameters', 'data_pbs', 'dataio']

    for var_reinst in variables_to_reinstantiate:
        if var_reinst in all_vars:
            vars()[var_reinst] = all_vars[var_reinst]

    plt.show()





