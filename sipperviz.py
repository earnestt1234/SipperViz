"""Code to run SipViz."""

from collections import OrderedDict
import inspect
from PIL import Image, ImageTk
import traceback
import tkinter as tk
from tkinter import ttk

import matplotlib as mpl
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk

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
                                'Right Sipper Name':'right_name'}
        self.file_info_names = list(self.attr_conversion.keys())
        times = []
        for xm in [' am', ' pm']:
            for num in range(0,12):
                time = str(num) + xm
                if time == '0 am':
                    time = 'midnight'
                if time == '0 pm':
                    time = 'noon'
                times.append(time)

        self.times_to_int = {time : num for num,time in enumerate(times)}
        self.plot_default_names = {sipperplots.drinkcount_cumulative:
                                   'Drink Count (Cumulative)'}
        self.args_to_names = {'shade_dark':'shade dark',
                              'lights_on': 'lights on',
                              'lights_off': 'lights off',
                              'show_left_count': 'show left',
                              'show_right_count': 'show right',}

    #---data management
        self.loaded_sippers = []
        self.loaded_plots = OrderedDict()

    #---create whole window
        self.title('SipViz')
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.main_frame = tk.Frame(self)
        self.main_frame.grid(row=0, column=0, sticky='nsew')
        self.main_frame.grid_rowconfigure(0, weight=1)
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
        self.shade_dark_val = tk.BooleanVar()
        self.shade_dark_val.set(True)
        self.shade_dark_box = ttk.Checkbutton(self.allplot_settings,
                                              variable=self.shade_dark_val,
                                              text='Shade dark periods')

        self.shade_dark_box.grid(row=0, column=0, sticky='w', padx=20, pady=5)

        # drink count
        self.drinkcount_settings = tk.Frame(self.plot_settings_window)
        self.plot_settings_tabs.add(self.drinkcount_settings,
                                    text='Drink Count Plots')
        self.dc_showleft_val = tk.BooleanVar()
        self.dc_showleft_val.set(True)
        self.dc_showleft_box = tk.Checkbutton(self.drinkcount_settings,
                                              variable=self.dc_showleft_val,
                                              text='Show left sipper')
        self.dc_showright_val = tk.BooleanVar()
        self.dc_showright_val.set(True)
        self.dc_showright_box = tk.Checkbutton(self.drinkcount_settings,
                                               variable=self.dc_showright_val,
                                               text='Show right sipper')

        self.dc_showleft_box.grid(row=0, column=0, sticky='w', padx=20, pady=5)
        self.dc_showright_box.grid(row=1, column=0, sticky='w', padx=20, pady=5)


    #---create treeview panes (left sash)
        self.left_sash = ttk.PanedWindow(self.main_frame, orient='vertical')

    #---create plot panes (right sash)
        self.right_sash = ttk.PanedWindow(self.main_frame, orient='vertical')

    #---create menu
        self.menubar = tk.Menu(self.main_frame)
        self.config(menu=self.menubar)
        self.filemenu = tk.Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label='Load files', command=self.load_files)
        self.menubar.add_cascade(menu=self.filemenu, label='File')
        self.plotmenu = tk.Menu(self.menubar, tearoff=0)
        self.plotmenu.add_command(label='Drink Count (Cumulative)', command=lambda:
                                  self.iter_plot(sipperplots.drinkcount_cumulative))
        self.menubar.add_cascade(menu=self.plotmenu, label='Plot')

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
                 'palette':'img/palette.png'}
        self.icons = {}
        for k, v in icons.items():
            image = Image.open(v).resize((25, 25))
            self.icons[k] = ImageTk.PhotoImage(image)

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
                                         command=print,
                                         width=40)

    #---pack buttons, add separators, labels
        self.load_button.grid(row=0, column=0, sticky='nsew', pady=5,
                              padx=5)
        self.delete_button.grid(row=0, column=1, sticky='nsew', pady=5,
                                padx=5)
        self.groups_button.grid(row=0, column=2, sticky='nsew', pady=5,
                                padx=5)
        self.concat_button.grid(row=0, column=3, sticky='nsew', pady=5,
                                padx=5)
        self.files_label = tk.Label(self.button_frame, text='Files')
        self.files_label.grid(row=1, column=0, sticky='nsew',
                              columnspan=4, pady=(0, 5))
        self.sep1 = ttk.Separator(self.button_frame, orient='vertical')
        self.sep1.grid(row=0,column=4,sticky='nsew', pady=5, rowspan=2)
        self.plot_button.grid(row=0, column=5, sticky='nsew', pady=5,
                              padx=5)
        self.plot_save_button.grid(row=0, column=6, sticky='nsew', pady=5,
                                   padx=5)
        self.plot_delete_button.grid(row=0, column=7, sticky='nsew', pady=5,
                                     padx=5)
        self.plot_data_button.grid(row=0, column=8, sticky='nsew', pady=5,
                                   padx=5)
        self.plot_code_button.grid(row=0, column=9, sticky='nsew', pady=5,
                                   padx=5)
        self.plots_label = tk.Label(self.button_frame, text='Plots')
        self.plots_label.grid(row=1, column=5, sticky='nsew',
                              columnspan=5, pady=(0, 5))
        self.sep2 = ttk.Separator(self.button_frame, orient='vertical')
        self.sep2.grid(row=0,column=10,sticky='nsew', pady=5, rowspan=2)
        self.plotopts_button.grid(row=0, column=11, sticky='nsew', pady=5,
                                  padx=5)
        self.settings_button.grid(row=0, column=12, sticky='nsew', pady=5,
                                  padx=5)
        self.settings_label = tk.Label(self.button_frame, text='Settings')
        self.settings_label.grid(row=1, column=11, sticky='nsew',
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

    def delete_files(self):
        selected = [int(i) for i in self.file_view.selection()]
        for index in sorted(selected, reverse=True):
            del(self.loaded_sippers[index])
        self.update_file_view()


    def update_file_view(self):
        self.file_view.delete(*self.file_view.get_children())
        for i, s in enumerate(self.loaded_sippers):
            self.file_view.insert("", i, str(i), text=s.filename, tag='file')

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

    def iter_plot(self, func):
        sippers = [self.loaded_sippers[int(i)]
                   for i in self.file_view.selection()]
        for i, s in enumerate(sippers):
            self.ax.clear()
            all_args = self.get_argument_settings_dict()
            func_args = inspect.getfullargspec(func).args
            args = {k:v for k,v in all_args.items() if k in func_args}
            args['sipper'] = s
            args['ax'] = self.ax
            name = self.create_plot_name(self.plot_default_names[func])
            plot = SipperPlot(name, func, args)
            self.loaded_plots[name] = plot
            func(**args)
            self.plot_list.insert('', 'end', iid=plot.name, values=[plot.name])
            self.display_plot(plot, new=True)

    def get_argument_settings_dict(self):
        settings_dict = {'shade_dark':self.shade_dark_val.get(),
                         'show_left_count':self.dc_showleft_val.get(),
                         'show_right_count':self.dc_showright_val.get()}
        return settings_dict

    def display_plot(self, plot, new=False):
        if new:
            self.plot_list.selection_remove(self.plot_list.selection())
            self.plot_list.selection_set(plot.name)
        self.ax.clear()
        self.display_plot_details(plot)
        plot.func(**plot.args)
        self.canvas.draw_idle()
        self.update()

    def create_plot_name(self, basename):
        fig_name = basename
        c = 1
        current_names = self.loaded_plots.keys()
        while fig_name in current_names:
            fig_name = basename + ' ' + str(c)
            c += 1
        return fig_name

    def raise_plot_from_click(self, event):
        clicked = self.plot_list.selection()
        if len(clicked) == 1:
            plot = self.loaded_plots[clicked[0]]
            self.display_plot(plot)

    def display_plot_details(self, plot):
        self.plot_info.delete(*self.plot_info.get_children())
        for i, (k, v) in enumerate(plot.args.items()):
            nice_name = self.args_to_names.get(k, None)
            if nice_name:
                text = nice_name + ' : ' + str(v)
                self.plot_info.insert('', i, text=text)

plt.style.use('seaborn-whitegrid')
root = SipperViz()
if __name__ == "__main__":
    root.lift()
    root.attributes('-topmost', True)
    root.after_idle(root.attributes, '-topmost', False)
    root.focus_force()
    root.mainloop()
plt.close('all')
root.quit()