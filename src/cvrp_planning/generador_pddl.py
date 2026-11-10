"""Traduce una Instancia a archivos de problema PDDL.

Codificaciones:
  - "numerico": fluents numéricos (PDDL 2.1) para ENHSP.
  - "clasico":  niveles de carga discretos para Fast Downward.
Flotas:
  - "limitada":   K vehículos, una ruta cada uno.
  - "ilimitada":  un vehículo multi-viaje (equivale a flota ilimitada).
"""
from __future__ import annotations

from pathlib import Path

from .instancias import Instancia

DOMINIOS = Path(__file__).resolve().parents[2] / "dominios"
CODIFICACIONES = ("numerico", "clasico")
FLOTAS = ("limitada", "ilimitada")


def ruta_dominio(codificacion: str, flota: str) -> Path:
    _checar(codificacion, flota)
    return DOMINIOS / f"{codificacion}_{flota}.pddl"


def _checar(codificacion: str, flota: str) -> None:
    if codificacion not in CODIFICACIONES:
        raise ValueError(f"Codificación desconocida: {codificacion}")
    if flota not in FLOTAS:
        raise ValueError(f"Flota desconocida: {flota}")


def nombre_nodo(i: int) -> str:
    return "d0" if i == 0 else f"c{i}"


def vehiculos(inst: Instancia, flota: str) -> list[str]:
    k = inst.num_vehiculos if flota == "limitada" else 1
    return [f"v{j}" for j in range(1, k + 1)]


def problema_pddl(inst: Instancia, codificacion: str, flota: str,
                  simetria: bool = False) -> str:
    """Devuelve el texto del archivo de problema.

    simetria=True activa el rompimiento de simetría entre vehículos
    (solo tiene efecto con flota limitada).
    """
    _checar(codificacion, flota)
    vs = vehiculos(inst, flota)
    clientes = [nombre_nodo(i) for i in inst.clientes]
    Q = inst.capacidad

    objetos = [f"    {' '.join(vs)} - vehiculo",
               f"    {' '.join(clientes)} - cliente",
               "    d0 - deposito"]
    if codificacion == "clasico":
        objetos.append("    " + " ".join(f"n{q}" for q in range(Q + 1)) + " - nivel")

    init: list[str] = []
    init += [f"(en {v} d0)" for v in vs]
    init += [f"(pendiente {c})" for c in clientes]

    if flota == "limitada":
        init += [f"(disponible {v})" for v in vs]
        if simetria:
            init.append(f"(puede-salir {vs[0]})")
            init += [f"(siguiente {a} {b})" for a, b in zip(vs, vs[1:])]
            init.append(f"(siguiente {vs[-1]} {vs[-1]})")
        else:
            init += [f"(puede-salir {v})" for v in vs]
            init += [f"(siguiente {v} {v})" for v in vs]

    if codificacion == "numerico":
        init += [f"(= (carga {v}) {Q})" for v in vs]
        if flota == "ilimitada":
            init.append(f"(= (capacidad) {Q})")
        init += [f"(= (demanda {nombre_nodo(i)}) {inst.demandas[i]})" for i in inst.clientes]
    else:
        init += [f"(carga {v} n{Q})" for v in vs]
        if flota == "ilimitada":
            init.append(f"(lleno n{Q})")
        for i in inst.clientes:
            d = inst.demandas[i]
            init += [f"(resta {nombre_nodo(i)} n{q} n{q - d})" for q in range(d, Q + 1)]

    nodos = range(len(inst.coords))
    init += [f"(= (distancia {nombre_nodo(a)} {nombre_nodo(b)}) {inst.dist[a][b]})"
             for a in nodos for b in nodos if a != b]
    init.append("(= (total-cost) 0)")

    meta = [f"(servido {c})" for c in clientes] + [f"(en {v} d0)" for v in vs]

    dominio = f"cvrp-{codificacion}-{flota}"
    return "\n".join([
        f"; Instancia {inst.nombre}: n={inst.n}, Q={Q}, K={len(vs)}, flota={flota}, "
        f"simetria={'si' if simetria else 'no'}",
        f"(define (problem {_limpio(inst.nombre)})",
        f"  (:domain {dominio})",
        "  (:objects",
        *objetos,
        "  )",
        "  (:init",
        *[f"    {h}" for h in init],
        "  )",
        "  (:goal (and",
        *[f"    {g}" for g in meta],
        "  ))",
        "  (:metric minimize (total-cost))",
        ")",
        "",
    ])


def escribir_problema(inst: Instancia, codificacion: str, flota: str,
                      carpeta: str | Path, simetria: bool = False) -> Path:
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    sufijo = "_sim" if simetria and flota == "limitada" else ""
    ruta = carpeta / f"{_limpio(inst.nombre)}_{codificacion}_{flota}{sufijo}.pddl"
    ruta.write_text(problema_pddl(inst, codificacion, flota, simetria), encoding="utf-8")
    return ruta


def _limpio(nombre: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in nombre)
