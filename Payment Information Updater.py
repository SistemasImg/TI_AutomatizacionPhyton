import os
import re
import threading
import requests
import pandas as pd
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from simple_salesforce import Salesforce
from pandas import json_normalize
import warnings

from configuracion import variable_requerida

warnings.filterwarnings("ignore", category=UserWarning)
pd.set_option("display.max_columns", None)


def clean_phone(phone):
    """Deja solo los dígitos de un teléfono (quita paréntesis, guiones, espacios, etc.)."""
    if phone is None or (isinstance(phone, float) and pd.isna(phone)):
        return ""
    return re.sub(r"\D", "", str(phone))

# ── Credenciales ───────────────────────────────────────────────────────────────
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
auth_response = response.json()
access_token  = auth_response["access_token"]
instance_url  = auth_response["instance_url"]
sf = Salesforce(instance_url=instance_url, session_id=access_token)

accounts = sf.query_all("""
    SELECT Id, Lead__c, Lead__r.Phone_Numbercontact__c, Lead__r.Status, Lead__r.Substatus__c,
           Lead__r.Owner.Name, Oportunidad__r.Name,
           Lead__r.Cost__c, Lead__r.Invoice__c, Lead__r.Billable__c, Lead__r.Paid__c,
           Lead__r.Bonus__c, Lead__r.Bonus_Amount__c, Lead__r.Replacement__c,
           Lead__r.Lead_Replaced__c, Lead__r.Amount_Replaced__c
    FROM Lead_de_oportunidad__c
""")

records = accounts.get("records", [])
if records:
    df = json_normalize(records)
    if "attributes" in df.columns:
        df = df.drop(columns=["attributes"])

df = df.rename(columns={
    "Lead__r.Phone_Numbercontact__c": "Phone Number",
    "Lead__r.Status":                 "Status",
    "Lead__r.Substatus__c":           "Substatus",
    "Lead__r.Owner.Name":             "Case Owner",
    "Oportunidad__r.Name":            "Opportunity Name",
    "Lead__r.Cost__c":               "Cost",
    "Lead__r.Invoice__c":            "Invoice",
    "Lead__r.Billable__c":           "Billable",
    "Lead__r.Paid__c":               "Paid",
    "Lead__r.Bonus__c":              "Bonus",
    "Lead__r.Bonus_Amount__c":       "Bonus Amount",
    "Lead__r.Replacement__c":        "Replacement",
    "Lead__r.Lead_Replaced__c":      "Lead Replaced",
    "Lead__r.Amount_Replaced__c":    "Amount Replaced",
})
df = df[['Id', 'Lead__c', 'Phone Number', 'Status', 'Substatus', 'Case Owner', 'Opportunity Name',
         'Cost', 'Invoice', 'Billable', 'Paid', 'Bonus', 'Bonus Amount', 'Replacement',
         'Lead Replaced', 'Amount Replaced']]
df['Phone Number'] = df['Phone Number'].apply(clean_phone)

# ── Design tokens ──────────────────────────────────────────────────────────────
BG         = "#F4F6F8"
CARD       = "#FFFFFF"
HDR        = "#1E293B"
HDR_SUB    = "#94A3B8"
PRIMARY    = "#2563EB"
PRIMARY_LT = "#EFF6FF"
SUCCESS    = "#28A745"
SUCCESS_BG = "#F0FDF4"
SUCCESS_BD = "#86EFAC"
ERROR_C    = "#DC2626"
ERROR_BG   = "#FEF2F2"
ERROR_BD   = "#FCA5A5"
WARN_BG    = "#FFFBEB"
WARN_C     = "#B45309"
TEXT       = "#0F172A"
MUTED      = "#6B7280"
BORDER     = "#E2E8F0"
DISABLED   = "#94A3B8"
DISABLED_BG= "#F1F5F9"

FH2    = ("Segoe UI", 14, "bold")
FH3    = ("Segoe UI", 11, "bold")
FBODY  = ("Segoe UI", 11)
FSMALL = ("Segoe UI", 9)
FBIG   = ("Segoe UI", 22, "bold")

# (label, columna en df, campo API en Case, es_checkbox, es_entero)
INFO_FIELDS = [
    ("Cost",             "Cost",             "Cost__c",            False, True),
    ("Invoice",          "Invoice",          "Invoice__c",         False, False),
    ("Billable",         "Billable",         "Billable__c",        True,  False),
    ("Paid",             "Paid",             "Paid__c",            True,  False),
    ("Bonus",            "Bonus",            "Bonus__c",           True,  False),
    ("Bonus Amount",     "Bonus Amount",     "Bonus_Amount__c",    False, False),
    ("Replacement",      "Replacement",      "Replacement__c",     True,  False),
    ("Lead Replaced",    "Lead Replaced",    "Lead_Replaced__c",   False, False),
    ("Amount Replaced",  "Amount Replaced",  "Amount_Replaced__c", False, False),
]

# columnas con formato de moneda ($)
MONEY_FIELDS = {"Cost", "Bonus Amount", "Amount Replaced"}

# columna → columna checkbox de la que depende (solo se muestra/aplica si esa es "Yes")
FIELD_DEPENDS_ON = {
    "Lead Replaced":   "Replacement",
    "Amount Replaced": "Replacement",
    "Bonus Amount":    "Bonus",
}


def _is_yes(val):
    if isinstance(val, str):
        return val.strip().lower() in ("yes", "true", "1", "si", "sí")
    if pd.isna(val):
        return False
    return bool(val)


def _visible_fields(getter):
    visible = []
    for f in INFO_FIELDS:
        parent = FIELD_DEPENDS_ON.get(f[1])
        if parent and not _is_yes(getter.get(parent)):
            continue
        visible.append(f)
    return visible


def _fmt_value(raw, is_int=False, is_money=False):
    if pd.isna(raw) or raw == "":
        return "—"
    if is_int:
        try:
            num = int(float(raw))
        except (TypeError, ValueError):
            return str(raw)
        return f"${num:,}" if is_money else f"{num:,}"
    if is_money:
        try:
            return f"${float(raw):,.2f}"
        except (TypeError, ValueError):
            return str(raw)
    return str(raw)


def _lookup_phone_by_case_id(case_id):
    if case_id is None or (isinstance(case_id, float) and pd.isna(case_id)):
        return None
    match = df[df['Lead__c'] == case_id]
    if not match.empty:
        return match.iloc[0]['Phone Number']
    return case_id


def _lookup_case_id_by_phone(phone):
    phone = clean_phone(phone)
    if not phone:
        return None
    match = df[df['Phone Number'] == phone]
    if match.empty:
        return None
    ids = match['Lead__c'].dropna().unique().tolist()
    return ids[0] if ids else None


# Solo se pueden actualizar casos cuyo Substatus esté en esta lista.
ALLOWED_SUBSTATUSES = {"Accepted", "Signed", "Transferred", "Posted", "Reject"}


def _substatus_ok(case_ids):
    """True solo si TODOS los Case indicados tienen un Substatus permitido."""
    if not case_ids:
        return False
    vals = df.loc[df['Lead__c'].isin(case_ids), 'Substatus']
    return not vals.empty and vals.isin(ALLOWED_SUBSTATUSES).all()


def _clean_dependent_payload(payload):
    """Anula los campos dependientes cuando el checkbox padre queda en No."""
    if "Replacement__c" in payload and not payload["Replacement__c"]:
        for f in ("Lead_Replaced__c", "Amount_Replaced__c"):
            if f in payload:
                payload[f] = None
    if "Bonus__c" in payload and not payload["Bonus__c"]:
        if "Bonus_Amount__c" in payload:
            payload["Bonus_Amount__c"] = None
    return payload


# ── Helpers ────────────────────────────────────────────────────────────────────
def _darken(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"#{max(0, r - 24):02x}{max(0, g - 24):02x}{max(0, b - 24):02x}"


def add_hover(btn, bg):
    dk = _darken(bg)
    btn.bind("<Enter>", lambda _: btn.config(bg=dk))
    btn.bind("<Leave>", lambda _: btn.config(bg=bg))


def center_win(win):
    win.update_idletasks()
    w = win.winfo_reqwidth()
    h = win.winfo_reqheight()
    x = (win.winfo_screenwidth()  - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"+{x}+{y}")


def make_header(parent, title, subtitle=""):
    """Dark header bar matching the reference design."""
    hdr = tk.Frame(parent, bg=HDR)
    hdr.pack(fill="x")
    tk.Label(hdr, text=title, font=FH2, bg=HDR, fg="white",
             padx=24).pack(anchor="w", pady=(16, 4 if subtitle else 16))
    if subtitle:
        tk.Label(hdr, text=subtitle, font=FSMALL, bg=HDR, fg=HDR_SUB,
                 padx=24).pack(anchor="w", pady=(0, 14))


def flat_btn(parent, text, bg, cmd, padx=14, pady=9, **kw):
    """Styled button with hover darkening."""
    b = tk.Button(
        parent, text=text, font=("Segoe UI", 10, "bold"),
        bg=bg, fg="white", relief="flat", bd=0,
        cursor="hand2", command=cmd,
        activebackground=_darken(bg), activeforeground="white",
        padx=padx, pady=pady, **kw
    )
    add_hover(b, bg)
    return b


def disable_btn(btn):
    btn.config(state="disabled", bg=DISABLED, fg="white", cursor="arrow")
    btn.unbind("<Enter>")
    btn.unbind("<Leave>")


def enable_btn(btn, bg):
    btn.config(state="normal", bg=bg, fg="white", cursor="hand2")
    add_hover(btn, bg)


def divider(parent, padx=0, pady=(10, 10)):
    tk.Frame(parent, height=1, bg=BORDER).pack(fill="x", padx=padx, pady=pady)


def section_label(parent, text):
    tk.Label(parent, text=text, font=FH3, bg=BG, fg=TEXT).pack(
        anchor="w", pady=(0, 10))


def step_badge(parent, n, text):
    row = tk.Frame(parent, bg=BG)
    row.pack(fill="x", pady=(0, 8))
    tk.Label(row, text=f" {n} ", font=("Segoe UI", 8, "bold"),
             bg=HDR, fg="white").pack(side="left")
    tk.Label(row, text=f"  {text}", font=("Segoe UI", 9, "bold"),
             bg=BG, fg=MUTED).pack(side="left")


def option_card(parent, title, desc, cmd, disabled=False):
    """Clickable card with hover highlight — matches reference style."""
    cur     = "arrow" if disabled else "hand2"
    fg_text = DISABLED if disabled else TEXT
    fg_desc = DISABLED if disabled else MUTED

    outer = tk.Frame(parent, bg=BORDER, padx=1, pady=1, cursor=cur)
    outer.pack(fill="x", pady=(0, 8))
    inner = tk.Frame(outer, bg=CARD, padx=16, pady=14, cursor=cur)
    inner.pack(fill="x")
    t = tk.Label(inner, text=title, font=FH3, bg=CARD, fg=fg_text, anchor="w", cursor=cur)
    t.pack(fill="x")
    d = tk.Label(inner, text=desc,  font=FSMALL, bg=CARD, fg=fg_desc, anchor="w", cursor=cur)
    d.pack(fill="x", pady=(3, 0))

    if not disabled:
        def _enter(_):
            outer.config(bg=PRIMARY)
            for w in (inner, t, d):
                w.config(bg=PRIMARY_LT)

        def _leave(_):
            outer.config(bg=BORDER)
            for w in (inner, t, d):
                w.config(bg=CARD)

        for w in (outer, inner, t, d):
            w.bind("<Enter>",    _enter)
            w.bind("<Leave>",    _leave)
            w.bind("<Button-1>", lambda _: cmd())


# ── Manual ─────────────────────────────────────────────────────────────────────
def abrir_manual():
    v = tk.Toplevel(root)
    v.title("Payment Information Updater — Manual")
    v.resizable(False, False)
    v.config(bg=BG)

    make_header(v, "Búsqueda Manual", "Busca por número de teléfono y consulta su información de pago")

    body = tk.Frame(v, bg=BG, padx=24, pady=20)
    body.pack(fill="both", expand=True)

    section_label(body, "Phone Number")

    search_row = tk.Frame(body, bg=BG)
    search_row.pack(fill="x", pady=(0, 16))

    entry = tk.Entry(
        search_row, font=FBODY, width=26, relief="flat",
        bg=CARD, fg=TEXT, insertbackground=TEXT,
        highlightthickness=1, highlightbackground=BORDER,
        highlightcolor=PRIMARY
    )
    entry.pack(side="left", ipady=8, ipadx=10, padx=(0, 8))
    entry.focus()

    btn_buscar = flat_btn(search_row, "Buscar", PRIMARY, lambda: buscar_status())
    btn_buscar.pack(side="left")
    entry.bind("<Return>", lambda _: buscar_status())

    # ── Result card ────────────────────────────────────────────────────────────
    result_outer = tk.Frame(body, bg=BORDER, padx=1, pady=1)
    result_inner = tk.Frame(result_outer, bg=CARD, padx=20, pady=18)
    result_inner.pack(fill="both")

    lbl_msg = tk.Label(result_inner, text="", font=FSMALL, bg=CARD, fg=ERROR_C)

    case_info_frame = tk.Frame(result_inner, bg=CARD)

    info_heading = tk.Label(result_inner, text="INFORMACIÓN DE PAGO",
                             font=("Segoe UI", 9, "bold"), bg=CARD, fg=HDR)
    info_frame = tk.Frame(result_inner, bg=CARD)
    edit_frame = tk.Frame(result_inner, bg=CARD)

    INFO_COLS = 3

    def _tile(parent, border_color=BORDER):
        """Caja con borde para envolver un campo (lectura o edición)."""
        outer = tk.Frame(parent, bg=border_color, padx=1, pady=1)
        inner = tk.Frame(outer, bg=CARD, padx=12, pady=10)
        inner.pack(fill="both", expand=True)
        return outer, inner

    def _grid_tiles(container):
        for c in range(INFO_COLS):
            container.grid_columnconfigure(c, weight=1, uniform="infocol")

    CASE_INFO_COLS = 4

    def _populate_case_info(resultado):
        """Muestra Status, Substatus, Case Owner y Opportunity Name — solo informativos, no editables."""
        for w in case_info_frame.winfo_children():
            w.destroy()
        for c in range(CASE_INFO_COLS):
            case_info_frame.grid_columnconfigure(c, weight=1, uniform="caseinfo")

        campos = (
            ("Status", resultado['Status']),
            ("Substatus", resultado['Substatus']),
            ("Case Owner", resultado['Case Owner']),
            ("Opportunity Name", resultado['Opportunity Name']),
        )

        for col_i, (label, serie) in enumerate(campos):
            vals = sorted(v for v in serie.dropna().unique().tolist())
            outer, inner = _tile(case_info_frame)
            outer.grid(row=0, column=col_i, sticky="nswe",
                       padx=(0, 8) if col_i < CASE_INFO_COLS - 1 else 0)
            tk.Label(inner, text=label.upper(), font=("Segoe UI", 8, "bold"),
                     bg=CARD, fg=MUTED).pack(anchor="w")
            tk.Label(inner, text=", ".join(vals) if vals else "—", font=FBODY,
                     bg=CARD, fg=TEXT).pack(anchor="w", pady=(2, 0))

    def _bool_pill(parent, value):
        if value is None:
            text, bg, fg = "— Sin dato", DISABLED_BG, MUTED
        elif value:
            text, bg, fg = "✓  Yes", SUCCESS_BG, SUCCESS
        else:
            text, bg, fg = "✕  No", ERROR_BG, ERROR_C
        return tk.Label(parent, text=f" {text} ", font=("Segoe UI", 9, "bold"),
                         bg=bg, fg=fg, padx=6, pady=3)

    def _populate_info(row):
        for w in info_frame.winfo_children():
            w.destroy()
        fields = _visible_fields(row)
        _grid_tiles(info_frame)
        for i, (label, col, _sf_field, is_bool, is_int) in enumerate(fields):
            r, c = divmod(i, INFO_COLS)
            outer, inner = _tile(info_frame)
            outer.grid(row=r, column=c, sticky="nswe",
                       padx=(0, 8) if c < INFO_COLS - 1 else 0, pady=(0, 8))
            tk.Label(inner, text=label.upper(), font=("Segoe UI", 8, "bold"),
                     bg=CARD, fg=MUTED).pack(anchor="w")
            if is_bool:
                raw = row.get(col)
                value = None if pd.isna(raw) else bool(raw)
                _bool_pill(inner, value).pack(anchor="w", pady=(5, 0))
            elif col == "Lead Replaced":
                phone = _lookup_phone_by_case_id(row.get(col))
                tk.Label(inner, text=phone or "—", font=FBODY,
                         bg=CARD, fg=TEXT).pack(anchor="w", pady=(2, 0))
            else:
                text = _fmt_value(row.get(col), is_int, col in MONEY_FIELDS)
                tk.Label(inner, text=text, font=FBODY,
                         bg=CARD, fg=TEXT).pack(anchor="w", pady=(2, 0))

    edit_widgets = {}
    edit_state   = {}

    def _sync_edit_state():
        for col, widget in edit_widgets.items():
            if col == "Lead Replaced":
                continue
            if isinstance(widget, tk.StringVar):
                edit_state[col] = widget.get()
            else:
                edit_state[col] = widget.get()

    def _build_lead_replaced_block(parent):
        """Bloque de búsqueda por teléfono para seleccionar el Case reemplazado."""
        outer, cell = _tile(parent, border_color=PRIMARY)
        tk.Label(cell, text="LEAD REPLACED", font=("Segoe UI", 8, "bold"),
                 bg=CARD, fg=MUTED).pack(anchor="w")

        lbl_sel = tk.Label(cell, font=("Segoe UI", 9, "bold"), padx=6, pady=3)
        lbl_sel.pack(anchor="w", pady=(5, 8))

        def _refresh_sel_label():
            phone = _lookup_phone_by_case_id(edit_state.get("Lead Replaced"))
            if phone:
                lbl_sel.config(text=f" ✓  {phone} ", bg=SUCCESS_BG, fg=SUCCESS)
            else:
                lbl_sel.config(text=" Ninguno seleccionado ", bg=DISABLED_BG, fg=MUTED)

        _refresh_sel_label()

        search_row = tk.Frame(cell, bg=CARD)
        search_row.pack(anchor="w", fill="x")
        lr_entry = tk.Entry(
            search_row, font=FBODY, width=20, relief="flat",
            bg=CARD, fg=TEXT, insertbackground=TEXT,
            highlightthickness=1, highlightbackground=BORDER, highlightcolor=PRIMARY
        )
        lr_entry.pack(side="left", ipady=5, ipadx=6, padx=(0, 8))

        lr_results = []
        lr_listbox = tk.Listbox(
            cell, font=FBODY, height=4, relief="flat", bd=0,
            bg=CARD, fg=TEXT, selectbackground=PRIMARY, selectforeground="white",
            highlightthickness=1, highlightbackground=BORDER, activestyle="none"
        )

        def _buscar():
            texto = clean_phone(lr_entry.get())
            lr_listbox.delete(0, tk.END)
            lr_results.clear()
            if not texto:
                return
            matches = df[df['Phone Number'] == texto]
            if matches.empty:
                lr_listbox.insert(tk.END, "Sin resultados")
                lr_listbox.pack(fill="x", pady=(8, 0))
                return
            vistos = set()
            for _, rec in matches.iterrows():
                case_id = rec['Lead__c']
                if pd.isna(case_id) or case_id in vistos:
                    continue
                vistos.add(case_id)
                lr_results.append((case_id, rec['Phone Number']))
                lr_listbox.insert(tk.END, rec['Phone Number'])
            lr_listbox.pack(fill="x", pady=(8, 0))

        def _seleccionar(_event=None):
            sel = lr_listbox.curselection()
            if not sel or sel[0] >= len(lr_results):
                return
            case_id, _phone = lr_results[sel[0]]
            edit_state["Lead Replaced"] = case_id
            _refresh_sel_label()

        lr_btn = flat_btn(search_row, "Buscar", PRIMARY, lambda: _buscar())
        lr_btn.pack(side="left", padx=(0, 8))
        lr_entry.bind("<Return>", lambda _e: _buscar())
        lr_listbox.bind("<<ListboxSelect>>", _seleccionar)

        btn_quitar = tk.Button(
            search_row, text="  Quitar  ", font=("Segoe UI", 9, "bold"),
            bg=CARD, fg=ERROR_C, relief="flat", bd=0, cursor="hand2",
            activebackground=CARD, activeforeground=ERROR_C,
            command=lambda: (edit_state.__setitem__("Lead Replaced", None), _refresh_sel_label())
        )
        btn_quitar.pack(side="left")

        edit_widgets["Lead Replaced"] = None
        return outer

    def _rebuild_edit_form():
        for w in edit_frame.winfo_children():
            w.destroy()
        edit_widgets.clear()
        fields = _visible_fields(edit_state)
        grid_fields = [f for f in fields if f[1] != "Lead Replaced"]
        _grid_tiles(edit_frame)

        for i, (label, col, _sf_field, is_bool, is_int) in enumerate(grid_fields):
            r, c = divmod(i, INFO_COLS)
            outer, cell = _tile(edit_frame, border_color=PRIMARY_LT)
            outer.grid(row=r, column=c, sticky="nswe",
                       padx=(0, 8) if c < INFO_COLS - 1 else 0, pady=(0, 8))
            tk.Label(cell, text=label.upper(), font=("Segoe UI", 8, "bold"),
                     bg=CARD, fg=MUTED).pack(anchor="w")
            if is_bool:
                current = edit_state.get(col, "No")
                var = tk.StringVar(value=current if current in ("Yes", "No") else "No")
                cb = ttk.Combobox(cell, textvariable=var, values=["Yes", "No"],
                                   state="readonly", font=FBODY, width=10)
                cb.bind("<<ComboboxSelected>>", lambda _e: _on_dependency_change())
                cb.pack(anchor="w", pady=(4, 0))
                edit_widgets[col] = var
            else:
                display_val = edit_state.get(col, "") or ""
                ent = tk.Entry(
                    cell, font=FBODY, width=14, relief="flat",
                    bg=CARD, fg=TEXT, insertbackground=TEXT,
                    highlightthickness=1, highlightbackground=BORDER, highlightcolor=PRIMARY
                )
                ent.insert(0, display_val)
                ent.pack(anchor="w", ipady=4, ipadx=4, pady=(4, 0), fill="x")
                edit_widgets[col] = ent

        if any(f[1] == "Lead Replaced" for f in fields):
            row_n = (len(grid_fields) + INFO_COLS - 1) // INFO_COLS
            lr_cell = _build_lead_replaced_block(edit_frame)
            lr_cell.grid(row=row_n, column=0, columnspan=INFO_COLS, sticky="we", pady=(0, 8))

    def _on_dependency_change():
        _sync_edit_state()
        _rebuild_edit_form()

    def _build_edit_form(row):
        edit_state.clear()
        for _label, col, _sf_field, is_bool, is_int in INFO_FIELDS:
            raw = row.get(col)
            if is_bool:
                edit_state[col] = "Yes" if _is_yes(raw) else "No"
            elif col == "Lead Replaced":
                edit_state[col] = None if pd.isna(raw) else raw
            else:
                display_val = _fmt_value(raw, is_int, is_money=False)
                edit_state[col] = "" if display_val == "—" else display_val
        _rebuild_edit_form()

    def _collect_payload():
        _sync_edit_state()
        payload = {}
        for label, col, sf_field, is_bool, is_int in INFO_FIELDS:
            if col == "Lead Replaced":
                payload[sf_field] = edit_state.get(col) or None
                continue
            value = edit_state.get(col, "No" if is_bool else "")
            if is_bool:
                payload[sf_field] = _is_yes(value)
                continue
            texto = (value or "").strip()
            if not texto:
                payload[sf_field] = None
            elif is_int:
                try:
                    payload[sf_field] = int(float(texto))
                except ValueError:
                    raise ValueError(f'"{label}" debe ser un número entero.')
            elif col in MONEY_FIELDS:
                try:
                    payload[sf_field] = float(texto)
                except ValueError:
                    raise ValueError(f'"{label}" debe ser un número.')
            else:
                payload[sf_field] = texto
        return _clean_dependent_payload(payload)

    btn_editar_row = tk.Frame(result_inner, bg=CARD)
    btn_editar = flat_btn(btn_editar_row, "  ✎  Editar información  ", HDR, lambda: _toggle_edit(True))
    btn_editar.pack(anchor="w")

    lbl_locked = tk.Label(
        result_inner,
        text="No se puede editar: el Substatus actual no lo permite "
             "(solo Accepted, Signed, Transferred o Posted).",
        font=FSMALL, bg=CARD, fg=WARN_C, wraplength=460, justify="left"
    )

    edit_actions_row = tk.Frame(result_inner, bg=CARD)
    btn_guardar = flat_btn(edit_actions_row, "  ✓  Guardar cambios  ", SUCCESS, lambda: guardar_edicion())
    btn_cancelar = tk.Button(
        edit_actions_row, text="  Cancelar  ", font=("Segoe UI", 10, "bold"),
        bg=CARD, fg=MUTED, relief="flat", bd=0, cursor="hand2",
        activebackground=CARD, activeforeground=TEXT,
        command=lambda: _toggle_edit(False)
    )
    btn_guardar.pack(side="left", padx=(0, 8))
    btn_cancelar.pack(side="left")

    lbl_ph = tk.Label(result_inner, text="Ingresa un número y presiona Buscar",
                      font=FSMALL, bg=CARD, fg=MUTED)
    lbl_ph.pack(pady=8)

    current_ids      = []
    current_lead_ids = []
    current_row      = {'data': None}

    def _toggle_edit(active):
        if active:
            if current_row['data'] is None:
                return
            _build_edit_form(current_row['data'])
            info_frame.pack_forget()
            btn_editar_row.pack_forget()
            edit_frame.pack(fill="x", pady=(0, 12))
            edit_actions_row.pack(anchor="w")
        else:
            edit_frame.pack_forget()
            edit_actions_row.pack_forget()
            info_frame.pack(fill="x")
            btn_editar_row.pack(anchor="w", pady=(10, 0))

    def guardar_edicion():
        if not current_lead_ids:
            return
        if not _substatus_ok(current_lead_ids):
            messagebox.showerror(
                "No permitido",
                "Este caso ya no tiene un Substatus permitido para actualizar "
                "(solo Accepted, Signed, Transferred o Posted).", parent=v)
            _toggle_edit(False)
            return
        try:
            payload = _collect_payload()
        except ValueError as exc:
            messagebox.showerror("Dato inválido", str(exc), parent=v)
            return
        try:
            for lead_id in current_lead_ids:
                sf.Case.update(lead_id, payload)
            for _label, col, sf_field, _is_bool, _is_int in INFO_FIELDS:
                df.loc[df['Lead__c'].isin(current_lead_ids), col] = payload[sf_field]
            current_row['data'] = df[df['Id'].isin(current_ids)].iloc[0]
            _populate_info(current_row['data'])
            _toggle_edit(False)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo guardar:\n{exc}", parent=v)

    def _show_placeholder():
        for w in (lbl_msg, case_info_frame, info_heading, info_frame, btn_editar_row,
                  lbl_locked, edit_frame, edit_actions_row):
            w.pack_forget()
        lbl_ph.pack(pady=8)
        result_outer.pack_forget()

    def _show_not_found(phone_input):
        edit_frame.pack_forget()
        edit_actions_row.pack_forget()
        lbl_ph.pack_forget()
        case_info_frame.pack_forget()
        info_heading.pack_forget()
        info_frame.pack_forget()
        btn_editar_row.pack_forget()
        lbl_locked.pack_forget()
        lbl_msg.config(text=f'No se encontraron registros para "{phone_input}".')
        lbl_msg.pack(anchor="w")
        result_outer.pack(fill="x", pady=(0, 4))

    def _show_info(resultado):
        edit_frame.pack_forget()
        edit_actions_row.pack_forget()
        lbl_ph.pack_forget()
        lbl_msg.pack_forget()
        row = resultado.iloc[0]
        _populate_case_info(resultado)
        _populate_info(row)
        case_info_frame.pack(fill="x", pady=(0, 14))
        info_heading.pack(anchor="w", pady=(0, 10))
        info_frame.pack(fill="x")

        case_ids = resultado['Lead__c'].dropna().unique().tolist()
        if _substatus_ok(case_ids):
            lbl_locked.pack_forget()
            btn_editar_row.pack(anchor="w", pady=(10, 0))
        else:
            btn_editar_row.pack_forget()
            lbl_locked.pack(anchor="w", pady=(10, 0))
        result_outer.pack(fill="x", pady=(0, 4))

    def buscar_status():
        phone_input = clean_phone(entry.get())
        if not phone_input:
            return
        resultado = df[df['Phone Number'] == phone_input]
        current_ids.clear()
        current_lead_ids.clear()

        if resultado.empty:
            current_row['data'] = None
            _show_not_found(phone_input)
            return

        current_ids.extend(resultado['Id'].tolist())
        current_lead_ids.extend(resultado['Lead__c'].dropna().unique().tolist())
        current_row['data'] = resultado.iloc[0]
        _show_info(resultado)

    _show_placeholder()
    v.after(1, lambda: center_win(v))


# ── Masivo ─────────────────────────────────────────────────────────────────────
def abrir_masivo():
    v = tk.Toplevel(root)
    v.title("Actualización Masiva — Excel")
    v.resizable(False, False)
    v.config(bg=BG)

    state = {'ruta': None, 'df_excel': None, 'response_codes': None}

    make_header(v, "Actualización Masiva",
                "Importa un Excel y actualiza información de pago en lote")

    body = tk.Frame(v, bg=BG, padx=24, pady=20)
    body.pack(fill="both", expand=True)

    # ── Paso 1 — archivo ───────────────────────────────────────────────────────
    step_badge(body, "1", "SELECCIONAR ARCHIVO")
    tk.Label(body, text="Columna requerida: Phone Number",
             font=FSMALL, bg=BG, fg=MUTED).pack(anchor="w")
    tk.Label(body,
             text="Columnas opcionales: Cost · Invoice · Billable · Paid · Bonus ·\n"
                  "Bonus Amount · Replacement · Lead Replaced · Amount Replaced\n"
                  "(deja la celda vacía en las filas donde no quieras tocar ese campo)",
             font=FSMALL, bg=BG, fg=MUTED, justify="left").pack(anchor="w", pady=(2, 10))

    btn_seleccionar = flat_btn(body, "  Seleccionar archivo Excel  ", HDR,
                               lambda: seleccionar_archivo())
    btn_seleccionar.pack(anchor="w", pady=(0, 10))

    # File slot — always visible, content changes with state
    file_slot  = tk.Frame(body, bg=BORDER, padx=1, pady=1)
    file_slot.pack(fill="x", pady=(0, 4))
    file_inner = tk.Frame(file_slot, bg=CARD, padx=14, pady=12)
    file_inner.pack(fill="x")

    lbl_ph_file = tk.Label(file_inner, text="Ningún archivo seleccionado",
                           font=FSMALL, bg=CARD, fg=MUTED)
    lbl_ph_file.pack(anchor="w")

    file_top  = tk.Frame(file_inner, bg=CARD)
    lbl_fname = tk.Label(file_top, text="", font=("Segoe UI", 10, "bold"),
                         bg=CARD, fg=TEXT)
    lbl_fname.pack(side="left")
    btn_eliminar = tk.Button(
        file_top, text="  Eliminar  ", font=("Segoe UI", 8, "bold"),
        bg=ERROR_BG, fg=ERROR_C, relief="flat", bd=0, cursor="hand2",
        activebackground=ERROR_BD, activeforeground=ERROR_C,
        command=lambda: eliminar_archivo()
    )
    btn_eliminar.pack(side="right")
    lbl_recs = tk.Label(file_inner, text="", font=FSMALL, bg=CARD, fg=MUTED)

    divider(body, pady=(12, 12))

    # ── Paso 2 — actualizar ────────────────────────────────────────────────────
    step_badge(body, "2", "ACTUALIZAR REGISTROS")

    btn_actualizar = flat_btn(body, "  Actualizar  ", SUCCESS,
                              lambda: actualizar(), padx=20, pady=10)
    disable_btn(btn_actualizar)
    btn_actualizar.pack(anchor="w", pady=(0, 6))

    pb = ttk.Progressbar(body, mode="indeterminate", length=350)

    divider(body, pady=(8, 12))

    # ── Paso 3 — resultados ────────────────────────────────────────────────────
    step_badge(body, "3", "RESULTADOS")

    boxes_row = tk.Frame(body, bg=BG)
    boxes_row.pack(anchor="w", pady=(0, 12))

    def stat_box(parent, box_bg, bd_color, label, is_success):
        color = SUCCESS if is_success else ERROR_C
        outer = tk.Frame(parent, bg=bd_color, padx=1, pady=1)
        outer.pack(side="left", padx=(0, 10))
        inner = tk.Frame(outer, bg=box_bg, padx=28, pady=12)
        inner.pack()
        num = tk.Label(inner, text="—", font=FBIG, bg=box_bg, fg=color)
        num.pack()
        tk.Label(inner, text=label, font=("Segoe UI", 8, "bold"),
                 bg=box_bg, fg=color).pack()
        return num

    lbl_succ = stat_box(boxes_row, SUCCESS_BG, SUCCESS_BD, "Successes", True)
    lbl_err  = stat_box(boxes_row, ERROR_BG,   ERROR_BD,   "Errors",    False)

    btn_ver = flat_btn(body, "  Ver Resultados  ", PRIMARY,
                       lambda: ver_resultados(), padx=20, pady=10)
    disable_btn(btn_ver)
    btn_ver.pack(anchor="w")

    # ── Lógica ─────────────────────────────────────────────────────────────────
    def _slot_empty():
        file_top.pack_forget()
        lbl_recs.pack_forget()
        file_slot.config(bg=BORDER)
        file_inner.config(bg=CARD)
        lbl_ph_file.config(bg=CARD, fg=MUTED)
        lbl_ph_file.pack(anchor="w")

    def _slot_loaded(nombre, n):
        lbl_ph_file.pack_forget()
        lbl_fname.config(text=f"  {nombre}")
        lbl_recs.config(text=f"  {n} registros cargados", bg=SUCCESS_BG)
        file_slot.config(bg=SUCCESS_BD)
        file_inner.config(bg=SUCCESS_BG)
        lbl_fname.config(bg=SUCCESS_BG)
        file_top.config(bg=SUCCESS_BG)
        btn_eliminar.config(bg=ERROR_BG)
        file_top.pack(fill="x")
        lbl_recs.pack(anchor="w", pady=(3, 0))

    def seleccionar_archivo():
        ruta = filedialog.askopenfilename(
            parent=v, title="Selecciona el archivo Excel",
            filetypes=[("Excel", "*.xlsx *.xls")]
        )
        if not ruta:
            return
        try:
            df_excel = pd.read_excel(ruta)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo leer el archivo:\n{exc}", parent=v)
            return

        if "Phone Number" not in df_excel.columns:
            messagebox.showerror("Columna faltante",
                                 'Falta la columna: "Phone Number"', parent=v)
            return

        if not any(f[0] in df_excel.columns for f in INFO_FIELDS):
            columnas = " · ".join(f[0] for f in INFO_FIELDS)
            messagebox.showerror(
                "Sin columnas de pago",
                f"El Excel no tiene ninguna columna de pago para actualizar.\n\nColumnas válidas: {columnas}",
                parent=v)
            return

        state['ruta']           = ruta
        state['df_excel']       = df_excel
        state['response_codes'] = None

        nombre = ruta.replace("\\", "/").split("/")[-1]
        _slot_loaded(nombre, len(df_excel))
        lbl_succ.config(text="—")
        lbl_err.config(text="—")
        enable_btn(btn_actualizar, SUCCESS)
        disable_btn(btn_ver)

    def eliminar_archivo():
        state['ruta']           = None
        state['df_excel']       = None
        state['response_codes'] = None
        _slot_empty()
        lbl_succ.config(text="—")
        lbl_err.config(text="—")
        disable_btn(btn_actualizar)
        disable_btn(btn_ver)

    def actualizar():
        if state['df_excel'] is None:
            return

        disable_btn(btn_actualizar)
        btn_actualizar.config(text="  Procesando...  ")
        disable_btn(btn_ver)
        pb.pack(anchor="w", pady=(0, 6))
        pb.start(10)

        df_excel = state['df_excel']

        # columnas de pago presentes en el Excel (todas opcionales)
        payment_fields = [f for f in INFO_FIELDS if f[0] in df_excel.columns]

        def _payment_payload(fila):
            """Solo incluye en el payload las celdas con valor; las vacías se
            ignoran por completo (no se tocan en Salesforce)."""
            payload = {}
            for label, col, sf_field, is_bool, is_int in payment_fields:
                raw = fila[col]
                vacio = pd.isna(raw) or str(raw).strip() == ""
                if col == "Lead Replaced":
                    if vacio:
                        continue
                    phone_val = str(raw).strip()
                    case_id = _lookup_case_id_by_phone(phone_val)
                    if case_id is None:
                        raise ValueError(
                            f'Lead Replaced: no se encontró un caso con el teléfono "{phone_val}".')
                    payload[sf_field] = case_id
                    continue
                if vacio:
                    continue
                if is_bool:
                    payload[sf_field] = _is_yes(raw)
                elif is_int:
                    try:
                        payload[sf_field] = int(float(raw))
                    except (TypeError, ValueError):
                        raise ValueError(f'"{label}" debe ser un número entero.')
                elif col in MONEY_FIELDS:
                    try:
                        payload[sf_field] = float(raw)
                    except (TypeError, ValueError):
                        raise ValueError(f'"{label}" debe ser un número.')
                else:
                    payload[sf_field] = str(raw).strip()
            return _clean_dependent_payload(payload)

        def process():
            response_codes = []
            successes = 0
            errors    = 0

            for _, fila in df_excel.iterrows():
                phone = clean_phone(fila['Phone Number'])

                coincidencias = df[df['Phone Number'] == phone]
                if coincidencias.empty:
                    response_codes.append("Error: Número no encontrado")
                    errors += 1
                    continue

                case_ids = coincidencias['Lead__c'].dropna().unique().tolist()
                if not case_ids:
                    response_codes.append("Error: sin Case asociado")
                    errors += 1
                    continue

                if not _substatus_ok(case_ids):
                    response_codes.append(
                        "Error: Substatus no permite actualizar (solo Accepted, "
                        "Signed, Transferred o Posted)")
                    errors += 1
                    continue

                try:
                    payload = _payment_payload(fila)
                    if not payload:
                        response_codes.append("Sin cambios (celdas vacías)")
                    else:
                        for case_id in case_ids:
                            sf.Case.update(case_id, payload)
                        for _label, col, sf_field, _is_bool, _is_int in payment_fields:
                            if sf_field in payload:
                                df.loc[df['Lead__c'].isin(case_ids), col] = payload[sf_field]
                        response_codes.append("Success")
                        successes += 1
                except Exception as exc:
                    response_codes.append(f"Error: {exc}")
                    errors += 1

            state['response_codes'] = response_codes
            v.after(0, lambda: _finish(successes, errors))

        def _finish(successes, errors):
            pb.stop()
            pb.pack_forget()
            lbl_succ.config(text=str(successes))
            lbl_err.config(text=str(errors))
            enable_btn(btn_actualizar, SUCCESS)
            btn_actualizar.config(text="  Actualizar  ")
            enable_btn(btn_ver, PRIMARY)

        threading.Thread(target=process, daemon=True).start()

    def ver_resultados():
        if state['df_excel'] is None or state['response_codes'] is None:
            return
        df_resultado = state['df_excel'].copy()
        df_resultado['Response Code'] = state['response_codes']
        ruta_base, ext = os.path.splitext(state['ruta'])
        ruta_resultado = f"{ruta_base}_results{ext}"
        try:
            df_resultado.to_excel(ruta_resultado, index=False)
            os.startfile(ruta_resultado)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo guardar el resultado:\n{exc}", parent=v)

    _slot_empty()
    v.after(1, lambda: center_win(v))


# ── Validador ──────────────────────────────────────────────────────────────────
def abrir_validador():
    v = tk.Toplevel(root)
    v.title("Validador — Excel")
    v.resizable(False, False)
    v.config(bg=BG)

    state = {'ruta': None, 'df_excel': None, 'df_out': None}

    VALIDADOR_COLS = ['Status', 'Substatus', 'Case Owner', 'Opportunity Name']

    make_header(v, "Validador",
                "Importa un Excel con teléfonos y consulta su Status, Substatus, Case Owner y Opportunity Name")

    body = tk.Frame(v, bg=BG, padx=24, pady=20)
    body.pack(fill="both", expand=True)

    # ── Paso 1 — archivo ───────────────────────────────────────────────────────
    step_badge(body, "1", "SELECCIONAR ARCHIVO")
    tk.Label(body, text="Columna requerida: Phone Number",
             font=FSMALL, bg=BG, fg=MUTED).pack(anchor="w", pady=(0, 10))

    btn_seleccionar = flat_btn(body, "  Seleccionar archivo Excel  ", HDR,
                               lambda: seleccionar_archivo())
    btn_seleccionar.pack(anchor="w", pady=(0, 10))

    file_slot  = tk.Frame(body, bg=BORDER, padx=1, pady=1)
    file_slot.pack(fill="x", pady=(0, 4))
    file_inner = tk.Frame(file_slot, bg=CARD, padx=14, pady=12)
    file_inner.pack(fill="x")

    lbl_ph_file = tk.Label(file_inner, text="Ningún archivo seleccionado",
                           font=FSMALL, bg=CARD, fg=MUTED)
    lbl_ph_file.pack(anchor="w")

    file_top  = tk.Frame(file_inner, bg=CARD)
    lbl_fname = tk.Label(file_top, text="", font=("Segoe UI", 10, "bold"),
                         bg=CARD, fg=TEXT)
    lbl_fname.pack(side="left")
    btn_eliminar = tk.Button(
        file_top, text="  Eliminar  ", font=("Segoe UI", 8, "bold"),
        bg=ERROR_BG, fg=ERROR_C, relief="flat", bd=0, cursor="hand2",
        activebackground=ERROR_BD, activeforeground=ERROR_C,
        command=lambda: eliminar_archivo()
    )
    btn_eliminar.pack(side="right")
    lbl_recs = tk.Label(file_inner, text="", font=FSMALL, bg=CARD, fg=MUTED)

    divider(body, pady=(12, 12))

    # ── Paso 2 — generar ───────────────────────────────────────────────────────
    step_badge(body, "2", "GENERAR EXCEL")

    btn_generar = flat_btn(body, "  Generar Excel  ", SUCCESS,
                           lambda: generar(), padx=20, pady=10)
    disable_btn(btn_generar)
    btn_generar.pack(anchor="w", pady=(0, 6))

    divider(body, pady=(8, 12))

    # ── Paso 3 — resultados ────────────────────────────────────────────────────
    step_badge(body, "3", "RESULTADOS")

    boxes_row = tk.Frame(body, bg=BG)
    boxes_row.pack(anchor="w", pady=(0, 12))

    def stat_box(parent, box_bg, bd_color, label, is_success):
        color = SUCCESS if is_success else ERROR_C
        outer = tk.Frame(parent, bg=bd_color, padx=1, pady=1)
        outer.pack(side="left", padx=(0, 10))
        inner = tk.Frame(outer, bg=box_bg, padx=28, pady=12)
        inner.pack()
        num = tk.Label(inner, text="—", font=FBIG, bg=box_bg, fg=color)
        num.pack()
        tk.Label(inner, text=label, font=("Segoe UI", 8, "bold"),
                 bg=box_bg, fg=color).pack()
        return num

    lbl_found    = stat_box(boxes_row, SUCCESS_BG, SUCCESS_BD, "Encontrados", True)
    lbl_notfound = stat_box(boxes_row, ERROR_BG,   ERROR_BD,   "No encontrados", False)

    btn_ver = flat_btn(body, "  Ver Resultados  ", PRIMARY,
                       lambda: ver_resultados(), padx=20, pady=10)
    disable_btn(btn_ver)
    btn_ver.pack(anchor="w")

    # ── Lógica ─────────────────────────────────────────────────────────────────
    def _slot_empty():
        file_top.pack_forget()
        lbl_recs.pack_forget()
        file_slot.config(bg=BORDER)
        file_inner.config(bg=CARD)
        lbl_ph_file.config(bg=CARD, fg=MUTED)
        lbl_ph_file.pack(anchor="w")

    def _slot_loaded(nombre, n):
        lbl_ph_file.pack_forget()
        lbl_fname.config(text=f"  {nombre}")
        lbl_recs.config(text=f"  {n} registros cargados", bg=SUCCESS_BG)
        file_slot.config(bg=SUCCESS_BD)
        file_inner.config(bg=SUCCESS_BG)
        lbl_fname.config(bg=SUCCESS_BG)
        file_top.config(bg=SUCCESS_BG)
        btn_eliminar.config(bg=ERROR_BG)
        file_top.pack(fill="x")
        lbl_recs.pack(anchor="w", pady=(3, 0))

    def seleccionar_archivo():
        ruta = filedialog.askopenfilename(
            parent=v, title="Selecciona el archivo Excel",
            filetypes=[("Excel", "*.xlsx *.xls")]
        )
        if not ruta:
            return
        try:
            df_excel = pd.read_excel(ruta)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo leer el archivo:\n{exc}", parent=v)
            return

        if "Phone Number" not in df_excel.columns:
            messagebox.showerror("Columna faltante",
                                 'Falta la columna: "Phone Number"', parent=v)
            return

        state['ruta']     = ruta
        state['df_excel'] = df_excel
        state['df_out']   = None

        nombre = ruta.replace("\\", "/").split("/")[-1]
        _slot_loaded(nombre, len(df_excel))
        lbl_found.config(text="—")
        lbl_notfound.config(text="—")
        enable_btn(btn_generar, SUCCESS)
        disable_btn(btn_ver)

    def eliminar_archivo():
        state['ruta']     = None
        state['df_excel'] = None
        state['df_out']   = None
        _slot_empty()
        lbl_found.config(text="—")
        lbl_notfound.config(text="—")
        disable_btn(btn_generar)
        disable_btn(btn_ver)

    def generar():
        df_excel = state['df_excel']
        if df_excel is None:
            return

        columnas = {c: [] for c in VALIDADOR_COLS}
        encontrados = 0
        no_encontrados = 0

        for _, fila in df_excel.iterrows():
            phone = clean_phone(fila['Phone Number'])
            coincidencias = df[df['Phone Number'] == phone] if phone else df.iloc[0:0]
            if coincidencias.empty:
                for c in VALIDADOR_COLS:
                    columnas[c].append("")
                no_encontrados += 1
                continue
            encontrados += 1
            for c in VALIDADOR_COLS:
                vals = sorted(v for v in coincidencias[c].dropna().unique().tolist())
                columnas[c].append(", ".join(vals) if vals else "")

        df_out = df_excel.copy()
        for c in VALIDADOR_COLS:
            df_out[c] = columnas[c]
        state['df_out'] = df_out

        lbl_found.config(text=str(encontrados))
        lbl_notfound.config(text=str(no_encontrados))
        enable_btn(btn_ver, PRIMARY)

    def ver_resultados():
        if state['df_out'] is None:
            return
        ruta_base, ext = os.path.splitext(state['ruta'])
        ruta_resultado = f"{ruta_base}_validado{ext}"
        try:
            state['df_out'].to_excel(ruta_resultado, index=False)
            os.startfile(ruta_resultado)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo guardar el resultado:\n{exc}", parent=v)

    _slot_empty()
    v.after(1, lambda: center_win(v))


# ── Root ───────────────────────────────────────────────────────────────────────
root = tk.Tk()
root.title("Payment Information Updater")
root.resizable(False, False)
root.config(bg=BG)

make_header(root, "Payment Information Updater", "Elige el modo de operación")

body_root = tk.Frame(root, bg=BG, padx=24, pady=20)
body_root.pack(fill="both", expand=True)

section_label(body_root, "Selecciona el modo")

option_card(body_root, "Manual",
            "Busca un número de teléfono y actualiza caso a caso.",
            abrir_manual)
option_card(body_root, "Actualización Masiva (Excel)",
            "Carga un Excel con múltiples registros y actualiza en lote.",
            abrir_masivo)
option_card(body_root, "Validador",
            "Carga un Excel con teléfonos y exporta su Status, Substatus, Case Owner y Opportunity Name.",
            abrir_validador)

tk.Label(body_root, text="© 2026 International Media Group. All Rights Reserved.",
         font=("Segoe UI", 8), bg=BG, fg=DISABLED).pack(pady=(10, 0))

root.after(1, lambda: center_win(root))
root.mainloop()
