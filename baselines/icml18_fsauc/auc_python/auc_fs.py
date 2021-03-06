# -*- coding: utf-8 -*-
"""
Created on Tue Nov  6 09:25:13 2018

@author: Yunwen

# -*- coding: utf-8 -*-
Spyder Editor

We apply the algorithm in Liu, 2018 ICML to do Fast AUC maximization

Input:
    x_tr: training instances
    y_tr: training labels
    x_te: testing instances
    y_te: testing labels
    options: a dictionary 
        'ids' stores the indices of examples traversed, ids divided by number of training examples is the number of passes
        'eta' stores the initial step size
        'beta': the parameter R
        'n_pass': the number of passes
        'time_lim': optional argument, the maximal time allowed
Output:
    aucs: results on iterates indexed by res_idx
    time:
"""
import os
import time
import numpy as np
from itertools import product
from sklearn import metrics
from sklearn.model_selection import KFold
from sklearn.metrics import roc_auc_score
import pickle as pkl
# from proj_l1ball import euclidean_proj_l1ball
import timeit
from scipy.sparse import isspmatrix

data_path = '/network/rit/lab/ceashpc/bz383376/data/icml2020/00_simu/'


def auc_fs(x_tr, y_tr, x_te, y_te, options):
    # options
    delta = 1e-1
    ids = options['ids']
    n_ids = len(ids)
    eta = options['eta']
    R = options['beta']  # beta is the parameter R, we use beta for consistency
    n_tr, dim = x_tr.shape
    v_1, alpha_1 = np.zeros(dim + 2), 0
    # the estimate of probability with positive example
    sp, t, time_s = 0, 0, 0
    sx_pos = np.zeros(dim)  # summation of positive instances
    sx_neg = np.zeros(dim)  # summation of negative instances
    m_pos = sx_pos
    m_neg = sx_neg
    # we have normalized the data
    m = int(0.5 * np.log2(2 * n_ids / np.log2(n_ids))) - 1
    n_0 = int(n_ids / m)
    para_r = 2 * np.sqrt(3) * R
    p_hat, beta, D = 0, 9, 2 * np.sqrt(2) * para_r
    gd = np.zeros(dim + 2)
    v_ave = np.zeros_like(v_1)
    for k in range(m):
        v_sum = np.zeros(dim + 2)
        v, alpha = v_1, alpha_1
        for kk in range(n_0):
            x_t = x_tr[ids[t], :]
            y_t = y_tr[ids[t]]
            wx = np.inner(x_t, v[:dim])
            if y_t == 1:
                sp = sp + 1
                p_hat = sp / (t + 1)
                sx_pos = sx_pos + x_t
                gd[:dim] = (1 - p_hat) * (wx - v[dim] - 1 - alpha) * x_t
                gd[dim] = (p_hat - 1) * (wx - v[dim])
                gd[dim + 1] = 0
                gd_alpha = (p_hat - 1) * (wx + p_hat * alpha)
            else:
                p_hat = sp / (t + 1)
                sx_neg = sx_neg + x_t
                gd[:dim] = p_hat * (wx - v[dim + 1] + 1 + alpha) * x_t
                gd[dim] = 0
                gd[dim + 1] = p_hat * (v[dim + 1] - wx)
                gd_alpha = p_hat * (wx + (p_hat - 1) * alpha)
            t = t + 1
            v = v - eta * gd
            alpha = alpha + eta * gd_alpha

            # some projection
            # ---------------------------------
            v[:dim] = ProjectOntoL1Ball(v[:dim], R)
            tnm = np.abs(v[dim])
            if tnm > R:
                v[dim] = v[dim] * (R / tnm)
            tnm = np.abs(v[dim + 1])
            if tnm > R:
                v[dim + 1] = v[dim + 1] * (R / tnm)
            tnm = np.abs(alpha)
            if tnm > 2 * R:
                alpha = alpha * (2 * R / tnm)

            vd = v - v_1
            tnm = np.linalg.norm(vd)
            if tnm > para_r:
                vd = vd * (para_r / tnm)
            v = v_1 + vd
            ad = alpha - alpha_1
            tnm = np.abs(ad)
            if tnm > D:
                ad = ad * (D / tnm)
            alpha = alpha_1 + ad
            v_sum = v_sum + v
            v_ave = v_sum / (kk + 1)
        para_r = para_r / 2
        # update D and beta
        tmp1 = 12 * np.sqrt(2) * (2 + np.sqrt(2 * np.log(12 / delta))) * R
        tmp2 = min(p_hat, 1 - p_hat) * n_0 - np.sqrt(2 * n_0 * np.log(12 / delta))
        if tmp2 > 0:
            D = 2 * np.sqrt(2) * para_r + tmp1 / np.sqrt(tmp2)
        else:
            D = 1e7
        tmp1 = 288 * ((2 + np.sqrt(2 * np.log(12 / delta))) ** 2)
        tmp2 = min(p_hat, 1 - p_hat) - np.sqrt(2 * np.log(12 / delta) / n_0)
        if tmp2 > 0:
            beta_new = 9 + tmp1 / tmp2
        else:
            beta_new = 1e7
        eta = min(np.sqrt(beta_new / beta) * eta / 2, eta)
        beta = beta_new
        if sp > 0:
            m_pos = sx_pos / sp
        if sp < t:
            m_neg = sx_neg / (t - sp)
        v_1 = v_ave
        alpha_1 = np.inner(m_neg - m_pos, v_ave[:dim])
    return v_ave[:dim]


def ProjectOntoL1Ball(v, b):
    nm = np.abs(v)
    if nm.sum() < b:
        w = v
    else:
        u = np.sort(nm)[::-1]
        sv = np.cumsum(u)
        rho = np.nonzero(u * np.arange(1, len(v) + 1) > (sv - b))[0][-1]
        theta = (sv[rho] - b) / (rho + 1)
        w = np.sign(v) * np.maximum(nm - theta, 0)
    return w


task_id = 0
k_fold, passes = 5, 10
tr_list = [1000]
mu_list = [0.3]
posi_ratio_list = [0.5]
fig_list = ['fig_4']
results = dict()
s_time = time.time()
for num_tr, mu, posi_ratio, fig_i in product(tr_list, mu_list, posi_ratio_list, fig_list):
    f_name = data_path + 'data_task_%02d_tr_%03d_mu_%.1f_p-ratio_%.1f.pkl'
    data = pkl.load(open(f_name % (task_id, num_tr, mu, posi_ratio), 'rb'))
    fold_id = 0
    key = (task_id, fold_id, passes, num_tr, mu, posi_ratio, fig_i)
    results[key] = dict()
    method = 'fsauc'
    list_r = 10. ** np.arange(-1, 6, 1, dtype=float)
    list_g = 2. ** np.arange(-10, 0, 1, dtype=float)
    for para_r, para_g in product(list_r, list_g):
        tr_index = data[fig_i]['task_%d_fold_%d' % (task_id, fold_id)]['tr_index']
        te_index = data[fig_i]['task_%d_fold_%d' % (task_id, fold_id)]['te_index']
        ids = []
        for i in range(10):
            ids.extend(range(len(tr_index)))
        options = {'ids': ids, 'eta': para_g, 'beta': para_r, 'n_pass': 10, 'rec': 0.5}
        wt = auc_fs(x_tr=np.asarray(data[fig_i]['x_tr'][tr_index], dtype=float),
                    y_tr=np.asarray(data[fig_i]['y_tr'][tr_index], dtype=float),
                    x_te=np.asarray(data[fig_i]['x_tr'][te_index], dtype=float),
                    y_te=np.asarray(data[fig_i]['y_tr'][te_index], dtype=float),
                    options=options)
        auc = roc_auc_score(y_true=data[fig_i]['y_tr'][te_index],
                            y_score=np.dot(data[fig_i]['x_tr'][te_index], wt))
        print(para_r, para_g, auc)
