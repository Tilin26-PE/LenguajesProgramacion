import subprocess
import sys
import os

id_producto = sys.argv[1]
monto = float(sys.argv[2])

# Carpeta donde está main.py
base_dir = os.path.dirname(os.path.abspath(__file__))

# Archivo Prolog absoluto
ruta_prolog = os.path.join(
    os.path.dirname(base_dir),
    "prolog",
    "reglas_descuento.pl"
)

ruta_prolog = ruta_prolog.replace("\\", "/")

consulta = f"""
consult('{ruta_prolog}'),
descuento({monto}, {id_producto}, D),
write(D),
halt.
"""

cmd = ["swipl", "-g", consulta, "-t", "halt."]

resultado = subprocess.run(
    cmd,
    capture_output=True,
    text=True
)

try:
    descuento = float(resultado.stdout.strip())
except:
    descuento = 0.0

print(descuento)