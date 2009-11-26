
from __future__ import print_function
import copy
import decimal
import math
import numpy as np
from types import ListType, TupleType

import my_globals
import getdata
import util

D = decimal.Decimal
decimal.getcontext().prec = 200

def get_list(dbe, cur, tbl, fld_measure, fld_filter, filter_val):
    """
    Get list of non-missing values in field.
    Used, for example, in the independent samples t-test.
    """
    debug = False
    quoter = getdata.get_obj_quoter_func(dbe)
    placeholder = getdata.get_placeholder(dbe)
    SQL_get_list = "SELECT %s FROM %s WHERE %s IS NOT NULL AND %s = %s" % \
                    (quoter(fld_measure), quoter(tbl), quoter(fld_measure), 
                     quoter(fld_filter), placeholder)
    if debug: print(SQL_get_list)
    cur.execute(SQL_get_list, (filter_val,))
    lst = [x[0] for x in cur.fetchall()]
    return lst

def get_paired_lists(dbe, cur, tbl, fld_a, fld_b):
    """
    For each field, returns a list of all non-missing values where there is also
        a non-missing value in the other field.
        Used in, for example, the paired samples t-test.
    """
    quoter = getdata.get_obj_quoter_func(dbe)
    SQL_get_lists = "SELECT %s, %s " % (quoter(fld_a), quoter(fld_b)) + \
        "FROM %s " % quoter(tbl) + \
        "WHERE %s IS NOT NULL AND %s IS NOT NULL" % (quoter(fld_a), 
                                                     quoter(fld_b))
    cur.execute(SQL_get_lists)
    data_tups = cur.fetchall()
    lst_a = [x[0] for x in data_tups]
    lst_b = [x[1] for x in data_tups]
    return lst_a, lst_b

def get_val_quoter(dbe, flds, fld, val):
    """
    Get function for quoting values according to field type and value.
    """
    num = True
    if not flds[fld][my_globals.FLD_BOLNUMERIC]:
        num = False
    elif dbe == my_globals.DBE_SQLITE:
        if not util.isNumeric(val):
            num = False
    if num:
        val_quoter = lambda s: s
    else:
        val_quoter = getdata.get_val_quoter_func(dbe)
    return val_quoter

def get_obs_exp(dbe, cur, tbl, flds, fld_a, fld_b):
    """
    Get list of observed and expected values ready for inclusion in Pearson's
        Chi Square test.
    NB must return 0 if nothing.  All cells must be filled.
    Returns lst_obs, lst_exp, min_count, perc_cells_lt_5, df.    
    """
    debug = False
    obj_quoter = getdata.get_obj_quoter_func(dbe)
    qtbl = obj_quoter(tbl)
    qfld_a = obj_quoter(fld_a)
    qfld_b = obj_quoter(fld_b)
    # get row vals used
    SQL_row_vals_used = """SELECT %(qfld_a)s
        FROM %(qtbl)s
        WHERE %(qfld_b)s IS NOT NULL AND %(qfld_a)s IS NOT NULL
        GROUP BY %(qfld_a)s
        ORDER BY %(qfld_a)s""" % {"qtbl": qtbl, "qfld_a": qfld_a, 
                                  "qfld_b": qfld_b}
    cur.execute(SQL_row_vals_used)
    vals_a = [x[0] for x in cur.fetchall()]
    if len(vals_a) > 30:
        raise Exception, "Too many values in row variable"
    # get col vals used
    SQL_col_vals_used = """SELECT %(qfld_b)s
        FROM %(qtbl)s
        WHERE %(qfld_a)s IS NOT NULL AND %(qfld_b)s IS NOT NULL
        GROUP BY %(qfld_b)s
        ORDER BY %(qfld_b)s""" % {"qtbl": qtbl, "qfld_a": qfld_a, 
                                  "qfld_b": qfld_b}
    cur.execute(SQL_col_vals_used)
    vals_b = [x[0] for x in cur.fetchall()]
    if len(vals_b) > 30:
        raise Exception, "Too many values in column variable"
    if len(vals_a)*len(vals_b) > 60:
        raise Exception, "Too many cells in contingency table."
    # build SQL to get all observed values (for each a, through b's)
    SQL_get_obs = "SELECT "
    sql_lst = []
    # need to filter by vals within SQL so may need quoting observed values etc
    for val_a in vals_a:
        val_quoter_a = get_val_quoter(dbe, flds, fld_a, val_a)
        for val_b in vals_b:
            val_quoter_b = get_val_quoter(dbe, flds, fld_b, val_b)
            clause = "\nSUM(CASE WHEN %s = %s and %s = %s THEN 1 ELSE 0 END)" \
                % (qfld_a, val_quoter_a(val_a), qfld_b, 
                   val_quoter_b(val_b))
            sql_lst.append(clause)
    SQL_get_obs += ", ".join(sql_lst)
    SQL_get_obs += "\nFROM %s " % qtbl
    if debug: print(SQL_get_obs)
    cur.execute(SQL_get_obs)
    tup_obs = cur.fetchall()[0]
    if not tup_obs:
        raise Exception, "No observed values"
    lst_obs = list(tup_obs)
    if debug: print("lst_obs: %s" % lst_obs)
    obs_total = sum(lst_obs)
    # expected values
    lst_fracs_a = get_fracs(cur, qtbl, qfld_a)
    lst_fracs_b = get_fracs(cur, qtbl, qfld_b)
    df = (len(lst_fracs_a)-1)*(len(lst_fracs_b)-1)
    lst_exp = []
    for frac_a in lst_fracs_a:
        for frac_b in lst_fracs_b:
            lst_exp.append(frac_a*frac_b*obs_total)
    if debug: print("lst_exp: %s" % lst_exp)
    if len(lst_obs) != len(lst_exp):
        raise Exception, "Different number of observed and expected values." + \
            " %s vs %s" % (len(lst_obs), len(lst_exp))
    min_count = min(lst_exp)
    lst_lt_5 = [x for x in lst_exp if x < 5]
    perc_cells_lt_5 = 100*(len(lst_lt_5))/float(len(lst_exp))
    return vals_a, vals_b, lst_obs, lst_exp, min_count, perc_cells_lt_5, df

def get_fracs(cur, qtbl, qfld):
    """
    What fraction of the cross tab values are for each value in field?
    Leaves out values where data is missing.
    Returns lst_fracs
    """
    debug = False
    SQL_get_fracs = """SELECT %(qfld)s, COUNT(*)
        FROM %(qtbl)s 
        WHERE %(qfld)s IS NOT NULL
        GROUP BY %(qfld)s
        ORDER BY %(qfld)s""" % {"qfld": qfld, "qtbl": qtbl}
    if debug: print(SQL_get_fracs)
    cur.execute(SQL_get_fracs)
    lst_counts = []
    total = 0
    for data_tup in cur.fetchall():
        val = data_tup[1]
        lst_counts.append(val)
        total += val
    lst_fracs = [x/float(total) for x in lst_counts]
    return lst_fracs

def pearsons_chisquare(dbe, cur, tbl, flds, fld_a, fld_b):
    """
    Returns chisq, p, min_count, perc_cells_lt_5
    """
    debug = False
    vals_a, vals_b, lst_obs, lst_exp, min_count, perc_cells_lt_5, df = \
                                get_obs_exp(dbe, cur, tbl, flds, fld_a, fld_b)
    if debug: print(lst_obs, lst_exp)
    chisq, p = chisquare(lst_obs, lst_exp, df)
    return (chisq, p, vals_a, vals_b, lst_obs, lst_exp, min_count, 
        perc_cells_lt_5, df)

# code below here is modified versions of code in stats.py and pstats.py

# Copyright notice for scipy stats.py.

# Copyright (c) Gary Strangman.  All rights reserved
#
# Disclaimer
#
# This software is provided "as-is".  There are no expressed or implied
# warranties of any kind, including, but not limited to, the warranties
# of merchantability and fittness for a given application.  In no event
# shall Gary Strangman be liable for any direct, indirect, incidental,
# special, exemplary or consequential damages (including, but not limited
# to, loss of use, data or profits, or business interruption) however
# caused and on any theory of liability, whether in contract, strict
# liability or tort (including negligence or otherwise) arising in any way
# out of the use of this software, even if advised of the possibility of
# such damage.
#

#
# Heavily adapted for use by SciPy 2002 by Travis Oliphant

def chisquare(f_obs,f_exp=None, df=None):
    """
    From stats.py.  Modified to receive df e.g. when in a crosstab.
    In a crosstab, df will NOT be k-1 it will be (a-1) x (b-1)
          Male   Female
    0-19
    20-29
    30-39
    40-49
    50+
    k=(2x5) i.e. 10, k-1 = 9 but df should be (2-1) x (5-1) i.e. 4 
    -------------------------------------
    Calculates a one-way chi square for list of observed frequencies and returns
    the result.  If no expected frequencies are given, the total N is assumed to
    be equally distributed across all groups.

    Usage:   chisquare(f_obs, f_exp=None)   f_obs = list of observed cell freq.
    Returns: chisquare-statistic, associated p-value
    """
    k = len(f_obs)                 # number of groups
    if f_exp == None:
        f_exp = [sum(f_obs)/float(k)] * len(f_obs) # create k bins with = freq.
    chisq = 0
    for i in range(len(f_obs)):
        chisq = chisq + (f_obs[i]-f_exp[i])**2 / float(f_exp[i])
    if not df: df = k-1
    return chisq, chisqprob(chisq, df)

def anova_orig(lst_samples, lst_labels, high=False):
    """
    Included for testing only.
    From stats.py.  Changed name to anova, replaced 
        array versions e.g. amean with list versions e.g. lmean,
        supply data as list of lists.  
    -------------------------------------
    Performs a 1-way ANOVA, returning an F-value and probability given
    any number of groups.  From Heiman, pp.394-7.

    Returns: F value, one-tailed p-value
    """
    a = len(lst_samples)           # ANOVA on 'a' groups, each in its own list
    n = len(lst_samples[0])
    ns = [0]*a
    alldata = []
    dics = []
    for i in range(a):
        sample = lst_samples[i]
        label = lst_labels[i]
        dics.append({"label": label, "n": n, "mean": mean(sample), 
                     "sd": stdev(sample), "min": min(sample), 
                     "max": max(sample)})
    ns = map(len, lst_samples)
    for i in range(len(lst_samples)):
        alldata = alldata + lst_samples[i]
    bign = len(alldata)
    sstot = sum_squares(alldata)-(square_of_sums(alldata)/float(bign))
    ssbn = 0
    for sample in lst_samples:
        ssbn = ssbn + square_of_sums(sample)/float(len(sample))
    ssbn = ssbn - (square_of_sums(alldata)/float(bign))
    sswn = sstot-ssbn
    dfbn = a-1
    dfwn = bign - a
    msb = ssbn/float(dfbn)
    msw = sswn/float(dfwn)
    F = msb/msw
    p = fprob(dfbn, dfwn, F)
    print("using orig with F: %s" % F)
    return p, F, dics, sswn, dfwn, msw, ssbn, dfbn, msb

def anova(samples, labels, high=True):
    """
    From NIST algorithm used for their ANOVA tests.
    Added correction factor.
    high - high precision but much, much slower.  Multiplies each by 10 (and
        divides by 10 and 100 as appropriate) plus uses decimal rather than
        floating point.  Needed to handle difficult datasets e.g. ANOVA test 9 
        from NIST site.
    """
    n_samples = len(samples)
    sample_ns = map(len, samples)
    dics = []
    for i in range(n_samples):
        sample = samples[i]
        label = labels[i]
        dics.append({"label": label, "n": sample_ns[i], 
                     "mean": mean(sample, high), "sd": stdev(sample, high), 
                     "min": min(sample), "max": max(sample)})
    if high: # inflate
        # if to 1 decimal point will push from float to integer (reduce errors)
        inflated_samples = []
        for sample in samples:
            inflated_samples.append([x*10 for x in sample]) # NB inflated
        samples = inflated_samples
        sample_means = [util.f2d(mean(x, high)) for x in samples] # NB inflated
    else:
        sample_means = [mean(x, high) for x in samples]
    sswn = get_sswn(samples, sample_means, sample_ns, high)
    dfwn = sum(sample_ns) - n_samples
    mean_squ_wn = sswn/dfwn
    ssbn = get_ssbn(samples, sample_means, n_samples, sample_ns, high)
    dfbn = n_samples - 1
    mean_squ_bn = ssbn/dfbn
    F = mean_squ_bn/mean_squ_wn
    p = fprob(dfbn, dfwn, F, high)
    return p, F, dics, sswn, dfwn, mean_squ_wn, ssbn, dfbn, mean_squ_bn

def get_sswn(samples, sample_means, sample_ns, high=False):
    "Get sum of squares within treatment"
    if not high:
        sswn = 0 # sum of squares within treatment
        for i, sample in enumerate(samples):
            diffs = []
            sample_mean = sample_means[i]
            for val in sample:
                diffs.append(val - sample_mean)
            squ_diffs = [(x**2) for x in diffs]
            sum_squ_diffs = sum(squ_diffs)
            sswn += sum_squ_diffs
    else:    
        sswn = D("0") # sum of squares within treatment
        for i, sample in enumerate(samples):
            diffs = []
            sample_mean = sample_means[i]
            for val in sample:
                diffs.append(util.f2d(val) - sample_mean)
            squ_diffs = [(x**2) for x in diffs]
            sum_squ_diffs = sum(squ_diffs)
            sswn += sum_squ_diffs
        sswn = sswn/10**2 # deflated
    return sswn

def get_ssbn(samples, sample_means, n_samples, sample_ns, high=False):
    """
    Get sum of squares between treatment.
    Has high-precision (but slower) version.  NB Samples and sample means are
        inflated uniformly in the high precision versions.
    """
    if not high:
        sum_all_vals = sum(sum(x) for x in samples)
        n_tot = sum(sample_ns)
        grand_mean = sum_all_vals/float(n_tot) # correction factor
        squ_diffs = []
        for i in range(n_samples):
            squ_diffs.append((sample_means[i] - grand_mean)**2)
        sum_n_x_squ_diffs = 0
        for i in range(n_samples):
            sum_n_x_squ_diffs += sample_ns[i]*squ_diffs[i]
        ssbn = sum_n_x_squ_diffs
    else:
        sum_all_vals = util.f2d(sum(util.f2d(sum(x)) for x in samples))
        n_tot = util.f2d(sum(sample_ns))
        grand_mean = sum_all_vals/n_tot # NB inflated
        squ_diffs = []
        for i in range(n_samples):
            squ_diffs.append((sample_means[i] - grand_mean)**2)
        sum_n_x_squ_diffs = D("0")
        for i in range(n_samples):
            sum_n_x_squ_diffs += sample_ns[i]*squ_diffs[i]
        ssbn = sum_n_x_squ_diffs/(10**2) # deflated
    return ssbn

def kruskalwallish(*args):
    """
    From stats.py.  No changes.  
    -------------------------------------
    The Kruskal-Wallis H-test is a non-parametric ANOVA for 3 or more
    groups, requiring at least 5 subjects in each group.  This function
    calculates the Kruskal-Wallis H-test for 3 or more independent samples
    and returns the result.  

    Usage:   kruskalwallish(*args)
    Returns: H-statistic (corrected for ties), associated p-value
    """
    args = list(args)
    n = [0]*len(args)
    all = []
    n = map(len,args)
    for i in range(len(args)):
        all = all + args[i]
    ranked = rankdata(all)
    T = tiecorrect(ranked)
    for i in range(len(args)):
        args[i] = ranked[0:n[i]]
        del ranked[0:n[i]]
    rsums = []
    for i in range(len(args)):
        rsums.append(sum(args[i])**2)
        rsums[i] = rsums[i] / float(n[i])
    ssbn = sum(rsums)
    totaln = sum(n)
    h = 12.0 / (totaln*(totaln+1)) * ssbn - 3*(totaln+1)
    df = len(args) - 1
    if T == 0:
        raise ValueError, 'All numbers are identical in kruskalwallish'
    h = h / float(T)
    return h, chisqprob(h,df)

def ttest_ind(sample_a, sample_b, label_a, label_b, use_orig_var=False):
    """
    From stats.py - there are changes to variable labels and comments;
        and the output is extracted early to give greater control over 
        presentation.  There are no changes to algorithms apart from calculating 
        sds once, rather than squaring to get var and taking sqrt to get sd 
        again ;-).  Plus use variance to get var, not stdev then squared.
    Returns t, p, dic_a, dic_b (p is the two-tailed probability)
    
    use_orig_var = use original (flawed) approach to sd and var.  Needed for 
        unit testing against stats.py.  Sort of like matching bug for bug ;-).
    ---------------------------------------------------------------------
    Calculates the t-obtained T-test on TWO INDEPENDENT samples of
    scores a, and b.  From Numerical Recipes, p.483.
    """
    mean_a = mean(sample_a)
    mean_b = mean(sample_b)
    if use_orig_var:
        se_a = stdev(sample_a)**2
        se_b = stdev(sample_b)**2
        sd_a = math.sqrt(se_a)
        sd_b = math.sqrt(se_b)
    else:
        se_a = variance(sample_a)
        se_b = variance(sample_b)
        sd_a = stdev(sample_a)
        sd_b = stdev(sample_a)
    n_a = len(sample_a)
    n_b = len(sample_b)
    df = n_a + n_b - 2
    svar = ((n_a - 1)*se_a + (n_b - 1)*se_b)/float(df)
    t = (mean_a - mean_b)/math.sqrt(svar*(1.0/n_a + 1.0/n_b))
    p = betai(0.5*df, 0.5, df/(df + t*t))
    min_a = min(sample_a)
    min_b = min(sample_b)
    max_a = max(sample_a)
    max_b = max(sample_b)
    dic_a = {"label": label_a, "n": n_a, "mean": mean_a, "sd": sd_a, 
             "min": min_a, "max": max_a}
    dic_b = {"label": label_b, "n": n_b, "mean": mean_b, "sd": sd_b, 
             "min": min_b, "max": max_b}
    return t, p, dic_a, dic_b

def ttest_rel (sample_a, sample_b, label_a='Sample1', label_b='Sample2'):
    """
    From stats.py - there are changes to variable labels and comments;
        and the output is extracted early to give greater control over 
        presentation.  There are no changes to algorithms.
    Returns t, p, dic_a, dic_b (p is the two-tailed probability)
    ---------------------------------------------------------------------
    Calculates the t-obtained T-test on TWO RELATED samples of scores,
    a and b.  From Numerical Recipes, p.483.
    """
    if len(sample_a)<>len(sample_b):
        raise ValueError, 'Unequal length lists in ttest_rel.'
    mean_a = mean(sample_a)
    mean_b = mean(sample_b)
    var_a = variance(sample_a)
    var_b = variance(sample_b)
    n = len(sample_a)
    cov = 0
    for i in range(n):
        cov = cov + (sample_a[i] - mean_a) * (sample_b[i] - mean_b)
    df = n - 1
    cov = cov / float(df)
    sd = math.sqrt((var_a + var_b - 2.0*cov) / float(n))
    t = (mean_a - mean_b)/sd
    p = betai(0.5*df, 0.5, df / (df + t*t))
    min_a = min(sample_a)
    min_b = min(sample_b)
    max_a = max(sample_a)
    max_b = max(sample_b)
    sd_a = math.sqrt(var_a)
    sd_b = math.sqrt(var_b)
    dic_a = {"label": label_a, "n": n, "mean": mean_a, "sd": sd_a, 
             "min": min_a, "max": max_a}
    dic_b = {"label": label_b, "n": n, "mean": mean_b, "sd": sd_b, 
             "min": min_b, "max": max_b}
    return t, p, dic_a, dic_b

def mannwhitneyu(sample_a, sample_b, label_a='Sample1', label_b='Sample2'):
    """
    From stats.py - there are changes to variable labels and comments;
        and the output is extracted early to give greater control over 
        presentation.  Also added calculation of mean ranks, plus min and 
        max values.
    -------------------------------------
    Calculates a Mann-Whitney U statistic on the provided scores and
    returns the result.  Use only when the n in each condition is < 20 and
    you have 2 independent samples of ranks.  NOTE: Mann-Whitney U is
    significant if the u-obtained is LESS THAN or equal to the critical
    value of U found in the tables.  Equivalent to Kruskal-Wallis H with
    just 2 groups.

    Usage:   mannwhitneyu(data)
    Returns: u-statistic, one-tailed p-value (i.e., p(z(U))), dic_a, dic_b
    """
    n_a = len(sample_a)
    n_b = len(sample_b)
    ranked = rankdata(sample_a + sample_b)
    rank_a = ranked[0:n_a]       # get the sample_a ranks
    rank_b = ranked[n_a:]        # the rest are sample_b ranks
    avg_rank_a = mean(rank_a)
    avg_rank_b = mean(rank_b)
    u_a = n_a*n_b + (n_a*(n_a + 1))/2.0 - sum(rank_a)  # calc U for sample_a
    u_b = n_a*n_b - u_a                            # remainder is U for sample_b
    bigu = max(u_a, u_b)
    smallu = min(u_a, u_b)
    T = math.sqrt(tiecorrect(ranked))  # correction factor for tied scores
    if T == 0:
        raise ValueError, 'All numbers are identical in lmannwhitneyu'
    sd = math.sqrt(T*n_a*n_b*(n_a + n_b + 1)/12.0)
    z = abs((bigu-n_a*n_b/2.0) / sd)  # normal approximation for prob calc
    p = 1.0 - zprob(z)
    min_a = min(sample_a)
    min_b = min(sample_b)
    max_a = max(sample_a)
    max_b = max(sample_b)
    dic_a = {"label": label_a, "n": n_a, "avg rank": avg_rank_a, 
             "min": min_a, "max": max_a}
    dic_b = {"label": label_b, "n": n_b, "avg rank": avg_rank_b, 
             "min": min_b, "max": max_b}
    return smallu, p, dic_a, dic_b

def wilcoxont(x, y):
    """
    From stats.py.  Added error trapping.
    -------------------------------------
    Calculates the Wilcoxon T-test for related samples and returns the
    result.  A non-parametric T-test.

    Usage:   wilcoxont(x,y)
    Returns: a t-statistic, two-tail probability estimate, z
    """
    if len(x) <> len(y):
        raise ValueError, 'Unequal N in wilcoxont.  Aborting.'
    n = len(x)
    d=[]
    for i in range(len(x)):
        try:
            diff = x[i] - y[i]
        except TypeError, e:            
            raise Exception, "Both values in pair must be numeric: %s and %s" \
                % (x[i], y[i])
        if diff <> 0:
            d.append(diff)
    count = len(d)
    absd = map(abs, d)
    absranked = rankdata(absd)
    r_plus = 0.0
    r_minus = 0.0
    for i in range(len(absd)):
        if d[i] < 0:
            r_minus = r_minus + absranked[i]
        else:
            r_plus = r_plus + absranked[i]
    wt = min(r_plus, r_minus)
    mn = count * (count+1) * 0.25
    se =  math.sqrt(count*(count+1)*(2.0*count+1.0)/24.0)
    z = math.fabs(wt-mn) / se
    prob = 2*(1.0 -zprob(abs(z)))
    return wt, prob

def pearsonr(x,y):
    """
    From stats.py.  No changes apart from added error trapping.  
    -------------------------------------
    Calculates a Pearson correlation coefficient and the associated
    probability value.  Taken from Heiman's Basic Statistics for the Behav.
    Sci (2nd), p.195.

    Usage:   pearsonr(x,y)      where x and y are equal-length lists
    Returns: Pearson's r value, two-tailed p-value
    """
    TINY = 1.0e-30
    if len(x) <> len(y):
        raise ValueError, 'Input values not paired in pearsonr.  Aborting.'
    n = len(x)
    try:
        x = map(float,x)
        y = map(float,y)
    except ValueError, e:
        raise Exception, "Unable to calculate Pearson's R.  %s" % e 
    xmean = mean(x)
    ymean = mean(y)
    r_num = n*(summult(x,y)) - sum(x)*sum(y)
    r_den = math.sqrt((n*sum_squares(x) - square_of_sums(x)) * 
                      (n*sum_squares(y)-square_of_sums(y)))
    r = (r_num / r_den)  # denominator already a float
    df = n-2
    t = r*math.sqrt(df/((1.0-r+TINY)*(1.0+r+TINY)))
    prob = betai(0.5*df,0.5,df/float(df+t*t))
    return r, prob

def spearmanr(x,y):
    """
    From stats.py.  No changes.  
    -------------------------------------
    Calculates a Spearman rank-order correlation coefficient.  Taken
    from Heiman's Basic Statistics for the Behav. Sci (1st), p.192.

    Usage:   spearmanr(x,y)      where x and y are equal-length lists
    Returns: Spearman's r, two-tailed p-value
    """
    TINY = 1e-30
    if len(x) <> len(y):
        raise ValueError, 'Input values not paired in spearmanr.  Aborting.'
    n = len(x)
    rankx = rankdata(x)
    ranky = rankdata(y)
    dsq = sumdiffsquared(rankx,ranky)
    rs = 1 - 6*dsq / float(n*(n**2-1))
    t = rs * math.sqrt((n-2) / ((rs+1.0)*(1.0-rs)))
    df = n-2
    probrs = betai(0.5*df,0.5,df/(df+t*t))  # t already a float
    # probability values for rs are from part 2 of the spearman function in
    # Numerical Recipes, p.510.  They are close to tables, but not exact. (?)
    return rs, probrs

def rankdata(inlist):
    """
    From stats.py.  No changes.  
    -------------------------------------
    Ranks the data in inlist, dealing with ties appropritely.  Assumes
    a 1D inlist.  Adapted from Gary Perlman's |Stat ranksort.

    Usage:   rankdata(inlist)
    Returns: a list of length equal to inlist, containing rank scores
    """
    n = len(inlist)
    svec, ivec = shellsort(inlist)
    sumranks = 0
    dupcount = 0
    newlist = [0]*n
    for i in range(n):
        sumranks = sumranks + i
        dupcount = dupcount + 1
        if i==n-1 or svec[i] <> svec[i+1]:
            averank = sumranks / float(dupcount) + 1
            for j in range(i-dupcount+1,i+1):
                newlist[ivec[j]] = averank
            sumranks = 0
            dupcount = 0
    return newlist

def shellsort(inlist):
    """
    From stats.py.  No changes.  
    -------------------------------------
    Shellsort algorithm.  Sorts a 1D-list.

    Usage:   shellsort(inlist)
    Returns: sorted-inlist, sorting-index-vector (for original list)
    """
    n = len(inlist)
    svec = copy.deepcopy(inlist)
    ivec = range(n)
    gap = n/2   # integer division needed
    while gap >0:
        for i in range(gap,n):
            for j in range(i-gap,-1,-gap):
                while j>=0 and svec[j]>svec[j+gap]:
                    temp        = svec[j]
                    svec[j]     = svec[j+gap]
                    svec[j+gap] = temp
                    itemp       = ivec[j]
                    ivec[j]     = ivec[j+gap]
                    ivec[j+gap] = itemp
        gap = gap / 2  # integer division needed
    # svec is now sorted inlist, and ivec has the order svec[i] = vec[ivec[i]]
    return svec, ivec

def tiecorrect(rankvals):
    """
    From stats.py.  No changes.  
    -------------------------------------
    Corrects for ties in Mann Whitney U and Kruskal Wallis H tests.  See
    Siegel, S. (1956) Nonparametric Statistics for the Behavioral Sciences.
    New York: McGraw-Hill.  Code adapted from |Stat rankind.c code.

    Usage:   tiecorrect(rankvals)
    Returns: T correction factor for U or H
    """
    sorted,posn = shellsort(rankvals)
    n = len(sorted)
    T = 0.0
    i = 0
    while (i<n-1):
        if sorted[i] == sorted[i+1]:
            nties = 1
            while (i<n-1) and (sorted[i] == sorted[i+1]):
                nties = nties +1
                i = i +1
            T = T + nties**3 - nties
        i = i+1
    T = T / float(n**3-n)
    return 1.0 - T


def zprob(z):
    """
    From stats.py.  No changes.  
    -------------------------------------
    Returns the area under the normal curve 'to the left of' the given z value.
    Thus, 
        - for z<0, zprob(z) = 1-tail probability
        - for z>0, 1.0-zprob(z) = 1-tail probability
        - for any z, 2.0*(1.0-zprob(abs(z))) = 2-tail probability
    Adapted from z.c in Gary Perlman's |Stat.

    Usage:   zprob(z)
    """
    Z_MAX = 6.0    # maximum meaningful z-value
    if z == 0.0:
        x = 0.0
    else:
        y = 0.5 * math.fabs(z)
        if y >= (Z_MAX*0.5):
            x = 1.0
        elif (y < 1.0):
            w = y*y
            x = ((((((((0.000124818987 * w
                        -0.001075204047) * w +0.005198775019) * w
                      -0.019198292004) * w +0.059054035642) * w
                    -0.151968751364) * w +0.319152932694) * w
                  -0.531923007300) * w +0.797884560593) * y * 2.0
        else:
            y = y - 2.0
            x = (((((((((((((-0.000045255659 * y
                             +0.000152529290) * y -0.000019538132) * y
                           -0.000676904986) * y +0.001390604284) * y
                         -0.000794620820) * y -0.002034254874) * y
                       +0.006549791214) * y -0.010557625006) * y
                     +0.011630447319) * y -0.009279453341) * y
                   +0.005353579108) * y -0.002141268741) * y
                 +0.000535310849) * y +0.999936657524
    if z > 0.0:
        prob = ((x+1.0)*0.5)
    else:
        prob = ((1.0-x)*0.5)
    return prob

def mean(vals, high=False):
    """
    From stats.py.  No changes except option of using Decimals instead 
        of floats and adding error trapping. 
    -------------------------------------
    Returns the arithmetic mean of the values in the passed list.
    Assumes a '1D' list, but will function on the 1st dim of an array(!).
    
    Usage:   mean(vals)
    """
    if not high:
        sum = 0
        for val in vals:
            try:
                sum += val
            except Exception:
                raise Exception, "Unable to add \"%s\" to running total." % val
        mean = sum/float(len(vals))
    else:
        tot = D("0")
        for val in vals:
            try:
                tot += util.f2d(val)
            except Exception:
                raise Exception, "Unable to add \"%s\" to running total." % val
        mean = tot/len(vals)
    return mean

def variance(vals, high=False):
    """
    From stats.py.  No changes except option of using Decimals not floats.  
    -------------------------------------
    Returns the variance of the values in the passed list using N-1
    for the denominator (i.e., for estimating population variance).
    
    Usage:   variance(vals)
    """
    n = len(vals)
    mn = mean(vals, high)
    deviations = [0]*len(vals)
    for i in range(len(vals)):
        val = vals[i]
        if high:
            val = util.f2d(val)
        deviations[i] = val - mn
    if not high:
        var = sum_squares(deviations)/float(n-1)
    else:
        var = sum_squares(deviations, high)/util.f2d(n-1)
    return var

def stdev(vals, high=False):
    """
    From stats.py.  No changes except option of using Decimals instead 
        of floats.  
    -------------------------------------
    Returns the standard deviation of the values in the passed list
    using N-1 in the denominator (i.e., to estimate population stdev).
    
    Usage:   stdev(vals)
    """
    try:
        if high:
            stdev = util.f2d(math.sqrt(variance(vals, high)))
        else:
            stdev = math.sqrt(variance(vals))
    except ValueError:
        raise Exception, ("stdev - error getting square root.  Negative "
                          "variance value?")
    return stdev

def betai(a, b, x, high=False):
    """
    From stats.py.  No changes apart from adding detail to error message.  
    -------------------------------------
    Returns the incomplete beta function:
    
        I-sub-x(a,b) = 1/B(a,b)*(Integral(0,x) of t^(a-1)(1-t)^(b-1) dt)
    
    where a,b>0 and B(a,b) = G(a)*G(b)/(G(a+b)) where G(a) is the gamma
    function of a.  The continued fraction formulation is implemented here,
    using the betacf function.  (Adapted from: Numerical Recipies in C.)
    
    Usage:   betai(a,b,x)
    """
    if high:        
        a = util.f2d(a)
        b = util.f2d(b)
        x = util.f2d(x)
        zero = D("0")
        one = D("1")
        two = D("2")
    else:
        zero = 0.0
        one = 1.0
        two = 2.0
    if (x < zero or x > one):
        raise ValueError, "Bad x %s in betai" % x
    if (x==zero or x==one):
        bt = zero
    else:
        if high:
            bt_raw = math.exp(gammln(a+b, high) - gammln(a, high) - \
                              gammln(b, high)+a*util.f2d(math.log(x)) + \
                              b*util.f2d(math.log(one - x)))
            bt = util.f2d(bt_raw)
        else:
            bt = math.exp(gammln(a+b, high) - gammln(a, high) - gammln(b, high)
                          + a*math.log(x) + b*math.log(1.0 - x))
    if (x < (a + one)/(a + b + two)):
        if high:
            return bt*betacf(a,b,x, high)/a
        else:
            return bt*betacf(a,b,x)/float(a)
    else:
        if high:
            return one-bt*betacf(b, a, one-x, high)/b
        else:
            return 1.0-bt*betacf(b,a,1.0-x)/float(b)

def sum_squares(vals, high=False):
    """
    From stats.py.  No changes except option of using Decimal instead of float.  
    -------------------------------------
    Squares each value in the passed list, adds up these squares and
    returns the result.
    
    Usage:   sum_squares(vals)
    """
    if high:
        sum_squares = D("0")
        for val in vals:
            decval = util.f2d(val)
            sum_squares += (decval * decval)
    else:
        sum_squares = 0
        for val in vals:
            sum_squares += (val * val)
    return sum_squares

def gammln(xx, high=False):
    """
    From stats.py.  No changes except using option of using Decimals not floats.  
    -------------------------------------
    Returns the gamma function of xx.
        Gamma(z) = Integral(0,infinity) of t^(z-1)exp(-t) dt.
    (Adapted from: Numerical Recipies in C.)
    
    Usage:   gammln(xx)
    """
    if high:
        intone = D("1")
        one = D("1.0")
        fiveptfive = D("5.5")
        xx = util.f2d(xx)
        coeff = [D("76.18009173"), D("-86.50532033"), D("24.01409822"), 
                 D("-1.231739516"), D("0.120858003e-2"), D("-0.536382e-5")]
    else:
        intone = 1
        one = 1.0
        fiveptfive = 5.5
        coeff = [76.18009173, -86.50532033, 24.01409822, 
                 -1.231739516, 0.120858003e-2, -0.536382e-5]
    x = xx - one
    tmp = x + fiveptfive
    if high:
        tmp = tmp - (x + D("0.5")) * util.f2d(math.log(tmp))
    else:
        tmp = tmp - (x + 0.5) * math.log(tmp)
    ser = one
    for j in range(len(coeff)):
        x = x + intone
        ser = ser + coeff[j]/x
    if high:
        gammln = -tmp + util.f2d(math.log(D("2.50662827465")*ser))
    else:
        gammln = -tmp + math.log(2.50662827465*ser)
    return gammln

def betacf(a, b, x, high=False):
    """
    From stats.py.  No changes.  
    -------------------------------------
    This function evaluates the continued fraction form of the incomplete
    Beta function, betai.  (Adapted from: Numerical Recipies in C.)
    
    Usage:   betacf(a,b,x)
    """
    if high:
        one = D("1")
        ITMAX = D("200")
        EPS = D("3.0e-7")
        a = util.f2d(a)
        b = util.f2d(b)
        x = util.f2d(x)
        bm = az = am = one
        qab = a+b
        qap = a+one
        qam = a-one
        bz = one-qab*x/qap
    else:
        one = 1.0
        ITMAX = 200
        EPS = 3.0e-7
        bm = az = am = one
        qab = a+b
        qap = a+one
        qam = a-one
        bz = one-qab*x/qap
    for i in range(ITMAX+1):
        if high:
            i = util.f2d(i)
        em = i + one
        tem = em + em
        d = em*(b-em)*x/((qam+tem)*(a+tem))
        ap = az + d*am
        bp = bz+d*bm
        d = -(a+em)*(qab+em)*x/((qap+tem)*(a+tem))
        app = ap+d*az
        bpp = bp+d*bz
        aold = az
        am = ap/bpp
        bm = bp/bpp
        az = app/bpp
        bz = one
        if (abs(az-aold)<(EPS*abs(az))):
            return az
    print('a or b too big, or ITMAX too small in Betacf.')

def summult (list1, list2):
    """
    From pstat.py.  No changes (apart from calling abut in existing module
        instead of pstat).
    Multiplies elements in list1 and list2, element by element, and
    returns the sum of all resulting multiplications.  Must provide equal
    length lists.

    Usage:   summult(list1,list2)
    """
    if len(list1) <> len(list2):
        raise ValueError, "Lists not equal length in summult."
    s = 0
    for item1,item2 in abut(list1,list2):
        s = s + item1*item2
    return s

def abut (source, *args):
    """
    From pstat.py.  No changes.  
    -------------------------------------
    Like the |Stat abut command.  It concatenates two lists side-by-side
    and returns the result.  '2D' lists are also accomodated for either argument
    (source or addon).  CAUTION:  If one list is shorter, it will be repeated
    until it is as long as the longest list.  If this behavior is not desired,
    use pstat.simpleabut().
    
    Usage:   abut(source, args)   where args=any # of lists
    Returns: a list of lists as long as the LONGEST list past, source on the
             'left', lists in <args> attached consecutively on the 'right'
    """

    if type(source) not in [ListType,TupleType]:
        source = [source]
    for addon in args:
        if type(addon) not in [ListType,TupleType]:
            addon = [addon]
        if len(addon) < len(source):                # is source list longer?
            if len(source) % len(addon) == 0:        # are they integer multiples?
                repeats = len(source)/len(addon)    # repeat addon n times
                origadd = copy.deepcopy(addon)
                for i in range(repeats-1):
                    addon = addon + origadd
            else:
                repeats = len(source)/len(addon)+1  # repeat addon x times,
                origadd = copy.deepcopy(addon)      #    x is NOT an integer
                for i in range(repeats-1):
                    addon = addon + origadd
                    addon = addon[0:len(source)]
        elif len(source) < len(addon):                # is addon list longer?
            if len(addon) % len(source) == 0:        # are they integer multiples?
                repeats = len(addon)/len(source)    # repeat source n times
                origsour = copy.deepcopy(source)
                for i in range(repeats-1):
                    source = source + origsour
            else:
                repeats = len(addon)/len(source)+1  # repeat source x times,
                origsour = copy.deepcopy(source)    #   x is NOT an integer
                for i in range(repeats-1):
                    source = source + origsour
                source = source[0:len(addon)]

        source = simpleabut(source,addon)
    return source

def simpleabut (source, addon):
    """
    From pstat.py.  No changes.  
    -------------------------------------
    Concatenates two lists as columns and returns the result.  '2D' lists
    are also accomodated for either argument (source or addon).  This DOES NOT
    repeat either list to make the 2 lists of equal length.  Beware of list
    pairs with different lengths ... the resulting list will be the length of 
    the FIRST list passed.
    
    Usage: simpleabut(source,addon)  where source, addon=list (or list-of-lists)
    Returns: a list of lists as long as source, with source on the 'left' and
                     addon on the 'right'
    """
    if type(source) not in [ListType,TupleType]:
        source = [source]
    if type(addon) not in [ListType,TupleType]:
        addon = [addon]
    minlen = min(len(source),len(addon))
    list = copy.deepcopy(source)                # start abut process
    if type(source[0]) not in [ListType,TupleType]:
        if type(addon[0]) not in [ListType,TupleType]:
            for i in range(minlen):
                list[i] = [source[i]] + [addon[i]]     # source/addon = column
        else:
            for i in range(minlen):
                list[i] = [source[i]] + addon[i]      # addon=list-of-lists
    else:
        if type(addon[0]) not in [ListType,TupleType]:
            for i in range(minlen):
                list[i] = source[i] + [addon[i]]     # source=list-of-lists
        else:
            for i in range(minlen):
                list[i] = source[i] + addon[i]    # source/addon = list-of-lists
    source = list
    return source

def square_of_sums(inlist):
    """
    From stats.py.  No changes.  
    -------------------------------------
    Adds the values in the passed list, squares the sum, and returns
    the result.

    Usage:   square_of_sums(inlist)
    Returns: sum(inlist[i])**2
    """
    s = sum(inlist)
    return float(s)*s

def sumdiffsquared(x,y):
    """
    From stats.py.  No changes.  
    -------------------------------------
    Takes pairwise differences of the values in lists x and y, squares
    these differences, and returns the sum of these squares.

    Usage:   sumdiffsquared(x,y)
    Returns: sum[(x[i]-y[i])**2]
    """
    sds = 0
    for i in range(len(x)):
        sds = sds + (x[i]-y[i])**2
    return sds


def chisqprob(chisq, df):
    """
    From stats.py.  No changes.  
    -------------------------------------
    Returns the (1-tailed) probability value associated with the provided
    chi-square value and df.  Adapted from chisq.c in Gary Perlman's |Stat.

    Usage:   chisqprob(chisq,df)
    """    
    BIG = 20.0
    def ex(x):
        BIG = 20.0
        if x < -BIG:
            return 0.0
        else:
            return math.exp(x)

    if chisq <=0 or df < 1:
        return 1.0
    a = 0.5 * chisq
    if df%2 == 0:
        even = 1
    else:
        even = 0
    if df > 1:
        y = ex(-a)
    if even:
        s = y
    else:
        s = 2.0 * zprob(-math.sqrt(chisq))
    if (df > 2):
        chisq = 0.5 * (df - 1.0)
        if even:
            z = 1.0
        else:
            z = 0.5
        if a > BIG:
            if even:
                e = 0.0
            else:
                e = math.log(math.sqrt(math.pi))
            c = math.log(a)
            while (z <= chisq):
                e = math.log(z) + e
                s = s + ex(c*z-a-e)
                z = z + 1.0
            return s
        else:
            if even:
                e = 1.0
            else:
                e = 1.0 / math.sqrt(math.pi) / math.sqrt(a)
            c = 0.0
            while (z <= chisq):
                e = e * (a/float(z))
                c = c + e
                z = z + 1.0
            return (c*y+s)
    else:
        return s

def fprob (dfnum, dfden, F, high=False):
    """
    From stats.py.  No changes except uses Decimals instead 
        of floats.  
    -------------------------------------
    Returns the (1-tailed) significance level (p-value) of an F
    statistic given the degrees of freedom for the numerator (dfR-dfF) and
    the degrees of freedom for the denominator (dfF).

    Usage:   fprob(dfnum, dfden, F)   where usually dfnum=dfbn, dfden=dfwn
    """
    debug = False
    if high:
        dfnum = util.f2d(dfnum)
        dfden = util.f2d(dfden)
        F = util.f2d(F)
        a = D("0.5")*dfden
        b = D("0.5")*dfnum
        x = dfden/(dfden + dfnum*F)
        if debug:
            print("a: %s" % a)
            print("b: %s" % b)
            print("x: %s" % x)
        p = betai(a, b, x, high)
    else:
        p = betai(0.5*dfden, 0.5*dfnum, dfden/float(dfden+dfnum*F), high)
    return p
