#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
SOFA BACKUP PLUG-IN
END-USER LICENCE AGREEMENT 
1. IMPORTANT NOTICE
YOU SHOULD READ THE FOLLOWING TERMS AND CONDITIONS CAREFULLY BEFORE YOU DOWNLOAD, INSTALL OR USE PSAL'S PROPRIETARY SOFTWARE IDENTIFIED ABOVE
This End-User Licence Agreement ("EULA") is a legal agreement between you and Paton-Simpson & Associates Limited (“PSAL”) for the PSAL software product(s) identified above together with all Updates thereto, and any and all accompanying documentation, files and materials (the “Plug-In").
By installing, copying, or otherwise using the Plug-In, you agree to be bound by the terms of this EULA. If you do not agree to the terms of this EULA, do not install or use the Plug-In. 
The Plug-In is protected by copyright laws and international copyright treaties, as well as other intellectual property laws and treaties. The Plug-In is licensed, not sold. 
2. GRANT OF LICENCE
The Plug-In is licensed as follows: 
(a) Installation and Use
In consideration of your payment of the licence fee and acceptance of the terms of this EULA, PSAL grants you the right to install and use one copy of the Plug-In on up to three digital processors, computers, or workstations (collectively, “Devices”) which you own or are under your control solely for your personal or internal business use, provided that the Plug-In is used on only one Device at any one time.
(b) Backup Copies
You may also make copies of the Plug-In as may be necessary for backup and archival purposes.
(c) Non-transferable licence
You agree that you will not sub-license, assign, transfer, distribute, pledge, lease, rent or share your rights under this Licence except with prior written permission from PSAL.
3. DESCRIPTION OF OTHER RIGHTS AND LIMITATIONS
(a) Maintenance of Copyright Notices
You must not remove or alter any copyright notices on any and all copies of the Plug-In.
(b) Distribution
You may not distribute copies of the Plug-In to third parties.
(c) Modification
You are permitted to modify the code of the Plug-In for your own use, but not to distribute any such modified code. 
(d) Support Services
PSAL may provide you with support services related to the Plug-In ("Support Services"). Any supplemental software code provided to you as part of the Support Services shall be considered part of the Plug-In and subject to the terms and conditions of this EULA. 
(e) Compliance with Applicable Laws
You must comply with all applicable laws regarding use of the Plug-In.
4. UPDATES
PSAL may provide you with updates, patches, fixes, modifications and enhancements to the Plug-In ("Updates"). If you have purchased a licence that includes the right to receive Updates, you are entitled to receive on request at no additional cost any Updates to the Plug-In produced by PSAL for a period of twelve months from the date of purchase of the licence.
4. TERMINATION 
Without prejudice to any other rights, PSAL may terminate this EULA if you fail to comply with the terms and conditions of this EULA. In such event, you must destroy all copies of the Plug-In in your possession.
5. COPYRIGHT
All title, including but not limited to copyrights, in and to the Plug-In and any copies thereof are owned by PSAL. All title and intellectual property rights in and to the content which may be accessed through use of the Plug-In is the property of the respective content owner and may be protected by applicable copyright or other intellectual property laws and treaties. This EULA grants you no rights to use such content. All rights not expressly granted are reserved by PSAL. 
6. NO WARRANTIES
PSAL expressly disclaims any warranty for the Plug-In or for any Support Services. The Plug-In and Support Services are provided “As Is” without any express or implied warranty of any kind, including but not limited to any warranties of merchantability, non-infringement, or fitness for a particular purpose. PSAL does not warrant or assume responsibility for the accuracy or completeness of any information, text, graphics, links or other items contained within the Plug-In or Support Services. PSAL makes no warranties respecting any harm that may be caused by the transmission of a computer virus, worm, time bomb, logic bomb, or other such software. PSAL further expressly disclaims any warranty or representation to any third party.
7. LIMITATION OF LIABILITY
In no event shall PSAL be liable for any damages (including, without limitation, lost profits, business interruption, or lost information) rising out of the use of or inability to use the Plug-In, even if PSAL has been advised of the possibility of such damages. In no event will PSAL be liable for loss of data or for indirect, special, incidental, consequential (including lost profit), or other damages based in contract, tort or otherwise. PSAL shall have no liability with respect to the content of the Plug-In or any part thereof, including but not limited to errors or omissions contained therein, libel, infringements of rights of publicity, privacy, trademark rights, business interruption, personal injury, loss of privacy, moral rights or the disclosure of confidential information. 
8. GOVERNING LAW 
This Agreement shall be governed by and construed in accordance with the laws of New Zealand.
9. MISCELLANEOUS
If any provision of this EULA is held to be invalid or unenforceable under any circumstances, its application in any other circumstances and the remaining provisions of this EULA shall not be affected. No waiver of any right under this EULA shall be effective unless given in writing by an authorised representative of PSAL. No waiver by PSAL of any right shall be deemed to be a waiver of any other right of PSAL arising under this EULA. 
10. ENTIRE AGREEMENT
This EULA represents the entire agreement concerning the Plug-In between you and PSAL, and it supersedes any prior proposal, representation, or understanding between the parties. 
"""

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
           u"folder.\n\nTIP: copy your backups to a USB stick and keep "
           u"it off-site." % (len(files2backup), backup_filname, backup_folder))
    return msg
