
from nose.tools import assert_equal
from nose.tools import assert_almost_equal
#from nose.plugins.attrib import attr
import pprint
import random
import stats

from .core_stats import ttest_ind
from .core_stats import ttest_rel
from .core_stats import mannwhitneyu
from .core_stats import wilcoxont

def test_anova():
    assert True

#@attr('include') # maybe in newer version
def atest_ind_2way_tests():
    samples = []
    for i in range(100):
        sample_size_a = random.randint(5, 1000)
        sample_size_b = random.randint(5, 1000)
        sample_a = random.sample([x/3.0 for x in xrange(1000000)], sample_size_a)
        sample_b = random.sample([x/3.0 for x in xrange(1000000)], sample_size_b)
        samples.append((sample_a, sample_b))
    for sample_a, sample_b in samples:
        _test_ind_t_test(sample_a, sample_b, verbose=True)
        _test_mann_whitney(sample_a, sample_b, verbose=True)
#test_ind_2way_tests.include = True

def _test_ind_t_test(sample_a, sample_b, verbose=False):
    t1, p1 = stats.ttest_ind(sample_a, sample_b, True, "Male", "Female")
    t2, p2, dic_a, dic_b = ttest_ind(sample_a, sample_b, "Male", "Female", 
                             use_orig_var=True)
    if verbose:
        print "t = %s" % t2
        print "p = %s" % p2
        pprint.pprint(dic_a)
        pprint.pprint(dic_b)
    assert_almost_equal(t1, t2)
    assert_almost_equal(p1, p2)

def _test_mann_whitney(sample_a, sample_b, verbose=False):
    u1, p1 = stats.mannwhitneyu(sample_a, sample_b)
    u2, p2, dic_a, dic_b = mannwhitneyu(sample_a, sample_b, "Male", "Female")
    if verbose:
        print "u = %s" % u2
        print "p = %s" % p2
        pprint.pprint(dic_a)
        pprint.pprint(dic_b)
    assert_almost_equal(u1, u2)
    assert_almost_equal(p1, p2)

def test_paired_tests():
    samples = []
    sample_n = 500
    for i in range(100):
        sample_a = random.sample([x/3 for x in xrange(1000000)], sample_n)
        sample_b = random.sample([x/3 for x in xrange(1000000)], sample_n)
        samples.append((sample_a, sample_b))
    for sample_a, sample_b in samples:
        #_test_rel_t_test(sample_a, sample_b, verbose=False)
        _test_wilcoxon(sample_a, sample_b, verbose=False)

def _test_rel_t_test(sample_a, sample_b, verbose=False):
    t1, p1 = stats.ttest_rel(sample_a, sample_b, True, "Male", "Female")
    t2, p2, dic_a, dic_b = ttest_rel(sample_a, sample_b, "Male", "Female")
    if verbose:
        print "t = %s" % t2
        print "p = %s" % p2
        pprint.pprint(dic_a)
        pprint.pprint(dic_b)
    assert_almost_equal(t1, t2)
    assert_almost_equal(p1, p2)
    
def _test_wilcoxon(sample_a, sample_b, verbose=False):
    w1, p1 = stats.wilcoxont(sample_a, sample_b)
    w2, p2 = wilcoxont(sample_a, sample_b)
    if verbose:
        print "w = %s" % w2
        print "p = %s" % p2
    assert_almost_equal(w1, w2)
    assert_almost_equal(p1, p2)
 