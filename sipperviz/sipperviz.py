"""Code to run SipViz."""

import traceback
import tkinter as tk
from tkinter import ttk

import matplotlib as mpl
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk

import sipper
import sipperplots

class SipViz(tk.Tk):
    """Class for SipViz"""
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=C0103
    def __init__(self):
        super(SipViz, self).__init__()
    #---constants
        self.attr_conversion = {'Start':'start_date', 'End':'end_date',
                                'Duration':'duration', 'Device': 'device_no',
                                'Left Sipper Name':'left_name',
                                'Right Sipper Name':'right_name'}
        self.file_info_names = list(self.attr_conversion.keys())

    #---data management
        self.loaded_sippers = []

    #---create whole window
        self.title('SipViz')
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.main_frame = tk.Frame(self)
        self.main_frame.grid(row=0, column=0, sticky='nsew')
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)

    #---create treeview panes
        self.left_sash = ttk.PanedWindow(self.main_frame, orient='vertical')
        self.left_sash.grid(row=0, column=0, sticky='nsew')
        self.left_sash.grid_rowconfigure(0, weight=1)

    #---create menu
        self.menubar = tk.Menu(self.main_frame)
        self.config(menu=self.menubar)
        self.filemenu = tk.Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label='Load files', command=self.load_files)
        self.menubar.add_cascade(menu=self.filemenu, label='File')
        self.plotmenu = tk.Menu(self.menubar, tearoff=0)
        self.plotmenu.add_command(label='Drink Count', command=lambda:
                                  self.iter_plot(sipperplots.drinkcount))
        self.menubar.add_cascade(menu=self.plotmenu, label='Plot')

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
        self.info_frame.grid_rowconfigure(0,weight=1)
        self.info_view.grid(row=0, column=0, sticky='nsw')
        self.info_scroll.grid(row=0,column=1,sticky='nsw')

    #---create plotting area
        self.plot_frame = tk.Frame(self.main_frame)
        self.fig = mpl.figure.Figure()
        self.ax = self.fig.add_subplot()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.draw_idle()
        self.canvas.get_tk_widget().pack(side='bottom', fill='both', expand=1)
        #uncomment next two lines to add toolbar (must import also)
        self.nav_toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame)
        self.nav_toolbar.update()
        self.canvas._tkcanvas.pack(side='top', fill='both', expand=1)

    #---pack things for main frame
        self.left_sash.add(self.file_frame)
        self.left_sash.add(self.info_frame)
        self.plot_frame.grid(row=0, column=1, sticky='nsew')

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
            func(s, ax=self.ax)
            self.canvas.draw_idle()
            self.update()

plt.style.use('seaborn-whitegrid')
root = SipViz()
root.geometry("1000x600")
if __name__ == "__main__":
    root.lift()
    root.attributes('-topmost', True)
    root.after_idle(root.attributes, '-topmost', False)
    root.focus_force()
    root.mainloop()
