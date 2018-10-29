from pprint import pformat as pf
import wx

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import lib
from sofastats.stats import paired2var


class DlgConfig(paired2var.DlgPaired2VarConfig):
    
    min_data_type = mg.VAR_TYPE_CAT_KEY
    
    def get_examples(self):
        eg1 = _("Answers the question, is there a relationship "
            "between two variables.")
        eg2 = _("For example, is there a relationship between ethnic "
            "group and gender?")
        eg3 = _("Or between gender and political preference?")
        return eg1, eg2, eg3

    def update_phrase(self):
        """
        Update phrase based on Group A and Group B.
        """
        try:
            unused, label_a, unused, label_b = self.get_drop_vals()
            self.lbl_phrase.SetLabel(_(
                "Is there a relationship between \"%(a)s\" and \"%(b)s\"")
                % {"a": label_a, "b": label_b})
        except Exception:
            self.lbl_phrase.SetLabel("")

    def get_script(self, css_idx, css_fil, report_name, details):
        "Build script from inputs"
        dd = mg.DATADETS_OBJ
        script_lst = []
        try:
            var_a, label_a, var_b, label_b = self.get_drop_vals()
        except Exception as e:
            wx.MessageBox(
                f'Unable to get script to make output. Orig error: {b.ue(e)}') 
        script_lst.append("add_to_report = %s" % ("True" if mg.ADD2RPT
                          else "False"))
        script_lst.append("report_name = \"%s\"" % 
                          lib.escape_pre_write(report_name))
        script_lst.append("dp = 3")
        script_lst.append(f'var_label_a = "{label_a}"')
        script_lst.append(f'var_label_b = "{label_b}"')
        unused, tbl_filt = lib.FiltLib.get_tbl_filt(dd.dbe, dd.db, dd.tbl)
        where_tbl_filt, and_tbl_filt = lib.FiltLib.get_tbl_filts(tbl_filt)
        dbe = mg.DBE_KEY2KEY_AS_STR[dd.dbe]
        fld_a = lib.esc_str_input(var_a)
        fld_b = lib.esc_str_input(var_b)
        script_lst.append(f'''
(chisq, p, vals_a, vals_b, lst_obs, lst_exp,
 min_count, perc_cells_lt_5, df) = core_stats.pearsons_chisquare(dbe=mg.{dbe},
    cur=cur, tbl="{dd.tbl}",
    flds=flds, fld_a="{fld_a}", fld_b="{fld_b}",
    tbl_filt=""" {tbl_filt} """,
    where_tbl_filt=""" {where_tbl_filt} """,
    and_tbl_filt=""" {and_tbl_filt} """)''')
        val_dic_a = self.val_dics.get(var_a, {})
        val_dic_b = self.val_dics.get(var_b, {})
        script_lst.append(f'val_dic_a = {pf(val_dic_a)}')
        script_lst.append(f'val_dic_b = {pf(val_dic_b)}')
        script_lst.append(
            'val_labels_a = [val_dic_a.get(x, str(x)) for x in vals_a]')
        script_lst.append(
            'val_labels_b = [val_dic_b.get(x, str(x)) for x in vals_b]')
        if details:
            script_lst.append(
                "details = core_stats.chisquare_details(vals_a, vals_b,"
                "\n    lst_obs, df)")
        else:
            script_lst.append("details = {}")
        css_fil = lib.escape_pre_write(css_fil)
        script_lst.append(f"""
chisquare_output = stats_output.chisquare_output(chisq, p, var_label_a,
    var_label_b, add_to_report, report_name, val_labels_a, val_labels_b,
    lst_obs, lst_exp, min_count, perc_cells_lt_5, df,
    css_fil="{css_fil}", css_idx={css_idx}, dp=dp,
    details=details, page_break_after=False)""")
        script_lst.append('fil.write(chisquare_output)')
        return "\n".join(script_lst)

    def on_btn_help(self, event):
        import webbrowser
        url = 'http://www.sofastatistics.com/wiki/doku.php?id=help:chisquare'
        webbrowser.open_new_tab(url)
        event.Skip()
