import datetime
import os

import wx
import zipfile

from sofastats import my_globals as mg

"""
If not available, make backup subfolder.

Make date-time stamped zip file and include in it all vdts, projs, sofa_db and, 
optionally, reports.

Do not include default_report_extras.
"""

BACKUP_FOLDER = 'backups'

def run_backup(inc_reports=True):
    debug = False
    report2gui = False
    backup_folder = os.path.join(mg.LOCAL_PATH, BACKUP_FOLDER)
    try:
        os.mkdir(backup_folder)
    except OSError:
        pass
    now = datetime.datetime.now().isoformat()
    ts = '-'.join(now.split(':')[:-1])
    backup_fname = f'sofa_backup_{ts}.zip'
    backup_path = os.path.join(backup_folder, backup_fname)
    ## http://www.doughellmann.com/PyMOTW/zipfile/
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
                    wx.MessageBox(f'Current root is: {root}')
            if root == mg.REPORT_EXTRAS_PATH:
                continue
            for filname in files:
                fpath = os.path.join(folder_path, root, filname)
                files2backup.append(fpath)
    for fpath in files2backup:
        if debug:
            print(f'Adding {fpath} ...')
            if report2gui:
                wx.MessageBox(f"File path is: {fpath}")
        zf.write(fpath)
    zf.close()
    if debug: print('Closed zip file')
    msg = (f'Backed up {len(files2backup)} files to:\n"{backup_fname}"'
        f'\n\nYou\'ll find it in your "{backup_folder}" folder.'
        '\n\nTIP: copy your backups to a USB stick and keep it off-site.')
    return msg
