# -*- coding: utf-8 -*-
import time
import aft_messages as m
nme = __name__

def stat_rounding(number, decimal):
    magnitude = 10 ** decimal
    return round(number * magnitude) / magnitude

def timing(start=None):
    """
    measure time for general process:
    for start: var_name = timing()
    for strop: timing(var_name)

    Parameters
    ----------
    start : time of starting function
        the default is None.

    Returns
    -------
    start : float
        starting time
        
    """
    if start == None:
        start_time = time.perf_counter()
        return start_time
    else:
        stop = time.perf_counter()
        time_elapsed = stat_rounding((stop - start), 4)
        m.aft_message(f'process duration: {time_elapsed} s:', nme, 1)

def key_reader(all_keys, full_dict, user_keys, algorithm):
    """
    read and check all keys from a parameters
    file by cycling through all_keys

    Parameters
    ----------
    all_keys : dict
        all keys necessary for some algorithm type.
    full_dict : dict
        all possible keys.
    parameters : dict
        read in parameters from an instruction file.
    algorithm : string
        type of algorithm.

    Returns
    -------
    whole dict : dict
        all keys copied from parameters
        
    """
    whole_dict = full_dict.copy()
    key_dict = all_keys[algorithm]

    for key in key_dict:
        if key in user_keys:
            whole_dict[key] = user_keys[key]
        elif key not in user_keys:
            if full_dict[key] == None:
                m.aft_error(f'missing mandatory key: "{key}"', nme)
            else:
                whole_dict[key] = full_dict[key]

    for key in user_keys:
        if key not in key_dict and key in full_dict:
            m.aft_warning(
                f'key: "{key}" is not allowed for "{algorithm}"', nme, 0
                )
        elif key not in full_dict:
            m.aft_warning(f'unexpected parameter: "{key}" invalid', nme, 0)

    return whole_dict

def setting_reader(all_settings, user_settings):
    """
    read and check all keys from a settings
    by cycling through all_settings

    Parameters
    ----------
    settings : dict
        all settings for calculation

    Returns
    -------
    whole_settings : dict
        all settings
        
    """
    whole_settings = user_settings.copy()

    for skey in all_settings:
        if skey in user_settings:
            whole_settings[skey] = user_settings[skey]
        elif skey not in user_settings:
            whole_settings[skey] = all_settings[skey]

    return whole_settings