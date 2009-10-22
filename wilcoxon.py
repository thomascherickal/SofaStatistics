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
    
    min_data_type = my_globals.VAR_TYPE_ORD
    
    def GetExamples(self):
        eg1 = _("Answers the question, are the elements of paired sets of "
                "data different from each other?")
        eg2 = _("For example, do tutors get better student ratings after a "
            "training session?")
        eg3 = _("Or have house values changed since the recession began?")
        return eg1, eg2, eg3
    
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
        script_lst.append("t, p = core_stats.wilcoxont(sample_a, sample_b)")
        script_lst.append("wilcoxon_output = stats_output.wilcoxon_output(" + \
            "t, p, label_a, label_b, dp=dp,\n    " + \
            "level=my_globals.OUTPUT_RESULTS_ONLY, css_idx=%s, " % css_idx + \
            "page_break_after=False)")
        script_lst.append("fil.write(wilcoxon_output)")
        return "\n".join(script_lst)