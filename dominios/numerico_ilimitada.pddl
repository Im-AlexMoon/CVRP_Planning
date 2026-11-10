; CVRP con flota ilimitada de vehículos idénticos.
; Equivale a un solo vehículo que regresa al depósito y recarga (multi-viaje):
; con costo = distancia total y vehículos idénticos, ambos problemas tienen
; el mismo óptimo, y se elimina la simetría entre vehículos.
; Codificación numérica (PDDL 2.1) para ENHSP.

(define (domain cvrp-numerico-ilimitada)
  (:requirements :typing :numeric-fluents)

  (:types
    vehiculo nodo - object
    cliente deposito - nodo)

  (:predicates
    (en ?v - vehiculo ?n - nodo)
    (pendiente ?c - cliente)
    (servido ?c - cliente))

  (:functions
    (carga ?v - vehiculo)
    (capacidad)
    (demanda ?c - cliente)
    (distancia ?a ?b - nodo)
    (total-cost))

  (:action salir
    :parameters (?v - vehiculo ?d - deposito ?c - cliente)
    :precondition (and (en ?v ?d) (pendiente ?c)
                       (>= (carga ?v) (demanda ?c)))
    :effect (and (not (en ?v ?d)) (en ?v ?c)
                 (not (pendiente ?c)) (servido ?c)
                 (decrease (carga ?v) (demanda ?c))
                 (increase (total-cost) (distancia ?d ?c))))

  (:action visitar
    :parameters (?v - vehiculo ?desde ?c - cliente)
    :precondition (and (en ?v ?desde) (pendiente ?c)
                       (>= (carga ?v) (demanda ?c)))
    :effect (and (not (en ?v ?desde)) (en ?v ?c)
                 (not (pendiente ?c)) (servido ?c)
                 (decrease (carga ?v) (demanda ?c))
                 (increase (total-cost) (distancia ?desde ?c))))

  ; Regresa al depósito y recarga por completo.
  (:action regresar
    :parameters (?v - vehiculo ?desde - cliente ?d - deposito)
    :precondition (en ?v ?desde)
    :effect (and (not (en ?v ?desde)) (en ?v ?d)
                 (assign (carga ?v) (capacidad))
                 (increase (total-cost) (distancia ?desde ?d))))
)
