import wx

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import lib
from sofastats.stats import indep2var


class DlgConfig(indep2var.DlgIndep2VarConfig):

    averaged = mg.CHART_AVERAGED_LBL
    range_gps = True   
    min_data_type = mg.VAR_TYPE_QUANT_KEY

    def get_examples(self):
        eg1 = _('Answers the question, do 3 or more groups have a '
            'different average?')
        eg2 = _('For example, is average IQ the same for students from '
            'three different universities?')
        eg3 = _('Or is the average height different between '
            'British, Australian, Canadian, and New Zealand adults?')
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
                "%(label_gp)s groups between \"%(a)s\" and \"%(b)s\"?")
                % {'label_gp': label_gp, 'avg': label_avg,
                   'a': label_a, 'b': label_b})
        except Exception:
            self.lbl_phrase.SetLabel('')

    def add_other_var_opts(self, szr):
        self.lbl_algorithm = wx.StaticText(
            self.panel_vars, -1, _('Algorithm: '))
        self.lbl_algorithm.SetFont(mg.LABEL_FONT)
        self.rad_precision = wx.RadioButton(
            self.panel_vars, -1, _('Precision'), style=wx.RB_GROUP)
        self.rad_precision.SetFont(mg.GEN_FONT)
        self.rad_speed = wx.RadioButton(self.panel_vars, -1, _('Speed'))
        self.rad_speed.SetFont(mg.GEN_FONT)
        self.rad_speed.SetToolTip(
            _('Precision is the best choice unless too slow'))
        self.rad_speed.SetValue(True)
        szr_algorithm = wx.BoxSizer(wx.HORIZONTAL)
        szr_algorithm.Add(self.lbl_algorithm, 0)
        szr_algorithm.Add(self.rad_precision, 0)
        szr_algorithm.Add(self.rad_speed, 0, wx.LEFT, 10)
        szr.Add(szr_algorithm, 0, wx.TOP, 5)

    def get_script(self, css_idx, css_fpath, report_fpath, details):
        "Build script from inputs"
        dd = mg.DATADETS_OBJ
        try:
            (var_gp_numeric, var_gp, label_gp, val_a, 
             label_a, val_b, label_b, var_avg, label_avg) = self.get_drop_vals()
        except Exception as e:
            wx.MessageBox(
                f'Unable to get script to make output. Orig error: {b.ue(e)}')
        script_lst = [f'dp = {mg.DEFAULT_STATS_DP}']
        script_lst.append(
            lib.FiltLib.get_tbl_filt_clause(dd.dbe, dd.db, dd.tbl))
        lst_samples = []
        lst_labels = []
        ## need sample for each of the values in range
        idx_val_a, idx_val_b = indep2var.get_range_idxs(
            self.gp_vals_sorted, val_a, val_b)
        vals_in_range = self.gp_vals_sorted[idx_val_a: idx_val_b + 1]
        dbe = mg.DBE_KEY2KEY_AS_STR[dd.dbe]
        var_avg_str = lib.esc_str_input(var_avg)
        var_gp_str = lib.esc_str_input(var_gp)
        str_get_sample = (f"""
%s = core_stats.get_list(dbe=mg.{dbe}, cur=cur, tbl="{dd.tbl}",
    tbl_filt=tbl_filt, flds=flds, fld_measure="{var_avg_str}",
    fld_filter="{var_gp_str}", filter_val=%s)""")
        for i, val in enumerate(vals_in_range):
            sample_name = f'sample_{i}'
            val_str_quoted = val if var_gp_numeric else f'"""{val}"""'
            script_lst.append(str_get_sample % (sample_name, val_str_quoted))
            lst_samples.append(sample_name)
            try:
                val_label = self.val_dics[var_gp][val]
            except KeyError:
                val_label = str(val).title()
            lst_labels.append(val_label)
        lst_samples_str = ', '.join(lst_samples)
        samples = f'[{lst_samples_str}]'
        script_lst.append(f'raw_labels = {lst_labels}')
        script_lst.append(f'raw_samples = {samples}')
        script_lst.append('raw_sample_dets = zip(raw_labels, raw_samples)')
        script_lst.append('sample_dets = [x for x in raw_sample_dets '
            'if len(x[1]) > 0]')
        script_lst.append('labels = [x[0] for x in sample_dets]')
        script_lst.append('samples = [x[1] for x in sample_dets]')
        script_lst.append("""
if len(samples) < 2:
    raise my_exceptions.TooFewSamplesForAnalysis""")
        script_lst.append(f'label_gp = """{label_gp}"""')
        script_lst.append(f'label_a = """{label_a}"""')
        script_lst.append(f'label_b = """{label_b}"""')
        script_lst.append(f'label_avg = """{label_avg}"""')
        add2report = 'True' if mg.ADD2RPT else 'False'
        script_lst.append(f'add_to_report = {add2report}')
        script_lst.append(f'css_fpath = Path("{lib.escape_pre_write(css_fpath)}")')
        script_lst.append(f'report_fpath = Path("{lib.escape_pre_write(report_fpath)}")')
        high = self.rad_precision.GetValue()
        script_lst.append(f"""
(p, F, dics, sswn, dfwn, mean_squ_wn, 
 ssbn, dfbn, mean_squ_bn) = core_stats.anova(samples, labels, high={high})""")
        script_lst.append('details = True' if details else 'details = {}')
        script_lst.append(f"""
anova_output = stats_output.anova_output(samples, F, p, dics, sswn, dfwn,
    mean_squ_wn, ssbn, dfbn, mean_squ_bn, label_gp, label_a, label_b,
    label_avg,
    report_fpath, css_fpath=css_fpath,
    css_idx={css_idx}, dp=dp, details=details,
    add_to_report=add_to_report, page_break_after=False)""")
        script_lst.append('fil.write(anova_output)')
        return '\n'.join(script_lst)

    def on_btn_help(self, event):
        import webbrowser
        url = 'http://www.sofastatistics.com/wiki/doku.php?id=help:anova'
        webbrowser.open_new_tab(url)
        event.Skip()
