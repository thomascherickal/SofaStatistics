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
        var_gp, label_gp, val_a, label_a, val_b, label_b, var_avg, \
            label_avg = self.GetDropVals()
        self.lblPhrase.SetLabel(_("Does %(gp)s \"%(a)s\" have a different "
                                  "%(avg)s from \"%(b)s\"?") % \
                                  {"gp": label_gp, "a": label_a, 
                                   "avg": label_avg, "b": label_b})

    def getScript(self, css_idx):
        "Build script from inputs"
        script_lst = []
        var_gp, label_gp, val_a, label_a, val_b, label_b, var_ranked, \
            label_ranked = self.GetDropVals()
        strGet_Sample = u"sample_%s = core_stats.get_list(" + \
            u"dbe=\"%s\", " % self.dbe + \
            u"cur=cur, tbl=\"%s\",\n    " % self.tbl + \
            u"fld_measure=\"%s\", " % var_ranked + \
            u"fld_filter=\"%s\", " % var_gp + \
            u"filter_val=%s)"
        script_lst.append(u"dp = 3")
        script_lst.append(strGet_Sample % (u"a", val_a))
        script_lst.append(strGet_Sample % (u"b", val_b))
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
