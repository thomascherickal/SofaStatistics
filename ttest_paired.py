#! /usr/bin/env python
# -*- coding: utf-8 -*-
import my_globals
import lib
import paired2var


class DlgConfig(paired2var.DlgPaired2VarConfig):
    
    min_data_type = my_globals.VAR_TYPE_QUANT
    
    def get_examples(self):
        eg1 = _("Answers the question, are the elements of paired sets of "
                "data different from each other?")
        eg2 = _("For example, do people have a higher average weight after a "
                "diet compared with before?")
        eg3 = _("Or does average performance in IQ tests vary between "
                "morning and mid afternoon?")
        return eg1, eg2, eg3
    
    def get_script(self, css_idx, add_to_report, report_name):
        "Build script from inputs"
        script_lst = []
        var_a, label_a, var_b, label_b = self.get_drop_vals()
        script_lst.append(lib.get_tbl_filt_clause(self.dbe, self.db, self.tbl))
        script_lst.append(u"sample_a, sample_b = " +
            u"core_stats.get_paired_lists(" +
            u"dbe=\"%s\", " % self.dbe +
            u"cur=cur, tbl=\"%s\",\n    " % self.tbl +
            u"tbl_filt=tbl_filt, " +
            u"fld_a=\"%s\", " % var_a +
            u"fld_b=\"%s\")" % var_b)
        script_lst.append(u"dp = 3")
        script_lst.append(u"label_a = \"%s\"" % label_a)
        script_lst.append(u"label_b = \"%s\"" % label_b)
        script_lst.append(u"add_to_report = %s" % ("True" if add_to_report \
                          else "False"))
        script_lst.append(u"report_name = \"%s\"" % 
                          lib.escape_win_path(report_name))
        script_lst.append(u"t, p, dic_a, dic_b, diffs = " +
            u"core_stats.ttest_rel(sample_a, sample_b, label_a, label_b)")
        script_lst.append(u"ttest_paired_output = "
            u"stats_output.ttest_paired_output("
            u"sample_a, sample_b, t, p, "
            u"\n    dic_a, dic_b, diffs, add_to_report, report_name, "
                u"label_avg=\"\", dp=dp, "
            u"\n    level=my_globals.OUTPUT_RESULTS_ONLY, "
            u"css_idx=%s, page_break_after=False)" % css_idx)        
        script_lst.append(u"fil.write(ttest_paired_output)")
        return u"\n".join(script_lst)