# screen -dmSL exp_9 bash -c "python run.py -data subbkg_dd_an -gpu 9 -name subbkg_dd_nll -nodedoc -diffa -within_type -anchor CCS -gcn_drop 0.4 -seed 21897"
import argparse
import re
import random
import time

def get_comb(params_str):
    '''
    params_str: must be in form of "-param1 -param2 -param3...."
    return: a list contains all combinations of these words (min of comb of 2)
    '''
    tokens = params_str.split("-")
    tokens = [param.strip(" ") for param in tokens[1:]]
    params = [f"-{token}" for token in tokens]
    param_num = len(params)

    result = []
    for i in range(param_num-1):
        base = params[i]
        for j in range(i, param_num-1):
            for k in range(j+1, param_num):
                curl = f"{base} {params[k]}"
                result.append(curl)
            base = f"{base} {params[j+1]}"
    return result 

def get_params(exp_num, seed, baseline_num, comb_params, param_pool):
    if exp_num 



    return
def free_gpus():
    return 

def run_exp():
    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("-param_pool", type=str, default="./params/params_pool.txt", help="The path to param_pool, the first line is the baseline, the following stores the param (single one) to use")
    parser.add_argument("-seed", type=int, default=-1, help="The deafult seed to run the experiment on, if its -1, then we randomly generate seed for each experiment")
    parser.add_argument("-exp_num", type=1, default=1, help="The number of experiments to run")
    parser.add_argument("-check_gap", type=int, default=1800, help="The time gap in sec between checks on whether running experiment is done")
    parser.add_argument("-comb_params", type=str, default="", help="The params to make combinations from, must be in form of '-param1 -param2 -param3....'")
    parser.add_argument("-baseline_num", type=int, deafult=1, help="The number of baselines to run on 1 seed")

    args = parser.parse_args()

    param_pool = args.param_pool
    seed = args.seed
    exp_num = args.exp_num
    baseline_num = args.baseline_num
    gap = args.check_gap
    comb_params = args.comb_params

    # params: dict s.t. k: seed, v: a list of cmd line to run
    # ex) ["python run.py -param1 -param2 -param3..."]
    params = get_params(exp_num, seed, baseline_num, comb_params, param_pool)

    for seed, cmds in params.items():
        print(f"Assigning GPUs to run experiment with seed: {seed}")
        run_exp(cmds, gap)
    print("All cmds are assigned to GPUs to run, waiting for results...")