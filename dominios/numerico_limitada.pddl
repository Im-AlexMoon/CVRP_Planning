; CVRP con flota limitada (K vehículos, una ruta por vehículo).
; Codificación numérica (PDDL 2.1, fluents numéricos) para ENHSP.
;
; Cada acción de visita combina "mover" y "entregar": un vehículo solo se
; mueve a un cliente pendiente y lo atiende en el mismo paso. Así el espacio
; de soluciones coincide exactamente con el del CVRP de OR (no se puede pasar
; por clientes ya servidos ni repartir la demanda) y el plan mide la mitad.
;
; Rompimiento de simetría opcional, controlado desde el archivo de problema:
;   - sin rompimiento: todos los vehículos tienen (puede-salir ?v) y (siguiente ?v ?v)
;   - con rompimiento: solo v1 puede salir; al salir v_i habilita a v_{i+1}

(define (domain cvrp-numerico-limitada)
  (:requirements :typing :numeric-fluents)

  (:types
    vehiculo nodo - object
    cliente deposito - nodo)

  (:predicates
    (en ?v - vehiculo ?n - nodo)
    (pendiente ?c - cliente)
    (servido ?c - cliente)
    (disponible ?v - vehiculo)          ; el vehículo aún no ha salido
    (puede-salir ?v - vehiculo)
    (siguiente ?v ?w - vehiculo))

  (:functions
    (carga ?v - vehiculo)               ; carga restante a bordo
    (demanda ?c - cliente)
    (distancia ?a ?b - nodo)
    (total-cost))

  ; Primer cliente de la ruta: sale del depósito.
  (:action salir
    :parameters (?v ?sig - vehiculo ?d - deposito ?c - cliente)
    :precondition (and (en ?v ?d) (disponible ?v) (puede-salir ?v)
                       (siguiente ?v ?sig) (pendiente ?c)
                       (>= (carga ?v) (demanda ?c)))
    :effect (and (not (en ?v ?d)) (en ?v ?c)
                 (not (disponible ?v)) (puede-salir ?sig)
                 (not (pendiente ?c)) (servido ?c)
                 (decrease (carga ?v) (demanda ?c))
                 (increase (total-cost) (distancia ?d ?c))))

  ; Siguiente cliente de la ruta.
  (:action visitar
    :parameters (?v - vehiculo ?desde ?c - cliente)
    :precondition (and (en ?v ?desde) (pendiente ?c)
                       (>= (carga ?v) (demanda ?c)))
    :effect (and (not (en ?v ?desde)) (en ?v ?c)
                 (not (pendiente ?c)) (servido ?c)
                 (decrease (carga ?v) (demanda ?c))
                 (increase (total-cost) (distancia ?desde ?c))))

  ; Cierra la ruta. Como el vehículo ya no está "disponible", no vuelve a salir.
  (:action regresar
    :parameters (?v - vehiculo ?desde - cliente ?d - deposito)
    :precondition (en ?v ?desde)
    :effect (and (not (en ?v ?desde)) (en ?v ?d)
                 (increase (total-cost) (distancia ?desde ?d))))
)
