#!/usr/bin/env python
# encoding: utf-8
"""
submitpbs.py

Created by Loic Matthey on 2012-10-29
Copyright (c) 2012 . All rights reserved.
"""

import numpy as np
import hashlib
import stat
import os
import subprocess
import progress
import functools
import time
import sys
import getpass
import compileall
import collections

import logging

import utils
import dataio

import jobwrapper

import cma

import matplotlib.pyplot as plt

PBS_SCRIPT = """#!/bin/bash
{pbs_options}
hostn=`hostname`
echo "Job execution host: $hostn"
echo "Filename: {filename}"
cd {working_dir}
T="$(date +%s)"
nice -n 15 {cmd}
echo "+++ Job completed +++"
T="$(($(date +%s)-T))"
printf "Elapsed time: %02d:%02d:%02d\n" "$((T/3600))" "$((T/60%60))" "$((T%60))"
"""


### Random unix commands
# - Rerun some pbs scripts that failed:
# find ../pbs_output/ -name "script.*.e*" -size +1k -exec sh -c "basename {} | cut -d "." -f1-2 | qsub" \;
# (error logs bigger than 1K had to be rerun)
#
# - Rerun unfinished scripts: (run in pbs_output)
# for f in ../pbs_scripts/script.*; do basef=`basename $f`; if grep -Fq $basef *; then echo "$basef ok"; else echo "$basef rerun"; qsub $f; fi; done;


class SubmitPBS():
    """
        Class creating scripts to be submitted to PBS and sending them.

        Also handles generating sets of parameters, checking them for a condition and then submitting them on PBS.

        Adapted from J. Gasthaus's run_pbs script.
    """

    def __init__(self, pbs_submission_infos=None, working_directory=None, memory='2gb', walltime='1:00:00', set_env=True, scripts_dir='pbs_scripts', output_dir='pbs_output', wait_submitting=False, submit_label='', pbs_submit_cmd='qsub', limit_max_queued_jobs=0, source_dir=None, debug=False):

        self.debug = debug
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
        self.logger = logging.getLogger(submit_label)

        if pbs_submission_infos is not None:
            # Extract informations from this dictionary instead
            working_directory   = pbs_submission_infos['simul_out_dir']
            memory              = pbs_submission_infos['memory']
            walltime            = pbs_submission_infos['walltime']

            wait_submitting = pbs_submission_infos.get('wait_submitting', wait_submitting)

            submit_label = pbs_submission_infos.get('submit_label', submit_label)

            source_dir = pbs_submission_infos.get('source_dir', None)

            pbs_submit_cmd = pbs_submission_infos.get('pbs_submit_cmd', pbs_submit_cmd)

            limit_max_queued_jobs = pbs_submission_infos.get('limit_max_queued_jobs', limit_max_queued_jobs)

            # Use either the pre-created Unfilled script at the top, or a provided one (which could be loaded as a string from elsewhere)
            self.pbs_unfilled_script = pbs_submission_infos.get('pbs_unfilled_script', PBS_SCRIPT)

            self.partition = pbs_submission_infos.get('partition', '')

            self.resource = pbs_submission_infos.get('resource', '')

            self.qos = pbs_submission_infos.get('qos', '')
            if self.qos == 'auto':
                # Compute it automatically.
                # rules:
                # < 1h -> short
                # < 24h -> normal
                # < 72h -> medium
                # < 7d -> long
                walltime_seconds = utils.convert_deltatime_str_to_seconds(walltime)
                if walltime_seconds <= 1*3600:
                    self.qos = 'short'
                elif walltime_seconds <= 24*3600:
                    self.qos = 'normal'
                elif walltime_seconds <= 72*3600:
                    self.qos = 'medium'
                else:
                    self.qos = 'long'



        self.pbs_options = {'mem': memory, 'pmem': memory, 'walltime': walltime, 'ncpus': '1'}
        self.set_env = set_env
        self.wait_submitting = wait_submitting
        self.submit_label = submit_label
        self.pbs_submit_cmd = pbs_submit_cmd

        # Keep track of submitted jobs numbers and available queue size if desired
        self.limit_max_queued_jobs = limit_max_queued_jobs
        self.update_running_jobs_number()

        # Initialise the directories
        if working_directory is None:
            self.working_directory = os.getcwd()
        else:
            self.working_directory = working_directory

        self.scripts_dir = os.path.join(self.working_directory, scripts_dir)
        self.output_dir = os.path.join(self.working_directory, output_dir)
        self.plot_output_dir = os.path.join(self.working_directory, 'outputs')
        self.make_dirs()

        # Tracking dictionaries for the Optimisation routines
        self.jobs_tracking_dict = dict()
        self.result_tracking_dict = dict()

        # Open the Submit file, containing instructions to submit everything
        self.open_submit_file()

        if self.debug:
            self.logger.info("SubmitPBS initialised:\n %s, %s, %s, %s" % (self.working_directory, self.scripts_dir, self.output_dir, self.pbs_options))

        # Force pre-compilation of everything
        if source_dir:
            compileall.compile_dir(source_dir, quiet=True)
        else:
            compileall.compile_dir(os.environ['WORKDIR'], quiet=True)


    def getEnvCommandString(self, command="export", env_keys_to_capture=frozenset(["PATH", "PYTHONPATH", "LD_LIBRARY_PATH"])):
        '''
            Catch and construct the list of environment variables to put in the script
        '''

        out = []
        out.append(command + " OMP_NUM_THREADS=1")
        for key in os.environ:
            if key in env_keys_to_capture:
                out.append(command + " " + key + '="'+ os.environ[key] + '"')
        return '\n'.join(out)


    def make_dirs(self):
        '''
            Create the directories for PBS submit scripts and PBS outputs.
        '''

        try:
            os.makedirs(self.scripts_dir)
        except:
            pass
        try:
            os.makedirs(self.output_dir)
        except:
            pass
        try:
            os.makedirs(self.plot_output_dir)
        except:
            pass

        self.directories_created = True


    def update_running_jobs_number(self, max_name_length=16):
        '''
            Get the current number of jobs on the queue

            Should work for both PBS and SLURM
        '''
        username = getpass.getuser()

        if self.pbs_submit_cmd == 'qsub':
            # Using PBS
            queue_status = subprocess.Popen(['qstat', '-u', username], stdout=subprocess.PIPE)
            jobname = self.submit_label[:max_name_length]
        elif self.pbs_submit_cmd == 'sbatch':
            # Using SLURM
            queue_status = subprocess.Popen(['squeue', '-h', '-o', '%i %j %u %P'], stdout=subprocess.PIPE)
            jobname = self.submit_label
        else:
            self.num_queued_jobs = 0
            return 0

        lines = queue_status.communicate()[0].splitlines()

        if self.partition:
            self.num_queued_jobs = len([line for line in lines if username in line and jobname in line and self.partition in line])
        else:
            self.num_queued_jobs = len([line for line in lines if username in line and jobname in line])


    def wait_queue_not_full(self, sleeping_period=dict(min=30, max=180)):
        '''
            Wait for the queue to have empty slots, compared to self.limit_max_queued_jobs

            Sleeps for random amounts between [sleeping_period.min, sleeping_period.max]
        '''

        # Update running jobs number
        self.update_running_jobs_number()

        while self.num_queued_jobs >= self.limit_max_queued_jobs:
            # Decide for how long to sleep
            sleep_time_rnd = np.random.randint(sleeping_period['min'], sleeping_period['max'])

            if self.debug:
                self.logger.info("Queue full (%d queued/%d limit max), waiting %d sec..." % (self.num_queued_jobs, self.limit_max_queued_jobs, sleep_time_rnd))

            # Sleep for a bit
            time.sleep(sleep_time_rnd)

            # Update running jobs number
            self.update_running_jobs_number()



    def open_submit_file(self, filename='submit_all.sh'):
        '''
            Open/create a file holding all the scripts created in the current script_directory.

            Could be improved to be a database of script/parameters/etc.. but not sure if really useful.
        '''

        self.submit_fn = os.path.join(self.scripts_dir, filename)

        try:
            # Try opening the file. If exist, we will just append to it
            with open(self.submit_fn, 'r'):
                pass

        except IOError:
            # No file, need to create it.
            with open(self.submit_fn, 'w') as submit_f:
                submit_f.write('#!/bin/sh\n')


    def add_to_submit_file(self, new_script_filename, command):
        '''
            Add a line in the Submit file
        '''

        with open(self.submit_fn, 'a') as submit_f:
            submit_f.write(self.pbs_submit_cmd + " " + new_script_filename + " #" + command + '\n')


    ########################################

    def create_submit_job_parameters(self, pbs_command_infos, force_parameters=None, submit=True):
        '''
            Given some pbs_command_infos (command='python script', other_options='--stuff 10') and extra parameters,
            automatically generate a simulation command, a script to execute it and submits it to PBS (if desired)

            If force_parameters is set, will change the dictionary pbs_command_infos['other_options'] accordingly
        '''

        # Enforce specific parameters (they usually are the ones we vary)
        if force_parameters is not None:
            pbs_command_infos['other_options'].update(force_parameters)

        # Generate the command
        sim_cmd = self.create_simulation_command(pbs_command_infos)

        # Create the script and submits
        if submit:
            self.submit_job(sim_cmd)
        else:
            self.make_script(sim_cmd)

        # Increment submitted job number
        self.num_queued_jobs += 1


    def create_simulation_command(self, pbs_command_infos):
        '''
            Generates a simulation command to be written in a script (and then possibly submitted to PBS).

            Takes a dictionary of pbs submission parameters.
            pbs_command_infos['other_options'] is special and will be automatically added as arguments to the command called.

            Supports:
                - param : param_value  -> --param param_value
                - param : None         -> --param

        '''

        assert pbs_command_infos is not None, "Provide pbs_command_infos..."

        # The command itself (e.g. python scriptname)
        simulation_command = pbs_command_infos['command']

        # Put the arguments
        for (param, param_value) in pbs_command_infos['other_options'].items():
            if param_value is None:
                simulation_command += " --{param}".format(param=param)
            else:
                simulation_command += " --{param} {param_value}".format(param=param, param_value=param_value)

        return simulation_command


    def make_script(self, command):
        '''
            Create a script for a given command.

            Will output in the script_directory.
        '''

        # Create a new script. Its name is a md5 hash of the command to execute.
        fn = os.path.join(self.scripts_dir, "script." + str(hashlib.md5(command).hexdigest()))

        with open(fn, 'w') as f:
            # Construct the pbs options
            pbs_options = '\n'.join(["#PBS -l " + k + "=" + v for (k, v) in self.pbs_options.items()])

            # Add SLURM options
            pbs_options += "\n#SBATCH -n1 --time={walltime} --mem-per-cpu={mem}".format(**self.pbs_options)

            # Add the label
            if self.submit_label:
                pbs_options += "\n#PBS -N " + self.submit_label
                pbs_options += "\n#SBATCH -J " + self.submit_label

            # Add the partition if needed
            if self.partition:
                pbs_options += "\n#SBATCH -p " + self.partition

            # Add the resource if provided
            if self.resource:
                pbs_options += "\n#SBATCH -A " + self.resource

            # Add the QOS if provided
            if self.qos:
                pbs_options += "\n#SBATCH --qos=" + self.qos

            # Add the environment
            if self.set_env:
                pbs_options = pbs_options + "\n" + self.getEnvCommandString()

            # Fill in the template script
            filled_script = self.pbs_unfilled_script.format(pbs_options=pbs_options, working_dir=self.working_directory, cmd=command, filename=fn)

            f.write(filled_script)

        # Make the script executable
        os.chmod(fn, stat.S_IXUSR | stat.S_IRUSR | stat.S_IWUSR)

        # Add it to the list of jobs
        self.add_to_submit_file(fn, command)

        if self.debug:
            self.logger.info("\n--- Script created: ---")
            self.logger.info(command + "\n")

        return fn


    def submit_job(self, command):
        '''
            Take a command, create a script to run it on PBS and submits it
        '''

        # Create job
        new_script_filename = self.make_script(command)

        # Wait for queue to have space for our jobs, if desired
        if self.limit_max_queued_jobs > 0:
            # Wait for the queue to be nearly full before checking and waiting
            if self.num_queued_jobs > 3*self.limit_max_queued_jobs/4:
                self.wait_queue_not_full()

        # Submit!
        if self.debug:
            self.logger.info("-> Submitting job " + new_script_filename + "\n")

        # Change to the PBS output directory first
        utils.chdir_safe(self.output_dir)

        # Submit the job
        if self.pbs_submit_cmd == 'sh':
            subprocess.call("sh " + new_script_filename, shell=True)
        else:
            os.popen(self.pbs_submit_cmd + " " + new_script_filename)

        # Change back to the working directory
        utils.chdir_safe(self.working_directory)

        # Wait a bit, randomly
        if self.wait_submitting:
            try:
                sleeping_time = np.random.normal(1.0, 0.5)
                if sleeping_time < 10.:
                    time.sleep(sleeping_time)
            except:
                pass



    #################################################

    def generate_submit_constrained_parameters_from_module_parameters(self, module_parameters):
        '''
            Entry-point for general parameter tuples creation. Optionally submits to PBS directly.

            Uses the new system that loads .py files as modules, which can contain parameters/functions directly.

            Loads generate_submit_constrained_parameters next, which then loads generate_submit_constrained_parameters_grid/generate_submit_constrained_parameters_random/perform_cma_es_optimization accordingly.
        '''

        # Make the loaded_module a dictionary, easier to handle
        submission_parameters_dict = module_parameters.__dict__

        ## Set some default values
        # If no filtering function given, just set it to None for the rest of the script
        default_params = (('filtering_function', None), ('filtering_function_parameters', None), ('num_random_samples', 100))
        for key, val in default_params:
            submission_parameters_dict.setdefault(key, val)

        if submission_parameters_dict['parameter_generation'] == 'grid':
            return self.generate_submit_constrained_parameters_grid(submission_parameters_dict['dict_parameters_range'], filtering_function=submission_parameters_dict['filtering_function'], filtering_function_parameters=submission_parameters_dict['filtering_function_parameters'], pbs_submission_infos=submission_parameters_dict['pbs_submission_infos'], submit_jobs=submission_parameters_dict['submit_jobs'])
        elif submission_parameters_dict['parameter_generation'] == 'random':
            return self.generate_submit_constrained_parameters_random(submission_parameters_dict['dict_parameters_range'], num_random_samples=submission_parameters_dict['num_random_samples'], filtering_function=submission_parameters_dict['filtering_function'], filtering_function_parameters=submission_parameters_dict['filtering_function_parameters'], pbs_submission_infos=submission_parameters_dict['pbs_submission_infos'], submit_jobs=submission_parameters_dict['submit_jobs'])
        elif submission_parameters_dict['parameter_generation'] == 'cma-es':
            return self.perform_cma_es_optimization(submission_parameters_dict)


    ################################################


    def generate_submit_constrained_parameters_random(self, dict_parameters_range, num_random_samples=100, filtering_function=None, filtering_function_parameters=None, pbs_submission_infos=None, submit_jobs=True):
        '''
            Takes a dictionary of parameters (which should contain low/high values for each or generator function), and
            generates num_random_samples possible parameters randomly.
            Checks them with some provided function before accepting them if provided.
            If pbs_submission_infos is provided, will additionally automatically create scripts and submit them to PBS. The PBS informations were already read from it in __init__ though, be careful.
        '''

        # Convert specific parameter sampling methods into generators
        self.create_generator_random_parameter(dict_parameters_range)

        # We will keep all constrained parameters for further use
        constrained_parameters = []

        fill_parameters_progress = progress.Progress(num_random_samples)
        tested_parameters = 0

        # Provide as many experimentally constrained parameters as desired
        while len(constrained_parameters) < num_random_samples:
            self.logger.info("Parameters tested %d, found %d. %d requested. %.2f%%, %s left - %s" % (tested_parameters, len(constrained_parameters), num_random_samples, fill_parameters_progress.percentage(), fill_parameters_progress.time_remaining_str(), fill_parameters_progress.eta_str()))

            # Sample new parameter values
            new_parameters = {}
            for curr_param, param_dict in dict_parameters_range.items():
                # Use the provided sampling function (some are predefined)
                new_parameters[curr_param] = param_dict['sampling_fct']()

            # Check if the new parameters are within the constraints
            if (filtering_function and filtering_function(new_parameters, dict_parameters_range, filtering_function_parameters)) or (filtering_function is None):
                # Yes, all good

                # Append to our parameters
                constrained_parameters.append(new_parameters)

                # If desired, generate a script and submits it to PBS
                if pbs_submission_infos:
                    self.create_submit_job_parameters(pbs_submission_infos, force_parameters=new_parameters, submit=submit_jobs)

                fill_parameters_progress.increment()

            tested_parameters += 1

        if self.debug:
            self.logger.info("\n-- Submitted/created %d jobs --\n" % self.num_queued_jobs)

        return constrained_parameters


    def create_generator_random_parameter(self, dict_parameters_range):
        '''
            Support some predefined random parameter sampling:
                - Uniform[a,b]
                - randint(a, b)

            After this function, a sampling_fct() will be set for each parameter
        '''

        for param_name, dict_specific_param_range in dict_parameters_range.items():
            if 'sampling_fct' not in dict_specific_param_range:
                # No sampling function, try to automatically define one
                if dict_specific_param_range['sampling_type'] == 'uniform':
                    # functool.partial is used to freeze the dict_parameters to the one at execution time. Work-around for immutable + functional programming madness.
                    dict_specific_param_range['sampling_fct'] = functools.partial(lambda params: params['low'] + np.random.rand()*(params['high'] - params['low']), dict_specific_param_range)
                elif dict_specific_param_range['sampling_type'] == 'randint':
                    dict_specific_param_range['sampling_fct'] = functools.partial(lambda params: np.random.randint(params['low'], params['high']), dict_specific_param_range)
                else:
                    raise ValueError('Sampling_type unknown and no sampling_fct provided... Cannot sample parameter %s' % param_name)


    ################################################


    def generate_submit_constrained_parameters_grid(self, dict_parameters_range, filtering_function=None, filtering_function_parameters=None, pbs_submission_infos=None, submit_jobs=True):
        '''
            Takes a dictionary of parameters, with their list of values, and generates a list of all the combinations.
            Filter them with a specific function if provided.
            if pbs_submission_infos is provided, will create a script and submit it to PBS when an acceptable set of parameters if found
        '''

        candidate_parameters = []

        # Get all cross combinations of parameters.
        # Also converts the type on the fly to correspond with the specified dtype.
        cross_comb = utils.cross([[dict_parameters_range[param]['dtype'](param_elem) for param_elem in dict_parameters_range[param]['range'].tolist()] for param in dict_parameters_range])
        # Convert them back into dictionaries
        candidate_parameters = [dict(zip(dict_parameters_range.keys(), x)) for x in cross_comb]

        # Some debuging info
        if self.debug:
            self.logger.info("\n=== Generating up to %d candidate parameter sets ===\n" % len(candidate_parameters))

        # Now filter them
        constrained_parameters = []
        for new_parameters in progress.ProgressDisplay(candidate_parameters, display=progress.SINGLE_LINE):
            if (filtering_function is None) or (filtering_function and filtering_function(new_parameters, dict_parameters_range, filtering_function_parameters)):

                constrained_parameters.append(new_parameters)

                # Submit to PBS if required
                if pbs_submission_infos:

                    self.create_submit_job_parameters(pbs_submission_infos, force_parameters=new_parameters, submit=submit_jobs)

        if self.debug:
            self.logger.info("\n-- Submitted/created %d jobs --\n" % self.num_queued_jobs)

        return constrained_parameters


    ################################################

    def generate_submit_sequential_optimisation(self, submission_parameters_dict):
        '''
            Function that will run multiple simulations (submitting them in JobWrappers) and get ResultComputation from them, to get the maximum value possible
        '''
        # Extract some variables
        dict_parameters_range = submission_parameters_dict['dict_parameters_range']
        max_optimisation_iterations = submission_parameters_dict.get('max_optimisation_iterations', 100)
        filtering_function = submission_parameters_dict.get('filtering_function', None)
        filtering_function_parameters = submission_parameters_dict.get('filtering_function_parameters', None)

        # Convert specific parameter sampling methods into generators
        self.create_generator_random_parameter(dict_parameters_range)

        # Track status of parameters: parameters -> dict(status=['waiting', 'submitted', 'completed'], result=None, jobwrapper=None, parameters=None)
        # self.jobs_tracking_dict

        fill_parameters_progress = progress.Progress(max_optimisation_iterations)
        parameters_tested = 0
        converged = False

        # Perform the sequential optimisation loop
        while parameters_tested < max_optimisation_iterations and not converged:
            self.logger.info(" >Parameters tested %d (max %d). %.2f%%, %s left - %s" % (parameters_tested, max_optimisation_iterations, fill_parameters_progress.percentage(), fill_parameters_progress.time_remaining_str(), fill_parameters_progress.eta_str()))

            # Get new parameter values. For now, random
            # TODO Do something better.
            new_parameters = {}
            for curr_param, param_dict in dict_parameters_range.items():
                # Use the provided sampling function (some are predefined)
                new_parameters[curr_param] = param_dict['sampling_fct']()
            if self.debug:
                self.logger.info("New parameters: %s \n" % new_parameters)

            # Check if the new parameters are within the constraints
            if (filtering_function is not None) and not filtering_function(new_parameters, dict_parameters_range, filtering_function_parameters):
                # Bad param, just ditch it
                continue

            # Submit the minibatch of size 1
            self.submit_minibatch_jobswrapper([new_parameters], submission_parameters_dict)

            fill_parameters_progress.increment()
            parameters_tested += 1


    def perform_cma_es_optimization(self, submission_parameters_dict):
        '''
            Instantiate a CMA_ES object and run the optimization.
            Parameters:
                - submission_parameters_dict['cma_population_size']
                - submission_parameters_dict['cma_sigma0']

            Uses submission_parameters_dict['dict_parameters_range'] to know which parameters to optimize.
                They should all provide their range, CMA-ES searches in x_0 +- 3*cma_sigma0*scaling.
                So provide either:
                    - x0, scaling (make sure they are compatible with cma_sigma0)
                    - low, high, which will be converted automatically to: x0 = (high-low)/2, scaling = (high-low)/(3*cma_sigma0)

        '''

        # Optization parameters
        cma_population_size = submission_parameters_dict.get('cma_population_size', None)
        cma_sigma0 = submission_parameters_dict.get('cma_sigma0', 1.0)
        cma_use_auto_scaling = submission_parameters_dict.get('cma_use_auto_scaling', True)
        cma_iter_callback_function_infos = submission_parameters_dict.get('cma_iter_callback_function_infos', None)
        cma_logger_do_plot = submission_parameters_dict.get('cma_logger_do_plot', False)
        cma_logger_filename = submission_parameters_dict.get('cma_logger_filename', 'logging_cmaes')
        cma_nan_replacement = submission_parameters_dict.get('cma_nan_replacement', 1000000000.)
        cma_use_bounds = submission_parameters_dict.get('cma_use_bounds', False)
        cma_boundary_handling = submission_parameters_dict.get('cma_boundary_handling', None)
        cma_tolx = submission_parameters_dict.get('cma_tolx', None)
        cma_tolfun = submission_parameters_dict.get('tolfun', None)
        cma_use_transforms = submission_parameters_dict.get('cma_use_transforms', False)

        # Extract the parameters ranges
        dict_parameters_range = submission_parameters_dict['dict_parameters_range']
        parameter_names_sorted = sorted(dict_parameters_range.keys())
        for curr_param_name in parameter_names_sorted:
            curr_param = dict_parameters_range[curr_param_name]
            # Check that we have x0 and scaling set for each variable
            if 'x0' not in curr_param or 'scaling' not in curr_param:
                if 'low' in curr_param and 'high' in curr_param:
                    if 'x0' not in curr_param:
                        curr_param['x0'] = (curr_param['high'] - curr_param['low'])/2.
                    if 'scaling' not in curr_param:
                        curr_param['scaling'] = (curr_param['high'] - curr_param['low'])/(3.*cma_sigma0)
                else:
                    raise ValueError('No x0/scaling and high/low for variable %s, provide either one' % curr_param)

        # Extract the arrays of scalings for the parameters
        parameters_scalings = np.array([dict_parameters_range[curr_param_name]['scaling'] for curr_param_name in parameter_names_sorted])

        # Setup parameter transformations
        if cma_use_transforms:
            parameters_transform_functions = {}

            # Collect all the forward/inverse transform functions per param
            all_transform_fct = []
            all_transform_inv_fct = []
            for param_name in parameter_names_sorted:
                if 'transform_fct' in dict_parameters_range[param_name]:
                    all_transform_fct.append(dict_parameters_range[param_name]['transform_fct'])
                else:
                    all_transform_fct.append(utils.identity)

                if 'transform_inv_fct' in dict_parameters_range[param_name]:
                    all_transform_inv_fct.append(dict_parameters_range[param_name]['transform_inv_fct'])
                else:
                    all_transform_inv_fct.append(utils.identity)

            # 'vectorized' version of the transformation of different parameters
            def transform_params_fct(parameters):
                return [all_transform_fct[param_i](param) for param_i, param in enumerate(parameters)]

            def transform_inv_params_fct(parameters):
                return [all_transform_inv_fct[param_i](param) for param_i, param in enumerate(parameters)]


        # Construct Options dict
        cma_options = cma.CMAOptions()
        if cma_population_size is not None:
            if cma_population_size == 'auto_10x':
                cma_options['popsize'] = 10*len(parameter_names_sorted)
            else:
                cma_options['popsize'] = cma_population_size
            self.logger.info("forcing popsize: %s " % cma_population_size)
        if cma_use_auto_scaling and not np.allclose(parameters_scalings, np.ones(len(parameter_names_sorted))):
            cma_options['CMA_stds'] = parameters_scalings
            self.logger.info("forcing scaling: %s" % parameters_scalings)
        if cma_use_bounds:
            cma_options['bounds'] = [[dict_parameters_range[param_key][bound_] for param_key in parameter_names_sorted] for bound_ in ('low', 'high')]
        if cma_boundary_handling is not None:
            cma_options['boundary_handling'] = cma_boundary_handling
        if cma_tolx is not None:
            cma_options['tolx'] = cma_tolx
        if cma_tolfun is not None:
            cma_options['tolfun'] = cma_tolfun
        if cma_use_transforms:
            cma_options['transformation'] = [transform_params_fct, transform_inv_params_fct]

        ### Instantiate CMA ES object.
        cma_es = cma.CMAEvolutionStrategy(self.cma_init_parameters(dict_parameters_range, parameter_names_sorted),
                                          cma_sigma0,
                                          inopts=cma_options
                                          )

        ## Instantiate a CMADataLogger. Will write to the current directory
        cma_log = cma.CMADataLogger(name_prefix=os.path.join(self.plot_output_dir, cma_logger_filename)).register(cma_es)

        ## Iteration loop!
        # Catch CTRL-C, to allow for final state saving.
        try:
            while not cma_es.stop():

                ## Request new parameters candidates
                parameters_candidates_array = cma_es.ask()

                # Convert to dictionaries
                parameters_candidates_dict = self.cma_list_parameters_array_to_dict(parameters_candidates_array, parameter_names_sorted, dict_parameters_range)

                # Make sure those parameters are acceptable
                wrong_parameters_indices = self.check_parameters_candidate(parameters_candidates_dict, parameter_names_sorted, dict_parameters_range)
                while len(wrong_parameters_indices) > 0:
                    # Resample those wrong parameters
                    for wrong_parameters_i in wrong_parameters_indices:
                        parameters_candidates_array[wrong_parameters_i] = cma_es.ask(1)[0]

                        parameters_candidates_dict[wrong_parameters_i] = self.cma_parameters_array_to_dict(parameters_candidates_array[wrong_parameters_i], parameter_names_sorted, dict_parameters_range)

                    wrong_parameters_indices = self.check_parameters_candidate(parameters_candidates_dict, parameter_names_sorted, dict_parameters_range)

                if self.debug:
                    self.logger.info("> Submitting minibatch (%d jobs)." % len(parameters_candidates_array))
                    for curr_param_dict_i, curr_param_dict in enumerate(parameters_candidates_dict):
                        self.logger.info(" - {params}".format(params=utils.pprint_dict(curr_param_dict, key_sorted=parameter_names_sorted)))


                ## Evaluate the parameters fitness, submit them!!
                fitness_results = self.submit_minibatch_jobswrapper(parameters_candidates_dict, submission_parameters_dict)

                # replace np.nan by large values...
                fitness_results[np.isnan(fitness_results)] = cma_nan_replacement

                if self.debug:
                    self.logger.info(">> Minibatch completed (%d jobs)." % len(parameters_candidates_array))
                    for curr_param_dict_i, curr_param_dict in enumerate(parameters_candidates_dict):
                        self.logger.info(" - {params} \t -> {result}".format(params=utils.pprint_dict(curr_param_dict, key_sorted=parameter_names_sorted), result=fitness_results[curr_param_dict_i]))

                ## Do something after each CMA-ES iteration if desired
                if cma_iter_callback_function_infos is not None:
                    cma_iter_callback_output = cma_iter_callback_function_infos['function'](locals(), parameters=cma_iter_callback_function_infos['parameters'])

                    # TODO(lmatthey) HACKY HACKY sorry...
                    if cma_iter_callback_output:
                        if 'fitness_results' in cma_iter_callback_output:
                            fitness_results = cma_iter_callback_output['fitness_results']

                ## Update the state of CMA-ES
                cma_es.tell(parameters_candidates_array, fitness_results)
                cma_log.add()

                ## Display and all
                if self.debug:
                    # CMA status
                    cma_es.disp()

                    # Results
                    cma.pprint(cma_es.result())

                    # DataLogger plots
                    if cma_logger_do_plot:
                        try:
                            cma_log.plot()
                            cma.savefig('cma_es_state.pdf')
                            cma_log.closefig()
                        except AttributeError:
                            # Sometimes, cma_log.plot() fails, I suppose when not enough runs exist... So just ignore it
                            pass
        except KeyboardInterrupt:
            # Ctrl-C
            self.logger.info(">>> Quit CMA/ES early")

        # Print overall best!
        self.logger.info("Overall best:")
        self.logger.info(utils.pprint_dict(self.cma_parameters_array_to_dict(cma_es.best.x, parameter_names_sorted, dict_parameters_range), parameter_names_sorted))
        self.logger.info(" -> result: %s" % cma_es.best.f)
        self.logger.info(cma_es.best.get())

        self.logger.info("=== CMA_ES FINISHED ===")

        return dict(result_final=cma_es.result(), result_tracking_dict=self.result_tracking_dict, best_params=cma_es.best.get(), best_f=cma_es.best.f)


    def check_parameters_candidate(self, list_parameters_candidates_dict, parameter_names_sorted, dict_parameters_range):
        '''
            Checks the provided parameters and verify they are all in the provided bounds
            return list of indices with unacceptable parameters
        '''

        wrong_parameters_indices = []

        for parameters_candidate_i, parameters_candidate in enumerate(list_parameters_candidates_dict):

            for param_name in parameter_names_sorted:
                if (parameters_candidate[param_name] < dict_parameters_range[param_name]['low']) or (parameters_candidate[param_name] > dict_parameters_range[param_name]['high']):
                    # wrong wrong wrong...
                    wrong_parameters_indices.append(parameters_candidate_i)

        return wrong_parameters_indices



    def cma_parameters_dict_to_array(self, parameters_dict, parameter_names_sorted):
        '''
            Take a dictionary of parameters and return the array with the parameters ordered like the parameter_names_sorted list
            (maybe too cautious, but dict have no ordering of their keys...)
        '''

        return np.array([parameters_dict[curr_param] for curr_param in parameter_names_sorted])

    def cma_list_parameters_dict_to_array(self, list_parameters_dict, parameter_names_sorted):
        '''
            Takes a list of dictionaries of parameters and converts it into a list of arrays
        '''

        return [self.cma_parameters_dict_to_array(parameters_dict, parameter_names_sorted) for parameters_dict in list_parameters_dict]


    def cma_parameters_array_to_dict(self, parameters_array, parameter_names_sorted, dict_parameters_range):
        '''
            Takes an array of parameters and creates a dictionary.
        '''

        return dict([(param_name, dict_parameters_range[param_name]['dtype'](parameters_array[param_name_i])) for param_name_i, param_name in enumerate(parameter_names_sorted)])


    def cma_list_parameters_array_to_dict(self, list_parameters_array, parameter_names_sorted, dict_parameters_range):
        '''
            Takes a list of arrays of parameters and converts it into a list of dictionaries

            Used to convert between CMA-ES parameter candidates and submissions to the queuing system
        '''

        return [self.cma_parameters_array_to_dict(parameters_array, parameter_names_sorted, dict_parameters_range) for parameters_array in list_parameters_array]


    def cma_init_parameters(self, dict_parameters_range, parameter_names_sorted):
        '''
            Takes dict_parameters_range and returns x0 for each of the parameters
        '''

        return np.array([dict_parameters_range[curr_param]['dtype'](dict_parameters_range[curr_param]['x0']) for curr_param in parameter_names_sorted])


    ##########################################################################

    def submit_minibatch_jobswrapper(self, parameters_to_submit, submission_parameters_dict):
        '''
            Take a list of parameters sets to submit.
            Submits them all, and then wait on all to finish

            Input: list[dict(param_name: param_value, ...)]

            Returns the ResultComputation for them if provided (should, if you don't it's useless to use this function...)
        '''

        pbs_submission_infos = submission_parameters_dict.get('pbs_submission_infos', None)
        sleeping_period = submission_parameters_dict.get('sleeping_period', dict(min=60, max=180))
        submit_jobs = submission_parameters_dict.get('submit_jobs', False)
        result_callback_function_infos = submission_parameters_dict.get('result_callback_function_infos', None)
        wait_jobs_completed = submission_parameters_dict.get('wait_jobs_completed', True)

        # Track status of parameters: parameters -> dict(status=['waiting', 'submitted', 'completed'], result=None, jobwrapper=None, parameters=None)

        completed_parameters_progress = progress.Progress(len(parameters_to_submit))
        # parameters_tested = 0
        job_names_ordered = []

        # Submit all jobs
        for current_parameters in parameters_to_submit:
            # Create job dictionary
            job_submission_parameters = self.prepare_job_parameters(current_parameters, pbs_submission_infos)

            # Create job
            new_job = jobwrapper.JobWrapper(job_submission_parameters, session_id=job_submission_parameters['session_id'], debug=False)

            # Add to our Job tracker
            self.track_new_job(new_job, current_parameters)
            job_names_ordered.append(new_job.job_name)

            # Submit it. When this call returns, it's been submitted.
            self.submit_jobwrapper(new_job, pbs_submission_infos, submit=submit_jobs)

        if self.debug:
            self.logger.info("-> submitted minibatch, %d jobs. %s computation" % (len(parameters_to_submit), job_submission_parameters.get('result_computation', 'no')))

        if wait_jobs_completed:
            ## Wait for Jobs to be completed (could do another version where you send multiple jobs before waiting)
            self.wait_all_jobs_collect_results(result_callback_function_infos=result_callback_function_infos, sleeping_period=sleeping_period, completion_progress=completed_parameters_progress, pbs_submission_infos=pbs_submission_infos)

            ## Now return the list of results, in the same ordering
            result_shape = (1,)
            for job_i, job_name in enumerate(job_names_ordered):
                if not np.isscalar(self.jobs_tracking_dict[job_name]['result']):
                    result_shape = self.jobs_tracking_dict[job_name]['result'].shape
            result_outputs = np.empty((len(job_names_ordered),) + result_shape)
            for job_i, job_name in enumerate(job_names_ordered):
                result_outputs[job_i] = self.jobs_tracking_dict[job_name]['result']
        else:
            result_outputs = np.empty(0)

        return result_outputs



    def prepare_job_parameters(self, new_parameters, pbs_submission_infos):
        '''
            A JobWrapper requires a dictionary of parameters. Set the ones we are optimising directly.

            Also sets some default required ones.
        '''

        job_submission_parameters = pbs_submission_infos['other_options'].copy()
        job_submission_parameters.update(new_parameters)
        job_submission_parameters['job_action'] = job_submission_parameters['action_to_do']
        job_submission_parameters['action_to_do'] = 'launcher_do_run_job'

        return job_submission_parameters


    def track_new_job(self, job, parameters=dict()):
        '''
            Enter a new job in the Tracking dictionary.

            Sets some default values in the process.

            dict[job_name] -> dict(status=['waiting', 'submitted', 'completed'], result=None, jobwrapper=None, job_submission_parameters=None, parameters=None)
        '''

        self.jobs_tracking_dict[job.job_name] = dict(status='waiting', job=job, job_submission_parameters=job.experiment_parameters, result=None, parameters=parameters, time_started=None, number_submissions=0)
        self.result_tracking_dict[tuple(parameters.items())] = dict(jobname=job.job_name, result=None)


    def complete_job(self, job_name):
        '''
            Complete a job:
                - Change its status
                - Update its result
                - Put the result in the result_tracking_dict
        '''

        self.jobs_tracking_dict[job_name]['status'] = 'completed'
        self.jobs_tracking_dict[job_name]['result'] = self.jobs_tracking_dict[job_name]['job'].get_result()
        self.result_tracking_dict[tuple(self.jobs_tracking_dict[job_name]['parameters'].items())]['result'] = self.jobs_tracking_dict[job_name]['result']


    def submit_jobwrapper(self, job, pbs_submission_infos, submit=False, debug_overwrite=False):
        '''
            Take a JobWrapper and submits it.
        '''

        # Force the job_name, to make all the file synchronization easier...
        job.experiment_parameters['job_name'] = job.job_name

        pbs_submission_infos_bis = pbs_submission_infos.copy()
        pbs_submission_infos_bis['other_options'] = job.experiment_parameters

        # Handle cases were the exact same job already ran (and thus the result_sync_* file already exists), in that case do not submit it, it will be reloaded automatically.
        if not job.check_completed():
            debug_pre = self.debug
            self.debug = debug_overwrite
            # This may block, depending on pbs_submission_infos (e.g. if limit on concurrent jobs is set)
            self.create_submit_job_parameters(pbs_submission_infos_bis, submit=submit)
            self.debug = debug_pre

        job.flag_job_submitted()
        self.jobs_tracking_dict[job.job_name]['status'] = 'submitted'
        self.jobs_tracking_dict[job.job_name]['time_started'] = time.time()
        self.jobs_tracking_dict[job.job_name]['number_submissions'] += 1


    def wait_all_jobs_collect_results(self, result_callback_function_infos=None, sleeping_period=dict(min=60, max=180), completion_progress=None, pbs_submission_infos=None, max_number_submissions=3):
        '''
            Wait for all Jobs to be completed, and collect the results when they are
            Optionally accepts a callback method on finding a result.
                result_callback_function_infos:
                'function':    f(job=JobWrapper, parameters=dict())
                'parameters':  dict()
        '''

        # Construct the list of submitted jobs.
        # Will use a deque (queue) because it's more efficient and nice
        submitted_job_names = collections.deque([job_name for job_name, job_dict in self.jobs_tracking_dict.iteritems() if job_dict['status'] == 'submitted'])

        last_str_len = 0
        while len(submitted_job_names) > 0:

            # Pop a job name (don't forget to put it in back later if needed)
            current_job_name = submitted_job_names.popleft()

            # Now do the work
            if self.jobs_tracking_dict[current_job_name]['status'] == 'completed':
                # If this job is already completed and has been tracked, jump to the next one!
                pass

            elif self.jobs_tracking_dict[current_job_name]['status'] == 'submitted':

                if self.jobs_tracking_dict[current_job_name]['job'].check_completed():
                    # This job just finished! Fantastic news

                    # Get the result
                    self.complete_job(current_job_name)

                    # Call the result_callback_function if it exists!
                    if result_callback_function_infos is not None:
                        result_callback_function_infos['function'](job=self.jobs_tracking_dict[current_job_name]['job'], parameters=result_callback_function_infos['parameters'])

                    if self.debug:
                        str_completion = "Job {0} done. Result: {1}. {2} left.".format(current_job_name, self.jobs_tracking_dict[current_job_name]['result'], len(submitted_job_names))

                        # (this ridiculous len(str) business is to have some pretty output, as we write \r)
                        self.logger.info(str_completion + " "*(last_str_len - len(str_completion)))

                    if completion_progress is not None:
                        completion_progress.increment()

                else:
                    ## Not done. Wait a bit and check the next job's state.
                    # Check how long we've waited
                    waited_time = time.time() - self.jobs_tracking_dict[current_job_name]['time_started']
                    if (waited_time > utils.convert_deltatime_str_to_seconds(self.pbs_options['walltime'])*1.2):
                        # Waited too long...
                        # try to resubmit it!
                        if self.debug:
                            self.logger.info("Waited more than walltime for job %s, resubmitting it (%d/%d)         " % (current_job_name, self.jobs_tracking_dict[current_job_name]['number_submissions'], max_number_submissions))

                        # Only resubmit a certain number of times...
                        if self.jobs_tracking_dict[current_job_name]['number_submissions'] < max_number_submissions:

                            self.submit_jobwrapper(self.jobs_tracking_dict[current_job_name]['job'], pbs_submission_infos, submit=True)
                        else:
                            # the walltime may be too short, just discard it
                            self.jobs_tracking_dict[current_job_name]['job'].store_result()
                            self.complete_job(current_job_name)
                            if completion_progress is not None:
                                completion_progress.increment()

                    # Sleep for some time
                    # Decide for how long to sleep
                    sleep_time_rnd = np.random.randint(sleeping_period['min'], sleeping_period['max'])

                    if self.debug:
                        status_str = "Waiting on Job %s, waited %d/%d. Sleeping for %d sec now." % (current_job_name, waited_time, utils.convert_deltatime_str_to_seconds(self.pbs_options['walltime'])*1.2, sleep_time_rnd)

                        if completion_progress is not None:
                            # Also add how much time to completion
                            status_str += " %.2f%%, %s left - %s. %d jobs left         " % (completion_progress.percentage(), completion_progress.time_remaining_str(), completion_progress.eta_str(), len(submitted_job_names)+1)

                        status_str += '\r'
                        sys.stdout.write(status_str)
                        sys.stdout.flush()

                        last_str_len = len(status_str)

                    # Sleep for a bit
                    time.sleep(sleep_time_rnd)

                    # Reput the job in the queue, it's not finished
                    submitted_job_names.append(current_job_name)






def test_sequential_optimisation():
    '''
        Test for generate_submit_sequential_optimisation
    '''

    run_label='test_seq_pbs_simple'
    submission_parameters_dict = dict(
        run_label=run_label,
        submit_jobs = True,
        sleeping_period = dict(min=10, max=30),
        dict_parameters_range = dict(T=dict(sampling_type='randint', low=1, high=6, dtype=int), sigmax=dict(sampling_type='uniform', low=0.01, high=1.0, dtype=float), M=dict(sampling_type='randint', low=6, high=625, dtype=int)),
        pbs_submission_infos = dict(description='Testing sequential optim',
                            command='python $WORKDIR/experimentlauncher.py',
                            other_options=dict(action_to_do='launcher_do_simple_run',
                                               inference_method='none',
                                               M=100,
                                               output_directory='.',
                                               autoset_parameters=None,
                                               label=run_label,
                                               session_id='pbs1',
                                               experiment_data_dir=os.path.normpath(os.path.join(os.environ['WORKDIR_DROP'], '../../experimental_data')),
                                               result_computation='random'
                                               ),
                            walltime='1:00:00',
                            memory='2gb',
                            simul_out_dir=os.path.join(os.getcwd(), run_label.format(**locals())),
                            pbs_submit_cmd='sbatch',
                            submit_label='test_seq_pbs')
    )
    default_params = (('filtering_function', None), ('filtering_function_parameters', None), ('num_random_samples', 100))
    for key, val in default_params:
        submission_parameters_dict.setdefault(key, val)

    # result_callback_function to track best parameter
    best_parameters_seen = dict(result=np.inf, job_name='', parameters=None)
    def best_parameters_callback(job, parameters=None):
        best_parameters_seen = parameters['best_parameters_seen']
        if job.get_result() <= best_parameters_seen['result']:
            # New best parameter!
            best_parameters_seen['result'] = job.get_result()
            best_parameters_seen['job_name'] = job.job_name
            best_parameters_seen['parameters'] = job.experiment_parameters

            self.logger.info("\n\n>>>>>> Found new best parameters: \n%s\n\n" % best_parameters_seen)
    submission_parameters_dict['result_callback_function_infos'] = dict(function=best_parameters_callback, parameters=dict(best_parameters_seen=best_parameters_seen))

    # Create a SubmitPBS
    submit_pbs = SubmitPBS(pbs_submission_infos=submission_parameters_dict['pbs_submission_infos'], debug=True)

    # Run the big useless sequential optimisation
    submit_pbs.generate_submit_sequential_optimisation(submission_parameters_dict)


def test_cmaes_optimisation():
    '''
        Test for perform_cma_es_optimization
    '''

    run_label='test_cmaes'
    # dict_parameters_range =dict(M=dict(low=5, high=800, x0=100, dtype=int), sigmax=dict(low=0.01, high=1.0, dtype=float), ratio_conj=dict(low=0.0, high=1.0, dtype=float))
    # dict_par_range =dict(sigmax=dict(low=0.01, high=1.0, dtype=float), ratio_conj=dict(low=0.0, high=1.0, dtype=float))
    dict_par_range =dict(M=dict(low=5, high=800, dtype=int), ratio_conj=dict(low=0.0, high=1.0, dtype=float))

    submission_parameters_dict = dict(
        run_label=run_label,
        submit_jobs = True,
        sleeping_period = dict(min=5, max=10),
        dict_parameters_range = dict_par_range,
        pbs_submission_infos = dict(description='Testing CMA-ES optim',
                            command='python $WORKDIR/experimentlauncher.py',
                            other_options=dict(action_to_do='launcher_do_memory_curve_marginal_fi',
                                               inference_method='max_lik',
                                               T=1,
                                               M=200,
                                               N=300,
                                               num_samples=500,
                                               selection_method='last',
                                               num_repetitions=5,
                                               sigmax=0.2,
                                               sigmay=0.0001,
                                               code_type='mixed',
                                               output_directory='.',
                                               autoset_parameters=None,
                                               label=run_label,
                                               session_id='emkappa',
                                               experiment_data_dir=os.path.normpath(os.path.join(os.environ['WORKDIR_DROP'], '../../experimental_data')),
                                               result_computation='distemkappa_bays09'
                                               ),
                            walltime='00:08:00',
                            memory='2gb',
                            simul_out_dir=os.path.join(os.getcwd(), run_label.format(**locals())),
                            pbs_submit_cmd='sbatch',
                            submit_label='test_cmaes')
    )

    # CMA/ES Parameters!
    submission_parameters_dict['cma_population_size'] = 30
    submission_parameters_dict['cma_sigma0'] = 1.0
    submission_parameters_dict['cma_logger_do_plot'] = True
    submission_parameters_dict['cma_use_auto_scaling'] = True
    submission_parameters_dict['cma_use_bounds'] = True


    # result_callback_function to track best parameter
    best_parameters_seen = dict(result=None, job_name='', parameters=None)
    def best_parameters_callback(job, parameters=None):
        best_parameters_seen = parameters['best_parameters_seen']
        if best_parameters_seen['result'] is None or job.get_result() <= best_parameters_seen['result'] and not np.isnan(job.get_result()):
            # New best parameter!
            best_parameters_seen['result'] = job.get_result()
            best_parameters_seen['job_name'] = job.job_name
            best_parameters_seen['parameters'] = job.experiment_parameters

            self.logger.info("\n\n>>>>>> Found new best parameters: \n%s\n\n" % best_parameters_seen)
    submission_parameters_dict['result_callback_function_infos'] = dict(function=best_parameters_callback, parameters=dict(best_parameters_seen=best_parameters_seen))

    # Callback after each iteration, let's save all candidates/fitness, and do a contour plot
    data_io = dataio.DataIO(label='test_cmaes', output_folder='.')
    cma_iter_parameters = dict(ax=None, candidates=[], fitness=[], dataio=data_io)
    def cma_iter_plot_contourf_candidates(all_variables, parameters=None):
        candidates = parameters['candidates']
        fitness = parameters['fitness']
        # Take candidates and fitness and append them
        candidates.extend(all_variables['parameters_candidates_array'])
        fitness.extend(all_variables['fitness_results'].tolist())

        # Do a plot
        parameters['ax'] = utils.contourf_interpolate_data(np.array(candidates), np.array(fitness), xlabel='Ratio_conj', ylabel='sigma x', title='Optimisation landscape', interpolation_numpoints=200, interpolation_method='linear', ax_handle=parameters['ax'], log_scale=True)

        if parameters['dataio'] is not None:
            parameters['dataio'].save_variables_default(locals(), ['candidates', 'fitness'])
            parameters['dataio'].save_current_figure('cmaes_optim_landscape_{label}_{unique_id}.pdf')

    submission_parameters_dict['cma_iter_callback_function_infos'] = dict(function=cma_iter_plot_contourf_candidates, parameters=cma_iter_parameters)


    # Create a SubmitPBS
    submit_pbs = SubmitPBS(pbs_submission_infos=submission_parameters_dict['pbs_submission_infos'], debug=True)

    # Run the CMA/ES optimization.
    #  Here we optimize for Bays09 kappa fit for T=1, using Max_lik to speed things up
    submit_pbs.perform_cma_es_optimization(submission_parameters_dict)


def test_cmaes_optimisation_3d():
    '''
        Test for perform_cma_es_optimization
    '''

    run_label='test_cmaes3d'
    dict_par_range =dict(M=dict(low=10, high=500, dtype=int), ratio_conj=dict(low=0.0, high=1.0, dtype=float), sigmax=dict(low=0.0001, high=2.0, dtype=float))

    submission_parameters_dict = dict(
        run_label=run_label,
        submit_jobs = True,
        sleeping_period = dict(min=10, max=30),
        dict_parameters_range = dict_par_range,
        pbs_submission_infos = dict(description='Testing CMA-ES optim',
                            command='python $WORKDIR/experimentlauncher.py',
                            other_options=dict(action_to_do='launcher_do_memory_curve_marginal_fi',
                                               inference_method='max_lik',
                                               T=1,
                                               M=200,
                                               N=300,
                                               num_samples=500,
                                               selection_method='last',
                                               num_repetitions=5,
                                               sigmax=0.2,
                                               sigmay=0.0001,
                                               code_type='mixed',
                                               output_directory='.',
                                               autoset_parameters=None,
                                               label=run_label,
                                               session_id='emkappa',
                                               experiment_data_dir=os.path.normpath(os.path.join(os.environ['WORKDIR_DROP'], '../../experimental_data')),
                                               result_computation='distemkappa_bays09'
                                               ),
                            walltime='00:15:00',
                            memory='2gb',
                            simul_out_dir=os.path.join(os.getcwd(), run_label.format(**locals())),
                            pbs_submit_cmd='sbatch',
                            submit_label=run_label)
    )

    # CMA/ES Parameters!
    submission_parameters_dict['cma_population_size'] = 30
    submission_parameters_dict['cma_sigma0'] = 1.0
    submission_parameters_dict['cma_logger_do_plot'] = True
    submission_parameters_dict['cma_use_auto_scaling'] = True
    submission_parameters_dict['cma_use_bounds'] = True


    # result_callback_function to track best parameter
    best_parameters_seen = dict(result=None, job_name='', parameters=None)
    def best_parameters_callback(job, parameters=None):
        best_parameters_seen = parameters['best_parameters_seen']
        if best_parameters_seen['result'] is None or job.get_result() <= best_parameters_seen['result'] and not np.isnan(job.get_result()):
            # New best parameter!
            best_parameters_seen['result'] = job.get_result()
            best_parameters_seen['job_name'] = job.job_name
            best_parameters_seen['parameters'] = job.experiment_parameters

            self.logger.info("\n\n>>>>>> Found new best parameters: \n%s\n\n" % best_parameters_seen)
    submission_parameters_dict['result_callback_function_infos'] = dict(function=best_parameters_callback, parameters=dict(best_parameters_seen=best_parameters_seen))

    # Callback after each iteration, let's save all candidates/fitness, and do a contour plot
    data_io = dataio.DataIO(label=run_label, output_folder='.')
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
        parameters['ax'] = utils.scatter3d(candidates_arr[:, 0], candidates_arr[:, 1], candidates_arr[:, 2], c=np.log(fitness_arr), xlabel=all_variables['parameter_names_sorted'][0], ylabel=all_variables['parameter_names_sorted'][1], zlabel=all_variables['parameter_names_sorted'][2], ax_handle=parameters['ax'])

        if parameters['dataio'] is not None:
            parameters['dataio'].save_variables_default(locals(), ['candidates', 'fitness'])
            parameters['dataio'].save_current_figure('cmaes_optim_landscape_scatter3d_{label}_{unique_id}.pdf')

    submission_parameters_dict['cma_iter_callback_function_infos'] = dict(function=cma_iter_plot_contourf_candidates, parameters=cma_iter_parameters)


    # Create a SubmitPBS
    submit_pbs = SubmitPBS(pbs_submission_infos=submission_parameters_dict['pbs_submission_infos'], debug=True)

    # Run the CMA/ES optimization.
    #  Here we optimize for Bays09 kappa fit for T=1, using Max_lik to speed things up
    submit_pbs.perform_cma_es_optimization(submission_parameters_dict)




if __name__ == '__main__':

    # Simple usage
    if False:
        cwd = os.getcwd()
        submit_pbs = SubmitPBS(working_directory=os.path.join(cwd, 'simple_pbs_test'), debug=True)
        # submit_pbs.make_script('echo "it works"')
        submit_pbs.submit_job('echo "it works"')

    # This is how you should generate random parameters and scripts
    if False:
        num_samples = 10
        pbs_submission_infos = dict(description='Getting the full memory curves for all the parameters compatible with the experimental Fisher information', command='echo "Testing PBS"', other_options=dict(option1='1', option2=2), walltime='10:00:00', memory='2gb', simul_out_dir=os.path.join(cwd, 'testing_pbs'))
        dict_parameters_range = dict(param1=dict(sampling_type='uniform', low=0.01, high=15.0, dtype=float), param2=dict(sampling_type='uniform', low=0.01, high=0.8, dtype=float))
        filtering_function = lambda parameters, dict_parameters_range, other_options: parameters['param1'] > 1.0

        submit_pbs = SubmitPBS(pbs_submission_infos=pbs_submission_infos, debug=True)
        submit_pbs.generate_submit_constrained_parameters_random(dict_parameters_range, num_samples=num_samples, filtering_function=filtering_function, filtering_function_parameters=None, pbs_submission_infos=pbs_submission_infos, submit_jobs=False)

    # Better preparation, big gun here.
    if False:
        test_sequential_optimisation()

    # Now test the funky CMA-ES optimisation
    if False:
        test_cmaes_optimisation()
        # test_cmaes_optimisation_3d()




