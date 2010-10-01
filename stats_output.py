import cgi
import numpy as np
import os
import pylab
import boomslang

import my_globals as mg
import lib
import charting_pylab
import core_stats
import output

"""
Output doesn't include the calculation of any values.  These are in discrete
    functions in core_stats, amenable to unit testing.
No html header or footer added here.  Just some body content.    
"""

def anova_output(samples, F, p, dics, sswn, dfwn, mean_squ_wn, ssbn, dfbn, 
                 mean_squ_bn, label_a, label_b, label_avg, add_to_report,
                 report_name, css_fil, css_idx=0, dp=3, 
                 level=mg.OUTPUT_RESULTS_ONLY, page_break_after=False):
    CSS_FIRST_COL_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_COL_VAR, css_idx)
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    CSS_LBL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_LBL, css_idx)
    CSS_TBL_HDR_FTNOTE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_TBL_HDR_FTNOTE, 
                                                   css_idx)
    footnotes = []
    html = []
    html.append(_("<h2>Results of ANOVA test of average %(avg)s for groups from"
             " \"%(a)s\" to \"%(b)s\"</h2>") % {"avg": label_avg, "a": label_a, 
                                                "b": label_b})
    html.append(u"\n\n<h3>" + _("Analysis of variance table") + u"</h3>")
    html.append(u"\n<table cellspacing='0'>\n<thead>")
    html.append(u"\n<tr>" + \
        u"<th class='%s'>" % CSS_FIRST_COL_VAR + _("Source") + u"</th>" + \
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Sum of Squares") + \
            u"</th>" + \
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("df") + u"</th>" + \
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Mean Sum of Squares") + \
            u"</th>" + \
        u"\n<th class='%s'>F</th>" % CSS_FIRST_COL_VAR)
    # footnote 1
    html.append(u"\n<th class='%s'>" % CSS_FIRST_COL_VAR +
                u"p<a class='%s' href='#ft1'><sup>1</sup></a></th></tr>" %
                CSS_TBL_HDR_FTNOTE)
    footnotes.append("\n<p><a id='ft%s'></a><sup>%s</sup> If p is small, "
        "e.g. less than 0.01, or 0.001, you can assume the result is "
        "statistically significant i.e. there is a difference.</p>")
    html.append(u"\n</thead>\n<tbody>")
    html.append(u"\n<tr><td>" + _("Between") +
                u"</td><td>%s</td><td>%s</td>" % (round(ssbn, dp), dfbn))
    html.append(u"<td>%s</td><td>%s</td><td>%s</td></tr>" %
                (round(mean_squ_bn, dp), round(F, dp), round(p, dp)))
    html.append(u"\n<tr><td>" + _("Within") +
                u"</td><td>%s</td><td>%s</td>" % (round(sswn, dp), dfwn))
    html.append(u"<td>%s</td><td></td><td></td></tr>" % round(mean_squ_wn, dp))
    html.append(u"\n</tbody>\n</table>\n")
    try:
        bolsim, p_sim = core_stats.sim_variance(samples, threshold=0.01)
        msg = round(p_sim, dp)
    except Exception:
        msg = "Unable to calculate"
    # footnote 2
    html.append(u"\n<p>" + _("O'Brien's test for homogeneity of variance") \
                + u": %s" % msg + u" <a href='#ft2'><sup>2</sup></a></p>")
    footnotes.append("\n<p><a id='ft%s'></a><sup>%s</sup> If the value is"
        " small, e.g. less than 0.01, or 0.001, you can assume there is a "
        "difference in variance.</p>")
    html.append(u"\n\n<h3>" + _("Group summary details") + u"</h3>")
    html.append(u"\n<table cellspacing='0'>\n<thead>")
    html.append(u"\n<tr><th class='%s'>" % CSS_FIRST_COL_VAR + _("Group") +
            u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("N") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Mean") + u"</th>")
    # footnote 3
    html.append(u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + 
                _("Standard Deviation") + u"<a class='%s" % CSS_TBL_HDR_FTNOTE +
                "' href='#ft3'><sup>3</sup></a></th></th>")
    footnotes.append("\n<p><a id='ft%s'></a><sup>%s</sup> Standard "
                     "Deviation measures the spread of values.</p>")
    html.append(u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Min") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Max") + u"</th>")
    # footnotes 4,5,6
    html.append(u"<th class='%s'>" % CSS_FIRST_COL_VAR + _("Kurtosis") + 
                u"<a class='%s' href='#ft4'><sup>4</sup></a></th>" % 
                CSS_TBL_HDR_FTNOTE)
    html.append(u"<th class='%s'>" % CSS_FIRST_COL_VAR + _("Skew") + 
                u"<a class='%s' href='#ft5'><sup>5</sup></a></th>" %
                CSS_TBL_HDR_FTNOTE)
    html.append(u"<th class='%s'>" % CSS_FIRST_COL_VAR + _("p abnormal") + 
                u"<a class='%s' href='#ft6'><sup>6</sup></a></th>" %
                CSS_TBL_HDR_FTNOTE)
    html.append(u"</tr>")
    footnotes += ("\n<p><a id='ft%s'></a><sup>%s</sup> " +
        _("Kurtosis measures the peakedness or flatness of values.  "
              "Between -1 and 1 is probably great. Between -2 and 2 is "
              "probably good.</p>"),
          "\n<p><a id='ft%s'></a><sup>%s</sup> " +
        _("Skew measures the lopsidedness of values.  Between -1 and 1 is "
              "probably great. Between -2 and 2 is probably good.</p>"),
          "\n<p><a id='ft%s'></a><sup>%s</sup> " +
        _("This provides a single measure of normality. If p is small, e.g."
              " less than 0.01, or 0.001, you can assume the distribution "
              "is not strictly normal.  Note - it may be normal enough "
              "though.</p>"),
        )    
    html.append(u"\n</thead>\n<tbody>")
    row_tpl = (u"\n<tr><td class='%s'>" % CSS_LBL + \
               u"%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>"
               u"<td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>")
    dic_sample_tups = zip(dics, samples)
    for dic, sample in dic_sample_tups:
        results = (dic["label"], dic["n"], round(dic["mean"], dp), 
                   round(dic["sd"], dp), dic["min"], dic["max"])
        try:
            unused, p_arr, cskew, unused, ckurtosis, unused = \
                                                core_stats.normaltest(sample)
            results += (round(ckurtosis, dp), round(cskew, dp), 
                        round(p_arr[0], dp))
        except Exception:
            results += (_("Unable to calculate kurtosis"), 
                        _("Unable to calculate skew"),
                        _("Unable to calculate overall p for normality test"),
                        )
        html.append(row_tpl % results)
    html.append(u"\n</tbody>\n</table>\n")
    for i, footnote in enumerate(footnotes):
        next_ft = i + 1
        html.append(footnote % (next_ft, next_ft))
    for i, dic_sample_tup in enumerate(dic_sample_tups):
        suffix = u"%s" % i
        dic, sample = dic_sample_tup
        hist_label = dic["label"]
        # histogram
        # http://www.scipy.org/Cookbook/Matplotlib/LaTeX_Examples
        charting_pylab.gen_config(axes_labelsize=10, xtick_labelsize=8, 
                                  ytick_labelsize=8)
        fig = pylab.figure()
        fig.set_size_inches((5.0, 3.5)) # see dpi to get image size in pixels
        grid_bg, item_colours, line_colour = \
                                        output.get_stats_chart_colours(css_fil)
        charting_pylab.config_hist(fig, sample, label_avg, hist_label, False, 
                                   grid_bg, item_colours[0], line_colour)
        img_src = charting_pylab.save_report_img(add_to_report, report_name, 
                                               save_func=pylab.savefig, dpi=100)
        html.append(u"\n<img src='%s'>" % img_src)
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)

def ttest_basic_results(sample_a, sample_b, t, p, dic_a, dic_b, label_avg, dp, 
                        indep, css_idx, html):
    """
    Footnotes are autonumbered at end.  The links to them will need numbering 
        though.
    """
    CSS_FIRST_COL_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_COL_VAR, css_idx)
    CSS_LBL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_LBL, css_idx)
    CSS_TBL_HDR_FTNOTE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_TBL_HDR_FTNOTE, 
                                                   css_idx)
    footnotes = []
    if indep:
        html.append(_("<h2>Results of Independent Samples t-test "
            "of average \"%(avg)s\" for \"%(a)s\" vs \"%(b)s\"</h2>") % \
            {"avg": label_avg, "a": dic_a["label"], "b": dic_b["label"]})
    else:
        html.append(_("<h2>Results of Paired Samples t-test "
            "of \"%(a)s\" vs \"%(b)s\"</h2>") % 
            {"a": dic_a["label"], "b": dic_b["label"]})
    # always footnote 1
    html.append(u"\n<p>" + _("p value") + u": %s" % round(p, dp) + 
                u" <a href='#ft1'><sup>1</sup></a></p>")
    footnotes.append("\n<p><a id='ft%s'></a><sup>%s</sup> If p is small, "
        "e.g. less than 0.01, or 0.001, you can assume the result is "
        "statistically significant i.e. there is a difference.</p>")
    html.append(u"\n<p>" + _("t statistic") + u": %s</p>" % round(t, dp))
    if indep:
        try:
            bolsim, p_sim = core_stats.sim_variance([sample_a, sample_b], 
                                                    threshold=0.01)
            msg = round(p_sim, dp)
        except Exception:
            msg = "Unable to calculate"
        # always footnote 2 if present
        html.append(u"\n<p>" + _("O'Brien's test for homogeneity of variance") \
                    + u": %s" % msg + u" <a href='#ft2'><sup>2</sup></a></p>")
        footnotes.append("\n<p><a id='ft%s'></a><sup>%s</sup> If the value is"
            " small, e.g. less than 0.01, or 0.001, you can assume there is a "
            "difference in variance.</p>")
    html.append(u"\n\n<table cellspacing='0'>\n<thead>")
    next_ft = len(footnotes) + 1
    html.append(u"\n<tr>" + \
        u"<th class='%s'>" % CSS_FIRST_COL_VAR + _("Group") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("N") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Mean") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Standard Deviation") +
            u"<a class='%s' href='#ft%s'><sup>%s</sup></a></th>" % 
            (CSS_TBL_HDR_FTNOTE, next_ft, next_ft) +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Min") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Max") + u"</th>")
    footnotes.append("\n<p><a id='ft%s'></a><sup>%s</sup> Standard "
                     "Deviation measures the spread of values.</p>")
    if indep:
        # if here, always 4,5,6
        html.append(u"<th class='%s'>" % CSS_FIRST_COL_VAR + _("Kurtosis") + 
                    u"<a class='%s' href='#ft4'><sup>4</sup></a></th>" % 
                    CSS_TBL_HDR_FTNOTE)
        html.append(u"<th class='%s'>" % CSS_FIRST_COL_VAR + _("Skew") + 
                    u"<a class='%s' href='#ft5'><sup>5</sup></a></th>" %
                    CSS_TBL_HDR_FTNOTE)
        html.append(u"<th class='%s'>" % CSS_FIRST_COL_VAR + _("p abnormal") + 
                    u"<a class='%s' href='#ft6'><sup>6</sup></a></th>" %
                    CSS_TBL_HDR_FTNOTE)
        footnotes += ("\n<p><a id='ft%s'></a><sup>%s</sup> " +
            _("Kurtosis measures the peakedness or flatness of values.  "
                  "Between -1 and 1 is probably great. Between -2 and 2 is "
                  "probably good.</p>"),
              "\n<p><a id='ft%s'></a><sup>%s</sup> " +
            _("Skew measures the lopsidedness of values.  Between -1 and 1 is "
                  "probably great. Between -2 and 2 is probably good.</p>"),
              "\n<p><a id='ft%s'></a><sup>%s</sup> " +
            _("This provides a single measure of normality. If p is small, e.g."
                  " less than 0.01, or 0.001, you can assume the distribution "
                  "is not strictly normal.  Note - it may be normal enough "
                  "though.</p>"),
            )
    html.append(u"</tr>")
    html.append(u"\n</thead>\n<tbody>")
    if indep:
        row_tpl = (u"\n<tr><td class='%s'>" % CSS_LBL + u"%s</td><td>%s</td>" +
            u"<td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>"
            "<td>%s</td><td>%s</td></tr>")
    else:
        row_tpl = (u"\n<tr><td class='%s'>" % CSS_LBL + u"%s</td><td>%s</td>" +
            u"<td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>")
    for dic, sample in [(dic_a, sample_a), (dic_b, sample_b)]:
        results = (dic["label"], dic["n"], round(dic["mean"], dp), 
                  round(dic["sd"], dp), dic["min"], dic["max"])
        if indep:
            try:
                unused, p_arr, cskew, unused, ckurtosis, unused = \
                        core_stats.normaltest(sample)
                results += (round(ckurtosis, dp), round(cskew, dp), 
                            round(p_arr[0], dp))
            except Exception:
                results += (_("Unable to calculate kurtosis"), 
                            _("Unable to calculate skew"),
                            _("Unable to calculate overall p for "
                                "normality test"),
                            )
        html.append(row_tpl % results)
    html.append(u"\n</tbody>\n</table>\n")
    html.append("\n<hr class='ftnote-line'>")
    for i, footnote in enumerate(footnotes):
        next_ft = i + 1
        html.append(footnote % (next_ft, next_ft))

def ttest_indep_output(sample_a, sample_b, t, p, dic_a, dic_b, label_avg, 
                       add_to_report, report_name, css_fil, css_idx=0, dp=3, 
                       level=mg.OUTPUT_RESULTS_ONLY, page_break_after=False):
    """
    Returns HTML table ready to display.
    dic_a = {"label": label_a, "n": n_a, "mean": mean_a, "sd": sd_a, 
             "min": min_a, "max": max_a}
    """
    html = []
    indep = True
    ttest_basic_results(sample_a, sample_b, t, p, dic_a, dic_b, label_avg, dp, 
                        indep, css_idx, html)
    sample_dets = [(u"a", sample_a, dic_a["label"]), 
                   (u"b", sample_b, dic_b["label"])]
    for (suffix, sample, hist_label) in sample_dets:
        # histogram
        # http://www.scipy.org/Cookbook/Matplotlib/LaTeX_Examples
        charting_pylab.gen_config(axes_labelsize=10, xtick_labelsize=8, 
                                  ytick_labelsize=8)
        fig = pylab.figure()
        fig.set_size_inches((5.0, 3.5)) # see dpi to get image size in pixels
        grid_bg, item_colours, line_colour = \
                                        output.get_stats_chart_colours(css_fil)
        charting_pylab.config_hist(fig, sample, label_avg, hist_label, False, 
                                   grid_bg, item_colours[0], line_colour)
        img_src = charting_pylab.save_report_img(add_to_report, report_name, 
                                               save_func=pylab.savefig, dpi=100)
        html.append(u"\n<img src='%s'>" % img_src)
    if page_break_after:
        CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % \
            (mg.CSS_PAGE_BREAK_BEFORE, css_idx)
        html.append(u"<br><hr><br><div class='%s'></div>" % \
                    CSS_PAGE_BREAK_BEFORE)
    html_str = u"\n".join(html)
    return html_str

def ttest_paired_output(sample_a, sample_b, t, p, dic_a, dic_b, diffs, 
                        add_to_report, report_name, css_fil, css_idx=0, 
                        label_avg=u"", dp=3, level=mg.OUTPUT_RESULTS_ONLY,
                        page_break_after=False):
    """
    Returns HTML table ready to display.
    dic_a = {"label": label_a, "n": n_a, "mean": mean_a, "sd": sd_a, 
             "min": min_a, "max": max_a}
    """
    html = []
    indep = False
    ttest_basic_results(sample_a, sample_b, t, p, dic_a, dic_b, label_avg, dp, 
                        indep, css_idx, html)
    # histogram
    charting_pylab.gen_config(axes_labelsize=10, xtick_labelsize=8, 
                              ytick_labelsize=8)
    fig = pylab.figure()
    fig.set_size_inches((7.5, 3.5)) # see dpi to get image size in pixels
    hist_label = u"Differences between %s and %s" % (dic_a["label"], 
                                                     dic_b["label"])
    grid_bg, item_colours, line_colour = output.get_stats_chart_colours(css_fil)
    charting_pylab.config_hist(fig, diffs, _("Differences"), hist_label, False, 
                               grid_bg, item_colours[0], line_colour)
    img_src = charting_pylab.save_report_img(add_to_report, report_name, 
                                             save_func=pylab.savefig, dpi=100)
    html.append(u"\n<img src='%s'>" % img_src)
    if page_break_after:
        CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % \
            (mg.CSS_PAGE_BREAK_BEFORE, css_idx)
        html.append(u"<br><hr><br><div class='%s'></div>" % \
                    CSS_PAGE_BREAK_BEFORE)
    html_str = u"\n".join(html)
    return html_str

def mann_whitney_output(u, p, dic_a, dic_b, label_ranked, css_fil, css_idx=0, 
                        dp=3, level=mg.OUTPUT_RESULTS_ONLY, 
                        page_break_after=False):
    CSS_FIRST_COL_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_COL_VAR, css_idx)
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    CSS_LBL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_LBL, css_idx)
    html = []
    html.append(_("<h2>Results of Mann Whitney U Test of \"%(ranked)s\" for "
             "\"%(a)s\" vs \"%(b)s\"</h2>") % {"ranked": label_ranked, 
                                               "a": dic_a["label"], 
                                               "b": dic_b["label"]})
    p_format = u"\n<p>" + _("p value") + u": %%.%sf</p>" % dp
    html.append(p_format % round(p, dp))
    html.append(u"\n<p>" + _("U statistic") + u": %s</p>" % round(u, dp))
    html.append(u"\n\n<table cellspacing='0'>\n<thead>")
    html.append(u"\n<tr>" +
        u"<th class='%s'>" % CSS_FIRST_COL_VAR + _("Group") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("N") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Median") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Avg Rank") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Min") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Max") + u"</th></tr>")
    html.append(u"\n</thead>\n<tbody>")
    row_tpl = u"\n<tr><td class='%s'>" % CSS_LBL + u"%s</td><td>%s</td>" + \
        u"<td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
    for dic in [dic_a, dic_b]:
        html.append(row_tpl % (dic[mg.STATS_DIC_LABEL], 
                               dic[mg.STATS_DIC_N], 
                               round(dic[mg.STATS_DIC_MEDIAN], dp), 
                               round(dic["avg rank"], dp),
                               dic[mg.STATS_DIC_MIN], 
                               dic[mg.STATS_DIC_MAX]))
    html.append(u"\n</tbody>\n</table>\n")
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)

def wilcoxon_output(t, p, label_a, label_b, css_fil, css_idx=0, dp=3, 
                    level=mg.OUTPUT_RESULTS_ONLY, page_break_after=False):
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    html = _("<h2>Results of Wilcoxon Signed Ranks Test of \"%(a)s\" vs "
             "\"%(b)s\"</h2>") % {"a": label_a, "b": label_b}
    p_format = u"\n<p>p value: %%.%sf</p>" % dp
    html += p_format % round(p, dp)
    html += u"\n<p>" + _("Wilcoxon Signed Ranks statistic") + u": %s</p>" % \
        round(t, dp)
    if page_break_after:
        html += u"<br><hr><br><div class='%s'></div>" % CSS_PAGE_BREAK_BEFORE
    return html

def pearsonsr_output(sample_a, sample_b, r, p, label_a, label_b, add_to_report,
                     report_name, css_fil, css_idx=0, dp=3, 
                     level=mg.OUTPUT_RESULTS_ONLY, page_break_after=False):
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    html = []
    a_vs_b = '"%s"' % label_a + _(" vs ") + '"%s"' % label_b
    title = (_("Results of Pearson's Test of Linear Correlation "
               "for %s") % a_vs_b)
    html.append("<h2>%s</h2>" % title)
    p_format = u"\n<p>" + _("p value") + u": %%.%sf</p>" % dp
    html.append(p_format % round(p, dp))
    html.append(u"\n<p>" + _("Pearson's R statistic") +
                u": %s</p>" % round(r, dp))
    grid_bg, item_colours, line_colour = output.get_stats_chart_colours(css_fil)
    dot_colour = item_colours[0]
    title_dets_html = u"" # already got an appropriate title for whole section
    charting_pylab.add_scatterplot(grid_bg, dot_colour, line_colour, sample_a, 
                                   sample_b, label_a, label_b, a_vs_b, 
                                   title_dets_html, add_to_report, report_name, 
                                   html)
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)

def spearmansr_output(sample_a, sample_b, r, p, label_a, label_b, add_to_report,
                      report_name, css_fil, css_idx=0, dp=3, 
                      level=mg.OUTPUT_RESULTS_ONLY, page_break_after=False):
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    html = []
    a_vs_b = '"%s"' % label_a + _(" vs ") + '"%s"' % label_b
    title = (_("Results of Spearman's Test of Linear Correlation "
               "for %s") % a_vs_b)
    html.append("<h2>%s</h2>" % title)
    p_format = u"\n<p>" + _("p value") + u": %%.%sf</p>" % dp
    html.append(p_format % round(p, dp))
    html.append(u"\n<p>" + _("Spearman's R statistic") + 
                u": %s</p>" % round(r, dp))
    grid_bg, item_colours, line_colour = output.get_stats_chart_colours(css_fil)
    dot_colour = item_colours[0]
    title_dets_html = u"" # already got an appropriate title for whole section
    charting_pylab.add_scatterplot(grid_bg, dot_colour, line_colour, sample_a, 
                                   sample_b, label_a, label_b, a_vs_b, 
                                   title_dets_html, add_to_report, report_name, 
                                   html)
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)

def chisquare_output(chi, p, var_label_a, var_label_b, add_to_report, 
                     report_name, val_labels_a, val_labels_b, lst_obs, lst_exp, 
                     min_count, perc_cells_lt_5, df, css_fil, css_idx=0, dp=3, 
                     level=mg.OUTPUT_RESULTS_ONLY, page_break_after=False):
    debug = False
    CSS_SPACEHOLDER = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_SPACEHOLDER, css_idx)
    CSS_FIRST_COL_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_COL_VAR, css_idx)
    CSS_FIRST_ROW_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_ROW_VAR, css_idx)
    CSS_ROW_VAL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_ROW_VAL, css_idx)
    CSS_DATACELL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_DATACELL, css_idx)
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    var_label_a = cgi.escape(var_label_a)
    var_label_b = cgi.escape(var_label_b)
    try:
        val_labels_a_html = map(cgi.escape, val_labels_a)
        val_labels_b_html = map(cgi.escape, val_labels_b)
    except AttributeError:
        # e.g. an int
        val_labels_a_html = val_labels_a
        val_labels_b_html = val_labels_b
    cells_per_col = 2
    val_labels_a_n = len(val_labels_a)
    val_labels_b_n = len(val_labels_b)
    html = []
    html.append(_("<h2>Results of Pearson's Chi Square Test of Association "
        "Between \"%(laba)s\" and \"%(labb)s\"</h2>") % {"laba": var_label_a, 
                                                         "labb": var_label_b})
    p_format = u"\n<p>" + _("p value") + u": %%.%sf</p>" % dp
    html.append(p_format % round(p, dp))
    html.append(u"\n<p>" + _("Pearson's Chi Square statistic") + u": %s</p>" %
                round(chi, dp))
    html.append(u"\n<p>" + _("Degrees of Freedom (df)") + u": %s</p>" % df)
    # headings
    html.append(u"\n\n<table cellspacing='0'>\n<thead>")
    html.append(u"\n<tr><th class='%s' colspan=2 rowspan=3></th>" % 
                CSS_SPACEHOLDER)
    html.append(u"<th class='%s' " % CSS_FIRST_COL_VAR +
                u"colspan=%s>%s</th></tr>" % ((val_labels_b_n+1)*cells_per_col, 
                                              var_label_b))
    html.append(u"\n<tr>")
    for val in val_labels_b:
        html.append(u"<th colspan=%s>%s</th>" % (cells_per_col, val))
    html.append(u"<th colspan=%s>" % cells_per_col + _("TOTAL") +
                u"</th></tr>\n<tr>")
    for i in range(val_labels_b_n + 1):
        html.append(u"<th>" + _("Obs") + u"</th><th>" + _("Exp") + u"</th>")
    html.append(u"</tr>")
    # body
    html.append(u"\n\n</thead><tbody>")
    item_i = 0
    html.append(u"\n<tr><td class='%s' rowspan=%s>%s</td>" % (CSS_FIRST_ROW_VAR, 
                                            val_labels_a_n + 1, var_label_a))
    col_obs_tots = [0]*val_labels_b_n
    col_exp_tots = [0]*val_labels_b_n
    # total row totals
    row_obs_tot_tot = 0 
    row_exp_tot_tot = 0
    for row_i, val_a in enumerate(val_labels_a_html):
        row_obs_tot = 0
        row_exp_tot = 0
        html.append(u"<td class='%s'>%s</td>" % (CSS_ROW_VAL, val_a))        
        for col_i, val_b in enumerate(val_labels_b_html):
            obs = lst_obs[item_i]
            exp = lst_exp[item_i]
            html.append(u"<td class='%s'>" % CSS_DATACELL +
                        u"%s</td><td class='%s'>%s</td>" % (obs, CSS_DATACELL, 
                                                            round(exp, 1)))
            row_obs_tot += obs
            row_exp_tot += exp
            col_obs_tots[col_i] += obs
            col_exp_tots[col_i] += exp
            item_i += 1
        # add total for row
        row_obs_tot_tot += row_obs_tot
        row_exp_tot_tot += row_exp_tot
        html.append(u"<td class='%s'>" % CSS_DATACELL +
                u"%s</td><td class='%s'>%s</td>" % (row_obs_tot, CSS_DATACELL, 
                                                    round(row_exp_tot,1)))
        html.append(u"</tr>\n<tr>")
    # add totals row
    col_tots = zip(col_obs_tots, col_exp_tots)
    html.append(u"<td class='%s'>" % CSS_ROW_VAL + _("TOTAL") + u"</td>")
    for col_obs_tot, col_exp_tot in col_tots:
        html.append(u"<td class='%s'>" % CSS_DATACELL +
            u"%s</td><td class='%s'>%s</td>" % (col_obs_tot, CSS_DATACELL,
                                                round(col_exp_tot, 1)))
    # add total of totals
    html.append(u"<td class='%s'>" % CSS_DATACELL +
                u"%s</td><td class='%s'>%s</td>" % (row_obs_tot_tot, 
                                                    CSS_DATACELL, 
                                                    round(row_exp_tot_tot,1)))
    html.append(u"</tr>")
    html.append(u"\n</tbody>\n</table>\n")
    # warnings
    html.append(u"\n<p>" + _("Minimum expected cell count") + u": %s</p>" %
                round(min_count, dp))
    html.append(u"\n<p>% " + _("cells with expected count < 5") + u": %s</p>" %
                round(perc_cells_lt_5, 1))
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    # clustered bar charts
    grid_bg, item_colours, line_colour = output.get_stats_chart_colours(css_fil)
    add_clustered_barcharts(grid_bg, item_colours, line_colour, lst_obs, 
                            var_label_a, var_label_b, val_labels_a, 
                            val_labels_b, val_labels_a_n, val_labels_b_n, 
                            add_to_report, report_name, html)
    return u"".join(html)

def add_clustered_barcharts(grid_bg, bar_colours, line_colour, lst_obs, 
                            var_label_a, var_label_b, val_labels_a, 
                            val_labels_b, val_labels_a_n, val_labels_b_n, 
                            add_to_report, report_name, html):
    # NB list_obs is bs within a and we need the other way around
    debug = False
    rows_n = len(lst_obs)/val_labels_b_n
    cols_n = val_labels_b_n
    bs_in_as = np.array(lst_obs).reshape(rows_n, cols_n)
    as_in_bs_lst = bs_in_as.transpose().tolist()
    # proportions of b within a
    propns_bs_in_as = []
    bs_in_as_lst = bs_in_as.tolist()
    for bs in bs_in_as_lst:
        propns_lst = []
        for b in bs:
            propns_lst.append(float(b)/float(sum(bs)))
        propns_bs_in_as.append(propns_lst)
    propns_as_in_bs_lst = np.array(propns_bs_in_as).transpose().tolist()
    if debug:
        print(bs_in_as)
        print(as_in_bs_lst)
        print(propns_as_in_bs_lst)
    title_tmp = _("%(laba)s and %(labb)s - %(y)s")
    title_overrides = {"fontsize": 14}
    # chart 1 - proportions
    plot = boomslang.Plot()
    y_label = _("Proportion")
    plot.setTitle(title_tmp % {"laba": var_label_a, "labb": var_label_b, 
                               "y": y_label})
    plot.setTitleProperties(title_overrides)
    plot.setDimensions(7) # allow height to be set by golden ratio
    plot.hasLegend(columns=val_labels_b_n, location="lower left")
    plot.setAxesLabelSize(11)
    plot.setLegendLabelSize(9)
    charting_pylab.config_clustered_barchart(grid_bg, bar_colours, line_colour, 
                                    plot, var_label_a, y_label, val_labels_a_n, 
                                    val_labels_a, val_labels_b, 
                                    propns_as_in_bs_lst)
    img_src = charting_pylab.save_report_img(add_to_report, report_name, 
                                             save_func=plot.save, dpi=None)
    html.append(u"\n<img src='%s'>" % img_src)
    # chart 2 - freqs
    plot = boomslang.Plot()
    y_label = _("Frequency")
    plot.setTitle(title_tmp % {"laba": var_label_a, "labb": var_label_b, 
                               "y": y_label})
    plot.setTitleProperties(title_overrides)
    plot.setDimensions(7) # allow height to be set by golden ratio
    plot.hasLegend(columns=val_labels_b_n, location="lower left")
    plot.setAxesLabelSize(11)
    plot.setLegendLabelSize(9)
    # only need 6 because program limits to that. See core_stats.get_obs_exp().
    charting_pylab.config_clustered_barchart(grid_bg, bar_colours, line_colour, 
                                    plot, var_label_a, y_label, val_labels_a_n, 
                                    val_labels_a, val_labels_b, as_in_bs_lst)
    img_src = charting_pylab.save_report_img(add_to_report, report_name, 
                                             save_func=plot.save, dpi=None)
    html.append(u"\n<img src='%s'>" % img_src)

def kruskal_wallis_output(h, p, label_a, label_b, dics, label_avg, css_fil, 
                          css_idx=0, dp=3, level=mg.OUTPUT_RESULTS_ONLY, 
                          page_break_after=False):
    CSS_FIRST_COL_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_COL_VAR, css_idx)
    CSS_LBL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_LBL, css_idx)
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    html = []
    html.append(_("<h2>Results of Kruskal-Wallis H test of average %(avg)s for "
                 "groups from \"%(a)s\" to \"%(b)s\"</h2>") % {"avg": label_avg, 
                                                "a": label_a, "b": label_b})
    p_format = "\n<p>" + _("p value") + ": %%.%sf</p>" % dp
    html.append(p_format % round(p, dp))
    html.append("\n<p>" + _("Kruskal-Wallis H statistic") + ": %s</p>" % \
                                                                round(h, dp))
    html.append(u"\n\n<table cellspacing='0'>\n<thead>")
    html.append(u"\n<tr>" +
        u"<th class='%s'>" % CSS_FIRST_COL_VAR + _("Group") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("N") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Median") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Min") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Max") + u"</th></tr>")
    html.append(u"\n</thead>\n<tbody>")
    row_tpl = u"\n<tr><td class='%s'>" % CSS_LBL + u"%s</td><td>%s</td>" + \
        u"<td>%s</td><td>%s</td><td>%s</td></tr>"
    for dic in dics:
        html.append(row_tpl % (dic[mg.STATS_DIC_LABEL], 
                               dic[mg.STATS_DIC_N], 
                               round(dic[mg.STATS_DIC_MEDIAN], dp),
                               dic[mg.STATS_DIC_MIN], 
                               dic[mg.STATS_DIC_MAX]))
    if page_break_after:
        html.append("<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)
