import wx

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import lib
from sofastats.stats import indep2var


class DlgConfig(indep2var.DlgIndep2VarConfig):

    averaged = _('Ranked')
    range_gps = False
    min_data_type = mg.VAR_TYPE_ORD_KEY

    def get_examples(self):
        eg1 = _('Answers the question, do 2 groups have different results '
            '(higher or lower ranks)?')
        eg2 = _('For example, do male or female tutors get different rating '
            'scores from students?')
        eg3 = _('Or do IT graduates have a different income in their first '
            'year in the workforce compared with law graduates?')
        return eg1, eg2, eg3
    
    def update_phrase(self):
        """
        Update phrase based on GroupBy, Group A, Group B, and Ranked by field.
        """
        try:
            (unused, unused, label_gp, unused, label_a, 
             unused, label_b, unused, label_avg) = self.get_drop_vals()
            self.lbl_phrase.SetLabel(_(
                "Does %(gp)s \"%(a)s\" have a different %(avg)s from \"%(b)s\"?"
                ) % {'gp': label_gp, 'a': label_a,
                'avg': label_avg, 'b': label_b})
        except Exception:
            self.lbl_phrase.SetLabel('')

    def get_script(self, css_idx, css_fil, report_name, details):
        "Build script from inputs"
        dd = mg.DATADETS_OBJ
        try:
            (var_gp_numeric, var_gp, label_gp, val_a, label_a, 
             val_b, label_b, var_ranked, label_ranked) = self.get_drop_vals()
        except Exception as e:
            wx.MessageBox(
                f'Unable to get script to make output. Orig error: {b.ue(e)}')
        script_lst = ['dp = 3', ]
        script_lst.append(
            lib.FiltLib.get_tbl_filt_clause(dd.dbe, dd.db, dd.tbl))
        dbe_str = mg.DBE_KEY2KEY_AS_STR[dd.dbe]
        str_get_sample = (f"""\
sample_%s = core_stats.get_list(dbe=mg.{dbe_str}, cur=cur,
        tbl="{dd.tbl}", tbl_filt=tbl_filt, flds=flds,
        fld_measure="{lib.esc_str_input(var_ranked)}",
        fld_filter="{lib.esc_str_input(var_gp)}",
        filter_val=%s)""")
        val_str_quoted_a = val_a if var_gp_numeric else f'"{val_a}"'
        val_str_quoted_b = val_b if var_gp_numeric else f'"{val_b}"'
        script_lst.append(str_get_sample % ('a', val_str_quoted_a))
        script_lst.append(str_get_sample % ('b', val_str_quoted_b))
        script_lst.append("""
if len(sample_a) < 2 or len(sample_b) < 2:
    raise my_exceptions.TooFewSamplesForAnalysis""")
        script_lst.append(f'label_gp = "{label_gp}"')
        script_lst.append(f'label_a = "{label_a}"')
        script_lst.append(f'label_b = "{label_b}"')
        script_lst.append(f'label_ranked = "{label_ranked}"')
        script_lst.append('u, p, dic_a, dic_b, z = core_stats.mannwhitneyu('
            'sample_a, sample_b, label_a, label_b, headless=False)')
        if details:
            script_lst.append(
                'details = core_stats.mannwhitneyu_details(sample_a, sample_b,'
                ' label_a, label_b, headless=False)')
        else:
            script_lst.append('details = {}')
        script_lst.append(f"""
mann_whitney_output = stats_output.mann_whitney_output(u, p, label_gp, dic_a, 
    dic_b, z, label_ranked, 
    css_idx={css_idx}, dp=dp, details=details, page_break_after=False)""")
        script_lst.append('fil.write(mann_whitney_output)')
        return '\n'.join(script_lst)

    def on_btn_help(self, event):
        import webbrowser
        url = (
            'http://www.sofastatistics.com/wiki/doku.php?id=help:mann_whitney')
        webbrowser.open_new_tab(url)
        event.Skip()
