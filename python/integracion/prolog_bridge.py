import subprocess
import os
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROLOG_DIR = os.path.join(_BASE, 'prolog')

# Ruta directa en Windows (evita depender del PATH del sistema)
_SWIPL_WIN = r'C:\Program Files\swipl\bin\swipl.exe'


def _swipl_exe() -> str:
    if sys.platform == 'win32' and os.path.isfile(_SWIPL_WIN):
        return _SWIPL_WIN
    return 'swipl'


def _run(query: str) -> str:
    """Ejecuta una consulta Prolog cargando las reglas de descuento."""
    reglas_pl = os.path.join(_PROLOG_DIR, 'reglas.pl').replace('\\', '/')
    full = f"consult('{reglas_pl}'), {query}"

    resultado = subprocess.run(
        [_swipl_exe(), '-g', full, '-t', 'halt.'],
        capture_output=True,
        text=True,
        encoding='utf-8',
    )
    return resultado.stdout.strip()


def obtener_descuento(monto: float, categoria: str) -> float:
    """Consulta a Prolog el porcentaje de descuento aplicable segun el
    monto y la categoria del producto (el catalogo vive en la base de datos,
    no en Prolog, por eso ya no se pasa el id del producto)."""
    query = f"descuento({monto}, {categoria}, D), write(D)"
    salida = _run(query)
    try:
        return float(salida)
    except (ValueError, TypeError):
        return 0.0
