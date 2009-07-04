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
        eg1 = "Answers the question, is there a linear relationship " + \
            "between two variables i.e. do they both change together?"
        eg2 = "For example, does IQ correlate with exam scores?"
        eg3 = "Or does a brief measure of addiction correlate with a much " + \
            "longer measure?"
        return eg1, eg2, eg3

    def UpdatePhrase(self):
        """
        Update phrase based on Group A and Group B.
        """
        var_a, label_a, var_b, label_b = self.GetDropVals()
        self.lblPhrase.SetLabel("Are \"%s\" and " % label_a + \
            "\"%s\" correlated - do they change together in a " % label_b + \
            "linear fashion?")
    
    def getScript(self):
        "Build script from inputs"
        script_lst = []
        var_a, label_a, var_b, label_b = self.GetDropVals()
        script_lst.append("sample_a, sample_b = " + \
            "core_stats.get_paired_lists(" + \
            "dbe=\"%s\", " % self.dbe + \
            "cur=cur, tbl=\"%s\",\n    " % self.tbl_name + \
            "fld_measure_a=\"%s\", " % var_a + \
            "fld_measure_b=\"%s\")" % var_b)
        script_lst.append("dp = 3")
        script_lst.append("label_a = \"%s\"" % label_a)
        script_lst.append("label_b = \"%s\"" % label_b)
        script_lst.append("r, p = " + \
            "core_stats.pearsonr(sample_a, sample_b)")
        script_lst.append("pearsonsr_output = " + \
                          "stats_output.pearsonsr_output(" + \
            "r, p, label_a, label_b, dp=dp,\n    " + \
            "level=my_globals.OUTPUT_RESULTS_ONLY, page_break_after=False)")
        script_lst.append("fil.write(pearsonsr_output)")
        return "\n".join(script_lst)
