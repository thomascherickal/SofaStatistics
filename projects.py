from __future__ import print_function

import codecs
import os
import pprint
import sys
import wx

import my_globals
import gen_config
import getdata
import projselect
import settings_grid
import util

LOCAL_PATH = my_globals.LOCAL_PATH

def GetProjs():
    """
    NB includes .proj at end.
    os.listdir()
    Changed in version 2.3: On Windows NT/2k/XP and Unix, if path is a Unicode 
        object, the result will be a list of Unicode objects. Undecodable 
        filenames will still be returned as string objects.
    May need unicode results so always provide a unicode path. 
    """
    proj_fils = os.listdir(os.path.join(LOCAL_PATH, u"projs"))
    proj_fils = [x for x in proj_fils if x.endswith(".proj")]
    proj_fils.sort()
    return proj_fils

def GetProjNotes(fil_proj, proj_dic):
    """
    If the default project, return the translated notes rather than what is 
        actually stored in the file (notes in English).
    """
    if fil_proj == my_globals.SOFA_DEFAULT_PROJ:
        proj_notes = _("Default project so users can get started without "
                       "having to understand projects.  NB read only.")
    else:
        proj_notes = proj_dic["proj_notes"]
    return proj_notes 
    
def GetProjSettingsDic(proj_name):
    """
    Returns proj_dic with keys such as conn_dets, fil_var_dets etc.
    proj_name MUST include .proj on end
    """
    proj_path = os.path.join(LOCAL_PATH, "projs", proj_name)
    f = codecs.open(proj_path, "U", encoding="utf-8")
    proj_cont = util.clean_bom_utf8(f.read())
    f.close() 
    proj_dic = {}
    try:
        # http://docs.python.org/reference/simple_stmts.html
        exec proj_cont in proj_dic
    except SyntaxError, e:
        wx.MessageBox(\
            _("Syntax error in project file \"%s\"." % proj_name + \
                      os.linesep + os.linesep + "Details: %s" % unicode(e)))
        raise Exception, unicode(e)
    except Exception, e:
        wx.MessageBox(\
            _("Error processing project file \"%s\"." % proj_name + \
                      os.linesep + os.linesep + "Details: %s" % unicode(e)))
        raise Exception, unicode(e)
    return proj_dic

def GetVarDets(fil_var_dets):
    """
    Get variable details from fil_var_dets file.
    Returns var_labels, var_notes, var_types, val_dics.
    """
    try:
        f = codecs.open(fil_var_dets, "U", encoding="utf-8")
    except IOError:
        var_labels = {}
        var_notes = {}
        var_types = {}
        val_dics = {}
        return var_labels, var_notes, var_types, val_dics
    var_dets = util.clean_bom_utf8(f.read())
    f.close()
    var_dets_dic = {}
    try:
        # http://docs.python.org/reference/simple_stmts.html
        exec var_dets in var_dets_dic
    except SyntaxError, e:
        wx.MessageBox(\
            _("Syntax error in variable details file \"%s\"." % fil_var_dets + \
                      os.linesep + os.linesep + "Details: %s" % unicode(e)))
        raise Exception, unicode(e)
    except Exception, e:
        wx.MessageBox(\
            _("Error processing variable"
              " details file \"%s\"." % fil_var_dets + \
              os.linesep + os.linesep + "Details: %s" % unicode(e)))
        raise Exception, unicode(e)
    try:
        results = var_dets_dic["var_labels"], var_dets_dic["var_notes"], \
                      var_dets_dic["var_types"], var_dets_dic["val_dics"]
    except Exception, e:
        raise Exception, "Three variables needed in " + \
            "'%s': var_labels, var_notes, var_types, and val_dics.  " + \
            "Please check file." % fil_var_dets
    return results

def SetVarProps(choice_item, var_name, var_label, flds, var_labels, var_notes, 
                var_types, val_dics, fil_var_dets):
    """
    For selected variable (name) gives user ability to set properties e.g.
        value labels.  Then stores in appropriate labels file.
    Returns True if user clicks OK to properties (presumably modified).
    """
    # get val_dic for variable (if any) and display in editable list
    data = []
    if val_dics.get(var_name):
        val_dic = val_dics.get(var_name)
        if val_dic:
            for key, value in val_dic.items():
                data.append((key, unicode(value)))
    new_grid_data = []
    # get new_grid_data back updated
    bolnumeric = flds[var_name][my_globals.FLD_BOLNUMERIC]
    boldecimal = flds[var_name][my_globals.FLD_DECPTS]
    boldatetime = flds[var_name][my_globals.FLD_BOLDATETIME]
    boltext = flds[var_name][my_globals.FLD_BOLTEXT]
    if bolnumeric:
        if boldecimal:
            val_type = settings_grid.COL_FLOAT
        else:
            val_type = settings_grid.COL_INT
    else:
        val_type = settings_grid.COL_STR
    title = _("Settings for %s") % choice_item
    notes = var_notes.get(var_name, "")
    # if nothing recorded, choose useful default variable type
    if bolnumeric:
        def_type = my_globals.VAR_TYPE_QUANT # have to trust the user somewhat!
    elif boldatetime:
        def_type = my_globals.VAR_TYPE_ORD
    else:
        def_type = my_globals.VAR_TYPE_CAT
    type = var_types.get(var_name, def_type)
    var_desc = {"label": var_label, "notes": notes, "type": type}
    getsettings = GetSettings(title, boltext, boldatetime, var_desc, data, 
                              new_grid_data, val_type)
    ret = getsettings.ShowModal()
    if ret == wx.ID_OK:
        # var label
        var_labels[var_name] = var_desc["label"]
        # var notes
        var_notes[var_name] = var_desc["notes"]
        # var type
        var_types[var_name] = var_desc["type"]
        # val dics
        new_val_dic = {}
        new_data_rows_n = len(new_grid_data)
        for i in range(new_data_rows_n):
            # the key is always returned as a string 
            # but we may need to store it as a number
            key, value = new_grid_data[i]
            if val_type == settings_grid.COL_FLOAT:
                key = float(key)
            elif val_type == settings_grid.COL_INT:
                key = int(key)
            new_val_dic[key] = value
        val_dics[var_name] = new_val_dic
        # update lbl file
        f = codecs.open(fil_var_dets, "w", encoding="utf-8")
        f.write(os.linesep + "var_labels=" + pprint.pformat(var_labels))
        f.write(os.linesep + "var_notes=" + pprint.pformat(var_notes))
        f.write(os.linesep + "var_types=" + pprint.pformat(var_types))
        f.write(os.linesep + os.linesep + "val_dics=" + \
                pprint.pformat(val_dics))
        f.close()
        return True
    else:
        return False
    
def GetAppropVarNames(min_data_type, var_types, flds):
    """
    Get filtered list of variable names according to minimum data type.
    """
    if min_data_type == my_globals.VAR_TYPE_CAT:
        var_names = [x for x in flds]
    elif min_data_type == my_globals.VAR_TYPE_ORD:
        # check for numeric as well in case user has manually 
        # misconfigured var_type in vdts file.
        var_names = [x for x in flds if flds[x][my_globals.FLD_BOLNUMERIC] and \
                     var_types.get(x) in (None, my_globals.VAR_TYPE_ORD, 
                                          my_globals.VAR_TYPE_QUANT)]
    elif min_data_type == my_globals.VAR_TYPE_QUANT:
        # check for numeric as well in case user has manually 
        # misconfigured var_type in vdts file.
        var_names = [x for x in flds if flds[x][my_globals.FLD_BOLNUMERIC] and \
                     var_types.get(x) in (None, my_globals.VAR_TYPE_QUANT)]
    return var_names

def GetIdxToSelect(choice_items, drop_var, var_labels, default):
    """
    Get index to select.  If variable passed in, use that if possible.
    It will not be possible if it has been removed from the list because
        of a user reclassification of data type e.g. was quantitative but
        has been redefined as categorical.
    If no variable passed in, or it was but couldn't be used (see above),
        use the default if possible.  If not possible, select the first 
        item.
    """
    var_removed = False
    if drop_var:
        item_new_version_drop = getdata.getChoiceItem(var_labels, drop_var)
        try:
            idx = choice_items.index(item_new_version_drop)
        except ValueError:
            var_removed = True # e.g. may require QUANT and user changed to 
            # ORD.  Variable will no longer appear in list. Cope!
    if (not drop_var) or var_removed: # use default if possible
        idx = 0
        if default:
            try:
                idx = choice_items.index(default)
            except ValueError:
                pass
    return idx
    
    
class GetSettings(settings_grid.TableEntryDlg):
    
    def __init__(self, title, boltext, boldatetime, var_desc, data, 
                 new_grid_data, val_type):
        """
        var_desc - dic with keys "label", "notes", and "type".
        data - list of tuples (must have at least one item, even if only a 
            "rename me".
        col_dets - See under settings_grid.TableEntry
        new_grid_data - add details to it in form of a list of tuples.
        """
        col_dets = [{"col_label": _("Value"), "col_type": val_type, 
                     "col_width": 50}, 
                    {"col_label": _("Label"), "col_type": settings_grid.COL_STR, 
                     "col_width": 200},
                     ]
        grid_size = (250, 250)
        wx.Dialog.__init__(self, None, title=title,
                          size=(500,400), 
                          style=wx.RESIZE_BORDER|wx.CAPTION|wx.CLOSE_BOX|
                              wx.SYSTEM_MENU)
        self.panel = wx.Panel(self)
        self.var_desc = var_desc
        # New controls
        lblVarLabel = wx.StaticText(self.panel, -1, _("Variable Label:"))
        lblVarLabel.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        lblVarNotes = wx.StaticText(self.panel, -1, "Notes:")
        lblVarNotes.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.txtVarLabel = wx.TextCtrl(self.panel, -1, self.var_desc["label"], 
                                       size=(250,-1))
        self.txtVarNotes = wx.TextCtrl(self.panel, -1, self.var_desc["notes"],
                                       style=wx.TE_MULTILINE)
        self.radDataType = wx.RadioBox(self.panel, -1, _("Data Type"),
                                       choices=my_globals.VAR_TYPES)
        self.radDataType.SetStringSelection(self.var_desc["type"])
        # if text or datetime, only enable categorical.
        # datetime cannot be quant (if a measurement of seconds etc would be 
        # numeric instead) and although ordinal, not used like that in any of 
        # these tests.
        if boltext or boldatetime:
            self.radDataType.EnableItem(my_globals.VAR_IDX_ORD, False)
            self.radDataType.EnableItem(my_globals.VAR_IDX_QUANT, False)
        btnTypeHelp = wx.Button(self.panel, wx.ID_HELP)
        btnTypeHelp.Bind(wx.EVT_BUTTON, self.OnTypeHelpButton)
        # sizers
        self.szrMain = wx.BoxSizer(wx.VERTICAL)
        self.szrVarLabel = wx.BoxSizer(wx.HORIZONTAL)
        self.szrVarLabel.Add(lblVarLabel, 0, wx.RIGHT, 5)
        self.szrVarLabel.Add(self.txtVarLabel, 1)
        self.szrVarNotes = wx.BoxSizer(wx.HORIZONTAL)
        self.szrVarNotes.Add(lblVarNotes, 0, wx.RIGHT, 5)
        self.szrVarNotes.Add(self.txtVarNotes, 1, wx.GROW)
        self.szrMain.Add(self.szrVarLabel, 0, wx.GROW|wx.ALL, 10)
        self.szrMain.Add(self.szrVarNotes, 1, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        self.szrMain.Add(self.radDataType, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        szrDataType = wx.BoxSizer(wx.HORIZONTAL)
        szrDataType.Add(self.radDataType, 0)  
        szrDataType.Add(btnTypeHelp, 0, wx.LEFT|wx.TOP, 10)        
        self.szrMain.Add(szrDataType, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        self.tabentry = settings_grid.TableEntry(self, self.panel, 
                                                 self.szrMain, 2, False, 
                                                 grid_size, col_dets, data,  
                                                 new_grid_data)
        self.SetupButtons()
        self.szrMain.Add(self.szrButtons, 0, wx.ALL, 10)
        self.panel.SetSizer(self.szrMain)
        self.szrMain.SetSizeHints(self)
        self.Layout()
        self.tabentry.grid.SetFocus()

    def OnTypeHelpButton(self, event):
        wx.MessageBox(_("Nominal data (names only) is just labels or names. "
          "Ordinal data has a sense of order but no amount, "
          "and Quantity data has actual amount e.g. 2 is twice 1."
          "\n\n* Example of Nominal (names only) data: sports codes ("
          "'Soccer', 'Badminton', 'Skiing' etc)."
          "\n\n* Example of Ordinal (ranked) data: ratings of restaurant "
          "service standards (1 - Very Poor, 2 - Poor, 3 - Average etc)."
          "\n\n* Example of Quantity (amount) data: height in cm."))

    def OnOK(self, event):
        """
        Override so we can extend to include variable label, type, and notes.
        """        
        self.var_desc["label"] = self.txtVarLabel.GetValue()
        self.var_desc["notes"] = self.txtVarNotes.GetValue()
        self.var_desc["type"] = self.radDataType.GetStringSelection()
        self.tabentry.UpdateNewGridData()
        self.Destroy()
        self.SetReturnCode(wx.ID_OK)


class ProjectDlg(wx.Dialog, gen_config.GenConfig):
    def __init__(self, parent, readonly=False, fil_proj=None):
        wx.Dialog.__init__(self, parent=parent, title=_("Project Settings"),
                           size=(1024, 600),
                           style=wx.CAPTION|wx.CLOSE_BOX|wx.SYSTEM_MENU|\
                           wx.TAB_TRAVERSAL, pos=(0, 0))
        y_start = -15 if util.in_windows() else 0
        self.panel_top = wx.Panel(self, pos=(0,0))
        top_height = 185
        self.scroll_conn_dets = wx.PyScrolledWindow(self, 
                                        pos=(10, top_height + y_start), 
                                        size=(1000, 355),
                                        style=wx.SUNKEN_BORDER|wx.TAB_TRAVERSAL)
        self.scroll_conn_dets.SetScrollbars(-1, 10, -1, -1) # else no scrollbars
        self.scroll_conn_dets.SetVirtualSize((1000, 620))
        self.panel_bottom = wx.Panel(self, pos=(0, top_height + 360 + y_start))
        self.parent = parent
        self.szrConn_Dets = wx.BoxSizer(wx.VERTICAL)
        self.szrBottom = wx.BoxSizer(wx.VERTICAL)
        # get available settings
        self.readonly = readonly
        if fil_proj:
            self.new_proj = False
            self.GetProjSettings(fil_proj)
        else:
            self.new_proj = True
        try:
            self.proj_name
        except AttributeError:
            self.proj_name = my_globals.EMPTY_PROJ_NAME
        try:
            self.proj_notes
        except AttributeError:
            self.proj_notes = ""
        try:
            self.fil_var_dets
        except AttributeError:
            # make empty labels file if necessary
            fil_default_var_dets = os.path.join(LOCAL_PATH, u"vdts", 
                                            my_globals.SOFA_DEFAULT_VDTS)
            if not os.path.exists(fil_default_var_dets):
                f = open(fil_default_var_dets, "w")
                f.write(u"# add variable details here")
                f.close()
            self.fil_var_dets = fil_default_var_dets
        try:            
            self.fil_css
        except AttributeError:
            self.fil_css = os.path.join(LOCAL_PATH, u"css", 
                                        my_globals.SOFA_DEFAULT_STYLE)
        try:            
            self.fil_report
        except AttributeError:       
            self.fil_report = os.path.join(LOCAL_PATH, u"reports", 
                                           my_globals.SOFA_DEFAULT_REPORT)
        try:            
            self.fil_script
        except AttributeError: 
            self.fil_script = os.path.join(LOCAL_PATH, u"scripts", 
                                           my_globals.SOFA_DEFAULT_SCRIPT)
        try:
            self.default_dbe
        except AttributeError:
            self.default_dbe = os.path.join(my_globals.DBE_SQLITE)
        getdata.setConnDetDefaults(self)
        # misc
        lblfont = wx.Font(9, wx.SWISS, wx.NORMAL, wx.BOLD)
        # Project Name and notes
        lblName = wx.StaticText(self.panel_top, -1, _("Project Name:"))
        lblName.SetFont(lblfont)
        self.txtName = wx.TextCtrl(self.panel_top, -1, self.proj_name, 
                                   size=(200, -1))
        self.txtName.Enable(not self.readonly)
        lblProjNotes = wx.StaticText(self.panel_top, -1, _("Notes:"))
        lblProjNotes.SetFont(lblfont)
        self.txtProjNotes = wx.TextCtrl(self.panel_top, -1, self.proj_notes,
                                        size=(600, 40), style=wx.TE_MULTILINE)
        self.txtProjNotes.Enable(not self.readonly)
        szrDesc = wx.BoxSizer(wx.HORIZONTAL)
        szrDesc.Add(lblName, 0, wx.RIGHT, 5)
        szrDesc.Add(self.txtName, 0, wx.RIGHT, 10)
        szrDesc.Add(lblProjNotes, 0, wx.RIGHT, 5)
        szrDesc.Add(self.txtProjNotes, 1, wx.GROW)
        self.MiscConfigSetup(self.panel_top, readonly=self.readonly) # mixin
        # DATA CONNECTIONS
        lblDataConnDets = wx.StaticText(self.panel_top, -1, 
                                        _("Data Connection Details:"))
        # default dbe
        lblDefault_Dbe = wx.StaticText(self.scroll_conn_dets, -1, 
                                       _("Default Database Engine:"))
        lblDefault_Dbe.SetFont(lblfont)
        self.dropDefault_Dbe = wx.Choice(self.scroll_conn_dets, -1, 
                                         choices=my_globals.DBES)
        sel_dbe_id = my_globals.DBES.index(self.default_dbe)
        self.dropDefault_Dbe.SetSelection(sel_dbe_id)
        self.dropDefault_Dbe.Bind(wx.EVT_CHOICE, self.OnDbeChoice)
        self.dropDefault_Dbe.Enable(not self.readonly)
        lblScrollDown = wx.StaticText(self.scroll_conn_dets, -1, 
                    _("(scroll down for details of all your database engines)"))
        # default dbe
        szrDefault_Dbe = wx.BoxSizer(wx.HORIZONTAL)
        szrDefault_Dbe.Add(lblDefault_Dbe, 0, wx.LEFT|wx.RIGHT, 5)
        szrDefault_Dbe.Add(self.dropDefault_Dbe, 0)
        szrDefault_Dbe.Add(lblScrollDown, 0, wx.LEFT, 10)
        # Close
        self.SetupButtons()
        # sizers
        # TOP
        self.szrTop = wx.BoxSizer(wx.VERTICAL)
        self.szrTop.Add(szrDesc, 1, wx.GROW|wx.ALL, 10)
        # mixin supplying self.szrConfigTop and self.szrConfigBottom
        self.SetupMiscConfigSizers(self.panel_top)
        self.szrTop.Add(self.szrConfigTop, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        self.szrTop.Add(self.szrConfigBottom, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        #self.szrTop.Add(szrOutput, 0, wx.GROW|wx.ALL, 10)
        self.szrTop.Add(lblDataConnDets, 0, wx.LEFT, 10)
        self.panel_top.SetSizer(self.szrTop)
        self.szrTop.SetSizeHints(self.panel_top)
        # CONN DETS
        self.szrConn_Dets.Add(szrDefault_Dbe, 0, wx.LEFT|wx.RIGHT|wx.TOP, 10)
        getdata.setDataConnGui(parent=self, read_only=self.readonly, 
                               scroll=self.scroll_conn_dets, 
                               szr=self.szrConn_Dets, lblfont=lblfont)
        self.scroll_conn_dets.SetSizer(self.szrConn_Dets)
        # NEVER SetSizeHints or else grows beyond size!!!!
        self.szrConn_Dets.SetVirtualSizeHints(self.scroll_conn_dets)
        self.scroll_conn_dets.FitInside() # no effect
        # BOTTOM        
        self.szrBottom.Add(self.szrButtons, 0, wx.ALL, 10)
        self.panel_bottom.SetSizer(self.szrBottom)
        self.szrBottom.SetSizeHints(self.panel_bottom)
        # FINAL
        self.Layout()
        self.sqlite_grid.grid.SetFocus()
        self.txtName.SetFocus()

    def GetProjSettings(self, fil_proj):
        """
        NB get any paths in form ready to display
        """
        proj_path = os.path.join(LOCAL_PATH, "projs", fil_proj)
        f = codecs.open(proj_path, "U", encoding="utf-8")
        proj_cont = util.clean_bom_utf8(f.read())
        f.close()
        proj_dic = {}
        try:
            exec proj_cont in proj_dic
        except SyntaxError, e:
            wx.MessageBox(\
                _("Syntax error in project file \"%s\"." % fil_proj + \
                          os.linesep + os.linesep + "Details: %s" % unicode(e)))
            raise Exception, unicode(e)
        except Exception, e:
            wx.MessageBox(\
                _("Error processing project file \"%s\"." % fil_proj + \
                          os.linesep + os.linesep + "Details: %s" % unicode(e)))
            raise Exception, unicode(e)
        self.proj_name = fil_proj[:-5]
        # Taking settings from proj file (via exec and proj_dic)
        #   and adding them to this frame ready for use.
        # Must always be stored, even if only ""
        self.proj_notes = GetProjNotes(fil_proj, proj_dic)
        self.fil_var_dets = proj_dic["fil_var_dets"]
        self.fil_css = proj_dic["fil_css"]
        self.fil_report = proj_dic["fil_report"]
        self.fil_script = proj_dic["fil_script"]
        self.default_dbe = proj_dic["default_dbe"]
        getdata.getProjConnSettings(self, proj_dic)
    
    def OnDbeChoice(self, event):
        sel_dbe_id = self.dropDefault_Dbe.GetSelection()
        self.default_dbe = my_globals.DBES[sel_dbe_id]
        event.Skip()
    
    def SetupButtons(self):
        """
        Must have ID of wx.ID_... to trigger validators (no event binding 
            needed) and for std dialog button layout.
        NB can only add some buttons as part of standard sizer to be realised.
        Insert or Add others after the Realize() as required.
        See http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3605904
        and http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3605432
        """
        btnDelete = wx.Button(self.panel_bottom, wx.ID_DELETE)
        btnDelete.Bind(wx.EVT_BUTTON, self.OnDelete)
        btnCancel = wx.Button(self.panel_bottom, wx.ID_CANCEL) # 
        btnCancel.Bind(wx.EVT_BUTTON, self.OnCancel)
        if self.readonly:
            btnDelete.Disable()
            btnCancel.Disable()
        btnOK = wx.Button(self.panel_bottom, wx.ID_OK)
        btnOK.Bind(wx.EVT_BUTTON, self.OnOK)
        self.szrButtons = wx.StdDialogButtonSizer()
        self.szrButtons.AddButton(btnCancel)
        self.szrButtons.AddButton(btnOK)
        self.szrButtons.Realize()
        self.szrButtons.Insert(0, btnDelete, 0)

    def OnDelete(self, event):
        proj_name = self.txtName.GetValue()
        if wx.MessageBox(_("Deleting a project cannot be undone.  "
                           "Do you want to delete the \"%s\" project?") % \
                           proj_name, 
                style=wx.YES|wx.NO|wx.ICON_EXCLAMATION|wx.NO_DEFAULT) == wx.NO:
            return
        try:
            fil_to_delete = os.path.join(LOCAL_PATH, "projs", 
                                   "%s.proj" % self.txtName.GetValue())
            #print(fil_to_delete) # debug
            os.remove(fil_to_delete)
        except Exception:
            pass
        self.Destroy()
        self.SetReturnCode(wx.ID_DELETE) # only for dialogs 
        # (MUST come after Destroy)

    def OnCancel(self, event):
        "Close returning us to wherever we came from"
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL) # only for dialogs 
        # (MUST come after Destroy)
       
    def OnOK(self, event):
        # get the data (separated for easier debugging)
        if not self.readonly:
            proj_name = self.txtName.GetValue()
            if proj_name == my_globals.EMPTY_PROJ_NAME:
                wx.MessageBox(_("Please provide a project name"))
                self.txtName.SetFocus()
                return
            try:
                # only needed if returning to projselect form
                # so OK to fail otherwise
               self.parent.StoreProjName("%s.proj" % proj_name)
            except Exception:
                print("Failed to change to %s.proj" % proj_name)
                pass
            proj_notes = self.txtProjNotes.GetValue()
            fil_var_dets = self.txtVarDetsFile.GetValue()
            fil_css = self.txtCssFile.GetValue()
            fil_report = self.txtReportFile.GetValue()
            fil_script = self.txtScriptFile.GetValue()
            default_dbe = my_globals.DBES[self.dropDefault_Dbe.GetSelection()]
            default_dbs = {}
            default_tbls = {}
            conn_dets = {}
            any_incomplete, any_conns, completed_dbes = \
                getdata.processConnDets(self, default_dbs, default_tbls, 
                                        conn_dets)
            if any_incomplete:
                return
            enough_completed = proj_name and any_conns
            if not enough_completed:
                wx.MessageBox(_("Not enough details completed to "
                                "save a project file"))
                return
            default_dbe_lacks_conn = default_dbe not in completed_dbes
            if default_dbe_lacks_conn:
                wx.MessageBox(_("Connection details need to be completed "
                      "for the default database engine (%s) to save a project"
                      " file.") % default_dbe)
                return
            # write the data
            fil_name = os.path.join(LOCAL_PATH, "projs", "%s.proj" % proj_name)
            f = codecs.open(fil_name, "w", encoding="utf-8")
            f.write("# Windows file paths _must_ have double not single "
                    "backslashes")
            f.write(os.linesep + "# All file paths _must_ have a u before the"
                    " quote-enclosed string")
            f.write(os.linesep + """# u"C:\\\\Users\\\\demo.txt" is GOOD""")
            f.write(os.linesep + """# u"C:\\Users\\demo.txt" is BAD""")
            f.write(os.linesep + """# "C:\\\\Users\\\\demo.txt" is also BAD""")
            f.write(os.linesep + os.linesep + u"proj_notes = u\"%s\"" % \
                    proj_notes)
            f.write(os.linesep + os.linesep + u"fil_var_dets = u\"%s\"" % 
                    util.escape_win_path(fil_var_dets))
            f.write(os.linesep + u"fil_css = u\"%s\"" % \
                    util.escape_win_path(fil_css))
            f.write(os.linesep + u"fil_report = u\"%s\"" % 
                    util.escape_win_path(fil_report))
            f.write(os.linesep + u"fil_script = u\"%s\"" % 
                    util.escape_win_path(fil_script))
            f.write(os.linesep + u"default_dbe = \"%s\"" % default_dbe)
            f.write(os.linesep + os.linesep + u"default_dbs = " + \
                    pprint.pformat(default_dbs))
            f.write(os.linesep + os.linesep + u"default_tbls = " + \
                    pprint.pformat(default_tbls))
            f.write(os.linesep + os.linesep + u"conn_dets = " + \
                    pprint.pformat(conn_dets))
            f.close()
            if self.new_proj:
                self.parent.parent.SetProj(proj_name)
        self.Destroy()
        self.SetReturnCode(wx.ID_OK) # only for dialogs 
        # (MUST come after Destroy)
        