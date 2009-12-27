#! /usr/bin/env python
# -*- coding: utf-8 -*-
import wx

import my_globals
import lib
import getdata
import projects


def get_val(raw_val, flds, fld_name):
    """
    Value is validated first.  Raw value will always be a string.
    If numeric, must be a number, an empty string (turned to Null), 
        or any variant of Null.
    If a date, must be a usable date, an empty string, or Null.  Empty 
        strings are turned to Null.  Usable dates are returned as std datetimes.
    If a string, can be anything.  Variants of Null are treated specially.
    Null values (or any variant of Null) are turned to None which will be 
        processed correctly as a Null when clauses are made.
    """
    debug = False
    bolnumeric = flds[fld_name][my_globals.FLD_BOLNUMERIC]
    boldatetime = flds[fld_name][my_globals.FLD_BOLDATETIME]
    if bolnumeric:
        if lib.is_numeric(raw_val):
            return float(raw_val)
        else: # not a num - a valid string?
            if isinstance(raw_val, basestring):
                if raw_val == "" or raw_val.lower() == "null":
                    return None
        raise Exception, ("Only a number, an empty string, or Null can "
                          "be entered for filtering a numeric field")
    elif boldatetime:
        usable_datetime = lib.is_usable_datetime_str(raw_val)
        if usable_datetime:
            if debug: print("A valid datetime: '%s'" % raw_val)
            return lib.get_std_datetime_str(raw_val)
        else: # not a datetime - a valid string?
            if isinstance(raw_val, basestring):
                if raw_val == "" or raw_val.lower() == "null":
                    return None
        raise Exception, ("Only a datetime, an empty string, or Null can "
                          "be entered for filtering a datetime field")
    else:
        if raw_val.lower() == "null":
            return None
        else:
            return raw_val
        

class FiltSelectDlg(wx.Dialog):
    def __init__(self, parent, dbe, con, cur, db, tbl, flds, var_labels, 
                 var_notes, var_types, val_dics, fil_var_dets):
        debug = False
        self.dbe = dbe
        self.con = con
        self.cur = cur
        self.db = db
        self.tbl = tbl
        self.flds = flds
        self.var_labels = var_labels
        self.var_notes = var_notes
        self.var_types = var_types
        self.val_dics = val_dics
        self.fil_var_dets = fil_var_dets
        tbl_filt_label, self.tbl_filt = lib.get_tbl_filt(self.dbe, self.db, 
                                                         self.tbl)
        title = _("Current filter") if self.tbl_filt else _("Apply filter")
        wx.Dialog.__init__(self, parent=parent, title=title, 
                           style=wx.CAPTION|wx.CLOSE_BOX|
                           wx.SYSTEM_MENU, pos=(300, 100))
        self.parent = parent
        self.panel = wx.Panel(self)
        # szrs
        szrMain = wx.BoxSizer(wx.VERTICAL)
        szrLabel = wx.BoxSizer(wx.HORIZONTAL)
        szrQuick = wx.BoxSizer(wx.HORIZONTAL)
        szrFlex = wx.BoxSizer(wx.VERTICAL)
        # assemble
        self.radQuick = wx.RadioButton(self.panel, -1, _("Quick"), 
                                       style=wx.RB_GROUP)
        radFlex = wx.RadioButton(self.panel, -1, _("Flexible"))
        self.radQuick.Bind(wx.EVT_RADIOBUTTON, self.OnRadQuickSel)
        radFlex.Bind(wx.EVT_RADIOBUTTON, self.OnRadFlexSel)
        # label content
        lblLabel = wx.StaticText(self.panel, -1, _("Label (optional):"))
        self.txtLabel = wx.TextCtrl(self.panel, -1, tbl_filt_label)
        szrLabel.Add(lblLabel, 0, wx.RIGHT, 10)
        szrLabel.Add(self.txtLabel, 1)
        # quick content
        self.dropVars = wx.Choice(self.panel, -1, size=(300, -1))
        self.dropVars.Bind(wx.EVT_RIGHT_DOWN, self.OnRightClickVars)
        self.dropVars.SetToolTipString(_("Right click variable to view/edit "
                                         "details"))
        self.setup_vars()
        gte_choices = my_globals.GTES
        self.dropGTE = wx.Choice(self.panel, -1, choices=gte_choices)
        self.dropGTE.SetSelection(0)
        self.txtVal = wx.TextCtrl(self.panel, -1, "")
        self.lblQuickInstructions = wx.StaticText(self.panel, -1, 
                              _("(don't quote strings e.g. John not \"John\". "
                                "Null for missing)"))
        szrQuick.Add(self.radQuick, 0)
        szrQuick.Add(self.dropVars, 1, wx.LEFT|wx.RIGHT, 5)
        szrQuick.Add(self.dropGTE, 0)
        szrQuick.Add(self.txtVal, 0)
        # split
        lnSplit = wx.StaticLine(self.panel) 
        # flexible content
        self.txtFlexFilter = wx.TextCtrl(self.panel, -1, "",
                                         style=wx.TE_MULTILINE, size=(-1, 75))
        self.lblFlexExample = wx.StaticText(self.panel, -1, 
                                        _("(enter a filter e.g. agegp > 5)"))
        szrFlex.Add(radFlex, 0)
        szrFlex.Add(self.lblFlexExample, 0)
        szrFlex.Add(self.txtFlexFilter, 1, wx.GROW)
        if self.tbl_filt:
            radFlex.SetValue(True)
            self.enable_quick_dets(False)
            self.enable_flex_dets(True)
            self.txtFlexFilter.SetValue(self.tbl_filt)
        else:
            self.radQuick.SetValue(True)
            self.enable_quick_dets(True)
            self.enable_flex_dets(False)
        self.setup_btns()
        szrMain.Add(szrLabel, 0, wx.GROW|wx.ALL, 10)
        szrMain.Add(szrQuick, 0, wx.ALL, 10)
        szrMain.Add(self.lblQuickInstructions, 0, 
                    wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        szrMain.Add(lnSplit, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szrMain.Add(szrFlex, 0, wx.GROW|wx.ALL, 10)
        szrMain.Add(self.szrBtns, 0, wx.ALL|wx.GROW, 10)
        self.panel.SetSizer(szrMain)
        szrMain.SetSizeHints(self)
        self.Layout()
        self.txtLabel.SetFocus()

    def setup_vars(self, var=None):
        var_names = projects.get_approp_var_names(self.flds)
        var_choices, self.sorted_var_names = lib.get_sorted_choice_items(
                                    dic_labels=self.var_labels, vals=var_names)
        self.dropVars.SetItems(var_choices)
        idx = self.sorted_var_names.index(var) if var else 0
        self.dropVars.SetSelection(idx)

    def setup_btns(self):
        """
        Must have ID of wx.ID_... to trigger validators (no event binding 
            needed) and for std dialog button layout.
        NB can only add some buttons as part of standard sizer to be realised.
        Insert or Add others after the Realize() as required.
        See http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3605904
        and http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3605432
        """
        btnVarDets = wx.Button(self.panel, -1, _("Variable Details"))
        btnVarDets.Bind(wx.EVT_BUTTON, self.OnVarDets)
        btnDelete = wx.Button(self.panel, wx.ID_DELETE, _("Remove"))
        btnDelete.Bind(wx.EVT_BUTTON, self.OnDelete)
        btnCancel = wx.Button(self.panel, wx.ID_CANCEL) # 
        btnCancel.Bind(wx.EVT_BUTTON, self.OnCancel)
        if not self.tbl_filt:
            btnDelete.Disable()
        btnOK = wx.Button(self.panel, wx.ID_OK, _("Apply"))
        btnOK.Bind(wx.EVT_BUTTON, self.OnOK)
        # szrs
        self.szrBtns = wx.BoxSizer(wx.HORIZONTAL)
        szrExtraBtns = wx.BoxSizer(wx.HORIZONTAL)
        szrStdBtns = wx.StdDialogButtonSizer()
        # assemble
        szrExtraBtns.Add(btnVarDets, 0, wx.ALIGN_LEFT)
        szrStdBtns.AddButton(btnCancel)
        szrStdBtns.AddButton(btnOK)
        szrStdBtns.Realize()
        szrStdBtns.Insert(0, btnDelete, 0)
        self.szrBtns.Add(szrExtraBtns, 1)
        self.szrBtns.Add(szrStdBtns, 0)
        btnOK.SetDefault()

    def OnVarDets(self, event):
        """
        Open dialog with list of variables. On selection, opens standard get 
            settings dialog.
        """
        updated = set() # will get populated with a True to indicate update
        dlg = projects.ListVarsDlg(self.flds, self.var_labels, self.var_notes, 
                                   self.var_types, self.val_dics, 
                                   self.fil_var_dets, updated)
        dlg.ShowModal()
        if updated:
            choice_text = self.dropVars.GetStringSelection()
            fld_name, unused = lib.extract_var_choice_dets(choice_text)
            self.setup_vars(var=fld_name)
        event.Skip()
        
    def OnDelete(self, event):
        try:
            del my_globals.DBE_TBL_FILTS[self.dbe][self.db][self.tbl]
        except KeyError:
            raise Exception, ("Tried to delete filter but not in global "
                              "dictionary")
        self.Destroy()
        self.SetReturnCode(wx.ID_DELETE) # only for dialogs 
        # (MUST come after Destroy)
    
    def OnCancel(self, event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL) # only for dialogs 
        # (MUST come after Destroy)

    def get_quick_filter(self):
        "Get filter from quick setting"
        debug = False
        choice_text = self.dropVars.GetStringSelection()
        fld_name, unused = lib.extract_var_choice_dets(choice_text)
        val = get_val(self.txtVal.GetValue(), self.flds, fld_name)
        gte = self.dropGTE.GetStringSelection()
        filt = getdata.make_fld_val_clause(self.dbe, self.flds, fld_name, val, 
                                           gte)
        if debug: print(filt)
        return filt

    def OnOK(self, event):
        debug = False
        tbl_filt_label = self.txtLabel.GetValue() 
        if self.radQuick.GetValue():
            try:
                tbl_filt = self.get_quick_filter()
            except Exception, e:
                wx.MessageBox(_("Problem with design of filter: %s") % e)
                return
        else:
            tbl_filt = self.txtFlexFilter.GetValue()
            if not tbl_filt:
                wx.MessageBox(_("Please enter a filter"))
                return
        # Must work with a simple query to that database
        obj_quoter = getdata.get_obj_quoter_func(self.dbe)
        filt_test_SQL = "SELECT * FROM %s " % obj_quoter(self.tbl) + \
            "WHERE (%s)" % tbl_filt
        if debug: print("Filter: %s" % filt_test_SQL)
        try:
            self.cur.execute(filt_test_SQL)
        except Exception:
            val_quoter = getdata.get_val_quoter_func(self.dbe)
            demo = ((_("\n\nFilters for %(dbe)s data should look like this:") + \
                u"\n\ne.g. %(city)s = %(vancouver)s" + \
                u"\ne.g. %(age)s >= 20" + \
                u"\ne.g. (%(city)s = %(vancouver)s AND %(age)s >= 20) " + \
                "OR %(gender)s = 2") %
                      {"dbe": self.dbe,
                       "city": obj_quoter("city"), 
                       "vancouver": val_quoter("Vancouver"),
                       "age": obj_quoter("age"),
                       "gender": obj_quoter("gender")})
            wx.MessageBox(_("Problem applying filter \"%s\" to \"%s\"") % \
                          (tbl_filt, self.tbl) + demo)
            return
        if self.dbe not in my_globals.DBE_TBL_FILTS:
            my_globals.DBE_TBL_FILTS[self.dbe] = {}
        if self.db not in my_globals.DBE_TBL_FILTS[self.dbe]:
            my_globals.DBE_TBL_FILTS[self.dbe][self.db] = {}
        my_globals.DBE_TBL_FILTS[self.dbe][self.db][self.tbl] = \
            (tbl_filt_label, tbl_filt)
        self.Destroy()
        self.SetReturnCode(wx.ID_OK) # or nothing happens!  
        # Prebuilt dialogs must do this internally.

    def OnRadQuickSel(self, event):
        ""
        self.enable_quick_dets(True)
        self.enable_flex_dets(False)
        
    def OnRadFlexSel(self, event):
        ""
        self.enable_quick_dets(False)
        self.enable_flex_dets(True)
        self.txtFlexFilter.SetFocus()
        
    def enable_quick_dets(self, enable):
        self.dropVars.Enable(enable)
        self.dropGTE.Enable(enable)
        self.txtVal.Enable(enable)
        self.lblQuickInstructions.Enable(enable)
        
    def enable_flex_dets(self, enable):
        self.lblFlexExample.Enable(enable)
        self.txtFlexFilter.Enable(enable)

    def get_var(self):
        idx = self.dropVars.GetSelection()
        var = self.sorted_var_names[idx]
        var_item = self.dropVars.GetStringSelection()
        return var, var_item
    
    def OnRightClickVars(self, event):
        var, choice_item = self.get_var()
        var_name, var_label = lib.extract_var_choice_dets(choice_item)
        updated = projects.set_var_props(choice_item, var_name, var_label, 
                            self.flds, self.var_labels, self.var_notes, 
                            self.var_types, self.val_dics, self.fil_var_dets)
        if updated:
            self.setup_vars(var)        