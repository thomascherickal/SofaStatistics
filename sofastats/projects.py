from pprint import pformat as pf
import wx

from . import my_globals as mg
from . import lib
from . import output
from . import settings_grid

BROKEN_VDT_MSG = _('This field is numeric, so any non-numeric keys in the '
    "source vdt file e.g. '1', '1a', 'apple' will be ignored. Did you manually"
    " edit it or generate your own vdt? Remember 1 or 1.0 is not equal to '1'") 

def valid_proj(subfolder, proj_filname):
    settings_path = mg.LOCAL_PATH / subfolder / proj_filname
    try:
        with open(settings_path, 'U', encoding='utf-8') as f:
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
    Get project file names (excluding paths but including .proj suffix).
    """
    proj_dir = mg.LOCAL_PATH / mg.PROJS_FOLDER
    proj_fils = [
        str(proj_fpath.name)
        for proj_fpath in proj_dir.iterdir()
        if proj_fpath.suffix == mg.PROJ_EXT]
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
        proj_notes = _('Default project so users can get started without '
            'having to understand projects. NB read only.')
    else:
        proj_notes = proj_dic['proj_notes']
    return proj_notes

def update_val_labels(val_dics, var_name, val_type, keyvals):
    """
    :param list val_dics: existing val-labels pairs for all variables
    :param str var_name: name of variable we are updating values for
    :param list keyvals: pairs of vals and their labels
    """
    new_val_dic = {}
    for key, value in keyvals:
        ## key always returned as a string but may need to store as number
        if key == '':
            continue
        elif val_type == settings_grid.COL_FLOAT:
            key = float(key)
        elif val_type == settings_grid.COL_INT:
            key = int(float(key))  ## so '12.0' -> 12. int('12.0') -> err
        new_val_dic[key] = value
    val_dics[var_name] = new_val_dic

def update_vdt(var_labels, var_notes, var_types, val_dics):
    # update lbl file
    cc = output.get_cc()
    with open(cc[mg.CURRENT_VDTS_PATH], 'w', encoding='utf-8') as f:
        f.write(f'var_labels={pf(var_labels)}')
        f.write(f'\n\nvar_notes={pf(var_notes)}')
        f.write(f'\n\nvar_types={pf(var_types)}')
        f.write(f'\n\n\nval_dics={pf(val_dics)}')
    wx.MessageBox(_("Settings saved to \"%s\"") % cc[mg.CURRENT_VDTS_PATH])

def sensibly_sorted_vals_and_lbls(vals_and_lbls):
    """
    :param list vals_and_lbls: List of (val, val_lbl) tuples

    Sort so None, '1', 2, 3, '4', 11, '12', 'Banana', 'apple'. In practice, the
    most important bit is the "numbers" being in order like
    '1', 2, 3, '4', 11, '12'.
    """
    nones = []
    nums4sorting = []
    strs = []
    for val, lbl in vals_and_lbls:
        if val is None:
            nones.append((val, lbl))
        else:
            try:
                num_val = float(val)
            except ValueError:
                strs.append((val, lbl))
            else:
                nums4sorting.append((num_val, val, lbl))
    nums4sorting.sort(key=lambda t: t[0])
    nums = [(val, lbl) for num_val, val, lbl in nums4sorting]
    strs.sort(key=lambda t: t[0])
    sensibly_sorted_keys = nones + nums + strs
    return sensibly_sorted_keys

def get_init_settings_data(val_dics, var_name, *, bolnumeric):
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
                    if not isinstance(key, (float, int)):  ## not going to worry about people wanting to add value labels to complex numbers or scientific notation ;-)
                        numeric_fld_but_non_numeric_keys = True
                    else:
                        init_settings_data.append((key, str(value)))
                init_settings_data.sort(key=lambda s: s[0])
                if numeric_fld_but_non_numeric_keys:
                    msg = BROKEN_VDT_MSG
            else:
                for key, value in val_dic.items():
                    init_settings_data.append((key, str(value)))
                init_settings_data = sensibly_sorted_vals_and_lbls(
                    init_settings_data)
    return init_settings_data, msg

def get_approp_var_names(var_types=None, min_data_type=mg.VAR_TYPE_CAT_KEY):
    """
    Get filtered list of variable names according to minimum data type. Use the
    information on the type of each variable to decide whether meets minimum
    e.g ordinal.
    """
    debug = False
    dd = mg.DATADETS_OBJ
    if min_data_type == mg.VAR_TYPE_CAT_KEY:
        var_names = [x for x in dd.flds]
    elif min_data_type == mg.VAR_TYPE_ORD_KEY:
        ## check for numeric as well in case user has manually misconfigured
        ## var_type in vdts file.
        var_names = [x for x in dd.flds
            if dd.flds[x][mg.FLD_BOLNUMERIC]
            and var_types.get(x) in (
                None, mg.VAR_TYPE_ORD_KEY, mg.VAR_TYPE_QUANT_KEY)]
    elif min_data_type == mg.VAR_TYPE_QUANT_KEY:
        ## check for numeric as well in case user has manually misconfigured
        ## var_type in vdts file.
        if debug:
            print(dd.flds)
        var_names = [x for x in dd.flds
            if dd.flds[x][mg.FLD_BOLNUMERIC]
            and var_types.get(x) in (None, mg.VAR_TYPE_QUANT_KEY)]
    else:
        raise Exception('get_approp_var_names() received a faulty '
            f'min_data_type: {min_data_type}')
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
            var_removed = True  ## e.g. may require QUANT and user changed to ORD. Variable will no longer appear in list. Cope!
    if (not drop_var) or var_removed:  ## use default if possible
        idx = 0
        if default:
            try:
                idx = choice_items.index(default)
            except ValueError:
                pass  ## OK if no default - use idx of 0.
    return idx

def get_proj_content(proj_notes, fil_var_dets, fil_css, fil_report, fil_script,
        default_dbe, default_dbs, default_tbls, con_dets):
    debug = False
    if debug:
        print(default_dbs)
        print(default_tbls)
        print(con_dets)
    content_list = []
    content_list.append(
        '# Windows file paths _must_ have double not single backslashes')
    content_list.append('# "C:\\\\Users\\\\demo.txt" is GOOD')
    content_list.append('# "C:\\Users\\demo.txt" is BAD')
    content = lib.escape_pre_write(proj_notes)
    content_end = content[-1]
    outer_quotes = "'''" if content_end == '"' else '"""'
    content_list.append(f'\nproj_notes = {outer_quotes}{content}{outer_quotes}')
    content_list.append(
        f'\nfil_var_dets = "{lib.escape_pre_write(fil_var_dets)}"')
    content_list.append(f'fil_css = "{lib.escape_pre_write(fil_css)}"')
    content_list.append(
        f'fil_report = "{lib.escape_pre_write(fil_report)}"')
    content_list.append(
        f'fil_script = "{lib.escape_pre_write(fil_script)}"')
    content_list.append(f'default_dbe = "{default_dbe}"')
    content_list.append(
        f'\ndefault_dbs = {lib.get_escaped_dict_pre_write(default_dbs)}')
    content_list.append(
        f'\ndefault_tbls = {lib.get_escaped_dict_pre_write(default_tbls)}')
    content_list.append(
        f'\ncon_dets = {lib.get_escaped_dict_pre_write(con_dets)}')
    ## no need to write open on start to proj file - if default, unwritable, if not default, doesn't start with it ;-) 
    # content_list.append(u'\nopen_on_start = %s' % mg.OPEN_ON_START)
    return '\n'.join(content_list)
