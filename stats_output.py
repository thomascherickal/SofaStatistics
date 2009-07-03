import my_globals

def ttest_output(t, p, dic_a, dic_b, label_avg="", dp=3, indep=True,
                 level=my_globals.OUTPUT_RESULTS_ONLY, page_break_after=False):
    """
    Returns HTML table ready to display.
    dic_a = {"label": label_a, "n": n_a, "mean": mean_a, "sd": sd_a, 
             "min": min_a, "max": max_a}
    """
    if indep:
        html = "<h2>Results of Independent Samples t-test " + \
            "of average \"%s\" for " % label_avg + \
            "\"%s\" vs \"%s\"</h2>" % (dic_a["label"], dic_b["label"])
    else:
        html = "<h2>Results of Paired Samples t-test " + \
            "of \"%s\" vs \"%s\"</h2>" % (dic_a["label"], dic_b["label"])
    p_format = "\n<p>p value: %%.%sf</p>" % dp
    html += p_format % round(p, dp)
    html += "\n<p>t statistic: %s</p>" % round(t, dp)
    html += "\n\n<table>\n<thead>"
    html += "\n<tr><th class='firstcolvar'>Group</th>" + \
        "\n<th class='firstcolvar'>N</th>" + \
        "\n<th class='firstcolvar'>Mean</th>" + \
        "\n<th class='firstcolvar'>Standard Deviation</th>" + \
        "\n<th class='firstcolvar'>Min</th>" + \
        "\n<th class='firstcolvar'>Max</th></tr>"
    html += "\n</thead>\n<tbody>"
    row_tpl = "\n<tr><td class='lbl'>%s</td><td>%s</td><td>%s</td>" + \
        "<td>%s</td><td>%s</td><td>%s</td></tr>"
    for dic in [dic_a, dic_b]:
        html += row_tpl % (dic["label"], dic["n"], round(dic["mean"], dp), 
                           round(dic["sd"],3), 
                           dic["min"], dic["max"])
    html += "\n</tbody>\n</table>\n"
    if page_break_after:
        html += "<br><hr><br><div class='page-break-before'></div>"
    return html

def mann_whitney_output(u, p, label_a, label_b, label_ranked, dp=3,
                 level=my_globals.OUTPUT_RESULTS_ONLY, page_break_after=False):
    html = "<h2>Results of Mann Whitney U Test of \"%s\" for" % label_ranked + \
            " \"%s\" vs \"%s\"</h2>" % (label_a, label_b)
    p_format = "\n<p>p value: %%.%sf</p>" % dp
    html += p_format % round(p, dp)
    html += "\n<p>U statistic: %s</p>" % round(u, dp)
    if page_break_after:
        html += "<br><hr><br><div class='page-break-before'></div>"
    return html
