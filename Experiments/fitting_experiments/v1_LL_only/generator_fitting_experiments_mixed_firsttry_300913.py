"""
    ExperimentDescriptor for Fitting experiments in a mixed population code
"""

import os
import numpy as np
from experimentlauncher import *
import inspect

# Commit @2042319 +

# Read from other scripts
parameters_entryscript=dict(action_to_do='launcher_do_generate_submit_pbs_from_param_files', output_directory='.')
submit_jobs = True
parameter_generation = 'grid'

M = 200
num_repetitions = 10

run_label = 'fitting_experiments_mixed_ratiosigmax_autoset_M{M}_repetitions{num_repetitions}_300913'

pbs_submission_infos = dict(description='Fitting of experimental data. First start with dualrecall dataset, fitting for 3 items. We use automatic parameter setting for rcscale and rcscale2, and vary ratio_conj and sigmax.',
                            command='python $WORKDIR/experimentlauncher.py',
                            other_options=dict(action_to_do='launcher_do_fitexperiment',
                                               code_type='mixed',
                                               output_directory='.',
                                               ratio_conj=0.5,
                                               M=M,
                                               sigmax=0.1,
                                               N=100,
                                               T=1,
                                               sigmay=0.0001,
                                               inference_method='none',
                                               num_repetitions=num_repetitions,
                                               stimuli_generation='separated',
                                               stimuli_generation_recall='random',
                                               autoset_parameters=None,
                                               label=run_label,
                                               experiment_data_dir=os.path.normpath(os.path.join(os.environ['WORKDIR_DROP'], '../../experimental_data'))),
                            walltime='10:00:00',
                            memory='2gb',
                            simul_out_dir=os.path.join(os.getcwd(), run_label.format(M=M, num_repetitions=num_repetitions)),
                            pbs_submit_cmd='qsub',
                            submit_label='fitexp_firsttry_mixed')


ratio_range           =   dict(range=np.linspace(0.01, 1.0, 20.), dtype=float)
sigmax_range          =   dict(range=np.linspace(0.01, 1.0, 31.), dtype=float)

dict_parameters_range = dict(ratio_conj=ratio_range, sigmax=sigmax_range)


if __name__ == '__main__':

    this_file = inspect.getfile(inspect.currentframe())
    print "Running ", this_file

    arguments_dict=dict(parameters_filename=this_file)
    arguments_dict.update(parameters_entryscript)
    experiment_launcher = ExperimentLauncher(run=True, arguments_dict=arguments_dict)

