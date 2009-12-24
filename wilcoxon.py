#! /usr/bin/env python
# -*- coding: utf-8 -*-
import my_globals
import paired2var
import util


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
        var_a, label_a, var_b, label_b = self.get_drop_vals()
        script_lst.append(util.get_tbl_filt_clause(self.dbe, self.db, self.tbl))
        script_lst.append(u"sample_a, sample_b = " + \
            u"core_stats.get_paired_lists(" + \
            u"dbe=\"%s\", " % self.dbe + \
            u"cur=cur, tbl=\"%s\",\n    " % self.tbl + \
            u"tbl_filt=tbl_filt, " + \
            u"fld_a=\"%s\", " % var_a + \
            u"fld_b=\"%s\")" % var_b)
        script_lst.append(u"dp = 3")
        script_lst.append(u"label_a = \"%s\"" % label_a)
        script_lst.append(u"label_b = \"%s\"" % label_b)
        script_lst.append(u"t, p = core_stats.wilcoxont(sample_a, sample_b)")
        script_lst.append(u"wilcoxon_output = stats_output.wilcoxon_output(" + \
            u"t, p, label_a, label_b, dp=dp,\n    " + \
            u"level=my_globals.OUTPUT_RESULTS_ONLY, css_idx=%s, " % css_idx + \
            u"page_break_after=False)")
        script_lst.append(u"fil.write(wilcoxon_output)")
        return u"\n".join(script_lst)