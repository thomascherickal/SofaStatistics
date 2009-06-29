import my_globals

def ttest_output(t, p, label_measure, dic_a, dic_b, indep=True, 
                 level=my_globals.OUTPUT_RESULTS_ONLY, page_break_after=False):
    """
    Returns HTML table ready to display.
    dic_a = {"label": label_a, "n": n_a, "mean": mean_a, "sd": sd_a, 
             "min": min_a, "max": max_a}
    """
    test_type = "Independent" if indep else "Paired" 
    html = "<h2>Results of %s t-test " % test_type + \
        "of average \"%s\" for " % label_measure + \
        "\"%s\" vs \"%s\"</h2>" % (dic_a["label"], dic_b["label"])
    html += "\n<p>p value: %s</p>" % p
    html += "\n<p>t statistic: %s</p>" % t
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
        html += row_tpl % (dic["label"], dic["n"], dic["mean"], dic["sd"], 
                           dic["min"], dic["max"])
    html += "\n</tbody>\n</table>\n"
    if page_break_after:
        html += "<br><hr><br><div class='page-break-before'></div>"
    return html
