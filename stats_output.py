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
    p_format = "\n<p>" + _("p value") + ": %%.%sf</p>" % dp
    html += p_format % round(p, dp)
    html += "\n<p>" + _("t statistic") + ": %s</p>" % round(t, dp)
    html += "\n\n<table>\n<thead>"
    html += "\n<tr>" + \
        "<th class='%s'>" % CSS_FIRST_COL_VAR + _("Group") + "</th>" + \
        "\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("N") + "</th>" + \
        "\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Mean") + "</th>" + \
        "\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Standard Deviation") + \
            "</th>" + \
        "\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Min") + "</th>" + \
        "\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Max") + "</th></tr>"
    html += "\n</thead>\n<tbody>"
    row_tpl = "\n<tr><td class='%s'>" % CSS_LBL + "%s</td><td>%s</td>" + \
        "<td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
    for dic in [dic_a, dic_b]:
        html += row_tpl % (dic["label"], dic["n"], round(dic["mean"], dp), 
                           round(dic["sd"], dp), 
                           dic["min"], dic["max"])
    html += "\n</tbody>\n</table>\n"
    if page_break_after:
        html += "<br><hr><br><div class='%s'></div>" % CSS_PAGE_BREAK_BEFORE
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
    p_format = "\n<p>" + _("p value") + ": %%.%sf</p>" % dp
    html += p_format % round(p, dp)
    html += "\n<p>" + _("U statistic") + ": %s</p>" % round(u, dp)
    html += "\n\n<table>\n<thead>"
    html += "\n<tr>" + \
        "<th class='%s'>" % CSS_FIRST_COL_VAR + _("Group") + "</th>" + \
        "\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("N") + "</th>" + \
        "\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Avg Rank") + "</th>" + \
        "\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Min") + "</th>" + \
        "\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Max") + "</th></tr>"
    html += "\n</thead>\n<tbody>"
    row_tpl = "\n<tr><td class='%s'>" % CSS_LBL + "%s</td><td>%s</td>" + \
        "<td>%s</td><td>%s</td><td>%s</td></tr>"
    for dic in [dic_a, dic_b]:
        html += row_tpl % (dic["label"], dic["n"], round(dic["avg rank"], dp),
                           dic["min"], dic["max"])
    html += "\n</tbody>\n</table>\n"
    if page_break_after:
        html += "<br><hr><br><div class='%s'></div>" % CSS_PAGE_BREAK_BEFORE
    return html

def wilcoxon_output(t, p, label_a, label_b, dp=3,
                 level=my_globals.OUTPUT_RESULTS_ONLY, css_idx=0, 
                 page_break_after=False):
    CSS_PAGE_BREAK_BEFORE = my_globals.CSS_SUFFIX_TEMPLATE % \
        (my_globals.CSS_PAGE_BREAK_BEFORE, css_idx)
    html = _("<h2>Results of Wilcoxon Signed Ranks Test of \"%(a)s\" vs "
             "\"%(b)s\"</h2>") % {"a": label_a, "b": label_b}
    p_format = "\n<p>p value: %%.%sf</p>" % dp
    html += p_format % round(p, dp)
    html += "\n<p>" + _("Wilcoxon Signed Ranks statistic") + ": %s</p>" % \
        round(t, dp)
    if page_break_after:
        html += "<br><hr><br><div class='%s'></div>" % CSS_PAGE_BREAK_BEFORE
    return html

def pearsonsr_output(r, p, label_a, label_b, dp=3,
                 level=my_globals.OUTPUT_RESULTS_ONLY, css_idx=0, 
                 page_break_after=False):
    CSS_PAGE_BREAK_BEFORE = my_globals.CSS_SUFFIX_TEMPLATE % \
        (my_globals.CSS_PAGE_BREAK_BEFORE, css_idx)
    html = _("<h2>Results of Pearson's Test of Linear Correlation for \"%(a)s\""
             " and \"%(b)s\"</h2>") % {"a": label_a, "b": label_b}
    p_format = "\n<p>" + _("p value") + ": %%.%sf</p>" % dp
    html += p_format % round(p, dp)
    html += "\n<p>" + _("Pearson's R statistic") + ": %s</p>" % round(r, dp)
    if page_break_after:
        html += "<br><hr><br><div class='%s'></div>" % CSS_PAGE_BREAK_BEFORE
    return html

def spearmansr_output(r, p, label_a, label_b, dp=3,
                 level=my_globals.OUTPUT_RESULTS_ONLY, css_idx=0, 
                 page_break_after=False):
    CSS_PAGE_BREAK_BEFORE = my_globals.CSS_SUFFIX_TEMPLATE % \
        (my_globals.CSS_PAGE_BREAK_BEFORE, css_idx)
    html = _("<h2>Results of Spearman's Test of Linear Correlation for "
             "\"%(a)s\" and \"%(b)s\"</h2>") % {"a": label_a, "b": label_b}
    p_format = "\n<p>" + _("p value") + ": %%.%sf</p>" % dp
    html += p_format % round(p, dp)
    html += "\n<p>" + _("Spearman's R statistic") + ": %s</p>" % round(r, dp)
    if page_break_after:
        html += "<br><hr><br><div class='%s'></div>" % CSS_PAGE_BREAK_BEFORE
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
    val_labels_a = map(cgi.escape, val_labels_a)
    val_labels_b = map(cgi.escape, val_labels_b)
    cells_per_col = 2
    val_labels_a_n = len(val_labels_a)
    val_labels_b_n = len(val_labels_b)
    html = _("<h2>Results of Pearson's Chi Square Test of Association Between"
             " \"%(laba)s\" and \"%(labb)s\"</h2>") % {"laba": var_label_a, 
                                                       "labb": var_label_b}
    p_format = "\n<p>" + _("p value") + ": %%.%sf</p>" % dp
    html += p_format % round(p, dp)
    html += "\n<p>" + _("Pearson's Chi Square statistic") + ": %s</p>" % \
        round(chi, dp)
    html += "\n<p>" + _("Degrees of Freedom (df)") + ": %s</p>" % df
    # headings
    html += "\n\n<table>\n<thead>"
    html += "\n<tr><th class='%s' colspan=2 rowspan=3></th>" % CSS_SPACEHOLDER
    html += "<th class='%s' " % CSS_FIRST_COL_VAR + \
        "colspan=%s>%s</th></tr>" % ((val_labels_b_n+1)*cells_per_col, 
                                     var_label_b)
    html += "\n<tr>"
    for val in val_labels_b:
        html += "<th colspan=%s>%s</th>" % (cells_per_col, val)
    html += "<th colspan=%s>" % cells_per_col + _("TOTAL") + "</th></tr>\n<tr>"
    for i in range(val_labels_b_n + 1):
        html += "<th>" + _("Obs") + "</th><th>" + _("Exp") + "</th>"
    html += "</tr>"
    # body
    html += "\n\n</thead><tbody>"
    item_i = 0
    html += "\n<tr><td class='%s' rowspan=%s>%s</td>" % \
        (CSS_FIRST_ROW_VAR, val_labels_a_n + 1, var_label_a)
    col_obs_tots = [0]*val_labels_b_n
    col_exp_tots = [0]*val_labels_b_n
    # total row totals
    row_obs_tot_tot = 0 
    row_exp_tot_tot = 0
    for row_i, val_a in enumerate(val_labels_a):
        row_obs_tot = 0
        row_exp_tot = 0
        html += "<td class='%s'>%s</td>" % (CSS_ROW_VAL, val_a)        
        for col_i, val_b in enumerate(val_labels_b):
            obs = lst_obs[item_i]
            exp = lst_exp[item_i]
            html += "<td class='%s'>" % CSS_DATACELL + \
                "%s</td><td class='%s'>%s</td>" % (obs, CSS_DATACELL, 
                                                   round(exp, 1))
            row_obs_tot += obs
            row_exp_tot += exp
            col_obs_tots[col_i] += obs
            col_exp_tots[col_i] += exp
            item_i += 1
        # add total for row
        row_obs_tot_tot += row_obs_tot
        row_exp_tot_tot += row_exp_tot
        html += "<td class='%s'>" % CSS_DATACELL + \
            "%s</td><td class='%s'>%s</td>" % (row_obs_tot, CSS_DATACELL, 
                                               round(row_exp_tot,1))
        html += "</tr>\n<tr>"
    # add totals row
    col_tots = zip(col_obs_tots, col_exp_tots)
    html += "<td class='%s'>" % CSS_ROW_VAL + _("TOTAL") + "</td>"
    for col_obs_tot, col_exp_tot in col_tots:
        html += "<td class='%s'>" % CSS_DATACELL + \
        "%s</td><td class='%s'>%s</td>" % (col_obs_tot, CSS_DATACELL,
                                           round(col_exp_tot, 1))
    # add total of totals
    html += "<td class='%s'>" % CSS_DATACELL + \
        "%s</td><td class='%s'>%s</td>" % (row_obs_tot_tot, 
                                           CSS_DATACELL, 
                                           round(row_exp_tot_tot,1))
    html += "</tr>"
    html += "\n</tbody>\n</table>\n"
    # warnings
    html += "\n<p>" + _("Minimum expected cell count") + ": %s</p>" % \
        round(min_count, dp)
    html += "\n<p>% " + _("cells with expected count < 5") + ": %s</p>" % \
        round(perc_cells_lt_5, 1)
    if page_break_after:
        html += "<br><hr><br><div class='%s'></div>" % CSS_PAGE_BREAK_BEFORE
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
    html += "\n\n<h3>" + _("Analysis of variance table") + "</h3>"
    html += "\n<table>\n<thead>"
    html += "\n<tr>" + \
        "<th class='%s'>" % CSS_FIRST_COL_VAR + _("Source") + "</th>" + \
        "\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Sum of Squares") + \
            "</th>" + \
        "\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("df") + "</th>" + \
        "\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Mean Sum of Squares") + \
            "</th>" + \
        "\n<th class='%s'>F</th>" % CSS_FIRST_COL_VAR + \
        "\n<th class='%s'>p</th></tr>" % CSS_FIRST_COL_VAR
    html += "\n</thead>\n<tbody>"
    html += "\n<tr><td>" + _("Between") + \
        "</td><td>%s</td><td>%s</td>" % (round(ssbn, dp), dfbn)
    html += "<td>%s</td><td>%s</td><td>%s</td></tr>" % (round(mean_squ_bn, dp), 
                                                    round(F, dp), round(p, dp))
    html += "\n<tr><td>" + _("Within") + \
        "</td><td>%s</td><td>%s</td>" % (round(sswn, dp), dfwn)
    html += "<td>%s</td><td></td><td></td></tr>" % round(mean_squ_wn, dp)
    html += "\n</tbody>\n</table>\n"
    html += "\n\n<h3>" + _("Group summary details") + "</h3>"
    html += "\n<table>\n<thead>"
    html += "\n<tr><th class='%s'>" % CSS_FIRST_COL_VAR + _("Group") + \
            "</th>" + \
        "\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("N") + "</th>" + \
        "\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Mean") + "</th>" + \
        "\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Standard Deviation") + \
            "</th>" + \
        "\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Min") + "</th>" + \
        "\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Max") + "</th></tr>"
    html += "\n</thead>\n<tbody>"
    row_tpl = ("\n<tr><td class='%s'>" % CSS_LBL + \
               "%s</td><td>%s</td><td>%s</td>"
               "<td>%s</td><td>%s</td><td>%s</td></tr>")
    for dic in dics:
        html += row_tpl % (dic["label"], dic["n"], round(dic["mean"], dp), 
                           round(dic["sd"], dp), dic["min"], dic["max"])
    html += "\n</tbody>\n</table>\n"
    if page_break_after:
        html += "<br><hr><br><div class='%s'></div>" % CSS_PAGE_BREAK_BEFORE
    return html
