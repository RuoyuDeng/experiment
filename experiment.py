
import argparse
import re
import random
import time
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

def get_params(exp_num, seed, baseline_num, comb_params, param_pool):
    '''
    exp_num: The number of experiments to run
    seed: The deafult seed to run the experiment on, if its -1, then we randomly generate seed for each experiment
    baseline_num: The number of baseline exps to run on 1 seed
    comb_params: The params to make combinations from, must be in form of '-param1 -param2 -param3....'
    param_pool: The path to params to use, the first line is the baseline, the following stores the param (every single line stores one param) to use
    '''
    s2p_map = {}
    for _ in range(exp_num):
        default_seed = random.randint(0,50000) if seed == -1 else seed
        seed_suffix = f"-seed {default_seed}"
        with open(param_pool,"r") as f:
            lines = f.readlines()
        baseline = lines[0]
        # add baselines to cmds
        cmds = [f"{baseline} {seed_suffix}" for _ in range(baseline_num)]

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
    gpu_num = 10
    pipe = Popen(["screen","-ls"], stdout=PIPE)
    text = pipe.communicate()[0].decode("utf-8")
    running_screens = text.split("\n")[1:-2]
    all_gpus = set([i for i in range(gpu_num)])

    if running_screens != []: # there are free gpus
        cur_gpus = []
        for l in running_screens:
            gpu_idx = re.search(r".*exp_\d",l).group()[-1]
            cur_gpus.append(int(gpu_idx))
        cur_gpus = set(cur_gpus)
        free_gpus = list(all_gpus.difference(cur_gpus))
        return free_gpus
    else: # no free gpus
        return []

def run_exp(cmds, gap, gpu_num):
    while True:
        free_gpus = get_free_gpus(gpu_num)
        free_gpusn = len(free_gpus)
        if free_gpus != []:
            for gpuidx in free_gpus:
                cmd = cmds[0]
                gpu_match = re.search(r" -gpu \d ",cmd).group()
                cmd_pre, cmd_post = cmd.split(gpu_match)
                exec_cmd = f"python {cmd_pre} -gpu {gpuidx} {cmd_post}"
                call(["screen","-dmSL",f"exp_{gpuidx}","bash","-c",exec_cmd])
                # screen -dmSL exp_9 bash -c "python run.py -data subbkg_dd_an -gpu 9 -name subbkg_dd_nll -nodedoc -diffa -within_type -anchor CCS -gcn_drop 0.4 -seed 21897"
            cmds = cmds[free_gpusn:]
                
        time.sleep(gap)

    # we want to run screen -dmSL exp_? bash -c "python run.py -param1 -param2 ..."
    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("-param_pool", type=str, default="./params/params_pool.txt", help="The path to params to use, the first line is the baseline, the following stores the param (single one) to use")
    parser.add_argument("-seed", type=int, default=-1, help="The deafult seed to run the experiment on, if its -1, then we randomly generate seed for each experiment")
    parser.add_argument("-exp_num", type=1, default=1, help="The number of experiments to run")
    parser.add_argument("-check_gap", type=int, default=1800, help="The time gap in sec between checks on whether running experiment is done")
    parser.add_argument("-comb_params", type=str, default="", help="The params to make combinations from, must be in form of '-param1 -param2 -param3....'")
    parser.add_argument("-baseline_num", type=int, deafult=1, help="The number of baselines to run on 1 seed")
    parser.add_argument("-gpus", type=int, default=10, help="The number of available GPUs to use in server")
    args = parser.parse_args()

    param_pool = args.param_pool
    seed = args.seed
    exp_num = args.exp_num
    baseline_num = args.baseline_num
    gap = args.check_gap
    comb_params = args.comb_params
    gpu_num = args.gpus

    # params: dict s.t. k: seed, v: a list of cmd line to run, with seed added
    # ex) ["run.py -param1 -param2 -param3..."]
    params = get_params(exp_num, seed, baseline_num, comb_params, param_pool)

    for seed, cmds in params.items():
        print(f"Assigning GPUs to run experiment with seed: {seed}")
        run_exp(cmds, gap, gpu_num)
    print("All cmds are assigned to GPUs to run, waiting for results...")