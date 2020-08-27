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

direc = r"C:\Users\earne\Desktop\sipper_example_data\same_date_sippers"
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

sipperplots.cumulative_averaged_drinkcount(same_dates, groups=['A'], avg_bins='4H')
dd = plotdata.cumulative_averaged_drinkcount(same_dates, groups=['A'], avg_bins='4H')

