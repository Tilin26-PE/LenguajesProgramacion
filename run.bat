@echo off
cd /d "%~dp0"
echo ============================================
echo  PedidoCore - Sistema de Gestion de Pedidos
echo ============================================
echo.

REM Detecta si hay que usar "py" (launcher oficial de Windows) o "python".
REM En muchas instalaciones de Windows, "python" apunta al alias falso
REM de la Microsoft Store y hay que usar "py" en su lugar.
set PYCMD=
py --version >nul 2>&1
if not errorlevel 1 (
    set PYCMD=py
) else (
    python --version >nul 2>&1
    if not errorlevel 1 set PYCMD=python
)

if "%PYCMD%"=="" (
    echo ERROR: Python no esta instalado o no esta en el PATH.
    echo Descargalo desde https://www.python.org/downloads/
    echo o revisa Configuracion ^> Aplicaciones ^> Alias de ejecucion de aplicaciones
    echo y desactiva el alias falso de "python.exe".
    pause
    exit /b 1
)

REM Instalar dependencias directamente en el Python del sistema
echo Instalando dependencias...
%PYCMD% -m pip install -r requirements.txt --quiet

if not exist ".env" (
    echo.
    echo ERROR: No existe el archivo .env
    echo Copia .env.example a .env y pega ahi tu DATABASE_URL de Supabase.
    pause
    exit /b 1
)

echo.
echo Listo. Abre tu navegador en: http://localhost:5000
echo Cuentas de prueba: cliente@pedidocore.com / cliente123  ^|  admin@pedidocore.com / admin123
echo Presiona Ctrl+C para detener el servidor.
echo.

%PYCMD% python\app.py
