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
        eg1 = "Answers the question, are the elements of paired sets of " + \
                "data different from each other?"
        eg2 = "For example, do people have a higher average weight after a " + \
                "diet compared with before?"
        eg3 = "Or does average performance in IQ tests vary between " + \
                "morning and mid afternoon?"
        return eg1, eg2, eg3
    
    def getScript(self):
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
        script_lst.append("indep = False")
        script_lst.append("t, p, dic_a, dic_b = " + \
            "core_stats.ttest_rel(sample_a, sample_b, label_a, label_b)")
        script_lst.append("ttest_output = stats_output.ttest_output(" + \
            "t, p, dic_a, dic_b, label_avg=\"\", dp=dp, indep=indep,\n    " + \
            "level=my_globals.OUTPUT_RESULTS_ONLY, page_break_after=False)")
        script_lst.append("fil.write(ttest_output)")
        return "\n".join(script_lst)