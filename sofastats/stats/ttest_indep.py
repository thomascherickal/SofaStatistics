import wx

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import lib
from sofastats.stats import indep2var


class DlgConfig(indep2var.DlgIndep2VarConfig):

    averaged = mg.CHART_AVERAGED_LBL
    range_gps = False
    min_data_type = mg.VAR_TYPE_QUANT_KEY

    def get_examples(self):
        eg1 = _("Answers the question, do 2 groups have a different average?")
        eg2 = _("For example, do PhD graduates earn the same on average as "
                    "Masters graduates?")
        eg3 = _("Or do parents of pre-schoolers get the same amount of "
                    "sleep on average as parents of teenagers?")
        return eg1, eg2, eg3
    
    def update_phrase(self):
        """
        Update phrase based on GroupBy, Group A, Group B, and Averaged by field.
        """
        try:
            (unused, unused, label_gp, unused, label_a, 
             unused, label_b, unused, label_avg) = self.get_drop_vals()
            self.lbl_phrase.SetLabel(_("Does %(gp)s \"%(a)s\" have a different "
                "average %(avg)s from \"%(b)s\"?") % {"gp": label_gp, 
                "a": label_a, "avg": label_avg, "b": label_b})
        except Exception:
            self.lbl_phrase.SetLabel(u"")

    def get_script(self, css_idx, css_fil, report_name, details):
        "Build script from inputs"
        dd = mg.DATADETS_OBJ
        script_lst = []
        try:
            (var_gp_numeric, var_gp, label_gp, val_a, 
             label_a, val_b, label_b, var_avg, label_avg) = self.get_drop_vals()
        except Exception as e:
            wx.MessageBox(u"Unable to get script to make output. Orig error: %s" 
                % b.ue(e))
        script_lst.append(u"dp = 3")
        script_lst.append(lib.FiltLib.get_tbl_filt_clause(dd.dbe, dd.db,
            dd.tbl))
        val_str_quoted_a = val_a if var_gp_numeric else u"u\"%s\"" % val_a
        val_str_quoted_b = val_b if var_gp_numeric else u"u\"%s\"" % val_b
        str_get_sample = (u"""
sample_%%s = core_stats.get_list(dbe=mg.%(dbe)s, cur=cur, 
    tbl=u"%(tbl)s", tbl_filt=tbl_filt, flds=flds, 
    fld_measure=u"%(var_avg)s", 
    fld_filter=u"%(var_gp)s", filter_val=%%s)""" % 
    {u"dbe": mg.DBE_KEY2KEY_AS_STR[dd.dbe], u"tbl": dd.tbl, 
    u"var_avg": lib.esc_str_input(var_avg), 
    u"var_gp": lib.esc_str_input(var_gp)})
        script_lst.append(str_get_sample % (u"a", val_str_quoted_a))
        script_lst.append(str_get_sample % (u"b", val_str_quoted_b))
        script_lst.append(u"""
if len(sample_a) < 2 or len(sample_b) < 2:
    raise my_exceptions.TooFewSamplesForAnalysis""")
        script_lst.append(u"label_gp = u\"%s\"" % label_gp)
        script_lst.append(u"label_a = u\"%s\"" % label_a)
        script_lst.append(u"label_b = u\"%s\"" % label_b)
        script_lst.append(u"label_avg = u\"%s\"" % label_avg)
        script_lst.append(u"add_to_report = %s" % ("True" if mg.ADD2RPT
            else "False"))
        script_lst.append(u"report_name = u\"%s\"" % 
            lib.escape_pre_write(report_name))
        script_lst.append(u"t, p, dic_a, dic_b, df = "
            u"core_stats.ttest_ind(sample_a, sample_b, label_a, label_b)")
        script_lst.append(u"details = True" if details else u"details = {}")
        script_lst.append(u"""
ttest_indep_output = stats_output.ttest_indep_output(sample_a, sample_b, t, p,
    label_gp, dic_a, dic_b, df, label_avg, add_to_report, report_name,
    css_fil=u"%(css_fil)s", css_idx=%(css_idx)s, dp=dp,
    details=details, page_break_after=False)""" %
            {u"css_fil": lib.escape_pre_write(css_fil), u"css_idx": css_idx})
        script_lst.append(u"fil.write(ttest_indep_output)")
        return u"\n".join(script_lst)

    def on_btn_help(self, event):
        import webbrowser
        url = u"http://www.sofastatistics.com/wiki/doku.php?id=help:indep_ttest"
        webbrowser.open_new_tab(url)
        event.Skip()