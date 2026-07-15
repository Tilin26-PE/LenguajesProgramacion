import subprocess
import os
import sys
import glob as _glob

_BASE      = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SCALA_DIR = os.path.join(_BASE, 'scala', 'pedidocore')
_SEP       = ';' if sys.platform == 'win32' else ':'

# JAR autocontenido (generado con `sbt assembly`, incluye scala-library):
# este es el que se usa en produccion (Render/Docker) y es el mas simple.
_ASSEMBLY_JAR = os.path.join(_SCALA_DIR, 'target', 'scala-2.13', 'pedidocore-assembly.jar')

# JAR plano (generado con `sbt package`, sin scala-library incluida):
# se deja como respaldo para desarrollo local si todavia no se corrio assembly.
_PLAIN_JAR = os.path.join(_SCALA_DIR, 'target', 'scala-2.13',
                          'pedidocore_2.13-0.1.0-SNAPSHOT.jar')

# Busca java.exe en carpetas de instalación comunes de Windows
# (no depende de PATH, que a veces no está disponible al ejecutar .bat)
_JAVA_WIN_GLOBS = [
    r'C:\Program Files\Eclipse Adoptium\jdk-*\bin\java.exe',
    r'C:\Program Files\Eclipse Adoptium\jre-*\bin\java.exe',
    r'C:\Program Files\Microsoft\jdk-*\bin\java.exe',
    r'C:\Program Files\Java\jdk-*\bin\java.exe',
    r'C:\Program Files\Java\jre-*\bin\java.exe',
    r'C:\Program Files\BellSoft\LibericaJDK-*\bin\java.exe',
    r'C:\Program Files\BellSoft\LibericaJRE-*\bin\java.exe',
    r'C:\Program Files (x86)\Java\jdk-*\bin\java.exe',
    r'C:\Program Files\Common Files\Oracle\Java\javapath\java.exe',
]


def _java_exe() -> str:
    """Localiza java: en Linux/Render usa el 'java' del PATH (instalado via
    apt en el Dockerfile); en Windows busca en JAVA_HOME y rutas conocidas."""
    if sys.platform == 'win32':
        jh = os.environ.get('JAVA_HOME', '')
        if jh:
            c = os.path.join(jh, 'bin', 'java.exe')
            if os.path.isfile(c):
                return c
        for patron in _JAVA_WIN_GLOBS:
            matches = _glob.glob(patron)
            if matches:
                return sorted(matches)[-1]
    return 'java'


def _find_scala_lib() -> str:
    """Solo se usa como respaldo con el jar plano (sin assembly)."""
    home = os.path.expanduser('~')
    patrones = [
        os.path.join(_SCALA_DIR, 'target', 'bg-jobs', '*', 'target', '*',
                     'scala-library-2.13.*.jar'),
        os.path.join(home, 'AppData', 'Local', 'Coursier', 'cache', 'v1',
                     'https', 'repo1.maven.org', 'maven2', 'org', 'scala-lang',
                     'scala-library', '2.13.*', 'scala-library-2.13.*.jar'),
        os.path.join(home, '.cache', 'coursier', 'v1',
                     'https', 'repo1.maven.org', 'maven2', 'org', 'scala-lang',
                     'scala-library', '2.13.*', 'scala-library-2.13.*.jar'),
        os.path.join(home, '.ivy2', 'cache', 'org.scala-lang', 'scala-library',
                     'jars', 'scala-library-2.13.*.jar'),
    ]
    for patron in patrones:
        encontrados = _glob.glob(patron)
        if encontrados:
            return sorted(encontrados)[-1]
    return ''


def _construir_comando(java: str, args: list) -> list | None:
    """Arma el comando java segun cual jar este disponible."""
    if os.path.isfile(_ASSEMBLY_JAR):
        return [java, '-jar', _ASSEMBLY_JAR, *args]

    if os.path.isfile(_PLAIN_JAR):
        scala_lib = _find_scala_lib()
        classpath = f'{_PLAIN_JAR}{_SEP}{scala_lib}' if scala_lib else _PLAIN_JAR
        return [java, '-cp', classpath, 'pedidocore.Main', *args]

    return None


def procesar_pedido(id_producto: str, nombre: str, precio: float,
                    cantidad: int, stock: int, descuento: float) -> str:
    """
    Ejecuta el JAR Scala compilado.
    Devuelve la linea de resultado: OK|...|... o ERROR|...
    """
    args = [id_producto, nombre, str(precio), str(cantidad), str(stock), str(descuento)]
    java = _java_exe()
    cmd  = _construir_comando(java, args)

    if cmd is None:
        return ('ERROR|JAR de Scala no encontrado. Ejecuta "sbt assembly" '
                '(o "sbt package") en scala/pedidocore')

    resultado = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8',
    )
    salida_total = resultado.stdout + resultado.stderr
    for linea in salida_total.split('\n'):
        linea = linea.strip()
        if linea.startswith('OK|') or linea.startswith('ERROR|'):
            return linea

    # Diagnóstico: mostrar qué imprimió Java para facilitar depuración
    stderr_info = resultado.stderr.strip()[:400] if resultado.stderr.strip() else '(vacío)'
    return f'ERROR|DIAGNOSTICO: java={java} | cmd={" ".join(cmd)} | stderr={stderr_info}'
