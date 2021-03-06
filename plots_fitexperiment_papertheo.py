#!/usr/bin/env python
# encoding: utf-8

import numpy as np
import matplotlib.pyplot as plt
import progress
import utils
import scipy.stats as spst
import pycircstat
import warnings

# plt.rcParams['font.size'] = 24


class PlotsFitExperimentAllTPaperTheo(object):
    """
        This class does all plots as in our PLOSCB2015 paper, for new
        FitExperimentAllT instances.

    """
    def __init__(self, fit_experiment_allt,
                 do_distrib_errors_fig5=True,
                 do_memcurves_fig6=True,
                 do_mixtcurves_fig13=True,
                 do_distrib_errors_data_fig2=True,
                 ):

        self.fit_exp = fit_experiment_allt
        self.experiment_id = self.fit_exp.experiment_id

        self.result_em_fits_stats = None
        self.do_distrib_errors_fig5 = do_distrib_errors_fig5
        self.do_memcurves_fig6 = do_memcurves_fig6
        self.do_mixtcurves_fig13 = do_mixtcurves_fig13
        self.do_distrib_errors_data_fig2 = do_distrib_errors_data_fig2

        print "Doing Paper plots for %s. \nFig5 %d, Fig6 %d, Fig13 %d" % (
            self.experiment_id,
            self.do_distrib_errors_fig5,
            self.do_memcurves_fig6,
            self.do_mixtcurves_fig13
        )


    def do_plots(self):
        '''
            Do all plots for that FitExperimentAllT.

            These correspond to a particular experiment_id only, not multiple.
        '''
        if self.do_distrib_errors_data_fig2:
            self.plots_distrib_errors_data_fig2()
        if self.do_distrib_errors_fig5:
            self.plots_distrib_errors_fig5()
        if self.do_memcurves_fig6 or self.do_mixtcurves_fig13:
            self.plots_memmixtcurves_fig6fig13()


    def plots_distrib_errors_data_fig2(self, size=6):
        '''
            HUMAN DATA for Fig5
            Same as plots_distrib_errors_fig5, but for the Experimental data

            Series of plots reproducing Fig 2 - Distribution of errors in human subjects
        '''
        f, axes = plt.subplots(nrows=2,
                               ncols=self.fit_exp.T_space.size,
                               figsize=(2*size, size)
                               )

        for t_i, T in enumerate(self.fit_exp.T_space):
            print "DATA T %d" % T

            self.fit_exp.setup_experimental_stimuli_T(T)
            self.fit_exp.restore_responses('human')

            self.fit_exp.sampler.plot_histogram_errors(bins=41, ax_handle=axes[0, t_i], norm='density')
            axes[0, t_i].set_title('')
            axes[0, t_i].set_ylim((0, 2))

            if T > 1:
                self.fit_exp.sampler.plot_histogram_bias_nontarget(bins=41, ax_handle=axes[1, t_i], show_parameters=False)
                axes[1, t_i].set_title('')
                axes[1, t_i].set_ylim((0, 0.3))
            else:
                axes[1, t_i].axis('off')

        f.suptitle('Fig2 - Human distribution errors', y=0.95)
        return axes


    def plots_distrib_errors_fig5(self, size=6):
        '''
            Series of plots reproducing Fig 5 - Distribution of errors of the
            model

            Arranged as in the paper.
        '''

        f, axes = plt.subplots(nrows=2,
                               ncols=self.fit_exp.T_space.size,
                               figsize=(2*size, size)
                               )

        for t_i, T in enumerate(self.fit_exp.T_space):
            print "MODEL T %d" % T

            self.fit_exp.setup_experimental_stimuli_T(T)
            if 'samples' in self.fit_exp.get_names_stored_responses():
                self.fit_exp.restore_responses('samples')
            else:
                self.fit_exp.sampler.force_sampling_round()
                self.fit_exp.store_responses('samples')

            self.fit_exp.sampler.plot_histogram_errors(bins=41, ax_handle=axes[0, t_i], norm='density')
            axes[0, t_i].set_title('')
            axes[0, t_i].set_ylim((0, 2))

            if T > 1:
                self.fit_exp.sampler.plot_histogram_bias_nontarget(bins=41, ax_handle=axes[1, t_i], show_parameters=False)
                axes[1, t_i].set_title('')
                axes[1, t_i].set_ylim((0, 0.3))
            else:
                axes[1, t_i].axis('off')

        f.suptitle('Fig5 - Model distribution errors', y=0.95)
        return axes


    def plots_KS_comparison_fig2fig5(self,
                                     bins=41,
                                     show_pval=True,
                                     size=6
                                     ):
        '''
            Will plot the ECDF of data/samples and then do Kolmogorov-Smirnov /Kuiper 2-samples tests on them.
        '''

        f, axes = plt.subplots(nrows=2,
                               ncols=self.fit_exp.T_space.size,
                               figsize=(size*2, size)
                               )

        result_KS = dict(human=dict(),
                         model=dict(),
                         ks_pval=dict(),
                         kuiper_pval=dict()
                         )

        warnings.simplefilter("ignore")

        for t_i, T in enumerate(self.fit_exp.T_space):
            result_KS['ks_pval'][T] = dict()
            result_KS['kuiper_pval'][T] = dict()

            self.fit_exp.setup_experimental_stimuli_T(T)

            # Human histograms and CDF
            self.fit_exp.restore_responses('human')
            result_KS['human'][T] = self.fit_exp.sampler.compute_errors_alltargets_histograms(bins=bins)

            # Samples histograms and CDF
            if 'samples' in self.fit_exp.get_names_stored_responses():
                self.fit_exp.restore_responses('samples')
            else:
                self.fit_exp.sampler.force_sampling_round()
                self.fit_exp.store_responses('samples')
            result_KS['model'][T] = self.fit_exp.sampler.compute_errors_alltargets_histograms(bins=bins)

            # Compute K-S 2-samples tests stats
            for condition in ['targets', 'nontargets']:
                if condition in result_KS['human'][T]:
                    ks_out = spst.ks_2samp(
                        result_KS['human'][T][condition]['samples'],
                        result_KS['model'][T][condition]['samples']
                    )

                    result_KS['ks_pval'][T][condition] = \
                        ks_out.pvalue

                    result_KS['kuiper_pval'][T][condition] = \
                        pycircstat.tests.kuiper(
                            result_KS['human'][T][condition]['samples'],
                            result_KS['model'][T][condition]['samples'])[0][0]

            ### Plot everything
            axes[0, t_i].plot(result_KS['human'][T]['targets']['x'],
                              result_KS['human'][T]['targets']['ecdf'],
                              label='data'
                              )
            axes[0, t_i].plot(result_KS['model'][T]['targets']['x'],
                              result_KS['model'][T]['targets']['ecdf'],
                              label='model'
                              )
            axes[0, t_i].set_title('')
            axes[0, t_i].set_xlim((-np.pi, np.pi))
            # axes[0, t_i].set_ylim((0, 2))

            if show_pval:
                axes[0, t_i].text(
                    0.02, 0.99,
                    "KS p: %.2f" % result_KS['ks_pval'][T]['targets'],
                    transform=axes[0, t_i].transAxes,
                    horizontalalignment='left',
                    verticalalignment='top'
                )
                axes[0, t_i].text(
                    0.02, 0.9,
                    "Kuiper p: %.2f" % result_KS['kuiper_pval'][T]['targets'],
                    transform=axes[0, t_i].transAxes,
                    horizontalalignment='left',
                    verticalalignment='top'
                )

            if T > 1:
                axes[1, t_i].plot(result_KS['human'][T]['nontargets']['x'],
                                  result_KS['human'][T]['nontargets']['ecdf'],
                                  label='data'
                                  )
                axes[1, t_i].plot(result_KS['model'][T]['nontargets']['x'],
                                  result_KS['model'][T]['nontargets']['ecdf'],
                                  label='model'
                                  )
                axes[1, t_i].set_title('')
                axes[1, t_i].set_xlim((-np.pi, np.pi))

                if show_pval:
                    axes[1, t_i].text(
                        0.02, 0.99,
                        "KS p: %.2f" % result_KS['ks_pval'][T]['nontargets'],
                        transform=axes[1, t_i].transAxes,
                        horizontalalignment='left',
                        verticalalignment='top'
                    )
                    axes[1, t_i].text(
                        0.02, 0.9,
                        "Kuiper p: %.2f" % result_KS['kuiper_pval'][T]['nontargets'],
                        transform=axes[1, t_i].transAxes,
                        horizontalalignment='left',
                        verticalalignment='top'
                    )
            else:
                axes[1, t_i].axis('off')

        axes[1, 1].legend(loc='center',
                          bbox_to_anchor=(0.5, 0.5),
                          bbox_transform=axes[1, 0].transAxes
                          )

        f.suptitle('ECDF between human and model')

        return axes, result_KS



    def plots_memmixtcurves_fig6fig13(self,
                                      num_repetitions=1,
                                      use_cache=True,
                                      layout='vertical',
                                      size=6
                                      ):
        '''
            Plots the memory fidelity for all T and the mixture proportions for all T
        '''

        if self.result_em_fits_stats is None or not use_cache:
            search_progress = progress.Progress(self.fit_exp.T_space.size*num_repetitions)

            # kappa, mixt_target, mixt_nontarget, mixt_random, ll
            result_em_fits = np.nan*np.ones((self.fit_exp.T_space.size, 5, num_repetitions))

            for T_i, T in enumerate(self.fit_exp.T_space):
                self.fit_exp.setup_experimental_stimuli_T(T)

                for repet_i in xrange(num_repetitions):
                    print "%.2f%%, %s left - %s" % (search_progress.percentage(), search_progress.time_remaining_str(), search_progress.eta_str())
                    print "Fit for T=%d, %d/%d" % (T, repet_i+1, num_repetitions)

                    if 'samples' in self.fit_exp.get_names_stored_responses() and repet_i < 1:
                        self.fit_exp.restore_responses('samples')
                    else:
                        self.fit_exp.sampler.force_sampling_round()
                        self.fit_exp.store_responses('samples')

                    # Fit mixture model
                    curr_params_fit = self.fit_exp.sampler.fit_mixture_model(use_all_targets=False)
                    result_em_fits[T_i, :, repet_i] = [curr_params_fit[key]
                        for key in ('kappa', 'mixt_target',
                                    'mixt_nontargets_sum', 'mixt_random',
                                    'train_LL')]

                    search_progress.increment()

            # Get stats of EM Fits
            self.result_em_fits_stats = dict(
                mean=utils.nanmean(result_em_fits, axis=-1),
                std=utils.nanstd(result_em_fits, axis=-1)
            )

        # Do the plots
        if self.do_memcurves_fig6 and self.do_mixtcurves_fig13:
            if layout == 'vertical':
                f, axes = plt.subplots(nrows=2, figsize=(size, size*2))
            else:
                f, axes = plt.subplots(ncols=2, figsize=(size*2, size))
        else:
            f, ax = plt.subplots(figsize=(size, size))
            axes = [ax]
        ax_i = 0

        if self.do_memcurves_fig6:
            self.__plot_memcurves(self.result_em_fits_stats,
                                  suptitle_text='Memory fidelity',
                                  ax=axes[ax_i]
                                  )
            ax_i += 1


        if self.do_mixtcurves_fig13:
            self.__plot_mixtcurves(self.result_em_fits_stats,
                                   suptitle_text='Mixture proportions',
                                   ax=axes[ax_i]
                                   )
            ax_i += 1

        return axes


    # Memory curve kappa
    def __plot_memcurves(self, model_em_fits, suptitle_text=None, ax=None):
        '''
            Nice plot for the memory fidelity, as in Fig6 of the paper theo

            Changes to using the subject fits if FitExperimentAllTSubject used.
        '''

        T_space = self.fit_exp.T_space
        data_em_fits = self.fit_exp.get_em_fits_arrays()

        if ax is None:
            _, ax = plt.subplots()
        else:
            ax.hold(False)

        ax = utils.plot_mean_std_area(
            T_space,
            data_em_fits['mean'][0],
            data_em_fits['std'][0],
            linewidth=3, fmt='o-', markersize=8,
            label='Data',
            ax_handle=ax
        )

        ax.hold(True)

        ax = utils.plot_mean_std_area(
            T_space,
            model_em_fits['mean'][..., 0],
            model_em_fits['std'][..., 0],
            xlabel='Number of items',
            ylabel="Memory error $[rad^{-2}]$",
            linewidth=3,
            fmt='o-', markersize=8,
            label='Model',
            ax_handle=ax
        )

        ax.legend(loc='upper right',
                  bbox_to_anchor=(1., 1.)
                  )
        ax.set_xlim([0.9, T_space.max()+0.1])
        ax.set_xticks(range(1, T_space.max()+1))
        ax.set_xticklabels(range(1, T_space.max()+1))

        if suptitle_text:
            ax.set_title(suptitle_text)
            # ax.get_figure().suptitle(suptitle_text)
        ax.hold(False)
        ax.get_figure().canvas.draw()

        return ax


    def __plot_mixtcurves(self, model_em_fits, suptitle_text=None, ax=None):
        '''
            Similar kind of plot, but showing the mixture proportions, as in Figure13
        '''
        T_space = self.fit_exp.T_space
        data_em_fits = self.fit_exp.get_em_fits_arrays()

        if ax is None:
            _, ax = plt.subplots()
        else:
            ax.hold(False)


        model_em_fits['mean'][np.isnan(model_em_fits['mean'])] = 0.0
        model_em_fits['std'][np.isnan(model_em_fits['std'])] = 0.0

        # Show model fits
        utils.plot_mean_std_area(
            T_space,
            model_em_fits['mean'][..., 1],
            model_em_fits['std'][..., 1],
            xlabel='Number of items',
            ylabel="Mixture probabilities",
            ax_handle=ax, linewidth=3, fmt='o-', markersize=5,
            label='Target',
        )
        ax.hold(True)
        utils.plot_mean_std_area(
            T_space,
            model_em_fits['mean'][..., 2],
            model_em_fits['std'][..., 2],
            xlabel='Number of items',
            ylabel="Mixture probabilities",
            ax_handle=ax, linewidth=3, fmt='o-', markersize=5,
            label='Nontarget'
        )
        utils.plot_mean_std_area(
            T_space,
            model_em_fits['mean'][..., 3],
            model_em_fits['std'][..., 3],
            xlabel='Number of items',
            ylabel="Mixture probabilities",
            ax_handle=ax, linewidth=3, fmt='o-', markersize=5,
            label='Random'
        )

        # Now data
        utils.plot_mean_std_area(
            T_space,
            data_em_fits['mean'][1],
            data_em_fits['std'][1],
            xlabel='Number of items',
            ylabel="Mixture probabilities",
            ax_handle=ax, linewidth=2, fmt='o--', markersize=5,
            label='Data target'
        )
        utils.plot_mean_std_area(
            T_space,
            data_em_fits['mean'][2],
            data_em_fits['std'][2],
            xlabel='Number of items',
            ylabel="Mixture probabilities",
            ax_handle=ax, linewidth=2, fmt='o--', markersize=5, label='Data nontarget'
        )
        utils.plot_mean_std_area(
            T_space,
            data_em_fits['mean'][3],
            data_em_fits['std'][3],
            xlabel='Number of items',
            ylabel="Mixture probabilities",
            ax_handle=ax, linewidth=2, fmt='o--', markersize=5, label='Data random'
        )

        ax.legend(loc='upper left',
                  bbox_to_anchor=(1., 1.)
                  )

        ax.set_xlim([0.9, T_space.max() + 0.1])
        ax.set_ylim([0.0, 1.1])
        ax.set_xticks(range(1, T_space.max() + 1))
        ax.set_xticklabels(range(1, T_space.max() + 1))

        if suptitle_text:
            ax.set_title(suptitle_text)
            # ax.get_figure().suptitle(suptitle_text)

        ax.get_figure().canvas.draw()

        ax.hold(False)

        return ax
