#!/usr/bin/env python
# encoding: utf-8
"""
utils_plot.py

Created by Loic Matthey on 2013-09-08.
Copyright (c) 2013 Gatsby Unit. All rights reserved.
"""

import numpy as np

import scipy.stats as spst
import scipy.interpolate as spint

import matplotlib.pyplot as plt
import matplotlib.patches as plt_patches
import matplotlib.gridspec as plt_grid
import matplotlib.ticker as plttic
from matplotlib import cm
# from matplotlib.ticker import LinearLocator
from matplotlib.colors import LogNorm
from matplotlib.widgets import Slider

import pandas as pd


import utils_math
import utils_fitting
import utils_helper
import utils_interpolate

# switch interactive mode on
plt.ion()

########################## PLOTTING FUNCTIONS #################################

def angle_to_rgb(angle, normalise=True):
    '''
        Convert angle to LAB coordinates, and then LAB to RGB.
    '''

    try:
        N = angle.size
    except AttributeError:
        N = 1

    # Convert angle to LAB
    lab_coord = 50*np.ones((N, 3))
    lab_coord[:, 1] = 20. + 60.*np.sin(angle)
    lab_coord[:, 2] = 20. + 60*np.cos(angle)

    # Convert Lab to RGB
    rgb_coord = lab2rgb(lab_coord)

    # Normalise
    if normalise:
        rgb_coord /= 255.

    return rgb_coord


def lab2rgb(lab):
    '''
        Convert from LAB to RGB

        Converted from Paul Bays
    '''
    V = np.empty((lab.shape[0], 3))

    # Convert CIE L*a*b* to CIE XYZ
    V[:, 1] = (lab[:, 0] + 16) / 116.     # (Y/Yn)^(1/3)
    V[:, 0] = lab[:, 1] / 500. + V[:, 1]    # (X/Xn)^(1/3)
    V[:, 2] = V[:, 1] - lab[:, 2]/200.      # (Z/Zn)^(1/3)

    Z = V**3.

    # Correction for small XYZ
    Z[Z <= 0.008856] = (V[Z <= 0.008856] - 16./116.) / 7.787

    # Adjust for white point (D65, CIE 2 Deg Standard Observer)
    Zn = np.array([95.047, 100.00, 108.883])
    Z *= Zn

    # Convert CIE XYZ to Rec 709 RGB
    M = np.array([[3.2406, -1.5372, -0.4986],
                  [-0.9689, 1.8758, 0.0415],
                  [0.0557, -0.2040, 1.0570]])

    R = np.dot(Z, M.T) / 100.

    # Correct for non-linear output of display
    Q = R*12.92
    Q[R > 0.0031308] = 1.055 * R[R > 0.0031308]**(1./2.4) - 0.055

    # Scale to range 1-255
    C = np.round(Q*255.)
    C[C > 255] = 255
    C[C < 0 ] = 0

    return C

def plot_multiple_mean_std_area(x, y, std, ax_handle=None, fignum=None, linewidth=1, fmt='-', markersize=1, color=None, xlabel=None, ylabel=None, label=''):
    '''
        Plots multiple x-y data with standard error, on the same graph

        Will iterate over the first axis, has to...
    '''
    if ax_handle is None:
        f = plt.figure(fignum)
        ax_handle = f.add_subplot(111)

    if x.ndim == 1:
        # x should be extended, for convenience
        x = np.tile(x, (y.shape[0], 1))

    for curr_plt in xrange(x.shape[0]):
        ax_handle = plot_mean_std_area(x[curr_plt], y[curr_plt], std[curr_plt], ax_handle=ax_handle, linewidth=linewidth, fmt=fmt, markersize=markersize, color=color, xlabel=xlabel, ylabel=ylabel, label=label)

    return ax_handle


def plot_mean_std_area(x, y, std, ax_handle=None, fignum=None, linewidth=1, fmt='-', markersize=1, color=None, xlabel=None, ylabel=None, label='', title=None, zorder=1):
    '''
        Plot a given x-y data, with a transparent area for its standard deviation

        If ax_handle is given, plots on this figure.
    '''

    if ax_handle is None:
        f = plt.figure(fignum)
        ax_handle = f.add_subplot(111)

    ishold = plt.ishold()

    if color is not None:
        ax = ax_handle.plot(x, y, fmt, linewidth=linewidth, markersize=markersize, color=color, label=label, zorder=zorder)
    else:
        ax = ax_handle.plot(x, y, fmt, linewidth=linewidth, markersize=markersize, label=label, zorder=zorder)

    current_color = ax[-1].get_c()

    plt.hold(True)

    if std is not None and np.any(std > 1e-6):
        ax_handle.fill_between(x, y-std, y+std, facecolor=current_color, alpha=0.4, zorder=zorder)

    if xlabel is not None:
        ax_handle.set_xlabel(xlabel)

    if ylabel is not None:
        ax_handle.set_ylabel(ylabel)

    if title is not None:
        ax_handle.set_title(title)

    ax_handle.get_figure().canvas.draw()

    plt.hold(ishold)

    return ax_handle


def plot_multiple_median_quantile_area(x, y=None, quantiles=None, axis=-1, ax_handle=None, fignum=None):
    '''
        Plots multiple x-y data with median and quantiles, on the same graph

        Will iterate over the first axis, has to...

        Assume that you give either the raw data in y, or the quantiles.
    '''

    assert (y is not None or quantiles is not None), "Give either y or quantiles"

    if ax_handle is None:
        f = plt.figure(fignum)
        ax_handle = f.add_subplot(111)

    if x.ndim == 1:
        # x should be extended, for convenience
        if y is not None:
            x = np.tile(x, (y.shape[0], 1))
        else:
            x = np.tile(x, (quantiles.shape[0], 1))

    for curr_plt in xrange(x.shape[0]):
        if y is not None:
            ax_handle = plot_median_quantile_area(x[curr_plt], y[curr_plt], quantiles=None, axis=axis, ax_handle=ax_handle)
        elif quantiles is not None:
            ax_handle = plot_median_quantile_area(x[curr_plt], quantiles=quantiles[curr_plt], axis=axis, ax_handle=ax_handle)


    return ax_handle


def plot_median_quantile_area(x, y=None, quantiles=None, axis=-1, ax_handle=None, fignum=None):
    """
        Plot the given x-y data, showing the median of y, and its 25 and 75 quantiles as a shaded area

        If ax_handle is given, plots on this figure
    """

    assert (y is not None or quantiles is not None), "Give either y or quantiles"

    if quantiles is None:
        quantiles = spst.mstats.mquantiles(y, axis=axis, prob=[0.25, 0.5, 0.75])

    if ax_handle is None:
        f = plt.figure(fignum)
        ax_handle = f.add_subplot(111)

    ax = ax_handle.plot(x, quantiles[..., 1])

    current_color = ax[-1].get_c()

    ax_handle.fill_between(x, quantiles[..., 0], quantiles[..., 2], facecolor=current_color, alpha=0.4,
                        label='quantile')

    ax_handle.get_figure().canvas.draw()

    return ax_handle


def semilogy_mean_std_area(x, y, std, ax_handle=None, fignum=None):
    if ax_handle is None:
        f = plt.figure(fignum)
        ax_handle = f.add_subplot(111)

    ax = ax_handle.semilogy(x, y)
    current_color = ax[-1].get_c()

    y_p = y+std
    y_m = y-std
    y_m[y_m < 0.0] = y[y_m < 0.0]

    ax_handle.fill_between(x, y_m, y_p, facecolor=current_color, alpha=0.4,
                        label='1 sigma range')

    return ax_handle


def plot_square_grid(x, y, nb_to_plot=-1):
    '''
        Construct a square grid of plots

        Uses the first dimension as number of subplots.
    '''
    if nb_to_plot < 0:
        nb_to_plot = y.shape[0]

    nb_plots_sqrt = np.round(np.sqrt(nb_to_plot)).astype(np.int32)
    f, subaxes = plt.subplots(nb_plots_sqrt, nb_plots_sqrt)

    for i in xrange(nb_plots_sqrt):
        for j in xrange(nb_plots_sqrt):
            try:
                subaxes[i, j].plot(x[nb_plots_sqrt*i+j], y[nb_plots_sqrt*i+j])
                subaxes[i, j].xaxis.set_major_locator(plttic.NullLocator())
                subaxes[i, j].yaxis.set_major_locator(plttic.NullLocator())
            except IndexError:
                subaxes[i, j].set_visible(False)

    return (f, subaxes)


def plot_mean_std_from_samples(x, y, bins=100, bins_y=100, xlabel='', ylabel='', title='', ax_handle=None, nb_stddev=1., show_scatter=False):
    '''
        Given a set of (x, y) variables, will estimate a mean and std through 'x'.
        Should give how many bins you want on the x axis (this will affect the fit)
        Do a 2d histogram to solve that.
    '''

    if ax_handle is None:
        f, ax_handle = plt.subplots()
    else:
        f = ax_handle.get_figure()

    cnts_hist, x_edges, y_edges = np.histogram2d(x, y, bins=[bins, bins_y])
    x_centers = (x_edges + np.diff(x_edges)[0]/2.)[:-1]
    y_centers = (y_edges + np.diff(y_edges)[0]/2.)[:-1]

    # Now compute mean and std by repeating the y_centers.
    # There should be a better way but I can't find it, it's late....
    binned_data = [np.repeat(y_centers, cnts_hist[i].astype(int)) for i in xrange(bins)]
    data_mean = np.array([np.mean(curr_data) for curr_data in binned_data])
    data_std = np.array([np.std(curr_data) for curr_data in binned_data])

    plot_mean_std_area(x_centers, data_mean, nb_stddev*data_std, ax_handle=ax_handle, xlabel=xlabel, ylabel=ylabel, title=title)

    if show_scatter:
        ax_handle.plot(x, y, '.k')

    f.canvas.draw()


def plot_mean_std_from_samples_rolling(x, y, window=25, xlabel='', ylabel='', title='', ax_handle=None, nb_stddev=1., show_scatter=False):
    '''
        Given a set of (x, y) data, will estimate mean and std through x.

        Uses Pandas and rolling mean and std to get that.
    '''

    # Construct a Dataframe, and appy rolling mean and std
    data_pd = pd.DataFrame(data=y, index=x)
    data_pd = data_pd.sort()

    data_mean = data_pd.rolling(window=window, center=True).mean()
    data_std = data_pd.rolling(window=window, center=True).std()

    # Now plot
    if ax_handle is None:
        f, ax_handle = plt.subplots()
    else:
        f = ax_handle.get_figure()

    plot_mean_std_area(data_mean.index.values.astype('float'), np.ma.masked_invalid(np.array(data_mean).flatten()), nb_stddev*np.ma.masked_invalid(np.array(data_std)).flatten(), ax_handle=ax_handle, xlabel=xlabel, ylabel=ylabel, title=title)

    if show_scatter:
        ax_handle.scatter(x, y, s=2, color='k')

    ax_handle.set_xlim([np.min(x), np.max(x)])
    ax_handle.set_ylim([np.min(y), np.max(y)])

    f.canvas.draw()


def hist_angular_data(data, bins=20, alpha=1.0, in_degrees=False, title=None, norm='density', fignum=None, ax_handle=None, pretty_xticks=False):
    '''
        Histogram for angular data.
        Can set additional properties automatically.

        bins: number of bins.
        norm: {max, sum, density}
    '''

    if in_degrees:
        bound_x = 180.
        data *= 180./np.pi
    else:
        bound_x = np.pi

    bar_heights, x, bins = utils_math.histogram_binspace(data, bins=bins, norm=norm, bound_x=bound_x)

    if ax_handle is None:
        f = plt.figure(fignum)
        ax_handle = f.add_subplot(1, 1, 1)

    ax_handle.bar(x, bar_heights, alpha=alpha, width=2.*bound_x/(bins-1), align='center')

    if title:
        ax_handle.set_title(title)
    ax_handle.set_xlim([x[0]-bound_x/(bins-1), x[-1]+bound_x/(bins-1)])

    if pretty_xticks:
        ax_handle.set_xticks((-np.pi, -np.pi/2, 0, np.pi/2., np.pi))
        ax_handle.set_xticklabels((r'$-\pi$', r'$-\frac{\pi}{2}$', r'$0$', r'$\frac{\pi}{2}$', r'$\pi$'), fontsize=16)


    ax_handle.get_figure().canvas.draw()

    return ax_handle


def hist_samples_density_estimation(samples, bins=50, ax_handle=None, title=None, show_parameters=True, dataio=None, filename=''):
    '''
        Take samples (assumed angular), fit a Kernel Density Estimator and a Von Mises Distribution on them, plot the results on top of each other
    '''

    if ax_handle is None:
        _, ax_handle = plt.subplots()

    # KDE fit
    import statsmodels.nonparametric.kde as stmokde
    samples_kde = stmokde.KDEUnivariate(samples)
    samples_kde.fit()

    # Von Mises fit
    samples_vonmises = utils_fitting.fit_vonmises_samples(samples, num_points=300, return_fitted_data=True, should_plot=False)

    # Plots
    ax_handle.hist(samples, bins=bins, normed=True)
    ax_handle.plot(samples_vonmises['support'], samples_vonmises['fitted_data'], 'r', linewidth=3)
    ax_handle.plot(samples_kde.support, samples_kde.density, 'g', linewidth=3)
    ax_handle.set_xlim([-np.pi, np.pi])

    if title is not None:
        ax_handle.set_title(title)

    if show_parameters:
        ax_handle.text(0.98, 0.95, "mu: %.2f, kappa:%.2f" % tuple(samples_vonmises['parameters'].tolist()), transform=ax_handle.transAxes, horizontalalignment='right')

    ax_handle.get_figure().canvas.draw()

    if dataio is not None:
        # Save the figure
        dataio.save_current_figure(filename)

    return ax_handle


def plot_hists_bias_nontargets(errors_nitems_nontargets, bins=20, label_nontargets='', label_nontargets_all='', label='', dataio=None, remove_first_column=False):
    '''
        Do multiple plots showing the histograms and density estimations for errors to nontargets
    '''

    if label_nontargets == '':
        label_nontargets = label
    if label_nontargets_all == '':
        label_nontargets_all = label

    angle_space = np.linspace(-np.pi, np.pi, bins)

    # Plot histogram to new nontargets
    for n_items_i in xrange(errors_nitems_nontargets.shape[0]):
        if remove_first_column:
            errors_to_nontargets = utils_math.dropnan(errors_nitems_nontargets[n_items_i][..., 1:])
        else:
            errors_to_nontargets = utils_math.dropnan(errors_nitems_nontargets[n_items_i])
        hist_samples_density_estimation(errors_to_nontargets, bins=angle_space, title='N=%d, %d Non-target %s' % (n_items_i+2, n_items_i+1, label_nontargets), dataio=dataio, filename='hist_bias_nontargets_%ditems_%s_{label}_{unique_id}.pdf' % (n_items_i+2, label_nontargets))

    # Get histogram of bias to nontargets, for all items number
    if remove_first_column:
        errors_to_nontargets_all = np.array(utils_helper.flatten_list([utils_math.dropnan(errors_nitems_nontargets[n_items_i][..., 1:]) for n_items_i in xrange(errors_nitems_nontargets.shape[0])]))

    else:
        # errors_to_nontargets_all = utils_math.dropnan(errors_nitems_nontargets)
        errors_to_nontargets_all = np.array(utils_helper.flatten_list([utils_math.dropnan(errors_nitems_nontargets[n_items_i]) for n_items_i in xrange(errors_nitems_nontargets.shape[0])]))

    hist_samples_density_estimation(errors_to_nontargets_all, bins=angle_space, title='Error to nontarget, all %s' % label_nontargets_all, dataio=dataio, filename='hist_bias_nontargets_allitems_%s_{label}_{unique_id}.pdf' % (label_nontargets_all))


def pcolor_2d_data(data, x=None, y=None, xlabel='', ylabel='', title='', colorbar=True, ax_handle=None, label_format="%.2f", xlabel_format=None, ylabel_format=None, fignum=None, interpolation='nearest', log_scale=False, ticks_interpolate=None, cmap=None, vmin=None, vmax=None):
    '''
        Plots a Pcolor-like 2d grid plot. Can give x and y arrays, which will provide ticks.

        Options:
         x                  array for x values
         y                  array for y values
         {x,y}_label        labels for axes
         log_scale          True for log scale of axis
         ticks_interpolate  If set, number of ticks to use instead of the x/y
                            values directly
    '''

    if xlabel_format is None:
        xlabel_format = label_format
    if ylabel_format is None:
        ylabel_format = label_format

    if ax_handle is None:
        f = plt.figure(fignum)
        ax_handle = f.add_subplot(111)
        ax_handle.clear()
    else:
        plt.figure(ax_handle.get_figure().number)

    if len(ax_handle.get_images()) > 0:
        # Update the data if the figure is already filled

        im = ax_handle.get_images()[0]
        im.set_data(data.T)
        im.set_clim(vmin=np.nanmin(data), vmax=np.nanmax(data))
        im.changed()

        # Change mouse over behaviour
        def report_pixel(x_mouse, y_mouse):
            # Extract loglik at that position

            try:
                x_i = int(np.round(x_mouse))
                y_i = int(np.round(y_mouse))

                if x is not None:
                    x_display = x[x_i]
                else:
                    x_display = x_i

                if y is not None:
                    y_display = y[y_i]
                else:
                    y_display = y_i

                return "x=%.2f y=%.2f value=%.2f" % (x_display, y_display, data[x_i, y_i])
            except:
                return ""

        ax_handle.format_coord = report_pixel


    else:
        # Create the Figure
        if log_scale:
            im = ax_handle.imshow(data.T, interpolation=interpolation, origin='lower left', norm=LogNorm(), cmap=cmap)
        else:
            im = ax_handle.imshow(data.T, interpolation=interpolation, origin='lower left', cmap=cmap, vmin=vmin, vmax=vmax)

        if x is not None:
            assert data.shape[0] == x.size, 'Wrong x dimension'

            if not ticks_interpolate is None:
                selected_ticks = np.array(np.linspace(0, x.size-1, ticks_interpolate), dtype=int)
                ax_handle.set_xticks(selected_ticks)
                ax_handle.set_xticklabels([xlabel_format % x[tick_i] for tick_i in selected_ticks], rotation=90)
            else:
                ax_handle.set_xticks(np.arange(x.size))
                ax_handle.set_xticklabels([xlabel_format % curr for curr in x], rotation=90)

        if y is not None:
            assert data.shape[1] == y.size, 'Wrong y dimension'

            if ticks_interpolate is not None:
                selected_ticks = np.array(np.linspace(0, y.size-1, ticks_interpolate), dtype=int)
                ax_handle.set_yticks(selected_ticks)
                ax_handle.set_yticklabels([ylabel_format % y[tick_i] for tick_i in selected_ticks])
            else:
                ax_handle.set_yticks(np.arange(y.size))
                ax_handle.set_yticklabels([ylabel_format % curr for curr in y])

        if xlabel:
            ax_handle.set_xlabel(xlabel)

        if ylabel:
            ax_handle.set_ylabel(ylabel)

        if colorbar:
            ax_handle.get_figure().colorbar(im, ax=ax_handle)

        if title:
            ax_handle.set_title(title)

        ax_handle.axis('tight')

        ## Change mouse over behaviour
        def report_pixel(x_mouse, y_mouse, format="%.2f"):
            # Extract loglik at that position

            try:
                x_i = int(np.round(x_mouse))
                y_i = int(np.round(y_mouse))

                if x is not None:
                    x_display = x[x_i]
                else:
                    x_display = x_i

                if y is not None:
                    y_display = y[y_i]
                else:
                    y_display = y_i

                return ("x=%.2f y=%.2f value="+format) % (x_display, y_display, data[x_i, y_i])
            except:
                return ""

        ax_handle.format_coord = report_pixel

        ## Change mouse click behaviour
        def onclick(event):
            # print 'button=%d, x=%d, y=%d, xdata=%f, ydata=%f'%(event.button, event.x, event.y, event.xdata, event.ydata)
            print report_pixel(event.xdata, event.ydata, format="%f")

        cid = ax_handle.get_figure().canvas.mpl_connect('button_press_event', onclick)

    # redraw
    ax_handle.get_figure().canvas.draw()

    return ax_handle, im



def contourf_interpolate_data(all_points, data, xlabel='', ylabel='', title='', interpolation_numpoints=200, interpolation_method='linear', mask_when_nearest=True, contour_numlevels=20, show_scatter=True, show_colorbar=True, fignum=None, ax_handle=None, mask_x_condition=None, mask_y_condition=None, log_scale=False):
    '''
        Take (x,y) and z tuples, construct an interpolation with them and plot them nicely.

        all_points: Nx2
        data:       Nx1

        mask_when_nearest: trick to hide points outside the convex hull of points even when using 'nearest' method
    '''

    assert all_points.shape[1] == 2, "Give a Nx2 matrix for all_points"

    # Construct the interpolation
    param1_space_int = np.linspace(all_points[:, 0].min(), all_points[:, 0].max(), interpolation_numpoints)
    param2_space_int = np.linspace(all_points[:, 1].min(), all_points[:, 1].max(), interpolation_numpoints)

    data_interpol = spint.griddata(all_points, data, (param1_space_int[None, :], param2_space_int[:, None]), method=interpolation_method)

    if interpolation_method == 'nearest' and mask_when_nearest:
        # Let's mask the points outside of the convex hull

        # The linear interpolation will have nan's on points outside of the convex hull of the all_points
        data_interpol_lin = spint.griddata(all_points, data, (param1_space_int[None, :], param2_space_int[:, None]), method='linear')

        # Mask
        data_interpol[np.isnan(data_interpol_lin)] = np.nan

    # Mask it based on some conditions
    if mask_x_condition is not None:
        data_interpol[mask_x_condition(param1_space_int), :] = 0.0
    if mask_y_condition is not None:
        data_interpol[:, mask_y_condition(param2_space_int)] = 0.0

    # Plot it
    if ax_handle is None:
        f = plt.figure(fignum)
        ax_handle = f.add_subplot(111)
    else:
        f = ax_handle.get_figure()
        f.clf()
        ax_handle = f.add_subplot(111)

    if log_scale:
        cs = ax_handle.contourf(param1_space_int, param2_space_int, data_interpol, contour_numlevels, locator=plttic.LogLocator())   # cmap=plt.cm.jet
    else:
        cs = ax_handle.contourf(param1_space_int, param2_space_int, data_interpol, contour_numlevels)   # cmap=plt.cm.jet
    ax_handle.set_xlabel(xlabel)
    ax_handle.set_ylabel(ylabel)
    ax_handle.set_title(title)

    if show_scatter:
        ax_handle.scatter(all_points[:, 0], all_points[:, 1], marker='o', c='b', s=5)

    ax_handle.set_xlim(param1_space_int.min(), param1_space_int.max())
    ax_handle.set_ylim(param2_space_int.min(), param2_space_int.max())

    if show_colorbar:
        f.colorbar(cs)

    return ax_handle


def contour3d_interpolate_data(all_points, data, xlabel='', ylabel='', title='', interpolation_numpoints=200j, interpolation_method='linear', mask_when_nearest=True, contour_numlevels=20, show_scatter=True, show_colorbar=True, fignum=None, ax_handle=None, mask_x_condition=None, mask_y_condition=None, mask_z_condition=None, log_scale=False, use_mayavi=True):
    '''
        Take (x,y,z) and f tuples, construct an interpolation with them and plot them nicely.

        all_points: Nx3
        data:       Nx1

        mask_when_nearest: trick to hide points outside the convex hull of points even when using 'nearest' method
    '''

    # Construct the interpolation
    X, Y, Z = np.mgrid[all_points[:, 0].min():all_points[:, 0].max():interpolation_numpoints, all_points[:, 1].min():all_points[:, 1].max():interpolation_numpoints, all_points[:, 2].min():all_points[:, 2].max():interpolation_numpoints]
    data_interpol = spint.griddata(all_points, data, (X, Y, Z), method=interpolation_method)

    # if interpolation_method == 'nearest' and mask_when_nearest:
    #     # Let's mask the points outside of the convex hull

    #     # The linear interpolation will have nan's on points outside of the convex hull of the all_points
    #     data_interpol_lin = spint.griddata(all_points, data, (param1_space_int[None, :], param2_space_int[:, None]), method='linear')

    #     # Mask
    #     data_interpol[np.isnan(data_interpol_lin)] = np.nan

    # # Mask it based on some conditions
    # if not mask_x_condition is None:
    #     data_interpol[mask_x_condition(param1_space_int), :] = 0.0
    # if not mask_y_condition is None:
    #     data_interpol[:, mask_y_condition(param2_space_int)] = 0.0

    # Plot it
    if use_mayavi:
        try:
            import mayavi.mlab as mlab3d
        except:
            # Faaailed
            use_mayavi = False

    if use_mayavi:

        # Normalise stuff
        X_norm = X/X.max()
        Y_norm = Y/Y.max()
        Z_norm = Z/Z.max()
        all_points_norm = all_points/np.max(all_points, axis=0)

        mlab3d.figure(bgcolor=(1.0, 1.0, 1.0))
        # mlab3d.figure()

        # TODO Try to do a dynamic contour2D on a plan!

        # mlab3d.contour3d(X_norm, Y_norm, Z_norm, np.log(data_interpol), contours=contour_numlevels, opacity=0.5)
        # mlab3d.axes(color=(0.0, 0.0, 0.0))

        # if show_scatter:
        mlab3d.points3d(all_points_norm[:, 0], all_points_norm[:, 1], all_points_norm[:, 2], np.log(fitness), scale_mode='none', scale_factor=0.03)

        if show_colorbar:
            mlab3d.colorbar(title='', orientation='vertical', label_fmt='%.2f', nb_labels=5)

        # mlab3d.outline(color=(0., 0., 0.))

        mlab3d.show()
    else:
        raise NotImplementedError('matplotlib 3d has no contour3d function...')


def contourf_interpolate_data_interactive_maxvalue(all_points, data, xlabel='', ylabel='', title='', interpolation_numpoints=200, interpolation_method='linear', mask_when_nearest=True, contour_numlevels=20, show_scatter=True, show_colorbar=True, fignum=None, ax_handle=None, mask_x_condition=None, mask_y_condition=None, log_scale=False, mask_smaller_than=None, mask_greater_than=None, show_slider=True):
    '''
        Take (x,y) and z tuples, construct an interpolation with them and plot them nicely.

        all_points: Nx2
        data:       Nx1

        mask_when_nearest: trick to hide points outside the convex hull of points even when using 'nearest' method
    '''

    assert all_points.shape[1] == 2, "Give a Nx2 matrix for all_points"

    # Construct the interpolation
    param1_space_int = np.linspace(all_points[:, 0].min(), all_points[:, 0].max(), interpolation_numpoints)
    param2_space_int = np.linspace(all_points[:, 1].min(), all_points[:, 1].max(), interpolation_numpoints)

    data_interpol = utils_interpolate.interpolate_data_2d(all_points, np.ma.masked_greater(data, data.max()), param1_space_int=param1_space_int, param2_space_int=param2_space_int, interpolation_numpoints=interpolation_numpoints, interpolation_method=interpolation_method, mask_when_nearest=mask_when_nearest, mask_x_condition=mask_x_condition, mask_y_condition=mask_y_condition, mask_smaller_than=mask_smaller_than, mask_greater_than=mask_greater_than)

    parameters = locals()

    # Plot it
    def __plot__(parameters, max_value, plot_min=True):

        # Construct the figure
        if parameters['ax_handle'] is None:
            f = plt.figure()
        else:
            f = parameters['ax_handle'].get_figure()
            f.clf()

        parameters['ax_handle'] = f.add_subplot(111)
        if show_slider:
            f.subplots_adjust(bottom=0.25)

        if log_scale:
            cs = parameters['ax_handle'].contourf(parameters['param1_space_int'], parameters['param2_space_int'], parameters['data_interpol'], parameters['contour_numlevels'], locator=plttic.LogLocator())   # cmap=plt.cm.jet
        else:
            cs = parameters['ax_handle'].contourf(parameters['param1_space_int'], parameters['param2_space_int'], parameters['data_interpol'], parameters['contour_numlevels'])   # cmap=plt.cm.jet
        parameters['ax_handle'].set_xlabel(parameters['xlabel'])
        parameters['ax_handle'].set_ylabel(parameters['ylabel'])
        parameters['ax_handle'].set_title(parameters['title'])

        if show_scatter:
            parameters['ax_handle'].scatter(parameters['all_points'][:, 0], parameters['all_points'][:, 1], marker='o', c='b', s=5)

            if plot_min:
                index_min = np.argmin(parameters['data'])
                parameters['ax_handle'].scatter(parameters['all_points'][index_min, 0], parameters['all_points'][index_min, 1], marker='o', c='r', s=15)

        parameters['ax_handle'].set_xlim(parameters['param1_space_int'].min(), parameters['param1_space_int'].max())
        parameters['ax_handle'].set_ylim(parameters['param2_space_int'].min(), parameters['param2_space_int'].max())

        if parameters['show_colorbar']:
            parameters['ax_handle'].get_figure().colorbar(cs)

        ### Add interactive slider
        if show_slider:
            # axcolor = 'lightgoldenrodyellow'
            ax_slider_max = plt.axes([0.1, 0.1, 0.75, 0.04])
            slider_max = Slider(ax_slider_max, 'Max', parameters['data'].min(), parameters['data'].max(), valinit=max_value)
            # parameters['ax_handle'].get_figure().sca(parameters['ax_handle'])

            def update_max(val):

                new_max = slider_max.val
                print 'Changed max: %.2f' % new_max

                # Recompute interpolation
                data_limited_ = np.ma.masked_greater(parameters['data'], new_max)
                parameters['data_interpol'] = utils_interpolate.interpolate_data_2d(parameters['all_points'], data_limited_, parameters['param1_space_int'], parameters['param2_space_int'], parameters['interpolation_numpoints'], parameters['interpolation_method'], parameters['mask_when_nearest'], parameters['mask_x_condition'], parameters['mask_y_condition'])

                # clean figure
                # parameters['ax_handle'].get_figure().subplots_adjust(right=1.1)
                # parameters['ax_handle'].get_figure().clf()

                __plot__(parameters, new_max)

                parameters['ax_handle'].get_figure().canvas.draw()

            slider_max.on_changed(update_max)

        ## Change mouse over behaviour
        def report_pixel(x_mouse, y_mouse, format="%.2f"):
            # Extract loglik at that position
            try:
                x_i = int(parameters['param2_space_int'].size*x_mouse)
                y_i = int(parameters['param1_space_int'].size*y_mouse)

                x_display = parameters['param2_space_int'][x_i]
                y_display = parameters['param1_space_int'][y_i]

                return ("x=%.2f y=%.2f value="+format) % (x_display, y_display, parameters['data_interpol'][y_i, x_i])
            except:
                return ""
        parameters['ax_handle'].format_coord = report_pixel

        ## Change mouse click behaviour
        def onclick(event):
            # print 'button=%d, x=%d, y=%d, xdata=%f, ydata=%f'%(event.button, event.x, event.y, event.xdata, event.ydata)
            report_str = report_pixel(event.xdata, event.ydata, format="%f")
            if report_str:
                print report_str

        parameters['ax_handle'].get_figure().canvas.mpl_connect('button_press_event', onclick)

        parameters['ax_handle'].get_figure().canvas.draw()

        return parameters['ax_handle']

    ax_handle = __plot__(parameters, data.max())

    return ax_handle


def pcolor_square_grid(data, nb_to_plot=-1):
    '''
        Construct a square grid of pcolor

        Uses the first dimension as number of subplots.
    '''
    if nb_to_plot < 0:
        nb_to_plot = data.shape[0]

    nb_plots_sqrt = np.ceil(np.sqrt(nb_to_plot)).astype(int)
    f, subaxes = plt.subplots(nb_plots_sqrt, nb_plots_sqrt)

    for i in xrange(nb_plots_sqrt):
        for j in xrange(nb_plots_sqrt):
            try:
                subaxes[i, j].imshow(data[nb_plots_sqrt*i+j], interpolation='nearest')
                subaxes[i, j].xaxis.set_major_locator(plttic.NullLocator())
                subaxes[i, j].yaxis.set_major_locator(plttic.NullLocator())
            except IndexError:
                subaxes[i, j].set_visible(False)

    return (f, subaxes)


def pcolor_line_grid(data, nb_to_plot=-1):
    '''
        Construct a line of pcolor

        Uses the first dimension as number of subplots.
    '''
    if nb_to_plot < 0:
        nb_to_plot = data.shape[0]

    f, subaxes = plt.subplots(nb_to_plot, 1, squeeze=False)

    for i in xrange(nb_to_plot):
        try:
            subaxes[i, 0].imshow(data[i], interpolation='nearest')
            subaxes[i, 0].xaxis.set_major_locator(plttic.NullLocator())
            subaxes[i, 0].yaxis.set_major_locator(plttic.NullLocator())
        except IndexError:
            subaxes[i, 0].set_visible(False)

    return (f, subaxes)


def plot_sphere(theta, gamma, Z, weight_deform=0.5, sphere_radius=1., try_mayavi=True):
    '''
        Plot a sphere, with the color set by Z.
            Also possible to deform the sphere according to Z, by putting a nonzero weight_deform.

        Need theta \in [0, 2pi] and gamma \in [0, pi]
    '''

    Z_norm = Z/Z.max()

    x = sphere_radius * np.outer(np.cos(theta), np.sin(gamma))*(1.+weight_deform*Z_norm)
    y = sphere_radius * np.outer(np.sin(theta), np.sin(gamma))*(1.+weight_deform*Z_norm)
    z = sphere_radius * np.outer(np.ones(np.size(theta)), np.cos(gamma))*(1.+weight_deform*Z_norm)

    # Have fun and try Mayavi for 3D plotting instead. Super faaaast.
    use_mayavi = False
    if try_mayavi:
        try:
            import mayavi.mlab as mplt

            use_mayavi = True
        except:
            pass

    if use_mayavi:
        mplt.figure()
        mplt.mesh(x, y, z, scalars=Z_norm)
        mplt.show()

    else:
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        ax.plot_surface(x, y, z, facecolors=cm.jet(Z_norm), rstride=1, cstride=1, linewidth=0, antialiased=True, shade=False)

        # Colorbar
        m = cm.ScalarMappable(cmap=cm.jet)
        m.set_array(Z_norm)
        plt.colorbar(m)

        plt.show()


def plot_torus(theta, gamma, Z, weight_deform=0., torus_radius=5., tube_radius=3.0, try_mayavi=True, draw_colorbar=True):
    '''
        Plot a torus, with the color set by Z.
            Also possible to deform the sphere according to Z, by putting a nonzero weight_deform.

        Need theta in [0, 2pi] and gamma in [0, pi]
    '''


    Z_norm = Z/Z.max()

    X, Y = np.meshgrid(theta, gamma)
    x = (torus_radius+ tube_radius*np.cos(X)*(1.+weight_deform*Z_norm))*np.cos(Y)
    y = (torus_radius+ tube_radius*np.cos(X)*(1.+weight_deform*Z_norm))*np.sin(Y)
    z = tube_radius*np.sin(X)*(1.+weight_deform*Z_norm)

    use_mayavi = False
    if try_mayavi:
        try:
            import mayavi.mlab as mplt

            use_mayavi = True
        except:
            pass

    if use_mayavi:
        # mplt.figure(bgcolor=(0.7,0.7,0.7))
        mplt.figure(bgcolor=(1.0, 1.0, 1.0))
        mplt.mesh(x, y, z, scalars=Z_norm, vmin=0.0)

        if draw_colorbar:
            cb = mplt.colorbar(title='', orientation='vertical', label_fmt='%.2f', nb_labels=5)

        mplt.outline(color=(0., 0., 0.))
        mplt.draw()

    else:
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        ax.plot_surface(x, y, z, facecolors=cm.jet(Z_norm), rstride=1, cstride=1, linewidth=0, antialiased=True, shade=False)

        # Colorbar
        m = cm.ScalarMappable(cmap=cm.jet)
        m.set_array(Z_norm)

        if draw_colorbar:
            plt.colorbar(m)

        # plt.show()


def scatter3d(x, y, z, s=20, c='b', title='', xlabel='', ylabel='', zlabel='', ax_handle=None):
    '''
        Plot a scatter of points in 3d

        Input:
            X, Y, Z
            S: either scalar size of points or array of sizes.
            C: either string color, or mappable array
    '''

    if ax_handle is None:
        fig = plt.figure()
        ax_handle = fig.add_subplot(111, projection='3d')
    else:
        # plt.close(ax_handle.get_figure().number)
        # fig = plt.figure()
        # ax_handle = fig.add_subplot(111, projection='3d')
        pass

    ax_handle.scatter(x, y, z, s=s, c=c)

    if title:
        ax_handle.set_title(title)
    if xlabel:
        ax_handle.set_xlabel(xlabel)
    if ylabel:
        ax_handle.set_ylabel(ylabel)
    if zlabel:
        ax_handle.set_zlabel(zlabel)

    ax_handle.get_figure().canvas.draw()

    return ax_handle


def scatter3d_torus(theta, gamma, torus_radius=5., tube_radius=3.0, try_mayavi=True):
    '''
        Plot points on a torus.

        Need theta \in [0, 2pi] and gamma \in [0, pi]
    '''

    x = (torus_radius + tube_radius*np.cos(theta))*np.cos(gamma)
    y = (torus_radius + tube_radius*np.cos(theta))*np.sin(gamma)
    z = tube_radius*np.sin(theta)

    use_mayavi = False
    if try_mayavi:
        try:
            import mayavi.mlab as mplt

            use_mayavi = True
        except:
            pass

    if use_mayavi:
        # mplt.figure(bgcolor=(0.7,0.7,0.7))
        mplt.figure(bgcolor=(1.0, 1.0, 1.0))
        mplt.points3d(x, y, z, scale_factor=1, color=(0.0, 0.2, 0.9))

        mplt.outline(color=(0., 0., 0.))
        mplt.draw()

    else:
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        ax.scatter(x, y, z)

        fig.canvas.draw()

        return ax


def plot_powerlaw_fit(xdata, ydata, amp, index, yerr=None, fignum=None):
    '''
        Plot a powerlaw with some associated datapoints
    '''

    plt.figure(fignum)
    plt.subplot(2, 1, 1)
    plt.plot(xdata, utils_math.powerlaw(xdata, amp, index))     # Fit

    if yerr is None:
        plt.plot(xdata, ydata, 'k.')  # Data
    else:
        plt.errorbar(xdata, ydata, yerr=yerr, fmt='k.')

    plt.title('Best Fit Power Law')
    plt.xlabel('X')
    plt.ylabel('Y')
    plt.xlim((xdata.min()*0.9, xdata.max()*1.1))

    plt.subplot(2, 1, 2)
    plt.loglog(xdata, utils_math.powerlaw(xdata, amp, index))

    if yerr is None:
        plt.plot(xdata, ydata, 'k.')  # Data
    else:
        plt.errorbar(xdata, ydata, yerr=yerr, fmt='k.')

    plt.xlabel('X (log scale)')
    plt.ylabel('Y (log scale)')
    plt.xlim((xdata.min()*0.9, xdata.max()*1.1))


def plot_fft_power(data, dt=1.0, n=None, axis=-1, fignum=None):
    '''
        Compute the FFT and plot the power spectrum.
    '''

    freq = np.fft.fftfreq(data.shape[-1], d=dt)
    FS = np.fft.fft(data, n=n, axis=axis)

    plt.figure(fignum)
    # plt.plot(freq, np.log(np.abs(np.fft.fftshift(FS))**2.))
    plt.plot(freq, np.abs(FS)**2.)
    plt.title('Power spectrum')


def plot_fft2_power(data, s=None, axes=(-2, -1), fignum=None):
    '''
        Compute the 2D FFT and plot the 2D power spectrum.
    '''

    FS = np.fft.fft2(data, s=s, axes=axes)

    plt.figure(fignum)
    plt.imshow(np.log(np.abs(np.fft.fftshift(FS))**2.))
    plt.title('Power spectrum')
    plt.colorbar()


def scatter_marginals(xdata, ydata, xlabel='', ylabel='', title='', scatter_marker='x', bins=50, factor_axis=1.1, fignum=None, figsize=None, show_colours=False):
    '''
        Plot the scattered distribution of (x, y), add the marginals as two subplots
    '''

    assert np.all(~np.isnan(xdata)) and np.all(~np.isnan(ydata)), "Xdata and Ydata should not contain NaNs"

    f = plt.figure(fignum, figsize=figsize)

    # Construct a grid of 2x2 axes, changing their ratio
    gs = plt_grid.GridSpec(2, 2, width_ratios=[1, 3], height_ratios=[3, 1])

    # First plot the 2D distribution
    ax = plt.subplot(gs[1])
    ax.scatter(xdata, ydata, marker=scatter_marker)
    ax.set_xlim((-np.pi*factor_axis, np.pi*factor_axis))
    ax.set_ylim((-np.pi*factor_axis, np.pi*factor_axis))
    ax.set_title(title)

    # Show colours on color plot, near axis
    # transform angles to RGB, and then plot small patches, near the axis. Automatically determine the width of those, to match the plot dimensions. Could adapt it to put the patches outside, not sure...
    if show_colours:
        thetas = np.linspace(-np.pi, np.pi, 100)
        dtheta = np.diff(thetas)[0]
        rgb_theta = angle_to_rgb(thetas)
        for theta_i, theta in enumerate(thetas):
            ax.add_patch(plt_patches.Rectangle((theta, -np.pi*factor_axis), dtheta, np.pi*0.9*(factor_axis - 1.0), color=rgb_theta[theta_i]))
            ax.add_patch(plt_patches.Rectangle((-np.pi*factor_axis, theta), np.pi*0.9*(factor_axis - 1.0), dtheta, color=rgb_theta[theta_i]))

    # Plot the marginals below and on the left. Bin everything.
    ax = plt.subplot(gs[0])
    plt.xticks(rotation=45)
    (counts_y, bin_edges) = np.histogram(ydata, bins=bins, normed=True)
    ax.barh(bin_edges[1:], counts_y, height=np.diff(bin_edges)[0])
    ax.invert_xaxis()
    ax.set_ylim((-np.pi*factor_axis, np.pi*factor_axis))

    ax.set_ylabel(ylabel)

    ax = plt.subplot(gs[3])
    (counts_x, bin_edges) = np.histogram(xdata, bins=bins, normed=True)
    ax.bar(bin_edges[1:], counts_x, width=np.diff(bin_edges)[0])
    ax.set_xlim((-np.pi*factor_axis, np.pi*factor_axis))

    ax.set_xlabel(xlabel)

    return f


def plot_vonmises_pdf(x, kappa, mu=0.0, scale=1.0, ax_handle=None, fignum=None, linewidth=1, fmt='-', markersize=1, color=None, xlabel=None, ylabel=None, label=''):
    '''
        Estimate the PDF of a Von Mises on the provided support.

        Plot it.
    '''

    ## Get PDF of Von Mises
    y_pdf = spst.vonmises.pdf(x, kappa, loc=mu, scale=1.0)

    # Correct the scale if needed
    if scale != 1.0:
        y_pdf /= np.max(y_pdf)/scale

    ## Plot it
    if ax_handle is None:
        f = plt.figure(fignum)
        ax_handle = f.add_subplot(111)

    if color is not None:
        ax = ax_handle.plot(x, y_pdf, fmt, linewidth=linewidth, markersize=markersize, color=color, label=label)
    else:
        ax = ax_handle.plot(x, y_pdf, fmt, linewidth=linewidth, markersize=markersize, label=label)

    if xlabel is not None:
        ax_handle.set_xlabel(xlabel)

    if ylabel is not None:
        ax_handle.set_ylabel(ylabel)

    ax_handle.get_figure().canvas.draw()


def plot_normal_pdf(x, mu=0.0, std=1.0, scale=1.0, ax_handle=None, fignum=None, linewidth=1, fmt='-', markersize=1, color=None, xlabel=None, ylabel=None, label=''):
    '''
        Estimate the PDF of a Normal on the provided support.

        Plot it.
    '''

    ## Get PDF of Von Mises
    y_pdf = spst.norm.pdf(x, loc=mu, scale=std)

    # Correct the scale if needed
    if scale != 1.0:
        y_pdf /= np.max(y_pdf)/scale

    ## Plot it
    if ax_handle is None:
        f = plt.figure(fignum)
        ax_handle = f.add_subplot(111)

    if color is not None:
        ax = ax_handle.plot(x, y_pdf, fmt, linewidth=linewidth, markersize=markersize, color=color, label=label)
    else:
        ax = ax_handle.plot(x, y_pdf, fmt, linewidth=linewidth, markersize=markersize, label=label)

    if xlabel is not None:
        ax_handle.set_xlabel(xlabel)

    if ylabel is not None:
        ax_handle.set_ylabel(ylabel)

    ax_handle.get_figure().canvas.draw()


