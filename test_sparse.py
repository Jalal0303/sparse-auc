# -*- coding: utf-8 -*-
import multiprocessing
import os
import pickle as pkl
import sys
import time
from itertools import product
import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import KFold

try:
    sys.path.append(os.getcwd())
    import sparse_module

    try:
        from sparse_module import c_algo_spam_sparse
        from sparse_module import c_algo_solam_sparse
        from sparse_module import c_algo_sht_am_sparse
        from sparse_module import c_algo_sht_am_sparse_2
        from sparse_module import c_algo_fsauc_sparse
        from sparse_module import c_algo_opauc_sparse
    except ImportError:
        print('cannot find some function(s) in sparse_module')
        exit(0)
except ImportError:
    print('cannot find the module: sparse_module')

data_path = '/network/rit/lab/ceashpc/bz383376/data/icml2020/'


def get_data_by_ind(data, tr_ind, sub_tr_ind):
    sub_x_vals, sub_x_inds, sub_x_posis, sub_x_lens = [], [], [], []
    prev_posi = 0
    for index in tr_ind[sub_tr_ind]:
        cur_len = data['x_tr_lens'][index]
        cur_posi = data['x_tr_poss'][index]
        sub_x_vals.extend(data['x_tr_vals'][cur_posi:cur_posi + cur_len])
        sub_x_inds.extend(data['x_tr_inds'][cur_posi:cur_posi + cur_len])
        sub_x_lens.append(cur_len)
        sub_x_posis.append(prev_posi)
        prev_posi += cur_len
    sub_x_vals = np.asarray(sub_x_vals, dtype=float)
    sub_x_inds = np.asarray(sub_x_inds, dtype=np.int32)
    sub_x_posis = np.asarray(sub_x_posis, dtype=np.int32)
    sub_x_lens = np.asarray(sub_x_lens, dtype=np.int32)
    sub_y_tr = np.asarray(data['y_tr'][tr_ind[sub_tr_ind]], dtype=float)
    return sub_x_vals, sub_x_inds, sub_x_posis, sub_x_lens, sub_y_tr


def pred_auc(data, tr_index, sub_te_ind, wt):
    if np.isnan(wt).any() or np.isinf(wt).any():  # not a valid score function.
        return 0.0
    _ = get_data_by_ind(data, tr_index, sub_te_ind)
    sub_x_vals, sub_x_inds, sub_x_posis, sub_x_lens, sub_y_te = _
    y_pred_wt = np.zeros_like(sub_te_ind, dtype=float)
    for i in range(len(sub_te_ind)):
        cur_posi = sub_x_posis[i]
        cur_len = sub_x_lens[i]
        cur_x = sub_x_vals[cur_posi:cur_posi + cur_len]
        cur_ind = sub_x_inds[cur_posi:cur_posi + cur_len]
        y_pred_wt[i] = np.sum([cur_x[_] * wt[cur_ind[_]] for _ in range(cur_len)])
    return roc_auc_score(y_true=sub_y_te, y_score=y_pred_wt)


def run_single_spam_l1(para):
    run_id, fold_id, k_fold, num_passes, step_len, para_c, para_l1, data_name = para
    results = {'auc_arr': np.zeros(k_fold, dtype=float),
               'run_time': np.zeros(k_fold, dtype=float),
               'para': para}
    f_name = os.path.join(data_path, '%s/data_run_%d.pkl' % (data_name, run_id))
    data = pkl.load(open(f_name, 'rb'))
    tr_index = data['fold_%d' % fold_id]['tr_index']
    fold = KFold(n_splits=k_fold, shuffle=False)
    for ind, (sub_tr_ind, sub_te_ind) in enumerate(fold.split(tr_index)):
        s_time = time.time()
        x_vals, x_inds, x_posis, x_lens, y_tr = get_data_by_ind(data, tr_index, sub_tr_ind)
        wt, wt_bar, auc, rts = c_algo_spam_sparse(
            x_vals, x_inds, x_posis, x_lens, y_tr,
            data['p'], para_c, para_l1, 0.0, 0, num_passes, step_len, 0)
        results['auc_arr'][ind] = pred_auc(data, tr_index, sub_te_ind, wt)
        results['run_time'][ind] = time.time() - s_time
        print(run_id, fold_id, para_c, para_l1, results['auc_arr'][ind], time.time() - s_time)
        sys.stdout.flush()
    return results


def run_single_spam_l2(para):
    run_id, fold_id, k_fold, num_passes, step_len, para_c, para_l2, data_name = para
    results = {'auc_arr': np.zeros(k_fold, dtype=float),
               'run_time': np.zeros(k_fold, dtype=float),
               'para': para}
    f_name = os.path.join(data_path, '%s/data_run_%d.pkl' % (data_name, run_id))
    data = pkl.load(open(f_name, 'rb'))
    tr_index = data['fold_%d' % fold_id]['tr_index']
    fold = KFold(n_splits=k_fold, shuffle=False)
    for ind, (sub_tr_ind, sub_te_ind) in enumerate(fold.split(tr_index)):
        s_time = time.time()
        x_vals, x_inds, x_posis, x_lens, y_tr = get_data_by_ind(data, tr_index, sub_tr_ind)
        wt, wt_bar, auc, rts = c_algo_spam_sparse(
            x_vals, x_inds, x_posis, x_lens, y_tr,
            data['p'], para_c, 0.0, para_l2, 1, num_passes, step_len, 0)
        results['auc_arr'][ind] = pred_auc(data, tr_index, sub_te_ind, wt)
        results['run_time'][ind] = time.time() - s_time
        print(run_id, fold_id, para_c, para_l2, results['auc_arr'][ind], time.time() - s_time)
        sys.stdout.flush()
    return results


def run_single_spam_l1l2(para):
    run_id, fold_id, k_fold, num_passes, step_len, para_c, para_l1, para_l2, data_name = para
    print(para_c, para_l1, para_l2, data_name)
    sys.stdout.flush()
    results = {'auc_arr': np.zeros(k_fold, dtype=float),
               'run_time': np.zeros(k_fold, dtype=float),
               'para': para}
    f_name = os.path.join(data_path, '%s/data_run_%d.pkl' % (data_name, run_id))
    data = pkl.load(open(f_name, 'rb'))
    tr_index = data['fold_%d' % fold_id]['tr_index']
    fold = KFold(n_splits=k_fold, shuffle=False)
    for ind, (sub_tr_ind, sub_te_ind) in enumerate(fold.split(tr_index)):
        s_time = time.time()
        x_vals, x_inds, x_posis, x_lens, y_tr = get_data_by_ind(data, tr_index, sub_tr_ind)
        wt, wt_bar, auc, rts = c_algo_spam_sparse(
            x_vals, x_inds, x_posis, x_lens, y_tr,
            data['p'], para_c, para_l1, para_l2, 0, num_passes, step_len, 0)
        results['auc_arr'][ind] = pred_auc(data, tr_index, sub_te_ind, wt)
        results['run_time'][ind] = time.time() - s_time
        print(run_id, fold_id, para_c, para_l2, results['auc_arr'][ind], time.time() - s_time)
        sys.stdout.flush()
    return results


def run_single_solam(para):
    run_id, fold_id, k_fold, num_passes, step_len, para_c, para_r, data_name = para
    print(para_c, para_r, data_name)
    sys.stdout.flush()
    results = {'auc_arr': np.zeros(k_fold, dtype=float),
               'run_time': np.zeros(k_fold, dtype=float),
               'para': para}
    f_name = os.path.join(data_path, '%s/data_run_%d.pkl' % (data_name, run_id))
    data = pkl.load(open(f_name, 'rb'))
    tr_index = data['fold_%d' % fold_id]['tr_index']
    fold = KFold(n_splits=k_fold, shuffle=False)
    for ind, (sub_tr_ind, sub_te_ind) in enumerate(fold.split(tr_index)):
        s_time = time.time()
        x_vals, x_inds, x_posis, x_lens, y_tr = get_data_by_ind(data, tr_index, sub_tr_ind)
        wt, wt_bar, auc, rts = c_algo_solam_sparse(
            x_vals, x_inds, x_posis, x_lens, y_tr,
            data['p'], para_c, para_r, num_passes, step_len, 0)
        results['auc_arr'][ind] = pred_auc(data, tr_index, sub_te_ind, wt)
        results['run_time'][ind] = time.time() - s_time
        print(run_id, fold_id, para_c, para_r, results['auc_arr'][ind], time.time() - s_time)
        sys.stdout.flush()
    return results


def run_single_fsauc(para):
    run_id, fold_id, k_fold, num_passes, step_len, para_r, para_g, data_name = para
    results = {'auc_arr': np.zeros(k_fold, dtype=float),
               'run_time': np.zeros(k_fold, dtype=float),
               'para': para}
    f_name = os.path.join(data_path, '%s/data_run_%d.pkl' % (data_name, run_id))
    data = pkl.load(open(f_name, 'rb'))
    tr_index = data['fold_%d' % fold_id]['tr_index']
    fold = KFold(n_splits=k_fold, shuffle=False)
    for ind, (sub_tr_ind, sub_te_ind) in enumerate(fold.split(tr_index)):
        s_time = time.time()
        x_vals, x_inds, x_posis, x_lens, y_tr = get_data_by_ind(data, tr_index, sub_tr_ind)
        wt, wt_bar, aucs, rts = c_algo_fsauc_sparse(
            x_vals, x_inds, x_posis, x_lens, y_tr,
            data['p'], para_r, para_g, num_passes, step_len, 0)
        results['auc_arr'][ind] = pred_auc(data, tr_index, sub_te_ind, wt)
        results['run_time'][ind] = time.time() - s_time
        print(run_id, fold_id, para_r, para_g, results['auc_arr'][ind], time.time() - s_time)
        sys.stdout.flush()
    return results


def run_single_opauc(para):
    run_id, fold_id, k_fold, num_passes, step_len, para_tau, para_eta, para_lam, data_name = para
    results = {'auc_arr': np.zeros(k_fold, dtype=float),
               'run_time': np.zeros(k_fold, dtype=float),
               'para': para}
    f_name = os.path.join(data_path, '%s/data_run_%d.pkl' % (data_name, run_id))
    data = pkl.load(open(f_name, 'rb'))
    tr_index = data['fold_%d' % fold_id]['tr_index']
    fold = KFold(n_splits=k_fold, shuffle=False)
    for ind, (sub_tr_ind, sub_te_ind) in enumerate(fold.split(tr_index)):
        s_time = time.time()
        x_vals, x_inds, x_posis, x_lens, y_tr = get_data_by_ind(data, tr_index, sub_tr_ind)
        wt, wt_bar, aucs, rts = c_algo_opauc_sparse(
            x_vals, x_inds, x_posis, x_lens, y_tr,
            data['p'], para_tau, para_eta, para_lam, num_passes, step_len, 0)
        results['auc_arr'][ind] = pred_auc(data, tr_index, sub_te_ind, wt)
        results['run_time'][ind] = time.time() - s_time
        print(run_id, fold_id, para_eta, para_lam, results['auc_arr'][ind], time.time() - s_time)
        sys.stdout.flush()
    return results


def run_single_sht_am(para):
    run_id, fold_id, k_fold, num_passes, step_len, para_s, para_b, para_c, data_name = para
    results = {'auc_arr': np.zeros(k_fold, dtype=float),
               'run_time': np.zeros(k_fold, dtype=float),
               'para': para}
    f_name = os.path.join(data_path, '%s/data_run_%d.pkl' % (data_name, run_id))
    data = pkl.load(open(f_name, 'rb'))
    tr_index = data['fold_%d' % fold_id]['tr_index']
    fold = KFold(n_splits=k_fold, shuffle=False)
    for ind, (sub_tr_ind, sub_te_ind) in enumerate(fold.split(tr_index)):
        s_time = time.time()
        x_vals, x_inds, x_posis, x_lens, y_tr = get_data_by_ind(data, tr_index, sub_tr_ind)
        wt, wt_bar, aucs, rts = c_algo_sht_am_sparse_2(
            x_vals, x_inds, x_posis, x_lens, y_tr,
            data['p'], para_s, para_b, para_c, 0.0, num_passes, step_len, 0)
        results['auc_arr'][ind] = pred_auc(data, tr_index, sub_te_ind, wt)
        results['run_time'][ind] = time.time() - s_time
        print(run_id, fold_id, para_s, para_b, para_c,
              results['auc_arr'][ind], time.time() - s_time)
        sys.stdout.flush()
    return results


def pred_results(wt, wt_bar, auc, rts, para_list, te_index, data):
    return {'auc_wt': pred_auc(data, te_index, range(len(te_index)), wt),
            'nonzero_wt': np.count_nonzero(wt),
            'algo_para': para_list,
            'auc': auc,
            'rts': rts,
            'nonzero_wt_bar': np.count_nonzero(wt_bar)}


def get_model(method, task_id, run_id, fold_id):
    ms = pkl.load(open(data_path + 'ms_task_%02d_%s.pkl' % (task_id, method), 'rb'))
    selected_model = {'aver_auc': 0.0}
    for index in ms[(run_id, fold_id)][method]:
        mean_auc = np.mean(ms[(run_id, fold_id)][method]['auc_arr'])
        if selected_model['aver_auc'] < mean_auc:
            selected_model['model'] = ms[(run_id, fold_id)][method][index]
            selected_model['aver_auc'] = mean_auc
    return selected_model


def reduce_para_space(data_name, run_id, fold_id):
    """ Reduce parameter space by using the model selection of spam_l1 and spam_l2. """
    sub_list_c, sub_list_l1, sub_list_l2 = set(), set(), set()
    re_spam_l1 = pkl.load(open(os.path.join(data_path, '%s/ms_run_%d_fold_%d_%s.pkl' %
                                            (data_name, run_id, fold_id, 'spam_l1')), 'rb'))
    re_spam_l2 = pkl.load(open(os.path.join(data_path, '%s/ms_run_%d_fold_%d_%s.pkl' %
                                            (data_name, run_id, fold_id, 'spam_l2')), 'rb'))
    for item in re_spam_l1:
        if np.mean(item['auc_arr']) >= 0.7:
            sub_list_c.add(item['para'][5])
            sub_list_l1.add(item['para'][6])
    for item in re_spam_l2:
        if np.mean(item['auc_arr']) >= 0.7:
            sub_list_c.add(item['para'][5])
            sub_list_l2.add(item['para'][6])
    return np.sort(list(sub_list_c)), np.sort(list(sub_list_l1)), np.sort(list(sub_list_l2))


def test_spam_l1():
    fold_id, k_fold, passes, step_len = 0, 5, 1, 1000000
    data_name, run_id = '14_news20b', 0
    f_name = os.path.join(data_path, '%s/data_run_%d.pkl' % (data_name, run_id))
    data = pkl.load(open(f_name, 'rb'))
    list_c = np.arange(1, 101, 9, dtype=float)
    list_l1 = 10. ** np.arange(-5, 6, 1, dtype=float)
    input_data_list = []
    for index, (para_c, para_l1) in enumerate(product(list_c, list_l1)):
        para = (run_id, fold_id, k_fold, passes, step_len, para_c, para_l1, data_name)
        input_data_list.append(para)
    pool = multiprocessing.Pool(processes=1)
    results = pool.map(run_single_spam_l1, input_data_list)
    pool.close()
    pool.join()


def test_sht_am():
    fold_id, k_fold, passes, step_len = 0, 5, 5, 1000000
    data_name, run_id = '13_realsim', 0
    f_name = os.path.join(data_path, '%s/data_run_%d.pkl' % (data_name, run_id))
    data = pkl.load(open(f_name, 'rb'))
    list_s = [int(_ * data['p']) for _ in np.arange(0.1, 1.01, 0.1)]
    list_b = [20, 50, 100]
    list_c = 2. ** np.arange(-10, 5, 2, dtype=float)
    input_data_list = []
    for index, (para_s, para_b, para_c) in enumerate(product(list_s, list_b, list_c)):
        para = (run_id, fold_id, k_fold, passes, step_len, para_s, para_b, para_c, data_name)
        input_data_list.append(para)
    pool = multiprocessing.Pool(processes=1)
    pool.map(run_single_sht_am, input_data_list)
    pool.close()
    pool.join()


def main():
    test_sht_am()


if __name__ == '__main__':
    main()