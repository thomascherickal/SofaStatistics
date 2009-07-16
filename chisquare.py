#! /usr/bin/env python
# -*- coding: utf-8 -*-
import paired2var


class DlgConfig(paired2var.DlgPaired2VarConfig):
    """
    GenConfig - provides reusable interface for data selection, setting labels 
        etc.  Sets values for db, default_tbl etc and responds to selections 
        etc.
    OutputButtons - provides standard buttons for output dialogs.
    """
   
    def GetExamples(self):
        eg1 = "Answers the question, is there a relationship " + \
            "between two variables."
        eg2 = "For example, is there a relationship between ethnic " + \
            "group and gender?"
        eg3 = "Or between gender and political preference?"
        return eg1, eg2, eg3

    def UpdatePhrase(self):
        """
        Update phrase based on Group A and Group B.
        """
        var_a, label_a, var_b, label_b = self.GetDropVals()
        self.lblPhrase.SetLabel("Is there a relationship between " + \
            "\"%s\" and \"%s\"" % (label_a, label_b))
    
    def getScript(self):
        "Build script from inputs"
        script_lst = []
        var_a, label_a, var_b, label_b = self.GetDropVals()
        script_lst.append("dp = 3")
        script_lst.append("label_a = \"%s\"" % label_a)
        script_lst.append("label_b = \"%s\"" % label_b)
        script_lst.append("chisq, p, lst_obs, lst_exp, min_count, " + \
            "perc_cells_lt_5, df = \\\n" + \
            "    core_stats.pearsons_chisquare(dbe=\"%s\", " % self.dbe + \
            "cur=cur, tbl=\"%s\", " % self.tbl + \
            "fld_a=\"%s\", fld_b=\"%s\")" % (var_a, var_b))
        script_lst.append("chisquare_output = " + \
            "stats_output.chisquare_output(chisq, p, lst_obs, lst_exp," + \
            "\n    min_count, perc_cells_lt_5, df, label_a, label_b, dp=dp," + \
            "\n    level=my_globals.OUTPUT_RESULTS_ONLY, " + \
            "page_break_after=False)")
        script_lst.append("fil.write(chisquare_output)")
        return "\n".join(script_lst)
