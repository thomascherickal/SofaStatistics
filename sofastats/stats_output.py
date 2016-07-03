#! -*- coding: utf-8 -*-
import cgi
import numpy as np
import boomslang
import pylab

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import lib
from sofastats import charting_pylab
from sofastats import core_stats
from sofastats import output

"""
Output doesn't include the calculation of any values. These are in discrete
    functions in core_stats, amenable to unit testing.
No html header or footer added here. Just some body content.    
"""

def add_footnote(footnotes, content):
    footnotes.append("\n<p><a id='ft%%(ftnum)s'></a><sup>%%(ftnum)s</sup> %s"
        u"</p>" % content)

def add_footnotes(footnotes, html):
    for i, footnote in enumerate(footnotes):
        next_ft = i + 1
        html.append(footnote % {u"ftnum": next_ft})

def _p_msg(p_sim):
    return lib.OutputLib.to_precision(num=p_sim, precision=4)

def anova_output(samples, F, p, dics, sswn, dfwn, mean_squ_wn, ssbn, dfbn, 
        mean_squ_bn, label_gp, label_a, label_b, label_avg, add_to_report, 
        report_name, css_fil, css_idx=0, dp=mg.DEFAULT_STATS_DP, details=None,
        page_break_after=False):
    debug = False
    CSS_FIRST_COL_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_COL_VAR, css_idx)
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
        css_idx)
    CSS_LBL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_LBL, css_idx)
    CSS_TBL_HDR_FTNOTE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_TBL_HDR_FTNOTE, 
        css_idx)
    CSS_ALIGN_RIGHT = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_ALIGN_RIGHT, css_idx)
    footnotes = []
    html = []
    title = _(u"Results of ANOVA test of average %(avg)s for %(label_gp)s "
        u"groups from \"%(a)s\" to \"%(b)s\"") % {u"label_gp": label_gp, 
        u"avg": label_avg, u"a": label_a, u"b": label_b}
    html_title = u"<h2>%s</h2>" % title
    html.append(mg.TBL_TITLE_START + html_title + mg.TBL_TITLE_END)
    html.append(u"\n\n<h3>" + mg.TBL_SUBTITLE_START 
        + _("Analysis of variance table") + mg.TBL_SUBTITLE_END + u"</h3>")
    html.append(u"\n%s<table cellspacing='0'>\n<thead>" % mg.REPORT_TABLE_START)
    html.append(u"\n<tr>" +
        u"<th class='%s'>" % CSS_FIRST_COL_VAR + _("Source") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Sum of Squares") +
            u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("df") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Mean Sum of Squares") +
            u"</th>" +
        u"\n<th class='%s'>F</th>" % CSS_FIRST_COL_VAR)
    # always footnote 1 (so can hardwire anchor)
    html.append(u"\n<th class='%s'>" % CSS_FIRST_COL_VAR +
        u"p<a class='%s' href='#ft1'><sup>1</sup></a></th></tr>" %
        CSS_TBL_HDR_FTNOTE)
    add_footnote(footnotes, content=mg.P_EXPLAN_DIFF)
    html.append(u"\n</thead>\n<tbody>")
    tpl = "%%.%sf" % dp
    html.append(u"\n<tr><td>" + _("Between") + u"</td>"
        u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" % 
        (tpl % round(ssbn, dp)) + u"<td class='%s'>" % CSS_ALIGN_RIGHT 
        + u"%s</td>" % dfbn)
    html.append(u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" % 
        (tpl % round(mean_squ_bn, dp)) + u"<td class='%s'>" 
        % CSS_ALIGN_RIGHT + u"%s</td>" % (tpl % round(F, dp)) +
        u"<td>%s</td></tr>" % lib.OutputLib.get_p(p))
    html.append(u"\n<tr><td>" + _("Within") +
        u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" % 
        (tpl % round(sswn, dp)) + u"<td class='%s'>" % CSS_ALIGN_RIGHT 
        + u"%s</td>" %  dfwn)
    html.append(u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" % 
        (tpl % round(mean_squ_wn, dp)) + u"<td></td><td></td></tr>")
    html.append(u"\n</tbody>\n</table>%s\n" % mg.REPORT_TABLE_END)
    output.append_divider(html, title, indiv_title=u"Analysis of Variance")
    try:
        unused, p_sim = core_stats.sim_variance(samples, threshold=0.01)
        msg = _p_msg(p_sim)
    except Exception:
        msg = "Unable to calculate"
    # footnote 2
    html.append(u"\n<p>" + _("O'Brien's test for homogeneity of variance")
        + u": %s" % msg + u" <a href='#ft2'><sup>2</sup></a></p>")
    add_footnote(footnotes, content=mg.OBRIEN_EXPLAN)
    html.append(mg.TBL_TITLE_START + mg.TBL_TITLE_END)
    html.append(u"\n\n<h3>"  + mg.TBL_SUBTITLE_START 
        + _("Group summary details")  + mg.TBL_SUBTITLE_END + u"</h3>")
    html.append(u"\n%s<table cellspacing='0'>\n<thead>" % mg.REPORT_TABLE_START)
    html.append(u"\n<tr><th class='%s'>" % CSS_FIRST_COL_VAR + _("Group") +
        u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("N") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Mean") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("CI 95%") + 
        u"<a class='%s" % CSS_TBL_HDR_FTNOTE 
        + u"' href='#ft3'><sup>3</sup></a></th>")
    # footnote 3
    add_footnote(footnotes, content=mg.CI_EXPLAN)
    # footnote 4
    html.append(u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + 
        _("Standard Deviation") + u"<a class='%s" % CSS_TBL_HDR_FTNOTE +
        "' href='#ft4'><sup>4</sup></a></th>")
    add_footnote(footnotes, content=mg.STD_DEV_EXPLAN)
    html.append(u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Min") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Max") + u"</th>")
    # footnotes 5,6,7
    html.append(u"<th class='%s'>" % CSS_FIRST_COL_VAR + _("Kurtosis") + 
        u"<a class='%s' href='#ft5'><sup>5</sup></a></th>" % CSS_TBL_HDR_FTNOTE)
    html.append(u"<th class='%s'>" % CSS_FIRST_COL_VAR + _("Skew") + 
        u"<a class='%s' href='#ft6'><sup>6</sup></a></th>" % CSS_TBL_HDR_FTNOTE)
    html.append(u"<th class='%s'>" % CSS_FIRST_COL_VAR + _("p abnormal") + 
        u"<a class='%s' href='#ft7'><sup>7</sup></a></th>" % CSS_TBL_HDR_FTNOTE)
    html.append(u"</tr>")
    add_footnote(footnotes, content=mg.KURT_EXPLAN)
    add_footnote(footnotes, content=mg.SKEW_EXPLAN)
    add_footnote(footnotes, content=mg.NORMALITY_MEASURE_EXPLAN)
    html.append(u"\n</thead>\n<tbody>")
    row_tpl = (u"\n<tr>"
        u"<td class='%s'>" % CSS_LBL + u"%s</td>" +
        u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" +
        u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" +
        u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" +
        u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" +
        u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" +
        u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" +
        u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" +
        u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" +
        u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td></tr>")
    dic_sample_tups = zip(dics, samples)
    for dic, sample in dic_sample_tups:
        results = (dic[mg.STATS_DIC_LBL],
            lib.formatnum(dic[mg.STATS_DIC_N]),
            round(dic[mg.STATS_DIC_MEAN], dp), "%s - %s" % 
            (tpl % round(dic[mg.STATS_DIC_CI][0], dp), 
            tpl % round(dic[mg.STATS_DIC_CI][1], dp)), 
            tpl % round(dic[mg.STATS_DIC_SD], dp), dic[mg.STATS_DIC_MIN], 
            dic[mg.STATS_DIC_MAX])
        try:
            (unused, p_arr, cskew, 
             unused, ckurtosis, unused) = core_stats.normaltest(sample)
            extra_results = []
            try:
                kurt = tpl % round(ckurtosis, dp)
                extra_results.append(kurt)
            except Exception:
                extra_results.append(_("Unable to calculate kurtosis"))
            try:
                skew = tpl % round(cskew, dp)
                extra_results.append(skew)
            except Exception:
                extra_results.append(_("Unable to calculate skew"))
            try:
                overall_p = lib.OutputLib.get_p(p_arr[0])
                extra_results.append(overall_p)
            except Exception:
                extra_results.append(_(u"Unable to calculate overall p for "
                    u"normality test"),)
            results += tuple(extra_results)
        except Exception:
            results += (_("Unable to calculate kurtosis"), 
                _("Unable to calculate skew"),
                _("Unable to calculate overall p for normality test"),
            )
        html.append(row_tpl % results)
    html.append(u"\n</tbody>\n</table>%s\n" % mg.REPORT_TABLE_END)
    add_footnotes(footnotes, html)    
    output.append_divider(html, title, indiv_title=u"Group Summary")
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
        css_dojo_dic = lib.OutputLib.extract_dojo_style(css_fil)
        item_colours = output.colour_mappings_to_item_colours(
            css_dojo_dic['colour_mappings'])
        try:
            charting_pylab.config_hist(fig, sample, label_avg, histlbl, False, 
                css_dojo_dic['plot_bg'], item_colours[0],
                css_dojo_dic['major_gridline_colour'])
            img_src = charting_pylab.save_report_img(add_to_report, report_name, 
                save_func=pylab.savefig, dpi=100)
            html.append(u"\n%s%s%s" % (mg.IMG_SRC_START, img_src, 
                mg.IMG_SRC_END))
        except Exception, e:
            html.append(u"<b>%s</b> - unable to display histogram. Reason: %s" % 
                (histlbl, b.ue(e)))
        output.append_divider(html, title, indiv_title=histlbl)
    ## details
    if details:
        html.append(u"""<p>No worked example available for this test</p>""")
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
            CSS_PAGE_BREAK_BEFORE)
    return u"".join(html)

def ttest_basic_results(sample_a, sample_b, t, p, label_gp, dic_a, dic_b, df, 
        label_avg, dp, indep, css_idx, html):
    """
    Footnotes are autonumbered at end. The links to them will need numbering 
        though.
    """
    CSS_FIRST_COL_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_COL_VAR, css_idx)
    CSS_LBL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_LBL, css_idx)
    CSS_TBL_HDR_FTNOTE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_TBL_HDR_FTNOTE, 
        css_idx)
    CSS_ALIGN_RIGHT = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_ALIGN_RIGHT, css_idx)
    footnotes = []
    if indep:
        title = (_(u"Results of Independent Samples t-test of average "
            u"\"%(avg)s\" for %(label_gp)s groups \"%(a)s\" vs \"%(b)s\"") % 
            {"label_gp": label_gp, "avg": label_avg, 
            "a": dic_a[mg.STATS_DIC_LBL], "b": dic_b[mg.STATS_DIC_LBL]})
    else:
        title = (_("Results of Paired Samples t-test of \"%(a)s\" vs \"%(b)s\"") 
            % {"a": dic_a[mg.STATS_DIC_LBL], "b": dic_b[mg.STATS_DIC_LBL]})
    title_html = u"%s\n<h2>%s</h2>\n%s" % (mg.TBL_TITLE_START, title,
        mg.TBL_TITLE_END)
    html.append(title_html)
    html.append(mg.TBL_SUBTITLE_START + mg.TBL_SUBTITLE_END)
    # always footnote 1 (so can hardwire anchor)
    html.append(u"\n<p>" + _("p value") + u": %s" % lib.OutputLib.get_p(p) + 
        u" <a href='#ft1'><sup>1</sup></a></p>")
    add_footnote(footnotes, content=mg.P_EXPLAN_DIFF)
    html.append(u"\n<p>" + _("t statistic") + u": %s</p>" % round(t, dp))
    html.append(u"\n<p>" + mg.DF + u": %s</p>" % df)
    if indep:
        try:
            unused, p_sim = core_stats.sim_variance([sample_a, sample_b], 
                threshold=0.01)
            msg = _p_msg(p_sim)
        except Exception:
            msg = "Unable to calculate"
        # always footnote 2 if present
        html.append(u"\n<p>" + _("O'Brien's test for homogeneity of variance")
            + u": %s" % msg + u" <a href='#ft2'><sup>2</sup></a></p>")
        add_footnote(footnotes, content=mg.OBRIEN_EXPLAN)
    html.append(u"\n\n%s<table cellspacing='0'>\n<thead>" % 
        mg.REPORT_TABLE_START)
    next_ft = len(footnotes) + 1
    html.append(u"\n<tr>" + \
        u"<th class='%s'>" % CSS_FIRST_COL_VAR + _("Group") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("N") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Mean") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("CI 95%")  + 
        u"<a class='%s" % CSS_TBL_HDR_FTNOTE +
        u"' href='#ft%s'><sup>%s</sup></a></th>" % (next_ft, next_ft) +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Standard Deviation") +
        u"<a class='%s' href='#ft%s'><sup>%s</sup></a></th>" % 
        (CSS_TBL_HDR_FTNOTE, next_ft+1, next_ft+1) +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Min") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Max") + u"</th>")
    add_footnote(footnotes, content=mg.CI_EXPLAN)
    add_footnote(footnotes, content=mg.STD_DEV_EXPLAN)
    if indep:
        # if here, always 5,6,7
        html.append(u"<th class='%s'>" % CSS_FIRST_COL_VAR + _("Kurtosis") + 
            u"<a class='%s' href='#ft5'><sup>5</sup></a></th>" % 
            CSS_TBL_HDR_FTNOTE)
        html.append(u"<th class='%s'>" % CSS_FIRST_COL_VAR + _("Skew") + 
            u"<a class='%s' href='#ft6'><sup>6</sup></a></th>" %
            CSS_TBL_HDR_FTNOTE)
        html.append(u"<th class='%s'>" % CSS_FIRST_COL_VAR + _("p abnormal") + 
            u"<a class='%s' href='#ft7'><sup>7</sup></a></th>" %
            CSS_TBL_HDR_FTNOTE)
        add_footnote(footnotes, content=mg.KURT_EXPLAN)
        add_footnote(footnotes, content=mg.SKEW_EXPLAN)
        add_footnote(footnotes, content=mg.NORMALITY_MEASURE_EXPLAN)
    tpl = "%%.%sf" % dp
    html.append(u"</tr>")
    html.append(u"\n</thead>\n<tbody>")
    if indep:
        row_tpl = (u"\n<tr><td class='%s'>" % CSS_LBL + u"%s</td>" +
            u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" +
            u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" +
            u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" +
            u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" +
            u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" +
            u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" +
            u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" +
            u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" +
            u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td></tr>")
    else:
        row_tpl = (u"\n<tr><td class='%s'>" % CSS_LBL + u"%s</td>" +
            u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" +
            u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" +
            u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" +
            u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" +
            u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td>" +
            u"<td class='%s'>" % CSS_ALIGN_RIGHT + u"%s</td></tr>")
    for dic, sample in [(dic_a, sample_a), (dic_b, sample_b)]:
        results = (dic[mg.STATS_DIC_LBL],
            lib.formatnum(dic[mg.STATS_DIC_N]),
            round(dic[mg.STATS_DIC_MEAN], dp), "%s - %s" % 
            (tpl % round(dic[mg.STATS_DIC_CI][0], dp), 
            tpl % round(dic[mg.STATS_DIC_CI][1], dp)), 
            tpl % round(dic[mg.STATS_DIC_SD], dp), 
            dic[mg.STATS_DIC_MIN], dic[mg.STATS_DIC_MAX])
        if indep:
            try:
                (unused, p_arr, cskew, unused, 
                 ckurtosis, unused) = core_stats.normaltest(sample)
                kurt = tpl % round(ckurtosis, dp)
                skew = tpl % round(cskew, dp)
                overall_p = lib.OutputLib.get_p(p_arr[0])
                results += (kurt, skew, overall_p)
            except Exception:
                results += (_("Unable to calculate kurtosis"), 
                    _("Unable to calculate skew"),
                    _("Unable to calculate overall p for normality test"),
                )
        html.append(row_tpl % results)
    html.append(u"\n</tbody>\n</table>%s\n" % mg.REPORT_TABLE_END)
    html.append("\n<hr class='ftnote-line'>")
    add_footnotes(footnotes, html)
    return title

def ttest_indep_output(sample_a, sample_b, t, p, label_gp, dic_a, dic_b, df, 
        label_avg, add_to_report, report_name, css_fil, css_idx=0,
        dp=mg.DEFAULT_STATS_DP, details=None, page_break_after=False):
    """
    Returns HTML table ready to display.
    dic_a = {"label": label_a, "n": n_a, "mean": mean_a, "sd": sd_a, 
        "min": min_a, "max": max_a}
    """
    html = []
    indep = True
    title = ttest_basic_results(sample_a, sample_b, t, p, label_gp, dic_a, 
        dic_b, df, label_avg, dp, indep, css_idx, html)
    output.append_divider(html, title, indiv_title=u"")
    sample_dets = [(u"a", sample_a, dic_a["label"]), 
        (u"b", sample_b, dic_b["label"])]
    for unused, sample, histlbl in sample_dets:
        # histogram
        # http://www.scipy.org/Cookbook/Matplotlib/LaTeX_Examples
        charting_pylab.gen_config(axes_labelsize=10, xtick_labelsize=8, 
            ytick_labelsize=8)
        fig = pylab.figure()
        fig.set_size_inches((5.0, 3.5)) # see dpi to get image size in pixels
        css_dojo_dic = lib.OutputLib.extract_dojo_style(css_fil)
        item_colours = output.colour_mappings_to_item_colours(
            css_dojo_dic['colour_mappings'])
        try:
            charting_pylab.config_hist(fig, sample, label_avg, histlbl, False, 
                css_dojo_dic['plot_bg'], item_colours[0],
                css_dojo_dic['major_gridline_colour'])
            img_src = charting_pylab.save_report_img(add_to_report, report_name, 
                save_func=pylab.savefig, dpi=100)
            html.append(u"\n%s%s%s" % (mg.IMG_SRC_START, img_src, 
                mg.IMG_SRC_END))
        except Exception, e:
            html.append(u"<b>%s</b> - unable to display histogram. Reason: %s" % 
                (histlbl, b.ue(e)))
        output.append_divider(html, title, indiv_title=histlbl)
    ## details
    if details:
        html.append(u"""<p>No worked example available for this test</p>""")
    if page_break_after:
        CSS_PAGE_BREAK_BEFORE = (mg.CSS_SUFFIX_TEMPLATE %
            (mg.CSS_PAGE_BREAK_BEFORE, css_idx))
        html.append(u"<br><hr><br><div class='%s'></div>" %
            CSS_PAGE_BREAK_BEFORE)
    html_str = u"\n".join(html)
    return html_str

def ttest_paired_output(sample_a, sample_b, t, p, dic_a, dic_b, df, diffs, 
        add_to_report, report_name, css_fil, css_idx=0, label_avg=u"",
        dp=mg.DEFAULT_STATS_DP, details=None, page_break_after=False):
    """
    Returns HTML table ready to display.
    dic_a = {"label": label_a, "n": n_a, "mean": mean_a, "sd": sd_a,
        "min": min_a, "max": max_a}
    """
    html = []
    indep = False
    label_gp = None
    title = ttest_basic_results(sample_a, sample_b, t, p, label_gp, dic_a,
        dic_b, df, label_avg, dp, indep, css_idx, html)
    output.append_divider(html, title, indiv_title=u"")
    # histogram
    histlbl = u"Differences between %s and %s" % (dic_a["label"], 
        dic_b["label"])
    charting_pylab.gen_config(axes_labelsize=10, xtick_labelsize=8,
        ytick_labelsize=8)
    fig = pylab.figure()
    fig.set_size_inches((7.5, 3.5)) # see dpi to get image size in pixels
    css_dojo_dic = lib.OutputLib.extract_dojo_style(css_fil)
    item_colours = output.colour_mappings_to_item_colours(
        css_dojo_dic['colour_mappings'])
    try:
        charting_pylab.config_hist(fig, diffs, _("Differences"), histlbl, False,
            css_dojo_dic['plot_bg'], item_colours[0],
            css_dojo_dic['major_gridline_colour'])
        img_src = charting_pylab.save_report_img(add_to_report, report_name,
            save_func=pylab.savefig, dpi=100)
        html.append(u"\n%s%s%s" % (mg.IMG_SRC_START, img_src, mg.IMG_SRC_END))
    except Exception, e:
        html.append(u"<b>%s</b> - unable to display histogram. Reason: %s" % 
            (histlbl, b.ue(e)))
    ## details
    if details:
        html.append(u"""<p>No worked example available for this test</p>""")
    if page_break_after:
        CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % \
            (mg.CSS_PAGE_BREAK_BEFORE, css_idx)
        html.append(u"<br><hr><br><div class='%s'></div>" %
            CSS_PAGE_BREAK_BEFORE)
    output.append_divider(html, title, indiv_title=histlbl)
    html_str = u"\n".join(html)
    return html_str

def mann_whitney_output(u, p, label_gp, dic_a, dic_b, z, label_ranked, css_fil, 
        css_idx=0, dp=mg.DEFAULT_STATS_DP, details=None,
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
        u"%(label_gp)s \"%(a)s\" vs \"%(b)s\"") % {"label_gp": label_gp, 
        "ranked": label_ranked, "a": label_a, "b": label_b})
    title_html = u"%s\n<h2>%s</h2>\n%s" % (mg.TBL_TITLE_START, title,
        mg.TBL_TITLE_END)
    html.append(title_html)
    html.append(mg.TBL_SUBTITLE_START + mg.TBL_SUBTITLE_END)
    # always footnote 1 (so can hardwire anchor)
    # double one-tailed p value so can report two-tailed result
    html.append(u"\n<p>" + _("Two-tailed p value") + u": %s" % 
        lib.OutputLib.get_p(p*2) + u" <a href='#ft1'><sup>1</sup></a></p>")
    add_footnote(footnotes, content=mg.P_EXPLAN_DIFF)
    # always footnote 2
    html.append(u"\n<p>" + _("U statistic") +
        u": %s <a href='#ft2'><sup>2</sup></a></p>" % round(u, dp))
    html.append(u"\n<p>z: %s</p>" % round(z, dp))
    add_footnote(footnotes, content=(u"U is based on the results of matches "
        u"between the \"%(label_a)s\" and \"%(label_b)s\" groups. "
        u"In each match,<br>the winner is the one with the "
        u"highest \"%(label_ranked)s\" "
        u"(in a draw, each group gets half a point which is<br>why U can "
        u"sometimes end in .5). "
        u"The further the number is away from an even result<br>"
        u" i.e. half the number of possible matches "
        u"(i.e. half of %(n_a)s x %(n_b)s in this case i.e. %(even_matches)s)"
        u"<br>the more unlikely the difference is by chance "
        u"alone and the more statistically significant it is.</p>") % 
        {u"label_a": label_a.replace(u"%",u"%%"), 
         u"label_b": label_b.replace(u"%",u"%%"), u"n_a": n_a, 
         u"n_b": n_b, u"label_ranked": label_ranked.replace(u"%",u"%%"),
         u"even_matches": (n_a*n_b)/float(2)})
    html.append(u"\n\n%s<table cellspacing='0'>\n<thead>" % 
        mg.REPORT_TABLE_START)
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
            lib.formatnum(dic[mg.STATS_DIC_N]),
            round(dic[mg.STATS_DIC_MEDIAN], dp), round(dic["avg rank"], dp),
            dic[mg.STATS_DIC_MIN], dic[mg.STATS_DIC_MAX]))
    html.append(u"\n</tbody>\n</table>%s\n" % mg.REPORT_TABLE_END)
    add_footnotes(footnotes, html)
    if details:
        html.append(u"""
        <hr>
        <h2>Worked Example of Key Calculations</h2>
        <p>Note - the method shown below is based on ranked values of the data
        as a whole, not on every possible comparison - but the result is exactly
        the same. Working with ranks is much more efficient.</p>
        <h3>Step 1 - Add ranks to all values</h3>
        <p>Note on ranking - rank such that all examples of a value get the
        median rank for all items of that value.</p>
        <p>If calculating by hand, and one sample is shorter than the others,
        make that the first sample to reduce the number of calculations</p>
        <p>For the rest of this worked example, sample 1 is "%s" and sample 2 is
        "%s".""" % (details[mg.MANN_WHITNEY_LABEL_1],
            details[mg.MANN_WHITNEY_LABEL_2]))
        html.append(u"""<table>
        <thead>
            <tr>
                <th>Sample</th>
                <th>Value</th>
                <th>Counter</th>
                <th>Rank</th>
            </tr>
        </thead>
        <tbody>""")
        val_dets = details[mg.MANN_WHITNEY_VAL_DETS]
        MAX_DISPLAY_ROWS = 50
        for val_det in val_dets[:MAX_DISPLAY_ROWS]:
            html.append(u"""
            <tr>
                <td>%(sample)s</td>
                <td>%(val)s</td>
                <td>%(counter)s</td>
                <td>%(rank)s</td>
            </tr>""" % val_det)
        diff = len(val_dets) - MAX_DISPLAY_ROWS
        if diff > 0: 
            html.append(u"""
            <tr><td colspan="4">%s rows not displayed</td></tr>""" % diff)
        html.append(u"""
        </tbody>
        </table>""")
        html.append(u"<h3>Step 2 - Sum the ranks for sample 1</h3>")
        val_1s2add = [str(x)
            for x in details[mg.MANN_WHITNEY_RANKS_1][:MAX_DISPLAY_ROWS]]
        diff_ranks_1 = details[mg.MANN_WHITNEY_N_1] - MAX_DISPLAY_ROWS
        if diff_ranks_1 > 0:
            val_1s2add.append(u"%s other values not displayed" %
                lib.formatnum(diff_ranks_1))
        html.append(u"""<p>sum_ranks<sub>1</sub> = """ + u" + ".join(val_1s2add) +
        u" i.e. <strong>%(sum_rank_1)s</strong></p>""" %
            {u"sum_rank_1": lib.formatnum(details[mg.MANN_WHITNEY_SUM_RANK_1])})
        html.append(u"""<h3>Step 3 - Calculate U for sample 1 as per:</h3>
        <p>u<sub>1</sub> = n<sub>1</sub>*n<sub>2</sub> + ((n<sub>1</sub>*(n<sub>1</sub> + 1))/2.0) - sum_ranks<sub>1</sub></p>""")
        html.append(u"""<p>u<sub>1</sub> = %(n_1)s*%(n_2)s + (%(n_1)s*(%(n_1)s+1))/2 -
        %(sum_rank_1)s i.e. <strong>%(u_1)s</strong></p>""" %
            {u"n_1": lib.formatnum(details[mg.MANN_WHITNEY_N_1]),
             u"n_2": lib.formatnum(details[mg.MANN_WHITNEY_N_2]),
             u"sum_rank_1": lib.formatnum(details[mg.MANN_WHITNEY_SUM_RANK_1]),
             u"u_1": lib.formatnum(details[mg.MANN_WHITNEY_U_1])})
        html.append(u"""<h3>Step 4 - Calculate U for sample 2 as per:</h3>
        <p>u<sub>2</sub> = n<sub>1</sub>*n<sub>2</sub> - u<sub>1</sub></p>""")
        html.append(u"""<p>u<sub>2</sub> = %(n_1)s*%(n_2)s - %(u_1)s i.e.
            <strong>%(u_2)s</strong></p>""" %
            {u"n_1": lib.formatnum(details[mg.MANN_WHITNEY_N_1]),
             u"n_2": lib.formatnum(details[mg.MANN_WHITNEY_N_2]),
             u"u_1": lib.formatnum(details[mg.MANN_WHITNEY_U_1]),
             u"u_2": lib.formatnum(details[mg.MANN_WHITNEY_U_2])})
        html.append(u"""<h3>Step 5 - Identify the lowest of the U values</h3>
        <p>The lowest value of %(u_1)s and %(u_2)s is
        <strong>%(u)s</strong></p>
        """ % {u"u_1": lib.formatnum(details[mg.MANN_WHITNEY_U_1]),
               u"u_2": lib.formatnum(details[mg.MANN_WHITNEY_U_2]),
               u"u": lib.formatnum(details[mg.MANN_WHITNEY_U])})
        html.append(u"""<p>After this, you would use the N values and other
        methods to see if the value for U is likely to happen by chance but
        that is outside of the scope of this worked example.</p>""")
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" %
            CSS_PAGE_BREAK_BEFORE)
    output.append_divider(html, title, indiv_title=u"")
    return u"".join(html)

def wilcoxon_output(t, p, dic_a, dic_b, css_fil, css_idx=0,
        dp=mg.DEFAULT_STATS_DP, details=None, page_break_after=False):
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
    title_html = u"%s\n<h2>%s</h2>\n%s" % (mg.TBL_TITLE_START, title,
        mg.TBL_TITLE_END)
    html.append(mg.TBL_SUBTITLE_START + mg.TBL_SUBTITLE_END)
    html.append(title_html)
    # always footnote 1 (so can hardwire anchor)
    html.append(u"\n<p>" + _("Two-tailed p value") + u": %s"
        % lib.OutputLib.get_p(p) + u" <a href='#ft1'><sup>1</sup></a></p>")
    add_footnote(footnotes, content=mg.P_EXPLAN_DIFF)
    html.append(u"\n<p>" + _("Wilcoxon Signed Ranks statistic") +
         u": %s" % round(t, dp) + u" <a href='#ft2'><sup>2</sup></a></p>")
    # http://stat.ethz.ch/R-manual/R-patched/library/stats/html/wilcox.test.html
    add_footnote(footnotes, content=u"Different statistics applications will "
        u"show different results here depending on the reporting approach "
        u"taken.")
    html.append(u"\n\n%s<table cellspacing='0'>\n<thead>" % 
        mg.REPORT_TABLE_START)
    html.append(u"\n<tr>" +
        u"<th class='%s'>" % CSS_FIRST_COL_VAR + _("Variable") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("N") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Median") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Min") + u"</th>" +
        u"\n<th class='%s'>" % CSS_FIRST_COL_VAR + _("Max") + u"</th></tr>")
    html.append(u"\n</thead>\n<tbody>")
    row_tpl = (u"\n<tr><td class='%s'>" % CSS_LBL + u"%s</td><td>%s</td>" +
        u"<td>%s</td><td>%s</td><td>%s</td></tr>")
    for dic in [dic_a, dic_b]:
        html.append(row_tpl % (dic[mg.STATS_DIC_LBL],
            lib.formatnum(dic[mg.STATS_DIC_N]),
            round(dic[mg.STATS_DIC_MEDIAN], dp), dic[mg.STATS_DIC_MIN], 
            dic[mg.STATS_DIC_MAX]))
    html.append(u"\n</tbody>\n</table>%s\n" % mg.REPORT_TABLE_END)
    add_footnotes(footnotes, html)
    ## details
    if details:
        html.append(u"""
        <hr>
        <h2>Worked Example of Key Calculations</h2>
        <h3>Step 1 - Get differences</h3>""")
        html.append(u"""<table>
        <thead>
            <tr>
                <th>%(label_a)s</th><th>%(label_b)s</th><th>Difference</th>
            </tr>
        </thead>
        <tbody>""" % {u'label_a': label_a, u'label_b': label_b})
        diff_dets = details[mg.WILCOXON_DIFF_DETS]
        MAX_DISPLAY_ROWS = 50
        for diff_det in diff_dets[:MAX_DISPLAY_ROWS]:
            html.append(u"""
            <tr>
                <td>%(a)s</td><td>%(b)s</td><td>%(diff)s</td>
            </tr>""" % diff_det)
        diff_diffs = len(diff_dets) - MAX_DISPLAY_ROWS
        if diff_diffs > 0: 
            html.append(u"""
            <tr><td colspan="3">%s rows not displayed</td></tr>""" %
                lib.formatnum(diff_diffs))
        html.append(u"""
        </tbody>
        </table>""")
        html.append(u"""<h3>Step 2 - Sort non-zero differences by absolute value
        and rank</h3>
        <p>Rank such that all examples of a value get the mean rank for all
        items of that value</p>""")
        html.append(u"""<table>
        <thead>
            <tr>
                <th>Difference</th>
                <th>Absolute Difference</th>
                <th>Counter</th>
                <th>Rank<br>(on Abs Diff)</th>
            </tr>
        </thead>
        <tbody>""" % {u'label_a': label_a, u'label_b': label_b})
        ranks_dets = details[mg.WILCOXON_RANKING_DETS]
        for rank_dets in ranks_dets[:MAX_DISPLAY_ROWS]:
            html.append(u"""
            <tr>
                <td>%(diff)s</td>
                <td>%(abs_diff)s</td>
                <td>%(counter)s</td>
                <td>%(rank)s</td>
            </tr>""" % rank_dets)
        diff_ranks = len(ranks_dets) - MAX_DISPLAY_ROWS
        if diff_ranks > 0: 
            html.append(u"""
            <tr><td colspan="4">%s rows not displayed</td></tr>""" %
                lib.formatnum(diff_ranks))
        html.append(u"""
        </tbody>
        </table>""")
        html.append(u"<h3>Step 3 - Sum ranks for positive differences</h3>")
        pos_rank_vals2add = [lib.formatnum(x)
            for x in details[mg.WILCOXON_PLUS_RANKS][:MAX_DISPLAY_ROWS]]
        diff_pos_ranks = len(details[mg.WILCOXON_PLUS_RANKS]) - MAX_DISPLAY_ROWS
        if diff_pos_ranks > 0:
            pos_rank_vals2add.append(u"%s other values not displayed" %
                lib.formatnum(diff_pos_ranks))
        html.append(u"<p>" + u" + ".join(pos_rank_vals2add) +
            u" = <strong>%s</strong>" % lib.formatnum(details[mg.WILCOXON_SUM_PLUS_RANKS])
            + u"</p>")
        html.append(u"<h3>Step 4 - Sum ranks for negative differences</h3>")
        neg_rank_vals2add = [lib.formatnum(x)
            for x in details[mg.WILCOXON_MINUS_RANKS][:MAX_DISPLAY_ROWS]]
        diff_neg_ranks = (len(details[mg.WILCOXON_MINUS_RANKS])
            - MAX_DISPLAY_ROWS)
        if diff_neg_ranks > 0:
            neg_rank_vals2add.append(u"%s other values not displayed" %
                lib.formatnum(diff_neg_ranks))
        html.append(u"<p>" + u" + ".join(neg_rank_vals2add) +
            u" = <strong>%s</strong>" % lib.formatnum(details[mg.WILCOXON_SUM_MINUS_RANKS])
            + u"</p>")
        html.append(u"<h3>Step 5 - Get smallest of sums for positive or "
            u"negative ranks</h3>")
        html.append(u"<p>The lowest value of %(plus)s and %(minus)s is "
            u"%(t)s so Wilcoxon's T statistic is <strong>%(t)s</strong>"
            u"</p>" % {
                u"plus": lib.formatnum(details[mg.WILCOXON_SUM_PLUS_RANKS]),
                u"minus": lib.formatnum(details[mg.WILCOXON_SUM_MINUS_RANKS]),
                u"t": lib.formatnum(details[mg.WILCOXON_T]),
        })
        html.append(u"<h3>Step 6 - Get count of all non-zero diffs</h3>")
        html.append(u"<p>Just the number of records in the table from Step 2 "
            u"i.e. <strong>%s</strong></p>" % lib.formatnum(details[mg.WILCOXON_N]))
        html.append(u"<p>The only remaining question is the probability of a "
            u"sum as large as that observed (T) for a given N value. The "
            u"smaller the N and the bigger the T the less likely the difference"
            u" between %s and %s could occur by chance.</p>" %
            (label_a, label_b))
    if page_break_after:
        html += u"<br><hr><br><div class='%s'></div>" % CSS_PAGE_BREAK_BEFORE
    output.append_divider(html, title, indiv_title=u"")
    return u"".join(html)

def pearsonsr_output(list_x, list_y, pearsons_r, p, df, label_x, label_y,
        add_to_report, report_name, css_fil, css_idx=0, dp=mg.DEFAULT_STATS_DP,
        details=None, page_break_after=False):
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
        css_idx)
    slope, intercept, unused, y0, y1 = core_stats.get_regression_dets(list_x,
        list_y)
    line_lst = [y0, y1]
    html = []
    footnotes = []
    x_vs_y = '"%s"' % label_x + _(" vs ") + '"%s"' % label_y
    title = (_("Results of Pearson's Test of Linear Correlation for %s") % 
        x_vs_y)
    title_html = "<h2>%s</h2>" % title
    html.append(title_html)
    # always footnote 1 (so can hardwire anchor)
    html.append(u"\n<p>" + _("Two-tailed p value")
        + u": %s"
        % lib.OutputLib.get_p(p) + u" <a href='#ft1'><sup>1</sup></a></p>")
    add_footnote(footnotes, content=mg.P_EXPLAN_REL)
    html.append(u"\n<p>" + _("Pearson's R statistic")
        + u": %s</p>" % round(pearsons_r, dp))
    html.append(u"\n<p>" + mg.DF + u": %s</p>" % df)
    html.append(u"<p>Linear Regression Details: "
        u"<a href='#ft2'><sup>2</sup></a></p>")
    add_footnote(footnotes, content=u"Always look at the scatter plot when "
        u"interpreting the linear regression line.</p>")
    html.append(u"<ul><li>Slope: %s</li>" % round(slope, dp))
    html.append(u"<li>Intercept: %s</li></ul>" % round(intercept, dp))
    output.append_divider(html, title, indiv_title=u"")
    css_dojo_dic = lib.OutputLib.extract_dojo_style(css_fil)
    item_colours = output.colour_mappings_to_item_colours(
        css_dojo_dic['colour_mappings'])
    title_dets_html = u"" # already got an appropriate title for whole section
    show_borders = True
    series_dets = [{mg.CHARTS_SERIES_LBL_IN_LEGEND: None, # None if only one series
        mg.LIST_X: list_x, mg.LIST_Y: list_y, mg.INC_REGRESSION: True, 
        mg.LINE_LST: line_lst, mg.DATA_TUPS: None}] # only Dojo needs data_tups
    n_chart = "N = " + lib.formatnum(len(list_x))
    charting_pylab.add_scatterplot(css_dojo_dic['plot_bg'], show_borders,
        css_dojo_dic['major_gridline_colour'],
        css_dojo_dic['plot_font_colour_filled'], n_chart, series_dets, label_x,
        label_y, x_vs_y, title_dets_html, add_to_report, report_name, html,
        dot_colour=item_colours[0])
    add_footnotes(footnotes, html)
    ## details
    if details:
        html.append(u"""<p>No worked example available for this test</p>""")
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
            CSS_PAGE_BREAK_BEFORE)
    output.append_divider(html, title, indiv_title=u"scatterplot")
    return u"".join(html)

def spearmansr_output(list_x, list_y, spearmans_r, p, df, label_x, label_y, 
        add_to_report, report_name, css_fil, css_idx=0, dp=mg.DEFAULT_STATS_DP, 
        details=None, page_break_after=False):
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
        css_idx)
    slope, intercept, unused, y0, y1 = core_stats.get_regression_dets(list_x, 
        list_y)
    line_lst = [y0, y1]
    html = []
    footnotes = []
    x_vs_y = '"%s"' % label_x + _(" vs ") + '"%s"' % label_y
    title = (_("Results of Spearman's Test of Linear Correlation "
        "for %s") % x_vs_y)
    title_html = "<h2>%s</h2>" % title
    html.append(title_html)
    # always footnote 1 (so can hardwire anchor)
    html.append(u"\n<p>" + _("p value") + u": %s" % lib.OutputLib.get_p(p) + 
        u" <a href='#ft1'><sup>1</sup></a></p>")
    add_footnote(footnotes, content=mg.P_EXPLAN_REL)
    html.append(u"\n<p>" + _("Spearman's R statistic") + 
        u": %s</p>" % round(spearmans_r, dp))
    html.append(u"\n<p>" + mg.DF + u": %s</p>" % df)
    html.append(u"<p>Linear Regression Details: "
        u"<a href='#ft2'><sup>2</sup></a></p>")
    add_footnote(footnotes, content=u"Always look at the scatter plot when "
        u"interpreting the linear regression line.</p>")
    html.append(u"<ul><li>Slope: %s</li>" % round(slope, dp))
    html.append(u"<li>Intercept: %s</li></ul>" % round(intercept, dp))
    output.append_divider(html, title, indiv_title=u"")
    css_dojo_dic = lib.OutputLib.extract_dojo_style(css_fil)
    item_colours = output.colour_mappings_to_item_colours(
        css_dojo_dic['colour_mappings'])
    title_dets_html = u"" # already got an appropriate title for whole section
    show_borders = True
    series_dets = [{mg.CHARTS_SERIES_LBL_IN_LEGEND: None, # None if only one series
        mg.LIST_X: list_x, mg.LIST_Y: list_y, mg.INC_REGRESSION: True, 
        mg.LINE_LST: line_lst, mg.DATA_TUPS: None}] # only Dojo needs data_tups
    n_chart = "N = " + lib.formatnum(len(list_x))
    charting_pylab.add_scatterplot(css_dojo_dic['plot_bg'], show_borders,
        css_dojo_dic['major_gridline_colour'],
        css_dojo_dic['plot_font_colour_filled'], n_chart, series_dets, label_x,
        label_y, x_vs_y, title_dets_html, add_to_report, report_name, html,
        dot_colour=item_colours[0])
    add_footnotes(footnotes, html)
    ## details
    if details:
        html.append(u"""<hr>
        <h2>Worked Example of Key Calculations</h2>
        <h3>Step 1 - Set up table of paired results</h3>
        <table>
        <thead>
            <tr><th>%(label_x)s</th><th>%(label_y)s</th></tr>
        </thead>
        <tbody>""" % {u"label_x": label_x, u"label_y": label_y})
        MAX_DISPLAY_ROWS = 50
        init_tbl = details[mg.SPEARMANS_INIT_TBL]
        for row in init_tbl[:MAX_DISPLAY_ROWS]:
            html.append(u"""<tr><td>%s</td><td>%s</td></tr>""" % row[:2])
        diff_init = len(init_tbl) - MAX_DISPLAY_ROWS
        if diff_init > 0: 
            html.append(u"""
            <tr><td colspan="2">%s rows not displayed</td></tr>""" %
                lib.formatnum(diff_init))
        html.append(u"""</tbody></table>""")
        html.append(u"""
        <h3>Step 2 - Work out ranks for the x and y values</h3>
        <p>Rank such that all examples of a value get the mean rank for all
        items of that value</p>
        <table>
        <thead>
            <tr><th>%(label_x)s</th><th>Rank within<br>%(label_x)s</th></tr>
        </thead>
        <tbody>""" % {u"label_x": label_x})
        x_ranked = details[mg.SPEARMANS_X_RANKED]
        for x, x_rank in x_ranked[:MAX_DISPLAY_ROWS]:
            html.append(u"""<tr><td>%s</td><td>%s</td></tr>""" % (x,
                x_rank))
        diff_x_ranked = len(x_ranked) - MAX_DISPLAY_ROWS
        if diff_x_ranked > 0: 
            html.append(u"<tr><td colspan='2'>%s rows not displayed</td></tr>" %
                lib.formatnum(diff_x_ranked))
        html.append(u"""</tbody></table>""")
        html.append(u"""
        <p>Do the same for %(label_y)s values</p>
        <table>
        <thead>
            <tr><th>%(label_y)s</th><th>Rank within<br>%(label_y)s</th></tr>
        </thead>
        <tbody>""" % {u"label_y": label_y})
        y_ranked = details[mg.SPEARMANS_Y_RANKED]
        for y, y_rank in y_ranked[:MAX_DISPLAY_ROWS]:
            html.append(u"""<tr><td>%s</td><td>%s</td></tr>""" % (y,
                y_rank))
        diff_y_ranked = len(y_ranked) - MAX_DISPLAY_ROWS
        if diff_y_ranked > 0: 
            html.append(u"<tr><td colspan='2'>%s rows not displayed</td></tr>" %
                lib.formatnum(diff_y_ranked))
        html.append(u"""</tbody></table>""")
        html.append(u"""
        <h3>Step 3 - Add ranks to original table or pairs</h3>
        <table>
        <thead>
            <tr>
                <th>%(label_x)s</th>
                <th>%(label_y)s</th>
                <th>%(label_x)s Ranks</th>
                <th>%(label_y)s Ranks</th>
            </tr>
        </thead>
        <tbody>""" % {u"label_x": label_x, u"label_y": label_y})
        for row in init_tbl[:MAX_DISPLAY_ROWS]:
            html.append(u"""<tr>
                <td>%s</td><td>%s</td><td>%s</td><td>%s</td>
            </tr>""" % row[:4])
        if diff_init > 0: 
            html.append(u"<tr><td colspan='4'>%s rows not displayed</td></tr>" %
                lib.formatnum(diff_init))
        html.append(u"""</tbody></table>""")
        html.append(u"""
        <h3>Step 4 - Add difference in ranks and get square of diff</h3>
        <table>
        <thead>
            <tr>
                <th>%(label_x)s</th>
                <th>%(label_y)s</th>
                <th>%(label_x)s Ranks</th>
                <th>%(label_y)s Ranks</th>
                <th>Difference</th>
                <th>Diff Squared</th>
            </tr>
        </thead>
        <tbody>""" % {u"label_x": label_x, u"label_y": label_y})
        for row in init_tbl[:MAX_DISPLAY_ROWS]:
            html.append(u"""<tr>
                <td>%s</td>
                <td>%s</td>
                <td>%s</td>
                <td>%s</td>
                <td>%s</td>
                <td>%s</td>
            </tr>""" % row)
        if diff_init > 0: 
            html.append(u"<tr><td colspan='6'>%s rows not displayed</td></tr>" %
                lib.formatnum(diff_init))
        html.append(u"""</tbody></table>""")
        html.append(u"""
        <h3>Step 5 - Count N pairs, cube it, and subtract N</h3>
        N = %s<br>N<sup>3</sup> - N = %s""" % (lib.formatnum(details[mg.SPEARMANS_N]),
            lib.formatnum(details[mg.SPEARMANS_N_CUBED_MINUS_N])))
        html.append(u"""
        <h3>Step 6 - Total squared diffs, multiply by 6, divide by N<sup>3</sup> -
        N value</h3>
        Total squared diffs = %s
        <br>Multiplied by 6 = %s<br>Divided by N<sup>3</sup> - N value (%s) = %s
        """ % (lib.formatnum(details[mg.SPEARMANS_TOT_D_SQUARED]),
            lib.formatnum(details[mg.SPEARMANS_TOT_D_SQUARED_x_6]),
            lib.formatnum(details[mg.SPEARMANS_N_CUBED_MINUS_N]),
            lib.formatnum(details[mg.SPEARMANS_PRE_RHO])))
        html.append(u"""
        <h3>Step 7 - Subtract from 1 to get Spearman's rho</h3>
        rho = 1 - %s = %s (all rounded to 4dp)""" %
        (details[mg.SPEARMANS_PRE_RHO], details[mg.SPEARMANS_RHO]))
        html.append(u"""<p>The only remaining question is the probability of a
        rho that size occurring for a given N value</p>""")
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
            CSS_PAGE_BREAK_BEFORE)
    output.append_divider(html, title, indiv_title=u"scatterplot")
    return u"".join(html)

def chisquare_output(chi, p, var_label_a, var_label_b, add_to_report, 
        report_name, val_labels_a, val_labels_b, lst_obs, lst_exp, min_count, 
        perc_cells_lt_5, df, css_fil, css_idx=0, dp=mg.DEFAULT_STATS_DP, 
        details=None, page_break_after=False):
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
    title_html = mg.TBL_TITLE_START + u"<h2>%s</h2>" % title + mg.TBL_TITLE_END
    html.append(title_html)
    html.append(mg.TBL_SUBTITLE_START + mg.TBL_SUBTITLE_END)
    # always footnote 1 (so can hardwire anchor)
    html.append(u"\n<p>" + _("p value") + u": %s" % lib.OutputLib.get_p(p) + 
        u" <a href='#ft1'><sup>1</sup></a></p>")
    add_footnote(footnotes, content=mg.P_EXPLAN_REL)  
    html.append(u"\n<p>" + _("Pearson's Chi Square statistic") + u": %s</p>" %
        round(chi, dp))
    html.append(u"\n<p>" + mg.DF + u": %s</p>" % df)
    # headings
    html.append(u"\n\n%s<table cellspacing='0'>\n<thead>" % 
        mg.REPORT_TABLE_START)
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
    for unused in range(val_labels_b_n + 1):
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
        u"%s</td><td class='%s'>%s</td>" % (row_obs_tot_tot, CSS_DATACELL, 
        round(row_exp_tot_tot,1)))
    html.append(u"</tr>")
    html.append(u"\n</tbody>\n</table>%s\n" % mg.REPORT_TABLE_END)
    # warnings
    html.append(u"\n<p>" + _("Minimum expected cell count") + u": %s</p>" %
        round(min_count, dp))
    html.append(u"\n<p>% " + _("cells with expected count < 5") + u": %s</p>" %
        round(perc_cells_lt_5, 1))
    add_footnotes(footnotes, html)
    ## details
    if details:
        html.append(u"""
        <hr>
        <h2>Worked Example of Key Calculations</h2>
        <h3>Step 1 - Calculate row and column sums</h3>""")
        html.append(u"<h4>Row sums</h4>")
        for row_n in range(1, details[mg.CHI_ROW_N] + 1):
            vals_added = u" + ".join(lib.formatnum(x) for x
                in details[mg.CHI_ROW_OBS][row_n])
            html.append(u"""
            <p>Row %s Total: %s = <strong>%s</strong></p>""" % (row_n,
                vals_added, lib.formatnum(details[mg.CHI_ROW_SUMS][row_n])))
        html.append(u"<h4>Column sums</h4>")
        for col_n in range(1, details[mg.CHI_COL_N] + 1):
            vals_added = u" + ".join(lib.formatnum(x) for x
                in details[mg.CHI_COL_OBS][col_n])
            html.append(u"""
            <p>Col %s Total: %s = <strong>%s</strong></p>""" % (col_n,
                vals_added, lib.formatnum(details[mg.CHI_COL_SUMS][col_n])))
        html.append(u"""
        <h3>Step 2 - Calculate expected values per cell</h3>
        <p>Multiply row and column sums for cell and divide by grand total
        </p>""")
        for coord, cell_data in details[mg.CHI_CELLS_DATA].items():
            row_n, col_n = coord
            html.append(u"""<p>Row %(row_n)s, Col %(col_n)s:
            (%(row_sum)s x %(col_sum)s)/%(grand_tot)s =
            <strong>%(expected)s</strong></p>
            """ % {u"row_n": row_n, u"col_n": col_n,
                u"row_sum": lib.formatnum(cell_data[mg.CHI_CELL_ROW_SUM]),
                u"col_sum": lib.formatnum(cell_data[mg.CHI_CELL_COL_SUM]),
                u"grand_tot": lib.formatnum(details[mg.CHI_GRAND_TOT]),
                u"expected": lib.formatnum(cell_data[mg.CHI_EXPECTED])})
        html.append(u"""
        <h3>Step 3 - Calculate the differences between observed and expected per
        cell, square them, and divide by expected value</h3>""")
        for coord, cell_data in details[mg.CHI_CELLS_DATA].items():
            row_n, col_n = coord
            html.append(u"""<p>Row %(row_n)s, Col %(col_n)s:
            (%(larger)s - %(smaller)s)<sup>2</sup> / %(expected)s =
            (%(diff)s)<sup>2</sup> / %(expected)s =
            %(diff_squ)s / %(expected)s = <strong>%(pre_chi)s</strong></p>""" %
               {u"row_n": row_n, u"col_n": col_n,
                u"larger": lib.formatnum(cell_data[mg.CHI_MAX_OBS_EXP]),
                u"smaller": lib.formatnum(cell_data[mg.CHI_MIN_OBS_EXP]),
                u"expected": lib.formatnum(cell_data[mg.CHI_EXPECTED]),
                u"diff": lib.formatnum(cell_data[mg.CHI_DIFF]),
                u"diff_squ": lib.formatnum(cell_data[mg.CHI_DIFF_SQU]),
                u"pre_chi": lib.formatnum(cell_data[mg.CHI_PRE_CHI]),
                })
        html.append(u"""
        <h3>Step 4 - Add up all the results to get Χ<sup>2</sup></h3>""")
        vals_added = u" + ".join(str(x) for x in details[mg.CHI_PRE_CHIS])
        html.append(u"""
        <p>%s = <strong>%s</strong></p>""" % (vals_added,
            details[mg.CHI_CHI_SQU]))
        html.append(u"""
        <h3>Step 5 - Calculate degrees of freedom</h3>
        <p>N rows - 1 multiplied by N columns - 1</p>
        <p>(%s - 1) x (%s - 1) = %s x %s = <strong>%s</strong></p>""" %
        (details[mg.CHI_ROW_N], details[mg.CHI_COL_N],
            details[mg.CHI_ROW_N_MINUS_1], details[mg.CHI_COL_N_MINUS_1],
            details[mg.CHI_DF]))
        html.append(u"""<p>The only remaining question is the probability of a
            Chi Square value that size occurring for a given degrees of freedom
            value</p>""")
    if page_break_after:
        html.append(u"<br><hr><br><div class='%s'></div>" % 
            CSS_PAGE_BREAK_BEFORE)
    # clustered bar charts
    html.append(u"<hr><p>Interpreting the Proportions chart - look at the "
        u"\"All combined\" category - the more different the other "
        U"%(var_label_a)s categories look from this the more likely the Chi "
        u"Square test will detect a difference. Within each %(var_label_a)s "
        u"category the %(var_label_b)s values add up to 1 i.e. 100%%. This is "
        u"not the same way of displaying data as a clustered bar chart although"
        u" the similarity can be confusing.</p>" % {"var_label_a": var_label_a,
        "var_label_b": var_label_b})
    css_dojo_dic = lib.OutputLib.extract_dojo_style(css_fil)
    item_colours = output.colour_mappings_to_item_colours(
        css_dojo_dic['colour_mappings'])
    output.append_divider(html, title, indiv_title=u"")
    add_chi_square_clustered_barcharts(css_dojo_dic['plot_bg'], item_colours,
        css_dojo_dic['major_gridline_colour'], lst_obs, var_label_a,
        var_label_b, val_labels_a, val_labels_b, val_labels_b_n, add_to_report,
        report_name, html)
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

def add_chi_square_clustered_barcharts(grid_bg, bar_colours, line_colour,
        lst_obs, var_label_a, var_label_b, val_labels_a, val_labels_b,
        val_labels_b_n, add_to_report, report_name, html):
    # NB list_obs is bs within a and we need the other way around
    debug = False
    #width = 7 
    n_clusters = len(val_labels_b)
    if n_clusters < 8:
        width = 7
        height = None # allow height to be set by golden ratio
    else:
        width = n_clusters*1.5
        height = 4.5
    rows_n = len(lst_obs)/val_labels_b_n
    cols_n = val_labels_b_n
    bs_in_as = np.array(lst_obs).reshape(rows_n, cols_n)
    as_in_bs_lst = bs_in_as.transpose().tolist()
    # proportions of b within a
    propns_bs_in_as = []
    # expected propn bs in as - so we have a reference to compare rest to
    total = sum(lst_obs)
    expected_propn_bs_in_as = []
    for as_in_b_lst in as_in_bs_lst:
        expected_propn_bs_in_as.append(float(sum(as_in_b_lst))/float(total))
    propns_bs_in_as.append(expected_propn_bs_in_as)
    # actual observed bs in as
    bs_in_as_lst = bs_in_as.tolist()
    for bs in bs_in_as_lst:
        propns_lst = []
        for b in bs:
            propns_lst.append(float(b)/float(sum(bs)))
        propns_bs_in_as.append(propns_lst)
    propns_as_in_bs_lst = np.array(propns_bs_in_as).transpose().tolist()
    if debug:
        print(lst_obs)
        print(bs_in_as)
        print(as_in_bs_lst)
        print(bs_in_as_lst)
        print(propns_as_in_bs_lst)
    title_tmp = _("%(laba)s and %(labb)s - %(y)s")
    title_overrides = {"fontsize": 14}
    # chart 1 - proportions ****************************************************
    plot = boomslang.Plot()
    y_label = _("Proportions")
    title = title_tmp % {"laba": var_label_a, "labb": var_label_b, "y": y_label}
    plot.setTitle(title)
    plot.setTitleProperties(title_overrides)
    plot.setDimensions(width, height)
    plot.hasLegend(columns=val_labels_b_n, location="lower left")
    plot.setAxesLabelSize(11)
    plot.setXTickLabelSize(get_xaxis_fontsize(val_labels_a))
    plot.setLegendLabelSize(9)
    val_labels_a_with_ref = val_labels_a[:]
    val_labels_a_with_ref.insert(0, "All\ncombined")
    charting_pylab.config_clustered_barchart(grid_bg, bar_colours, line_colour, 
        plot, var_label_a, y_label, val_labels_a_with_ref, val_labels_b,
        propns_as_in_bs_lst)
    img_src = charting_pylab.save_report_img(add_to_report, report_name, 
        save_func=plot.save, dpi=None)
    html.append(u"\n%s%s%s" % (mg.IMG_SRC_START, img_src, mg.IMG_SRC_END))
    output.append_divider(html, title, indiv_title=u"proportion")
    # chart 2 - freqs **********************************************************
    plot = boomslang.Plot()
    y_label = _("Frequencies")
    title = title_tmp % {"laba": var_label_a, "labb": var_label_b, "y": y_label}
    plot.setTitle(title)
    plot.setTitleProperties(title_overrides)
    plot.setDimensions(width, height)
    plot.hasLegend(columns=val_labels_b_n, location="lower left")
    plot.setAxesLabelSize(11)
    plot.setXTickLabelSize(get_xaxis_fontsize(val_labels_a))
    plot.setLegendLabelSize(9)
    # only need 6 because program limits to that. See core_stats.get_obs_exp().
    charting_pylab.config_clustered_barchart(grid_bg, bar_colours, line_colour, 
        plot, var_label_a, y_label, val_labels_a, val_labels_b, as_in_bs_lst)
    img_src = charting_pylab.save_report_img(add_to_report, report_name, 
        save_func=plot.save, dpi=None)
    html.append(u"\n%s%s%s" % (mg.IMG_SRC_START, img_src, mg.IMG_SRC_END))
    output.append_divider(html, title, indiv_title=u"frequency")

def kruskal_wallis_output(h, p, label_gp, label_a, label_b, dics, df, label_avg, 
        css_fil, css_idx=0, dp=mg.DEFAULT_STATS_DP, details=None,
        page_break_after=False):
    CSS_FIRST_COL_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_COL_VAR, css_idx)
    CSS_LBL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_LBL, css_idx)
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, 
        css_idx)
    html = []
    footnotes = []
    title = (_(u"Results of Kruskal-Wallis H test of average %(avg)s for "
        u"%(label_gp)s groups from \"%(a)s\" to \"%(b)s\"") % 
        {"label_gp": label_gp, "avg": label_avg, "a": label_a, "b": label_b})
    title_html = u"%s\n<h2>%s</h2>\n%s" % (mg.TBL_TITLE_START, title,
        mg.TBL_TITLE_END)
    html.append(title_html)
    html.append(mg.TBL_SUBTITLE_START + mg.TBL_SUBTITLE_END)
    # always footnote 1 (so can hardwire anchor)
    html.append(u"\n<p>" + _("p value") + u": %s" % lib.OutputLib.get_p(p) + 
        u" <a href='#ft1'><sup>1</sup></a></p>")
    add_footnote(footnotes, content=mg.P_EXPLAN_DIFF) 
    html.append("\n<p>" + _("Kruskal-Wallis H statistic") + ": %s</p>" %
        round(h, dp))
    html.append(u"\n<p>" + mg.DF + u": %s</p>" % df)
    html.append(u"\n\n%s<table cellspacing='0'>\n<thead>" % 
        mg.REPORT_TABLE_START)
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
            lib.formatnum(dic[mg.STATS_DIC_N]),
            round(dic[mg.STATS_DIC_MEDIAN], dp), dic[mg.STATS_DIC_MIN], 
            dic[mg.STATS_DIC_MAX]))
    html.append(u"\n</tbody></table>%s" % mg.REPORT_TABLE_END)
    add_footnotes(footnotes, html)
    ## details
    if details:
        html.append(u"""<p>No worked example available for this test</p>""")
    if page_break_after:
        html.append("<br><hr><br><div class='%s'></div>" % 
            CSS_PAGE_BREAK_BEFORE)
    output.append_divider(html, title, indiv_title=u"")
    return u"".join(html)
