"""
Carrito de compras. Vive en la sesion de Flask mientras el usuario compra
(no se guarda en la BD hasta que confirma el pedido en /carrito/confirmar).

session['carrito'] = { 'p001': 2, 'p003': 1, ... }   # id_producto -> cantidad
"""

from flask import session
from integracion.productos_repo import obtener_producto


def _carrito_raw() -> dict:
    return session.setdefault('carrito', {})


def contar_items() -> int:
    """Total de unidades en el carrito (para el badge del navbar)."""
    return sum(_carrito_raw().values())


def agregar(id_producto: str, cantidad: int = 1):
    carrito = _carrito_raw()
    carrito[id_producto] = carrito.get(id_producto, 0) + cantidad
    session['carrito'] = carrito
    session.modified = True


def actualizar_cantidad(id_producto: str, cantidad: int):
    carrito = _carrito_raw()
    if cantidad <= 0:
        carrito.pop(id_producto, None)
    else:
        carrito[id_producto] = cantidad
    session['carrito'] = carrito
    session.modified = True


def eliminar(id_producto: str):
    carrito = _carrito_raw()
    carrito.pop(id_producto, None)
    session['carrito'] = carrito
    session.modified = True


def vaciar():
    session['carrito'] = {}
    session.modified = True


def obtener_items_enriquecidos() -> list:
    """
    Devuelve el carrito con los datos actuales del producto (precio, stock,
    categoria) traidos de la base de datos, mas el subtotal de cada linea.
    Si un producto ya no existe o fue desactivado, se omite (y se limpia
    del carrito) para no romper el checkout.
    """
    carrito = _carrito_raw()
    items = []
    cambio = False

    for id_producto, cantidad in list(carrito.items()):
        producto = obtener_producto(id_producto)
        if not producto or not producto['activo']:
            carrito.pop(id_producto, None)
            cambio = True
            continue
        items.append({
            'id_producto': id_producto,
            'nombre': producto['nombre'],
            'categoria': producto['categoria'],
            'precio': producto['precio'],
            'stock_disponible': producto['stock'],
            'cantidad': cantidad,
            'subtotal_linea': round(producto['precio'] * cantidad, 2),
        })

    if cambio:
        session['carrito'] = carrito
        session.modified = True

    return items
