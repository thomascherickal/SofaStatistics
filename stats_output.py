import cgi

import my_globals

def ttest_output(t, p, dic_a, dic_b, label_avg="", dp=3, indep=True,
                 level=my_globals.OUTPUT_RESULTS_ONLY, css_idx=0, 
                 page_break_after=False):
    """
    Returns HTML table ready to display.
    dic_a = {"label": label_a, "n": n_a, "mean": mean_a, "sd": sd_a, 
             "min": min_a, "max": max_a}
    """
    CSS_FIRST_COL_VAR = my_globals.CSS_SUFFIX_TEMPLATE % \
        (my_globals.CSS_FIRST_COL_VAR, css_idx)
    CSS_PAGE_BREAK_BEFORE = my_globals.CSS_SUFFIX_TEMPLATE % \
        (my_globals.CSS_PAGE_BREAK_BEFORE, css_idx)
    CSS_LBL = my_globals.CSS_SUFFIX_TEMPLATE % \
        (my_globals.CSS_LBL, css_idx)
    if indep:
        html = _("<h2>Results of Independent Samples t-test "
            "of average \"%(avg)s\" for \"%(a)s\" vs \"%(b)s\"</h2>") % \
            {"avg": label_avg, "a": dic_a["label"], "b": dic_b["label"]}
    else:
        html = _("<h2>Results of Paired Samples t-test "
            "of \"%(a)s\" vs \"%(b)s\"</h2>") % {"a": dic_a["label"], "b": 
                                                 dic_b["label"]}
    p_format = u"\n<p>" + _("p value") + u": %%.%sf</p>" % dp
    html += p_format % round(p, dp)
    html += u"\n<p>" + _("t statistic") + u": %s</p>" % round(t, dp)
    html += u"\n\n<table>\n<thead>"
    html += u"\n<tr>" + \
        u"<th class='%s'>" % CSS_FIRST_COL_VAR + _("Group") + u"</th>" + \
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("N") + u"</th>" + \
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Mean") + u"</th>" + \
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Standard Deviation") + \
            u"</th>" + \
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Min") + u"</th>" + \
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Max") + u"</th></tr>"
    html += u"\n</thead>\n<tbody>"
    row_tpl = u"\n<tr><td class='%s'>" % CSS_LBL + u"%s</td><td>%s</td>" + \
        u"<td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
    for dic in [dic_a, dic_b]:
        html += row_tpl % (dic["label"], dic["n"], round(dic["mean"], dp), 
                           round(dic["sd"], dp), 
                           dic["min"], dic["max"])
    html += u"\n</tbody>\n</table>\n"
    if page_break_after:
        html += u"<br><hr><br><div class='%s'></div>" % CSS_PAGE_BREAK_BEFORE
    return html

def mann_whitney_output(u, p, dic_a, dic_b, label_ranked, dp=3,
                 level=my_globals.OUTPUT_RESULTS_ONLY, css_idx=0, 
                 page_break_after=False):
    CSS_FIRST_COL_VAR = my_globals.CSS_SUFFIX_TEMPLATE % \
        (my_globals.CSS_FIRST_COL_VAR, css_idx)
    CSS_PAGE_BREAK_BEFORE = my_globals.CSS_SUFFIX_TEMPLATE % \
        (my_globals.CSS_PAGE_BREAK_BEFORE, css_idx)
    CSS_LBL = my_globals.CSS_SUFFIX_TEMPLATE % \
        (my_globals.CSS_LBL, css_idx)
    html = _("<h2>Results of Mann Whitney U Test of \"%(ranked)s\" for "
             "\"%(a)s\" vs \"%(b)s\"</h2>") % {"ranked": label_ranked, 
                                               "a": dic_a["label"], 
                                               "b": dic_b["label"]}
    p_format = u"\n<p>" + _("p value") + u": %%.%sf</p>" % dp
    html += p_format % round(p, dp)
    html += u"\n<p>" + _("U statistic") + u": %s</p>" % round(u, dp)
    html += u"\n\n<table>\n<thead>"
    html += u"\n<tr>" + \
        u"<th class='%s'>" % CSS_FIRST_COL_VAR + _("Group") + u"</th>" + \
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("N") + u"</th>" + \
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Avg Rank") + u"</th>" + \
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Min") + u"</th>" + \
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Max") + u"</th></tr>"
    html += u"\n</thead>\n<tbody>"
    row_tpl = u"\n<tr><td class='%s'>" % CSS_LBL + u"%s</td><td>%s</td>" + \
        u"<td>%s</td><td>%s</td><td>%s</td></tr>"
    for dic in [dic_a, dic_b]:
        html += row_tpl % (dic["label"], dic["n"], round(dic["avg rank"], dp),
                           dic["min"], dic["max"])
    html += u"\n</tbody>\n</table>\n"
    if page_break_after:
        html += u"<br><hr><br><div class='%s'></div>" % CSS_PAGE_BREAK_BEFORE
    return html

def wilcoxon_output(t, p, label_a, label_b, dp=3,
                 level=my_globals.OUTPUT_RESULTS_ONLY, css_idx=0, 
                 page_break_after=False):
    CSS_PAGE_BREAK_BEFORE = my_globals.CSS_SUFFIX_TEMPLATE % \
        (my_globals.CSS_PAGE_BREAK_BEFORE, css_idx)
    html = _("<h2>Results of Wilcoxon Signed Ranks Test of \"%(a)s\" vs "
             "\"%(b)s\"</h2>") % {"a": label_a, "b": label_b}
    p_format = u"\n<p>p value: %%.%sf</p>" % dp
    html += p_format % round(p, dp)
    html += u"\n<p>" + _("Wilcoxon Signed Ranks statistic") + u": %s</p>" % \
        round(t, dp)
    if page_break_after:
        html += u"<br><hr><br><div class='%s'></div>" % CSS_PAGE_BREAK_BEFORE
    return html

def pearsonsr_output(r, p, label_a, label_b, dp=3,
                 level=my_globals.OUTPUT_RESULTS_ONLY, css_idx=0, 
                 page_break_after=False):
    CSS_PAGE_BREAK_BEFORE = my_globals.CSS_SUFFIX_TEMPLATE % \
        (my_globals.CSS_PAGE_BREAK_BEFORE, css_idx)
    html = _("<h2>Results of Pearson's Test of Linear Correlation for \"%(a)s\""
             " and \"%(b)s\"</h2>") % {"a": label_a, "b": label_b}
    p_format = u"\n<p>" + _("p value") + u": %%.%sf</p>" % dp
    html += p_format % round(p, dp)
    html += u"\n<p>" + _("Pearson's R statistic") + u": %s</p>" % round(r, dp)
    if page_break_after:
        html += u"<br><hr><br><div class='%s'></div>" % CSS_PAGE_BREAK_BEFORE
    return html

def spearmansr_output(r, p, label_a, label_b, dp=3,
                 level=my_globals.OUTPUT_RESULTS_ONLY, css_idx=0, 
                 page_break_after=False):
    CSS_PAGE_BREAK_BEFORE = my_globals.CSS_SUFFIX_TEMPLATE % \
        (my_globals.CSS_PAGE_BREAK_BEFORE, css_idx)
    html = _("<h2>Results of Spearman's Test of Linear Correlation for "
             "\"%(a)s\" and \"%(b)s\"</h2>") % {"a": label_a, "b": label_b}
    p_format = u"\n<p>" + _("p value") + u": %%.%sf</p>" % dp
    html += p_format % round(p, dp)
    html += u"\n<p>" + _("Spearman's R statistic") + u": %s</p>" % round(r, dp)
    if page_break_after:
        html += u"<br><hr><br><div class='%s'></div>" % CSS_PAGE_BREAK_BEFORE
    return html

def chisquare_output(chi, p, var_label_a, var_label_b, 
                     val_labels_a, val_labels_b, lst_obs, lst_exp, min_count, 
                     perc_cells_lt_5, df, dp=3, 
                     level=my_globals.OUTPUT_RESULTS_ONLY, css_idx=0, 
                     page_break_after=False):
    CSS_SPACEHOLDER = my_globals.CSS_SUFFIX_TEMPLATE % \
        (my_globals.CSS_SPACEHOLDER, css_idx)
    CSS_FIRST_COL_VAR = my_globals.CSS_SUFFIX_TEMPLATE % \
        (my_globals.CSS_FIRST_COL_VAR, css_idx)
    CSS_FIRST_ROW_VAR = my_globals.CSS_SUFFIX_TEMPLATE % \
        (my_globals.CSS_FIRST_ROW_VAR, css_idx)
    CSS_ROW_VAL = my_globals.CSS_SUFFIX_TEMPLATE % \
        (my_globals.CSS_ROW_VAL, css_idx)
    CSS_DATACELL = my_globals.CSS_SUFFIX_TEMPLATE % \
        (my_globals.CSS_DATACELL, css_idx)
    CSS_PAGE_BREAK_BEFORE = my_globals.CSS_SUFFIX_TEMPLATE % \
        (my_globals.CSS_PAGE_BREAK_BEFORE, css_idx)
    var_label_a = cgi.escape(var_label_a)
    var_label_b = cgi.escape(var_label_b)
    try:
        val_labels_a = map(cgi.escape, val_labels_a)
        val_labels_b = map(cgi.escape, val_labels_b)
    except AttributeError:
        pass # e.g. an int
    cells_per_col = 2
    val_labels_a_n = len(val_labels_a)
    val_labels_b_n = len(val_labels_b)
    html = _("<h2>Results of Pearson's Chi Square Test of Association Between"
             " \"%(laba)s\" and \"%(labb)s\"</h2>") % {"laba": var_label_a, 
                                                       "labb": var_label_b}
    p_format = u"\n<p>" + _("p value") + u": %%.%sf</p>" % dp
    html += p_format % round(p, dp)
    html += u"\n<p>" + _("Pearson's Chi Square statistic") + u": %s</p>" % \
        round(chi, dp)
    html += u"\n<p>" + _("Degrees of Freedom (df)") + u": %s</p>" % df
    # headings
    html += u"\n\n<table>\n<thead>"
    html += u"\n<tr><th class='%s' colspan=2 rowspan=3></th>" % CSS_SPACEHOLDER
    html += u"<th class='%s' " % CSS_FIRST_COL_VAR + \
        u"colspan=%s>%s</th></tr>" % ((val_labels_b_n+1)*cells_per_col, 
                                      var_label_b)
    html += u"\n<tr>"
    for val in val_labels_b:
        html += u"<th colspan=%s>%s</th>" % (cells_per_col, val)
    html += u"<th colspan=%s>" % cells_per_col + _("TOTAL") + \
        u"</th></tr>\n<tr>"
    for i in range(val_labels_b_n + 1):
        html += u"<th>" + _("Obs") + u"</th><th>" + _("Exp") + u"</th>"
    html += u"</tr>"
    # body
    html += u"\n\n</thead><tbody>"
    item_i = 0
    html += u"\n<tr><td class='%s' rowspan=%s>%s</td>" % \
        (CSS_FIRST_ROW_VAR, val_labels_a_n + 1, var_label_a)
    col_obs_tots = [0]*val_labels_b_n
    col_exp_tots = [0]*val_labels_b_n
    # total row totals
    row_obs_tot_tot = 0 
    row_exp_tot_tot = 0
    for row_i, val_a in enumerate(val_labels_a):
        row_obs_tot = 0
        row_exp_tot = 0
        html += u"<td class='%s'>%s</td>" % (CSS_ROW_VAL, val_a)        
        for col_i, val_b in enumerate(val_labels_b):
            obs = lst_obs[item_i]
            exp = lst_exp[item_i]
            html += u"<td class='%s'>" % CSS_DATACELL + \
                u"%s</td><td class='%s'>%s</td>" % (obs, CSS_DATACELL, 
                                                    round(exp, 1))
            row_obs_tot += obs
            row_exp_tot += exp
            col_obs_tots[col_i] += obs
            col_exp_tots[col_i] += exp
            item_i += 1
        # add total for row
        row_obs_tot_tot += row_obs_tot
        row_exp_tot_tot += row_exp_tot
        html += u"<td class='%s'>" % CSS_DATACELL + \
            u"%s</td><td class='%s'>%s</td>" % (row_obs_tot, CSS_DATACELL, 
                                                round(row_exp_tot,1))
        html += u"</tr>\n<tr>"
    # add totals row
    col_tots = zip(col_obs_tots, col_exp_tots)
    html += u"<td class='%s'>" % CSS_ROW_VAL + _("TOTAL") + u"</td>"
    for col_obs_tot, col_exp_tot in col_tots:
        html += u"<td class='%s'>" % CSS_DATACELL + \
            u"%s</td><td class='%s'>%s</td>" % (col_obs_tot, CSS_DATACELL,
                                                round(col_exp_tot, 1))
    # add total of totals
    html += u"<td class='%s'>" % CSS_DATACELL + \
        u"%s</td><td class='%s'>%s</td>" % (row_obs_tot_tot, 
                                            CSS_DATACELL, 
                                            round(row_exp_tot_tot,1))
    html += u"</tr>"
    html += u"\n</tbody>\n</table>\n"
    # warnings
    html += u"\n<p>" + _("Minimum expected cell count") + u": %s</p>" % \
        round(min_count, dp)
    html += u"\n<p>% " + _("cells with expected count < 5") + u": %s</p>" % \
        round(perc_cells_lt_5, 1)
    if page_break_after:
        html += u"<br><hr><br><div class='%s'></div>" % CSS_PAGE_BREAK_BEFORE
    return html

def kruskal_wallis_output(h, p, label_a, label_b, label_avg, dp=3,
                 level=my_globals.OUTPUT_RESULTS_ONLY, css_idx=0, 
                 page_break_after=False):
    CSS_PAGE_BREAK_BEFORE = my_globals.CSS_SUFFIX_TEMPLATE % \
        (my_globals.CSS_PAGE_BREAK_BEFORE, css_idx) 
    html = _("<h2>Results of Kruskal-Wallis H test of average %(avg)s for "
             "groups from \"%(a)s\" to \"%(b)s\"</h2>") % {"avg": label_avg, 
                                                "a": label_a, "b": label_b}
    p_format = "\n<p>" + _("p value") + ": %%.%sf</p>" % dp
    html += p_format % round(p, dp)
    html += "\n<p>" + _("Kruskal-Wallis H statistic") + ": %s</p>" % \
        round(h, dp)
    if page_break_after:
        html += "<br><hr><br><div class='%s'></div>" % CSS_PAGE_BREAK_BEFORE
    return html

def anova_output(F, p, dics, sswn, dfwn, mean_squ_wn, ssbn, dfbn, 
                 mean_squ_bn, label_a, label_b, label_avg, dp=3,
                 level=my_globals.OUTPUT_RESULTS_ONLY, css_idx=0, 
                 page_break_after=False):
    CSS_FIRST_COL_VAR = my_globals.CSS_SUFFIX_TEMPLATE % \
        (my_globals.CSS_FIRST_COL_VAR, css_idx)
    CSS_PAGE_BREAK_BEFORE = my_globals.CSS_SUFFIX_TEMPLATE % \
        (my_globals.CSS_PAGE_BREAK_BEFORE, css_idx)
    CSS_LBL = my_globals.CSS_SUFFIX_TEMPLATE % \
        (my_globals.CSS_LBL, css_idx)
    html = _("<h2>Results of ANOVA test of average %(avg)s for groups from"
             " \"%(a)s\" to \"%(b)s\"</h2>") % {"avg": label_avg, "a": label_a, 
                                                "b": label_b}
    html += u"\n\n<h3>" + _("Analysis of variance table") + u"</h3>"
    html += u"\n<table>\n<thead>"
    html += u"\n<tr>" + \
        u"<th class='%s'>" % CSS_FIRST_COL_VAR + _("Source") + u"</th>" + \
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Sum of Squares") + \
            u"</th>" + \
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("df") + u"</th>" + \
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Mean Sum of Squares") + \
            u"</th>" + \
        u"\n<th class='%s'>F</th>" % CSS_FIRST_COL_VAR + \
        u"\n<th class='%s'>p</th></tr>" % CSS_FIRST_COL_VAR
    html += u"\n</thead>\n<tbody>"
    html += u"\n<tr><td>" + _("Between") + \
        u"</td><td>%s</td><td>%s</td>" % (round(ssbn, dp), dfbn)
    html += u"<td>%s</td><td>%s</td><td>%s</td></tr>" % (round(mean_squ_bn, dp), 
                                                     round(F, dp), round(p, dp))
    html += u"\n<tr><td>" + _("Within") + \
        u"</td><td>%s</td><td>%s</td>" % (round(sswn, dp), dfwn)
    html += u"<td>%s</td><td></td><td></td></tr>" % round(mean_squ_wn, dp)
    html += u"\n</tbody>\n</table>\n"
    html += u"\n\n<h3>" + _("Group summary details") + u"</h3>"
    html += u"\n<table>\n<thead>"
    html += u"\n<tr><th class='%s'>" % CSS_FIRST_COL_VAR + _("Group") + \
            u"</th>" + \
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("N") + u"</th>" + \
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Mean") + u"</th>" + \
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Standard Deviation") + \
            u"</th>" + \
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Min") + u"</th>" + \
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Max") + u"</th></tr>"
    html += u"\n</thead>\n<tbody>"
    row_tpl = (u"\n<tr><td class='%s'>" % CSS_LBL + \
               u"%s</td><td>%s</td><td>%s</td>"
               u"<td>%s</td><td>%s</td><td>%s</td></tr>")
    for dic in dics:
        html += row_tpl % (dic["label"], dic["n"], round(dic["mean"], dp), 
                           round(dic["sd"], dp), dic["min"], dic["max"])
    html += u"\n</tbody>\n</table>\n"
    if page_break_after:
        html += u"<br><hr><br><div class='%s'></div>" % CSS_PAGE_BREAK_BEFORE
    return html
