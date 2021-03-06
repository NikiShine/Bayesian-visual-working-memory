"""
    ExperimentDescriptor for Misbinding effect for Mixed population code.
"""

import os
import numpy as np
import matplotlib.pyplot as plt


import pypr.clustering.gmm as pygmm

import launchers

from experimentlauncher import *
from dataio import *
# from smooth import *
import inspect
import em_circularmixture
import em_circularmixture_allitems_uniquekappa
import em_circularmixture_allitems_kappafi

import cPickle as pickle

import utils

# # Commit @2042319 +

parameters_entryscript=dict(action_to_do='launcher_do_reload_constrained_parameters', output_directory='.')


def plots_misbinding_logposterior(data_pbs, generator_module=None):
    '''
        Reload 3D volume runs from PBS and plot them

    '''


    #### SETUP
    #
    savedata = False
    savefigs = True

    plot_logpost = False
    plot_error = False
    plot_mixtmodel = True
    plot_hist_responses_fisherinfo = True
    compute_plot_bootstrap = False
    compute_fisher_info_perratioconj = True

    # mixturemodel_to_use = 'original'
    mixturemodel_to_use = 'allitems'
    # mixturemodel_to_use = 'allitems_kappafi'

    caching_fisherinfo_filename = os.path.join(generator_module.pbs_submission_infos['simul_out_dir'], 'cache_fisherinfo.pickle')


    #
    #### /SETUP

    print "Order parameters: ", generator_module.dict_parameters_range.keys()

    result_all_log_posterior = np.squeeze(data_pbs.dict_arrays['result_all_log_posterior']['results'])
    result_all_thetas = np.squeeze(data_pbs.dict_arrays['result_all_thetas']['results'])

    ratio_space = data_pbs.loaded_data['parameters_uniques']['ratio_conj']

    print ratio_space
    print result_all_log_posterior.shape

    N = result_all_thetas.shape[-1]

    result_prob_wrong = np.zeros((ratio_space.size, N))
    result_em_fits = np.empty((ratio_space.size, 6))*np.nan

    all_args = data_pbs.loaded_data['args_list']

    fixed_means = [-np.pi*0.6, np.pi*0.6]
    all_angles = np.linspace(-np.pi, np.pi, result_all_log_posterior.shape[-1])

    dataio = DataIO(output_folder=generator_module.pbs_submission_infos['simul_out_dir'] + '/outputs/', label='global_' + dataset_infos['save_output_filename'])


    plt.rcParams['font.size'] = 18


    if plot_hist_responses_fisherinfo:

        # From cache
        if caching_fisherinfo_filename is not None:
            if os.path.exists(caching_fisherinfo_filename):
                # Got file, open it and try to use its contents
                try:
                    with open(caching_fisherinfo_filename, 'r') as file_in:
                        # Load and assign values
                        cached_data = pickle.load(file_in)
                        result_fisherinfo_ratio = cached_data['result_fisherinfo_ratio']
                        compute_fisher_info_perratioconj = False

                except IOError:
                    print "Error while loading ", caching_fisherinfo_filename, "falling back to computing the Fisher Info"

        if compute_fisher_info_perratioconj:
            # We did not save the Fisher info, but need it if we want to fit the mixture model with fixed kappa. So recompute them using the args_dicts

            result_fisherinfo_ratio = np.empty(ratio_space.shape)

            # Invert the all_args_i -> ratio_conj direction
            parameters_indirections = data_pbs.loaded_data['parameters_dataset_index']

            for ratio_conj_i, ratio_conj in enumerate(ratio_space):
                # Get index of first dataset with the current ratio_conj (no need for the others, I think)
                arg_index = parameters_indirections[(ratio_conj,)][0]

                # Now using this dataset, reconstruct a RandomFactorialNetwork and compute the fisher info
                curr_args = all_args[arg_index]

                curr_args['stimuli_generation'] = lambda T: np.linspace(-np.pi*0.6, np.pi*0.6, T)

                (random_network, data_gen, stat_meas, sampler) = launchers.init_everything(curr_args)

                # Theo Fisher info
                result_fisherinfo_ratio[ratio_conj_i] = sampler.estimate_fisher_info_theocov()

                del curr_args['stimuli_generation']

            # Save everything to a file, for faster later plotting
            if caching_fisherinfo_filename is not None:
                try:
                    with open(caching_fisherinfo_filename, 'w') as filecache_out:
                        data_cache = dict(result_fisherinfo_ratio=result_fisherinfo_ratio)
                        pickle.dump(data_cache, filecache_out, protocol=2)
                except IOError:
                    print "Error writing out to caching file ", caching_fisherinfo_filename

        # Now plots. Do histograms of responses (around -pi/6 and pi/6), add Von Mises derived from Theo FI on top, and vertical lines for the correct target/nontarget angles.
        for ratio_conj_i, ratio_conj in enumerate(ratio_space):
            # Histogram
            ax = utils.hist_angular_data(result_all_thetas[ratio_conj_i], bins=100, title='ratio %.2f, fi %.0f' % (ratio_conj, result_fisherinfo_ratio[ratio_conj_i]))
            bar_heights, _, _ = utils.histogram_binspace(result_all_thetas[ratio_conj_i], bins=100, norm='density')

            # Add Fisher info prediction on top
            x = np.linspace(-np.pi, np.pi, 1000)
            if result_fisherinfo_ratio[ratio_conj_i] < 700:
                # Von Mises PDF
                utils.plot_vonmises_pdf(x, utils.stddev_to_kappa(1./result_fisherinfo_ratio[ratio_conj_i]**0.5), mu=fixed_means[-1], ax_handle=ax, linewidth=3, color='r', scale=np.max(bar_heights), fmt='-')
            else:
                # Switch to Gaussian instead
                utils.plot_normal_pdf(x, mu=fixed_means[-1], std=1./result_fisherinfo_ratio[ratio_conj_i]**0.5, ax_handle=ax, linewidth=3, color='r', scale=np.max(bar_heights), fmt='-')

            # ax.set_xticks([])
            # ax.set_yticks([])

            # Add vertical line to correct target/nontarget
            ax.axvline(x=fixed_means[0], color='g', linewidth=2)
            ax.axvline(x=fixed_means[1], color='r', linewidth=2)

            ax.get_figure().canvas.draw()

            if savefigs:
                # plt.tight_layout()
                dataio.save_current_figure('results_misbinding_histresponses_vonmisespdf_ratioconj%.2f{label}_{unique_id}.pdf' % (ratio_conj))



    if plot_logpost:
        for ratio_conj_i, ratio_conj in enumerate(ratio_space):
            # ax = utils.plot_mean_std_area(all_angles, nanmean(result_all_log_posterior[ratio_conj_i], axis=0), nanstd(result_all_log_posterior[ratio_conj_i], axis=0))

            # ax.set_xlim((-np.pi, np.pi))
            # ax.set_xticks((-np.pi, -np.pi / 2, 0, np.pi / 2., np.pi))
            # ax.set_xticklabels((r'$-\pi$', r'$-\frac{\pi}{2}$', r'$0$', r'$\frac{\pi}{2}$', r'$\pi$'))
            # ax.set_yticks(())

            # ax.get_figure().canvas.draw()

            # if savefigs:
            #     dataio.save_current_figure('results_misbinding_logpost_ratioconj%.2f_{label}_global_{unique_id}.pdf' % ratio_conj)


            # Compute the probability of answering wrongly (from fitting mixture distrib onto posterior)
            for n in xrange(result_all_log_posterior.shape[1]):
                result_prob_wrong[ratio_conj_i, n], _, _ = utils.fit_gaussian_mixture_fixedmeans(all_angles, np.exp(result_all_log_posterior[ratio_conj_i, n]), fixed_means=fixed_means, normalise=True, return_fitted_data=False, should_plot=False)

        # ax = utils.plot_mean_std_area(ratio_space, nanmean(result_prob_wrong, axis=-1), nanstd(result_prob_wrong, axis=-1))
        plt.figure()
        plt.plot(ratio_space, utils.nanmean(result_prob_wrong, axis=-1))

        # ax.get_figure().canvas.draw()
        if savefigs:
            dataio.save_current_figure('results_misbinding_probwrongpost_allratioconj_{label}_global_{unique_id}.pdf')

    if plot_error:

        ## Compute Standard deviation/precision from samples and plot it as a function of ratio_conj
        stats = utils.compute_mean_std_circular_data(utils.wrap_angles(result_all_thetas - fixed_means[1]).T)

        f = plt.figure()
        plt.plot(ratio_space, stats['std'])
        plt.ylabel('Standard deviation [rad]')

        if savefigs:
            dataio.save_current_figure('results_misbinding_stddev_allratioconj_{label}_global_{unique_id}.pdf')

        f = plt.figure()
        plt.plot(ratio_space, utils.compute_angle_precision_from_std(stats['std'], square_precision=False), linewidth=2)
        plt.ylabel('Precision [$1/rad$]')
        plt.xlabel('Proportion of conjunctive units')
        plt.grid()

        if savefigs:
            dataio.save_current_figure('results_misbinding_precision_allratioconj_{label}_global_{unique_id}.pdf')

        ## Compute the probability of misbinding
        # 1) Just count samples < 0 / samples tot
        # 2) Fit a mixture model, average over mixture probabilities
        prob_smaller0 = np.sum(result_all_thetas <= 1, axis=1)/float(result_all_thetas.shape[1])

        em_centers = np.zeros((ratio_space.size, 2))
        em_covs = np.zeros((ratio_space.size, 2))
        em_pk = np.zeros((ratio_space.size, 2))
        em_ll = np.zeros(ratio_space.size)
        for ratio_conj_i, ratio_conj in enumerate(ratio_space):
            cen_lst, cov_lst, em_pk[ratio_conj_i], em_ll[ratio_conj_i] = pygmm.em(result_all_thetas[ratio_conj_i, np.newaxis].T, K = 2, max_iter = 400, init_kw={'cluster_init':'fixed', 'fixed_means': fixed_means})

            em_centers[ratio_conj_i] = np.array(cen_lst).flatten()
            em_covs[ratio_conj_i] = np.array(cov_lst).flatten()

        # print em_centers
        # print em_covs
        # print em_pk

        f = plt.figure()
        plt.plot(ratio_space, prob_smaller0)
        plt.ylabel('Misbound proportion')
        if savefigs:
            dataio.save_current_figure('results_misbinding_countsmaller0_allratioconj_{label}_global_{unique_id}.pdf')

        f = plt.figure()
        plt.plot(ratio_space, np.max(em_pk, axis=-1), 'g', linewidth=2)
        plt.ylabel('Mixture proportion, correct')
        plt.xlabel('Proportion of conjunctive units')
        plt.grid()
        if savefigs:
            dataio.save_current_figure('results_misbinding_emmixture_allratioconj_{label}_global_{unique_id}.pdf')


        # Put everything on one figure
        f = plt.figure(figsize=(10, 6))
        norm_for_plot = lambda x: (x - np.min(x))/np.max((x - np.min(x)))
        plt.plot(ratio_space, norm_for_plot(stats['std']), ratio_space, norm_for_plot(utils.compute_angle_precision_from_std(stats['std'], square_precision=False)), ratio_space, norm_for_plot(prob_smaller0), ratio_space, norm_for_plot(em_pk[:, 1]), ratio_space, norm_for_plot(em_pk[:, 0]))
        plt.legend(('Std dev', 'Precision', 'Prob smaller 1', 'Mixture proportion correct', 'Mixture proportion misbinding'))
        # plt.plot(ratio_space, norm_for_plot(compute_angle_precision_from_std(stats['std'], square_precision=False)), ratio_space, norm_for_plot(em_pk[:, 1]), linewidth=2)
        # plt.legend(('Precision', 'Mixture proportion correct'), loc='best')
        plt.grid()
        if savefigs:
            dataio.save_current_figure('results_misbinding_allmetrics_allratioconj_{label}_global_{unique_id}.pdf')


    if plot_mixtmodel:
        # Fit Paul's model
        target_angle = np.ones(N)*fixed_means[1]
        nontarget_angles = np.ones((N, 1))*fixed_means[0]

        for ratio_conj_i, ratio_conj in enumerate(ratio_space):
            print "Ratio: ", ratio_conj

            responses = result_all_thetas[ratio_conj_i]

            if mixturemodel_to_use == 'allitems_kappafi':
                curr_params_fit = em_circularmixture_allitems_kappafi.fit(responses, target_angle, nontarget_angles, kappa=result_fisherinfo_ratio[ratio_conj_i])
            elif mixturemodel_to_use == 'allitems':
                curr_params_fit = em_circularmixture_allitems_uniquekappa.fit(responses, target_angle, nontarget_angles)
            else:
                curr_params_fit = em_circularmixture.fit(responses, target_angle, nontarget_angles)

            result_em_fits[ratio_conj_i] = [curr_params_fit['kappa'], curr_params_fit['mixt_target']] + utils.arrnum_to_list(curr_params_fit['mixt_nontargets']) + [curr_params_fit[key] for key in ('mixt_random', 'train_LL', 'bic')]

            print curr_params_fit


        if False:
            f, ax = plt.subplots()
            ax2 = ax.twinx()

            # left axis, kappa
            ax = utils.plot_mean_std_area(ratio_space, result_em_fits[:, 0], 0*result_em_fits[:, 0], xlabel='Proportion of conjunctive units', ylabel="Inverse variance $[rad^{-2}]$", ax_handle=ax, linewidth=3, fmt='o-', markersize=8, label='Fitted kappa', color='k')

            # Right axis, mixture probabilities
            utils.plot_mean_std_area(ratio_space, result_em_fits[:, 1], 0*result_em_fits[:, 1], xlabel='Proportion of conjunctive units', ylabel="Mixture probabilities", ax_handle=ax2, linewidth=3, fmt='o-', markersize=8, label='Target')
            utils.plot_mean_std_area(ratio_space, result_em_fits[:, 2], 0*result_em_fits[:, 2], xlabel='Proportion of conjunctive units', ylabel="Mixture probabilities", ax_handle=ax2, linewidth=3, fmt='o-', markersize=8, label='Nontarget')
            utils.plot_mean_std_area(ratio_space, result_em_fits[:, 3], 0*result_em_fits[:, 3], xlabel='Proportion of conjunctive units', ylabel="Mixture probabilities", ax_handle=ax2, linewidth=3, fmt='o-', markersize=8, label='Random')

            lines, labels = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines + lines2, labels + labels2, fontsize=12, loc='right')

            # ax.set_xlim([0.9, 5.1])
            # ax.set_xticks(range(1, 6))
            # ax.set_xticklabels(range(1, 6))
            plt.grid()

            f.canvas.draw()

        if True:
            # Mixture probabilities
            ax = utils.plot_mean_std_area(ratio_space, result_em_fits[:, 1], 0*result_em_fits[:, 1], xlabel='Proportion of conjunctive units', ylabel="Mixture probabilities", linewidth=3, fmt='-', markersize=8, label='Target')
            utils.plot_mean_std_area(ratio_space, result_em_fits[:, 2], 0*result_em_fits[:, 2], xlabel='Proportion of conjunctive units', ylabel="Mixture probabilities", ax_handle=ax, linewidth=3, fmt='-', markersize=8, label='Nontarget')
            utils.plot_mean_std_area(ratio_space, result_em_fits[:, 3], 0*result_em_fits[:, 3], xlabel='Proportion of conjunctive units', ylabel="Mixture probabilities", ax_handle=ax, linewidth=3, fmt='-', markersize=8, label='Random')

            ax.legend(loc='right')

            # ax.set_xlim([0.9, 5.1])
            # ax.set_xticks(range(1, 6))
            # ax.set_xticklabels(range(1, 6))
            plt.grid()

            if savefigs:
                dataio.save_current_figure('results_misbinding_emmixture_allratioconj_{label}_global_{unique_id}.pdf')

        if True:
            # Kappa
            # ax = utils.plot_mean_std_area(ratio_space, result_em_fits[:, 0], 0*result_em_fits[:, 0], xlabel='Proportion of conjunctive units', ylabel="$\kappa [rad^{-2}]$", linewidth=3, fmt='-', markersize=8, label='Kappa')
            ax = utils.plot_mean_std_area(ratio_space, utils.kappa_to_stddev(result_em_fits[:, 0]), 0*result_em_fits[:, 2], xlabel='Proportion of conjunctive units', ylabel="Standard deviation [rad]", linewidth=3, fmt='-', markersize=8, label='Mixture model $\kappa$')

            # Add Fisher Info theo
            ax = utils.plot_mean_std_area(ratio_space, utils.kappa_to_stddev(result_fisherinfo_ratio), 0*result_em_fits[:, 2], xlabel='Proportion of conjunctive units', ylabel="Standard deviation [rad]", linewidth=3, fmt='-', markersize=8, label='Fisher Information', ax_handle=ax)

            ax.legend(loc='best')

            # ax.set_xlim([0.9, 5.1])
            # ax.set_xticks(range(1, 6))
            # ax.set_xticklabels(range(1, 6))
            plt.grid()

            if savefigs:
                dataio.save_current_figure('results_misbinding_kappa_allratioconj_{label}_global_{unique_id}.pdf')

    if compute_plot_bootstrap:
        ## Compute the bootstrap pvalue for each ratio
        #       use the bootstrap CDF from mixed runs, not the exact current ones, not sure if good idea.

        bootstrap_to_load = 1
        if bootstrap_to_load == 1:
            cache_bootstrap_fn = os.path.join(generator_module.pbs_submission_infos['simul_out_dir'], 'outputs', 'cache_bootstrap_mixed_from_bootstrapnontargets.pickle')
            bootstrap_ecdf_sum_label = 'bootstrap_ecdf_allitems_sum_sigmax_T'
            bootstrap_ecdf_all_label = 'bootstrap_ecdf_allitems_all_sigmax_T'
        elif bootstrap_to_load == 2:
            cache_bootstrap_fn = os.path.join(generator_module.pbs_submission_infos['simul_out_dir'], 'outputs', 'cache_bootstrap_misbinding_mixed.pickle')
            bootstrap_ecdf_sum_label = 'bootstrap_ecdf_allitems_sum_ratioconj'
            bootstrap_ecdf_all_label = 'bootstrap_ecdf_allitems_all_ratioconj'

        try:
            with open(cache_bootstrap_fn, 'r') as file_in:
                # Load and assign values
                cached_data = pickle.load(file_in)
                assert bootstrap_ecdf_sum_label in cached_data
                assert bootstrap_ecdf_all_label in cached_data
                should_fit_bootstrap = False

        except IOError:
            print "Error while loading ", cache_bootstrap_fn

        # Select the ECDF to use
        if bootstrap_to_load == 1:
            sigmax_i = 3    # corresponds to sigmax = 2, input here.
            T_i = 1         # two possible targets here.
            bootstrap_ecdf_sum_used = cached_data[bootstrap_ecdf_sum_label][sigmax_i][T_i]['ecdf']
            bootstrap_ecdf_all_used = cached_data[bootstrap_ecdf_all_label][sigmax_i][T_i]['ecdf']
        elif bootstrap_to_load == 2:
            ratio_conj_i = 4
            bootstrap_ecdf_sum_used = cached_data[bootstrap_ecdf_sum_label][ratio_conj_i]['ecdf']
            bootstrap_ecdf_all_used = cached_data[bootstrap_ecdf_all_label][ratio_conj_i]['ecdf']


        result_pvalue_bootstrap_sum = np.empty(ratio_space.size)*np.nan
        result_pvalue_bootstrap_all = np.empty((ratio_space.size, nontarget_angles.shape[-1]))*np.nan

        for ratio_conj_i, ratio_conj in enumerate(ratio_space):
            print "Ratio: ", ratio_conj

            responses = result_all_thetas[ratio_conj_i]

            bootstrap_allitems_nontargets_allitems_uniquekappa = em_circularmixture_allitems_uniquekappa.bootstrap_nontarget_stat(responses, target_angle, nontarget_angles,
                sumnontargets_bootstrap_ecdf=bootstrap_ecdf_sum_used,
                allnontargets_bootstrap_ecdf=bootstrap_ecdf_all_used)

            result_pvalue_bootstrap_sum[ratio_conj_i] = bootstrap_allitems_nontargets_allitems_uniquekappa['p_value']
            result_pvalue_bootstrap_all[ratio_conj_i] = bootstrap_allitems_nontargets_allitems_uniquekappa['allnontarget_p_value']

        ## Plots
        # f, ax = plt.subplots()
        # ax.plot(ratio_space, result_pvalue_bootstrap_all, linewidth=2)

        # if savefigs:
        #     dataio.save_current_figure("pvalue_bootstrap_all_ratioconj_{label}_{unique_id}.pdf")

        f, ax = plt.subplots()
        ax.plot(ratio_space, result_pvalue_bootstrap_sum, linewidth=2)
        plt.grid()

        if savefigs:
            dataio.save_current_figure("pvalue_bootstrap_sum_ratioconj_{label}_{unique_id}.pdf")


    # plt.figure()
    # plt.plot(ratio_MMlower, results_filtered_smoothed/np.max(results_filtered_smoothed, axis=0), linewidth=2)
    # plt.plot(ratio_MMlower[np.argmax(results_filtered_smoothed, axis=0)], np.ones(results_filtered_smoothed.shape[-1]), 'ro', markersize=10)
    # plt.grid()
    # plt.ylim((0., 1.1))
    # plt.subplots_adjust(right=0.8)
    # plt.legend(['%d item' % i + 's'*(i>1) for i in xrange(1, T+1)], loc='center right', bbox_to_anchor=(1.3, 0.5))
    # plt.xticks(np.linspace(0, 1.0, 5))

    variables_to_save = ['target_angle', 'nontarget_angles']

    if savedata:
        dataio.save_variables_default(locals(), variables_to_save)
        dataio.make_link_output_to_dropbox(dropbox_current_experiment_folder='misbindings')


    plt.show()

    return locals()




generator_script='generator_misbinding_mixed_varyratio_avgpostsamples_newlabel_210613.py'

generator_module = imp.load_source(os.path.splitext(generator_script)[0], generator_script)
dataset_infos = dict(label='Study misbindings, by computing an average posterior for fixed stimuli. Check the distribution of errors as well. Uses a Mixed population, vary ratio_conj to see what happens. Limit to squared ratio_subpop_nb only. Plots already done before, but lets try to redo them',
                     files="%s/%s*.npy" % (generator_module.pbs_submission_infos['simul_out_dir'], generator_module.pbs_submission_infos['other_options']['label'].split('{')[0]),
                     launcher_module=generator_module,
                     loading_type='args',
                     parameters=['ratio_conj'],
                     variables_to_load=['result_all_log_posterior', 'result_all_thetas'],
                     variables_description=['Log posterior for multiple ratio_conj'],
                     post_processing=plots_misbinding_logposterior,
                     save_output_filename='plots_misbinding_logposterior'
                     )




if __name__ == '__main__':

    this_file = inspect.getfile(inspect.currentframe())
    print "Running ", this_file

    arguments_dict=dict(parameters_filename=this_file)
    arguments_dict.update(parameters_entryscript)
    experiment_launcher = ExperimentLauncher(run=True, arguments_dict=arguments_dict)

    variables_to_reinstantiate = ['data_gen', 'sampler', 'stat_meas', 'random_network', 'args', 'constrained_parameters', 'data_pbs', 'dataio', 'post_processing_outputs']

    if 'variables_to_save' in experiment_launcher.all_vars:
        # Also reinstantiate the variables we saved
        variables_to_reinstantiate.extend(experiment_launcher.all_vars['variables_to_save'])

    for var_reinst in variables_to_reinstantiate:
        if var_reinst in experiment_launcher.all_vars:
            vars()[var_reinst] = experiment_launcher.all_vars[var_reinst]

    for var_reinst in post_processing_outputs:
        vars()[var_reinst] = post_processing_outputs[var_reinst]

