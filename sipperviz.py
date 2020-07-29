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

import sipper
import sipperplots

class SipperPlot:
    def __init__(self, name, func, args):
        self.name = name
        self.func = func
        self.args = args

class SipperViz(tk.Tk):
    """Class for SipViz"""
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=C0103
    def __init__(self):
        super(SipperViz, self).__init__()
    #---constants/conversions
        self.attr_conversion = {'Start':'start_date', 'End':'end_date',
                                'Duration':'duration', 'Device': 'device_no',
                                'Left Sipper Name':'left_name',
                                'Right Sipper Name':'right_name',
                                'Contents': 'contents',
                                'Version': 'version', 'Groups':'groups'}
        self.file_info_names = list(self.attr_conversion.keys())
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
        self.plot_default_names = {sipperplots.drinkcount_cumulative:
                                   'Drink Count (Cumulative)',
                                   sipperplots.drinkduration_cumulative:
                                   'Drink Duration (Cumulative)'}
        self.args_to_names = {'shade_dark':'shade dark',
                              'lights_on': 'lights on',
                              'lights_off': 'lights off',
                              'show_left': 'show left',
                              'show_right': 'show right',
                              'show_content': 'content'}

    #---data management
        self.loaded_sippers = []
        self.loaded_plots = OrderedDict()
        self.avail_contents = []

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
        p3 = '"Show selected contents" box is ticked for any given plot.'
        text = p1 + p2 + p3
        self.contentselect_text = tk.Label(self.contentselect_frame,
                                           text=text, justify='left',
                                           wraplength=300)
        self.contentselect.grid(row=0, column=0, sticky='nsw', padx=(20,0))
        self.contentselect_scroll.grid(row=0, column=1, sticky='nsw')
        self.contentselect_text.grid(row=0, column=2, sticky='new', padx=20)

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
        self.drink_showleft_box = tk.Checkbutton(self.drink_settings,
                                              variable=self.drink_showleft_val,
                                              text='Show left sipper')
        self.drink_showright_val = tk.BooleanVar()
        self.drink_showright_val.set(True)
        self.drink_showright_box = tk.Checkbutton(self.drink_settings,
                                               variable=self.drink_showright_val,
                                               text='Show right sipper')
        self.drink_showcontent_val = tk.BooleanVar()
        self.drink_showcontent_val.set(True)
        self.drink_showcontent_box = tk.Checkbutton(self.drink_settings,
                                                 variable=self.drink_showcontent_val,
                                                 text='Show contents (see Content tab)')

        self.drink_settings_label.grid(row=0, column=1, sticky='nsew', padx=20, pady=5)
        self.drink_showleft_box.grid(row=1, column=1, sticky='w', padx=20, pady=5)
        self.drink_showright_box.grid(row=2, column=1, sticky='w', padx=20, pady=5)
        self.drink_showcontent_box.grid(row=3, column=1, sticky='w', padx=20, pady=5)

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
        self.plotmenu = tk.Menu(self.menubar, tearoff=0)
        self.plotmenu.add_command(label='Drink Count (Cumulative)', command=lambda:
                                  self.iter_plot(sipperplots.drinkcount_cumulative))
        self.plotmenu.add_command(label='Drink Duration (Cumulative)', command=lambda:
                                  self.iter_plot(sipperplots.drinkduration_cumulative))
        self.menubar.add_cascade(menu=self.plotmenu, label='Plot')

    #---create buttons
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
                                       command=print,
                                       width=40)
        self.concat_button = tk.Button(self.button_frame,
                                       image=self.icons['tack'],
                                       text='Concat', compound='top',
                                       borderwidth=0,
                                       command=print,
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
                                     command=print,
                                     width=40)
        self.plot_save_button = tk.Button(self.button_frame,
                                          image=self.icons['picture'],
                                          text='Save', compound='top',
                                          borderwidth=0,
                                          command=print,
                                          width=40)
        self.plot_data_button = tk.Button(self.button_frame,
                                          image=self.icons['spreadsheet'],
                                          text='Data', compound='top',
                                          borderwidth=0,
                                          command=print,
                                          width=40)
        self.plot_code_button = tk.Button(self.button_frame,
                                          image=self.icons['script'],
                                          text='Code', compound='top',
                                          borderwidth=0,
                                          command=print,
                                          width=40)
        self.plot_delete_button = tk.Button(self.button_frame,
                                            image=self.icons['delete_graph'],
                                            text='Delete', compound='top',
                                            borderwidth=0,
                                            command=print,
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
        self.file_view.bind('<<TreeviewSelect>>', self.display_details)
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
        self.fig = mpl.figure.Figure(figsize=(12, 5))
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

    #---operations pre opening
        self.set_date_filter_state()

    #---file functions
    def load_files(self):
        file_types = [('All', '*.*'), ('Comma-Separated Values', '*.csv'),
                      ('Excel', '*.xls, *.xslx'),]
        files = tk.filedialog.askopenfilenames(title='Select FED3 Data',
                                               filetypes=file_types)
        if files:
            for file in files:
                try:
                    self.loaded_sippers.append(sipper.Sipper(file))
                except:
                    tb = traceback.format_exc()
                    print(tb)
            self.update_file_view()
            self.update_avail_contents()

    def delete_files(self):
        selected = [int(i) for i in self.file_view.selection()]
        for index in sorted(selected, reverse=True):
            del(self.loaded_sippers[index])
        self.update_file_view()
        self.update_avail_contents()

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

    def update_file_view(self):
        self.file_view.delete(*self.file_view.get_children())
        for i, s in enumerate(self.loaded_sippers):
            self.file_view.insert("", i, str(i), text=s.filename, tag='file')

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
                self.info_view.insert('', i, text=text, tag='spec')

    #---plotting functions
    def iter_plot(self, func):
        self.bad_date_sippers = []
        sippers = [self.loaded_sippers[int(i)]
                   for i in self.file_view.selection()]
        for i, s in enumerate(sippers):
            self.ax.clear()
            all_args = self.get_argument_settings_dict()
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
            plot = SipperPlot(name, func, args)
            self.loaded_plots[name] = plot
            func(**args)
            self.plot_list.insert('', 'end', iid=plot.name, values=[plot.name])
            self.display_plot(plot, new=True)
        if self.bad_date_sippers:
            self.raise_dfilter_error()

    def display_plot(self, plot, new=False):
        if new:
            self.plot_list.selection_remove(self.plot_list.selection())
            self.plot_list.selection_set(plot.name)
        self.ax.clear()
        self.display_plot_details(plot)
        plot.func(**plot.args)
        self.canvas.draw_idle()
        self.update()

    def raise_plot_from_click(self, event):
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

    #---settings functions
    def get_argument_settings_dict(self):
        lon = self.times_to_int[self.lightson_menu.get()]
        loff = self.times_to_int[self.lightsoff_menu.get()]
        if self.drink_showcontent_val.get():
            drink_content = list(self.contentselect.selection())
        else:
            drink_content = []
        settings_dict = {'shade_dark'  :self.shade_dark_val.get(),
                         'lights_on'   :lon,
                         'lights_off'  :loff,
                         'show_left'   :self.drink_showleft_val.get(),
                         'show_right'  :self.drink_showright_val.get(),
                         'show_content':drink_content}
        return settings_dict

    def get_all_settings_df(self):
        #first get plot settings:
        d = self.get_argument_settings_dict()
        #then add general settings
        d['dfilter_val'] = self.date_filter_val.get()
        d['dfilter_sdate'] = self.dfilter_s_date.get_date()
        d['dfilter_edate'] = self.dfilter_e_date.get_date()
        d['dfilter_shour'] = self.times_to_int[self.dfilter_s_hour.get()]
        d['dfilter_ehour'] = self.times_to_int[self.dfilter_e_hour.get()]
        d['show_content_val'] = self.show_content_val.get()
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
            df = pd.read_csv(path)
            v = 'Value'
            self.shade_dark_val.set(df.loc['shade_dark', v])
            self.lightson_menu.set(df.loc['lights_on', v])
            self.lightsoff_menu.set(df.loc['lights_off', v])
            self.drink_showleft_val.set(df.loc['show_left', v])
            self.drink_showright_val.set(df.loc['show_right', v])
            self.show_content_val.set(df.loc['show_content_val', v])

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
        self.contents_window.grab_set()
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
        self.close_content_window()
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
        self.contents_window.grab_release()
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
            settings_df = self.get_all_settings_df()
            settings_df.to_csv(os.path.join(settings_dir, 'LAST_USED.csv'))
        self.destroy()
        self.quit()

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