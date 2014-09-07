"""
    ExperimentDescriptor to fit the experimental data, using the Mixture models only.

    Spawns random samples for now, let's see.
"""

import os
import numpy as np
import experimentlauncher
import inspect
import getpass

# Commit @d8c9acb

# Read from other scripts
parameters_entryscript = dict(action_to_do='launcher_do_generate_submit_pbs_from_param_files', output_directory='.')
submit_jobs = True

parameter_generation = 'random'  ## !!!!!! RANDOM HERE   !!!!!
num_random_samples = 5000
limit_max_queued_jobs = 70

resource = ''

# submit_cmd = 'qsub'
submit_cmd = 'sbatch'

# FOR DIRAC
if getpass.getuser() == 'dc-matt1':
  resource = 'DIRAC-DX001'
  submit_cmd = 'sbatch'
  pbs_unfilled_script = open(os.path.join(os.environ['WORKDIR_DROP'], 'dirac_submission_slurm_unfilled.sh'), 'r').read()

num_repetitions = 3

run_label = 'normalisedsigmaxsigmaoutput_random_fittingexperiments_sigmaxMratiosigmaoutput_repetitions{num_repetitions}_050914'

pbs_submission_infos = dict(description='Fitting of experimental data. Computes LL, BIC and LL90 for 3 datasets. Meant to run random sampling for a long while! Uses the new output noise process, varying sigma_output accordingly. Also use the new normalised sigma_x, which should behave better.',
                            command='python $WORKDIR/experimentlauncher.py',
                            other_options=dict(action_to_do='launcher_do_fitexperiment_allT',
                                               code_type='mixed',
                                               output_directory='.',
                                               ratio_conj=0.5,
                                               M=100,
                                               sigmax=0.1,
                                               renormalize_sigmax=None,
                                               N=200,
                                               R=2,
                                               T=6,
                                               sigmay=0.0001,
                                               sigma_output=0.0,
                                               inference_method='none',
                                               num_samples=200,
                                               selection_num_samples=1,
                                               selection_method='last',
                                               slice_width=0.07,
                                               burn_samples=200,
                                               num_repetitions=num_repetitions,
                                               enforce_min_distance=0.17,
                                               specific_stimuli_random_centers=None,
                                               stimuli_generation='random',
                                               stimuli_generation_recall='random',
                                               autoset_parameters=None,
                                               collect_responses=None,
                                               label=run_label,
                                               experiment_data_dir=os.path.normpath(os.path.join(os.environ['WORKDIR_DROP'], '../../experimental_data')),
                                               ),
                            walltime='10:00:00',
                            memory='2gb',
                            simul_out_dir=os.path.join(os.getcwd(), run_label.format(**locals())),
                            pbs_submit_cmd=submit_cmd,
                            limit_max_queued_jobs=limit_max_queued_jobs,
                            submit_label='fitex_sigxo_4d1',
                            resource=resource,
                            qos='auto')

if getpass.getuser() == 'dc-matt1':
    pbs_submission_infos['pbs_unfilled_script'] = pbs_unfilled_script
    pbs_submission_infos['walltime'] = '12:00:00'


## Define our filtering function
def filtering_function(new_parameters, dict_parameters_range, function_parameters=None):
    '''
    Given M and ratio_conj, will adapt them so that M_conj is always correct and integer.

    or if should_clamp is False, will not change them
    '''

    M_conj_prior = int(new_parameters['M']*new_parameters['ratio_conj'])
    M_conj_true = int(np.floor(M_conj_prior**0.5)**2)
    M_feat_true = int(np.floor((new_parameters['M']-M_conj_prior)/2.)*2.)
    M_true = M_conj_true + M_feat_true
    ratio_true = M_conj_true/float(M_true)

    if function_parameters['should_clamp']:
        # Clamp them and return true
        new_parameters['M'] = M_true
        new_parameters['ratio_conj'] = ratio_true

        return True
    else:
        return np.allclose(M_true, new_parameters['M'])

filtering_function_parameters = {'should_clamp': True}

sigmax_range      =   dict(sampling_type='uniform', low=0.01, high=1.0, dtype=float)
ratioconj_range   =   dict(sampling_type='uniform', low=0.01, high=1.0, dtype=float)
sigmaoutput_range =   dict(sampling_type='uniform', low=0.0, high=3.0, dtype=float)
M_range           =   dict(sampling_type='randint', low=6, high=625, dtype=int)

dict_parameters_range =   dict(M=M_range, sigma_output=sigmaoutput_range, ratio_conj=ratioconj_range, sigmax=sigmax_range)

if __name__ == '__main__':

    this_file = inspect.getfile(inspect.currentframe())
    print "Running ", this_file

    arguments_dict = dict(parameters_filename=this_file)
    arguments_dict.update(parameters_entryscript)

    experiment_launcher = experimentlauncher.ExperimentLauncher(run=True, arguments_dict=arguments_dict)

