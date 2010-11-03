#! /usr/bin/env python
# -*- coding: utf-8 -*-
import my_globals as mg
import lib
import getdata
import paired2var

dd = getdata.get_dd()


class DlgConfig(paired2var.DlgPaired2VarConfig):
    
    min_data_type = mg.VAR_TYPE_ORD
    
    def get_examples(self):
        eg1 = _("Answers the question, are the elements of paired sets of "
                "data different from each other?")
        eg2 = _("For example, do tutors get better student ratings after a "
            "training session?")
        eg3 = _("Or have house values changed since the recession began?")
        return eg1, eg2, eg3
    
    def get_script(self, css_idx, css_fil, add_to_report, report_name):
        "Build script from inputs"
        script_lst = []
        var_a, label_a, var_b, label_b = self.get_drop_vals()
        script_lst.append(lib.get_tbl_filt_clause(dd.dbe, dd.db, dd.tbl))
        script_lst.append(u"sample_a, sample_b, data_tups = "
                           u"core_stats.get_paired_data("
                           u"dbe=u\"%s\", " % dd.dbe +
                           u"cur=cur, tbl=u\"%s\"," % dd.tbl +
                           u"\n    tbl_filt=tbl_filt, "
                           u"fld_a=u\"%s\", " % var_a +
                           u"fld_b=u\"%s\")" % var_b)
        script_lst.append(u"dp = 3")
        script_lst.append(u"label_a = u\"%s\"" % label_a)
        script_lst.append(u"label_b = u\"%s\"" % label_b)
        script_lst.append(u"t, p = core_stats.wilcoxont(sample_a, sample_b)")
        script_lst.append(u"wilcoxon_output = stats_output.wilcoxon_output("
                    u"t, p, label_a, label_b,"
                    u"\n    css_fil=\"%s\", css_idx=%s, " % (css_fil, css_idx) +
                    u"dp=dp, level=mg.OUTPUT_RESULTS_ONLY, "
                    u"page_break_after=False)")
        script_lst.append(u"fil.write(wilcoxon_output)")
        return u"\n".join(script_lst)