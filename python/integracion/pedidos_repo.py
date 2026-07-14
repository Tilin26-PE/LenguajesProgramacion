"""Acceso a las tablas `pedidos` (cabecera) y `pedido_items` (lineas) en Supabase."""

from db import get_conn

_CAMPOS_NUMERICOS_ITEM = (
    'precio_unitario', 'subtotal', 'descuento_pct', 'monto_descuento', 'total_linea'
)
_CAMPOS_NUMERICOS_PEDIDO = ('subtotal', 'monto_descuento', 'total_final')

ESTADOS = ('pendiente', 'en_camino', 'entregado', 'cancelado')
# A que estados se puede avanzar un pedido segun su estado actual (evita
# saltos ilogicos como "entregado" -> "pendiente").
_TRANSICIONES_VALIDAS = {
    'pendiente':  {'en_camino', 'cancelado'},
    'en_camino':  {'entregado'},
    'entregado':  set(),
    'cancelado':  set(),
}


def _normalizar(fila: dict, campos: tuple) -> dict:
    """psycopg2 devuelve NUMERIC como Decimal; lo pasamos a float para que
    las comparaciones/formatos en los templates funcionen sin sorpresas."""
    for campo in campos:
        if campo in fila and fila[campo] is not None:
            fila[campo] = float(fila[campo])
    return fila


def confirmar_pedido(usuario_id: int, cliente: str, items: list) -> dict:
    """
    Confirma el checkout de un carrito completo en una sola transaccion:
    por cada item, bloquea el producto (FOR UPDATE), revalida que haya
    stock suficiente (por si cambio algo entre que se armo el carrito y
    se confirmo) y lo descuenta; recien si TODO el carrito es valido,
    inserta el pedido y sus lineas. Si un solo item falla, no se guarda
    ni se descuenta nada (rollback completo).

    `items` es una lista de dicts ya calculados (con descuento de Prolog
    y totales de Scala resueltos) con las llaves:
    id_producto, nombre_producto, categoria, cantidad, precio_unitario,
    subtotal, descuento_pct, monto_descuento, total_linea

    Devuelve {'ok': True, 'pedido_id': int} o {'ok': False, 'motivo': str}.
    """
    if not items:
        return {'ok': False, 'motivo': 'El carrito esta vacio.'}

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            for item in items:
                cur.execute(
                    'SELECT stock, activo FROM productos WHERE id = %s FOR UPDATE',
                    (item['id_producto'],)
                )
                producto = cur.fetchone()
                if not producto or not producto['activo']:
                    conn.rollback()
                    return {'ok': False, 'motivo': f'"{item["nombre_producto"]}" ya no esta disponible.'}
                if producto['stock'] < item['cantidad']:
                    conn.rollback()
                    return {
                        'ok': False,
                        'motivo': f'Stock insuficiente para "{item["nombre_producto"]}" '
                                  f'(disponible: {producto["stock"]}).'
                    }
                cur.execute(
                    'UPDATE productos SET stock = stock - %s WHERE id = %s',
                    (item['cantidad'], item['id_producto'])
                )

            subtotal        = sum(i['subtotal'] for i in items)
            monto_descuento  = sum(i['monto_descuento'] for i in items)
            total_final      = sum(i['total_linea'] for i in items)

            cur.execute(
                'INSERT INTO pedidos (usuario_id, cliente, subtotal, monto_descuento, total_final) '
                'VALUES (%s, %s, %s, %s, %s) RETURNING id',
                (usuario_id, cliente, subtotal, monto_descuento, total_final)
            )
            pedido_id = cur.fetchone()['id']

            for item in items:
                cur.execute(
                    """
                    INSERT INTO pedido_items (
                        pedido_id, id_producto, nombre_producto, categoria, cantidad,
                        precio_unitario, subtotal, descuento_pct, monto_descuento, total_linea
                    ) VALUES (
                        %(pedido_id)s, %(id_producto)s, %(nombre_producto)s, %(categoria)s, %(cantidad)s,
                        %(precio_unitario)s, %(subtotal)s, %(descuento_pct)s, %(monto_descuento)s, %(total_linea)s
                    )
                    """,
                    {**item, 'pedido_id': pedido_id}
                )

        conn.commit()
        return {'ok': True, 'pedido_id': pedido_id}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def obtener_pedido(pedido_id: int) -> dict | None:
    """Devuelve el pedido con sus items anidados en la llave 'items'."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM pedidos WHERE id = %s', (pedido_id,))
            pedido = cur.fetchone()
            if not pedido:
                return None
            cur.execute(
                'SELECT * FROM pedido_items WHERE pedido_id = %s ORDER BY id',
                (pedido_id,)
            )
            items = cur.fetchall()
    finally:
        conn.close()

    pedido = _normalizar(dict(pedido), _CAMPOS_NUMERICOS_PEDIDO)
    pedido['items'] = [_normalizar(dict(i), _CAMPOS_NUMERICOS_ITEM) for i in items]
    return pedido


def listar_pedidos_usuario(usuario_id: int) -> list:
    """Historial de un usuario normal: solo sus propios pedidos (cabeceras)."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.*, COUNT(i.id) AS num_items
                FROM pedidos p
                LEFT JOIN pedido_items i ON i.pedido_id = p.id
                WHERE p.usuario_id = %s
                GROUP BY p.id
                ORDER BY p.id DESC
            """, (usuario_id,))
            filas = cur.fetchall()
    finally:
        conn.close()
    return [_normalizar(dict(f), _CAMPOS_NUMERICOS_PEDIDO) for f in filas]


def listar_todos_los_pedidos() -> list:
    """Historial completo: solo para el admin."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.*, u.email AS usuario_email, COUNT(i.id) AS num_items
                FROM pedidos p
                LEFT JOIN usuarios u ON u.id = p.usuario_id
                LEFT JOIN pedido_items i ON i.pedido_id = p.id
                GROUP BY p.id, u.email
                ORDER BY p.id DESC
            """)
            filas = cur.fetchall()
    finally:
        conn.close()
    return [_normalizar(dict(f), _CAMPOS_NUMERICOS_PEDIDO) for f in filas]


def cambiar_estado(pedido_id: int, nuevo_estado: str) -> dict:
    """
    Avanza el estado de un pedido (pendiente -> en_camino -> entregado),
    validando que la transicion tenga sentido. Para cancelar se usa
    cancelar_pedido(), que ademas repone el stock.
    """
    if nuevo_estado not in ESTADOS:
        return {'ok': False, 'motivo': 'Estado invalido.'}

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT estado FROM pedidos WHERE id = %s FOR UPDATE', (pedido_id,))
            pedido = cur.fetchone()
            if not pedido:
                conn.rollback()
                return {'ok': False, 'motivo': 'Pedido no encontrado.'}

            actual = pedido['estado']
            if nuevo_estado not in _TRANSICIONES_VALIDAS.get(actual, set()):
                conn.rollback()
                return {'ok': False, 'motivo': f'No se puede pasar de "{actual}" a "{nuevo_estado}".'}

            cur.execute('UPDATE pedidos SET estado = %s WHERE id = %s', (nuevo_estado, pedido_id))
        conn.commit()
        return {'ok': True}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def cancelar_pedido(pedido_id: int, usuario_id, es_admin: bool) -> dict:
    """
    Cancela un pedido y repone el stock de cada item, todo en una sola
    transaccion. Solo se puede cancelar mientras esta 'pendiente' (una vez
    que el admin lo marco 'en_camino' ya no, para evitar inconsistencias
    con un envio que ya salio).

    Un cliente solo puede cancelar sus propios pedidos; el admin puede
    cancelar cualquiera.
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM pedidos WHERE id = %s FOR UPDATE', (pedido_id,))
            pedido = cur.fetchone()
            if not pedido:
                conn.rollback()
                return {'ok': False, 'motivo': 'Pedido no encontrado.'}

            if not es_admin and pedido['usuario_id'] != usuario_id:
                conn.rollback()
                return {'ok': False, 'motivo': 'No tienes permiso para cancelar este pedido.'}

            if pedido['estado'] != 'pendiente':
                conn.rollback()
                return {'ok': False, 'motivo': f'Ya no se puede cancelar (estado actual: {pedido["estado"]}).'}

            cur.execute('SELECT * FROM pedido_items WHERE pedido_id = %s', (pedido_id,))
            items = cur.fetchall()

            for item in items:
                cur.execute(
                    'UPDATE productos SET stock = stock + %s WHERE id = %s',
                    (item['cantidad'], item['id_producto'])
                )

            cur.execute("UPDATE pedidos SET estado = 'cancelado' WHERE id = %s", (pedido_id,))
        conn.commit()
        return {'ok': True}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()