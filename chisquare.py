#! /usr/bin/env python
# -*- coding: utf-8 -*-
import pprint

import my_globals
import paired2var


class DlgConfig(paired2var.DlgPaired2VarConfig):
    """
    GenConfig - provides reusable interface for data selection, setting labels 
        etc.  Sets values for db, default_tbl etc and responds to selections 
        etc.
    OutputButtons - provides standard buttons for output dialogs.
    """
    
    min_data_type = my_globals.VAR_TYPE_CAT
    
    def GetExamples(self):
        eg1 = _("Answers the question, is there a relationship "
            "between two variables.")
        eg2 = _("For example, is there a relationship between ethnic "
            "group and gender?")
        eg3 = _("Or between gender and political preference?")
        return eg1, eg2, eg3

    def UpdatePhrase(self):
        """
        Update phrase based on Group A and Group B.
        """
        var_a, label_a, var_b, label_b = self.GetDropVals()
        self.lblPhrase.SetLabel(_("Is there a relationship between "
            "\"%(a)s\" and \"%(b)s\"") % {"a": label_a, "b": label_b})
    
    def getScript(self, css_idx):
        "Build script from inputs"
        script_lst = []
        var_a, label_a, var_b, label_b = self.GetDropVals()
        script_lst.append("dp = 3")
        script_lst.append("var_label_a = \"%s\"" % label_a)
        script_lst.append("var_label_b = \"%s\"" % label_b)
        script_lst.append("chisq, p, vals_a, vals_b, lst_obs, lst_exp, " + \
            "min_count, perc_cells_lt_5, df = \\\n" + \
            "    core_stats.pearsons_chisquare(dbe=\"%s\", " % self.dbe + \
            "cur=cur, tbl=\"%s\"," % self.tbl + \
            "\n    flds=flds, fld_a=\"%s\", fld_b=\"%s\")" % (var_a, var_b))
        val_dic_a = self.val_dics.get(var_a, {})
        val_dic_b = self.val_dics.get(var_b, {})
        script_lst.append("val_dic_a = %s" % pprint.pformat(val_dic_a))
        script_lst.append("val_dic_b = %s" % pprint.pformat(val_dic_b))
        script_lst.append("val_labels_a = [val_dic_a.get(x, x) for " + \
                          "x in vals_a]")
        script_lst.append("val_labels_b = [val_dic_b.get(x, x) for " + \
                          "x in vals_b]")        
        script_lst.append("chisquare_output = " + \
            "stats_output.chisquare_output(chisq, p, " + \
            "var_label_a, var_label_b," + \
            "\n    val_labels_a, val_labels_b," + \
            "\n    lst_obs, lst_exp, min_count, perc_cells_lt_5, df, dp=dp," + \
            "\n    level=my_globals.OUTPUT_RESULTS_ONLY, " + \
            "css_idx=%s, page_break_after=False)" % css_idx)
        script_lst.append("fil.write(chisquare_output)")
        return "\n".join(script_lst)
