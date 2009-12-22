#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os

import wx

import my_globals
import indep2var


class DlgConfig(indep2var.DlgIndep2VarConfig):

    averaged = _("Ranked")
    min_data_type = my_globals.VAR_TYPE_ORD

    def GetExamples(self):
        eg1 = _("Answers the question, do 2 groups have different results "
            "(higher or lower ranks)?")
        eg2 = _("For example, do male or female tutors get different rating "
            "scores from students?")
        eg3 = _("Or do IT graduates have a different income in their first "
        " year in the workforce compared with law graduates?")
        return eg1, eg2, eg3
    
    def UpdatePhrase(self):
        """
        Update phrase based on GroupBy, Group A, Group B, and Ranked by field.
        """
        unused, unused, label_gp, unused, label_a, unused, label_b, unused, \
            label_avg = self.get_drop_vals()
        self.lblPhrase.SetLabel(_("Does %(gp)s \"%(a)s\" have a different "
                                  "%(avg)s from \"%(b)s\"?") % \
                                  {"gp": label_gp, "a": label_a, 
                                   "avg": label_avg, "b": label_b})

    def getScript(self, css_idx):
        "Build script from inputs"
        var_gp_numeric, var_gp, label_gp, val_a, label_a, val_b, label_b, \
            var_ranked, label_ranked = self.get_drop_vals()
        script_lst = [u"dp = 3"]
        script_lst.append(util.get_tbl_filt_clause(self.dbe, self.db, self.tbl))
        strGet_Sample = u"sample_%s = core_stats.get_list(" + \
            u"dbe=\"%s\", " % self.dbe + \
            u"cur=cur, tbl=\"%s\",\n    " % self.tbl + \
            u"tbl_filt=tbl_filt, " + \
            u"flds=flds, " + \
            u"fld_measure=\"%s\", " % var_ranked + \
            u"fld_filter=\"%s\", " % var_gp + \
            u"filter_val=%s)"
        val_str_quoted_a = val if var_gp_numeric else "\"%s\"" % val_a
        val_str_quoted_b = val if var_gp_numeric else "\"%s\"" % val_b
        script_lst.append(strGet_Sample % (u"a", val_str_quoted_a))
        script_lst.append(strGet_Sample % (u"b", val_str_quoted_b))
        script_lst.append(u"label_a = \"%s\"" % label_a)
        script_lst.append(u"label_b = \"%s\"" % label_b)
        script_lst.append(u"label_ranked = \"%s\"" % label_ranked)
        script_lst.append(u"u, p, dic_a, dic_b = " + \
            u"core_stats.mannwhitneyu(sample_a, sample_b, label_a, label_b)")
        script_lst.append(u"mann_whitney_output = " + \
            u"stats_output.mann_whitney_output(" + \
            u"u, p, dic_a, dic_b, label_ranked, dp,\n     " + \
            u"level=my_globals.OUTPUT_RESULTS_ONLY, css_idx=%s, " % css_idx + \
            u"page_break_after=False)")
        script_lst.append(u"fil.write(mann_whitney_output)")
        return u"\n".join(script_lst)