"""Validación independiente de soluciones.

No confiamos en el costo que reporta cada método: reconstruimos las rutas,
revisamos factibilidad y recalculamos el costo con la matriz de la instancia.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .instancias import Instancia


@dataclass
class Validacion:
    valido: bool
    costo: int | None
    rutas: list[list[int]]
    error: str = ""


def _nodo(nombre: str) -> int:
    if nombre == "d0":
        return 0
    m = re.fullmatch(r"c(\d+)", nombre)
    if not m:
        raise ValueError(f"Nodo inesperado: {nombre}")
    return int(m.group(1))


def plan_a_rutas(plan: list[str]) -> list[list[int]]:
    """Convierte un plan PDDL (salir / visitar / regresar) en rutas de clientes.

    Funciona con ambas codificaciones y ambas flotas: un vehículo multi-viaje
    produce una ruta por cada viaje.
    """
    abiertas: dict[str, list[int]] = {}
    rutas: list[list[int]] = []
    for paso in plan:
        partes = paso.strip().strip("()").lower().split()
        accion, args = partes[0], partes[1:]
        v = args[0]
        if accion == "salir":
            if v in abiertas:
                raise ValueError(f"{v} sale sin haber regresado")
            cliente = next(a for a in args[1:] if re.fullmatch(r"c\d+", a))
            abiertas[v] = [_nodo(cliente)]
        elif accion == "visitar":
            if v not in abiertas or abiertas[v][-1] != _nodo(args[1]):
                raise ValueError(f"'{paso}' no continúa la ruta de {v}")
            abiertas[v].append(_nodo(args[2]))
        elif accion == "regresar":
            if v not in abiertas or abiertas[v][-1] != _nodo(args[1]):
                raise ValueError(f"'{paso}' no cierra la ruta de {v}")
            rutas.append(abiertas.pop(v))
        else:
            raise ValueError(f"Acción desconocida: {accion}")
    if abiertas:
        raise ValueError(f"Vehículos sin regresar al depósito: {sorted(abiertas)}")
    return rutas


def validar_rutas(inst: Instancia, rutas: list[list[int]], flota: str) -> Validacion:
    try:
        visitados = [c for r in rutas for c in r]
        faltan = set(inst.clientes) - set(visitados)
        if faltan:
            raise ValueError(f"Clientes sin servir: {sorted(faltan)}")
        if len(visitados) != len(set(visitados)):
            raise ValueError("Algún cliente se visitó más de una vez")
        for r in rutas:
            carga = sum(inst.demandas[c] for c in r)
            if carga > inst.capacidad:
                raise ValueError(f"Ruta {r} excede la capacidad ({carga} > {inst.capacidad})")
        if flota == "limitada" and len(rutas) > inst.num_vehiculos:
            raise ValueError(f"Usa {len(rutas)} rutas y solo hay K={inst.num_vehiculos}")
    except ValueError as e:
        return Validacion(False, None, rutas, str(e))
    return Validacion(True, costo_rutas(inst, rutas), rutas)


def validar_plan(inst: Instancia, plan: list[str], flota: str) -> Validacion:
    try:
        rutas = plan_a_rutas(plan)
    except (ValueError, StopIteration, IndexError) as e:
        return Validacion(False, None, [], f"Plan mal formado: {e}")
    return validar_rutas(inst, rutas, flota)


def costo_rutas(inst: Instancia, rutas: list[list[int]]) -> int:
    total = 0
    for r in rutas:
        camino = [0, *r, 0]
        total += sum(inst.dist[a][b] for a, b in zip(camino, camino[1:]))
    return total
