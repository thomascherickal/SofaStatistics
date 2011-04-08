#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os
import wx

import my_globals as mg
import lib
import getdata
import indep2var


class DlgConfig(indep2var.DlgIndep2VarConfig):

    averaged = _("Ranked")
    range_gps = False
    min_data_type = mg.VAR_TYPE_ORD

    def get_examples(self):
        eg1 = _("Answers the question, do 2 groups have different results "
            "(higher or lower ranks)?")
        eg2 = _("For example, do male or female tutors get different rating "
            "scores from students?")
        eg3 = _("Or do IT graduates have a different income in their first "
        " year in the workforce compared with law graduates?")
        return eg1, eg2, eg3
    
    def update_phrase(self):
        """
        Update phrase based on GroupBy, Group A, Group B, and Ranked by field.
        """
        unused, unused, label_gp, unused, label_a, unused, label_b, unused, \
            label_avg = self.get_drop_vals()
        self.lbl_phrase.SetLabel(_("Does %(gp)s \"%(a)s\" have a different "
                                  "%(avg)s from \"%(b)s\"?") % \
                                  {"gp": label_gp, "a": label_a, 
                                   "avg": label_avg, "b": label_b})

    def get_script(self, css_idx, css_fil, add_to_report, report_name):
        "Build script from inputs"
        dd = getdata.get_dd()
        var_gp_numeric, var_gp, label_gp, val_a, label_a, val_b, label_b, \
            var_ranked, label_ranked = self.get_drop_vals()
        script_lst = [u"dp = 3"]
        script_lst.append(lib.get_tbl_filt_clause(dd.dbe, dd.db, dd.tbl))
        str_get_sample = (u"""
sample_%%s = core_stats.get_list(dbe=u"%(dbe)s", cur=cur, 
        tbl=u"%(tbl)s", tbl_filt=tbl_filt, flds=flds, 
        fld_measure=u"%(fld_measure)s", fld_filter=u"%(fld_filter)s",
        filter_val=%%s)""" % {u"dbe": dd.dbe, u"tbl": dd.tbl,
                              u"fld_measure": lib.esc_str_input(var_ranked),
                              u"fld_filter": lib.esc_str_input(var_gp)})
        val_str_quoted_a = val_a if var_gp_numeric else u"u\"%s\"" % val_a
        val_str_quoted_b = val_b if var_gp_numeric else u"u\"%s\"" % val_b
        script_lst.append(str_get_sample % (u"a", val_str_quoted_a))
        script_lst.append(str_get_sample % (u"b", val_str_quoted_b))
        script_lst.append(u"""
if len(sample_a) < 2 or len(sample_b) < 2:
    raise my_exceptions.TooFewSamplesForAnalysisException""")
        script_lst.append(u"label_a = u\"%s\"" % label_a)
        script_lst.append(u"label_b = u\"%s\"" % label_b)
        script_lst.append(u"label_ranked = u\"%s\"" % label_ranked)
        script_lst.append(u"u, p, dic_a, dic_b = " + \
            u"core_stats.mannwhitneyu(sample_a, sample_b, label_a, label_b)")
        script_lst.append(u"mann_whitney_output = "
            u"stats_output.mann_whitney_output("
            u"u, p, dic_a, dic_b, label_ranked, "
            u"css_fil=\"%s\", css_idx=%s, dp=dp,"  % (css_fil, css_idx) +
            u"\n     level=mg.OUTPUT_RESULTS_ONLY, page_break_after=False)")
        script_lst.append(u"fil.write(mann_whitney_output)")
        return u"\n".join(script_lst)

    def on_btn_help(self, event):
        import webbrowser
        url = u"http://www.sofastatistics.com/wiki/doku.php" + \
              u"?id=help:mann_whitney"
        webbrowser.open_new_tab(url)
        event.Skip()