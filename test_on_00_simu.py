# -*- coding: utf-8 -*-
import os
import sys
import time
import numpy as np
import pickle as pkl
from itertools import product
from sklearn.model_selection import KFold
from sklearn.metrics import roc_auc_score

try:
    sys.path.append(os.getcwd())
    import sparse_module

    try:
        from sparse_module import c_algo_spam
        from sparse_module import c_algo_solam
        from sparse_module import c_algo_solam_sparse
        from sparse_module import c_algo_opauc
        from sparse_module import c_algo_sht_am
        from sparse_module import c_algo_graph_am
        from sparse_module import c_algo_fsauc
    except ImportError:
        print('cannot find some function(s) in sparse_module')
        pass
except ImportError:
    print('cannot find the module: sparse_module')
    pass

data_path = '/network/rit/lab/ceashpc/bz383376/data/icml2020/00_simu/'


def cv_spam_l1(task_id, k_fold, num_passes, data):
    list_c = 10. ** np.arange(-5, 3, 1, dtype=float)
    list_l1 = 10. ** np.arange(-5, 3, 1, dtype=float)
    s_time = time.time()
    auc_wt, auc_wt_bar = dict(), dict()
    for fold_id, para_c, para_l1 in product(range(k_fold), list_c, list_l1):
        print(fold_id, para_c, para_l1)
        algo_para = (task_id, fold_id, num_passes, para_c, para_l1, k_fold)
        tr_index = data['task_%d_fold_%d' % (task_id, fold_id)]['tr_index']
        # cross validate based on tr_index
        if (task_id, fold_id) not in auc_wt:
            auc_wt[(task_id, fold_id)] = {'auc': 0.0, 'para': algo_para, 'num_nonzeros': 0.0}
            auc_wt_bar[(task_id, fold_id)] = {'auc': 0.0, 'para': algo_para, 'num_nonzeros': 0.0}
        # cross validate based on tr_index
        list_auc_wt = np.zeros(k_fold)
        list_auc_wt_bar = np.zeros(k_fold)
        list_num_nonzeros_wt = np.zeros(k_fold)
        list_num_nonzeros_wt_bar = np.zeros(k_fold)
        kf = KFold(n_splits=k_fold, shuffle=False)
        for ind, (sub_tr_ind, sub_te_ind) in enumerate(
                kf.split(np.zeros(shape=(len(tr_index), 1)))):
            sub_x_tr = np.asarray(data['x_tr'][tr_index[sub_tr_ind]], dtype=float)
            sub_y_tr = np.asarray(data['y_tr'][tr_index[sub_tr_ind]], dtype=float)
            sub_x_te = data['x_tr'][tr_index[sub_te_ind]]
            sub_y_te = data['y_tr'][tr_index[sub_te_ind]]
            reg_opt, step_len, is_sparse, verbose, para_beta = 0, 10000, 0, 0, 0.0
            re = c_algo_spam(sub_x_tr, sub_y_tr, para_c, para_l1, para_beta, reg_opt, num_passes,
                             step_len, is_sparse, verbose)
            wt, wt_bar = np.asarray(re[0]), np.asarray(re[1])
            list_auc_wt[ind] = roc_auc_score(y_true=sub_y_te, y_score=np.dot(sub_x_te, wt))
            list_auc_wt_bar[ind] = roc_auc_score(y_true=sub_y_te, y_score=np.dot(sub_x_te, wt_bar))
            list_num_nonzeros_wt[ind] = np.count_nonzero(wt)
            list_num_nonzeros_wt_bar[ind] = np.count_nonzero(wt_bar)
        if auc_wt[(task_id, fold_id)]['auc'] < np.mean(list_auc_wt):
            auc_wt[(task_id, fold_id)]['auc'] = float(np.mean(list_auc_wt))
            auc_wt[(task_id, fold_id)]['para'] = algo_para
            auc_wt[(task_id, fold_id)]['num_nonzeros'] = float(np.mean(list_num_nonzeros_wt))
        if auc_wt_bar[(task_id, fold_id)]['auc'] < np.mean(list_auc_wt_bar):
            auc_wt_bar[(task_id, fold_id)]['auc'] = float(np.mean(list_auc_wt_bar))
            auc_wt_bar[(task_id, fold_id)]['para'] = algo_para
            auc_wt_bar[(task_id, fold_id)]['num_nonzeros'] = float(
                np.mean(list_num_nonzeros_wt_bar))
        # print(para_c, para_beta, para_l1, np.mean(list_auc_wt), np.mean(list_auc_wt_bar))
    run_time = time.time() - s_time
    print('-' * 40 + ' spam-l1l2 ' + '-' * 40)
    print('run_time: %.4f' % run_time)
    print('AUC-wt: ' + ' '.join(['%.4f' % auc_wt[_]['auc'] for _ in auc_wt]))
    print('AUC-wt-bar: ' + ' '.join(['%.4f' % auc_wt_bar[_]['auc'] for _ in auc_wt_bar]))
    print('nonzeros-wt: ' + ' '.join(['%.4f' % auc_wt[_]['num_nonzeros'] for _ in auc_wt]))
    print('nonzeros-wt-bar: ' + ' '.join(['%.4f' % auc_wt_bar[_]['num_nonzeros']
                                          for _ in auc_wt_bar]))
    return auc_wt, auc_wt_bar


def cv_spam_l2(task_id, k_fold, num_passes, data):
    """
    Model selection of SPAM-l2
    :param task_id:
    :param k_fold:
    :param num_passes:
    :param data:
    :return:
    """
    list_c = 10. ** np.arange(-5, 3, 1, dtype=float)
    list_beta = 10. ** np.arange(-5, 3, 1, dtype=float)
    auc_wt, auc_wt_bar = dict(), dict()
    s_time = time.time()
    for fold_id, para_c, para_beta in product(range(k_fold), list_c, list_beta):
        algo_para = (task_id, fold_id, num_passes, para_c, para_beta, k_fold)
        tr_index = data['task_%d_fold_%d' % (task_id, fold_id)]['tr_index']
        # cross validate based on tr_index
        if (task_id, fold_id) not in auc_wt:
            auc_wt[(task_id, fold_id)] = {'auc': 0.0, 'para': algo_para, 'num_nonzeros': 0.0}
            auc_wt_bar[(task_id, fold_id)] = {'auc': 0.0, 'para': algo_para, 'num_nonzeros': 0.0}
        list_auc_wt = np.zeros(k_fold)
        list_auc_wt_bar = np.zeros(k_fold)
        list_num_nonzeros_wt = np.zeros(k_fold)
        list_num_nonzeros_wt_bar = np.zeros(k_fold)
        kf = KFold(n_splits=k_fold, shuffle=False)  # Folding is fixed.
        for ind, (sub_tr_ind, sub_te_ind) in enumerate(
                kf.split(np.zeros(shape=(len(tr_index), 1)))):
            sub_x_tr = np.asarray(data['x_tr'][tr_index[sub_tr_ind]], dtype=float)
            sub_y_tr = np.asarray(data['y_tr'][tr_index[sub_tr_ind]], dtype=float)
            sub_x_te = data['x_tr'][tr_index[sub_te_ind]]
            sub_y_te = data['y_tr'][tr_index[sub_te_ind]]
            l1_reg, reg_opt, step_len, is_sparse, verbose = 0.0, 1, 10000, 0, 0
            re = c_algo_spam(sub_x_tr, sub_y_tr, para_c, l1_reg, para_beta, reg_opt, num_passes,
                             step_len, is_sparse, verbose)
            wt, wt_bar = np.asarray(re[0]), np.asarray(re[1])
            list_auc_wt[ind] = roc_auc_score(y_true=sub_y_te, y_score=np.dot(sub_x_te, wt))
            list_auc_wt_bar[ind] = roc_auc_score(y_true=sub_y_te, y_score=np.dot(sub_x_te, wt_bar))
            list_num_nonzeros_wt[ind] = np.count_nonzero(wt)
            list_num_nonzeros_wt_bar[ind] = np.count_nonzero(wt_bar)
        # print(para_c, para_beta, np.mean(list_auc_wt), np.mean(list_auc_wt_bar))
        if auc_wt[(task_id, fold_id)]['auc'] < np.mean(list_auc_wt):
            auc_wt[(task_id, fold_id)]['auc'] = float(np.mean(list_auc_wt))
            auc_wt[(task_id, fold_id)]['para'] = algo_para
            auc_wt[(task_id, fold_id)]['num_nonzeros'] = float(np.mean(list_num_nonzeros_wt))
        if auc_wt_bar[(task_id, fold_id)]['auc'] < np.mean(list_auc_wt_bar):
            auc_wt_bar[(task_id, fold_id)]['auc'] = float(np.mean(list_auc_wt_bar))
            auc_wt_bar[(task_id, fold_id)]['para'] = algo_para
            auc_wt_bar[(task_id, fold_id)]['num_nonzeros'] = float(
                np.mean(list_num_nonzeros_wt_bar))
    run_time = time.time() - s_time
    print('-' * 40 + ' spam-l2 ' + '-' * 40)
    print('run_time: %.4f' % run_time)
    print('AUC-wt: ' + ' '.join(['%.4f' % auc_wt[_]['auc'] for _ in auc_wt]))
    print('AUC-wt-bar: ' + ' '.join(['%.4f' % auc_wt_bar[_]['auc'] for _ in auc_wt_bar]))
    print('nonzeros-wt: ' + ' '.join(['%.4f' % auc_wt[_]['num_nonzeros'] for _ in auc_wt]))
    print('nonzeros-wt-bar: ' + ' '.join(['%.4f' % auc_wt_bar[_]['num_nonzeros']
                                          for _ in auc_wt_bar]))
    return auc_wt, auc_wt_bar


def cv_spam_l1l2(task_id, k_fold, num_passes, data):
    list_c = 10. ** np.arange(-5, 3, 1, dtype=float)
    list_beta = 10. ** np.arange(-5, 3, 1, dtype=float)
    list_l1 = 10. ** np.arange(-5, 3, 1, dtype=float)
    s_time = time.time()
    auc_wt, auc_wt_bar = dict(), dict()
    for fold_id, para_c, para_beta, para_l1 in product(range(k_fold), list_c, list_beta, list_l1):
        algo_para = (task_id, fold_id, num_passes, para_c, para_beta, para_l1, k_fold)
        tr_index = data['task_%d_fold_%d' % (task_id, fold_id)]['tr_index']
        # cross validate based on tr_index
        if (task_id, fold_id) not in auc_wt:
            auc_wt[(task_id, fold_id)] = {'auc': 0.0, 'para': algo_para, 'num_nonzeros': 0.0}
            auc_wt_bar[(task_id, fold_id)] = {'auc': 0.0, 'para': algo_para, 'num_nonzeros': 0.0}
        # cross validate based on tr_index
        list_auc_wt = np.zeros(k_fold)
        list_auc_wt_bar = np.zeros(k_fold)
        list_num_nonzeros_wt = np.zeros(k_fold)
        list_num_nonzeros_wt_bar = np.zeros(k_fold)
        kf = KFold(n_splits=k_fold, shuffle=False)
        for ind, (sub_tr_ind, sub_te_ind) in enumerate(
                kf.split(np.zeros(shape=(len(tr_index), 1)))):
            sub_x_tr = np.asarray(data['x_tr'][tr_index[sub_tr_ind]], dtype=float)
            sub_y_tr = np.asarray(data['y_tr'][tr_index[sub_tr_ind]], dtype=float)
            sub_x_te = data['x_tr'][tr_index[sub_te_ind]]
            sub_y_te = data['y_tr'][tr_index[sub_te_ind]]
            reg_opt, step_len, is_sparse, verbose = 0, 10000, 0, 0
            re = c_algo_spam(sub_x_tr, sub_y_tr, para_c, para_l1, para_beta, reg_opt, num_passes,
                             step_len, is_sparse, verbose)
            wt, wt_bar = np.asarray(re[0]), np.asarray(re[1])
            list_auc_wt[ind] = roc_auc_score(y_true=sub_y_te, y_score=np.dot(sub_x_te, wt))
            list_auc_wt_bar[ind] = roc_auc_score(y_true=sub_y_te, y_score=np.dot(sub_x_te, wt_bar))
            list_num_nonzeros_wt[ind] = np.count_nonzero(wt)
            list_num_nonzeros_wt_bar[ind] = np.count_nonzero(wt_bar)
        if auc_wt[(task_id, fold_id)]['auc'] < np.mean(list_auc_wt):
            auc_wt[(task_id, fold_id)]['auc'] = float(np.mean(list_auc_wt))
            auc_wt[(task_id, fold_id)]['para'] = algo_para
            auc_wt[(task_id, fold_id)]['num_nonzeros'] = float(np.mean(list_num_nonzeros_wt))
        if auc_wt_bar[(task_id, fold_id)]['auc'] < np.mean(list_auc_wt_bar):
            auc_wt_bar[(task_id, fold_id)]['auc'] = float(np.mean(list_auc_wt_bar))
            auc_wt_bar[(task_id, fold_id)]['para'] = algo_para
            auc_wt_bar[(task_id, fold_id)]['num_nonzeros'] = float(
                np.mean(list_num_nonzeros_wt_bar))
        # print(para_c, para_beta, para_l1, np.mean(list_auc_wt), np.mean(list_auc_wt_bar))
    run_time = time.time() - s_time
    print('-' * 40 + ' spam-l1l2 ' + '-' * 40)
    print('run_time: %.4f' % run_time)
    print('AUC-wt: ' + ' '.join(['%.4f' % auc_wt[_]['auc'] for _ in auc_wt]))
    print('AUC-wt-bar: ' + ' '.join(['%.4f' % auc_wt_bar[_]['auc'] for _ in auc_wt_bar]))
    print('nonzeros-wt: ' + ' '.join(['%.4f' % auc_wt[_]['num_nonzeros'] for _ in auc_wt]))
    print('nonzeros-wt-bar: ' + ' '.join(['%.4f' % auc_wt_bar[_]['num_nonzeros']
                                          for _ in auc_wt_bar]))
    return auc_wt, auc_wt_bar


def cv_solam(task_id, k_fold, num_passes, data):
    list_xi = np.arange(1, 101, 9, dtype=float)
    list_r = 10 ** np.arange(-1, 6, 1, dtype=float)
    s_time = time.time()
    auc_wt, auc_wt_bar = dict(), dict()
    for fold_id, para_xi, para_r in product(range(k_fold), list_xi, list_r):
        # only run sub-tasks for parallel
        algo_para = (task_id, fold_id, num_passes, para_xi, para_r, k_fold)
        tr_index = data['task_%d_fold_%d' % (task_id, fold_id)]['tr_index']
        # cross validate based on tr_index
        if (task_id, fold_id) not in auc_wt:
            auc_wt[(task_id, fold_id)] = {'auc': 0.0, 'para': algo_para, 'num_nonzeros': 0.0}
            auc_wt_bar[(task_id, fold_id)] = {'auc': 0.0, 'para': algo_para, 'num_nonzeros': 0.0}
        list_auc_wt = np.zeros(k_fold)
        list_auc_wt_bar = np.zeros(k_fold)
        list_num_nonzeros_wt = np.zeros(k_fold)
        list_num_nonzeros_wt_bar = np.zeros(k_fold)
        kf = KFold(n_splits=k_fold, shuffle=False)
        for ind, (sub_tr_ind, sub_te_ind) in enumerate(
                kf.split(np.zeros(shape=(len(tr_index), 1)))):
            re = c_algo_solam(np.asarray(data['x_tr'][tr_index[sub_tr_ind]], dtype=float),
                              np.asarray(data['y_tr'][tr_index[sub_tr_ind]], dtype=float),
                              para_xi, para_r, num_passes, 0)
            wt = np.asarray(re[0])
            wt_bar = np.asarray(re[1])
            sub_x_te = data['x_tr'][tr_index[sub_te_ind]]
            sub_y_te = data['y_tr'][tr_index[sub_te_ind]]
            list_auc_wt[ind] = roc_auc_score(y_true=sub_y_te, y_score=np.dot(sub_x_te, wt))
            list_auc_wt_bar[ind] = roc_auc_score(y_true=sub_y_te, y_score=np.dot(sub_x_te, wt_bar))
            list_num_nonzeros_wt[ind] = np.count_nonzero(wt)
            list_num_nonzeros_wt_bar[ind] = np.count_nonzero(wt_bar)
        print('para_xi: %.4f para_r: %.4f AUC-wt: %.4f AUC-wt-bar: %.4f run_time: %.2f' %
              (para_xi, para_r, float(np.mean(list_auc_wt)),
               float(np.mean(list_auc_wt_bar)), time.time() - s_time))
        if auc_wt[(task_id, fold_id)]['auc'] < np.mean(list_auc_wt):
            auc_wt[(task_id, fold_id)]['auc'] = float(np.mean(list_auc_wt))
            auc_wt[(task_id, fold_id)]['para'] = algo_para
            auc_wt[(task_id, fold_id)]['num_nonzeros'] = float(np.mean(list_num_nonzeros_wt))
        if auc_wt_bar[(task_id, fold_id)]['auc'] < np.mean(list_auc_wt_bar):
            auc_wt_bar[(task_id, fold_id)]['auc'] = float(np.mean(list_auc_wt_bar))
            auc_wt_bar[(task_id, fold_id)]['para'] = algo_para
            auc_wt_bar[(task_id, fold_id)]['num_nonzeros'] = float(
                np.mean(list_num_nonzeros_wt_bar))

    run_time = time.time() - s_time

    print('-' * 40 + ' solam ' + '-' * 40)
    print('run_time: %.4f' % run_time)
    print('AUC-wt: ' + ' '.join(['%.4f' % auc_wt[_]['auc'] for _ in auc_wt]))
    print('AUC-wt-bar: ' + ' '.join(['%.4f' % auc_wt_bar[_]['auc'] for _ in auc_wt_bar]))
    print('nonzeros-wt: ' + ' '.join(['%.4f' % auc_wt[_]['num_nonzeros'] for _ in auc_wt]))
    print('nonzeros-wt-bar: ' + ' '.join(['%.4f' % auc_wt_bar[_]['num_nonzeros']
                                          for _ in auc_wt_bar]))
    return auc_wt, auc_wt_bar


def cv_opauc(task_id, k_fold, num_passes, data):
    list_eta = 2. ** np.arange(-6, -4, 1, dtype=float)
    list_lambda = 2. ** np.arange(-2, 0, 1, dtype=float)
    auc_wt, auc_wt_bar = dict(), dict()
    s_time = time.time()
    for fold_id, para_eta, para_lambda in product(range(k_fold), list_eta, list_lambda):
        if fold_id == 1:
            break
        # only run sub-tasks for parallel
        algo_para = (task_id, fold_id, num_passes, para_eta, para_lambda, k_fold)
        tr_index = data['task_%d_fold_%d' % (task_id, fold_id)]['tr_index']
        # cross validate based on tr_index
        if (task_id, fold_id) not in auc_wt:
            auc_wt[(task_id, fold_id)] = {'auc': 0.0, 'para': algo_para, 'num_nonzeros': 0.0}
            auc_wt_bar[(task_id, fold_id)] = {'auc': 0.0, 'para': algo_para, 'num_nonzeros': 0.0}
        list_auc_wt = np.zeros(k_fold)
        list_auc_wt_bar = np.zeros(k_fold)
        list_num_nonzeros_wt = np.zeros(k_fold)
        list_num_nonzeros_wt_bar = np.zeros(k_fold)
        kf = KFold(n_splits=k_fold, shuffle=False)
        for ind, (sub_tr_ind, sub_te_ind) in enumerate(
                kf.split(np.zeros(shape=(len(tr_index), 1)))):
            sub_x_tr = np.asarray(data['x_tr'][tr_index[sub_tr_ind]], dtype=float)
            sub_y_tr = np.asarray(data['y_tr'][tr_index[sub_tr_ind]], dtype=float)
            re = c_algo_opauc(sub_x_tr, sub_y_tr, data['p'], len(sub_tr_ind),
                              para_eta, para_lambda)
            wt = np.asarray(re[0])
            wt_bar = np.asarray(re[1])
            sub_x_te = data['x_tr'][tr_index[sub_te_ind]]
            sub_y_te = data['y_tr'][tr_index[sub_te_ind]]
            list_auc_wt[ind] = roc_auc_score(y_true=sub_y_te, y_score=np.dot(sub_x_te, wt))
            list_auc_wt_bar[ind] = roc_auc_score(y_true=sub_y_te, y_score=np.dot(sub_x_te, wt_bar))
            list_num_nonzeros_wt[ind] = np.count_nonzero(wt)
            list_num_nonzeros_wt_bar[ind] = np.count_nonzero(wt_bar)
        print('fold-id:%d AUC-wt: %.4f AUC-wt-bar: %.4f run_time: %.4f' %
              (fold_id, float(np.mean(list_auc_wt)), float(np.mean(list_auc_wt_bar)),
               time.time() - s_time))
        if auc_wt[(task_id, fold_id)]['auc'] < np.mean(list_auc_wt):
            auc_wt[(task_id, fold_id)]['auc'] = float(np.mean(list_auc_wt))
            auc_wt[(task_id, fold_id)]['para'] = algo_para
            auc_wt[(task_id, fold_id)]['num_nonzeros'] = float(np.mean(list_num_nonzeros_wt))
        if auc_wt_bar[(task_id, fold_id)]['auc'] < np.mean(list_auc_wt_bar):
            auc_wt_bar[(task_id, fold_id)]['auc'] = float(np.mean(list_auc_wt_bar))
            auc_wt_bar[(task_id, fold_id)]['para'] = algo_para
            auc_wt_bar[(task_id, fold_id)]['num_nonzeros'] = float(
                np.mean(list_num_nonzeros_wt_bar))
    # to save some model selection time.
    for fold_id in range(k_fold):
        if (task_id, fold_id) not in auc_wt:
            auc_wt[(task_id, fold_id)] = {
                'auc': auc_wt[(task_id, 0)]['auc'],
                'para': auc_wt[(task_id, 0)]['para'],
                'num_nonzeros': auc_wt[(task_id, 0)]['num_nonzeros']}
            auc_wt_bar[(task_id, fold_id)] = {
                'auc': auc_wt_bar[(task_id, 0)]['auc'],
                'para': auc_wt_bar[(task_id, 0)]['para'],
                'num_nonzeros': auc_wt_bar[(task_id, 0)]['num_nonzeros']}
    run_time = time.time() - s_time
    print('-' * 40 + ' opauc ' + '-' * 40)
    print('run_time: %.4f' % run_time)
    print('AUC-wt: ' + ' '.join(['%.4f' % auc_wt[_]['auc'] for _ in auc_wt]))
    print('AUC-wt-bar: ' + ' '.join(['%.4f' % auc_wt_bar[_]['auc'] for _ in auc_wt_bar]))
    print('nonzeros-wt: ' + ' '.join(['%.4f' % auc_wt[_]['num_nonzeros'] for _ in auc_wt]))
    print('nonzeros-wt-bar: ' + ' '.join(['%.4f' % auc_wt_bar[_]['num_nonzeros']
                                          for _ in auc_wt_bar]))
    return auc_wt, auc_wt_bar


def cv_fsauc(task_id, k_fold, num_passes, data):
    list_r = 10. ** np.arange(-1, 6, 1, dtype=float)
    list_g = 2. ** np.arange(-10, -2, 1, dtype=float)
    auc_wt, auc_wt_bar = dict(), dict()
    s_time = time.time()
    for fold_id, para_r, para_g in product(range(k_fold), list_r, list_g):
        # only run sub-tasks for parallel
        algo_para = (task_id, fold_id, num_passes, para_r, para_g, k_fold)
        tr_index = data['task_%d_fold_%d' % (task_id, fold_id)]['tr_index']
        # cross validate based on tr_index
        if (task_id, fold_id) not in auc_wt:
            auc_wt[(task_id, fold_id)] = {'auc': 0.0, 'para': algo_para, 'num_nonzeros': 0.0}
            auc_wt_bar[(task_id, fold_id)] = {'auc': 0.0, 'para': algo_para, 'num_nonzeros': 0.0}
        list_auc_wt = np.zeros(k_fold)
        list_auc_wt_bar = np.zeros(k_fold)
        list_num_nonzeros_wt = np.zeros(k_fold)
        list_num_nonzeros_wt_bar = np.zeros(k_fold)
        kf = KFold(n_splits=k_fold, shuffle=False)
        for ind, (sub_tr_ind, sub_te_ind) in enumerate(
                kf.split(np.zeros(shape=(len(tr_index), 1)))):
            sub_x_tr = np.asarray(data['x_tr'][tr_index[sub_tr_ind]], dtype=float)
            sub_y_tr = np.asarray(data['y_tr'][tr_index[sub_tr_ind]], dtype=float)
            re = c_algo_fsauc(sub_x_tr, sub_y_tr, data['p'], len(sub_tr_ind),
                              num_passes, para_r, para_g)
            wt = np.asarray(re[0])
            wt_bar = np.asarray(re[1])
            sub_x_te = data['x_tr'][tr_index[sub_te_ind]]
            sub_y_te = data['y_tr'][tr_index[sub_te_ind]]
            list_auc_wt[ind] = roc_auc_score(y_true=sub_y_te, y_score=np.dot(sub_x_te, wt))
            list_auc_wt_bar[ind] = roc_auc_score(y_true=sub_y_te, y_score=np.dot(sub_x_te, wt_bar))
            list_num_nonzeros_wt[ind] = np.count_nonzero(wt)
            list_num_nonzeros_wt_bar[ind] = np.count_nonzero(wt_bar)
        if auc_wt[(task_id, fold_id)]['auc'] < np.mean(list_auc_wt):
            auc_wt[(task_id, fold_id)]['auc'] = float(np.mean(list_auc_wt))
            auc_wt[(task_id, fold_id)]['para'] = algo_para
            auc_wt[(task_id, fold_id)]['num_nonzeros'] = float(np.mean(list_num_nonzeros_wt))
        if auc_wt_bar[(task_id, fold_id)]['auc'] < np.mean(list_auc_wt_bar):
            auc_wt_bar[(task_id, fold_id)]['auc'] = float(np.mean(list_auc_wt_bar))
            auc_wt_bar[(task_id, fold_id)]['para'] = algo_para
            auc_wt_bar[(task_id, fold_id)]['num_nonzeros'] = float(
                np.mean(list_num_nonzeros_wt_bar))

    run_time = time.time() - s_time
    print('-' * 40 + ' opauc ' + '-' * 40)
    print('run_time: %.4f' % run_time)
    print('AUC-wt: ' + ' '.join(['%.4f' % auc_wt[_]['auc'] for _ in auc_wt]))
    print('AUC-wt-bar: ' + ' '.join(['%.4f' % auc_wt_bar[_]['auc'] for _ in auc_wt_bar]))
    print('nonzeros-wt: ' + ' '.join(['%.4f' % auc_wt[_]['num_nonzeros'] for _ in auc_wt]))
    print('nonzeros-wt-bar: ' + ' '.join(['%.4f' % auc_wt_bar[_]['num_nonzeros']
                                          for _ in auc_wt_bar]))
    return auc_wt, auc_wt_bar


def cv_sht_am(task_id, k_fold, num_passes, data):
    sparsity = 1 * len(data['subgraph'])
    list_c = 10. ** np.arange(-5, 3, 1, dtype=float)
    s_time = time.time()
    auc_wt, auc_wt_bar = dict(), dict()
    for fold_id, para_c in product(range(k_fold), list_c):
        # only run sub-tasks for parallel
        algo_para = (task_id, fold_id, num_passes, para_c, sparsity, k_fold)
        tr_index = data['task_%d_fold_%d' % (task_id, fold_id)]['tr_index']
        # cross validate based on tr_index
        if (task_id, fold_id) not in auc_wt:
            auc_wt[(task_id, fold_id)] = {'auc': 0.0, 'para': algo_para, 'num_nonzeros': 0.0}
            auc_wt_bar[(task_id, fold_id)] = {'auc': 0.0, 'para': algo_para, 'num_nonzeros': 0.0}
        step_len, is_sparse, verbose = 10000, 0, 0
        list_auc_wt = np.zeros(k_fold)
        list_auc_wt_bar = np.zeros(k_fold)
        list_num_nonzeros_wt = np.zeros(k_fold)
        list_num_nonzeros_wt_bar = np.zeros(k_fold)
        kf = KFold(n_splits=k_fold, shuffle=False)
        for ind, (sub_tr_ind, sub_te_ind) in enumerate(
                kf.split(np.zeros(shape=(len(tr_index), 1)))):
            b, para_beta = len(sub_tr_ind), 0.0
            re = c_algo_sht_am(np.asarray(data['x_tr'][tr_index[sub_tr_ind]], dtype=float),
                               np.asarray(data['y_tr'][tr_index[sub_tr_ind]], dtype=float),
                               sparsity, b, para_c, para_beta, num_passes,
                               step_len, is_sparse, verbose,
                               np.asarray(data['subgraph'], dtype=np.int32))
            wt = np.asarray(re[0])
            wt_bar = np.asarray(re[1])
            sub_x_te = data['x_tr'][tr_index[sub_te_ind]]
            sub_y_te = data['y_tr'][tr_index[sub_te_ind]]
            list_auc_wt[ind] = roc_auc_score(y_true=sub_y_te, y_score=np.dot(sub_x_te, wt))
            list_auc_wt_bar[ind] = roc_auc_score(y_true=sub_y_te, y_score=np.dot(sub_x_te, wt_bar))
            list_num_nonzeros_wt[ind] = np.count_nonzero(wt)
            list_num_nonzeros_wt_bar[ind] = np.count_nonzero(wt_bar)
        if auc_wt[(task_id, fold_id)]['auc'] < np.mean(list_auc_wt):
            auc_wt[(task_id, fold_id)]['auc'] = float(np.mean(list_auc_wt))
            auc_wt[(task_id, fold_id)]['para'] = algo_para
            auc_wt[(task_id, fold_id)]['num_nonzeros'] = float(np.mean(list_num_nonzeros_wt))
        if auc_wt_bar[(task_id, fold_id)]['auc'] < np.mean(list_auc_wt_bar):
            auc_wt_bar[(task_id, fold_id)]['auc'] = float(np.mean(list_auc_wt_bar))
            auc_wt_bar[(task_id, fold_id)]['para'] = algo_para
            auc_wt_bar[(task_id, fold_id)]['num_nonzeros'] = float(
                np.mean(list_num_nonzeros_wt_bar))
    run_time = time.time() - s_time
    print('-' * 40 + ' sht-am ' + '-' * 40)
    print('run_time: %.4f' % run_time)
    print('AUC-wt: ' + ' '.join(['%.4f' % auc_wt[_]['auc'] for _ in auc_wt]))
    print('AUC-wt-bar: ' + ' '.join(['%.4f' % auc_wt_bar[_]['auc'] for _ in auc_wt_bar]))
    print('nonzeros-wt: ' + ' '.join(['%.4f' % auc_wt[_]['num_nonzeros'] for _ in auc_wt]))
    print('nonzeros-wt-bar: ' + ' '.join(['%.4f' % auc_wt_bar[_]['num_nonzeros']
                                          for _ in auc_wt_bar]))
    return auc_wt, auc_wt_bar


def cv_graph_am(task_id, k_fold, num_passes, data):
    sparsity = 1 * len(data['subgraph'])
    list_c = 10. ** np.arange(-5, 3, 1, dtype=float)
    s_time = time.time()
    auc_wt, auc_wt_bar = dict(), dict()
    for fold_id, para_c in product(range(k_fold), list_c):
        # only run sub-tasks for parallel
        algo_para = (task_id, fold_id, num_passes, para_c, sparsity, k_fold)
        tr_index = data['task_%d_fold_%d' % (task_id, fold_id)]['tr_index']
        # cross validate based on tr_index
        if (task_id, fold_id) not in auc_wt:
            auc_wt[(task_id, fold_id)] = {'auc': 0.0, 'para': algo_para, 'num_nonzeros': 0.0}
            auc_wt_bar[(task_id, fold_id)] = {'auc': 0.0, 'para': algo_para, 'num_nonzeros': 0.0}
        step_len, is_sparse, verbose = 10000, 0, 0
        list_auc_wt = np.zeros(k_fold)
        list_auc_wt_bar = np.zeros(k_fold)
        list_num_nonzeros_wt = np.zeros(k_fold)
        list_num_nonzeros_wt_bar = np.zeros(k_fold)
        kf = KFold(n_splits=k_fold, shuffle=False)
        for ind, (sub_tr_ind, sub_te_ind) in enumerate(
                kf.split(np.zeros(shape=(len(tr_index), 1)))):
            sub_x_tr = np.asarray(data['x_tr'][tr_index[sub_tr_ind]], dtype=float)
            sub_y_tr = np.asarray(data['y_tr'][tr_index[sub_tr_ind]], dtype=float)
            b, para_beta = len(sub_x_tr), 0.0
            re = c_algo_graph_am(sub_x_tr, sub_y_tr, sparsity, b, para_c, para_beta, num_passes,
                                 step_len, is_sparse, verbose,
                                 np.asarray(data['edges'], dtype=np.int32),
                                 np.asarray(data['weights'], dtype=float),
                                 np.asarray(data['subgraph'], dtype=np.int32))
            wt = np.asarray(re[0])
            wt_bar = np.asarray(re[1])
            sub_x_te = data['x_tr'][tr_index[sub_te_ind]]
            sub_y_te = data['y_tr'][tr_index[sub_te_ind]]
            list_auc_wt[ind] = roc_auc_score(y_true=sub_y_te, y_score=np.dot(sub_x_te, wt))
            list_auc_wt_bar[ind] = roc_auc_score(y_true=sub_y_te, y_score=np.dot(sub_x_te, wt_bar))
            list_num_nonzeros_wt[ind] = np.count_nonzero(wt)
            list_num_nonzeros_wt_bar[ind] = np.count_nonzero(wt_bar)
            # print(np.mean(list_auc_wt), np.mean(list_auc_wt_bar))
        if auc_wt[(task_id, fold_id)]['auc'] < np.mean(list_auc_wt):
            auc_wt[(task_id, fold_id)]['auc'] = float(np.mean(list_auc_wt))
            auc_wt[(task_id, fold_id)]['para'] = algo_para
            auc_wt[(task_id, fold_id)]['num_nonzeros'] = float(np.mean(list_num_nonzeros_wt))
        if auc_wt_bar[(task_id, fold_id)]['auc'] < np.mean(list_auc_wt_bar):
            auc_wt_bar[(task_id, fold_id)]['auc'] = float(np.mean(list_auc_wt_bar))
            auc_wt_bar[(task_id, fold_id)]['para'] = algo_para
            auc_wt_bar[(task_id, fold_id)]['num_nonzeros'] = float(
                np.mean(list_num_nonzeros_wt_bar))
    run_time = time.time() - s_time

    print('-' * 40 + ' graph-am ' + '-' * 40)
    print('run_time: %.4f' % run_time)
    print('AUC-wt: ' + ' '.join(['%.4f' % auc_wt[_]['auc'] for _ in auc_wt]))
    print('AUC-wt-bar: ' + ' '.join(['%.4f' % auc_wt_bar[_]['auc'] for _ in auc_wt_bar]))
    print('nonzeros-wt: ' + ' '.join(['%.4f' % auc_wt[_]['num_nonzeros'] for _ in auc_wt]))
    print('nonzeros-wt-bar: ' + ' '.join(['%.4f' % auc_wt_bar[_]['num_nonzeros']
                                          for _ in auc_wt_bar]))
    return auc_wt, auc_wt_bar


def run_spam_l1(task_id, fold_id, para_c, para_l1, num_passes, data):
    tr_index = data['task_%d_fold_%d' % (task_id, fold_id)]['tr_index']
    te_index = data['task_%d_fold_%d' % (task_id, fold_id)]['te_index']
    reg_opt, step_len, verbose = 0, 1000000, 0
    re = c_algo_spam(np.asarray(data['x_tr'][tr_index], dtype=float),
                     np.asarray(data['y_tr'][tr_index], dtype=float),
                     para_c, para_l1, 0.0, reg_opt, num_passes, step_len, verbose)
    wt = np.asarray(re[0])
    wt_bar = np.asarray(re[1])
    t_auc = np.asarray(re[3])
    return {'algo_para': [task_id, fold_id, para_c, para_l1],
            'auc_wt': roc_auc_score(y_true=data['y_tr'][te_index],
                                    y_score=np.dot(data['x_tr'][te_index], wt)),
            'auc_wt_bar': roc_auc_score(y_true=data['y_tr'][te_index],
                                        y_score=np.dot(data['x_tr'][te_index], wt_bar)),
            't_auc': t_auc,
            'nonzero_wt': np.count_nonzero(wt),
            'nonzero_wt_bar': np.count_nonzero(wt_bar)}


def run_spam_l2(task_id, fold_id, para_c, para_beta, num_passes, data):
    tr_index = data['task_%d_fold_%d' % (task_id, fold_id)]['tr_index']
    te_index = data['task_%d_fold_%d' % (task_id, fold_id)]['te_index']
    l1_reg, reg_opt, step_len, verbose = 0.0, 1, len(tr_index), 0
    re = c_algo_spam(np.asarray(data['x_tr'][tr_index], dtype=float),
                     np.asarray(data['y_tr'][tr_index], dtype=float), para_c,
                     l1_reg, para_beta, reg_opt, num_passes, step_len, verbose)
    wt = np.asarray(re[0])
    wt_bar = np.asarray(re[1])
    t_auc = np.asarray(re[3])
    return {'algo_para': [task_id, fold_id, para_c, para_beta],
            'auc_wt': roc_auc_score(y_true=data['y_tr'][te_index],
                                    y_score=np.dot(data['x_tr'][te_index], wt)),
            'auc_wt_bar': roc_auc_score(y_true=data['y_tr'][te_index],
                                        y_score=np.dot(data['x_tr'][te_index], wt_bar)),
            't_auc': t_auc,
            'nonzero_wt': np.count_nonzero(wt),
            'nonzero_wt_bar': np.count_nonzero(wt_bar)}


def run_spam_l1l2(task_id, fold_id, para_c, para_beta, para_l1, num_passes, data):
    tr_index = data['task_%d_fold_%d' % (task_id, fold_id)]['tr_index']
    te_index = data['task_%d_fold_%d' % (task_id, fold_id)]['te_index']
    reg_opt, step_len, verbose = 0, len(tr_index), 0
    re = c_algo_spam(np.asarray(data['x_tr'][tr_index], dtype=float),
                     np.asarray(data['y_tr'][tr_index], dtype=float),
                     para_c, para_l1, para_beta, reg_opt, num_passes, step_len, verbose)
    wt = np.asarray(re[0])
    wt_bar = np.asarray(re[1])
    t_auc = np.asarray(re[3])
    return {'algo_para': [task_id, fold_id, para_c, para_beta],
            'auc_wt': roc_auc_score(y_true=data['y_tr'][te_index],
                                    y_score=np.dot(data['x_tr'][te_index], wt)),
            'auc_wt_bar': roc_auc_score(y_true=data['y_tr'][te_index],
                                        y_score=np.dot(data['x_tr'][te_index], wt_bar)),
            't_auc': t_auc,
            'nonzero_wt': np.count_nonzero(wt),
            'nonzero_wt_bar': np.count_nonzero(wt_bar)}


def run_sht_am(task_id, fold_id, para_c, sparsity, b, num_passes, data):
    tr_index = data['task_%d_fold_%d' % (task_id, fold_id)]['tr_index']
    te_index = data['task_%d_fold_%d' % (task_id, fold_id)]['te_index']
    step_len, verbose = 1000 * len(tr_index), 0
    re = c_algo_sht_am(np.asarray(data['x_tr'][tr_index], dtype=float),
                       np.asarray(data['y_tr'][tr_index], dtype=float),
                       sparsity, b, para_c, 0.0, num_passes, step_len, verbose)
    wt = np.asarray(re[0])
    wt_bar = np.asarray(re[1])
    t_auc = np.asarray(re[3])
    return {'algo_para': [task_id, fold_id, para_c],
            'auc_wt': roc_auc_score(y_true=data['y_tr'][te_index],
                                    y_score=np.dot(data['x_tr'][te_index], wt)),
            'auc_wt_bar': roc_auc_score(y_true=data['y_tr'][te_index],
                                        y_score=np.dot(data['x_tr'][te_index], wt_bar)),
            't_auc': t_auc,
            'nonzero_wt': np.count_nonzero(wt),
            'nonzero_wt_bar': np.count_nonzero(wt_bar)}


def run_graph_am(task_id, fold_id, para_c, sparsity, b, num_passes, data):
    tr_index = data['task_%d_fold_%d' % (task_id, fold_id)]['tr_index']
    te_index = data['task_%d_fold_%d' % (task_id, fold_id)]['te_index']
    step_len, verbose = len(tr_index), 0
    re = c_algo_graph_am(np.asarray(data['x_tr'][tr_index], dtype=float),
                         np.asarray(data['y_tr'][tr_index], dtype=float),
                         sparsity, b, para_c, 0.0, num_passes, step_len, verbose,
                         np.asarray(data['edges'], dtype=np.int32),
                         np.asarray(data['weights'], dtype=float))
    wt = np.asarray(re[0])
    wt_bar = np.asarray(re[1])
    t_auc = np.asarray(re[3])
    return {'algo_para': [task_id, fold_id, para_c, sparsity],
            'auc_wt': roc_auc_score(y_true=data['y_tr'][te_index],
                                    y_score=np.dot(data['x_tr'][te_index], wt)),
            'auc_wt_bar': roc_auc_score(y_true=data['y_tr'][te_index],
                                        y_score=np.dot(data['x_tr'][te_index], wt_bar)),
            't_auc': t_auc,
            'nonzero_wt': np.count_nonzero(wt),
            'nonzero_wt_bar': np.count_nonzero(wt_bar)}


def run_opauc(task_id, fold_id, para_eta, para_lambda, data):
    tr_index = data['task_%d_fold_%d' % (task_id, fold_id)]['tr_index']
    te_index = data['task_%d_fold_%d' % (task_id, fold_id)]['te_index']
    re = c_algo_opauc(np.asarray(data['x_tr'][tr_index], dtype=float),
                      np.asarray(data['y_tr'][tr_index], dtype=float),
                      data['p'], len(tr_index), para_eta, para_lambda)
    wt = np.asarray(re[0])
    wt_bar = np.asarray(re[1])
    return {'algo_para': [task_id, fold_id, para_eta, para_lambda],
            'auc_wt': roc_auc_score(y_true=data['y_tr'][te_index],
                                    y_score=np.dot(data['x_tr'][te_index], wt)),
            'auc_wt_bar': roc_auc_score(y_true=data['y_tr'][te_index],
                                        y_score=np.dot(data['x_tr'][te_index], wt_bar)),
            't_auc': 0.0,
            'nonzero_wt': np.count_nonzero(wt),
            'nonzero_wt_bar': np.count_nonzero(wt_bar)}


def run_fsauc(task_id, fold_id, num_passes, para_r, para_g, data):
    tr_index = data['task_%d_fold_%d' % (task_id, fold_id)]['tr_index']
    te_index = data['task_%d_fold_%d' % (task_id, fold_id)]['te_index']
    re = c_algo_fsauc(np.asarray(data['x_tr'][tr_index], dtype=float),
                      np.asarray(data['y_tr'][tr_index], dtype=float),
                      num_passes, para_r, para_g)
    wt = np.asarray(re[0])
    wt_bar = np.asarray(re[1])
    return {'algo_para': [task_id, fold_id, para_r, para_g],
            'auc_wt': roc_auc_score(y_true=data['y_tr'][te_index],
                                    y_score=np.dot(data['x_tr'][te_index], wt)),
            'auc_wt_bar': roc_auc_score(y_true=data['y_tr'][te_index],
                                        y_score=np.dot(data['x_tr'][te_index], wt_bar)),
            't_auc': 0.0,
            'nonzero_wt': np.count_nonzero(wt),
            'nonzero_wt_bar': np.count_nonzero(wt_bar)}


def run_solam(task_id, fold_id, para_xi, para_r, num_passes, data):
    tr_index = data['task_%d_fold_%d' % (task_id, fold_id)]['tr_index']
    te_index = data['task_%d_fold_%d' % (task_id, fold_id)]['te_index']
    re = c_algo_solam(np.asarray(data['x_tr'][tr_index], dtype=float),
                      np.asarray(data['y_tr'][tr_index], dtype=float),
                      para_xi, para_r, num_passes, 0)
    wt = np.asarray(re[0])
    wt_bar = np.asarray(re[1])
    return {'algo_para': [task_id, fold_id, para_xi, para_r],
            'auc_wt': roc_auc_score(y_true=data['y_tr'][te_index],
                                    y_score=np.dot(data['x_tr'][te_index], wt)),
            'auc_wt_bar': roc_auc_score(y_true=data['y_tr'][te_index],
                                        y_score=np.dot(data['x_tr'][te_index], wt_bar)),
            'nonzero_wt': np.count_nonzero(wt),
            'nonzero_wt_bar': np.count_nonzero(wt_bar)}


def run_ms(method_name):
    if 'SLURM_ARRAY_TASK_ID' in os.environ:
        task_id = int(os.environ['SLURM_ARRAY_TASK_ID'])
    else:
        task_id = 0
    k_fold, num_passes = 5, 10
    tr_list = [1000]
    mu_list = [0.3]
    posi_ratio_list = [0.1, 0.2, 0.3, 0.4, 0.5]
    fig_list = ['fig_1', 'fig_2', 'fig_3', 'fig_4']
    results = dict()
    if method_name == 'spam_l1':
        for num_tr, mu, posi_ratio, fig_i in product(tr_list, mu_list, posi_ratio_list, fig_list):
            f_name = data_path + 'data_task_%02d_tr_%03d_mu_%.1f_p-ratio_%.1f.pkl'
            data = pkl.load(open(f_name % (task_id, num_tr, mu, posi_ratio), 'rb'))
            item = (task_id, num_passes, num_tr, mu, posi_ratio, fig_i)
            results[item] = dict()
            results[item][method_name] = cv_spam_l1(task_id, k_fold, num_passes, data[fig_i])
    elif method_name == 'spam_l2':
        for num_tr, mu, posi_ratio, fig_i in product(tr_list, mu_list, posi_ratio_list, fig_list):
            f_name = data_path + 'data_task_%02d_tr_%03d_mu_%.1f_p-ratio_%.1f.pkl'
            data = pkl.load(open(f_name % (task_id, num_tr, mu, posi_ratio), 'rb'))
            item = (task_id, num_passes, num_tr, mu, posi_ratio, fig_i)
            results[item] = dict()
            results[item][method_name] = cv_spam_l2(task_id, k_fold, num_passes, data[fig_i])
    elif method_name == 'spam_l1l2':
        for num_tr, mu, posi_ratio, fig_i in product(tr_list, mu_list, posi_ratio_list, fig_list):
            f_name = data_path + 'data_task_%02d_tr_%03d_mu_%.1f_p-ratio_%.1f.pkl'
            data = pkl.load(open(f_name % (task_id, num_tr, mu, posi_ratio), 'rb'))
            item = (task_id, num_passes, num_tr, mu, posi_ratio, fig_i)
            results[item] = dict()
            results[item][method_name] = cv_spam_l1l2(task_id, k_fold, num_passes, data[fig_i])
    elif method_name == 'solam':
        for num_tr, mu, posi_ratio, fig_i in product(tr_list, mu_list, posi_ratio_list, fig_list):
            f_name = data_path + 'data_task_%02d_tr_%03d_mu_%.1f_p-ratio_%.1f.pkl'
            data = pkl.load(open(f_name % (task_id, num_tr, mu, posi_ratio), 'rb'))
            item = (task_id, num_passes, num_tr, mu, posi_ratio, fig_i)
            results[item] = dict()
            results[item][method_name] = cv_solam(task_id, k_fold, num_passes, data[fig_i])
    elif method_name == 'sht_am':
        for num_tr, mu, posi_ratio, fig_i in product(tr_list, mu_list, posi_ratio_list, fig_list):
            f_name = data_path + 'data_task_%02d_tr_%03d_mu_%.1f_p-ratio_%.1f.pkl'
            data = pkl.load(open(f_name % (task_id, num_tr, mu, posi_ratio), 'rb'))
            item = (task_id, num_passes, num_tr, mu, posi_ratio, fig_i)
            results[item] = dict()
            results[item][method_name] = cv_sht_am(task_id, k_fold, num_passes, data[fig_i])
    elif method_name == 'graph_am':
        for num_tr, mu, posi_ratio, fig_i in product(tr_list, mu_list, posi_ratio_list, fig_list):
            f_name = data_path + 'data_task_%02d_tr_%03d_mu_%.1f_p-ratio_%.1f.pkl'
            data = pkl.load(open(f_name % (task_id, num_tr, mu, posi_ratio), 'rb'))
            item = (task_id, num_passes, num_tr, mu, posi_ratio, fig_i)
            results[item] = dict()
            results[item][method_name] = cv_graph_am(task_id, k_fold, num_passes, data[fig_i])
    elif method_name == 'opauc':
        for num_tr, mu, posi_ratio, fig_i in product(tr_list, mu_list, posi_ratio_list, fig_list):
            f_name = data_path + 'data_task_%02d_tr_%03d_mu_%.1f_p-ratio_%.1f.pkl'
            data = pkl.load(open(f_name % (task_id, num_tr, mu, posi_ratio), 'rb'))
            item = (task_id, num_passes, num_tr, mu, posi_ratio, fig_i)
            results[item] = dict()
            results[item][method_name] = cv_opauc(task_id, k_fold, num_passes, data[fig_i])
    elif method_name == 'fsauc':
        for num_tr, mu, posi_ratio, fig_i in product(tr_list, mu_list, posi_ratio_list, fig_list):
            f_name = data_path + 'data_task_%02d_tr_%03d_mu_%.1f_p-ratio_%.1f.pkl'
            data = pkl.load(open(f_name % (task_id, num_tr, mu, posi_ratio), 'rb'))
            item = (task_id, num_passes, num_tr, mu, posi_ratio, fig_i)
            results[item] = dict()
            results[item][method_name] = cv_fsauc(task_id, k_fold, num_passes, data[fig_i])
    pkl.dump(results, open(data_path + 'ms_task_%02d_%s.pkl' % (task_id, method_name), 'wb'))


def run_testing():
    if 'SLURM_ARRAY_TASK_ID' in os.environ:
        task_id = int(os.environ['SLURM_ARRAY_TASK_ID'])
    else:
        task_id = 0
    k_fold, passes = 5, 10
    tr_list = [1000]
    mu_list = [0.3]
    posi_ratio_list = [0.1, 0.2, 0.3, 0.4, 0.5]
    fig_list = ['fig_1', 'fig_2', 'fig_3', 'fig_4']
    results = dict()
    for num_tr, mu, posi_ratio, fig_i in product(tr_list, mu_list, posi_ratio_list, fig_list):
        f_name = data_path + 'data_task_%02d_tr_%03d_mu_%.1f_p-ratio_%.1f.pkl'
        data = pkl.load(open(f_name % (task_id, num_tr, mu, posi_ratio), 'rb'))
        item = (task_id, passes, num_tr, mu, posi_ratio, fig_i)
        for fold_id in range(k_fold):
            key = (task_id, fold_id, passes, num_tr, mu, posi_ratio, fig_i)
            results[key] = dict()
            # -----------------------
            method = 'spam_l1'
            ms = pkl.load(open(data_path + 'ms_task_%02d_%s.pkl' % (task_id, method), 'rb'))
            _, _, _, para_c, para_l1, _ = ms[item][method][0][(task_id, fold_id)]['para']
            re = run_spam_l1(task_id, fold_id, para_c, para_l1, passes, data[fig_i])
            results[key][method] = re
            print(fold_id, method, re['auc_wt'], re['auc_wt_bar'])
            # -----------------------
            method = 'spam_l2'
            ms = pkl.load(open(data_path + 'ms_task_%02d_%s.pkl' % (task_id, method), 'rb'))
            _, _, _, para_c, para_beta, _ = ms[item][method][0][(task_id, fold_id)]['para']
            re = run_spam_l2(task_id, fold_id, para_c, para_beta, passes, data[fig_i])
            results[key][method] = re
            print(fold_id, method, re['auc_wt'], re['auc_wt_bar'])
            # -----------------------
            method = 'spam_l1l2'
            ms = pkl.load(open(data_path + 'ms_task_%02d_%s.pkl' % (task_id, method), 'rb'))
            temp = ms[item][method][0][(task_id, fold_id)]['para']
            _, _, _, para_c, para_beta, para_l1, _ = temp
            re = run_spam_l1l2(task_id, fold_id, para_c, para_beta, para_l1, passes, data[fig_i])
            results[key][method] = re
            print(fold_id, method, re['auc_wt'], re['auc_wt_bar'])
            # -----------------------
            method = 'solam'
            ms = pkl.load(open(data_path + 'ms_task_%02d_%s.pkl' % (task_id, method), 'rb'))
            _, _, _, para_xi, para_r, _ = ms[item][method][0][(task_id, fold_id)]['para']
            re = run_solam(task_id, fold_id, para_xi, para_r, passes, data[fig_i])
            results[key][method] = re
            print(fold_id, method, re['auc_wt'], re['auc_wt_bar'])
            # -----------------------
            method = 'sht_am'
            ms = pkl.load(open(data_path + 'ms_task_%02d_%s.pkl' % (task_id, method), 'rb'))
            _, _, _, para_c, sparsity, _ = ms[item][method][0][(task_id, fold_id)]['para']
            re = run_sht_am(task_id, fold_id, para_c, sparsity, passes, data[fig_i])
            results[key][method] = re
            print(fold_id, method, re['auc_wt'], re['auc_wt_bar'])
            # -----------------------
            method = 'graph_am'
            ms = pkl.load(open(data_path + 'ms_task_%02d_%s.pkl' % (task_id, method), 'rb'))
            _, _, _, para_c, sparsity, _ = ms[item][method][0][(task_id, fold_id)]['para']
            re = run_graph_am(task_id, fold_id, para_c, sparsity, passes, data[fig_i])
            results[key][method] = re
            print(fold_id, method, re['auc_wt'], re['auc_wt_bar'])
            # -----------------------
            method = 'opauc'
            ms = pkl.load(open(data_path + 'ms_task_%02d_%s.pkl' % (task_id, method), 'rb'))
            _, _, _, para_eta, para_lambda, _ = ms[item][method][0][(task_id, fold_id)]['para']
            re = run_opauc(task_id, fold_id, para_eta, para_lambda, data[fig_i])
            results[key][method] = re
            print(fold_id, method, re['auc_wt'], re['auc_wt_bar'])
            # -----------------------
            method = 'fsauc'
            ms = pkl.load(open(data_path + 'ms_task_%02d_%s.pkl' % (task_id, method), 'rb'))
            _, _, _, para_eta, para_lambda, _ = ms[item][method][0][(task_id, fold_id)]['para']
            re = run_fsauc(task_id, fold_id, passes, para_eta, para_lambda, data[fig_i])
            results[key][method] = re
            print(fold_id, method, re['auc_wt'], re['auc_wt_bar'])
    f_name = 'results_task_%02d.pkl'
    pkl.dump(results, open(os.path.join(data_path, f_name % task_id), 'wb'))


def run_para_sparsity():
    if 'SLURM_ARRAY_TASK_ID' in os.environ:
        task_id = int(os.environ['SLURM_ARRAY_TASK_ID'])
    else:
        task_id = 0
    k_fold, passes = 5, 10
    tr_list = [1000]
    mu_list = [0.3]
    posi_ratio_list = [0.1, 0.5]
    fig_list = ['fig_2']
    results = dict()
    for num_tr, mu, posi_ratio, fig_i in product(tr_list, mu_list, posi_ratio_list, fig_list):
        f_name = data_path + 'data_task_%02d_tr_%03d_mu_%.1f_p-ratio_%.1f.pkl'
        data = pkl.load(open(f_name % (task_id, num_tr, mu, posi_ratio), 'rb'))
        item = (task_id, passes, num_tr, mu, posi_ratio, fig_i)
        for fold_id in range(k_fold):
            key = (task_id, fold_id, passes, num_tr, mu, posi_ratio, fig_i)
            results[key] = dict()
            # -----------------------
            method = 'sht_am'
            ms = pkl.load(open(data_path + 'ms_task_%02d_%s.pkl' % (task_id, method), 'rb'))
            _, _, _, para_c, _, _ = ms[item][method][0][(task_id, fold_id)]['para']
            re = []
            for sparsity in [22, 28, 34, 40, 46, 52, 58, 66, 72]:
                _ = run_sht_am(task_id, fold_id, para_c, sparsity, 800, passes, data[fig_i])
                re.append(_['auc_wt'])
            results[key][method] = re
            print(fold_id, method, ' '.join('%.4f' % _ for _ in re))
            # -----------------------
            method = 'graph_am'
            ms = pkl.load(open(data_path + 'ms_task_%02d_%s.pkl' % (task_id, method), 'rb'))
            _, _, _, para_c, _, _ = ms[item][method][0][(task_id, fold_id)]['para']
            re = []
            for sparsity in [22, 28, 34, 40, 46, 52, 58, 66, 72]:
                _ = run_graph_am(task_id, fold_id, para_c, sparsity, 800, passes, data[fig_i])
                re.append(_['auc_wt'])
            results[key][method] = re
            print(fold_id, method, ' '.join('%.4f' % _ for _ in re))
    f_name = 'results_task_%02d_sparsity.pkl'
    pkl.dump(results, open(os.path.join(data_path, f_name % task_id), 'wb'))


def run_para_blocksize():
    if 'SLURM_ARRAY_TASK_ID' in os.environ:
        task_id = int(os.environ['SLURM_ARRAY_TASK_ID'])
    else:
        task_id = 0
    k_fold, passes = 5, 10
    tr_list = [1000]
    mu_list = [0.3]
    posi_ratio_list = [0.1, 0.5]
    fig_list = ['fig_2']
    results = dict()
    for num_tr, mu, posi_ratio, fig_i in product(tr_list, mu_list, posi_ratio_list, fig_list):
        f_name = data_path + 'data_task_%02d_tr_%03d_mu_%.1f_p-ratio_%.1f.pkl'
        data = pkl.load(open(f_name % (task_id, num_tr, mu, posi_ratio), 'rb'))
        item = (task_id, passes, num_tr, mu, posi_ratio, fig_i)
        for fold_id in range(k_fold):
            key = (task_id, fold_id, passes, num_tr, mu, posi_ratio, fig_i)
            results[key] = dict()
            # -----------------------
            method = 'sht_am'
            ms = pkl.load(open(data_path + 'ms_task_%02d_%s.pkl' % (task_id, method), 'rb'))
            _, _, _, para_c, sparsity, _ = ms[item][method][0][(task_id, fold_id)]['para']
            re = []
            for b in [16, 32, 40, 100, 200, 400, 800]:
                _ = run_sht_am(task_id, fold_id, para_c, sparsity, b, passes, data[fig_i])
                re.append(_['auc_wt'])
            results[key][method] = re
            print(fold_id, method, ' '.join('%.4f' % _ for _ in re))
            # -----------------------
            method = 'graph_am'
            ms = pkl.load(open(data_path + 'ms_task_%02d_%s.pkl' % (task_id, method), 'rb'))
            _, _, _, para_c, sparsity, _ = ms[item][method][0][(task_id, fold_id)]['para']
            re = []
            for b in [16, 32, 40, 100, 200, 400, 800]:
                _ = run_graph_am(task_id, fold_id, para_c, sparsity, b, passes, data[fig_i])
                re.append(_['auc_wt'])
            results[key][method] = re
            print(fold_id, method, ' '.join('%.4f' % _ for _ in re))
    f_name = 'results_task_%02d_blocksize.pkl'
    pkl.dump(results, open(os.path.join(data_path, f_name % task_id), 'wb'))


def test_solam_simu():
    if 'SLURM_ARRAY_TASK_ID' in os.environ:
        task_id = int(os.environ['SLURM_ARRAY_TASK_ID'])
    else:
        task_id = 0
    k_fold, passes = 5, 10
    tr_list = [1000]
    mu_list = [0.3]
    posi_ratio_list = [0.5]
    fig_list = ['fig_4']
    results = dict()
    for num_tr, mu, posi_ratio, fig_i in product(tr_list, mu_list, posi_ratio_list, fig_list):
        f_name = data_path + 'data_task_%02d_tr_%03d_mu_%.1f_p-ratio_%.1f.pkl'
        data = pkl.load(open(f_name % (task_id, num_tr, mu, posi_ratio), 'rb'))
        for fold_id in range(k_fold):
            key = (task_id, fold_id, passes, num_tr, mu, posi_ratio, fig_i)
            results[key] = dict()
            method = 'solam'
            list_xi = np.arange(1, 101, 9, dtype=float)
            list_r = 10 ** np.arange(-1, 6, 1, dtype=float)
            best_auc = None
            for para_xi, para_r in product(list_xi, list_r):
                re = run_solam(task_id, fold_id, para_xi, para_r, passes, data[fig_i])
                if best_auc is None or best_auc['auc_wt'] < re['auc_wt']:
                    best_auc = re
            results[key][method] = best_auc
            print(fold_id, method, best_auc['auc_wt'], best_auc['auc_wt_bar'])


def main():
    test_solam_simu()


if __name__ == '__main__':
    main()
