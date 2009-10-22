#! /usr/bin/env python
# -*- coding: utf-8 -*-
import my_globals
import indep2var


class DlgConfig(indep2var.DlgIndep2VarConfig):

    averaged = _("Averaged")
    min_data_type = my_globals.VAR_TYPE_QUANT

    def GetExamples(self):
        eg1 = _("Answers the question, do 2 groups have a different average?")
        eg2 = _("For example, do PhD graduates earn the same on average as "
                    "Masters graduates?")
        eg3 = _("Or do parents of pre-schoolers get the same amount of "
                    "sleep on average as parents of teenagers?")
        return eg1, eg2, eg3
    
    def UpdatePhrase(self):
        """
        Update phrase based on GroupBy, Group A, Group B, and Averaged by field.
        """
        var_gp, label_gp, val_a, label_a, val_b, label_b, \
            var_avg, label_avg = self.GetDropVals()
        self.lblPhrase.SetLabel(_("Does %(gp)s \"%(a)s\" have a different "
                                  "average %(avg)s from \"%(b)s\"?") % \
                                  {"gp": label_gp, "a": label_a, 
                                   "avg": label_avg, "b": label_b})

    def getScript(self, css_idx):
        "Build script from inputs"
        script_lst = []
        var_gp, label_gp, val_a, label_a, val_b, label_b, \
            var_avg, label_avg = self.GetDropVals()
        strGet_Sample = "sample_%s = core_stats.get_list(" + \
            "dbe=\"%s\", " % self.dbe + \
            "cur=cur, tbl=\"%s\",\n    " % self.tbl + \
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
            "level=my_globals.OUTPUT_RESULTS_ONLY, " + \
            "css_idx=%s, page_break_after=False)" % css_idx)
        script_lst.append("fil.write(ttest_output)")
        return "\n".join(script_lst)
    