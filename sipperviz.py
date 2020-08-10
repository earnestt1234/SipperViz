"""Code to run SipViz."""

import datetime as dt
from collections import OrderedDict
import inspect
import os
from PIL import Image, ImageTk
import traceback
import tkinter as tk
from tkinter import ttk

import matplotlib as mpl
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
import pandas as pd
from tkcalendar import DateEntry

import plotdata
import sipper
import sipperinspect
import sipperplots

class SipperPlot:
    def __init__(self, name, func, args, data):
        self.name = name
        self.func = func
        self.args = args
        self.data = data
        self.content_dicts = {}
        self.populate_content_dicts()

    def populate_content_dicts(self):
        if 'sipper' in self.args:
            s = self.args['sipper']
            v = s.get_contents_dict() if s.sipperviz_assigned else {}
            self.content_dicts[s] = v
        elif 'sippers' in self.args:
            for s in self.args['sippers']:
                v = s.get_contents_dict() if s.sipperviz_assigned else {}
                self.content_dicts[s] = v

class SipperViz(tk.Tk):
    """Class for SipViz"""
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=C0103
    def __init__(self):
        super(SipperViz, self).__init__()
    #---constants/conversions
        #flags
        self.loading = False
        self.plotting = True

        #pretty names for Sipper attributes represented in info pane
        self.attr_conversion = {'Start':'start_date', 'End':'end_date',
                                'Duration':'duration', 'Device': 'device_no',
                                'Left Sipper Name':'left_name',
                                'Right Sipper Name':'right_name',
                                'Contents': 'contents',
                                'Version': 'version', 'Groups':'groups'}
        self.file_info_names = list(self.attr_conversion.keys())

        #way to covert times to integers
        self.times = []
        for xm in [' am', ' pm']:
            for num in range(0,12):
                time = str(num) + xm
                if time == '0 am':
                    time = 'midnight'
                if time == '0 pm':
                    time = 'noon'
                self.times.append(time)
        self.times_to_int = {time : num for num,time in enumerate(self.times)}

        #binsizes
        self.binsizes = ['5 minutes', '10 minutes', '15 minutes', '30 minutes', '1 hour']
        self.binsizes += [str(i) + ' hours' for i in range(2,25)]
        self.bin_convert = {}
        for val in self.binsizes:
            out =''
            for char in val:
                if char.isdigit():
                    out += char
            if 'minutes' in val:
                out += 'T'
            elif 'hour' in val:
                out += 'H'
            self.bin_convert[val] = out

        #link each plot function to a pretty name
        #also reverse the dictionary when needing to access the plot from the name
        self.plot_default_names = {
            sipperplots.drinkcount_cumulative:
                'Drink Count (Cumulative)',
            sipperplots.drinkduration_cumulative:
                'Drink Duration (Cumulative)',
            sipperplots.drinkcount_binned:
                'Drink Count (Binned)',
            sipperplots.drinkduration_binned:
                'Drink Duration (Binned)',
            sipperplots.interdrink_intervals:
                'Interdrink Intervals',
            sipperplots.interdrink_intervals_byside:
                'Interdrink Intervals (By Side)',
            sipperplots.interdrink_intervals_bycontent:
                'Interdrink Intervals (By Content)',
            sipperplots.drinkcount_chronogram:
                'Chronogram (Drink Count)',
            sipperplots.drinkcount_chronogram_grouped:
                'Grouped Chronogram (Drink Count)'}
        self.plot_names_to_funcs = {v:k for k,v in self.plot_default_names.items()}

        #link each plot to its function for retrieving data
        self.get_data_funcs = {k:v for k, v in
                               inspect.getmembers(plotdata, inspect.isfunction)}

        #link each plot to how sipperviz will create it
        self.plot_routes = {}
        #  for all plots which are iteratively created when multiple files selected
        for func in [
                sipperplots.drinkcount_cumulative,
                sipperplots.drinkcount_binned,
                sipperplots.drinkduration_cumulative,
                sipperplots.drinkduration_binned,
                sipperplots.drinkcount_chronogram]:
            self.plot_routes[func] = self.iter_plot

        #  for all plots which combine files into a single graph
        for func in [
                sipperplots.interdrink_intervals,
                sipperplots.interdrink_intervals_byside,
                sipperplots.interdrink_intervals_bycontent
                ]:
            self.plot_routes[func] = self.combo_plot

        #  for plots using groups
        for func in [
                sipperplots.drinkcount_chronogram_grouped,
                ]:
            self.plot_routes[func] = self.group_plot

        #pretty names for plot arguments, for plot details pane
        self.args_to_names = {'shade_dark':'shade dark',
                              'lights_on': 'lights on',
                              'lights_off': 'lights off',
                              'show_left': 'show left',
                              'show_right': 'show right',
                              'show_content': 'content',
                              'binsize': 'binning size',
                              'kde': 'kernel density estimation',
                              'logx': 'logarithmic x-axis',
                              'combine': 'combined data',
                              'circ_left': 'show left',
                              'circ_right': 'show right',
                              'circ_content': 'content',
                              'circ_show_indvl': 'show individual data',
                              'circ_var': 'error value'}

        #flag to prevent repetitive drawing of plots
        self.suspend_plot_raising = False

    #---data management
        self.loaded_sippers = []
        self.loaded_plots = OrderedDict()
        self.loaded_groups = []
        self.avail_contents = []
        self.avail_groups = []

    #---load button images
        icons = {'gear':"img/settings_icon.gif",
                 'bottle':'img/bottle_icon.png',
                 'delete_bottle':'img/delete_bottle.png',
                 'tack':'img/tack.png',
                 'paperclip':'img/paperclip.png',
                 'save':'img/save.png',
                 'script':'img/script.png',
                 'spreadsheet':'img/spreadsheet.png',
                 'graph':'img/graph.png',
                 'delete_graph':'img/delete_graph.png',
                 'picture':'img/picture.png',
                 'palette':'img/palette.png',
                 'drop':'img/drop.png',
                 'swap':'img/swap.png'}
        self.icons = {}
        for k, v in icons.items():
            image = Image.open(v).resize((25, 25))
            self.icons[k] = ImageTk.PhotoImage(image)

    #---create whole window
        self.title('SipperViz')
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.main_frame = tk.Frame(self)
        self.main_frame.grid(row=0, column=0, sticky='nsew')
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)

    #---create plot settings window
        self.plot_settings_window = tk.Toplevel(self)
        self.plot_settings_window.withdraw()
        self.plot_settings_window.title('Plotting Settings')
        self.plot_settings_tabs = ttk.Notebook(self.plot_settings_window)
        self.plot_settings_tabs.pack(fill='both', expand=1)
        self.plot_settings_window.protocol("WM_DELETE_WINDOW",
                                           self.plot_settings_window.withdraw)

    #---plot settings
        # all plots
        self.allplot_settings = tk.Frame(self.plot_settings_window)
        self.plot_settings_tabs.add(self.allplot_settings, text='All Plots')
        self.allplots_top = tk.Frame(self.allplot_settings)
        self.allplots_top.grid(row=0, column=0, sticky='nsew')

        self.date_filter_val = tk.BooleanVar()
        self.date_filter_val.set(False)
        self.date_filter_box = ttk.Checkbutton(self.allplots_top,
                                               text='Globally filter dates',
                                               var=self.date_filter_val,
                                               command=self.set_date_filter_state)
        self.dfilter_s_label = tk.Label(self.allplots_top,
                                        text='Start date/time')
        self.dfilter_e_label = tk.Label(self.allplots_top,
                                        text='End date/time')
        self.dfilter_s_date = DateEntry(self.allplots_top, width=10)
        self.dfilter_e_date = DateEntry(self.allplots_top, width=10)
        self.dfilter_s_hour = ttk.Combobox(self.allplots_top,
                                           values=self.times,
                                           width=10)
        self.dfilter_e_hour = ttk.Combobox(self.allplots_top,
                                           values=self.times,
                                           width=10)
        self.dfilter_s_hour.set('noon')
        self.dfilter_e_hour.set('noon')
        self.shade_dark_val = tk.BooleanVar()
        self.shade_dark_val.set(True)
        self.shade_dark_box = ttk.Checkbutton(self.allplots_top,
                                              variable=self.shade_dark_val,
                                              text='Shade dark periods (set light cycle under General Settings)')
        self.date_filter_box.grid(row=0, column=0, sticky='w', padx=20, pady=5)
        self.dfilter_s_label.grid(row=1, column=0, sticky='w', padx=40)
        self.dfilter_s_date.grid(row=1, column=1, sticky='nsw')
        self.dfilter_s_hour.grid(row=1, column=2, sticky='nsw')
        self.dfilter_e_label.grid(row=2, column=0, sticky='w', padx=40)
        self.dfilter_e_date.grid(row=2, column=1, sticky='nsw')
        self.dfilter_e_hour.grid(row=2, column=2, sticky='nsw')
        self.shade_dark_box.grid(row=3, column=0, sticky='w', padx=20, pady=5)

        # content
        self.contentselect_tab = tk.Frame(self.plot_settings_window)
        self.plot_settings_tabs.add(self.contentselect_tab, text='Contents')
        self.contentselect_frame = tk.Frame(self.contentselect_tab)
        self.contentselect_frame.grid(row=0, column=0, sticky='nsew', padx=20, pady=20)
        self.contentselect = ttk.Treeview(self.contentselect_frame, height=8,
                                          columns=['Contents'])
        self.contentselect.column('Contents', width=230)
        self.contentselect.heading(0, text='Contents')
        self.contentselect['show'] = 'headings'
        self.contentselect_scroll = ttk.Scrollbar(self.contentselect_frame,
                                                  command=self.contentselect.yview,)
        self.contentselect.configure(yscrollcommand=self.contentselect_scroll.set)

        p1 = 'All the liquids assigned to the loaded Sippers will show up here. '
        p2 = 'Contents selected here will be used in plots when the '
        p3 = '"Show contents" box is ticked for any given plot.'
        text = p1 + p2 + p3
        self.contentselect_text = tk.Label(self.contentselect_frame,
                                           text=text, justify='left',
                                           wraplength=300)
        self.contentselect.grid(row=0, column=0, sticky='nsw', padx=(20,0))
        self.contentselect_scroll.grid(row=0, column=1, sticky='nsw')
        self.contentselect_text.grid(row=0, column=2, sticky='new', padx=20)

        # groups
        self.groupselect_tab = tk.Frame(self.plot_settings_window)
        self.plot_settings_tabs.add(self.groupselect_tab, text='Groups')
        self.groupselect_frame = tk.Frame(self.groupselect_tab)
        self.groupselect_frame.grid(row=0, column=0, sticky='nsew', padx=20, pady=20)
        self.groupselect = ttk.Treeview(self.groupselect_frame, height=8,
                                        columns=['Groups'])
        self.groupselect.column('Groups', width=230)
        self.groupselect.heading(0, text='Groups')
        self.groupselect['show'] = 'headings'
        self.groupselect_scroll = ttk.Scrollbar(self.groupselect_frame,
                                                command=self.groupselect.yview,)
        self.groupselect.configure(yscrollcommand=self.groupselect_scroll.set)

        p1 = 'All loaded Groups will appear here.  '
        p2 = 'Groups selected here will be used when creating plots '
        p3 = 'that use Groups (i.e. Grouped Chonrograms).  '
        p4 = 'Groups can be edited from the main Groups button in SipperViz.'
        text = p1 + p2 + p3 + p4
        self.groupselect_text = tk.Label(self.groupselect_frame,
                                         text=text, justify='left',
                                         wraplength=300)
        self.groupselect.grid(row=0, column=0, sticky='nsw', padx=(20,0))
        self.groupselect_scroll.grid(row=0, column=1, sticky='nsw')
        self.groupselect_text.grid(row=0, column=2, sticky='new', padx=20)

        # drinks
        self.drink_settings = tk.Frame(self.plot_settings_window)
        self.plot_settings_tabs.add(self.drink_settings,
                                    text='Drink Plots')
        s1 = 'The following settings affect the Drink Count (Cumulative), '
        s2 = 'Drink Count (Binned), Drink Duration (Cumulative), and '
        s3 = 'Drink Duration (Binned) plots.'
        text = s1 + s2 + s3
        self.drink_settings_label = tk.Label(self.drink_settings, text=text,
                                             wraplength=600, justify='left')
        self.drink_showleft_val = tk.BooleanVar()
        self.drink_showleft_val.set(True)
        self.drink_showleft_box = ttk.Checkbutton(self.drink_settings,
                                                  variable=self.drink_showleft_val,
                                                  text='Show left sipper')
        self.drink_showright_val = tk.BooleanVar()
        self.drink_showright_val.set(True)
        self.drink_showright_box = ttk.Checkbutton(self.drink_settings,
                                                   variable=self.drink_showright_val,
                                                   text='Show right sipper')
        self.drink_showcontent_val = tk.BooleanVar()
        self.drink_showcontent_val.set(True)
        self.drink_showcontent_box = ttk.Checkbutton(self.drink_settings,
                                                     variable=self.drink_showcontent_val,
                                                     text='Show contents (see Content tab)')
        self.drink_binsize_label = tk.Label(self.drink_settings,
                                            text='Bin size for binned plots')
        self.drink_binsize_menu = ttk.Combobox(self.drink_settings,
                                               values=self.binsizes)
        self.drink_binsize_menu.set('1 hour')

        self.drink_settings_label.grid(row=0, column=0, sticky='nsew', padx=20, pady=5,
                                       columnspan=2)
        self.drink_showleft_box.grid(row=1, column=0, sticky='w', padx=20, pady=5)
        self.drink_showright_box.grid(row=2, column=0, sticky='w', padx=20, pady=5)
        self.drink_showcontent_box.grid(row=3, column=0, sticky='w', padx=20, pady=5)
        self.drink_binsize_label.grid(row=4, column=0, sticky='w', padx=20, pady=5)
        self.drink_binsize_menu.grid(row=4, column=1, sticky='nsew', padx=20, pady=5)

        # idi
        self.idi_settings = tk.Frame(self.plot_settings_window)
        self.plot_settings_tabs.add(self.idi_settings,
                                    text='Interdrink Intervals')
        s1 = 'The following settings affect Interdrink Intervals plots'
        text = s1
        self.idi_settings_label = tk.Label(self.idi_settings, text=text,
                                           wraplength=600, justify='left')
        self.kde_val = tk.BooleanVar()
        self.kde_val.set(True)
        self.kde_box = ttk.Checkbutton(self.idi_settings, var=self.kde_val,
                                       text='Include kernel density estimation')
        self.logx_val = tk.BooleanVar()
        self.logx_val.set(True)
        self.logx_box = ttk.Checkbutton(self.idi_settings, var=self.logx_val,
                                        text='Plot on a logarithmic x-axis')
        self.combine_idi_val = tk.BooleanVar()
        self.combine_idi_val.set(True)
        self.combine_idi_box = ttk.Checkbutton(self.idi_settings,
                                               var=self.combine_idi_val,
                                               text='Combine data into one curve')

        self.idi_settings_label.grid(row=0, column=0, sticky='nsew', padx=20, pady=5)
        self.kde_box.grid(row=1, column=0, sticky='nsew', padx=20, pady=5)
        self.logx_box.grid(row=2, column=0, sticky='nsew', padx=20, pady=5)
        self.combine_idi_box.grid(row=3, column=0, sticky='nsew', padx=20, pady=5)

        #circadian
        self.circ_settings = tk.Frame(self.plot_settings_window)
        self.plot_settings_tabs.add(self.circ_settings,
                                    text='Circadian')
        s1 = 'The following settings affect the Chronogram (Drink Count) plots'
        s2 = ''
        s3 = ''
        text = s1 + s2 + s3
        self.circ_settings_label = tk.Label(self.circ_settings, text=text,
                                            wraplength=600, justify='left')
        self.circ_showleft_val = tk.BooleanVar()
        self.circ_showleft_val.set(True)
        self.circ_showleft_box = ttk.Checkbutton(self.circ_settings,
                                                  variable=self.circ_showleft_val,
                                                  text='Show left sipper')
        self.circ_showright_val = tk.BooleanVar()
        self.circ_showright_val.set(True)
        self.circ_showright_box = ttk.Checkbutton(self.circ_settings,
                                                   variable=self.circ_showright_val,
                                                   text='Show right sipper')
        self.circ_showcontent_val = tk.BooleanVar()
        self.circ_showcontent_val.set(True)
        self.circ_showcontent_box = ttk.Checkbutton(self.circ_settings,
                                                     variable=self.circ_showcontent_val,
                                                     text='Show contents (see Content tab)')
        self.circ_showindvl_val = tk.BooleanVar()
        self.circ_showindvl_val.set(False)
        self.circ_showindvl_box = ttk.Checkbutton(self.circ_settings,
                                                  variable=self.circ_showindvl_val,
                                                  text='Display data for individual files')
        self.circ_var_label = tk.Label(self.circ_settings, text='Error value')
        self.circ_var_menu = ttk.Combobox(self.circ_settings,
                                          values=['SEM', 'STD', 'None'])
        self.circ_var_menu.set('SEM')
        self.circ_settings_label.grid(row=0, column=0, sticky='nsew', padx=20, pady=5,
                                       columnspan=2)
        self.circ_showleft_box.grid(row=1, column=0, sticky='w', padx=20, pady=5)
        self.circ_showright_box.grid(row=2, column=0, sticky='w', padx=20, pady=5)
        self.circ_showcontent_box.grid(row=3, column=0, sticky='w', padx=20, pady=5)
        self.circ_showindvl_box.grid(row=4, column=0, sticky='w', padx=20, pady=5)
        self.circ_var_label.grid(row=5, column=0, sticky='w', padx=20, pady=5)
        self.circ_var_menu.grid(row=5, column=1, sticky='w', padx=20, pady=5)

    #---create general settings window
        self.general_settings = tk.Toplevel(self)
        self.general_settings.withdraw()
        self.general_settings.title('General settings')
        self.general_settings.protocol("WM_DELETE_WINDOW",
                                              self.general_settings.withdraw)

    #---populate general settings window
        self.lightson_label = tk.Label(self.general_settings, text='Lights on')
        self.lightsoff_label = tk.Label(self.general_settings, text='Lights off')
        self.lightson_menu = ttk.Combobox(self.general_settings, width=10,
                                          values=self.times)
        self.lightson_menu.set('7 am')
        self.lightsoff_menu = ttk.Combobox(self.general_settings, width=10,
                                           values=self.times)
        self.lightsoff_menu.set('7 pm')
        self.lightson_label.grid(row=0, column=0, sticky='nsw', padx=20)
        self.lightson_menu.grid(row=0,column=1, sticky='nsew', padx=20)
        self.lightsoff_label.grid(row=1, column=0, sticky='nsw', padx=20)
        self.lightsoff_menu.grid(row=1,column=1, sticky='nsew', padx=20)

    #---create assign contents window
        self.contents_window = tk.Toplevel(self)
        self.contents_window.withdraw()
        self.contents_window.title('Assign Sipper contents')
        self.contents_window.resizable(False, False)
        self.contents_window.protocol("WM_DELETE_WINDOW",
                                      self.close_content_window)

    #---widgets for assign contents window
        self.assign_frame1 = tk.Frame(self.contents_window)
        s1 = 'Enter start and end times for left and right bottle contents.'
        s2 = 'Contents will be assigned to Sippers currently selected in the file view,'
        s3 = 'and they will be assigned in order from top to bottom.'
        intro = ' '.join([s1, s2, s3])
        self.contents_intro = tk.Label(self.assign_frame1, text=intro,
                                       wraplength=800, justify='left')
        self.assign_frame2 = tk.Frame(self.contents_window)
        self.sdate_label = tk.Label(self.assign_frame2, text='Start date')
        self.shour_label = tk.Label(self.assign_frame2, text='Start hour')
        self.edate_label = tk.Label(self.assign_frame2, text='End date')
        self.ehour_label = tk.Label(self.assign_frame2, text='End hour')
        self.lcontent_label = tk.Label(self.assign_frame2,
                                       text='Left bottle content')
        self.rcontent_label = tk.Label(self.assign_frame2,
                                       text='Right bottle content')
        self.sdate_entry = DateEntry(self.assign_frame2, width=10)
        self.shour_entry = ttk.Combobox(self.assign_frame2, width=10,
                                        values=self.times)
        self.shour_entry.set('noon')
        self.edate_entry = DateEntry(self.assign_frame2, width=10)
        self.ehour_entry = ttk.Combobox(self.assign_frame2, width=10,
                                        values=self.times)
        self.ehour_entry.set('noon')
        self.lcontent_val = tk.StringVar()
        self.lcontent_val.set('')
        self.lcontent_val.trace_add('write', self.update_content_buttons)
        self.lcontent_entry = tk.Entry(self.assign_frame2, width=10,
                                       textvariable=self.lcontent_val)
        self.rcontent_val = tk.StringVar()
        self.rcontent_val.set('')
        self.rcontent_val.trace_add('write', self.update_content_buttons)
        self.rcontent_entry = tk.Entry(self.assign_frame2, width=10,
                                       textvariable=self.rcontent_val)
        self.swapcontent = tk.Button(self.assign_frame2,
                                     image=self.icons['swap'],
                                     command=self.swapcontents,
                                     width=20)
        labels = ['Start', 'End', 'Left', 'Right']
        self.assign_content_view = ttk.Treeview(self.contents_window,
                                                columns=labels,
                                                selectmode='browse')
        self.assign_frame4 = tk.Frame(self.contents_window)
        self.content_add = tk.Button(self.assign_frame4, text='Add',
                                     command=self.add_content)
        self.content_delete = tk.Button(self.assign_frame4, text='Delete',
                                        command=self.delete_content)
        self.content_moveup = tk.Button(self.assign_frame4, text='Move Up',
                                        command=lambda b=-1: self.move_content(b))
        self.content_movedown = tk.Button(self.assign_frame4, text='Move Down',
                                          command=lambda b=1: self.move_content(b))
        self.content_assign = tk.Button(self.assign_frame4, text='Assign',
                                        command=self.assign_content)
        self.content_cancel = tk.Button(self.assign_frame4, text="Cancel",
                                        command=self.close_content_window)

        for i, name in enumerate(labels):
            self.assign_content_view.column(name, width=150)
            self.assign_content_view.heading(i, text=name)
        self.assign_content_view['show'] = 'headings'
        self.assign_content_view.bind('<<TreeviewSelect>>',
                                      self.update_content_buttons)

        self.assign_frame1.grid(row=1, column=0, sticky='nsew')
        self.assign_frame2.grid(row=2, column=0, sticky='nsew')
        self.assign_content_view.grid(row=3, column=0, sticky='nsew', pady=(30,0))
        self.assign_frame4.grid(row=4, column=0, sticky='nsew')
        self.contents_intro.grid(row=0, column=0, sticky='nsew', pady=(30,20), padx=30)
        self.sdate_label.grid(row=1, column=0, sticky='w', padx=20)
        self.sdate_entry.grid(row=1, column=2, sticky='nsw')
        self.shour_label.grid(row=2, column=0, sticky='w', padx=20)
        self.shour_entry.grid(row=2, column=2, sticky='nsw')
        self.edate_label.grid(row=3, column=0, sticky='w', padx=20)
        self.edate_entry.grid(row=3, column=2, sticky='nsw')
        self.ehour_label.grid(row=4, column=0, sticky='w', padx=20)
        self.ehour_entry.grid(row=4, column=2, sticky='nsw')
        self.lcontent_label.grid(row=5, column=0, sticky='w', padx=20)
        self.lcontent_entry.grid(row=5, column=2, sticky='nsew')
        self.rcontent_label.grid(row=6, column=0, sticky='w', padx=20)
        self.rcontent_entry.grid(row=6, column=2, sticky='nsew')
        self.swapcontent.grid(row=5, column=3, sticky='nsw', rowspan=2, padx=20)
        self.content_add.grid(row=0, column=0, sticky='nsew', padx=10, pady=5)
        self.content_delete.grid(row=0, column=1, sticky='nsew', padx=10, pady=5)
        self.content_moveup.grid(row=0, column=2, sticky='nsew', padx=10, pady=5)
        self.content_movedown.grid(row=0, column=3, sticky='nsew', padx=10, pady=5)
        self.content_assign.grid(row=0, column=4, sticky='nsew', padx=10, pady=5)
        self.content_cancel.grid(row=0, column=5, sticky='nsew', padx=10, pady=5)
        for i in range(6):
            self.assign_frame4.columnconfigure(i, weight=1)

    #---create make plot window
        self.makeplot_window = tk.Toplevel(self)
        self.makeplot_window.grid_rowconfigure(0, weight=1)
        self.makeplot_window.withdraw()
        self.makeplot_window.resizable(False, True)
        self.makeplot_window.title('Create Plots')
        self.makeplot_window.protocol("WM_DELETE_WINDOW",
                                      self.close_makeplot_window)

    #---populate makeplots window
        self.makeplot_selectionframe = tk.Frame(self.makeplot_window)
        self.makeplot_selectionframe.grid_rowconfigure(0, weight=1)
        self.makeplot_selection = ttk.Treeview(self.makeplot_selectionframe,
                                               height=12)
        self.makeplot_selection.column('#0', width=230)
        self.makeplot_selection.heading('#0', text='Plots')
        self.makeplot_drinks = self.makeplot_selection.insert('', 1, text='Drink Plots',
                                                              open=True)
        self.makeplot_selection.insert(self.makeplot_drinks, 1, text='Drink Count (Cumulative)')
        self.makeplot_selection.insert(self.makeplot_drinks, 2, text='Drink Count (Binned)')
        self.makeplot_selection.insert(self.makeplot_drinks, 3, text='Drink Duration (Cumulative)')
        self.makeplot_selection.insert(self.makeplot_drinks, 4, text='Drink Duration (Binned)')
        self.makeplot_idi = self.makeplot_selection.insert('', 2, text='IDI',
                                                           open=True)
        self.makeplot_selection.insert(self.makeplot_idi, 1, text='Interdrink Intervals')
        self.makeplot_selection.insert(self.makeplot_idi, 2, text='Interdrink Intervals (By Side)')
        self.makeplot_selection.insert(self.makeplot_idi, 3, text='Interdrink Intervals (By Content)')
        self.makeplot_circ = self.makeplot_selection.insert('', 3, text='Circadian',
                                                            open=True)
        self.makeplot_selection.insert(self.makeplot_circ, 1, text='Chronogram (Drink Count)')
        self.makeplot_selection.insert(self.makeplot_circ, 3, text='Grouped Chronogram (Drink Count)')
        self.makeplot_selection.bind('<<TreeviewSelect>>', self.update_makeplot_run)
        self.makeplot_scroll = ttk.Scrollbar(self.makeplot_selectionframe,
                                             command=self.makeplot_selection.yview,)
        self.makeplot_selection.configure(yscrollcommand=self.makeplot_scroll.set)
        self.makeplot_selection.grid(row=0, column=0, sticky='nsw')
        self.makeplot_scroll.grid(row=0, column=1, sticky='nsw')

        self.makeplot_run_button = tk.Button(self.makeplot_window, text='Run',
                                             command=self.run_makeplots)
        self.makeplot_cancel_button = tk.Button(self.makeplot_window, text='Cancel',
                                                command=self.close_makeplot_window)

        self.makeplot_selectionframe.grid(row=0, column=0, sticky='nsew', columnspan=2)
        self.makeplot_run_button.grid(row=1, column=0, sticky='nsew')
        self.makeplot_cancel_button.grid(row=1, column=1, sticky='nsew')

    #---create groups window
        self.groups_window = tk.Toplevel(self)
        self.groups_window.resizable(False, True)
        self.groups_window.withdraw()
        self.groups_window.title('Group Manager')
        self.groups_window.protocol("WM_DELETE_WINDOW",
                                    self.groups_window.withdraw)

    #---populate groups window
        self.groupview_frame = tk.Frame(self.groups_window)
        self.groupview = ttk.Treeview(self.groupview_frame, height=12)
        self.groupview.bind('<<TreeviewSelect>>', self.update_groupview_buttons)
        self.groupview.heading('#0', text='Groups')
        self.groupview.column('#0', width=230)
        self.groupview_scroll = ttk.Scrollbar(self.groupview_frame,
                                              command=self.groupview.yview,)
        self.groupview.configure(yscrollcommand=self.groupview_scroll.set)
        self.groupview_frame.grid_rowconfigure(0,weight=1)
        self.groupview.grid(row=0, column=0, sticky='nsw')
        self.groupview_scroll.grid(row=0,column=1,sticky='nsw')

        self.group_create = tk.Button(self.groups_window, text='Create Group',
                                      command=self.create_group)
        self.group_add = tk.Button(self.groups_window, text='Add Files to Group',
                                   command=self.group_add)
        self.group_remove = tk.Button(self.groups_window, text='Remove Files from Group',
                                      command=self.group_remove)
        self.group_select = tk.Button(self.groups_window, text='Select Files in these Groups',
                                      command=self.group_select)
        self.group_delete = tk.Button(self.groups_window, text='Delete Group',
                                      command=self.group_delete)
        self.group_save = tk.Button(self.groups_window, text='Save Groups')
        self.group_load = tk.Button(self.groups_window, text='Load Groups')

        self.groupview_frame.grid(row=0, column=0, sticky='nsew')
        self.groups_window.grid_rowconfigure(0, weight=1)
        self.group_create.grid(row=1, column=0, sticky='nsew')
        self.group_add.grid(row=2, column=0, sticky='nsew')
        self.group_remove.grid(row=3, column=0, sticky='nsew')
        self.group_select.grid(row=4, column=0, sticky='nsew')
        self.group_delete.grid(row=5, column=0, sticky='nsew')
        self.group_save.grid(row=6, column=0, sticky='nsew')
        self.group_load.grid(row=7, column=0, sticky='nsew')

    #---create loading window
        self.loading_window = tk.Toplevel(self)
        self.loading_window.resizable(False, False)
        self.loading_window.withdraw()
        self.loading_window.protocol("WM_DELETE_WINDOW",
                                     self.loading_window.withdraw)

    #---populate loading window
        self.loading_label1 = tk.Label(self.loading_window,
                                       text='Loading File:')
        self.loading_str = tk.StringVar()
        self.loading_str.set('')
        self.loading_label2 = tk.Label(self.loading_window,
                                       textvariable=self.loading_str)
        self.loading_bar = ttk.Progressbar(self.loading_window, orient='horizontal',
                                           mode='determinate', length=400)
        self.load_abort = tk.Button(self.loading_window, text='Abort',
                                    command=self.escape)

        self.loading_label1.grid(row=0, column=0, sticky='w', padx=20, pady=5)
        self.loading_label2.grid(row=0, column=1, sticky='w', padx=20, pady=5)
        self.loading_bar.grid(row=1, column=0, sticky='w', padx=20, pady=5,
                              columnspan=2)
        self.load_abort.grid(row=2, column=0, sticky='nsew', padx=20, pady=5,
                             columnspan=2)

    #---create treeview panes (left sash)
        self.left_sash = ttk.PanedWindow(self.main_frame, orient='vertical')

    #---create plot panes (right sash)
        self.right_sash = ttk.PanedWindow(self.main_frame, orient='vertical')

    #---menu bar
        self.menubar = tk.Menu(self.main_frame)
        self.config(menu=self.menubar)
        self.filemenu = tk.Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label='Load files', command=self.load_files)
        self.menubar.add_cascade(menu=self.filemenu, label='File')
        self.sippermenu = tk.Menu(self.menubar, tearoff=0)
        self.sippermenu.add_command(label='Assign contents', command=self.raise_content_window)
        self.sippermenu.add_command(label='Show/edit file contents',
                                    command=self.raise_content_window_for_file)
        self.sippermenu.add_command(label='Clear contents', command=self.clear_contents)
        self.menubar.add_cascade(menu=self.sippermenu, label='Sippers')
        self.plotmenu = tk.Menu(self.menubar, tearoff=0)
        self.plotmenu.add_command(label='Drink Count (Cumulative)', command=lambda:
                                  self.iter_plot(sipperplots.drinkcount_cumulative))
        self.plotmenu.add_command(label='Drink Count (Binned)', command=lambda:
                                  self.iter_plot(sipperplots.drinkcount_binned))
        self.plotmenu.add_command(label='Drink Duration (Cumulative)', command=lambda:
                                  self.iter_plot(sipperplots.drinkduration_cumulative))
        self.plotmenu.add_command(label='Drink Duration (Binned)', command=lambda:
                                  self.iter_plot(sipperplots.drinkduration_binned))
        self.plotmenu.add_separator()
        self.plotmenu.add_command(label='Interdrink Intervals', command=lambda:
                                  self.combo_plot(sipperplots.interdrink_intervals))
        self.plotmenu.add_command(label='Interdrink Intervals (By Side)', command=lambda:
                                  self.combo_plot(sipperplots.interdrink_intervals_byside))
        self.plotmenu.add_command(label='Interdrink Intervals (By Content)', command=lambda:
                                  self.combo_plot(sipperplots.interdrink_intervals_bycontent))
        self.plotmenu.add_separator()
        self.plotmenu.add_command(label='Chronogram (Drink Count)', command=lambda:
                                  self.iter_plot(sipperplots.drinkcount_chronogram))
        self.plotmenu.add_command(label='Grouped Chronogram (Drink Count)', command=lambda:
                                  self.group_plot(sipperplots.drinkcount_chronogram_grouped))
        self.menubar.add_cascade(menu=self.plotmenu, label='Create Plot')

    #---create main buttons
        self.button_frame = tk.Frame(self.main_frame)
        self.load_button = tk.Button(self.button_frame,
                                     image=self.icons['bottle'],
                                     text='Load', compound='top',
                                     borderwidth=0,
                                     command=self.load_files,
                                     width=40)
        self.delete_button = tk.Button(self.button_frame,
                                       image=self.icons['delete_bottle'],
                                       text='Delete', compound='top',
                                       borderwidth=0,
                                       command=self.delete_files,
                                       width=40)
        self.groups_button = tk.Button(self.button_frame,
                                       image=self.icons['paperclip'],
                                       text='Groups', compound='top',
                                       borderwidth=0,
                                       command=self.raise_group_window,
                                       width=40)
        self.concat_button = tk.Button(self.button_frame,
                                       image=self.icons['tack'],
                                       text='Concat', compound='top',
                                       borderwidth=0,
                                       command=self.concat_files,
                                       width=40)
        self.assign_button = tk.Button(self.button_frame,
                                       image=self.icons['drop'],
                                       text='Assign', compound='top',
                                       borderwidth=0,
                                       command=self.raise_content_window,
                                       width=40)
        self.savefile_button = tk.Button(self.button_frame,
                                         image=self.icons['save'],
                                         text='Save', compound='top',
                                         borderwidth=0,
                                         command=self.save_files,
                                         width=40)
        self.plot_button = tk.Button(self.button_frame,
                                     image=self.icons['graph'],
                                     text='Plot', compound='top',
                                     borderwidth=0,
                                     command=self.raise_makeplot_window,
                                     width=40)
        self.plot_save_button = tk.Button(self.button_frame,
                                          image=self.icons['picture'],
                                          text='Save', compound='top',
                                          borderwidth=0,
                                          command=self.save_plots,
                                          width=40)
        self.plot_data_button = tk.Button(self.button_frame,
                                          image=self.icons['spreadsheet'],
                                          text='Data', compound='top',
                                          borderwidth=0,
                                          command=self.save_plot_data,
                                          width=40)
        self.plot_code_button = tk.Button(self.button_frame,
                                          image=self.icons['script'],
                                          text='Code', compound='top',
                                          borderwidth=0,
                                          command=self.show_plot_code,
                                          width=40)
        self.plot_delete_button = tk.Button(self.button_frame,
                                            image=self.icons['delete_graph'],
                                            text='Delete', compound='top',
                                            borderwidth=0,
                                            command=self.delete_plots,
                                            width=40)
        self.plotopts_button = tk.Button(self.button_frame,
                                         image=self.icons['palette'],
                                         text='Plots', compound='top',
                                         borderwidth=0,
                                         command=self.plot_settings_window.deiconify,
                                         width=40)
        self.settings_button = tk.Button(self.button_frame,
                                         image=self.icons['gear'],
                                         text='General', compound='top',
                                         borderwidth=0,
                                         command=self.general_settings.deiconify,
                                         width=40)

    #---pack buttons, add separators, labels
        self.load_button.grid(row=0, column=0, sticky='nsew', pady=5,
                              padx=5)
        self.delete_button.grid(row=0, column=1, sticky='nsew', pady=5,
                                padx=5)
        self.savefile_button.grid(row=0, column=2, sticky='nsew', pady=5,
                                  padx=5)
        self.groups_button.grid(row=0, column=3, sticky='nsew', pady=5,
                                padx=5)
        self.concat_button.grid(row=0, column=4, sticky='nsew', pady=5,
                                padx=5)
        self.assign_button.grid(row=0, column=5, sticky='nsew', pady=5,
                                padx=5)
        self.files_label = tk.Label(self.button_frame, text='Files')
        self.files_label.grid(row=1, column=0, sticky='nsew',
                              columnspan=6, pady=(0, 5))
        self.sep1 = ttk.Separator(self.button_frame, orient='vertical')
        self.sep1.grid(row=0,column=6,sticky='nsew', pady=5, rowspan=2)
        self.plot_button.grid(row=0, column=7, sticky='nsew', pady=5,
                              padx=5)
        self.plot_save_button.grid(row=0, column=8, sticky='nsew', pady=5,
                                   padx=5)
        self.plot_delete_button.grid(row=0, column=9, sticky='nsew', pady=5,
                                     padx=5)
        self.plot_data_button.grid(row=0, column=10, sticky='nsew', pady=5,
                                   padx=5)
        self.plot_code_button.grid(row=0, column=11, sticky='nsew', pady=5,
                                   padx=5)
        self.plots_label = tk.Label(self.button_frame, text='Plots')
        self.plots_label.grid(row=1, column=7, sticky='nsew',
                              columnspan=5, pady=(0, 5))
        self.sep2 = ttk.Separator(self.button_frame, orient='vertical')
        self.sep2.grid(row=0,column=12,sticky='nsew', pady=5, rowspan=2)
        self.plotopts_button.grid(row=0, column=13, sticky='nsew', pady=5,
                                  padx=5)
        self.settings_button.grid(row=0, column=14, sticky='nsew', pady=5,
                                  padx=5)
        self.settings_label = tk.Label(self.button_frame, text='Settings')
        self.settings_label.grid(row=1, column=13, sticky='nsew',
                                 columnspan=2, pady=(0, 5))

    #---create file_view
        self.file_frame = tk.Frame(self.left_sash)
        self.file_view = ttk.Treeview(self.file_frame, height=16)
        self.file_view.heading('#0', text='Sippers')
        self.file_view.column('#0', width=230)
        self.files_scroll = ttk.Scrollbar(self.file_frame,
                                          command=self.file_view.yview,)
        self.file_view.configure(yscrollcommand=self.files_scroll.set)
        self.file_view.bind('<<TreeviewSelect>>', self.handle_file_select)
        self.file_frame.grid_rowconfigure(0,weight=1)
        self.file_view.grid(row=0, column=0, sticky='nsw')
        self.files_scroll.grid(row=0,column=1,sticky='nsw')

    #---create info view
        self.info_frame = tk.Frame(self.left_sash)
        self.info_view = ttk.Treeview(self.info_frame, selectmode='none',
                                      height=8)
        self.info_view.heading('#0', text='Details')
        self.info_view.column('#0', width=230)
        self.info_scroll = ttk.Scrollbar(self.info_frame,
                                         command=self.info_view.yview,)
        self.info_view.configure(yscrollcommand=self.info_scroll.set)
        self.info_frame.grid_rowconfigure(0, weight=1)
        self.info_view.grid(row=0, column=0, sticky='nsw')
        self.info_scroll.grid(row=0, column=1, sticky='nsw')

    #---create plotting area
        self.plot_frame = tk.Frame(self.main_frame)
        self.fig = mpl.figure.Figure(figsize=(7, 4), dpi=100)
        self.ax = self.fig.add_subplot()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.draw_idle()
        self.canvas.get_tk_widget().pack(side='bottom', fill='both', expand=1)
        self.nav_toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame)
        self.nav_toolbar.update()
        self.canvas._tkcanvas.pack(side='top', fill='both', expand=1)

    #---create plot list
        self.plot_list_frame = tk.Frame(self.right_sash)
        self.plot_list_frame.grid_rowconfigure(0, weight=1)
        self.plot_list = ttk.Treeview(self.plot_list_frame, height=12,
                                      columns=['Plots'])
        self.plot_list.column('Plots', width=230)
        self.plot_list.heading(0, text='Plots')
        self.plot_list['show'] = 'headings'
        self.plot_list.bind('<<TreeviewSelect>>', self.raise_plot_from_click)
        self.plot_scroll = ttk.Scrollbar(self.plot_list_frame,
                                          command=self.plot_list.yview, )
        self.plot_list.configure(yscrollcommand=self.plot_scroll.set)
        self.plot_list.grid(row=0, column=0, sticky='nsw')
        self.plot_scroll.grid(row=0, column=1, sticky='nsw')

    #---create plot info
        self.plot_info_frame = tk.Frame(self.right_sash)
        self.plot_info = ttk.Treeview(self.plot_info_frame, selectmode='browse',
                                      height=12)
        self.plot_info.heading('#0', text='Plot Info')
        self.plot_info.column('#0', width=230)
        self.plot_info_scroll = ttk.Scrollbar(self.plot_info_frame,
                                              command=self.plot_info.yview,)
        self.plot_info.configure(yscrollcommand=self.plot_info_scroll.set)
        self.plot_info_frame.grid_rowconfigure(0, weight=1)
        self.plot_info.grid(row=0, column=0, sticky='nsw')
        self.plot_info_scroll.grid(row=0, column=1, sticky='nsw')

    #---pack things for main frame
        self.button_frame.grid(row=0, column=0, sticky='nsew', columnspan=3)
        self.left_sash.grid(row=1, column=0, sticky='nsew')
        self.left_sash.grid_rowconfigure(0, weight=1)
        self.left_sash.add(self.file_frame)
        self.left_sash.add(self.info_frame)
        self.plot_frame.grid(row=1, column=1, sticky='nsew')
        self.right_sash.grid(row=1, column=2, sticky='nsew')
        self.right_sash.grid_rowconfigure(0, weight=1)
        self.right_sash.add(self.plot_list_frame)
        self.right_sash.add(self.plot_info_frame)

    #---bindings
        self.bind('<Escape>', self.escape)
        ctrla1 = '<Control-a>'
        ctrla2 = '<Control-A>'
        self.bind(ctrla1, self.select_all)
        self.bind(ctrla2, self.select_all)

    #---operations pre opening
        last_settings = 'memory/settings/LAST_USED.CSV'
        if os.path.isfile(last_settings):
            # self.load_settings_df(last_settings) #for testing
            try:
                self.load_settings_df(last_settings)
            except:
                print('Found LAST_USED settings but unable to load!')
        self.set_date_filter_state()
        self.update_all_buttons()

    #---file functions
    def load_files(self):
        file_types = [('All', '*.*'), ('Comma-Separated Values', '*.csv'),
                      ('Excel', '*.xls, *.xslx'),]
        files = tk.filedialog.askopenfilenames(title='Select FED3 Data',
                                               filetypes=file_types)

        if files:
            self.loading = True
            self.loading_window.deiconify()
            for file in files:
                if self.loading:
                    try:
                        self.loaded_sippers.append(sipper.Sipper(file))
                    except:
                        tb = traceback.format_exc()
                        print(tb)
                self.loading_str.set(file)
                self.loading_bar.step(1/len(files)*100)
                self.update()
            self.update_file_view()
            self.update_avail_contents()
            self.update_all_buttons()
            self.loading_window.withdraw()
            self.loading = False

    def delete_files(self):
        selected = [int(i) for i in self.file_view.selection()]
        for index in sorted(selected, reverse=True):
            del(self.loaded_sippers[index])
        self.update_file_view()
        self.update_avail_contents()
        self.update_all_buttons()
        self.display_details()

    def save_files(self):
        selected = [self.loaded_sippers[int(i)] for i in self.file_view.selection()]
        if len(selected) == 1:
            s = selected[0]
            filetypes = [('Comma-Separated Values', '*.csv')]
            savepath = tk.filedialog.asksaveasfilename(title='Save file',
                                                       defaultextension='.csv',
                                                       initialfile=s.basename,
                                                       filetypes=filetypes)
            if savepath:
                s.data.to_csv(savepath)
        elif len(selected) > 1:
            folder = tk.filedialog.askdirectory(title='Save multiple files')
            if folder:
                for s in selected:
                    savepath = os.path.join(folder, s.basename)
                    savepath = self.create_file_name(savepath)
                    s.data.to_csv(savepath)

    def concat_files(self):
        selected = [self.loaded_sippers[int(i)] for i in self.file_view.selection()]
        try:
            new = sipper.sipper_concat(selected)
            savepath = tk.filedialog.asksaveasfilename(title='Save concatenated file',
                                                       defaultextension='.csv',
                                                       filetypes=[('Comma-Separated Values', '*.csv')])
            if savepath:
                new.to_csv(savepath)
                new_file = sipper.Sipper(savepath)
                self.loaded_sippers.append(new_file)
                for s in selected:
                    self.loaded_sippers.remove(s)
                self.update_file_view()
        except sipper.SipperError:
            print('cant concat, add popup')

    def update_file_view(self):
        self.file_view.delete(*self.file_view.get_children())
        for i, s in enumerate(self.loaded_sippers):
            self.file_view.insert("", i, str(i), text=s.filename, tag='file')

    def update_all_buttons(self, *event):
        self.update_main_buttons()
        self.update_content_buttons()
        self.update_groupview_buttons()
        self.update_makeplot_run()
        self.update_avail_contents()
        self.update_avail_groups()

    def update_main_buttons(self, *event):
        #if files are selected
        if self.file_view.selection():
            self.delete_button.configure(state='normal')
            self.savefile_button.configure(state='normal')
            self.concat_button.configure(state='normal')
            self.assign_button.configure(state='normal')
        else:
            self.delete_button.configure(state='disabled')
            self.savefile_button.configure(state='disabled')
            self.concat_button.configure(state='disabled')
            self.assign_button.configure(state='disabled')
        #if plots are selected
        if self.plot_list.selection():
            self.plot_delete_button.configure(state='normal')
            self.plot_save_button.configure(state='normal')
            self.plot_data_button.configure(state='normal')
            self.plot_code_button.configure(state='normal')
        else:
            self.plot_delete_button.configure(state='disabled')
            self.plot_save_button.configure(state='disabled')
            self.plot_data_button.configure(state='disabled')
            self.plot_code_button.configure(state='disabled')

    def handle_file_select(self, *event):
        self.display_details()
        self.update_all_buttons()

    #---info pane functions
    def display_details(self, *event):
        self.info_view.delete(*self.info_view.get_children())
        selected = [self.loaded_sippers[int(i)]
                    for i in self.file_view.selection()]
        if len(selected) == 1:
            s = selected[0]
            for i, name in enumerate(self.file_info_names):
                attr = str(getattr(s, self.attr_conversion[name]))
                text = ' : '.join([name, attr])
                self.info_view.insert('', i, text=text)
        elif len(selected) > 1:
            mindate = min([s.start_date for s in selected])
            maxdate = max([s.end_date for s in selected])
            nos = list(set([s.device_no for s in selected]))
            groups = list(set([g for s in selected for g in s.groups]))
            self.info_view.insert('', 1, text='Selected : {}'.format(len(selected)))
            self.info_view.insert('', 2, text='Start : {}'.format(mindate))
            self.info_view.insert('', 3, text='End : {}'.format(maxdate))
            self.info_view.insert('', 4, text='Device #s: {}'.format(nos))
            self.info_view.insert('', 5, text='Groups: {}'.format(groups))

    #---routes from buttons to plots
    def iter_plot(self, func):
        self.plotting = True
        self.bad_date_sippers = []
        sippers = [self.loaded_sippers[int(i)]
                   for i in self.file_view.selection()]
        for i, s in enumerate(sippers):
            if self.plotting:
                self.ax.clear()
                all_args = self.get_settings_dict_as_args()
                func_args = inspect.getfullargspec(func).args
                args = {k:v for k,v in all_args.items() if k in func_args}
                if self.date_filter_val.get():
                    b,e = self.get_date_filter_dates()
                    if not sipperplots.date_filter_okay(s.data, b, e):
                            self.bad_date_sippers.append(s)
                            continue
                    else:
                        args['date_filter'] = b, e
                args['sipper'] = s
                args['ax'] = self.ax
                name = self.create_plot_name(self.plot_default_names[func])
                data = self.get_data_funcs[func.__name__](**args)
                plot = SipperPlot(name, func, args, data)
                self.loaded_plots[name] = plot
                self.plot_list.insert('', 'end', iid=plot.name, values=[plot.name])
                self.display_plot(plot, new=True)
        if self.bad_date_sippers:
            self.raise_dfilter_error()
        self.plotting = False

    def combo_plot(self, func):
        self.bad_date_sippers = []
        sippers = [self.loaded_sippers[int(i)]
                   for i in self.file_view.selection()]
        self.ax.clear()
        all_args = self.get_settings_dict_as_args()
        func_args = inspect.getfullargspec(func).args
        args = {k:v for k,v in all_args.items() if k in func_args}
        if self.date_filter_val.get():
            b,e = self.get_date_filter_dates()
            args['date_filter'] = b, e
            for s in sippers:
                if not sipperplots.date_filter_okay(s.data, b, e):
                        self.bad_date_sippers.append(s)
                        continue
        if self.bad_date_sippers:
            self.raise_dfilter_error()
            return
        args['sippers'] = sippers
        args['ax'] = self.ax
        name = self.create_plot_name(self.plot_default_names[func])
        data = self.get_data_funcs[func.__name__](**args)
        plot = SipperPlot(name, func, args, data)
        self.loaded_plots[name] = plot
        self.plot_list.insert('', 'end', iid=plot.name, values=[plot.name])
        self.display_plot(plot, new=True)

    def group_plot(self, func):
        self.bad_date_sippers = []
        groups = self.groupselect.selection()
        sippers = []
        for s in self.loaded_sippers:
            for g in groups:
                if g in s.groups:
                    sippers.append(s)
                    break
        self.ax.clear()
        all_args = self.get_settings_dict_as_args()
        func_args = inspect.getfullargspec(func).args
        args = {k:v for k,v in all_args.items() if k in func_args}
        if self.date_filter_val.get():
            b,e = self.get_date_filter_dates()
            args['date_filter'] = b, e
            for s in sippers:
                if not sipperplots.date_filter_okay(s.data, b, e):
                        self.bad_date_sippers.append(s)
                        continue
        if self.bad_date_sippers:
            self.raise_dfilter_error()
            return
        args['sippers'] = sippers
        args['groups'] = groups
        args['ax'] = self.ax
        name = self.create_plot_name(self.plot_default_names[func])
        data = self.get_data_funcs[func.__name__](**args)
        plot = SipperPlot(name, func, args, data)
        self.loaded_plots[name] = plot
        self.plot_list.insert('', 'end', iid=plot.name, values=[plot.name])
        self.display_plot(plot, new=True)

    #---plotting functions
    def display_plot(self, plot, new=False, select=True):
        self.suspend_plot_raising = True
        self.ax.clear()
        self.display_plot_details(plot)
        plot.func(**plot.args)
        if select:
            self.plot_list.selection_remove(self.plot_list.selection())
            self.plot_list.selection_set(plot.name)
        self.canvas.draw_idle()
        self.update()
        self.suspend_plot_raising = False
        self.update_all_buttons()

    def raise_plot_from_click(self, event):
        if not self.suspend_plot_raising:
            clicked = self.plot_list.selection()
            if len(clicked) == 1:
                plot = self.loaded_plots[clicked[0]]
                self.display_plot(plot)

    def display_plot_details(self, plot):
        self.plot_info.delete(*self.plot_info.get_children())
        dfilter = False
        for i, (k, v) in enumerate(plot.args.items()):
            nice_name = self.args_to_names.get(k, None)
            if nice_name:
                text = nice_name + ' : ' + str(v)
                self.plot_info.insert('', i, text=text)
            elif k == 'date_filter':
                dfilter = True
                x = self.plot_info.insert('',i, text='date filter : True')
                self.plot_info.insert(x, 0, text='start : ' + str(v[0]))
                self.plot_info.insert(x, 1, text='end : ' + str(v[1]))
        if not dfilter:
            self.plot_info.insert('','end', text='date filter : False')

    def is_plottable(self, graphname):
        plottable = False
        if graphname in [
                'Drink Count (Cumulative)',
                'Drink Duration (Cumulative)',
                'Drink Count (Binned)',
                'Drink Duration (Binned)',
                'Interpellet Intervals',
                'Interpellet Intervals (By Side)',
                'Chronogram (Drink Count)'
                ]:
            if self.file_view.selection():
                plottable = True
        if graphname in [
                'Interpellet Intervals (By Content)'
                ]:
            if self.contentselect.selection():
                plottable = True
        if graphname in [
                'Grouped Chronogram (Drink Count)'
                ]:
            if self.groupselect.selection():
                plottable = True
        return plottable

    def raise_makeplot_window(self):
        self.makeplot_window.deiconify()
        self.update_makeplot_run()

    def update_makeplot_run(self, *event):
        selected = self.makeplot_selection.selection()
        plottable_list = []
        for i in selected:
            text = self.makeplot_selection.item(i, 'text')
            plottable_list.append(self.is_plottable(text))
        if any(plottable_list):
            self.makeplot_run_button.configure(state='normal')
        else:
            self.makeplot_run_button.configure(state='disabled')

    def close_makeplot_window(self):
        self.makeplot_window.grab_release()
        self.grab_set()
        self.makeplot_window.withdraw()

    def run_makeplots(self):
        for i in self.makeplot_selection.selection():
            graphname = self.makeplot_selection.item(i)['text']
            if self.is_plottable(graphname):
                plot_func = self.plot_names_to_funcs[graphname]
                route_func = self.plot_routes[plot_func]
                route_func(plot_func)

    #---plot button functions
    def delete_plots(self):
        selected = self.plot_list.selection()
        self.plot_list.delete(*selected)
        for name in selected:
            del self.loaded_plots[name]
        if self.plot_list.get_children():
            lastname = self.plot_list.get_children()[-1]
            self.display_plot(self.loaded_plots[lastname])
        else:
            self.ax.clear()
            self.canvas.draw_idle()
            self.update()
            self.update_all_buttons()
            self.plot_info.delete(*self.plot_info.get_children())

    def save_plots(self):
        selected = self.plot_list.selection()
        if len(selected) == 1:
            s = self.loaded_plots[selected[0]]
            filetypes = [('Portable Network Graphic', '*.png')]
            savepath = tk.filedialog.asksaveasfilename(title='Save plot',
                                                        defaultextension='.csv',
                                                        initialfile=s.name,
                                                        filetypes=filetypes)
            if savepath:
                self.fig.savefig(savepath, dpi=300)
                self.fig.set_dpi(100)
                self.canvas.draw_idle()
                self.nav_toolbar.update()
                self.update()

        elif len(selected) > 1:
            folder = tk.filedialog.askdirectory(title='Save multiple files')
            if folder:
                for s in selected:
                    plot = self.loaded_plots.get(s)
                    self.display_plot(plot)
                    save_name = plot.name + '.png'
                    full_save = os.path.join(folder, save_name)
                    final = self.create_file_name(full_save)
                    self.fig.savefig(final, dpi=300)
                    self.fig.set_dpi(100)
                    self.canvas.draw_idle()
                    self.nav_toolbar.update()
                    self.update()

    def show_plot_code(self):
        clicked = self.plot_list.selection()
        for i in clicked:
            plot  = self.loaded_plots[i]
            name = plot.name
            new_window = tk.Toplevel(self)
            new_window.title('Code for "' + name +'"')
            textview = tk.Text(new_window, width=150)
            code = sipperinspect.generate_code(plot)
            textview.insert(tk.END, code)
            textview.configure(state=tk.DISABLED)
            scrollbar = tk.Scrollbar(new_window, command=textview.yview)
            textview['yscrollcommand'] = scrollbar.set
            save_button = tk.Button(new_window, text='Save as...',
                                    command=print)
            textview.grid(row=0,column=0,sticky='nsew')
            scrollbar.grid(row=0,column=1,sticky='nsew')
            save_button.grid(row=1,column=0,sticky='w')
            new_window.grid_rowconfigure(0,weight=1)
            new_window.grid_columnconfigure(0,weight=1)

    def save_plot_data(self):
        selected = self.plot_list.selection()
        if len(selected) == 1:
            plot = self.loaded_plots[selected[0]]
            filetypes = [('Comma-Separated Values', '*.csv')]
            savepath = tk.filedialog.asksaveasfilename(title='Save data',
                                                       defaultextension='.csv',
                                                       initialfile=plot.name,
                                                       filetypes=filetypes)
            if savepath:
                if plot.func in [
                        sipperplots.interdrink_intervals
                        ]:
                    path = self.create_file_name(savepath)
                    base_path, ext = os.path.splitext(path)
                    bar_name = base_path + ' BARS' + ext
                    kde_name = base_path + ' KDE' + ext
                    plot.data[0].to_csv(bar_name)
                    if not plot.data[1].empty:
                        plot.data[1].to_csv(kde_name)
                else:
                    final_path = self.create_file_name(savepath)
                    plot.data.to_csv(final_path)

        elif len(selected) > 1:
            folder = tk.filedialog.askdirectory(title='Save multiple files')
            if folder:
                for s in selected:
                    plot = self.loaded_plots.get(s)
                    data = plot.data
                    if plot.func in [
                        sipperplots.interdrink_intervals
                        ]:
                        bar_save = plot.name + ' BARS.csv'
                        full_bar = os.path.join(folder, bar_save)
                        final = self.create_file_name(full_bar)
                        data[0].to_csv(final)
                        if not data[1].empty:
                            kde_save = plot.name + ' KDE.csv'
                            full_kde = os.path.join(folder, kde_save)
                            final = self.create_file_name(full_kde)
                            data[1].to_csv(final)
                    else:
                        save_name = plot.name + '.csv'
                        full_save = os.path.join(folder, save_name)
                        final = self.create_file_name(full_save)
                        data.to_csv(final)

    #---group functions
    def raise_group_window(self):
        self.update_groupview_buttons()
        self.groups_window.deiconify()

    def create_group(self):
        self.create_window = tk.Toplevel(self)
        self.create_window.title('Enter a group name')
        self.create_name = tk.StringVar()
        self.create_name.set('')
        self.create_name.trace_add('write',self.create_group_check)
        self.warning_var = tk.StringVar()
        self.warning_var.set('')
        warning_label = tk.Label(self.create_window,
                                 textvariable=self.warning_var)
        entry = tk.Entry(self.create_window,
                         textvariable=self.create_name,
                         width=50)
        self.ok_button_create = tk.Button(self.create_window,text='OK',
                                          command=lambda: self.create_okay(),
                                          state=tk.DISABLED)
        cancel_button = tk.Button(self.create_window,
                                  text='Cancel',
                                  command=self.create_window.destroy)
        warning_label.grid(row=0,column=0, sticky='w',
                           columnspan=2,padx=(20,0),pady=(20,0))
        entry.grid(row=1,column=0,sticky='ew',padx=(20,20),pady=(20,0),
                   columnspan=2)
        self.ok_button_create.grid(row=2,column=0,sticky='ew',padx=(20,20),pady=(20,20))
        cancel_button.grid(row=2,column=1,sticky='ew',padx=(20,20),pady=(20,20))

    def create_okay(self):
        group_name = self.create_name.get()
        self.loaded_groups.append(group_name)
        self.groupview.insert('', 'end', iid=group_name, text=group_name)
        self.groupview.selection_add(group_name)
        self.create_window.destroy()

    def create_group_check(self, *args):
        new_name = self.create_name.get()
        if new_name == '':
            self.ok_button_create.configure(state=tk.DISABLED)
        else:
            if new_name in self.loaded_groups:
                self.warning_var.set('Group already in use!')
                self.ok_button_create.configure(state=tk.DISABLED)
            else:
                self.warning_var.set('')
                self.ok_button_create.configure(state=tk.NORMAL)

    # self.group_add = tk.Button(self.groups_window, text='Add Files to Group')
    # self.group_remove = tk.Button(self.groups_window, text='Remove Files from Group')
    # self.group_select = tk.Button(self.groups_window, text='Select Files in these Groups')
    # self.group_delete = tk.Button(self.groups_window, text='Delete Group')
    # self.group_save = tk.Button(self.groups_window, text='Save Groups')
    # self.group_load = tk.Button(self.groups_window, text='Load Groups')

    def group_add(self):
        groups = self.groupview.selection()
        files = [self.loaded_sippers[int(i)] for i in self.file_view.selection()]
        for s in files:
            for g in groups:
                if g not in s.groups:
                    s.groups.append(g)
        self.update_all_buttons()
        self.display_details()
        self.update_makeplot_run()

    def group_remove(self):
        groups = self.groupview.selection()
        files = [self.loaded_sippers[int(i)] for i in self.file_view.selection()]
        for s in files:
            for g in groups:
                if g in s.groups:
                    s.groups.remove(g)
        self.update_all_buttons()
        self.display_details()
        self.update_makeplot_run()

    def group_select(self):
        groups = self.groupview.selection()
        self.file_view.selection_remove(*self.file_view.get_children())
        for i, s in enumerate(self.loaded_sippers):
            for g in groups:
                if g in s.groups:
                    self.file_view.selection_add(i)
                    break

    def group_delete(self):
        groups = self.groupview.selection()
        for g in groups:
            for s in self.loaded_sippers:
                if g in s.groups:
                    s.groups.remove(g)
            self.loaded_groups.remove(g)
        self.groupview.delete(*groups)
        self.update_all_buttons()
        self.display_details()
        self.update_makeplot_run()

    def update_groupview_buttons(self, *event):
        groups = self.groupview.selection()
        files = self.file_view.selection()
        if files and groups:
            self.group_add.configure(state='normal')
            self.group_remove.configure(state='normal')
            self.group_delete.configure(state='normal')
        else:
            self.group_add.configure(state='disabled')
            self.group_remove.configure(state='disabled')
            self.group_delete.configure(state='disabled')
        if groups:
            self.group_select.configure(state='normal')
        else:
            self.group_select.configure(state='disabled')

    def update_avail_groups(self):
        self.avail_groups = []
        for s in self.loaded_sippers:
            for g in s.groups:
                if g not in self.avail_groups:
                    self.avail_groups.append(g)
        self.avail_groups.sort()
        self.update_groupselect()

    def update_groupselect(self):
        current = self.groupselect.selection()
        total = self.groupselect.get_children()
        self.groupselect.delete(*self.groupselect.get_children())
        for i, c in enumerate(self.avail_groups):
            self.groupselect.insert('', 'end', iid=c, values=[c])
            if c in current:
                self.groupselect.selection_add(c)
            elif c in total and c not in current:
                pass
            else:
                self.groupselect.selection_add(c)

    #---settings functions
    def get_settings_dict(self):
        settings_dict = dict(dfilter_val     =self.date_filter_val.get(),
                             dfilter_sdate   =self.dfilter_s_date.get_date(),
                             dfilter_edate   =self.dfilter_e_date.get_date(),
                             dfilter_shour   =self.dfilter_s_hour.get(),
                             dfilter_ehour   =self.dfilter_e_hour.get(),
                             shade_dark      =self.shade_dark_val.get(),
                             lights_on       =self.lightson_menu.get(),
                             lights_off      =self.lightsoff_menu.get(),
                             show_left       =self.drink_showleft_val.get(),
                             show_right      =self.drink_showright_val.get(),
                             show_content_val=self.drink_showcontent_val.get(),
                             binsize         =self.drink_binsize_menu.get(),
                             kde             =self.kde_val.get(),
                             logx            =self.logx_val.get(),
                             combine         =self.combine_idi_val.get(),
                             circ_left       =self.circ_showleft_val.get(),
                             circ_right      =self.circ_showright_val.get(),
                             circ_content    =self.circ_showcontent_val.get(),
                             circ_show_indvl =self.circ_showindvl_val.get(),
                             circ_var        =self.circ_var_menu.get())
        return settings_dict

    def get_settings_dict_as_args(self):
        settings_dict = self.get_settings_dict()
        selected_contents = list(self.contentselect.selection())
        drink_content = selected_contents if self.drink_showcontent_val.get() else []
        circ_content = selected_contents if self.circ_showcontent_val.get() else []
        settings_dict['show_content'] = drink_content
        settings_dict['circ_content'] = circ_content
        for time_setting in ['lights_on','lights_off']:
            settings_dict[time_setting] = self.times_to_int[settings_dict[time_setting]]
        for bin_setting in ['binsize']:
            settings_dict[bin_setting] = self.bin_convert[settings_dict[bin_setting]]
        return settings_dict

    def get_settings_df(self):
        d = self.get_settings_dict()
        settings_df = pd.DataFrame(columns=['Value'])
        for k, v in d.items():
            settings_df.loc[k, 'Value'] = v
        return settings_df

    def load_settings_df(self, path):
        if os.path.exists(path):
            pass
        else:
            path = tk.filedialog.askopenfilenames(title='Select FED3 Data',
                                                  defaultextension='.csv',
                                                  filetypes=[('Comma-Separated Values', '*.csv')],
                                                  initialdir='memory/settings')
        if path:
            df = pd.read_csv(path, index_col=0)
            v = 'Value'
            self.shade_dark_val.set(df.loc['shade_dark', v])
            self.lightson_menu.set(df.loc['lights_on', v])
            self.lightsoff_menu.set(df.loc['lights_off', v])
            self.drink_showleft_val.set(df.loc['show_left', v])
            self.drink_showright_val.set(df.loc['show_right', v])
            self.drink_showcontent_val.set(df.loc['show_content_val', v])
            self.drink_binsize_menu.set(df.loc['binsize', v])
            self.kde_val.set(df.loc['kde', v])
            self.logx_val.set(df.loc['logx', v])
            self.combine_idi_val.set(df.loc['combine', v])
            s = pd.to_datetime(df.loc['dfilter_sdate', v])
            e = pd.to_datetime(df.loc['dfilter_edate', v])
            if str(self.dfilter_s_date.cget('state')) == 'disabled':
                self.dfilter_s_date.configure(state='normal')
                self.dfilter_s_date.set_date(s)
                self.dfilter_s_date.configure(state='disabled')
            else:
                self.dfilter_s_date.set_date(s)
            if str(self.dfilter_e_date.cget('state')) == 'disabled':
                self.dfilter_e_date.configure(state='normal')
                self.dfilter_e_date.set_date(e)
                self.dfilter_e_date.configure(state='disabled')
            else:
                self.dfilter_e_date.set_date(e)
            self.dfilter_s_hour.set(df.loc['dfilter_shour', v])
            self.dfilter_e_hour.set(df.loc['dfilter_ehour', v])
            self.circ_showleft_val.set(df.loc['circ_left', v])
            self.circ_showright_val.set(df.loc['circ_right', v])
            self.circ_showcontent_val.set(df.loc['circ_content', v])
            self.circ_showindvl_val.set(df.loc['circ_show_indvl', v])
            self.circ_var_menu.set(df.loc['circ_var', v])


    def set_date_filter_state(self):
        if self.date_filter_val.get():
            self.dfilter_s_date.configure(state='normal')
            self.dfilter_e_date.configure(state='normal')
            self.dfilter_s_hour.configure(state='normal')
            self.dfilter_e_hour.configure(state='normal')
        else:
            self.dfilter_s_date.configure(state='disabled')
            self.dfilter_e_date.configure(state='disabled')
            self.dfilter_s_hour.configure(state='disabled')
            self.dfilter_e_hour.configure(state='disabled')

    #---naming functions

    def create_file_name(self, savepath, overwrite=False):
        root, ext = os.path.splitext(savepath)
        if not overwrite:
            c=1
            while os.path.exists(savepath):
                savepath = root + ' ' + str(c) + ext
                c += 1
        return savepath

    def create_plot_name(self, basename):
        fig_name = basename
        c = 1
        current_names = self.loaded_plots.keys()
        while fig_name in current_names:
            fig_name = basename + ' ' + str(c)
            c += 1
        return fig_name

    #---content window functions
    def raise_content_window(self):
        self.assign_content_view.delete(*self.assign_content_view.get_children())
        selected = [self.loaded_sippers[int(i)] for i in self.file_view.selection()]
        mindate = dt.datetime(2999, 12, 13)
        maxdate = dt.datetime(1970, 1, 1)
        for s in selected:
            if s.start_date < mindate:
                mindate = s.start_date
            if s.end_date > maxdate:
                maxdate = s.end_date
        shour = mindate.hour
        ehour = maxdate.hour
        sdate = mindate.date()
        edate = maxdate.date()
        self.sdate_entry.set_date(sdate)
        self.edate_entry.set_date(edate)
        self.shour_entry.set(self.times[shour])
        self.ehour_entry.set(self.times[ehour])
        self.contents_window.deiconify()
        self.update_content_buttons()

    def raise_content_window_for_file(self):
        selected = [self.loaded_sippers[int(i)] for i in self.file_view.selection()]
        file = selected[0]
        self.raise_content_window()
        contents = file.get_contents_dict()
        for i, ((s, e), (l, r)) in enumerate(contents.items()):
            values = [s, e, l, r]
            self.assign_content_view.insert('', 'end', i, values=values)
        self.update_content_buttons()

    def get_content_dates(self):
        sdate = self.sdate_entry.get_date()
        shour = self.times_to_int[self.shour_entry.get()]
        edate = self.edate_entry.get_date()
        ehour = self.times_to_int[self.ehour_entry.get()]
        start = dt.datetime.combine(sdate, dt.time(hour=shour))
        end = dt.datetime.combine(edate, dt.time(hour=ehour))
        return start, end

    def get_date_filter_dates(self):
        sdate = self.dfilter_s_date.get_date()
        shour = self.times_to_int[self.dfilter_s_hour.get()]
        edate = self.dfilter_e_date.get_date()
        ehour = self.times_to_int[self.dfilter_e_hour.get()]
        start = dt.datetime.combine(sdate, dt.time(hour=shour))
        end = dt.datetime.combine(edate, dt.time(hour=ehour))
        return start, end

    def get_content_dict(self):
        output = OrderedDict()
        to_assign = self.assign_content_view.get_children()
        for c in to_assign:
            s, e, l, r = self.assign_content_view.item(c)['values']
            s = pd.to_datetime(s)
            e = pd.to_datetime(e)
            output[(s,e)] = (l,r)
        return output

    def add_content(self):
        s, e = self.get_content_dates()
        values = [s, e, self.lcontent_val.get(), self.rcontent_val.get()]
        allvals = self.assign_content_view.get_children()
        self.assign_content_view.insert('', 'end', len(allvals), values=values)
        self.update_content_buttons()

    def delete_content(self):
        selected = self.assign_content_view.selection()
        self.assign_content_view.delete(selected)
        self.update_content_buttons()

    def move_content(self, by):
        selected = self.assign_content_view.selection()
        index = self.assign_content_view.index(selected)
        self.assign_content_view.move(selected, '', index + by)

    def assign_content(self):
        d = self.get_content_dict()
        files = [self.loaded_sippers[int(i)] for i in self.file_view.selection()]
        if files:
            for f in files:
                f.assign_contents(d)
                f.sipperviz_assigned = True
        self.close_content_window()
        self.display_details()
        self.update_avail_contents()

    def clear_contents(self):
        files = [self.loaded_sippers[int(i)] for i in self.file_view.selection()]
        if files:
            for f in files:
                f.clear_contents()
        self.display_details()
        self.update_avail_contents()

    def update_content_buttons(self, *event):
        entries = self.assign_content_view.get_children()
        selected = self.assign_content_view.selection()
        if len(selected) == 1:
            self.content_moveup.configure(state='normal')
            self.content_movedown.configure(state='normal')
            self.content_delete.configure(state='normal')
        else:
            self.content_moveup.configure(state='disabled')
            self.content_movedown.configure(state='disabled')
            self.content_delete.configure(state='disabled')
        if entries:
            self.content_assign.configure(state='normal')
        else:
            self.content_assign.configure(state='disabled')
        if self.lcontent_val.get() and self.rcontent_val.get():
            self.content_add.configure(state='normal')
        else:
            self.content_add.configure(state='disabled')

    def close_content_window(self):
        self.grab_set()
        self.contents_window.withdraw()

    def swapcontents(self):
        lcontent = self.lcontent_val.get()
        rcontent = self.rcontent_val.get()
        self.lcontent_val.set(rcontent)
        self.rcontent_val.set(lcontent)

    def update_avail_contents(self):
        self.avail_contents = []
        for s in self.loaded_sippers:
            for c in s.contents:
                if c not in self.avail_contents:
                    self.avail_contents.append(c)
        self.avail_contents.sort()
        self.update_contentselect()

    def update_contentselect(self):
        current = self.contentselect.selection()
        total = self.contentselect.get_children()
        self.contentselect.delete(*self.contentselect.get_children())
        for i, c in enumerate(self.avail_contents):
            self.contentselect.insert('','end',iid=c,values=[c])
            if c in current:
                self.contentselect.selection_add(c)
            elif c in total and c not in current:
                pass
            else:
                self.contentselect.selection_add(c)

    #---errors
    def raise_dfilter_error(self):
        warn_window = tk.Toplevel(self)
        warn_window.grab_set()
        warn_window.title('Date filter error')
        # if not platform.system() == 'Darwin':
        #     warn_window.iconbitmap('img/exclam.ico')
        text = ("The following files did not have any data within the date filter" +
                '\nPlease edit or remove the global date filter to plot them:\n')
        for s in self.bad_date_sippers:
            text += '\n  - ' + s.basename
        warning = tk.Label(warn_window, text=text, justify=tk.LEFT)
        warning.pack(padx=(20,20),pady=(20,20))

    #---run before closing:
    def on_close(self):
        settings_dir = 'memory/settings'
        if os.path.isdir(settings_dir):
            settings_df = self.get_settings_df()
            settings_df.to_csv(os.path.join(settings_dir, 'LAST_USED.csv'))
        self.destroy()
        self.quit()

    #---bindings
    def escape(self, *event):
        widget = self.focus_get()
        if type(widget) == ttk.Treeview:
            widget.selection_remove(*widget.selection())
        if self.loading:
            self.loading = False
        if self.plotting:
            self.plotting = False
        self.update_all_buttons()

    def select_all(self, *event):
        widget = self.focus_get()
        if type(widget) == ttk.Treeview:
            widget.selection_set(*widget.get_children())

plt.style.use('seaborn-whitegrid')
root = SipperViz()
root.protocol("WM_DELETE_WINDOW", root.on_close)
if __name__ == "__main__":
    root.lift()
    root.attributes('-topmost', True)
    root.after_idle(root.attributes, '-topmost', False)
    root.focus_force()
    root.mainloop()
plt.close('all')
root.quit()