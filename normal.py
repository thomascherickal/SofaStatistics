#! /usr/bin/env python
# -*- coding: utf-8 -*-

import wx
import wxmpl
import pylab # must import after wxmpl so matplotlib.use() is always first

import my_globals as mg
import lib
import my_exceptions
import charting_pylab as charts
import config_dlg
import core_stats
import getdata
import full_html
import os
import projects

dd = getdata.get_dd()


class NormalityDlg(wx.Dialog, config_dlg.ConfigDlg):
    
    def __init__(self, parent, var_labels, var_notes, var_types, val_dics):
        wx.Dialog.__init__(self, parent=parent, title=_("Normal Data?"),
                           size=(1024,600), 
                           style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|\
                           wx.RESIZE_BORDER|wx.SYSTEM_MENU|wx.CAPTION|\
                           wx.CLIP_CHILDREN)
        # the following properties all required to utilise get_szr_data
        self.var_labels = var_labels
        self.var_notes = var_notes
        self.var_types = var_types
        self.val_dics = val_dics
        self.paired = False
        CHECK_LABEL = _("Check")
        self.varbox_label_unpaired = _("Variable to Check")
        self.varbox_label_paired = _("Paired Variables to Check")
        self.var_label_unpaired = _("Variable:")
        self.var_label_paired = _("Variables:")
        self.desc_label_unpaired = _("Select the variable you are interested "
            "in. Is its distribution close enough to the normal curve for use "
            "with tests requiring that?\n\nLook for gross outliers, extreme "
            "skewing, and clustering into groups.")
        self.desc_label_paired = _("Select the paired variables you are "
            "interested in. Looking at the differences, is the distribution "
            "close enough\nto the normal curve for use with tests requiring "
            "that?\n\nNote: if comparing samples, each sample must be normal "
            "enough. Filter for each sample by right clicking on the table "
            "selector.") # OS X can display oddly dep on breaks
        paired_choices = [_("Single"), _("Paired")]
        self.img_blank_hist = wx.Image(os.path.join(mg.SCRIPT_PATH, u"images", 
                                         u"blankhisto.xpm"), wx.BITMAP_TYPE_XPM)
        self.blank_hist_txt_unpaired = \
                lib.get_text_to_draw(_("Select variable and click %s to see "
                                       "graph") % CHECK_LABEL, 145)
        self.blank_hist_txt_paired = \
                lib.get_text_to_draw(_("Select variables and click %s to see "
                                       "graph") % CHECK_LABEL, 145)
        self.panel = wx.Panel(self)
        # szrs
        szr_main = wx.BoxSizer(wx.VERTICAL)
        bxDesc = wx.StaticBox(self.panel, -1, _("Purpose"))
        self.szr_desc = wx.StaticBoxSizer(bxDesc, wx.VERTICAL)
        self.szr_data = self.get_szr_data(self.panel) # mixin
        szr_paired = wx.BoxSizer(wx.HORIZONTAL)
        self.bx_vars = wx.StaticBox(self.panel, -1, self.varbox_label_unpaired)
        szr_vars = wx.StaticBoxSizer(self.bx_vars, wx.HORIZONTAL)
        szr_vars_right = wx.BoxSizer(wx.VERTICAL)
        #self.szr_level = self.get_szr_level(self.panel) # mixin
        self.szr_examine = wx.BoxSizer(wx.HORIZONTAL)
        szr_shape = wx.BoxSizer(wx.VERTICAL)
        szr_normality_test = wx.BoxSizer(wx.HORIZONTAL)
        # assembly
        self.lbl_desc = wx.StaticText(self.panel, -1, self.desc_label_unpaired)
        self.szr_desc.Add(self.lbl_desc, 0, wx.ALL, 10)
        self.lbl_vars = wx.StaticText(self.panel, -1, self.var_label_unpaired)
        self.lbl_vars.SetFont(self.LABEL_FONT)
        self.rad_paired = wx.RadioBox(self.panel, -1, 
                                      _("Single or Paired variables"), 
                                      choices=paired_choices, size=(-1,45),
                                      style=wx.RA_SPECIFY_COLS)
        self.rad_paired.SetStringSelection(_("Single"))
        self.rad_paired.Bind(wx.EVT_RADIOBOX, self.on_rad_paired)
        szr_paired.Add(self.rad_paired, 0)
        self.drop_var_a = wx.Choice(self.panel, -1, size=(300, -1))
        self.drop_var_a.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_var_a)
        self.drop_var_a.SetToolTipString(_("Right click variable to view/edit "
                                         "details"))
        self.drop_var_b = wx.Choice(self.panel, -1, size=(300, -1))
        self.drop_var_b.Bind(wx.EVT_CONTEXT_MENU, self.on_rclick_var_b)
        self.drop_var_b.SetToolTipString(_("Right click variable to "
                                              "view/edit details"))
        self.drop_var_b.Enable(False)
        self.setup_vars(var_a=True, var_b=False)
        btn_check = wx.Button(self.panel, -1, CHECK_LABEL)
        btn_check.Bind(wx.EVT_BUTTON, self.on_btn_check)
        szr_vars.Add(self.lbl_vars, 0, wx.LEFT|wx.RIGHT, 5)
        szr_vars.Add(self.drop_var_a, 0)
        szr_vars.Add(self.drop_var_b, 0, wx.LEFT, 10)
        szr_vars.Add(btn_check, 0, wx.LEFT, 10)
        self.img_hist = wx.StaticBitmap(self.panel, -1, size=(200, 100), 
                                        pos=(0,0))
        self.set_histo_to_blank()
        self.btn_details = wx.Button(self.panel, -1, _("Details"))
        self.btn_details.Bind(wx.EVT_BUTTON, self.on_details_click)
        self.btn_details.Enable(False)
        szr_shape.Add(self.img_hist, 0)
        szr_shape.Add(self.btn_details, 0, wx.TOP, 10)
        self.szr_examine.Add(szr_shape, 0, wx.TOP|wx.LEFT, 10)
        myheight = 100 if mg.MAX_HEIGHT < 800 else 200
        self.html = full_html.FullHTML(self.panel, size=(200, myheight))
        self.set_output_to_blank()
        szr_normality_test.Add(self.html, 1, wx.GROW)
        self.szr_examine.Add(szr_normality_test, 1, wx.GROW|wx.ALL, 10)
        btn_ok = wx.Button(self.panel, wx.ID_OK)
        btn_ok.Bind(wx.EVT_BUTTON, self.on_ok)
        szr_std_btns = wx.StdDialogButtonSizer()
        szr_std_btns.AddButton(btn_ok)
        szr_std_btns.Realize()
        szr_main.Add(self.szr_desc, 0, wx.ALL, 10)
        szr_main.Add(self.szr_data, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szr_main.Add(szr_paired, 0, wx.ALL, 10)
        szr_main.Add(szr_vars, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szr_main.Add(self.szr_examine, 1, wx.GROW)
        #szr_std_btns.Insert(0, self.szr_level, wx.ALIGN_LEFT|wx.ALL, 10)
        szr_main.Add(szr_std_btns, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(szr_main)
        self.szr_lst = [self.szr_desc, self.szr_data, szr_vars, szr_paired,
                   self.szr_examine]
        self.set_size()

    def set_size(self):
        lib.set_size(window=self, szr_lst=self.szr_lst, height_init=560)

    def on_rad_paired(self, event):
        "Respond to selection of single/paired"
        self.paired = (self.rad_paired.GetSelection() == 1)
        if self.paired:
            self.bx_vars.SetLabel(self.varbox_label_paired)
            self.lbl_desc.SetLabel(self.desc_label_paired)
            self.lbl_vars.SetLabel(self.var_label_paired)
        else:
            self.bx_vars.SetLabel(self.varbox_label_unpaired)
            self.lbl_desc.SetLabel(self.desc_label_unpaired)
            self.lbl_vars.SetLabel(self.var_label_unpaired)
        self.drop_var_b.Enable(self.paired)
        self.setup_vars(var_a=True, var_b=self.paired)
        self.set_histo_to_blank()
        self.btn_details.Enable(False)
        self.set_size()

    def get_bmp_blank_hist(self, paired=False):
        msg = self.blank_hist_txt_paired if self.paired \
                                            else self.blank_hist_txt_unpaired
        bmp_blank_hist = wx.BitmapFromImage(self.img_blank_hist)
        msg_font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD)
        lib.add_text_to_bitmap(bmp_blank_hist, msg, msg_font, "white", 
                               left=20, top=20)
        return bmp_blank_hist
        
    def set_histo_to_blank(self):
        bmp_blank_hist = self.get_bmp_blank_hist(self.paired)
        self.img_hist.SetBitmap(bmp_blank_hist)

    def set_output_to_blank(self):
        if self.paired:
            msg = _("Select two variables and click Check button to see results"
                    " of normality test")
        else:
            msg = _("Select a variable and click Check button to see results of"
                    " normality test")
        self.html.show_html("<p>%s</p>" % msg)

    def on_ok(self, event):
        self.Destroy()
        event.Skip()

    def on_database_sel(self, event):
        config_dlg.ConfigDlg.on_database_sel(self, event)
        self.setup_vars(var_a=True, var_b=self.paired)
        self.set_histo_to_blank()
        self.set_output_to_blank()
        
    def on_table_sel(self, event):
        config_dlg.ConfigDlg.on_table_sel(self, event)
        self.setup_vars(var_a=True, var_b=self.paired)
        self.set_histo_to_blank()
        self.set_output_to_blank()
        
    def on_rclick_tables(self, event):
        config_dlg.ConfigDlg.on_rclick_tables(self, event)
        self.update_examination()
        #event.Skip() - don't use or will appear twice in Windows!
    
    def setup_var_a(self, var=None):
        self.setup_vars(var_a=True, var_b=False, var=var)
    
    def setup_var_b(self, var=None):
        self.setup_vars(var_a=False, var_b=True, var=var)
        
    def setup_vars(self, var_a=True, var_b=True, var=None):
        var_names = projects.get_approp_var_names(self.var_types,
                                                min_data_type=mg.VAR_TYPE_QUANT)
        var_choices, self.sorted_var_names = lib.get_sorted_choice_items(
                                    dic_labels=self.var_labels, vals=var_names)
        if var_a:
            self.drop_var_a.SetItems(var_choices)
            idx_a = self.sorted_var_names.index(var) if var else 0
            self.drop_var_a.SetSelection(idx_a)
        if var_b:
            self.drop_var_b.SetItems(var_choices)
            idx_b = self.sorted_var_names.index(var) if var else 0
            self.drop_var_b.SetSelection(idx_a)

    def refresh_vars(self):
        config_dlg.ConfigDlg.update_var_dets(self)
        
    def get_var_a(self):
        idx = self.drop_var_a.GetSelection()
        var = self.sorted_var_names[idx]
        var_item = self.drop_var_a.GetStringSelection()
        return var, var_item

    def get_var_b(self):
        idx = self.drop_var_b.GetSelection()
        var = self.sorted_var_names[idx]
        var_item = self.drop_var_b.GetStringSelection()
        return var, var_item

    def get_exam_inputs(self):
        """
        Get variable label and a list of the non-null values (with any 
            additional filtering applied).
        NB For a paired sample, the 'variable' is the difference between two 
            selected variables.
        """
        var_a, choice_item_a = self.get_var_a()
        var_label_a = lib.get_item_label(item_labels=self.var_labels, 
                                         item_val=var_a)
        if self.paired:
            var_b, choice_item_b = self.get_var_b()
            var_label_b = lib.get_item_label(item_labels=self.var_labels, 
                                             item_val=var_b)
        unused, tbl_filt = lib.get_tbl_filt(dd.dbe, dd.db, dd.tbl)
        unused, and_filt = lib.get_tbl_filts(tbl_filt)
        obj_quoter = getdata.get_obj_quoter_func(dd.dbe)
        if not self.paired:
            s = u"""SELECT %(var)s
                FROM %(tbl)s
                WHERE %(var)s IS NOT NULL 
                %(and_filt)s
                ORDER BY %(var)s """ % {"var": obj_quoter(var_a), 
                                        "tbl": obj_quoter(dd.tbl),
                                        "and_filt": and_filt}
        else:
            s = u"""SELECT %(var_b)s - %(var_a)s
                FROM %(tbl)s
                WHERE %(var_a)s IS NOT NULL AND %(var_b)s IS NOT NULL 
                %(and_filt)s """ % {"var_a": obj_quoter(var_a), 
                                    "var_b": obj_quoter(var_b), 
                                    "tbl": obj_quoter(dd.tbl),
                                    "and_filt": and_filt}
        dd.cur.execute(s)
        vals = [x[0] for x in dd.cur.fetchall()]
        if len(set(vals)) == 1:
            raise my_exceptions.TooFewValsForDisplay
        if not self.paired:
            data_label = var_label_a
        else:
            data_label = _("Difference between %(a)s and %(b)s" % 
                           {"a": var_label_a, "b": var_label_b})
        return data_label, vals
    
    def update_examination(self):
        """
        Create and display thumbnail of histogram with normal dist curve plus
            discussion of normality test results.
        """
        try:
            self.data_label, self.vals = self.get_exam_inputs()
        except my_exceptions.TooFewValsForDisplay:
            wx.MessageBox(_("Not enough variability in data to allow a "
                            "histogram to be displayed"))
            return
        self.btn_details.Enable(True)
        # histogram
        charts.gen_config()
        fig = pylab.figure()
        fig.set_size_inches((2.3, 1.0)) # see dpi to get image size in pixels
        charts.config_hist(fig, self.vals, self.data_label, thumbnail=True)
        pylab.savefig(mg.INT_IMG_ROOT + u".png", dpi=100)
        thumbnail_uncropped = wx.Image(mg.INT_IMG_ROOT + u".png", 
                                       wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        rem_blank_axes_rect = wx.Rect(15, 0, 200, 100)
        thumbnail = thumbnail_uncropped.GetSubBitmap(rem_blank_axes_rect)
        self.img_hist.SetBitmap(thumbnail)
        # normality test (includes both kurtosis and skew)
        n_vals = len(self.vals)
        USUAL_FAIL_N = 100
        if n_vals < 20:
            msg = _("Need at least 20 values to test normality.  Rely entirely "
                "on visual inspection of graph above.")
        else:
            try:
                unused, p_arr, cskew, unused, ckurtosis, unused = \
                        core_stats.normaltest(self.vals)
                p = p_arr[0]
                if abs(cskew) <= 1:
                    sindic = "a great sign"
                elif abs(cskew) <= 2:
                    sindic = "a good sign"
                else:
                    sindic = "not a good sign"
                skew_msg = _("Skew (lopsidedness) is %(skew)s which is probably"
                             " %(indic)s.") % {"skew": round(cskew, 3), 
                                               "indic": sindic}   
                if abs(ckurtosis) <= 1:
                    kindic = "a great sign"
                elif abs(ckurtosis) <= 2:
                    kindic = "a good sign"
                else:
                    kindic = "not a good sign"
                kurtosis_msg = _("Kurtosis (peakedness or flatness) is %(kurt)s"
                                 " which is probably %(indic)s.") % \
                                 {"kurt": round(ckurtosis, 3), "indic": kindic}               
                if n_vals > USUAL_FAIL_N:
                    msg = _("Rely on visual inspection of graph above. "
                        "Although the data failed the ideal normality test, "
                        "most real-world data-sets with as many results (%s) "
                        "would fail for even slight differences from the "
                        "perfect normal curve.") % n_vals + u" " + skew_msg + \
                            u" " + kurtosis_msg
                else:
                    if p < 0.05:
                        msg = _("The distribution of %s passed one test for "
                            "normality.  Confirm or reject based on visual "
                            "inspection of graph above.") % self.data_label + \
                                u" " + skew_msg + u" " + kurtosis_msg
                    else:
                        msg = _("Although the distribution of %s is not "
                            "perfectly 'normal', it may still be 'normal' "
                            "enough for use. View graph above to decide.") % \
                                self.data_label + u" " + skew_msg + u" " + \
                                kurtosis_msg
            except Exception:
                msg = _("Unable to calculate normality tests")
        self.html.show_html(u"<p>%s</p>" % msg)
    
    def on_btn_check(self, event):
        if self.paired:
            if self.drop_var_a.GetStringSelection() == \
                    self.drop_var_b.GetStringSelection():
                wx.MessageBox(_("The two variables must be different"))
                event.Skip()
                return
        self.update_examination()
        event.Skip()
          
    def on_details_click(self, event):
        tbl_filt_label, tbl_filt = lib.get_tbl_filt(dd.dbe, dd.db, dd.tbl)
        filt_msg = lib.get_filt_msg(tbl_filt_label, tbl_filt)
        hist_label = u"Histogram of %s\n%s" % (self.data_label, filt_msg)
        dlg = charts.HistDlg(parent=self, vals=self.vals, 
                             var_label=self.data_label, hist_label=hist_label)
        dlg.ShowModal()
        event.Skip()
    
    def on_rclick_var_a(self, event):
        var_a, choice_item = self.get_var_a()
        var_label_a = lib.get_item_label(item_labels=self.var_labels, 
                                         item_val=var_a)
        updated = projects.set_var_props(choice_item, var_a, var_label_a, 
                                         self.var_labels, self.var_notes, 
                                         self.var_types, self.val_dics)
        if updated:
            self.setup_var_a(var_a)
    
    def on_rclick_var_b(self, event):
        var_b, choice_item = self.get_var_b()
        var_label_b = lib.get_item_label(item_labels=self.var_labels, 
                                         item_val=var_b)
        updated = projects.set_var_props(choice_item, var_b, var_label_b, 
                                         self.var_labels, self.var_notes, 
                                         self.var_types, self.val_dics)
        if updated:
            self.setup_var_b(var_b)