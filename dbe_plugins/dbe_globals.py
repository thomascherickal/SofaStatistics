import win32com.client

# http://www.devguru.com/Technologies/ado/quickref/field_type.html
# numeric
ADO_TINYINT = 'Tiny Int - 1-byte signed integer' # adTinyInt
ADO_UNSIGNEDTINYINT = \
    'Unsigned TinyInt - 1-byte unsigned integer' # adUnsignedTinyInt
ADO_SMALLINT = 'SmallInt - 2-byte signed integer' # adSmallInt
ADO_UNSIGNEDSMALLINT = \
    'Unsigned SmallInt - 2-byte unsigned integer' # adUnsignedSmallInt
ADO_INTEGER = 'Integer - 4-byte signed integer' # adInteger
ADO_UNSIGNEDINT = 'Unsigned Integer - 4-byte unsigned integer' # adUnsignedInt
ADO_BIGINT = 'Big Integer - 8-byte signed integer' # adBigInt
ADO_UNSIGNEDBIGINT = \
    'Unsigned Big Integer - 8-byte unsigned integer' # adUnsignedBigInt
ADO_DECIMAL = 'Decimal - Number with fixed precision and scale' # adDecimal
ADO_SINGLE = 'Single - single-precision floating-point value' # adSingle
ADO_DOUBLE = 'Double - double precision floating-point' # adDouble
ADO_CURRENCY = 'Currency format' # adCurrency
ADO_NUMERIC = 'Number with fixed precision and scale' # adNumeric
ADO_VARNUMERIC = 'Variable width exact numeric with signed scale' # adVarNumeric

# other
ADO_BOOLEAN = 'boolean' # adBoolean
ADO_DATE = 'Date - Number of days since 12/30/1899' # adDate
ADO_DBDATE = 'DB Date - YYYYMMDD date format' # adDBDate
ADO_DBTIME = 'DB Time - HHMMSS time format' # adDBTime
ADO_DBTIMESTAMP = \
    'DBtimestamp - YYYYMMDDHHMMSS date/time format' # adDBTimeStamp
ADO_CHAR = 'Char' # adChar
ADO_WCHAR = 'WVarChar - Null-terminated Unicode character string' # adWChar
ADO_VARCHAR = 'Varchar string' # adVarChar
ADO_VARWCHAR = \
    'VarWChar - Null-terminated Unicode character string' # adVarWChar
ADO_LONGVARCHAR = 'Long varchar' # adLongVarChar
ADO_LONGVARWCHAR = 'Long varWchar' # adLongVarWChar
ADO_BINARY = 'Binary' # adBinary
ADO_VARBINARY = 'Binary value' # adVarBinary
ADO_LONGVARBINARY = 'Long var binary' # adLongVarBinary
ADO_VARIANT = 'Variant - automation variant' # adVariant
ADO_GUID = 'Globally Unique identifier' # adGUID

NUMERIC_TYPES = [ADO_TINYINT, ADO_UNSIGNEDTINYINT, ADO_SMALLINT, 
    ADO_UNSIGNEDSMALLINT, ADO_INTEGER, ADO_UNSIGNEDINT, ADO_BIGINT, 
    ADO_UNSIGNEDBIGINT, ADO_DECIMAL, ADO_SINGLE, ADO_DOUBLE, ADO_CURRENCY, 
    ADO_NUMERIC, ADO_VARNUMERIC]

DATETIME_TYPES = [ADO_DATE, ADO_DBDATE, ADO_DBTIME, ADO_DBTIMESTAMP]

def getADODic():
    """
    Fails unless run _after_ something else (not sure what) has run first.
    """
    return {win32com.client.constants.adTinyInt: ADO_TINYINT,
            win32com.client.constants.adUnsignedTinyInt: ADO_UNSIGNEDTINYINT,
            win32com.client.constants.adSmallInt: ADO_SMALLINT,
            win32com.client.constants.adUnsignedSmallInt: ADO_UNSIGNEDSMALLINT,
            win32com.client.constants.adInteger: ADO_INTEGER,
            win32com.client.constants.adUnsignedInt: ADO_UNSIGNEDINT,
            win32com.client.constants.adBigInt: ADO_BIGINT,
            win32com.client.constants.adUnsignedBigInt: ADO_UNSIGNEDBIGINT,
            win32com.client.constants.adDecimal: ADO_DECIMAL,
            win32com.client.constants.adSingle: ADO_SINGLE,
            win32com.client.constants.adDouble: ADO_DOUBLE,
            win32com.client.constants.adCurrency: ADO_CURRENCY,
            win32com.client.constants.adNumeric: ADO_NUMERIC,
            win32com.client.constants.adVarNumeric: ADO_VARNUMERIC,
            win32com.client.constants.adBoolean: ADO_BOOLEAN,
            win32com.client.constants.adDate: ADO_DATE,
            win32com.client.constants.adDBDate: ADO_DBDATE,
            win32com.client.constants.adDBTime: ADO_DBTIME,
            win32com.client.constants.adDBTimeStamp: ADO_DBTIMESTAMP,
            win32com.client.constants.adChar: ADO_CHAR,
            win32com.client.constants.adWChar: ADO_WCHAR,
            win32com.client.constants.adVarChar: ADO_VARCHAR,
            win32com.client.constants.adVarWChar: ADO_VARWCHAR,
            win32com.client.constants.adLongVarChar: ADO_LONGVARCHAR,
            win32com.client.constants.adLongVarWChar: ADO_LONGVARWCHAR,
            win32com.client.constants.adBinary: ADO_BINARY,
            win32com.client.constants.adVarBinary: ADO_VARBINARY,
            win32com.client.constants.adLongVarBinary: ADO_LONGVARBINARY,
            win32com.client.constants.adVariant: ADO_VARIANT,
            win32com.client.constants.adGUID: ADO_GUID,
            }
    
def GetMinMax(fld_type, num_prec, dec_pts):
    """
    Returns minimum and maximum allowable numeric values.  
    Nones if not numeric (or if an unknwon numeric e.g. ADO_VARNUMERIC).
    NB even though a floating point type will not store values closer 
        to zero than a certain level, such values will be accepted here.
        The database will store these as zero.
    http://www.databasedev.co.uk/fields_datatypes.html
    http://www.sql-server-helper.com/faq/data-types-p01.aspx
    """
    if fld_type == ADO_TINYINT:
        min = -(2**8)
        max = (2**8)-1 # 255
    elif fld_type == ADO_UNSIGNEDTINYINT:
        min = 0
        max = (2**8)-1 # 255
    elif fld_type == ADO_SMALLINT:
        min = -(2**15)
        max = (2**15)-1
    elif fld_type == ADO_UNSIGNEDSMALLINT:
        min = 0
        max = (2**15)-1
    elif fld_type == ADO_INTEGER:
        min = -(2**31)
        max = (2**31)-1
    elif fld_type == ADO_UNSIGNEDINT:
        min = 0
        max = (2**31)-1
    elif fld_type == ADO_BIGINT:
        min = -(2**63)
        max = (2**63)-1
    elif fld_type == ADO_UNSIGNEDBIGINT:
        min = 0
        max = (2**63)-1
    elif fld_type in [ADO_DECIMAL, ADO_NUMERIC]:
        # (+- 38 if .adp as opposed to .mdb)
        min = -(10**28 -1)
        max = (10**28)-1
    elif fld_type == ADO_SINGLE: # signed by default
        min = -(2**128) # -3.402823466E+38
        max = (2**128)-1 # 3.402823466E+38
    elif fld_type == ADO_DOUBLE:
        min = -(2**1024) # -1.79769313486231E308
        max = 2**1024 # 1.79769313486231E308
    elif fld_type == ADO_CURRENCY:
        """
        Accurate to 15 digits to the left of the decimal point and 
            4 digits to the right.
        e.g. 19,4 -> 999999999999999.9999
        """
        dec_pts = 4
        num_prec = 15 + dec_pts
        abs_max = ((10**(num_prec + 1))-1)/(10**dec_pts)
        min = -abs_max
        max = abs_max
    else:
        min = None
        max = None
    return min, max
