import sipper
import sipperplots
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
o = s.get_content_values('Oxy', 'Count')

sipperplots.drinkcount_cumulative(s, show_content_count=['Oxy'])