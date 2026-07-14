package pedidocore.servicios

object ProcesadorPedidos {

  def calcularSubtotal(precio: Double, cantidad: Int): Double =
    precio * cantidad

  def aplicarDescuento(subtotal: Double, porcentaje: Double): Double =
    subtotal - (subtotal * porcentaje)
}
