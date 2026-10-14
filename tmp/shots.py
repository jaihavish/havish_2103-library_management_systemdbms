import os, sys, ctypes
sys.path.insert(0, r"D:\denos\hp1\app")
sys.path.insert(0, r"D:\denos\hp1\tests")
os.environ["LIB_DB_PASSWORD"] = "12345678"
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
import tkinter as tk
import mysql.connector
from PIL import ImageGrab
import library, app
from test_library import run_script

admin = mysql.connector.connect(host="localhost", user="root", password="12345678")
for f in ("01_schema.sql", "02_sample_data.sql", "03_views.sql"):
    run_script(admin, f)
admin.close()

OUT = r"D:\denos\hp1\tmp\shots"
os.makedirs(OUT, exist_ok=True)
root = tk.Tk()
root.geometry("1180x720+20+20")
root.attributes("-topmost", True)
a = app.App(root, library.Library(library.connect()))


def snap(name):
    root.update_idletasks(); root.update()
    root.after(250); root.update()
    x, y = root.winfo_rootx(), root.winfo_rooty()
    ImageGrab.grab((x, y, x + root.winfo_width(), y + root.winfo_height())).save(f"{OUT}\\{name}.png")
    print("saved", name, root.winfo_width(), root.winfo_height())


a.go("Dashboard"); snap("dashboard")

a.go("Catalogue"); p = a.pages["Catalogue"]
p.q.set("database"); p.filter(); snap("catalogue")

a.go("Members"); p = a.pages["Members"]
p.table.tree.selection_set("0"); p.table.tree.focus("0")   # first member alphabetically
for i, r in enumerate(p.table.rows):
    if r["card_no"] == "LIB2025001":
        p.table.tree.selection_set(str(i)); p.table.tree.see(str(i)); break
snap("members")

a.go("Issue & Return"); p = a.pages["Issue & Return"]
p.member.choose("LIB2025007")
p.copy.choose("ACC-0002")
p.issue(); snap("issue")
p.acc.set("ACC-0001"); p.ret(); snap("return")

a.go("Reservations"); snap("reservations")
a.go("Fines"); snap("fines")
a.go("Reports"); p = a.pages["Reports"]
p.pick.set("Overdue copies"); p.refresh(); snap("report_overdue")
p.pick.set("Fine collection by month"); p.refresh(); snap("report_fines")
a.go("Digital"); snap("digital")
root.destroy()

admin = mysql.connector.connect(host="localhost", user="root", password="12345678")
for f in ("01_schema.sql", "02_sample_data.sql", "03_views.sql"):
    run_script(admin, f)
print("db reset")
