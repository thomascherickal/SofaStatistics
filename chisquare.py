#! /usr/bin/env python
# -*- coding: utf-8 -*-
import pprint

import my_globals
import lib
import paired2var


class DlgConfig(paired2var.DlgPaired2VarConfig):
    
    min_data_type = my_globals.VAR_TYPE_CAT
    
    def get_examples(self):
        eg1 = _("Answers the question, is there a relationship "
            "between two variables.")
        eg2 = _("For example, is there a relationship between ethnic "
            "group and gender?")
        eg3 = _("Or between gender and political preference?")
        return eg1, eg2, eg3

    def update_phrase(self):
        """
        Update phrase based on Group A and Group B.
        """
        unused, label_a, unused, label_b = self.get_drop_vals()
        self.lblPhrase.SetLabel(_("Is there a relationship between "
            "\"%(a)s\" and \"%(b)s\"") % {"a": label_a, "b": label_b})
    
    def get_script(self, css_idx, add_to_report, report_name):
        "Build script from inputs"
        script_lst = []
        var_a, label_a, var_b, label_b = self.get_drop_vals()
        script_lst.append(u"add_to_report = %s" % ("True" if add_to_report
                          else "False"))
        script_lst.append(u"report_name = \"%s\"" % 
                          lib.escape_win_path(report_name))
        script_lst.append(u"dp = 3")
        script_lst.append(u"var_label_a = \"%s\"" % label_a)
        script_lst.append(u"var_label_b = \"%s\"" % label_b)
        script_lst.append(u"chisq, p, vals_a, vals_b, lst_obs, lst_exp, " +
            u"min_count, perc_cells_lt_5, df = \\\n" +
            u"    core_stats.pearsons_chisquare(dbe=\"%s\", " % self.dbe +
            u"db=\"%s\", " % self.db +
            u"cur=cur, tbl=\"%s\"," % self.tbl +
            u"\n    flds=flds, fld_a=\"%s\", fld_b=\"%s\")" % (var_a, var_b))
        val_dic_a = self.val_dics.get(var_a, {})
        val_dic_b = self.val_dics.get(var_b, {})
        script_lst.append(u"val_dic_a = %s" % pprint.pformat(val_dic_a))
        script_lst.append(u"val_dic_b = %s" % pprint.pformat(val_dic_b))
        script_lst.append(u"val_labels_a = [val_dic_a.get(x, x) for " +
                          u"x in vals_a]")
        script_lst.append(u"val_labels_b = [val_dic_b.get(x, x) for " +
                          u"x in vals_b]")        
        script_lst.append(u"chisquare_output = " +
            u"stats_output.chisquare_output(chisq, p, " +
            u"var_label_a, var_label_b, add_to_report, report_name, " +
            u"\n    val_labels_a, val_labels_b," +
            u"\n    lst_obs, lst_exp, min_count, perc_cells_lt_5, df, dp=dp," +
            u"\n    level=my_globals.OUTPUT_RESULTS_ONLY, " +
            u"css_idx=%s, page_break_after=False)" % css_idx)
        script_lst.append(u"fil.write(chisquare_output)")
        return u"\n".join(script_lst)