import cgi
import numpy as np
import boomslang

import my_globals as mg
import lib
import my_exceptions

try:
    import wxmpl
except my_exceptions.MatplotlibBackendException, e:
    import wx
    wx.MessageBox(lib.ue(e))
    
import pylab # must import after wxmpl so matplotlib.use() is always first
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
    debug = False
    CSS_FIRST_COL_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_COL_VAR, css_idx)
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    CSS_LBL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_LBL, css_idx)
    CSS_TBL_HDR_FTNOTE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_TBL_HDR_FTNOTE, 
                                                   css_idx)
    footnotes = []
    html = []
    title = _(u"Results of ANOVA test of average %(avg)s for groups from"
              u" \"%(a)s\" to \"%(b)s\"") % {u"avg": label_avg, 
                                             u"a": label_a, u"b": label_b}
    html_title = u"<h2>%s</h2>" % title
    html.append(html_title)
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
    # always footnote 1 (so can hardwire anchor)
    html.append(u"\n<th class='%s'>" % CSS_FIRST_COL_VAR +
                u"p<a class='%s' href='#ft1'><sup>1</sup></a></th></tr>" %
                CSS_TBL_HDR_FTNOTE)
    footnotes.append("\n<p><a id='ft%%s'></a><sup>%%s</sup> %s</p>" % \
                     mg.P_EXPLAN_DIFF)
    html.append(u"\n</thead>\n<tbody>")
    html.append(u"\n<tr><td>" + _("Between") +
                u"</td><td>%s</td><td>%s</td>" % (round(ssbn, dp), dfbn))
    html.append(u"<td>%s</td><td>%s</td><td>%s</td></tr>" %
                (round(mean_squ_bn, dp), round(F, dp), lib.get_p(p, dp)))
    html.append(u"\n<tr><td>" + _("Within") +
                u"</td><td>%s</td><td>%s</td>" % (round(sswn, dp), dfwn))
    html.append(u"<td>%s</td><td></td><td></td></tr>" % round(mean_squ_wn, dp))
    html.append(u"\n</tbody>\n</table>\n")
    try:
        unused, p_sim = core_stats.sim_variance(samples, threshold=0.01)
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
            (unused, p_arr, cskew, 
             unused, ckurtosis, unused) = core_stats.normaltest(sample)
            results += (round(ckurtosis, dp), round(cskew, dp), 
                        lib.get_p(p_arr[0], dp))
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
    output.append_divider(html, title, indiv_title=u"")
    for dic_sample_tup in dic_sample_tups:
        dic, sample = dic_sample_tup
        histlbl = dic["label"]
        if debug: print(histlbl)
        # histogram
        # http://www.scipy.org/Cookbook/Matplotlib/LaTeX_Examples
        charting_pylab.gen_config(axes_labelsize=10, xtick_labelsize=8, 
                                  ytick_labelsize=8)
        fig = pylab.figure()
        fig.set_size_inches((5.0, 3.5)) # see dpi to get image size in pixels
        (grid_bg, item_colours, 
            line_colour) = output.get_stats_chart_colours(css_fil)
        try:
            charting_pylab.config_hist(fig, sample, label_avg, histlbl, 
                                   False, grid_bg, item_colours[0], line_colour)
            img_src = charting_pylab.save_report_img(add_to_report, report_name, 
                                               save_func=pylab.savefig, dpi=100)
            html.append(u"\n%s%s%s" % (mg.IMG_SRC_START, img_src, 
                                       mg.IMG_SRC_END))
        except Exception, e:
            html.append(u"<b>%s</b> - unable to display histogram. Reason: %s" % 
                        (histlbl, lib.ue(e)))
        output.append_divider(html, title, indiv_title=histlbl)
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)

def ttest_basic_results(sample_a, sample_b, t, p, dic_a, dic_b, df, label_avg, 
                        dp, indep, css_idx, html):
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
        title = (_(u"Results of Independent Samples t-test of average "
                   u"\"%(avg)s\" for \"%(a)s\" vs \"%(b)s\"") %
                                {"avg": label_avg, "a": dic_a[mg.STATS_DIC_LBL], 
                                 "b": dic_b[mg.STATS_DIC_LBL]})
        
    else:
        title = (_("Results of Paired Samples t-test of \"%(a)s\" vs \"%(b)s\"") 
                 % {"a": dic_a[mg.STATS_DIC_LBL], "b": dic_b[mg.STATS_DIC_LBL]})
    title_html = u"<h2>%s</h2>" % title
    html.append(title_html)
    # always footnote 1 (so can hardwire anchor)
    html.append(u"\n<p>" + _("p value") + u": %s" % lib.get_p(p, dp) + 
                u" <a href='#ft1'><sup>1</sup></a></p>")
    footnotes.append("\n<p><a id='ft%%s'></a><sup>%%s</sup> %s</p>" % \
                     mg.P_EXPLAN_DIFF)
    html.append(u"\n<p>" + _("t statistic") + u": %s</p>" % round(t, dp))
    html.append(u"\n<p>" + mg.DF + u": %s</p>" % df)
    if indep:
        try:
            unused, p_sim = core_stats.sim_variance([sample_a, sample_b], 
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
    return title

def ttest_indep_output(sample_a, sample_b, t, p, dic_a, dic_b, df, label_avg, 
                       add_to_report, report_name, css_fil, css_idx=0, dp=3, 
                       level=mg.OUTPUT_RESULTS_ONLY, page_break_after=False):
    """
    Returns HTML table ready to display.
    dic_a = {"label": label_a, "n": n_a, "mean": mean_a, "sd": sd_a, 
             "min": min_a, "max": max_a}
    """
    html = []
    indep = True
    title = ttest_basic_results(sample_a, sample_b, t, p, dic_a, dic_b, df, 
                                label_avg, dp, indep, css_idx, html)
    output.append_divider(html, title, indiv_title=u"")
    sample_dets = [(u"a", sample_a, dic_a["label"]), 
                   (u"b", sample_b, dic_b["label"])]
    for chart_idx, sample_det in enumerate(sample_dets):
        unused, sample, histlbl = sample_det
        # histogram
        # http://www.scipy.org/Cookbook/Matplotlib/LaTeX_Examples
        charting_pylab.gen_config(axes_labelsize=10, xtick_labelsize=8, 
                                  ytick_labelsize=8)
        fig = pylab.figure()
        fig.set_size_inches((5.0, 3.5)) # see dpi to get image size in pixels
        (grid_bg, item_colours, 
         line_colour) = output.get_stats_chart_colours(css_fil)
        try:
            charting_pylab.config_hist(fig, sample, label_avg, histlbl, 
                                   False, grid_bg, item_colours[0], line_colour)
            img_src = charting_pylab.save_report_img(add_to_report, report_name, 
                                               save_func=pylab.savefig, dpi=100)
            html.append(u"\n%s%s%s" % (mg.IMG_SRC_START, img_src, 
                                       mg.IMG_SRC_END))
        except Exception, e:
            html.append(u"<b>%s</b> - unable to display histogram. Reason: %s" % 
                        (histlbl, lib.ue(e)))
        output.append_divider(html, title, indiv_title=histlbl)
    if page_break_after:
        CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % \
            (mg.CSS_PAGE_BREAK_BEFORE, css_idx)
        html.append(u"<br><hr><br><div class='%s'></div>" % \
                    CSS_PAGE_BREAK_BEFORE)
    html_str = u"\n".join(html)
    return html_str

def ttest_paired_output(sample_a, sample_b, t, p, dic_a, dic_b, df, diffs, 
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
    title = ttest_basic_results(sample_a, sample_b, t, p, dic_a, dic_b, df, 
                                label_avg, dp, indep, css_idx, html)
    output.append_divider(html, title, indiv_title=u"")
    # histogram
    histlbl = u"Differences between %s and %s" % (dic_a["label"], 
                                                  dic_b["label"])
    charting_pylab.gen_config(axes_labelsize=10, xtick_labelsize=8, 
                              ytick_labelsize=8)
    fig = pylab.figure()
    fig.set_size_inches((7.5, 3.5)) # see dpi to get image size in pixels
    grid_bg, item_colours, line_colour = output.get_stats_chart_colours(css_fil)
    try:
        charting_pylab.config_hist(fig, diffs, _("Differences"), histlbl, 
                                   False, grid_bg, item_colours[0], line_colour)
        img_src = charting_pylab.save_report_img(add_to_report, report_name, 
                                               save_func=pylab.savefig, dpi=100)
        html.append(u"\n%s%s%s" % (mg.IMG_SRC_START, img_src, mg.IMG_SRC_END))
    except Exception, e:
        html.append(u"<b>%s</b> - unable to display histogram. Reason: %s" % 
                    (histlbl, lib.ue(e)))
    if page_break_after:
        CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % \
            (mg.CSS_PAGE_BREAK_BEFORE, css_idx)
        html.append(u"<br><hr><br><div class='%s'></div>" %
                    CSS_PAGE_BREAK_BEFORE)
    output.append_divider(html, title, indiv_title=histlbl)
    html_str = u"\n".join(html)
    return html_str

def mann_whitney_output(u, p, dic_a, dic_b, z, label_ranked, css_fil, css_idx=0, 
                        dp=3, level=mg.OUTPUT_RESULTS_ONLY, 
                        page_break_after=False):
    CSS_FIRST_COL_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_COL_VAR, css_idx)
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    CSS_LBL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_LBL, css_idx)
    html = []
    footnotes = []
    label_a = dic_a[mg.STATS_DIC_LBL]
    label_b = dic_b[mg.STATS_DIC_LBL]
    n_a = dic_a[mg.STATS_DIC_N]
    n_b = dic_b[mg.STATS_DIC_N]
    title = (_(u"Results of Mann Whitney U Test of \"%(ranked)s\" for "
               u"\"%(a)s\" vs \"%(b)s\"") % {"ranked": label_ranked, 
                                             "a": label_a, "b": label_b})
    title_html = u"<h2>%s</h2>" % title
    html.append(title_html)
    # always footnote 1 (so can hardwire anchor)
    # double one-tailed p value so can report two-tailed result
    html.append(u"\n<p>" + _("Two-tailed p value") \
                + u": %s" % lib.get_p(p*2, dp) + 
                u" <a href='#ft1'><sup>1</sup></a></p>")
    footnotes.append("\n<p><a id='ft%%(ftnum)s'></a>"
                     "<sup>%%(ftnum)s</sup> %s</p>" % mg.P_EXPLAN_DIFF)
    # always footnote 2
    html.append(u"\n<p>" + _("U statistic") +
                u": %s <a href='#ft2'><sup>2</sup></a></p>" % round(u, dp))
    html.append(u"\n<p>z: %s</p>" % round(z, dp))
    footnotes.append((u"\n<p><a id='ft%%(ftnum)s'></a><sup>%%(ftnum)s</sup> U "
        u"is based on the results of matches between "
        u"the \"%(label_a)s\" and \"%(label_b)s\" groups. "
        u"In each match, the winner is the one with the "
        u"highest \"%(label_ranked)s\" "
        u"(in a draw, each group gets half a point which is why U can "
        u"sometimes end in .5). "
        u"The further the number is away from an even "
        u"result i.e. half the number of possible matches "
        u"(i.e. half of %(n_a)s x %(n_b)s i.e. %(even_matches)s) "
        u"the more unlikely the difference is by chance "
        u"alone and the more statistically significant it is.</p>") % 
            {u"label_a": label_a.replace(u"%",u"%%"), 
             u"label_b": label_b.replace(u"%",u"%%"), u"n_a": n_a, 
             u"n_b": n_b, u"label_ranked": label_ranked.replace(u"%",u"%%"),
             u"even_matches": (n_a*n_b)/float(2)})
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
        html.append(row_tpl % (dic[mg.STATS_DIC_LBL], 
                               dic[mg.STATS_DIC_N], 
                               round(dic[mg.STATS_DIC_MEDIAN], dp), 
                               round(dic["avg rank"], dp),
                               dic[mg.STATS_DIC_MIN], 
                               dic[mg.STATS_DIC_MAX]))
    html.append(u"\n</tbody>\n</table>\n")
    for i, footnote in enumerate(footnotes):
        next_ft = i + 1
        html.append(footnote % {u"ftnum": next_ft})
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    output.append_divider(html, title, indiv_title=u"")
    return u"".join(html)

def wilcoxon_output(t, p, dic_a, dic_b, css_fil, css_idx=0, dp=3, 
                    level=mg.OUTPUT_RESULTS_ONLY, page_break_after=False):
    CSS_FIRST_COL_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_COL_VAR, css_idx)
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    CSS_LBL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_LBL, css_idx)
    html = []
    footnotes = []
    label_a = dic_a[mg.STATS_DIC_LBL]
    label_b = dic_b[mg.STATS_DIC_LBL]
    title = (_(u"Results of Wilcoxon Signed Ranks Test of \"%(a)s\" vs "
               u"\"%(b)s\"") % {"a": label_a, "b": label_b})
    title_html = u"<h2>%s</h2>" % title
    html.append(title_html)
    # always footnote 1 (so can hardwire anchor)
    html.append(u"\n<p>" + _("Two-tailed p value") + \
                u": %s" % lib.get_p(p, dp) + 
                u" <a href='#ft1'><sup>1</sup></a></p>")
    footnotes.append("\n<p><a id='ft%%s'></a><sup>%%s</sup> %s</p>" % \
                     mg.P_EXPLAN_DIFF)
    html.append(u"\n<p>" + _("Wilcoxon Signed Ranks statistic") + \
                u": %s</p>" % round(t, dp))
    html.append(u"\n\n<table cellspacing='0'>\n<thead>")
    html.append(u"\n<tr>" +
        u"<th class='%s'>" % CSS_FIRST_COL_VAR + _("Variable") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("N") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Median") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Min") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Max") + u"</th></tr>")
    html.append(u"\n</thead>\n<tbody>")
    row_tpl = u"\n<tr><td class='%s'>" % CSS_LBL + u"%s</td><td>%s</td>" + \
        u"<td>%s</td><td>%s</td><td>%s</td></tr>"
    for dic in [dic_a, dic_b]:
        html.append(row_tpl % (dic[mg.STATS_DIC_LBL], 
                               dic[mg.STATS_DIC_N], 
                               round(dic[mg.STATS_DIC_MEDIAN], dp), 
                               dic[mg.STATS_DIC_MIN], 
                               dic[mg.STATS_DIC_MAX]))
    html.append(u"\n</tbody>\n</table>\n")
    for i, footnote in enumerate(footnotes):
        next_ft = i + 1
        html.append(footnote % (next_ft, next_ft))
    if page_break_after:
        html += u"<br><hr><br><div class='%s'></div>" % CSS_PAGE_BREAK_BEFORE
    output.append_divider(html, title, indiv_title=u"")
    return u"".join(html)

def pearsonsr_output(list_x, list_y, r, p, df, label_x, label_y, add_to_report,
                     report_name, css_fil, css_idx=0, dp=3, 
                     level=mg.OUTPUT_RESULTS_ONLY, page_break_after=False):
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    slope, intercept, r, unused, unused = core_stats.linregress(list_x, list_y)
    html = []
    footnotes = []
    x_vs_y = '"%s"' % label_x + _(" vs ") + '"%s"' % label_y
    title = (_("Results of Pearson's Test of Linear Correlation for %s") % 
             x_vs_y)
    title_html = "<h2>%s</h2>" % title
    html.append(title_html)
    # always footnote 1 (so can hardwire anchor)
    html.append(u"\n<p>" + _("Two-tailed p value") + \
                u": %s" % lib.get_p(p, dp) + 
                u" <a href='#ft1'><sup>1</sup></a></p>")
    footnotes.append(u"\n<p><a id='ft%%s'></a><sup>%%s</sup> %s</p>" % \
                     mg.P_EXPLAN_REL)
    html.append(u"\n<p>" + _("Pearson's R statistic") +
                u": %s</p>" % round(r, dp))
    html.append(u"\n<p>" + mg.DF + u": %s</p>" % df)
    html.append(u"<p>Linear Regression Details: "
                u"<a href='#ft2'><sup>2</sup></a></p>")
    footnotes.append(u"\n<p><a id='ft%s'></a><sup>%s</sup>"
        u"Always look at the scatter plot when interpreting the linear "
        u"regression line.</p>")
    html.append(u"<ul><li>Slope: %s</li>" % round(slope, dp))
    html.append(u"<li>Intercept: %s</li></ul>" % round(intercept, dp))
    output.append_divider(html, title, indiv_title=u"")
    grid_bg, dot_colours, line_colour = output.get_stats_chart_colours(css_fil)
    title_dets_html = u"" # already got an appropriate title for whole section
    dot_borders = True
    def gety(x, slope, intercept):
        y = (x*slope) + intercept
        return y
    minx = min(list_x)
    maxx = max(list_x)
    series_dets = [{mg.CHARTS_SERIES_LBL_IN_LEGEND: None, # None if only one series
                    mg.LIST_X: list_x, mg.LIST_Y: list_y, mg.DATA_TUPS: None}] # only Dojo needs data_tups
    line_lst = [gety(minx, slope, intercept), gety(maxx, slope, intercept)]
    charting_pylab.add_scatterplot(grid_bg, dot_borders, line_colour, 
                                   series_dets, label_x, label_y, x_vs_y, 
                                   title_dets_html, add_to_report, 
                                   report_name, html, line_lst=line_lst, 
                                   line_lbl=u"Regression line", 
                                   dot_colour=dot_colours[0])
    for i, footnote in enumerate(footnotes):
        next_ft = i + 1
        html.append(footnote % (next_ft, next_ft))
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    output.append_divider(html, title, indiv_title=u"scatterplot")
    return u"".join(html)

def spearmansr_output(list_x, list_y, r, p, df, label_x, label_y, add_to_report,
                      report_name, css_fil, css_idx=0, dp=3, 
                      level=mg.OUTPUT_RESULTS_ONLY, page_break_after=False):
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    html = []
    footnotes = []
    x_vs_y = '"%s"' % label_x + _(" vs ") + '"%s"' % label_y
    title = (_("Results of Spearman's Test of Linear Correlation "
               "for %s") % x_vs_y)
    title_html = "<h2>%s</h2>" % title
    html.append(title_html)
    # always footnote 1 (so can hardwire anchor)
    html.append(u"\n<p>" + _("p value") + u": %s" % lib.get_p(p, dp) + 
                u" <a href='#ft1'><sup>1</sup></a></p>")
    footnotes.append("\n<p><a id='ft%%s'></a><sup>%%s</sup> %s</p>" %
                     mg.P_EXPLAN_REL)
    html.append(u"\n<p>" + _("Spearman's R statistic") + 
                u": %s</p>" % round(r, dp))
    html.append(u"\n<p>" + mg.DF + u": %s</p>" % df)
    output.append_divider(html, title, indiv_title=u"")
    grid_bg, dot_colours, line_colour = output.get_stats_chart_colours(css_fil)
    title_dets_html = u"" # already got an appropriate title for whole section
    dot_borders = True
    series_dets = [{mg.CHARTS_SERIES_LBL_IN_LEGEND: None, # None if only one series
                    mg.LIST_X: list_x, mg.LIST_Y: list_y, mg.DATA_TUPS: None}] # only Dojo needs data_tups
    
    charting_pylab.add_scatterplot(grid_bg, dot_borders, line_colour, 
                                   series_dets, label_x, label_y, x_vs_y, 
                                   title_dets_html, add_to_report, 
                                   report_name, html, dot_colour=dot_colours[0])
    for i, footnote in enumerate(footnotes):
        next_ft = i + 1
        html.append(footnote % (next_ft, next_ft))
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    output.append_divider(html, title, indiv_title=u"scatterplot")
    return u"".join(html)

def chisquare_output(chi, p, var_label_a, var_label_b, add_to_report, 
                     report_name, val_labels_a, val_labels_b, lst_obs, lst_exp, 
                     min_count, perc_cells_lt_5, df, css_fil, css_idx=0, dp=3, 
                     level=mg.OUTPUT_RESULTS_ONLY, page_break_after=False):
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
    footnotes = []
    title = (_("Results of Pearson's Chi Square Test of Association Between "
               "\"%(laba)s\" and \"%(labb)s\"") % {u"laba": var_label_a, 
                                                   u"labb": var_label_b})
    title_html = u"<h2>%s</h2>" % title
    html.append(title_html)
    # always footnote 1 (so can hardwire anchor)
    html.append(u"\n<p>" + _("p value") + u": %s" % lib.get_p(p, dp) + 
                u" <a href='#ft1'><sup>1</sup></a></p>")
    footnotes.append("\n<p><a id='ft%%s'></a><sup>%%s</sup> %s</p>" % \
                     mg.P_EXPLAN_REL)  
    html.append(u"\n<p>" + _("Pearson's Chi Square statistic") + u": %s</p>" %
                round(chi, dp))
    html.append(u"\n<p>" + mg.DF + u": %s</p>" % df)
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
    for val_a in val_labels_a_html:
        row_obs_tot = 0
        row_exp_tot = 0
        html.append(u"<td class='%s'>%s</td>" % (CSS_ROW_VAL, val_a))        
        for col_i, unused in enumerate(val_labels_b_html):
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
    for i, footnote in enumerate(footnotes):
        next_ft = i + 1
        html.append(footnote % (next_ft, next_ft))
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    # clustered bar charts
    grid_bg, item_colours, line_colour = output.get_stats_chart_colours(css_fil)
    output.append_divider(html, title, indiv_title=u"")
    add_clustered_barcharts(grid_bg, item_colours, line_colour, lst_obs, 
                            var_label_a, var_label_b, val_labels_a, 
                            val_labels_b, val_labels_a_n, val_labels_b_n, 
                            add_to_report, report_name, html)
    return u"".join(html)

def get_xaxis_fontsize(val_labels):
    maxlen = max(len(x) for x in val_labels)
    if maxlen > 15:
        fontsize = 7
    elif maxlen > 10:
        fontsize = 9
    elif maxlen > 7:
        fontsize = 10
    else:
        fontsize = 11
    return fontsize

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
    title = title_tmp % {"laba": var_label_a, "labb": var_label_b, "y": y_label}
    plot.setTitle(title)
    plot.setTitleProperties(title_overrides)
    plot.setDimensions(7) # allow height to be set by golden ratio
    plot.hasLegend(columns=val_labels_b_n, location="lower left")
    plot.setAxesLabelSize(11)
    plot.setXTickLabelSize(get_xaxis_fontsize(val_labels_a))
    plot.setLegendLabelSize(9)
    charting_pylab.config_clustered_barchart(grid_bg, bar_colours, line_colour, 
                                    plot, var_label_a, y_label, val_labels_a_n, 
                                    val_labels_a, val_labels_b, 
                                    propns_as_in_bs_lst)
    img_src = charting_pylab.save_report_img(add_to_report, report_name, 
                                             save_func=plot.save, dpi=None)
    html.append(u"\n%s%s%s" % (mg.IMG_SRC_START, img_src, mg.IMG_SRC_END))
    output.append_divider(html, title, indiv_title=u"proportion")
    # chart 2 - freqs
    plot = boomslang.Plot()
    y_label = _("Frequency")
    title = title_tmp % {"laba": var_label_a, "labb": var_label_b, "y": y_label}
    plot.setTitle(title)
    plot.setTitleProperties(title_overrides)
    plot.setDimensions(7) # allow height to be set by golden ratio
    plot.hasLegend(columns=val_labels_b_n, location="lower left")
    plot.setAxesLabelSize(11)
    plot.setXTickLabelSize(get_xaxis_fontsize(val_labels_a))
    plot.setLegendLabelSize(9)
    # only need 6 because program limits to that. See core_stats.get_obs_exp().
    charting_pylab.config_clustered_barchart(grid_bg, bar_colours, line_colour, 
                                    plot, var_label_a, y_label, val_labels_a_n, 
                                    val_labels_a, val_labels_b, as_in_bs_lst)
    img_src = charting_pylab.save_report_img(add_to_report, report_name, 
                                             save_func=plot.save, dpi=None)
    html.append(u"\n%s%s%s" % (mg.IMG_SRC_START, img_src, mg.IMG_SRC_END))
    output.append_divider(html, title, indiv_title=u"frequency")

def kruskal_wallis_output(h, p, label_a, label_b, dics, df, label_avg, css_fil, 
                          css_idx=0, dp=3, level=mg.OUTPUT_RESULTS_ONLY, 
                          page_break_after=False):
    CSS_FIRST_COL_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_COL_VAR, css_idx)
    CSS_LBL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_LBL, css_idx)
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
                                                      css_idx)
    html = []
    footnotes = []
    title = (_(u"Results of Kruskal-Wallis H test of average %(avg)s for "
               u"groups from \"%(a)s\" to \"%(b)s\"") % {"avg": label_avg, 
                                                   "a": label_a, "b": label_b})
    title_html = u"<h2>%s</h2>" % title
    html.append(title_html)
    # always footnote 1 (so can hardwire anchor)
    html.append(u"\n<p>" + _("p value") + u": %s" % lib.get_p(p, dp) + 
                u" <a href='#ft1'><sup>1</sup></a></p>")
    footnotes.append("\n<p><a id='ft%%s'></a><sup>%%s</sup> %s</p>" % \
                     mg.P_EXPLAN_DIFF) 
    html.append("\n<p>" + _("Kruskal-Wallis H statistic") + ": %s</p>" % \
                                                                round(h, dp))
    html.append(u"\n<p>" + mg.DF + u": %s</p>" % df)
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
        html.append(row_tpl % (dic[mg.STATS_DIC_LBL], 
                               dic[mg.STATS_DIC_N], 
                               round(dic[mg.STATS_DIC_MEDIAN], dp),
                               dic[mg.STATS_DIC_MIN], 
                               dic[mg.STATS_DIC_MAX]))
    html.append(u"\n</tbody></table>")
    for i, footnote in enumerate(footnotes):
        next_ft = i + 1
        html.append(footnote % (next_ft, next_ft))
    if page_break_after:
        html.append("<br><hr><br><div class='%s'></div>" % 
                    CSS_PAGE_BREAK_BEFORE)
    output.append_divider(html, title, indiv_title=u"")
    return u"".join(html)
