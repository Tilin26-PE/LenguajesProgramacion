# PedidoCore

Sistema de gestion de pedidos con motor de reglas en **Prolog**, procesamiento
en **Scala** y aplicacion web en **Python (Flask)**. Los usuarios y los
pedidos se guardan en una base de datos **PostgreSQL alojada en Supabase**.

## 1. Crear el proyecto en Supabase

1. Entra a [supabase.com](https://supabase.com) y crea un proyecto nuevo (gratis).
2. Ve a **Project Settings → Database → Connection string → URI**.
3. Copia esa URL. Si vas a desplegar en Render/Railway usa el modo
   **Session pooler** (puerto `6543`); para correr en tu PC puedes usar
   la conexion directa (puerto `5432`).
4. No necesitas crear tablas a mano: la app las crea solas la primera vez
   que arranca (ver `python/db.py`).

## 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` y pega tu `DATABASE_URL` real de Supabase.

## 3. Instalar dependencias y ejecutar

```bash
cd python
pip install -r ../requirements.txt
python app.py
```

O en Windows, simplemente ejecuta `run.bat` (ya instala todo y valida que
exista el `.env`).

Abre `http://localhost:5000`.

## 4. Usuarios de prueba

Al arrancar por primera vez, la app crea automaticamente 2 cuentas
(funcion `seed_usuarios_demo()` en `python/db.py`):

| Rol      | Correo                   | Contrasena  |
|----------|---------------------------|-------------|
| Cliente  | `cliente@pedidocore.com`  | `cliente123`|
| Admin    | `admin@pedidocore.com`    | `admin123`  |

Tambien puedes registrar cuentas nuevas desde `/registro` (siempre se crean
como `cliente`; el rol `admin` solo se asigna manualmente en la base de
datos o desde el seed).

## 5. Estructura de la base de datos

**usuarios**
| campo         | tipo         |
|---------------|--------------|
| id            | serial (PK)  |
| nombre        | varchar(100) |
| email         | varchar(150) unico |
| password_hash | varchar(255) |
| rol           | 'cliente' \| 'admin' |
| creado_en     | timestamp    |

**pedidos**
| campo            | tipo         |
|------------------|--------------|
| id               | serial (PK)  |
| usuario_id       | FK -> usuarios.id |
| cliente          | varchar(100) |
| id_producto      | varchar(10)  |
| nombre_producto  | varchar(100) |
| cantidad         | int          |
| precio_unitario  | numeric(10,2)|
| subtotal         | numeric(10,2)|
| descuento_pct    | numeric(5,2) |
| monto_descuento  | numeric(10,2)|
| total_final      | numeric(10,2)|
| categoria        | varchar(50)  |
| creado_en        | timestamp    |

El catalogo de productos (`prolog/productos.pl`) y las reglas de descuento
(`prolog/reglas.pl`) se mantienen en Prolog: esa es la parte del sistema que
demuestra el motor de inferencia. La base de datos guarda lo que antes vivia
solo en memoria: cuentas de usuario y el historial real de pedidos.

## 6. Permisos

- **Cliente**: crea pedidos y ve solo su propio historial (`/historial`).
- **Admin**: ademas ve `/admin`, con el historial completo de todos los
  usuarios.

## 7. Arquitectura

```
python/app.py                       -> rutas Flask (auth + pedidos + admin)
python/auth.py                      -> decoradores login_required / admin_required
python/db.py                        -> conexion a Supabase + creacion de tablas
python/integracion/usuarios_repo.py -> queries de usuarios (registro/login)
python/integracion/pedidos_repo.py  -> queries de pedidos (guardar/listar)
python/integracion/prolog_bridge.py -> catalogo + descuento (SWI-Prolog)
python/integracion/scala_bridge.py  -> validacion final del pedido (JAR Scala)
```
