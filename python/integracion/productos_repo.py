"""Acceso a la tabla `productos` en Supabase. El catalogo (antes en Prolog
como hechos estaticos) ahora vive aqui para que el stock se pueda actualizar
de verdad con cada pedido."""

from db import get_conn


def _normalizar(fila: dict) -> dict:
    if fila.get('precio') is not None:
        fila['precio'] = float(fila['precio'])
    return fila


def listar_productos(solo_activos: bool = True) -> list:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if solo_activos:
                cur.execute('SELECT * FROM productos WHERE activo = TRUE ORDER BY id')
            else:
                cur.execute('SELECT * FROM productos ORDER BY id')
            filas = cur.fetchall()
    finally:
        conn.close()
    return [_normalizar(dict(f)) for f in filas]


def obtener_producto(id_producto: str) -> dict | None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM productos WHERE id = %s', (id_producto,))
            fila = cur.fetchone()
    finally:
        conn.close()
    return _normalizar(dict(fila)) if fila else None


def crear_producto(id_producto: str, nombre: str, precio: float,
                   categoria: str, stock: int) -> dict | None:
    """Crea un producto. Devuelve None si el id ya existe."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id FROM productos WHERE id = %s', (id_producto,))
            if cur.fetchone():
                return None
            cur.execute(
                'INSERT INTO productos (id, nombre, precio, categoria, stock) '
                'VALUES (%s, %s, %s, %s, %s) RETURNING *',
                (id_producto, nombre, precio, categoria, stock)
            )
            producto = cur.fetchone()
        conn.commit()
        return _normalizar(dict(producto))
    finally:
        conn.close()


def actualizar_producto(id_producto: str, nombre: str, precio: float,
                        categoria: str, stock: int) -> bool:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE productos SET nombre = %s, precio = %s, categoria = %s, '
                'stock = %s WHERE id = %s',
                (nombre, precio, categoria, stock, id_producto)
            )
            actualizado = cur.rowcount > 0
        conn.commit()
        return actualizado
    finally:
        conn.close()


def desactivar_producto(id_producto: str) -> bool:
    """No se borra fisicamente (podria haber pedidos ligados a el);
    se marca como inactivo para que ya no aparezca en el catalogo."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('UPDATE productos SET activo = FALSE WHERE id = %s', (id_producto,))
            actualizado = cur.rowcount > 0
        conn.commit()
        return actualizado
    finally:
        conn.close()


def reactivar_producto(id_producto: str) -> bool:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('UPDATE productos SET activo = TRUE WHERE id = %s', (id_producto,))
            actualizado = cur.rowcount > 0
        conn.commit()
        return actualizado
    finally:
        conn.close()


def descontar_stock(id_producto: str, cantidad: int) -> dict:
    """
    Descuenta stock de forma segura ante pedidos simultaneos:
    bloquea la fila (SELECT ... FOR UPDATE) dentro de una transaccion,
    vuelve a validar el stock disponible, y recien ahi resta.

    Devuelve {'ok': True, 'producto': {...}} o {'ok': False, 'motivo': '...'}.
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT * FROM productos WHERE id = %s FOR UPDATE',
                (id_producto,)
            )
            producto = cur.fetchone()

            if not producto:
                conn.rollback()
                return {'ok': False, 'motivo': 'Producto no encontrado.'}

            if not producto['activo']:
                conn.rollback()
                return {'ok': False, 'motivo': 'Producto no disponible.'}

            if producto['stock'] < cantidad:
                conn.rollback()
                return {'ok': False, 'motivo': f'Stock insuficiente. Disponible: {producto["stock"]}.'}

            cur.execute(
                'UPDATE productos SET stock = stock - %s WHERE id = %s RETURNING *',
                (cantidad, id_producto)
            )
            actualizado = cur.fetchone()
        conn.commit()
        return {'ok': True, 'producto': _normalizar(dict(actualizado))}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def seed_productos_demo():
    """Carga el catalogo inicial (los mismos 5 productos que antes vivian
    en prolog/productos.pl) si la tabla esta vacia."""
    demo = [
        ('p001', 'Laptop',      1200.0, 'electronica', 5),
        ('p002', 'Camiseta',      25.0, 'ropa',       20),
        ('p003', 'Auriculares',  150.0, 'electronica', 10),
        ('p004', 'Pantalon',      60.0, 'ropa',       15),
        ('p005', 'Tablet',       450.0, 'electronica',  8),
    ]
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) AS n FROM productos')
            if cur.fetchone()['n'] > 0:
                return
            for id_producto, nombre, precio, categoria, stock in demo:
                cur.execute(
                    'INSERT INTO productos (id, nombre, precio, categoria, stock) '
                    'VALUES (%s, %s, %s, %s, %s)',
                    (id_producto, nombre, precio, categoria, stock)
                )
        conn.commit()
    finally:
        conn.close()
