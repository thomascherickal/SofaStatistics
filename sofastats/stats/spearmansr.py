import wx

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import lib
from sofastats.stats import paired2var

"""
Add Kendall rank correlation coefficient?
"""

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
    
    def get_script(self, css_idx, css_fil, report_name, details):
        "Build script from inputs"
        dd = mg.DATADETS_OBJ
        script_lst = []
        try:
            var_x, label_x, var_y, label_y = self.get_drop_vals()
        except Exception as e:
            wx.MessageBox(u"Unable to get script to make output. Orig error: %s" 
                % b.ue(e))
        script_lst.append(lib.FiltLib.get_tbl_filt_clause(dd.dbe, dd.db,
            dd.tbl))
        script_lst.append(u"""
sample_x, sample_y, data_tups = core_stats.get_paired_data(
    dbe=mg.%(dbe)s, cur=cur, tbl=u"%(tbl)s",
    tbl_filt=tbl_filt, fld_a=u"%(var_x)s", fld_b=u"%(var_y)s")""" %
            {u"dbe": mg.DBE_KEY2KEY_AS_STR[dd.dbe], u"tbl": dd.tbl, 
            u"var_x": var_x, u"var_y": var_y})
        script_lst.append(u"add_to_report = %s" % ("True" if mg.ADD2RPT
                          else "False"))
        script_lst.append(u"report_name = u\"%s\"" % 
                          lib.escape_pre_write(report_name))
        script_lst.append(u"dp = 3")
        script_lst.append(u"label_x = u\"%s\"" % label_x)
        script_lst.append(u"label_y = u\"%s\"" % label_y)
        script_lst.append(u"r, p, df = core_stats.spearmanr(sample_x, "
                          u"sample_y, headless=False)")
        if details:
            script_lst.append(
                u"details = core_stats.spearmanr_details(sample_x, sample_y,"
                u" label_x, label_y, headless=False)")
        else:
            script_lst.append(u"details = {}")
        script_lst.append(u"""
spearmansr_output = stats_output.spearmansr_output(sample_x, sample_y, r, p, df,
    label_x, label_y, add_to_report, report_name,
    css_fil=u"%(css_fil)s", css_idx=%(css_idx)s, dp=dp,
    details=details, page_break_after=False)""" %
            {u"css_fil": lib.escape_pre_write(css_fil), u"css_idx": css_idx})
        script_lst.append(u"fil.write(spearmansr_output)")
        return u"\n".join(script_lst)
    
    def on_btn_help(self, event):
        import webbrowser
        url = u"http://www.sofastatistics.com/wiki/doku.php?id=help:spearmansr"
        webbrowser.open_new_tab(url)
        event.Skip()