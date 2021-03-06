
import sys
import numpy as np
import scipy.io as sio
import matplotlib.pyplot as plt
# import matplotlib.patches as plt_patches
# import matplotlib.gridspec as plt_grid
import os
import os.path
import cPickle as pickle
# import bottleneck as bn
import em_circularmixture
import em_circularmixture_allitems_uniquekappa
import pandas as pd

import matplotlib.cm as cmx
import matplotlib.colors as mcolors
from mpl_toolkits.mplot3d import Axes3D

import dataio as DataIO

import utils


def plot_kappa_mean_error(T_space, mean, yerror, ax=None, dataio=None, title='',
                          **args):
    '''
        !!! IMPORTANT !!!

        Main plotting function to show the evolution of Kappa with T

        !!! IMPORTANT !!!
    '''

    if ax is None:
        f, ax = plt.subplots()

    ax = utils.plot_mean_std_area(
        T_space,
        mean,
        np.ma.masked_invalid(yerror).filled(0.0),
        ax_handle=ax,
        linewidth=3,
        markersize=8,
        fmt='o-',
        **args)

    ax.legend(prop={'size': 15}, loc='best')
    if title:
        ax.set_title('Kappa: %s' % title)
    ax.set_xlim([0.9, T_space.max()+0.1])
    ax.set_ylim([0.0, max(np.max(mean)*1.1, ax.get_ylim()[1])])
    ax.set_xticks(range(1, T_space.max()+1))
    ax.set_xticklabels(range(1, T_space.max()+1))
    ax.get_figure().canvas.draw()

    if dataio is not None:
        dataio.save_current_figure('%s_kappa_{label}_{unique_id}.pdf' % title)

    return ax


def plot_emmixture_mean_error(T_space, mean, yerror, ax=None, dataio=None,
                              title='', **args):
    '''
        !!! IMPORTANT !!!

        Main plotting function to show the evolution of an EM Mixture proportion with T

        !!! IMPORTANT !!!
    '''
    if ax is None:
        f, ax = plt.subplots()

    utils.plot_mean_std_area(T_space, mean, np.ma.masked_invalid(yerror).filled(0.0), ax_handle=ax, linewidth=3, fmt='o-', markersize=8, **args)

    ax.legend(prop={'size': 15}, loc='best')
    if title:
        ax.set_title('Mixture prop: %s' % title)
    ax.set_xlim([0.9, T_space.max() + 0.1])
    ax.set_ylim([0.0, 1.01])
    ax.set_xticks(range(1, T_space.max()+1))
    ax.set_xticklabels(range(1, T_space.max()+1))

    ax.get_figure().canvas.draw()

    if dataio is not None:
        dataio.save_current_figure('%s_mixtures_{label}_{unique_id}.pdf' % title)

    return ax



def plot_check_bias_nontarget(dataset, dataio=None):
    '''
        Get an histogram of the errors between the response and all non targets
            If biased towards 0-values, should indicate misbinding errors.

        (if you do this with respect to all targets, it's retarded and should always be biased)
    '''
    n_items_space = np.unique(dataset['n_items'])
    angle_space = np.linspace(-np.pi, np.pi, 20)

    # Get histograms of errors, per n_item
    for nitems_i in xrange(n_items_space.size):
        utils.hist_samples_density_estimation(dataset['errors_nitems'][nitems_i], bins=angle_space, title='%s N=%d' % (dataset['name'], n_items_space[nitems_i]), dataio=dataio, filename='hist_bias_targets_%ditems_{label}_{unique_id}.pdf' % (n_items_space[nitems_i]))

    # Get histograms of bias to nontargets. Do that by binning the errors to others nontargets of the array.
    utils.plot_hists_bias_nontargets(dataset['errors_all_nitems'][n_items_space>1], bins=20, dataio=dataio, label='allnontargets', remove_first_column=True)

    rayleigh = utils.rayleigh(dataset['errors_all_nitems'][n_items_space>1].flatten())
    v_test = utils.V_test(dataset['errors_all_nitems'][n_items_space>1].flatten())
    print rayleigh
    print v_test



def plot_check_bias_bestnontarget(dataset, dataio=None):
    '''
        Get an histogram of errors between response and best nontarget.
        Should be more biased towards 0 than the overall average
    '''
    n_items_space = np.unique(dataset['n_items'])

    # Compute the errors to the best non target
    errors_nontargets = dataset['errors_all_nitems'][n_items_space>1]
    errors_nontargets = np.array([errors_nontargets_nitem[~np.all(np.isnan(errors_nontargets_nitem), axis=1), :] for errors_nontargets_nitem in errors_nontargets])

    indices_bestnontarget = [np.nanargmin(np.abs(errors_nontargets[n_item_i][..., 1:]), axis=-1) for n_item_i in xrange(errors_nontargets.shape[0])]
    # indices_bestnontarget = np.nanargmin(np.abs(errors_nontargets), axis=2)

    # Index of the argmin of absolute error. Not too bad, easy to index into.
    errors_bestnontargets_nitems = np.array([ errors_nontargets[n_items_i][ xrange(errors_nontargets[n_items_i].shape[0]), indices_bestnontarget[n_items_i] + 1]   for n_items_i in xrange(errors_nontargets.shape[0]) ])

    # Show histograms per n_items, like in Bays2009 figure
    utils.plot_hists_bias_nontargets(errors_bestnontargets_nitems, bins=20, label='bestnontarget', dataio=dataio)



def plot_check_bias_nontarget_randomized(dataset, dataio=None):
    '''
        Plot the histogram of errors to nontargets, after replacing all nontargets by random angles.
        If show similar bias, would be indication of low predictive power of distribution of errors to nontargets.
    '''

    n_items_space = np.unique(dataset['n_items'])

    # Copy item_angles
    new_item_angles = dataset['item_angle'].copy()

    # Will resample multiple times
    errors_nitems_new_dict = dict()
    nb_resampling = 100

    for resampling_i in xrange(nb_resampling):

        # Replace nontargets randomly
        nontarget_indices = np.nonzero(~np.isnan(new_item_angles[:, 1:]))
        new_item_angles[nontarget_indices[0], nontarget_indices[1]+1] = 2*np.pi*np.random.random(nontarget_indices[0].size) - np.pi

        # Compute errors
        new_all_errors = utils.wrap_angles(new_item_angles - dataset['response'], bound=np.pi)

        for n_items in n_items_space:
            ids_filtered = (dataset['n_items'] == n_items).flatten()

            if n_items in errors_nitems_new_dict:
                errors_nitems_new_dict[n_items] = np.r_[errors_nitems_new_dict[n_items], new_all_errors[ids_filtered]]
            else:
                errors_nitems_new_dict[n_items] = new_all_errors[ids_filtered]

    errors_nitems_new = np.array([val for key, val in errors_nitems_new_dict.items()])

    utils.plot_hists_bias_nontargets(errors_nitems_new[n_items_space>1], bins=20, label='allnontarget_randomized_%dresamplings' % nb_resampling, dataio=dataio, remove_first_column=True)

    ### Do same for best non targets
    # TODO Convert this for data_dualrecall
    errors_nontargets = errors_nitems_new[1:, :, 1:]
    indices_bestnontarget = np.nanargmin(np.abs(errors_nontargets), axis=2)

    # Index of the argmin of absolute error. Not too bad, easy to index into.
    errors_bestnontargets_nitems = np.array([ errors_nontargets[n_items_i, xrange(errors_nontargets.shape[1]), indices_bestnontarget[n_items_i]]   for n_items_i in xrange(errors_nontargets.shape[0]) ])

    # Show histograms
    utils.plot_hists_bias_nontargets(errors_bestnontargets_nitems, bins=20, label='bestnontarget_randomized_%dresamplings' % nb_resampling, dataio=dataio)




def plot_check_oblique_effect(data, nb_bins=100):
    '''
        Humans are more precise for vertical and horizontal bars than diagonal orientations.

        Check if present.
    '''

    # Construct the list of (target angles, errors), see if there is some structure in that
    errors_per_angle = np.array(zip(data['item_angle'][np.arange(data['probe'].size), data['probe'][:, 0]], data['error'][:, 0]))

    # response_per_angle = np.array(zip(data['item_angle'][np.arange(data['probe'].size), data['probe'][:, 0]], data['response']))
    # response_per_colour = np.array(zip(data['item_colour'][np.arange(data['probe'].size), data['probe'][:, 0]], data['response']))

    plt.figure()
    plt.plot(errors_per_angle[:, 0], errors_per_angle[:, 1], 'x')

    plt.figure()
    plt.plot(errors_per_angle[:, 0], np.abs(errors_per_angle[:, 1]), 'x')

    discrete_x = np.linspace(-np.pi/2., np.pi/2., nb_bins)
    avg_error = np.zeros(discrete_x.shape)
    std_error = np.zeros(discrete_x.shape)

    for x_i in np.arange(discrete_x.size):
        if x_i < discrete_x.size - 1:
            # Check what data comes in the current interval x[x_i, x_i+1]
            avg_error[x_i] = utils.mean_angles(errors_per_angle[np.logical_and(errors_per_angle[:, 0] > discrete_x[x_i], errors_per_angle[:, 0] < discrete_x[x_i+1]), 1])
            std_error[x_i] = utils.angle_circular_std_dev(errors_per_angle[np.logical_and(errors_per_angle[:, 0] > discrete_x[x_i], errors_per_angle[:, 0] < discrete_x[x_i+1]), 1])

    plt.figure()
    plt.plot(discrete_x, avg_error)

    plt.figure()
    plt.plot(discrete_x, avg_error**2.)

    plt.figure()
    plt.plot(discrete_x, np.abs(avg_error))

    plt.figure()
    plt.plot(errors_per_angle[:, 0], errors_per_angle[:, 1], 'x')
    plt.plot(discrete_x, avg_error, 'ro')


def plot_histograms_errors_targets_nontargets_nitems(dataset, dataio=None):
    '''
        Create subplots showing histograms of errors to targets and nontargets

        Adds Vtest texts on the nontargets
    '''

    angle_space = np.linspace(-np.pi, np.pi, 51)
    bins_center = angle_space[:-1] + np.diff(angle_space)[0]/2

    #### Histograms of errors / errors to nontargets, collapsing across subjects
    if False:
        f1, axes1 = plt.subplots(ncols=dataset['n_items_size'],
                             nrows=2,
                             figsize=(dataset['n_items_size']*6, 12),
                             )

        for n_items_i, n_items in enumerate(np.unique(dataset['n_items'])):
            utils.hist_angular_data(
                dataset['errors_nitems'][n_items_i],
                bins=angle_space,
                title='N=%d' % (n_items),
                norm='density',
                ax_handle=axes1[0, n_items_i],
                pretty_xticks=True)
            axes1[0, n_items_i].set_ylim([0., 2.0])

            if n_items > 1:
                utils.hist_angular_data(
                    utils.dropnan(dataset['errors_nontarget_nitems'][n_items_i]),
                    bins=angle_space,
                    # title='Nontarget %s N=%d' % (dataset['name'], n_items),
                    norm='density',
                    ax_handle=axes1[1, n_items_i],
                    pretty_xticks=True)

                axes1[1, n_items_i].text(
                    0.02,
                    0.96,
                    "Vtest pval: %.4f" % (dataset['vtest_nitems'][n_items_i]),
                    transform=axes1[1, n_items_i].transAxes,
                    horizontalalignment='left',
                    fontsize=13)

                axes1[1, n_items_i].set_ylim([0., 0.3])
            else:
                axes1[1, n_items_i].axis('off')

        # f1.suptitle(dataset['name'])

        f1.canvas.draw()

        if dataio is not None:
            plt.figure(f1.number)
            # plt.tight_layout()
            dataio.save_current_figure("hist_error_all_{label}_{unique_id}.pdf")

    ### Histograms per subject and nitems
    if True:
        f2, axes2 = plt.subplots(ncols=dataset['n_items_size'],
                                 nrows=2,
                                 figsize=(dataset['n_items_size']*6, 12))
        for n_items_i, n_items in enumerate(np.unique(dataset['n_items'])):

            axes2[0, n_items_i].bar(
                bins_center,
                dataset['hist_cnts_target_nitems_stats']['mean'][n_items_i],
                width=2.*np.pi/(angle_space.size-1),
                align='center',
                yerr=dataset['hist_cnts_target_nitems_stats']['sem'][n_items_i])
            # axes3[n_items_i].set_title('N=%d' % n_items)
            axes2[0, n_items_i].set_title('N=%d' % n_items)
            axes2[0, n_items_i].set_xlim(
                [bins_center[0]-np.pi/(angle_space.size-1),
                 bins_center[-1]+np.pi/(angle_space.size-1)])
            axes2[0, n_items_i].set_ylim([0., 2.0])
            axes2[0, n_items_i].set_xticks((-np.pi, -np.pi/2, 0, np.pi/2., np.pi))
            axes2[0, n_items_i].set_xticklabels(
                (r'$-\pi$',
                 r'$-\frac{\pi}{2}$',
                 r'$0$',
                 r'$\frac{\pi}{2}$',
                 r'$\pi$'),
                fontsize=16)

            if n_items > 1:
                axes2[1, n_items_i].bar(
                    bins_center,
                    dataset['hist_cnts_nontarget_nitems_stats']['mean'][n_items_i],
                    yerr=dataset['hist_cnts_nontarget_nitems_stats']['sem'][n_items_i],
                    width=2.*np.pi/(angle_space.size-1),
                    align='center')
                # axes2[1, n_items_i].set_title('N=%d' % n_items)
                # axes2[1, n_items_i].text(0.02, 0.96, "Vtest pval: %.4f" % (pvalue_nontarget_subject_nitems_mean[n_items_i]), transform=axes2[1, n_items_i].transAxes, horizontalalignment='left', fontsize=13)
                axes2[1, n_items_i].text(
                    0.02,
                    0.96,
                    "Vtest pval: %.4f" % (dataset['vtest_nitems'][n_items_i]),
                    transform=axes2[1, n_items_i].transAxes,
                    horizontalalignment='left',
                    fontsize=14)

                # TODO Add bootstrap there instead.
                # axes2[1, n_items_i].set_title('Nontarget, subject, N=%d' % n_items)
                axes2[1, n_items_i].set_xlim(
                    [bins_center[0]-np.pi/(angle_space.size-1),
                     bins_center[-1]+np.pi/(angle_space.size-1)])
                axes2[1, n_items_i].set_ylim([0., 0.3])
                axes2[1, n_items_i].set_xticks(
                    (-np.pi, -np.pi/2, 0, np.pi/2., np.pi))
                axes2[1, n_items_i].set_xticklabels(
                    (r'$-\pi$',
                     r'$-\frac{\pi}{2}$',
                     r'$0$',
                     r'$\frac{\pi}{2}$',
                     r'$\pi$'),
                    fontsize=16)
            else:
                axes2[1, n_items_i].axis('off')

            # f2.suptitle(dataset['name'])

        f2.canvas.draw()

        if dataio is not None:
            plt.figure(f2.number)
            # plt.tight_layout()
            dataio.save_current_figure("hist_error_persubj_{label}_{unique_id}.pdf")


    ### Scatter marginals, 3-parts figures
    if True:
        f3_all = []
        for n_items_i, n_items in enumerate(np.unique(dataset['n_items'])):
            f3 = utils.scatter_marginals(
                utils.dropnan(
                    dataset['data_to_fit'][n_items]['item_features'][:, 0, 0]),
                utils.dropnan(dataset['data_to_fit'][n_items]['response']),
                xlabel='Target',
                ylabel='Response',
                # title='%s, %d items' % (
                    # dataset['name'], n_items),
                figsize=(9, 9),
                factor_axis=1.1,
                bins=61)
            f3_all.append(f3)

    return f1, f2, f3_all


def plot_em_mixtures(dataset, dataio=None, use_sem=True):
    '''
        Do plots for the mixture models and kappa
    '''
    T_space_exp = np.unique(dataset['n_items'])

    f, ax = plt.subplots()

    if use_sem:
        errorbars = 'sem'
    else:
        errorbars = 'std'

    # Mixture probabilities
    utils.plot_mean_std_area(T_space_exp, dataset['em_fits_nitems_arrays']['mean'][1], np.ma.masked_invalid(dataset['em_fits_nitems_arrays'][errorbars][1]).filled(0.0), xlabel='Number of items', ylabel="Mixture probabilities", ax_handle=ax, linewidth=3, fmt='o-', markersize=5, label='Target')
    utils.plot_mean_std_area(T_space_exp, np.ma.masked_invalid(dataset['em_fits_nitems_arrays']['mean'][2]).filled(0.0), np.ma.masked_invalid(dataset['em_fits_nitems_arrays'][errorbars][2]).filled(0.0), xlabel='Number of items', ylabel="Mixture probabilities", ax_handle=ax, linewidth=3, fmt='o-', markersize=5, label='Nontarget')
    utils.plot_mean_std_area(T_space_exp, dataset['em_fits_nitems_arrays']['mean'][3], np.ma.masked_invalid(dataset['em_fits_nitems_arrays'][errorbars][3]).filled(0.0), xlabel='Number of items', ylabel="Mixture probabilities", ax_handle=ax, linewidth=3, fmt='o-', markersize=5, label='Random')

    ax.legend(prop={'size':15})

    ax.set_title('Mixture model for EM fit %s' % dataset['name'])
    ax.set_xlim([1.0, T_space_exp.max()])
    ax.set_ylim([0.0, 1.1])
    ax.set_xticks(range(1, T_space_exp.max()+1))
    ax.set_xticklabels(range(1, T_space_exp.max()+1))

    f.canvas.draw()

    if dataio is not None:
        dataio.save_current_figure('emfits_mixtures_{label}_{unique_id}.pdf')

    # Kappa
    f, ax = plt.subplots()

    ax = utils.plot_mean_std_area(T_space_exp,
    dataset['em_fits_nitems_arrays']['mean'][0], np.ma.masked_invalid(dataset['em_fits_nitems_arrays'][errorbars][0]).filled(0.0), linewidth=3, fmt='o-', markersize=8, label='Kappa', xlabel='Number of items', ylabel='Experimental data', ax_handle=ax)

    ax.legend(prop={'size':15})
    ax.set_title('Kappa for EM fit %s' % dataset['name'])
    ax.set_xlim([0.9, T_space_exp.max()+0.1])
    ax.set_ylim([0.0, np.max(dataset['em_fits_nitems_arrays']['mean'][0])*1.1])
    ax.set_xticks(range(1, T_space_exp.max()+1))
    ax.set_xticklabels(range(1, T_space_exp.max()+1))
    ax.get_figure().canvas.draw()

    if dataio is not None:
        dataio.save_current_figure('emfits_kappa_{label}_{unique_id}.pdf')

def plot_precision(dataset, dataio=None, use_sem=True):
    '''
        Do plots for the mixture models and kappa
    '''
    T_space_exp = np.unique(dataset['n_items'])

    precisions_to_plot = [['precision_subject_nitems_theo', 'Precision Theo'],['precision_subject_nitems_bays_notreatment', 'Precision BaysNoTreat'],['precision_subject_nitems_bays', 'Precision Bays'],['precision_subject_nitems_theo_nochance', 'Precision TheoNoChance']]

    for precision_to_plot, precision_title in precisions_to_plot:
        f, ax = plt.subplots()

        # Compute the errorbars
        precision_mean = np.mean(dataset[precision_to_plot], axis=0)
        precision_errors = np.std(dataset[precision_to_plot], axis=0)
        if use_sem:
            precision_errors /= np.sqrt(dataset['subject_size'])

        # Now show the precision
        utils.plot_mean_std_area(T_space_exp, precision_mean, precision_errors, xlabel='Number of items', label="Precision", ax_handle=ax, linewidth=3, fmt='o-', markersize=5)

        ax.legend(prop={'size':15})

        ax.set_title('%s %s' % (precision_title, dataset['name']))
        ax.set_xlim([1.0, T_space_exp.max()])
        ax.set_ylim([0.0, np.max(precision_mean)+np.max(precision_errors)])
        ax.set_xticks(range(1, T_space_exp.max()+1))
        ax.set_xticklabels(range(1, T_space_exp.max()+1))

        f.canvas.draw()

        if dataio is not None:
            dataio.save_current_figure('%s_{label}_{unique_id}.pdf' % precision_title)


def plot_dualrecall(dataset):
    '''
        Create plots for the double recall dataset
    '''

    to_plot = {'resp_vs_targ':True, 'error_boxplot':True, 'resp_rating':True, 'em_fits':True, 'loglik':True, 'resp_distrib':True, 'resp_conds':True}

    dataset_pd = dataset['panda']

    dataset_pd['error_abs'] = dataset_pd.error.abs()

    # Show distributions of responses wrt target angles/colour
    if to_plot['resp_vs_targ']:

        # Plot scatter and marginals for the orientation trials
        utils.scatter_marginals(utils.dropnan(dataset['item_angle'][dataset['angle_trials'] & dataset['3_items_trials'], 0]), utils.dropnan(dataset['probe_angle'][dataset['angle_trials'] & dataset['3_items_trials']]), xlabel ='Target angle', ylabel='Response angle', title='%s Angle trials, 3 items' % (dataset['name']), figsize=(9, 9), factor_axis=1.1, bins=61)
        utils.scatter_marginals(utils.dropnan(dataset['item_angle'][dataset['angle_trials'] & dataset['6_items_trials'], 0]), utils.dropnan(dataset['probe_angle'][dataset['angle_trials'] & dataset['6_items_trials']]), xlabel ='Target angle', ylabel='Response angle', title='%s Angle trials, 6 items' % (dataset['name']), figsize=(9, 9), factor_axis=1.1, bins=61)

        # Plot scatter and marginals for the colour trials
        utils.scatter_marginals(utils.dropnan(dataset['item_colour'][dataset['colour_trials']& dataset['3_items_trials'], 0]), utils.dropnan(dataset['probe_colour'][dataset['colour_trials'] & dataset['3_items_trials']]), xlabel ='Target colour', ylabel='Response colour', title='%s Colour trials, 3 items' % (dataset['name']), figsize=(9, 9), factor_axis=1.1, bins=61, show_colours=True)
        utils.scatter_marginals(utils.dropnan(dataset['item_colour'][dataset['colour_trials'] & dataset['6_items_trials'], 0]), utils.dropnan(dataset['probe_colour'][dataset['colour_trials'] & dataset['6_items_trials']]), xlabel ='Target colour', ylabel='Response colour', title='%s Colour trials, 6 items' % (dataset['name']), figsize=(9, 9), factor_axis=1.1, bins=61, show_colours=True)


    if 'em_fits' in dataset:

        # dataset_pd[ids_filtered][ids_targets_responses].boxplot('error_angle_abs', by='rating')
        # dataset_pd[ids_filtered][ids_nontargets_responses].boxplot('error_angle_abs', by='rating')

        if to_plot['error_boxplot']:
            dataset_pd.boxplot(column=['error_abs'], by=['cond', 'n_items', 'rating'])

        # for i in dataset_pd.subject.unique():
        #     dataset_pd[dataset_pd.subject == i].boxplot(column=['error_angle'], by=['n_items', 'rating'])

        # Show distribution responsibility as a function of rating
        if to_plot['resp_rating']:
            # dataset_grouped_nona_rating = dataset_pd[dataset_pd.n_items == 3.0].dropna(subset=['error']).groupby(['rating'])
            dataset_grouped_nona_rating = dataset_pd[dataset_pd.n_items == 6.0][dataset_pd.cond == 1.].dropna(subset=['error']).groupby(['rating'])
            _, axes = plt.subplots(dataset_pd.rating.nunique(), 3)
            i = 0
            bins = np.linspace(0., 1.0, 31)
            for name, group in dataset_grouped_nona_rating:
                print name

                # Compute histograms and normalize per rating condition
                counts_target, bins_edges = np.histogram(group.resp_target, bins=bins)
                counts_nontarget, bins_edges = np.histogram(group.resp_nontarget, bins=bins)
                counts_random, bins_edges = np.histogram(group.resp_random, bins=bins)
                dedges = np.diff(bins_edges)[0]

                sum_counts = float(np.sum(counts_target) + np.sum(counts_nontarget) + np.sum(counts_random))
                counts_target = counts_target/sum_counts
                counts_nontarget = counts_nontarget/sum_counts
                counts_random = counts_random/sum_counts

                # Print Responsibility target density estimation
                # group.resp_target.plot(kind='kde', ax=axes[i, 0])
                axes[i, 0].bar(bins_edges[:-1], counts_target, dedges, color='b')
                axes[i, 0].set_xlim((0.0, 1.0))
                axes[i, 0].set_ylim((0.0, 0.35))
                axes[i, 0].text(0.5, 0.8, "T " + str(name), fontweight='bold', horizontalalignment='center', transform = axes[i, 0].transAxes)

                # Print Responsibility nontarget density estimation
                # group.resp_nontarget.plot(kind='kde', ax=axes[i, 1])
                axes[i, 1].bar(bins_edges[:-1], counts_nontarget, dedges, color='g')
                axes[i, 1].set_xlim((0.0, 1.0))
                axes[i, 1].set_ylim((0.0, 0.35))
                axes[i, 1].text(0.5, 0.8, "NT " + str(name), fontweight='bold', horizontalalignment='center', transform = axes[i, 1].transAxes)

                # Print Responsibility random density estimation
                # group.resp_random.plot(kind='kde', ax=axes[i, 1])
                axes[i, 2].bar(bins_edges[:-1], counts_random, dedges, color='r')
                axes[i, 2].set_xlim((0.0, 1.0))
                axes[i, 2].set_ylim((0.0, 0.35))
                axes[i, 2].text(0.5, 0.8, "R " + str(name), fontweight='bold', horizontalalignment='center', transform = axes[i, 2].transAxes)

                i += 1

            plt.suptitle("Colour trials")

        dataset_grouped_nona_rating = dataset_pd[dataset_pd.n_items == 6.0][dataset_pd.cond == 2.].dropna(subset=['error']).groupby(['rating'])
        f, axes = plt.subplots(dataset_pd.rating.nunique(), 3)
        i = 0
        bins = np.linspace(0., 1.0, 31)
        for name, group in dataset_grouped_nona_rating:
            print name

            # Compute histograms and normalize per rating condition
            counts_target, bins_edges = np.histogram(group.resp_target, bins=bins)
            counts_nontarget, bins_edges = np.histogram(group.resp_nontarget, bins=bins)
            counts_random, bins_edges = np.histogram(group.resp_random, bins=bins)
            dedges = np.diff(bins_edges)[0]

            sum_counts = float(np.sum(counts_target) + np.sum(counts_nontarget) + np.sum(counts_random))
            counts_target = counts_target/sum_counts
            counts_nontarget = counts_nontarget/sum_counts
            counts_random = counts_random/sum_counts

            # Print Responsibility target density estimation
            # group.resp_target.plot(kind='kde', ax=axes[i, 0])
            axes[i, 0].bar(bins_edges[:-1], counts_target, dedges, color='b')
            axes[i, 0].set_xlim((0.0, 1.0))
            axes[i, 0].set_ylim((0.0, 0.35))
            axes[i, 0].text(0.5, 0.8, "T " + str(name), fontweight='bold', horizontalalignment='center', transform = axes[i, 0].transAxes)

            # Print Responsibility nontarget density estimation
            # group.resp_nontarget.plot(kind='kde', ax=axes[i, 1])
            axes[i, 1].bar(bins_edges[:-1], counts_nontarget, dedges, color='g')
            axes[i, 1].set_xlim((0.0, 1.0))
            axes[i, 1].set_ylim((0.0, 0.35))
            axes[i, 1].text(0.5, 0.8, "NT " + str(name), fontweight='bold', horizontalalignment='center', transform = axes[i, 1].transAxes)

            # Print Responsibility random density estimation
            # group.resp_random.plot(kind='kde', ax=axes[i, 1])
            axes[i, 2].bar(bins_edges[:-1], counts_random, dedges, color='r')
            axes[i, 2].set_xlim((0.0, 1.0))
            axes[i, 2].set_ylim((0.0, 0.35))
            axes[i, 2].text(0.5, 0.8, "R " + str(name), fontweight='bold', horizontalalignment='center', transform = axes[i, 2].transAxes)

            i += 1
        plt.suptitle("Angle trials")


        # Add condition names
        dataset_pd['cond_name'] = np.array(['Colour', 'Angle'])[np.array(dataset_pd['cond']-1, dtype=int)]

        # Regroup some data
        dataset_grouped_nona_conditems = dataset_pd.dropna(subset=['error']).groupby(['cond_name', 'n_items'])
        dataset_grouped_nona_conditems_mean = dataset_grouped_nona_conditems.mean()[['mixt_target', 'mixt_nontargets_sum', 'mixt_random', 'kappa', 'train_LL', 'test_LL']]

        # Show inferred mixture proportions and kappa
        if to_plot['em_fits']:
            # ax = dataset_grouped_nona_conditems_mean[['mixt_target', 'mixt_nontargets_sum', 'mixt_random', 'kappa']].plot(secondary_y='kappa', kind='bar')
            ax = dataset_grouped_nona_conditems_mean[['mixt_target', 'mixt_nontargets_sum', 'mixt_random']].plot(kind='bar')
            ax.set_ylabel('Mixture proportions')

            ax = dataset_grouped_nona_conditems_mean[['kappa']].plot(kind='bar')
            ax.set_ylabel('Kappa')

        # Show loglihood of fit
        if to_plot['loglik']:
            f, ax = plt.subplots(1, 1)
            dataset_grouped_nona_conditems_mean[['train_LL', 'test_LL']].plot(kind='bar', ax=ax, secondary_y='test_LL')

        # Show boxplot of responsibilities
        if to_plot['resp_distrib']:
            dataset_grouped_nona_conditems.boxplot(column=['resp_target', 'resp_nontarget', 'resp_random'])

        # Show distributions of responsibilities
        if to_plot['resp_conds']:
            f, axes = plt.subplots(dataset_pd.cond_name.nunique()*dataset_pd.n_items.nunique(), 3)
            i = 0
            bins = np.linspace(0., 1.0, 31)
            for name, group in dataset_grouped_nona_conditems:
                print name

                # Print Responsibility target density estimation
                # group.resp_target.plot(kind='kde', ax=axes[i, 0])
                group.resp_target.hist(ax=axes[i, 0], color='b', bins=bins)
                axes[i, 0].text(0.5, 0.85, "T " + ' '.join([str(x) for x in name]), fontweight='bold', horizontalalignment='center', transform = axes[i, 0].transAxes)
                axes[i, 0].set_xlim((0.0, 1.0))

                # Print Responsibility nontarget density estimation
                # group.resp_nontarget.plot(kind='kde', ax=axes[i, 1])
                group.resp_nontarget.hist(ax=axes[i, 1], color='g', bins=bins)
                axes[i, 1].text(0.5, 0.85, "NT " + ' '.join([str(x) for x in name]), fontweight='bold', horizontalalignment='center', transform = axes[i, 1].transAxes)
                axes[i, 1].set_xlim((0.0, 1.0))

                # Print Responsibility random density estimation
                # group.resp_random.plot(kind='kde', ax=axes[i, 1])
                group.resp_random.hist(ax=axes[i, 2], color='r', bins=bins)
                axes[i, 2].text(0.5, 0.85, "R " + ' '.join([str(x) for x in name]), fontweight='bold', horizontalalignment='center', transform = axes[i, 2].transAxes)
                axes[i, 2].set_xlim((0.0, 1.0))

                i += 1

        # Extract some parameters
        fitted_parameters = dataset_grouped_nona_conditems_mean.iloc[0].loc[['kappa', 'mixt_target', 'mixt_nontargets_sum', 'mixt_random']]
        print fitted_parameters


def plot_bias_close_feature(dataset, dataio=None):
    '''
        Check if there is a bias in the response towards closest item (either closest wrt cued feature, or wrt all features)
    '''
    number_items_considered = 2

    # Error to nontarget
    bias_to_nontarget = np.abs(dataset['errors_nontarget_nitems'][number_items_considered-1][:, :number_items_considered-1].flatten())
    bias_to_target = np.abs(dataset['errors_nitems'][number_items_considered-1].flatten())
    ratio_biases = bias_to_nontarget/ bias_to_target
    response = dataset['data_to_fit'][number_items_considered]['response']

    target = dataset['data_to_fit'][number_items_considered]['item_features'][:, 0]
    nontarget = dataset['data_to_fit'][number_items_considered]['item_features'][:, 1]

    # Distance between probe and closest nontarget, in full feature space
    dist_target_nontarget_torus = utils.dist_torus(target, nontarget)

    # Distance only looking at recalled feature
    dist_target_nontarget_recalled = np.abs(utils.wrap_angles((target[:, 0] - nontarget[:, 0])))

    # Distance only looking at cued feature.
    # Needs more work. They are only a few possible values, so we can group them and get a boxplot for each
    dist_target_nontarget_cue = np.round(np.abs(utils.wrap_angles((target[:, 1] - nontarget[:, 1]))), decimals=8)
    dist_distinct_values = np.unique(dist_target_nontarget_cue)
    bias_to_nontarget_grouped_dist_cue = []
    for dist_value in dist_distinct_values:
        bias_to_nontarget_grouped_dist_cue.append(bias_to_nontarget[dist_target_nontarget_cue == dist_value])

    # Check if the response is closer to the target or nontarget, in relative terms.
    # Need to compute a ratio linking bias_to_target and bias_to_nontarget.
    # Two possibilities: response was between target and nontarget, or response was "behind" the target.
    ratio_response_close_to_nontarget = bias_to_nontarget/dist_target_nontarget_recalled
    indices_filter_other_side = bias_to_nontarget > dist_target_nontarget_recalled
    ratio_response_close_to_nontarget[indices_filter_other_side] = bias_to_nontarget[indices_filter_other_side]/(dist_target_nontarget_recalled[indices_filter_other_side] + bias_to_target[indices_filter_other_side])

    f, ax = plt.subplots(2, 2)
    ax[0, 0].plot(dist_target_nontarget_torus, bias_to_nontarget, 'x')
    ax[0, 0].set_xlabel('Distance full feature space')
    ax[0, 0].set_ylabel('Error to nontarget')

    ax[0, 1].boxplot(bias_to_nontarget_grouped_dist_cue, positions=dist_distinct_values)
    ax[0, 1].set_ylabel('Error to nontarget')
    ax[0, 1].set_xlabel('Distance cued feature only')

    # ax[1, 0].plot(dist_target_nontarget_recalled, np.ma.masked_greater(ratio_biases, 100), 'x')
    ax[1, 0].plot(dist_target_nontarget_recalled, bias_to_nontarget, 'x')
    # ax[1, 0].plot(dist_target_nontarget_recalled, np.ma.masked_greater(bias_to_nontarget/dist_target_nontarget_recalled, 30), 'x')
    ax[1, 0].set_xlabel('Distance recalled feature only')
    ax[1, 0].set_ylabel('Error to nontarget')

    ax[1, 1].plot(dist_target_nontarget_recalled, ratio_response_close_to_nontarget, 'x')
    ax[1, 1].set_xlabel('Distance recalled feature only')
    ax[1, 1].set_ylabel('Normalised distance to nontarget')


    f.suptitle('Effect of distance between items on bias of response towards nontarget')

    if dataio:
        f.set_size_inches(16, 16, forward=True)
        dataio.save_current_figure('plot_bias_close_feature_{label}_{unique_id}.pdf')



def plot_compare_bic_collapsed_mixture_model(dataset, dataio=None):
    '''
        Check what models fits the data best using the BIC

        As we have one BIC per subject (collapsed) and one BIC per subject / n_item (non-collapsed), we need to sum them properly somehow.
    '''

    collapsed_bic = np.empty((dataset['data_subject_split']['subjects_space'].size))
    for subject, subject_data in dataset['collapsed_em_fits_subjects'].iteritems():
        collapsed_bic[subject-1] = subject_data['bic']

    separate_bic = np.empty((dataset['data_subject_split']['subjects_space'].size, dataset['data_subject_split']['nitems_space'].size))
    for subject_i, subject_data in enumerate(dataset['em_fits_subjects_nitems'].values()):
        for nitems_i, nitems_data in enumerate(subject_data.values()):
            separate_bic[subject_i, nitems_i] = nitems_data['bic']


    print 'Collapsed summed BIC: ', np.sum(collapsed_bic)
    print 'Original non-collapsed BIC: ', np.sum(separate_bic)

    f, ax = plt.subplots()
    ax.plot(np.sum(separate_bic, axis=-1), collapsed_bic, 'o', markersize=10)

    ixx = np.linspace(collapsed_bic.min()*0.95, collapsed_bic.max()*1.05, 100)
    ax.plot(ixx, ixx, '--k')

    ax.set_aspect('equal')
    ax.set_xlabel('Non-collapsed BIC per subject')
    ax.set_ylabel('Collapsed BIC per subject')
    f.canvas.draw()

    return separate_bic, collapsed_bic


def plot_collapsed_em_mixtures(dataset, dataio=None, use_sem=True):
    '''
        Do plots for the mixture models and kappa
    '''
    T_space_exp = dataset['data_subject_split']['nitems_space']

    f, ax = plt.subplots()

    if use_sem:
        errorbars = 'sem'
    else:
        errorbars = 'std'

    # Mixture probabilities
    utils.plot_mean_std_area(T_space_exp, dataset['collapsed_em_fits']['mean']['mixt_target'], np.ma.masked_invalid(dataset['collapsed_em_fits'][errorbars]['mixt_target']).filled(0.0), xlabel='Number of items', ylabel="Mixture probabilities", ax_handle=ax, linewidth=3, fmt='o-', markersize=5, label='Target')
    utils.plot_mean_std_area(T_space_exp, np.ma.masked_invalid(dataset['collapsed_em_fits']['mean']['mixt_nontargets']).filled(0.0), np.ma.masked_invalid(dataset['collapsed_em_fits'][errorbars]['mixt_nontargets']).filled(0.0), xlabel='Number of items', ylabel="Mixture probabilities", ax_handle=ax, linewidth=3, fmt='o-', markersize=5, label='Nontarget')
    utils.plot_mean_std_area(T_space_exp, dataset['collapsed_em_fits']['mean']['mixt_random'], np.ma.masked_invalid(dataset['collapsed_em_fits'][errorbars]['mixt_random']).filled(0.0), xlabel='Number of items', ylabel="Mixture probabilities", ax_handle=ax, linewidth=3, fmt='o-', markersize=5, label='Random')

    ax.legend(prop={'size':15})

    ax.set_title('Mixture model for Collapsed EM fit %s' % dataset['name'])
    ax.set_xlim([1.0, T_space_exp.max()])
    ax.set_ylim([0.0, 1.1])
    ax.set_xticks(range(1, T_space_exp.max()+1))
    ax.set_xticklabels(range(1, T_space_exp.max()+1))

    f.canvas.draw()

    if dataio is not None:
        dataio.save_current_figure('collapsedemfits_mixtures_{label}_{unique_id}.pdf')

    # Kappa
    f, ax = plt.subplots()

    ax = utils.plot_mean_std_area(T_space_exp, dataset['collapsed_em_fits']['mean']['kappa'], np.ma.masked_invalid(dataset['collapsed_em_fits'][errorbars]['kappa']).filled(0.0), linewidth=3, fmt='o-', markersize=8, ylabel='Experimental data', ax_handle=ax, label='Kappa')

    ax.legend(prop={'size':15})
    ax.set_title('Kappa for Collapsed EM fit %s' % dataset['name'])
    ax.set_xlim([0.9, T_space_exp.max()+0.1])
    ax.set_ylim([0.0, np.max(dataset['collapsed_em_fits']['mean']['kappa'])*1.1])
    ax.set_xticks(range(1, T_space_exp.max()+1))
    ax.set_xticklabels(range(1, T_space_exp.max()+1))
    ax.get_figure().canvas.draw()

    if dataio is not None:
        dataio.save_current_figure('collapsedemfits_kappa_{label}_{unique_id}.pdf')


def plot_compare_bic_collapsed_mixture_model_sequential(dataset, dataio=None):
    '''
        SEQUENTIAL GORGO 11 VERSION

        Check what models fits the data best using the BIC

        As we have one BIC per subject (collapsed) and one BIC per subject / n_item (non-collapsed), we need to sum them properly somehow.
    '''

    bic_collapsed_subjects_trecall = np.array([dataset['collapsed_em_fits_trecall']['values'][trecall]['bic'] for trecall in dataset['data_subject_split']['nitems_space']]).T
    bic_collapsed_subjects_nitems = np.array([dataset['collapsed_em_fits_nitems']['values'][nitems]['bic'] for nitems in dataset['data_subject_split']['nitems_space']]).T


    # em_fits_subjects_nitems_trecall
    # em_fits_nitems_trecall
    # em_fits_subjects_nitems
    bic_separate_subjects_nitems_trecall = np.nan*np.empty((dataset['subject_size'], dataset['n_items_size'], dataset['n_items_size']))
    ll_separate_subjects_nitems_trecall = np.nan*np.empty((dataset['subject_size'], dataset['n_items_size'], dataset['n_items_size']))

    for subject_i, subject in enumerate(dataset['data_subject_split']['subjects_space']):
        for n_items_i, n_items in enumerate(dataset['data_subject_split']['nitems_space']):
            for t_i, trecall in enumerate(np.arange(1, n_items + 1)):
                trecall_i = n_items - trecall
                bic_separate_subjects_nitems_trecall[subject_i, n_items_i, t_i] = dataset['em_fits_subjects_nitems_trecall'][subject_i, n_items_i, trecall_i]['bic']
                ll_separate_subjects_nitems_trecall[subject_i, n_items_i, t_i] = dataset['em_fits_subjects_nitems_trecall'][subject_i, n_items_i, trecall_i]['train_LL']

    # Full double powerlaw model
    bic_collapsed_subjects_doublepowerlaw = np.array([dataset['collapsed_em_fits_doublepowerlaw_subjects'][subj]['bic'] for subj in dataset['data_subject_split']['subjects_space']]).T
    ll_collapsed_subjects_doublepowerlaw = np.array([dataset['collapsed_em_fits_doublepowerlaw_subjects'][subj]['train_LL'] for subj in dataset['data_subject_split']['subjects_space']]).T

    print 'Collapsed trecall summed BIC: ', np.sum(bic_collapsed_subjects_trecall)
    print 'Collapsed nitems summed BIC: ', np.sum(bic_collapsed_subjects_nitems)
    print '\n\nCollapsed double powerlaw BIC: ', np.sum(bic_collapsed_subjects_doublepowerlaw)
    print 'Original non-collapsed BIC: ', np.nansum(bic_separate_subjects_nitems_trecall)

    print '\nCollapsed double powerlaw LL: ', np.sum(ll_collapsed_subjects_doublepowerlaw)
    print 'Original non-collapsed LL: ', np.nansum(ll_separate_subjects_nitems_trecall)

    bic_separate_subjects_trecall = np.nansum(bic_separate_subjects_nitems_trecall, axis=-2)
    bic_separate_subjects_nitems = np.nansum(bic_separate_subjects_nitems_trecall, axis=-1)

    # Plot Collapsed trecall vs separate (all)
    if False:
        f, axes = plt.subplots(nrows=1, ncols=2)

        axes[0].plot(bic_separate_subjects_trecall.flatten(), bic_collapsed_subjects_trecall.flatten(), 'o', markersize=10)
        ixx = np.linspace(min(bic_collapsed_subjects_trecall.min(), bic_separate_subjects_trecall.min())*0.95, max(bic_collapsed_subjects_trecall.max(), bic_separate_subjects_trecall.max())*1.05, 100)
        axes[0].plot(ixx, ixx, '--k')
        axes[0].set_aspect('equal')
        axes[0].set_xlabel('Non-collapsed BIC, subject/nitem')
        axes[0].set_ylabel('Collapsed trecall BIC, subject/nitem')
        f.canvas.draw()

        # Plot Collapsed nitems vs separate (all)
        axes[1].plot(bic_separate_subjects_nitems.flatten(), bic_collapsed_subjects_nitems.flatten(), 'o', markersize=10)
        ixx = np.linspace(min(bic_collapsed_subjects_nitems.min(), bic_separate_subjects_nitems.min())*0.95, max(bic_collapsed_subjects_nitems.max(), bic_separate_subjects_nitems.max())*1.05, 100)
        axes[1].plot(ixx, ixx, '--k')
        axes[1].set_aspect('equal')
        axes[1].set_xlabel('Non-collapsed BIC, subject/nitem')
        axes[1].set_ylabel('Collapsed nitems BIC, subject/nitem')
        f.canvas.draw()

        if dataio is not None:
            dataio.save_current_figure('bic_separate_vs_collapsed_subjnitems_{label}_{unique_id}.pdf')

    # Now do one summed BIC per subject
    if False:
        bic_collapsed_subjects_trecall_sum = np.nansum(bic_collapsed_subjects_trecall, axis=-1)
        bic_collapsed_subjects_nitems_sum = np.nansum(bic_collapsed_subjects_nitems, axis=-1)

        bic_separate_subjects_trecall_sum = np.nansum(bic_separate_subjects_trecall, axis=-1)
        bic_separate_subjects_nitems_sum = np.nansum(bic_separate_subjects_nitems, axis=-1)

        # Plot Collapsed trecall vs separate (per subject)
        f, axes = plt.subplots(nrows=2, ncols=2, figsize=(15, 15))

        axes[0, 0].plot(bic_separate_subjects_trecall_sum.flatten(), bic_collapsed_subjects_trecall_sum.flatten(), 'o', markersize=10)
        ixx = np.linspace(min(bic_collapsed_subjects_trecall_sum.min(), bic_separate_subjects_trecall_sum.min())*0.95, max(bic_collapsed_subjects_trecall_sum.max(), bic_separate_subjects_trecall_sum.max())*1.05, 100)
        axes[0, 0].plot(ixx, ixx, '--k')
        axes[0, 0].set_aspect('equal')
        axes[0, 0].set_xlabel('Non-collapsed BIC')
        axes[0, 0].set_ylabel('Collapsed trecall BIC')
        f.canvas.draw()

        # Plot Collapsed nitems vs separate (per subject)
        axes[0, 1].plot(bic_separate_subjects_nitems_sum.flatten(), bic_collapsed_subjects_nitems_sum.flatten(), 'o', markersize=10)
        ixx = np.linspace(min(bic_collapsed_subjects_nitems_sum.min(), bic_separate_subjects_nitems_sum.min())*0.95, max(bic_collapsed_subjects_nitems_sum.max(), bic_separate_subjects_nitems_sum.max())*1.05, 100)
        axes[0, 1].plot(ixx, ixx, '--k')
        axes[0, 1].set_aspect('equal')
        axes[0, 1].set_xlabel('Non-collapsed BIC')
        axes[0, 1].set_ylabel('Collapsed nitems BIC')
        f.canvas.draw()

        if dataio is not None:
            dataio.save_current_figure('bic_separate_vs_collapsed_subjects_{label}_{unique_id}.pdf')


        # Plot double powerlaw vs collapsed nitems
        axes[1, 0].plot(bic_collapsed_subjects_nitems_sum.flatten(), bic_collapsed_subjects_doublepowerlaw, 'o', markersize=10)
        ixx = np.linspace(min(bic_collapsed_subjects_nitems_sum.min(), bic_collapsed_subjects_doublepowerlaw.min())*0.95, max(bic_collapsed_subjects_nitems_sum.max(), bic_collapsed_subjects_doublepowerlaw.max())*1.05, 100)
        axes[1, 0].plot(ixx, ixx, '--k')
        axes[1, 0].set_aspect('equal')
        axes[1, 0].set_ylabel('Collapsed double powerlaw BIC')
        axes[1, 0].set_xlabel('Collapsed nitems BIC')
        f.canvas.draw()

        # Plot double powerlaw vs collapsed trecall
        axes[1, 1].plot(bic_collapsed_subjects_trecall_sum.flatten(), bic_collapsed_subjects_doublepowerlaw, 'o', markersize=10)
        ixx = np.linspace(min(bic_collapsed_subjects_trecall_sum.min(), bic_collapsed_subjects_doublepowerlaw.min())*0.95, max(bic_collapsed_subjects_trecall_sum.max(), bic_collapsed_subjects_doublepowerlaw.max())*1.05, 100)
        axes[1, 1].plot(ixx, ixx, '--k')
        axes[1, 1].set_aspect('equal')
        axes[1, 1].set_ylabel('Collapsed double powerlaw BIC')
        axes[1, 1].set_xlabel('Collapsed trecall BIC')
        f.canvas.draw()

    # Compare double-powerlaw vs original, per subject and nitems
    if True:
        bic_separate_subjects = np.nansum(
            np.nansum(bic_separate_subjects_nitems_trecall, axis=-1),
            axis=-1)

        f, ax = plt.subplots()
        ax.plot(
            bic_separate_subjects.flatten(),
            bic_collapsed_subjects_doublepowerlaw,
            'o', markersize=10)
        ixx = np.linspace(
            min(bic_separate_subjects.min(),
                bic_collapsed_subjects_doublepowerlaw.min())*0.95,
            max(bic_separate_subjects.max(),
                bic_collapsed_subjects_doublepowerlaw.max())*1.05,
            100)
        ax.plot(ixx, ixx, '--k')
        ax.set_aspect('equal')
        ax.set_xlabel('Original model BIC')
        ax.set_ylabel('Collapsed double power-law BIC')
        f.canvas.draw()

        if dataio is not None:
            dataio.save_current_figure('bic_separate_vs_collapsed_doublepowerlaw_{label}_{unique_id}.pdf')

    # Works well. Overall quite a huge improvement in BIC, as I thought.


def plot_sequential_histograms_errors(dataset, dataio=None):
    '''
        Create subplots showing histograms of errors to targets and nontargets
    '''

    angle_space = np.linspace(-np.pi, np.pi, 51)
    f1, f2, f3_all = None, None, None

    #### Histograms of errors / errors to nontargets, collapsing across subjects
    if True:
        f1, axes1 = plt.subplots(
            ncols=dataset['n_items_size'],
            nrows=2*dataset['n_items_size'],
            figsize=(15, 30))

        for n_items_i, n_items in enumerate(np.unique(dataset['n_items'])):
            for trecall_i, trecall in enumerate(np.unique(dataset['n_items'])):
                if trecall <= n_items:
                    utils.hist_angular_data(
                        dataset['errors_nitems_trecall'][n_items_i, trecall_i],
                        bins=angle_space,
                        # title='N=%d, trecall=%d' % (n_items, trecall),
                        norm='density',
                        ax_handle=axes1[2*n_items_i, trecall_i],
                        pretty_xticks=False)
                    axes1[2*n_items_i, trecall_i].set_ylim([0., 1.4])
                    axes1[2*n_items_i, trecall_i].xaxis.set_major_locator(
                        plt.NullLocator())
                    axes1[2*n_items_i, trecall_i].yaxis.set_major_locator(
                        plt.NullLocator())


                    if n_items > 1:
                        utils.hist_angular_data(
                            utils.dropnan(dataset['errors_nontarget_nitems_trecall'][n_items_i, trecall_i]),
                            bins=angle_space,
                            # title='Nontarget %s N=%d' % (dataset['name'], n_items),
                            norm='density',
                            ax_handle=axes1[2*n_items_i + 1, trecall_i],
                            pretty_xticks=False)

                        axes1[2*n_items_i + 1, trecall_i].set_ylim([0., 0.3])
                    # else:
                        # axes1[2*n_items_i + 1, trecall_i].axis('off')

                    axes1[2*n_items_i + 1, trecall_i].xaxis.set_major_locator(plt.NullLocator())
                    axes1[2*n_items_i + 1, trecall_i].yaxis.set_major_locator(plt.NullLocator())


                else:
                    axes1[2*n_items_i, trecall_i].axis('off')
                    axes1[2*n_items_i + 1, trecall_i].axis('off')

        # f1.suptitle(dataset['name'])
        f1.canvas.draw()
        plt.tight_layout()

        if dataio is not None:
            plt.figure(f1.number)
            # plt.tight_layout()
            dataio.save_current_figure("hist_error_all_{label}_{unique_id}.pdf")

    ### Scatter marginals, 3-parts figures
    if False:
        f3_all = []
        for n_items_i, n_items in enumerate(np.unique(dataset['n_items'])):
            f3 = utils.scatter_marginals(
                utils.dropnan(
                    dataset['data_to_fit'][n_items]['item_features'][:, 0, 0]),
                utils.dropnan(dataset['data_to_fit'][n_items]['response']),
                xlabel='Target',
                ylabel='Response',
                # title='%s, %d items' % (
                    # dataset['name'], n_items),
                figsize=(9, 9),
                factor_axis=1.1,
                bins=61)
            f3_all.append(f3)

    return f1, f2, f3_all



# def plot_sequential_em_mixtures(dataset, dataio=None):
#     maxItems = 5
#     itemSpace = np.arange(maxItems)
#     itemIndices = np.arange(dataset['n_items_size']) < maxItems

#     # Fig 6
#     plt.figure()
#     plt.plot(np.nanmean(dataset['em_fits_subjects_nitems_arrays'], axis=0)[:maxItems, 0], 'o-', linewidth=2)
#     plt.title('kappa, across trecalls')
#     plt.xlabel('t_recall')
#     plt.xticks(itemSpace, itemSpace+1)

#     plt.figure()
#     plt.plot(np.nanmean(dataset['em_fits_subjects_nitems_arrays'], axis=0)[:maxItems, 1:(maxItems-1)], 'o-', linewidth=2)
#     plt.title('mixture probs, across trecalls')
#     plt.xlabel('t_recall')
#     plt.xticks(itemSpace, itemSpace+1)
#     plt.legend(('target', 'nontarget', 'random'))

#     # fig 7
#     plt.figure()
#     plt.plot(utils.fliplr_nonan(dataset['em_fits_nitems_trecall_arrays'][:maxItems, :maxItems, 0]).T, 'o-', linewidth=2)
#     plt.title('EM kappa')
#     plt.xlabel('t_recall')
#     plt.xticks(itemSpace, itemSpace+1)
#     plt.legend([str(x) for x in itemSpace+1])

#     plt.figure()
#     plt.plot(utils.fliplr_nonan(dataset['em_fits_nitems_trecall_arrays'][:maxItems, :maxItems, 1]).T, 'o-', linewidth=2)
#     plt.title('EM target')
#     plt.xlabel('t_recall')
#     plt.xticks(itemSpace, itemSpace+1)
#     plt.legend([str(x) for x in itemSpace+1])

#     plt.figure()
#     plt.plot(utils.fliplr_nonan(dataset['em_fits_nitems_trecall_arrays'][:maxItems, :maxItems, 2]).T, 'o-', linewidth=2)
#     plt.title('EM nontarget')
#     plt.xlabel('t_recall')
#     plt.xticks(itemSpace, itemSpace+1)
#     plt.legend([str(x) for x in itemSpace+1])

#     plt.figure()
#     plt.plot(utils.fliplr_nonan(dataset['em_fits_nitems_trecall_arrays'][:maxItems, :maxItems, 3]).T, 'o-', linewidth=2)
#     plt.title('EM random')
#     plt.xlabel('t_recall')
#     plt.xticks(itemSpace, itemSpace+1)
#     plt.legend([str(x) for x in itemSpace+1])



def plot_sequential_collapsed_doublepowerlaw(dataset,
                                             dataio=None,
                                             use_sem=True):
    '''
        Plots for Gorgo11 sequential, collapsed mixture model
    '''

    T_space_exp = dataset['data_subject_split']['nitems_space']
    if use_sem:
        errorbars = 'sem'
    else:
        errorbars = 'std'

    ####### SINGLE POWERLAW

    ######## Double powerlaw collapsed model
    if True:
        # Fig 6, trecall=last, nitems on the x-axis
        f1, axes1 = plt.subplots(nrows=1, ncols=2, figsize=(12, 6))
        plot_kappa_mean_error(
            T_space_exp,
            dataset['collapsed_em_fits_doublepowerlaw']['mean'][
                'kappa'][:, 0],
            dataset['collapsed_em_fits_doublepowerlaw'][errorbars][
                'kappa'][:, 0],
            xlabel='items', ylabel='Kappa', ax=axes1[0])
        plot_emmixture_mean_error(
            T_space_exp,
            dataset['collapsed_em_fits_doublepowerlaw']['mean'][
                'mixt_target_tr'][:, 0],
            dataset['collapsed_em_fits_doublepowerlaw'][errorbars][
                'mixt_target_tr'][:, 0],
            label='Target', ax=axes1[1])
        plot_emmixture_mean_error(
            T_space_exp,
            dataset['collapsed_em_fits_doublepowerlaw']['mean'][
                'mixt_nontargets_tr'][:, 0],
            dataset['collapsed_em_fits_doublepowerlaw'][errorbars][
                'mixt_nontargets_tr'][:, 0],
            label='Nontargets', ax=axes1[1])
        plot_emmixture_mean_error(
            T_space_exp,
            dataset['collapsed_em_fits_doublepowerlaw']['mean'][
                'mixt_random_tr'][:, 0],
            dataset['collapsed_em_fits_doublepowerlaw'][errorbars][
                'mixt_random_tr'][:, 0],
            label='Random',
            xlabel='items', ylabel='Mixture proportions', ax=axes1[1])

        f1.suptitle('Fig 6: Last trecall')

        if dataio is not None:
            dataio.save_current_figure('fig6_doublepowerlaw_{label}_{unique_id}.pdf')

    # Fig 7, kappa and mixtures, one plot per nitems, trecall on the x-axis
    if True:
        f2, axes2 = plt.subplots(nrows=2, ncols=2, figsize=(10, 10))

        for nitems_i, nitems in enumerate(T_space_exp):
            plot_kappa_mean_error(
                T_space_exp[:nitems],
                dataset['collapsed_em_fits_doublepowerlaw']['mean'][
                    'kappa'][nitems_i, :nitems],
                dataset['collapsed_em_fits_doublepowerlaw'][errorbars][
                    'kappa'][nitems_i, :nitems],
                # title='collapsed_doublepowerlaw',
                ax=axes2[0, 0],
                label='%d items' % nitems,
                xlabel='Serial order (reversed)',
                zorder=7 - nitems)

            plot_emmixture_mean_error(
                T_space_exp[:nitems],
                dataset['collapsed_em_fits_doublepowerlaw']['mean'][
                    'mixt_target_tr'][nitems_i, :nitems],
                dataset['collapsed_em_fits_doublepowerlaw'][errorbars][
                    'mixt_target_tr'][nitems_i, :nitems],
                # title='Target collapsed_doublepowerlaw',
                ax=axes2[0, 1],
                label='%d items' % nitems,
                xlabel='Serial order (reversed)',
                zorder=7 - nitems)
            plot_emmixture_mean_error(
                T_space_exp[:nitems],
                dataset['collapsed_em_fits_doublepowerlaw']['mean'][
                    'mixt_nontargets_tr'][nitems_i, :nitems],
                dataset['collapsed_em_fits_doublepowerlaw'][errorbars][
                    'mixt_nontargets_tr'][nitems_i, :nitems],
                # title='Nontarget collapsed_doublepowerlaw',
                ax=axes2[1, 0],
                label='%d items' % nitems,
                xlabel='Serial order (reversed)',
                zorder=7 - nitems)
            plot_emmixture_mean_error(
                T_space_exp[:nitems],
                dataset['collapsed_em_fits_doublepowerlaw']['mean'][
                    'mixt_random_tr'][nitems_i, :nitems],
                dataset['collapsed_em_fits_doublepowerlaw'][errorbars][
                    'mixt_random_tr'][nitems_i, :nitems],
                # title='Random collapsed_doublepowerlaw',
                ax=axes2[1, 1],
                label='%d items' % nitems,
                xlabel='Serial order (reversed)',
                zorder=7 - nitems)

        f2.suptitle('Fig7: Collapsed Powerlaw fits')

        if dataio is not None:
            plt.figure(f2.number)
            dataio.save_current_figure('fig7_doublepowerlaw_{label}_{unique_id}.pdf')

    ## Checking parameters of kappa()
    if False:
        kappa_theta_all = np.array(dataset['collapsed_em_fits_doublepowerlaw']['values']['kappa_theta'])

        f, axes = plt.subplots(2, 2)
        axes[0, 0].plot(kappa_theta_all[:, 1], kappa_theta_all[:, 2], 'x', markersize=10)
        axes[0, 0].set_xlabel('beta [nitems]')
        axes[0, 0].set_ylabel('gamma [trecall]')

        axes[1, 0].plot(kappa_theta_all[:, 0], kappa_theta_all[:, 1], 'x', markersize=10)
        axes[1, 0].set_xlabel('alpha [kappa max]')
        axes[1, 0].set_ylabel('beta [nitems]')

        axes[1, 1].plot(kappa_theta_all[:, 0], kappa_theta_all[:, 2], 'x', markersize=10)
        axes[1, 1].set_xlabel('alpha [kappa max]')
        axes[1, 1].set_ylabel('gamma [trecall]')
        f.suptitle('Powerlaw exponents, per subject')

        if dataio is not None:
            dataio.save_current_figure('doublepowerlaw_exponent_persubject_{label}_{unique_id}.pdf')

    #  Same but 3D
    if False:
        fig = plt.figure()
        ax = Axes3D(fig)
        utils.scatter3d(
            kappa_theta_all[:, 1],
            kappa_theta_all[:, 2],
            kappa_theta_all[:, 0],
            c=dataset['data_subject_split']['subjects_space'],
            s=50,
            xlabel='beta [nitems]',
            ylabel='gamma [trecall]',
            zlabel='alpha [kappa max]',
            title='Kappa parameters per subject',
            ax_handle=ax)

        # Now kappa directly
        fig = plt.figure()
        ax = Axes3D(fig)
        kappas_all = np.array(dataset['collapsed_em_fits_doublepowerlaw']['values']['kappa'])
        kappas_all = kappas_all[:, np.isfinite(kappas_all[0])]
        T_trecall_space = np.concatenate([[(T, trecall) for trecall in xrange(1, T+1)] for T in T_space_exp])
        subject_colour_space = np.linspace(0, 1, dataset['data_subject_split']['subjects_space'].size)

        cm = plt.get_cmap('jet')
        cNorm = mcolors.Normalize(vmin=min(subject_colour_space), vmax=max(subject_colour_space))
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)

        for subject_i, subject in enumerate(dataset['data_subject_split']['subjects_space']):
            ax.scatter(T_trecall_space[:, 0], T_trecall_space[:, 1], kappas_all[subject_i], s=50, c=scalarMap.to_rgba(subject_colour_space[subject_i]))
        ax.set_xlabel('nitems')
        ax.set_ylabel('trecall')
        ax.set_zlabel('kappa')

    # Check per subject
    if False:
        for subject_i, subject in enumerate(dataset['data_subject_split']['subjects_space']):
            f, axes = plt.subplots(2, 2)
            for nitems_i, nitems in enumerate(T_space_exp):
                axes[0, 0] = plot_kappa_mean_error(
                    T_space_exp[:nitems],
                    dataset['collapsed_em_fits_doublepowerlaw_subjects'][subject]['kappa'][nitems_i, :nitems],
                    dataset['collapsed_em_fits_doublepowerlaw_subjects'][subject]['kappa'][nitems_i, :nitems]*0.0,
                    title='Subject %d \nbeta %.1f, gamma %.1f, alpha %d' % (
                        subject,
                        dataset['collapsed_em_fits_doublepowerlaw_subjects'][subject]['kappa_theta'][1],
                        dataset['collapsed_em_fits_doublepowerlaw_subjects'][subject]['kappa_theta'][2],
                        dataset['collapsed_em_fits_doublepowerlaw_subjects'][subject]['kappa_theta'][0]),
                    ax=axes[0, 0],
                    label='%d items' % nitems,
                    xlabel='T_recall')
                axes[0, 0].set_ylim((0.0, 15.5))

            for nitems_i, nitems in enumerate(T_space_exp):
                axes[0, 1] = plot_emmixture_mean_error(
                    T_space_exp[:nitems],
                    dataset['collapsed_em_fits_doublepowerlaw_subjects'][subject]['mixt_target_tr'][nitems_i, :nitems],
                    dataset['collapsed_em_fits_doublepowerlaw_subjects'][subject]['mixt_target_tr'][nitems_i, :nitems]*0.0,
                    title='Target, subject %d' % (subject),
                    ax=axes[0, 1],
                    label='%d items' % nitems,
                    xlabel='T_recall')
                axes[1, 0] = plot_emmixture_mean_error(T_space_exp[:nitems],
                    dataset['collapsed_em_fits_doublepowerlaw_subjects'][subject]['mixt_nontargets_tr'][nitems_i, :nitems],
                    dataset['collapsed_em_fits_doublepowerlaw_subjects'][subject]['mixt_target_tr'][nitems_i, :nitems]*0.0,
                    title='Nontarget, subject %d' % (subject),
                    ax=axes[1, 0],
                    label='%d items' % nitems,
                    xlabel='T_recall')
                axes[1, 1] = plot_emmixture_mean_error(T_space_exp[:nitems],
                    dataset['collapsed_em_fits_doublepowerlaw_subjects'][subject]['mixt_random_tr'][nitems_i, :nitems],
                    dataset['collapsed_em_fits_doublepowerlaw_subjects'][subject]['mixt_target_tr'][nitems_i, :nitems]*0.0,
                    title='Random, subject %d' % (subject),
                    ax=axes[1, 1],
                    label='%d items' % nitems,
                    xlabel='T_recall')


# def plot_sequential_collapsed_singlepowerlaw(dataset, dataio=None, use_sem=True):

#     T_space_exp = dataset['data_subject_split']['nitems_space']
#     if use_sem:
#         errorbars = 'sem'
#     else:
#         errorbars = 'std'

#     ####### Fit per t_recall, nitem on the x-axis #####
#     ##
#     # Fig 6, now for trecall=last only. Makes sense.
#     if True:
#         trecall_fixed = 1

#         plot_kappa_mean_error(
#             T_space_exp,
#             dataset['collapsed_em_fits_trecall']['mean'][trecall_fixed]['kappa'],
#             dataset['collapsed_em_fits_trecall'][errorbars][trecall_fixed]['kappa'],
#             title='collapsed_trecall')

#         if dataio is not None:
#             dataio.save_current_figure('fig6_trecalllast_kappa_{label}_{unique_id}.pdf')

#         # Mixture probabilities
#         ax = plot_emmixture_mean_error(
#             T_space_exp,
#             dataset['collapsed_em_fits_trecall']['mean'][trecall_fixed]['mixt_target'],
#             dataset['collapsed_em_fits_trecall'][errorbars][trecall_fixed]['mixt_target'],
#             title='collapsed_trecall',
#             label='Target')
#         ax = plot_emmixture_mean_error(
#             T_space_exp,
#             dataset['collapsed_em_fits_trecall']['mean'][trecall_fixed]['mixt_nontargets'],
#             dataset['collapsed_em_fits_trecall'][errorbars][trecall_fixed]['mixt_nontargets'],
#             title='collapsed_trecall',
#             label='Nontarget',
#             ax=ax)
#         ax = plot_emmixture_mean_error(
#             T_space_exp,
#             dataset['collapsed_em_fits_trecall']['mean'][trecall_fixed]['mixt_random'],
#             dataset['collapsed_em_fits_trecall'][errorbars][trecall_fixed]['mixt_random'],
#             title='collapsed_trecall',
#             label='Random',
#             ax=ax)

#         if dataio is not None:
#             dataio.save_current_figure('fig6_trecalllast_mixt_{label}_{unique_id}.pdf')

#     # Now do for all possible trecall
#     if False:
#         f, ax = plt.subplots()
#         for trecall in xrange(1, 7):
#             ax = plot_kappa_mean_error(T_space_exp[(trecall-1):], dataset['collapsed_em_fits_trecall']['mean'][trecall]['kappa'], dataset['collapsed_em_fits_trecall'][errorbars][trecall]['kappa'], title='collapsed_trecall', ax=ax, label='tr=-%d' % trecall, xlabel='nitems')

#         if dataio is not None:
#             dataio.save_current_figure('collapsed_trecall_kappa_{label}_{unique_id}.pdf')

#         _, ax_target = plt.subplots()
#         _, ax_nontarget = plt.subplots()
#         _, ax_random = plt.subplots()
#         for trecall in xrange(1, 7):
#             ax_target = plot_emmixture_mean_error(T_space_exp[(trecall-1):], dataset['collapsed_em_fits_trecall']['mean'][trecall]['mixt_target'], dataset['collapsed_em_fits_trecall'][errorbars][trecall]['mixt_target'], title='Target collapsed_trecall', ax=ax_target, label='tr=-%d' % trecall, xlabel='nitems')
#             ax_nontarget = plot_emmixture_mean_error(T_space_exp[(trecall-1):], dataset['collapsed_em_fits_trecall']['mean'][trecall]['mixt_nontargets'], dataset['collapsed_em_fits_trecall'][errorbars][trecall]['mixt_nontargets'], title='Nontarget collapsed_trecall', ax=ax_nontarget, label='tr=-%d' % trecall, xlabel='nitems')
#             ax_random = plot_emmixture_mean_error(T_space_exp[(trecall-1):], dataset['collapsed_em_fits_trecall']['mean'][trecall]['mixt_random'], dataset['collapsed_em_fits_trecall'][errorbars][trecall]['mixt_random'], title='Random collapsed_trecall', ax=ax_random, label='tr=-%d' % trecall, xlabel='nitems')

#         if dataio is not None:
#             plt.figure(ax_target.get_figure().number)
#             dataio.save_current_figure('collapsed_trecall_mixttarget_{label}_{unique_id}.pdf')

#             plt.figure(ax_nontarget.get_figure().number)
#             dataio.save_current_figure('collapsed_trecall_mixtnontarget_{label}_{unique_id}.pdf')

#             plt.figure(ax_random.get_figure().number)
#             dataio.save_current_figure('collapsed_trecall_mixtrandom_{label}_{unique_id}.pdf')

#     ####### Fit per nitem, t_recall on the x-axis #####
#     ##
#     # fig 7
#     if True:
#         f, ax = plt.subplots()
#         for nitem in xrange(1, 7):
#             ax = plot_kappa_mean_error(T_space_exp[:nitem], dataset['collapsed_em_fits_nitems']['mean'][nitem]['kappa'], dataset['collapsed_em_fits_nitems'][errorbars][nitem]['kappa'], title='collapsed_nitem', ax=ax, label='%d items' % nitem, xlabel='T_recall')

#         if dataio is not None:
#             dataio.save_current_figure('fig7_nitem_kappa_{label}_{unique_id}.pdf')

#         _, ax_target = plt.subplots()
#         _, ax_nontarget = plt.subplots()
#         _, ax_random = plt.subplots()
#         for nitem in xrange(1, 7):
#             ax_target = plot_emmixture_mean_error(T_space_exp[:nitem], dataset['collapsed_em_fits_nitems']['mean'][nitem]['mixt_target'], dataset['collapsed_em_fits_nitems'][errorbars][nitem]['mixt_target'], title='Target collapsed_nitem', ax=ax_target, label='%d items' % nitem, xlabel='T_recall')
#             ax_nontarget = plot_emmixture_mean_error(T_space_exp[:nitem], dataset['collapsed_em_fits_nitems']['mean'][nitem]['mixt_nontargets'], dataset['collapsed_em_fits_nitems'][errorbars][nitem]['mixt_nontargets'], title='Nontarget collapsed_nitem', ax=ax_nontarget, label='%d items' % nitem, xlabel='T_recall')
#             ax_random = plot_emmixture_mean_error(T_space_exp[:nitem], dataset['collapsed_em_fits_nitems']['mean'][nitem]['mixt_random'], dataset['collapsed_em_fits_nitems'][errorbars][nitem]['mixt_random'], title='Random collapsed_nitem', ax=ax_random, label='%d items' % nitem, xlabel='T_recall')

#         if dataio is not None:
#             dataio.save_current_figure('fig7_nitem_mixt_{label}_{unique_id}.pdf')

#     # Show BIC scores
#     if True:
#         collapsed_trecall_bic = np.array([np.sum(dataset['collapsed_em_fits_trecall']['values'][trecall]['bic']) for trecall in T_space_exp])
#         collapsed_nitems_bic = np.array([np.sum(dataset['collapsed_em_fits_nitems']['values'][nitems]['bic']) for nitems in T_space_exp])

#         f, axes = plt.subplots(nrows=1, ncols=3)
#         axes[0].bar(T_space_exp, collapsed_trecall_bic, align='center')
#         axes[0].set_title('BIC collapsed_trecall')
#         axes[0].set_xticks(T_space_exp)
#         axes[0].set_xlabel('nitems')
#         axes[0].set_ylim([0.0, 1.05*max(collapsed_trecall_bic.max(), collapsed_nitems_bic.max())])
#         axes[1].bar(T_space_exp, collapsed_nitems_bic, align='center')
#         axes[1].set_title('BIC collapsed_nitems')
#         axes[1].set_xlabel('trecall')
#         axes[1].set_xticks(T_space_exp)
#         axes[1].set_ylim([0.0, 1.05*max(collapsed_trecall_bic.max(), collapsed_nitems_bic.max())])

#         # Add the overall BIC sum
#         axes[2].bar(np.array([1,2]), [np.sum(collapsed_trecall_bic), np.sum(collapsed_nitems_bic), ], align='center')
#         axes[2].set_xticks(np.array([1,2]))
#         axes[2].set_xticklabels(['Collapsed_trecall', 'Collapsed_nitems'])
#         axes[2].set_title('BIC total summed')

#         f.canvas.draw()

#         if dataio is not None:
#             dataio.save_current_figure('bic_comparison_sequential_{label}_{unique_id}.pdf')


############################################################################
############################################################################

def plots_bays2009(dataset, dataio=None):
    '''

    Some plots for the Bays2009 data
    '''

    plot_histograms_errors_targets_nontargets_nitems(dataset, dataio)

    # plot_precision(dataset, dataio)

    plot_em_mixtures(dataset, dataio)

    # plot_collapsed_em_mixtures(dataset, dataio)


def plots_gorgo11(dataset, dataio=None):
    '''
        Plots for Gorgo11, assuming sequential data
    '''
    plot_histograms_errors_targets_nontargets_nitems(dataset, dataio)

    # plot_precision(dataset, dataio)

    plot_em_mixtures(dataset, dataio)

    plot_collapsed_em_mixtures(dataset, dataio)


def plots_gorgo11_sequential(dataset, dataio=None):
    '''
        Plots for Gorgo11 sequential, different
    '''

    # plot_sequential_em_mixtures(dataset, dataio)

    plot_sequential_collapsed_doublepowerlaw(dataset, dataio)

    # plot_sequential_collapsed_singlepowerlaw(dataset, dataio)

    plot_sequential_histograms_errors(dataset, dataio)


