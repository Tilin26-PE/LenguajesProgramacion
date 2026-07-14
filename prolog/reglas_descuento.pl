categoria(p001, electronica).
categoria(p002, ropa).

descuento(Monto, _, 0.10) :- Monto > 100, !.
descuento(_, Id, 0.05) :- categoria(Id, electronica), !.
descuento(_, _, 0.0).