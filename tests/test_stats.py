from __future__ import print_function

import gettext
gettext.install('sofa', './locale', unicode=True)

from nose.tools import assert_equal
from nose.tools import assert_almost_equal
#from nose.plugins.attrib import attr
import numpy as np
import pprint
import random

import tests.stats as stats

from core_stats import ttest_ind, ttest_rel, mannwhitneyu, wilcoxont, \
    pearsonr, spearmanr, kruskalwallish, anova, fprob, betai, gammln, betacf, \
    chisquare, kurtosis, skew, moment, kurtosistest, skewtest, normaltest, \
    sim_variance

def test_sim_variance():
    sample_a = [random.randint(1, 100000)/3.0 for x in range(10)]
    sample_b = [x*1.2 for x in sample_a if round(x,0) % 2 == 0]
    print(sample_a)
    print(sample_b)
    bolsim, p = sim_variance(sample_a, sample_b)
    assert_equal(bolsim, True)
    
def test_kurtosis():
    FISHER_ADJUSTMENT = 3.0
    for i in range(100):
        sample_size = random.randint(20, 1000)
        sample = [random.randint(1, 100000)/3.0 for x in range(sample_size)]
        k1 = stats.lkurtosis(sample)
        k2 = kurtosis(sample) + FISHER_ADJUSTMENT
        assert_almost_equal(k1, k2)
        
def test_skew():
    for i in range(100):
        sample_size = random.randint(20, 1000)
        sample = [random.randint(1, 100000)/3.0 for x in range(sample_size)]
        s1 = stats.lskew(sample)
        s2 = skew(sample)
        assert_almost_equal(s1, s2)
        
def test_kurtosistest():
    for i in range(100):
        sample_size = random.randint(20, 1000)
        sample = [random.randint(1, 100000)/3.0 for x in range(sample_size)]
        z1, p1 = stats.kurtosistest(np.array(sample))
        z2, p2, unused = kurtosistest(sample)
        assert_almost_equal(z1, z2)
        assert_almost_equal(p1, p2)

def test_skewtest():
    for i in range(100):
        sample_size = random.randint(20, 1000)
        sample = [random.randint(1, 100000)/3.0 for x in range(sample_size)]
        z1, p1 = stats.skewtest(np.array(sample))
        z2, p2, unused = skewtest(sample)
        assert_almost_equal(z1, z2)
        assert_almost_equal(p1, p2)
 
def test_normaltest():
    for i in range(100):
        sample_size = random.randint(20, 1000)
        sample = [random.randint(1, 100000)/3.0 for x in range(sample_size)]
        z1, p1 = stats.normaltest(np.array(sample))
        z2, p2, unused, unused, unused, unused = normaltest(sample)
        assert_almost_equal(z1, z2)
        assert_almost_equal(p1, p2)
        
#@attr('include') # maybe in newer version
def test_ind_2way_tests():
    for i in range(100):
        sample_size_a = random.randint(5, 1000)
        sample_size_b = random.randint(5, 1000)
        sample_a = [random.randint(1, 100000)/3.0 for x in range(sample_size_a)]
        sample_b = [random.randint(1, 100000)/3.0 for x in range(sample_size_b)]
        _test_ind_t_test(sample_a, sample_b, verbose=True)
        _test_mann_whitney(sample_a, sample_b, verbose=True)
#test_ind_2way_tests.include = True

def _test_ind_t_test(sample_a, sample_b, verbose=False):
    t1, p1 = stats.ttest_ind(sample_a, sample_b, True, "Male", "Female")
    t2, p2, dic_a, dic_b = ttest_ind(sample_a, sample_b, "Male", "Female", 
                             use_orig_var=True)
    if verbose:
        print("t1: %s t2: %s" % (t1, t2))
        print("p1: %s p2: %s" % (p1, p2))
        pprint.pprint(dic_a)
        pprint.pprint(dic_b)
    assert_almost_equal(t1, t2)
    assert_almost_equal(p1, p2)

def _test_mann_whitney(sample_a, sample_b, verbose=False):
    u1, p1 = stats.mannwhitneyu(sample_a, sample_b)
    u2, p2, dic_a, dic_b = mannwhitneyu(sample_a, sample_b, "Male", "Female")
    if verbose:
        print("u1: %s u2: %s" % (u1, u2))
        print("p1: %s p2: %s" % (p1, p2))
        pprint.pprint(dic_a)
        pprint.pprint(dic_b)
    assert_almost_equal(u1, u2)
    assert_almost_equal(p1, p2)

def test_paired_tests():
    sample_n = random.randint(20, 1000)
    for i in range(100):
        sample_a = [random.randint(1, 100000)/3.0 for x in range(sample_n)]
        sample_b = [random.randint(1, 100000)/3.0 for x in range(sample_n)]
        _test_rel_t_test(sample_a, sample_b, verbose=False)
        _test_wilcoxon(sample_a, sample_b, verbose=False)
        _test_pearsonr(sample_a, sample_b, verbose=False)
        _test_spearmanr(sample_a, sample_b, verbose=False)
#test_paired_tests.include = True

def _test_rel_t_test(sample_a, sample_b, verbose=False):
    t1, p1 = stats.ttest_rel(sample_a, sample_b, True, "Male", "Female")
    t2, p2, dic_a, dic_b = ttest_rel(sample_a, sample_b, "Male", "Female")
    if verbose:
        print("t1: %s t2: %s" % (t1, t2))
        print("p1: %s p2: %s" % (p1, p2))
        pprint.pprint(dic_a)
        pprint.pprint(dic_b)
    assert_almost_equal(t1, t2)
    assert_almost_equal(p1, p2)
    
def _test_wilcoxon(sample_a, sample_b, verbose=False):
    w1, p1 = stats.wilcoxont(sample_a, sample_b)
    w2, p2 = wilcoxont(sample_a, sample_b)
    if verbose:
        print("w1: %s w2: %s" % (w1, w2))
        print("p1: %s p2: %s" % (p1, p2))
    assert_almost_equal(w1, w2)
    assert_almost_equal(p1, p2)
    
def _test_pearsonr(sample_a, sample_b, verbose=False):
    r1, p1 = stats.pearsonr(sample_a, sample_b)
    r2, p2 = pearsonr(sample_a, sample_b)
    if verbose:
        print("r1: %s r2: %s" % (r1, r2))
        print("p1: %s p2: %s" % (p1, p2))
    assert_almost_equal(r1, r2)
    assert_almost_equal(p1, p2)
    
def _test_spearmanr(sample_a, sample_b, verbose=False):
    r1, p1 = stats.spearmanr(sample_a, sample_b)
    r2, p2 = spearmanr(sample_a, sample_b)
    if verbose:
        print("r1: %s r2: %s" % (r1, r2))
        print("p1: %s p2: %s" % (p1, p2))
    assert_almost_equal(r1, r2)
    assert_almost_equal(p1, p2)
 
def test_ind_nway_tests():
    """
    Very important to test cases where there is not much of a difference as well
        as those where there is.
    """
    for i in range(100):
        sample_lst = []
        samples_n = random.randint(3, 10)
        sample_size = random.randint(20, 1000)
        has_little_difference = random.choice([True, False])
        if has_little_difference:
            base_sample = [random.randint(1, 2000)/3.0 for x in \
                           range(sample_size)]
        else:
            has_equal_sizes = random.choice([True, False])
        for j in range(samples_n):
            if has_little_difference:
                sample_lst.append([x + \
                    random.choice([x/3.0, -x/3.0, 1, -1, 0.001, -0.001]) \
                                   for x in base_sample])
            else:
                if not has_equal_sizes:
                    sample_size += random.randint(1, round(sample_size/2.0, 0))
                sample = [random.randint(1, 10000000)/3.0 for x in \
                          range(sample_size)]
                sample_lst.append(sample)
        _test_kruskal_wallis_h(sample_lst, verbose=True)
        _test_anova(sample_lst, verbose=True)
test_ind_nway_tests.include = True

def _test_kruskal_wallis_h(sample_lst, verbose=False):
    h1, p1 = stats.kruskalwallish(sample_lst)
    h2, p2 = kruskalwallish(sample_lst)
    if verbose:
        print("h1: %s h2: %s" % (h1, h2))
        print("p1: %s p2: %s" % (p1, p2))
    assert_almost_equal(h1, h2)
    assert_almost_equal(p1, p2)

def _test_anova(sample_lst, verbose=False):
    f1, p1 = stats.anova(*sample_lst)
    labels = ["label %s" % x for x in range(len(sample_lst))]
    anova_res = anova(sample_lst, labels, high=True)
    f2 = anova_res[1]
    p2 = anova_res[0]
    if verbose:
        print("f1: %s f2: %s" % (f1, f2))
        print("p1: %s p2: %s" % (p1, p2))
    assert_almost_equal(f1, float(f2))
    assert_almost_equal(p1, float(p2))
    
def test_fprob():
    for i in range(100):
        dfnum = random.randint(3, 12)
        dfden = random.randint(100, 20000)
        div = random.randint(2,100)
        F = random.randint(0, 1000)/float(div)
        p1 = stats.lfprob(dfnum, dfden, F)
        p2 = float(fprob(dfnum, dfden, F, high=True))
        assert_almost_equal(p1, p2)
#test_fprob.include = True

def test_betai():
    for i in range(100):
        x_near_edge = random.choice([True, False])
        a = random.randint(600, 18000)/3.0 # 218
        b = random.randint(1,5)/3.0 # 1.5
        if x_near_edge:
            print("Near edge")
            x = random.choice([0.000001234121, 0.99814821929386453580553591])
        else:
            x = random.random()
        b1 = stats.lbetai(a, b, x)
        b2 = float(betai(a, b, x, high=True))
        assert_almost_equal(b1, b2)
#test_betai.include = True

def test_gammln():
    for i in range(100):
        xx = random.randint(0, 10000)/103.0
        g1 = stats.gammln(xx)
        g2 = float(gammln(xx, high=True))
        assert_almost_equal(g1, g2)
#test_gammln.include = True

def test_betacf():
    for i in range(100):
        x_near_edge = random.choice([True, False])
        a = random.randint(100, 10000)/3.0 # 660.333333333
        b = random.randint(1,5)/3.0 # 0.333333333333
        if x_near_edge:
            print("Near edge")
            x = random.choice([0.000001234121, 0.994394814936])
        else:
            x = random.random()
        print(a, b, x)
        b1 = stats.lbetacf(a, b, x)
        b2 = float(betacf(a, b, x, high=True))
        assert_almost_equal(b1, b2)
#test_betacf.include = True

def test_chisquare():
    """
    Cannot test with df because assumed to be k-1 in stats.
    So not a complete test.
    """
    make_very_similar = random.choice([True, False])
    for i in range(100):
        sample_size = random.randint(3, 30)
        f_obs = [random.randint(3, 500) for x in range(sample_size)]
        if make_very_similar:
            f_exp = [x + random.randint(-1, 1) for x in f_obs]
        else:
            f_exp = [random.randint(3, 500) for x in range(sample_size)]
        c1, p1 = stats.lchisquare(f_obs, f_exp)
        c2, p2 = chisquare(f_obs, f_exp)
        c2 = float(c2)
        p2 = float(p2)
        assert_almost_equal(c1, c2)
        assert_almost_equal(p1, p2)
#test_chisquare.include = True
