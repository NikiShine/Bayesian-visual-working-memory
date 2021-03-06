"""
    ExperimentDescriptor for Fitting experiments in a mixed population code

    reloader_specific_stimuli_mixed_sigmaxrangebis_191013
"""

import os
import numpy as np
from experimentlauncher import *
from dataio import *
import re

import matplotlib.pyplot as plt

import inspect

import utils
import cPickle as pickle

import em_circularmixture_allitems_uniquekappa
import em_circularmixture_allitems_kappafi

import launchers

# Commit @2042319 +


def plots_specific_stimuli_mixed(data_pbs, generator_module=None):
    '''
        Reload and plot behaviour of mixed population code on specific Stimuli
        of 3 items.
    '''

    #### SETUP
    #
    savefigs = True
    savedata = True

    plot_per_min_dist_all = False
    specific_plots_paper = False
    plots_emfit_allitems = False
    plot_min_distance_effect = True

    compute_bootstraps = False

    should_fit_allitems_model = True
    # caching_emfit_filename = None
    mixturemodel_to_use = 'allitems_uniquekappa'
    # caching_emfit_filename = os.path.join(generator_module.pbs_submission_infos['simul_out_dir'], 'cache_emfitallitems_uniquekappa.pickle')
    # mixturemodel_to_use = 'allitems_fikappa'

    caching_emfit_filename = os.path.join(generator_module.pbs_submission_infos['simul_out_dir'], 'cache_emfit%s.pickle' % mixturemodel_to_use)

    compute_fisher_info_perratioconj = True
    caching_fisherinfo_filename = os.path.join(generator_module.pbs_submission_infos['simul_out_dir'], 'cache_fisherinfo.pickle')

    colormap = None  # or 'cubehelix'
    plt.rcParams['font.size'] = 16
    #
    #### /SETUP

    print "Order parameters: ", generator_module.dict_parameters_range.keys()

    all_args = data_pbs.loaded_data['args_list']
    result_all_precisions_mean = utils.nanmean(np.squeeze(data_pbs.dict_arrays['result_all_precisions']['results']), axis=-1)
    result_all_precisions_std = utils.nanstd(np.squeeze(data_pbs.dict_arrays['result_all_precisions']['results']), axis=-1)
    result_em_fits_mean = utils.nanmean(np.squeeze(data_pbs.dict_arrays['result_em_fits']['results']), axis=-1)
    result_em_fits_std = utils.nanstd(np.squeeze(data_pbs.dict_arrays['result_em_fits']['results']), axis=-1)
    result_em_kappastddev_mean = utils.nanmean(utils.kappa_to_stddev(np.squeeze(data_pbs.dict_arrays['result_em_fits']['results'])[..., 0, :]), axis=-1)
    result_em_kappastddev_std = utils.nanstd(utils.kappa_to_stddev(np.squeeze(data_pbs.dict_arrays['result_em_fits']['results'])[..., 0, :]), axis=-1)
    result_responses_all = np.squeeze(data_pbs.dict_arrays['result_responses']['results'])
    result_target_all = np.squeeze(data_pbs.dict_arrays['result_target']['results'])
    result_nontargets_all = np.squeeze(data_pbs.dict_arrays['result_nontargets']['results'])

    nb_repetitions = result_responses_all.shape[-1]
    K = result_nontargets_all.shape[-2]
    N = result_responses_all.shape[-2]

    enforce_min_distance_space = data_pbs.loaded_data['parameters_uniques']['enforce_min_distance']
    sigmax_space = data_pbs.loaded_data['parameters_uniques']['sigmax']
    ratio_space = data_pbs.loaded_data['datasets_list'][0]['ratio_space']

    print enforce_min_distance_space
    print sigmax_space
    print ratio_space
    print result_all_precisions_mean.shape, result_em_fits_mean.shape
    print result_responses_all.shape

    dataio = DataIO(output_folder=generator_module.pbs_submission_infos['simul_out_dir'] + '/outputs/', label='global_' + dataset_infos['save_output_filename'])

    # Reload cached emfitallitems
    if caching_emfit_filename is not None:
        if os.path.exists(caching_emfit_filename):
            # Got file, open it and try to use its contents
            try:
                with open(caching_emfit_filename, 'r') as file_in:
                    # Load and assign values
                    print "Reloader EM fits from cache", caching_emfit_filename
                    cached_data = pickle.load(file_in)
                    result_emfitallitems = cached_data['result_emfitallitems']
                    mixturemodel_used = cached_data.get('mixturemodel_used', '')

                    if mixturemodel_used != mixturemodel_to_use:
                        print "warning, reloaded model used a different mixture model class"
                    should_fit_allitems_model = False

            except IOError:
                print "Error while loading ", caching_emfit_filename, "falling back to computing the EM fits"


    # Load the Fisher Info from cache if exists. If not, compute it.
    if caching_fisherinfo_filename is not None:
        if os.path.exists(caching_fisherinfo_filename):
            # Got file, open it and try to use its contents
            try:
                with open(caching_fisherinfo_filename, 'r') as file_in:
                    # Load and assign values
                    cached_data = pickle.load(file_in)
                    result_fisherinfo_mindist_sigmax_ratio = cached_data['result_fisherinfo_mindist_sigmax_ratio']
                    compute_fisher_info_perratioconj = False

            except IOError:
                print "Error while loading ", caching_fisherinfo_filename, "falling back to computing the Fisher Info"

    if compute_fisher_info_perratioconj:
        # We did not save the Fisher info, but need it if we want to fit the mixture model with fixed kappa. So recompute them using the args_dicts

        result_fisherinfo_mindist_sigmax_ratio = np.empty((enforce_min_distance_space.size, sigmax_space.size, ratio_space.size))

        # Invert the all_args_i -> min_dist, sigmax indexing
        parameters_indirections = data_pbs.loaded_data['parameters_dataset_index']

        # min_dist_i, sigmax_level_i, ratio_i
        for min_dist_i, min_dist in enumerate(enforce_min_distance_space):
            for sigmax_i, sigmax in enumerate(sigmax_space):
                # Get index of first dataset with the current (min_dist, sigmax) (no need for the others, I think)
                arg_index = parameters_indirections[(min_dist, sigmax)][0]

                # Now using this dataset, reconstruct a RandomFactorialNetwork and compute the fisher info
                curr_args = all_args[arg_index]

                for ratio_conj_i, ratio_conj in enumerate(ratio_space):
                    # Update param
                    curr_args['ratio_conj'] = ratio_conj
                    # curr_args['stimuli_generation'] = 'specific_stimuli'

                    (_, _, _, sampler) = launchers.init_everything(curr_args)

                    # Theo Fisher info
                    result_fisherinfo_mindist_sigmax_ratio[min_dist_i, sigmax_i, ratio_conj_i] = sampler.estimate_fisher_info_theocov()

                    print "Min dist: %.2f, Sigmax: %.2f, Ratio: %.2f: %.3f" % (min_dist, sigmax, ratio_conj, result_fisherinfo_mindist_sigmax_ratio[min_dist_i, sigmax_i, ratio_conj_i])


        # Save everything to a file, for faster later plotting
        if caching_fisherinfo_filename is not None:
            try:
                with open(caching_fisherinfo_filename, 'w') as filecache_out:
                    data_cache = dict(result_fisherinfo_mindist_sigmax_ratio=result_fisherinfo_mindist_sigmax_ratio)
                    pickle.dump(data_cache, filecache_out, protocol=2)
            except IOError:
                print "Error writing out to caching file ", caching_fisherinfo_filename


    if plot_per_min_dist_all:
        # Do one plot per min distance.
        for min_dist_i, min_dist in enumerate(enforce_min_distance_space):
            # Show log precision
            utils.pcolor_2d_data(result_all_precisions_mean[min_dist_i].T, x=ratio_space, y=sigmax_space, xlabel='ratio', ylabel='sigma_x', title='Precision, min_dist=%.3f' % min_dist)
            if savefigs:
                dataio.save_current_figure('precision_permindist_mindist%.2f_ratiosigmax_{label}_{unique_id}.pdf' % min_dist)

            # Show log precision
            utils.pcolor_2d_data(result_all_precisions_mean[min_dist_i].T, x=ratio_space, y=sigmax_space, xlabel='ratio', ylabel='sigma_x', title='Precision, min_dist=%.3f' % min_dist, log_scale=True)
            if savefigs:
                dataio.save_current_figure('logprecision_permindist_mindist%.2f_ratiosigmax_{label}_{unique_id}.pdf' % min_dist)


            # Plot estimated model precision
            utils.pcolor_2d_data(result_em_fits_mean[min_dist_i, ..., 0].T, x=ratio_space, y=sigmax_space, xlabel='ratio', ylabel='sigma_x', title='EM precision, min_dist=%.3f' % min_dist, log_scale=False)
            if savefigs:
                dataio.save_current_figure('logemprecision_permindist_mindist%.2f_ratiosigmax_{label}_{unique_id}.pdf' % min_dist)

            # Plot estimated Target, nontarget and random mixture components, in multiple subplots
            _, axes = plt.subplots(1, 3, figsize=(18, 6))
            plt.subplots_adjust(left=0.05, right=0.97, wspace = 0.3, bottom=0.15)
            utils.pcolor_2d_data(result_em_fits_mean[min_dist_i, ..., 1].T, x=ratio_space, y=sigmax_space, xlabel='ratio', ylabel='sigma_x', title='Target, min_dist=%.3f' % min_dist, log_scale=False, ax_handle=axes[0], ticks_interpolate=5)
            utils.pcolor_2d_data(result_em_fits_mean[min_dist_i, ..., 2].T, x=ratio_space, y=sigmax_space, xlabel='ratio', ylabel='sigma_x', title='Nontarget, min_dist=%.3f' % min_dist, log_scale=False, ax_handle=axes[1], ticks_interpolate=5)
            utils.pcolor_2d_data(result_em_fits_mean[min_dist_i, ..., 3].T, x=ratio_space, y=sigmax_space, xlabel='ratio', ylabel='sigma_x', title='Random, min_dist=%.3f' % min_dist, log_scale=False, ax_handle=axes[2], ticks_interpolate=5)

            if savefigs:
                dataio.save_current_figure('em_mixtureprobs_permindist_mindist%.2f_ratiosigmax_{label}_{unique_id}.pdf' % min_dist)

            # Plot Log-likelihood of Mixture model, sanity check
            utils.pcolor_2d_data(result_em_fits_mean[min_dist_i, ..., -1].T, x=ratio_space, y=sigmax_space, xlabel='ratio', ylabel='sigma_x', title='EM loglik, min_dist=%.3f' % min_dist, log_scale=False)
            if savefigs:
                dataio.save_current_figure('em_loglik_permindist_mindist%.2f_ratiosigmax_{label}_{unique_id}.pdf' % min_dist)

    if specific_plots_paper:
        # We need to choose 3 levels of min_distances
        target_sigmax = 0.25
        target_mindist_low = 0.15
        target_mindist_medium = 0.36
        target_mindist_high = 1.5

        sigmax_level_i = np.argmin(np.abs(sigmax_space - target_sigmax))
        min_dist_level_low_i = np.argmin(np.abs(enforce_min_distance_space - target_mindist_low))
        min_dist_level_medium_i = np.argmin(np.abs(enforce_min_distance_space - target_mindist_medium))
        min_dist_level_high_i = np.argmin(np.abs(enforce_min_distance_space - target_mindist_high))

        ## Do for each distance
        # for min_dist_i in [min_dist_level_low_i, min_dist_level_medium_i, min_dist_level_high_i]:
        for min_dist_i in xrange(enforce_min_distance_space.size):
            # Plot precision
            if False:
                utils.plot_mean_std_area(ratio_space, result_all_precisions_mean[min_dist_i, sigmax_level_i], result_all_precisions_std[min_dist_i, sigmax_level_i]) #, xlabel='Ratio conjunctivity', ylabel='Precision of recall')
                # plt.title('Min distance %.3f' % enforce_min_distance_space[min_dist_i])
                plt.ylim([0, np.max(result_all_precisions_mean[min_dist_i, sigmax_level_i] + result_all_precisions_std[min_dist_i, sigmax_level_i])])

                if savefigs:
                    dataio.save_current_figure('mindist%.2f_precisionrecall_forpaper_{label}_{unique_id}.pdf' % enforce_min_distance_space[min_dist_i])

            # Plot kappa fitted
            ax_handle = utils.plot_mean_std_area(ratio_space, result_em_fits_mean[min_dist_i, sigmax_level_i, :, 0], result_em_fits_std[min_dist_i, sigmax_level_i, :, 0]) #, xlabel='Ratio conjunctivity', ylabel='Fitted kappa')
            # Add distance between items in kappa units
            dist_items_kappa = utils.stddev_to_kappa(enforce_min_distance_space[min_dist_i])
            ax_handle.plot(ratio_space, dist_items_kappa*np.ones(ratio_space.size), 'k--', linewidth=3)
            plt.ylim([-0.1, np.max((np.max(result_em_fits_mean[min_dist_i, sigmax_level_i, :, 0] + result_em_fits_std[min_dist_i, sigmax_level_i, :, 0]), 1.1*dist_items_kappa))])
            # plt.title('Min distance %.3f' % enforce_min_distance_space[min_dist_i])
            if savefigs:
                dataio.save_current_figure('mindist%.2f_emkappa_forpaper_{label}_{unique_id}.pdf' % enforce_min_distance_space[min_dist_i])

            # Plot kappa-stddev fitted. Easier to visualize
            ax_handle = utils.plot_mean_std_area(ratio_space, result_em_kappastddev_mean[min_dist_i, sigmax_level_i], result_em_kappastddev_std[min_dist_i, sigmax_level_i]) #, xlabel='Ratio conjunctivity', ylabel='Fitted kappa_stddev')
            # Add distance between items in std dev units
            dist_items_std = (enforce_min_distance_space[min_dist_i])
            ax_handle.plot(ratio_space, dist_items_std*np.ones(ratio_space.size), 'k--', linewidth=3)
            # plt.title('Min distance %.3f' % enforce_min_distance_space[min_dist_i])
            plt.ylim([0, 1.1*np.max((np.max(result_em_kappastddev_mean[min_dist_i, sigmax_level_i] + result_em_kappastddev_std[min_dist_i, sigmax_level_i]), dist_items_std))])
            if savefigs:
                dataio.save_current_figure('mindist%.2f_emkappastddev_forpaper_{label}_{unique_id}.pdf' % enforce_min_distance_space[min_dist_i])


            if False:
                # Plot LLH
                utils.plot_mean_std_area(ratio_space, result_em_fits_mean[min_dist_i, sigmax_level_i, :, -1], result_em_fits_std[min_dist_i, sigmax_level_i, :, -1]) #, xlabel='Ratio conjunctivity', ylabel='Loglikelihood of Mixture model fit')
                # plt.title('Min distance %.3f' % enforce_min_distance_space[min_dist_i])
                if savefigs:
                    dataio.save_current_figure('mindist%.2f_emllh_forpaper_{label}_{unique_id}.pdf' % enforce_min_distance_space[min_dist_i])

                # Plot mixture parameters, std
                utils.plot_multiple_mean_std_area(ratio_space, result_em_fits_mean[min_dist_i, sigmax_level_i, :, 1:4].T, result_em_fits_std[min_dist_i, sigmax_level_i, :, 1:4].T)
                plt.ylim([0.0, 1.1])
                # plt.title('Min distance %.3f' % enforce_min_distance_space[min_dist_i])
                # plt.legend("Target", "Non-target", "Random")
                if savefigs:
                    dataio.save_current_figure('mindist%.2f_emprobs_forpaper_{label}_{unique_id}.pdf' % enforce_min_distance_space[min_dist_i])

                # Mixture parameters, SEM
                utils.plot_multiple_mean_std_area(ratio_space, result_em_fits_mean[min_dist_i, sigmax_level_i, :, 1:4].T, result_em_fits_std[min_dist_i, sigmax_level_i, :, 1:4].T/np.sqrt(nb_repetitions))
                plt.ylim([0.0, 1.1])
                # plt.title('Min distance %.3f' % enforce_min_distance_space[min_dist_i])
                # plt.legend("Target", "Non-target", "Random")
                if savefigs:
                    dataio.save_current_figure('mindist%.2f_emprobs_forpaper_sem_{label}_{unique_id}.pdf' % enforce_min_distance_space[min_dist_i])

    if plots_emfit_allitems:
        # We need to choose 3 levels of min_distances
        target_sigmax = 0.25
        target_mindist_low = 0.15
        target_mindist_medium = 0.36
        target_mindist_high = 1.5

        sigmax_level_i = np.argmin(np.abs(sigmax_space - target_sigmax))
        min_dist_level_low_i = np.argmin(np.abs(enforce_min_distance_space - target_mindist_low))
        min_dist_level_medium_i = np.argmin(np.abs(enforce_min_distance_space - target_mindist_medium))
        min_dist_level_high_i = np.argmin(np.abs(enforce_min_distance_space - target_mindist_high))

        min_dist_i_plotting_space = np.array([min_dist_level_low_i, min_dist_level_medium_i, min_dist_level_high_i])

        if should_fit_allitems_model:

            # kappa, mixt_target, mixt_nontargets (K), mixt_random, LL, bic
            # result_emfitallitems = np.empty((min_dist_i_plotting_space.size, ratio_space.size, 2*K+5))*np.nan
            result_emfitallitems = np.empty((enforce_min_distance_space.size, ratio_space.size, K+5))*np.nan

            ## Do for each distance
            # for min_dist_plotting_i, min_dist_i in enumerate(min_dist_i_plotting_space):
            for min_dist_i in xrange(enforce_min_distance_space.size):
                # Fit the mixture model
                for ratio_i, ratio in enumerate(ratio_space):
                    print "Refitting EM all items. Ratio:", ratio, "Dist:", enforce_min_distance_space[min_dist_i]

                    if mixturemodel_to_use == 'allitems_uniquekappa':
                        em_fit = em_circularmixture_allitems_uniquekappa.fit(
                            result_responses_all[min_dist_i, sigmax_level_i, ratio_i].flatten(),
                            result_target_all[min_dist_i, sigmax_level_i, ratio_i].flatten(),
                            result_nontargets_all[min_dist_i, sigmax_level_i, ratio_i].transpose((0, 2, 1)).reshape((N*nb_repetitions, K)))
                    elif mixturemodel_to_use == 'allitems_fikappa':
                        em_fit = em_circularmixture_allitems_kappafi.fit(result_responses_all[min_dist_i, sigmax_level_i, ratio_i].flatten(),
                            result_target_all[min_dist_i, sigmax_level_i, ratio_i].flatten(),
                            result_nontargets_all[min_dist_i, sigmax_level_i, ratio_i].transpose((0, 2, 1)).reshape((N*nb_repetitions, K)),
                            kappa=result_fisherinfo_mindist_sigmax_ratio[min_dist_i, sigmax_level_i, ratio_i])
                    else:
                        raise ValueError("Wrong mixturemodel_to_use, %s" % mixturemodel_to_use)

                    result_emfitallitems[min_dist_i, ratio_i] = [em_fit['kappa'], em_fit['mixt_target']] + em_fit['mixt_nontargets'].tolist() + [em_fit[key] for key in ('mixt_random', 'train_LL', 'bic')]

            # Save everything to a file, for faster later plotting
            if caching_emfit_filename is not None:
                try:
                    with open(caching_emfit_filename, 'w') as filecache_out:
                        data_em = dict(result_emfitallitems=result_emfitallitems, target_sigmax=target_sigmax)
                        pickle.dump(data_em, filecache_out, protocol=2)
                except IOError:
                    print "Error writing out to caching file ", caching_emfit_filename


        ## Plots now, for each distance!
        # for min_dist_plotting_i, min_dist_i in enumerate(min_dist_i_plotting_space):
        for min_dist_i in xrange(enforce_min_distance_space.size):

            # Plot now
            _, ax = plt.subplots()
            ax.plot(ratio_space, result_emfitallitems[min_dist_i, :, 1:5], linewidth=3)
            plt.ylim([0.0, 1.1])
            plt.legend(['Target', 'Nontarget 1', 'Nontarget 2', 'Random'], loc='upper left')

            if savefigs:
                dataio.save_current_figure('mindist%.2f_emprobsfullitems_{label}_{unique_id}.pdf' % enforce_min_distance_space[min_dist_i])

    if plot_min_distance_effect:
        conj_receptive_field_size = 2.*np.pi/((all_args[0]['M']*ratio_space)**0.5)

        target_vs_nontargets_mindist_ratio = result_emfitallitems[..., 1]/np.sum(result_emfitallitems[..., 1:4], axis=-1)
        nontargetsmean_vs_targnontarg_mindist_ratio = np.mean(result_emfitallitems[..., 2:4]/np.sum(result_emfitallitems[..., 1:4], axis=-1)[..., np.newaxis], axis=-1)

        for ratio_conj_i, ratio_conj in enumerate(ratio_space):
            # Do one plot per ratio, putting the receptive field size on each
            f, ax = plt.subplots()

            ax.plot(enforce_min_distance_space[1:], target_vs_nontargets_mindist_ratio[1:, ratio_conj_i], linewidth=3, label='target mixture')
            ax.plot(enforce_min_distance_space[1:], nontargetsmean_vs_targnontarg_mindist_ratio[1:, ratio_conj_i], linewidth=3, label='non-target mixture')
            # ax.plot(enforce_min_distance_space[1:], result_emfitallitems[1:, ratio_conj_i, 1:5], linewidth=3)

            ax.axvline(x=conj_receptive_field_size[ratio_conj_i]/2., color='k', linestyle='--', linewidth=2)
            ax.axvline(x=conj_receptive_field_size[ratio_conj_i]*2., color='r', linestyle='--', linewidth=2)

            plt.legend(loc='upper left')
            plt.grid()
            # ax.set_xlabel('Stimuli separation')
            # ax.set_ylabel('Ratio Target to Non-targets')
            plt.axis('tight')
            ax.set_ylim([0.0, 1.0])
            ax.set_xlim([enforce_min_distance_space[1:].min(), enforce_min_distance_space[1:].max()])

            if savefigs:
                dataio.save_current_figure('ratio%.2f_mindistpred_ratiotargetnontarget_{label}_{unique_id}.pdf' % ratio_conj)


    if compute_bootstraps:
        ## Bootstrap evaluation

        # We need to choose 3 levels of min_distances
        target_sigmax = 0.25
        target_mindist_low = 0.15
        target_mindist_medium = 0.5
        target_mindist_high = 1.

        sigmax_level_i = np.argmin(np.abs(sigmax_space - target_sigmax))
        min_dist_level_low_i = np.argmin(np.abs(enforce_min_distance_space - target_mindist_low))
        min_dist_level_medium_i = np.argmin(np.abs(enforce_min_distance_space - target_mindist_medium))
        min_dist_level_high_i = np.argmin(np.abs(enforce_min_distance_space - target_mindist_high))

        # cache_bootstrap_fn = os.path.join(generator_module.pbs_submission_infos['simul_out_dir'], 'outputs', 'cache_bootstrap.pickle')
        cache_bootstrap_fn = '/Users/loicmatthey/Dropbox/UCL/1-phd/Work/Visual_working_memory/code/git-bayesian-visual-working-memory/Experiments/specific_stimuli/specific_stimuli_corrected_mixed_sigmaxmindistance_autoset_repetitions5mult_collectall_281113_outputs/cache_bootstrap.pickle'
        try:
            with open(cache_bootstrap_fn, 'r') as file_in:
                # Load and assign values
                cached_data = pickle.load(file_in)
                bootstrap_ecdf_bays_sigmax_T = cached_data['bootstrap_ecdf_bays_sigmax_T']
                bootstrap_ecdf_allitems_sum_sigmax_T = cached_data['bootstrap_ecdf_allitems_sum_sigmax_T']
                bootstrap_ecdf_allitems_all_sigmax_T = cached_data['bootstrap_ecdf_allitems_all_sigmax_T']
                should_fit_bootstrap = False

        except IOError:
            print "Error while loading ", cache_bootstrap_fn

        ratio_i = 0

        # bootstrap_allitems_nontargets_allitems_uniquekappa = em_circularmixture_allitems_uniquekappa.bootstrap_nontarget_stat(
        # result_responses_all[min_dist_level_low_i, sigmax_level_i, ratio_i].flatten(),
        # result_target_all[min_dist_level_low_i, sigmax_level_i, ratio_i].flatten(),
        # result_nontargets_all[min_dist_level_low_i, sigmax_level_i, ratio_i].transpose((0, 2, 1)).reshape((N*nb_repetitions, K)),
        # sumnontargets_bootstrap_ecdf=bootstrap_ecdf_allitems_sum_sigmax_T[sigmax_level_i][K]['ecdf'],
        # allnontargets_bootstrap_ecdf=bootstrap_ecdf_allitems_all_sigmax_T[sigmax_level_i][K]['ecdf']

        # TODO FINISH HERE

    variables_to_save = ['nb_repetitions']

    if savedata:
        dataio.save_variables_default(locals(), variables_to_save)

        dataio.make_link_output_to_dropbox(dropbox_current_experiment_folder='specific_stimuli')


    plt.show()


    return locals()



this_file = inspect.getfile(inspect.currentframe())

parameters_entryscript=dict(action_to_do='launcher_do_reload_constrained_parameters', output_directory='.')

generator_script = 'generator' + re.split("^reloader", os.path.split(this_file)[-1])[-1]
# generator_script = 'generator_specific_stimuli_mixed_fixedemfit_otherrange_201113.py'

print "Reloader data generated from ", generator_script

generator_module = imp.load_source(os.path.splitext(generator_script)[0], generator_script)
dataset_infos = dict(label='See patterns of errors on Specific Stimuli, with Mixed population code. Internally vary ratio_conj. Vary sigmax and enforce_min_distance here. Did collect all responses for these, need to fit Mixture models',
                     files="%s/%s*.npy" % (generator_module.pbs_submission_infos['simul_out_dir'], generator_module.pbs_submission_infos['other_options']['label'].split('{')[0]),
                     launcher_module=generator_module,
                     loading_type='args',
                     parameters=['enforce_min_distance', 'sigmax'],
                     variables_to_load=['result_all_precisions', 'result_em_fits', 'result_em_resp', 'result_responses', 'result_target', 'result_nontargets'],
                     variables_description=['Precision of recall', 'Fits mixture model', 'Responsibilities mixture model', 'Responses', 'Target', 'Non-targets'],
                     post_processing=plots_specific_stimuli_mixed,
                     save_output_filename='plots_specificstimuli_mixed',
                     concatenate_multiple_datasets=True
                     )

if __name__ == '__main__':

    print "Running ", this_file

    arguments_dict=dict(parameters_filename=this_file)
    arguments_dict.update(parameters_entryscript)
    experiment_launcher = ExperimentLauncher(run=True, arguments_dict=arguments_dict)

    variables_to_reinstantiate = ['data_gen', 'sampler', 'stat_meas', 'random_network', 'args', 'constrained_parameters', 'data_pbs', 'dataio', 'post_processing_outputs', 'fit_exp']

    if 'variables_to_save' in experiment_launcher.all_vars:
        # Also reinstantiate the variables we saved
        variables_to_reinstantiate.extend(experiment_launcher.all_vars['variables_to_save'])

    for var_reinst in variables_to_reinstantiate:
        if var_reinst in experiment_launcher.all_vars:
            vars()[var_reinst] = experiment_launcher.all_vars[var_reinst]

    for var_reinst in post_processing_outputs:
        vars()[var_reinst] = post_processing_outputs[var_reinst]

