import os
import pprint
import wx

from sofastats import my_globals as mg
from sofastats import config_ui
from sofastats import config_globals


class DlgPrefs(wx.Dialog):
    def __init__(self, parent, prefs_dic_in):
        """
        prefs_dic_in -- expects a dict, even an empty one. If empty, or with 
            wrong keys, starts fresh and will store what gets selected here if
            user applies changes.
        Explanation level is unusual in that it can get (re)set on most dialogs 
            as well, and the sizer is shared code as well.
        """
        wx.Dialog.__init__(self, parent=parent, title=_("Preferences"), 
            style=wx.CAPTION|wx.SYSTEM_MENU, pos=(mg.HORIZ_OFFSET+100,300))
        if not prefs_dic_in or mg.PREFS_KEY not in prefs_dic_in:
            prefs_dic_in = {mg.PREFS_KEY: {}}
        self.parent = parent
        self.panel = wx.Panel(self)
        self.szr_main = wx.BoxSizer(wx.VERTICAL)
        self.szr_details = config_ui.get_szr_details(self, self.panel)
        self.chk_details.SetValue(mg.DEFAULT_DETAILS)
        self.szr_main.Add(self.szr_details, 0, wx.ALL, 10)
        self.setup_btns()
        self.szr_main.Add(self.szr_std_btns, 0, wx.GROW|wx.ALL, 10)
        self.panel.SetSizer(self.szr_main)
        self.szr_main.SetSizeHints(self)
        self.Layout()
        
    def setup_btns(self):
        """
        Set up standard buttons.
        """
        btn_cancel = wx.Button(self.panel, wx.ID_CANCEL)
        btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        btn_ok = wx.Button(self.panel, wx.ID_OK, _("Apply"))
        btn_ok.Bind(wx.EVT_BUTTON, self.on_ok)
        btn_ok.SetDefault()
        self.szr_std_btns = wx.StdDialogButtonSizer()
        self.szr_std_btns.AddButton(btn_cancel)
        self.szr_std_btns.AddButton(btn_ok)
        self.szr_std_btns.Realize()

    def on_cancel(self, _event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL) # only for dialogs 
        # (MUST come after Destroy)
    
    def on_ok(self, _event):
        # collect prefs.  Do it all from scratch here
        prefs_dic_out = {mg.PREFS_KEY: {}}
        prefs_dic_out[mg.PREFS_KEY][mg.PREFS_DEFAULT_DETAILS_KEY] = \
            self.chk_details.GetValue()
        # create updated prefs file
        prefs_path = os.path.join(mg.INT_PATH, mg.INT_PREFS_FILE)
        f = open(prefs_path, "w", encoding="utf-8")
        prefs_str = pprint.pformat(prefs_dic_out[mg.PREFS_KEY])
        f.write(u"%s = " % mg.PREFS_KEY + prefs_str)
        f.close()
        # misc
        config_globals.set_DEFAULT_DETAILS() # run after prefs file updated.
        self.Destroy()
        self.SetReturnCode(wx.ID_OK) # or nothing happens!  
        # Prebuilt dialogs must do this internally.
        