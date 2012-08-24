#! /usr/bin/env python
# -*- coding: utf-8 -*-

import wx

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
        try:
            unused, label_a, unused, label_b = self.get_drop_vals()
            self.lbl_phrase.SetLabel(_("Is there a relationship between "
                                       "\"%(a)s\" and \"%(b)s\"") % 
                                     {"a": label_a, "b": label_b})
            
        except Exception:
            self.lbl_phrase.SetLabel(u"")
    
    def get_script(self, css_idx, css_fil, report_name):
        "Build script from inputs"
        dd = mg.DATADETS_OBJ
        script_lst = []
        try:
            var_a, label_a, var_b, label_b = self.get_drop_vals()
        except Exception, e:
            wx.MessageBox(u"Unable to get script to make output. Orig error: %s" 
                          % lib.ue(e))
        script_lst.append(u"add_to_report = %s" % ("True" if mg.ADD2RPT
                          else "False"))
        script_lst.append(u"report_name = u\"%s\"" % 
                          lib.escape_pre_write(report_name))
        script_lst.append(u"dp = 3")
        script_lst.append(u"var_label_a = u\"%s\"" % label_a)
        script_lst.append(u"var_label_b = u\"%s\"" % label_b)
        unused, tbl_filt = lib.get_tbl_filt(dd.dbe, dd.db, dd.tbl)
        where_tbl_filt, and_tbl_filt = lib.get_tbl_filts(tbl_filt)
        script_lst.append(u"""
(chisq, p, vals_a, vals_b, lst_obs, lst_exp, 
 min_count, perc_cells_lt_5, df) = core_stats.pearsons_chisquare(dbe=u"%(dbe)s",
    db=u"%(db)s", cur=cur, tbl=u"%(tbl)s",
    flds=flds, fld_a=u"%(fld_a)s", fld_b=u"%(fld_b)s",
    tbl_filt=u\"\"\" %(tbl_filt)s \"\"\",
    where_tbl_filt=\"\"\" %(where_tbl_filt)s \"\"\",
    and_tbl_filt=\"\"\" %(and_tbl_filt)s \"\"\")""" %
            {u"dbe": dd.dbe, u"db": dd.db, u"tbl": dd.tbl, 
             u"fld_a": lib.esc_str_input(var_a),
             u"fld_b": lib.esc_str_input(var_b), u"tbl_filt": tbl_filt,
             u"where_tbl_filt": where_tbl_filt, u"and_tbl_filt": and_tbl_filt})
        val_dic_a = self.val_dics.get(var_a, {})
        val_dic_b = self.val_dics.get(var_b, {})
        script_lst.append(u"val_dic_a = %s" % lib.dic2unicode(val_dic_a))
        script_lst.append(u"val_dic_b = %s" % lib.dic2unicode(val_dic_b))
        script_lst.append(u"val_labels_a = [val_dic_a.get(x, unicode(x)) for "
                          u"x in vals_a]")
        script_lst.append(u"val_labels_b = [val_dic_b.get(x, unicode(x)) for "
                          u"x in vals_b]")        
        script_lst.append(u"""
chisquare_output = stats_output.chisquare_output(chisq, p, var_label_a, 
    var_label_b, add_to_report, report_name, val_labels_a, val_labels_b,
    lst_obs, lst_exp, min_count, perc_cells_lt_5, df,
    css_fil=u"%(css_fil)s", css_idx=%(css_idx)s, dp=dp,
    level=mg.OUTPUT_RESULTS_ONLY, page_break_after=False)""" %
            {u"css_fil": lib.escape_pre_write(css_fil), u"css_idx": css_idx})
        script_lst.append(u"fil.write(chisquare_output)")
        return u"\n".join(script_lst)

    def on_btn_help(self, event):
        import webbrowser
        url = u"http://www.sofastatistics.com/wiki/doku.php" + \
              u"?id=help:chisquare"
        webbrowser.open_new_tab(url)
        event.Skip()
        