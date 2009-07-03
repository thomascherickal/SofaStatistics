import copy
import math

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

def get_paired_lists(dbe, cur, tbl, fld_measure_a, fld_measure_b):
    """
    For each field, returns a list of all non-missing values where there is also
        a non-missing value in the other field.
        Used in, for example, the paired samples t-test.
    """
    quoter = getdata.get_quoter_func(dbe)
    SQL_get_lists = "SELECT %s, %s " % (quoter(fld_measure_a), 
                                        quoter(fld_measure_b)) + \
        "FROM %s " % quoter(tbl) + \
        "WHERE %s IS NOT NULL AND %s IS NOT NULL" % (quoter(fld_measure_a), 
                                                     quoter(fld_measure_b))
    cur.execute(SQL_get_lists)
    data_tups = cur.fetchall()
    lst_a = [x[0] for x in data_tups]
    lst_b = [x[1] for x in data_tups]
    return lst_a, lst_b


# code below here is modified versions of code in stats.py and pstats.py

# Copyright notice for stats and pstats.

# Functions taken from stats.py have their origin indicated in their doc string

# Copyright (c) 1999-2007 Gary Strangman; All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# Comments and/or additions are welcome (send e-mail to:
# strang@nmr.mgh.harvard.edu).
# 

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
    Calculates the Wilcoxon T-test for related samples and returns the
    result.  A non-parametric T-test.

    Usage:   wilcoxont(x,y)
    Returns: a t-statistic, two-tail probability estimate
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
    Returns the standard deviation of the values in the passed list
    using N-1 in the denominator (i.e., to estimate population stdev).
    
    Usage:   stdev(inlist)
    """
    return math.sqrt(var(inlist))

def betai(a, b, x):
    """
    From stats.py.  No changes.
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


def betacf(a,b,x):
    """
    From stats.py.  No changes.
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
