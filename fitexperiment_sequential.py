#!/usr/bin/env python
# encoding: utf-8
"""
fitexperimentAllT.py

Created by Loic Matthey on 2013-09-26.
Copyright (c) 2013 Gatsby Unit. All rights reserved.
"""

import os

import numpy as np

# import scipy as sp
# import scipy.optimize as spopt
# import scipy.stats as spst

# import progress

import experimentlauncher
import launchers
import load_experimental_data
import utils


class FitExperimentSequentialSubjectAll(object):
    '''
        Loads sequential experimental data, set up DataGenerator and associated RFN, Sampler to optimize parameters.

        This version loads a unique dataset and will automatically run processings over all the possible nitems in it.
    '''

    def __init__(self, parameters={}, debug=True):
        '''
            FitExperimentSequentialAll takes a parameters dict, same as a full launcher_

            Will then instantiate a Sampler and force a specific DataGenerator with constrained data from human experimental data.

            Requires experiment_id to be set.
        '''

        self.enforced_T = -1
        self.enforced_trecall = -1
        self.sampler = None
        self.all_samplers = dict()
        self.cache_responses = dict()
        self.experimental_dataset = None
        self.experiment_data_to_fit = None
        self.T_space = None
        self.num_datapoints = -1
        self.em_fits_arrays = None

        self.subject = parameters.get('experiment_subject', 0)
        self.parameters = parameters
        self.debug = debug

        self.experiment_id = parameters.get('experiment_id', '')
        self.data_dir = parameters.get('experiment_data_dir',
                                       os.path.normpath(os.path.join(
                                           os.environ['WORKDIR_DROP'],
                                           '../../experimental_data/'))
                                       )

        # Load data
        self.load_dataset()

        # Handle limiting the number of datapoints
        self.init_filter_datapoints()

        if self.debug:
            print "FitExperimentSequentialSubjectAll: subject %d, %s dataset. %d datapoints" % (
                (self.subject, self.experiment_id, self.num_datapoints))


    def load_dataset(self):
        '''
            Load and select dataset given the parameters.
        '''
        assert self.experiment_id == 'gorgo11_sequential', "Only this one supported here"
        self.experimental_dataset = load_experimental_data.load_data(
            experiment_id=self.experiment_id,
            data_dir=self.data_dir,
            fit_mixture_model=True
        )
        self.subject_space = self.experimental_dataset['data_subject_split']['subjects_space']
        assert self.subject in self.subject_space, "Subject id not found in dataset!"

        self.experiment_data_to_fit = self.experimental_dataset['data_subject_split']['data_subject_nitems_trecall'][self.subject]
        self.T_space = self.experimental_dataset['data_subject_split']['nitems_space']
        self.num_datapoints = int(self.experimental_dataset['data_subject_split']['subject_smallestN'][self.subject - 1])

    def init_filter_datapoints(self):
        '''
            To speed things up, we may want to limit how many datapoints we actually use (per T/n_items).

            Check in the parameters dict:
            1) filter_datapoints_size [float] [if <= 1, treated as percent of total dataset size for given item]
            2) filter_datapoints_selection: {random, sequential}
            3) filter_datapoints_mask [array] direct mask to use. (If another FitExperiment already exist?)
        '''

        if 'filter_datapoints_mask' in self.parameters:
            self.filter_datapoints_mask = self.parameters['filter_datapoints_mask']
            self.num_datapoints = self.filter_datapoints_mask.size
        elif self.parameters.get('filter_datapoints_size', -1) > 0:
            selection_method = self.parameters.get('filter_datapoints_selection', 'sequential')
            selection_size = self.parameters.get('filter_datapoints_size', 1.)

            if selection_method == 'sequential':
                if selection_size > 1:
                    self.filter_datapoints_mask = np.arange(
                        min(self.num_datapoints, int(selection_size)))
                else:
                    self.filter_datapoints_mask = np.arange(np.floor(self.num_datapoints*selection_size))
            elif selection_method == 'random':
                if selection_size > 1:
                    self.filter_datapoints_mask = np.random.permutation(np.arange(self.num_datapoints))[:int(selection_size)]
                else:
                    self.filter_datapoints_mask = np.random.permutation(np.arange(self.num_datapoints))[:np.floor(self.num_datapoints*selection_size)]

            self.num_datapoints = self.filter_datapoints_mask.size
        else:
            self.filter_datapoints_mask = slice(0, self.num_datapoints)


    def setup_experimental_stimuli(self, T, trecall):
        '''
            Setup everything needed (Sampler, etc) and then force a human experimental dataset.

            If already setup correctly, do nothing.
        '''

        assert T in self.T_space, "T=%d not possible. %s" % (T, self.T_space)

        if self.enforced_T != T or self.enforced_trecall != trecall:
            self.enforced_T = T
            self.enforced_trecall = trecall

            if (T, trecall) not in self.all_samplers:
                print "\n>>> Setting up {} nitems, {} trecall, {} datapoints".format(T, trecall, self.num_datapoints)

                # Update parameters
                self.parameters['T'] = T
                self.parameters['N'] = self.num_datapoints
                self.parameters['fixed_cued_feature_time'] = trecall - 1

                self.parameters['stimuli_to_use'] = (
                    self.experiment_data_to_fit[T][trecall]['item_features'][
                        self.filter_datapoints_mask])

                # Instantiate everything
                (_, _, _, self.sampler) = launchers.init_everything(self.parameters)

                # Fix responses to the human ones
                self.sampler.set_theta(
                    self.experiment_data_to_fit[T][trecall]['responses'][
                        self.filter_datapoints_mask])
                self.store_responses('human')

                # Store it
                self.all_samplers[(T, trecall)] = self.sampler

            self.sampler = self.all_samplers[
                (self.enforced_T, self.enforced_trecall)]


    def store_responses(self, name):
        '''
            Given a name, will store the current Sampler responses for later.

            Useful to switch between data/samples efficiently.
        '''

        self.cache_responses.setdefault(
            (self.enforced_T, self.enforced_trecall),
            dict())[name] = self.sampler.get_theta().copy()

    def restore_responses(self, name):
        '''
            Will restore the responses to the cached one with the appropriate name
        '''
        assert name in self.cache_responses[
            (self.enforced_T, self.enforced_trecall)], "Response name unknown"
        self.sampler.set_theta(
            self.cache_responses[
                (self.enforced_T, self.enforced_trecall)][name])

    def get_names_stored_responses(self):
        '''
            Returns the list of possible names currently cached.
        '''
        return self.cache_responses[
            (self.enforced_T, self.enforced_trecall)].keys()


    def get_em_fits_arrays(self):
        '''
            Give a numpy array of the current EM Fits.

            Returns:
            * dict(mean=np.array, std=np.array)
        '''

        if self.em_fits_arrays is None:
            self.em_fits_arrays = self.experimental_dataset['collapsed_em_fits_doublepowerlaw']

        return self.em_fits_arrays


    def apply_fct_dataset(self, T, trecall, fct_infos):
        '''
            Apply a function after having forced a specific dataset
            The function will be called as follows:

            result = fct_infos['fct'](self, fct_infos['parameters'])
        '''

        # Set dataset
        self.setup_experimental_stimuli(T, trecall)

        # Apply function
        result = fct_infos['fct'](self, fct_infos.get('parameters', {}))

        return result


    def apply_fct_datasets_all(self, fct_infos, return_array=False):
        '''
            Apply a function on all datasets

            TODO(lmatthey) if setting up dataset is costly, might need to provide a list of fcts and avoid reconstructing the DataGenerator each time.

            result = fct_infos['fct'](self, fct_infos['parameters'])
        '''

        result_all = []
        for T in self.T_space:
            for trecall in range(1, T+1):
                result_all.append(
                    self.apply_fct_dataset(T, trecall, fct_infos))

        if return_array:
            # Bit stupid for now. Might want to handle list of dictionaries, but meh
            result_all_array = np.array(result_all)

            return result_all_array
        else:
            return result_all


    def compute_dist_experimental_em_fits_currentT(self, model_fits):
        '''
            Given provided model_fits array, compute the distance to
            the loaded Experimental Data em fits.

            Inputs:
            * model_fits:   [array 6x1] ['kappa', 'mixt_target', 'mixt_nontargets_sum', 'mixt_random', 'train_LL', 'bic']


            Returns dict:
            * kappa MSE
            * mixture prop MSE
            * summed MSE
            * mixture prop KL divergence
        '''

        distances = dict()

        # TODO (lmatthey): use the EM Fits on the actual current subset here, instead of the full dataset!
        data_mixture_means = self.get_em_fits_arrays()['mean']

        curr_T_i = np.nonzero(self.T_space == self.enforced_T)[0][0]
        distances['all_mse'] = (data_mixture_means[:4, curr_T_i] - model_fits[:4])**2.
        distances['mixt_kl'] = utils.KL_div(data_mixture_means[1:4, curr_T_i], model_fits[1:4])

        return distances


###########################################################################


def test_fitexperimentsequentialall():

    # Set some parameters and let the others default
    experiment_parameters = dict(action_to_do='launcher_do_simple_run',
                                 inference_method='none',
                                 experiment_id='gorgo11_sequential',
                                 experiment_subject=1,
                                 M=100,
                                 filter_datapoints_size=500,
                                 filter_datapoints_selection='random',
                                 num_samples=100,
                                 selection_method='last',
                                 sigmax=0.1,
                                 renormalize_sigmax=None,
                                 sigmay=0.0001,
                                 code_type='mixed',
                                 slice_width=0.07,
                                 burn_samples=200,
                                 ratio_conj=0.7,
                                 stimuli_generation_recall='random',
                                 autoset_parameters=None,
                                 label='test_fitexperimentsequentialall'
                                 )
    experiment_launcher = experimentlauncher.ExperimentLauncher(run=False, arguments_dict=experiment_parameters)
    experiment_parameters_full = experiment_launcher.args_dict

    # Now let's build a FitExperimentAllT
    fit_exp = FitExperimentSequentialSubjectAll(experiment_parameters_full)

    # Now compute some loglikelihoods
    def compute_everything(self, parameters):
        results = dict()

        print ">> Computing LL all N..."
        results['result_ll_n'] = self.sampler.compute_loglikelihood_N()

        print ">> Computing LL sum..."
        results['result_ll_sum'] = np.nansum(results['result_ll_n'])
        print results['result_ll_sum']

        print ">> Computing BIC..."
        results['result_bic'] = self.sampler.compute_bic(
            K=parameters['bic_K'], LL=results['result_ll_sum'])

        print ">> Computing LL90/92/95/97..."
        results['result_ll90_sum'] = (
            self.sampler.compute_loglikelihood_top90percent(
                all_loglikelihoods=results['result_ll_n']))
        results['result_ll92_sum'] = (
            self.sampler.compute_loglikelihood_top_p_percent(
                0.92, all_loglikelihoods=results['result_ll_n']))
        results['result_ll95_sum'] = (
            self.sampler.compute_loglikelihood_top_p_percent(
                0.95, all_loglikelihoods=results['result_ll_n']))
        results['result_ll97_sum'] = (
            self.sampler.compute_loglikelihood_top_p_percent(
                0.97, all_loglikelihoods=results['result_ll_n']))

    res_listdicts = fit_exp.apply_fct_datasets_all(
        dict(fct=compute_everything,
             parameters=experiment_parameters_full))

    # print(res_listdicts)
    # print fit_exp.compute_loglik_all_datasets()
    # print fit_exp.compute_sum_loglik_all_datasets()

    # Compute BIC
    # print fit_exp.compute_bic_all_datasets()

    return locals()


if __name__ == '__main__':
    if True:
        all_vars = test_fitexperimentsequentialall()

    for key, val in all_vars.iteritems():
        locals()[key] = val
