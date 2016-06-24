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

def get_ado_dict():
    """
    Generate this using makepy via cli.
    makepy.py -o grab_consts.py
    NB have to manually put utf-8 encoding in after disabling assert in 
        genpy.py.
    """
    adBigInt                      =20         # from enum DataTypeEnum
    adBinary                      =128        # from enum DataTypeEnum
    adBoolean                     =11         # from enum DataTypeEnum
    adChapter                     =136        # from enum DataTypeEnum
    adChar                        =129        # from enum DataTypeEnum
    adCurrency                    =6          # from enum DataTypeEnum
    adDBDate                      =133        # from enum DataTypeEnum
    adDBTime                      =134        # from enum DataTypeEnum
    adDBTimeStamp                 =135        # from enum DataTypeEnum
    adDate                        =7          # from enum DataTypeEnum
    adDecimal                     =14         # from enum DataTypeEnum
    adDouble                      =5          # from enum DataTypeEnum
    adEmpty                       =0          # from enum DataTypeEnum
    adError                       =10         # from enum DataTypeEnum
    adFileTime                    =64         # from enum DataTypeEnum
    adGUID                        =72         # from enum DataTypeEnum
    adIDispatch                   =9          # from enum DataTypeEnum
    adIUnknown                    =13         # from enum DataTypeEnum
    adInteger                     =3          # from enum DataTypeEnum
    adLongVarBinary               =205        # from enum DataTypeEnum
    adLongVarChar                 =201        # from enum DataTypeEnum
    adLongVarWChar                =203        # from enum DataTypeEnum
    adNumeric                     =131        # from enum DataTypeEnum
    adPropVariant                 =138        # from enum DataTypeEnum
    adSingle                      =4          # from enum DataTypeEnum
    adSmallInt                    =2          # from enum DataTypeEnum
    adTinyInt                     =16         # from enum DataTypeEnum
    adUnsignedBigInt              =21         # from enum DataTypeEnum
    adUnsignedInt                 =19         # from enum DataTypeEnum
    adUnsignedSmallInt            =18         # from enum DataTypeEnum
    adUnsignedTinyInt             =17         # from enum DataTypeEnum
    adUserDefined                 =132        # from enum DataTypeEnum
    adVarBinary                   =204        # from enum DataTypeEnum
    adVarChar                     =200        # from enum DataTypeEnum
    adVarNumeric                  =139        # from enum DataTypeEnum
    adVarWChar                    =202        # from enum DataTypeEnum
    adVariant                     =12         # from enum DataTypeEnum
    adWChar                       =130        # from enum DataTypeEnum
    adEditAdd                     =2          # from enum EditModeEnum
    adEditDelete                  =4          # from enum EditModeEnum
    adEditInProgress              =1          # from enum EditModeEnum
    adEditNone                    =0          # from enum EditModeEnum

    return {adTinyInt: ADO_TINYINT,
            adUnsignedTinyInt: ADO_UNSIGNEDTINYINT,
            adSmallInt: ADO_SMALLINT,
            adUnsignedSmallInt: ADO_UNSIGNEDSMALLINT,
            adInteger: ADO_INTEGER,
            adUnsignedInt: ADO_UNSIGNEDINT,
            adBigInt: ADO_BIGINT,
            adUnsignedBigInt: ADO_UNSIGNEDBIGINT,
            adDecimal: ADO_DECIMAL,
            adSingle: ADO_SINGLE,
            adDouble: ADO_DOUBLE,
            adCurrency: ADO_CURRENCY,
            adNumeric: ADO_NUMERIC,
            adVarNumeric: ADO_VARNUMERIC,
            adBoolean: ADO_BOOLEAN,
            adDate: ADO_DATE,
            adDBDate: ADO_DBDATE,
            adDBTime: ADO_DBTIME,
            adDBTimeStamp: ADO_DBTIMESTAMP,
            adChar: ADO_CHAR,
            adWChar: ADO_WCHAR,
            adVarChar: ADO_VARCHAR,
            adVarWChar: ADO_VARWCHAR,
            adLongVarChar: ADO_LONGVARCHAR,
            adLongVarWChar: ADO_LONGVARWCHAR,
            adBinary: ADO_BINARY,
            adVarBinary: ADO_VARBINARY,
            adLongVarBinary: ADO_LONGVARBINARY,
            adVariant: ADO_VARIANT,
            adGUID: ADO_GUID,
            }
    
def get_min_max(fldtype, num_prec, dec_pts):
    """
    Returns minimum and maximum allowable numeric values.  
    Nones if not numeric (or if an unknown numeric e.g. ADO_VARNUMERIC).
    NB even though a floating point type will not store values closer 
        to zero than a certain level, such values will be accepted here.
        The database will store these as zero.
    http://www.databasedev.co.uk/fields_datatypes.html
    http://www.sql-server-helper.com/faq/data-types-p01.aspx
    """
    if fldtype == ADO_TINYINT:
        min = -(2**8)
        max = (2**8)-1 # 255
    elif fldtype == ADO_UNSIGNEDTINYINT:
        min = 0
        max = (2**8)-1 # 255
    elif fldtype == ADO_SMALLINT:
        min = -(2**15)
        max = (2**15)-1
    elif fldtype == ADO_UNSIGNEDSMALLINT:
        min = 0
        max = (2**15)-1
    elif fldtype == ADO_INTEGER:
        min = -(2**31)
        max = (2**31)-1
    elif fldtype == ADO_UNSIGNEDINT:
        min = 0
        max = (2**31)-1
    elif fldtype == ADO_BIGINT:
        min = -(2**63)
        max = (2**63)-1
    elif fldtype == ADO_UNSIGNEDBIGINT:
        min = 0
        max = (2**63)-1
    elif fldtype in [ADO_DECIMAL, ADO_NUMERIC]:
        # (+- 38 if .adp as opposed to .mdb)
        min = -(10**28 -1)
        max = (10**28)-1
    elif fldtype == ADO_SINGLE: # signed by default
        min = -(2**128) # -3.402823466E+38
        max = (2**128)-1 # 3.402823466E+38
    elif fldtype == ADO_DOUBLE:
        min = -(2**1024) # -1.79769313486231E308
        max = 2**1024 # 1.79769313486231E308
    elif fldtype == ADO_CURRENCY:
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
