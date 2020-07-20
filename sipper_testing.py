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
from tkinter import ttk, Tk, Toplevel

root = Tk()
welcome_window = Toplevel(root)
welcome_window.title('Welcome')

lab_window = Toplevel(root)
lab_window.title('Lab')

root.withdraw() # hide root window
lab_window.withdraw() # hide lab window

def goto_lab():
    welcome_window.destroy()
    lab_window.deiconify() # show lab window

button1 = ttk.Button(welcome_window, text='Close',\
                     command=goto_lab)
button1.pack(padx=100, pady=50)

button2 = ttk.Button(lab_window, text='Close',\
                     command=quit)
button2.pack(padx=100, pady=50)

root.mainloop()