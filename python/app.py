import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, redirect, url_for, session, flash

from integracion.prolog_bridge import obtener_descuento
from integracion.scala_bridge import procesar_pedido
from integracion.usuarios_repo import crear_usuario, autenticar
from integracion.pedidos_repo import confirmar_pedido, obtener_pedido, listar_pedidos_usuario, listar_todos_los_pedidos
from integracion.productos_repo import (
    listar_productos, obtener_producto, crear_producto, actualizar_producto,
    desactivar_producto, reactivar_producto, seed_productos_demo,
)
from integracion import carrito as carrito_srv
from auth import login_required, admin_required
from db import init_db, seed_usuarios_demo

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'pedidocore2024')

# Crea las tablas (si no existen) y los datos de prueba al arrancar.
with app.app_context():
    init_db()
    seed_usuarios_demo()
    seed_productos_demo()


@app.context_processor
def inyectar_carrito():
    """Disponible en todos los templates para mostrar el contador del navbar."""
    if session.get('usuario_id'):
        return {'carrito_items': carrito_srv.contar_items()}
    return {'carrito_items': 0}


# ---------- Autenticacion ----------

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'GET':
        return render_template('registro.html', errores=[])

    nombre    = request.form.get('nombre', '').strip()
    email     = request.form.get('email', '').strip().lower()
    password  = request.form.get('password', '')
    password2 = request.form.get('password2', '')

    errores = []
    if not nombre:
        errores.append('El nombre es obligatorio.')
    if not email or '@' not in email:
        errores.append('Ingresa un correo valido.')
    if len(password) < 6:
        errores.append('La contrasena debe tener al menos 6 caracteres.')
    if password != password2:
        errores.append('Las contrasenas no coinciden.')

    if errores:
        return render_template('registro.html', errores=errores)

    usuario = crear_usuario(nombre, email, password, rol='cliente')
    if not usuario:
        return render_template('registro.html', errores=['Ese correo ya esta registrado.'])

    session['usuario_id'] = usuario['id']
    session['nombre']     = usuario['nombre']
    session['rol']        = usuario['rol']
    flash(f'Bienvenido, {usuario["nombre"]}! Tu cuenta fue creada.', 'success')
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', error=None)

    email    = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')

    usuario = autenticar(email, password)
    if not usuario:
        return render_template('login.html', error='Correo o contrasena incorrectos.')

    session['usuario_id'] = usuario['id']
    session['nombre']     = usuario['nombre']
    session['rol']        = usuario['rol']
    flash(f'Hola de nuevo, {usuario["nombre"]}!', 'success')
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.clear()
    flash('Sesion cerrada.', 'info')
    return redirect(url_for('login'))


# ---------- Catalogo ----------

@app.route('/')
@login_required
def index():
    productos = listar_productos()
    q = request.args.get('q', '').strip()
    if q:
        productos = [p for p in productos if q.lower() in p['nombre'].lower()]
    return render_template('index.html', productos=productos, q=q)


# ---------- Carrito ----------

@app.route('/carrito')
@login_required
def ver_carrito():
    items = carrito_srv.obtener_items_enriquecidos()
    total = round(sum(i['subtotal_linea'] for i in items), 2)
    return render_template('carrito.html', items=items, total=total)


@app.route('/carrito/agregar', methods=['POST'])
@login_required
def carrito_agregar():
    id_producto = request.form.get('producto', '').strip()
    try:
        cantidad = int(request.form.get('cantidad', '1'))
    except ValueError:
        cantidad = 1
    cantidad = max(cantidad, 1)

    producto = obtener_producto(id_producto)
    if not producto or not producto['activo']:
        flash('Ese producto ya no esta disponible.', 'danger')
        return redirect(request.referrer or url_for('index'))

    carrito_srv.agregar(id_producto, cantidad)
    flash(f'"{producto["nombre"]}" se agrego al carrito.', 'success')
    return redirect(request.referrer or url_for('index'))


@app.route('/carrito/actualizar', methods=['POST'])
@login_required
def carrito_actualizar():
    id_producto = request.form.get('producto', '').strip()
    try:
        cantidad = int(request.form.get('cantidad', '0'))
    except ValueError:
        cantidad = 0
    carrito_srv.actualizar_cantidad(id_producto, cantidad)
    return redirect(url_for('ver_carrito'))


@app.route('/carrito/eliminar/<id_producto>', methods=['POST'])
@login_required
def carrito_eliminar(id_producto):
    carrito_srv.eliminar(id_producto)
    return redirect(url_for('ver_carrito'))


@app.route('/carrito/confirmar', methods=['POST'])
@login_required
def carrito_confirmar():
    cliente = request.form.get('cliente', '').strip()
    if not cliente:
        flash('Ingresa el nombre del cliente para confirmar el pedido.', 'danger')
        return redirect(url_for('ver_carrito'))

    items_carrito = carrito_srv.obtener_items_enriquecidos()
    if not items_carrito:
        flash('Tu carrito esta vacio.', 'warning')
        return redirect(url_for('index'))

    items_calculados = []
    for item in items_carrito:
        if item['cantidad'] > item['stock_disponible']:
            flash(f'Stock insuficiente para "{item["nombre"]}" '
                  f'(disponible: {item["stock_disponible"]}).', 'danger')
            return redirect(url_for('ver_carrito'))

        # Prolog: descuento segun monto de la linea y categoria
        subtotal_previo = item['precio'] * item['cantidad']
        descuento_pct = obtener_descuento(subtotal_previo, item['categoria'])

        # Scala: calculo final de la linea (subtotal, descuento, total)
        resultado = procesar_pedido(
            item['id_producto'], item['nombre'], item['precio'],
            item['cantidad'], item['stock_disponible'], descuento_pct,
        )
        if resultado.startswith('ERROR|'):
            msg = resultado.split('|')[1] if '|' in resultado else 'Error al procesar el pedido.'
            flash(f'{item["nombre"]}: {msg}', 'danger')
            return redirect(url_for('ver_carrito'))

        # OK|id|nombre|cantidad|precio|subtotal|desc_pct|monto_desc|total
        p = resultado.split('|')
        items_calculados.append({
            'id_producto':     p[1],
            'nombre_producto': p[2],
            'categoria':       item['categoria'],
            'cantidad':        int(p[3]),
            'precio_unitario': float(p[4]),
            'subtotal':        float(p[5]),
            'descuento_pct':   float(p[6]),
            'monto_descuento': float(p[7]),
            'total_linea':     float(p[8]),
        })

    # Checkout atomico: valida stock de nuevo y descuenta todo junto, o nada.
    resultado = confirmar_pedido(session['usuario_id'], cliente, items_calculados)
    if not resultado['ok']:
        flash(resultado['motivo'], 'danger')
        return redirect(url_for('ver_carrito'))

    carrito_srv.vaciar()
    flash('Pedido confirmado!', 'success')
    return redirect(url_for('resultado', pedido_id=resultado['pedido_id']))


# ---------- Pedidos ----------

@app.route('/resultado/<int:pedido_id>')
@login_required
def resultado(pedido_id):
    pedido = obtener_pedido(pedido_id)
    if not pedido:
        return redirect(url_for('index'))
    if session.get('rol') != 'admin' and pedido['usuario_id'] != session['usuario_id']:
        flash('No tienes acceso a ese pedido.', 'danger')
        return redirect(url_for('historial'))
    return render_template('resultado.html', pedido=pedido)


@app.route('/historial')
@login_required
def historial():
    pedidos = listar_pedidos_usuario(session['usuario_id'])
    return render_template('historial.html', pedidos=pedidos)


# ---------- Panel de administrador ----------

@app.route('/admin')
@admin_required
def admin_panel():
    pedidos = listar_todos_los_pedidos()
    return render_template('admin.html', pedidos=pedidos)


@app.route('/admin/productos')
@admin_required
def admin_productos():
    productos = listar_productos(solo_activos=False)
    return render_template('admin_productos.html', productos=productos)


@app.route('/admin/productos/nuevo', methods=['GET', 'POST'])
@admin_required
def admin_producto_nuevo():
    if request.method == 'GET':
        return render_template('admin_producto_form.html', producto=None, errores=[])

    errores = _validar_form_producto(request.form)
    if errores:
        return render_template('admin_producto_form.html', producto=request.form, errores=errores)

    nuevo = crear_producto(
        request.form['id'].strip(),
        request.form['nombre'].strip(),
        float(request.form['precio']),
        request.form['categoria'].strip(),
        int(request.form['stock']),
    )
    if not nuevo:
        errores = [f'Ya existe un producto con el id "{request.form["id"]}".']
        return render_template('admin_producto_form.html', producto=request.form, errores=errores)

    flash(f'Producto "{nuevo["nombre"]}" creado.', 'success')
    return redirect(url_for('admin_productos'))


@app.route('/admin/productos/<id_producto>/editar', methods=['GET', 'POST'])
@admin_required
def admin_producto_editar(id_producto):
    producto = obtener_producto(id_producto)
    if not producto:
        flash('Producto no encontrado.', 'danger')
        return redirect(url_for('admin_productos'))

    if request.method == 'GET':
        return render_template('admin_producto_form.html', producto=producto, errores=[])

    errores = _validar_form_producto(request.form, es_edicion=True)
    if errores:
        return render_template('admin_producto_form.html', producto=producto, errores=errores)

    actualizar_producto(
        id_producto,
        request.form['nombre'].strip(),
        float(request.form['precio']),
        request.form['categoria'].strip(),
        int(request.form['stock']),
    )
    flash('Producto actualizado.', 'success')
    return redirect(url_for('admin_productos'))


@app.route('/admin/productos/<id_producto>/desactivar', methods=['POST'])
@admin_required
def admin_producto_desactivar(id_producto):
    desactivar_producto(id_producto)
    flash('Producto desactivado (ya no aparece en el catalogo).', 'info')
    return redirect(url_for('admin_productos'))


@app.route('/admin/productos/<id_producto>/activar', methods=['POST'])
@admin_required
def admin_producto_activar(id_producto):
    reactivar_producto(id_producto)
    flash('Producto reactivado.', 'success')
    return redirect(url_for('admin_productos'))


def _validar_form_producto(form, es_edicion: bool = False) -> list:
    errores = []
    if not es_edicion and not form.get('id', '').strip():
        errores.append('El id del producto es obligatorio (ej: p006).')
    if not form.get('nombre', '').strip():
        errores.append('El nombre es obligatorio.')
    if not form.get('categoria', '').strip():
        errores.append('La categoria es obligatoria.')
    try:
        if float(form.get('precio', -1)) <= 0:
            errores.append('El precio debe ser mayor a 0.')
    except ValueError:
        errores.append('El precio debe ser un numero.')
    try:
        if int(form.get('stock', -1)) < 0:
            errores.append('El stock no puede ser negativo.')
    except ValueError:
        errores.append('El stock debe ser un numero entero.')
    return errores


if __name__ == '__main__':
    app.run(debug=True, port=5000)
