import wx

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import lib
from sofastats.stats import paired2var
from pyatspi.interface import interface


class DlgConfig(paired2var.DlgPaired2VarConfig):
    
    min_data_type = mg.VAR_TYPE_ORD_KEY
    
    def get_examples(self):
        eg1 = _('Answers the question, are the elements of paired sets of '
                'data different from each other?')
        eg2 = _('For example, do tutors get better student ratings after a '
            'training session?')
        eg3 = _('Or have house values changed since the recession began?')
        return eg1, eg2, eg3

    def get_script(self, css_idx, css_fil, report_name, details):
        """
        Build script from inputs

        css_fil and report_name needed to comply with standard interface
        """
        dd = mg.DATADETS_OBJ
        script_lst = []
        try:
            var_a, label_a, var_b, label_b = self.get_drop_vals()
        except Exception as e:
            wx.MessageBox('Unable to get script to make output. '
                f'Orig error: {b.ue(e)}')
        script_lst.append(lib.FiltLib.get_tbl_filt_clause(
            dd.dbe, dd.db, dd.tbl))
        dbe = mg.DBE_KEY2KEY_AS_STR[dd.dbe]
        script_lst.append(f"""
sample_a, sample_b, data_tups = core_stats.get_paired_data(dbe=mg.{dbe},
                cur=cur, tbl="{dd.tbl}", tbl_filt=tbl_filt,
                fld_a="{var_a}", fld_b="{var_b}")""")
        script_lst.append('dp = 3')
        script_lst.append(f'label_a = "{label_a}"')
        script_lst.append(f'label_b = "{label_b}"')
        script_lst.append('t, p, dic_a, dic_b = core_stats.wilcoxont('
            'sample_a, sample_b, label_a, label_b, headless=False)')
        if details:
            script_lst.append(
                'details = core_stats.wilcoxont_details(sample_a, sample_b)')
        else:
            script_lst.append('details = {}')
        script_lst.append(f"""
wilcoxon_output = stats_output.wilcoxon_output(t, p, dic_a, dic_b,
            css_idx={css_idx}, dp=dp, details=details,
            page_break_after=False)""")
        script_lst.append('fil.write(wilcoxon_output)')
        return '\n'.join(script_lst)

    def on_btn_help(self, event):
        import webbrowser
        url = 'http://www.sofastatistics.com/wiki/doku.php?id=help:wilcoxon'
        webbrowser.open_new_tab(url)
        event.Skip()
