#! /usr/bin/env python
# -*- coding: utf-8 -*-
import my_globals
import lib
import paired2var


class DlgConfig(paired2var.DlgPaired2VarConfig):
    
    min_data_type = my_globals.VAR_TYPE_QUANT
    
    def GetExamples(self):
        eg1 = _("Answers the question, is there a linear relationship "
                "between two variables i.e. do they both change together?")
        eg2 = _("For example, does IQ correlate with exam scores?")
        eg3 = _("Or does a brief measure of addiction correlate with a much "
                "longer measure?")
        return eg1, eg2, eg3

    def UpdatePhrase(self):
        """
        Update phrase based on Group A and Group B.
        """
        unused, label_a, unused, label_b = self.get_drop_vals()
        self.lblPhrase.SetLabel(_("Are \"%(a)s\" and \"%(b)s\" correlated - "
                               "do they change together in a linear fashion?") \
                                % {"a": label_a, "b": label_b})
    
    def get_script(self, css_idx):
        "Build script from inputs"
        script_lst = []
        script_lst.append(lib.get_tbl_filt_clause(self.dbe, self.db, self.tbl))
        var_a, label_a, var_b, label_b = self.get_drop_vals()
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
        script_lst.append(u"r, p = " + \
            u"core_stats.pearsonr(sample_a, sample_b)")
        script_lst.append(u"pearsonsr_output = " + \
                          u"stats_output.pearsonsr_output(" + \
            u"r, p, label_a, label_b, dp=dp,\n    " + \
            u"level=my_globals.OUTPUT_RESULTS_ONLY, " + \
            u"css_idx=%s, page_break_after=False)" % css_idx)
        script_lst.append(u"fil.write(pearsonsr_output)")
        return u"\n".join(script_lst)