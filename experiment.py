import argparse
import re
import random
import time
import json
from collections import defaultdict as ddict
from subprocess import PIPE,Popen,call

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

def get_params(exp_num, seed, baseline_num, comb_params, param_pool, only_base):
    '''
    exp_num: The number of experiments to run
    seed: The default seed to run the experiment on, if its -1, then we randomly generate seed for each experiment
    baseline_num: The number of baseline exps to run on 1 seed
    comb_params: The params to make combinations from, must be in form of '-param1 -param2 -param3....'
    param_pool: The path to params to use, the first line is the baseline, the following stores the param (every single line stores one param) to use
    only_base: Set to true if only want to run baseline

    return: a seed to params map (s2p)
    '''
    s2p_map = {}
    for _ in range(exp_num):
        default_seed = random.randint(0,50000) if seed == -1 else seed
        seed_suffix = f"-seed {default_seed}"
        with open(param_pool,"r") as f:
            lines = f.readlines()
        baseline = lines[0].strip("\n")
        # add baselines to cmds (if there is one)
        cmds = [f"{baseline} {seed_suffix}" for _ in range(baseline_num)]
        if only_base:
            # no need to operate on the rest if only want the baselines, skip the rest by continue and go to next iteration
            s2p_map[seed_suffix] = cmds
            continue
        # only params are created differently if comb_params is given as non-empty str
        if comb_params == "":
            params = [l.strip("\n") for l in lines[1:]]
        else:
            params = get_comb(comb_params)
            
        params_seed = [f"{p} {seed_suffix}" for p in params]
        cmds += [f"{baseline} {p_s}" for p_s in params_seed]
        s2p_map[seed_suffix] = cmds
    return s2p_map

def get_free_gpus(gpu_num):
    '''
    gpu_num: the total number of GPUs available in server or local
    return: the list of free gpu idx
    '''
    # get output from stdout
    pipe = Popen(["screen","-ls"], stdout=PIPE)
    text = pipe.communicate()[0].decode("utf-8") # index 0 -> stdout of PIPE
    running_screens = text.split("\n")[1:-2]
    all_gpus = set([i for i in range(gpu_num)])

    if running_screens != []: # there are running gpus
        running_gpus = []
        for l in running_screens:
            gpu_match = re.search(r".*exp_\d",l)
            if gpu_match:
                gpu_idx = gpu_match.group()[-1]
                running_gpus.append(int(gpu_idx))
        running_gpus = set(running_gpus)
        free_gpus = list(all_gpus.difference(running_gpus))
        return free_gpus
    else: # no running gpus, all free
        return [i for i in range(gpu_num)]

def run_exp(cmds, gap, gpu_num):
    '''
    cmds: cmds to run
    gap: the time diff between 2 checks of experiments
    gpu_num: the total number of GPUs available in server or local

    return: none, this function starts running experiments 
    '''
    while True:
        free_gpus = get_free_gpus(gpu_num)
        cmd_left = len(cmds)
        if len(free_gpus) > cmd_left:
            free_gpus = free_gpus[:cmd_left] # match free_gpus with cmd_left, so that we do not waste time

        if free_gpus != []:
            for gpuidx in free_gpus:
                cmd = cmds[0]
                gpu_match = re.search(r" -gpu \d ",cmd).group() # might need to be changed for future experiments
                cmd_pre, cmd_post = cmd.split(gpu_match)
                exec_cmd = f"python {cmd_pre} -gpu {gpuidx} {cmd_post}" 
                call(["screen","-dmSL",f"exp_{gpuidx}","bash","-c",exec_cmd]) # call (screen -dmSL exp_9 bash -c "python [baseline] [params]")
                cmds = cmds[1:] # reduce the cmds left to run by 1
                time.sleep(6) # between every 2 calls, gap by 3 seconds to write log files
                
            if cmds == []: # all cmds assigned to GPUs, we are good to go, otherwise, keep looping every 30mins
                break
        time.sleep(gap)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("-param_pool", type=str, default="./params/params_pool.txt", help="The path to params to use, the first line is the baseline, the following stores the param (single one) to use")
    parser.add_argument("-seed", type=int, default=-1, help="The default seed to run the experiment on, if its -1, then we randomly generate seed for each experiment")
    parser.add_argument("-exp_num", type=int, default=1, help="The number of experiments to run")
    parser.add_argument("-check_gap", type=int, default=1800, help="The time gap in sec between checks on whether running experiment is done")
    parser.add_argument("-comb_params", type=str, default="", help="The params to make combinations from, must be in form of '-param1 -param2 -param3....'")
    parser.add_argument("-baseline_num", type=int, default=0, help="The number of baselines to run on 1 seed")
    parser.add_argument("-only_base", action="store_true", help="Include this option if only want to run baseline")
    parser.add_argument("-gpus", type=int, default=10, help="The number of available GPUs to use in server")
    parser.add_argument("-missing", type=str, default="", help='The missing experiments to run')
    args = parser.parse_args()

    missing_exps = args.missing
    param_pool = args.param_pool
    seed = args.seed
    exp_num = args.exp_num
    baseline_num = args.baseline_num
    gap = args.check_gap
    comb_params = args.comb_params
    gpu_num = args.gpus
    only_base = args.only_base
    

    if missing_exps != "":
        with open("missing_exp.json","r") as f:
            params = json.load(f)
            
    else:
        # params: dict s.t. k: seed, v: a list of cmd line to run, with seed added
        # ex) ["run.py -param1 -param2 -param3..."]
        params = get_params(exp_num, seed, baseline_num, comb_params, param_pool, only_base)

    for seed, cmds in params.items():
        if cmds == []:
            print("Found empty cmd!")
            break
        print(f"Assigning GPUs to run experiment with seed: {seed}")
        run_exp(cmds, gap, gpu_num)
    print("All cmds are assigned to GPUs to run, waiting for results...")

    # 1. Run 1 experiment without baseline:
    # screen -dmSL main bash -c "python experiment.py -seed 14557 "

    # 2. Run 1 experiment with X number of baselines (including other params tunning):
    # screen -dmSL main bash -c "python experiment.py -baseline_num X"

    # 3. Run experiment with only baseline (without other params tunning):
    # screen -dmSL main bash -c "python experiment.py -only_base"

    # 4. Run experiments in 3 diff seeds with X number of baselines (to calculate avg):
    # screen -dmSL main bash -c "python experiment.py -exp_num 4 -baseline_num 3"
    # screen -dmSL main bash -c "python experiment.py -missing ./missing_exp.json"

    # screen -dmSL exp_0 bash -c "python run.py -data subbkg_dd_an -gpu 0 -name subbkg_dd_nll -nodedoc -diffa -within_type -anchor CCS -init_dim 512 -seed 14557"
    # screen -dmSL exp_1 bash -c "python run.py -data subbkg_dd_an -gpu 0 -name subbkg_dd_nll -nodedoc -diffa -within_type -anchor CCS -hid_drop 0.1 -seed 20284"
    # screen -dmSL exp_2 bash -c "python run.py -data subbkg_dd_an -gpu 0 -name subbkg_dd_nll -nodedoc -diffa -within_type -anchor CCS -hid_drop 0.2 -seed 20284"
    # screen -dmSL exp_3 bash -c "python run.py -data subbkg_dd_an -gpu 0 -name subbkg_dd_nll -nodedoc -diffa -within_type -anchor CCS -hid_drop 0.4 -seed 31388"