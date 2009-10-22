#! /usr/bin/env python
# -*- coding: utf-8 -*-
import my_globals
import paired2var


class DlgConfig(paired2var.DlgPaired2VarConfig):
    """
    GenConfig - provides reusable interface for data selection, setting labels 
        etc.  Sets values for db, default_tbl etc and responds to selections 
        etc.
    OutputButtons - provides standard buttons for output dialogs.
    """
    
    min_data_type = my_globals.VAR_TYPE_QUANT
    
    def GetExamples(self):
        eg1 = _("Answers the question, is there a linear relationship "
                "between two variables i.e. do they both change together?")
        eg2 = _("For example, does IQ correlate with exam scores?")
        eg3 = _("Or does a brief measure of addiction correlate with a much "
                "longer measure?")
        return eg1, eg2, eg3

    def UpdatePhrase(self):
        """
        Update phrase based on Group A and Group B.
        """
        var_a, label_a, var_b, label_b = self.GetDropVals()
        self.lblPhrase.SetLabel(_("Are \"%(a)s\" and \"%(b)s\" correlated - "
                               "do they change together in a linear fashion?") \
                                % {"a": label_a, "b": label_b})
    
    def getScript(self, css_idx):
        "Build script from inputs"
        script_lst = []
        var_a, label_a, var_b, label_b = self.GetDropVals()
        script_lst.append("sample_a, sample_b = " + \
            "core_stats.get_paired_lists(" + \
            "dbe=\"%s\", " % self.dbe + \
            "cur=cur, tbl=\"%s\",\n    " % self.tbl + \
            "fld_a=\"%s\", " % var_a + \
            "fld_b=\"%s\")" % var_b)
        script_lst.append("dp = 3")
        script_lst.append("label_a = \"%s\"" % label_a)
        script_lst.append("label_b = \"%s\"" % label_b)
        script_lst.append("r, p = " + \
            "core_stats.pearsonr(sample_a, sample_b)")
        script_lst.append("pearsonsr_output = " + \
                          "stats_output.pearsonsr_output(" + \
            "r, p, label_a, label_b, dp=dp,\n    " + \
            "level=my_globals.OUTPUT_RESULTS_ONLY, " + \
            "css_idx=%s, page_break_after=False)" % css_idx)
        script_lst.append("fil.write(pearsonsr_output)")
        return "\n".join(script_lst)
