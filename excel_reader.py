import win32com.client

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

def get_numbered_flds(n_flds):
    return [u"Fld_%s" % (x+1,) for x in range(n_flds)]

def PlainProcess(val):
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

def EncodeProcess(val, encoding):
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
        return PlainProcess(val)
       

class Workbook(object):

    def __init__(self, filename):
        self.conn = win32com.client.Dispatch('ADODB.Connection')
        self.conn.Open('PROVIDER=Microsoft.Jet.OLEDB.4.0;'+
            'DATA SOURCE=%s;Extended Properties="Excel 8.0;HDR=1;IMEX=1"' % \
            filename)

    def GetSheets(self):
        "Get list of worksheet names"
        sheets = []
        rs = self.conn.OpenSchema(adSchemaTables)
        while not rs.EOF:
            sheets.append(rs.Fields[2].Value)
            rs.MoveNext()
        rs.Close()
        rs = None
        del rs
        return sheets

    def GetSheet(self, name, has_header=True, encoding=None):
        """
        Get named worksheet.
        has_header - has headings in first row?
        encoding - character encoding used to encode the unicode strings 
            returned by Excel, so we can use ordinary Python strings.
        """
        return Worksheet(self, name, has_header, encoding)
			
    def __del__(self):
        self.close()

    def close(self):
        "Closes Excel Workbook. Automatically called when Workbook deleted."
        try:
            self.conn.Close()
            del self.conn
        except Exception:
            pass


class Worksheet(object):
    """
    A worksheet which can be iterated through row by row.
    has_header - first row contains column headings?
    """
    def __init__(self, doc, name, has_header, encoding):
        self.doc = doc
        self.name = name
        self.has_header = has_header
        self.encoding = encoding

    def GetRowsN(self):
        """
        Need a static cursor to do a record count 
        http://www.w3schools.com/ado/prop_rs_recordcount.asp
        """
        rs = win32com.client.Dispatch('ADODB.Recordset')		
        rs.Open(u"SELECT * FROM [%s]" % self.name, self.doc.conn, adOpenStatic,
                adLockReadOnly)
        rows_n = rs.RecordCount
        rs.Close()
        rs = None
        del rs
        return rows_n

    def GetFldNames(self):
        """
        Returns a list of field names for the sheet.
        If a header, use those, otherwise follow convention Fld_1, ...
        """
        rs = win32com.client.Dispatch('ADODB.Recordset')		
        try:
            rs.Open(u'SELECT * FROM [%s]' % self.name, self.doc.conn,
                adOpenForwardOnly, adLockReadOnly)
        except Exception, e:
            if e[2][2] == 'Too many fields defined.':
                raise Exception, \
                    "Delete blank columns at end of worksheet to keep " + \
                    "within JET 255 column limit.  " + \
                    "See http://support.microsoft.com/kb/198504/EN-US/"
            else:
                raise
        try:
            if self.has_header:
                if self.encoding:
                    fld_names = [EncodeProcess(fld.Name, self.encoding) \
								 for fld in rs.Fields]
                else:
                	fld_names = [PlainProcess(fld.Name) for fld in rs.Fields]
            else:
                fld_names = get_numbered_flds(n_flds=len(rs.Fields))
            return fld_names
        finally:
            rs.Close()
            del rs

    def __iter__(self):
        "Returns paged iterator."
        return self.BufferedRows()

    def BufferedRows(self):
        """
        Returns an iterator on the rows in the worksheet. Rows are returned as
            dicts with field names as keys.
        """
        rs = win32com.client.Dispatch('ADODB.Recordset')
        rs.Open(u'SELECT * FROM [%s]' % self.name, self.doc.conn,
                adOpenForwardOnly, adLockReadOnly)
        try:
            flds = self.GetFldNames()
            rows_left = True
            while True:
                rows = zip(*rs.GetRows(ROW_BUFFER))				
                if rs.EOF:
                    rs.Close()
                    rs = None
                    rows_left = False
                for row in rows:
                	if self.encoding:
                		vals = [EncodeProcess(x, self.encoding) for \
								x in row]
                		yield dict(zip(flds, vals))
                	else:
                		vals = [PlainProcess(x) for x in row]
                		yield dict(zip(flds, vals))
                if not rows_left:
                	break
        except Exception:
            if rs is not None:
                rs.Close()
                del rs
            raise