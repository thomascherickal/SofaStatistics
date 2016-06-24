from __future__ import print_function

import codecs
import os
import wx

import my_globals as mg
import lib
import output
import settings_grid

BROKEN_VDT_MSG = _(u"This field is numeric, so any non-numeric keys in the "
    u"source vdt file e.g. '1', '1a', 'apple' will be ignored. Did you manually"
    u" edit it or generate your own vdt? Remember 1 or 1.0 is not equal to '1'") 

def valid_proj(subfolder, proj_filname):
    settings_path = os.path.join(mg.LOCAL_PATH, subfolder, proj_filname)
    try:
        with codecs.open(settings_path, "U", encoding="utf-8") as f:
            f.close()
            valid_proj = True
    except IOError:
        valid_proj = False
    return valid_proj

def filname2projname(filname):
    projname = filname[:-len(mg.PROJ_EXT)]
    return projname

def get_projs():
    """
    NB includes .proj at end.
    os.listdir()
    
    Changed in version 2.3: On Windows NT/2k/XP and Unix, if path is a Unicode 
    object, the result will be a list of Unicode objects. Undecodable filenames 
    will still be returned as string objects.
    
    May need unicode results so always provide a unicode path. 
    """
    proj_fils = os.listdir(os.path.join(mg.LOCAL_PATH, mg.PROJS_FOLDER))
    proj_fils = [x for x in proj_fils if x.endswith(mg.PROJ_EXT)]
    proj_fils.sort()
    return proj_fils

def get_hide_db():
    return (len(get_projs()) < 2)

def get_proj_notes(fil_proj, proj_dic):
    """
    Read the proj file and extract the notes part.
    
    If the default project, return the translated notes rather than what is 
    actually stored in the file (notes in English).
    """
    if fil_proj == mg.DEFAULT_PROJ:
        proj_notes = _("Default project so users can get started without "
            "having to understand projects. NB read only.")
    else:
        proj_notes = proj_dic["proj_notes"]
    return proj_notes

def update_val_labels(val_dics, var_name, val_type, keyvals):
    """
    var_name -- name of variable we are updating values for
    val_dics -- existing val-labels pairs for all variables
    keyvals -- pairs of vals and their labels
    """
    new_val_dic = {}
    for key, value in keyvals:
        # key always returned as a string but may need to store as number
        if key == u"":
            continue
        elif val_type == settings_grid.COL_FLOAT:
            key = float(key)
        elif val_type == settings_grid.COL_INT:
            key = int(float(key)) # so '12.0' -> 12. int('12.0') -> err
        new_val_dic[key] = value
    val_dics[var_name] = new_val_dic
    
def update_vdt(var_labels, var_notes, var_types, val_dics):
    # update lbl file
    cc = output.get_cc()
    f = codecs.open(cc[mg.CURRENT_VDTS_PATH], "w", encoding="utf-8")
    f.write(u"var_labels=" + lib.UniLib.dic2unicode(var_labels))
    f.write(u"\n\nvar_notes=" + lib.UniLib.dic2unicode(var_notes))
    f.write(u"\n\nvar_types=" + lib.UniLib.dic2unicode(var_types))
    f.write(u"\n\n\nval_dics=" + lib.UniLib.dic2unicode(val_dics))
    f.close()
    wx.MessageBox(_("Settings saved to \"%s\"") % cc[mg.CURRENT_VDTS_PATH])

def val2sortnum(val):
    try:
        sortnum = float(val)
    except (ValueError, TypeError):
        sortnum = val # will be after the numbers - sort order seems to be None, 1, capital text, lower case text
    return sortnum

def sensible_sort_keys(input_list):
    """
    Sort so None, '1', 2, 3, '4', 11, '12', 'Banana', 'apple'. In practice, the 
    most important bit is the "numbers" being in order like '1', 2, 3, '4', 11, 
    '12'.
    """
    return input_list.sort(key=lambda s: val2sortnum(s[0]))

def get_init_settings_data(val_dics, var_name, bolnumeric):
    """
    Get initial settings to display value labels appropriately.
    
    Needs to handle the following scenarios appropriately:
    
    User has a numeric field. They are only allowed to enter value labels for 
    numeric keys. No problems will ever occur for this user.

    User has a text field. They can enter any text, including numbers 
    e.g. "Apple", "1", "1b" etc. I want these displayed in the correct sort 
    order but still being stored as string. So I want 'apple', 'banana','1','2',
    '3','11','99','100' ... This is necessary because people sometimes import 
    data with a text data type when it really should have been numeric. But they 
    hate it when the labels are '1','11','12','2','3' etc and fair enough. This 
    is a pretty common case.

    User has a numeric field. They have edited the vdt file outside of SOFA e.g. 
    manually, or they have generated it programmatically, and included some 
    non-numeric keys e.g. '1'. Anything that can be converted into a number 
    should be displayed as a number. Anything else should be discarded and the 
    user should be warned that this has happened and why.
    """
    init_settings_data = []
    msg = None
    if val_dics.get(var_name):
        val_dic = val_dics.get(var_name)
        if val_dic:
            if bolnumeric:
                numeric_fld_but_non_numeric_keys = False
                for key, value in val_dic.items():
                    if not isinstance(key, (float, int)): # not going to worry about people wanting to add value labels to complex numbers or scientific notation ;-)
                        numeric_fld_but_non_numeric_keys = True
                    else:
                        init_settings_data.append((key, unicode(value)))
                init_settings_data.sort(key=lambda s: s[0])
                if numeric_fld_but_non_numeric_keys:
                    msg = BROKEN_VDT_MSG
            else:
                for key, value in val_dic.items():
                    init_settings_data.append((key, unicode(value)))
                    sensible_sort_keys(init_settings_data)
    return init_settings_data, msg

def get_approp_var_names(var_types=None, min_data_type=mg.VAR_TYPE_CAT_KEY):
    """
    Get filtered list of variable names according to minimum data type. Use the 
        information on the type of each variable to decide whether meets 
        minimum e.g ordinal.
    """
    debug = False
    dd = mg.DATADETS_OBJ
    if min_data_type == mg.VAR_TYPE_CAT_KEY:
        var_names = [x for x in dd.flds]
    elif min_data_type == mg.VAR_TYPE_ORD_KEY:
        # check for numeric as well in case user has manually 
        # misconfigured var_type in vdts file.
        var_names = [x for x in dd.flds if dd.flds[x][mg.FLD_BOLNUMERIC] and
            var_types.get(x) in (None, mg.VAR_TYPE_ORD_KEY, 
            mg.VAR_TYPE_QUANT_KEY)]
    elif min_data_type == mg.VAR_TYPE_QUANT_KEY:
        # check for numeric as well in case user has manually 
        # misconfigured var_type in vdts file.
        if debug:
            print(dd.flds)
        var_names = [x for x in dd.flds if dd.flds[x][mg.FLD_BOLNUMERIC] and
            var_types.get(x) in (None, mg.VAR_TYPE_QUANT_KEY)]
    else:
        raise Exception(u"get_approp_var_names received a faulty min_data_"
            u"type: %s" % min_data_type)
    return var_names

def get_idx_to_select(choice_items, drop_var, var_labels, default):
    """
    Get index to select. If variable passed in, use that if possible.
    
    It will not be possible if it has been removed from the list e.g. because
    of a user reclassification of data type (e.g. was quantitative but has been 
    redefined as categorical); or because of a change of filtering.
    
    If no variable passed in, or it was but couldn't be used (see above), use 
    the default if possible. If not possible, select the first item.
    """
    var_removed = False
    if drop_var:
        item_new_version_drop = lib.GuiLib.get_choice_item(var_labels, drop_var)
        try:
            idx = choice_items.index(item_new_version_drop)
        except ValueError:
            var_removed = True # e.g. may require QUANT and user changed to 
            # ORD.  Variable will no longer appear in list. Cope!
    if (not drop_var) or var_removed: # use default if possible
        idx = 0
        if default:
            try:
                idx = choice_items.index(default)
            except ValueError:
                pass # OK if no default - use idx of 0.
    return idx

def get_proj_content(proj_notes, fil_var_dets, fil_css, fil_report, fil_script,
        default_dbe, default_dbs, default_tbls, con_dets):
    debug = False
    if debug:
        print(default_dbs)
        print(default_tbls)
        print(con_dets)
    content_list = []
    content_list.append(u"# Windows file paths _must_ have double not single "
        u"backslashes")
    content_list.append(u"# All file paths _must_ have a u before the"
        u" quote-enclosed string")
    content_list.append(u"""# u"C:\\\\Users\\\\demo.txt" is GOOD""")
    content_list.append(u"""# u"C:\\Users\\demo.txt" is BAD""")
    content_list.append(u"""# "C:\\\\Users\\\\demo.txt" is also BAD""")
    content_list.append(u"\nproj_notes = u\"\"\"%s\"\"\"" %
        lib.escape_pre_write(proj_notes))
    content_list.append(u"\nfil_var_dets = u\"%s\"" %
        lib.escape_pre_write(fil_var_dets))
    content_list.append(u"fil_css = u\"%s\"" %
        lib.escape_pre_write(fil_css))
    content_list.append(u"fil_report = u\"%s\"" %
        lib.escape_pre_write(fil_report))
    content_list.append(u"fil_script = u\"%s\"" %
        lib.escape_pre_write(fil_script))
    content_list.append(u"default_dbe = u\"%s\"" % default_dbe)
    content_list.append(u"\ndefault_dbs = "
        + lib.get_escaped_dict_pre_write(default_dbs))
    content_list.append(u"\ndefault_tbls = "
        + lib.get_escaped_dict_pre_write(default_tbls))
    content_list.append(u"\ncon_dets = "
        + lib.get_escaped_dict_pre_write(con_dets))
    ## no need to write open on start to proj file - if default, unwritable, if not default, doesn't start with it ;-) 
    # content_list.append(u"\nopen_on_start = %s" % mg.OPEN_ON_START)
    return u"\n".join(content_list)
