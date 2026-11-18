import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).with_name(".env"), encoding="utf-8-sig", interpolate=False)


def variable_requerida(nombre: str) -> str:
    valor = os.getenv(nombre)
    if valor is None or not valor.strip():
        raise RuntimeError(f"Falta configurar {nombre} en el entorno o en el archivo .env.")
    return valor
