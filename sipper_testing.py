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

def drinkcount_cumulative(sipper, show_left=True, show_right=True,
                          show_content=[], shade_dark=True,
                          lights_on=7, lights_off=19, **kwargs):
    if 'ax' in kwargs:
        ax = kwargs['ax']
    else:
        fig, ax = plt.subplots()
    df = sipper.data
    if 'date_filter' in kwargs:
        s, e = kwargs['date_filter']
        df = df[(df.index >= s) &
                (df.index <= e)].copy()
    if show_left:
        ax.plot(df.index, df['LeftCount'], drawstyle='steps', color='red',
                label=sipper.left_name)
    if show_right:
        ax.plot(df.index, df['RightCount'], drawstyle='steps', color='blue',
                label=sipper.right_name)
    content_max = df.index.min()
    content_min = df.index.max()
    if show_content:
        for c in show_content:
            count = sipper.get_content_values(c, out='Count', df=df)
            if not count.empty:
                ax.plot(count.index, count, drawstyle='steps', label=c)
                if count.index.max() > content_max:
                    content_max = count.index.max()
                if count.index.min() < content_min:
                    content_min = count.index.min()
    if any((show_right, show_left)):
        date_format_x(ax, df.index[0], df.index[-1])
    else:
        date_format_x(ax, content_min, content_max)
    ax.set_title('Drink Count for ' + sipper.filename)
    ax.set_ylabel('Total Drinks')
    ax.set_xlabel('Date')
    if shade_dark:
        shade_darkness(ax, df.index[0], df.index[-1], lights_on, lights_off)
    ax.legend()
    plt.tight_layout()
    return fig if 'ax' not in kwargs else None