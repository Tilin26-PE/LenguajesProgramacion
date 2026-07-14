"""
Conexion a la base de datos (Supabase / PostgreSQL).

Usa la variable de entorno DATABASE_URL, que es el "Connection string"
que Supabase te da en:  Project Settings -> Database -> Connection string (URI).

Ejemplo de formato (usando el pooler, recomendado por compatibilidad IPv4):
postgresql://postgres.PROJECT_REF:[TU-PASSWORD]@aws-0-REGION.pooler.supabase.com:5432/postgres
"""

import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL', '')


def get_conn():
    """Abre una conexion nueva a Supabase. Se cierra despues de cada uso."""
    if not DATABASE_URL:
        raise RuntimeError(
            'No se encontro la variable de entorno DATABASE_URL. '
            'Copia .env.example a .env y pega ahi tu connection string de Supabase.'
        )
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def init_db():
    """Crea las tablas si no existen. Se llama una vez al arrancar la app."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id             SERIAL PRIMARY KEY,
                    nombre         VARCHAR(100) NOT NULL,
                    email          VARCHAR(150) UNIQUE NOT NULL,
                    password_hash  VARCHAR(255) NOT NULL,
                    rol            VARCHAR(20)  NOT NULL DEFAULT 'cliente'
                                   CHECK (rol IN ('cliente', 'admin')),
                    creado_en      TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS productos (
                    id          VARCHAR(10) PRIMARY KEY,
                    nombre      VARCHAR(100) NOT NULL,
                    precio      NUMERIC(10,2) NOT NULL,
                    categoria   VARCHAR(50) NOT NULL,
                    stock       INTEGER NOT NULL DEFAULT 0,
                    activo      BOOLEAN NOT NULL DEFAULT TRUE,
                    creado_en   TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS pedidos (
                    id               SERIAL PRIMARY KEY,
                    usuario_id       INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
                    cliente          VARCHAR(100) NOT NULL,
                    subtotal         NUMERIC(10,2) NOT NULL,
                    monto_descuento  NUMERIC(10,2) NOT NULL,
                    total_final      NUMERIC(10,2) NOT NULL,
                    estado           VARCHAR(20) NOT NULL DEFAULT 'pendiente',
                    creado_en        TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS pedido_items (
                    id               SERIAL PRIMARY KEY,
                    pedido_id        INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
                    id_producto      VARCHAR(10)  NOT NULL REFERENCES productos(id),
                    nombre_producto  VARCHAR(100) NOT NULL,
                    categoria        VARCHAR(50),
                    cantidad         INTEGER      NOT NULL,
                    precio_unitario  NUMERIC(10,2) NOT NULL,
                    subtotal         NUMERIC(10,2) NOT NULL,
                    descuento_pct    NUMERIC(5,2)  NOT NULL,
                    monto_descuento  NUMERIC(10,2) NOT NULL,
                    total_linea      NUMERIC(10,2) NOT NULL
                );
            """)
        conn.commit()
    finally:
        conn.close()


def seed_usuarios_demo():
    """
    Crea los 2 usuarios de prueba si todavia no existen:
      - cliente@pedidocore.com  / cliente123   (rol: cliente)
      - admin@pedidocore.com    / admin123     (rol: admin)
    Se puede llamar en cada arranque: si ya existen, no hace nada.
    """
    from werkzeug.security import generate_password_hash

    demo_usuarios = [
        ('Cliente Demo', 'cliente@pedidocore.com', 'cliente123', 'cliente'),
        ('Administrador', 'admin@pedidocore.com', 'admin123', 'admin'),
    ]

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            for nombre, email, password, rol in demo_usuarios:
                cur.execute('SELECT id FROM usuarios WHERE email = %s', (email,))
                if cur.fetchone():
                    continue
                cur.execute(
                    'INSERT INTO usuarios (nombre, email, password_hash, rol) '
                    'VALUES (%s, %s, %s, %s)',
                    (nombre, email, generate_password_hash(password), rol)
                )
        conn.commit()
    finally:
        conn.close()
