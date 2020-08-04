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

sipperplots.drinkcount_binned(s, show_right=False)

def groupby_getcontentdict(d):
    t1 = d.index.min()
    t2 = d.index.max()
    s1 = d['LeftContents'].unique()[0]
    s2 = d['RightContents'].unique()[0]
    return {(t1, t2):(s1, s2)}

def get_contents_dict(d):
    d = d.dropna(subset=['LeftContents', 'RightContents']).copy()
    l = d['LeftContents'].ne(d['LeftContents'].shift().bfill())
    r = d['RightContents'].ne(d['RightContents'].shift().bfill())
    changes = (l|r).astype(int).cumsum()
    groupdict = d.groupby(changes).apply(groupby_getcontentdict).to_dict()
    output = {}
    for i in groupdict.values():
        print(i)
        output.update(i)
    return output

x = get_contents_dict(d)

#%%
import tkinter as tk
from tkinter.font import Font

class CustomText(tk.Text):
    '''A text widget with a new method, highlight_pattern()

    example:

    text = CustomText()
    text.tag_configure("red", foreground="#ff0000")
    text.highlight_pattern("this should be red", "red")

    The highlight_pattern method is a simplified python
    version of the tcl code at http://wiki.tcl.tk/3246
    '''
    def __init__(self, *args, **kwargs):
        tk.Text.__init__(self, *args, **kwargs)

    def highlight_pattern(self, pattern, tag, start="1.0", end="end",
                          regexp=False):
        '''Apply the given tag to all text that matches the given pattern

        If 'regexp' is set to True, pattern will be treated as a regular
        expression according to Tcl's regular expression syntax.
        '''

        start = self.index(start)
        end = self.index(end)
        self.mark_set("matchStart", start)
        self.mark_set("matchEnd", start)
        self.mark_set("searchLimit", end)

        count = tk.IntVar()
        while True:
            index = self.search(pattern, "matchEnd","searchLimit",
                                count=count, regexp=regexp)
            if index == "": break
            if count.get() == 0: break # degenerate pattern which matches zero-length strings
            self.mark_set("matchStart", index)
            self.mark_set("matchEnd", "%s+%sc" % (index, count.get()))
            self.tag_add(tag, "matchStart", "matchEnd")

root = tk.Tk()
text = """
def foo(a, b, c=10)
    return a + b + c

class Main
    def __init__(self, value):
        self.value = value

# this is a comment

x = 1
d = 1.0
b = [1,2,3]
s = ["a"]
ss = ['a']"""
widget = CustomText(root, font='Courier')
widget.tag_configure('comment', foreground='gray')
widget.tag_configure('number', foreground='blue')
widget.tag_configure('string', foreground='green')
widget.tag_configure('keyword1', foreground='purple')
widget.tag_configure('self', foreground='red', font='Courier 12 italic')
widget.pack()
widget.insert('end', text)
widget.highlight_pattern('#.*', tag='comment', regexp=True)
widget.highlight_pattern('\d', tag='number', regexp=True)
widget.highlight_pattern('"."|\'.\'', tag='string', regexp=True)
widget.highlight_pattern('\n*\s*def\s', tag='keyword1', regexp=True)
widget.highlight_pattern('\n*\s*class\s', tag='keyword1', regexp=True)
widget.highlight_pattern('self', tag='self')
root.mainloop()