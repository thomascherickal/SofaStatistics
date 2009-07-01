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
