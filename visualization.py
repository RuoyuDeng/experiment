###################################### visulization related functions, to use in ipynb #####################################
import pandas as pd
import matplotlib.pyplot as plt
import os
import re
from collections import defaultdict as ddict

# highlight related functions

# FIXME: 1. float(tokens_s[i][0]) we want max for TCs / min for PPL
#        2. float(tokens_s[i][1]) we want min for both PPL and TCs
def compute_max(s,sign):
    '''
    s: a series with each cell being string values like: "1123 + 12312" or "123123 * 12313"
    sign: the sign we split on, "+", "*", ....
    return: a series with True/False telling whether each cell is the maximum value after computing the cell
    '''
    tokens_s = s.str.split(sign)
    indexes = list(tokens_s.index)
    avg = pd.Series([],dtype='float64').rename(s.name)
    stderr = pd.Series([],dtype='float64').rename(s.name)
    for i in indexes:
        avg[i] = float(tokens_s[i][0]) 
        stderr[i] = float(tokens_s[i][1])
    result_tf = avg == avg.max()
    df_avg = avg.to_frame()
    cols = list(df_avg.columns)
    # get all indexes in the series that equals to max value
    avg_maxidxs = list(df_avg[df_avg[cols[0]] == df_avg[cols[0]].max()].index)

    # from all these indexes with same max avgs, find the one with min stderr and remove it from idxlist
    resultidx = avg_maxidxs.remove(stderr[avg_maxidxs].idxmin())
    # the rest (when min stderr idx is removed) will be the ones must be false
    if resultidx != None:
        result_tf[resultidx] = False
    return result_tf
    
def compute_min(s,sign):
    '''
    s: a series with each cell being string values like: "1123 + 12312" or "123123 * 12313"
    sign: the sign we split on, "+", "*", ....
    return: a series with True/False telling whether each cell is the maximum value after computing the cell
    '''
    tokens_s = s.str.split(sign)
    indexes = list(tokens_s.index)
    avg = pd.Series([],dtype='float64').rename(s.name)
    stderr = pd.Series([],dtype='float64').rename(s.name)
    for i in indexes:
        avg[i] = float(tokens_s[i][0]) 
        stderr[i] = float(tokens_s[i][1])
    result_tf = avg == avg.min()
    df_avg = avg.to_frame()
    cols = list(df_avg.columns)
    # get all indexes in the series that equals to max value
    avg_maxidxs = list(df_avg[df_avg[cols[0]] == df_avg[cols[0]].max()].index)

    # from all these indexes with same max avgs, find the one with min stderr and remove it from idxlist
    resultidx = avg_maxidxs.remove(stderr[avg_maxidxs].idxmin())
    # the rest (when min stderr idx is removed) will be the ones must be false
    if resultidx != None:
        result_tf[resultidx] = False
    return result_tf

def same_params(s2p_map):
    '''
    s2p_map: a seeds to full-params mapping dict
    return: 
            1. a dict of shared parameters tunned for all seeds params
            key: seed, value: the params to compare
            2. a list of unique shared params
    '''
    sets = []
    for params in s2p_map.values():
        params_set = []
        for param in params:
            match = re.search(r" -seed .*",param).group()
            newl = param.replace(match,"")
            params_set.append(newl)
        sets.append(set(params_set))
    same_params = list(set.intersection(*sets))
    result = {}
    for seed in s2p_map.keys():
        result[seed] = [f"{param} {seed}" for param in same_params]
    return result,same_params


def get_s2p(indexes):
    '''
    indexes: a list of all indexes of the data frame
    return: a seeds to full-params mapping dict
    '''
    s2p_map = ddict(list)
    for l in indexes:
        seed = re.search(r"-seed.*",l).group()
        s2p_map[seed].append(l)
    
    return dict(s2p_map)
        


def get_f2p(param_log):
    '''
    param_log: the path to the params log file
    return: a file_name to parameters map
    '''
    f2param = {}
    with open(param_log, "r") as f:
        lines = f.readlines()
        lines = list(filter(None,lines))
        for l in lines:
            tokens = l.strip('\n').split("\t")
            k,v = tokens[0], tokens[1]
            f2param[k] = v
    return f2param

def get_row(csv_path, csv_name, f2p_map, max_measures):
    '''
    csv_path: the path to the csv file
    csv_name: the name of the csv file
    f2p_map: the dict that maps file name to the parameters tunned for such file
    return: series with all wanted info and best_epoch 
    '''
    params = f2p_map[csv_name]
    df = pd.read_csv(csv_path)
    df.rename(columns={'topic_coherence_drug-drug':'tc_drug_drug', \
        'topic_coherence_disease-disease': "tc_disease_disease", \
            "topic_coherence_drug-disease": "tc_drug_disease"}, inplace=True)
    test_row = df.iloc[-1].rename(f"{params}_test")

    df = df[:-1] # remove test row
    best_row = df.iloc[df["PPL"].idxmin()].rename(params)
    best_row['best_epoch'] = test_row["Epoch"]

    # including the max measures and their corresponding epoches
    for col in max_measures:
        best_row[f"{col}_max"] = df[col].max()
        best_row[f"{col}_max_epoch"] = df.iloc[df[col].idxmax()]["Epoch"]
    return best_row

def plt_csv(csv_path, csv_name, f2p_map, showfig=False, img_path = './tuning_img', cols = ["PPL","topic_recon", 'tc_drug_drug', "tc_disease_disease", "tc_drug_disease"]):
    '''
    csv_path: the path to the csv file
    csv_name: the name of the csv file
    f2p_map: the dict that maps file name to the parameters tunned for such file
    showfig: switch for displaying plts or not
    return: Nothing
    '''
    df = pd.read_csv(csv_path)
    df.rename(columns={'topic_coherence_drug-drug':'tc_drug_drug', \
        'topic_coherence_disease-disease': "tc_disease_disease", \
            "topic_coherence_drug-disease": "tc_drug_disease"}, inplace=True)
    
    figname = csv_name[:-4]
    fig, axs = plt.subplots(nrows=2,ncols=3, figsize=(13,10))
    fig.suptitle(f"{figname}, Tuned: {f2p_map[csv_name]}")
    plt.subplots_adjust(hspace=0.5)
    for col, ax in zip(cols,axs.ravel()):
        # excluding the test result
        data = df[col][:-1]
        diff = data.iloc[-1] - data.iloc[0]
        ftype = col.split("_")[-1]
        title = f"TC_{ftype}" if col != "topic_recon" and col != "PPL" else col
        data.plot(ax=ax)
        ax.set_title(f"{title}, net-change: {diff:> 1.3f}")
        ax.set_xlabel("")
    fig.delaxes(axs[1,2])
    plt.savefig(os.path.join(img_path,figname+".jpg")) # store it before showing it
    if showfig:
        plt.show()
    plt.close(fig)
    