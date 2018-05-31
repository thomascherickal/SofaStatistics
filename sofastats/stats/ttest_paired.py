import wx

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import lib
from sofastats.stats import paired2var


class DlgConfig(paired2var.DlgPaired2VarConfig):
    
    min_data_type = mg.VAR_TYPE_QUANT_KEY
    
    def get_examples(self):
        eg1 = _("Answers the question, are the elements of paired sets of "
                "data different from each other?")
        eg2 = _("For example, do people have a higher average weight after a "
                "diet compared with before?")
        eg3 = _("Or does average performance in IQ tests vary between "
                "morning and mid afternoon?")
        return eg1, eg2, eg3
    
    def get_script(self, css_idx, css_fil, report_name, details):
        "Build script from inputs"
        dd = mg.DATADETS_OBJ
        script_lst = []
        try:
            var_a, label_a, var_b, label_b = self.get_drop_vals()
        except Exception as e:
            wx.MessageBox(u"Unable to get script to make output. Orig error: %s" 
                % b.ue(e))
        script_lst.append(lib.FiltLib.get_tbl_filt_clause(dd.dbe, dd.db,
            dd.tbl))
        script_lst.append(u"""
sample_a, sample_b, data_tups = core_stats.get_paired_data(dbe=mg.%(dbe)s, 
    cur=cur, tbl=u"%(tbl)s", tbl_filt=tbl_filt, 
    fld_a=u"%(var_a)s", fld_b=u"%(var_b)s")""" % 
    {u"dbe": mg.DBE_KEY2KEY_AS_STR[dd.dbe], 
             u"tbl": dd.tbl, u"var_a": lib.esc_str_input(var_a), 
             u"var_b": lib.esc_str_input(var_b)})
        script_lst.append(u"dp = 3")
        script_lst.append(u"label_a = u\"%s\"" % label_a)
        script_lst.append(u"label_b = u\"%s\"" % label_b)
        script_lst.append(u"add_to_report = %s" % ("True" if mg.ADD2RPT
                          else "False"))
        script_lst.append(u"report_name = u\"%s\"" % 
                          lib.escape_pre_write(report_name))
        script_lst.append(u"t, p, dic_a, dic_b, df, diffs = "
            u"core_stats.ttest_rel(sample_a, sample_b, label_a, label_b)")
        script_lst.append(u"details = True" if details else u"details = {}")
        script_lst.append(u"""
ttest_paired_output = stats_output.ttest_paired_output(sample_a, sample_b, t, p,
    dic_a, dic_b, df, diffs, add_to_report, report_name,
    css_fil=u"%(css_fil)s", css_idx=%(css_idx)s, label_avg=u"", dp=dp,
    details=details, page_break_after=False)""" %
            {u"css_fil": lib.escape_pre_write(css_fil), u"css_idx": css_idx})        
        script_lst.append(u"fil.write(ttest_paired_output)")
        return u"\n".join(script_lst)

    def on_btn_help(self, event):
        import webbrowser
        url = u"http://www.sofastatistics.com/wiki/doku.php" + \
              u"?id=help:paired_ttest"
        webbrowser.open_new_tab(url)
        event.Skip()
        