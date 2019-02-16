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
        eg1 = _('Answers the question, do 2 groups have a different average?')
        eg2 = _('For example, do PhD graduates earn the same on average as '
                    'Masters graduates?')
        eg3 = _('Or do parents of pre-schoolers get the same amount of '
                    'sleep on average as parents of teenagers?')
        return eg1, eg2, eg3
    
    def update_phrase(self):
        """
        Update phrase based on GroupBy, Group A, Group B, and Averaged by field.
        """
        try:
            (unused, unused, label_gp, unused, label_a,
             unused, label_b, unused, label_avg) = self.get_drop_vals()
            self.lbl_phrase.SetLabel(_("Does %(gp)s \"%(a)s\" have a different "
                "average %(avg)s from \"%(b)s\"?")
                % {'gp': label_gp, 'a': label_a, 'avg': label_avg, 'b': label_b})
        except Exception:
            self.lbl_phrase.SetLabel(u'')

    def get_script(self, css_idx, css_fpath, report_fpath, details):
        "Build script from inputs"
        dd = mg.DATADETS_OBJ
        script_lst = []
        try:
            (var_gp_numeric, var_gp, label_gp, val_a,
             label_a, val_b, label_b, var_avg, label_avg) = self.get_drop_vals()
        except Exception as e:
            wx.MessageBox(
                f'Unable to get script to make output. Orig error: {b.ue(e)}')
        script_lst.append('dp = 3')
        script_lst.append(
            lib.FiltLib.get_tbl_filt_clause(dd.dbe, dd.db, dd.tbl))
        val_str_quoted_a = val_a if var_gp_numeric else f'"{val_a}"'
        val_str_quoted_b = val_b if var_gp_numeric else f'"{val_b}"'
        dbe_str = mg.DBE_KEY2KEY_AS_STR[dd.dbe]
        str_get_sample = (f"""
sample_%s = core_stats.get_list(dbe=mg.{dbe_str}, cur=cur,
    tbl="{dd.tbl}", tbl_filt=tbl_filt, flds=flds,
    fld_measure="{lib.esc_str_input(var_avg)}",
    fld_filter="{lib.esc_str_input(var_gp)}", filter_val=%s)""")
        script_lst.append(str_get_sample % ('a', val_str_quoted_a))
        script_lst.append(str_get_sample % ('b', val_str_quoted_b))
        script_lst.append("""
if len(sample_a) < 2 or len(sample_b) < 2:
    raise my_exceptions.TooFewSamplesForAnalysis""")
        script_lst.append(f'label_gp = "{label_gp}"')
        script_lst.append(f'label_a = "{label_a}"')
        script_lst.append(f'label_b = "{label_b}"')
        script_lst.append(f'label_avg = "{label_avg}"')
        add2report = 'True' if mg.ADD2RPT else 'False'
        script_lst.append(f'add_to_report = {add2report}')
        script_lst.append(
            f'css_fpath = Path("{lib.escape_pre_write(str(css_fpath))}")')
        script_lst.append(
            f'report_fpath = Path("{lib.escape_pre_write(str(report_fpath))}")')
        script_lst.append('t, p, dic_a, dic_b, df = '
            'core_stats.ttest_ind(sample_a, sample_b, label_a, label_b)')
        script_lst.append('details = True' if details else 'details = {}')
        script_lst.append(f"""
ttest_indep_output = stats_output.ttest_indep_output(sample_a, sample_b, t, p,
    label_gp, dic_a, dic_b, df, label_avg,
    report_fpath, css_fpath=css_fpath, css_idx={css_idx},
    dp=dp, details=details, add_to_report=add_to_report,
    page_break_after=False)""")
        script_lst.append('fil.write(ttest_indep_output)')
        return '\n'.join(script_lst)

    def on_btn_help(self, event):
        import webbrowser
        url = 'http://www.sofastatistics.com/wiki/doku.php?id=help:indep_ttest'
        webbrowser.open_new_tab(url)
        event.Skip()
