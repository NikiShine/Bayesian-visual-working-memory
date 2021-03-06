"""
    ExperimentDescriptor for Fitting experiments in a mixed population code

    Uses the new version of FitExperiment (e5b63db), and random samples
"""

import os
# import numpy as np
from experimentlauncher import *
import inspect
import getpass

# Commit @3f93dfb +

# Read from other scripts
parameters_entryscript=dict(action_to_do='launcher_do_generate_submit_pbs_from_param_files', output_directory='.')
submit_jobs = True

parameter_generation = 'random'  ## !!!!!! RANDOM HERE   !!!!!
num_random_samples = 7000
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
T = 6

run_label = 'fitting_experiments_mixed_Mratiosigmax_allT_ll90_random_repetitions{num_repetitions}_260314'

pbs_submission_infos = dict(description='Random sampling. Fitting of experimental data. Use automatic parameter setting for rcscale and rcscale2, and vary M, ratio_conj, sigmax. Should fit following datasets: Bays09, Dualrecall, Gorgo11. Compute and store LL and LL90%',
                            command='python $WORKDIR/experimentlauncher.py',
                            other_options=dict(action_to_do='launcher_do_fitexperiment_allT',
                                               code_type='mixed',
                                               output_directory='.',
                                               ratio_conj=0.5,
                                               M=10,
                                               N=50,
                                               T=T,
                                               sigmax=0.1,
                                               sigmay=0.0001,
                                               inference_method='none',
                                               num_samples=300,
                                               burn_samples=300,
                                               selection_num_samples=1,
                                               selection_method='last',
                                               slice_width=0.07,
                                               num_repetitions=num_repetitions,
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
                            submit_label='fitexp_3d_rnd_ll',
                            resource=resource)

if getpass.getuser() == 'dc-matt1':
  pbs_submission_infos['pbs_unfilled_script'] = pbs_unfilled_script
  pbs_submission_infos['walltime'] = '12:00:00'

sigmax_range      =   dict(sampling_type='uniform', low=0.01, high=1.0, dtype=float)
ratio_range       =   dict(sampling_type='uniform', low=0.01, high=1.0, dtype=float)
M_range           =   dict(sampling_type='randint', low=6, high=625, dtype=int)

dict_parameters_range = dict(M=M_range, ratio_conj=ratio_range, sigmax=sigmax_range)


if __name__ == '__main__':

    this_file = inspect.getfile(inspect.currentframe())
    print "Running ", this_file

    arguments_dict=dict(parameters_filename=this_file)
    arguments_dict.update(parameters_entryscript)
    experiment_launcher = ExperimentLauncher(run=True, arguments_dict=arguments_dict)

