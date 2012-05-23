from __future__ import print_function

import codecs
import os
import pprint
import wx

import my_globals as mg
import lib
import my_exceptions
import getdata
import config_output
import settings_grid

def get_projs():
    """
    NB includes .proj at end.
    os.listdir()
    Changed in version 2.3: On Windows NT/2k/XP and Unix, if path is a Unicode 
        object, the result will be a list of Unicode objects. Undecodable 
        filenames will still be returned as string objects.
    May need unicode results so always provide a unicode path. 
    """
    proj_fils = os.listdir(os.path.join(mg.LOCAL_PATH, mg.PROJS_FOLDER))
    proj_fils = [x for x in proj_fils if x.endswith(u".proj")]
    proj_fils.sort()
    return proj_fils

def get_proj_notes(fil_proj, proj_dic):
    """
    Read the proj file and extract the notes part.
    If the default project, return the translated notes rather than what is 
        actually stored in the file (notes in English).
    """
    if fil_proj == mg.DEFAULT_PROJ:
        proj_notes = _("Default project so users can get started without "
                       "having to understand projects. NB read only.")
    else:
        proj_notes = proj_dic["proj_notes"]
    return proj_notes

def update_val_labels(val_dics, var_name, val_type, keyvals):
    """
    var_name -- name of variable we are updating values for
    val_dics -- existing val-labels pairs for all variables
    keyvals -- pairs of vals and their labels
    """
    new_val_dic = {}
    for key, value in keyvals:
        # key always returned as a string but may need to store as number
        if key == u"":
            continue
        elif val_type == settings_grid.COL_FLOAT:
            key = float(key)
        elif val_type == settings_grid.COL_INT:
            key = int(float(key)) # so '12.0' -> 12. int('12.0') -> err
        new_val_dic[key] = value
    val_dics[var_name] = new_val_dic
    
def update_vdt(var_labels, var_notes, var_types, val_dics):
    # update lbl file
    cc = config_output.get_cc()
    f = codecs.open(cc[mg.CURRENT_VDTS_PATH], "w", encoding="utf-8")
    f.write(u"var_labels=" + lib.dic2unicode(var_labels))
    f.write(u"\n\nvar_notes=" + lib.dic2unicode(var_notes))
    f.write(u"\n\nvar_types=" + lib.dic2unicode(var_types))
    f.write(u"\n\n\nval_dics=" + lib.dic2unicode(val_dics))
    f.close()
    wx.MessageBox(_("Settings saved to \"%s\"") % cc[mg.CURRENT_VDTS_PATH])

def set_var_props(choice_item, var_name, var_label, var_labels, var_notes, 
                  var_types, val_dics):
    """
    For selected variable (name) gives user ability to set properties e.g.
        value labels.  Then stores in appropriate labels file.
    Returns True if user clicks OK to properties (presumably modified).
    """
    dd = mg.DATADETS_OBJ
    # get val_dic for variable (if any) and display in editable list
    init_settings_data = []
    if val_dics.get(var_name):
        val_dic = val_dics.get(var_name)
        if val_dic:
            for key, value in val_dic.items():
                # If a number, even if stored as string, get as number and use 
                # that and sort by that.
                try:
                    newkey = int(key)
                except Exception:
                    try:
                        newkey = float(key)
                    except Exception:
                        newkey = key
                init_settings_data.append((newkey, unicode(value)))
    init_settings_data.sort(key=lambda s: s[0])
    settings_data = [] # get settings_data back updated
    bolnumeric = dd.flds[var_name][mg.FLD_BOLNUMERIC]
    boldecimal = dd.flds[var_name][mg.FLD_DECPTS]
    boldatetime = dd.flds[var_name][mg.FLD_BOLDATETIME]
    boltext = dd.flds[var_name][mg.FLD_BOLTEXT]
    if bolnumeric:
        if boldecimal or dd.dbe == mg.DBE_SQLITE: # could be int or float so  
            # have to allow the more inclusive.
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
        def_type = mg.VAR_TYPE_CAT # see notes when enabling under GetSettings
    else:
        def_type = mg.VAR_TYPE_CAT
    type = var_types.get(var_name, def_type)
    var_desc = {"label": var_label, "notes": notes, "type": type}
    getsettings = GetSettings(title, boltext, boldatetime, var_desc, 
                              init_settings_data, settings_data, val_type)
    ret = getsettings.ShowModal()
    if ret == wx.ID_OK:
        if var_desc["label"].strip():
            var_labels[var_name] = var_desc["label"]
        else:
            try: # otherwise uses empty string as label which can't be seen ;-). 
                # Better to act as if has no label at all.
                del var_labels[var_name]
            except KeyError:
                pass
        var_notes[var_name] = var_desc["notes"]
        var_types[var_name] = var_desc["type"]
        update_val_labels(val_dics, var_name, val_type, keyvals=settings_data)
        update_vdt(var_labels, var_notes, var_types, val_dics)
        return True
    else:
        return False
    
def get_approp_var_names(var_types=None, min_data_type=mg.VAR_TYPE_CAT):
    """
    Get filtered list of variable names according to minimum data type.
    """
    dd = mg.DATADETS_OBJ
    if min_data_type == mg.VAR_TYPE_CAT:
        var_names = [x for x in dd.flds]
    elif min_data_type == mg.VAR_TYPE_ORD:
        # check for numeric as well in case user has manually 
        # misconfigured var_type in vdts file.
        var_names = [x for x in dd.flds if dd.flds[x][mg.FLD_BOLNUMERIC] and \
                     var_types.get(x) in (None, mg.VAR_TYPE_ORD, 
                                          mg.VAR_TYPE_QUANT)]
    elif min_data_type == mg.VAR_TYPE_QUANT:
        # check for numeric as well in case user has manually 
        # misconfigured var_type in vdts file.
        var_names = [x for x in dd.flds if dd.flds[x][mg.FLD_BOLNUMERIC] and \
                     var_types.get(x) in (None, mg.VAR_TYPE_QUANT)]
    return var_names

def get_idx_to_select(choice_items, drop_var, var_labels, default):
    """
    Get index to select. If variable passed in, use that if possible.
    It will not be possible if it has been removed from the list e.g. because
        of a user reclassification of data type (e.g. was quantitative but
        has been redefined as categorical); or because of a change of filtering.
    If no variable passed in, or it was but couldn't be used (see above),
        use the default if possible. If not possible, select the first 
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
                my_exceptions.DoNothingException("OK if no default - use idx "
                                                 "of 0.")
    return idx
    
    
class ListVarsDlg(wx.Dialog):
    def __init__(self, var_labels, var_notes, var_types, val_dics, updated):
        "updated -- empty set - add True to 'return' updated True"
        wx.Dialog.__init__(self, None, title=_("Variable Details"),
                           size=(500,600), 
                           style=wx.CAPTION|wx.CLOSE_BOX|wx.SYSTEM_MENU)
        self.Bind(wx.EVT_CLOSE, self.on_ok)
        self.var_labels = var_labels
        self.var_notes = var_notes
        self.var_types = var_types
        self.val_dics = val_dics
        self.updated = updated
        self.panel = wx.Panel(self)
        self.szr_main = wx.BoxSizer(wx.VERTICAL)
        szr_std_btns = wx.StdDialogButtonSizer()
        self.lst_vars = wx.ListBox(self.panel, -1, choices=[])
        self.setup_vars()
        self.lst_vars.Bind(wx.EVT_LISTBOX, self.on_lst_click)
        btn_ok = wx.Button(self.panel, wx.ID_OK)
        btn_ok.Bind(wx.EVT_BUTTON, self.on_ok)
        self.panel.SetSizer(self.szr_main)
        self.szr_main.Add(self.lst_vars, 0, wx.ALL, 10)
        szr_std_btns.AddButton(btn_ok)
        szr_std_btns.Realize()
        self.szr_main.Add(szr_std_btns, 0, wx.ALIGN_RIGHT|wx.ALL, 10)
        self.szr_main.SetSizeHints(self)
        self.Layout()
    
    def on_lst_click(self, event):
        debug = False
        try:
            var_name, choice_item = self.get_var()
        except Exception: # seems to be triggered on exit
            if debug: print(u"Clicked badly")
            event.Skip()
            return
        var_label = lib.get_item_label(item_labels=self.var_labels, 
                                       item_val=var_name)
        if debug:
            dd = mg.DATADETS_OBJ
            print(var_name)
            pprint.pprint(dd.flds)
        updated = set_var_props(choice_item, var_name, var_label,
                                self.var_labels, self.var_notes, self.var_types, 
                                self.val_dics)
        if updated:
            event.Skip()
            self.setup_vars()
            self.updated.add(True)
        event.Skip()
        self.lst_vars.DeselectAll()
    
    def on_ok(self, event):
        self.Destroy()
    
    def setup_vars(self):
        """
        Sets up list of variables ensuring using latest details.
        Leaves list unselected.  That way we can select something more than 
            once.
        """
        var_names = get_approp_var_names()
        var_choices, self.sorted_var_names = lib.get_sorted_choice_items(
                                    dic_labels=self.var_labels, vals=var_names)
        self.lst_vars.SetItems(var_choices)

    def get_var(self):
        idx = self.lst_vars.GetSelection()
        if idx == -1:
            raise Exception(u"Nothing selected")
        var = self.sorted_var_names[idx]
        var_item = self.lst_vars.GetStringSelection()
        return var, var_item
    
    
class GetSettings(settings_grid.SettingsEntryDlg):
    
    def __init__(self, title, boltext, boldatetime, var_desc, 
                 init_settings_data, settings_data, val_type):
        """
        var_desc - dic with keys "label", "notes", and "type".
        init_settings_data - list of tuples (must have at least one item, even 
            if only a "rename me").
        col_dets - See under settings_grid.SettingsEntry
        settings_data - add details to it in form of a list of tuples.
        """
        col_dets = [{"col_label": _("Value"), "coltype": val_type, 
                     "colwidth": 50}, 
                    {"col_label": _("Label"), "coltype": settings_grid.COL_STR, 
                     "colwidth": 200},
                     ]
        grid_size = (250, 250)
        wx.Dialog.__init__(self, None, title=title,
                          size=(500,400), pos=(mg.HORIZ_OFFSET+150,100),
                          style=wx.RESIZE_BORDER|wx.CAPTION|wx.CLOSE_BOX|\
                            wx.SYSTEM_MENU)
        self.panel = wx.Panel(self)
        self.Bind(wx.EVT_CLOSE, self.on_ok)
        self.var_desc = var_desc
        # New controls
        lbl_var_label = wx.StaticText(self.panel, -1, _("Variable Label:"))
        lbl_var_label.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        lbl_var_notes = wx.StaticText(self.panel, -1, "Notes:")
        lbl_var_notes.SetFont(font=wx.Font(11, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.txt_var_label = wx.TextCtrl(self.panel, -1, self.var_desc["label"], 
                                         size=(250,-1))
        self.txt_var_notes = wx.TextCtrl(self.panel, -1, self.var_desc["notes"],
                                         style=wx.TE_MULTILINE)
        self.rad_data_type = wx.RadioBox(self.panel, -1, _("Data Type"),
                                       choices=mg.VAR_TYPES)
        self.rad_data_type.SetStringSelection(self.var_desc["type"])
        # if text or datetime, only enable categorical.
        # datetime cannot be quant (if a measurement of seconds etc would be 
        # numeric instead) and although ordinal, not used like that in any of 
        # these tests.
        if boltext or boldatetime:
            self.rad_data_type.EnableItem(mg.VAR_IDX_ORD, False)
            self.rad_data_type.EnableItem(mg.VAR_IDX_QUANT, False)
        btn_type_help = wx.Button(self.panel, wx.ID_HELP)
        btn_type_help.Bind(wx.EVT_BUTTON, self.on_type_help_btn)
        # sizers
        self.szr_main = wx.BoxSizer(wx.VERTICAL)
        self.szr_var_label = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_var_label.Add(lbl_var_label, 0, wx.RIGHT, 5)
        self.szr_var_label.Add(self.txt_var_label, 1)
        self.szr_var_notes = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_var_notes.Add(lbl_var_notes, 0, wx.RIGHT, 5)
        self.szr_var_notes.Add(self.txt_var_notes, 1, wx.GROW)
        self.szr_main.Add(self.szr_var_label, 0, wx.GROW|wx.ALL, 10)
        self.szr_main.Add(self.szr_var_notes, 1, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        self.szr_main.Add(self.rad_data_type, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        szr_data_type = wx.BoxSizer(wx.HORIZONTAL)
        szr_data_type.Add(self.rad_data_type, 0)  
        szr_data_type.Add(btn_type_help, 0, wx.LEFT|wx.TOP, 10)        
        self.szr_main.Add(szr_data_type, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        self.tabentry = settings_grid.SettingsEntry(self, self.panel, False, 
                                        grid_size, col_dets, init_settings_data, 
                                        settings_data)
        self.szr_main.Add(self.tabentry.grid, 2, wx.GROW|wx.ALL, 5)
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
        self.var_desc["label"] = lib.fix_eols(self.txt_var_label.GetValue())
        self.var_desc["notes"] = lib.fix_eols(self.txt_var_notes.GetValue())
        self.var_desc["type"] = self.rad_data_type.GetStringSelection()
        self.tabentry.update_settings_data() # eol-safe already
        self.Destroy()
        self.SetReturnCode(wx.ID_OK)


class ProjectDlg(wx.Dialog, config_output.ConfigUI):
    def __init__(self, parent, readonly=False, fil_proj=None):
        config_output.ConfigUI.__init__(self, autoupdate=False)
        self.can_run_report = False
        if mg.MAX_WIDTH <= 1024:
            mywidth = 976
        else:
            mywidth = 1024
        if mg.MAX_HEIGHT <= 620:
            myheight = 576
        elif mg.MAX_HEIGHT <= 870:
            myheight = mg.MAX_HEIGHT - 70
        else:
            myheight = 800
        wx.Dialog.__init__(self, parent=parent, title=_("Project Settings"),
               size=(mywidth, myheight), 
               style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|wx.RESIZE_BORDER|\
               wx.SYSTEM_MENU|wx.CAPTION|wx.TAB_TRAVERSAL) 
        # wx.CLIP_CHILDREN causes problems in Windows
        self.szr = wx.BoxSizer(wx.VERTICAL)
        self.panel_top = wx.Panel(self)
        self.panel_top.SetBackgroundColour(wx.Colour(205, 217, 215))
        self.scroll_con_dets = wx.PyScrolledWindow(self, 
                                        size=(900, 350), # need for Windows
                                        style=wx.SUNKEN_BORDER|wx.TAB_TRAVERSAL)
        self.scroll_con_dets.SetScrollRate(10,10) # gives it the scroll bars
        self.panel_config = wx.Panel(self)
        self.panel_config.SetBackgroundColour(wx.Colour(205, 217, 215))
        self.panel_bottom = wx.Panel(self)
        self.panel_bottom.SetBackgroundColour(wx.Colour(115, 99, 84))
        self.parent = parent
        self.szr_con_dets = wx.BoxSizer(wx.VERTICAL)
        self.szr_config_outer = wx.BoxSizer(wx.VERTICAL)
        self.szr_bottom = wx.BoxSizer(wx.VERTICAL)
        # get available settings
        self.readonly = readonly
        self.new = (fil_proj is None)
        self.set_defaults(fil_proj)
        self.set_extra_dets(vdt_file=self.fil_var_dets, 
                            script_file=self.script_file) # so opens proj settings
        getdata.set_con_det_defaults(self)
        # misc
        lblfont = wx.Font(9, wx.SWISS, wx.NORMAL, wx.BOLD)
        # Project Name and notes
        lbl_empty = wx.StaticText(self.panel_top, -1, "")
        lbl_name = wx.StaticText(self.panel_top, -1, _("Project Name:"))
        lbl_name.SetFont(lblfont)
        self.txt_name = wx.TextCtrl(self.panel_top, -1, self.proj_name, 
                                   size=(200, -1))
        self.txt_name.Enable(not self.readonly)
        lbl_proj_notes = wx.StaticText(self.panel_top, -1, _("Notes:"))
        lbl_proj_notes.SetFont(lblfont)
        self.txt_proj_notes = wx.TextCtrl(self.panel_top, -1, self.proj_notes,
                                          style=wx.TE_MULTILINE)
        self.txt_proj_notes.Enable(not self.readonly)
        szr_desc = wx.BoxSizer(wx.HORIZONTAL)
        szr_desc_left = wx.BoxSizer(wx.VERTICAL)
        szr_desc_mid = wx.BoxSizer(wx.VERTICAL)
        szr_desc_right = wx.BoxSizer(wx.VERTICAL)
        self.btn_help = wx.Button(self.panel_top, wx.ID_HELP)
        self.btn_help.Bind(wx.EVT_BUTTON, self.on_btn_help)
        #img_ctrl_sofa = wx.StaticBitmap(self.panel_top)
        #img_sofa = wx.Image(os.path.join(mg.SCRIPT_PATH, u"images", 
        #                                u"sofa_left.xpm"), wx.BITMAP_TYPE_XPM)
        #bmp_sofa = wx.BitmapFromImage(img_sofa)
        #img_ctrl_sofa.SetBitmap(bmp_sofa)
        szr_desc_left.Add(lbl_empty, 0, wx.RIGHT, 10)
        szr_desc_left.Add(self.btn_help, 0, wx.RIGHT, 10)
        szr_desc_mid.Add(lbl_name, 0)
        szr_desc_mid.Add(self.txt_name, 0, wx.RIGHT, 10)
        #szr_desc_left.Add(img_ctrl_sofa, 0, wx.TOP, 10)
        szr_desc_right.Add(lbl_proj_notes, 0)
        szr_desc_right.Add(self.txt_proj_notes, 1, wx.GROW)
        szr_desc.Add(szr_desc_left, 0)
        szr_desc.Add(szr_desc_mid)
        szr_desc.Add(szr_desc_right, 1, wx.GROW)
        # DATA CONNECTIONS
        lbl_data_con_dets = wx.StaticText(self.panel_top, -1, 
                                        _("How to connect to my data:"))
        lbl_data_con_dets.SetFont(lblfont)
        # default dbe
        lbl_default_dbe = wx.StaticText(self.scroll_con_dets, -1, 
                                       _("Default Database Engine:"))
        lbl_default_dbe.SetFont(lblfont)
        self.drop_default_dbe = wx.Choice(self.scroll_con_dets, -1, 
                                         choices=mg.DBES)
        sel_dbe_id = mg.DBES.index(self.default_dbe)
        self.drop_default_dbe.SetSelection(sel_dbe_id)
        self.drop_default_dbe.Bind(wx.EVT_CHOICE, self.on_dbe_choice)
        self.drop_default_dbe.Enable(not self.readonly)
        lbl_scroll_down = wx.StaticText(self.scroll_con_dets, -1, 
                    _("(scroll down for details of all your database engines)"))
        # default dbe
        szr_default_dbe = wx.BoxSizer(wx.HORIZONTAL)
        szr_default_dbe.Add(lbl_default_dbe, 0, wx.LEFT|wx.RIGHT, 5)
        szr_default_dbe.Add(self.drop_default_dbe, 0)
        szr_default_dbe.Add(lbl_scroll_down, 0, wx.LEFT, 10)
        # Close
        self.setup_btns()
        # sizers
        # TOP
        self.szr_top = wx.BoxSizer(wx.VERTICAL)
        self.szr_top.Add(szr_desc, 1, wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP, 10)
        #self.szr_top.Add(szrOutput, 0, wx.GROW|wx.ALL, 10)
        self.szr_top.Add(lbl_data_con_dets, 0, wx.GROW|wx.LEFT|wx.BOTTOM, 10)
        self.panel_top.SetSizer(self.szr_top)
        self.szr_top.SetSizeHints(self.panel_top)
        # CON DETS
        self.szr_con_dets.Add(szr_default_dbe, 0, wx.LEFT|wx.RIGHT|wx.TOP, 10)
        getdata.set_data_con_gui(parent=self, readonly=self.readonly, 
                                 scroll=self.scroll_con_dets, 
                                 szr=self.szr_con_dets, lblfont=lblfont)
        self.scroll_con_dets.SetSizer(self.szr_con_dets)
        # NEVER SetSizeHints or else grows beyond size!!!!
        self.szr_con_dets.SetVirtualSizeHints(self.scroll_con_dets)
        # CONFIG
        # mixin supplying self.szr_config
        self.szr_config = self.get_config_szr(self.panel_config, 
                                              readonly=self.readonly, 
                                              report_file=self.fil_report,
                                              css_file=self.fil_css)
        self.szr_config_outer.Add(self.szr_config, 0, wx.GROW|wx.ALL, 10)
        self.panel_config.SetSizer(self.szr_config_outer)
        self.szr_config_outer.SetSizeHints(self.panel_config)
        # BOTTOM
        self.szr_bottom.Add(self.szr_btns, 0, wx.GROW|wx.ALL|wx.ALIGN_RIGHT, 10)
        self.panel_bottom.SetSizer(self.szr_bottom)
        self.szr_bottom.SetSizeHints(self.panel_bottom)
        # FINAL # NB any ratio changes must work in multiple OSs
        self.szr.Add(self.panel_top, 0, wx.GROW)
        self.szr.Add(self.scroll_con_dets, 3, 
                     wx.GROW|wx.LEFT|wx.BOTTOM|wx.RIGHT, 10)
        self.szr.Add(self.panel_config, 0, wx.GROW)
        self.szr.Add(self.panel_bottom, 0, wx.GROW)
        self.SetAutoLayout(True)
        self.SetSizer(self.szr)
        self.SetMinSize((930,550))
        self.Layout()
        self.sqlite_grid.grid.SetFocus()
        self.txt_name.SetFocus()
    
    def set_defaults(self, fil_proj):
        """
        If a proj file, grabs default settings from there and stores as 
            attributes of dialog via get_proj_settings().
        """
        if fil_proj:
            self.new_proj = False
            self.get_proj_settings(fil_proj)
        else:
            # prepopulate with default settings
            self.get_proj_settings(fil_proj=mg.DEFAULT_PROJ)
            self.proj_name = mg.EMPTY_PROJ_NAME
            self.proj_notes = _("The internal sofa_db is added by default. It "
                u"is needed to allow you to add new tables to SOFA Statistics")
            self.new_proj = True
        try:
            self.proj_name
        except AttributeError:
            self.proj_name = mg.EMPTY_PROJ_NAME
        try:
            self.proj_notes
        except AttributeError:
            self.proj_notes = u""
        try:
            self.fil_var_dets
        except AttributeError:
            # make empty labels file if necessary
            fil_default_var_dets = os.path.join(mg.LOCAL_PATH, mg.VDTS_FOLDER, 
                                                mg.DEFAULT_VDTS)
            if not os.path.exists(fil_default_var_dets):
                f = codecs.open(fil_default_var_dets, "w", "utf-8")
                f.write(u"# add variable details here")
                f.close()
            self.fil_var_dets = fil_default_var_dets
        try:            
            self.fil_css
        except AttributeError:
            self.fil_css = os.path.join(mg.LOCAL_PATH, mg.CSS_FOLDER, 
                                        mg.DEFAULT_STYLE)
        try:            
            self.fil_report
        except AttributeError:
            self.fil_report = os.path.join(mg.REPORTS_PATH, mg.DEFAULT_REPORT)
        try:            
            self.fil_script
        except AttributeError:
            self.fil_script = os.path.join(mg.LOCAL_PATH, mg.SCRIPTS_FOLDER, 
                                           mg.DEFAULT_SCRIPT)
        try:
            self.default_dbe
        except AttributeError:
            self.default_dbe = os.path.join(mg.DBE_SQLITE)
        
    def get_proj_settings(self, fil_proj):
        """
        NB get any paths in form ready to display
        """
        proj_path = os.path.join(mg.LOCAL_PATH, mg.PROJS_FOLDER, fil_proj)
        f = codecs.open(proj_path, "U", encoding="utf-8")
        proj_txt = lib.get_exec_ready_text(text=f.read())
        f.close()
        proj_cont = lib.clean_bom_utf8(proj_txt)
        proj_dic = {}
        try:
            exec proj_cont in proj_dic
        except SyntaxError, e:
            wx.MessageBox(\
                _(u"Syntax error in project file \"%(fil_proj)s\"."
                  u"\n\nDetails: %(err)s") % {u"fil_proj": fil_proj,
                                              u"err": lib.ue(e)})
            raise
        except Exception, e:
            wx.MessageBox(\
                _(u"Error processing project file \"%(fil_proj)s\"."
                  u"\n\nDetails: %(err)s") % {u"fil_proj": fil_proj,
                                              u"err": lib.ue(e)})
            raise
        try:
            self.proj_name = fil_proj[:-5]
        except Exception, e:
            wx.MessageBox(_("Please check %(fil_proj)s for errors. "
                            "Use %(def_proj)s for reference.") % 
                            {u"fil_proj": fil_proj, 
                             u"def_proj": mg.DEFAULT_PROJ})
            raise
        # Taking settings from proj file (via exec and proj_dic)
        #   and adding them to this frame ready for use.
        # Must always be stored, even if only ""
        try:
            self.proj_notes = get_proj_notes(fil_proj, proj_dic)
            self.fil_var_dets = proj_dic[mg.PROJ_FIL_VDTS]
            self.fil_css = proj_dic[mg.PROJ_FIL_CSS]
            self.fil_report = proj_dic[mg.PROJ_FIL_RPT]
            self.fil_script = proj_dic[mg.PROJ_FIL_SCRIPT]
            self.default_dbe = proj_dic[mg.PROJ_DBE]
            getdata.get_proj_con_settings(self, proj_dic)
        except KeyError, e:
            wx.MessageBox(_("Please check %(fil_proj)s for errors. "
                            "Use %(def_proj)s for reference.") % 
                            {u"fil_proj": fil_proj, 
                             u"def_proj": mg.DEFAULT_PROJ})
            raise Exception(u"Key error reading from proj_dic."
                            u"\nCaused by error: %s" % lib.ue(e))
        except Exception, e:
            wx.MessageBox(_("Please check %(fil_proj)s for errors. "
                            "Use %(def_proj)s for reference.") % 
                            {u"fil_proj": fil_proj, 
                             u"def_proj": mg.DEFAULT_PROJ})
            raise
    
    def on_dbe_choice(self, event):
        sel_dbe_id = self.drop_default_dbe.GetSelection()
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
            btn_cancel = wx.Button(self.panel_bottom, wx.ID_CANCEL)
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

    def on_btn_config(self, event):
        ret_dic = config_output.ConfigUI.on_btn_config(self, event)
        self.vdt_file = ret_dic[mg.VDT_RET]
        if mg.ADVANCED:
            self.script_file = ret_dic[mg.SCRIPT_RET]
        self.set_extra_dets(vdt_file=self.vdt_file, 
                            script_file=self.script_file) # so opens proj 
            # settings with these same settings even if not saved yet.

    def on_btn_help(self, event):
        """
        Export script if enough data to create table.
        """
        import webbrowser
        url = (u"http://www.sofastatistics.com/wiki/doku.php"
               u"?id=help:projects")
        webbrowser.open_new_tab(url)
        event.Skip()
    
    def on_delete(self, event):
        proj_name = self.txt_name.GetValue()
        if wx.MessageBox(_("Deleting a project cannot be undone. Do you want "
                           "to delete the \"%s\" project?") % proj_name, 
                style=wx.YES|wx.NO|wx.ICON_EXCLAMATION|wx.NO_DEFAULT) == wx.NO:
            return
        try:
            fil_to_delete = os.path.join(mg.LOCAL_PATH, mg.PROJS_FOLDER, 
                                   "%s.proj" % self.txt_name.GetValue())
            #print(fil_to_delete) # debug
            os.remove(fil_to_delete)
        except Exception:
            raise Exception("Unable to delete selected project.")
        self.Destroy()
        self.SetReturnCode(wx.ID_DELETE) # only for dialogs 
        # (MUST come after Destroy)

    def on_cancel(self, event):
        "Close returning us to wherever we came from"
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL) # only for dialogs 
        # (MUST come after Destroy)
       
    def on_ok(self, event):
        """
        If not read-only, writes settings to proj file.
        Name, notes and report are all taken from the text in the text boxes.
        """
        # get the data (separated for easier debugging)
        proj_name = self.txt_name.GetValue()
        if self.readonly:
            self.parent.store_proj_name(u"%s.proj" % proj_name)
        else:
            if proj_name == mg.EMPTY_PROJ_NAME:
                wx.MessageBox(_("Please provide a project name"))
                self.txt_name.SetFocus()
                return
            elif proj_name == mg.DEFAULT_PROJ[:-5]:
                wx.MessageBox(_("You cannot use the default project name"))
                self.txt_name.SetFocus()
                return
            try:
                self.parent.store_proj_name(u"%s.proj" % proj_name)
            except Exception:
                print(u"Failed to change to %s.proj" % proj_name)
                my_exceptions.DoNothingException("Only needed if returning to "
                                    "projselect form so OK to fail otherwise.")
            proj_notes = self.txt_proj_notes.GetValue()
            fil_var_dets = self.vdt_file
            fil_script = self.script_file if self.script_file else u""
            style = self.drop_style.GetStringSelection()
            fil_css = config_output.style2path(style)
            fil_report = self.txt_report_file.GetValue()
            default_dbe = mg.DBES[self.drop_default_dbe.GetSelection()]
            default_dbs = {}
            default_tbls = {}
            con_dets = {}
            (any_incomplete, any_cons, 
             completed_dbes) = getdata.process_con_dets(self, default_dbs, 
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
            fil_name = os.path.join(mg.LOCAL_PATH, mg.PROJS_FOLDER, u"%s.proj" 
                                    % proj_name)
            # In Windows, MySQL.proj and mysql.proj are the same in the file 
            # system - if already a file with same name, delete it first
            # otherwise will write to mysql.proj when saving MySQL.proj.
            # And MySQL won't appear in list on return to projselect.
            if mg.PLATFORM == mg.WINDOWS and os.path.exists(fil_name):
                os.remove(fil_name)
            try:
                f = codecs.open(fil_name, "w", encoding="utf-8")
            except IOError, e:
                wx.MessageBox(_(u"Unable to save project file. Please check "
                                u"\"%(fil_name)s\" is a valid file name."
                                u"\n\nCaused by error: %(err)s")
                                % {u"fil_name": fil_name, 
                                   u"err": lib.ue(e)})
                return
            f.write(u"# Windows file paths _must_ have double not single "
                    u"backslashes")
            f.write(u"\n# All file paths _must_ have a u before the"
                    u" quote-enclosed string")
            f.write(u"""\n# u"C:\\\\Users\\\\demo.txt" is GOOD""")
            f.write(u"""\n# u"C:\\Users\\demo.txt" is BAD""")
            f.write(u"""\n# "C:\\\\Users\\\\demo.txt" is also BAD""")
            f.write(u"\n\nproj_notes = u\"\"\"%s\"\"\"" %
                    lib.escape_pre_write(proj_notes))
            f.write(u"\n\nfil_var_dets = u\"%s\"" % 
                    lib.escape_pre_write(fil_var_dets))
            f.write(u"\nfil_css = u\"%s\"" % \
                    lib.escape_pre_write(fil_css))
            f.write(u"\nfil_report = u\"%s\"" % 
                    lib.escape_pre_write(fil_report))
            f.write(u"\nfil_script = u\"%s\"" % 
                    lib.escape_pre_write(fil_script))
            f.write(u"\ndefault_dbe = u\"%s\"" % default_dbe)
            f.write(u"\n\ndefault_dbs = " + 
                    lib.escape_pre_write(lib.dic2unicode(default_dbs)))
            f.write(u"\n\ndefault_tbls = " + 
                    lib.escape_pre_write(lib.dic2unicode(default_tbls)))
            f.write(u"\n\ncon_dets = " + 
                    lib.escape_pre_write(lib.dic2unicode(con_dets)))
            f.close()
            self.parent.parent.set_proj_lbl(proj_name)
        self.Destroy()
        self.SetReturnCode(wx.ID_OK) # only for dialogs
        # (MUST come after Destroy)        
        