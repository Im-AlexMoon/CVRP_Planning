"""Lectura, generación y representación de instancias CVRP.

Convención de distancias: TSPLIB/CVRPLib, es decir, distancia euclidiana
redondeada al entero más cercano (nint). Así los costos coinciden con los
mejores conocidos publicados en CVRPLib y son enteros, como exigen
Fast Downward y PyVRP.
"""
from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Instancia:
    nombre: str
    coords: list[tuple[float, float]]   # índice 0 = depósito
    demandas: list[int]                 # demandas[0] = 0 (depósito)
    capacidad: int
    num_vehiculos: int                  # K (solo aplica a flota limitada)
    mejor_conocido: int | None = None   # BKS, si se conoce
    dist: list[list[int]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.demandas[0] != 0:
            raise ValueError("La demanda del depósito (índice 0) debe ser 0.")
        if max(self.demandas) > self.capacidad:
            raise ValueError("Hay un cliente con demanda mayor que la capacidad.")
        self.dist = [[nint(math.dist(a, b)) for b in self.coords] for a in self.coords]

    @property
    def n(self) -> int:
        """Número de clientes (sin contar el depósito)."""
        return len(self.coords) - 1

    @property
    def clientes(self) -> range:
        return range(1, len(self.coords))

    def k_minimo(self) -> int:
        """Cota inferior trivial de vehículos: ceil(demanda total / Q)."""
        return math.ceil(sum(self.demandas) / self.capacidad)


def nint(x: float) -> int:
    """Redondeo TSPLIB: entero más cercano."""
    return int(x + 0.5)


# --------------------------------------------------------------------------- #
# Formato VRPLIB
# --------------------------------------------------------------------------- #
def leer_vrplib(ruta: str | Path, num_vehiculos: int | None = None,
                mejor_conocido: int | None = None) -> Instancia:
    """Lee un archivo .vrp (CVRPLib). Solo EUC_2D con un depósito.

    K se toma, en este orden, del argumento, de "No of trucks" en COMMENT,
    del sufijo -kN del nombre, o de ceil(demanda total / Q).
    """
    import vrplib

    ruta = Path(ruta)
    datos = vrplib.read_instance(str(ruta), compute_edge_weights=False)
    if datos.get("edge_weight_type", "EUC_2D") != "EUC_2D":
        raise ValueError("Solo se soportan instancias EUC_2D por ahora.")
    deposito = int(datos["depot"][0])
    if deposito != 0:
        raise ValueError("Se esperaba el depósito en el primer nodo.")

    coords = [tuple(map(float, xy)) for xy in datos["node_coord"]]
    demandas = [int(d) for d in datos["demand"]]
    nombre = str(datos.get("name", ruta.stem))

    if num_vehiculos is None:
        m = re.search(r"No of trucks:\s*(\d+)", str(datos.get("comment", "")))
        if m:
            num_vehiculos = int(m.group(1))
    if num_vehiculos is None:
        m = re.search(r"-k(\d+)", nombre)
        if m:
            num_vehiculos = int(m.group(1))
    if mejor_conocido is None:
        m = re.search(r"(?:Optimal|Best) value:\s*(\d+)", str(datos.get("comment", "")))
        if m:
            mejor_conocido = int(m.group(1))

    inst = Instancia(nombre, coords, demandas, int(datos["capacity"]), 0, mejor_conocido)
    inst.num_vehiculos = num_vehiculos or inst.k_minimo()
    return inst


def escribir_vrplib(inst: Instancia, ruta: str | Path) -> None:
    lineas = [
        f"NAME : {inst.nombre}",
        f"COMMENT : (generada por cvrp_planning, No of trucks: {inst.num_vehiculos})",
        "TYPE : CVRP",
        f"DIMENSION : {len(inst.coords)}",
        "EDGE_WEIGHT_TYPE : EUC_2D",
        f"CAPACITY : {inst.capacidad}",
        "NODE_COORD_SECTION",
        *[f"{i + 1} {x:g} {y:g}" for i, (x, y) in enumerate(inst.coords)],
        "DEMAND_SECTION",
        *[f"{i + 1} {d}" for i, d in enumerate(inst.demandas)],
        "DEPOT_SECTION",
        "1",
        "-1",
        "EOF",
    ]
    Path(ruta).write_text("\n".join(lineas) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# Instancias aleatorias (estilo Augerat serie A)
# --------------------------------------------------------------------------- #
def generar_aleatoria(n: int, semilla: int, capacidad: int = 50,
                      demanda_max: int = 20, holgura_k: int = 0,
                      lado: int = 100) -> Instancia:
    """Clientes y depósito uniformes en [0, lado]^2, demandas en [1, demanda_max].

    K = ceil(demanda total / Q) + holgura_k. Con holgura_k = 0 la instancia
    puede ser infactible si las demandas no "empacan" en K vehículos; el
    generador reintenta hasta encontrar una factible (comprobado por
    empacado first-fit decreasing, que es suficiente pero no necesario).
    """
    rng = random.Random(semilla)
    for _ in range(1000):
        coords = [(rng.randint(0, lado), rng.randint(0, lado)) for _ in range(n + 1)]
        demandas = [0] + [rng.randint(1, demanda_max) for _ in range(n)]
        k = math.ceil(sum(demandas) / capacidad) + holgura_k
        if _empaca_ffd(demandas[1:], capacidad, k):
            nombre = f"R-n{n + 1}-k{k}-s{semilla}"
            return Instancia(nombre, coords, demandas, capacidad, k)
    raise RuntimeError("No se encontró una instancia factible; sube holgura_k.")


def _empaca_ffd(demandas: list[int], capacidad: int, k: int) -> bool:
    cajas = [0] * k
    for d in sorted(demandas, reverse=True):
        for i in range(k):
            if cajas[i] + d <= capacidad:
                cajas[i] += d
                break
        else:
            return False
    return True
