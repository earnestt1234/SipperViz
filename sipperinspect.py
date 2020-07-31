# -*- coding: utf-8 -*-
"""
Tools for SipperViz for inspecting plot code.
"""

import inspect

import sipper
import sipperplots

imports = """# importing libraries (may be redundant):

from collections import OrderedDict
import datetime
import os
import warnings

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas.plotting import register_matplotlib_converters

register_matplotlib_converters()
"""

# relate each function name to its function from sipperplots
func_dict = {name:func for name, func in inspect.getmembers(sipperplots)}

# create lists of plots grouped by helper functions needed
shade_funcs = ['drinkcount_cumulative', 'drinkduration_cumulative']
date_format_funcs = ['drinkcount_cumulative', 'drinkduration_cumulative']

# create strings of the helper function code
shade_help = '# shading dark periods\n\n'
shade_help += inspect.getsource(sipperplots.convert_dt64_to_dt) + '\n'
shade_help += inspect.getsource(sipperplots.hours_between) + '\n'
shade_help += inspect.getsource(sipperplots.is_day_or_night) + '\n'
shade_help += inspect.getsource(sipperplots.night_intervals) + '\n'
shade_help += inspect.getsource(sipperplots.shade_darkness) + '\n'

date_format_help = '# formatting date x-axis\n\n'
date_format_help += inspect.getsource(sipperplots.date_format_x) + '\n'

def generate_code(sipper_plot):
    func = sipper_plot.func
    output = ''

    # imports
    output += imports + '\n'

    # code to load sippers
    output += '# loading sipper files\n'
    output += inspect.getsource(sipperplots.date_filter_okay) + '\n'
    output += inspect.getsource(sipper.Sipper) + '\n'

    # helper functions
    if func in shade_funcs:
        output += shade_help
    if func in date_format_funcs:
        output += date_format_help

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
    for arg in func_args:
        #handle multiple sippers, else single sippers can
        #follow the else condition for formatting
        if arg == 'sippers':
            pass
        else:
            output += arg + ' = ' + str(used_args[arg]) + '\n'

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
