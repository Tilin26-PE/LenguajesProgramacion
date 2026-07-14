package pedidocore.servicios

object ValidadorPedido {
  def validar(cantidad: Int): Boolean = cantidad > 0
}