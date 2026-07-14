"""Acceso a la tabla `usuarios` en Supabase."""

from werkzeug.security import generate_password_hash, check_password_hash
from db import get_conn


def crear_usuario(nombre: str, email: str, password: str, rol: str = 'cliente') -> dict | None:
    """
    Crea un usuario nuevo. Devuelve el usuario creado, o None si el
    email ya esta registrado.
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id FROM usuarios WHERE email = %s', (email,))
            if cur.fetchone():
                return None

            cur.execute(
                'INSERT INTO usuarios (nombre, email, password_hash, rol) '
                'VALUES (%s, %s, %s, %s) '
                'RETURNING id, nombre, email, rol',
                (nombre, email, generate_password_hash(password), rol)
            )
            usuario = cur.fetchone()
        conn.commit()
        return dict(usuario)
    finally:
        conn.close()


def autenticar(email: str, password: str) -> dict | None:
    """Valida credenciales. Devuelve el usuario (sin el hash) si son correctas."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, nombre, email, password_hash, rol FROM usuarios WHERE email = %s',
                (email,)
            )
            usuario = cur.fetchone()
    finally:
        conn.close()

    if not usuario:
        return None
    if not check_password_hash(usuario['password_hash'], password):
        return None

    return {
        'id': usuario['id'],
        'nombre': usuario['nombre'],
        'email': usuario['email'],
        'rol': usuario['rol'],
    }


def obtener_usuario(usuario_id: int) -> dict | None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, nombre, email, rol FROM usuarios WHERE id = %s',
                (usuario_id,)
            )
            usuario = cur.fetchone()
    finally:
        conn.close()
    return dict(usuario) if usuario else None
