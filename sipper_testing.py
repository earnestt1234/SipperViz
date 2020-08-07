import plotdata
import sipper
import sipperplots

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

path = r"C:\Users\earne\Box\20200313 Behavior Study sipper data\4\SIP004_030320_00.CSV"
path2 = r"C:\Users\earne\Box\20200313 Behavior Study sipper data\4\SIP005_020320_01.CSV"


t1 = pd.Timestamp(year=2020, month=3, day=3, hour=13)
t2 = pd.Timestamp(year=2020, month=3, day=3, hour=21)
t3 = pd.Timestamp(year=2020, month=3, day=4, hour=0)
t4 = pd.Timestamp(year=2020, month=3, day=4, hour=4)

s = sipper.Sipper(path)
s.assign_contents({(t1,t2):("Water","Oxy"),
                    (t2,t3):("Oxy","Water"),
                    (t3,t4):('Water',"Oxy")})
d = s.data

s2 = sipper.Sipper(path2)

sippers = [s, s2]
for i in sippers:
    i.groups.append('One')

# sipperplots.drinkcount_chronogram(s2, circ_content=['Oxy'])

# sipperplots.drinkcount_chronogram_grouped(sippers, groups=['One'], circ_var='raw',
#                                           circ_content=['Oxy'])

k = plotdata.drinkcount_chronogram(s2, circ_content=['Oxy'])
