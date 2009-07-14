#! /usr/bin/env python
# -*- coding: utf-8 -*-

import indep2var


class DlgConfig(indep2var.DlgIndep2VarConfig):

    averaged = "Averaged"

    def GetExamples(self):
        eg1 = "Answers the question, do 2 groups have a different average?"
        eg2 = "For example, do PhD graduates earn the same on average as " + \
                    "Masters graduates?"
        eg3 = "Or do parents of pre-schoolers get the same amount of " + \
                    "sleep on average as parents of teenagers?"
        return eg1, eg2, eg3
    
    def UpdatePhrase(self):
        """
        Update phrase based on GroupBy, Group A, Group B, and Averaged by field.
        """
        var_gp, label_gp, val_a, label_a, val_b, label_b, var_avg, \
            label_avg = self.GetDropVals()
        self.lblPhrase.SetLabel("Does %s \"%s\" have" % (label_gp, label_a) + \
            " a different average %s from \"%s\"?" % (label_avg, label_b))

    def getScript(self):
        "Build script from inputs"
        script_lst = []
        var_gp, label_gp, val_a, label_a, val_b, label_b, var_avg, \
            label_avg = self.GetDropVals()
        strGet_Sample = "sample_%s = core_stats.get_list(" + \
            "dbe=\"%s\", " % self.dbe + \
            "cur=cur, tbl=\"%s\",\n    " % self.tbl_name + \
            "fld_measure=\"%s\", " % var_avg + \
            "fld_filter=\"%s\", " % var_gp + \
            "filter_val=%s)"
        script_lst.append("dp = 3")
        script_lst.append(strGet_Sample % ("a", val_a))
        script_lst.append(strGet_Sample % ("b", val_b))
        script_lst.append("label_a = \"%s\"" % label_a)
        script_lst.append("label_b = \"%s\"" % label_b)
        script_lst.append("label_avg = \"%s\"" % label_avg)
        script_lst.append("indep = True")
        script_lst.append("t, p, dic_a, dic_b = " + \
            "core_stats.ttest_ind(sample_a, sample_b, label_a, label_b)")
        script_lst.append("ttest_output = stats_output.ttest_output(" + \
            "t, p, dic_a, dic_b, label_avg,\n    dp, indep, " + \
            "level=my_globals.OUTPUT_RESULTS_ONLY, page_break_after=False)")
        script_lst.append("fil.write(ttest_output)")
        return "\n".join(script_lst)
    