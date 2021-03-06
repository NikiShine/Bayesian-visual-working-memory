"""
    ExperimentDescriptor to use CMA-ES to fit Memory curves using a Mixed population code

"""

import os
import numpy as np
import experimentlauncher
import inspect
import utils
import dataio

# Commit @8c49507 +

# Read from other scripts
parameters_entryscript = dict(action_to_do='launcher_do_generate_submit_pbs_from_param_files', output_directory='.')
submit_jobs = True
# submit_cmd = 'qsub'
submit_cmd = 'sbatch'

num_repetitions = 5
M  = 200

# run_label = 'memory_curve_conj_Msigmax_autoset_correctsampling_repetitions{num_repetitions}_211013'
run_label = 'cmaes_distfitexpbic_mixed_ratiosigmax_singleT_repetitions{num_repetitions}_120214'
simul_out_dir = os.path.join(os.getcwd(), run_label.format(**locals()))

parameter_generation = 'cma-es'
cma_population_size = 20
cma_sigma0 = 1.0
cma_logger_do_plot = True
cma_use_auto_scaling = True
cma_use_bounds = True

sleeping_period = dict(min=10, max=30)

# result_callback_function to track best parameter
best_parameters_seen = dict(result=None, job_name='', parameters=None)
def best_parameters_callback(job, parameters=None):

  if parameters['result'] is None or job.get_result() <= parameters['result'] and not np.isnan(job.get_result()):
      # New best parameter!
      parameters['result'] = job.get_result()
      parameters['job_name'] = job.job_name
      parameters['parameters'] = job.experiment_parameters

      print "\n\n>>>>>> Found new best parameters: \n%s\n\n" % parameters

      np.save('best_params', dict(parameters=parameters))

result_callback_function_infos = dict(function=best_parameters_callback, parameters=best_parameters_seen)

# Callback after each iteration, let's save all candidates/fitness, and do a contour plot
data_io = dataio.DataIO(label='cmaes_alliter_tracking', output_folder=simul_out_dir)
cma_iter_parameters = dict(ax=None, candidates=[], fitness=[], dataio=data_io)
def cma_iter_plot_contourf_candidates(all_variables, parameters=None):
    candidates = parameters['candidates']
    fitness = parameters['fitness']

    # Take candidates and fitness and append them
    candidates.extend(all_variables['parameters_candidates_array'])
    fitness.extend(all_variables['fitness_results'].tolist())

    candidates_arr = np.array(candidates)
    fitness_arr = np.array(fitness)

    # Do a plot
    parameters['ax'] = utils.contourf_interpolate_data(candidates_arr, fitness_arr, xlabel='Ratio_conj', ylabel='sigma x', title='Optimisation landscape', interpolation_numpoints=200, interpolation_method='linear', ax_handle=parameters['ax'], log_scale=True)

    if parameters['dataio'] is not None:
        parameters['dataio'].save_variables_default(locals(), ['candidates', 'fitness'])
        parameters['dataio'].save_current_figure('cmaes_optim_landscape_contourf_{label}_{unique_id}.pdf')

cma_iter_callback_function_infos = dict(function=cma_iter_plot_contourf_candidates, parameters=cma_iter_parameters)

pbs_submission_infos = dict(description='Fit experiments (bays09, gorgo11, dualrecall), using distfitexpbic ResultComputation), using the CMA-ES code. Only looks at T=1 for now, should implement a version with all T.',
                            command='python $WORKDIR/experimentlauncher.py',
                            other_options=dict(action_to_do='launcher_do_fitexperiment',
                                               code_type='mixed',
                                               output_directory='.',
                                               ratio_conj=0.5,
                                               subaction='collect_responses',
                                               session_id='cmaes_ratiosigmax',
                                               result_computation='distfitexpbic',
                                               M=M,
                                               sigmax=0.1,
                                               N=200,
                                               T=1,
                                               sigmay=0.0001,
                                               inference_method='none',
                                               num_samples=300,
                                               selection_num_samples=1,
                                               selection_method='last',
                                               slice_width=0.07,
                                               burn_samples=300,
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
                            simul_out_dir=simul_out_dir,
                            pbs_submit_cmd=submit_cmd,
                            submit_label='cmaes_ratiosigmax')


sigmax_range      =   dict(low=0.01, high=3.0, dtype=float)
ratioconj_range   =   dict(low=0.0, high=1.0, dtype=float)

dict_parameters_range =   dict(ratio_conj=ratioconj_range, sigmax=sigmax_range)

if __name__ == '__main__':

    this_file = inspect.getfile(inspect.currentframe())
    print "Running ", this_file

    arguments_dict = dict(parameters_filename=this_file)
    arguments_dict.update(parameters_entryscript)

    experiment_launcher = experimentlauncher.ExperimentLauncher(run=True, arguments_dict=arguments_dict)

