"""
Misc centralised gui elements that aren't in config_ui. Prevents a multitude of
potential circular import problems.
"""

from pathlib import Path
import pprint
import wx

from . import my_globals as mg
from . import lib
from . import projects
from . import settings_grid

debug = False
PRETEND_IS_MAC = debug
IS_MAC = ((mg.PLATFORM != mg.MAC) if PRETEND_IS_MAC
    else (mg.PLATFORM == mg.MAC))

label_divider = ' ' if mg.PLATFORM == mg.WINDOWS else '\n'
ADD2_RPT_LBL = _("Also add%sto report") % label_divider
RUN_LBL = _('Show Results')

def add_icon(frame):
    """
    Probably best to add largest first:
    http://stackoverflow.com/questions/525329/embedding-icon-in-exe-with-py2exe-visible-in-vista/6198910#6198910
    """
    ib = wx.IconBundle()
    for sz in (128, 64, 48, 32, 16):
        icon_path = str(Path(mg.SCRIPT_PATH) / 'images' / f'sofastats_{sz}.xpm')
        ib.AddIcon(icon_path, wx.BITMAP_TYPE_XPM)
    frame.SetIcons(ib)


class GetSettings(settings_grid.DlgSettingsEntry):
    
    def __init__(self,
            title, var_desc, init_settings_data, settings_data, val_type, *,
            boltext, boldatetime):
        """
        var_desc - dic with keys "label", "notes", and "type".

        init_settings_data - list of tuples (must have at least one item, even
        if only a "rename me").

        col_dets - See under settings_grid.SettingsEntry

        settings_data - add details to it in form of a list of tuples.
        """
        col_dets = [
            {'col_label': _('Value'), 'coltype': val_type, 'colwidth': 50},
            {'col_label': _('Label'), 'coltype': settings_grid.COL_STR, 'colwidth': 200},
        ]
        grid_size = (250, 250)
        wx.Dialog.__init__(self, None, title=title, size=(500,400),
            pos=(mg.HORIZ_OFFSET+150,100),
            style=wx.RESIZE_BORDER|wx.CAPTION|wx.CLOSE_BOX|wx.SYSTEM_MENU)
        self.panel = wx.Panel(self)
        self.Bind(wx.EVT_CLOSE, self.on_ok)
        self.var_desc = var_desc
        ## New controls
        lbl_var_label = wx.StaticText(self.panel, -1, _('Variable Label:'))
        lbl_var_label.SetFont(mg.LABEL_FONT)
        lbl_var_notes = wx.StaticText(self.panel, -1, 'Notes:')
        lbl_var_notes.SetFont(mg.LABEL_FONT)
        self.txt_var_label = wx.TextCtrl(
            self.panel, -1, self.var_desc['label'], size=(250,-1))
        self.txt_var_notes = wx.TextCtrl(
            self.panel, -1, self.var_desc['notes'], style=wx.TE_MULTILINE)
        self.rad_data_type = wx.RadioBox(
            self.panel, -1, _('Data Type'), choices=mg.VAR_TYPE_LBLS)
        self.rad_data_type.SetStringSelection(
            mg.VAR_TYPE_KEY2LBL[self.var_desc['type']])
        ## if text or datetime, only enable categorical.
        ## datetime cannot be quant (if a measurement of seconds etc would be
        ## numeric instead) and although ordinal, not used like that in any of
        ## these tests.
        if boltext or boldatetime:
            self.rad_data_type.EnableItem(mg.VAR_IDX_ORD, False)
            self.rad_data_type.EnableItem(mg.VAR_IDX_QUANT, False)
        btn_type_help = wx.Button(self.panel, wx.ID_HELP)
        btn_type_help.Bind(wx.EVT_BUTTON, self.on_type_help_btn)
        ## sizers
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
        self.tabentry = settings_grid.SettingsEntry(self,
            self.panel, grid_size, col_dets,
            init_settings_data, settings_data,
            read_only=False, force_focus=False)
        self.szr_main.Add(self.tabentry.grid, 2, wx.GROW|wx.ALL, 5)
        self.setup_btns(read_only=False)
        self.szr_main.Add(self.szr_btns, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(self.szr_main)
        self.szr_main.SetSizeHints(self)
        self.Layout()
        self.tabentry.grid.SetFocus()

    def on_type_help_btn(self, _event):
        wx.MessageBox(_('Nominal data (names only) is just labels or names. '
            'Ordinal data has a sense of order but no amount, '
            'and Quantity data has actual amount e.g. 2 is twice 1.'
            '\n\n* Example of Nominal (names only) data: sports codes ('
            "'Soccer', 'Badminton', 'Skiing' etc)."
            '\n\n* Example of Ordinal (ranked) data: ratings of restaurant '
            'service standards (1 - Very Poor, 2 - Poor, 3 - Average etc).'
            '\n\n* Example of Quantity (amount) data: height in cm.'
            '\n\nDatetime data is ordinal (ordered) of course, but SOFA treats '
            "it as categorical because it isn't generally used in statistical "
            'tests as ordinal data.'))

    def on_ok(self, _event):
        """
        Override so we can extend to include variable label, type, and notes.
        """
        self.var_desc['label'] = lib.fix_eols(self.txt_var_label.GetValue())
        self.var_desc['notes'] = lib.fix_eols(self.txt_var_notes.GetValue())
        self.var_desc['type'] = mg.VAR_TYPE_LBL2KEY[
            self.rad_data_type.GetStringSelection()]
        self.tabentry.update_settings_data()  ## eol-safe already
        self.Destroy()
        self.SetReturnCode(wx.ID_OK)


def set_var_props(choice_item,
        var_name, var_label, var_labels, var_notes, var_types, val_dics):
    """
    For selected variable (name) gives user ability to set properties e.g.
    value labels. Then stores in appropriate labels file.

    Returns True if user clicks OK to properties (presumably modified).
    """
    dd = mg.DATADETS_OBJ
    ## get val_dic for variable (if any) and display in editable list
    settings_data = []  ## get settings_data back updated
    bolnumeric = dd.flds[var_name][mg.FLD_BOLNUMERIC]
    boldecimal = dd.flds[var_name][mg.FLD_DECPTS]
    boldatetime = dd.flds[var_name][mg.FLD_BOLDATETIME]
    boltext = dd.flds[var_name][mg.FLD_BOLTEXT]
    init_settings_data, msg = projects.get_init_settings_data(
        val_dics, var_name, bolnumeric)
    if msg: wx.MessageBox(msg)
    if bolnumeric:
        if boldecimal or dd.dbe == mg.DBE_SQLITE:  ## could be int or float so have to allow the more inclusive.
            val_type = settings_grid.COL_FLOAT
        else:
            val_type = settings_grid.COL_INT
    else:
        val_type = settings_grid.COL_STR
    title = _('Settings for %s') % choice_item
    notes = var_notes.get(var_name, '')
    ## if nothing recorded, choose useful default variable type
    if bolnumeric:
        def_type = mg.VAR_TYPE_QUANT_KEY  ## have to trust the user somewhat!
    elif boldatetime:
        def_type = mg.VAR_TYPE_CAT_KEY  ## see notes when enabling under GetSettings
    else:
        def_type = mg.VAR_TYPE_CAT_KEY
    var_type = var_types.get(var_name, def_type)
    if var_type not in mg.VAR_TYPE_KEYS:  ## can remove this in late 2020 ;-) - break stuff then to clean the code up? 
        var_type = mg.VAR_TYPE_LBL2KEY.get(var_type, def_type)
    var_desc = {'label': var_label, 'notes': notes, 'type': var_type}
    getsettings = GetSettings(title, var_desc,
        init_settings_data, settings_data, val_type,
        boltext=boltext, boldatetime=boldatetime)
    ret = getsettings.ShowModal()
    if ret == wx.ID_OK:
        if var_desc['label'].strip():
            var_labels[var_name] = var_desc['label']
        else:
            try:  ## otherwise uses empty string as label which can't be seen ;-). Better to act as if has no label at all.
                del var_labels[var_name]
            except KeyError:
                pass
        var_notes[var_name] = var_desc['notes']
        var_types[var_name] = var_desc['type']
        projects.update_val_labels(
            val_dics, var_name, val_type, keyvals=settings_data)
        projects.update_vdt(var_labels, var_notes, var_types, val_dics)
        return True
    else:
        return False


class DlgListVars(wx.Dialog):
    def __init__(self, var_labels, var_notes, var_types, val_dics, updated):
        "updated -- empty set - add True to 'return' updated True"
        wx.Dialog.__init__(self, None, title=_('Variable Details'),
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
        except Exception:  ## seems to be triggered on exit
            if debug: print('Clicked badly')
            event.Skip()
            return
        var_label = lib.GuiLib.get_item_label(
            item_labels=self.var_labels, item_val=var_name)
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
    
    def on_ok(self, _event):
        self.Destroy()
    
    def setup_vars(self):
        """
        Sets up list of variables ensuring using latest details.

        Leaves list unselected.  That way we can select something more than once
        """
        vals = projects.get_approp_var_names()
        dic_labels = self.var_labels
        (var_choices,
         self.sorted_var_names) = lib.GuiLib.get_sorted_choice_items(
             dic_labels, vals)
        self.lst_vars.SetItems(var_choices)

    def get_var(self):
        idx = self.lst_vars.GetSelection()
        if idx == -1:
            raise Exception('Nothing selected')
        var = self.sorted_var_names[idx]
        var_item = self.lst_vars.GetStringSelection()
        return var, var_item
