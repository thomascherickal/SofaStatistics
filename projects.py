from __future__ import print_function

import codecs
import os
import pprint
import sys
import wx

import my_globals as mg
import lib
import config_dlg
import getdata
import projselect
import settings_grid

LOCAL_PATH = mg.LOCAL_PATH

def get_projs():
    """
    NB includes .proj at end.
    os.listdir()
    Changed in version 2.3: On Windows NT/2k/XP and Unix, if path is a Unicode 
        object, the result will be a list of Unicode objects. Undecodable 
        filenames will still be returned as string objects.
    May need unicode results so always provide a unicode path. 
    """
    proj_fils = os.listdir(os.path.join(LOCAL_PATH, u"projs"))
    proj_fils = [x for x in proj_fils if x.endswith(u".proj")]
    proj_fils.sort()
    return proj_fils

def get_proj_notes(fil_proj, proj_dic):
    """
    If the default project, return the translated notes rather than what is 
        actually stored in the file (notes in English).
    """
    if fil_proj == mg.SOFA_DEFAULT_PROJ:
        proj_notes = _("Default project so users can get started without "
                       "having to understand projects.  NB read only.")
    else:
        proj_notes = proj_dic["proj_notes"]
    return proj_notes 
    
def get_var_dets(fil_var_dets):
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
    var_dets = lib.clean_bom_utf8(f.read())
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
        raise Exception, u"Three variables needed in " + \
            u"'%s': var_labels, var_notes, var_types, and val_dics.  " + \
            u"Please check file." % fil_var_dets
    return results

def set_var_props(choice_item, var_name, var_label, flds, var_labels, var_notes, 
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
    data.sort(key=lambda s: s[0])
    config_data = []
    # get config_data back updated
    bolnumeric = flds[var_name][mg.FLD_BOLNUMERIC]
    boldecimal = flds[var_name][mg.FLD_DECPTS]
    boldatetime = flds[var_name][mg.FLD_BOLDATETIME]
    boltext = flds[var_name][mg.FLD_BOLTEXT]
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
        def_type = mg.VAR_TYPE_QUANT # have to trust the user somewhat!
    elif boldatetime:
        def_type = mg.VAR_TYPE_CAT # see notes when enabling under 
            # GetSettings
    else:
        def_type = mg.VAR_TYPE_CAT
    type = var_types.get(var_name, def_type)
    var_desc = {"label": var_label, "notes": notes, "type": type}
    getsettings = GetSettings(title, boltext, boldatetime, var_desc, data, 
                              config_data, val_type)
    ret = getsettings.ShowModal()
    if ret == wx.ID_OK:
        # var label, notes, and types
        var_labels[var_name] = var_desc["label"]
        var_notes[var_name] = var_desc["notes"]
        var_types[var_name] = var_desc["type"]
        # val dics
        new_val_dic = {}
        new_data_rows_n = len(config_data)
        for i in range(new_data_rows_n):
            # the key is always returned as a string 
            # but we may need to store it as a number
            key, value = config_data[i]
            if key == "":
                continue
            elif val_type == settings_grid.COL_FLOAT:
                key = float(key)
            elif val_type == settings_grid.COL_INT:
                key = int(key)
            new_val_dic[key] = value
        val_dics[var_name] = new_val_dic
        # update lbl file
        f = codecs.open(fil_var_dets, "w", encoding="utf-8")
        f.write(os.linesep + u"var_labels=" + pprint.pformat(var_labels))
        f.write(os.linesep + u"var_notes=" + pprint.pformat(var_notes))
        f.write(os.linesep + u"var_types=" + pprint.pformat(var_types))
        f.write(os.linesep + os.linesep + u"val_dics=" + \
                pprint.pformat(val_dics))
        f.close()
        wx.MessageBox(_("Settings saved to \"%s\"" % fil_var_dets))
        return True
    else:
        return False
    
def get_approp_var_names(flds, var_types=None,
                         min_data_type=mg.VAR_TYPE_CAT):
    """
    Get filtered list of variable names according to minimum data type.
    """
    if min_data_type == mg.VAR_TYPE_CAT:
        var_names = [x for x in flds]
    elif min_data_type == mg.VAR_TYPE_ORD:
        # check for numeric as well in case user has manually 
        # misconfigured var_type in vdts file.
        var_names = [x for x in flds if flds[x][mg.FLD_BOLNUMERIC] and \
                     var_types.get(x) in (None, mg.VAR_TYPE_ORD, 
                                          mg.VAR_TYPE_QUANT)]
    elif min_data_type == mg.VAR_TYPE_QUANT:
        # check for numeric as well in case user has manually 
        # misconfigured var_type in vdts file.
        var_names = [x for x in flds if flds[x][mg.FLD_BOLNUMERIC] and \
                     var_types.get(x) in (None, mg.VAR_TYPE_QUANT)]
    return var_names

def get_idx_to_select(choice_items, drop_var, var_labels, default):
    """
    Get index to select.  If variable passed in, use that if possible.
    It will not be possible if it has been removed from the list e.g. because
        of a user reclassification of data type (e.g. was quantitative but
        has been redefined as categorical); or because of a change of filtering.
    If no variable passed in, or it was but couldn't be used (see above),
        use the default if possible.  If not possible, select the first 
        item.
    """
    var_removed = False
    if drop_var:
        item_new_version_drop = lib.get_choice_item(var_labels, drop_var)
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
    
    
class ListVarsDlg(wx.Dialog):
    def __init__(self, flds, var_labels, var_notes, var_types, val_dics, 
                 fil_var_dets, updated):
        "updated -- empty set - add True to 'return' updated True"
        wx.Dialog.__init__(self, None, title=_("Variable Details"),
                  size=(500,600), style=wx.CAPTION|wx.CLOSE_BOX|wx.SYSTEM_MENU)
        self.flds = flds
        self.var_labels = var_labels
        self.var_notes = var_notes
        self.var_types = var_types
        self.val_dics = val_dics
        self.fil_var_dets = fil_var_dets
        self.updated = updated
        self.panel = wx.Panel(self)
        self.szr_main = wx.BoxSizer(wx.VERTICAL)
        szrStdBtns = wx.StdDialogButtonSizer()
        self.lstVars = wx.ListBox(self.panel, -1, choices=[])
        self.lstVars.Bind(wx.EVT_LISTBOX, self.on_lst_click)
        self.setup_vars()
        btn_ok = wx.Button(self.panel, wx.ID_OK)
        btn_ok.Bind(wx.EVT_BUTTON, self.on_ok)
        self.panel.SetSizer(self.szr_main)
        self.szr_main.Add(self.lstVars, 0, wx.ALL, 10)
        szrStdBtns.AddButton(btn_ok)
        szrStdBtns.Realize()
        self.szr_main.Add(szrStdBtns, 0, wx.ALIGN_RIGHT|wx.ALL, 10)
        self.szr_main.SetSizeHints(self)
        self.Layout()
    
    def on_lst_click(self, event):
        debug = False
        try:
            var_name, choice_item = self.get_var()
        except Exception: # seems to be triggered
            return
        var_label = lib.get_item_label(item_labels=self.var_labels, 
                                       item_val=var_name)
        if debug:
            print(var_name)
            pprint.pprint(self.flds)
        updated = set_var_props(choice_item, var_name, var_label, self.flds, 
                                self.var_labels, self.var_notes, self.var_types, 
                                self.val_dics, self.fil_var_dets)
        if updated:
            self.setup_vars(var_name)
            self.updated.add(True)
    
    def on_ok(self, event):
        self.Destroy()
    
    def setup_vars(self, var=None):
        var_names = get_approp_var_names(self.flds)
        var_choices, self.sorted_var_names = lib.get_sorted_choice_items(
                                    dic_labels=self.var_labels, vals=var_names)
        self.lstVars.SetItems(var_choices)
        idx = self.sorted_var_names.index(var) if var else -1
        self.lstVars.SetSelection(idx)

    def get_var(self):
        idx = self.lstVars.GetSelection()
        if idx == -1:
            raise Exception, "Nothing selected"
        var = self.sorted_var_names[idx]
        var_item = self.lstVars.GetStringSelection()
        return var, var_item
    
    
class GetSettings(settings_grid.SettingsEntryDlg):
    
    def __init__(self, title, boltext, boldatetime, var_desc, data, 
                 config_data, val_type):
        """
        var_desc - dic with keys "label", "notes", and "type".
        data - list of tuples (must have at least one item, even if only a 
            "rename me".
        col_dets - See under settings_grid.SettingsEntry
        config_data - add details to it in form of a list of tuples.
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
                                       choices=mg.VAR_TYPES)
        self.radDataType.SetStringSelection(self.var_desc["type"])
        # if text or datetime, only enable categorical.
        # datetime cannot be quant (if a measurement of seconds etc would be 
        # numeric instead) and although ordinal, not used like that in any of 
        # these tests.
        if boltext or boldatetime:
            self.radDataType.EnableItem(mg.VAR_IDX_ORD, False)
            self.radDataType.EnableItem(mg.VAR_IDX_QUANT, False)
        btn_type_help = wx.Button(self.panel, wx.ID_HELP)
        btn_type_help.Bind(wx.EVT_BUTTON, self.on_type_help_btn)
        # sizers
        self.szr_main = wx.BoxSizer(wx.VERTICAL)
        self.szrVarLabel = wx.BoxSizer(wx.HORIZONTAL)
        self.szrVarLabel.Add(lblVarLabel, 0, wx.RIGHT, 5)
        self.szrVarLabel.Add(self.txtVarLabel, 1)
        self.szrVarNotes = wx.BoxSizer(wx.HORIZONTAL)
        self.szrVarNotes.Add(lblVarNotes, 0, wx.RIGHT, 5)
        self.szrVarNotes.Add(self.txtVarNotes, 1, wx.GROW)
        self.szr_main.Add(self.szrVarLabel, 0, wx.GROW|wx.ALL, 10)
        self.szr_main.Add(self.szrVarNotes, 1, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        self.szr_main.Add(self.radDataType, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        szr_data_type = wx.BoxSizer(wx.HORIZONTAL)
        szr_data_type.Add(self.radDataType, 0)  
        szr_data_type.Add(btn_type_help, 0, wx.LEFT|wx.TOP, 10)        
        self.szr_main.Add(szr_data_type, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        self.tabentry = settings_grid.SettingsEntry(self, self.panel, 
                                            self.szr_main, 2, False, grid_size, 
                                            col_dets, data, config_data)
        self.setup_btns(readonly=False)
        self.szr_main.Add(self.szr_btns, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(self.szr_main)
        self.szr_main.SetSizeHints(self)
        self.Layout()
        self.tabentry.grid.SetFocus()

    def on_type_help_btn(self, event):
        wx.MessageBox(_("Nominal data (names only) is just labels or names. "
          "Ordinal data has a sense of order but no amount, "
          "and Quantity data has actual amount e.g. 2 is twice 1."
          "\n\n* Example of Nominal (names only) data: sports codes ("
          "'Soccer', 'Badminton', 'Skiing' etc)."
          "\n\n* Example of Ordinal (ranked) data: ratings of restaurant "
          "service standards (1 - Very Poor, 2 - Poor, 3 - Average etc)."
          "\n\n* Example of Quantity (amount) data: height in cm."))

    def on_ok(self, event):
        """
        Override so we can extend to include variable label, type, and notes.
        """
        self.var_desc["label"] = self.txtVarLabel.GetValue()
        self.var_desc["notes"] = self.txtVarNotes.GetValue()
        self.var_desc["type"] = self.radDataType.GetStringSelection()
        self.tabentry.update_config_data()
        self.Destroy()
        self.SetReturnCode(wx.ID_OK)


class ProjectDlg(wx.Dialog, config_dlg.ConfigDlg):
    def __init__(self, parent, readonly=False, fil_proj=None):
        if mg.MAX_HEIGHT <= 620:
            myheight = 600
        elif mg.MAX_HEIGHT <= 870:
            myheight = mg.MAX_HEIGHT - 70
        else:
            myheight = 800
        wx.Dialog.__init__(self, parent=parent, title=_("Project Settings"),
               size=(1024, myheight), 
               style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|wx.RESIZE_BORDER|\
               wx.SYSTEM_MENU|wx.CAPTION|wx.CLOSE_BOX|wx.TAB_TRAVERSAL) 
               # wx.CLIP_CHILDREN causes problems in Windows
        self.szr = wx.BoxSizer(wx.VERTICAL)
        self.panel_top = wx.Panel(self)
        self.scroll_con_dets = wx.PyScrolledWindow(self, 
                size=(900, 350), # need for Windows
                style=wx.SUNKEN_BORDER|wx.TAB_TRAVERSAL)
        self.scroll_con_dets.SetScrollRate(10,10) # gives it the scroll bars
        self.panel_bottom = wx.Panel(self)
        self.parent = parent
        self.szr_con_dets = wx.BoxSizer(wx.VERTICAL)
        self.szr_bottom = wx.BoxSizer(wx.VERTICAL)
        # get available settings
        self.readonly = readonly
        self.new = (fil_proj is None)
        self.set_defaults(fil_proj)
        getdata.set_con_det_defaults(self)
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
                                        size=(200, 40), style=wx.TE_MULTILINE)
        self.txtProjNotes.Enable(not self.readonly)
        szr_desc = wx.BoxSizer(wx.HORIZONTAL)
        szr_desc.Add(lblName, 0, wx.RIGHT, 5)
        szr_desc.Add(self.txtName, 0, wx.RIGHT, 10)
        szr_desc.Add(lblProjNotes, 0, wx.RIGHT, 5)
        szr_desc.Add(self.txtProjNotes, 1, wx.GROW)
        # DATA CONNECTIONS
        lblDataConDets = wx.StaticText(self.panel_top, -1, 
                                        _("Data Connection Details:"))
        # default dbe
        lblDefault_Dbe = wx.StaticText(self.scroll_con_dets, -1, 
                                       _("Default Database Engine:"))
        lblDefault_Dbe.SetFont(lblfont)
        self.dropDefault_Dbe = wx.Choice(self.scroll_con_dets, -1, 
                                         choices=mg.DBES)
        sel_dbe_id = mg.DBES.index(self.default_dbe)
        self.dropDefault_Dbe.SetSelection(sel_dbe_id)
        self.dropDefault_Dbe.Bind(wx.EVT_CHOICE, self.on_dbe_choice)
        self.dropDefault_Dbe.Enable(not self.readonly)
        lblScrollDown = wx.StaticText(self.scroll_con_dets, -1, 
                    _("(scroll down for details of all your database engines)"))
        # default dbe
        szr_default_dbe = wx.BoxSizer(wx.HORIZONTAL)
        szr_default_dbe.Add(lblDefault_Dbe, 0, wx.LEFT|wx.RIGHT, 5)
        szr_default_dbe.Add(self.dropDefault_Dbe, 0)
        szr_default_dbe.Add(lblScrollDown, 0, wx.LEFT, 10)
        # Close
        self.setup_btns()
        # sizers
        # TOP
        self.szrTop = wx.BoxSizer(wx.VERTICAL)
        self.szrTop.Add(szr_desc, 1, wx.GROW|wx.ALL, 10)
        # mixin supplying self.szr_config_top and self.szr_config_bottom
        self.szr_config_bottom, self.szr_config_top = \
            self.get_misc_config_szrs(self.panel_top, readonly=self.readonly)
        self.szrTop.Add(self.szr_config_top, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        self.szrTop.Add(self.szr_config_bottom, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        #self.szrTop.Add(szrOutput, 0, wx.GROW|wx.ALL, 10)
        self.szrTop.Add(lblDataConDets, 0, wx.GROW|wx.LEFT, 10)
        self.panel_top.SetSizer(self.szrTop)
        self.szrTop.SetSizeHints(self.panel_top)
        # CON DETS
        self.szr_con_dets.Add(szr_default_dbe, 0, wx.LEFT|wx.RIGHT|wx.TOP, 10)
        getdata.set_data_con_gui(parent=self, readonly=self.readonly, 
                                 scroll=self.scroll_con_dets, 
                                 szr=self.szr_con_dets, lblfont=lblfont)
        self.scroll_con_dets.SetSizer(self.szr_con_dets)
        # NEVER SetSizeHints or else grows beyond size!!!!
        self.szr_con_dets.SetVirtualSizeHints(self.scroll_con_dets)
        # BOTTOM
        self.szr_bottom.Add(self.szr_btns, 0, wx.GROW|wx.LEFT|wx.BOTTOM|\
                            wx.RIGHT|wx.ALIGN_RIGHT, 10)
        self.panel_bottom.SetSizer(self.szr_bottom)
        self.szr_bottom.SetSizeHints(self.panel_bottom)
        # FINAL # NB any ratio changes must work in multiple OSs
        self.szr.Add(self.panel_top, 1, wx.GROW)
        self.szr.Add(self.scroll_con_dets, 2, wx.GROW|wx.LEFT|wx.BOTTOM|wx.RIGHT, 10)
        self.szr.Add(self.panel_bottom, 0, wx.GROW)
        self.SetAutoLayout(True)
        self.SetSizer(self.szr)
        self.SetMinSize((930,550))
        self.Layout()
        self.sqlite_grid.grid.SetFocus()
        self.txtName.SetFocus()
        
    def set_defaults(self, fil_proj):
        if fil_proj:
            self.new_proj = False
            self.get_proj_settings(fil_proj)
        else:
            # prepopulate with default settings
            self.get_proj_settings(fil_proj=mg.SOFA_DEFAULT_PROJ)
            self.proj_name = mg.EMPTY_PROJ_NAME
            self.proj_notes = _("The SOFA Default Database is needed to allow "
                                "you to add new tables to SOFA Statistics")
            self.new_proj = True
        try:
            self.proj_name
        except AttributeError:
            self.proj_name = mg.EMPTY_PROJ_NAME
        try:
            self.proj_notes
        except AttributeError:
            self.proj_notes = ""
        try:
            self.fil_var_dets
        except AttributeError:
            # make empty labels file if necessary
            fil_default_var_dets = os.path.join(LOCAL_PATH, u"vdts", 
                                            mg.SOFA_DEFAULT_VDTS)
            if not os.path.exists(fil_default_var_dets):
                f = open(fil_default_var_dets, "w")
                f.write(u"# add variable details here")
                f.close()
            self.fil_var_dets = fil_default_var_dets
        try:            
            self.fil_css
        except AttributeError:
            self.fil_css = os.path.join(LOCAL_PATH, u"css", 
                                        mg.SOFA_DEFAULT_STYLE)
        try:            
            self.fil_report
        except AttributeError:       
            self.fil_report = os.path.join(LOCAL_PATH, u"reports", 
                                           mg.SOFA_DEFAULT_REPORT)
        try:            
            self.fil_script
        except AttributeError: 
            self.fil_script = os.path.join(LOCAL_PATH, u"scripts", 
                                           mg.SOFA_DEFAULT_SCRIPT)
        try:
            self.default_dbe
        except AttributeError:
            self.default_dbe = os.path.join(mg.DBE_SQLITE)
        
    def get_proj_settings(self, fil_proj):
        """
        NB get any paths in form ready to display
        """
        proj_path = os.path.join(LOCAL_PATH, "projs", fil_proj)
        f = codecs.open(proj_path, "U", encoding="utf-8")
        proj_cont = lib.clean_bom_utf8(f.read())
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
        try:
            self.proj_notes = get_proj_notes(fil_proj, proj_dic)
            self.fil_var_dets = proj_dic["fil_var_dets"]
            self.fil_css = proj_dic["fil_css"]
            self.fil_report = proj_dic["fil_report"]
            self.fil_script = proj_dic["fil_script"]
            self.default_dbe = proj_dic["default_dbe"]
            getdata.get_proj_con_settings(self, proj_dic)
        except Exception, e:
            wx.MessageBox(_("Please check %s for errors e.g. conn_dets instead "
                            "of con_dets.  Use the default project file for "
                            "reference.") % fil_proj)
            raise Exception, e
    
    def on_dbe_choice(self, event):
        sel_dbe_id = self.dropDefault_Dbe.GetSelection()
        self.default_dbe = mg.DBES[sel_dbe_id]
        event.Skip()
    
    def setup_btns(self):
        """
        Must have ID of wx.ID_... to trigger validators (no event binding 
            needed) and for std dialog button layout.
        NB can only add some buttons as part of standard sizer to be realised.
        Insert or Add others after the Realize() as required.
        See http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3605904
        and http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3605432
        """
        if self.readonly:
            btn_ok = wx.Button(self.panel_bottom, wx.ID_OK)
        else:
            if not self.new:
                btn_delete = wx.Button(self.panel_bottom, wx.ID_DELETE)
                btn_delete.Bind(wx.EVT_BUTTON, self.on_delete)
            btn_cancel = wx.Button(self.panel_bottom, wx.ID_CANCEL) # 
            btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
            btn_ok = wx.Button(self.panel_bottom, wx.ID_OK, _("Update"))
        btn_ok.Bind(wx.EVT_BUTTON, self.on_ok)
        self.szr_btns = wx.StdDialogButtonSizer()
        if not self.readonly:
            self.szr_btns.AddButton(btn_cancel)
        self.szr_btns.AddButton(btn_ok)
        self.szr_btns.Realize()
        if not self.readonly and not self.new:
            self.szr_btns.Insert(0, btn_delete, 0)

    def on_delete(self, event):
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

    def on_cancel(self, event):
        "Close returning us to wherever we came from"
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL) # only for dialogs 
        # (MUST come after Destroy)
       
    def on_ok(self, event):
        # get the data (separated for easier debugging)
        if not self.readonly:
            proj_name = self.txtName.GetValue()
            if proj_name == mg.EMPTY_PROJ_NAME:
                wx.MessageBox(_("Please provide a project name"))
                self.txtName.SetFocus()
                return
            try:
                # only needed if returning to projselect form
                # so OK to fail otherwise
               self.parent.store_proj_name(u"%s.proj" % proj_name)
            except Exception:
                print(u"Failed to change to %s.proj" % proj_name)
                pass
            proj_notes = self.txtProjNotes.GetValue()
            fil_var_dets = self.txtVarDetsFile.GetValue()
            fil_css = self.txtCssFile.GetValue()
            fil_report = self.txtReportFile.GetValue()
            fil_script = self.txtScriptFile.GetValue()
            default_dbe = mg.DBES[self.dropDefault_Dbe.GetSelection()]
            default_dbs = {}
            default_tbls = {}
            con_dets = {}
            any_incomplete, any_cons, completed_dbes = \
                                getdata.process_con_dets(self, default_dbs, 
                                                         default_tbls, con_dets)
            if any_incomplete:
                return
            enough_completed = proj_name and any_cons
            if not enough_completed:
                wx.MessageBox(_("Not enough details completed to "
                                "save a project file"))
                return
            default_dbe_lacks_con = default_dbe not in completed_dbes
            if default_dbe_lacks_con:
                wx.MessageBox(_("Connection details need to be completed "
                      "for the default database engine (%s) to save a project"
                      " file.") % default_dbe)
                return
            # write the data
            fil_name = os.path.join(LOCAL_PATH, u"projs", u"%s.proj" % \
                                    proj_name)
            f = codecs.open(fil_name, "w", encoding="utf-8")
            f.write(u"# Windows file paths _must_ have double not single "
                    u"backslashes")
            f.write(os.linesep + u"# All file paths _must_ have a u before the"
                    u" quote-enclosed string")
            f.write(os.linesep + u"""# u"C:\\\\Users\\\\demo.txt" is GOOD""")
            f.write(os.linesep + u"""# u"C:\\Users\\demo.txt" is BAD""")
            f.write(os.linesep + u"""# "C:\\\\Users\\\\demo.txt" is also BAD""")
            f.write(os.linesep + os.linesep + u"proj_notes = u\"\"\"%s\"\"\"" \
                    % proj_notes)
            f.write(os.linesep + os.linesep + u"fil_var_dets = u\"%s\"" % 
                    lib.escape_win_path(fil_var_dets))
            f.write(os.linesep + u"fil_css = u\"%s\"" % \
                    lib.escape_win_path(fil_css))
            f.write(os.linesep + u"fil_report = u\"%s\"" % 
                    lib.escape_win_path(fil_report))
            f.write(os.linesep + u"fil_script = u\"%s\"" % 
                    lib.escape_win_path(fil_script))
            f.write(os.linesep + u"default_dbe = u\"%s\"" % default_dbe)
            f.write(os.linesep + os.linesep + u"default_dbs = " + \
                    pprint.pformat(default_dbs))
            f.write(os.linesep + os.linesep + u"default_tbls = " + \
                    pprint.pformat(default_tbls))
            f.write(os.linesep + os.linesep + u"con_dets = " + \
                    pprint.pformat(con_dets))
            f.close()
            if self.new_proj:
                self.parent.parent.set_proj(proj_name)
        self.Destroy()
        self.SetReturnCode(wx.ID_OK) # only for dialogs
        # (MUST come after Destroy)        
        