#! /usr/bin/env python
# -*- coding: utf-8 -*-
import wx

import basic_lib as b
import my_globals as mg
import lib
import paired2var


class DlgConfig(paired2var.DlgPaired2VarConfig):
    
    min_data_type = mg.VAR_TYPE_ORD_KEY
    
    def get_examples(self):
        eg1 = _("Answers the question, are the elements of paired sets of "
                "data different from each other?")
        eg2 = _("For example, do tutors get better student ratings after a "
            "training session?")
        eg3 = _("Or have house values changed since the recession began?")
        return eg1, eg2, eg3
    
    def get_script(self, css_idx, css_fil, report_name, details):
        "Build script from inputs"
        dd = mg.DATADETS_OBJ
        script_lst = []
        try:
            var_a, label_a, var_b, label_b = self.get_drop_vals()
        except Exception, e:
            wx.MessageBox(u"Unable to get script to make output. Orig error: %s" 
                % b.ue(e))
        script_lst.append(lib.FiltLib.get_tbl_filt_clause(dd.dbe, dd.db,
            dd.tbl))
        script_lst.append(u"""
sample_a, sample_b, data_tups = core_stats.get_paired_data(dbe=mg.%(dbe)s, 
                cur=cur, tbl=u"%(tbl)s", tbl_filt=tbl_filt,
                fld_a=u"%(var_a)s", fld_b=u"%(var_b)s")""" % 
                {u"dbe": mg.DBE_KEY2KEY_AS_STR[dd.dbe], u"tbl": dd.tbl, 
                u"var_a": var_a, u"var_b": var_b})
        script_lst.append(u"dp = 3")
        script_lst.append(u"label_a = u\"%s\"" % label_a)
        script_lst.append(u"label_b = u\"%s\"" % label_b)
        script_lst.append(u"t, p, dic_a, dic_b = core_stats.wilcoxont(sample_a,"
            u" sample_b, label_a, label_b, headless=False)")
        if details:
            script_lst.append(
                u"details = core_stats.wilcoxont_details(sample_a, sample_b, "
                u"label_a, label_b, headless=False)")
        else:
            script_lst.append(u"details = {}")
        script_lst.append(u"""
wilcoxon_output = stats_output.wilcoxon_output(t, p, dic_a, dic_b,
            css_fil=u"%(css_fil)s", 
            css_idx=%(css_idx)s, dp=dp, details=details,
            page_break_after=False)""" % 
            {u"css_fil": lib.escape_pre_write(css_fil), u"css_idx": css_idx})
        script_lst.append(u"fil.write(wilcoxon_output)")
        return u"\n".join(script_lst)

    def on_btn_help(self, event):
        import webbrowser
        url = u"http://www.sofastatistics.com/wiki/doku.php?id=help:wilcoxon"
        webbrowser.open_new_tab(url)
        event.Skip()
