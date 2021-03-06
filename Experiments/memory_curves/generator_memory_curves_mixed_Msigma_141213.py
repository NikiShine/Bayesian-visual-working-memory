"""
    ExperimentDescriptor to fit Memory curves using a Mixed population code

    Uses the new Marginal Inverse Fisher Information, and some new code altogether.
    Precisions do fit nicely, given a factor of 2.
"""

import os
import numpy as np
import experimentlauncher
import inspect

# Commit @9c6e104

# Read from other scripts
parameters_entryscript = dict(action_to_do='launcher_do_generate_submit_pbs_from_param_files', output_directory='.')
submit_jobs = True
parameter_generation = 'grid'
submit_cmd = 'qsub'
#submit_cmd = 'sbatch'

# num_repetitions = 10

# num_repetitions = 1
# ratio_conj = 0.87

num_repetitions = 5
ratio_conj = 0.84

# num_repetitions = 5
# ratio_conj = 0.9

M_conj = np.arange(5, 25)**2.

# run_label = 'memory_curve_conj_Msigmax_autoset_correctsampling_repetitions{num_repetitions}_211013'
run_label = 'memory_curve_mixed_Msigmax_ratioconj{ratio_conj}repetitions{num_repetitions}_141213'

pbs_submission_infos = dict(description='Fit Memory curves using the new code (october 2013). Fit Mixture models directly. Uses mixed population code, automatically set. Now also save all responses! Trying to get better fits...',
                            command='python $WORKDIR/experimentlauncher.py',
                            other_options=dict(action_to_do='launcher_do_memory_curve_marginal_fi',
                                               subaction='collect_responses',
                                               code_type='mixed',
                                               output_directory='.',
                                               ratio_conj=ratio_conj,
                                               M=100,
                                               sigmax=0.1,
                                               N=300,
                                               T=6,
                                               sigmay=0.0001,
                                               inference_method='sample',
                                               num_samples=500,
                                               selection_num_samples=1,
                                               slice_width=0.07,
                                               burn_samples=500,
                                               num_repetitions=num_repetitions,
                                               enforce_min_distance=0.17,
                                               specific_stimuli_random_centers=None,
                                               stimuli_generation='random',
                                               stimuli_generation_recall='random',
                                               autoset_parameters=None,
                                               label=run_label,
                                               experiment_data_dir=os.path.normpath(os.path.join(os.environ['WORKDIR_DROP'], '../../experimental_data')),
                                               ),
                            walltime='10:00:00',
                            memory='2gb',
                            simul_out_dir=os.path.join(os.getcwd(), run_label.format(**locals())),
                            pbs_submit_cmd=submit_cmd,
                            submit_label='memcurv_mixed_M')


sigmax_range =   dict(range=np.linspace(0.01, 0.6, 30.), dtype=float)
M_range      =   dict(range=np.round(M_conj/ratio_conj).astype(int), dtype=int)

dict_parameters_range =   dict(M=M_range, sigmax=sigmax_range)

if __name__ == '__main__':

    this_file = inspect.getfile(inspect.currentframe())
    print "Running ", this_file

    arguments_dict = dict(parameters_filename=this_file)
    arguments_dict.update(parameters_entryscript)

    experiment_launcher = experimentlauncher.ExperimentLauncher(run=True, arguments_dict=arguments_dict)

