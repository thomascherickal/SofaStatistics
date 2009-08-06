#! /usr/bin/env python
# -*- coding: utf-8 -*-

import my_globals
import indep2var


class DlgConfig(indep2var.DlgIndep2VarConfig):

    averaged = "Averaged"    
    min_data_type = my_globals.VAR_TYPE_QUANT

    def GetExamples(self):
        eg1 = "Answers the question, do 3 or more groups have a " + \
            "different average?"
        eg2 = "For example, is average IQ the same for students from " + \
            "three different universities?"
        eg3 = "Or is the average height different between " + \
            "British, Australian, Canadian, and New Zealand adults?"
        return eg1, eg2, eg3
    
    def UpdatePhrase(self):
        """
        Update phrase based on GroupBy, Group A, Group B, and Averaged by field.
        """
        var_gp, label_gp, val_a, label_a, val_b, label_b, var_avg, \
            label_avg = self.GetDropVals()
        self.lblPhrase.SetLabel("Does average %s " % label_avg + "vary in " + \
            "the groups between \"%s\" and \"%s\"?" % (label_a, label_b))

    def getScript(self, css_idx):
        "Build script from inputs"
        script_lst = []
        var_gp, label_gp, val_a, label_a, val_b, label_b, var_avg, \
            label_avg = self.GetDropVals()        
        # need list of values in range
        var_gp_numeric = self.flds[var_gp][my_globals.FLD_BOLNUMERIC]
        if var_gp_numeric:
            val_a = float(val_a)
            val_b = float(val_b)
        else:
            val_a = val_a.strip('"')
            val_b = val_b.strip('"')
        idx_val_a = self.vals.index(val_a)
        idx_val_b = self.vals.index(val_b)
        vals_in_range = self.vals[idx_val_a: idx_val_b + 1]
        if not var_gp_numeric:
            vals_in_range = ["\"%s\"" % x for x in vals_in_range]
        strGet_Sample = "%s = core_stats.get_list(" + \
            "dbe=\"%s\", " % self.dbe + \
            "cur=cur, tbl=\"%s\",\n    " % self.tbl + \
            "fld_measure=\"%s\", " % var_avg + \
            "fld_filter=\"%s\", " % var_gp + \
            "filter_val=%s)"
        script_lst.append("dp = 3")
        lst_samples = []
        lst_labels = []
        for i, val in enumerate(vals_in_range):
            sample_name = "sample_%s" % i
            script_lst.append(strGet_Sample % (sample_name, val))
            lst_samples.append(sample_name)
            val_label = self.val_dics[var_gp].get(val)
            lst_labels.append(val_label)
        samples = "[" + ", ".join(lst_samples) + "]"
        script_lst.append("lst_samples = %s" % samples)
        script_lst.append("lst_labels = %s" % lst_labels)
        script_lst.append("label_a = \"%s\"" % label_a)
        script_lst.append("label_b = \"%s\"" % label_b)
        script_lst.append("label_avg = \"%s\"" % label_avg)
        script_lst.append("indep = True")
        script_lst.append("f, p, dics = " + \
            "core_stats.anova(lst_samples, lst_labels)")
        script_lst.append("anova_output = " + \
            "stats_output.anova_output(" + \
            "f, p, dics, label_a," + \
            "\n    label_b, label_avg, dp," + \
            "\n    level=my_globals.OUTPUT_RESULTS_ONLY, " + \
            "css_idx=%s, page_break_after=False)" % css_idx)
        script_lst.append("fil.write(anova_output)")
        return "\n".join(script_lst)
    