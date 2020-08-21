import plotdata
import sipper
import sipperplots

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

#%%
path = r"C:\Users\earne\Box\20200313 Behavior Study sipper data\4\SIP004_030320_00.CSV"
path2 = r"C:\Users\earne\Box\20200313 Behavior Study sipper data\4\SIP005_020320_01.CSV"



t1 = pd.Timestamp(year=2020, month=3, day=3, hour=13)
t2 = pd.Timestamp(year=2020, month=3, day=3, hour=21)
t3 = pd.Timestamp(year=2020, month=3, day=4, hour=0)
t4 = pd.Timestamp(year=2020, month=3, day=4, hour=4)

s = sipper.Sipper(path)
s.assign_contents({(t1,t2):("Water","Oxy"),
                    (t2,t3):("Oxy","Water"),
                    (t3,t4):('Pepsi',"Oxy")})
d = s.data

s2 = sipper.Sipper(path2)

sippers = [s, s2]
for i in sippers:
    i.groups.append('One')


#%%
l = d['LeftCount']
origin = l.index[0]
elapsed = [i - origin for i in l.index]
l.index = elapsed

#%%
import os

direc = r"C:\Users\earne\Desktop\same_date_sippers"
same_dates = []
t1 = pd.Timestamp(year=2020, month=2, day=3, hour=13)
t2 = pd.Timestamp(year=2020, month=2, day=6, hour=21)
t3 = pd.Timestamp(year=2020, month=2, day=13, hour=0)

for p in os.listdir(direc):
    sub = os.path.join(direc, p)
    s = sipper.Sipper(sub)
    if 'Copy' in p:
        s.groups.append('B')
    else:
        s.groups.append('A')
    s.assign_contents(({(t1,t2):("Water","Oxy"),
                        (t2,t3):("Oxy","Water"),}))
    same_dates.append(s)


    #%%
# Try to import Python 2 name
try:
    import Tkinter as tk
# Fall back to Python 3 if import fails
except ImportError:
    import tkinter as tk

class Example(tk.Frame):
    def __init__(self, root):
        tk.Frame.__init__(self, root)
        menubar = tk.Menu(self)
        fileMenu = tk.Menu(self)
        recentMenu = tk.Menu(self)

        menubar.add_cascade(label="File", menu=fileMenu)
        fileMenu.add_cascade(label="Open Recent", menu=recentMenu)
        for name in ("file1.txt", "file2.txt", "file3.txt"):
            recentMenu.add_command(label=name)


        root.configure(menu=menubar)
        root.geometry("200x200")

if __name__ == "__main__":
    root = tk.Tk()
    Example(root).pack(fill="both", expand=True)
    root.mainloop()