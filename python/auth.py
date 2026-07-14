"""Decoradores para proteger rutas segun sesion / rol."""

from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if not session.get('usuario_id'):
            flash('Debes iniciar sesion para continuar.', 'warning')
            return redirect(url_for('login'))
        return vista(*args, **kwargs)
    return envoltura


def admin_required(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if not session.get('usuario_id'):
            flash('Debes iniciar sesion para continuar.', 'warning')
            return redirect(url_for('login'))
        if session.get('rol') != 'admin':
            flash('No tienes permisos de administrador.', 'danger')
            return redirect(url_for('index'))
        return vista(*args, **kwargs)
    return envoltura
