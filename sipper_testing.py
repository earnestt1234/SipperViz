import sipper
import sipperplots
import pandas as pd

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

d['LeftContents'].ne(d['LeftContents'].shift().bfill()).astype(int).cumsum()

# s2 = sipper.Sipper(path2)

# d2 = s2.data

# sipperplots.drinkcount(s2, left=True, right=True, shade_dark=True,
#                        lights_on=7, lights_off=19)

