#! /usr/bin/env python
# -*- coding: utf-8 -*-

import my_globals
import indep2var


class DlgConfig(indep2var.DlgIndep2VarConfig):

    averaged = _("Averaged")
    min_data_type = my_globals.VAR_TYPE_ORD

    def GetExamples(self):
        eg1 = _("Answers the question, do 3 or more groups have a "
            "different average?")
        eg2 = _("For example, is average income the same for people from "
            "three different cities?")
        eg3 = _("Or is the average amount spent annually on pets different "
            "between dog, cat, and pony owners?")
        return eg1, eg2, eg3
    
    def UpdatePhrase(self):
        """
        Update phrase based on GroupBy, Group A, Group B, and Averaged by field.
        """
        unused, unused, unused, unused, label_a, unused, label_b, unused, \
            label_avg = self.get_drop_vals()
        self.lblPhrase.SetLabel(_("Does average %(avg)s vary in the groups "
                                 "between \"%(a)s\" and \"%(b)s\"?") % \
                                 {"avg": label_avg, "a": label_a, "b": label_b})

    def getScript(self, css_idx):
        "Build script from inputs"
        var_gp_numeric, var_gp, label_gp, val_a, label_a, val_b, label_b, \
            var_avg, label_avg = self.get_drop_vals()        
        strGet_Sample = u"%s = core_stats.get_list(" + \
            u"dbe=\"%s\", " % self.dbe + \
            u"db=\"%s\", " % self.db + \
            u"cur=cur, tbl=\"%s\",\n    " % self.tbl + \
            u"flds=flds, " + \
            u"fld_measure=\"%s\", " % var_avg + \
            u"fld_filter=\"%s\", " % var_gp + \
            u"filter_val=%s)"
        # need sample for each of the values in range
        idx_val_a, idx_val_b = indep2var.get_range_idxs(self.vals, val_a, val_b)
        vals_in_range = self.vals[idx_val_a: idx_val_b + 1]
        script_lst = [u"dp = 3"]
        lst_samples = []
        for i, val in enumerate(vals_in_range):
            sample_name = u"sample_%s" % i
            val_str_quoted = val if var_gp_numeric else "\"%s\"" % val
            script_lst.append(strGet_Sample % (sample_name, val_str_quoted))
            lst_samples.append(sample_name)
        # only need labels for start and end of range
        samples = u"(" + u", ".join(lst_samples) + u")"
        script_lst.append(u"samples = %s" % samples)        
        script_lst.append(u"label_a = \"%s\"" % label_a)
        script_lst.append(u"label_b = \"%s\"" % label_b)
        script_lst.append(u"label_avg = \"%s\"" % label_avg)
        script_lst.append(u"indep = True")
        script_lst.append(u"h, p = " + \
            u"core_stats.kruskalwallish(*samples)")
        script_lst.append(u"kruskal_wallis_output = " + \
            u"stats_output.kruskal_wallis_output(" + \
            u"h, p, label_a," + \
            u"\n    label_b, label_avg, dp," + \
            u"\n    level=my_globals.OUTPUT_RESULTS_ONLY, " + \
            u"css_idx=%s, page_break_after=False)" % css_idx)
        script_lst.append(u"fil.write(kruskal_wallis_output)")
        return u"\n".join(script_lst)
    