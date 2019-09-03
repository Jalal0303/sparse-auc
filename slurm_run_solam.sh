#!/bin/bash
#SBATCH --job-name=slurm-run-sparse
#SBATCH --output=/network/rit/lab/ceashpc/bz383376/git/sparse-auc/logs/array_%A_%a.out
#SBATCH --array=0-24
#SBATCH --time=12:00:00
#SBATCH --partition=ceashpc
#SBATCH --mem=2G
#SBATCH --ntasks=1

# %A_%a notation is filled in with the master job id (%A) and the array task id (%a)
# the environment variable SLURM_ARRAY_TASK_ID contains
# the index corresponding to the current job step
/network/rit/lab/ceashpc/bz383376/opt/env-python2.7.14/bin/python slurm_run_solam.py
