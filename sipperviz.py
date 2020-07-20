"""Code to run SipViz."""

from collections import OrderedDict
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

    #---create settings window
        self.settings_window = tk.Toplevel(self)
        self.settings_window.withdraw()
        self.settings_window.title('Settings')
        self.settings_tabs = ttk.Notebook(self.settings_window)
        self.settings_tabs.pack(fill='both', expand=1)
        self.settings_window.protocol("WM_DELETE_WINDOW",
                                      self.settings_window.withdraw)

    #---general settings
        self.general_settings = tk.Frame(self.settings_window)
        self.settings_tabs.add(self.general_settings, text='General')
        self.shade_dark_val = tk.BooleanVar()
        self.shade_dark_val.set(True)
        self.shade_dark_box = ttk.Checkbutton(self.general_settings,
                                              variable=self.shade_dark_val,
                                              text='Shade dark periods')
        self.shade_dark_box.grid(row=0, column=0, sticky='w', padx=20, pady=5)

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

    #---create button images
        icons = {'gear':"img/settings_icon.gif",
                 'bottle':'img/bottle_icon.png'}
        self.icons = {}
        for k, v in icons.items():
            image = Image.open(v).resize((25, 25))
            self.icons[k] = ImageTk.PhotoImage(image)

    #---create buttons
        self.button_frame = tk.Frame(self.main_frame)
        self.settings_button = tk.Button(self.button_frame,
                                         image=self.icons['gear'],
                                         text='Settings', compound='top',
                                         borderwidth=0,
                                         command=self.settings_window.deiconify)
        self.settings_button.grid(row=0, column=5, sticky='nsew', pady=5,
                                  padx=5)
        self.load_button = tk.Button(self.button_frame,
                                     image=self.icons['bottle'],
                                     text='Load', compound='top',
                                     borderwidth=0,
                                     command=self.load_files)
        self.load_button.grid(row=0, column=0, sticky='nsew', pady=5,
                                  padx=5)

    #---create file_view
        self.file_frame = tk.Frame(self.left_sash)
        self.file_view = ttk.Treeview(self.file_frame, height=20)
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
                                      height=10)
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
        self.plot_list = ttk.Treeview(self.plot_list_frame, height=15)
        self.plot_list.heading('#0', text='Plots')
        self.plot_list.column('#0', width=230)
        self.plot_list.bind('<<TreeviewSelect>>', self.raise_plot_from_click)
        self.plot_scroll = ttk.Scrollbar(self.plot_list_frame,
                                          command=self.plot_list.yview, )
        self.plot_list.configure(yscrollcommand=self.plot_scroll.set)
        self.plot_list.grid(row=0, column=0, sticky='nsw')
        self.plot_scroll.grid(row=0, column=1, sticky='nsw')

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
        for s in sippers:
            self.ax.clear()
            args = self.get_settings_as_args()
            args['sipper'] = s
            args['ax'] = self.ax
            name = self.create_plot_name(self.plot_default_names[func])
            plot = SipperPlot(name, func, args)
            self.loaded_plots[name] = plot
            func(**args)
            self.plot_list.insert('', 'end', iid=plot.name, text=plot.name)
            self.display_plot(plot)

    def get_settings_as_args(self):
        settings_dict = {'shade_dark':self.shade_dark_val.get()}
        return settings_dict

    def display_plot(self, plot):
        self.ax.clear()
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