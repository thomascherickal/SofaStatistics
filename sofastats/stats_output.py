import cgi
from functools import partial

import numpy as np
import pylab

from sofastats import boomslang
from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import lib
from sofastats import output
from sofastats.charting import charting_pylab
from sofastats.stats import core_stats

"""
Output doesn't include the calculation of any values. These are in discrete
functions in core_stats, amenable to unit testing.

No html header or footer added here. Just some body content.   
"""

row_str = partial(lib.pluralise_with_s, 'row')

def add_footnote(footnotes, content):
    footnotes.append("\n<p><a id='ft%%(ftnum)s'></a><sup>%%(ftnum)s</sup> %s"
        "</p>" % content)

def add_footnotes(footnotes, html):
    for i, footnote in enumerate(footnotes):
        next_ft = i + 1
        html.append(footnote % {'ftnum': next_ft})

def _p_msg(p_sim):
    return lib.OutputLib.to_precision(num=p_sim, precision=4)

def anova_output(samples, F, p, dics, sswn, dfwn, mean_squ_wn, ssbn, dfbn,
        mean_squ_bn, label_gp, label_a, label_b, label_avg,
        report_name, css_fil, css_idx=0, dp=mg.DEFAULT_STATS_DP, details=None,
        *, add_to_report=False, page_break_after=False):
    debug = False
    CSS_FIRST_COL_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_COL_VAR, css_idx)
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (
        mg.CSS_PAGE_BREAK_BEFORE, css_idx)
    CSS_LBL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_LBL, css_idx)
    CSS_TBL_HDR_FTNOTE = mg.CSS_SUFFIX_TEMPLATE % (
        mg.CSS_TBL_HDR_FTNOTE, css_idx)
    CSS_ALIGN_RIGHT = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_ALIGN_RIGHT, css_idx)
    footnotes = []
    html = []
    title = _('Results of ANOVA test of average %(avg)s for %(label_gp)s '
        "groups from \"%(a)s\" to \"%(b)s\"") % {'label_gp': label_gp,
        'avg': label_avg, 'a': label_a, 'b': label_b}
    html_title = f'<h2>{title}</h2>'
    html.append(mg.TBL_TITLE_START + html_title + mg.TBL_TITLE_END)
    html.append('\n\n<h3>' + mg.TBL_SUBTITLE_START
        + _('Analysis of variance table') + mg.TBL_SUBTITLE_END + '</h3>')
    html.append(f"\n{mg.REPORT_TABLE_START}<table cellspacing='0'>\n<thead>")
    html.append('\n<tr>'
        + f"<th class='{CSS_FIRST_COL_VAR}'>" + _('Source') + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('Sum of Squares') + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('df') + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('Mean Sum of Squares')
        + '</th>' + f"\n<th class='{CSS_FIRST_COL_VAR}'>F</th>")
    ## always footnote 1 (so can hardwire anchor)
    html.append(f"\n<th class='{CSS_FIRST_COL_VAR}'>"
        + f"p<a class='{CSS_TBL_HDR_FTNOTE}' href='#ft1'><sup>1</sup></a>"
        + '</th></tr>')
    add_footnote(footnotes, content=mg.P_EXPLAN_DIFF)
    html.append('\n</thead>\n<tbody>')
    tpl = '%%.%sf' % dp
    html.append('\n<tr><td>' + _('Between') + '</td>'
        f"<td class='{CSS_ALIGN_RIGHT}'>"
        + '{}</td>'.format(tpl % round(ssbn, dp))
        + f"<td class='{CSS_ALIGN_RIGHT}'>"
        + f'{dfbn}</td>')
    html.append(f"<td class='{CSS_ALIGN_RIGHT}'>"
        + '{}</td>'.format(tpl % round(mean_squ_bn, dp))
        + f"<td class='{CSS_ALIGN_RIGHT}'>"
        + '{}</td>'.format(tpl % round(F, dp))
        + f'<td>{lib.OutputLib.get_p(p)}</td></tr>')
    html.append('\n<tr><td>' + _('Within')
        + f"<td class='{CSS_ALIGN_RIGHT}'>"
        + "{}</td>".format(tpl % round(sswn, dp))
        + f"<td class='{CSS_ALIGN_RIGHT}'>" + f"{dfwn}</td>")
    html.append(f"<td class='{CSS_ALIGN_RIGHT}'>" + "%s</td>"
        % (tpl % round(mean_squ_wn, dp)) + "<td></td><td></td></tr>")
    html.append(f'\n</tbody>\n</table>{mg.REPORT_TABLE_END}\n')
    output.append_divider(html, title, indiv_title='Analysis of Variance')
    try:
        unused, p_sim = core_stats.sim_variance(samples, threshold=0.01)
        msg = _p_msg(p_sim)
    except Exception:
        msg = 'Unable to calculate'
    ## footnote 2
    html.append('\n<p>' + _("O'Brien's test for homogeneity of variance")
        + f': {msg}' + " <a href='#ft2'><sup>2</sup></a></p>")
    add_footnote(footnotes, content=mg.OBRIEN_EXPLAN)
    html.append(mg.TBL_TITLE_START + mg.TBL_TITLE_END)
    html.append('\n\n<h3>'  + mg.TBL_SUBTITLE_START
        + _('Group summary details')  + mg.TBL_SUBTITLE_END + '</h3>')
    html.append(f"\n{mg.REPORT_TABLE_START}<table cellspacing='0'>\n<thead>")
    html.append(f"\n<tr><th class='{CSS_FIRST_COL_VAR}'>" + _('Group')
        + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('N') + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('Mean') + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('CI 95%')
        + f"<a class='{CSS_TBL_HDR_FTNOTE}"
        + "' href='#ft3'><sup>3</sup></a></th>")
    ## footnote 3
    add_footnote(footnotes, content=mg.CI_EXPLAN)
    ## footnote 4
    html.append(f"\n<th class='{CSS_FIRST_COL_VAR}'>"
        + _("Standard Deviation") + f"<a class='{CSS_TBL_HDR_FTNOTE}"
        + "' href='#ft4'><sup>4</sup></a></th>")
    add_footnote(footnotes, content=mg.STD_DEV_EXPLAN)
    html.append(f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('Min') + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('Max') + '</th>')
    ## footnotes 5,6,7
    html.append(f"<th class='{CSS_FIRST_COL_VAR}'>" + _('Kurtosis') 
        + f"<a class='{CSS_TBL_HDR_FTNOTE}' href='#ft5'><sup>5</sup></a></th>")
    html.append(f"<th class='{CSS_FIRST_COL_VAR}'>" + _('Skew')
        + f"<a class='{CSS_TBL_HDR_FTNOTE}' href='#ft6'><sup>6</sup></a></th>")
    html.append(f"<th class='{CSS_FIRST_COL_VAR}'>" + _('p abnormal') 
        + f"<a class='{CSS_TBL_HDR_FTNOTE}' href='#ft7'><sup>7</sup></a></th>")
    html.append('</tr>')
    add_footnote(footnotes, content=mg.KURT_EXPLAN)
    add_footnote(footnotes, content=mg.SKEW_EXPLAN)
    add_footnote(footnotes, content=mg.NORMALITY_MEASURE_EXPLAN)
    html.append('\n</thead>\n<tbody>')
    row_tpl = ('\n<tr>'
        f"<td class='{CSS_LBL}'>" + '%s</td>'
        + f"<td class='{CSS_ALIGN_RIGHT}'>" + "%s</td>"
        + f"<td class='{CSS_ALIGN_RIGHT}'>" + "%s</td>"
        + f"<td class='{CSS_ALIGN_RIGHT}'>" + "%s</td>"
        + f"<td class='{CSS_ALIGN_RIGHT}'>" + "%s</td>"
        + f"<td class='{CSS_ALIGN_RIGHT}'>" + "%s</td>"
        + f"<td class='{CSS_ALIGN_RIGHT}'>" + "%s</td>"
        + f"<td class='{CSS_ALIGN_RIGHT}'>" + "%s</td>"
        + f"<td class='{CSS_ALIGN_RIGHT}'>" + "%s</td>"
        + f"<td class='{CSS_ALIGN_RIGHT}'>" + "%s</td></tr>")
    dic_sample_tups = list(zip(dics, samples))
    for dic, sample in dic_sample_tups:
        results = (dic[mg.STATS_DIC_LBL],
            lib.formatnum(dic[mg.STATS_DIC_N]),
            round(dic[mg.STATS_DIC_MEAN], dp),
            '{} - {}'.format(
                tpl % round(dic[mg.STATS_DIC_CI][0], dp),
                tpl % round(dic[mg.STATS_DIC_CI][1], dp)
            ),
            tpl % round(dic[mg.STATS_DIC_SD], dp),
            dic[mg.STATS_DIC_MIN],
            dic[mg.STATS_DIC_MAX])
        try:
            (unused, p_arr, cskew,
             unused, ckurtosis, unused) = core_stats.normaltest(sample)
            extra_results = []
            try:
                kurt = tpl % round(ckurtosis, dp)
                extra_results.append(kurt)
            except Exception:
                extra_results.append(_('Unable to calculate kurtosis'))
            try:
                skew = tpl % round(cskew, dp)
                extra_results.append(skew)
            except Exception:
                extra_results.append(_('Unable to calculate skew'))
            try:
                overall_p = lib.OutputLib.get_p(p_arr[0])
                extra_results.append(overall_p)
            except Exception:
                extra_results.append(_(
                    'Unable to calculate overall p for normality test'), )
            results += tuple(extra_results)
        except Exception:
            results += (_('Unable to calculate kurtosis'),
                _('Unable to calculate skew'),
                _('Unable to calculate overall p for normality test'),
            )
        html.append(row_tpl % results)
    html.append(f'\n</tbody>\n</table>{mg.REPORT_TABLE_END}\n')
    add_footnotes(footnotes, html)    
    output.append_divider(html, title, indiv_title='Group Summary')
    for dic_sample_tup in dic_sample_tups:
        dic, sample = dic_sample_tup
        histlbl = dic['label']
        if debug: print(histlbl)
        ## histogram
        ## http://www.scipy.org/Cookbook/Matplotlib/LaTeX_Examples
        charting_pylab.gen_config(
            axes_labelsize=10, xtick_labelsize=8, ytick_labelsize=8)
        fig = pylab.figure()
        fig.set_size_inches((5.0, 3.5))  ## see dpi to get image size in pixels
        css_dojo_dic = lib.OutputLib.extract_dojo_style(css_fil)
        item_colours = output.colour_mappings_to_item_colours(
            css_dojo_dic['colour_mappings'])
        try:
            charting_pylab.config_hist(fig, sample, label_avg, histlbl,
                css_dojo_dic['plot_bg'], item_colours[0],
                css_dojo_dic['major_gridline_colour'], thumbnail=False)
            img_src = charting_pylab.save_report_img(
                add_to_report, report_name, save_func=pylab.savefig, dpi=100)
            html.append(f'\n{mg.IMG_SRC_START}{img_src}{mg.IMG_SRC_END}')
        except Exception as e:
            html.append(f'<b>{histlbl}</b> - unable to display histogram. '
                f'Reason: {b.ue(e)}')
        output.append_divider(html, title, indiv_title=histlbl)
    ## details
    if details:
        html.append('<p>No worked example available for this test</p>')
    if page_break_after:
        html.append(f"<br><hr><br><div class='{CSS_PAGE_BREAK_BEFORE}'></div>")
    return ''.join(html)

def ttest_basic_results(sample_a, sample_b, t, p, label_gp, dic_a, dic_b, df,
        label_avg, dp, indep, css_idx, html):
    """
    Footnotes are autonumbered at end. The links to them will need numbering
    though.
    """
    CSS_FIRST_COL_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_COL_VAR, css_idx)
    CSS_LBL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_LBL, css_idx)
    CSS_TBL_HDR_FTNOTE = mg.CSS_SUFFIX_TEMPLATE % (
        mg.CSS_TBL_HDR_FTNOTE, css_idx)
    CSS_ALIGN_RIGHT = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_ALIGN_RIGHT, css_idx)
    footnotes = []
    if indep:
        title = (_('Results of Independent Samples t-test of average '
            "\"%(avg)s\" for %(label_gp)s groups \"%(a)s\" vs \"%(b)s\"")
            % {'label_gp': label_gp, 'avg': label_avg,
            'a': dic_a[mg.STATS_DIC_LBL], 'b': dic_b[mg.STATS_DIC_LBL]})
    else:
        title = (_("Results of Paired Samples t-test of \"%(a)s\" vs \"%(b)s\"") 
            % {'a': dic_a[mg.STATS_DIC_LBL], 'b': dic_b[mg.STATS_DIC_LBL]})
    title_html = f'{mg.TBL_TITLE_START}\n<h2>{title}</h2>\n{mg.TBL_TITLE_END}'
    html.append(title_html)
    html.append(mg.TBL_SUBTITLE_START + mg.TBL_SUBTITLE_END)
    ## always footnote 1 (so can hardwire anchor)
    html.append('\n<p>' + _('p value') + f': {lib.OutputLib.get_p(p)}'
        + " <a href='#ft1'><sup>1</sup></a></p>")
    add_footnote(footnotes, content=mg.P_EXPLAN_DIFF)
    html.append('\n<p>' + _('t statistic') + f': {round(t, dp)}</p>')
    html.append('\n<p>' + mg.DF + f': {df}</p>')
    if indep:
        try:
            unused, p_sim = core_stats.sim_variance(
                [sample_a, sample_b], threshold=0.01)
            msg = _p_msg(p_sim)
        except Exception:
            msg = 'Unable to calculate'
        ## always footnote 2 if present
        html.append('\n<p>' + _("O'Brien's test for homogeneity of variance")
            + f": {msg} <a href='#ft2'><sup>2</sup></a></p>")
        add_footnote(footnotes, content=mg.OBRIEN_EXPLAN)
    html.append(f"\n\n{mg.REPORT_TABLE_START}<table cellspacing='0'>\n<thead>")
    next_ft = len(footnotes) + 1
    html.append('\n<tr>'
        + f"<th class='{CSS_FIRST_COL_VAR}'>" + _('Group') + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('N') + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('Mean') + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('CI 95%')
        + f"<a class='{CSS_TBL_HDR_FTNOTE}"
        + f"' href='#ft{next_ft}'><sup>{next_ft}</sup></a></th>"
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('Standard Deviation')
        + f"<a class='{CSS_TBL_HDR_FTNOTE}' "
        + f"href='#ft{next_ft+1}'><sup>{next_ft+1}</sup></a></th>"
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('Min') + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('Max') + '</th>')
    add_footnote(footnotes, content=mg.CI_EXPLAN)
    add_footnote(footnotes, content=mg.STD_DEV_EXPLAN)
    if indep:
        ## if here, always 5,6,7
        html.append(f"<th class='{CSS_FIRST_COL_VAR}'>" + _('Kurtosis')
            + f"<a class='{CSS_TBL_HDR_FTNOTE}' "
            + "href='#ft5'><sup>5</sup></a></th>")
        html.append(f"<th class='{CSS_FIRST_COL_VAR}'>" + _('Skew')
            + f"<a class='{CSS_TBL_HDR_FTNOTE}' "
            "href='#ft6'><sup>6</sup></a></th>")
        html.append(f"<th class='{CSS_FIRST_COL_VAR}'>" + _('p abnormal')
            + f"<a class='{CSS_TBL_HDR_FTNOTE}' "
            + "href='#ft7'><sup>7</sup></a></th>")
        add_footnote(footnotes, content=mg.KURT_EXPLAN)
        add_footnote(footnotes, content=mg.SKEW_EXPLAN)
        add_footnote(footnotes, content=mg.NORMALITY_MEASURE_EXPLAN)
    tpl = "%%.%sf" % dp
    html.append('</tr>')
    html.append('\n</thead>\n<tbody>')
    if indep:
        row_tpl = ('\n<tr>'
            f"<td class='{CSS_LBL}'>%s</td>"
            f"<td class='{CSS_ALIGN_RIGHT}'>%s</td>"
            f"<td class='{CSS_ALIGN_RIGHT}'>%s</td>"
            f"<td class='{CSS_ALIGN_RIGHT}'>%s</td>"
            f"<td class='{CSS_ALIGN_RIGHT}'>%s</td>"
            f"<td class='{CSS_ALIGN_RIGHT}'>%s</td>"
            f"<td class='{CSS_ALIGN_RIGHT}'>%s</td>"
            f"<td class='{CSS_ALIGN_RIGHT}'>%s</td>"
            f"<td class='{CSS_ALIGN_RIGHT}'>%s</td>"
            f"<td class='{CSS_ALIGN_RIGHT}'>%s</td>"
            '</tr>')
    else:
        row_tpl = ('\n<tr>'
            f"<td class='{CSS_LBL}'>%s</td>"
            f"<td class='{CSS_ALIGN_RIGHT}'>%s</td>"
            f"<td class='{CSS_ALIGN_RIGHT}'>%s</td>"
            f"<td class='{CSS_ALIGN_RIGHT}'>%s</td>"
            f"<td class='{CSS_ALIGN_RIGHT}'>%s</td>"
            f"<td class='{CSS_ALIGN_RIGHT}'>%s</td>"
            f"<td class='{CSS_ALIGN_RIGHT}'>%s</td></tr>")
    for dic, sample in [(dic_a, sample_a), (dic_b, sample_b)]:
        results = (dic[mg.STATS_DIC_LBL],
            lib.formatnum(dic[mg.STATS_DIC_N]),
            round(dic[mg.STATS_DIC_MEAN], dp),
            '%s - %s' % (tpl % round(dic[mg.STATS_DIC_CI][0], dp),
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
                results += (_('Unable to calculate kurtosis'),
                    _('Unable to calculate skew'),
                    _('Unable to calculate overall p for normality test'))
        html.append(row_tpl % results)
    html.append(f'\n</tbody>\n</table>{mg.REPORT_TABLE_END}\n')
    html.append("\n<hr class='ftnote-line'>")
    add_footnotes(footnotes, html)
    return title

def ttest_indep_output(sample_a, sample_b, t, p, label_gp, dic_a, dic_b, df,
        label_avg, report_name, css_fil, css_idx=0,
        dp=mg.DEFAULT_STATS_DP, details=None, *,
        add_to_report=False, page_break_after=False):
    """
    Returns HTML table ready to display.

    dic_a = {"label": label_a, "n": n_a, "mean": mean_a, "sd": sd_a,
        "min": min_a, "max": max_a}
    """
    html = []
    indep = True
    title = ttest_basic_results(sample_a, sample_b, t, p, label_gp, dic_a, 
        dic_b, df, label_avg, dp, indep, css_idx, html)
    output.append_divider(html, title, indiv_title='')
    sample_dets = [
        ('a', sample_a, dic_a['label']),
        ('b', sample_b, dic_b['label'])]
    for unused, sample, histlbl in sample_dets:
        ## histogram
        ## http://www.scipy.org/Cookbook/Matplotlib/LaTeX_Examples
        charting_pylab.gen_config(
            axes_labelsize=10, xtick_labelsize=8, ytick_labelsize=8)
        fig = pylab.figure()
        fig.set_size_inches((5.0, 3.5))  ## see dpi to get image size in pixels
        css_dojo_dic = lib.OutputLib.extract_dojo_style(css_fil)
        item_colours = output.colour_mappings_to_item_colours(
            css_dojo_dic['colour_mappings'])
        try:
            charting_pylab.config_hist(fig, sample, label_avg, histlbl,
                css_dojo_dic['plot_bg'], item_colours[0],
                css_dojo_dic['major_gridline_colour'], thumbnail=False)
            img_src = charting_pylab.save_report_img(add_to_report, report_name, 
                save_func=pylab.savefig, dpi=100)
            html.append(f'\n{mg.IMG_SRC_START}{img_src}{mg.IMG_SRC_END}')
        except Exception as e:
            html.append(f'<b>{histlbl}</b> - unable to display histogram. '
                f'Reason: {b.ue(e)}')
        output.append_divider(html, title, indiv_title=histlbl)
    ## details
    if details: html.append('<p>No worked example available for this test</p>')
    if page_break_after:
        CSS_PAGE_BREAK_BEFORE = (
            mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_PAGE_BREAK_BEFORE, css_idx))
        html.append(f"<br><hr><br><div class='{CSS_PAGE_BREAK_BEFORE}'></div>")
    html_str = '\n'.join(html)
    return html_str

def ttest_paired_output(sample_a, sample_b, t, p, dic_a, dic_b, df, diffs,
        report_name, css_fil, css_idx=0, label_avg='',
        dp=mg.DEFAULT_STATS_DP, details=None, *,
        add_to_report, page_break_after=False):
    """
    Returns HTML table ready to display.
    dic_a = {"label": label_a, "n": n_a, "mean": mean_a, "sd": sd_a,
        "min": min_a, "max": max_a}
    """
    html = []
    indep = False
    label_gp = None
    title = ttest_basic_results(sample_a, sample_b,
        t, p, label_gp,
        dic_a, dic_b, df, label_avg, dp, indep,
        css_idx, html)
    output.append_divider(html, title, indiv_title='')
    ## histogram
    histlbl = f"Differences between {dic_a['label']} and {dic_b['label']}"
    charting_pylab.gen_config(
        axes_labelsize=10, xtick_labelsize=8, ytick_labelsize=8)
    fig = pylab.figure()
    fig.set_size_inches((7.5, 3.5))  ## see dpi to get image size in pixels
    css_dojo_dic = lib.OutputLib.extract_dojo_style(css_fil)
    item_colours = output.colour_mappings_to_item_colours(
        css_dojo_dic['colour_mappings'])
    try:
        charting_pylab.config_hist(fig, diffs, _('Differences'), histlbl,
            css_dojo_dic['plot_bg'], item_colours[0],
            css_dojo_dic['major_gridline_colour'], thumbnail=False)
        img_src = charting_pylab.save_report_img(add_to_report, report_name,
            save_func=pylab.savefig, dpi=100)
        html.append(f'\n{mg.IMG_SRC_START}{img_src}{mg.IMG_SRC_END}')
    except Exception as e:
        html.append(f'<b>{histlbl}</b> - unable to display histogram. '
            f'Reason: {b.ue(e)}')
    ## details
    if details:
        html.append('<p>No worked example available for this test</p>')
    if page_break_after:
        CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % \
            (mg.CSS_PAGE_BREAK_BEFORE, css_idx)
        html.append(f"<br><hr><br><div class='{CSS_PAGE_BREAK_BEFORE}'></div>")
    output.append_divider(html, title, indiv_title=histlbl)
    html_str = '\n'.join(html)
    return html_str

def mann_whitney_output(u, p, label_gp, dic_a, dic_b, z, label_ranked,
        css_idx=0, dp=mg.DEFAULT_STATS_DP, details=None, *,
        page_break_after=False):
    CSS_FIRST_COL_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_COL_VAR, css_idx)
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (
        mg.CSS_PAGE_BREAK_BEFORE, css_idx)
    CSS_LBL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_LBL, css_idx)
    html = []
    footnotes = []
    label_a = dic_a[mg.STATS_DIC_LBL]
    label_b = dic_b[mg.STATS_DIC_LBL]
    n_a = dic_a[mg.STATS_DIC_N]
    n_b = dic_b[mg.STATS_DIC_N]
    title = (_("Results of Mann Whitney U Test of \"%(ranked)s\" for "
        "%(label_gp)s \"%(a)s\" vs \"%(b)s\"") % {"label_gp": label_gp,
        "ranked": label_ranked, "a": label_a, "b": label_b})
    title_html = f'{mg.TBL_TITLE_START}\n<h2>{title}</h2>\n{mg.TBL_TITLE_END}'
    html.append(title_html)
    html.append(mg.TBL_SUBTITLE_START + mg.TBL_SUBTITLE_END)
    ## always footnote 1 (so can hardwire anchor)
    ## double one-tailed p value so can report two-tailed result
    html.append('\n<p>' + _('Two-tailed p value')
        + f": {lib.OutputLib.get_p(p*2)} <a href='#ft1'><sup>1</sup></a></p>")
    add_footnote(footnotes, content=mg.P_EXPLAN_DIFF)
    ## always footnote 2
    html.append('\n<p>' + _('U statistic')
        + f": {round(u, dp)} <a href='#ft2'><sup>2</sup></a></p>")
    html.append(f'\n<p>z: {round(z, dp)}</p>')
    label_a = label_a.replace('%', '%%')
    label_b = label_b.replace('%', '%%')
    label_ranked = label_ranked.replace('%','%%')
    even_matches = (n_a * n_b) / float(2)
    add_footnote(footnotes, content=('U is based on the results of matches '
        f'between the "{label_a}" and "{label_b}" groups. In each match,<br>'
        f'the winner is the one with the highest "{label_ranked}" (in a draw, '
        'each group gets half a point which is<br>why U can sometimes end in '
        '.5). The further the number is away from an even result<br>i.e. half '
        f'the number of possible matches (i.e. half of {n_a} x {n_b} in this '
        f'case i.e. {even_matches})<br>the more unlikely the difference is by '
        'chance alone and the more statistically significant it is.</p>'))
    html.append(f"\n\n{mg.REPORT_TABLE_START}<table cellspacing='0'>\n<thead>")
    html.append('\n<tr>'
        + f"<th class='{CSS_FIRST_COL_VAR}'>" + _('Group') + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('N') + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('Median') + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('Avg Rank') + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('Min') + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('Max') + '</th></tr>')
    html.append('\n</thead>\n<tbody>')
    row_tpl = (f"\n<tr><td class='{CSS_LBL}'>" + '%s</td><td>%s</td>'
        + '<td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>')
    for dic in [dic_a, dic_b]:
        html.append(row_tpl % (dic[mg.STATS_DIC_LBL],
            lib.formatnum(dic[mg.STATS_DIC_N]),
            round(dic[mg.STATS_DIC_MEDIAN], dp), round(dic['avg rank'], dp),
            dic[mg.STATS_DIC_MIN], dic[mg.STATS_DIC_MAX]))
    html.append(f'\n</tbody>\n</table>{mg.REPORT_TABLE_END}\n')
    add_footnotes(footnotes, html)
    if details:
        html.append(f"""
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
        <p>For the rest of this worked example, sample 1 is
        "{details[mg.MANN_WHITNEY_LABEL_1]}" and sample 2 is
        "{details[mg.MANN_WHITNEY_LABEL_2]}".""")
        html.append("""<table>
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
            html.append("""
            <tr>
                <td>%(sample)s</td>
                <td>%(val)s</td>
                <td>%(counter)s</td>
                <td>%(rank)s</td>
            </tr>""" % val_det)
        diff = len(val_dets) - MAX_DISPLAY_ROWS
        if diff > 0: 
            html.append(f"""
            <tr><td colspan="4">{lib.formatnum(diff)} {row_str(diff)}
            not displayed</td></tr>""")
        html.append("""
        </tbody>
        </table>""")
        html.append('<h3>Step 2 - Sum the ranks for sample 1</h3>')
        val_1s2add = [str(x)
            for x in details[mg.MANN_WHITNEY_RANKS_1][:MAX_DISPLAY_ROWS]]
        diff_ranks_1 = details[mg.MANN_WHITNEY_N_1] - MAX_DISPLAY_ROWS
        if diff_ranks_1 > 0:
            val_1s2add.append(
                f'{lib.formatnum(diff_ranks_1)} other values not displayed')
        sum_rank_1 = lib.formatnum(details[mg.MANN_WHITNEY_SUM_RANK_1])
        html.append('<p>sum_ranks<sub>1</sub> = ' + ' + '.join(val_1s2add)
            + f' i.e. <strong>{sum_rank_1}</strong></p>')
        html.append("""<h3>Step 3 - Calculate U for sample 1 as per:</h3>
        <p>u<sub>1</sub> = n<sub>1</sub>*n<sub>2</sub>
        + ((n<sub>1</sub>*(n<sub>1</sub> + 1))/2.0)
        - sum_ranks<sub>1</sub></p>""")
        n_1 = lib.formatnum(details[mg.MANN_WHITNEY_N_1])
        n_2 = lib.formatnum(details[mg.MANN_WHITNEY_N_2])
        sum_rank_1 = lib.formatnum(details[mg.MANN_WHITNEY_SUM_RANK_1])
        u_1 = lib.formatnum(details[mg.MANN_WHITNEY_U_1])
        u_2 = lib.formatnum(details[mg.MANN_WHITNEY_U_2])
        u_val = lib.formatnum(details[mg.MANN_WHITNEY_U])
        html.append(f"""<p>u<sub>1</sub> = {n_1}*{n_2} + ({n_1}*({n_2}+1))/2 -
        {sum_rank_1} i.e. <strong>{u_1}</strong></p>""")
        html.append(f"""<h3>Step 4 - Calculate U for sample 2 as per:</h3>
        <p>u<sub>2</sub> = n<sub>1</sub>*n<sub>2</sub> - u<sub>1</sub></p>""")
        html.append(f"""<p>u<sub>2</sub> = {n_1}*{n_2} - {u_1} i.e.
            <strong>{u_2}</strong></p>""")
        html.append(f"""<h3>Step 5 - Identify the lowest of the U values</h3>
        <p>The lowest value of {u_1} and {u_2} is
        <strong>{u_val}</strong></p>""")
        html.append("""<p>After this, you would use the N values and other
        methods to see if the value for U is likely to happen by chance but
        that is outside of the scope of this worked example.</p>""")
    if page_break_after:
        html.append(f"<br><hr><br><div class='{CSS_PAGE_BREAK_BEFORE}'></div>")
    output.append_divider(html, title, indiv_title='')
    return ''.join(html)

def wilcoxon_output(t, p, dic_a, dic_b, css_idx=0,
        dp=mg.DEFAULT_STATS_DP, details=None, *, page_break_after=False):
    CSS_FIRST_COL_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_COL_VAR, css_idx)
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (
        mg.CSS_PAGE_BREAK_BEFORE, css_idx)
    CSS_LBL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_LBL, css_idx)
    html = []
    footnotes = []
    label_a = dic_a[mg.STATS_DIC_LBL]
    label_b = dic_b[mg.STATS_DIC_LBL]
    title = (
        _("Results of Wilcoxon Signed Ranks Test of \"%(a)s\" vs \"%(b)s\"")
        % {"a": label_a, "b": label_b})
    title_html = "%s\n<h2>%s</h2>\n%s" % (
        mg.TBL_TITLE_START, title, mg.TBL_TITLE_END)
    html.append(mg.TBL_SUBTITLE_START + mg.TBL_SUBTITLE_END)
    html.append(title_html)
    ## always footnote 1 (so can hardwire anchor)
    html.append('\n<p>' + _('Two-tailed p value')
        + f': {lib.OutputLib.get_p(p)}'
        + " <a href='#ft1'><sup>1</sup></a></p>")
    add_footnote(footnotes, content=mg.P_EXPLAN_DIFF)
    html.append('\n<p>' + _('Wilcoxon Signed Ranks statistic')
        + f': {round(t, dp)}' + " <a href='#ft2'><sup>2</sup></a></p>")
    ## http://stat.ethz.ch/R-manual/R-patched/library/stats/html/wilcox.test.html
    add_footnote(footnotes, content='Different statistics applications will '
        'show different results here depending on the reporting approach taken.')
    html.append("\n\n%s<table cellspacing='0'>\n<thead>"
        % mg.REPORT_TABLE_START)
    html.append('\n<tr>'
        + f"<th class='{CSS_FIRST_COL_VAR}'>" + _('Variable') + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('N') + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('Median') + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('Min') + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('Max') + '</th></tr>')
    html.append('\n</thead>\n<tbody>')
    row_tpl = (f"\n<tr><td class='{CSS_LBL}'>%s</td><td>%s</td>"
        '<td>%s</td><td>%s</td><td>%s</td></tr>')
    for dic in [dic_a, dic_b]:
        html.append(row_tpl % (dic[mg.STATS_DIC_LBL],
            lib.formatnum(dic[mg.STATS_DIC_N]),
            round(dic[mg.STATS_DIC_MEDIAN], dp), dic[mg.STATS_DIC_MIN],
            dic[mg.STATS_DIC_MAX]))
    html.append(f'\n</tbody>\n</table>{mg.REPORT_TABLE_END}\n')
    add_footnotes(footnotes, html)
    ## details
    if details:
        plus_ranks = details[mg.WILCOXON_PLUS_RANKS]
        minus_ranks = details[mg.WILCOXON_MINUS_RANKS]
        sum_plus_ranks = details[mg.WILCOXON_SUM_PLUS_RANKS]
        sum_minus_ranks = details[mg.WILCOXON_SUM_MINUS_RANKS]
        sum_plus_ranks_str = lib.formatnum(sum_plus_ranks)
        sum_minus_ranks_str = lib.formatnum(sum_minus_ranks)
        html.append("""
        <hr>
        <h2>Worked Example of Key Calculations</h2>
        <h3>Step 1 - Get differences</h3>""")
        html.append(f"""<table>
        <thead>
            <tr>
                <th>{label_a}</th><th>{label_b}</th><th>Difference</th>
            </tr>
        </thead>
        <tbody>""")
        diff_dets = details[mg.WILCOXON_DIFF_DETS]
        MAX_DISPLAY_ROWS = 50
        for diff_det in diff_dets[:MAX_DISPLAY_ROWS]:
            html.append("""
            <tr>
                <td>{a}</td><td>{b}</td><td>{diff}</td>
            </tr>""".format(**diff_det))
        diff_diffs = len(diff_dets) - MAX_DISPLAY_ROWS
        if diff_diffs > 0: 
            html.append(f"""
            <tr><td colspan="3">{lib.formatnum(diff_diffs)}
            {row_str(diff_diffs)} not displayed</td></tr>""")
        html.append("""
        </tbody>
        </table>""")
        html.append("""\
        <h3>Step 2 - Sort non-zero differences by absolute value and rank</h3>
        <p>Rank such that all examples of a value get the mean rank for all
        items of that value</p>""")
        html.append("""<table>
        <thead>
            <tr>
                <th>Difference</th>
                <th>Absolute Difference</th>
                <th>Counter</th>
                <th>Rank<br>(on Abs Diff)</th>
            </tr>
        </thead>
        <tbody>""")
        ranks_dets = details[mg.WILCOXON_RANKING_DETS]
        for rank_dets in ranks_dets[:MAX_DISPLAY_ROWS]:
            html.append("""
            <tr>
                <td>{diff}</td>
                <td>{abs_diff}</td>
                <td>{counter}</td>
                <td>{rank}</td>
            </tr>""".format(**rank_dets))
        diff_ranks = len(ranks_dets) - MAX_DISPLAY_ROWS
        if diff_ranks > 0: 
            html.append(f"""
            <tr><td colspan="4">{lib.formatnum(diff_ranks)}
            {row_str(diff_ranks)} not displayed</td></tr>""")
        html.append("""
        </tbody>
        </table>""")
        html.append('<h3>Step 3 - Sum ranks for positive differences</h3>')
        pos_rank_vals2add = [lib.formatnum(x)
            for x in plus_ranks[:MAX_DISPLAY_ROWS]]
        diff_pos_ranks = len(plus_ranks) - MAX_DISPLAY_ROWS
        if diff_pos_ranks > 0:
            pos_rank_vals2add.append(
                f'{lib.formatnum(diff_pos_ranks)} other values not displayed')
        html.append('<p>' + ' + '.join(pos_rank_vals2add)
            + f' = <strong>{sum_plus_ranks_str}</strong></p>')
        html.append('<h3>Step 4 - Sum ranks for negative differences</h3>')
        neg_rank_vals2add = [lib.formatnum(x)
            for x in minus_ranks[:MAX_DISPLAY_ROWS]]
        diff_neg_ranks = (len(minus_ranks)
            - MAX_DISPLAY_ROWS)
        if diff_neg_ranks > 0:
            neg_rank_vals2add.append(
                f"{lib.formatnum(diff_neg_ranks)} other values not displayed")
        html.append('<p>' + ' + '.join(neg_rank_vals2add)
            + f' = <strong>{sum_minus_ranks_str}</strong></p>')
        html.append('<h3>Step 5 - Get smallest of sums for positive or '
            'negative ranks</h3>')
        t = lib.formatnum(details[mg.WILCOXON_T])
        html.append(f'<p>The lowest value of {sum_plus_ranks_str} and '
            f"{sum_minus_ranks_str} is {t} so Wilcoxon's T statistic is "
            f'<strong>{t}</strong></p>')
        html.append('<h3>Step 6 - Get count of all non-zero diffs</h3>')
        n = lib.formatnum(details[mg.WILCOXON_N])
        html.append('<p>Just the number of records in the table from Step 2 '
            f'i.e. <strong>{n}</strong></p>')
        html.append('<p>The only remaining question is the probability of a '
            'sum as large as that observed (T) for a given N value. The '
            'smaller the N and the bigger the T the less likely the difference'
            f' between {label_a} and {label_b} could occur by chance.</p>')
    if page_break_after:
        html += f"<br><hr><br><div class='{CSS_PAGE_BREAK_BEFORE}'></div>"
    output.append_divider(html, title, indiv_title='')
    return ''.join(html)

def pearsonsr_output(list_x, list_y, pearsons_r, p, df, label_x, label_y,
        report_name, css_fil, css_idx=0, dp=mg.DEFAULT_STATS_DP,
        details=None, *, add_to_report=False, page_break_after=False):
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (
        mg.CSS_PAGE_BREAK_BEFORE, css_idx)
    slope, intercept, unused, y0, y1 = core_stats.get_regression_dets(
        list_x, list_y)
    line_lst = [y0, y1]
    html = []
    footnotes = []
    x_vs_y = f'"{label_x}"' + _(' vs ') + f'"{label_y}"'
    title = (
        _("Results of Pearson's Test of Linear Correlation for %s") % x_vs_y)
    title_html = f'<h2>{title}</h2>'
    html.append(title_html)
    ## always footnote 1 (so can hardwire anchor)
    html.append('\n<p>' + _("Two-tailed p value")
        + f': {lib.OutputLib.get_p(p)}'
        + " <a href='#ft1'><sup>1</sup></a></p>")
    add_footnote(footnotes, content=mg.P_EXPLAN_REL)
    html.append('\n<p>' + _("Pearson's R statistic")
        + f': {round(pearsons_r, dp)}</p>')
    html.append(f'\n<p>{mg.DF}: {df}</p>')
    html.append('<p>Linear Regression Details: '
        "<a href='#ft2'><sup>2</sup></a></p>")
    add_footnote(footnotes, content='Always look at the scatter plot when '
        'interpreting the linear regression line.</p>')
    html.append(f'<ul><li>Slope: {round(slope, dp)}</li>')
    html.append(f'<li>Intercept: {round(intercept, dp)}</li></ul>')
    output.append_divider(html, title, indiv_title='')
    css_dojo_dic = lib.OutputLib.extract_dojo_style(css_fil)
    item_colours = output.colour_mappings_to_item_colours(
        css_dojo_dic['colour_mappings'])
    title_dets_html = ''  ## already got an appropriate title for whole section
    show_borders = True
    series_dets = [{mg.CHARTS_SERIES_LBL_IN_LEGEND: None,  ## None if only one series
        mg.LIST_X: list_x, mg.LIST_Y: list_y,
        mg.INC_REGRESSION: True, mg.LINE_LST: line_lst, mg.DATA_TUPS: None}]  ## only Dojo needs data_tups
    n_chart = 'N = ' + lib.formatnum(len(list_x))
    charting_pylab.add_scatterplot(css_dojo_dic['plot_bg'], show_borders,
        css_dojo_dic['major_gridline_colour'],
        css_dojo_dic['plot_font_colour_filled'], n_chart, series_dets, label_x,
        label_y, x_vs_y, title_dets_html, add_to_report, report_name, html,
        dot_colour=item_colours[0])
    add_footnotes(footnotes, html)
    ## details
    if details:
        html.append('<p>No worked example available for this test</p>')
    if page_break_after:
        html.append(f"<br><hr><br><div class='{CSS_PAGE_BREAK_BEFORE}'></div>")
    output.append_divider(html, title, indiv_title='scatterplot')
    return ''.join(html)

def spearmansr_output(list_x, list_y, spearmans_r, p, df, label_x, label_y, 
        report_name, css_fil, css_idx=0, dp=mg.DEFAULT_STATS_DP, 
        details=None, *, add_to_report=False, page_break_after=False):
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (
        mg.CSS_PAGE_BREAK_BEFORE, css_idx)
    slope, intercept, unused, y0, y1 = core_stats.get_regression_dets(
        list_x, list_y)
    line_lst = [y0, y1]
    html = []
    footnotes = []
    x_vs_y = f'"{label_x}"' + _(' vs ') + f'"{label_y}"'
    title = (
        _("Results of Spearman's Test of Linear Correlation for %s") % x_vs_y)
    title_html = f'<h2>{title}</h2>'
    html.append(title_html)
    ## always footnote 1 (so can hardwire anchor)
    html.append('\n<p>' + _('p value') + f': {lib.OutputLib.get_p(p)}'
        + " <a href='#ft1'><sup>1</sup></a></p>")
    add_footnote(footnotes, content=mg.P_EXPLAN_REL)
    html.append('\n<p>' + _("Spearman's R statistic")
        + f': {round(spearmans_r, dp)}</p>')
    html.append(f'\n<p>{mg.DF}: {df}</p>')
    html.append('<p>Linear Regression Details: '
        "<a href='#ft2'><sup>2</sup></a></p>")
    add_footnote(footnotes, content='Always look at the scatter plot when '
        'interpreting the linear regression line.</p>')
    html.append(f'<ul><li>Slope: {round(slope, dp)}</li>')
    html.append(f'<li>Intercept: {round(intercept, dp)}</li></ul>')
    output.append_divider(html, title, indiv_title='')
    css_dojo_dic = lib.OutputLib.extract_dojo_style(css_fil)
    item_colours = output.colour_mappings_to_item_colours(
        css_dojo_dic['colour_mappings'])
    title_dets_html = ''  ## already got an appropriate title for whole section
    show_borders = True
    series_dets = [{mg.CHARTS_SERIES_LBL_IN_LEGEND: None,  ## None if only one series
        mg.LIST_X: list_x, mg.LIST_Y: list_y, mg.INC_REGRESSION: True, 
        mg.LINE_LST: line_lst, mg.DATA_TUPS: None}]  ## only Dojo needs data_tups
    n_chart = 'N = ' + lib.formatnum(len(list_x))
    charting_pylab.add_scatterplot(css_dojo_dic['plot_bg'], show_borders,
        css_dojo_dic['major_gridline_colour'],
        css_dojo_dic['plot_font_colour_filled'], n_chart, series_dets, label_x,
        label_y, x_vs_y, title_dets_html, add_to_report, report_name, html,
        dot_colour=item_colours[0])
    add_footnotes(footnotes, html)
    ## details
    if details:
        html.append(f"""<hr>
        <h2>Worked Example of Key Calculations</h2>
        <h3>Step 1 - Set up table of paired results</h3>
        <table>
        <thead>
            <tr><th>{label_x}</th><th>{label_y}</th></tr>
        </thead>
        <tbody>""")
        MAX_DISPLAY_ROWS = 50
        init_tbl = details[mg.SPEARMANS_INIT_TBL]
        for row in init_tbl[:MAX_DISPLAY_ROWS]:
            html.append('<tr><td>{}</td><td>{}</td></tr>'.format(*row[:2]))
        diff_init = len(init_tbl) - MAX_DISPLAY_ROWS
        if diff_init > 0: 
            html.append(f"""
            <tr><td colspan="2">{lib.formatnum(diff_init)} {row_str(diff_init)} 
            not displayed</td></tr>""")
        html.append('</tbody></table>')
        html.append(f"""
        <h3>Step 2 - Work out ranks for the x and y values</h3>
        <p>Rank such that all examples of a value get the mean rank for all
        items of that value</p>
        <table>
        <thead>
            <tr><th>{label_x}</th><th>Rank within<br>{label_x}</th></tr>
        </thead>
        <tbody>""")
        x_ranked = details[mg.SPEARMANS_X_RANKED]
        for x, x_rank in x_ranked[:MAX_DISPLAY_ROWS]:
            html.append(f'<tr><td>{x}</td><td>{x_rank}</td></tr>')
        diff_x_ranked = len(x_ranked) - MAX_DISPLAY_ROWS
        if diff_x_ranked > 0: 
            html.append(f"""<tr><td colspan='2'>{lib.formatnum(diff_x_ranked)}
                {row_str(diff_x_ranked)} not displayed</td></tr>""")
        html.append('</tbody></table>')
        html.append(f"""
        <p>Do the same for {label_y} values</p>
        <table>
        <thead>
            <tr><th>{label_y}</th><th>Rank within<br>{label_y}</th></tr>
        </thead>
        <tbody>""")
        y_ranked = details[mg.SPEARMANS_Y_RANKED]
        for y, y_rank in y_ranked[:MAX_DISPLAY_ROWS]:
            html.append(f'<tr><td>{y}</td><td>{y_rank}</td></tr>')
        diff_y_ranked = len(y_ranked) - MAX_DISPLAY_ROWS
        if diff_y_ranked > 0: 
            html.append(f"""<tr><td colspan='2'>{lib.formatnum(diff_y_ranked)}
                {row_str(diff_y_ranked)} not displayed</td></tr>""")
        html.append('</tbody></table>')
        html.append(f"""
        <h3>Step 3 - Add ranks to original table or pairs</h3>
        <table>
        <thead>
            <tr>
                <th>{label_x}</th>
                <th>{label_y}</th>
                <th>{label_x} Ranks</th>
                <th>{label_y} Ranks</th>
            </tr>
        </thead>
        <tbody>""")
        for row in init_tbl[:MAX_DISPLAY_ROWS]:
            html.append("""<tr>
                <td>{}</td><td>{}</td><td>{}</td><td>{}</td>
            </tr>""".format(*row[:4]))
        if diff_init > 0:
            html.append(f"""<tr><td colspan='4'>{lib.formatnum(diff_init)}
                {row_str(diff_init)} not displayed</td></tr>""")
        html.append('</tbody></table>')
        html.append(f"""
        <h3>Step 4 - Add difference in ranks and get square of diff</h3>
        <table>
        <thead>
            <tr>
                <th>{label_x}</th>
                <th>{label_y}</th>
                <th>{label_x} Ranks</th>
                <th>{label_y} Ranks</th>
                <th>Difference</th>
                <th>Diff Squared</th>
            </tr>
        </thead>
        <tbody>""")
        for row in init_tbl[:MAX_DISPLAY_ROWS]:
            html.append("""<tr>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
            </tr>""".format(*row))
        if diff_init > 0: 
            html.append(f"""<tr><td colspan='6'>{lib.formatnum(diff_init)}
                {row_str(diff_init)} not displayed</td></tr>""")
        html.append('</tbody></table>')
        n = lib.formatnum(details[mg.SPEARMANS_N])
        n_cubed_minus_n = lib.formatnum(details[mg.SPEARMANS_N_CUBED_MINUS_N])
        html.append(f"""
        <h3>Step 5 - Count N pairs, cube it, and subtract N</h3>
        N = {n}<br>N<sup>3</sup> - N = {n_cubed_minus_n}""")
        tot_d_squared = lib.formatnum(details[mg.SPEARMANS_TOT_D_SQUARED])
        tot_d_squared_minus_6 = lib.formatnum(
            details[mg.SPEARMANS_TOT_D_SQUARED_x_6])
        n_cubed_minus_n = lib.formatnum(details[mg.SPEARMANS_N_CUBED_MINUS_N])
        pre_rho = lib.formatnum(details[mg.SPEARMANS_PRE_RHO])
        rho = details[mg.SPEARMANS_RHO]
        html.append(f"""
        <h3>Step 6 - Total squared diffs, multiply by 6, divide by N<sup>3</sup> -
        N value</h3>
        Total squared diffs = {tot_d_squared}
        <br>Multiplied by 6 = {tot_d_squared_minus_6}<br>
        Divided by N<sup>3</sup> - N value ({n_cubed_minus_n}) = {pre_rho}
        """)
        html.append(f"""
        <h3>Step 7 - Subtract from 1 to get Spearman's rho</h3>
        rho = 1 - {pre_rho} = {rho} (all rounded to 4dp)""")
        html.append('<p>The only remaining question is the probability of a '
            'rho that size occurring for a given N value</p>')
    if page_break_after:
        html.append(f"<br><hr><br><div class='{CSS_PAGE_BREAK_BEFORE}'></div>")
    output.append_divider(html, title, indiv_title='scatterplot')
    return ''.join(html)

def chisquare_output(chi, p,
        var_label_a, var_label_b,
        add_to_report, report_name,
        val_labels_a, val_labels_b,
        lst_obs, lst_exp,
        min_count, perc_cells_lt_5, df,
        css_fil, css_idx=0,
        dp=mg.DEFAULT_STATS_DP, details=None, page_break_after=False):
    CSS_SPACEHOLDER = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_SPACEHOLDER, css_idx)
    CSS_FIRST_COL_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_COL_VAR, css_idx)
    CSS_FIRST_ROW_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_ROW_VAR, css_idx)
    CSS_ROW_VAL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_ROW_VAL, css_idx)
    CSS_DATACELL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_DATACELL, css_idx)
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (
        mg.CSS_PAGE_BREAK_BEFORE, css_idx)
    var_label_a = cgi.escape(var_label_a)
    var_label_b = cgi.escape(var_label_b)
    try:
        val_labels_a_html = list(map(cgi.escape, val_labels_a))
        val_labels_b_html = list(map(cgi.escape, val_labels_b))
    except AttributeError:
        ## e.g. an int
        val_labels_a_html = val_labels_a
        val_labels_b_html = val_labels_b
    cells_per_col = 2
    val_labels_a_n = len(val_labels_a)
    val_labels_b_n = len(val_labels_b)
    html = []
    footnotes = []
    title = (_("Results of Pearson's Chi Square Test of Association Between "
        f'"{var_label_a}" and "{var_label_b}"'))
    title_html = mg.TBL_TITLE_START + f'<h2>{title}</h2>{mg.TBL_TITLE_END}'
    html.append(title_html)
    html.append(mg.TBL_SUBTITLE_START + mg.TBL_SUBTITLE_END)
    ## always footnote 1 (so can hardwire anchor)
    html.append('\n<p>' + _('p value') + f': {lib.OutputLib.get_p(p)}'
        + " <a href='#ft1'><sup>1</sup></a></p>")
    add_footnote(footnotes, content=mg.P_EXPLAN_REL)  
    html.append('\n<p>' + _("Pearson's Chi Square statistic")
        + f': {round(chi, dp)}</p>')
    html.append(f'\n<p>{mg.DF}: {df}</p>')
    ## headings
    html.append(f"\n\n{mg.REPORT_TABLE_START}<table cellspacing='0'>\n<thead>")
    html.append(f"\n<tr><th class='{CSS_SPACEHOLDER}' colspan=2 rowspan=3></th>")
    colspan2use = (val_labels_b_n+1)*cells_per_col
    html.append(f"<th class='{CSS_FIRST_COL_VAR}' "
        + f'colspan={colspan2use}>{var_label_b}</th></tr>')
    html.append('\n<tr>')
    for val in val_labels_b:
        html.append(f'<th colspan={cells_per_col}>{val}</th>')
    html.append(f'<th colspan={cells_per_col}>' + _('TOTAL')
        + '</th></tr>\n<tr>')
    for unused in range(val_labels_b_n + 1):
        html.append('<th>' + _('Obs') + '</th><th>' + _('Exp') + '</th>')
    html.append('</tr>')
    ## body
    html.append('\n\n</thead><tbody>')
    item_i = 0
    html.append(f"\n<tr><td class='{CSS_FIRST_ROW_VAR}' "
        f'rowspan={val_labels_a_n + 1}>{var_label_a}</td>')
    col_obs_tots = [0, ] * val_labels_b_n
    col_exp_tots = [0, ] * val_labels_b_n
    ## total row totals
    row_obs_tot_tot = 0 
    row_exp_tot_tot = 0
    for val_a in val_labels_a_html:
        row_obs_tot = 0
        row_exp_tot = 0
        html.append(f"<td class='{CSS_ROW_VAL}'>{val_a}</td>")        
        for col_i, unused in enumerate(val_labels_b_html):
            obs = lst_obs[item_i]
            exp = lst_exp[item_i]
            html.append(f"<td class='{CSS_DATACELL}'>"
                + f"{obs}</td><td class='{CSS_DATACELL}'>{round(exp, 1)}</td>")
            row_obs_tot += obs
            row_exp_tot += exp
            col_obs_tots[col_i] += obs
            col_exp_tots[col_i] += exp
            item_i += 1
        ## add total for row
        row_obs_tot_tot += row_obs_tot
        row_exp_tot_tot += row_exp_tot
        html.append(f"<td class='{CSS_DATACELL}'>"
            + f"{row_obs_tot}</td><td class='{CSS_DATACELL}'>"
            + f'{round(row_exp_tot, 1)}</td>')
        html.append('</tr>\n<tr>')
    ## add totals row
    col_tots = zip(col_obs_tots, col_exp_tots)
    html.append(f"<td class='{CSS_ROW_VAL}'>" + _('TOTAL') + '</td>')
    for col_obs_tot, col_exp_tot in col_tots:
        html.append(f"<td class='{CSS_DATACELL}'>"
            + f'{col_obs_tot}</td>'
            + f"<td class='{CSS_DATACELL}'>{round(col_exp_tot, 1)}</td>")
    ## add total of totals
    tot_tot_str = round(row_exp_tot_tot, 1)
    html.append(f"<td class='{CSS_DATACELL}'>"
        f"{row_obs_tot_tot}</td><td class='{CSS_DATACELL}'>{tot_tot_str}</td>")
    html.append('</tr>')
    html.append(f'\n</tbody>\n</table>{mg.REPORT_TABLE_END}\n')
    ## warnings
    html.append('\n<p>' + _('Minimum expected cell count')
        + f': {round(min_count, dp)}</p>')
    html.append('\n<p>% ' + _('cells with expected count < 5')
        + f': {round(perc_cells_lt_5, 1)}</p>')
    add_footnotes(footnotes, html)
    ## details
    if details:
        html.append("""
        <hr>
        <h2>Worked Example of Key Calculations</h2>
        <h3>Step 1 - Calculate row and column sums</h3>""")
        html.append('<h4>Row sums</h4>')
        for row_n in range(1, details[mg.CHI_ROW_N] + 1):
            vals_added = ' + '.join(lib.formatnum(x) for x
                in details[mg.CHI_ROW_OBS][row_n])
            row_sums = lib.formatnum(details[mg.CHI_ROW_SUMS][row_n])
            html.append(f"""
            <p>Row {row_n} Total: {vals_added} = <strong>{row_sums}</strong></p>
            """)
        html.append('<h4>Column sums</h4>')
        for col_n in range(1, details[mg.CHI_COL_N] + 1):
            vals_added = ' + '.join(lib.formatnum(x) for x
                in details[mg.CHI_COL_OBS][col_n])
            col_sums = lib.formatnum(details[mg.CHI_COL_SUMS][col_n])
            html.append(f"""
            <p>Col {col_n} Total: {vals_added} = <strong>{col_sums}</strong></p>
            """)
        html.append("""
        <h3>Step 2 - Calculate expected values per cell</h3>
        <p>Multiply row and column sums for cell and divide by grand total
        </p>""")
        for coord, cell_data in details[mg.CHI_CELLS_DATA].items():
            row_n, col_n = coord
            row_sum = lib.formatnum(cell_data[mg.CHI_CELL_ROW_SUM])
            col_sum = lib.formatnum(cell_data[mg.CHI_CELL_COL_SUM])
            grand_tot = lib.formatnum(details[mg.CHI_GRAND_TOT])
            expected = lib.formatnum(cell_data[mg.CHI_EXPECTED])
            html.append(f"""<p>Row {row_n}, Col {col_n}: ({row_sum} x {col_sum})
            /{grand_tot} = <strong>{expected}</strong></p>""")
        html.append("""
        <h3>Step 3 - Calculate the differences between observed and expected per
        cell, square them, and divide by expected value</h3>""")
        for coord, cell_data in details[mg.CHI_CELLS_DATA].items():
            row_n, col_n = coord
            larger = lib.formatnum(cell_data[mg.CHI_MAX_OBS_EXP])
            smaller = lib.formatnum(cell_data[mg.CHI_MIN_OBS_EXP])
            expected = lib.formatnum(cell_data[mg.CHI_EXPECTED])
            diff = lib.formatnum(cell_data[mg.CHI_DIFF])
            diff_squ = lib.formatnum(cell_data[mg.CHI_DIFF_SQU])
            pre_chi = lib.formatnum(cell_data[mg.CHI_PRE_CHI])
            html.append(f"""
            <p>Row {row_n}, Col {col_n}:
            ({larger} - {smaller})<sup>2</sup> / {expected}
            = ({diff})<sup>2</sup> / {expected}
            = {diff_squ} / {expected}
            = <strong>{pre_chi}</strong></p>""")
        html.append(
            '<h3>Step 4 - Add up all the results to get Χ<sup>2</sup></h3>')
        vals_added = ' + '.join(str(x) for x in details[mg.CHI_PRE_CHIS])
        html.append(
            f'<p>{vals_added} = <strong>{details[mg.CHI_CHI_SQU]}</strong></p>')
        row_n = details[mg.CHI_ROW_N]
        col_n = details[mg.CHI_COL_N]
        row_n_minus_1 = details[mg.CHI_ROW_N_MINUS_1]
        col_n_minus_1 = details[mg.CHI_COL_N_MINUS_1]
        chi_df = details[mg.CHI_DF]
        html.append(f"""
        <h3>Step 5 - Calculate degrees of freedom</h3>
        <p>N rows - 1 multiplied by N columns - 1</p>
        <p>({row_n} - 1) x ({col_n} - 1) = {row_n_minus_1} x {col_n_minus_1}
        = <strong>{chi_df}</strong></p>""")
        html.append("""<p>The only remaining question is the probability of a
            Chi Square value that size occurring for a given degrees of freedom
            value</p>""")
    if page_break_after:
        html.append(f"<br><hr><br><div class='{CSS_PAGE_BREAK_BEFORE}'></div>")
    ## clustered bar charts
    html.append('<hr><p>Interpreting the Proportions chart - look at the '
        '"All combined" category - the more different the other '
        f'{var_label_a} categories look from this the more likely the Chi '
        f'Square test will detect a difference. Within each {var_label_a} '
        f'category the {var_label_b} values add up to 1 i.e. 100%. This is '
        'not the same way of displaying data as a clustered bar chart although '
        'the similarity can be confusing.</p>')
    css_dojo_dic = lib.OutputLib.extract_dojo_style(css_fil)
    item_colours = output.colour_mappings_to_item_colours(
        css_dojo_dic['colour_mappings'])
    output.append_divider(html, title, indiv_title='')
    add_chi_square_clustered_barcharts(css_dojo_dic['plot_bg'], item_colours,
        css_dojo_dic['major_gridline_colour'], lst_obs, var_label_a,
        var_label_b, val_labels_a, val_labels_b, val_labels_b_n,
        report_name, html, add_to_report=add_to_report)
    return ''.join(html)

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
        val_labels_b_n, report_name, html, *, add_to_report):
    ## NB list_obs is bs within a and we need the other way around
    debug = False
    ## width = 7 
    n_clusters = len(val_labels_b)
    if n_clusters < 8:
        width = 7
        height = None  ## allow height to be set by golden ratio
    else:
        width = n_clusters*1.5
        height = 4.5
    rows_n = int(len(lst_obs) / val_labels_b_n)
    cols_n = val_labels_b_n
    bs_in_as = np.array(lst_obs).reshape(rows_n, cols_n)
    as_in_bs_lst = bs_in_as.transpose().tolist()
    ## proportions of b within a
    propns_bs_in_as = []
    ## expected propn bs in as - so we have a reference to compare rest to
    total = sum(lst_obs)
    expected_propn_bs_in_as = []
    for as_in_b_lst in as_in_bs_lst:
        expected_propn_bs_in_as.append(float(sum(as_in_b_lst))/float(total))
    propns_bs_in_as.append(expected_propn_bs_in_as)
    ## actual observed bs in as
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
    title_tmp = _("%(laba)s and %(labb)s - %(y)s")
    title_overrides = {'fontsize': 14}
    ## chart 1 - proportions ****************************************************
    plot = boomslang.Plot()
    y_label = _('Proportions')
    title = title_tmp % {'laba': var_label_a, 'labb': var_label_b, 'y': y_label}
    plot.setTitle(title)
    plot.setTitleProperties(title_overrides)
    plot.setDimensions(width, height)
    plot.hasLegend(columns=val_labels_b_n, location='lower left')
    plot.setAxesLabelSize(11)
    plot.setXTickLabelSize(get_xaxis_fontsize(val_labels_a))
    plot.setLegendLabelSize(9)
    val_labels_a_with_ref = val_labels_a[:]
    val_labels_a_with_ref.insert(0, 'All\ncombined')
    if debug:
        print(grid_bg)
        print(bar_colours)
        print(line_colour)
        print(var_label_a)
        print(y_label)
        print(val_labels_a_with_ref)
        print(val_labels_b)
        print(propns_as_in_bs_lst)
    charting_pylab.config_clustered_barchart(grid_bg, bar_colours,
        plot, var_label_a, y_label, val_labels_a_with_ref, val_labels_b,
        propns_as_in_bs_lst)
    img_src = charting_pylab.save_report_img(add_to_report, report_name,
        save_func=plot.save, dpi=None)
    html.append(f'\n{mg.IMG_SRC_START}{img_src}{mg.IMG_SRC_END}')
    output.append_divider(html, title, indiv_title='proportion')
    ## chart 2 - freqs **********************************************************
    plot = boomslang.Plot()
    y_label = _('Frequencies')
    title = title_tmp % {'laba': var_label_a, 'labb': var_label_b, 'y': y_label}
    plot.setTitle(title)
    plot.setTitleProperties(title_overrides)
    plot.setDimensions(width, height)
    plot.hasLegend(columns=val_labels_b_n, location='lower left')
    plot.setAxesLabelSize(11)
    plot.setXTickLabelSize(get_xaxis_fontsize(val_labels_a))
    plot.setLegendLabelSize(9)
    ## only need 6 because program limits to that. See core_stats.get_obs_exp().
    charting_pylab.config_clustered_barchart(grid_bg, bar_colours,
        plot, var_label_a, y_label, val_labels_a, val_labels_b, as_in_bs_lst)
    img_src = charting_pylab.save_report_img(add_to_report, report_name,
        save_func=plot.save, dpi=None)
    html.append(f'\n{mg.IMG_SRC_START}{img_src}{mg.IMG_SRC_END}')
    output.append_divider(html, title, indiv_title='frequency')

def kruskal_wallis_output(h, p,
        label_gp, label_a, label_b,
        dics, df, label_avg, css_idx=0,
        dp=mg.DEFAULT_STATS_DP, details=None, *,
        page_break_after=False):
    CSS_FIRST_COL_VAR = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_FIRST_COL_VAR, css_idx)
    CSS_LBL = mg.CSS_SUFFIX_TEMPLATE % (mg.CSS_LBL, css_idx)
    CSS_PAGE_BREAK_BEFORE = mg.CSS_SUFFIX_TEMPLATE % (
        mg.CSS_PAGE_BREAK_BEFORE, css_idx)
    html = []
    footnotes = []
    title = (
        _("Results of Kruskal-Wallis H test of average %(avg)s for "
        "%(label_gp)s groups from \"%(a)s\" to \"%(b)s\"") % 
        {'label_gp': label_gp, 'avg': label_avg, 'a': label_a, 'b': label_b})
    title_html = f'{mg.TBL_TITLE_START}\n<h2>{title}</h2>\n{mg.TBL_TITLE_END}'
    html.append(title_html)
    html.append(mg.TBL_SUBTITLE_START + mg.TBL_SUBTITLE_END)
    ## always footnote 1 (so can hardwire anchor)
    html.append('\n<p>' + _('p value') + f': {lib.OutputLib.get_p(p)}'
        + " <a href='#ft1'><sup>1</sup></a></p>")
    add_footnote(footnotes, content=mg.P_EXPLAN_DIFF) 
    html.append('\n<p>' + _('Kruskal-Wallis H statistic')
        + f': {round(h, dp)}</p>')
    html.append(f'\n<p>{mg.DF}: {df}</p>')
    html.append(f"\n\n{mg.REPORT_TABLE_START}<table cellspacing='0'>\n<thead>")
    html.append('\n<tr>'
        + f"<th class='{CSS_FIRST_COL_VAR}'>" + _('Group') + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('N') + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('Median') + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('Min') + '</th>'
        + f"\n<th class='{CSS_FIRST_COL_VAR}'>" + _('Max') + '</th></tr>')
    html.append('\n</thead>\n<tbody>')
    row_tpl = (f"\n<tr><td class='{CSS_LBL}'>" + '%s</td><td>%s</td>'
        + '<td>%s</td><td>%s</td><td>%s</td></tr>')
    for dic in dics:
        html.append(row_tpl % (dic[mg.STATS_DIC_LBL],
            lib.formatnum(dic[mg.STATS_DIC_N]),
            round(dic[mg.STATS_DIC_MEDIAN], dp), dic[mg.STATS_DIC_MIN],
            dic[mg.STATS_DIC_MAX]))
    html.append(f'\n</tbody></table>{mg.REPORT_TABLE_END}')
    add_footnotes(footnotes, html)
    ## details
    if details:
        html.append('<p>No worked example available for this test</p>')
    if page_break_after:
        html.append(f"<br><hr><br><div class='{CSS_PAGE_BREAK_BEFORE}'></div>")
    output.append_divider(html, title, indiv_title='')
    return ''.join(html)
