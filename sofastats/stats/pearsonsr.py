import wx

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import lib
from sofastats.stats import paired2var


class DlgConfig(paired2var.DlgPaired2VarConfig):

    min_data_type = mg.VAR_TYPE_QUANT_KEY

    def get_examples(self):
        eg1 = _('Answers the question, is there a linear relationship '
                'between two variables i.e. do they both change together?')
        eg2 = _('For example, does IQ correlate with exam scores?')
        eg3 = _('Or does a brief measure of addiction correlate with a much '
                'longer measure?')
        return eg1, eg2, eg3

    def update_phrase(self):
        """
        Update phrase based on Group A and Group B.
        """
        try:
            unused, label_a, unused, label_b = self.get_drop_vals()
            self.lbl_phrase.SetLabel(_("Are \"%(a)s\" and \"%(b)s\" correlated"
                ' - do they change together in a linear fashion?')
                % {'a': label_a, 'b': label_b})
        except Exception:
            self.lbl_phrase.SetLabel('')

    def get_script(self, css_idx, css_fpath, report_fpath, details):
        "Build script from inputs"
        dd = mg.DATADETS_OBJ
        script_lst = []
        script_lst.append(lib.FiltLib.get_tbl_filt_clause(
            dd.dbe, dd.db, dd.tbl))
        try:
            var_a, label_a, var_b, label_b = self.get_drop_vals()
        except Exception as e:
            wx.MessageBox(
                f'Unable to get script to make output. Orig error: {b.ue(e)}')
        dbe_str = mg.DBE_KEY2KEY_AS_STR[dd.dbe]
        script_lst.append(f"""
sample_a, sample_b, data_tups = core_stats.get_paired_data(dbe=mg.{dbe_str},
    cur=cur, tbl="{dd.tbl}", tbl_filt=tbl_filt, fld_a="{var_a}",
    fld_b="{var_b}")""")
        script_lst.append(
            'add_to_report = %s' % ('True' if mg.ADD2RPT else 'False'))
        script_lst.append(f'css_fpath = Path("{lib.escape_pre_write(str(css_fpath))}")')
        script_lst.append(f'report_fpath = Path("{lib.escape_pre_write(str(report_fpath))}")')
        script_lst.append('dp = 3')
        script_lst.append(f'label_a = "{label_a}"')
        script_lst.append(f'label_b = "{label_b}"')
        script_lst.append('r, p, df = core_stats.pearsonr(sample_a, sample_b)')
        script_lst.append('details = True' if details else 'details = {}')
        script_lst.append(f"""
pearsonsr_output = stats_output.pearsonsr_output(sample_a, sample_b, r, p, df,
    label_a, label_b,
    report_fpath, css_fpath=css_fpath, css_idx={css_idx},
    dp=dp, details=details,
    add_to_report=add_to_report, page_break_after=False)""")
        script_lst.append('fil.write(pearsonsr_output)')
        return '\n'.join(script_lst)

    def on_btn_help(self, event):
        import webbrowser
        url = 'http://www.sofastatistics.com/wiki/doku.php?id=help:pearsonsr'
        webbrowser.open_new_tab(url)
        event.Skip()
