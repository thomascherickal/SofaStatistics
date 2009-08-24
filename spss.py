"""
A Python module for importing SPSS files

(c) Alan James Salmoni
Released under the Affero General Public License

Modified by Grant Paton-Simpson for inclusion in SOFA Statistics.

Notes: This only imports types 7 subtypes 3, 4, 5 and 6. Other subtypes are:
7: Multiple response set definitions
8: Data Entry for Windows (DEW) information
10: TextSmart information
11: Measurement level, column width and alignment for each variable
"""

import os
import os.path
import struct
import sys

debug = False

def pkint(vv):
    """
    An auxilliary function that returns an integer from a 4-byte word.
    The integer is packed in a tuple.
    """
    return struct.unpack("i",vv)

def pkflt(vv):
    """
    An auxilliary function returns a double-precision float from an 8-byte word
    The float is packed in a tuple.
    """
    vvlen = len(vv)
    if vvlen != 8:
        print "Not 8 long - %s instead" % vvlen
    if debug: print "vv is: %s" % len(vv)
    pkflt = struct.unpack("d",vv)
    return pkflt

def pkstr(vv):
    """
    An auxiliary function that returns a string from an 8-byte word. The 
    string is NOT packed.
    """
    bstr = ''
    for i in str(vv):
        bstr = bstr + struct.unpack("s",i)[0]
    return bstr


class variable(object):
    """
    This class contains a variable and its attributes. Each variable within 
    the SPSS file causes an instantiation of this class. The file object 
    contains a list of these in self.variablelist.
    """
    def __init__(self):
        self.name = None # 8 char limit
        self.namelabel = None
        self.data = []
        self.missingmarker = None
        self.missingd = []
        self.missingr = []
        self.type = None # 0 = numeric, 1 = string, -1 = string continuation
        self.printformatcode = []
        self.writeformatcode = []
        self.labelvalues = []
        self.labelfields = []

class SPSSFile(object):
    def __init__(self, dir, filename):
        self.filename = filename
        os.chdir(dir)
        self.vartypecode = []
        self.varlabel = []
        self.varmissingcode = []
        self.varprintformatcode = []
        self.varwriteformatcode = []
        self.varlabel = []
        self.missingvals = []
        self.missingvalmins = []
        self.missingvalmaxs = []
        self.documents = ''
        self.variablelist = []
        self.numvars = 0
        self.variablesets = None
        self.datevars = []

    def OpenFile(self):
        """
        This method trys to open the SPSS file.
        """
        try:
            print "Trying to open %s" % self.filename
            self.fin = open(self.filename, "rb")
        except IOError:
            print "Cannot open file"
            self.fin = None

    def GetRecords(self):
        """
        This method read a 4-byte word and works out what record type it is, 
        and then dispatches to the correct method. This continues until the 
        '999' code is reached (and of dictionary) upon which the data are read.
        """
        self.GetRecordType1()
        while 1:
            IN = pkint(self.fin.read(4))[0]
            if IN == 2:
                # get record type 2
                self.GetRecordType2()
            elif IN == 3:
                # get record type 3
                self.GetRecordType3()
            elif IN == 6:
                # get record type 6
                pass
            elif IN == 7:
                # get record type 7
                self.GetRecordType7()
            elif IN == 999:
                # last record end
                self.fin.read(4)
                self.GetData()
            #else:
                #print "Ending: invalid record type (%s) specified"%IN
                print "Ending here"
                return
                #sys.exit()
        print "ending here"
        return
        #sys.exit()

    def GetRecordType1(self):
        """
        This method reads in a type 1 record (file meta-data).
        """
        if self.fin is not None:
            self.recordtype = self.fin.read(4)
            self.eyecatcher = self.fin.read(60)
            self.filelayoutcode = pkint(self.fin.read(4))
            self.numOBSelements = pkint(self.fin.read(4))
            self.compressionswitch = pkint(self.fin.read(4))
            self.caseweightvar = pkint(self.fin.read(4))
            self.numcases = pkint(self.fin.read(4))
            self.compressionbias = (self.fin.read(8))
            self.metastr = self.fin.read(84)
        else:
            print "None type!"

    def GetRecordType2(self):
        """
        This method reads in a type 2 record (variable meta-data).
        """
        x = variable()
        IN = pkint(self.fin.read(4))[0]
        x.typecode = IN
        if x.typecode != -1:
            IN = pkint(self.fin.read(4))[0]
            x.labelmarker = IN
            IN = pkint(self.fin.read(4))[0]
            x.missingmarker = IN
            IN = self.fin.read(4)
            x.decplaces = ord(IN[0])
            x.colwidth = ord(IN[1])
            x.formattype = self.GetPrintWriteCode(ord(IN[2]))
            IN = self.fin.read(4)
            x.decplaces_wrt = ord(IN[0])
            x.colwidth_wrt = ord(IN[1])
            x.formattype_wrt = self.GetPrintWriteCode(ord(IN[2]))
            IN = pkstr(self.fin.read(8))
            nameblankflag = True
            x.name = IN
            for i in x.name:
                if ord(i) != 32:
                    nameblankflag = False
            if x.labelmarker == 1:
                IN = pkint(self.fin.read(4))[0]
                x.labellength = IN
                if (IN % 4) != 0:
                    IN = IN + 4 - (IN % 4)
                IN = pkstr(self.fin.read(IN))
                x.label = IN
            else:
                x.label = ''
            for i in range(abs(x.missingmarker)):
                self.fin.read(8)
            if x.missingmarker == 0:
                # no missing values
                x.missingd = None
                x.missingr = (None,None)
            elif (x.missingmarker == -2) or (x.missingmarker == -3):
                # range of missing values
                val1 = pkflt(self.fin.read(8))[0]
                val2 = pkflt(self.fin.read(8))[0]
                x.missingr = (val1, val2)
                if x.missingmarker == -3:
                    IN = pkflt(self.fin.read(8))[0]
                    x.missingd = IN
                else:
                    x.missings = None
            elif (x.missingmarker > 0) and (x.missingmarker < 4):
                # n(mval) missing vals
                tmpmiss = []
                for i in range(x.missingmarker):
                    IN = pkflt(self.fin.read(8))[0]
                    tmpmiss.append(IN)
                x.missingd = tmpmiss
                x.missingr = None
            if nameblankflag == False:
                self.variablelist.append(x)
        elif x.typecode == -1:
            # read the rest
            self.fin.read(24)

    def GetRecordType3(self):
        """
        This method reads in a type 3 and a type 4 record. These always occur 
        together. Type 3 is a value label record (value-field pairs for 
        labels), and type 4 is the variable index record (which variables 
        have these value-field pairs).
        """
        # now record type 3
        self.r3values = []
        self.r3labels = []
        IN = pkint(self.fin.read(4))[0]
        values = []
        fields = []
        for labels in range(IN):
            IN = self.fin.read(8)
            IN = pkflt(IN)[0]
            values.append(IN)
            l = ord(self.fin.read(1))
            if (l % 8) != 0:
                l = l + 8 - (l % 8)
            IN = pkstr(self.fin.read(l-1))
            fields.append(IN)
        # get record type 4
        t = pkint(self.fin.read(4))[0]
        if t == 4:
            numvars = pkint(self.fin.read(4))[0]
            # IN is number of variables
            labelinds = []
            for i in range(numvars):
                IN = pkint(self.fin.read(4))[0]
                # this is index, store it
                labelinds.append(IN)
            for i in labelinds:
                self.variablelist[i-1].labelvalues = values
                self.variablelist[i-1].labelfields = fields
        else:
            print "Invalid subtype (%t)"%t
            return
            #sys.exit()

    def GetRecordType6(self):
        """
        This method retrieves the document record. 
        """
        # document record, only one allowed
        IN = pkint(self.fin.read(4))[0]
        if self.documents == '':
            for i in range(IN):
                self.documents = self.documents + pkstr(self.fin.read(80))[0]

    def GetRecordType7(self):
        """
        This method is called when a type 7 record is encountered. The 
        subtype is then worked out and despatched to the proper method. Any 
        subtypes that are not yet programmed are read in and skipped over, so 
        not all subtype methods are yet functional.
        """
        # get subtype code
        subtype = pkint(self.fin.read(4))[0]
        if subtype == 3:
            self.GetType73()
        elif subtype == 4:
            self.GetType74()
        elif subtype == 5:
            self.GetType75()
        elif subtype == 6:
            self.GetType76()
        else:
            self.GetType7other()

    def GetType73(self):
        """
        This method retrieves records of type 7, subtype 3. This is for 
        release and machine specific integer information (eg, release 
        number, floating-point representation, compression scheme code etc).
        """
        # this is for release and machine-specific information
        datatype = pkint(self.fin.read(4))[0]
        numelements = pkint(self.fin.read(4))[0]
        if numelements == 8:
            self.releasenum = pkint(self.fin.read(4))[0]
            self.releasesubnum = pkint(self.fin.read(4))[0]
            self.releaseidnum = pkint(self.fin.read(4))[0]
            self.machinecode = pkint(self.fin.read(4))[0]
            self.FPrep = pkint(self.fin.read(4))[0]
            self.compressionscheme = pkint(self.fin.read(4))[0]
            self.endiancode = pkint(self.fin.read(4))[0]
            self.charrepcode = pkint(self.fin.read(4))[0]
        else:
            print "Error reading type 7/3"
            return
            #sys.exit()

    def GetType74(self):
        """
        This method retrieves records of type 7, subtype 4. This is for 
        release and machine-specific OBS-type information (system missing 
        value [self.SYSMIS], and highest and lowest missing values.
        """
        # release & machine specific OBS information
        datatype = pkint(self.fin.read(4))[0]
        numelements = pkint(self.fin.read(4))[0]
        if (numelements == 3) and (datatype == 8):
            self.SYSMIS = pkflt(self.fin.readline(8))[0]
            self.himissingval = pkflt(self.fin.readline(8))[0]
            self.lomissingval = pkflt(self.fin.readline(8))[0]
        else:
            print "Error reading type 7/4"
            return
            #sys.exit()

    def GetType75(self):
        """
        This method parses variable sets information. This is not 
        functional yet.
        """
        # variable sets information
        datatype = pkint(self.fin.read(4))[0]
        numelements = pkint(self.fin.read(4))[0]
        IN = pkstr(self.fin.read(4 * numelements))
        self.variablesets =IN

    def GetType76(self):
        """
        This method parses TRENDS data variable information. This is not 
        functional yet.
        """
        # TRENDS data variable information
        datatype = pkint(self.fin.read(4))[0]
        numelements = pkint(self.fin.read(4))[0]
        # get data array
        self.explicitperiodflag = pkint(self.fin.read(4))[0]
        self.period = pkint(self.fin.read(4))[0]
        self.numdatevars = pkint(self.fin.read(4))[0]
        self.lowestincr = pkint(self.fin.read(4))[0]
        self.higheststart = pkint(self.fin.read(4))[0]
        self.datevarsmarker = pkint(self.fin.read(4))[0]
        for i in range(1, self.numdatevars + 1):
            recd = []
            recd.append(pkint(self.fin.read(4))[0])
            recd.append(pkint(self.GetDateVar(self.fin.read(4))[0]))
            recd.append(pkint(self.fin.read(4))[0])
            self.datevars.append(recd)

    def GetType711(self):
        """
        This method retrieves information about the measurement level, column 
        width and alignment.
        """
        datatype = pkint(self.fin.read(4))[0]
        numelements = pkint(self.fin.read(4))[0]
        IN = self.fin.read(datatype * numelements)

    def GetType7other(self):
        """
        This method is called when other subtypes not catered for are 
        encountered. See the introduction to this module for more 
        information about their contents.
        """
        datatype = pkint(self.fin.read(4))[0]
        numelements = pkint(self.fin.read(4))[0]
        IN = self.fin.read(datatype * numelements)

    def GetData(self):
        """
        This method retrieves the actual data and stores them into the 
        appropriate variable's 'data' attribute.
        """
        self.cluster = []
        for case in range(self.numcases[0]):
            for i, var in enumerate(self.variablelist):
                if var.typecode == 0: # numeric variable
                    N = self.GetNumber(var)
                    if N == "False":
                        print "Error returning case %s, var %s"%(case, i)
                        sys.exit()
                    var.data.append(N)
                elif (var.typecode > 0) and (var.typecode < 256):
                    S = self.GetString(var)
                    if S == "False":
                        print "Error returning case %s, var %s"%(case, i)
                        sys.exit()
                    var.data.append(S)

    def GetNumber(self, var):
        """
        This method is called when a number / numeric datum is to be 
        retrieved. This method returns "False" (the string, not the Boolean 
        because of conflicts when 0 is returned) if the operation is not 
        possible.
        """
        if self.compressionswitch == 0: # uncompressed number
            IN = self.fin.read(8)
            if len(IN) < 1:
                return "False"
            else:
                return pkflt(IN)[0]
        else: # compressed number
            if len(self.cluster) == 0: # read new bytecodes
                IN = self.fin.read(8)
                for byte in IN:
                    self.cluster.append(ord(byte))
            byte = self.cluster.pop(0)
            if (byte > 1) and (byte < 252):
                return byte - 100
            elif byte == 252:
                return "False"
            elif byte == 253:
                IN = self.fin.read(8)
                if len(IN) < 1:
                    return "False"
                else:
                    return pkflt(IN)[0]
            elif byte == 254:
                return 0.0
            elif byte == 255:
                return self.SYSMIS

    def GetString(self, var):
        """
        This method is called when a string is to be retrieved. Strings can be 
        longer than 8-bytes long if so indicated. This method returns SYSMIS 
        (the string not the Boolean) is returned due to conflicts. 
        """
        if self.compressionswitch == 0:
            IN = self.fin.read(8)
            if len(IN) < 1:
                return self.SYSMIS
            else:
                return pkstr(IN)
        else:
            ln = ''
            while 1:
                if len(self.cluster) == 0:
                    IN = self.fin.read(8)
                    for byte in IN:
                        self.cluster.append(ord(byte))
                byte = self.cluster.pop(0)
                if (byte > 0) and (byte < 252):
                    return byte - 100
                if byte == 252:
                    return self.SYSMIS
                if byte == 253:
                    IN = self.fin.read(8)
                    if len(IN) < 1:
                        return self.SYSMIS
                    else:
                        ln = ln + pkstr(IN)
                        if len(ln) > var.typecode:
                            return ln
                if byte == 254:
                    if ln != '':
                        return ln
                if byte == 255:
                    return self.SYSMIS

    def GetPrintWriteCode(self, code):
        """
        This method returns the print / write format code of a variable. The 
        returned value is a tuple consisting of the format abbreviation 
        (string <= 8 chars) and a meaning (long string). Non-existent codes 
        have a (None, None) tuple returned.
        """
        if code == 0:
            return ('','Continuation of string variable')
        elif code == 1:
            return ('A','Alphanumeric')
        elif code == 2:
            return ('AHEX', 'alphanumeric hexadecimal')
        elif code == 3:
            return ('COMMA', 'F format with commas')
        elif code == 4:
            return ('DOLLAR', 'Commas and floating point dollar sign')
        elif code == 5:
            return ('F', 'F (default numeric) format')
        elif code == 6:
            return ('IB', 'Integer binary')
        elif code == 7:
            return ('PIBHEX', 'Positive binary integer - hexadecimal')
        elif code == 8:
            return ('P', 'Packed decimal')
        elif code == 9:
            return ('PIB', 'Positive integer binary (Unsigned)')
        elif code == 10:
            return ('PK', 'Positive packed decimal (Unsigned)')
        elif code == 11:
            return ('RB', 'Floating point binary')
        elif code == 12:
            return ('RBHEX', 'Floating point binary - hexadecimal')
        elif code == 15:
            return ('Z', 'Zoned decimal')
        elif code == 16:
            return ('N', 'N format - unsigned with leading zeros')
        elif code == 17:
            return ('E', 'E format - with explicit power of ten')
        elif code == 20:
            return ('DATE', 'Date format dd-mmm-yyyy')
        elif code == 21:
            return ('TIME', 'Time format hh:mm:ss.s')
        elif code == 22:
            return ('DATETIME', 'Date and time')
        elif code == 23:
            return ('ADATE', 'Date in mm/dd/yyyy form')
        elif code == 24:
            return ('JDATE', 'Julian date - yyyyddd')
        elif code == 25:
            return ('DTIME', 'Date-time dd hh:mm:ss.s')
        elif code == 26:
            return ('WKDAY', 'Day of the week')
        elif code == 27:
            return ('MONTH', 'Month')
        elif code == 28:
            return ('MOYR', 'mmm yyyy')
        elif code == 29:
            return ('QYR', 'q Q yyyy')
        elif code == 30:
            return ('WKYR', 'ww WK yyyy')
        elif code == 31:
            return ('PCT', 'Percent - F followed by "%"')
        elif code == 32:
            return ('DOT', 'Like COMMA, switching dot for comma')
        elif (code >= 33) and (code <= 37):
            return ('CCA-CCE', 'User-programmable currency format')
        elif code == 38:
            return ('EDATE', 'Date in dd.mm.yyyy style')
        elif code == 39:
            return ('SDATE', 'Date in yyyy/mm/dd style')
        else:
            return (None, None)

    def GetDateVar(self, code):
        datetypes = [   "Cycle","Year","Quarter","Month","Week","Day","Hour",
                        "Minute","Second","Observation","DATE_"]
        try:
            return datetypes[code]
        except IndexError:
            return None

    def EndReading(self, cd = None):
        """
        This method is only (I think) used in exceptional circumstances 
        and is designed for debugging. Valid files should never reach here.
        """
        # reached end-of-file
        print "Ended code %s with %s lines"%(cd, self.lncnt)
        print self.variablelist, self.numvars
        v = self.variablelist
        for i in v:
            #print i.labelvalues
            #print i.labelfields
            print i.typecode
        #print self.variablelist[0].data
        #THISSHOULDSTOPOPERATION
        sys.exit()



    # NEED TO ADD:

    # * working methods for various type 7 subtypes (all meta-data, some documented, not all)
    # * 'names' method to return names from all variables
    # * 'rows' method to return data from particular row
    # * labels method to return labels from all variables
    # * Any others?
