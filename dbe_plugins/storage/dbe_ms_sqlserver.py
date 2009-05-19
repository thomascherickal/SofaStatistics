"""
    def getFldType(self, adotype):
        
        # http://www.devguru.com/Technologies/ado/quickref/field_type.html
        # Yes, yes could be done with a dict ;-)
        # Yes - some are not found in mdbs (may eventually rationalise for all 
        #    ADO databases so keep results of research on hand here until then)
        
        if adotype == win32com.client.constants.adUnsignedTinyInt:
            fld_type = UNSIGNEDTINYINT
        elif adotype == win32com.client.constants.adTinyInt:
            fld_type = TINYINT
        elif adotype == win32com.client.constants.adUnsignedSmallInt:
            fld_type = UNSIGNEDSMALLINT
        elif adotype == win32com.client.constants.adSmallInt:
            fld_type = SMALLINT
        elif adotype == win32com.client.constants.adUnsignedInt:
            fld_type = UNSIGNEDINTEGER
        elif adotype == win32com.client.constants.adInteger:
            fld_type = INTEGER
        elif adotype == win32com.client.constants.adUnsignedBigInt:
            fld_type = UNSIGNEDBIGINT
        elif adotype == win32com.client.constants.adBigInt:
            fld_type = BIGINT
        elif adotype == win32com.client.constants.adSingle:
            fld_type = SINGLE
        elif adotype == win32com.client.constants.adDouble:
            fld_type = DOUBLE
        elif adotype == win32com.client.constants.adCurrency:
            fld_type = CURRENCY
        elif adotype == win32com.client.constants.adDecimal:
            fld_type = DECIMAL
        elif adotype == win32com.client.constants.adNumeric:
            fld_type = NUMERIC # Number with fixed precision and scale
        elif adotype == win32com.client.constants.adVarNumeric:
            fld_type = VARNUMERIC # Variable width exact numeric with signed scale
        elif adotype == win32com.client.constants.adBoolean:
            fld_type = BOOLEAN
        elif adotype == win32com.client.constants.adDate:
            fld_type = DATE
        elif adotype == win32com.client.constants.adDBTimeStamp:
            fld_type = TIMESTAMP
        elif adotype == win32com.client.constants.adVarWChar:
            fld_type = VARCHAR
        elif adotype == win32com.client.constants.adLongVarWChar:
            fld_type = LONGVARCHAR
        else:
            raise Exception, "Unrecognised ADO field type %d" % adotype
        return fld_type
"""
