#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import datetime
import os

import wx
import zipfile

import my_globals as mg

"""
If not available, make backup subfolder.

Make date-time stamped zip file and include in it all vdts, projs, sofa_db and, 
optionally, reports.

Do not include default_report_extras.
"""

BACKUP_FOLDER = "backups"

def run_backup(inc_reports=True):
    debug = False
    report2gui = False
    backup_folder = os.path.join(mg.LOCAL_PATH, BACKUP_FOLDER)
    try:
        os.mkdir(backup_folder)
    except OSError:
        pass
    now = datetime.datetime.now().isoformat()
    ts = u"-".join(now.split(u":")[:-1])
    backup_filname = u"sofa_backup_%s.zip" % ts
    backup_path = os.path.join(backup_folder, backup_filname)
    # http://www.doughellmann.com/PyMOTW/zipfile/
    zf = zipfile.ZipFile(backup_path, mode='w', 
        compression=zipfile.ZIP_DEFLATED)
    folders2backup = [mg.PROJS_FOLDER, mg.VDTS_FOLDER]
    if inc_reports:
        folders2backup.append(mg.REPORTS_FOLDER)
    files2backup = []
    files2backup.append(os.path.join(mg.INT_PATH, mg.SOFA_DB))
    for folder in folders2backup:
        folder_path = os.path.join(mg.LOCAL_PATH, folder)
        for root, unused, files in os.walk(folder_path):
            if debug: 
                print(root)
                if report2gui:
                    wx.MessageBox(u"Current root is: %s" % root)
            if root == mg.REPORT_EXTRAS_PATH:
                continue
            for filname in files:
                filpath = os.path.join(folder_path, root, filname)
                files2backup.append(filpath)
    for filpath in files2backup:
        if debug: 
            print("Adding %s ..." % filpath)
            if report2gui:
                wx.MessageBox(u"File path is: %s" % filpath)
        zf.write(filpath)
    zf.close()
    if debug: print("Closed zip file")
    msg = (u"Backed up %s files to:\n\"%s\"\n\nYou'll find it in your \"%s\" "
        u"folder.\n\nTIP: copy your backups to a USB stick and keep it "
        u"off-site." % (len(files2backup), backup_filname, backup_folder))
    return msg
