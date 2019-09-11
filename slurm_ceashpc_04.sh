#!/bin/bash
#SBATCH --job-name=sparse-run
#SBATCH --output=/network/rit/lab/ceashpc/bz383376/git/sparse-auc/logs/array_%A_%a.out
#SBATCH --array=74-99
#SBATCH --nodelist=ceashpc-07
#SBATCH --time=12:00:00
#SBATCH --partition=ceashpc
#SBATCH --mem=2G
#SBATCH --ntasks=1
# %A_%a notation is filled in with the master job id (%A) and the array task id (%a)
# the environment variable SLURM_ARRAY_TASK_ID contains
# the index corresponding to the current job step
/network/rit/lab/ceashpc/bz383376/opt/env-python2.7.14/bin/python test_on_09_sector.py
