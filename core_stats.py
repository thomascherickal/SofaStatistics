import copy
import math
import numpy as np
from types import ListType, TupleType

import getdata

def get_list(dbe, cur, tbl, fld_measure, fld_filter, filter_val):
    """
    Get list of non-missing values in field.
    Used, for example, in the independent samples t-test.
    """
    quoter = getdata.get_quoter_func(dbe)
    SQL_get_list = "SELECT %s FROM %s WHERE %s IS NOT NULL AND %s = ?" % \
                    (quoter(fld_measure), quoter(tbl), quoter(fld_measure), 
                     quoter(fld_filter))
    cur.execute(SQL_get_list, (filter_val,))
    lst = [x[0] for x in cur.fetchall()]
    return lst

def get_paired_lists(dbe, cur, tbl, fld_a, fld_b):
    """
    For each field, returns a list of all non-missing values where there is also
        a non-missing value in the other field.
        Used in, for example, the paired samples t-test.
    """
    quoter = getdata.get_quoter_func(dbe)
    SQL_get_lists = "SELECT %s, %s " % (quoter(fld_a), quoter(fld_b)) + \
        "FROM %s " % quoter(tbl) + \
        "WHERE %s IS NOT NULL AND %s IS NOT NULL" % (quoter(fld_a), 
                                                     quoter(fld_b))
    cur.execute(SQL_get_lists)
    data_tups = cur.fetchall()
    lst_a = [x[0] for x in data_tups]
    lst_b = [x[1] for x in data_tups]
    return lst_a, lst_b

def get_obs_exp(dbe, cur, tbl, fld_a, fld_b):
    """
    Get list of observed and expected values ready for inclusion in Pearson's
        Chi Square test.
    Returns lst_obs, lst_exp, min_count, perc_cells_lt_5, df.    
    """
    quoter = getdata.get_quoter_func(dbe)
    qtbl = quoter(tbl)
    qfld_a = quoter(fld_a)
    qfld_b = quoter(fld_b)
    # observed values etc
    SQL_get_obs = "SELECT %s, %s, COUNT(*) " % (qfld_a, qfld_b) + \
        "FROM %s " % qtbl + \
        "WHERE %s IS NOT NULL AND %s IS NOT NULL " % (qfld_a, qfld_b) + \
        "GROUP BY %s, %s " %  (qfld_a, qfld_b) + \
        "ORDER BY %s, %s" % (qfld_a, qfld_b)
    cur.execute(SQL_get_obs)
    data_tups = cur.fetchall()
    if not data_tups:
        raise Exception, "No observed values"
    lst_obs = []
    for data_tup in data_tups:
        lst_obs.append(data_tup[2])
    obs_total = sum(lst_obs)
    # expected values
    lst_fracs_a = get_fracs(cur, qtbl, qfld_a, qfld_b)
    lst_fracs_b = get_fracs(cur, qtbl, qfld_b, qfld_a)
    df = (len(lst_fracs_a)-1)*(len(lst_fracs_b)-1)
    lst_exp = []
    for frac_a in lst_fracs_a:
        for frac_b in lst_fracs_b:
            lst_exp.append(frac_a*frac_b*obs_total)
    min_count = min(lst_exp)
    lst_lt_5 = [x for x in lst_exp if x < 5]
    perc_cells_lt_5 = 100*(len(lst_lt_5))/float(len(lst_exp))
    return lst_obs, lst_exp, min_count, perc_cells_lt_5, df

def get_fracs(cur, qtbl, qfld, qfld_oth):
    """
    What fraction of the cross tab values are for each value in field?
    Leaves out values where data is missing or the other field is missing.
    Returns lst_fracs
    """
    SQL_get_fracs = "SELECT %s, COUNT(*) " % qfld + \
        "FROM %s " % qtbl + \
        """WHERE %s IS NOT NULL
            AND %s IS NOT NULL
        GROUP BY %s
        ORDER BY %s""" % (qfld, qfld_oth, qfld, qfld)    
    cur.execute(SQL_get_fracs)
    lst_counts = []
    total = 0
    for data_tup in cur.fetchall():
        val = data_tup[1]
        lst_counts.append(val)
        total += val
    lst_fracs = [x/float(total) for x in lst_counts]
    return lst_fracs
    
    

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

def pearsons_chisquare(dbe, cur, tbl, fld_a, fld_b):
    """
    Returns chisq, p, min_count, perc_cells_lt_5
    """
    lst_obs, lst_exp, min_count, perc_cells_lt_5, df = \
        get_obs_exp(dbe, cur, tbl, fld_a, fld_b)
    chisq, p = chisquare(lst_obs, lst_exp, df)
    return chisq, p, lst_obs, lst_exp, min_count, perc_cells_lt_5, df

def anova(*lists):
    """
    From stats.py.  No changes except changing name to anova and replacing 
        array versions e.g. amean with list versions e.g. lmean.  
    -------------------------------------
    Performs a 1-way ANOVA, returning an F-value and probability given
    any number of groups.  From Heiman, pp.394-7.

    Usage:   anova(*lists)    where *lists is any number of lists, one per 
        treatment group
    Returns: F value, one-tailed p-value
    """
    a = len(lists)           # ANOVA on 'a' groups, each in its own list
    means = [0]*a
    vars = [0]*a
    ns = [0]*a
    alldata = []
    means = map(mean, lists)
    vars = map(var, lists)
    ns = map(len,lists)
    for i in range(len(lists)):
        alldata = alldata + lists[i]
    bign = len(alldata)
    sstot = ss(alldata)-(square_of_sums(alldata)/float(bign))
    ssbn = 0
    for list in lists:
        ssbn = ssbn + square_of_sums(list)/float(len(list))
    ssbn = ssbn - (square_of_sums(alldata)/float(bign))
    sswn = sstot-ssbn
    dfbn = a-1
    dfwn = bign - a
    msb = ssbn/float(dfbn)
    msw = sswn/float(dfwn)
    f = msb/msw
    prob = fprob(dfbn, dfwn,f)
    return f, prob

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

def ttest_ind(sample_a, sample_b, label_a, label_b):
    """
    From stats.py - there are changes to variable labels and comments;
        and the output is extracted early to give greater control over 
        presentation.  There are no changes to algorithms.
    Returns t, p, dic_a, dic_b (p is the two-tailed probability)
    ---------------------------------------------------------------------
    Calculates the t-obtained T-test on TWO INDEPENDENT samples of
    scores a, and b.  From Numerical Recipes, p.483.
    """
    mean_a = mean(sample_a)
    mean_b = mean(sample_b)
    se_a = stdev(sample_a)**2
    se_b = stdev(sample_b)**2
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
    sd_a = math.sqrt(se_a)
    sd_b = math.sqrt(se_b)
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
    var_a = var(sample_a)
    var_b = var(sample_b)
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

def mannwhitneyu(x,y):
    """
    From stats.py.  No changes.  
    -------------------------------------
    Calculates a Mann-Whitney U statistic on the provided scores and
    returns the result.  Use only when the n in each condition is < 20 and
    you have 2 independent samples of ranks.  NOTE: Mann-Whitney U is
    significant if the u-obtained is LESS THAN or equal to the critical
    value of U found in the tables.  Equivalent to Kruskal-Wallis H with
    just 2 groups.

    Usage:   mannwhitneyu(data)
    Returns: u-statistic, one-tailed p-value (i.e., p(z(U)))
    """
    n1 = len(x)
    n2 = len(y)
    ranked = rankdata(x+y)
    rankx = ranked[0:n1]       # get the x-ranks
    ranky = ranked[n1:]        # the rest are y-ranks
    u1 = n1*n2 + (n1*(n1+1))/2.0 - sum(rankx)  # calc U for x
    u2 = n1*n2 - u1                            # remainder is U for y
    bigu = max(u1,u2)
    smallu = min(u1,u2)
    T = math.sqrt(tiecorrect(ranked))  # correction factor for tied scores
    if T == 0:
        raise ValueError, 'All numbers are identical in lmannwhitneyu'
    sd = math.sqrt(T*n1*n2*(n1+n2+1)/12.0)
    z = abs((bigu-n1*n2/2.0) / sd)  # normal approximation for prob calc
    return smallu, 1.0 - zprob(z)


def wilcoxont(x,y):
    """
    From stats.py.
    -------------------------------------
    Calculates the Wilcoxon T-test for related samples and returns the
    result.  A non-parametric T-test.

    Usage:   wilcoxont(x,y)
    Returns: a t-statistic, two-tail probability estimate, z
    """
    if len(x) <> len(y):
        raise ValueError, 'Unequal N in wilcoxont.  Aborting.'
    d=[]
    for i in range(len(x)):
        diff = x[i] - y[i]
        if diff <> 0:
            d.append(diff)
    count = len(d)
    absd = map(abs,d)
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
    From stats.py.  No changes.  
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
    x = map(float,x)
    y = map(float,y)
    xmean = mean(x)
    ymean = mean(y)
    r_num = n*(summult(x,y)) - sum(x)*sum(y)
    r_den = math.sqrt((n*ss(x) - square_of_sums(x))*(n*ss(y)-square_of_sums(y)))
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

def mean (inlist):
    """
    From stats.py.  No changes.  
    -------------------------------------
    Returns the arithematic mean of the values in the passed list.
    Assumes a '1D' list, but will function on the 1st dim of an array(!).
    
    Usage:   mean(inlist)
    """
    sum = 0
    for item in inlist:
        sum = sum + item
    return sum/float(len(inlist))

def var (inlist):
    """
    From stats.py.  No changes.  
    -------------------------------------
    Returns the variance of the values in the passed list using N-1
    for the denominator (i.e., for estimating population variance).
    
    Usage:   var(inlist)
    """
    n = len(inlist)
    mn = mean(inlist)
    deviations = [0]*len(inlist)
    for i in range(len(inlist)):
        deviations[i] = inlist[i] - mn
    return ss(deviations)/float(n-1)

def stdev (inlist):
    """
    From stats.py.  No changes.  
    -------------------------------------
    Returns the standard deviation of the values in the passed list
    using N-1 in the denominator (i.e., to estimate population stdev).
    
    Usage:   stdev(inlist)
    """
    return math.sqrt(var(inlist))

def betai(a, b, x):
    """
    From stats.py.  No changes.  
    -------------------------------------
    Returns the incomplete beta function:
    
        I-sub-x(a,b) = 1/B(a,b)*(Integral(0,x) of t^(a-1)(1-t)^(b-1) dt)
    
    where a,b>0 and B(a,b) = G(a)*G(b)/(G(a+b)) where G(a) is the gamma
    function of a.  The continued fraction formulation is implemented here,
    using the betacf function.  (Adapted from: Numerical Recipies in C.)
    
    Usage:   betai(a,b,x)
    """
    if (x<0.0 or x>1.0):
        raise ValueError, 'Bad x in lbetai'
    if (x==0.0 or x==1.0):
        bt = 0.0
    else:
        bt = math.exp(gammln(a+b)-gammln(a)-gammln(b)+a*math.log(x)+b*
                      math.log(1.0-x))
    if (x<(a+1.0)/(a+b+2.0)):
        return bt*betacf(a,b,x)/float(a)
    else:
        return 1.0-bt*betacf(b,a,1.0-x)/float(b)

def ss(inlist):
    """
    From stats.py.  No changes.  
    -------------------------------------
    Squares each value in the passed list, adds up these squares and
    returns the result.
    
    Usage:   ss(inlist)
    """
    ss = 0
    for item in inlist:
        ss = ss + item*item
    return ss

def gammln(xx):
    """
    From stats.py.  No changes.  
    -------------------------------------
    Returns the gamma function of xx.
        Gamma(z) = Integral(0,infinity) of t^(z-1)exp(-t) dt.
    (Adapted from: Numerical Recipies in C.)
    
    Usage:   gammln(xx)
    """
    coeff = [76.18009173, -86.50532033, 24.01409822, -1.231739516,
             0.120858003e-2, -0.536382e-5]
    x = xx - 1.0
    tmp = x + 5.5
    tmp = tmp - (x+0.5)*math.log(tmp)
    ser = 1.0
    for j in range(len(coeff)):
        x = x + 1
        ser = ser + coeff[j]/x
    return -tmp + math.log(2.50662827465*ser)


def betacf(a, b, x):
    """
    From stats.py.  No changes.  
    -------------------------------------
    This function evaluates the continued fraction form of the incomplete
    Beta function, betai.  (Adapted from: Numerical Recipies in C.)
    
    Usage:   betacf(a,b,x)
    """
    ITMAX = 200
    EPS = 3.0e-7

    bm = az = am = 1.0
    qab = a+b
    qap = a+1.0
    qam = a-1.0
    bz = 1.0-qab*x/qap
    for i in range(ITMAX+1):
        em = float(i+1)
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
        bz = 1.0
        if (abs(az-aold)<(EPS*abs(az))):
            return az
    print 'a or b too big, or ITMAX too small in Betacf.'

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

def fprob (dfnum, dfden, F):
    """
    From stats.py.  No changes.  
    -------------------------------------
    Returns the (1-tailed) significance level (p-value) of an F
    statistic given the degrees of freedom for the numerator (dfR-dfF) and
    the degrees of freedom for the denominator (dfF).

    Usage:   fprob(dfnum, dfden, F)   where usually dfnum=dfbn, dfden=dfwn
    """
    p = betai(0.5*dfden, 0.5*dfnum, dfden/float(dfden+dfnum*F))
    return p
