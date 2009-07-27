#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os

import wx

import my_globals
import indep2var


class DlgConfig(indep2var.DlgIndep2VarConfig):

    averaged = "Ranked"
    min_data_type = my_globals.VAR_TYPE_ORD

    def GetExamples(self):
        eg1 = "Answers the question, do 2 groups have different results " + \
            "(higher or lower ranks)?"
        eg2 = "For example, do male or female tutors get different rating " + \
            "scores from students?"
        eg3 = "Or do IT graduates have a different income in their first " + \
        " year in the workforce compared with law graduates?"
        return eg1, eg2, eg3
    
    def UpdatePhrase(self):
        """
        Update phrase based on GroupBy, Group A, Group B, and Ranked by field.
        """
        var_gp, label_gp, val_a, label_a, val_b, label_b, var_avg, \
            label_avg = self.GetDropVals()
        self.lblPhrase.SetLabel("Does %s \"%s\" have" % (label_gp, label_a) + \
            " a different %s from \"%s\"?" % (label_avg, label_b))

    def getScript(self):
        "Build script from inputs"
        script_lst = []
        var_gp, label_gp, val_a, label_a, val_b, label_b, var_ranked, \
            label_ranked = self.GetDropVals()
        strGet_Sample = "sample_%s = core_stats.get_list(" + \
            "dbe=\"%s\", " % self.dbe + \
            "cur=cur, tbl=\"%s\",\n    " % self.tbl + \
            "fld_measure=\"%s\", " % var_ranked + \
            "fld_filter=\"%s\", " % var_gp + \
            "filter_val=%s)"
        script_lst.append("dp = 3")
        script_lst.append(strGet_Sample % ("a", val_a))
        script_lst.append(strGet_Sample % ("b", val_b))
        script_lst.append("label_a = \"%s\"" % label_a)
        script_lst.append("label_b = \"%s\"" % label_b)
        script_lst.append("label_ranked = \"%s\"" % label_ranked)
        script_lst.append("u, p = core_stats.mannwhitneyu(sample_a, sample_b)")
        script_lst.append("mann_whitney_output = " + \
            "stats_output.mann_whitney_output(" + \
            "u, p, label_a, label_b, label_ranked, dp,\n     " + \
            "level=my_globals.OUTPUT_RESULTS_ONLY, page_break_after=False)")
        script_lst.append("fil.write(mann_whitney_output)")
        return "\n".join(script_lst)
