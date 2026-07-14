package pedidocore

import pedidocore.servicios.{ValidadorPedido, ProcesadorPedidos}

// Entrada: id nombre precio cantidad stock descuento_pct
// Salida:  OK|id|nombre|cantidad|precio|subtotal|desc_pct|monto_desc|total
//          ERROR|mensaje
object Main {

  def main(args: Array[String]): Unit = {
    if (args.length < 6) {
      println("ERROR|Argumentos insuficientes")
      return
    }

    val idProducto   = args(0)
    val nombre       = args(1)
    val precio       = args(2).toDouble
    val cantidad     = args(3).toInt
    val stock        = args(4).toInt
    val descuentoPct = args(5).toDouble

    if (!ValidadorPedido.validar(cantidad)) {
      println("ERROR|Cantidad invalida")
      return
    }

    if (stock < cantidad) {
      println("ERROR|Stock insuficiente")
      return
    }

    val subtotal       = ProcesadorPedidos.calcularSubtotal(precio, cantidad)
    val totalFinal     = ProcesadorPedidos.aplicarDescuento(subtotal, descuentoPct)
    val montoDescuento = subtotal - totalFinal

    println(s"OK|$idProducto|$nombre|$cantidad|$precio|$subtotal|$descuentoPct|$montoDescuento|$totalFinal")
  }
}
