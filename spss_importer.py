import spss

# How to use this
f = "/home/g/projects/SOFA/storage"
sav = spss.SPSSFile(f, "1991 U.S. General Social Survey.sav")
sav.OpenFile()
sav.GetRecords()
# then use commands like this to access data & metadata

# FILE META-DATA:
print sav.eyecatcher # shows OS, machine, SPSS version etc
# sav.numOBSelements # puted number of variables (use x.numvars instead)
# sav.compressionswitch # 0 if not compressed
# sav.metastr # creation date, time, file label.
# sav.variablelist # list of variable objects contained within
print sav.numvars # number of variables.
# sav.documents # documentation record (if any)

# VARIABLE META-DATA:
vars = sav.variablelist
for var in vars:
    #print var.data # the data
    print var.name # 8-byte variable name
    print var.label # longer string label
    print var.decplaces # number of decimal places
    print var.colwidth # column width
    # vars.formattype # print format code (the exact data type)
    print var.labelvalues # values for substitute labels
    print var.labelfields # fields for substitute labels
# vars.missingd # list of discrete missing values
# vars.missingr # upper and lower bounds of a range of missing values