#! /usr/bin/env python
# -*- coding: utf-8 -*-
import my_globals
import lib
import paired2var


class DlgConfig(paired2var.DlgPaired2VarConfig):
    
    min_data_type = my_globals.VAR_TYPE_ORD
    
    def get_examples(self):
        eg1 = _("Answers the question, are the elements of paired sets of "
                "data different from each other?")
        eg2 = _("For example, do tutors get better student ratings after a "
            "training session?")
        eg3 = _("Or have house values changed since the recession began?")
        return eg1, eg2, eg3
    
    def get_script(self, css_idx, add_to_report, report_name):
        "Build script from inputs"
        script_lst = []
        var_a, label_a, var_b, label_b = self.get_drop_vals()
        script_lst.append(lib.get_tbl_filt_clause(self.dbe, self.db, self.tbl))
        script_lst.append(u"sample_a, sample_b = " + \
            u"core_stats.get_paired_lists(" + \
            u"dbe=u\"%s\", " % self.dbe + \
            u"cur=cur, tbl=u\"%s\",\n    " % self.tbl + \
            u"tbl_filt=tbl_filt, " + \
            u"fld_a=u\"%s\", " % var_a + \
            u"fld_b=u\"%s\")" % var_b)
        script_lst.append(u"dp = 3")
        script_lst.append(u"label_a = u\"%s\"" % label_a)
        script_lst.append(u"label_b = u\"%s\"" % label_b)
        script_lst.append(u"t, p = core_stats.wilcoxont(sample_a, sample_b)")
        script_lst.append(u"wilcoxon_output = stats_output.wilcoxon_output(" + \
            u"t, p, label_a, label_b, dp=dp,\n    " + \
            u"level=my_globals.OUTPUT_RESULTS_ONLY, css_idx=%s, " % css_idx + \
            u"page_break_after=False)")
        script_lst.append(u"fil.write(wilcoxon_output)")
        return u"\n".join(script_lst)