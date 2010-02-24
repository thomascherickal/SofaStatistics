#! /usr/bin/env python
# -*- coding: utf-8 -*-

import wx
import wxmpl
import pylab # must import after wxmpl so matplotlib.use() is always first

import my_globals
import lib
import my_exceptions
import full_html
import getdata
import charting_pylab as charts
import config_dlg
import core_stats
import os
import projects


class NormalityDlg(wx.Dialog, config_dlg.ConfigDlg):
    
    def __init__(self, parent, dbe, con_dets, default_dbs, default_tbls,
                 var_labels, var_notes, var_types, val_dics, fil_var_dets, 
                 paired=False):
        wx.Dialog.__init__(self, parent=parent, title=_("Normal Data?"),
                           size=(1024, 600),
                           style=wx.MINIMIZE_BOX | wx.MAXIMIZE_BOX | \
                           wx.RESIZE_BORDER | wx.SYSTEM_MENU | \
                           wx.CAPTION | wx.CLOSE_BOX | \
                           wx.CLIP_CHILDREN)
        # the following properties all required to utilise get_szrData
        self.dbe = dbe
        self.con_dets = con_dets
        self.default_dbs = default_dbs
        self.default_tbls = default_tbls
        self.var_labels = var_labels
        self.var_notes = var_notes
        self.var_types = var_types
        self.val_dics = val_dics
        self.fil_var_dets = fil_var_dets
        self.paired = paired
        self.panel = wx.Panel(self)
        # szrs
        szrMain = wx.BoxSizer(wx.VERTICAL)
        bxDesc = wx.StaticBox(self.panel, -1, _("Purpose"))
        szrDesc = wx.StaticBoxSizer(bxDesc, wx.VERTICAL)
        self.szrData = self.get_szrData(self.panel) # mixin
        if not self.paired:
            varbox_label = _("Variable to Check")
        else:
            varbox_label = _("Paired Variables to Check")
        bxVars = wx.StaticBox(self.panel, -1, varbox_label)
        szrVars = wx.StaticBoxSizer(bxVars, wx.HORIZONTAL)
        szrVarsRight = wx.BoxSizer(wx.VERTICAL)
        self.szrLevel = self.get_szrLevel(self.panel) # mixin
        self.szrExamine = wx.BoxSizer(wx.VERTICAL)
        szrShape = wx.BoxSizer(wx.HORIZONTAL)
        szrNormalityTest = wx.BoxSizer(wx.HORIZONTAL)
        # assembly
        if not self.paired:
            lblDesc1 = wx.StaticText(self.panel, -1, 
                _("Select the variable you are interested in. Is its "
                  "distribution close enough to the normal curve for use with "
                  "tests requiring that?"))
        else:
            lblDesc1 = wx.StaticText(self.panel, -1, 
                _("Select the paired variables you are interested in. Looking "
                  "at the differences, is the distribution close enough to the "
                  "normal curve for use with tests requiring that?"))
        lblDesc2 = wx.StaticText(self.panel, -1, 
            _("Look for gross outliers, extreme skewing, and clustering into "
              "groups."))
        szrDesc.Add(lblDesc1, 0, wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szrDesc.Add(lblDesc2, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        if not self.paired:
            lblDesc3 = wx.StaticText(self.panel, -1, 
                _("Note: if comparing samples, each sample must be normal "
                  "enough. Filter for each sample by right clicking on the "
                  "table selector."))
            szrDesc.Add(lblDesc3, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
            lblVars = wx.StaticText(self.panel, -1, _("Variable:"))
        else:
            lblVars = wx.StaticText(self.panel, -1, _("Variables:"))
        lblVars.SetFont(self.LABEL_FONT)
        self.dropVarA = wx.Choice(self.panel, -1, size=(300, -1))
        self.dropVarA.Bind(wx.EVT_CONTEXT_MENU, self.OnRightClickVarA)
        self.dropVarA.SetToolTipString(_("Right click variable to view/edit "
                                         "details"))
        if self.paired:
            self.dropVarB = wx.Choice(self.panel, -1, size=(300, -1))
            self.dropVarB.Bind(wx.EVT_CONTEXT_MENU, self.OnRightClickVarB)
            self.dropVarB.SetToolTipString(_("Right click variable to "
                                              "view/edit details"))
        self.setup_vars(var_a=True, var_b=self.paired)
        btnCheck = wx.Button(self.panel, -1, _("Check"))
        btnCheck.Bind(wx.EVT_BUTTON, self.OnButtonCheck)
        szrVars.Add(lblVars, 0, wx.LEFT|wx.RIGHT, 5)
        szrVars.Add(self.dropVarA, 0)
        if self.paired:
            szrVars.Add(self.dropVarB, 0, wx.LEFT, 10)
        szrVars.Add(btnCheck, 0, wx.LEFT, 10)
        self.imgHist = wx.StaticBitmap(self.panel, -1, size=(200, 100), 
                                        pos=(0,0))
        msg_font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD)
        img_blank_hist = wx.Image(os.path.join(my_globals.SCRIPT_PATH, 
                                               u"images", u"blankhisto.xpm"), 
                                               wx.BITMAP_TYPE_XPM)
        self.bmp_blank_hist = wx.BitmapFromImage(img_blank_hist)
        if not self.paired:
            raw_msg = _("Select variable to see graph")
        else:
            raw_msg = _("Select variables to see graph")
        msg = lib.get_text_to_draw(raw_msg, 145)
        lib.add_text_to_bitmap(self.bmp_blank_hist, msg, msg_font, "white", 
                               left=20, top=30)
        self.set_shape_to_blank()
        self.btnDetails = wx.Button(self.panel, -1, _("Details"))
        self.btnDetails.Bind(wx.EVT_BUTTON, self.OnDetailsClick)
        self.btnDetails.Enable(False)
        szrShape.Add(self.imgHist, 0)
        szrShape.Add(self.btnDetails, 0, wx.LEFT, 10)
        self.szrExamine.Add(szrShape, 0, wx.ALL, 10)
        self.html = full_html.FullHTML(self.panel, size=(200, 150))
        self.set_output_to_blank()
        szrNormalityTest.Add(self.html, 1, wx.GROW)
        self.szrExamine.Add(szrNormalityTest, 1, wx.GROW|wx.ALL, 10)
        btnOK = wx.Button(self.panel, wx.ID_OK)
        btnOK.Bind(wx.EVT_BUTTON, self.OnOK)
        szrStdBtns = wx.StdDialogButtonSizer()
        szrStdBtns.AddButton(btnOK)
        szrStdBtns.Realize()
        szrMain.Add(szrDesc, 0, wx.ALL, 10)
        szrMain.Add(self.szrData, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szrMain.Add(szrVars, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szrMain.Add(self.szrExamine, 1, wx.GROW)
        szrStdBtns.Insert(0, self.szrLevel, wx.ALIGN_LEFT|wx.ALL, 10)
        szrMain.Add(szrStdBtns, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(szrMain)
        szrMain.SetSizeHints(self)
        self.Layout()

    def set_shape_to_blank(self):
        self.imgHist.SetBitmap(self.bmp_blank_hist)

    def set_output_to_blank(self):
        if self.paired:
            msg = _("Select two variables to check to see results of normality "
                    "test")
        else:
            msg = _("Select a variable to check to see results of normality "
                    "test")
        self.html.show_html("<p>%s</p>" % msg)

    def OnOK(self, event):
        my_globals.DBE_DEFAULT = self.dbe
        my_globals.DB_DEFAULTS[self.dbe] = self.db
        my_globals.TBL_DEFAULTS[self.dbe] = self.tbl
        self.Destroy()
        event.Skip()

    def OnDatabaseSel(self, event):
        config_dlg.ConfigDlg.OnDatabaseSel(self, event)
        self.setup_vars()
        self.set_shape_to_blank()
        self.set_output_to_blank()
        
    def OnTableSel(self, event):
        config_dlg.ConfigDlg.OnTableSel(self, event)
        self.setup_vars()
        self.set_shape_to_blank()
        self.set_output_to_blank()
        
    def OnRightClickTables(self, event):
        config_dlg.ConfigDlg.OnRightClickTables(self, event)
        self.update_examination()
    
    def setup_var_a(self, var=None):
        self.setup_vars(var_a=True, var_b=False, var=var)
    
    def setup_var_b(self, var=None):
        self.setup_vars(var_a=False, var_b=True, var=var)
        
    def setup_vars(self, var_a=True, var_b=True, var=None):
        """
        
        """
        var_names = projects.get_approp_var_names(self.flds, self.var_types,
                                        min_data_type=my_globals.VAR_TYPE_QUANT)
        var_choices, self.sorted_var_names = lib.get_sorted_choice_items(
                                    dic_labels=self.var_labels, vals=var_names)
        if var_a:
            self.dropVarA.SetItems(var_choices)
            idx_a = self.sorted_var_names.index(var) if var else 0
            self.dropVarA.SetSelection(idx_a)
        if var_b:
            self.dropVarB.SetItems(var_choices)
            idx_b = self.sorted_var_names.index(var) if var else 0
            self.dropVarB.SetSelection(idx_a)

    def refresh_vars(self):
        config_dlg.ConfigDlg.update_var_dets(self)
        
    def get_var_a(self):
        idx = self.dropVarA.GetSelection()
        var = self.sorted_var_names[idx]
        var_item = self.dropVarA.GetStringSelection()
        return var, var_item

    def get_var_b(self):
        idx = self.dropVarB.GetSelection()
        var = self.sorted_var_names[idx]
        var_item = self.dropVarB.GetStringSelection()
        return var, var_item

    def get_exam_inputs(self):
        """
        Get variable label and a list of the non-null values (with any 
            additional filtering applied).
        NB For a paired sample, the 'variable' is the difference between two 
            selected variables.
        """
        var_a, choice_item_a = self.get_var_a()
        unused, var_label_a = lib.extract_var_choice_dets(choice_item_a)
        if self.paired:
            var_b, choice_item_b = self.get_var_b()
            unused, var_label_b = lib.extract_var_choice_dets(choice_item_b)
        unused, tbl_filt = lib.get_tbl_filt(self.dbe, self.db, self.tbl)
        unused, and_filt = lib.get_tbl_filts(tbl_filt)
        obj_quoter = getdata.get_obj_quoter_func(self.dbe)
        if not self.paired:
            s = """SELECT %(var)s
                FROM %(tbl)s
                WHERE %(var)s IS NOT NULL 
                %(and_filt)s
                ORDER BY %(var)s""" % {"var": obj_quoter(var_a), 
                                       "tbl": obj_quoter(self.tbl),
                                       "and_filt": and_filt}
        else:
            s = """SELECT %(var_b)s - %(var_a)s
                FROM %(tbl)s
                WHERE %(var_a)s IS NOT NULL AND %(var_b)s IS NOT NULL 
                %(and_filt)s""" % {"var_a": obj_quoter(var_a), 
                                   "var_b": obj_quoter(var_b), 
                                   "tbl": obj_quoter(self.tbl),
                                   "and_filt": and_filt}
        self.cur.execute(s)
        vals = [x[0] for x in self.cur.fetchall()]
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
        self.btnDetails.Enable(True)
        # histogram
        charts.gen_config()
        fig = pylab.figure()
        fig.set_size_inches((2.3, 1.0)) # see dpi to get image size in pixels
        charts.config_hist(fig, self.vals, self.data_label, thumbnail=True)
        pylab.savefig(my_globals.INT_IMG_ROOT + u".png", dpi=100)
        thumbnail_uncropped = wx.Image(my_globals.INT_IMG_ROOT + u".png", 
                                       wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        rem_blank_axes_rect = wx.Rect(15, 0, 200, 100)
        thumbnail = thumbnail_uncropped.GetSubBitmap(rem_blank_axes_rect)
        self.imgHist.SetBitmap(thumbnail)
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
                        "perfect normal curve") % n_vals + u" " + skew_msg + \
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
    
    def OnButtonCheck(self, event):
        if self.paired:
            if self.dropVarA.GetStringSelection() == \
                    self.dropVarB.GetStringSelection():
                wx.MessageBox(_("The two variables must be different"))
                event.Skip()
                return
        self.update_examination()
        event.Skip()
          
    def OnDetailsClick(self, event):
        tbl_filt_label, tbl_filt = lib.get_tbl_filt(self.dbe, self.db, self.tbl)
        filt_msg = lib.get_filt_msg(tbl_filt_label, tbl_filt)
        hist_label = u"Histogram of %s\n%s" % (self.data_label, filt_msg)
        dlg = charts.HistDlg(parent=self, vals=self.vals, 
                             var_label=self.data_label, hist_label=hist_label)
        dlg.ShowModal()
        event.Skip()
    
    def OnRightClickVarA(self, event):
        var, choice_item = self.get_var_a()
        var_name, var_label = lib.extract_var_choice_dets(choice_item)
        updated = projects.set_var_props(choice_item, var_name, var_label, 
                            self.flds, self.var_labels, self.var_notes, 
                            self.var_types, self.val_dics, self.fil_var_dets)
        if updated:
            self.setup_var_a(var)
    
    def OnRightClickVarB(self, event):
        var, choice_item = self.get_var_b()
        var_name, var_label = lib.extract_var_choice_dets(choice_item)
        updated = projects.set_var_props(choice_item, var_name, var_label, 
                            self.flds, self.var_labels, self.var_notes, 
                            self.var_types, self.val_dics, self.fil_var_dets)
        if updated:
            self.setup_var_b(var)