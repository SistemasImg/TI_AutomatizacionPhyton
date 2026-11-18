import os
import smtplib
import requests
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders
from simple_salesforce import Salesforce
from pandas import json_normalize
import warnings

from configuracion import variable_requerida
warnings.filterwarnings("ignore", category=UserWarning)
pd.set_option("display.max_columns", None)

# ===========================
# 1) Obtener datos desde Salesforce
# ===========================

def cargar_datos():
    consumer_key    = variable_requerida("SF_CLIENT_ID")
    consumer_secret = variable_requerida("SF_CLIENT_SECRET")

    username = variable_requerida("SF_USERNAME")
    password = variable_requerida("SF_PASSWORD")
    login_url       = "https://login.salesforce.com/services/oauth2/token"

    params = {
        "grant_type":    "password",
        "client_id":     consumer_key,
        "client_secret": consumer_secret,
        "username":      username,
        "password":      password,
    }

    response = requests.post(login_url, data=params)
    response.raise_for_status()
    auth = response.json()

    sf = Salesforce(instance_url=auth["instance_url"], session_id=auth["access_token"])

    accounts = sf.query_all(
        """
            SELECT
            Oportunidad__r.Account_Name_Text__c,
            Oportunidad__r.Name,
            Oportunidad__r.StageName,
            Oportunidad__r.Quantityleads__c,
            Lead__r.CaseNumber,
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.Substatus__c,
            Lead__r.Type
            FROM Lead_de_oportunidad__c
            WHERE Oportunidad__r.StageName = 'In progress'
        """
    )

    records = accounts.get("records", [])
    df = json_normalize(records)
    if "attributes" in df.columns:
        df = df.drop(columns=["attributes"])

    df["Opportunity Name"] = df["Oportunidad__r.Name"]

    df = df.rename(columns={
        "Oportunidad__r.Account_Name_Text__c": "Client",
        "Oportunidad__r.Name":                 "Tier",
        "Oportunidad__r.StageName":            "Stage Name",
        "Lead__r.CaseNumber":                  "Case Number",
        "Lead__r.FirstName__c":                "First Name",
        "Lead__r.Last_Name__c":                "Last Name",
        "Lead__r.Phone_Numbercontact__c":      "Phone Number",
        "Lead__r.Substatus__c":                "Substatus",
        "Lead__r.Type":                        "Type",
        "Oportunidad__r.Quantityleads__c":     "Quantity",
    })

    df = df[['Client', 'Tier', 'Opportunity Name', 'Stage Name', 'Case Number',
             'First Name', 'Last Name', 'Phone Number', 'Substatus', 'Type', 'Quantity']]

    df.loc[df['Substatus'].isin(['Signed', 'Transferred', 'Posted']), 'Substatus'] = 'Pending'

    # df = df[
    #     (df["Tier"] != "RS T9 #3 | PLG") &
    #     (df["Client"] != "Openjar") &
    #     (df["Client"] != "AdReach IQ") &
    #     (df["Client"] != "A4D")
    # ]

    df_quantity = df[['Tier', 'Quantity']].drop_duplicates().copy()
    df_quantity["Quantity"] = df_quantity["Quantity"].astype(int)

    df = df[["Client", "Tier", "Opportunity Name", "Type", "Substatus"]]

    resultado = (
        df
        .groupby(["Client", "Tier", "Opportunity Name", "Type", "Substatus"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    resultado.columns.name = None

    for col in ["Accepted", "Reject", "Pending"]:
        if col not in resultado.columns:
            resultado[col] = 0

    resultado = resultado[["Client", "Tier", "Opportunity Name", "Type", "Accepted", "Reject", "Pending"]]
    resultado["Leads Sent"] = resultado[["Accepted", "Reject", "Pending"]].sum(axis=1)

    resultado = resultado.merge(df_quantity[["Tier", "Quantity"]], on="Tier", how="left")

    resultado["Pending to Send"]       = resultado["Quantity"] - resultado["Accepted"] - resultado["Pending"]
    resultado["Accepted + In Progress"] = resultado["Accepted"] + resultado["Pending"]

    resultado['Tier'] = resultado['Tier'].str.extract(r'(T\d+)')

    resultado = resultado[['Type', 'Tier', 'Opportunity Name', 'Client',
                           'Leads Sent', 'Accepted + In Progress', 'Pending to Send']]

    resultado["Status"] = "ACTIVE"
    
    return pd.DataFrame(resultado)


resultado = cargar_datos()


# ===========================
# 5) Función: Guardar + Enviar correo
# ===========================

def send_priorities():
    downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(downloads_path, exist_ok=True)

    excel_filename = "Priorities.xlsx"
    excel_path = os.path.join(downloads_path, excel_filename)

    rows = [tree.item(iid)["values"][:-1] for iid in tree.get_children()]
    df_final = pd.DataFrame(rows, columns=["Priority"] + data_cols)

    df_final.to_excel(excel_path, index=False)

    tabla_resultado = df_final.to_html(index=False)

    SMTP_SERVER = "smtp.office365.com"
    SMTP_PORT   = 587
    FROM_EMAIL  = variable_requerida("SMTP_PRIORITIES_USERNAME")
    EMAIL_PASS  = variable_requerida("SMTP_PASSWORD")

    # TO_EMAILS = ["jocelyn.sairitupac@img360.com", "katherine.hidalgo@img360.com", "christyjen.ruiz@img360.com", "ada.valdivia@img360.com"]
    # CC_EMAILS = ["bruno.flores@img360.com", "manuel.chero@img360.com"]

    TO_EMAILS = ["bruno.flores@img360.com"]
    CC_EMAILS = ["bruno.flores@img360.com"]

    hoy_mmddyyyy_hhmm = datetime.now().strftime("%m/%d/%Y %H:%M")
    subject = f"Priorities {hoy_mmddyyyy_hhmm}"

    body = f"""
            <html>
            <head>
            <style>
                body {{ font-family: Arial, Helvetica, sans-serif; font-size: 14px; color: #333; }}
                table {{ width: auto; border-collapse: collapse; margin-bottom: 20px; font-size: 13px; }}
                th {{ background-color: #f2f2f2; padding: 8px; border: 1px solid #ddd; text-align: left; font-weight: bold; }}
                td {{ padding: 8px; border: 1px solid #ddd; text-align: left; }}
                tr:nth-child(even) {{ background-color: #fafafa; }}
                .section-title {{ font-size: 15px; font-weight: bold; margin-top: 25px; margin-bottom: 5px; }}
            </style>
            </head>
            <body>
            <p>Hi,</p>
            <p>Please find the Priorities for your review.</p>
            {tabla_resultado}
            <p>Thanks!</p>
            </body>
            </html>
            """

    msg = MIMEMultipart()
    msg["From"] = FROM_EMAIL
    msg["To"] = ", ".join(TO_EMAILS)
    msg["Cc"] = ", ".join(CC_EMAILS)
    msg["Date"] = formatdate(localtime=True)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html", "utf-8"))

    with open(excel_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{excel_filename}"')
    msg.attach(part)

    all_recipients = TO_EMAILS + CC_EMAILS
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(FROM_EMAIL, EMAIL_PASS)
        server.sendmail(FROM_EMAIL, all_recipients, msg.as_string())

    mostrar_exito()


# ===========================
# 6) Ventana de previsualización
# ===========================

BG         = "#F1F5F9"
CARD_BG    = "#FFFFFF"
PRIMARY    = "#2ea043"
PRIMARY_HV = "#2c974b"
TEXT_DARK  = "#1E293B"
TEXT_MUTED = "#64748B"
BORDER     = "#CBD5E1"
DIS_BG     = "#F1F5F9"
DIS_FG     = "#94A3B8"


def mostrar_exito():
    win = tk.Toplevel()
    win.title("Éxito")
    win.geometry("420x240")
    win.configure(bg=BG)
    win.resizable(False, False)
    win.grab_set()

    hdr = tk.Frame(win, bg="#1E293B")
    hdr.pack(fill="x")
    tk.Label(hdr, text="  Éxito", font=("Segoe UI", 12, "bold"),
             bg="#1E293B", fg="white", padx=16, pady=11, anchor="w").pack(side="left")
    tk.Frame(win, bg=PRIMARY, height=3).pack(fill="x")

    body_f = tk.Frame(win, bg=BG, padx=24, pady=22)
    body_f.pack(fill="both", expand=True)
    tk.Label(body_f,
             text="¡Prioridades enviadas exitosamente!\n\nEl archivo fue guardado y el correo fue enviado.",
             font=("Segoe UI", 11), bg=BG, fg=TEXT_DARK,
             wraplength=360, justify="left").pack(anchor="w")

    win_btn = tk.Frame(win, bg=BG, padx=16, pady=12)
    win_btn.pack(fill="x", side="bottom")
    tk.Frame(win_btn, bg=BORDER, height=1).pack(fill="x", pady=(0, 10))
    tk.Button(win_btn, text="Aceptar",
              command=lambda: [win.destroy(), root.destroy()],
              bg=PRIMARY, fg="white",
              activebackground=PRIMARY_HV, activeforeground="white",
              font=("Segoe UI", 11, "bold"), relief="flat", bd=0,
              cursor="hand2", pady=9).pack(fill="x")


root = tk.Tk()
root.title("Priorities Preview")
root.state("zoomed")
root.configure(bg=BG)

# --- Header ---
header = tk.Frame(root, bg="#1E293B")
header.pack(fill="x")
tk.Label(header, text="Priorities Preview", font=("Segoe UI", 15, "bold"),
         bg="#1E293B", fg="white", pady=12).pack()
tk.Label(header, text="Gestión de Prioridades de Envío", font=("Segoe UI", 9),
         bg="#1E293B", fg="#94A3B8").pack(pady=(0, 10))

# --- Footer (pack before body) ---
footer = tk.Frame(root, bg=BG)
footer.pack(fill="x", side="bottom")
tk.Frame(footer, bg=BORDER, height=1).pack(fill="x")
tk.Label(footer, text="© 2026 International Media Group. All Rights Reserved.",
         font=("Segoe UI", 7), bg=BG, fg=TEXT_MUTED).pack(pady=5)

# --- Button area (pack before body so queda encima del footer) ---
btn_area = tk.Frame(root, bg=BG, padx=16, pady=14)
btn_area.pack(fill="x", side="bottom")
tk.Frame(btn_area, bg=BORDER, height=1).pack(fill="x", pady=(0, 12))

inner_btns = tk.Frame(btn_area, bg=BG)
inner_btns.pack()

btn_undo = tk.Button(
    inner_btns, text="↩ Undo",
    command=lambda: undo_last(),
    bg=DIS_BG, fg=DIS_FG,
    activebackground="#E2E8F0", activeforeground=TEXT_DARK,
    font=("Segoe UI", 11), relief="flat", bd=0,
    cursor="hand2", padx=20, pady=11, state="disabled",
)
btn_undo.pack(side="left", padx=6)

btn_send = tk.Button(
    inner_btns, text="Send Priorities",
    command=send_priorities,
    bg=PRIMARY, fg="white",
    activebackground=PRIMARY_HV, activeforeground="white",
    font=("Segoe UI", 12, "bold"), relief="flat", bd=0,
    cursor="hand2", padx=20, pady=11,
)
btn_send.pack(side="left", padx=6)

# --- Body ---
body = tk.Frame(root, bg=BG, padx=16, pady=16)
body.pack(fill="both", expand=True)

tk.Label(body, text="Resultado", font=("Segoe UI", 10, "bold"),
         bg=BG, fg=TEXT_DARK, anchor="w").pack(fill="x", pady=(0, 8))

# --- Treeview styling ---
style = ttk.Style()
style.theme_use("clam")
style.configure("Custom.Treeview",
    background=CARD_BG, foreground=TEXT_DARK, fieldbackground=CARD_BG,
    rowheight=32, font=("Segoe UI", 10), borderwidth=0,
)
style.configure("Custom.Treeview.Heading",
    background="#1E293B", foreground="white",
    font=("Segoe UI", 10, "bold"), relief="flat", borderwidth=0, padding=8,
)
style.map("Custom.Treeview",
    background=[("selected", "#DCFCE7")],
    foreground=[("selected", TEXT_DARK)],
)

# --- Card wrapper ---
card_outer = tk.Frame(body, bg=BORDER)
card_outer.pack(fill="both", expand=True)
card_inner = tk.Frame(card_outer, bg=CARD_BG)
card_inner.pack(fill="both", expand=True, padx=1, pady=1)
card_inner.grid_rowconfigure(0, weight=1)
card_inner.grid_columnconfigure(0, weight=1)

data_cols = list(resultado.columns)
priority_col = "Priority"
trash_col = "🗑"
all_cols = [priority_col] + data_cols + [trash_col]

tree = ttk.Treeview(card_inner, columns=all_cols, show="headings", style="Custom.Treeview")

tree.heading(priority_col, text="Priority")
tree.column(priority_col, width=70, anchor="center", stretch=False)

for col in data_cols:
    tree.heading(col, text=col)
    tree.column(col, width=140, anchor="center")

tree.heading(trash_col, text="")
tree.column(trash_col, width=42, anchor="center", stretch=False)

tree.tag_configure("odd",  background="#F8FAFC")
tree.tag_configure("even", background=CARD_BG)

for i, (_, row) in enumerate(resultado.iterrows(), start=1):
    tag = "odd" if i % 2 != 0 else "even"
    tree.insert("", "end", values=[i] + list(row) + ["🗑"], tags=(tag,))

vsb = ttk.Scrollbar(card_inner, orient="vertical",   command=tree.yview)
hsb = ttk.Scrollbar(card_inner, orient="horizontal", command=tree.xview)
tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

tree.grid(row=0, column=0, sticky="nsew")
vsb.grid(row=0, column=1, sticky="ns")
hsb.grid(row=1, column=0, sticky="ew")

# --- Lógica de interacción ---
undo_stack = []


def update_priorities():
    for i, iid in enumerate(tree.get_children(), start=1):
        vals = list(tree.item(iid)["values"])
        vals[0] = i
        tag = "odd" if i % 2 != 0 else "even"
        tree.item(iid, values=vals, tags=(tag,))


def undo_last(_event=None):
    if not undo_stack:
        return
    saved = undo_stack.pop()
    children = tree.get_children()
    insert_at = saved["index"] if saved["index"] <= len(children) else len(children)
    tree.insert("", insert_at, values=saved["values"])
    update_priorities()
    if not undo_stack:
        btn_undo.config(state="disabled", bg=DIS_BG, fg=DIS_FG)


drag_data = {"item": None, "start_y": 0, "dragging": False}


def on_press(event):
    if tree.identify_region(event.x, event.y) == "cell":
        drag_data["item"] = tree.identify_row(event.y)
        drag_data["start_y"] = event.y
        drag_data["dragging"] = False


def on_motion(event):
    if drag_data["item"] and abs(event.y - drag_data["start_y"]) > 5:
        drag_data["dragging"] = True
        target = tree.identify_row(event.y)
        if target and target != drag_data["item"]:
            tree.move(drag_data["item"], "", tree.index(target))


def on_release(event):
    if not drag_data["dragging"]:
        if tree.identify_region(event.x, event.y) == "cell":
            col_index = int(tree.identify_column(event.x).replace("#", "")) - 1
            if col_index == len(data_cols) + 1:
                item = tree.identify_row(event.y)
                if item:
                    idx = tree.index(item)
                    vals = list(tree.item(item)["values"])
                    undo_stack.append({"values": vals, "index": idx})
                    tree.delete(item)
                    update_priorities()
                    btn_undo.config(state="normal", bg=CARD_BG, fg=TEXT_DARK)
    else:
        update_priorities()
    drag_data["item"] = None
    drag_data["dragging"] = False


tree.bind("<ButtonPress-1>", on_press)
tree.bind("<B1-Motion>", on_motion)
tree.bind("<ButtonRelease-1>", on_release)
root.bind("<Control-z>", undo_last)

root.mainloop()
