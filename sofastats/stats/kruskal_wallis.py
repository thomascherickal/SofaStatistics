import wx

from sofastats import basic_lib as b
from sofastats import my_globals as mg
from sofastats import lib
from sofastats.stats import indep2var


class DlgConfig(indep2var.DlgIndep2VarConfig):

    averaged = mg.CHART_AVERAGED_LBL
    range_gps = True
    min_data_type = mg.VAR_TYPE_ORD_KEY

    def get_examples(self):
        eg1 = _("Answers the question, do 3 or more groups have a "
            "different average?")
        eg2 = _("For example, is average income the same for people from "
            "three different cities?")
        eg3 = _("Or is the average amount spent annually on pets different "
            "between dog, cat, and pony owners?")
        return eg1, eg2, eg3
    
    def update_phrase(self):
        """
        Update phrase based on GroupBy, Group A, Group B, and Averaged by field.
        """
        try:
            (unused, unused, label_gp, unused, label_a, 
             unused, label_b, unused, label_avg) = self.get_drop_vals()
            self.lbl_phrase.SetLabel(_("Does average %(avg)s vary for the "
                u"%(label_gp)s groups between \"%(a)s\" and \"%(b)s\"?") %
                {"label_gp": label_gp, "avg": label_avg, "a": label_a, 
                "b": label_b})
        except Exception:
            self.lbl_phrase.SetLabel(u"")

    def get_script(self, css_idx, css_fil, report_name, details):
        "Build script from inputs"
        dd = mg.DATADETS_OBJ
        try:
            (var_gp_numeric, var_gp, label_gp, val_a, 
             label_a, val_b, label_b, var_avg, label_avg) = self.get_drop_vals()
        except Exception as e:
            wx.MessageBox("Unable to get script to make output. "
                f"Orig error: {b.ue(e)}")
        script_lst = ["dp = 3"]
        script_lst.append(lib.FiltLib.get_tbl_filt_clause(dd.dbe, dd.db,
            dd.tbl))
        lst_samples = []
        lst_labels = []
        # need sample for each of the values in range
        idx_val_a, idx_val_b = indep2var.get_range_idxs(
            self.gp_vals_sorted, val_a, val_b)
        vals_in_range = self.gp_vals_sorted[idx_val_a: idx_val_b + 1]
        str_get_sample = ("%s = core_stats.get_list("
            + f"dbe=mg.{mg.DBE_KEY2KEY_AS_STR[dd.dbe]}, "
            + f"cur=cur, tbl=u\"{dd.tbl}\","
            + "\n    tbl_filt=tbl_filt, "
            + "flds=flds, "
            + f"fld_measure=u\"{lib.esc_str_input(var_avg)}\", "
            + f"fld_filter=\"{lib.esc_str_input(var_gp)}\", "
            + "filter_val=%s)")
        for i, val in enumerate(vals_in_range):
            sample_name = f"sample_{i}"
            val_str_quoted = val if var_gp_numeric else f"\"{val}\""
            script_lst.append(str_get_sample % (sample_name, val_str_quoted))
            lst_samples.append(sample_name)
            try:
                val_label = self.val_dics[var_gp][val]
            except KeyError:
                val_label = str(val).title()
            lst_labels.append(val_label)
        samples = "[%s]" % ", ".join(lst_samples)
        script_lst.append(f"raw_labels = {lst_labels}")
        script_lst.append(f"raw_samples = {samples}")
        script_lst.append("raw_sample_dets = zip(raw_labels, raw_samples)")
        script_lst.append("sample_dets = [x for x in raw_sample_dets "
                          "if len(x[1]) > 0]")
        script_lst.append("labels = [x[0] for x in sample_dets]")
        script_lst.append("samples = [x[1] for x in sample_dets]")
        script_lst.append("""
if len(samples) < 2:
    raise my_exceptions.TooFewSamplesForAnalysis""")
        script_lst.append(f"label_gp = u\"{label_gp}\"")
        script_lst.append(f"label_a = u\"{label_a}\"")
        script_lst.append(f"label_b = u\"{label_b}\"")
        script_lst.append(f"label_avg = u\"{label_avg}\"")
        script_lst.append("indep = True")
        script_lst.append("h, p, dics, df = "
            + "core_stats.kruskalwallish(samples, labels)")
        script_lst.append("details = True" if details else "details = {}")
        script_lst.append("""
kruskal_wallis_output = stats_output.kruskal_wallis_output(h, p, label_gp, 
    label_a, label_b, dics, df, label_avg, 
    css_idx=%(css_idx)s, dp=dp, details=details, page_break_after=False)"""
        % {"css_fil": lib.escape_pre_write(css_fil), "css_idx": css_idx})
        script_lst.append("fil.write(kruskal_wallis_output)")
        return "\n".join(script_lst)

    def on_btn_help(self, event):
        import webbrowser
        url = u"http://www.sofastatistics.com/wiki/doku.php" + \
              u"?id=help:kruskal"
        webbrowser.open_new_tab(url)
        event.Skip()