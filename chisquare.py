#! /usr/bin/env python
# -*- coding: utf-8 -*-
import pprint

import my_globals as mg
import lib
import paired2var


class DlgConfig(paired2var.DlgPaired2VarConfig):
    
    min_data_type = mg.VAR_TYPE_CAT
    
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
        self.lbl_phrase.SetLabel(_("Is there a relationship between "
            "\"%(a)s\" and \"%(b)s\"") % {"a": label_a, "b": label_b})
    
    def get_script(self, css_idx, add_to_report, report_name):
        "Build script from inputs"
        script_lst = []
        var_a, label_a, var_b, label_b = self.get_drop_vals()
        script_lst.append(u"add_to_report = %s" % ("True" if add_to_report
                          else "False"))
        script_lst.append(u"report_name = u\"%s\"" % 
                          lib.escape_win_path(report_name))
        script_lst.append(u"dp = 3")
        script_lst.append(u"var_label_a = u\"%s\"" % label_a)
        script_lst.append(u"var_label_b = u\"%s\"" % label_b)
        unused, tbl_filt = lib.get_tbl_filt(self.dbe, self.db, self.tbl)
        where_tbl_filt, and_tbl_filt = lib.get_tbl_filts(tbl_filt)
        script_lst.append(u"chisq, p, vals_a, vals_b, lst_obs, lst_exp, " +
            u"min_count, perc_cells_lt_5, df = \\" +
            u"\n    core_stats.pearsons_chisquare(dbe=u\"%s\", " % self.dbe +
            u"db=u\"%s\", " % self.db +
            u"cur=cur, tbl=u\"%s\"," % self.tbl +
            u"\n    flds=flds, fld_a=u\"%s\", fld_b=u\"%s\"," % (var_a, var_b) +
            u"\n    tbl_filt=u\"\"\" %s \"\"\", " % tbl_filt +
            u"where_tbl_filt=\"\"\" %s \"\"\"," % where_tbl_filt +
            u"\n    and_tbl_filt=\"\"\" %s \"\"\")" % and_tbl_filt)
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
            u"\n    level=mg.OUTPUT_RESULTS_ONLY, " +
            u"css_idx=%s, page_break_after=False)" % css_idx)
        script_lst.append(u"fil.write(chisquare_output)")
        return u"\n".join(script_lst)