#! /usr/bin/env python
# -*- coding: utf-8 -*-

import wx

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import lib
from sofastats import indep2var


class DlgConfig(indep2var.DlgIndep2VarConfig):

    averaged = mg.CHART_AVERAGED_LBL
    range_gps = True   
    min_data_type = mg.VAR_TYPE_QUANT_KEY

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
        try:
            (unused, unused, label_gp, unused, 
             label_a, unused, 
             label_b, unused, 
             label_avg) = self.get_drop_vals()
            self.lbl_phrase.SetLabel(_("Does average %(avg)s vary for the "
                u"%(label_gp)s groups between \"%(a)s\" and \"%(b)s\"?") % 
                {"label_gp": label_gp, "avg": label_avg, "a": label_a, 
                "b": label_b})
        except Exception:
            self.lbl_phrase.SetLabel(u"")

    def add_other_var_opts(self, szr):
        self.lbl_algorithm = wx.StaticText(self.panel_vars, -1, 
            _("Algorithm: "))
        self.lbl_algorithm.SetFont(mg.LABEL_FONT)
        self.rad_precision = wx.RadioButton(self.panel_vars, -1, _("Precision"), 
            style=wx.RB_GROUP)
        self.rad_precision.SetFont(mg.GEN_FONT)
        self.rad_speed = wx.RadioButton(self.panel_vars, -1, _("Speed"))
        self.rad_speed.SetFont(mg.GEN_FONT)
        self.rad_speed.SetToolTipString(_("Precision is the best choice unless "
            "too slow"))
        self.rad_speed.SetValue(True)
        szr_algorithm = wx.BoxSizer(wx.HORIZONTAL)
        szr_algorithm.Add(self.lbl_algorithm, 0)
        szr_algorithm.Add(self.rad_precision, 0)
        szr_algorithm.Add(self.rad_speed, 0, wx.LEFT, 10)
        szr.Add(szr_algorithm, 0, wx.TOP, 5)
    
    def get_script(self, css_idx, css_fil, report_name, details):
        "Build script from inputs"
        dd = mg.DATADETS_OBJ
        try:
            (var_gp_numeric, var_gp, label_gp, val_a, 
             label_a, val_b, label_b, var_avg, label_avg) = self.get_drop_vals()
        except Exception, e:
            wx.MessageBox(u"Unable to get script to make output. Orig error: %s" 
                % b.ue(e))
        script_lst = [u"dp = %s" % mg.DEFAULT_STATS_DP]
        script_lst.append(lib.FiltLib.get_tbl_filt_clause(dd.dbe, dd.db,
            dd.tbl))
        lst_samples = []
        lst_labels = []
        # need sample for each of the values in range
        idx_val_a, idx_val_b = indep2var.get_range_idxs(self.gp_vals_sorted, 
            val_a, val_b)
        vals_in_range = self.gp_vals_sorted[idx_val_a: idx_val_b + 1]
        str_get_sample = (u"""
%%s = core_stats.get_list(dbe=mg.%(dbe)s, cur=cur, tbl=u"%(tbl)s", 
    tbl_filt=tbl_filt, flds=flds, fld_measure=u"%(var_avg)s", 
    fld_filter=u"%(var_gp)s", filter_val=%%s)""" % 
    {u"dbe": mg.DBE_KEY2KEY_AS_STR[dd.dbe], u"tbl": dd.tbl, 
        u"var_avg": lib.esc_str_input(var_avg), 
        u"var_gp": lib.esc_str_input(var_gp)})
        for i, val in enumerate(vals_in_range):
            sample_name = u"sample_%s" % i
            val_str_quoted = val if var_gp_numeric else u'u"""%s"""' % val
            script_lst.append(str_get_sample % (sample_name, val_str_quoted))
            lst_samples.append(sample_name)
            try:
                val_label = self.val_dics[var_gp][val]
            except KeyError:
                val_label = unicode(val).title()
            lst_labels.append(val_label)
        samples = u"[%s]" % u", ".join(lst_samples)
        script_lst.append(u"raw_labels = %s" % lst_labels)
        script_lst.append(u"raw_samples = %s" % samples)
        script_lst.append(u"raw_sample_dets = zip(raw_labels, raw_samples)")
        script_lst.append(u"sample_dets = [x for x in raw_sample_dets "
            u"if len(x[1]) > 0]")
        script_lst.append(u"labels = [x[0] for x in sample_dets]")
        script_lst.append(u"samples = [x[1] for x in sample_dets]")
        script_lst.append(u"""
if len(samples) < 2:
    raise my_exceptions.TooFewSamplesForAnalysis""")
        script_lst.append(u'label_gp = u"""%s"""' % label_gp)
        script_lst.append(u'label_a = u"""%s"""' % label_a)
        script_lst.append(u'label_b = u"""%s"""' % label_b)
        script_lst.append(u'label_avg = u"""%s"""' % label_avg)
        script_lst.append(u"add_to_report = %s" % ("True" if mg.ADD2RPT
            else "False"))
        script_lst.append(u"report_name = u\"%s\"" % 
            lib.escape_pre_write(report_name))
        high = self.rad_precision.GetValue()
        script_lst.append(u"""
(p, F, dics, sswn, dfwn, mean_squ_wn, 
 ssbn, dfbn, mean_squ_bn) = core_stats.anova(samples, labels, high=%s)""" % 
            high)
        script_lst.append(u"details = True" if details else u"details = {}")
        script_lst.append(u"""
anova_output = stats_output.anova_output(samples, F, p, dics, sswn, dfwn, 
    mean_squ_wn, ssbn, dfbn, mean_squ_bn, label_gp, label_a, label_b, 
    label_avg, add_to_report, report_name, css_fil=u"%(css_fil)s", 
    css_idx=%(css_idx)s, dp=dp, details=details,
    page_break_after=False)""" % {u"css_fil": lib.escape_pre_write(css_fil),
        u"css_idx": css_idx})
        script_lst.append(u"fil.write(anova_output)")
        return u"\n".join(script_lst)

    def on_btn_help(self, event):
        import webbrowser
        url = u"http://www.sofastatistics.com/wiki/doku.php?id=help:anova"
        webbrowser.open_new_tab(url)
        event.Skip()