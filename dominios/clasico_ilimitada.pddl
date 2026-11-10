; CVRP con flota ilimitada (un vehículo multi-viaje), codificación CLÁSICA
; con niveles de carga, para Fast Downward. (lleno ?n) marca el nivel máximo Q.

(define (domain cvrp-clasico-ilimitada)
  (:requirements :typing :action-costs)

  (:types
    vehiculo nodo nivel - object
    cliente deposito - nodo)

  (:predicates
    (en ?v - vehiculo ?n - nodo)
    (pendiente ?c - cliente)
    (servido ?c - cliente)
    (carga ?v - vehiculo ?n - nivel)
    (lleno ?n - nivel)
    (resta ?c - cliente ?antes ?despues - nivel))

  (:functions
    (distancia ?a ?b - nodo) - number
    (total-cost) - number)

  (:action salir
    :parameters (?v - vehiculo ?d - deposito ?c - cliente ?n1 ?n2 - nivel)
    :precondition (and (en ?v ?d) (pendiente ?c)
                       (carga ?v ?n1) (resta ?c ?n1 ?n2))
    :effect (and (not (en ?v ?d)) (en ?v ?c)
                 (not (pendiente ?c)) (servido ?c)
                 (not (carga ?v ?n1)) (carga ?v ?n2)
                 (increase (total-cost) (distancia ?d ?c))))

  (:action visitar
    :parameters (?v - vehiculo ?desde ?c - cliente ?n1 ?n2 - nivel)
    :precondition (and (en ?v ?desde) (pendiente ?c)
                       (carga ?v ?n1) (resta ?c ?n1 ?n2))
    :effect (and (not (en ?v ?desde)) (en ?v ?c)
                 (not (pendiente ?c)) (servido ?c)
                 (not (carga ?v ?n1)) (carga ?v ?n2)
                 (increase (total-cost) (distancia ?desde ?c))))

  ; Regresa y recarga: pasa del nivel actual ?n al nivel lleno ?q.
  (:action regresar
    :parameters (?v - vehiculo ?desde - cliente ?d - deposito ?n ?q - nivel)
    :precondition (and (en ?v ?desde) (carga ?v ?n) (lleno ?q))
    :effect (and (not (en ?v ?desde)) (en ?v ?d)
                 (not (carga ?v ?n)) (carga ?v ?q)
                 (increase (total-cost) (distancia ?desde ?d))))
)
