import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import random
import string
from datetime import datetime
import sqlite3

# ---------- Files ----------

VOUCHER_FILE = "vouchers.json"
ORDER_FILE = "orders.json"
DB_FILE = "restaurant.db"

# ---------- Colors / Fonts ----------

BG_COLOR = "#f8f0d8"
PANEL_BG = "#f5e8c6"
HEADER_BG = "#b4876e"
HEADER_FG = "white"
TITLE_FONT = ("Segoe UI", 20, "bold")
SUBTITLE_FONT = ("Segoe UI", 14, "bold")
TEXT_FONT = ("Segoe UI", 11)
BUTTON_FONT = ("Segoe UI", 10, "bold")
COL_HEADER_FONT = ("Segoe UI", 11, "bold")

BLUE_BTN = "#0d73d6"
GREEN_BTN = "#218838"
BROWN_BTN = "#8b5a3c"
RED_BTN = "#d9534f"

CATEGORIES = ["Kacchi Combo", "Drinks & Dessert", "Add-ons", "Sharing Platter"]

# ---------- Default menu (first run only) ----------

DEFAULT_MENU = {
    "Kacchi Combo": [
        ("Basic Kacchi", 300),
        ("Kacchi Meal", 320),
        ("Kacchi + Borhani + Firni", 420),
        ("Kacchi + Roast + Borhani", 450),
        ("Kacchi + Roast + Borhani + Firni", 480),
    ],
    "Drinks & Dessert": [
        ("Borhani", 60),
        ("Soft Drink", 40),
        ("Mineral Water", 20),
        ("Firni", 50),
        ("Jorda", 50),
    ],
    "Add-ons": [
        ("Plain Polao", 250),
        ("Chicken Roast", 200),
        ("Beef Rezala", 220),
        ("Jali Kabab", 80),
        ("Salad", 40),
        ("Chatni", 20),
    ],
    "Sharing Platter": [
        ("Sharing Platter 1", 280),
        ("Sharing Platter 2", 920),
    ],
}

# ---------- Admin password helper ----------

ADMIN_PASSWORDS = {
    "Tanim119": "Tanim",
    "Mim31": "Mim",
}


def ask_admin_password(message="Enter admin password:"):
    pw = simpledialog.askstring("Admin Access", message, show="*")
    if pw is None:
        return None
    if pw in ADMIN_PASSWORDS:
        return ADMIN_PASSWORDS[pw]
    messagebox.showerror("Access denied", "Wrong admin password.")
    return None


# ---------- DB helpers (employees + menu) ----------

def init_db():
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0
        )
    """)

    # seed default menu if empty
    cur.execute("SELECT COUNT(*) FROM menu_items")
    if cur.fetchone()[0] == 0:
        for cat, items in DEFAULT_MENU.items():
            for sort_order, (name, price) in enumerate(items):
                cur.execute(
                    "INSERT INTO menu_items(category, name, price, sort_order) "
                    "VALUES (?,?,?,?)",
                    (cat, name, float(price), sort_order),
                )
        con.commit()

    con.close()


def load_employees():
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("SELECT id, name, password FROM employees ORDER BY id")
    rows = cur.fetchall()
    con.close()
    return [{"id": r[0], "name": r[1], "password": r[2]} for r in rows]


def save_employees(employees):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("DELETE FROM employees")
    for emp in employees:
        cur.execute(
            "INSERT INTO employees(id, name, password) VALUES (?,?,?)",
            (emp["id"], emp["name"], emp["password"]),
        )
    con.commit()
    con.close()


def load_menu_data():
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    data = {}
    for cat in CATEGORIES:
        cur.execute(
            "SELECT name, price FROM menu_items "
            "WHERE category=? ORDER BY sort_order, id",
            (cat,),
        )
        rows = cur.fetchall()
        data[cat] = [(name, float(price)) for (name, price) in rows]
    con.close()
    return data


def update_menu_category(cat, items):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("DELETE FROM menu_items WHERE category=?", (cat,))
    for idx, (name, price) in enumerate(items):
        cur.execute(
            "INSERT INTO menu_items(category, name, price, sort_order) "
            "VALUES (?,?,?,?)",
            (cat, name, float(price), idx),
        )
    con.commit()
    con.close()


# ---------- JSON helpers for vouchers/orders ----------

def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Error saving", path, ":", e)


def load_vouchers():
    raw = load_json(VOUCHER_FILE, {})
    # Old format handle: list -> convert to dict
    if isinstance(raw, list):
        converted = {}
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            code = str(entry.get("code", "")).upper()
            if not code:
                continue
            converted[code] = {
                "code": code,
                "discount": float(entry.get("discount", entry.get("percent", 0))),
                "max_uses": int(entry.get("max_uses", entry.get("max", 0))),
                "used": int(entry.get("used", 0)),
                "deleted": bool(entry.get("deleted", False)),
            }
        raw = converted

    normalized = {}
    for code, v in raw.items():
        code_u = str(code).upper()
        normalized[code_u] = {
            "code": code_u,
            "discount": float(v.get("discount", v.get("percent", 0))),
            "max_uses": int(v.get("max_uses", v.get("max", 0))),
            "used": int(v.get("used", 0)),
            "deleted": bool(v.get("deleted", False)),
        }
    return normalized


def save_vouchers(vouchers):
    save_json(VOUCHER_FILE, vouchers)


def load_orders():
    return load_json(ORDER_FILE, [])


def save_orders(orders):
    save_json(ORDER_FILE, orders)


# ---------- Formatting helpers ----------

def format_tk(amount):
    return f"Tk {amount:,.2f}"


def format_item_price(amount):
    a = float(amount)
    if a.is_integer():
        return f"{int(a)} Tk"
    else:
        return f"{a:,.2f} Tk"


# ---------- Tk root ----------

root = tk.Tk()
root.title("Kacchi Bhai Style Restaurant Billing - Bangladesh")
root.configure(bg=BG_COLOR)
root.geometry("1200x700")   # a little taller, so Add-ons fits nicely

# ---------- Global state ----------

init_db()
employees = load_employees()
vouchers = load_vouchers()
orders = load_orders()
menu_data = load_menu_data()

current_user_name = None
current_role = None

login_frame = tk.Frame(root, bg=BG_COLOR)
main_frame = tk.Frame(root, bg=BG_COLOR)

user_label_var = tk.StringVar(value="User: ---")

menu_items = []
selection_total_var = tk.DoubleVar(value=0.0)

applied_voucher_code = None
applied_discount_percent = 0.0

bill_no_var = tk.StringVar()
datetime_var = tk.StringVar()
food_cost_var = tk.StringVar(value="Tk 0.00")

discount_display_var = tk.StringVar(value="Tk 0.00")
vat_var            = tk.StringVar(value="Tk 0.00")
total_bill_var     = tk.StringVar(value="Tk 0.00")


payment_method_var = tk.StringVar(value="Cash")
paid_amount_var = tk.StringVar()
change_due_var = tk.StringVar()

voucher_entry_var = tk.StringVar()
voucher_message_var = tk.StringVar()

paid_amount_entry = None

content_frame = None
menu_page = None
summary_page = None


# ---------- Transaction helpers ----------

def reset_transaction():
    global applied_voucher_code, applied_discount_percent
    for item in menu_items:
        item["qty_var"].set(0)
        item["total_var"].set(0.0)
        item["total_str_var"].set("0 Tk")
        if "menu_total_label" in item:
            item["menu_total_label"].config(fg="black")
    selection_total_var.set(0.0)
    applied_voucher_code = None
    applied_discount_percent = 0.0
    voucher_entry_var.set("")
    voucher_message_var.set("")
    bill_no_var.set("")
    datetime_var.set("")
    food_cost_var.set("Tk 0.00")
    discount_display_var.set("Tk 0.00")
    vat_var.set("Tk 0.00")
    total_bill_var.set("Tk 0.00")
    paid_amount_var.set("")
    change_due_var.set("")


def generate_bill_no():
    return str(random.randint(20000, 49999))


def calculate_totals():
    subtotal = 0.0
    for item in menu_items:
        qty = item["qty_var"].get()
        line_total = qty * item["price"]
        subtotal += line_total
        item["total_var"].set(line_total)
        item["total_str_var"].set(format_item_price(line_total))
        if "menu_total_label" in item:
            item["menu_total_label"].config(
                fg="green" if line_total > 0 else "black"
            )

    selection_total_var.set(subtotal)

    discount_amount = subtotal * (applied_discount_percent / 100.0)
    after_discount = max(0.0, subtotal - discount_amount)

    if applied_discount_percent > 0:
        discount_display_var.set(
            f"{applied_discount_percent:.0f}% (-{format_tk(discount_amount)[3:]})"
        )
    else:
        discount_display_var.set("Tk 0.00")

    vat_amount = after_discount * 0.05 if after_discount > 0 else 0.0
    vat_var.set(format_tk(vat_amount))

    total = after_discount + vat_amount
    total_bill_var.set(format_tk(total))
    food_cost_var.set(format_tk(subtotal))

    if payment_method_var.get() != "Cash":
        paid_amount_var.set(f"{total:.2f}")
        change_due_var.set("")


def on_qty_change():
    calculate_totals()


def make_qty_controls(parent, item):
    frame = tk.Frame(parent, bg=PANEL_BG)
    minus_btn = tk.Button(
        frame, text="-", width=2, font=BUTTON_FONT,
        command=lambda: change_qty(item, -1)
    )
    qty_lbl = tk.Label(
        frame, textvariable=item["qty_var"], width=2,
        font=TEXT_FONT, bg="white", relief="solid", bd=1
    )
    plus_btn = tk.Button(
        frame, text="+", width=2, font=BUTTON_FONT,
        command=lambda: change_qty(item, +1)
    )

    minus_btn.grid(row=0, column=0)
    qty_lbl.grid(row=0, column=1, padx=1)
    plus_btn.grid(row=0, column=2)

    return frame


def change_qty(item, delta):
    v = item["qty_var"].get() + delta
    if v < 0:
        v = 0
    item["qty_var"].set(v)
    on_qty_change()


# ---------- Login UI ----------

def build_login_ui():
    login_frame.configure(bg=BG_COLOR)
    for w in login_frame.winfo_children():
        w.destroy()

    title = tk.Label(
        login_frame,
        text="Kacchi Bhai Style Restaurant Billing",
        bg=HEADER_BG,
        fg=HEADER_FG,
        font=TITLE_FONT,
        padx=20,
        pady=10,
    )
    title.pack(fill="x")

    inner = tk.Frame(login_frame, bg=BG_COLOR, pady=40)
    inner.pack(expand=True)

    tk.Label(inner, text="Login", font=("Segoe UI", 16, "bold"),
             bg=BG_COLOR).grid(row=0, column=0, columnspan=2, pady=(0, 20))

    role_var = tk.StringVar(value="Employee")

    def on_role_change(*_):
        role = role_var.get()
        if role == "Employee":
            id_entry.configure(state="normal")
            id_entry.focus_set()
            pwd_label.configure(text="Password:")
        else:
            id_entry.configure(state="disabled")
            pwd_label.configure(text="Admin Password:")
            pwd_entry.focus_set()

    tk.Label(inner, text="Role:", font=TEXT_FONT, bg=BG_COLOR)\
        .grid(row=1, column=0, sticky="e", padx=5, pady=5)

    role_frame = tk.Frame(inner, bg=BG_COLOR)
    role_frame.grid(row=1, column=1, sticky="w", pady=5)

    tk.Radiobutton(
        role_frame, text="Employee", variable=role_var,
        value="Employee", bg=BG_COLOR, font=TEXT_FONT,
        command=on_role_change
    ).pack(side="left", padx=5)
    tk.Radiobutton(
        role_frame, text="Admin", variable=role_var,
        value="Admin", bg=BG_COLOR, font=TEXT_FONT,
        command=on_role_change
    ).pack(side="left", padx=5)

    tk.Label(inner, text="Employee ID:", font=TEXT_FONT, bg=BG_COLOR)\
        .grid(row=2, column=0, sticky="e", padx=5, pady=5)

    id_var = tk.StringVar()
    id_entry = tk.Entry(inner, textvariable=id_var, font=TEXT_FONT, width=18)
    id_entry.grid(row=2, column=1, sticky="w", padx=5, pady=5)

    global pwd_label
    pwd_label = tk.Label(inner, text="Password:", font=TEXT_FONT, bg=BG_COLOR)
    pwd_label.grid(row=3, column=0, sticky="e", padx=5, pady=5)

    pwd_var = tk.StringVar()
    pwd_entry = tk.Entry(inner, textvariable=pwd_var, show="*",
                         font=TEXT_FONT, width=18)
    pwd_entry.grid(row=3, column=1, sticky="w", padx=5, pady=5)

    msg_var = tk.StringVar()
    tk.Label(inner, textvariable=msg_var, fg="red",
             bg=BG_COLOR, font=TEXT_FONT)\
        .grid(row=4, column=0, columnspan=2, pady=(5, 10))

    def do_login(event=None):
        role = role_var.get()
        uid = id_var.get().strip()
        pw = pwd_var.get().strip()

        if role == "Employee":
            if not uid or not pw:
                msg_var.set("Please enter Employee ID and Password.")
                return
            emp = next((e for e in employees if e["id"] == uid), None)
            if not emp or emp["password"] != pw:
                msg_var.set("Invalid employee credentials.")
                return
            start_main_session(f'{emp["name"]} (Employee)', "Employee")
        else:
            if pw not in ADMIN_PASSWORDS:
                msg_var.set("Wrong admin password.")
                return
            name = ADMIN_PASSWORDS[pw]
            start_main_session(f"{name} (Admin)", "Admin")

    tk.Button(
        inner, text="LOGIN", font=BUTTON_FONT, bg=BLUE_BTN, fg="white",
        width=15, command=do_login
    ).grid(row=5, column=0, columnspan=2, pady=(15, 5))

    tk.Button(
        inner, text="EXIT", font=BUTTON_FONT, bg="gray20", fg="white",
        width=15, command=root.destroy
    ).grid(row=6, column=0, columnspan=2, pady=(5, 0))

    pwd_entry.bind("<Return>", do_login)
    id_entry.bind("<Return>", do_login)

    on_role_change()


# ---------- Main UI ----------

def build_main_ui():
    global content_frame, menu_page, summary_page

    for w in main_frame.winfo_children():
        w.destroy()

    title_bar = tk.Frame(main_frame, bg=HEADER_BG)
    title_bar.pack(fill="x")

    tk.Label(
        title_bar,
        text="Kacchi Bhai Style Restaurant Billing",
        bg=HEADER_BG,
        fg=HEADER_FG,
        font=TITLE_FONT,
        padx=20,
        pady=6,
    ).pack(side="left")

    tk.Label(
        title_bar,
        textvariable=user_label_var,
        bg=HEADER_BG,
        fg=HEADER_FG,
        font=("Segoe UI", 10, "bold"),
        padx=15,
    ).pack(side="right")

    content_frame = tk.Frame(main_frame, bg=BG_COLOR)
    content_frame.pack(fill="both", expand=True)

    global menu_page, summary_page
    menu_page = tk.Frame(content_frame, bg=BG_COLOR)
    summary_page = tk.Frame(content_frame, bg=BG_COLOR)

    for f in (menu_page, summary_page):
        f.grid(row=0, column=0, sticky="nsew")
    content_frame.grid_rowconfigure(0, weight=1)
    content_frame.grid_columnconfigure(0, weight=1)

    build_menu_page()
    build_summary_page()
    show_menu_page()


def build_menu_page():
    global menu_items
    for w in menu_page.winfo_children():
        w.destroy()

    outer = tk.Frame(menu_page, bg=BG_COLOR, padx=8, pady=8)
    outer.pack(fill="both", expand=True)

    outer.grid_columnconfigure(0, weight=1, uniform="col")
    outer.grid_columnconfigure(1, weight=1, uniform="col")
    outer.grid_rowconfigure(0, weight=1)
    outer.grid_rowconfigure(1, weight=1)

    menu_items.clear()

    def build_category(row, col, cat_name):
        cat_frame = tk.Frame(
            outer, bg=PANEL_BG, bd=1, relief="solid", padx=8, pady=6
        )
        cat_frame.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)

        header = tk.Label(
            cat_frame, text=cat_name, bg=HEADER_BG, fg=HEADER_FG,
            font=SUBTITLE_FONT, padx=8, pady=3
        )
        header.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 4))

        tk.Label(cat_frame, text="Item", bg=PANEL_BG,
                 font=COL_HEADER_FONT, anchor="w")\
            .grid(row=1, column=0, sticky="w", padx=(0, 8))
        tk.Label(cat_frame, text="Price", bg=PANEL_BG,
                 font=COL_HEADER_FONT, anchor="e")\
            .grid(row=1, column=1, sticky="e")
        tk.Label(cat_frame, text="Qty", bg=PANEL_BG,
                 font=COL_HEADER_FONT, anchor="center")\
            .grid(row=1, column=2)
        tk.Label(cat_frame, text="Item Total", bg=PANEL_BG,
                 font=COL_HEADER_FONT, anchor="e")\
            .grid(row=1, column=3, sticky="e", padx=(8, 0))

        items = menu_data.get(cat_name, [])
        start_row = 2
        for idx, (name, price) in enumerate(items):
            r = start_row + idx
            item = {
                "category": cat_name,
                "name": name,
                "price": float(price),
                "qty_var": tk.IntVar(value=0),
                "total_var": tk.DoubleVar(value=0.0),
                "total_str_var": tk.StringVar(value="0 Tk"),
            }
            menu_items.append(item)

            tk.Label(cat_frame, text=name, bg=PANEL_BG,
                     font=TEXT_FONT, anchor="w")\
                .grid(row=r, column=0, sticky="w", padx=(0, 8), pady=1)

            tk.Label(cat_frame, text=format_item_price(price), bg=PANEL_BG,
                     font=TEXT_FONT, anchor="e")\
                .grid(row=r, column=1, sticky="e", pady=1)

            qty_frame = make_qty_controls(cat_frame, item)
            qty_frame.grid(row=r, column=2, pady=1)

            total_lbl = tk.Label(
                cat_frame,
                textvariable=item["total_str_var"],
                bg=PANEL_BG,
                fg="black",
                font=TEXT_FONT,
                anchor="e",
            )
            total_lbl.grid(row=r, column=3, sticky="e",
                           padx=(8, 0), pady=1)
            item["menu_total_label"] = total_lbl

        for c in range(4):
            cat_frame.grid_columnconfigure(c, weight=(3 if c == 0 else 1))

    build_category(0, 0, "Kacchi Combo")
    build_category(0, 1, "Drinks & Dessert")
    build_category(1, 0, "Add-ons")
    build_category(1, 1, "Sharing Platter")

    # bottom bar
    bottom = tk.Frame(outer, bg=BG_COLOR)
    bottom.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))
    for c in range(9):
        bottom.grid_columnconfigure(c, weight=0)
    bottom.grid_columnconfigure(0, weight=1)

    tk.Label(
        bottom,
        text="Current Selection Total:",
        bg=BG_COLOR,
        font=("Segoe UI", 12, "bold"),
    ).grid(row=0, column=0, sticky="w")

    def upd_sel_label(*_):
        lbl_sel.configure(text=format_tk(selection_total_var.get()))

    lbl_sel = tk.Label(
        bottom,
        text=format_tk(0.0),
        bg=BG_COLOR,
        font=("Segoe UI", 12, "bold"),
        fg="green",
    )
    lbl_sel.grid(row=0, column=1, sticky="w", padx=(5, 20))

    selection_total_var.trace_add("write", lambda *a: upd_sel_label())

    tk.Button(
        bottom, text="EXIT", font=BUTTON_FONT, bg="gray20", fg="white",
        width=10, command=on_logout_request
    ).grid(row=0, column=2, padx=4)

    tk.Button(
        bottom, text="RESET", font=BUTTON_FONT, bg=RED_BTN, fg="white",
        width=10, command=reset_transaction
    ).grid(row=0, column=3, padx=4)

    tk.Button(
        bottom, text="CREATE VOUCHER", font=BUTTON_FONT,
        bg="#0099a8", fg="white", width=16,
        command=open_voucher_admin
    ).grid(row=0, column=4, padx=4)

    tk.Button(
        bottom, text="EMPLOYEES", font=BUTTON_FONT,
        bg="#6f42c1", fg="white", width=14,
        command=open_employee_admin
    ).grid(row=0, column=5, padx=4)

    tk.Button(
        bottom, text="HISTORY", font=BUTTON_FONT,
        bg="#555555", fg="white", width=10,
        command=open_history_window
    ).grid(row=0, column=6, padx=4)

    tk.Button(
        bottom, text="ITEMS", font=BUTTON_FONT,
        bg="#797979", fg="white", width=10,
        command=open_items_window
    ).grid(row=0, column=7, padx=4)

    tk.Button(
        bottom, text="NEXT →", font=BUTTON_FONT, bg=BLUE_BTN, fg="white",
        width=12, command=go_to_summary
    ).grid(row=0, column=8, padx=(10, 0))


def build_summary_page():
    global paid_amount_entry

    for w in summary_page.winfo_children():
        w.destroy()

    outer = tk.Frame(summary_page, bg=BG_COLOR, padx=10, pady=10)
    outer.pack(fill="both", expand=True)

    left = tk.Frame(outer, bg=PANEL_BG, bd=1, relief="solid")
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 5))

    outer.grid_rowconfigure(0, weight=1)
    outer.grid_columnconfigure(0, weight=3)
    outer.grid_columnconfigure(1, weight=2)

    tk.Label(
        left, text="Order Summary", bg=PANEL_BG,
        font=SUBTITLE_FONT, anchor="w", padx=10, pady=6
    ).grid(row=0, column=0, columnspan=5, sticky="ew")

    rows_frame = tk.Frame(left, bg=PANEL_BG)
    rows_frame.grid(row=1, column=0, columnspan=5,
                    sticky="nsew", padx=5, pady=(0, 5))
    left.grid_rowconfigure(1, weight=1)

    voucher_frame = tk.Frame(left, bg=PANEL_BG, pady=10)
    voucher_frame.grid(row=2, column=0, columnspan=5,
                       sticky="w", padx=10)

    tk.Label(voucher_frame, text="Voucher Code:",
             bg=PANEL_BG, font=TEXT_FONT)\
        .grid(row=0, column=0, padx=(0, 5))

    voucher_entry = tk.Entry(
        voucher_frame, textvariable=voucher_entry_var,
        font=TEXT_FONT, width=15, bg="white"
    )
    voucher_entry.grid(row=0, column=1, padx=(0, 5))

    apply_btn = tk.Button(
        voucher_frame, text="APPLY", font=BUTTON_FONT,
        bg=BLUE_BTN, fg="white", width=8,
        command=apply_voucher
    )
    apply_btn.grid(row=0, column=2)

    msg_lbl = tk.Label(
        voucher_frame, textvariable=voucher_message_var,
        bg=PANEL_BG, font=TEXT_FONT, fg="red"
    )
    msg_lbl.grid(row=1, column=0, columnspan=3, sticky="w", pady=(5, 0))

    voucher_entry.bind("<Return>", lambda e: apply_voucher())

    right = tk.Frame(outer, bg=BG_COLOR)
    right.grid(row=0, column=1, sticky="nsew")

    bill_panel = tk.Frame(right, bg=PANEL_BG,
                          bd=1, relief="solid", padx=10, pady=10)
    bill_panel.pack(fill="x", pady=(0, 10))

    tk.Label(bill_panel, text="Bill No", bg=PANEL_BG,
             font=TEXT_FONT)\
        .grid(row=0, column=0, sticky="e", padx=5, pady=3)
    tk.Label(bill_panel, textvariable=bill_no_var, bg="#0f5132", fg="white",
             font=("Consolas", 12, "bold"), width=10, relief="sunken")\
        .grid(row=0, column=1, sticky="w", padx=5, pady=3)

    tk.Label(bill_panel, text="Date & Time", bg=PANEL_BG,
             font=TEXT_FONT)\
        .grid(row=1, column=0, sticky="e", padx=5, pady=3)
    tk.Label(bill_panel, textvariable=datetime_var, bg="#e5efe0",
             font=TEXT_FONT, width=20, relief="sunken", anchor="w")\
        .grid(row=1, column=1, sticky="w", padx=5, pady=3)

    tk.Label(bill_panel, text="Food Cost", bg=PANEL_BG,
             font=TEXT_FONT)\
        .grid(row=2, column=0, sticky="e", padx=5, pady=3)
    tk.Label(bill_panel, textvariable=food_cost_var, bg="#e5efe0",
             font=TEXT_FONT, width=15, relief="sunken", anchor="e")\
        .grid(row=2, column=1, sticky="w", padx=5, pady=3)

    tk.Label(bill_panel, text="Discount", bg=PANEL_BG,
             font=TEXT_FONT)\
        .grid(row=3, column=0, sticky="e", padx=5, pady=3)
    tk.Label(bill_panel, textvariable=discount_display_var, bg="#e5efe0",
             font=TEXT_FONT, width=15, relief="sunken", anchor="e")\
        .grid(row=3, column=1, sticky="w", padx=5, pady=3)

    tk.Label(bill_panel, text="VAT (5%)", bg=PANEL_BG,
             font=TEXT_FONT)\
        .grid(row=4, column=0, sticky="e", padx=5, pady=3)
    tk.Label(bill_panel, textvariable=vat_var, bg="#e5efe0",
             font=TEXT_FONT, width=15, relief="sunken", anchor="e")\
        .grid(row=4, column=1, sticky="w", padx=5, pady=3)

    tk.Label(bill_panel, text="Total Bill", bg=PANEL_BG,
             font=TEXT_FONT)\
        .grid(row=5, column=0, sticky="e", padx=5, pady=8)
    tk.Label(bill_panel, textvariable=total_bill_var, bg="#0f5132",
             fg="white", font=("Segoe UI", 13, "bold"),
             width=15, relief="sunken", anchor="e")\
        .grid(row=5, column=1, sticky="w", padx=5, pady=8)

    pay_panel = tk.Frame(right, bg=PANEL_BG,
                         bd=1, relief="solid", padx=10, pady=10)
    pay_panel.pack(fill="both", expand=True)

    tk.Label(pay_panel, text="Payment Details", bg=PANEL_BG,
             font=SUBTITLE_FONT)\
        .grid(row=0, column=0, columnspan=2, pady=(0, 10))

    tk.Label(pay_panel, text="Method:", bg=PANEL_BG,
             font=TEXT_FONT)\
        .grid(row=1, column=0, sticky="e", padx=5, pady=3)

    method_frame = tk.Frame(pay_panel, bg=PANEL_BG)
    method_frame.grid(row=1, column=1, sticky="w", pady=3)

    methods = ["Cash", "bKash", "Nagad", "Rocket", "Card"]
    for m in methods:
        tk.Radiobutton(
            method_frame, text=m, variable=payment_method_var, value=m,
            bg=PANEL_BG, font=TEXT_FONT, command=on_method_change
        ).pack(side="left", padx=3)

    tk.Label(pay_panel, text="Paid Amount (Tk):",
             bg=PANEL_BG, font=TEXT_FONT)\
        .grid(row=2, column=0, sticky="e", padx=5, pady=3)
    global paid_amount_entry
    paid_amount_entry = tk.Entry(
        pay_panel, textvariable=paid_amount_var, font=TEXT_FONT, width=18
    )
    paid_amount_entry.grid(row=2, column=1, sticky="w", padx=5, pady=3)
    paid_amount_entry.bind("<Return>", lambda e: calculate_change())

    tk.Label(pay_panel, text="Change / Due:", bg=PANEL_BG,
             font=TEXT_FONT)\
        .grid(row=3, column=0, sticky="e", padx=5, pady=3)
    tk.Entry(
        pay_panel, textvariable=change_due_var, font=TEXT_FONT,
        width=18, state="readonly"
    ).grid(row=3, column=1, sticky="w", padx=5, pady=3)

    btn_calc = tk.Button(
        pay_panel, text="CALCULATE CHANGE", font=BUTTON_FONT,
        bg=BLUE_BTN, fg="white", width=26, command=calculate_change
    )
    btn_calc.grid(row=4, column=0, columnspan=2, pady=(10, 5))

    btn_complete = tk.Button(
        pay_panel, text="PAYMENT COMPLETE", font=BUTTON_FONT,
        bg="#198754", fg="white", width=26, command=payment_complete
    )
    btn_complete.grid(row=5, column=0, columnspan=2, pady=5)

    btn_back = tk.Button(
        pay_panel, text="← BACK", font=BUTTON_FONT,
        bg=BROWN_BTN, fg="white", width=26, command=show_menu_page
    )
    btn_back.grid(row=6, column=0, columnspan=2, pady=(10, 0))

    summary_page.summary_rows_frame = rows_frame


def rebuild_order_summary():
    frame = summary_page.summary_rows_frame
    for w in frame.winfo_children():
        w.destroy()

    header_row = 0
    tk.Label(frame, text="Item", bg=PANEL_BG,
             font=TEXT_FONT, anchor="w")\
        .grid(row=header_row, column=0, sticky="w",
              padx=(10, 10), pady=(0, 2))
    tk.Label(frame, text="Unit Price", bg=PANEL_BG,
             font=TEXT_FONT, anchor="e")\
        .grid(row=header_row, column=1, sticky="e", pady=(0, 2))
    tk.Label(frame, text="Qty", bg=PANEL_BG,
             font=TEXT_FONT)\
        .grid(row=header_row, column=2, pady=(0, 2))
    tk.Label(frame, text="Line Total", bg=PANEL_BG,
             font=TEXT_FONT, anchor="e")\
        .grid(row=header_row, column=3, sticky="e", pady=(0, 2))
    tk.Label(frame, text="", bg=PANEL_BG,
             font=TEXT_FONT)\
        .grid(row=header_row, column=4)

    row = 1
    for item in menu_items:
        qty = item["qty_var"].get()
        if qty <= 0:
            continue

        tk.Label(frame, text=item["name"], bg=PANEL_BG,
                 font=TEXT_FONT, anchor="w")\
            .grid(row=row, column=0, sticky="w",
                  padx=(10, 10), pady=2)

        price_display = f"{int(item['price'])} Tk" if item["price"].is_integer() else f"{item['price']:.2f} Tk"
        tk.Label(frame, text=price_display, bg=PANEL_BG,
                 font=TEXT_FONT, anchor="e")\
            .grid(row=row, column=1, sticky="e", pady=2)

        qty_frame = make_qty_controls(frame, item)
        qty_frame.grid(row=row, column=2, pady=2)

        total_lbl = tk.Label(
            frame,
            text=format_tk(item["qty_var"].get() * item["price"]),
            bg=PANEL_BG, font=TEXT_FONT, anchor="e"
        )
        total_lbl.grid(row=row, column=3, sticky="e",
                       padx=(10, 0), pady=2)

        item["qty_var"].trace_add(
            "write",
            lambda *args, v=item["qty_var"], p=item["price"], l=total_lbl:
            l.configure(text=format_tk(v.get() * p))
        )

        rem_btn = tk.Button(
            frame, text="Remove", font=("Segoe UI", 9),
            bg="#f8d7da", fg="black", width=8,
            command=lambda it=item: remove_item(it)
        )
        rem_btn.grid(row=row, column=4, padx=5, pady=2)

        row += 1

    for c in range(5):
        frame.grid_columnconfigure(c, weight=(3 if c == 0 else 1))

    if row == 1:
        tk.Label(
            frame, text="No items selected.", bg=PANEL_BG,
            font=TEXT_FONT, fg="gray40"
        ).grid(row=1, column=0, columnspan=5,
               pady=10, padx=10, sticky="w")


def remove_item(item):
    item["qty_var"].set(0)
    on_qty_change()
    rebuild_order_summary()


# ---------- Payment / voucher ----------

def on_method_change():
    method = payment_method_var.get()
    total_text = total_bill_var.get().replace("Tk", "").strip() or "0"
    try:
        total = float(total_text.replace(",", ""))
    except ValueError:
        total = 0.0

    if method == "Cash":
        paid_amount_entry.configure(state="normal")
        paid_amount_var.set("")
        change_due_var.set("")
        paid_amount_entry.focus_set()
    else:
        paid_amount_entry.configure(state="readonly")
        paid_amount_var.set(f"{total:.2f}")
        change_due_var.set("")


def calculate_change():
    method = payment_method_var.get()
    total_text = total_bill_var.get().replace("Tk", "").strip() or "0"
    try:
        total = float(total_text.replace(",", ""))
    except ValueError:
        total = 0.0

    if method != "Cash":
        change_due_var.set("")
        return

    try:
        paid = float(paid_amount_var.get().strip() or "0")
    except ValueError:
        messagebox.showerror("Invalid amount", "Please enter a valid paid amount.")
        return

    diff = paid - total
    if diff >= 0:
        change_due_var.set(f"Back Tk {diff:,.2f}")
    else:
        change_due_var.set(f"Due Tk {-diff:,.2f}")


def apply_voucher():
    global applied_voucher_code, applied_discount_percent

    subtotal = selection_total_var.get()
    if subtotal <= 0:
        voucher_message_var.set("No items to discount.")
        return

    code = voucher_entry_var.get().strip().upper()
    if not code:
        voucher_message_var.set("Please enter a voucher code.")
        return

    v = vouchers.get(code)
    if not v or v.get("deleted", False):
        voucher_message_var.set("Invalid voucher code.")
        return

    max_uses = v.get("max_uses", 0)
    used = v.get("used", 0)

    if max_uses > 0 and used >= max_uses:
        voucher_message_var.set("Voucher limit reached.")
        return

    applied_voucher_code = code
    applied_discount_percent = v.get("discount", 0.0)
    voucher_message_var.set("Voucher applied successfully.")

    calculate_totals()


def payment_complete():
    global orders, vouchers, applied_voucher_code, applied_discount_percent

    has_item = any(it["qty_var"].get() > 0 for it in menu_items)
    if not has_item:
        messagebox.showwarning("No items", "Please select at least one item.")
        return

    method = payment_method_var.get()
    total_str = total_bill_var.get().replace("Tk", "").strip() or "0"
    try:
        total = float(total_str.replace(",", ""))
    except ValueError:
        total = 0.0

    if method == "Cash":
        text = paid_amount_var.get().strip()
        try:
            paid = float(text or "0")
        except ValueError:
            messagebox.showerror("Invalid amount", "Please enter a valid paid amount.")
            return

        if total > 0 and paid <= 0:
            messagebox.showerror("Invalid amount", "Please enter a valid paid amount.")
            return
    else:
        paid = total

    calculate_change()

    items_list = []
    for it in menu_items:
        q = it["qty_var"].get()
        if q <= 0:
            continue
        items_list.append({
            "category": it["category"],
            "name": it["name"],
            "price": it["price"],
            "qty": q,
            "line_total": q * it["price"],
        })

    order = {
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "bill_no": bill_no_var.get(),
        "employee": current_user_name,
        "method": method,
        "total_bill": total,
        "paid": paid,
        "change_or_due": change_due_var.get(),
        "voucher_code": applied_voucher_code or "None",
        "discount_percent": applied_discount_percent,
        "items": items_list,
    }

    orders.append(order)
    save_orders(orders)

    if applied_voucher_code:
        v = vouchers.get(applied_voucher_code)
        if v:
            v["used"] = v.get("used", 0) + 1
            save_vouchers(vouchers)

    messagebox.showinfo("Payment", "Payment successful.")

    reset_transaction()
    show_menu_page()


# ---------- Voucher admin ----------

def generate_voucher_code():
    return "".join(random.choice(string.ascii_uppercase + string.digits)
                   for _ in range(6))


def open_voucher_admin():
    if not ask_admin_password("Admin password for voucher management:"):
        return

    win = tk.Toplevel(root)
    win.title("Voucher Administration")
    win.configure(bg=BG_COLOR)

    tk.Label(
        win, text="Create Voucher", bg=BG_COLOR,
        font=SUBTITLE_FONT
    ).grid(row=0, column=0, columnspan=3, pady=(10, 5), padx=10, sticky="w")

    tk.Label(win, text="Code:", bg=BG_COLOR, font=TEXT_FONT)\
        .grid(row=1, column=0, sticky="e", padx=5, pady=3)
    code_var = tk.StringVar(value=generate_voucher_code())
    code_entry = tk.Entry(win, textvariable=code_var, font=TEXT_FONT, width=10)
    code_entry.grid(row=1, column=1, sticky="w", padx=5, pady=3)

    def regen():
        code_var.set(generate_voucher_code())

    tk.Button(
        win, text="Regenerate", font=("Segoe UI", 9),
        command=regen
    ).grid(row=1, column=2, sticky="w", padx=5, pady=3)

    tk.Label(win, text="Discount (%):", bg=BG_COLOR, font=TEXT_FONT)\
        .grid(row=2, column=0, sticky="e", padx=5, pady=3)
    disc_var = tk.StringVar()
    tk.Entry(win, textvariable=disc_var, font=TEXT_FONT, width=10)\
        .grid(row=2, column=1, sticky="w", padx=5, pady=3)

    tk.Label(win, text="Max uses (0 = unlimited):", bg=BG_COLOR,
             font=TEXT_FONT)\
        .grid(row=3, column=0, sticky="e", padx=5, pady=3)
    max_var = tk.StringVar(value="0")
    tk.Entry(win, textvariable=max_var, font=TEXT_FONT, width=10)\
        .grid(row=3, column=1, sticky="w", padx=5, pady=3)

    def create_voucher():
        code = code_var.get().strip().upper()
        if not code:
            messagebox.showerror("Error", "Please enter a voucher code.")
            return
        try:
            disc = float(disc_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid discount percent.")
            return
        try:
            max_uses = int(max_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid max uses number.")
            return
        vouchers[code] = {
            "code": code,
            "discount": disc,
            "max_uses": max_uses,
            "used": 0,
            "deleted": False,
        }
        save_vouchers(vouchers)
        refresh_tree()
        messagebox.showinfo("Voucher", "Voucher created.")
        regen()
        disc_var.set("")
        max_var.set("0")

    tk.Button(
        win, text="Create Voucher", font=BUTTON_FONT,
        bg=BLUE_BTN, fg="white", width=15,
        command=create_voucher
    ).grid(row=4, column=0, columnspan=3, pady=(10, 10))

    tk.Label(
        win, text="Active Vouchers", bg=BG_COLOR, font=SUBTITLE_FONT
    ).grid(row=5, column=0, columnspan=3, pady=(0, 5), padx=10, sticky="w")

    cols = ("code", "percent", "used", "max")
    tree = ttk.Treeview(win, columns=cols, show="headings", height=8)
    for c, txt, w in [
        ("code", "Code", 80),
        ("percent", "%", 60),
        ("used", "Used", 60),
        ("max", "Max", 60),
    ]:
        tree.heading(c, text=txt)
        tree.column(c, width=w, anchor="center")
    tree.grid(row=6, column=0, columnspan=3, padx=10, pady=(0, 5), sticky="nsew")

    win.grid_rowconfigure(6, weight=1)
    win.grid_columnconfigure(0, weight=1)

    def refresh_tree():
        tree.delete(*tree.get_children())
        for code, v in vouchers.items():
            if v.get("deleted"):
                continue
            tree.insert("", "end", values=(
                code,
                f'{v.get("discount", 0):.1f}',
                v.get("used", 0),
                v.get("max_uses", 0),
            ))

    def delete_selected():
        sel = tree.selection()
        if not sel:
            return
        code = tree.item(sel[0], "values")[0]
        if messagebox.askyesno("Delete", f"Delete voucher {code}?"):
            if code in vouchers:
                vouchers[code]["deleted"] = True
                save_vouchers(vouchers)
                refresh_tree()

    def copy_code():
        sel = tree.selection()
        if not sel:
            return
        code = tree.item(sel[0], "values")[0]
        root.clipboard_clear()
        root.clipboard_append(code)
        root.update()
        messagebox.showinfo("Copy", f"Copied voucher code: {code}")

    btn_frame = tk.Frame(win, bg=BG_COLOR)
    btn_frame.grid(row=7, column=0, columnspan=3, pady=(0, 10))

    tk.Button(
        btn_frame, text="Delete selected", font=("Segoe UI", 9),
        bg=RED_BTN, fg="white", command=delete_selected
    ).pack(side="left", padx=5)
    tk.Button(
        btn_frame, text="Copy", font=("Segoe UI", 9),
        bg="#e2f0fb", command=copy_code
    ).pack(side="left", padx=5)

    refresh_tree()


# ---------- Employee admin ----------

def open_employee_admin():
    if not ask_admin_password("Admin password for employee management:"):
        return

    win = tk.Toplevel(root)
    win.title("Employee Administration")
    win.configure(bg=BG_COLOR)

    tk.Label(win, text="Employee Accounts", bg=BG_COLOR,
             font=SUBTITLE_FONT).pack(pady=(10, 5))

    cols = ("id", "name", "password")
    tree = ttk.Treeview(win, columns=cols, show="headings", height=10)
    for c, txt, w in [
        ("id", "Employee ID", 100),
        ("name", "Name", 160),
        ("password", "Password", 120),
    ]:
        tree.heading(c, text=txt)
        tree.column(c, width=w, anchor="center")
    tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def refresh():
        tree.delete(*tree.get_children())
        for emp in employees:
            tree.insert("", "end",
                        values=(emp["id"], emp["name"], emp["password"]))

    form = tk.Frame(win, bg=BG_COLOR)
    form.pack(pady=(0, 10))

    tk.Label(form, text="ID:", bg=BG_COLOR, font=TEXT_FONT)\
        .grid(row=0, column=0, padx=5, pady=2)
    id_var = tk.StringVar()
    tk.Entry(form, textvariable=id_var, font=TEXT_FONT, width=10)\
        .grid(row=0, column=1, padx=5, pady=2)

    tk.Label(form, text="Name:", bg=BG_COLOR, font=TEXT_FONT)\
        .grid(row=0, column=2, padx=5, pady=2)
    name_var = tk.StringVar()
    tk.Entry(form, textvariable=name_var, font=TEXT_FONT, width=16)\
        .grid(row=0, column=3, padx=5, pady=2)

    tk.Label(form, text="Password:", bg=BG_COLOR, font=TEXT_FONT)\
        .grid(row=0, column=4, padx=5, pady=2)
    pwd_var = tk.StringVar()
    tk.Entry(form, textvariable=pwd_var, font=TEXT_FONT, width=12)\
        .grid(row=0, column=5, padx=5, pady=2)

    def add_employee():
        eid = id_var.get().strip()
        nm = name_var.get().strip()
        pw = pwd_var.get().strip()
        if not eid or not nm or not pw:
            messagebox.showerror("Error", "Please fill ID, Name and Password.")
            return
        if any(e["id"] == eid for e in employees):
            messagebox.showerror("Error", "Employee ID already exists.")
            return
        employees.append({"id": eid, "name": nm, "password": pw})
        save_employees(employees)
        refresh()
        id_var.set("")
        name_var.set("")
        pwd_var.set("")

    def delete_selected():
        sel = tree.selection()
        if not sel:
            return
        eid = tree.item(sel[0], "values")[0]
        if messagebox.askyesno("Delete", f"Delete employee {eid}?"):
            employees[:] = [e for e in employees if e["id"] != eid]
            save_employees(employees)
            refresh()

    btn_frame = tk.Frame(win, bg=BG_COLOR)
    btn_frame.pack(pady=(0, 10))

    tk.Button(
        btn_frame, text="Add Employee", font=BUTTON_FONT,
        bg=BLUE_BTN, fg="white", command=add_employee
    ).pack(side="left", padx=5)

    tk.Button(
        btn_frame, text="Delete selected", font=BUTTON_FONT,
        bg=RED_BTN, fg="white", command=delete_selected
    ).pack(side="left", padx=5)

    tk.Button(
        btn_frame, text="Close", font=BUTTON_FONT,
        bg=BROWN_BTN, fg="white", command=win.destroy
    ).pack(side="left", padx=5)

    refresh()


# ---------- Items window (menu editor) ----------

def parse_menu_block(text):
    items = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "—" in line:
            name_part, price_part = line.split("—", 1)
        elif "-" in line:
            name_part, price_part = line.split("-", 1)
        else:
            continue
        name = name_part.strip()
        price_str = price_part.lower().replace("tk", "").strip()
        price_str = price_str.replace(",", "")
        try:
            price = float(price_str)
        except ValueError:
            continue
        items.append((name, price))
    return items


def open_items_window():
    if not ask_admin_password("Admin password to open Items window:"):
        return

    win = tk.Toplevel(root)
    win.title("Menu Items")
    win.configure(bg=BG_COLOR)

    nb = ttk.Notebook(win)
    nb.pack(fill="both", expand=True, padx=5, pady=5)

    global menu_data
    text_widgets = {}

    for cat in CATEGORIES:
        frame = tk.Frame(nb, bg=BG_COLOR)
        nb.add(frame, text=cat)
        txt = tk.Text(frame, font=("Consolas", 11), wrap="word")
        txt.pack(fill="both", expand=True, padx=5, pady=(5, 0))

        lines = []
        for name, price in menu_data.get(cat, []):
            lines.append(f"{name} — {format_item_price(price)}")
        txt.insert("1.0", "\n".join(lines))
        text_widgets[cat] = txt

    def save_items():
        global menu_data
        for cat in CATEGORIES:
            raw = text_widgets[cat].get("1.0", "end-1c")
            items = parse_menu_block(raw)
            update_menu_category(cat, items)

        menu_data = load_menu_data()
        build_menu_page()
        messagebox.showinfo("Items", "Menu updated successfully.")

    btn_frame = tk.Frame(win, bg=BG_COLOR)
    btn_frame.pack(pady=5)
    tk.Button(
        btn_frame, text="Save", font=BUTTON_FONT,
        bg=BLUE_BTN, fg="white", width=10, command=save_items
    ).pack(side="left", padx=5)
    tk.Button(
        btn_frame, text="Close", font=BUTTON_FONT,
        bg=BROWN_BTN, fg="white", width=10, command=win.destroy
    ).pack(side="left", padx=5)


# ---------- Order history ----------

def open_history_window():
    win = tk.Toplevel(root)
    win.title("Order History")
    win.configure(bg=BG_COLOR)
    win.geometry("750x420")

    tk.Label(win, text="Order History", bg=BG_COLOR,
             font=SUBTITLE_FONT).pack(pady=(10, 5))

    cols = ("datetime", "bill", "employee", "method", "total", "voucher")
    tree = ttk.Treeview(win, columns=cols, show="headings")
    tree.pack(fill="both", expand=True, padx=10, pady=(0, 5))

    headings = [
        ("datetime", "Date & Time", 150),
        ("bill", "Bill No", 70),
        ("employee", "Employee", 160),
        ("method", "Method", 80),
        ("total", "Total", 80),
        ("voucher", "Voucher", 80),
    ]
    for c, txt, w in headings:
        tree.heading(c, text=txt)
        tree.column(c, width=w, anchor="center")

    count_by_method = {"Cash": 0, "bKash": 0, "Nagad": 0,
                       "Rocket": 0, "Card": 0}

    for idx, o in enumerate(orders):
        tree.insert("", "end", iid=str(idx), values=(
            o.get("datetime", ""),
            o.get("bill_no", ""),
            o.get("employee", ""),
            o.get("method", ""),
            f'{o.get("total_bill", 0):.2f}',
            o.get("voucher_code", ""),
        ))
        m = o.get("method")
        if m in count_by_method:
            count_by_method[m] += 1

    summary = f"Total orders: {len(orders)}"
    for m in ["Cash", "bKash", "Nagad", "Rocket", "Card"]:
        summary += f"   {m}: {count_by_method[m]}"

    tk.Label(win, text=summary, bg=BG_COLOR,
             font=TEXT_FONT).pack(pady=(0, 5))

    def show_order_details(event=None):
        sel = tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        order = orders[idx]

        detail = tk.Toplevel(win)
        detail.title(f"Bill {order.get('bill_no', '')} details")
        detail.configure(bg=BG_COLOR)

        tk.Label(detail, text=f"Bill No: {order.get('bill_no', '')}",
                 bg=BG_COLOR, font=SUBTITLE_FONT)\
            .pack(pady=(10, 5))

        cols2 = ("item", "price", "qty", "line")
        tree2 = ttk.Treeview(detail, columns=cols2, show="headings", height=8)
        tree2.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        for c, txt, w in [
            ("item", "Item", 220),
            ("price", "Unit Price", 90),
            ("qty", "Qty", 50),
            ("line", "Line Total", 100),
        ]:
            tree2.heading(c, text=txt)
            tree2.column(c, width=w, anchor="center")

        for it in order.get("items", []):
            tree2.insert("", "end", values=(
                it.get("name", ""),
                format_item_price(it.get("price", 0)),
                it.get("qty", 0),
                format_item_price(it.get("line_total", 0)),
            ))

        tk.Button(
            detail, text="Close", font=BUTTON_FONT,
            bg=BROWN_BTN, fg="white",
            command=detail.destroy
        ).pack(pady=(0, 10))

    tree.bind("<Double-1>", show_order_details)


# ---------- Navigation ----------

def show_menu_page():
    menu_page.tkraise()


def show_summary_page():
    summary_page.tkraise()


def go_to_summary():
    if not any(it["qty_var"].get() > 0 for it in menu_items):
        messagebox.showwarning("No items", "Please select at least one item.")
        return

    rebuild_order_summary()
    bill_no_var.set(generate_bill_no())
    datetime_var.set(datetime.now().strftime("%d-%m-%Y  %I:%M %p"))
    calculate_totals()
    voucher_message_var.set("")
    show_summary_page()


def on_logout_request():
    reset_transaction()
    main_frame.pack_forget()
    login_frame.pack(fill="both", expand=True)
    build_login_ui()


def start_main_session(user_display_name, role):
    global current_user_name, current_role
    current_user_name = user_display_name
    current_role = role
    user_label_var.set(f"User: {user_display_name}")

    reset_transaction()
    build_main_ui()
    login_frame.pack_forget()
    main_frame.pack(fill="both", expand=True)


# ---------- Start ----------

build_login_ui()
login_frame.pack(fill="both", expand=True)

root.mainloop()

