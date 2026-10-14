"""Desktop front end for the library database (Tkinter).

Run:  python app.py
Database settings come from LIB_DB_HOST, LIB_DB_PORT, LIB_DB_USER,
LIB_DB_PASSWORD and LIB_DB_NAME. If the password is wrong you are asked for it.
"""
import csv
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

import mysql.connector

import library
from library import Library, LibraryError

# ---------- look ----------
NAVY, NAVY_HI, ACCENT = "#1b2540", "#2a3a63", "#3b6fe0"
BG, CARD, LINE = "#f3f5f9", "#ffffff", "#dfe3ec"
TEXT, MUTED = "#1f2937", "#6b7280"
RED_BG, AMBER_BG, GREEN_BG = "#fde8e8", "#fff4d6", "#e3f6ea"
FONT = ("Segoe UI", 10)


def open_library(root):
    password = None
    while True:
        try:
            return Library(library.connect(password))
        except mysql.connector.Error as e:
            if e.errno == 1045:
                password = simpledialog.askstring("Database login", "MySQL password:", show="*", parent=root)
                if password is None:
                    raise SystemExit
            else:
                messagebox.showerror("Cannot connect", str(e))
                raise SystemExit


def setup_style(root):
    st = ttk.Style(root)
    st.theme_use("clam")
    root.configure(bg=BG)
    st.configure(".", font=FONT, background=BG, foreground=TEXT)
    st.configure("TFrame", background=BG)
    st.configure("Card.TFrame", background=CARD, relief="solid", borderwidth=1, bordercolor=LINE)
    st.configure("TLabel", background=BG)
    st.configure("Inner.TFrame", background=CARD)
    st.configure("Card.TLabel", background=CARD)
    st.configure("Muted.TLabel", foreground=MUTED)
    st.configure("H1.TLabel", font=("Segoe UI Semibold", 18))
    st.configure("H2.TLabel", font=("Segoe UI Semibold", 11), background=CARD)
    st.configure("TButton", padding=(12, 6), background="#e8ecf4", borderwidth=0, focuscolor="none")
    st.map("TButton", background=[("active", "#d7dded")])
    st.configure("Accent.TButton", background=ACCENT, foreground="white")
    st.map("Accent.TButton", background=[("active", "#2f5bc0")])
    st.configure("Danger.TButton", background="#d64545", foreground="white")
    st.map("Danger.TButton", background=[("active", "#b83636")])
    st.configure("TEntry", padding=5, fieldbackground="white", bordercolor=LINE)
    st.configure("TCombobox", padding=5, fieldbackground="white")
    st.map("TCombobox", fieldbackground=[("readonly", "white")], background=[("readonly", "#e8ecf4")])
    st.configure("TCheckbutton", background=BG)
    st.configure("Treeview", rowheight=27, background="white", fieldbackground="white",
                 bordercolor=LINE, borderwidth=1)
    st.configure("Treeview.Heading", font=("Segoe UI Semibold", 10), background="#e9edf5",
                 foreground=TEXT, padding=6, relief="flat")
    st.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", "white")])


class Table(ttk.Frame):
    """Striped table. Rows are dicts. Click a row to get it from .selected()."""

    def __init__(self, parent, height=10, on_select=None):
        super().__init__(parent)
        self.tree = ttk.Treeview(self, show="headings", height=height, selectmode="browse")
        vs = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hs = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        for tag, bg in (("even", "white"), ("odd", "#f7f9fc"), ("bad", RED_BG),
                        ("warn", AMBER_BG), ("good", GREEN_BG)):
            self.tree.tag_configure(tag, background=bg)
        self.rows = []
        if on_select:
            self.tree.bind("<<TreeviewSelect>>", lambda _e: on_select(self.selected()))

    @staticmethod
    def _tag(row, i):
        if (row.get("days_overdue") or 0) > 0 or row.get("loan_status") == "OVERDUE"                 or row.get("status") in ("EXPIRED", "SUSPENDED"):
            return "bad"
        if (row.get("balance") or 0) > 0 or row.get("available") == 0:
            return "warn"
        if row.get("status") == "READY":
            return "good"
        return "even" if i % 2 == 0 else "odd"

    def show(self, rows):
        self.rows = list(rows or [])
        t = self.tree
        t.delete(*t.get_children())
        if not self.rows:
            t["columns"] = ("info",)
            t.heading("info", text="")
            t.column("info", width=300)
            t.insert("", "end", values=("Nothing to show.",))
            return
        cols = list(self.rows[0].keys())
        t["columns"] = cols
        for c in cols:
            longest = max(len(str(r[c])) for r in self.rows[:60])
            width = max(80, min(340, max(longest * 9, len(c) * 11) + 30))
            t.heading(c, text=c.replace("_", " ").title())
            t.column(c, width=width, anchor="e" if isinstance(self.rows[0][c], (int, float)) else "w")
        for i, r in enumerate(self.rows):
            t.insert("", "end", iid=str(i), tags=(self._tag(r, i),),
                     values=["" if v is None else v for v in r.values()])

    def selected(self):
        sel = self.tree.selection()
        return self.rows[int(sel[0])] if sel and self.rows else None


class Picker(ttk.Combobox):
    """Drop-down that shows readable text but returns a key."""

    def __init__(self, parent, width=44):
        super().__init__(parent, state="readonly", width=width)
        self.keys = []

    def load(self, rows, label, key):
        self.keys = [r[key] for r in rows]
        self["values"] = [label(r) for r in rows]
        self.set("")

    def choose(self, key):
        if key in self.keys:
            self.current(self.keys.index(key))

    @property
    def value(self):
        i = self.current()
        if i < 0:
            raise LibraryError("Please pick an item from the list.")
        return self.keys[i]


def card(parent, title=None, **grid):
    f = ttk.Frame(parent, style="Card.TFrame", padding=14)
    if title:
        ttk.Label(f, text=title, style="H2.TLabel").pack(anchor="w", pady=(0, 8))
    return f


def field(parent, label, row, width=30, show=None):
    ttk.Label(parent, text=label, style="Card.TLabel").grid(row=row, column=0, sticky="w", pady=4, padx=(0, 10))
    v = tk.StringVar()
    ttk.Entry(parent, textvariable=v, width=width, show=show).grid(row=row, column=1, sticky="ew", pady=4)
    return v


class Dialog(tk.Toplevel):
    def __init__(self, app, title):
        super().__init__(app.root)
        self.title(title)
        self.configure(bg=CARD, padx=20, pady=16)
        self.transient(app.root)
        self.resizable(False, False)
        self.grab_set()
        self.body = ttk.Frame(self, style="Inner.TFrame")
        self.body.pack()
        self.body.columnconfigure(1, weight=1)


class App:
    def __init__(self, root, lib):
        self.root, self.lib = root, lib
        setup_style(root)
        side = tk.Frame(root, bg=NAVY, width=210)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Label(side, text="Library", bg=NAVY, fg="white", font=("Segoe UI Semibold", 20)).pack(
            anchor="w", padx=20, pady=(22, 0))
        tk.Label(side, text="Circulation system", bg=NAVY, fg="#9fb0d6", font=("Segoe UI", 9)).pack(
            anchor="w", padx=20, pady=(0, 22))
        main = ttk.Frame(root, padding=(24, 18))
        main.pack(side="left", fill="both", expand=True)
        self.title = ttk.Label(main, style="H1.TLabel")
        self.title.pack(anchor="w", pady=(0, 12))
        self.status = tk.StringVar(value="Ready.")
        tk.Label(main, textvariable=self.status, anchor="w", bg=BG, fg=MUTED).pack(side="bottom", fill="x", pady=(8, 0))
        self.holder = ttk.Frame(main)
        self.holder.pack(fill="both", expand=True)

        self.pages, self.navs, self.current = {}, {}, None
        for name, cls in [("Dashboard", DashboardPage), ("Catalogue", CataloguePage),
                          ("Members", MembersPage), ("Issue & Return", CirculationPage),
                          ("Reservations", ReservationsPage), ("Fines", FinesPage),
                          ("Digital", DigitalPage), ("Reports", ReportsPage)]:
            page = cls(self.holder, self)
            self.pages[name] = page
            b = tk.Label(side, text="   " + name, anchor="w", bg=NAVY, fg="white", font=("Segoe UI", 11),
                         padx=8, pady=9, cursor="hand2")
            b.pack(fill="x")
            b.bind("<Button-1>", lambda _e, n=name: self.go(n))
            b.bind("<Enter>", lambda _e, w=b, n=name: w.configure(bg=NAVY_HI) if n != self.current else None)
            b.bind("<Leave>", lambda _e, w=b, n=name: w.configure(bg=NAVY) if n != self.current else None)
            self.navs[name] = b
        self.go("Dashboard")

    def go(self, name):
        if self.current:
            self.pages[self.current].pack_forget()
            self.navs[self.current].configure(bg=NAVY)
        self.current = name
        self.navs[name].configure(bg=ACCENT)
        self.title.configure(text=name)
        self.pages[name].pack(fill="both", expand=True)
        self.pages[name].refresh()

    def refresh(self):
        self.pages[self.current].refresh()

    def run(self, action, ok=None, refresh=True):
        """Run a library call. Errors go in a box, success goes in the status bar."""
        try:
            result = action()
        except LibraryError as e:
            messagebox.showwarning("Cannot do that", str(e), parent=self.root)
            self.status.set("Failed: " + str(e))
            return None
        except mysql.connector.Error as e:
            messagebox.showerror("Database error", str(e), parent=self.root)
            self.status.set("Database error.")
            return None
        if ok:
            self.status.set(ok(result) if callable(ok) else ok)
        if refresh:
            self.refresh()
        return result if result is not None else True


# ---------- pages ----------

class Page(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app, self.lib = app, app.lib
        self.build()

    def build(self):
        pass

    def refresh(self):
        pass


class DashboardPage(Page):
    def build(self):
        self.grid_f = ttk.Frame(self)
        self.grid_f.pack(fill="x")
        self.tiles = {}
        for i in range(4):
            self.grid_f.columnconfigure(i, weight=1, uniform="t")
        lower = ttk.Frame(self)
        lower.pack(fill="both", expand=True, pady=(14, 0))
        lower.columnconfigure((0, 1), weight=1, uniform="c")
        lower.rowconfigure(0, weight=1)
        c1 = card(lower, "Overdue copies")
        c1.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.overdue = Table(c1, 8)
        self.overdue.pack(fill="both", expand=True)
        c2 = card(lower, "Most popular books")
        c2.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.popular = Table(c2, 8)
        self.popular.pack(fill="both", expand=True)

    def refresh(self):
        stats = self.app.run(lambda: library.dashboard_stats(self.lib), refresh=False)
        if not stats:
            return
        colours = {"Overdue": "#d64545", "Unpaid fines (Rs)": "#d98a00"}
        for w in self.grid_f.winfo_children():
            w.destroy()
        for i, (k, v) in enumerate(stats.items()):
            t = ttk.Frame(self.grid_f, style="Card.TFrame", padding=(16, 12))
            t.grid(row=i // 4, column=i % 4, sticky="nsew", padx=6, pady=6)
            tk.Label(t, text=str(v), bg=CARD, fg=colours.get(k, ACCENT), font=("Segoe UI Semibold", 24)).pack(anchor="w")
            tk.Label(t, text=k, bg=CARD, fg=MUTED).pack(anchor="w")
        self.overdue.show(self.lib.rows(
            "SELECT accession_no, title, full_name AS member, days_overdue, fine_so_far "
            "FROM v_overdue_copies ORDER BY days_overdue DESC"))
        self.popular.show(self.lib.rows(library.REPORTS["Popular books"]))


class CataloguePage(Page):
    def build(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 10))
        self.q = tk.StringVar()
        e = ttk.Entry(bar, textvariable=self.q, width=40)
        e.pack(side="left")
        e.bind("<KeyRelease>", lambda _e: self.filter())
        ttk.Label(bar, text="  Search by title, author, category or ISBN", style="Muted.TLabel").pack(side="left")
        ttk.Button(bar, text="Add book", style="Accent.TButton", command=self.add_book).pack(side="right")
        ttk.Button(bar, text="Add copy", command=self.add_copy).pack(side="right", padx=6)
        ttk.Button(bar, text="Withdraw copy", command=self.withdraw).pack(side="right")
        self.table = Table(self, 12)
        self.table.pack(fill="both", expand=True)
        ttk.Label(self, text="Amber rows have no copy on the shelf right now.", style="Muted.TLabel").pack(
            anchor="w", pady=(6, 0))
        self.all_rows = []

    def refresh(self):
        self.all_rows = self.app.run(lambda: library.catalogue(self.lib), refresh=False) or []
        self.filter()

    def filter(self):
        t = self.q.get().strip().lower()
        self.table.show([r for r in self.all_rows if not t or t in " ".join(map(str, r.values())).lower()])

    def add_book(self):
        d = Dialog(self.app, "Add a book")
        f = d.body
        title, authors = field(f, "Title", 0, 40), field(f, "Authors (comma separated)", 1, 40)
        pub, isbn = field(f, "Publisher", 2, 40), field(f, "ISBN (13 digits)", 3, 40)
        ed, year, pages = field(f, "Edition no", 4, 40), field(f, "Year", 5, 40), field(f, "Pages", 6, 40)
        ed.set("1")
        cats = {c["name"]: c["category_id"] for c in self.lib.categories()}
        ttk.Label(f, text="Category", style="Card.TLabel").grid(row=7, column=0, sticky="w", pady=4)
        cat = ttk.Combobox(f, values=list(cats), state="readonly", width=38)
        cat.grid(row=7, column=1, sticky="ew", pady=4)
        cat.current(0)

        def save():
            if self.app.run(lambda: self.lib.add_book(title.get(), cats[cat.get()], authors.get(), pub.get(),
                                                      isbn.get(), ed.get(), year.get(), pages.get()),
                            "Book added to the catalogue."):
                d.destroy()
        ttk.Button(f, text="Save", style="Accent.TButton", command=save).grid(row=8, column=1, sticky="e", pady=(10, 0))

    def add_copy(self):
        row = self.table.selected()
        if not row:
            return messagebox.showinfo("Add copy", "Click a book in the table first.", parent=self.app.root)
        d = Dialog(self.app, "Add a copy")
        ttk.Label(d.body, text=row["title"], style="H2.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        acc, shelf = field(d.body, "Accession no", 1), field(d.body, "Shelf", 2)

        def save():
            if self.app.run(lambda: self.lib.add_copy(row["isbn"], acc.get(), shelf.get()), "Copy added."):
                d.destroy()
        ttk.Button(d.body, text="Save", style="Accent.TButton", command=save).grid(row=3, column=1, sticky="e", pady=(10, 0))

    def withdraw(self):
        acc = simpledialog.askstring("Withdraw copy", "Accession number to withdraw:", parent=self.app.root)
        if acc:
            self.app.run(lambda: self.lib.remove_copy(acc), "Copy withdrawn.")


class MembersPage(Page):
    def build(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 10))
        self.q = tk.StringVar()
        e = ttk.Entry(bar, textvariable=self.q, width=40)
        e.pack(side="left")
        e.bind("<KeyRelease>", lambda _e: self.filter())
        ttk.Label(bar, text="  Search by name, card or email", style="Muted.TLabel").pack(side="left")
        ttk.Button(bar, text="Register member", style="Accent.TButton", command=self.register).pack(side="right")
        self.table = Table(self, 9, on_select=self.show_history)
        self.table.pack(fill="both", expand=True)
        c = card(self, "Borrowing history of the selected member")
        c.pack(fill="both", expand=True, pady=(10, 0))
        self.hist = Table(c, 7)
        self.hist.pack(fill="both", expand=True)
        self.all_rows = []

    def refresh(self):
        self.all_rows = self.app.run(lambda: library.all_members(self.lib), refresh=False) or []
        self.filter()

    def filter(self):
        t = self.q.get().strip().lower()
        self.table.show([r for r in self.all_rows if not t or t in " ".join(map(str, r.values())).lower()])

    def show_history(self, row):
        if row:
            self.hist.show(library.member_history(self.lib, row["card_no"]))

    def register(self):
        d = Dialog(self.app, "Register a member")
        f = d.body
        card_no, name = field(f, "Card no", 0, 34), field(f, "Full name", 1, 34)
        email, phone = field(f, "Email", 2, 34), field(f, "Phone (10 digits)", 3, 34)
        ttk.Label(f, text="Type", style="Card.TLabel").grid(row=4, column=0, sticky="w", pady=4)
        typ = ttk.Combobox(f, values=["STUDENT", "FACULTY", "PUBLIC"], state="readonly", width=32)
        typ.grid(row=4, column=1, sticky="ew", pady=4)
        typ.current(0)

        def save():
            if self.app.run(lambda: self.lib.register_member(card_no.get(), name.get(), email.get(),
                                                             phone.get(), typ.get()),
                            "Member registered for one year."):
                d.destroy()
        ttk.Button(f, text="Register", style="Accent.TButton", command=save).grid(row=5, column=1, sticky="e", pady=(10, 0))


class CirculationPage(Page):
    def build(self):
        top = ttk.Frame(self)
        top.pack(fill="x")
        top.columnconfigure((0, 1), weight=1, uniform="a")
        c1 = card(top, "Issue a book")
        c1.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ttk.Label(c1, text="Member", style="Card.TLabel").pack(anchor="w")
        self.member = Picker(c1, 50)
        self.member.pack(fill="x", pady=(2, 8))
        ttk.Label(c1, text="Book copy (shelf or held for a member)", style="Card.TLabel").pack(anchor="w")
        self.copy = Picker(c1, 50)
        self.copy.pack(fill="x", pady=(2, 10))
        ttk.Button(c1, text="Issue book", style="Accent.TButton", command=self.issue).pack(anchor="e")

        c2 = card(top, "Return or renew")
        c2.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ttk.Label(c2, text="Click a row below, or type the accession no:",
                  style="Card.TLabel").pack(anchor="w")
        self.acc = tk.StringVar()
        ttk.Entry(c2, textvariable=self.acc, width=24).pack(anchor="w", pady=(4, 10))
        row = ttk.Frame(c2, style="Inner.TFrame")
        row.pack(anchor="e", fill="x")
        ttk.Button(row, text="Renew", command=self.renew).pack(side="right")
        ttk.Button(row, text="Return book", style="Accent.TButton", command=self.ret).pack(side="right", padx=8)

        c3 = card(self, "Books currently on loan")
        c3.pack(fill="both", expand=True, pady=(12, 0))
        self.table = Table(c3, 6, on_select=lambda r: r and self.acc.set(r["accession_no"]))
        self.table.pack(fill="both", expand=True)
        ttk.Label(c3, text="Red rows are overdue.", style="Muted.TLabel").pack(anchor="w", pady=(6, 0))

    def refresh(self):
        self.member.load(library.member_choices(self.lib),
                         lambda r: f"{r['full_name']}  ({r['card_no']}, {r['member_type'].title()})", "card_no")
        self.copy.load(library.available_copies(self.lib),
                       lambda r: f"{r['accession_no']}  ·  {r['title']}", "accession_no")
        rows = library.loans_out(self.lib)
        for r in rows:               # use a plain key so the table colours overdue rows
            r["days_overdue"] = r.pop("days_late")
        self.table.show(rows)

    def issue(self):
        def go():
            return self.lib.issue_book(self.member.value, self.copy.value)
        self.app.run(go, lambda due: f"Issued. Due back on {due}.")

    def ret(self):
        self.app.run(lambda: self.lib.return_book(self.acc.get()),
                     lambda fine: "Returned on time. No fine." if fine == 0 else f"Returned late. Fine: Rs {fine}")

    def renew(self):
        self.app.run(lambda: self.lib.renew_book(self.acc.get()), lambda due: f"Renewed. New due date {due}.")


class ReservationsPage(Page):
    def build(self):
        c = card(self, "Reserve a title (only titles with no copy on the shelf)")
        c.pack(fill="x")
        r = ttk.Frame(c, style="Inner.TFrame")
        r.pack(fill="x")
        self.member = Picker(r, 28)
        self.member.pack(side="left")
        self.title = Picker(r, 34)
        self.title.pack(side="left", padx=8)
        ttk.Button(r, text="Reserve", style="Accent.TButton", command=self.reserve).pack(side="left")
        ttk.Button(r, text="Cancel selected", style="Danger.TButton", command=self.cancel).pack(side="right")
        c2 = card(self, "Reservation queue")
        c2.pack(fill="both", expand=True, pady=(12, 0))
        self.table = Table(c2, 9)
        self.table.pack(fill="both", expand=True)
        ttk.Label(c2, text="READY means a copy is being held for that member.", style="Muted.TLabel").pack(
            anchor="w", pady=(6, 0))

    def refresh(self):
        self.member.load(library.member_choices(self.lib), lambda r: f"{r['full_name']} ({r['card_no']})", "card_no")
        self.title.load(library.reservable_editions(self.lib),
                        lambda r: f"{r['title']}  (ed. {r['edition_no']})", "isbn")
        self.table.show(library.reservations_live(self.lib))

    def reserve(self):
        self.app.run(lambda: self.lib.reserve(self.member.value, self.title.value),
                     lambda q: f"Reserved. Queue number {q}.")

    def cancel(self):
        row = self.table.selected()
        if not row:
            return messagebox.showinfo("Cancel", "Click a reservation first.", parent=self.app.root)
        self.app.run(lambda: self.lib.cancel_reservation(row["reservation_id"]), "Reservation cancelled.")


class FinesPage(Page):
    def build(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 10))
        self.unpaid = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="Show unpaid only", variable=self.unpaid, command=self.refresh).pack(side="left")
        self.amount = tk.StringVar()
        ttk.Button(bar, text="Take payment", style="Accent.TButton", command=self.pay).pack(side="right")
        ttk.Entry(bar, textvariable=self.amount, width=10).pack(side="right", padx=6)
        ttk.Label(bar, text="Amount (Rs):").pack(side="right")
        self.table = Table(self, 12, on_select=lambda r: r and self.amount.set(str(r["balance"])))
        self.table.pack(fill="both", expand=True)
        ttk.Label(self, text="Click a fine, check the amount (it fills in the full balance), then take payment.",
                  style="Muted.TLabel").pack(anchor="w", pady=(6, 0))

    def refresh(self):
        self.table.show(library.all_fines(self.lib, self.unpaid.get()))

    def pay(self):
        row = self.table.selected()
        if not row:
            return messagebox.showinfo("Payment", "Click a fine first.", parent=self.app.root)
        self.app.run(lambda: self.lib.pay_fine(row["fine_id"], self.amount.get()),
                     lambda left: f"Payment taken. Balance left: Rs {left}")


class DigitalPage(Page):
    def build(self):
        c = card(self, "Record digital access")
        c.pack(fill="x")
        r = ttk.Frame(c, style="Inner.TFrame")
        r.pack(fill="x")
        self.member = Picker(r, 28)
        self.member.pack(side="left")
        self.res = Picker(r, 34)
        self.res.pack(side="left", padx=8)
        self.mins = tk.StringVar(value="30")
        ttk.Entry(r, textvariable=self.mins, width=6).pack(side="left")
        ttk.Label(r, text=" min  ", style="Card.TLabel").pack(side="left")
        ttk.Button(r, text="Log access", style="Accent.TButton", command=self.log).pack(side="left")
        c2 = card(self, "Usage by resource")
        c2.pack(fill="both", expand=True, pady=(12, 0))
        self.table = Table(c2, 9)
        self.table.pack(fill="both", expand=True)

    def refresh(self):
        self.member.load(library.member_choices(self.lib), lambda r: f"{r['full_name']} ({r['card_no']})", "card_no")
        self.res.load(self.lib.digital_resources(), lambda r: f"{r['title']} [{r['resource_type'].lower()}]",
                      "resource_id")
        self.table.show(self.lib.rows(library.REPORTS["Digital resource usage"]))

    def log(self):
        self.app.run(lambda: self.lib.log_digital_access(self.member.value, self.res.value, self.mins.get()),
                     "Access recorded.")


class ReportsPage(Page):
    def build(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 10))
        self.pick = ttk.Combobox(bar, values=list(library.REPORTS), state="readonly", width=34)
        self.pick.pack(side="left")
        self.pick.current(0)
        self.pick.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        ttk.Button(bar, text="Save as CSV", command=self.export).pack(side="right")
        self.table = Table(self, 12)
        self.table.pack(fill="both", expand=True)

    def refresh(self):
        rows = self.app.run(lambda: self.lib.rows(library.REPORTS[self.pick.get()]), refresh=False)
        self.table.show(rows if rows and rows is not True else [])
        self.app.status.set(f"{self.pick.get()}: {len(self.table.rows)} rows.")

    def export(self):
        if not self.table.rows:
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=self.pick.get() + ".csv",
                                            filetypes=[("CSV file", "*.csv")], parent=self.app.root)
        if path:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(self.table.rows[0]))
                w.writeheader()
                w.writerows(self.table.rows)
            self.app.status.set("Saved " + path)


def main():
    root = tk.Tk()
    root.title("Library Circulation System")
    root.geometry("1180x720")
    root.minsize(980, 620)
    App(root, open_library(root))
    root.mainloop()


if __name__ == "__main__":
    main()
