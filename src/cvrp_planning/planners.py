"""Ejecución de planners (ENHSP y Fast Downward) como procesos externos.

Rutas por defecto: las que instalan los paquetes up-enhsp y up-fast-downward.
Se pueden sobrescribir con las variables de entorno ENHSP_JAR y FD_PY.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Configuraciones de cada planner. Agrega aquí las que quieras probar.
CONFIG_ENHSP = {
    "opt": ["-planner", "opt-hrmax"],   # A* con h_max numérico + restricciones redundantes (óptimo)
    "sat": ["-planner", "sat-hmrp"],    # GBFS con heurística MRP (satisficing)
    "blind": ["-planner", "opt-blind"], # A* ciego (óptimo, referencia de "sin heurística")
}
CONFIG_FD = {
    "opt": ["--search", "astar(lmcut())"],    # A* con LM-cut (óptimo)
    "sat": ["--alias", "lama-first"],         # LAMA, primer plan (satisficing)
    "blind": ["--search", "astar(blind())"],  # A* ciego (óptimo)
}


def ruta_enhsp() -> str:
    if os.environ.get("ENHSP_JAR"):
        return os.environ["ENHSP_JAR"]
    import up_enhsp
    return str(Path(up_enhsp.__file__).parent / "ENHSP" / "enhsp.jar")


def ruta_fd() -> str:
    if os.environ.get("FD_PY"):
        return os.environ["FD_PY"]
    import up_fast_downward
    return str(Path(up_fast_downward.__file__).parent / "downward" / "fast-downward.py")


def _ejecutar(cmd: list[str], timeout: float, cwd: str) -> tuple[str, float, bool]:
    t0 = time.perf_counter()
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        salida, agotado = p.stdout + p.stderr, False
    except subprocess.TimeoutExpired as e:
        salida = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        agotado = True
    return salida, time.perf_counter() - t0, agotado


def _ultimo_int(patron: str, texto: str) -> int | None:
    m = re.findall(patron, texto)
    return int(float(m[-1])) if m else None


def correr_enhsp(dominio: Path, problema: Path, config: str = "opt",
                 timeout: float = 60, memoria_gb: int = 4) -> dict:
    cmd = ["java", f"-Xmx{memoria_gb}g", "-jar", ruta_enhsp(),
           "-o", str(dominio), "-f", str(problema), *CONFIG_ENHSP[config]]
    with tempfile.TemporaryDirectory() as tmp:
        salida, tiempo, agotado = _ejecutar(cmd, timeout, tmp)
    res = {
        "tiempo": tiempo,
        "expandidos": _ultimo_int(r"Expanded Nodes:\s*(\d+)", salida),
        "acciones_ground": _ultimo_int(r"\|A\|:\s*(\d+)", salida),
        "costo_reportado": _ultimo_int(r"Metric \(Search\):\s*([\d.]+)", salida),
    }
    if agotado:
        return {**res, "estado": "timeout"}
    if "Problem Solved" not in salida:
        estado = "sin-memoria" if "OutOfMemory" in salida else ("sin-solucion" if "unsolvable" in salida.lower() else "error")
        return {**res, "estado": estado, "error": salida[-500:]}
    plan = re.findall(r"^\s*[\d.]+:\s*(\(.*\))", salida, flags=re.M)
    return {**res, "estado": "resuelto", "plan": plan}


def correr_fd(dominio: Path, problema: Path, config: str = "opt",
              timeout: float = 60, memoria_gb: int = 4) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        plan_file = Path(tmp) / "plan"
        conf = CONFIG_FD[config]
        # --alias va antes de los archivos; --search va después
        antes, despues = (conf, []) if conf[0] == "--alias" else ([], conf)
        cmd = [sys.executable, ruta_fd(), *antes,
               "--overall-time-limit", f"{int(timeout)}s",
               "--overall-memory-limit", f"{memoria_gb}G",
               "--plan-file", str(plan_file),
               str(dominio), str(problema), *despues]
        salida, tiempo, agotado = _ejecutar(cmd, timeout + 10, tmp)
        # lama-first puede escribir plan, plan.1, ...: tomamos el último
        planes = sorted(Path(tmp).glob("plan*"))
        plan_txt = planes[-1].read_text() if planes else ""
    res = {
        "tiempo": tiempo,
        "expandidos": _ultimo_int(r"Expanded (\d+) state", salida),
        "acciones_ground": _ultimo_int(r"(\d+) of \d+ operators necessary", salida),
        "costo_reportado": _ultimo_int(r"Plan cost:\s*(\d+)", salida),
    }
    plan = [l.strip() for l in plan_txt.splitlines() if l.strip().startswith("(")]
    if plan:
        return {**res, "estado": "resuelto", "plan": plan}
    if agotado or "Time limit" in salida or "timed out" in salida.lower():
        return {**res, "estado": "timeout"}
    if "Memory limit" in salida or "MemoryError" in salida:
        return {**res, "estado": "sin-memoria"}
    if "unsolvable" in salida.lower():
        return {**res, "estado": "sin-solucion"}
    return {**res, "estado": "error", "error": salida[-500:]}
