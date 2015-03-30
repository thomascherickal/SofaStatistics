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
        eg1 = _("Answers the question, do two variables change together. E.g. "
                "if one increases, the other also increases "
                "(or stays the same).")
        eg2 = _("For example, does IQ correlate with exam scores?")
        eg3 = _("Or does a brief measure of addiction correlate with a much "
            "longer measure?")
        return eg1, eg2, eg3

    def update_phrase(self):
        """
        Update phrase based on Group A and Group B.
        """
        try:
            unused, label_a, unused, label_b = self.get_drop_vals()
            self.lbl_phrase.SetLabel(_(u"Are \"%(a)s\" and \"%(b)s\" correlated"
                                       u" - do they change together in a linear"
                                       u" fashion?") % {"a": label_a, 
                                                        "b": label_b})
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
                % b.ue(e))
        script_lst.append(lib.get_tbl_filt_clause(dd.dbe, dd.db, dd.tbl))
        script_lst.append(u"""
sample_a, sample_b, data_tups = core_stats.get_paired_data(
    dbe=mg.%(dbe)s, cur=cur, tbl=u"%(tbl)s",
    tbl_filt=tbl_filt, fld_a=u"%(var_a)s", fld_b=u"%(var_b)s")""" %
            {u"dbe": mg.DBE_KEY2KEY_AS_STR[dd.dbe], u"tbl": dd.tbl, 
            u"var_a": var_a, u"var_b": var_b})
        script_lst.append(u"add_to_report = %s" % ("True" if mg.ADD2RPT
                          else "False"))
        script_lst.append(u"report_name = u\"%s\"" % 
                          lib.escape_pre_write(report_name))
        script_lst.append(u"dp = 3")
        script_lst.append(u"label_a = u\"%s\"" % label_a)
        script_lst.append(u"label_b = u\"%s\"" % label_b)
        script_lst.append(u"r, p, df = core_stats.spearmanr(sample_a, "
                          u"sample_b, headless=False)")
        script_lst.append(u"""
spearmansr_output = stats_output.spearmansr_output(sample_a, sample_b, r, p, df,
    label_a, label_b, add_to_report, report_name,
    css_fil=u"%(css_fil)s", css_idx=%(css_idx)s, dp=dp,
    level=mg.OUTPUT_RESULTS_ONLY, page_break_after=False)""" %
            {u"css_fil": lib.escape_pre_write(css_fil), u"css_idx": css_idx})
        script_lst.append(u"fil.write(spearmansr_output)")
        return u"\n".join(script_lst)
    
    def on_btn_help(self, event):
        import webbrowser
        url = u"http://www.sofastatistics.com/wiki/doku.php?id=help:spearmansr"
        webbrowser.open_new_tab(url)
        event.Skip()