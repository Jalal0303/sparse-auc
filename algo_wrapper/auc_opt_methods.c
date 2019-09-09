//
// Created by baojian on 9/9/19.
//
#include "auc_opt_methods.h"


sparse_vector *_malloc_sparse_vector(double *x_vals, int *x_indices, int x_len) {
    sparse_vector *sv = malloc(sizeof(sparse_vector));
    sv->x_vals = x_vals;
    sv->x_indices = x_indices;
    sv->x_len = x_len;
    return sv;
}

void _free_sparse_vector(sparse_vector *sv) {
    free(sv);
}

double _sparse_dot(const int *x_indices, const double *x_values, int x_len, const double *y) {
    double result = 0.0;
    for (int i = 0; i < x_len; i++) {
        result += x_values[i] * y[x_indices[i]];
    }
    return result;
}


void _sparse_cblas_daxpy(const int *x_indices, const double *x_values, int x_len,
                         double alpha, double *y) {
    for (int i = 0; i < x_len; i++) {
        y[x_indices[i]] += alpha * x_values[i];
    }
}


void _floyd_rivest_select(double *array, int l, int r, int k) {
    register int n, i, j, s, sd, ll, rr;
    register double z, t;
    while (r > l) {
        if (r - l > 600) {
            /**
             * use select() recursively on a sample of size s to get an
             * estimate for the (k-l+1)-th smallest element into array[k],
             * biased slightly so that the (k-l+1)-th element is expected to
             * lie in the smaller set after partitioning.
             */
            n = r - l + 1;
            i = k - l + 1;
            z = log(n);
            s = (int) (0.5 * exp(2 * z / 3));
            sd = (int) (0.5 * sqrt(z * s * (n - s) / n) * sign(i - n / 2));
            ll = max(l, k - i * s / n + sd);
            rr = min(r, k + (n - i) * s / n + sd);
            _floyd_rivest_select(array, ll, rr, k);
        }
        t = array[k];
        /**
         * the following code partitions x[l:r] about t, it is similar to partition
         * but will run faster on most machines since subscript range checking on i
         * and j has been eliminated.
         */
        i = l;
        j = r;
        swap(array[l], array[k]);
        if (array[r] < t) {
            swap(array[r], array[l]);
        }
        while (i < j) {
            swap(array[i], array[j]);
            do i++; while (array[i] > t);
            do j--; while (array[j] < t);
        }
        if (array[l] == t) {
            swap(array[l], array[j]);
        } else {
            j++;
            swap(array[j], array[r]);
        }
        /**
         * New adjust l, r so they surround the subset containing the
         * (k-l+1)-th smallest element.
         */
        if (j <= k) {
            l = j + 1;
        }
        if (k <= j) {
            r = j - 1;
        }
    }
}

int _hard_thresholding(double *arr, int n, int k) {
    double *temp_arr = malloc(sizeof(double) * n), kth_largest;
    for (int i = 0; i < n; i++) {
        temp_arr[i] = fabs(arr[i]);
    }
    _floyd_rivest_select(temp_arr, 0, n - 1, k - 1);
    kth_largest = temp_arr[k - 1];
    bool flag = false;
    for (int i = 0; i < n; i++) {
        if (fabs(arr[i]) < kth_largest) {
            arr[i] = 0.0;
        } else if ((fabs(arr[i]) == kth_largest) && (flag == false)) {
            flag = true; // to handle the multiple cases.
        } else if ((fabs(arr[i]) == kth_largest) && (flag == true)) {
            arr[i] = 0.0;
        }
    }
    free(temp_arr);
    return 0;
}


bool algo_solam(solam_para *para, solam_results *results) {

    // make sure openblas uses only one cpu at a time.
    openblas_set_num_threads(1);
    int *rand_id = para->para_rand_ind;
    int num_tr = para->num_tr;
    double *zero_v = malloc(sizeof(double) * (para->p + 2));
    double *one_v = malloc(sizeof(double) * (para->p + 2));
    for (int i = 0; i < para->p + 2; i++) {
        zero_v[i] = 0.0;
        one_v[i] = 1.0;
    }
    double *x_train = para->x_tr;
    double *y_train = para->y_tr;

    // start of the algorithm
    double sr = para->para_r;
    double sc = para->para_xi;
    int n_pass = para->para_num_pass;
    int n_dim = para->p;
    double n_p0_ = 0.; // number of positive
    double *n_v0_ = malloc(sizeof(double) * (n_dim + 2));
    cblas_dcopy(n_dim + 2, zero_v, 1, n_v0_, 1);
    double n_a_p0_ = 0.;
    double n_g_a0_ = 0.;
    // initial vector
    double *n_v0 = malloc(sizeof(double) * (n_dim + 2));
    cblas_dcopy(n_dim, one_v, 1, n_v0, 1);
    cblas_dscal(n_dim, sqrt(sr * sr / (n_dim * 1.0)), n_v0, 1);
    n_v0[n_dim] = sr;
    n_v0[n_dim + 1] = sr;
    double n_a_p0 = 2. * sr;
    // iteration time.
    double n_t = 1.;
    int n_cnt = 1;
    double *v_wt = malloc(sizeof(double) * n_dim);
    double *v_p_dv = malloc(sizeof(double) * (n_dim + 2));
    double *n_v1 = malloc(sizeof(double) * (n_dim + 2));
    double *n_v1_ = malloc(sizeof(double) * (n_dim + 2));
    double v_p_da;
    double n_a_p1;
    double n_a_p1_;
    double n_p1_;
    while (true) {
        if (n_cnt > n_pass) {
            break;
        }
        for (int j = 0; j < num_tr; j++) {
            double *t_feat = x_train + rand_id[j] * n_dim;
            double *t_label = y_train + rand_id[j];
            double n_ga = sc / sqrt(n_t);
            if (*t_label > 0) { // if it is positive case
                n_p1_ = ((n_t - 1.) * n_p0_ + 1.) / n_t;
                cblas_dcopy(n_dim, n_v0, 1, v_wt, 1);
                double n_a = n_v0[n_dim];
                cblas_dcopy(n_dim + 2, zero_v, 1, v_p_dv, 1);
                double vt_dot = cblas_ddot(n_dim, v_wt, 1, t_feat, 1);
                double weight =
                        2. * (1. - n_p1_) * (vt_dot - n_a) - 2. * (1. + n_a_p0) * (1. - n_p1_);
                cblas_daxpy(n_dim, weight, t_feat, 1, v_p_dv, 1);
                v_p_dv[n_dim] = -2. * (1. - n_p1_) * (vt_dot - n_a);
                v_p_dv[n_dim + 1] = 0.;
                cblas_dscal(n_dim + 2, -n_ga, v_p_dv, 1);
                cblas_daxpy(n_dim + 2, 1.0, n_v0, 1, v_p_dv, 1);
                v_p_da = -2. * (1. - n_p1_) * vt_dot - 2. * n_p1_ * (1. - n_p1_) * n_a_p0;
                v_p_da = n_a_p0 + n_ga * v_p_da;
            } else {
                n_p1_ = ((n_t - 1.) * n_p0_) / n_t;
                cblas_dcopy(n_dim, n_v0, 1, v_wt, 1);
                double n_b = n_v0[n_dim + 1];
                cblas_dcopy(n_dim + 2, zero_v, 1, v_p_dv, 1);
                double vt_dot = cblas_ddot(n_dim, v_wt, 1, t_feat, 1);
                double weight = 2. * n_p1_ * (vt_dot - n_b) + 2. * (1. + n_a_p0) * n_p1_;
                cblas_daxpy(n_dim, weight, t_feat, 1, v_p_dv, 1);
                v_p_dv[n_dim] = 0.;
                v_p_dv[n_dim + 1] = -2. * n_p1_ * (vt_dot - n_b);
                cblas_dscal(n_dim + 2, -n_ga, v_p_dv, 1);
                cblas_daxpy(n_dim + 2, 1.0, n_v0, 1, v_p_dv, 1);
                v_p_da = 2. * n_p1_ * vt_dot - 2. * n_p1_ * (1. - n_p1_) * n_a_p0;
                v_p_da = n_a_p0 + n_ga * v_p_da;
            }
            // normalization -- the projection step.
            double n_rv = sqrt(cblas_ddot(n_dim, v_p_dv, 1, v_p_dv, 1));
            if (n_rv > sr) {
                cblas_dscal(n_dim, 1. / n_rv * sr, v_p_dv, 1);
            }
            if (v_p_dv[n_dim] > sr) {
                v_p_dv[n_dim] = sr;
            }
            if (v_p_dv[n_dim + 1] > sr) {
                v_p_dv[n_dim + 1] = sr;
            }
            cblas_dcopy(n_dim + 2, v_p_dv, 1, n_v1, 1); //n_v1 = v_p_dv
            double n_ra = fabs(v_p_da);
            if (n_ra > 2. * sr) {
                n_a_p1 = v_p_da / n_ra * (2. * sr);
            } else {
                n_a_p1 = v_p_da;
            }
            // update gamma_
            double n_g_a1_ = n_g_a0_ + n_ga;
            // update v_
            cblas_dcopy(n_dim + 2, n_v0, 1, n_v1_, 1);
            cblas_dscal(n_dim + 2, n_ga / n_g_a1_, n_v1_, 1);
            cblas_daxpy(n_dim + 2, n_g_a0_ / n_g_a1_, n_v0_, 1, n_v1_, 1);
            // update alpha_
            n_a_p1_ = (n_g_a0_ * n_a_p0_ + n_ga * n_a_p0) / n_g_a1_;
            // update the information
            n_p0_ = n_p1_;
            cblas_dcopy(n_dim + 2, n_v1_, 1, n_v0_, 1); // n_v0_ = n_v1_;
            n_a_p0_ = n_a_p1_;
            n_g_a0_ = n_g_a1_;
            cblas_dcopy(n_dim + 2, n_v1, 1, n_v0, 1); // n_v0 = n_v1;
            n_a_p0 = n_a_p1;
            // update the counts
            n_t = n_t + 1.;
        }
        n_cnt += 1;
    }
    cblas_dcopy(n_dim, n_v1_, 1, results->wt, 1);
    results->a = n_v1_[n_dim];
    results->b = n_v1_[n_dim + 1];
    free(n_v1_);
    free(n_v1);
    free(n_v0);
    free(n_v0_);
    free(v_p_dv);
    free(v_wt);
    free(one_v);
    free(zero_v);
    return true;
}

bool algo_solam_sparse(solam_para_sparse *para, solam_results *results) {

    // make sure openblas uses only one cpu at a time.
    openblas_set_num_threads(1);
    int *rand_id = para->para_rand_ind;
    int num_tr = para->num_tr;
    double *zero_v = malloc(sizeof(double) * (para->p + 2));
    double *one_v = malloc(sizeof(double) * (para->p + 2));
    for (int i = 0; i < para->p + 2; i++) {
        zero_v[i] = 0.0;
        one_v[i] = 1.0;
    }
    int *x_train_indices = para->x_tr_indices;
    double *x_train_values = para->x_tr_values;
    double *y_train = para->y_tr;

    // start of the algorithm
    double sr = para->para_r;
    double sc = para->para_xi;
    int n_pass = para->para_num_pass;
    int n_dim = para->p;
    double n_p0_ = 0.; // number of positive
    double *n_v0_ = malloc(sizeof(double) * (n_dim + 2));
    cblas_dcopy(n_dim + 2, zero_v, 1, n_v0_, 1);
    double n_a_p0_ = 0.;
    double n_g_a0_ = 0.;
    // initial vector
    double *n_v0 = malloc(sizeof(double) * (n_dim + 2));
    cblas_dcopy(n_dim, one_v, 1, n_v0, 1);
    cblas_dscal(n_dim, sqrt(sr * sr / (n_dim * 1.0)), n_v0, 1);
    n_v0[n_dim] = sr;
    n_v0[n_dim + 1] = sr;
    // printf("n_v0: %.4f\n", sqrt(cblas_ddot(n_dim + 2, n_v0, 1, n_v0, 1)));
    double n_a_p0 = 2. * sr;
    // iteration time.
    double n_t = 1.;
    int n_cnt = 1;
    double *v_wt = malloc(sizeof(double) * n_dim);
    double *v_p_dv = malloc(sizeof(double) * (n_dim + 2));
    double *n_v1 = malloc(sizeof(double) * (n_dim + 2));
    double *n_v1_ = malloc(sizeof(double) * (n_dim + 2));
    double v_p_da;
    double n_a_p1;
    double n_a_p1_;
    double n_p1_;
    //printf("n_dim: %d\n", n_dim);
    while (true) {
        if (n_cnt > n_pass) {
            break;
        }
        for (int j = 0; j < num_tr; j++) {
            int *t_feat_indices = x_train_indices + j * para->max_nonzero;
            double *t_feat_values = x_train_values + j * para->max_nonzero;
            int s_len = t_feat_indices[0];
            double *t_label = y_train + j;
            double n_ga = sc / sqrt(n_t);
            //printf("j: %d s_len: %d\n", j, s_len);
            if (*t_label > 0) { // if it is positive case
                n_p1_ = ((n_t - 1.) * n_p0_ + 1.) / n_t;
                cblas_dcopy(n_dim, n_v0, 1, v_wt, 1);
                double n_a = n_v0[n_dim];
                cblas_dcopy(n_dim + 2, zero_v, 1, v_p_dv, 1);
                double vt_dot = _sparse_dot(t_feat_indices + 1, t_feat_values + 1, s_len, v_wt);
                double weight = 2. * (1. - n_p1_) * (vt_dot - n_a);
                weight -= 2. * (1. + n_a_p0) * (1. - n_p1_);
                _sparse_cblas_daxpy(t_feat_indices + 1, t_feat_values + 1, s_len, weight, v_p_dv);
                v_p_dv[n_dim] = -2. * (1. - n_p1_) * (vt_dot - n_a);
                v_p_dv[n_dim + 1] = 0.;
                cblas_dscal(n_dim + 2, -n_ga, v_p_dv, 1);
                cblas_daxpy(n_dim + 2, 1.0, n_v0, 1, v_p_dv, 1);
                v_p_da = -2. * (1. - n_p1_) * vt_dot - 2. * n_p1_ * (1. - n_p1_) * n_a_p0;
                if (false) {
                    printf("posi v_p_da: %.4f vt_dot: %.4f n_p1_:%.4f n_a_p0: %.4f n_t: %.4f,"
                           "weight: %.4f ||v||: %.4f na: %.4f\n",
                           v_p_da, vt_dot, n_p1_, n_a_p0, n_t, weight,
                           sqrt(cblas_ddot(n_dim + 2, v_p_dv, 1, v_p_dv, 1)), n_a);
                }
                v_p_da = n_a_p0 + n_ga * v_p_da;
            } else {
                n_p1_ = ((n_t - 1.) * n_p0_) / n_t;
                cblas_dcopy(n_dim, n_v0, 1, v_wt, 1);
                double n_b = n_v0[n_dim + 1];
                cblas_dcopy(n_dim + 2, zero_v, 1, v_p_dv, 1);
                double vt_dot = _sparse_dot(t_feat_indices + 1, t_feat_values + 1, s_len, v_wt);
                double weight = 2. * n_p1_ * (vt_dot - n_b) + 2. * (1. + n_a_p0) * n_p1_;
                if (false) {
                    printf("s_len: %d, cur_indices: %d cur_values: %.4f, ||v||: %.4f \n",
                           s_len, *(t_feat_indices + 1), *(t_feat_values + 1),
                           sqrt(cblas_ddot(n_dim + 2, v_p_dv, 1, v_p_dv, 1)));
                }
                _sparse_cblas_daxpy(t_feat_indices + 1, t_feat_values + 1, s_len, weight, v_p_dv);
                if (false) {
                    printf("s_len: %d, cur_indices: %d cur_values: %.4f, ||v||: %.4f \n",
                           s_len, *(t_feat_indices + 1), *(t_feat_values + 1),
                           sqrt(cblas_ddot(n_dim + 2, v_p_dv, 1, v_p_dv, 1)));
                }
                v_p_dv[n_dim] = 0.;
                v_p_dv[n_dim + 1] = -2. * n_p1_ * (vt_dot - n_b);
                cblas_dscal(n_dim + 2, -n_ga, v_p_dv, 1);
                cblas_daxpy(n_dim + 2, 1.0, n_v0, 1, v_p_dv, 1);
                v_p_da = 2. * n_p1_ * vt_dot - 2. * n_p1_ * (1. - n_p1_) * n_a_p0;
                if (false) {
                    printf("nega v_p_da: %.4f vt_dot: %.4f n_p1_:%.4f n_a_p0: %.4f n_t: %.4f,"
                           "weight: %.4f ||v||: %.4f nb: %.4f\n",
                           v_p_da, vt_dot, n_p1_, n_a_p0, n_t, weight,
                           sqrt(cblas_ddot(n_dim + 2, v_p_dv, 1, v_p_dv, 1)), n_b);
                }
                v_p_da = n_a_p0 + n_ga * v_p_da;
            }

            if (false) {
                printf("lr: %.4f alpha: %.4f sr: %.4f sc:%.4f n_p1: %.4f label: %.1f\n",
                       n_ga, v_p_da, sr, sc, n_p1_, *t_label);
                if (j == 10) {
                    return false;
                }
            }

            // normalization -- the projection step.
            double n_rv = sqrt(cblas_ddot(n_dim, v_p_dv, 1, v_p_dv, 1));
            if (n_rv > sr) {
                cblas_dscal(n_dim, 1. / n_rv * sr, v_p_dv, 1);
            }
            if (v_p_dv[n_dim] > sr) {
                v_p_dv[n_dim] = sr;
            }
            if (v_p_dv[n_dim + 1] > sr) {
                v_p_dv[n_dim + 1] = sr;
            }
            cblas_dcopy(n_dim + 2, v_p_dv, 1, n_v1, 1); //n_v1 = v_p_dv


            double n_ra = fabs(v_p_da);
            if (n_ra > 2. * sr) {
                n_a_p1 = v_p_da / n_ra * (2. * sr);
            } else {
                n_a_p1 = v_p_da;
            }

            // update gamma_
            double n_g_a1_ = n_g_a0_ + n_ga;

            // update v_
            cblas_dcopy(n_dim + 2, n_v0, 1, n_v1_, 1);
            cblas_dscal(n_dim + 2, n_ga / n_g_a1_, n_v1_, 1);
            cblas_daxpy(n_dim + 2, n_g_a0_ / n_g_a1_, n_v0_, 1, n_v1_, 1);

            // update alpha_
            n_a_p1_ = (n_g_a0_ * n_a_p0_ + n_ga * n_a_p0) / n_g_a1_;

            // update the information
            n_p0_ = n_p1_;
            cblas_dcopy(n_dim + 2, n_v1_, 1, n_v0_, 1); // n_v0_ = n_v1_;
            n_a_p0_ = n_a_p1_;
            n_g_a0_ = n_g_a1_;
            cblas_dcopy(n_dim + 2, n_v1, 1, n_v0, 1); // n_v0 = n_v1;
            n_a_p0 = n_a_p1;

            // update the counts
            n_t = n_t + 1.;
        }
        n_cnt += 1;
    }
    cblas_dcopy(n_dim, n_v1_, 1, results->wt, 1);
    results->a = n_v1_[n_dim];
    results->b = n_v1_[n_dim + 1];
    free(n_v1_);
    free(n_v1);
    free(n_v0);
    free(n_v0_);
    free(v_p_dv);
    free(v_wt);
    free(one_v);
    free(zero_v);
    return true;
}


bool algo_stoht_am(stoht_am_para *para, stoht_am_results *results) {

    // make sure openblas uses only one cpu at a time.
    openblas_set_num_threads(1);
    int *rand_id = para->para_rand_ind;
    int num_tr = para->num_tr;
    double *zero_v = malloc(sizeof(double) * (para->p + 2));
    double *one_v = malloc(sizeof(double) * (para->p + 2));
    for (int i = 0; i < para->p + 2; i++) {
        zero_v[i] = 0.0;
        one_v[i] = 1.0;
    }
    double *x_train = para->x_tr;
    double *y_train = para->y_tr;

    // start of the algorithm
    double sr = para->para_r;
    double sc = para->para_xi;
    int n_pass = para->para_num_pass;
    int n_dim = para->p;
    double n_p0_ = 0.; // number of positive
    double *n_v0_ = malloc(sizeof(double) * (n_dim + 2));
    cblas_dcopy(n_dim + 2, zero_v, 1, n_v0_, 1);
    double n_a_p0_ = 0.;
    double n_g_a0_ = 0.;
    // initial vector
    double *n_v0 = malloc(sizeof(double) * (n_dim + 2));
    cblas_dcopy(n_dim, one_v, 1, n_v0, 1);
    cblas_dscal(n_dim, sqrt(sr * sr / (n_dim * 1.0)), n_v0, 1);
    n_v0[n_dim] = sr;
    n_v0[n_dim + 1] = sr;
    double n_a_p0 = 2. * sr;
    // iteration time.
    double n_t = 1.;
    int n_cnt = 1;
    double *v_wt = malloc(sizeof(double) * n_dim);
    double *v_p_dv = malloc(sizeof(double) * (n_dim + 2));
    double *n_v1 = malloc(sizeof(double) * (n_dim + 2));
    double *n_v1_ = malloc(sizeof(double) * (n_dim + 2));
    double v_p_da;
    double n_a_p1;
    double n_a_p1_;
    double n_p1_;
    while (true) {
        if (n_cnt > n_pass) {
            break;
        }
        for (int j = 0; j < num_tr; j++) {
            double *t_feat = x_train + rand_id[j] * n_dim;
            double *t_label = y_train + rand_id[j];
            double n_ga = sc / sqrt(n_t);
            if (*t_label > 0) { // if it is positive case
                n_p1_ = ((n_t - 1.) * n_p0_ + 1.) / n_t;
                cblas_dcopy(n_dim, n_v0, 1, v_wt, 1);
                double n_a = n_v0[n_dim];
                cblas_dcopy(n_dim + 2, zero_v, 1, v_p_dv, 1);
                double vt_dot = cblas_ddot(n_dim, v_wt, 1, t_feat, 1);
                double weight =
                        2. * (1. - n_p1_) * (vt_dot - n_a) - 2. * (1. + n_a_p0) * (1. - n_p1_);
                cblas_daxpy(n_dim, weight, t_feat, 1, v_p_dv, 1);
                v_p_dv[n_dim] = -2. * (1. - n_p1_) * (vt_dot - n_a);
                v_p_dv[n_dim + 1] = 0.;
                cblas_dscal(n_dim + 2, -n_ga, v_p_dv, 1);
                cblas_daxpy(n_dim + 2, 1.0, n_v0, 1, v_p_dv, 1);
                v_p_da = -2. * (1. - n_p1_) * vt_dot - 2. * n_p1_ * (1. - n_p1_) * n_a_p0;
                v_p_da = n_a_p0 + n_ga * v_p_da;
            } else {
                n_p1_ = ((n_t - 1.) * n_p0_) / n_t;
                cblas_dcopy(n_dim, n_v0, 1, v_wt, 1);
                double n_b = n_v0[n_dim + 1];
                cblas_dcopy(n_dim + 2, zero_v, 1, v_p_dv, 1);
                double vt_dot = cblas_ddot(n_dim, v_wt, 1, t_feat, 1);
                double weight = 2. * n_p1_ * (vt_dot - n_b) + 2. * (1. + n_a_p0) * n_p1_;
                cblas_daxpy(n_dim, weight, t_feat, 1, v_p_dv, 1);
                v_p_dv[n_dim] = 0.;
                v_p_dv[n_dim + 1] = -2. * n_p1_ * (vt_dot - n_b);
                cblas_dscal(n_dim + 2, -n_ga, v_p_dv, 1);
                cblas_daxpy(n_dim + 2, 1.0, n_v0, 1, v_p_dv, 1);
                v_p_da = 2. * n_p1_ * vt_dot - 2. * n_p1_ * (1. - n_p1_) * n_a_p0;
                v_p_da = n_a_p0 + n_ga * v_p_da;
            }
            // normalization -- the projection step.
            double n_rv = sqrt(cblas_ddot(n_dim, v_p_dv, 1, v_p_dv, 1));
            if (n_rv > sr) {
                cblas_dscal(n_dim, 1. / n_rv * sr, v_p_dv, 1);
            }
            if (v_p_dv[n_dim] > sr) {
                v_p_dv[n_dim] = sr;
            }
            if (v_p_dv[n_dim + 1] > sr) {
                v_p_dv[n_dim + 1] = sr;
            }
            //----- sparse projection step
            _hard_thresholding(v_p_dv, n_dim, para->para_s);
            //----- sparse projection step
            cblas_dcopy(n_dim + 2, v_p_dv, 1, n_v1, 1); //n_v1 = v_p_dv
            double n_ra = fabs(v_p_da);
            if (n_ra > 2. * sr) {
                n_a_p1 = v_p_da / n_ra * (2. * sr);
            } else {
                n_a_p1 = v_p_da;
            }
            // update gamma_
            double n_g_a1_ = n_g_a0_ + n_ga;
            // update v_
            cblas_dcopy(n_dim + 2, n_v0, 1, n_v1_, 1);
            cblas_dscal(n_dim + 2, n_ga / n_g_a1_, n_v1_, 1);
            cblas_daxpy(n_dim + 2, n_g_a0_ / n_g_a1_, n_v0_, 1, n_v1_, 1);
            // update alpha_
            n_a_p1_ = (n_g_a0_ * n_a_p0_ + n_ga * n_a_p0) / n_g_a1_;
            // update the information
            n_p0_ = n_p1_;
            cblas_dcopy(n_dim + 2, n_v1_, 1, n_v0_, 1); // n_v0_ = n_v1_;
            n_a_p0_ = n_a_p1_;
            n_g_a0_ = n_g_a1_;
            cblas_dcopy(n_dim + 2, n_v1, 1, n_v0, 1); // n_v0 = n_v1;
            n_a_p0 = n_a_p1;
            // update the counts
            n_t = n_t + 1.;
        }
        n_cnt += 1;
    }
    cblas_dcopy(n_dim, n_v1_, 1, results->wt, 1);
    results->a = n_v1_[n_dim];
    results->b = n_v1_[n_dim + 1];
    free(n_v1_);
    free(n_v1);
    free(n_v0);
    free(n_v0_);
    free(v_p_dv);
    free(v_wt);
    free(one_v);
    free(zero_v);
    return true;
}

bool algo_stoht_am_sparse(stoht_am_sparse_para *para, stoht_am_results *results) {

    // make sure openblas uses only one cpu at a time.
    openblas_set_num_threads(1);
    int *rand_id = para->para_rand_ind;
    int num_tr = para->num_tr;
    double *zero_v = malloc(sizeof(double) * (para->p + 2));
    double *one_v = malloc(sizeof(double) * (para->p + 2));
    for (int i = 0; i < para->p + 2; i++) {
        zero_v[i] = 0.0;
        one_v[i] = 1.0;
    }
    int *x_train_indices = para->x_tr_indices;
    double *x_train_values = para->x_tr_values;
    double *y_train = para->y_tr;

    // start of the algorithm
    double sr = para->para_r;
    double sc = para->para_xi;
    int n_pass = para->para_num_pass;
    int n_dim = para->p;
    double n_p0_ = 0.; // number of positive
    double *n_v0_ = malloc(sizeof(double) * (n_dim + 2));
    cblas_dcopy(n_dim + 2, zero_v, 1, n_v0_, 1);
    double n_a_p0_ = 0.;
    double n_g_a0_ = 0.;
    // initial vector
    double *n_v0 = malloc(sizeof(double) * (n_dim + 2));
    cblas_dcopy(n_dim, one_v, 1, n_v0, 1);
    cblas_dscal(n_dim, sqrt(sr * sr / (n_dim * 1.0)), n_v0, 1);
    n_v0[n_dim] = sr;
    n_v0[n_dim + 1] = sr;
    // printf("n_v0: %.4f\n", sqrt(cblas_ddot(n_dim + 2, n_v0, 1, n_v0, 1)));
    double n_a_p0 = 2. * sr;
    // iteration time.
    double n_t = 1.;
    int n_cnt = 1;
    double *v_wt = malloc(sizeof(double) * n_dim);
    double *v_p_dv = malloc(sizeof(double) * (n_dim + 2));
    double *n_v1 = malloc(sizeof(double) * (n_dim + 2));
    double *n_v1_ = malloc(sizeof(double) * (n_dim + 2));
    double *block_grad_v = malloc(sizeof(double) * (n_dim + 2));
    double v_p_da;
    double n_a_p1;
    double n_a_p1_;
    double n_p1_ = n_p0_;
    int block_size = 1;
    while (true) {
        if (n_cnt > n_pass) {
            break;
        }
        for (int j = 0; j < num_tr / block_size; j++) {
            int *t_feat_indices = x_train_indices + j * para->max_nonzero * block_size;
            double *t_feat_values = x_train_values + j * para->max_nonzero * block_size;
            double n_ga = sc / sqrt(n_t);

            cblas_dcopy(n_dim, n_v0, 1, v_wt, 1);

            // update gradient
            cblas_dcopy(n_dim + 2, zero_v, 1, block_grad_v, 1);
            double block_grad_alpha = 0.0;
            for (int jj = 0; jj < block_size; jj++) {
                double *cur_label = y_train + j * block_size + jj;
                int *cur_indices = t_feat_indices + para->max_nonzero * jj;
                double *cur_values = t_feat_values + para->max_nonzero * jj;
                int s_len = cur_indices[0];
                double vt_dot = _sparse_dot(cur_indices + 1, cur_values + 1, s_len, v_wt);
                double weight;
                if (*cur_label > 0) {
                    cblas_dcopy(n_dim + 2, zero_v, 1, v_p_dv, 1);
                    n_p1_ = ((n_t - 1.) * n_p0_ + 1.) / n_t;
                    double n_a = n_v0[n_dim];
                    weight = 2. * (1. - n_p1_) * (vt_dot - n_a);
                    weight -= 2. * (1. + n_a_p0) * (1. - n_p1_);
                    // gradient of w
                    _sparse_cblas_daxpy(cur_indices + 1, cur_values + 1, s_len, weight, v_p_dv);
                    // gradient of a
                    v_p_dv[n_dim] = -2. * (1. - n_p1_) * (vt_dot - n_a);
                    // gradient of b
                    v_p_dv[n_dim + 1] = 0.;
                    // gradient of alpha
                    v_p_da = -2. * (1. - n_p1_) * vt_dot - 2. * n_p1_ * (1. - n_p1_) * n_a_p0;
                    if (false) {
                        printf("posi v_p_da: %.4f vt_dot: %.4f n_p1_:%.4f n_a_p0: %.4f n_t: %.4f,"
                               "weight: %.4f ||v||: %.4f na: %.4f\n",
                               v_p_da, vt_dot, n_p1_, n_a_p0, n_t, weight,
                               sqrt(cblas_ddot(n_dim + 2, v_p_dv, 1, v_p_dv, 1)), n_a);
                    }
                } else {
                    cblas_dcopy(n_dim + 2, zero_v, 1, v_p_dv, 1);
                    n_p1_ = ((n_t - 1.) * n_p0_) / n_t;
                    double n_b = n_v0[n_dim + 1];
                    weight = 2. * n_p1_ * (vt_dot - n_b) + 2. * (1. + n_a_p0) * n_p1_;
                    // gradient of w
                    if (false) {
                        printf("s_len: %d, cur_indices: %d cur_values: %.4f, ||v||: %.4f \n",
                               s_len, *(cur_indices + 1), *(cur_values + 1),
                               sqrt(cblas_ddot(n_dim + 2, v_p_dv, 1, v_p_dv, 1)));
                    }
                    _sparse_cblas_daxpy(cur_indices + 1, cur_values + 1, s_len, weight, v_p_dv);
                    if (false) {
                        printf("s_len: %d, cur_indices: %d cur_values: %.4f, ||v||: %.4f \n",
                               s_len, *(cur_indices + 1), *(cur_values + 1),
                               sqrt(cblas_ddot(n_dim + 2, v_p_dv, 1, v_p_dv, 1)));
                    }
                    // gradient of a
                    v_p_dv[n_dim] = 0.;
                    // gradient of b
                    v_p_dv[n_dim + 1] = -2. * n_p1_ * (vt_dot - n_b);
                    // gradient of alpha
                    v_p_da = 2. * n_p1_ * vt_dot - 2. * n_p1_ * (1. - n_p1_) * n_a_p0;
                }
                cblas_daxpy(n_dim + 2, 1., v_p_dv, 1, block_grad_v, 1);
                block_grad_alpha += v_p_da;
                // update the counts
                n_t = n_t + 1.;
            }
            //gradient descent step of alpha
            cblas_dscal(n_dim + 2, -n_ga, block_grad_v, 1);
            cblas_daxpy(n_dim + 2, 1.0, n_v0, 1, block_grad_v, 1);
            cblas_dcopy(n_dim + 2, block_grad_v, 1, v_p_dv, 1);
            v_p_da = n_a_p0 + n_ga * block_grad_alpha;
            if (false) {
                if (j % 50 == 0) {
                    printf("lr: %.4f alpha: %.4f sr: %.4f sc:%.4f n_p1: %.4f label: %.1f, norm: %.4f\n",
                           n_ga, v_p_da, sr, sc, n_p1_, para->y_tr[j],
                           sqrt(cblas_ddot(n_dim + 2, v_p_dv, 1, v_p_dv, 1)));
                }
            }
            // normalization -- the projection step.
            double n_rv = sqrt(cblas_ddot(n_dim, v_p_dv, 1, v_p_dv, 1));
            if (n_rv > sr) {
                cblas_dscal(n_dim, 1. / n_rv * sr, v_p_dv, 1);
            }
            if (v_p_dv[n_dim] > sr) {
                v_p_dv[n_dim] = sr;
            }
            if (v_p_dv[n_dim + 1] > sr) {
                v_p_dv[n_dim + 1] = sr;
            }

            //----- sparse projection step
            _hard_thresholding(v_p_dv, n_dim, para->para_s);
            //----- sparse projection step

            cblas_dcopy(n_dim + 2, v_p_dv, 1, n_v1, 1); // n_v1 = v_p_dv

            double n_ra = fabs(v_p_da);
            if (n_ra > 2. * sr) {
                n_a_p1 = v_p_da / n_ra * (2. * sr);
            } else {
                n_a_p1 = v_p_da;
            }

            // update gamma_
            double n_g_a1_ = n_g_a0_ + n_ga;

            // update v_
            cblas_dcopy(n_dim + 2, n_v0, 1, n_v1_, 1);
            cblas_dscal(n_dim + 2, n_ga / n_g_a1_, n_v1_, 1);
            cblas_daxpy(n_dim + 2, n_g_a0_ / n_g_a1_, n_v0_, 1, n_v1_, 1);

            // update alpha_
            n_a_p1_ = (n_g_a0_ * n_a_p0_ + n_ga * n_a_p0) / n_g_a1_;

            // update the information
            n_p0_ = n_p1_;
            cblas_dcopy(n_dim + 2, n_v1_, 1, n_v0_, 1); // n_v0_ = n_v1_;
            n_a_p0_ = n_a_p1_;
            n_g_a0_ = n_g_a1_;
            cblas_dcopy(n_dim + 2, n_v1, 1, n_v0, 1); // n_v0 = n_v1;
            n_a_p0 = n_a_p1;
        }
        n_cnt += 1;
    }
    cblas_dcopy(n_dim, n_v1_, 1, results->wt, 1);
    results->a = n_v1_[n_dim];
    results->b = n_v1_[n_dim + 1];
    free(block_grad_v);
    free(n_v1_);
    free(n_v1);
    free(n_v0);
    free(n_v0_);
    free(v_p_dv);
    free(v_wt);
    free(one_v);
    free(zero_v);
    return true;
}


bool algo_da_solam_func(da_solam_para *para, da_solam_results *results) {

    // make sure openblas uses only one cpu at a time.
    openblas_set_num_threads(1);
    int *rand_id = para->para_rand_ind;
    int num_tr = para->num_tr;
    double *zero_v = malloc(sizeof(double) * (para->p + 2));
    double *one_v = malloc(sizeof(double) * (para->p + 2));
    for (int i = 0; i < para->p + 2; i++) {
        zero_v[i] = 0.0;
        one_v[i] = 1.0;
    }
    double *x_train = para->x_tr;
    double *y_train = para->y_tr;

    // start of the algorithm
    double sr = para->para_r;
    double sc = para->para_xi;
    int n_pass = para->para_num_pass;
    int n_dim = para->p;
    double n_p0_ = 0.; // number of positive
    double *n_v0_ = malloc(sizeof(double) * (n_dim + 2));
    cblas_dcopy(n_dim + 2, zero_v, 1, n_v0_, 1);
    double n_a_p0_ = 0.;
    double n_g_a0_ = 0.;
    // initial vector
    double *n_v0 = malloc(sizeof(double) * (n_dim + 2));
    cblas_dcopy(n_dim, one_v, 1, n_v0, 1);
    cblas_dscal(n_dim, sqrt(sr * sr / (n_dim * 1.0)), n_v0, 1);
    n_v0[n_dim] = sr;
    n_v0[n_dim + 1] = sr;
    double n_a_p0 = 2. * sr;
    // iteration time.
    double n_t = 1.;
    int n_cnt = 1;
    double *v_wt = malloc(sizeof(double) * n_dim);
    double *v_p_dv = malloc(sizeof(double) * (n_dim + 2));
    double *n_v1 = malloc(sizeof(double) * (n_dim + 2));
    double *n_v1_ = malloc(sizeof(double) * (n_dim + 2));
    double v_p_da;
    double n_a_p1;
    double n_a_p1_;
    double n_p1_;
    double *temp = malloc(sizeof(double) * n_dim);
    double *dual_aver = malloc(sizeof(double) * (n_dim + 2));
    double *bt = malloc(sizeof(double) * (n_dim + 2));
    cblas_dcopy(n_dim + 2, zero_v, 1, dual_aver, 1);
    cblas_dcopy(n_dim + 2, zero_v, 1, bt, 1);
    while (true) {
        if (n_cnt > n_pass) {
            break;
        }
        for (int j = 0; j < num_tr; j++) {
            double *t_feat = x_train + rand_id[j] * n_dim;
            double *t_label = y_train + rand_id[j];
            double n_ga = sc / sqrt(n_t);
            if (*t_label > 0) { // if it is positive case
                n_p1_ = ((n_t - 1.) * n_p0_ + 1.) / n_t;
                cblas_dcopy(n_dim, n_v0, 1, v_wt, 1);
                double n_a = n_v0[n_dim];
                cblas_dcopy(n_dim + 2, zero_v, 1, v_p_dv, 1);
                double vt_dot = cblas_ddot(n_dim, v_wt, 1, t_feat, 1);
                double weight =
                        2. * (1. - n_p1_) * (vt_dot - n_a) - 2. * (1. + n_a_p0) * (1. - n_p1_);
                cblas_daxpy(n_dim, weight, t_feat, 1, v_p_dv, 1);
                v_p_dv[n_dim] = -2. * (1. - n_p1_) * (vt_dot - n_a);
                v_p_dv[n_dim + 1] = 0.;
                cblas_daxpy(n_dim + 2, 1.0, v_p_dv, 1, dual_aver, 1);
                cblas_dscal(n_dim + 2, -n_ga, v_p_dv, 1);
                cblas_daxpy(n_dim + 2, 1.0, n_v0, 1, v_p_dv, 1);
                v_p_da = -2. * (1. - n_p1_) * vt_dot - 2. * n_p1_ * (1. - n_p1_) * n_a_p0;
                v_p_da = n_a_p0 + n_ga * v_p_da;
            } else {
                n_p1_ = ((n_t - 1.) * n_p0_) / n_t;
                cblas_dcopy(n_dim, n_v0, 1, v_wt, 1);
                double n_b = n_v0[n_dim + 1];
                cblas_dcopy(n_dim + 2, zero_v, 1, v_p_dv, 1);
                double vt_dot = cblas_ddot(n_dim, v_wt, 1, t_feat, 1);
                double weight = 2. * n_p1_ * (vt_dot - n_b) + 2. * (1. + n_a_p0) * n_p1_;
                cblas_daxpy(n_dim, weight, t_feat, 1, v_p_dv, 1);
                v_p_dv[n_dim] = 0.;
                v_p_dv[n_dim + 1] = -2. * n_p1_ * (vt_dot - n_b);
                cblas_daxpy(n_dim + 2, 1.0, v_p_dv, 1, dual_aver, 1);
                cblas_dscal(n_dim + 2, -n_ga, v_p_dv, 1);
                cblas_daxpy(n_dim + 2, 1.0, n_v0, 1, v_p_dv, 1);
                v_p_da = 2. * n_p1_ * vt_dot - 2. * n_p1_ * (1. - n_p1_) * n_a_p0;
                v_p_da = n_a_p0 + n_ga * v_p_da;
            }
            // normalization -- the projection step.
            cblas_dcopy(n_dim + 2, dual_aver, 1, bt, 1);
            cblas_dscal(n_dim + 2, -sqrt(n_t) / sc, bt, 1);
            cblas_dcopy(n_dim + 2, bt, 1, v_p_dv, 1);
            double n_rv = sqrt(cblas_ddot(n_dim, v_p_dv, 1, v_p_dv, 1));
            if (n_rv > sr) {
                cblas_dscal(n_dim, 1. / n_rv * sr, v_p_dv, 1);
            }
            if (v_p_dv[n_dim] > sr) {
                v_p_dv[n_dim] = sr;
            }
            if (v_p_dv[n_dim + 1] > sr) {
                v_p_dv[n_dim + 1] = sr;
            }

            //----- sparse projection step
            _hard_thresholding(v_p_dv, n_dim, para->para_s);
            //----- sparse projection step

            cblas_dcopy(n_dim + 2, v_p_dv, 1, n_v1, 1); //n_v1 = v_p_dv
            double n_ra = fabs(v_p_da);
            if (n_ra > 2. * sr) {
                n_a_p1 = v_p_da / n_ra * (2. * sr);
            } else {
                n_a_p1 = v_p_da;
            }
            // update gamma_
            double n_g_a1_ = n_g_a0_ + n_ga;
            // update v_
            cblas_dcopy(n_dim + 2, n_v0, 1, n_v1_, 1);
            cblas_dscal(n_dim + 2, n_ga / n_g_a1_, n_v1_, 1);
            cblas_daxpy(n_dim + 2, n_g_a0_ / n_g_a1_, n_v0_, 1, n_v1_, 1);
            // update alpha_
            n_a_p1_ = (n_g_a0_ * n_a_p0_ + n_ga * n_a_p0) / n_g_a1_;
            // update the information
            n_p0_ = n_p1_;
            cblas_dcopy(n_dim + 2, n_v1_, 1, n_v0_, 1); // n_v0_ = n_v1_;
            n_a_p0_ = n_a_p1_;
            n_g_a0_ = n_g_a1_;
            cblas_dcopy(n_dim + 2, n_v1, 1, n_v0, 1); // n_v0 = n_v1;
            n_a_p0 = n_a_p1;
            // update the counts
            n_t = n_t + 1.;
        }
        n_cnt += 1;
    }
    cblas_dcopy(n_dim, n_v1_, 1, results->wt, 1);
    results->a = n_v1_[n_dim];
    results->b = n_v1_[n_dim + 1];
    free(bt);
    free(dual_aver);
    free(temp);
    free(n_v1_);
    free(n_v1);
    free(n_v0);
    free(n_v0_);
    free(v_p_dv);
    free(v_wt);
    free(one_v);
    free(zero_v);
    return true;
}

/**
 * SPAM algorithm.
 * @param x_tr: The matrix of data samples.
 * @param y_tr: We assume that each y_tr[i] is either +1.0 or -1.0.
 * @param p: >=1 (at least one feature).
 * @param n: >=2 (at least two samples).
 * @param num_passes: >=1 (at least pass dataset once)
 * @param para_xi: >0 (constant factor of learning rate).
 * @param para_l1_reg: >=0. (==0.0 without l1-regularization.)
 * @param para_l2_reg: >=0. (==0.0 without l2-regularization.)
 * @param results: wt/wt_bar.
 * @return
 */
bool _algo_spam(const double *x_tr,
                const double *y_tr,
                int p,
                int n,
                int num_passes,
                double para_xi,
                double para_l1_reg,
                double para_l2_reg,
                spam_results *results) {

    // zero vector
    double *zero_vector = malloc(sizeof(double) * p);
    memset(zero_vector, 0, p * sizeof(double)); //set to zero.

    // initialize w1
    double *w1 = malloc(sizeof(double) * p);

    // initialize the estimate of probability p=Pr(y=1)
    double est_prob_p = 0.0;

    // initialize the estimate of the expectation of positive sample x., i.e. E[x|y=1]
    double *est_e_posi_x = malloc(sizeof(double) * p);

    // initialize the estimate of the expectation of positive sample x., i.e. E[x|y=-1]
    double *est_e_nega_x = malloc(sizeof(double) * p);

    //for each epoch i.
    for (int i = 0; i < num_passes; i++) {
        // for each training sample j
        for (int j = 0; j < n; j++) {
            // receive training sample zt=(xt,yt)
            double *cur_xt = x_tr + j * p;
            double cur_yt = y_tr[j];
            // compute a(wt), b(wt), and alpha(wt) by (8) and (9).
            if (cur_yt > 0) {

            }
        }
    }
    free(est_e_posi_x);
    free(w1);
    return true;
}

bool _algo_spam_sparse(const double *x_tr_vals,
                       const int *x_tr_indices,
                       int x_sparse_p,
                       const double *y_tr,
                       int p,
                       int n,
                       int num_passes,
                       double para_xi,
                       double para_l1_reg,
                       double para_l2_reg,
                       spam_results *results) {
    return true;
}

bool algo_spam(spam_para *para, spam_results *results) {
    if (para->is_sparse) {
        // non-sparse case
        return _algo_spam(para->x_tr, para->y_tr, para->p, para->num_tr, para->num_passes,
                          para->para_xi, para->para_l1_reg, para->para_l2_reg, results);
    } else {
        // sparse case (for sparse data).
        return _algo_spam_sparse(para->sparse_x_values, para->sparse_x_indices, para->sparse_p,
                                 para->y_tr, para->p, para->num_tr, para->num_passes,
                                 para->para_xi, para->para_l1_reg, para->para_l2_reg, results);
    }
}