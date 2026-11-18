import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, ttk

from tkinterdnd2 import DND_FILES, TkinterDnD

import pymupdf4llm

IS_WINDOWS = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    class _GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    _FOLDERID_DOWNLOADS = "{374DE290-123F-4565-9164-39C4925E467B}"


def get_downloads_path():
    if IS_WINDOWS:
        try:
            guid = _GUID()
            ctypes.windll.ole32.CLSIDFromString(_FOLDERID_DOWNLOADS, ctypes.byref(guid))
            path_ptr = ctypes.c_wchar_p()
            ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, 0, ctypes.byref(path_ptr))
            path = path_ptr.value
            ctypes.windll.ole32.CoTaskMemFree(path_ptr)
            return path
        except OSError:
            pass
    return os.path.join(os.path.expanduser("~"), "Downloads")


def open_path(path):
    if IS_WINDOWS:
        os.startfile(path)
    elif IS_MAC:
        subprocess.run(["open", path])
    else:
        subprocess.run(["xdg-open", path])

# ── Design tokens ──────────────────────────────────────────────────────────────
BG         = "#F4F6F8"
CARD       = "#FFFFFF"
PRIMARY    = "#2563EB"
PRIMARY_LT = "#EFF6FF"
INFO_BG    = "#EEF2F6"
SUCCESS    = "#28A745"
ERROR_C    = "#DC2626"
TEXT       = "#0F172A"
MUTED      = "#6B7280"
BORDER     = "#E2E8F0"
DISABLED   = "#94A3B8"

FONT_FAMILY = "Segoe UI" if IS_WINDOWS else ("Helvetica Neue" if IS_MAC else "DejaVu Sans")

FH2    = (FONT_FAMILY, 14, "bold")
FH3    = (FONT_FAMILY, 11, "bold")
FLABEL = (FONT_FAMILY, 9, "bold")
FBODY  = (FONT_FAMILY, 11)
FSMALL = (FONT_FAMILY, 9)


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
    x = (win.winfo_screenwidth() - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"+{x}+{y}")


def flat_btn(parent, text, bg, fg, cmd, padx=14, pady=9, **kw):
    b = tk.Button(
        parent, text=text, font=(FONT_FAMILY, 10, "bold"),
        bg=bg, fg=fg, relief="flat", bd=0,
        cursor="hand2", command=cmd,
        activebackground=_darken(bg), activeforeground=fg,
        padx=padx, pady=pady, **kw
    )
    add_hover(b, bg)
    return b


def divider(parent, padx=0, pady=(10, 10)):
    tk.Frame(parent, height=1, bg=BORDER).pack(fill="x", padx=padx, pady=pady)


def disable_btn(btn):
    btn.config(state="disabled", bg=DISABLED, fg="white", cursor="arrow")
    btn.unbind("<Enter>")
    btn.unbind("<Leave>")


def enable_btn(btn, bg, fg="white"):
    btn.config(state="normal", bg=bg, fg=fg, cursor="hand2")
    add_hover(btn, bg)


def format_size(num_bytes):
    kb = num_bytes / 1024
    if kb < 1024:
        return f"{kb:,.0f} KB"
    return f"{kb / 1024:,.1f} MB"


# ── Root ───────────────────────────────────────────────────────────────────────
root = TkinterDnD.Tk()
root.title("Markdown Converter")
root.resizable(False, False)
root.config(bg=BG)

style = ttk.Style(root)
style.theme_use("clam")
style.configure(
    "Brand.Horizontal.TProgressbar",
    troughcolor=BORDER, background=PRIMARY, bordercolor=BORDER,
    lightcolor=PRIMARY, darkcolor=PRIMARY, thickness=8, borderwidth=0
)

# ── Header ─────────────────────────────────────────────────────────────────────
header = tk.Frame(root, bg=CARD, padx=24, pady=18)
header.pack(fill="x")

icon_box = tk.Frame(header, bg=PRIMARY, width=40, height=40)
icon_box.pack(side="left", padx=(0, 12))
icon_box.pack_propagate(False)
tk.Label(icon_box, text="📄", font=(FONT_FAMILY, 15), bg=PRIMARY, fg="white").pack(expand=True)

header_text = tk.Frame(header, bg=CARD)
header_text.pack(side="left", fill="x", expand=True)
tk.Label(header_text, text="Markdown Converter", font=FH2, bg=CARD, fg=TEXT).pack(anchor="w")
tk.Label(header_text, text="Convierte PDFs a Markdown en segundos", font=FSMALL, bg=CARD, fg=MUTED).pack(anchor="w")

tk.Frame(root, height=1, bg=BORDER).pack(fill="x")

body = tk.Frame(root, bg=BG, padx=24, pady=20, width=460)
body.pack(fill="both", expand=True)

# ── File selection ─────────────────────────────────────────────────────────────
tk.Label(body, text="ARCHIVOS PDF", font=FLABEL, bg=BG, fg=MUTED).pack(anchor="w", pady=(0, 12))

selected_files = {"paths": []}
is_converting = {"value": False}
file_rows = {}

drop_card = tk.Frame(body, bg=CARD, width=460, height=210,
                      highlightthickness=2, highlightbackground=BORDER)
drop_card.pack(fill="x", pady=(0, 14))
drop_card.pack_propagate(False)

drop_icon_box = tk.Frame(drop_card, bg=PRIMARY_LT, width=44, height=44)
drop_icon_box.pack(pady=(30, 12))
drop_icon_box.pack_propagate(False)
tk.Label(drop_icon_box, text="📄", font=(FONT_FAMILY, 18), bg=PRIMARY_LT, fg=PRIMARY).pack(expand=True)

tk.Label(drop_card, text="Arrastra y suelta tus PDFs aquí", font=(FONT_FAMILY, 11, "bold"),
         bg=CARD, fg=TEXT).pack()
tk.Label(drop_card, text="o", font=FSMALL, bg=CARD, fg=MUTED).pack(pady=(8, 10))


def add_files(rutas):
    pdfs = [r for r in rutas if r.lower().endswith(".pdf")]
    if not pdfs:
        _show_result("Archivo no válido", "Selecciona archivos PDF.", True)
        return
    for ruta in pdfs:
        if ruta not in selected_files["paths"]:
            selected_files["paths"].append(ruta)
            _add_file_row(ruta)
    _refresh_list_state()
    _hide_result()


def remove_file(ruta):
    if is_converting["value"]:
        return
    if ruta in selected_files["paths"]:
        selected_files["paths"].remove(ruta)
    widgets = file_rows.pop(ruta, None)
    if widgets is not None:
        for w in widgets:
            w.destroy()
    _refresh_list_state()


def elegir_archivo():
    if is_converting["value"]:
        return
    rutas = filedialog.askopenfilenames(title="Selecciona archivo(s) PDF", filetypes=[("Archivos PDF", "*.pdf")])
    if rutas:
        add_files(list(rutas))


def on_drop(event):
    if is_converting["value"]:
        return
    rutas = root.tk.splitlist(event.data)
    if rutas:
        add_files(list(rutas))


def _dnd_enter(_event=None):
    if not is_converting["value"]:
        drop_card.config(highlightbackground=PRIMARY)


def _dnd_leave(_event=None):
    if not is_converting["value"]:
        drop_card.config(highlightbackground=BORDER)


drop_card.drop_target_register(DND_FILES)
drop_card.dnd_bind("<<DropEnter>>", _dnd_enter)
drop_card.dnd_bind("<<DropLeave>>", _dnd_leave)
drop_card.dnd_bind("<<Drop>>", on_drop)

btn_browse = flat_btn(drop_card, "Elegir archivos", CARD, TEXT, elegir_archivo,
                       padx=18, pady=9, highlightthickness=1, highlightbackground=BORDER)
btn_browse.pack()

# ── Selected files list ────────────────────────────────────────────────────────
list_section = tk.Frame(body, bg=BG)
list_section.pack(fill="x")

info_banner = tk.Frame(list_section, bg=INFO_BG, padx=14, pady=12)
tk.Label(info_banner, text="ⓘ", font=(FONT_FAMILY, 10, "bold"), bg=INFO_BG, fg=MUTED).pack(side="left", padx=(0, 8))
tk.Label(info_banner, text="Aún no se han añadido archivos", font=FSMALL, bg=INFO_BG, fg=MUTED).pack(side="left")
info_banner.pack(fill="x", pady=(0, 18))

list_outer = tk.Frame(list_section, bg=BORDER, padx=1, pady=1)

list_canvas = tk.Canvas(list_outer, bg=CARD, highlightthickness=0, height=150)
list_scrollbar = tk.Scrollbar(list_outer, orient="vertical", command=list_canvas.yview)
list_inner = tk.Frame(list_canvas, bg=CARD)

list_inner.bind("<Configure>", lambda _e: list_canvas.configure(scrollregion=list_canvas.bbox("all")))
list_canvas_window = list_canvas.create_window((0, 0), window=list_inner, anchor="nw")
list_canvas.bind("<Configure>", lambda e: list_canvas.itemconfig(list_canvas_window, width=e.width))
list_canvas.configure(yscrollcommand=list_scrollbar.set)

list_canvas.pack(side="left", fill="both", expand=True)
list_scrollbar.pack(side="right", fill="y")


def _on_mousewheel(event):
    list_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


list_canvas.bind("<Enter>", lambda _e: list_canvas.bind_all("<MouseWheel>", _on_mousewheel))
list_canvas.bind("<Leave>", lambda _e: list_canvas.unbind_all("<MouseWheel>"))


def _add_file_row(ruta):
    row = tk.Frame(list_inner, bg=CARD)
    row.pack(fill="x", padx=12, pady=(10, 0))

    info = tk.Frame(row, bg=CARD)
    info.pack(side="left", fill="x", expand=True)
    tk.Label(info, text=os.path.basename(ruta), font=FBODY, bg=CARD, fg=TEXT, anchor="w").pack(fill="x")
    tk.Label(info, text=format_size(os.path.getsize(ruta)), font=FSMALL, bg=CARD, fg=MUTED,
              anchor="w").pack(fill="x")

    remove_btn = tk.Label(row, text="✕", font=(FONT_FAMILY, 10, "bold"), bg=CARD, fg=MUTED, cursor="hand2")
    remove_btn.pack(side="right", padx=(8, 0))
    remove_btn.bind("<Button-1>", lambda _e: remove_file(ruta))
    remove_btn.bind("<Enter>", lambda _e: remove_btn.config(fg=ERROR_C))
    remove_btn.bind("<Leave>", lambda _e: remove_btn.config(fg=MUTED))

    sep = tk.Frame(list_inner, height=1, bg=BORDER)
    sep.pack(fill="x", padx=12, pady=(10, 0))

    file_rows[ruta] = (row, sep)


def _refresh_list_state():
    if selected_files["paths"]:
        info_banner.pack_forget()
        list_outer.pack(fill="x", pady=(0, 18))
        enable_btn(btn_convertir, PRIMARY)
    else:
        list_outer.pack_forget()
        info_banner.pack(fill="x", pady=(0, 18))
        disable_btn(btn_convertir)


divider(body, pady=(0, 18))

# ── Convert ──────────────────────────────────────────────────────────────────
convert_row = tk.Frame(body, bg=BG)
convert_row.pack(fill="x")

btn_convertir = flat_btn(convert_row, "Convertir", PRIMARY, "white", lambda: convertir(), padx=20, pady=12)
btn_convertir.pack(fill="x")
disable_btn(btn_convertir)

progress_status = tk.Label(convert_row, text="", font=FSMALL, bg=BG, fg=MUTED)
progress = ttk.Progressbar(convert_row, mode="determinate", style="Brand.Horizontal.TProgressbar",
                            length=260, maximum=100)

result_outer = tk.Frame(body, bg=BORDER, padx=1, pady=1)
result_inner = tk.Frame(result_outer, bg=CARD, padx=20, pady=16)
result_inner.pack(fill="both")

result_badge = tk.Label(result_inner, text="", font=(FONT_FAMILY, 13, "bold"), bg=CARD)
result_badge.pack(anchor="w")

result_detail = tk.Label(result_inner, text="", font=FSMALL, bg=CARD, fg=MUTED,
                          wraplength=380, justify="left")
result_detail.pack(anchor="w", pady=(6, 0))

actions_row = tk.Frame(result_inner, bg=CARD)


def _hide_result():
    result_outer.pack_forget()
    actions_row.pack_forget()


def _show_result(title, detail, is_error, output_path=None, is_folder=False):
    result_badge.config(text=title, fg=ERROR_C if is_error else SUCCESS)
    result_detail.config(text=detail)

    for w in actions_row.winfo_children():
        w.destroy()

    if output_path:
        if is_folder:
            flat_btn(actions_row, "Abrir carpeta", CARD, TEXT, lambda: open_path(output_path),
                      padx=12, pady=6, highlightthickness=1, highlightbackground=BORDER).pack(side="left")
        else:
            flat_btn(actions_row, "Abrir archivo", CARD, TEXT, lambda: open_path(output_path),
                      padx=12, pady=6, highlightthickness=1, highlightbackground=BORDER).pack(side="left", padx=(0, 8))
            flat_btn(actions_row, "Abrir carpeta", CARD, TEXT, lambda: open_path(os.path.dirname(output_path)),
                      padx=12, pady=6, highlightthickness=1, highlightbackground=BORDER).pack(side="left")
        actions_row.pack(anchor="w", pady=(12, 0))

    result_outer.pack(fill="x", pady=(14, 0))
    center_win(root)


def convertir():
    rutas = list(selected_files["paths"])
    if not rutas or is_converting["value"]:
        return

    is_converting["value"] = True
    _hide_result()
    disable_btn(btn_convertir)
    btn_browse.config(state="disabled", cursor="arrow")
    btn_convertir.config(text="Convirtiendo...")
    progress.configure(value=0)
    progress_status.pack(pady=(12, 4))
    progress.pack(fill="x")

    total = len(rutas)

    def _update_progress(i, nombre):
        progress_status.config(text=f"Convirtiendo {i} de {total} — {nombre}")
        progress.configure(value=((i - 1) / total) * 100)

    def worker():
        downloads = get_downloads_path()
        exitosos = []
        fallidos = []

        for i, ruta in enumerate(rutas, start=1):
            nombre = os.path.basename(ruta)
            root.after(0, lambda i=i, nombre=nombre: _update_progress(i, nombre))
            try:
                markdown_text = pymupdf4llm.to_markdown(ruta)
                nombre_base = os.path.splitext(nombre)[0]
                destino = os.path.join(downloads, f"{nombre_base}.md")
                with open(destino, "w", encoding="utf-8") as f:
                    f.write(markdown_text)
                exitosos.append(destino)
            except Exception as exc:
                fallidos.append((nombre, str(exc)))
            root.after(0, lambda i=i: progress.configure(value=(i / total) * 100))

        def finish():
            if not fallidos:
                if len(exitosos) == 1:
                    _show_result("● Conversión completa", f"Guardado en {exitosos[0]}", False,
                                  output_path=exitosos[0])
                else:
                    _show_result("● Conversión completa", f"{len(exitosos)} archivos guardados en {downloads}", False,
                                  output_path=downloads, is_folder=True)
            else:
                detalle_fallos = "\n".join(f"{nombre}: {error}" for nombre, error in fallidos)
                detalle = f"{len(exitosos)} correctos, {len(fallidos)} con errores:\n{detalle_fallos}"
                _show_result("Conversión finalizada con errores", detalle, True,
                              output_path=downloads if exitosos else None, is_folder=True)

        root.after(0, finish)
        root.after(0, _reset_after_convert)

    def _reset_after_convert():
        is_converting["value"] = False
        progress.pack_forget()
        progress_status.pack_forget()
        btn_convertir.config(text="Convertir")
        enable_btn(btn_convertir, PRIMARY)
        btn_browse.config(state="normal", cursor="hand2")

    threading.Thread(target=worker, daemon=True).start()


root.after(1, lambda: center_win(root))
root.mainloop()
