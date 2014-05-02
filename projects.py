from __future__ import print_function

import codecs
import os
import pprint
import wx

import my_globals as mg
import lib
import output
import settings_grid

BROKEN_VDT_MSG = _(u"This field is numeric, so any non-numeric keys in the "
    u"source vdt file e.g. '1', '1a', 'apple' will be ignored. Did you manually"
    u" edit it or generate your own vdt? Remember 1 or 1.0 is not equal to '1'") 

def valid_proj(subfolder, proj_filname):
    settings_path = os.path.join(mg.LOCAL_PATH, subfolder, proj_filname)
    try:
        with codecs.open(settings_path, "U", encoding="utf-8") as f:
            f.close()
            valid_proj = True
    except IOError:
        valid_proj = False
    return valid_proj

def filname2projname(filname):
    projname = filname[:-len(mg.PROJ_EXT)]
    return projname

def get_projs():
    """
    NB includes .proj at end.
    os.listdir()
    
    Changed in version 2.3: On Windows NT/2k/XP and Unix, if path is a Unicode 
    object, the result will be a list of Unicode objects. Undecodable filenames 
    will still be returned as string objects.
    
    May need unicode results so always provide a unicode path. 
    """
    proj_fils = os.listdir(os.path.join(mg.LOCAL_PATH, mg.PROJS_FOLDER))
    proj_fils = [x for x in proj_fils if x.endswith(mg.PROJ_EXT)]
    proj_fils.sort()
    return proj_fils

def get_hide_db():
    return (len(get_projs()) < 2)

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
    cc = output.get_cc()
    f = codecs.open(cc[mg.CURRENT_VDTS_PATH], "w", encoding="utf-8")
    f.write(u"var_labels=" + lib.dic2unicode(var_labels))
    f.write(u"\n\nvar_notes=" + lib.dic2unicode(var_notes))
    f.write(u"\n\nvar_types=" + lib.dic2unicode(var_types))
    f.write(u"\n\n\nval_dics=" + lib.dic2unicode(val_dics))
    f.close()
    wx.MessageBox(_("Settings saved to \"%s\"") % cc[mg.CURRENT_VDTS_PATH])

def val2sortnum(val):
    try:
        sortnum = float(val)
    except (ValueError, TypeError):
        sortnum = val # will be after the numbers - sort order seems to be None, 1, capital text, lower case text
    return sortnum

def sensible_sort_keys(input_list):
    """
    Sort so None, '1', 2, 3, '4', 11, '12', 'Banana', 'apple'. In practice, the 
    most important bit is the "numbers" being in order like '1', 2, 3, '4', 11, 
    '12'.
    """
    return input_list.sort(key=lambda s: val2sortnum(s[0]))

def get_init_settings_data(val_dics, var_name, bolnumeric):
    """
    Get initial settings to display value labels appropriately.
    
    Needs to handle the following scenarios appropriately:
    
    User has a numeric field. They are only allowed to enter value labels for 
    numeric keys. No problems will ever occur for this user.

    User has a text field. They can enter any text, including numbers 
    e.g. "Apple", "1", "1b" etc. I want these displayed in the correct sort 
    order but still being stored as string. So I want 'apple', 'banana','1','2',
    '3','11','99','100' ... This is necessary because people sometimes import 
    data with a text data type when it really should have been numeric. But they 
    hate it when the labels are '1','11','12','2','3' etc and fair enough. This 
    is a pretty common case.

    User has a numeric field. They have edited the vdt file outside of SOFA e.g. 
    manually, or they have generated it programmatically, and included some 
    non-numeric keys e.g. '1'. Anything that can be converted into a number 
    should be displayed as a number. Anything else should be discarded and the 
    user should be warned that this has happened and why.
    """
    init_settings_data = []
    msg = None
    if val_dics.get(var_name):
        val_dic = val_dics.get(var_name)
        if val_dic:
            if bolnumeric:
                numeric_fld_but_non_numeric_keys = False
                for key, value in val_dic.items():
                    if not isinstance(key, (float, int)): # not going to worry about people wanting to add value labels to complex numbers or scientific notation ;-)
                        numeric_fld_but_non_numeric_keys = True
                    else:
                        init_settings_data.append((key, unicode(value)))
                init_settings_data.sort(key=lambda s: s[0])
                if numeric_fld_but_non_numeric_keys:
                    msg = BROKEN_VDT_MSG
            else:
                for key, value in val_dic.items():
                    init_settings_data.append((key, unicode(value)))
                    sensible_sort_keys(init_settings_data)
    return init_settings_data, msg

def set_var_props(choice_item, var_name, var_label, var_labels, var_notes, 
        var_types, val_dics):
    """
    For selected variable (name) gives user ability to set properties e.g.
    value labels. Then stores in appropriate labels file.
    
    Returns True if user clicks OK to properties (presumably modified).
    """
    dd = mg.DATADETS_OBJ
    # get val_dic for variable (if any) and display in editable list
    settings_data = [] # get settings_data back updated
    bolnumeric = dd.flds[var_name][mg.FLD_BOLNUMERIC]
    boldecimal = dd.flds[var_name][mg.FLD_DECPTS]
    boldatetime = dd.flds[var_name][mg.FLD_BOLDATETIME]
    boltext = dd.flds[var_name][mg.FLD_BOLTEXT]
    init_settings_data, msg = get_init_settings_data(val_dics, var_name, 
        bolnumeric)
    if msg: wx.MessageBox(msg)
    if bolnumeric:
        if boldecimal or dd.dbe == mg.DBE_SQLITE: # could be int or float so have to allow the more inclusive.
            val_type = settings_grid.COL_FLOAT
        else:
            val_type = settings_grid.COL_INT
    else:
        val_type = settings_grid.COL_STR
    title = _("Settings for %s") % choice_item
    notes = var_notes.get(var_name, u"")
    # if nothing recorded, choose useful default variable type
    if bolnumeric:
        def_type = mg.VAR_TYPE_QUANT_KEY # have to trust the user somewhat!
    elif boldatetime:
        def_type = mg.VAR_TYPE_CAT_KEY # see notes when enabling under GetSettings
    else:
        def_type = mg.VAR_TYPE_CAT_KEY
    var_type = var_types.get(var_name, def_type)
    if var_type not in mg.VAR_TYPE_KEYS: # can remove this in late 2020 ;-) - break stuff then to clean the code up? 
        var_type = mg.VAR_TYPE_LBL2KEY.get(var_type, def_type)
    var_desc = {"label": var_label, "notes": notes, "type": var_type}
    getsettings = GetSettings(title, boltext, boldatetime, var_desc, 
        init_settings_data, settings_data, val_type)
    ret = getsettings.ShowModal()
    if ret == wx.ID_OK:
        if var_desc["label"].strip():
            var_labels[var_name] = var_desc["label"]
        else:
            try: # otherwise uses empty string as label which can't be seen ;-). Better to act as if has no label at all.
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
    
def get_approp_var_names(var_types=None, min_data_type=mg.VAR_TYPE_CAT_KEY):
    """
    Get filtered list of variable names according to minimum data type. Use the 
        information on the type of each variable to decide whether meets 
        minimum e.g ordinal.
    """
    debug = False
    dd = mg.DATADETS_OBJ
    if min_data_type == mg.VAR_TYPE_CAT_KEY:
        var_names = [x for x in dd.flds]
    elif min_data_type == mg.VAR_TYPE_ORD_KEY:
        # check for numeric as well in case user has manually 
        # misconfigured var_type in vdts file.
        var_names = [x for x in dd.flds if dd.flds[x][mg.FLD_BOLNUMERIC] and
            var_types.get(x) in (None, mg.VAR_TYPE_ORD_KEY, 
            mg.VAR_TYPE_QUANT_KEY)]
    elif min_data_type == mg.VAR_TYPE_QUANT_KEY:
        # check for numeric as well in case user has manually 
        # misconfigured var_type in vdts file.
        if debug:
            print(dd.flds)
        var_names = [x for x in dd.flds if dd.flds[x][mg.FLD_BOLNUMERIC] and
            var_types.get(x) in (None, mg.VAR_TYPE_QUANT_KEY)]
    else:
        raise Exception(u"get_approp_var_names received a faulty min_data_"
            u"type: %s" % min_data_type)
    return var_names

def get_idx_to_select(choice_items, drop_var, var_labels, default):
    """
    Get index to select. If variable passed in, use that if possible.
    
    It will not be possible if it has been removed from the list e.g. because
    of a user reclassification of data type (e.g. was quantitative but has been 
    redefined as categorical); or because of a change of filtering.
    
    If no variable passed in, or it was but couldn't be used (see above), use 
    the default if possible. If not possible, select the first item.
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
                pass # OK if no default - use idx of 0.
    return idx
    
    
class DlgListVars(wx.Dialog):
    def __init__(self, var_labels, var_notes, var_types, val_dics, updated):
        "updated -- empty set - add True to 'return' updated True"
        wx.Dialog.__init__(self, None, title=_("Variable Details"),
            size=(500,600), style=wx.CAPTION|wx.CLOSE_BOX|wx.SYSTEM_MENU)
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
            self.var_labels, self.var_notes, self.var_types, self.val_dics)
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
        vals = get_approp_var_names()
        dic_labels = self.var_labels
        (var_choices, 
         self.sorted_var_names) = lib.get_sorted_choice_items(dic_labels, vals)
        self.lst_vars.SetItems(var_choices)

    def get_var(self):
        idx = self.lst_vars.GetSelection()
        if idx == -1:
            raise Exception(u"Nothing selected")
        var = self.sorted_var_names[idx]
        var_item = self.lst_vars.GetStringSelection()
        return var, var_item
    
    
class GetSettings(settings_grid.DlgSettingsEntry):
    
    def __init__(self, title, boltext, boldatetime, var_desc, 
            init_settings_data, settings_data, val_type):
        """
        var_desc - dic with keys "label", "notes", and "type".
        
        init_settings_data - list of tuples (must have at least one item, even 
        if only a "rename me").
        
        col_dets - See under settings_grid.SettingsEntry
        
        settings_data - add details to it in form of a list of tuples.
        """
        col_dets = [
            {"col_label": _("Value"), "coltype": val_type, "colwidth": 50}, 
            {"col_label": _("Label"), "coltype": settings_grid.COL_STR, 
            "colwidth": 200},
        ]
        grid_size = (250, 250)
        wx.Dialog.__init__(self, None, title=title, size=(500,400), 
            pos=(mg.HORIZ_OFFSET+150,100), style=wx.RESIZE_BORDER|wx.CAPTION
            |wx.CLOSE_BOX|wx.SYSTEM_MENU)
        self.panel = wx.Panel(self)
        self.Bind(wx.EVT_CLOSE, self.on_ok)
        self.var_desc = var_desc
        # New controls
        lbl_var_label = wx.StaticText(self.panel, -1, _("Variable Label:"))
        lbl_var_label.SetFont(mg.LABEL_FONT)
        lbl_var_notes = wx.StaticText(self.panel, -1, "Notes:")
        lbl_var_notes.SetFont(mg.LABEL_FONT)
        self.txt_var_label = wx.TextCtrl(self.panel, -1, self.var_desc["label"], 
            size=(250,-1))
        self.txt_var_notes = wx.TextCtrl(self.panel, -1, self.var_desc["notes"],
            style=wx.TE_MULTILINE)
        self.rad_data_type = wx.RadioBox(self.panel, -1, _("Data Type"),
            choices=mg.VAR_TYPE_LBLS)
        self.rad_data_type.SetStringSelection(mg.VAR_TYPE_KEY2LBL[
            self.var_desc["type"]])
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
            grid_size, col_dets, init_settings_data, settings_data)
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
        self.var_desc["type"] = mg.VAR_TYPE_LBL2KEY[
            self.rad_data_type.GetStringSelection()]
        self.tabentry.update_settings_data() # eol-safe already
        self.Destroy()
        self.SetReturnCode(wx.ID_OK)
