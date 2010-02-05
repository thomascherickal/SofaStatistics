#! /usr/bin/env python
# -*- coding: utf-8 -*-

import wx

import my_globals
import lib
import indep2var


class DlgConfig(indep2var.DlgIndep2VarConfig):

    averaged = _("Averaged")    
    min_data_type = my_globals.VAR_TYPE_QUANT

    def get_examples(self):
        eg1 = _("Answers the question, do 3 or more groups have a "
            "different average?")
        eg2 = _("For example, is average IQ the same for students from "
            "three different universities?")
        eg3 = _("Or is the average height different between "
            "British, Australian, Canadian, and New Zealand adults?")
        return eg1, eg2, eg3
    
    def update_phrase(self):
        """
        Update phrase based on GroupBy, Group A, Group B, and Averaged by field.
        """
        unused, unused, unused, unused, label_a, unused, label_b, unused, \
            label_avg = self.get_drop_vals()
        self.lblPhrase.SetLabel(_("Does average %(avg)s vary in the groups "
            "between \"%(a)s\" and \"%(b)s\"?") % {"avg": label_avg, 
                                                   "a": label_a, "b": label_b})

    def add_other_var_opts(self):
        self.radHigh = wx.RadioBox(self.panel, -1, _("Algorithm"), 
                         choices=(_("Precision (best choice unless too slow)"),
                                  _("Speed")),
                         style=wx.RA_SPECIFY_COLS)
        self.szrVarsRight.Add(self.radHigh, 0)
    
    def get_script(self, css_idx, add_to_report, report_name):
        "Build script from inputs"
        debug = False
        var_gp_numeric, var_gp, label_gp, val_a, label_a, val_b, label_b, \
            var_avg, label_avg = self.get_drop_vals()
        script_lst = [u"dp = 3"]
        script_lst.append(lib.get_tbl_filt_clause(self.dbe, self.db, self.tbl))
        lst_samples = []
        lst_labels = []
        # need sample for each of the values in range
        idx_val_a, idx_val_b = indep2var.get_range_idxs(self.vals, val_a, val_b)
        vals_in_range = self.vals[idx_val_a: idx_val_b + 1]
        strGet_Sample = u"%s = core_stats.get_list(" + \
            u"dbe=u\"%s\", " % self.dbe + \
            u"cur=cur, tbl=u\"%s\",\n    " % self.tbl + \
            u"tbl_filt=tbl_filt, " + \
            u"flds=flds, " + \
            u"fld_measure=u\"%s\", " % var_avg + \
            u"fld_filter=u\"%s\", " % var_gp + \
            u"filter_val=%s)"        
        for i, val in enumerate(vals_in_range):
            sample_name = u"sample_%s" % i
            val_str_quoted = val if var_gp_numeric else u"u\"%s\"" % val
            script_lst.append(strGet_Sample % (sample_name, val_str_quoted))
            lst_samples.append(sample_name)
            try:
                val_label = self.val_dics[var_gp][val]
            except KeyError:
                val_label = unicode(val).upper()
            lst_labels.append(val_label)
        samples = u"[%s]" % u", ".join(lst_samples)
        script_lst.append(u"samples = %s" % samples)
        script_lst.append(u"labels = %s" % lst_labels)
        script_lst.append(u"label_a = u\"%s\"" % label_a)
        script_lst.append(u"label_b = u\"%s\"" % label_b)
        script_lst.append(u"label_avg = u\"%s\"" % label_avg)
        script_lst.append(u"add_to_report = %s" % ("True" if add_to_report \
                          else "False"))
        script_lst.append(u"report_name = u\"%s\"" % 
                          lib.escape_win_path(report_name))
        high = not self.radHigh.GetSelection()
        script_lst.append(u"p, F, dics, sswn, dfwn, mean_squ_wn, ssbn, dfbn, "
            u"mean_squ_bn = \\\n    core_stats.anova(samples, labels, "
            u"high=%s)" % high)
        script_lst.append(u"anova_output = stats_output.anova_output("
                u"samples, F, p, dics, sswn, dfwn, mean_squ_wn, "
            u"\n    ssbn, dfbn, mean_squ_bn, label_a, label_b, label_avg, "
                u"add_to_report, report_name, dp,"
            u"\n    level=my_globals.OUTPUT_RESULTS_ONLY, "
                u"css_idx=%s, page_break_after=False)" % css_idx)
        script_lst.append(u"fil.write(anova_output)")
        return u"\n".join(script_lst)