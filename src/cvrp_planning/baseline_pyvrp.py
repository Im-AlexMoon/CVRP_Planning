"""Baseline de Investigación de Operaciones: PyVRP (HGS)."""
from __future__ import annotations

import time

from .instancias import Instancia


def resolver_pyvrp(inst: Instancia, flota: str, tiempo_max: float = 10.0,
                   semilla: int = 0) -> dict:
    from pyvrp import Model
    from pyvrp.stop import MaxRuntime

    m = Model()
    ubic = [m.add_location(x=x, y=y) for x, y in inst.coords]
    m.add_depot(ubic[0])
    for i in inst.clientes:
        m.add_client(ubic[i], delivery=[inst.demandas[i]], name=f"c{i}")
    k = inst.num_vehiculos if flota == "limitada" else inst.n
    m.add_vehicle_type(num_available=k, capacity=[inst.capacidad])
    for a in range(len(ubic)):
        for b in range(len(ubic)):
            if a != b:
                m.add_edge(ubic[a], ubic[b], distance=inst.dist[a][b])

    t0 = time.perf_counter()
    res = m.solve(MaxRuntime(tiempo_max), seed=semilla, display=False)
    tiempo = time.perf_counter() - t0
    if not res.is_feasible():
        return {"estado": "sin-solucion-factible", "tiempo": tiempo}

    datos = m.data()
    rutas = []
    for ruta in res.best.routes():
        clientes = []
        for act in ruta:
            if act.is_client():  # act.idx es el índice 0-based del cliente
                nombre = datos.client(act.idx).name
                clientes.append(int(nombre[1:]))
        if clientes:
            rutas.append(clientes)
    return {"estado": "resuelto", "costo": int(res.cost()), "rutas": rutas, "tiempo": tiempo}
