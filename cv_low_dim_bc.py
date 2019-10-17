# -*- coding: utf-8 -*-
import os
import csv
import sys
import numpy as np
import pickle as pkl
from sklearn.model_selection import KFold
from itertools import product
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


def get_related_genes():
    # [0] Wooster, Richard, Graham Bignell, Jonathan Lancaster, Sally Swift, Sheila Seal,
    # Jonathan Mangion, Nadine Collins et al. "Identification of the breast cancer
    # susceptibility gene BRCA2." Nature 378, no. 6559 (1995): 789.
    # [0] Miki, Yoshio, Jeff Swensen, Donna Shattuck-Eidens, P. Andrew Futreal, Keith
    # Harshman, Sean Tavtigian, Qingyun Liu et al. "A strong candidate for the breast and
    # ovarian cancer susceptibility gene BRCA1." Science (1994): 66-71.
    gen_list_dict_01 = {675: ['BRCA2'], 672: ['BRCA1']}
    # found in the following paper:
    # [1] Agius, Phaedra, Yiming Ying, and Colin Campbell. "Bayesian
    # unsupervised learning with multiple data types." Statistical
    # applications in genetics and molecular biology 8.1 (2009): 1-27.
    gen_list_dict_02 = {2568: ['GABRP'], 1824: ['DSC2'], 9: ['NAT1'], 834139: ['XPB1'],
                        10551: ['AGR2'], 771: ['CA12'], 7033: ['TFF3'], 3169: ['FOXA1'],
                        367: ['AR'], 2203: ['FBP1'], 1001: ['CDH3'], 2625: ['GATA3'],
                        2296: ['FOXC1'], 7494: ['XBP1']}
    # [2] Couch, Fergus J., et al. "Associations between
    # cancer predisposition testing panel genes and breast cancer."
    # JAMA oncology 3.9 (2017): 1190-1196.
    gen_list_dict_03 = {3169: ['FOXA1'], 472: ['ATM'], 580: ['BARD1'],
                        11200: ['CHEK2'], 79728: ['PALB2'], 5892: ['RAD51D']}
    # [3] Rheinbay, Esther, et al. "Recurrent and functional regulatory
    # mutations in breast cancer." Nature 547.7661 (2017): 55-60.
    gen_list_dict_04 = {3169: ['FOXA1'], 6023: ['RMRP', 'CHH', 'NME1', 'RRP2', 'RMRPR'],
                        283131: ['NEAT1']}
    # [4] Györffy, Balazs, et al. "An online survival analysis tool to rapidly
    #  assess the effect of 22,277 genes on breast cancer prognosis using
    # microarray data of 1,809 patients." Breast cancer research and
    # treatment 123.3 (2010): 725-731.
    gen_list_dict_05 = {7153: ['TOP2A'], 7155: ['TOP2B'], 4288: ['MKI67'], 894: ['CCND2'],
                        896: ['CCND3'], 1026: ['CDKN1A'], 7084: ['TK2']}
    all_related_genes = dict()
    for key in gen_list_dict_01:
        all_related_genes[key] = gen_list_dict_01[key]
    for key in gen_list_dict_02:
        all_related_genes[key] = gen_list_dict_02[key]
    for key in gen_list_dict_03:
        all_related_genes[key] = gen_list_dict_03[key]
    for key in gen_list_dict_04:
        all_related_genes[key] = gen_list_dict_04[key]
    for key in gen_list_dict_05:
        all_related_genes[key] = gen_list_dict_05[key]
    return all_related_genes


def raw_data_process(root_input):
    import scipy.io as sio
    import networkx as nx
    raw = sio.loadmat(os.path.join(root_input, 'raw_input/vant.mat'))
    data = {'x': np.asarray(raw['X'], dtype=float),
            'y': np.asarray([_[1] for _ in raw['Y']], dtype=float),
            'entrez': [_[0] for _ in np.asarray(raw['entrez'])]}
    for i, each_row in enumerate(data['x']):
        print(i, np.linalg.norm(each_row), np.mean(each_row), np.std(each_row))
    for i in range(len(data['x'][0])):
        if np.mean(data['x'][:, i]) == 0. and np.std(data['x'][:, i]) == 0.0:
            print('default values.')
    edges, costs, g = [], [], nx.Graph()
    with open(os.path.join(root_input, 'raw_input/edge.txt')) as csvfile:
        edge_reader = csv.reader(csvfile, delimiter='\t', quotechar='|')
        for row in edge_reader:
            g.add_edge(row[0], row[1])
            edges.append([int(row[0]) - 1, int(row[1]) - 1])
            costs.append(1.)
    pathways = dict()
    with open(os.path.join(root_input, 'raw_input/pathways.txt')) as csvfile:
        edge_reader = csv.reader(csvfile, delimiter='\t', quotechar='|')
        for row in edge_reader:
            if int(row[0]) not in pathways:
                pathways[int(row[0])] = []
            pathways[int(row[0])].append(int(row[1]))
    print(nx.number_connected_components(g))
    print(nx.number_of_edges(g))
    print(nx.number_of_nodes(g))
    nodes = [int(_) for _ in nx.nodes(g)]
    print(min(nodes), max(nodes), len(nodes))
    data['edges'] = np.asarray(edges, dtype=int)
    data['costs'] = np.asarray(costs, dtype=np.float64)
    data['pathways'] = pathways

    # ------------- get entrez gene maps.
    test_entrez_gene_names = dict()
    with open(root_input + 'raw_input/entrez_gene_map_from_match_miner.txt') as csvfile:
        line_reader = csv.reader(csvfile, delimiter='\t', quotechar='|')
        for row_ind, row in enumerate(line_reader):
            if row_ind >= 21:
                if int(row[2]) not in test_entrez_gene_names:
                    test_entrez_gene_names[int(row[2])] = []
                test_entrez_gene_names[int(row[2])].append(row[3])

    entrez_gene_names = dict()
    with open(root_input + 'raw_input/entrez_gene_map_from_uniprot.tab') as csvfile:
        line_reader = csv.reader(csvfile, delimiter='\t', quotechar='|')
        for row_ind, row in enumerate(line_reader):
            if row_ind >= 1:
                if str.find(row[-1], ',') != -1:
                    for entrez_id in str.split(row[-1], ','):
                        gene_names = str.split(row[-2], ' ')
                        gene_names = [_ for _ in gene_names if len(_) > 0]
                        if int(entrez_id) not in entrez_gene_names:
                            entrez_gene_names[int(entrez_id)] = []
                        entrez_gene_names[int(entrez_id)].extend(gene_names)
                else:
                    entrez_id = int(row[-1])
                    gene_names = str.split(row[-2], ' ')
                    gene_names = [_ for _ in gene_names if len(_) > 0]
                    if int(entrez_id) not in entrez_gene_names:
                        entrez_gene_names[int(entrez_id)] = []
                    entrez_gene_names[int(entrez_id)].extend(gene_names)

    all_entrez_gene_names = dict()
    for key in test_entrez_gene_names:
        all_entrez_gene_names[key] = test_entrez_gene_names[key]
    for key in entrez_gene_names:
        all_entrez_gene_names[key].extend(entrez_gene_names[key])
    data['entrez_gene_name_map'] = all_entrez_gene_names

    # ---------------- get genes names from van_t_veer_2002 nature paper
    f_name = os.path.join(root_input, 'raw_input/van_t_veer_2002/Table_NKI_295_1.txt')
    print('load data from: %s' % f_name)
    with open(f_name) as csvfile:
        edge_reader = csv.reader(csvfile, delimiter='\t', quotechar='|')
        all_lines = [row for row_ind, row in enumerate(edge_reader)]
        col_gene_name_list = \
            [row[1] for row_ind, row in enumerate(all_lines) if row_ind >= 2]
        data['van_t_veer_gene_name_list'] = col_gene_name_list

    # ----------------- get cancer related genes
    all_genes_from_database = dict()
    for entrez_id in data['entrez_gene_name_map']:
        for gene in data['entrez_gene_name_map'][entrez_id]:
            all_genes_from_database[gene] = entrez_id
    all_related_genes = get_related_genes()
    finalized_cancer_gene = dict()
    for entrez in all_related_genes:
        flag = False
        for gene in all_related_genes[entrez]:
            if entrez in data['entrez']:
                print('find: %s' % gene)
                finalized_cancer_gene[gene] = entrez
                flag = True
                break
        if not flag:
            print('cannot find: %s' % all_related_genes[entrez])
    print('all related genes: %d' % len(all_related_genes))
    print('all valid related genes: %d' % len(finalized_cancer_gene))
    data['cancer_related_genes'] = finalized_cancer_gene
    pkl.dump(data, open(root_input + 'raw_input/raw_input_bc.pkl', 'wb'))


def map_entrez_gene_name(root_input):
    test_entrez_gene_names = dict()
    with open(root_input + 'entrez_gene_map_from_match_miner.txt') as csvfile:
        line_reader = csv.reader(csvfile, delimiter='\t', quotechar='|')
        for row_ind, row in enumerate(line_reader):
            if row_ind >= 21:
                if int(row[2]) not in test_entrez_gene_names:
                    test_entrez_gene_names[int(row[2])] = []
                test_entrez_gene_names[int(row[2])].append(row[3])

    overlap_data = pkl.load(open(root_input + 'overlap_data.pkl'))
    original_data = pkl.load(open(root_input + 'original_data.pkl'))
    entrez_gene_names = dict()
    final_results = dict()
    with open(root_input + 'entrez_gene_map_from_uniprot.tab') as csvfile:
        line_reader = csv.reader(csvfile, delimiter='\t', quotechar='|')
        for row_ind, row in enumerate(line_reader):
            if row_ind >= 1:
                if str.find(row[-1], ',') != -1:
                    for entrez_id in str.split(row[-1], ','):
                        gene_names = str.split(row[-2], ' ')
                        gene_names = [_ for _ in gene_names if len(_) > 0]
                        if int(entrez_id) not in entrez_gene_names:
                            entrez_gene_names[int(entrez_id)] = []
                        entrez_gene_names[int(entrez_id)].extend(gene_names)
                else:
                    entrez_id = int(row[-1])
                    gene_names = str.split(row[-2], ' ')
                    gene_names = [_ for _ in gene_names if len(_) > 0]
                    if int(entrez_id) not in entrez_gene_names:
                        entrez_gene_names[int(entrez_id)] = []
                    entrez_gene_names[int(entrez_id)].extend(gene_names)

    all_entrez_gene_names = dict()
    for key in test_entrez_gene_names:
        all_entrez_gene_names[key] = test_entrez_gene_names[key]
    for key in entrez_gene_names:
        all_entrez_gene_names[key].extend(entrez_gene_names[key])

    index, num_gene_not_found, num_entrez_not_found = 0, 0, 0
    for item_ind, cur_entrez in enumerate(overlap_data['entrez']):
        if cur_entrez in all_entrez_gene_names:
            found_gene, ind = None, -1
            for each_gene in all_entrez_gene_names[cur_entrez]:
                if each_gene in original_data['col_gene_name_list']:
                    index += 1
                    re1 = overlap_data['x'][:, item_ind]
                    print('-' * 40)
                    print(len(np.where(re1 > 0.0)[0]),
                          len(np.where(re1 <= 0.0)[0]))
                    re2 = np.asarray(original_data['data_log_ratio'][item_ind])
                    print(len(np.where(re2 > 0.0)[0]),
                          len(np.where(re2 <= 0.0)[0]))
                    print('id: %d entrez: %d gene_name: %s' %
                          (index, cur_entrez, each_gene))
                    final_results[cur_entrez] = each_gene
                    found_gene = each_gene
                    break
            if found_gene is None:
                final_results[cur_entrez] = 'No_Gene_Found'
                num_gene_not_found += 1
        else:
            print(cur_entrez)
            num_entrez_not_found += 1
            final_results[cur_entrez] = 'No_Entrez_Found'
    print('number of genes not found: %d number of entrez not found: %d' %
          (num_gene_not_found, num_entrez_not_found))
    f_name = root_input + 'final_entrez_gene_map.pkl'
    pkl.dump(final_results, open(f_name, 'wb'))
    return final_results


def get_processed_data():
    root_input = '/network/rit/lab/ceashpc/bz383376/data/icml2020/16_bc/'
    import scipy.io as sio
    cancer_related_genes = {
        4288: 'MKI67', 1026: 'CDKN1A', 472: 'ATM', 7033: 'TFF3', 2203: 'FBP1',
        7494: 'XBP1', 1824: 'DSC2', 1001: 'CDH3', 11200: 'CHEK2',
        7153: 'TOP2A', 672: 'BRCA1', 675: 'BRCA2', 580: 'BARD1', 9: 'NAT1',
        771: 'CA12', 367: 'AR', 7084: 'TK2', 5892: 'RAD51D', 2625: 'GATA3',
        7155: 'TOP2B', 896: 'CCND3', 894: 'CCND2', 10551: 'AGR2',
        3169: 'FOXA1', 2296: 'FOXC1'}
    data = dict()
    re = sio.loadmat(root_input + 'raw_input/overlap_data_00.mat')['save_data'][0][0]
    data['data_X'] = np.asarray(re['data_X'], dtype=np.float64)
    data_y = [_[0] for _ in re['data_Y']]
    data['data_Y'] = np.asarray(data_y, dtype=np.float64)
    data_edges = [[_[0] - 1, _[1] - 1] for _ in re['data_edges']]
    data['data_edges'] = np.asarray(data_edges, dtype=int)
    data_pathways = [[_[0], _[1]] for _ in re['data_pathways']]
    data['data_pathways'] = np.asarray(data_pathways, dtype=int)
    data_entrez = [_[0] for _ in re['data_entrez']]
    data['data_entrez'] = np.asarray(data_entrez, dtype=int)
    import networkx as nx
    g = nx.Graph()
    ind_pathways = {_: i for i, _ in enumerate(data['data_entrez'])}
    re_path_entrez = [_[0] for _ in re['re_path_entrez']]
    data['re_path_entrez'] = np.asarray(re_path_entrez)
    all_nodes = {ind_pathways[_]: '' for _ in data['re_path_entrez']}
    maximum_nodes, maximum_list_edges = set(), []
    for edge in data['data_edges']:
        if edge[0] in all_nodes and edge[1] in all_nodes:
            g.add_edge(edge[0], edge[1])
    isolated_genes = set()
    maximum_genes = set()
    for cc in nx.connected_component_subgraphs(g):
        if len(cc) <= 5:
            for item in list(cc):
                isolated_genes.add(data['data_entrez'][item])
        else:
            for item in list(cc):
                maximum_nodes = set(list(cc))
                maximum_genes.add(data['data_entrez'][item])
    maximum_nodes = np.asarray(list(maximum_nodes))
    subgraph = nx.Graph()
    for edge in data['data_edges']:
        if edge[0] in maximum_nodes and edge[1] in maximum_nodes:
            if edge[0] != edge[1]:  # remove some self-loops
                maximum_list_edges.append(edge)
            subgraph.add_edge(edge[0], edge[1])
    print('number of connected components: %d' % nx.number_connected_components(subgraph))
    data['map_entrez'] = np.asarray([data['data_entrez'][_]
                                     for _ in maximum_nodes])
    data['edges'] = np.asarray(maximum_list_edges, dtype=int)
    data['costs'] = np.asarray([1.] * len(maximum_list_edges),
                               dtype=np.float64)
    data['x'] = data['data_X'][:, maximum_nodes]
    data['y'] = data['data_Y']
    data['nodes'] = np.asarray(range(len(maximum_nodes)), dtype=int)
    data['cancer_related_genes'] = cancer_related_genes
    for edge_ind, edge in enumerate(data['edges']):
        uu = list(maximum_nodes).index(edge[0])
        vv = list(maximum_nodes).index(edge[1])
        data['edges'][edge_ind][0] = uu
        data['edges'][edge_ind][1] = vv
    # data normalization
    x_mean = np.tile(np.mean(data['x'], axis=0), (len(data['x']), 1))
    x_std = np.tile(np.std(data['x'], axis=0), (len(data['x']), 1))
    data['x'] = np.nan_to_num(np.divide(data['x'] - x_mean, x_std))
    normalized_data = []
    for row in data['x']:
        normalized_data.append(row / np.linalg.norm(row))
    input_data = {'all_x_tr': np.asarray(data['data_X'], dtype=float),
                  'all_y_tr': np.asarray(data['data_Y'], dtype=float),
                  'all_edges': data['data_edges'], 'all_entrez': data['data_entrez'],
                  'cancer_related_genes': data['cancer_related_genes'],
                  'data_x_tr': np.asarray(normalized_data, dtype=float),
                  'data_y_tr': np.asarray(data['y'], dtype=float),
                  'data_weights': np.asarray(data['costs'], dtype=float),
                  'data_edges': data['edges'], 'data_nodes': data['nodes'],
                  'map_entrez': data['map_entrez'],
                  'n': 295,
                  'p': 3243,
                  'num_runs': 25,
                  'k_fold': 5,
                  'data_name': '16_bc'}
    for run_index in range(input_data['num_runs']):
        kf = KFold(n_splits=input_data['num_k_fold'], shuffle=False)
        # just need the number of training samples
        fake_x = np.zeros(shape=(input_data['n'], 1))
        for fold_index, (train_index, test_index) in enumerate(kf.split(fake_x)):
            # since original data is ordered, we need to shuffle it!
            rand_perm = np.random.permutation(input_data['n'])
            print(rand_perm[:10], len(rand_perm[train_index]), len(rand_perm[test_index]))
            input_data['run_%d_fold_%d' % (run_index, fold_index)] = {
                'tr_index': rand_perm[train_index], 'te_index': rand_perm[test_index]}
    pkl.dump(input_data, open(os.path.join(root_input, 'input_bc.pkl'), 'wb'))


def pred(wt, wt_bar, te_index, data):
    if (not np.isnan(wt).any()) and (not np.isinf(wt).any()):
        auc_wt = roc_auc_score(y_true=data['data_y_tr'][te_index],
                               y_score=np.dot(data['data_x_tr'][te_index], wt))
    else:
        auc_wt = 0.0
    if (not np.isnan(wt_bar).any()) and (not np.isinf(wt_bar).any()):
        auc_wt_bar = roc_auc_score(
            y_true=data['data_y_tr'][te_index],
            y_score=np.dot(data['data_x_tr'][te_index], wt_bar))
    else:
        auc_wt_bar = 0.0
    return auc_wt, auc_wt_bar


def cv_spam_l1(method_name, k_fold, task_id, num_passes, step_len, data):
    results = dict()
    list_c = 10. ** np.arange(-5, 6, 1, dtype=float)
    list_l1 = 10. ** np.arange(-5, 6, 1, dtype=float)
    for fold_id in range(k_fold):
        results[(task_id, fold_id)] = dict()
        tr_index = data['run_%d_fold_%d' % (task_id, fold_id)]['tr_index']
        te_index = data['run_%d_fold_%d' % (task_id, fold_id)]['te_index']
        best_auc = None
        for para_c, para_l1 in product(list_c, list_l1):
            wt, wt_bar, auc, rts = c_algo_spam(
                np.asarray(data['data_x_tr'][tr_index], dtype=float),
                np.asarray(data['data_y_tr'][tr_index], dtype=float),
                para_c, para_l1, 0.0, 0, num_passes, step_len, 0)
            auc_wt, auc_wt_bar = pred(wt, wt_bar, te_index, data)
            print(fold_id, para_c, para_l1, auc_wt, auc_wt_bar)
            if best_auc is None or best_auc['auc_wt'] < auc_wt:
                best_auc = {'auc_wt': auc_wt, 'auc_wt_bar': auc_wt_bar,
                            'auc': auc, 'rts': rts, 'para_c': para_c, 'para_l1': para_l1}
        results[(task_id, fold_id)][method_name] = best_auc
    return results


def cv_spam_l2(method_name, k_fold, task_id, num_passes, step_len, data):
    results = dict()
    list_c = 10. ** np.arange(-5, 6, 1, dtype=float)
    list_l2 = 10. ** np.arange(-5, 6, 1, dtype=float)
    for fold_id in range(k_fold):
        results[(task_id, fold_id)] = dict()
        tr_index = data['run_%d_fold_%d' % (task_id, fold_id)]['tr_index']
        te_index = data['run_%d_fold_%d' % (task_id, fold_id)]['te_index']
        best_auc = None
        for para_c, para_l2 in product(list_c, list_l2):
            wt, wt_bar, auc, rts = c_algo_spam(
                np.asarray(data['data_x_tr'][tr_index], dtype=float),
                np.asarray(data['data_y_tr'][tr_index], dtype=float),
                para_c, 0.0, para_l2, 1, num_passes, step_len, 0)
            auc_wt, auc_wt_bar = pred(wt, wt_bar, te_index, data)
            print(fold_id, para_c, para_l2, auc_wt, auc_wt_bar)
            if best_auc is None or best_auc['auc_wt'] < auc_wt:
                best_auc = {'auc_wt': auc_wt, 'auc_wt_bar': auc_wt_bar,
                            'auc': auc, 'rts': rts, 'para_c': para_c, 'para_l2': para_l2}
        results[(task_id, fold_id)][method_name] = best_auc
    return results


def cv_spam_l1l2(method_name, k_fold, task_id, num_passes, step_len, data):
    results = dict()
    list_c = 10. ** np.arange(-2, 3, 1, dtype=float)
    list_l1 = 10. ** np.arange(-5, 6, 1, dtype=float)
    list_l2 = 10. ** np.arange(-5, 6, 1, dtype=float)
    for fold_id in range(k_fold):
        results[(task_id, fold_id)] = dict()
        tr_index = data['run_%d_fold_%d' % (task_id, fold_id)]['tr_index']
        te_index = data['run_%d_fold_%d' % (task_id, fold_id)]['te_index']
        best_auc = None
        for para_c, para_l1, para_l2 in product(list_c, list_l1, list_l2):
            wt, wt_bar, auc, rts = c_algo_spam(
                np.asarray(data['data_x_tr'][tr_index], dtype=float),
                np.asarray(data['data_y_tr'][tr_index], dtype=float),
                para_c, para_l1, para_l2, 0, num_passes, step_len, 0)
            auc_wt, auc_wt_bar = pred(wt, wt_bar, te_index, data)
            print(fold_id, para_c, para_l2, auc_wt, auc_wt_bar)
            if best_auc is None or best_auc['auc_wt'] < auc_wt:
                best_auc = {'auc_wt': auc_wt, 'auc_wt_bar': auc_wt_bar,
                            'auc': auc, 'rts': rts, 'para_c': para_c, 'para_l2': para_l2}
        results[(task_id, fold_id)][method_name] = best_auc
    return results


def cv_sht_am(method_name, k_fold, task_id, num_passes, step_len, data):
    results = dict()
    list_b = [20]
    list_c = 10. ** np.arange(-5, 3, 1, dtype=float)
    list_sparsity = [50, 100, 150, 200, 250, 300, 350, 400]
    for fold_id in range(k_fold):
        results[(task_id, fold_id)] = dict()
        tr_index = data['run_%d_fold_%d' % (task_id, fold_id)]['tr_index']
        te_index = data['run_%d_fold_%d' % (task_id, fold_id)]['te_index']
        best_auc = None
        for para_b, para_c, sparsity in product(list_b, list_c, list_sparsity):
            wt, wt_bar, auc, rts = c_algo_sht_am(
                np.asarray(data['data_x_tr'][tr_index], dtype=float),
                np.asarray(data['data_y_tr'][tr_index], dtype=float),
                sparsity, para_b, para_c, 0.0, num_passes, step_len, 0)
            auc_wt, auc_wt_bar = pred(wt, wt_bar, te_index, data)
            print(fold_id, para_b, para_c, sparsity, auc_wt, auc_wt_bar)
            if best_auc is None or best_auc['auc_wt'] < auc_wt:
                best_auc = {'auc_wt': auc_wt, 'auc_wt_bar': auc_wt_bar,
                            'auc': auc, 'rts': rts, 'para_c': para_c, 'sparsity': sparsity}
        results[(task_id, fold_id)][method_name] = best_auc
    return results


def cv_graph_am(method_name, k_fold, task_id, num_passes, step_len, data):
    results = dict()
    list_b = [118]
    list_c = 10. ** np.arange(-5, 3, 1, dtype=float)
    list_sparsity = [100, 200, 300, 400, 500, 600, 700]
    for fold_id in range(k_fold):
        results[(task_id, fold_id)] = dict()
        tr_index = data['run_%d_fold_%d' % (task_id, fold_id)]['tr_index']
        te_index = data['run_%d_fold_%d' % (task_id, fold_id)]['te_index']
        best_auc = None
        for para_b, para_c, sparsity in product(list_b, list_c, list_sparsity):
            wt, wt_bar, auc, rts = c_algo_graph_am(
                np.asarray(data['data_x_tr'][tr_index], dtype=float),
                np.asarray(data['data_y_tr'][tr_index], dtype=float),
                np.asarray(data['data_edges'], dtype=np.int32),
                np.asarray(data['data_weights'], dtype=float),
                sparsity, para_b, para_c, 1e-3, num_passes, step_len, 0)
            auc_wt, auc_wt_bar = pred(wt, wt_bar, te_index, data)
            print(fold_id, para_b, para_c, sparsity, auc_wt, auc_wt_bar)
            if best_auc is None or best_auc['auc_wt'] < auc_wt:
                best_auc = {'auc_wt': auc_wt, 'auc_wt_bar': auc_wt_bar,
                            'auc': auc, 'rts': rts, 'para_c': para_c, 'sparsity': sparsity}
        results[(task_id, fold_id)][method_name] = best_auc
    return results


def cv_fsauc(method_name, k_fold, task_id, num_passes, step_len, data):
    results = dict()
    list_r = 10. ** np.arange(-1, 6, 1, dtype=float)
    list_g = 2. ** np.arange(-10, 1, 1, dtype=float)
    for fold_id in range(k_fold):
        results[(task_id, fold_id)] = dict()
        tr_index = data['run_%d_fold_%d' % (task_id, fold_id)]['tr_index']
        te_index = data['run_%d_fold_%d' % (task_id, fold_id)]['te_index']
        best_auc = None
        for para_r, para_g in product(list_r, list_g):
            wt, wt_bar, auc, rts = c_algo_fsauc(
                np.asarray(data['data_x_tr'][tr_index], dtype=float),
                np.asarray(data['data_y_tr'][tr_index], dtype=float),
                para_r, para_g, num_passes, step_len, 0)
            auc_wt, auc_wt_bar = pred(wt, wt_bar, te_index, data)
            print(fold_id, para_r, para_g, auc_wt, auc_wt_bar)
            if best_auc is None or best_auc['auc_wt'] < auc_wt:
                best_auc = {'auc_wt': auc_wt, 'auc_wt_bar': auc_wt_bar,
                            'auc': auc, 'rts': rts, 'para_r': para_r, 'para_g': para_g}
        results[(task_id, fold_id)][method_name] = best_auc
    return results


def cv_solam(method_name, k_fold, task_id, num_passes, step_len, data):
    results = dict()
    list_xi = np.arange(1, 101, 9, dtype=float)
    list_r = 10 ** np.arange(-1, 6, 1, dtype=float)
    for fold_id in range(k_fold):
        results[(task_id, fold_id)] = dict()
        tr_index = data['run_%d_fold_%d' % (task_id, fold_id)]['tr_index']
        te_index = data['run_%d_fold_%d' % (task_id, fold_id)]['te_index']
        best_auc = None
        for para_xi, para_r in product(list_xi, list_r):
            wt, wt_bar, auc, rts = c_algo_solam(
                np.asarray(data['data_x_tr'][tr_index], dtype=float),
                np.asarray(data['data_y_tr'][tr_index], dtype=float),
                para_xi, para_r, num_passes, step_len, 0)
            auc_wt, auc_wt_bar = pred(wt, wt_bar, te_index, data)
            print(fold_id, para_xi, para_r, auc_wt, auc_wt_bar)
            if best_auc is None or best_auc['auc_wt'] < auc_wt:
                best_auc = {'auc_wt': auc_wt, 'auc_wt_bar': auc_wt_bar,
                            'auc': auc, 'rts': rts, 'para_xi': para_xi, 'para_r': para_r}
        results[(task_id, fold_id)][method_name] = best_auc
    return results


def cv_opauc(method_name, k_fold, task_id, num_passes, step_len, data):
    results = dict()
    list_eta = 2. ** np.arange(-12, -3, 1, dtype=float)
    list_lambda = 2. ** np.arange(-10, 1, 1, dtype=float)
    for fold_id in range(k_fold):
        results[(task_id, fold_id)] = dict()
        tr_index = data['run_%d_fold_%d' % (task_id, fold_id)]['tr_index']
        te_index = data['run_%d_fold_%d' % (task_id, fold_id)]['te_index']
        best_auc = None
        for para_eta, para_lambda in product(list_eta, list_lambda):
            wt, wt_bar, auc, rts = c_algo_opauc(
                np.asarray(data['data_x_tr'][tr_index], dtype=float),
                np.asarray(data['data_y_tr'][tr_index], dtype=float),
                para_eta, para_lambda, num_passes, step_len, 0)
            auc_wt, auc_wt_bar = pred(wt, wt_bar, te_index, data)
            print(fold_id, para_eta, para_lambda, auc_wt, auc_wt_bar)
            if best_auc is None or best_auc['auc_wt'] < auc_wt:
                best_auc = {'auc_wt': auc_wt, 'auc_wt_bar': auc_wt_bar, 'auc': auc, 'rts': rts,
                            'para_eta': para_eta, 'para_lambda': para_lambda}
        print(best_auc['auc_wt'], best_auc['auc_wt_bar'])
        results[(task_id, fold_id)][method_name] = best_auc
    return results


def run_ms(method_name):
    if 'SLURM_ARRAY_TASK_ID' in os.environ:
        task_id = int(os.environ['SLURM_ARRAY_TASK_ID'])
    else:
        task_id = 0
    k_fold, num_passes, step_len = 5, 50, 20
    data_path = '/network/rit/lab/ceashpc/bz383376/data/icml2020/16_bc/'
    data = pkl.load(open(os.path.join(data_path, 'input_bc.pkl'), 'rb'))
    results = dict()
    if method_name == 'spam_l1':
        results = cv_spam_l1(method_name, k_fold, task_id, num_passes, step_len, data)
    elif method_name == 'spam_l2':
        results = cv_spam_l2(method_name, k_fold, task_id, num_passes, step_len, data)
    elif method_name == 'spam_l1l2':
        results = cv_spam_l1l2(method_name, k_fold, task_id, num_passes, step_len, data)
    elif method_name == 'sht_am':
        results = cv_sht_am(method_name, k_fold, task_id, num_passes, step_len, data)
    elif method_name == 'graph_am':
        results = cv_graph_am(method_name, k_fold, task_id, num_passes, step_len, data)
    elif method_name == 'fsauc':
        results = cv_fsauc(method_name, k_fold, task_id, num_passes, step_len, data)
    elif method_name == 'solam':
        results = cv_solam(method_name, k_fold, task_id, num_passes, step_len, data)
    elif method_name == 'opauc':
        results = cv_opauc(method_name, k_fold, task_id, num_passes, step_len, data)
    f_path = os.path.join(data_path, 'ms_task_%02d_%s.pkl' % (task_id, method_name))
    pkl.dump(results, open(f_path, 'wb'))


def main():
    run_ms(method_name=sys.argv[1])


if __name__ == '__main__':
    main()
