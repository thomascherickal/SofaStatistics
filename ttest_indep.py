#! /usr/bin/env python
# -*- coding: utf-8 -*-
import my_globals
import lib
import indep2var


class DlgConfig(indep2var.DlgIndep2VarConfig):

    averaged = _("Averaged")
    min_data_type = my_globals.VAR_TYPE_QUANT

    def get_examples(self):
        eg1 = _("Answers the question, do 2 groups have a different average?")
        eg2 = _("For example, do PhD graduates earn the same on average as "
                    "Masters graduates?")
        eg3 = _("Or do parents of pre-schoolers get the same amount of "
                    "sleep on average as parents of teenagers?")
        return eg1, eg2, eg3
    
    def update_phrase(self):
        """
        Update phrase based on GroupBy, Group A, Group B, and Averaged by field.
        """
        unused, unused, label_gp, unused, label_a, unused, label_b, unused, \
            label_avg = self.get_drop_vals()
        self.lblPhrase.SetLabel(_("Does %(gp)s \"%(a)s\" have a different "
                                  "average %(avg)s from \"%(b)s\"?") % \
                                  {"gp": label_gp, "a": label_a, 
                                   "avg": label_avg, "b": label_b})

    def get_script(self, css_idx, add_to_report, report_name):
        "Build script from inputs"
        script_lst = []
        var_gp_numeric, var_gp, label_gp, val_a, label_a, val_b, label_b, \
            var_avg, label_avg = self.get_drop_vals()
        script_lst.append(u"dp = 3")
        script_lst.append(lib.get_tbl_filt_clause(self.dbe, self.db, self.tbl))
        val_str_quoted_a = val_a if var_gp_numeric else "\"%s\"" % val_a
        val_str_quoted_b = val_b if var_gp_numeric else "\"%s\"" % val_b
        strGet_Sample = u"sample_%s = core_stats.get_list(" + \
            u"dbe=\"%s\", " % self.dbe + \
            u"cur=cur, tbl=\"%s\",\n    " % self.tbl + \
            u"tbl_filt=tbl_filt, " + \
            u"flds=flds, " + \
            u"fld_measure=\"%s\", " % var_avg + \
            u"fld_filter=\"%s\", " % var_gp + \
            u"filter_val=%s)"
        script_lst.append(strGet_Sample % (u"a", val_a))
        script_lst.append(strGet_Sample % (u"b", val_b))
        script_lst.append(u"label_a = \"%s\"" % label_a)
        script_lst.append(u"label_b = \"%s\"" % label_b)
        script_lst.append(u"label_avg = \"%s\"" % label_avg)
        script_lst.append(u"report_name = \"%s\"" % report_name)
        script_lst.append(u"add_to_report = %s" % ("True" if add_to_report \
                          else "False"))
        script_lst.append(u"t, p, dic_a, dic_b = " + \
            u"core_stats.ttest_ind(sample_a, sample_b, label_a, label_b)")
        script_lst.append(u"ttest_indep_output = "
            u"stats_output.ttest_indep_output("
            u"sample_a, sample_b, t, p, "
            u"\n    dic_a, dic_b, label_avg, add_to_report, report_name, dp, "
            u"\n    level=my_globals.OUTPUT_RESULTS_ONLY, "
            u"css_idx=%s, page_break_after=False)" % css_idx)
        script_lst.append(u"fil.write(ttest_indep_output)")
        return u"\n".join(script_lst)    