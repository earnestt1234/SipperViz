# -*- coding: utf-8 -*-
"""
Tools for SipperViz for inspecting plot code.
"""

import importlib.util
import inspect
import os

#see here:
    #https://stackoverflow.com/questions/61379330/problem-with-inspect-using-pyinstaller-can-get-source-of-class-but-not-function
homedir = os.path.dirname(os.path.realpath(__file__))

location = os.path.join(homedir, 'sipperplots.py')
spec = importlib.util.spec_from_file_location('sipperplots', location)
sipperplots = importlib.util.module_from_spec(spec) #my plots module
spec.loader.exec_module(sipperplots)

location = os.path.join(homedir, 'sipper.py')
spec = importlib.util.spec_from_file_location("sipper", location)
sipper = importlib.util.module_from_spec(spec) #my plots module
spec.loader.exec_module(sipper)

imports = """# importing libraries (may be redundant):

from collections import defaultdict
import datetime
import os
import warnings

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas import Timestamp
from pandas.plotting import register_matplotlib_converters
from scipy import stats
import seaborn as sns

register_matplotlib_converters()

#setting style
plt.style.use('seaborn-whitegrid')
"""

# relate each function name to its function from sipperplots
func_dict = {name:func for name, func in inspect.getmembers(sipperplots)}

#create a list of arguments that need to be formatted as a string
string_args = ['binsize', 'circ_var', 'pref_bins', 'pref_side', 'pref_metric',
               'averaging', 'avg_bins', 'avg_var']

# create strings of the helper function code
shade_funcs = ['drinkcount_cumulative', 'drinkduration_cumulative',
               'drinkcount_binned', 'drinkduration_binned',
               'side_preference', 'averaged_drinkcount',
               'averaged_drinkdruation']
shade_help = '# shading dark periods\n\n'
shade_help += inspect.getsource(sipperplots.convert_dt64_to_dt) + '\n'
shade_help += inspect.getsource(sipperplots.hours_between) + '\n'
shade_help += inspect.getsource(sipperplots.is_day_or_night) + '\n'
shade_help += inspect.getsource(sipperplots.night_intervals) + '\n'
shade_help += inspect.getsource(sipperplots.shade_darkness) + '\n'

date_format_funcs = ['drinkcount_cumulative', 'drinkduration_cumulative',
                     'drinkcount_binned', 'drinkduration_binned',
                     'side_preference', 'averaged_drinkcount',
                     'averaged_drinkdruation']
date_format_help = '# formatting date x-axis\n\n'
date_format_help += inspect.getsource(sipperplots.date_format_x) + '\n'

idi_funcs = ['interdrink_intervals', 'interdrink_intervals_byside',
             'interdrink_intervals_bycontent']
idi_help = '# interdrink intervals\n\n'
idi_help += inspect.getsource(sipperplots.get_any_idi) + '\n'
idi_help += inspect.getsource(sipperplots.get_side_idi) + '\n'
idi_help += inspect.getsource(sipperplots.get_content_idi) + '\n'
idi_help += inspect.getsource(sipperplots.setup_idi_axes) + '\n'

chrono_funcs = ['drinkcount_chronogram', 'drinkcount_chronogram_grouped',
                'drinkduration_chronogram', 'drinkduration_chronogram_grouped']
chrono_help = '# chronograms\n\n'
chrono_help += inspect.getsource(sipperplots.get_chronogram_vals) + '\n'

avg_funcs = ['averaged_drinkcount', 'averaged_drinkdruation']
avg_help = '# averaging\n\n'
avg_help += inspect.getsource(sipperplots.preproc_averaging) + '\n'
avg_help += inspect.getsource(sipperplots.format_averaging_axes) + '\n'

def add_quotes(string):
    output = '"' + string + '"'
    return output

def generate_code(sipper_plot):
    func = sipper_plot.func
    funcname = func.__name__
    output = ''

    # imports
    output += imports + '\n'

    # helper functions for loading sippers
    output += '# sipper loading helper functions\n'
    output += inspect.getsource(sipper.date_filter_okay) + '\n'
    output += inspect.getsource(sipper.SipperError) + '\n'
    output += inspect.getsource(sipper.SipperWarning) + '\n'
    output += inspect.getsource(sipper.is_concatable) + '\n'
    output += inspect.getsource(sipper.groupby_getcontentdict) + '\n'
    output += inspect.getsource(sipper.groupby_convertcontent) + '\n'

    # code to load sippers
    output += '# loading sipper files\n'
    output += inspect.getsource(sipper.Sipper) + '\n'

    # helper functions
    if funcname in shade_funcs:
        output += shade_help
    if funcname in date_format_funcs:
        output += date_format_help
    if funcname in idi_funcs:
        output += idi_help
    if funcname in chrono_funcs:
        output += chrono_help
    if funcname in avg_funcs:
        output += avg_help

    # plotting function
    output += '# plotting function\n'
    output += inspect.getsource(func) + '\n'

    # arguments
    output += '# arguments\n'
    func_args = inspect.getfullargspec(func).args
    used_args = sipper_plot.args
    # add specific **kwargs if they were used
    extra_args = ['date_filter']
    for k in extra_args:
        if k in used_args:
            func_args.append(k)

    #loop over all arguments used by the function
    sipper_varnames = {}
    for arg in func_args:
        #handle multiple sippers, else single sippers can
        #follow the else condition for formatting
        if arg == 'sipper':
            output += arg + ' = ' + str(used_args[arg]) + '\n'
            s = used_args[arg]
            if sipper_plot.content_dicts[s]:
                d = sipper_plot.content_dicts[s]
                output += arg + '.assign_contents({})\n'.format(d)
        elif arg == 'sippers':
            sipper_list = []
            for i, s in enumerate(used_args[arg]):
                variable = 'sipper{}'.format(i)
                sipper_varnames[s] = variable
                sipper_list.append(variable)
                output += variable + ' = ' + str(s) + '\n'
                if sipper_plot.content_dicts[s]:
                    d = sipper_plot.content_dicts[s]
                    output += variable + '.assign_contents({})\n'.format(d)
            var_list = '\nsippers = ' + '[%s]' % ', '.join(map(str, sipper_list)) + '\n'
            output += var_list
        elif arg == 'groups':
            output += ('\ngroups = ' + str(used_args['groups']) + '\n\n')
            for s in used_args['sippers']:
                for group in used_args['groups']:
                    if group in s.groups:
                        output += (sipper_varnames[s] + '.groups.append('
                                   + add_quotes(group) +')\n')
            output += '\n'
        else:
            formatted = str(used_args[arg])
            if arg in string_args:
                formatted = add_quotes(formatted)
            output += arg + ' = ' + formatted + '\n'

    # call
    output += '\n# calling the function\n'
    call = 'plot = ' + func.__name__ + '('
    for i, arg in enumerate(func_args, start=1):
        if i != len(func_args):
            call += arg + ', '
        else:
            call += arg + ')'
    output += call
    return output
