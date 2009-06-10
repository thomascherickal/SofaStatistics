import csv
import wx


class FileImporter(object):
    """
    Import csv file into default SOFA SQLite database.
    Checks table name first to ensure no collision.
    Adds unique index id so can identify unique records with certainty.
    """
    
    def __init__(self, file_path, tbl_name):
        """"""
        self.file_path = file_path
        self.tbl_name = tbl_name
        wx.MessageBox("My file path is '%s' and the table name is '%s'" % (file_path, tbl_name))
        

    def GetParams(self):
        """
        Get any user choices required.
        """
        pass
        
