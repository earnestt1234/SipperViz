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

groups = d['LeftContents'].ne(d['LeftContents'].shift().bfill()).astype(int).cumsum()



def groupby_drinkcount(df, content):
    if content in df['LeftContents']:
        return df.loc[:,['LeftCount','LeftContents']]
    else:
        return df.loc[:,['RightCount','RightContents']]

gr = d.groupby(groups).apply(groupby_drinkcount, content='Oxy')
