from textwrap import dedent
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
            wx.MessageBox(
                f'Unable to get script to make output. Orig error: {b.ue(e)}')
        script_lst.append(lib.FiltLib.get_tbl_filt_clause(
            dd.dbe, dd.db, dd.tbl))
        script_lst.append(dedent(f"""
        sample_a, sample_b, data_tups = core_stats.get_paired_data(
            dbe=mg.{mg.DBE_KEY2KEY_AS_STR[dd.dbe]},
            cur=cur, tbl='{dd.tbl}', tbl_filt=tbl_filt,
            fld_a='{lib.esc_str_input(var_a)}',
            fld_b='{lib.esc_str_input(var_b)}')"""))
        script_lst.append('dp = 3')
        script_lst.append(f'label_a = "{label_a}"')
        script_lst.append(f'label_b = "{label_b}"')
        add_to_report = 'True' if mg.ADD2RPT else 'False'
        script_lst.append(f'add_to_report = {add_to_report}')
        script_lst.append(
            f'report_name = "{lib.escape_pre_write(report_name)}"')
        script_lst.append('t, p, dic_a, dic_b, df, diffs = '
            'core_stats.ttest_rel(sample_a, sample_b, label_a, label_b)')
        script_lst.append("details = True" if details else 'details = {}')
        script_lst.append(dedent(f"""
        ttest_paired_output = stats_output.ttest_paired_output(
            sample_a, sample_b, t, p,
            dic_a, dic_b, df, diffs, report_name,
            css_fil="{lib.escape_pre_write(css_fil)}",
            css_idx={css_idx}, label_avg='', dp=dp,
            details=details, add_to_report=add_to_report,
            page_break_after=False)"""))
        script_lst.append('fil.write(ttest_paired_output)')
        return '\n'.join(script_lst)

    def on_btn_help(self, event):
        import webbrowser
        url = 'http://www.sofastatistics.com/wiki/doku.php?id=help:paired_ttest'
        webbrowser.open_new_tab(url)
        event.Skip()
