import os
import win32com.client

import my_globals as mg
import my_exceptions

# Copyright (c) Grant Paton-Simpson 2009. All rights reserved. 
# Based on excel.py with major modifications
# Copyright notice for excel.py: Copyright (c) Nicolas Lehuen 2005 
# (Code available at http://code.activestate.com/recipes/440661)

# http://www.w3schools.com/ADO/met_rs_open.asp
adOpenForwardOnly = 0
adOpenStatic = 3
adLockReadOnly = 1
adSchemaTables = 20
ROW_BUFFER = 256 # for iteration. -1 buffers the entire worksheet

"""
When counting rows, or iterating through the rows, only the data rows are 
    included.
Making ADODB include the first row when there was no header required the HDR=No 
    setting.
NB by default ADODB will not count the first row assuming that it is a 
    header - see http://jack-fx.com/vbqa/2010/02/11/...
    ...how-to-use-ado-with-excel-data-from-visual-basic-or-vba/.
And it cannot be corrected in ODBC http://support.microsoft.com/kb/288343/EN-US/
Handled OK in OLEDB by HDR=No. HDR=0 didn't work even though it was supposed to!
"""

def get_numbered_flds(n_flds):
    return [mg.NEXT_FLDNAME_TEMPLATE % (x+1,) for x in range(n_flds)]

def plain_process(val):
    """
    If value an ordinary string, return it stripped of extraneous whitespace.
    If was all whitespace, return None.
    If not a string, return as was. 
    """
    if isinstance(val, basestring):
        val = val.strip()
        if val == "":
            return None
    return val

def encode_process(val, encoding):
    """
    If unicode, encode if possible.
    """
    if isinstance(val, unicode):
        val = val.strip()
        if val == "":
            return None
        else:
            return val.encode(encoding)
    else:
        return plain_process(val)
       

class Workbook(object):

    def __init__(self, filename, sheets_have_hdrs=True):
        """
        In ADODB, treatment of headers is set at the workbook connection level.
        Have to treat all sheets in a workbook the same.  NB dummy headers can 
            be used if necessary.
        """
        if not os.path.exists(filename):
            raise IOError
        self.sheets_have_hdrs = sheets_have_hdrs
        self.con = win32com.client.Dispatch('ADODB.Connection')
        dns = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=%s;" % filename
        if self.sheets_have_hdrs:
            dns += "Extended Properties=\"Excel 8.0;IMEX=1;HDR=Yes;\""
        else:
            dns += "Extended Properties=\"Excel 8.0;IMEX=1;HDR=No;\""
        self.con.Open(dns)

    def get_sheet_names(self):
        "Get list of worksheet names"
        sheets = []
        rs = self.con.OpenSchema(adSchemaTables)
        while not rs.EOF:
            sheets.append(rs.Fields[2].Value)
            rs.MoveNext()
        rs.Close()
        rs = None
        del rs
        return sheets

    def get_sheet(self, name, encoding=None):
        """
        Get named worksheet.
        encoding - character encoding used to encode the unicode strings 
            returned by Excel, so we can use ordinary Python strings.
        """
        return Worksheet(self, name, encoding)
            
    def __del__(self):
        self.close()

    def close(self):
        "Closes Excel Workbook. Automatically called when Workbook deleted."
        try:
            self.con.Close()
            del self.con
        except Exception:
            my_exceptions.DoNothingException()


class Worksheet(object):
    """
    A worksheet which can be iterated through row by row.
    NB any time you start iterating it will start at the beginning, even if you
        got part-way through last time on same object.
    """
    def __init__(self, doc, name, encoding):
        self.doc = doc
        self.name = name
        self.encoding = encoding
        self.fld_names = self.get_fld_names()

    def get_data_rows_n(self):
        """
        Excludes header row (if any) from count.
        Need a static cursor to do a record count 
        http://www.w3schools.com/ado/prop_rs_recordcount.asp
        """
        rs = win32com.client.Dispatch('ADODB.Recordset')
        rs.Open(u"SELECT * FROM [%s]" % self.name, self.doc.con, adOpenStatic,
                adLockReadOnly)
        rows_n = rs.RecordCount
        rs.Close()
        rs = None
        del rs
        return rows_n

    def get_fld_names(self):
        """
        Returns a list of field names for the sheet.
        If a header, use those, otherwise follow convention Fld_1, ...
        """
        rs = win32com.client.Dispatch('ADODB.Recordset')        
        try:
            rs.Open(u'SELECT * FROM [%s]' % self.name, self.doc.con,
                adOpenForwardOnly, adLockReadOnly)
        except Exception, e:
            if e[2][2] == 'Too many fields defined.':
                raise Exception(
                        u"Delete blank columns at end of worksheet to keep " +
                        u"within JET 255 column limit.  " +
                        u"See http://support.microsoft.com/kb/198504/EN-US/")
            else:
                raise
        try:
            if self.doc.sheets_have_hdrs:
                if self.encoding:
                    fld_names = [encode_process(fld.Name, self.encoding) \
                                 for fld in rs.Fields]
                else:
                    fld_names = [plain_process(fld.Name) for fld in rs.Fields]
            else:
                fld_names = get_numbered_flds(n_flds=len(rs.Fields))
            return fld_names
        finally:
            rs.Close()
            del rs

    def __iter__(self):
        "Returns paged iterator."
        return self.buffered_rows()

    def buffered_rows(self):
        """
        Returns an iterator on the rows in the worksheet. Rows are returned as
            dicts with field names as keys. Starts with the first row, whether 
            or not a header.  Although that is not needed if extracting the data 
            records it could be useful to debug processing of the header etc.
        """
        rs = win32com.client.Dispatch('ADODB.Recordset')
        rs.Open(u'SELECT * FROM [%s]' % self.name, self.doc.con,
                adOpenForwardOnly, adLockReadOnly)
        try:
            rows_left = True
            while True:
                rows = zip(*rs.GetRows(ROW_BUFFER))
                if rs.EOF:
                    rs.Close()
                    rs = None
                    rows_left = False
                for row in rows:
                    if self.encoding:
                        vals = [encode_process(x, self.encoding) for \
                                x in row]
                        yield dict(zip(self.fld_names, vals))
                    else:
                        vals = [plain_process(x) for x in row]
                        yield dict(zip(self.fld_names, vals))
                if not rows_left:
                    break
        except Exception:
            if rs is not None:
                rs.Close()
                del rs
            raise