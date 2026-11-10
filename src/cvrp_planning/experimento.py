"""Línea de comandos: generar instancias y correr experimentos.

Ejemplos:
  python -m cvrp_planning.experimento generar --n 5 6 7 8 --semillas 3 --salida instancias/aleatorias
  python -m cvrp_planning.experimento correr --instancias instancias/aleatorias/*.vrp \\
      --metodos exacto pyvrp enhsp-opt fd-opt --timeout 60 --salida resultados/prueba.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import tempfile
from datetime import datetime
from pathlib import Path

from .baseline_pyvrp import resolver_pyvrp
from .exacto import resolver_exacto
from .generador_pddl import escribir_problema, ruta_dominio
from .instancias import escribir_vrplib, generar_aleatoria, leer_vrplib
from .planners import correr_enhsp, correr_fd
from .validar import validar_plan, validar_rutas

METODOS = ["exacto", "pyvrp", "enhsp-opt", "enhsp-sat", "enhsp-blind",
           "fd-opt", "fd-sat", "fd-blind"]
OPTIMOS = {"exacto", "enhsp-opt", "enhsp-blind", "fd-opt", "fd-blind"}

COLUMNAS = ["fecha", "instancia", "n", "K", "Q", "flota", "simetria", "metodo",
            "estado", "valido", "costo", "costo_reportado", "referencia",
            "tipo_referencia", "gap_pct", "tiempo_s", "expandidos",
            "acciones_ground", "rutas", "error"]


def correr_metodo(inst, metodo: str, flota: str, simetria: bool, timeout: float,
                  carpeta_pddl: Path, memoria_gb: int, tiempo_pyvrp: float = 5.0) -> dict:
    if metodo == "exacto":
        r = resolver_exacto(inst, flota)
    elif metodo == "pyvrp":
        r = resolver_pyvrp(inst, flota, tiempo_max=tiempo_pyvrp)
    else:
        planner, config = metodo.split("-")
        cod = "numerico" if planner == "enhsp" else "clasico"
        prob = escribir_problema(inst, cod, flota, carpeta_pddl, simetria)
        dom = ruta_dominio(cod, flota)
        correr = correr_enhsp if planner == "enhsp" else correr_fd
        r = correr(dom, prob, config, timeout, memoria_gb)

    if r.get("estado") != "resuelto":
        return r
    v = validar_plan(inst, r["plan"], flota) if "plan" in r else validar_rutas(inst, r["rutas"], flota)
    r.update(valido=v.valido, costo=v.costo, rutas=v.rutas)
    if not v.valido:
        r["error"] = v.error
    return r


def correr_experimento(rutas_inst: list[str], metodos: list[str], flotas: list[str],
                       simetria: bool, timeout: float, salida: Path,
                       carpeta_pddl: Path | None, memoria_gb: int,
                       tiempo_pyvrp: float = 5.0) -> None:
    salida.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not salida.exists()
    tmp = None
    if carpeta_pddl is None:
        tmp = tempfile.TemporaryDirectory()
        carpeta_pddl = Path(tmp.name)
    with salida.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS)
        if nuevo:
            w.writeheader()
        for ruta in rutas_inst:
            inst = leer_vrplib(ruta)
            for flota in flotas:
                filas = []
                for metodo in metodos:
                    print(f"[{inst.nombre}] flota={flota} {metodo} ...", end=" ", flush=True)
                    r = correr_metodo(inst, metodo, flota, simetria, timeout, carpeta_pddl, memoria_gb, tiempo_pyvrp)
                    print(r.get("estado"), r.get("costo", ""), f"{r.get('tiempo', 0):.2f}s")
                    filas.append((metodo, r))
                ref, tipo = _referencia(inst, filas)
                for metodo, r in filas:
                    costo = r.get("costo") if r.get("valido") else None
                    gap = round(100 * (costo - ref) / ref, 3) if costo is not None and ref else None
                    w.writerow({
                        "fecha": datetime.now().isoformat(timespec="seconds"),
                        "instancia": inst.nombre, "n": inst.n,
                        "K": inst.num_vehiculos if flota == "limitada" else "ilimitada",
                        "Q": inst.capacidad, "flota": flota,
                        "simetria": "si" if simetria and flota == "limitada" else "no",
                        "metodo": metodo, "estado": r.get("estado"),
                        "valido": r.get("valido", ""), "costo": costo,
                        "costo_reportado": r.get("costo_reportado", ""),
                        "referencia": ref, "tipo_referencia": tipo, "gap_pct": gap,
                        "tiempo_s": round(r.get("tiempo", 0), 3),
                        "expandidos": r.get("expandidos", ""),
                        "acciones_ground": r.get("acciones_ground", ""),
                        "rutas": json.dumps(r.get("rutas", [])) if r.get("rutas") else "",
                        "error": (r.get("error") or "")[:300].replace("\n", " "),
                    })
                f.flush()
    if tmp:
        tmp.cleanup()


def _referencia(inst, filas) -> tuple[int | None, str]:
    """Costo contra el que se mide el gap: óptimo exacto > BKS > mejor encontrado."""
    exacto = next((r for m, r in filas if m == "exacto" and r.get("valido")), None)
    if exacto:
        return exacto["costo"], "optimo-exacto"
    if inst.mejor_conocido:
        return inst.mejor_conocido, "bks"
    validos = [r["costo"] for _, r in filas if r.get("valido")]
    return (min(validos), "mejor-encontrado") if validos else (None, "")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="cvrp_planning.experimento")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generar", help="Genera instancias aleatorias en formato VRPLIB")
    g.add_argument("--n", type=int, nargs="+", required=True, help="Números de clientes")
    g.add_argument("--semillas", type=int, default=3, help="Instancias por tamaño")
    g.add_argument("--capacidad", type=int, default=50)
    g.add_argument("--demanda-max", type=int, default=20)
    g.add_argument("--holgura-k", type=int, default=0, help="Vehículos extra sobre ceil(D/Q)")
    g.add_argument("--salida", type=Path, default=Path("instancias/aleatorias"))

    c = sub.add_parser("correr", help="Corre métodos sobre instancias y guarda un CSV")
    c.add_argument("--instancias", nargs="+", required=True)
    c.add_argument("--metodos", nargs="+", default=["exacto", "pyvrp", "enhsp-opt", "fd-opt"],
                   choices=METODOS)
    c.add_argument("--flota", nargs="+", default=["limitada"], choices=["limitada", "ilimitada"])
    c.add_argument("--simetria", action="store_true", help="Rompimiento de simetría (flota limitada)")
    c.add_argument("--timeout", type=float, default=60, help="Segundos por corrida")
    c.add_argument("--memoria-gb", type=int, default=4)
    c.add_argument("--tiempo-pyvrp", type=float, default=5, help="Segundos que corre PyVRP")
    c.add_argument("--guardar-pddl", type=Path, default=None, help="Carpeta para conservar los PDDL")
    c.add_argument("--salida", type=Path, default=Path("resultados/resultados.csv"))

    a = p.parse_args(argv)
    if a.cmd == "generar":
        a.salida.mkdir(parents=True, exist_ok=True)
        for n in a.n:
            for s in range(1, a.semillas + 1):
                inst = generar_aleatoria(n, s, a.capacidad, a.demanda_max, a.holgura_k)
                ruta = a.salida / f"{inst.nombre}.vrp"
                escribir_vrplib(inst, ruta)
                print(ruta)
    else:
        correr_experimento(a.instancias, a.metodos, a.flota, a.simetria, a.timeout,
                           a.salida, a.guardar_pddl, a.memoria_gb, a.tiempo_pyvrp)


if __name__ == "__main__":
    main()
