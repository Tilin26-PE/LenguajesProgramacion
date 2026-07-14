import subprocess
import os
import sys
import glob as _glob

_BASE      = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SCALA_DIR = os.path.join(_BASE, 'scala', 'pedidocore')
_JAR       = os.path.join(_SCALA_DIR, 'target', 'scala-2.13',
                          'pedidocore_2.13-0.1.0-SNAPSHOT.jar')
_SEP       = ';' if sys.platform == 'win32' else ':'

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
    """Localiza java.exe: primero JAVA_HOME, luego rutas conocidas, luego PATH."""
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
    """Localiza scala-library-2.13.x.jar en el proyecto o en cachés de sbt/coursier."""
    home = os.path.expanduser('~')
    patrones = [
        # Dentro del propio proyecto (bg-jobs generados al compilar con sbt)
        os.path.join(_SCALA_DIR, 'target', 'bg-jobs', '*', 'target', '*',
                     'scala-library-2.13.*.jar'),
        # Caché de Coursier en Windows (%LOCALAPPDATA%\Coursier\cache)
        os.path.join(home, 'AppData', 'Local', 'Coursier', 'cache', 'v1',
                     'https', 'repo1.maven.org', 'maven2', 'org', 'scala-lang',
                     'scala-library', '2.13.*', 'scala-library-2.13.*.jar'),
        # Caché de Coursier en Linux/Mac
        os.path.join(home, '.cache', 'coursier', 'v1',
                     'https', 'repo1.maven.org', 'maven2', 'org', 'scala-lang',
                     'scala-library', '2.13.*', 'scala-library-2.13.*.jar'),
        # Caché de ivy2
        os.path.join(home, '.ivy2', 'cache', 'org.scala-lang', 'scala-library',
                     'jars', 'scala-library-2.13.*.jar'),
    ]
    for patron in patrones:
        encontrados = _glob.glob(patron)
        if encontrados:
            return sorted(encontrados)[-1]
    return ''


def procesar_pedido(id_producto: str, nombre: str, precio: float,
                    cantidad: int, stock: int, descuento: float) -> str:
    """
    Ejecuta el JAR Scala compilado con java -cp.
    Devuelve la linea de resultado: OK|...|... o ERROR|...
    """
    if not os.path.isfile(_JAR):
        return 'ERROR|JAR de Scala no encontrado. Ejecuta "sbt package" en scala/pedidocore'

    java     = _java_exe()
    scala_lib = _find_scala_lib()
    classpath = f'{_JAR}{_SEP}{scala_lib}' if scala_lib else _JAR

    cmd = [
        java, '-cp', classpath, 'pedidocore.Main',
        id_producto, nombre,
        str(precio), str(cantidad), str(stock), str(descuento),
    ]
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
    scala_lib_info = scala_lib if scala_lib else 'NO ENCONTRADO'
    stderr_info    = resultado.stderr.strip()[:400] if resultado.stderr.strip() else '(vacío)'
    return (f'ERROR|DIAGNOSTICO: java={java} | '
            f'scala_lib={scala_lib_info} | '
            f'stderr={stderr_info}')
