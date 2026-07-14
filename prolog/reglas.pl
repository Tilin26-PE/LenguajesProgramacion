% Reglas de descuento por monto y categoria
% El catalogo de productos (precio, stock) ahora vive en la base de datos
% (Supabase), asi que esta regla ya no depende de los hechos producto/5:
% recibe la categoria directamente en vez de buscarla por Id.
% descuento(+Monto, +Categoria, -Porcentaje)
descuento(Monto, _,           0.15) :- Monto > 500, !.
descuento(Monto, _,           0.10) :- Monto > 100, !.
descuento(_,     electronica, 0.05) :- !.
descuento(_,     _,           0.0).

