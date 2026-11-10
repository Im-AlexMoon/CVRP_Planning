"""Solver exacto para instancias chicas (n <= 12): verdad de referencia.

1. Held-Karp: costo mínimo de una ruta que visita exactamente el conjunto S
   (si su demanda cabe en Q).
2. Partición de conjuntos por programación dinámica: cubrir todos los clientes
   con a lo sumo K rutas (flota limitada) o con cualquier número (ilimitada).
Complejidad aproximada O(2^n n^2 + K 3^n).
"""
from __future__ import annotations

import time

from .instancias import Instancia

INF = float("inf")
N_MAX = 12


def resolver_exacto(inst: Instancia, flota: str) -> dict:
    n = inst.n
    if n > N_MAX:
        return {"estado": "no-aplica", "error": f"n={n} > {N_MAX}"}
    t0 = time.perf_counter()
    d, q, Q = inst.dist, inst.demandas, inst.capacidad
    total = 1 << n

    demanda = [0] * total
    for S in range(1, total):
        b = (S & -S).bit_length() - 1
        demanda[S] = demanda[S & (S - 1)] + q[b + 1]

    # dp[S][j]: depósito -> todos los de S -> termina en el cliente j (en S)
    dp = [[INF] * n for _ in range(total)]
    padre = [[-1] * n for _ in range(total)]
    for j in range(n):
        if q[j + 1] <= Q:
            dp[1 << j][j] = d[0][j + 1]
    for S in range(1, total):
        if demanda[S] > Q:
            continue
        fila = dp[S]
        for j in range(n):
            cj = fila[j]
            if cj == INF:
                continue
            for k in range(n):
                if S >> k & 1:
                    continue
                T = S | 1 << k
                if demanda[T] > Q:
                    continue
                c = cj + d[j + 1][k + 1]
                if c < dp[T][k]:
                    dp[T][k] = c
                    padre[T][k] = j

    ruta_costo = [INF] * total
    ruta_fin = [-1] * total
    for S in range(1, total):
        if demanda[S] <= Q:
            for j in range(n):
                c = dp[S][j] + d[j + 1][0]
                if c < ruta_costo[S]:
                    ruta_costo[S], ruta_fin[S] = c, j

    kmax = inst.num_vehiculos if flota == "limitada" else n
    lleno = total - 1
    # g[S] con a lo sumo k rutas, iterando k (se guarda la elección por nivel)
    g = [INF] * total
    g[0] = 0
    elecciones = []
    mejor, mejor_k = INF, 0
    for k in range(1, kmax + 1):
        ng = [INF] * total
        ng[0] = 0
        eleccion = [0] * total
        for S in range(1, total):
            bajo = S & -S
            resto = S ^ bajo
            T = resto
            while True:  # subconjuntos que contienen al bit más bajo de S
                R = T | bajo
                c = ruta_costo[R] + g[S ^ R]
                if c < ng[S]:
                    ng[S], eleccion[S] = c, R
                if T == 0:
                    break
                T = (T - 1) & resto
        g = ng
        elecciones.append(eleccion)
        if g[lleno] < mejor:
            mejor, mejor_k = g[lleno], k

    tiempo = time.perf_counter() - t0
    if mejor == INF:
        return {"estado": "infactible", "tiempo": tiempo}

    rutas, S = [], lleno
    for k in range(mejor_k, 0, -1):
        if S == 0:
            break
        R = elecciones[k - 1][S]
        rutas.append(_reconstruir(R, ruta_fin[R], padre))
        S ^= R
    return {"estado": "resuelto", "costo": int(mejor), "rutas": rutas, "tiempo": tiempo}


def _reconstruir(S: int, j: int, padre: list[list[int]]) -> list[int]:
    ruta = []
    while j != -1:
        ruta.append(j + 1)
        S, j = S ^ (1 << j), padre[S][j]
    return ruta[::-1]
