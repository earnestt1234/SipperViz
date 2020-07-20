import sipper
import sipperplots

path = r"C:\Users\earne\Box\20200313 Behavior Study sipper data\4\SIP004_030320_00.CSV"
path2 = r"C:\Users\earne\Box\20200313 Behavior Study sipper data\4\SIP005_020320_01.CSV"

s = sipper.Sipper(path)
d = s.data

s2 = sipper.Sipper(path2)
d2 = s2.data

sipperplots.drinkcount(s2, left=True, right=True, shade_dark=True,
                       lights_on=7, lights_off=19)

#%%
import tkinter as tk
from tkinter import ttk

root = tk.Tk()

# root.columnconfigure(0,weight=1)
root.rowconfigure(0,weight=1)

panes = ttk.Panedwindow(root,orient='vertical')
panes.grid(row=0,column=0,sticky='nsew')

f1 = ttk.Frame(panes)
f2 = ttk.Frame(panes)
f1.grid_rowconfigure(0,weight=1)
f2.grid_rowconfigure(0,weight=1)

t1 = ttk.Treeview(f1, height=20)
t1.grid(row=0,column=0,sticky='nsew')
t2 = ttk.Treeview(f2, height=10)
t2.grid(row=0,column=0,sticky='nsew')
panes.add(f1, weight=10)
panes.add(f2, weight=1)

root.mainloop()