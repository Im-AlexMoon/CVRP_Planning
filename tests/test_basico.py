"""Pruebas mínimas. Correr con:  pytest -q"""
import itertools
import shutil

import pytest

from cvrp_planning.exacto import resolver_exacto
from cvrp_planning.experimento import correr_metodo
from cvrp_planning.generador_pddl import problema_pddl
from cvrp_planning.instancias import Instancia, generar_aleatoria
from cvrp_planning.validar import costo_rutas, validar_plan


def fuerza_bruta(inst, flota):
    """Óptimo por enumeración de permutaciones + cortes (solo n <= 6)."""
    mejor = None
    clientes = list(inst.clientes)
    for perm in itertools.permutations(clientes):
        for cortes in itertools.product([0, 1], repeat=len(perm) - 1):
            rutas, actual = [], [perm[0]]
            for c, corte in zip(perm[1:], cortes):
                if corte:
                    rutas.append(actual)
                    actual = []
                actual.append(c)
            rutas.append(actual)
            if any(sum(inst.demandas[c] for c in r) > inst.capacidad for r in rutas):
                continue
            if flota == "limitada" and len(rutas) > inst.num_vehiculos:
                continue
            costo = costo_rutas(inst, rutas)
            mejor = costo if mejor is None else min(mejor, costo)
    return mejor


@pytest.mark.parametrize("semilla", [1, 2, 3])
@pytest.mark.parametrize("flota", ["limitada", "ilimitada"])
def test_exacto_igual_a_fuerza_bruta(semilla, flota):
    inst = generar_aleatoria(5, semilla, capacidad=30, demanda_max=15)
    r = resolver_exacto(inst, flota)
    assert r["costo"] == fuerza_bruta(inst, flota)
    assert costo_rutas(inst, r["rutas"]) == r["costo"]


def test_flota_limitada_puede_costar_mas():
    # 4 clientes en las esquinas, demanda 1, Q=4: con K=1 hay que hacer un solo tour.
    inst = Instancia("cuadro", [(0, 0), (10, 0), (0, 10), (-10, 0), (0, -10)],
                     [0, 1, 1, 1, 1], capacidad=4, num_vehiculos=1)
    assert resolver_exacto(inst, "limitada")["costo"] >= resolver_exacto(inst, "ilimitada")["costo"]


def test_validador_detecta_errores():
    inst = generar_aleatoria(3, 1, capacidad=100, demanda_max=10)
    bueno = ["(salir v1 v1 d0 c1)", "(visitar v1 c1 c2)", "(visitar v1 c2 c3)", "(regresar v1 c3 d0)"]
    assert validar_plan(inst, bueno, "limitada").valido
    falta = bueno[:2] + ["(regresar v1 c2 d0)"]
    assert not validar_plan(inst, falta, "limitada").valido
    salto = ["(salir v1 v1 d0 c1)", "(visitar v1 c3 c2)", "(regresar v1 c2 d0)"]
    assert not validar_plan(inst, salto, "limitada").valido


def test_generador_niveles_de_carga():
    inst = generar_aleatoria(4, 1, capacidad=20, demanda_max=8)
    txt = problema_pddl(inst, "clasico", "limitada")
    esperado = sum(inst.capacidad - inst.demandas[c] + 1 for c in inst.clientes)
    assert txt.count("(resta ") == esperado


@pytest.mark.skipif(shutil.which("java") is None, reason="ENHSP requiere Java")
@pytest.mark.parametrize("flota", ["limitada", "ilimitada"])
def test_planners_optimos_coinciden_con_exacto(tmp_path, flota):
    inst = generar_aleatoria(5, 2)
    exacto = resolver_exacto(inst, flota)["costo"]
    for metodo in ["enhsp-opt", "fd-opt"]:
        r = correr_metodo(inst, metodo, flota, False, 60, tmp_path, 2)
        assert r["estado"] == "resuelto", r
        assert r["valido"], r.get("error")
        assert r["costo"] == exacto, metodo
