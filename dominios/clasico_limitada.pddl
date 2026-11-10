; CVRP con flota limitada, codificación CLÁSICA (sin fluents numéricos)
; para Fast Downward. La carga se representa con niveles discretos
; n0..nQ (objetos de tipo nivel), al estilo del dominio Transport de la IPC.
; El archivo de problema incluye los hechos estáticos
;   (resta ?c ?antes ?despues)  <=>  despues = antes - demanda(c), despues >= 0
; Los costos de acción son enteros: (distancia ?a ?b) es una función estática.

(define (domain cvrp-clasico-limitada)
  (:requirements :typing :action-costs)

  (:types
    vehiculo nodo nivel - object
    cliente deposito - nodo)

  (:predicates
    (en ?v - vehiculo ?n - nodo)
    (pendiente ?c - cliente)
    (servido ?c - cliente)
    (disponible ?v - vehiculo)
    (puede-salir ?v - vehiculo)
    (siguiente ?v ?w - vehiculo)
    (carga ?v - vehiculo ?n - nivel)
    (resta ?c - cliente ?antes ?despues - nivel))

  (:functions
    (distancia ?a ?b - nodo) - number
    (total-cost) - number)

  (:action salir
    :parameters (?v ?sig - vehiculo ?d - deposito ?c - cliente ?n1 ?n2 - nivel)
    :precondition (and (en ?v ?d) (disponible ?v) (puede-salir ?v)
                       (siguiente ?v ?sig) (pendiente ?c)
                       (carga ?v ?n1) (resta ?c ?n1 ?n2))
    :effect (and (not (en ?v ?d)) (en ?v ?c)
                 (not (disponible ?v)) (puede-salir ?sig)
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

  (:action regresar
    :parameters (?v - vehiculo ?desde - cliente ?d - deposito)
    :precondition (en ?v ?desde)
    :effect (and (not (en ?v ?desde)) (en ?v ?d)
                 (increase (total-cost) (distancia ?desde ?d))))
)
