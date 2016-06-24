#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Note -- enable images saved to be in high resolution for publishing purposes.
Warn users it will take longer (give an estimate) and show progress on a bar.
"""
import datetime
import os

import wx

import basic_lib as b
import my_globals as mg
import lib
import my_exceptions
import export_output
import export_output_images
import export_output_pdfs
import export_output_spreadsheets

PDF_ITEM_TAKES = 4
TBL_ITEM_TAKES = 1

def get_start_and_steps(n_pdfs, n_imgs, output_dpi, n_tbls):
    """
    Where should we start on the progress gauge and how much should each item 
    move us along?
    
    Start by have a basic concept of the relativities for pdf vs images vs 
    tables, and knowing how many items of each sort there are.
    """
    pdf_taken = (n_pdfs*PDF_ITEM_TAKES)
    output_dpi2takes = {72: 1, 150: 2, 300: 4, 600: 10, 1200: 30}
    IMG_ITEM_TAKES = output_dpi2takes[output_dpi]
    imgs_taken = (n_imgs*IMG_ITEM_TAKES)
    tbls_taken = (n_tbls*TBL_ITEM_TAKES)
    tot_taken = pdf_taken + imgs_taken + tbls_taken
    if tot_taken == 0:
        raise Exception(u"Unable to get start and steps - zero items to show "
            u"progress for.")
    pdf_as_prop = pdf_taken/float(tot_taken)
    imgs_as_prop = imgs_taken/float(tot_taken)
    tbls_as_prop = tbls_taken/float(tot_taken)
    steps_for_pdf = mg.EXPORT_IMG_GAUGE_STEPS*pdf_as_prop
    steps_for_imgs = mg.EXPORT_IMG_GAUGE_STEPS*imgs_as_prop
    steps_for_tbls =  mg.EXPORT_IMG_GAUGE_STEPS*tbls_as_prop
    if n_pdfs == 0:
        steps_per_pdf_item = 0 # doesn't matter - should not be used if no items
    else:
        steps_per_pdf_item = steps_for_pdf/float(n_pdfs)
    if n_imgs == 0:
        steps_per_img_item = 0
    else:
        steps_per_img_item = steps_for_imgs/float(n_imgs)
    if n_tbls == 0:
        steps_per_tbl_item = 0
    else:
        steps_per_tbl_item = steps_for_tbls/float(n_tbls)
    gauge_start_pdf = 0
    gauge_start_imgs = steps_for_pdf
    gauge_start_tbls = steps_for_pdf + steps_for_imgs
    return (gauge_start_pdf, steps_per_pdf_item, gauge_start_imgs, 
        steps_per_img_item, gauge_start_tbls, steps_per_tbl_item)


class DlgExportOutput(wx.Dialog):
    
    def __init__(self, title, report_path, save2report_path=True):
        """
        save2report_path -- output goes into the report folder. If False, 
        exporting output to a temporary desktop folder for the user to look at. 
        """
        wx.Dialog.__init__(self, parent=None, id=-1, title=title, 
            pos=(mg.HORIZ_OFFSET+200, 300), style=wx.MINIMIZE_BOX|
            wx.MAXIMIZE_BOX|wx.RESIZE_BORDER|wx.CLOSE_BOX|wx.SYSTEM_MENU|
            wx.CAPTION|wx.CLIP_CHILDREN)
        self.save2report_path = save2report_path
        if mg.OVERRIDE_FOLDER:
            self.save2report_path = True
        self.report_path = report_path
        szr = wx.BoxSizer(wx.VERTICAL)
        self.export_status = {mg.CANCEL_EXPORT: False} # can change and running script can check on it.
        if self.save2report_path:
            report_name = os.path.split(report_path)[1]
            msg = u"Export \"%s\"" % report_name
        else:
            msg = u"Export content currently displayed in SOFA"
        lbl_msg = wx.StaticText(self, -1, msg)
        szr.Add(lbl_msg, 0, wx.ALL, 10)
        szr_pdf_or_tbls = wx.BoxSizer(wx.VERTICAL)
        szr_left_and_right = wx.BoxSizer(wx.HORIZONTAL)
        self.chk_pdf = wx.CheckBox(self, -1, _("Export as PDF"))
        self.chk_pdf.Bind(wx.EVT_CHECKBOX, self.on_chk_pdf)
        self.chk_tbls = wx.CheckBox(self, -1, _("Export to spreadsheet (report "
            u"tables only)"))
        self.chk_tbls.Bind(wx.EVT_CHECKBOX, self.on_chk_tbls)
        szr_pdf_or_tbls.Add(self.chk_pdf, 0, wx.ALL, 10)
        szr_pdf_or_tbls.Add(self.chk_tbls, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        ln_split = wx.StaticLine(self, style=wx.LI_VERTICAL)
        szr_left_and_right.Add(szr_pdf_or_tbls)
        szr_left_and_right.Add(ln_split, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
        szr_imgs = wx.BoxSizer(wx.VERTICAL)
        self.chk_imgs = wx.CheckBox(self, -1, _("Export as Images"))
        self.chk_imgs.Bind(wx.EVT_CHECKBOX, self.on_chk_imgs)
        self.choice_dpis = [
            (_(u"Draft Quality (%s dpi)") % mg.DRAFT_DPI, mg.DRAFT_DPI), 
            (_(u"Screen Quality (%s dpi)") % mg.SCREEN_DPI, mg.SCREEN_DPI), 
            (_(u"Print Quality (%s dpi)") % mg.PRINT_DPI, mg.PRINT_DPI),
            (_(u"High Quality (%s dpi)") % mg.HIGH_QUAL_DPI, mg.HIGH_QUAL_DPI),
            (_(u"Top Quality (%s dpi)") % mg.TOP_DPI, mg.TOP_DPI),
        ]
        choices = [x[0] for x in self.choice_dpis]
        self.drop_dpi = wx.Choice(self, -1, choices=choices)
        idx_print = 2
        self.drop_dpi.SetSelection(idx_print)
        self.drop_dpi.SetToolTipString(u"The more dots per inch (dpi) the "
            u"higher the quality but the slower the export process.")
        szr_imgs.Add(self.chk_imgs, 0, wx.LEFT|wx.RIGHT|wx.TOP, 10)
        szr_imgs.Add(self.drop_dpi, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        szr_left_and_right.Add(szr_imgs, 0)
        szr.Add(szr_left_and_right, 0) 
        self.btn_cancel = wx.Button(self, wx.ID_CANCEL)
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.on_btn_cancel)
        self.btn_cancel.Enable(False)
        self.btn_export = wx.Button(self, -1, u"Export")
        self.btn_export.Bind(wx.EVT_BUTTON, self.on_btn_export)
        self.btn_export.Enable(False)
        szr_btns = wx.FlexGridSizer(rows=1, cols=2, hgap=5, vgap=0)
        szr_btns.AddGrowableCol(1,2) # idx, propn
        szr_btns.Add(self.btn_cancel, 0)
        szr_btns.Add(self.btn_export, 0, wx.ALIGN_RIGHT)       
        self.progbar = wx.Gauge(self, -1, mg.EXPORT_IMG_GAUGE_STEPS, 
            size=(-1, 20), style=wx.GA_PROGRESSBAR)
        self.btn_close = wx.Button(self, wx.ID_CLOSE)
        self.btn_close.Bind(wx.EVT_BUTTON, self.on_btn_close)
        szr.Add(szr_btns, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        szr.Add(self.progbar, 0, wx.GROW|wx.ALIGN_RIGHT|wx.ALL, 10)
        szr.Add(self.btn_close, 0, wx.ALIGN_RIGHT|wx.ALL, 10)
        self.SetSizer(szr)
        szr.SetSizeHints(self)
        szr.Layout()
    
    def on_btn_export(self, event):
        debug = False
        headless = False
        if mg.EXPORT_IMAGES_DIAGNOSTIC: debug = True
        self.progbar.SetValue(0)
        wx.BeginBusyCursor()
        do_pdf = self.chk_pdf.IsChecked()
        do_imgs = self.chk_imgs.IsChecked()
        do_tbls = self.chk_tbls.IsChecked()
        if not (do_pdf or do_imgs or do_tbls):
            lib.GuiLib.safe_end_cursor()
            self.align_btns_to_exporting(exporting=False)
            wx.MessageBox(u"Please select a format(s) to export in.")
            return
        msgs = []
        hdr, img_items, tbl_items = export_output.get_hdr_and_items(
            self.report_path, mg.EXPORT_IMAGES_DIAGNOSTIC)
        n_imgs = len(img_items)
        n_tbls = len(tbl_items)
        if not (do_pdf or (do_imgs and n_imgs) or (do_tbls and n_tbls)):
            lib.GuiLib.safe_end_cursor()
            self.align_btns_to_exporting(exporting=False)
            wx.MessageBox(u"No output of the selected type(s) to export.")
            return
        self.align_btns_to_exporting(exporting=True)
        if self.save2report_path:
            temp_desktop_path = None
        else:
            # save to folder on desktop
            ts = datetime.datetime.now().strftime('%b %d %I-%M %p').strip()
            foldername = u"SOFA export %s" % ts
            desktop = os.path.join(mg.HOME_PATH, u"Desktop")
            temp_desktop_path = os.path.join(desktop, foldername)
            if debug: print(temp_desktop_path)
            try:
                os.mkdir(temp_desktop_path)
            except OSError:
                pass # already there
        idx_sel = self.drop_dpi.GetSelection()
        idx_dpi = 1
        self.output_dpi = self.choice_dpis[idx_sel][idx_dpi]
        n_pdfs = 1 if do_pdf else 0
        (gauge_start_pdf, steps_per_pdf, 
        gauge_start_imgs, steps_per_img, 
        gauge_start_tbls, steps_per_tbl) = get_start_and_steps(n_pdfs, n_imgs, 
            self.output_dpi, n_tbls)
        if do_pdf:
            try:
                export_output_pdfs.pdf_tasks(self.save2report_path, self.report_path, 
                    temp_desktop_path, headless, gauge_start_pdf, steps_per_pdf, 
                    msgs, self.progbar)
            except Exception, e:
                self.progbar.SetValue(0)
                lib.GuiLib.safe_end_cursor()
                self.align_btns_to_exporting(exporting=False)
                self.export_status[mg.CANCEL_EXPORT] = False
                wx.MessageBox(u"Unable to export PDF. Orig error: %s" % b.ue(e))
                return
        if do_imgs:
            try:
                export_output_images.export2imgs(hdr, img_items, self.save2report_path, 
                    self.report_path, temp_desktop_path, self.output_dpi, 
                    gauge_start_imgs, headless, self.export_status, 
                    steps_per_img, msgs, self.progbar)
            except Exception, e:
                try:
                    raise
                except my_exceptions.ExportCancel:
                    wx.MessageBox(u"Export Cancelled")
                except Exception, e:
                    msg = (u"Problem exporting output. Orig error: %s" % 
                        b.ue(e))
                    if debug: print(msg)
                    wx.MessageBox(msg)
                self.progbar.SetValue(0)
                lib.GuiLib.safe_end_cursor()
                self.align_btns_to_exporting(exporting=False)
                self.export_status[mg.CANCEL_EXPORT] = False
                return
        if do_tbls:
            if n_tbls == 0:
                wx.MessageBox(_(u"No report tables to export to spreadsheet - "
                    u"skipping this task"))
            else:
                try:
                    export_output_spreadsheets.export2spreadsheet(hdr, tbl_items, 
                        self.save2report_path, self.report_path, temp_desktop_path, 
                        gauge_start_tbls, headless, steps_per_tbl, msgs, 
                        self.progbar)
                except Exception, e:
                    try:
                        raise
                    except my_exceptions.ExportCancel:
                        wx.MessageBox(u"Export Cancelled")
                    except Exception, e:
                        msg = (u"Problem exporting output. Orig error: %s" % 
                            b.ue(e))
                        if debug: print(msg)
                        wx.MessageBox(msg)
                    self.progbar.SetValue(0)
                    lib.GuiLib.safe_end_cursor()
                    self.align_btns_to_exporting(exporting=False)
                    self.export_status[mg.CANCEL_EXPORT] = False
                    return
        self.progbar.SetValue(mg.EXPORT_IMG_GAUGE_STEPS)
        lib.GuiLib.safe_end_cursor()
        self.align_btns_to_exporting(exporting=False)
        msg = u"\n\n".join(msgs)
        caption = (_(u"EXPORTED REPORT") if self.save2report_path 
            else _(u"EXPORTED CURRENT OUTPUT"))
        wx.MessageBox(_(u"Exporting completed.\n\n%s") % msg, caption=caption)
        self.progbar.SetValue(0)
    
    def on_chk_pdf(self, event):
        self.align_btns_to_completeness()
        
    def on_chk_imgs(self, event):
        self.align_btns_to_completeness()
        
    def on_chk_tbls(self, event):
        self.align_btns_to_completeness()
    
    def on_btn_cancel(self, event):
        self.export_status[mg.CANCEL_EXPORT] = True

    def align_btns_to_completeness(self):
        do_pdf = self.chk_pdf.IsChecked()
        do_imgs = self.chk_imgs.IsChecked()
        do_tbls = self.chk_tbls.IsChecked()
        complete = (do_pdf or do_imgs or do_tbls)
        self.btn_export.Enable(complete)

    def align_btns_to_exporting(self, exporting):
        self.btn_close.Enable(not exporting)
        self.btn_cancel.Enable(exporting)
        self.btn_export.Enable(not exporting)
    
    def on_btn_close(self, event):
        self.Destroy()
