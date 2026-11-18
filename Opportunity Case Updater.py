import os
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


def leer_excel_con_columnas(ruta, columnas_req):
    xls = pd.ExcelFile(ruta)
    primera_hoja = None
    for nombre_hoja in xls.sheet_names:
        df_hoja = pd.read_excel(xls, sheet_name=nombre_hoja)
        if primera_hoja is None:
            primera_hoja = df_hoja
        if columnas_req.issubset(df_hoja.columns):
            return df_hoja
    return primera_hoja

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
    SELECT Id, Lead__r.Phone_Numbercontact__c, Aceptar_Rechazar__c, Comments__c
    FROM Lead_de_oportunidad__c
    WHERE Oportunidad__r.StageName = 'In progress'
""")

records = accounts.get("records", [])
if records:
    df = json_normalize(records)
    if "attributes" in df.columns:
        df = df.drop(columns=["attributes"])

df = df.rename(columns={
    "Lead__r.Phone_Numbercontact__c": "Phone Number",
    "Aceptar_Rechazar__c":           "Status",
    "Comments__c":                   "Comments",
})
df = df[['Id', 'Phone Number', 'Status', 'Comments']]
df['Status'] = df['Status'].fillna('Pending')

opportunities = sf.query_all("""
    SELECT Id, Lead__c, Lead__r.Phone_Numbercontact__c, Oportunidad__r.Name
    FROM Lead_de_oportunidad__c
""")

op_records = opportunities.get("records", [])
if op_records:
    df_op = json_normalize(op_records)
    if "attributes" in df_op.columns:
        df_op = df_op.drop(columns=["attributes"])

df_op = df_op.rename(columns={
    "Lead__r.Phone_Numbercontact__c": "Phone Number",
    "Oportunidad__r.Name":            "Opportunity Name",
})
df_op = df_op[['Id', 'Lead__c', 'Phone Number', 'Opportunity Name']]

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

LABEL_MAP = {"Aceptar": "Aceptado", "Rechazar": "Rechazado"}


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
    v.title("Aceptar / Rechazar — Manual")
    v.resizable(False, False)
    v.config(bg=BG)

    make_header(v, "Búsqueda Manual", "Busca por número de teléfono y actualiza el status")

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
    result_inner = tk.Frame(result_outer, bg=CARD, padx=16, pady=14)
    result_inner.pack(fill="both")

    lbl_badge   = tk.Label(result_inner, text="", font=("Segoe UI", 8, "bold"), padx=10, pady=3)
    lbl_caption = tk.Label(result_inner, text="", font=FSMALL, bg=CARD, fg=MUTED)

    lbl_comments = tk.Label(result_inner, text="Comments (opcional)",
                            font=FSMALL, bg=CARD, fg=MUTED)
    txt_comments = tk.Text(
        result_inner, font=FBODY, height=3, width=40, relief="flat", bd=0,
        bg=CARD, fg=TEXT, insertbackground=TEXT, wrap="word",
        highlightthickness=1, highlightbackground=BORDER, highlightcolor=PRIMARY
    )

    sep_h       = tk.Frame(result_inner, height=1, bg=BORDER)
    actions_row = tk.Frame(result_inner, bg=CARD)

    btn_aceptar  = flat_btn(actions_row, "  Aceptar  ", SUCCESS, lambda: actualizar_status("Aceptar"))
    btn_rechazar = flat_btn(actions_row, "  Rechazar  ", ERROR_C, lambda: actualizar_status("Rechazar"))
    btn_aceptar.pack(side="left", padx=(0, 8))
    btn_rechazar.pack(side="left")

    lbl_ph = tk.Label(result_inner, text="Ingresa un número y presiona Buscar",
                      font=FSMALL, bg=CARD, fg=MUTED)
    lbl_ph.pack(pady=8)

    current_ids = []

    def _show_placeholder():
        for w in (lbl_badge, lbl_caption, lbl_comments, sep_h, actions_row):
            w.pack_forget()
        txt_comments.pack_forget()
        lbl_ph.pack(pady=8)
        result_outer.pack_forget()

    def _show_result(badge_txt, badge_bg, badge_fg, caption, show_actions):
        lbl_ph.pack_forget()
        lbl_badge.config(text=f"  {badge_txt}  ", bg=badge_bg, fg=badge_fg)
        lbl_badge.pack(anchor="w")
        lbl_caption.config(text=caption)
        lbl_caption.pack(anchor="w", pady=(4, 0))
        if show_actions:
            lbl_comments.pack(anchor="w", pady=(10, 4))
            txt_comments.pack(fill="x")
            sep_h.pack(fill="x", pady=10)
            actions_row.pack(anchor="w")
        else:
            lbl_comments.pack_forget()
            txt_comments.pack_forget()
            sep_h.pack_forget()
            actions_row.pack_forget()
        result_outer.pack(fill="x", pady=(0, 4))

    def buscar_status():
        phone_input = entry.get().strip()
        if not phone_input:
            return
        resultado = df[df['Phone Number'] == phone_input]
        current_ids.clear()
        txt_comments.delete("1.0", "end")

        if resultado.empty:
            _show_result("No encontrado", ERROR_BG, ERROR_C,
                         f'Sin resultados para "{phone_input}".', False)
            return

        current_ids.extend(resultado['Id'].tolist())
        statuses       = resultado['Status'].unique()
        ya_procesado   = all(s in ("Aceptar", "Rechazar") for s in statuses)

        if ya_procesado:
            estado = ', '.join(LABEL_MAP.get(s, s) for s in statuses)
            _show_result(f"✓  {estado}", SUCCESS_BG, SUCCESS,
                         "Este caso ya fue procesado en Salesforce.", False)
        else:
            _show_result("●  Pendiente", WARN_BG, WARN_C,
                         "Selecciona la acción a aplicar:", True)

    def actualizar_status(nuevo_valor):
        if not current_ids:
            return
        comentario = txt_comments.get("1.0", "end-1c").strip()
        try:
            for record_id in current_ids:
                sf.Lead_de_oportunidad__c.update(record_id, {
                    'Aceptar_Rechazar__c': nuevo_valor,
                    'Comments__c':         comentario,
                })
                df.loc[df['Id'] == record_id, 'Status']   = nuevo_valor
                df.loc[df['Id'] == record_id, 'Comments'] = comentario
            label = LABEL_MAP.get(nuevo_valor, nuevo_valor)
            _show_result(f"✓  {label}", SUCCESS_BG, SUCCESS,
                         "Actualizado correctamente en Salesforce.", False)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo actualizar:\n{exc}", parent=v)

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
                "Importa un Excel y actualiza registros en lote")

    body = tk.Frame(v, bg=BG, padx=24, pady=20)
    body.pack(fill="both", expand=True)

    # ── Paso 1 — archivo ───────────────────────────────────────────────────────
    step_badge(body, "1", "SELECCIONAR ARCHIVO")
    tk.Label(body, text="Columnas requeridas: Phone Number · Status · Comments",
             font=FSMALL, bg=BG, fg=MUTED).pack(anchor="w", pady=(0, 10))

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
        columnas_req = {"Phone Number", "Status", "Comments"}
        try:
            df_excel = leer_excel_con_columnas(ruta, columnas_req)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo leer el archivo:\n{exc}", parent=v)
            return

        if not columnas_req.issubset(df_excel.columns):
            faltantes = columnas_req - set(df_excel.columns)
            messagebox.showerror("Columnas faltantes",
                                 f"Faltan columnas: {', '.join(faltantes)}", parent=v)
            return

        state['ruta']          = ruta
        state['df_excel']      = df_excel
        state['response_codes'] = None

        nombre = ruta.replace("\\", "/").split("/")[-1]
        _slot_loaded(nombre, len(df_excel))
        lbl_succ.config(text="—")
        lbl_err.config(text="—")
        enable_btn(btn_actualizar, SUCCESS)
        disable_btn(btn_ver)

    def eliminar_archivo():
        state['ruta']          = None
        state['df_excel']      = None
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

        def process():
            response_codes = []
            successes = 0
            errors    = 0

            for _, fila in df_excel.iterrows():
                phone        = str(fila['Phone Number']).strip()
                nuevo_status = str(fila['Status']).strip()
                comentario   = str(fila['Comments']).strip() if pd.notna(fila['Comments']) else ""

                if nuevo_status not in ("Aceptar", "Rechazar"):
                    response_codes.append(f"Error: Status '{nuevo_status}' inválido")
                    errors += 1
                    continue

                coincidencias = df[df['Phone Number'] == phone]
                if coincidencias.empty:
                    response_codes.append("Error: Número no encontrado")
                    errors += 1
                    continue

                any_success = False
                last_error  = None

                for _, rec in coincidencias.iterrows():
                    if rec['Status'] in ("Aceptar", "Rechazar"):
                        continue
                    try:
                        payload = {'Aceptar_Rechazar__c': nuevo_status}
                        if comentario:
                            payload['Comments__c'] = comentario
                        sf.Lead_de_oportunidad__c.update(rec['Id'], payload)
                        df.loc[df['Id'] == rec['Id'], 'Status'] = nuevo_status
                        any_success = True
                    except Exception as exc:
                        last_error = str(exc)

                if any_success:
                    response_codes.append("Success")
                    successes += 1
                elif last_error:
                    response_codes.append(f"Error: {last_error}")
                    errors += 1
                else:
                    found = [LABEL_MAP.get(s, s) for s in coincidencias['Status'].unique()
                             if s in ("Aceptar", "Rechazar")]
                    response_codes.append(f"Already Processed ({', '.join(found)})")
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


def reasignar_oportunidad_registro(record_id, lead_id, nuevo_opp_id):
    """Reasigna un Lead_de_oportunidad__c a otra oportunidad (elimina + crea).
    Si el Case relacionado está Closed, lo pasa temporalmente a Sent/Signed
    para poder operar y luego restaura Status, Substatus__c y Sent_Date2__c.
    Aceptar_Rechazar__c y Comments__c del registro original se conservan en el nuevo."""
    registro_res = sf.query(f"""
        SELECT Aceptar_Rechazar__c, Comments__c
        FROM Lead_de_oportunidad__c
        WHERE Id = '{record_id}'
    """)
    registro_records = registro_res.get('records', [])
    aceptar_rechazar = registro_records[0]['Aceptar_Rechazar__c'] if registro_records else None
    comentario        = registro_records[0]['Comments__c']        if registro_records else None

    case_res = sf.query(f"""
        SELECT Status, Substatus__c, Sent_Date2__c
        FROM Case
        WHERE Id = '{lead_id}'
    """)
    case_records = case_res.get('records', [])
    status = case_records[0]['Status'] if case_records else None

    if status == 'Closed':
        campos_originales = {
            'Status':        case_records[0]['Status'],
            'Substatus__c':  case_records[0]['Substatus__c'],
            'Sent_Date2__c': case_records[0]['Sent_Date2__c'],
        }
        sf.Lead_de_oportunidad__c.delete(record_id)
        sf.Case.update(lead_id, {'Status': 'Sent', 'Substatus__c': 'Signed'})
        nuevo = sf.Lead_de_oportunidad__c.create({
            'Lead__c':             lead_id,
            'Oportunidad__c':      nuevo_opp_id,
            'Aceptar_Rechazar__c': aceptar_rechazar,
            'Comments__c':         comentario,
        })
        sf.Case.update(lead_id, campos_originales)
    else:
        sf.Lead_de_oportunidad__c.delete(record_id)
        nuevo = sf.Lead_de_oportunidad__c.create({
            'Lead__c':             lead_id,
            'Oportunidad__c':      nuevo_opp_id,
            'Aceptar_Rechazar__c': aceptar_rechazar,
            'Comments__c':         comentario,
        })

    return nuevo['id']


CASE_STATUS_MAP = {
    'Aceptar':  {'Status': 'Closed', 'Substatus__c': 'Accepted'},
    'Rechazar': {'Status': 'Closed', 'Substatus__c': 'Reject'},
}


def cambiar_status_registro(record_id, lead_id, opp_id, nuevo_status, comentario):
    """Cambia Aceptar_Rechazar__c sin restricción de etapa, recreando el
    registro Lead_de_oportunidad__c en la misma oportunidad (elimina + crea,
    mismo patrón que reasignar_oportunidad_registro) para poder pasar el
    Case por Sent/Signed y operar. Guarda el Date Sent original, deja el
    Case en Status='Closed' con Substatus__c acorde al resultado
    (Aceptar -> Accepted, Rechazar -> Reject) y restaura Sent_Date2__c."""
    case_res = sf.query(f"""
        SELECT Sent_Date2__c
        FROM Case
        WHERE Id = '{lead_id}'
    """)
    case_records = case_res.get('records', [])
    sent_date_original = case_records[0]['Sent_Date2__c'] if case_records else None

    sf.Lead_de_oportunidad__c.delete(record_id)
    sf.Case.update(lead_id, {'Status': 'Sent', 'Substatus__c': 'Signed'})
    nuevo = sf.Lead_de_oportunidad__c.create({
        'Lead__c':             lead_id,
        'Oportunidad__c':      opp_id,
        'Aceptar_Rechazar__c': nuevo_status,
        'Comments__c':         comentario,
    })

    sf.Case.update(lead_id, CASE_STATUS_MAP[nuevo_status])
    # Llamada aparte: algún workflow re-marca Sent_Date2__c al cambiar
    # Status/Substatus, así que se restaura después, no en el mismo update.
    sf.Case.update(lead_id, {'Sent_Date2__c': sent_date_original})

    return nuevo['id']


# ── Forzar Cambio de Estado — sin restricción de etapa ──────────────────────────
def abrir_forzar_estado():
    v = tk.Toplevel(root)
    v.title("Forzar Cambio de Estado")
    v.resizable(False, False)
    v.config(bg=BG)

    make_header(v, "Forzar Cambio de Estado",
                "Busca por teléfono sin restricción de etapa y alterna Aceptado / Rechazado")

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

    btn_buscar = flat_btn(search_row, "Buscar", PRIMARY, lambda: buscar_registro())
    btn_buscar.pack(side="left")
    entry.bind("<Return>", lambda _: buscar_registro())

    # ── Result card ────────────────────────────────────────────────────────────
    result_outer = tk.Frame(body, bg=BORDER, padx=1, pady=1)
    result_inner = tk.Frame(result_outer, bg=CARD, padx=16, pady=14)
    result_inner.pack(fill="both")

    lbl_badge   = tk.Label(result_inner, text="", font=("Segoe UI", 8, "bold"), padx=10, pady=3)
    lbl_caption = tk.Label(result_inner, text="", font=FSMALL, bg=CARD, fg=MUTED)

    lbl_comments = tk.Label(result_inner, text="Comments (opcional)",
                            font=FSMALL, bg=CARD, fg=MUTED)
    txt_comments = tk.Text(
        result_inner, font=FBODY, height=3, width=40, relief="flat", bd=0,
        bg=CARD, fg=TEXT, insertbackground=TEXT, wrap="word",
        highlightthickness=1, highlightbackground=BORDER, highlightcolor=PRIMARY
    )

    sep_h       = tk.Frame(result_inner, height=1, bg=BORDER)
    actions_row = tk.Frame(result_inner, bg=CARD)

    btn_aceptar  = flat_btn(actions_row, "  Marcar Aceptado  ", SUCCESS, lambda: aplicar_cambio("Aceptar"))
    btn_rechazar = flat_btn(actions_row, "  Marcar Rechazado  ", ERROR_C, lambda: aplicar_cambio("Rechazar"))
    btn_aceptar.pack(side="left", padx=(0, 8))
    btn_rechazar.pack(side="left")

    lbl_ph = tk.Label(result_inner, text="Ingresa un número y presiona Buscar",
                      font=FSMALL, bg=CARD, fg=MUTED)
    lbl_ph.pack(pady=8)

    current = {'records': []}

    def _show_placeholder():
        for w in (lbl_badge, lbl_caption, lbl_comments, sep_h, actions_row):
            w.pack_forget()
        txt_comments.pack_forget()
        lbl_ph.pack(pady=8)
        result_outer.pack_forget()

    def _show_result(badge_txt, badge_bg, badge_fg, caption, show_actions):
        lbl_ph.pack_forget()
        lbl_badge.config(text=f"  {badge_txt}  ", bg=badge_bg, fg=badge_fg)
        lbl_badge.pack(anchor="w")
        lbl_caption.config(text=caption)
        lbl_caption.pack(anchor="w", pady=(4, 0))
        if show_actions:
            lbl_comments.pack(anchor="w", pady=(10, 4))
            txt_comments.pack(fill="x")
            sep_h.pack(fill="x", pady=10)
            actions_row.pack(anchor="w")
        else:
            lbl_comments.pack_forget()
            txt_comments.pack_forget()
            sep_h.pack_forget()
            actions_row.pack_forget()
        result_outer.pack(fill="x", pady=(0, 4))

    def buscar_registro():
        phone_input = entry.get().strip()
        if not phone_input:
            return
        current['records'] = []
        txt_comments.delete("1.0", "end")

        phone_escaped = phone_input.replace("\\", "\\\\").replace("'", "\\'")
        try:
            res = sf.query_all(f"""
                SELECT Id, Lead__c, Oportunidad__c, Aceptar_Rechazar__c, Comments__c
                FROM Lead_de_oportunidad__c
                WHERE Lead__r.Phone_Numbercontact__c = '{phone_escaped}'
            """)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo buscar:\n{exc}", parent=v)
            return

        registros = res.get('records', [])
        if not registros:
            _show_result("No encontrado", ERROR_BG, ERROR_C,
                         f'Sin resultados para "{phone_input}".', False)
            return

        current['records'] = registros
        statuses = {r.get('Aceptar_Rechazar__c') or 'Pending' for r in registros}
        estado = ', '.join(LABEL_MAP.get(s, s) for s in statuses)
        _show_result(f"●  {estado}", WARN_BG, WARN_C,
                     "Estado actual. Selecciona la nueva acción a aplicar:", True)

    def aplicar_cambio(nuevo_valor):
        global df
        if not current['records']:
            return
        comentario = txt_comments.get("1.0", "end-1c").strip()
        try:
            nuevos_registros = []
            for rec in current['records']:
                nuevo_id = cambiar_status_registro(
                    rec['Id'], rec['Lead__c'], rec['Oportunidad__c'], nuevo_valor, comentario)

                mask = df['Id'] == rec['Id']
                if mask.any():
                    df.loc[mask, 'Status']   = nuevo_valor
                    df.loc[mask, 'Comments'] = comentario
                    df.loc[mask, 'Id']       = nuevo_id

                nuevos_registros.append({
                    **rec,
                    'Id':                   nuevo_id,
                    'Aceptar_Rechazar__c':  nuevo_valor,
                    'Comments__c':          comentario,
                })
            current['records'] = nuevos_registros

            label = LABEL_MAP.get(nuevo_valor, nuevo_valor)
            _show_result(f"✓  {label}", SUCCESS_BG, SUCCESS,
                         "Actualizado correctamente en Salesforce.", False)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo actualizar:\n{exc}", parent=v)

    _show_placeholder()
    v.after(1, lambda: center_win(v))


# ── Cambiar Oportunidades — Manual ──────────────────────────────────────────────
def abrir_manual_oportunidades():
    v = tk.Toplevel(root)
    v.title("Cambiar Oportunidad — Manual")
    v.resizable(False, False)
    v.config(bg=BG)

    make_header(v, "Cambiar Oportunidad", "Busca por número de teléfono y reasigna la oportunidad")

    body = tk.Frame(v, bg=BG, padx=24, pady=20)
    body.pack(fill="both", expand=True)

    # ── Paso 1 — buscar lead ───────────────────────────────────────────────────
    step_badge(body, "1", "BUSCAR POR TELÉFONO")

    search_row = tk.Frame(body, bg=BG)
    search_row.pack(fill="x", pady=(0, 12))

    entry = tk.Entry(
        search_row, font=FBODY, width=26, relief="flat",
        bg=CARD, fg=TEXT, insertbackground=TEXT,
        highlightthickness=1, highlightbackground=BORDER,
        highlightcolor=PRIMARY
    )
    entry.pack(side="left", ipady=8, ipadx=10, padx=(0, 8))
    entry.focus()

    btn_buscar = flat_btn(search_row, "Buscar", PRIMARY, lambda: buscar_lead())
    btn_buscar.pack(side="left")
    entry.bind("<Return>", lambda _: buscar_lead())

    tk.Label(body, text="  OPORTUNIDAD ACTUAL", font=("Segoe UI", 9, "bold"),
             bg=BG, fg=MUTED).pack(anchor="w", pady=(4, 8))

    result_outer = tk.Frame(body, bg=BORDER, padx=1, pady=1)
    result_inner = tk.Frame(result_outer, bg=CARD, padx=16, pady=14)
    result_inner.pack(fill="both")

    lbl_badge   = tk.Label(result_inner, text="", font=("Segoe UI", 8, "bold"), padx=10, pady=3)
    lbl_caption = tk.Label(result_inner, text="", font=FSMALL, bg=CARD, fg=MUTED)

    lbl_ph = tk.Label(result_inner, text="Ingresa un número y presiona Buscar",
                      font=FSMALL, bg=CARD, fg=MUTED)
    lbl_ph.pack(pady=8)

    divider2 = tk.Frame(body, height=1, bg=BORDER)

    # ── Paso 2 — buscar y asignar nueva oportunidad ────────────────────────────
    step2_frame = tk.Frame(body, bg=BG)

    step_badge(step2_frame, "2", "BUSCAR NUEVA OPORTUNIDAD")

    search_row2 = tk.Frame(step2_frame, bg=BG)
    search_row2.pack(fill="x", pady=(0, 10))

    entry2 = tk.Entry(
        search_row2, font=FBODY, width=26, relief="flat",
        bg=CARD, fg=TEXT, insertbackground=TEXT,
        highlightthickness=1, highlightbackground=BORDER,
        highlightcolor=PRIMARY
    )
    entry2.pack(side="left", ipady=8, ipadx=10, padx=(0, 8))

    btn_buscar2 = flat_btn(search_row2, "Buscar", PRIMARY, lambda: buscar_oportunidad())
    btn_buscar2.pack(side="left")
    entry2.bind("<Return>", lambda _: buscar_oportunidad())

    list_outer = tk.Frame(step2_frame, bg=BORDER, padx=1, pady=1)
    list_outer.pack(fill="x", pady=(0, 10))
    list_inner = tk.Frame(list_outer, bg=CARD)
    list_inner.pack(fill="both")

    list_scroll = tk.Scrollbar(list_inner)
    listbox = tk.Listbox(
        list_inner, font=FBODY, height=6, relief="flat", bd=0,
        bg=CARD, fg=TEXT, selectbackground=PRIMARY, selectforeground="white",
        highlightthickness=0, activestyle="none",
        yscrollcommand=list_scroll.set
    )
    list_scroll.config(command=listbox.yview)
    listbox.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=8)
    list_scroll.pack(side="right", fill="y")

    btn_asignar = flat_btn(step2_frame, "  Asignar Oportunidad  ", SUCCESS,
                           lambda: asignar_oportunidad(), padx=20, pady=10)
    disable_btn(btn_asignar)
    btn_asignar.pack(anchor="w")

    current_ids  = []
    opp_results  = []
    selected_opp = {'id': None, 'name': None}

    def _reset_paso2():
        listbox.delete(0, tk.END)
        opp_results.clear()
        selected_opp['id']   = None
        selected_opp['name'] = None
        disable_btn(btn_asignar)

    def _show_placeholder():
        lbl_badge.pack_forget()
        lbl_caption.pack_forget()
        lbl_ph.pack(pady=8)
        result_outer.pack(fill="x", pady=(0, 4))
        step2_frame.pack_forget()
        divider2.pack_forget()

    def _show_current(badge_txt, badge_bg, badge_fg, caption):
        lbl_ph.pack_forget()
        lbl_badge.config(text=f"  {badge_txt}  ", bg=badge_bg, fg=badge_fg)
        lbl_badge.pack(anchor="w")
        lbl_caption.config(text=caption)
        lbl_caption.pack(anchor="w", pady=(4, 0))
        result_outer.pack(fill="x", pady=(0, 4))

    def buscar_lead():
        phone_input = entry.get().strip()
        if not phone_input:
            return
        resultado = df_op[df_op['Phone Number'] == phone_input]
        current_ids.clear()
        _reset_paso2()

        if resultado.empty:
            _show_current("No encontrado", ERROR_BG, ERROR_C,
                          f'Sin resultados para "{phone_input}".')
            step2_frame.pack_forget()
            divider2.pack_forget()
            return

        current_ids.extend(resultado[['Id', 'Lead__c']].itertuples(index=False, name=None))
        nombres = [n for n in resultado['Opportunity Name'].unique() if pd.notna(n)]
        caption = (f"Oportunidad actual: {', '.join(nombres)}" if nombres
                   else "Sin oportunidad asignada actualmente.")
        _show_current("●  Encontrado", WARN_BG, WARN_C, caption)

        divider2.pack(fill="x", pady=(10, 10))
        step2_frame.pack(fill="x")

    def buscar_oportunidad():
        texto = entry2.get().strip()
        if not texto:
            return
        texto_escaped = texto.replace("\\", "\\\\").replace("'", "\\'")
        try:
            res = sf.query(
                f"SELECT Id, Name FROM Opportunity WHERE Name LIKE '%{texto_escaped}%' LIMIT 20"
            )
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo buscar oportunidades:\n{exc}", parent=v)
            return

        _reset_paso2()
        registros = res.get('records', [])
        if not registros:
            listbox.insert(tk.END, "Sin resultados")
            return
        for rec in registros:
            opp_results.append((rec['Id'], rec['Name']))
            listbox.insert(tk.END, rec['Name'])

    def seleccionar_oportunidad(_event):
        sel = listbox.curselection()
        if not sel or sel[0] >= len(opp_results):
            return
        opp_id, opp_name = opp_results[sel[0]]
        selected_opp['id']   = opp_id
        selected_opp['name'] = opp_name
        enable_btn(btn_asignar, SUCCESS)

    listbox.bind("<<ListboxSelect>>", seleccionar_oportunidad)

    def asignar_oportunidad():
        global df_op
        if not current_ids or not selected_opp['id']:
            return
        try:
            nuevos_ids = []
            for record_id, lead_id in current_ids:
                nuevo_id = reasignar_oportunidad_registro(record_id, lead_id, selected_opp['id'])
                df_op.drop(df_op[df_op['Id'] == record_id].index, inplace=True)
                nuevos_ids.append((nuevo_id, lead_id))

            nuevas_filas = pd.DataFrame([{
                'Id':               nid,
                'Lead__c':          lead_id,
                'Phone Number':     entry.get().strip(),
                'Opportunity Name': selected_opp['name'],
            } for nid, lead_id in nuevos_ids])
            df_op = pd.concat([df_op, nuevas_filas], ignore_index=True)

            current_ids.clear()
            current_ids.extend(nuevos_ids)

            _show_current(f"✓  {selected_opp['name']}", SUCCESS_BG, SUCCESS,
                          "Oportunidad reasignada correctamente en Salesforce.")
            disable_btn(btn_asignar)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo reasignar:\n{exc}", parent=v)

    _show_placeholder()
    v.after(1, lambda: center_win(v))


# ── Cambiar Oportunidades — Masivo ───────────────────────────────────────────────
def abrir_masivo_oportunidades():
    v = tk.Toplevel(root)
    v.title("Cambiar Oportunidad — Actualización Masiva")
    v.resizable(False, False)
    v.config(bg=BG)

    state = {'ruta': None, 'df_excel': None, 'response_codes': None}

    make_header(v, "Actualización Masiva",
                "Importa un Excel y reasigna oportunidades en lote")

    body = tk.Frame(v, bg=BG, padx=24, pady=20)
    body.pack(fill="both", expand=True)

    # ── Paso 1 — archivo ───────────────────────────────────────────────────────
    step_badge(body, "1", "SELECCIONAR ARCHIVO")
    tk.Label(body, text="Columnas requeridas: Phone Number · Opportunity Name",
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

    # ── Paso 2 — reasignar ─────────────────────────────────────────────────────
    step_badge(body, "2", "REASIGNAR REGISTROS")

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
        columnas_req = {"Phone Number", "Opportunity Name"}
        try:
            df_excel = leer_excel_con_columnas(ruta, columnas_req)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo leer el archivo:\n{exc}", parent=v)
            return

        if not columnas_req.issubset(df_excel.columns):
            faltantes = columnas_req - set(df_excel.columns)
            messagebox.showerror("Columnas faltantes",
                                 f"Faltan columnas: {', '.join(faltantes)}", parent=v)
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

        def process():
            global df_op
            response_codes = []
            successes = 0
            errors    = 0

            for _, fila in df_excel.iterrows():
                phone         = str(fila['Phone Number']).strip()
                opp_name_dest = str(fila['Opportunity Name']).strip()

                coincidencias = df_op[df_op['Phone Number'] == phone]
                if coincidencias.empty:
                    response_codes.append("Error: Número no encontrado")
                    errors += 1
                    continue

                opp_escaped = opp_name_dest.replace("\\", "\\\\").replace("'", "\\'")
                try:
                    opp_res = sf.query(
                        f"SELECT Id, Name FROM Opportunity WHERE Name = '{opp_escaped}' LIMIT 1"
                    )
                except Exception as exc:
                    response_codes.append(f"Error: {exc}")
                    errors += 1
                    continue

                opp_records = opp_res.get('records', [])
                if not opp_records:
                    response_codes.append(f"Error: Oportunidad '{opp_name_dest}' no encontrada")
                    errors += 1
                    continue
                target_opp_id = opp_records[0]['Id']

                fila_errores = []
                exito_alguno = False
                for _, rec in coincidencias.iterrows():
                    try:
                        nuevo_id = reasignar_oportunidad_registro(
                            rec['Id'], rec['Lead__c'], target_opp_id)
                        df_op.drop(df_op[df_op['Id'] == rec['Id']].index, inplace=True)
                        nueva_fila = pd.DataFrame([{
                            'Id':               nuevo_id,
                            'Lead__c':          rec['Lead__c'],
                            'Phone Number':     phone,
                            'Opportunity Name': opp_name_dest,
                        }])
                        df_op = pd.concat([df_op, nueva_fila], ignore_index=True)
                        exito_alguno = True
                    except Exception as exc:
                        fila_errores.append(str(exc))

                if exito_alguno:
                    response_codes.append("Success")
                    successes += 1
                else:
                    response_codes.append(f"Error: {'; '.join(fila_errores)}")
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


# ── Cambiar Oportunidades — Selección de modo ───────────────────────────────────
def abrir_cambiar_oportunidades():
    v = tk.Toplevel(root)
    v.title("Cambiar Oportunidades")
    v.resizable(False, False)
    v.config(bg=BG)

    make_header(v, "Cambiar Oportunidades", "Elige el modo de operación")

    body = tk.Frame(v, bg=BG, padx=24, pady=20)
    body.pack(fill="both", expand=True)

    section_label(body, "Selecciona el modo")

    option_card(body, "Manual",
                "Busca un número de teléfono y reasigna la oportunidad caso a caso.",
                lambda: [v.destroy(), abrir_manual_oportunidades()])
    option_card(body, "Actualización Masiva (Excel)",
                "Carga un Excel con teléfonos y oportunidades destino, y reasigna en lote.",
                lambda: [v.destroy(), abrir_masivo_oportunidades()])

    v.after(1, lambda: center_win(v))


# ── Selección de modo ──────────────────────────────────────────────────────────
def abrir_aceptar_rechazar():
    v = tk.Toplevel(root)
    v.title("Aceptar / Rechazar Casos")
    v.resizable(False, False)
    v.config(bg=BG)

    make_header(v, "Aceptar / Rechazar", "Elige el modo de operación")

    body = tk.Frame(v, bg=BG, padx=24, pady=20)
    body.pack(fill="both", expand=True)

    section_label(body, "Selecciona el modo")

    option_card(body, "Manual",
                "Busca un número de teléfono y actualiza caso a caso.",
                lambda: [v.destroy(), abrir_manual()])
    option_card(body, "Actualización Masiva (Excel)",
                "Carga un Excel con múltiples registros y actualiza en lote.",
                lambda: [v.destroy(), abrir_masivo()])

    v.after(1, lambda: center_win(v))


# ── Root ───────────────────────────────────────────────────────────────────────
root = tk.Tk()
root.title("Gestión de Casos")
root.resizable(False, False)
root.config(bg=BG)

make_header(root, "Gestión de Casos", "Panel de operaciones Salesforce")

body_root = tk.Frame(root, bg=BG, padx=24, pady=20)
body_root.pack(fill="both", expand=True)

section_label(body_root, "Selecciona una opción")

option_card(body_root,
            "Aceptar / Rechazar Casos",
            "Actualiza el status de leads manualmente o en lote.",
            abrir_aceptar_rechazar)
option_card(body_root,
            "Cambiar Oportunidades",
            "Reasigna la oportunidad de un lead manualmente o en lote.",
            abrir_cambiar_oportunidades)
option_card(body_root,
            "Forzar Cambio de Estado",
            "Busca sin restricción de etapa y alterna Aceptado ↔ Rechazado, incluso si ya fue procesado.",
            abrir_forzar_estado)

tk.Label(body_root, text="© 2026 International Media Group. All Rights Reserved.",
         font=("Segoe UI", 8), bg=BG, fg=DISABLED).pack(pady=(10, 0))

root.after(1, lambda: center_win(root))
root.mainloop()