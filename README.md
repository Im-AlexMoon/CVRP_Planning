# CVRP con planning automatizado

Experimento base del proyecto: resolver el CVRP con planners independientes del
dominio (ENHSP y Fast Downward) y compararlos contra un solver de Investigación
de Operaciones (PyVRP) y contra un solver exacto, midiendo dónde y por qué
dejan de escalar.

## Estructura

```
dominios/                     Dominios PDDL (estáticos)
  numerico_limitada.pddl      Fluents numéricos, K vehículos      -> ENHSP
  numerico_ilimitada.pddl     Fluents numéricos, flota ilimitada  -> ENHSP
  clasico_limitada.pddl       Niveles de carga discretos, K vehículos     -> Fast Downward
  clasico_ilimitada.pddl      Niveles de carga discretos, flota ilimitada -> Fast Downward
src/cvrp_planning/
  instancias.py               Lectura/escritura VRPLIB, generador aleatorio, matriz de distancias
  generador_pddl.py           Instancia -> archivo de problema PDDL
  planners.py                 Ejecuta ENHSP y Fast Downward (configuraciones en CONFIG_*)
  baseline_pyvrp.py           Baseline de OR (PyVRP / HGS)
  exacto.py                   Óptimo exacto para n <= 12 (Held-Karp + partición)
  validar.py                  Valida cada solución y recalcula su costo de forma independiente
  experimento.py              Línea de comandos: generar instancias y correr experimentos
tests/                        Pruebas (pytest)
instancias/                   Instancias generadas (hito y escalamiento)
resultados/                   CSV de resultados
```

## Instalación

Requisitos: Python 3.10 o superior y Java 17 o superior (para ENHSP).

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q                          # 11 pruebas; debe tardar unos segundos
```

`up-enhsp` trae el `.jar` de ENHSP y `up-fast-downward` trae Fast Downward
compilado. Si quieres usar otra versión, define las variables de entorno
`ENHSP_JAR` y `FD_PY` con sus rutas. Lo probé en Linux; si en Windows falla
Fast Downward, usa WSL.

## Uso

Generar instancias aleatorias (estilo Augerat; por defecto Q=50, demandas 1–20,
K = ceil(demanda total / Q)). El nombre sigue la convención de CVRPLib:
`R-n6-k2-s1` tiene 6 nodos (5 clientes + depósito), K=2, semilla 1.

```bash
python -m cvrp_planning.experimento generar --n 5 6 7 8 --semillas 3 --salida instancias/aleatorias
```

Correr métodos y guardar resultados:

```bash
python -m cvrp_planning.experimento correr \
    --instancias instancias/aleatorias/*.vrp \
    --metodos exacto pyvrp enhsp-opt enhsp-sat fd-opt fd-sat \
    --flota limitada \
    --timeout 60 \
    --salida resultados/mi_experimento.csv
```

Opciones útiles:

| Opción | Qué hace |
|---|---|
| `--flota limitada ilimitada` | Corre ambas variantes de flota |
| `--simetria` | Activa el rompimiento de simetría entre vehículos (flota limitada) |
| `--guardar-pddl carpeta/` | Conserva los archivos de problema PDDL generados |
| `--tiempo-pyvrp 5` | Segundos que corre PyVRP |
| `--memoria-gb 4` | Memoria máxima para cada planner |

Métodos disponibles: `exacto`, `pyvrp`, `enhsp-opt`, `enhsp-sat`, `enhsp-blind`,
`fd-opt`, `fd-sat`, `fd-blind`. Las configuraciones están en `planners.py`:

| Método | Configuración | Tipo |
|---|---|---|
| `enhsp-opt` | A* con h_max numérico + restricciones redundantes (`opt-hrmax`) | Óptimo |
| `enhsp-sat` | GBFS con heurística MRP (`sat-hmrp`) | Satisficing |
| `fd-opt` | A* con LM-cut | Óptimo |
| `fd-sat` | LAMA, primer plan (`lama-first`) | Satisficing |
| `*-blind` | A* sin heurística | Óptimo (referencia) |

Instancias de CVRPLib: descárgalas desde la página de CVRPLib (serie A de
Augerat, por ejemplo `A-n32-k5.vrp`) y pásalas con `--instancias`. Si el
archivo trae el valor óptimo en COMMENT, se usa como referencia para el gap.

### Columnas del CSV

`estado` (resuelto, timeout, sin-memoria, error), `valido` (la solución pasó la
validación independiente), `costo` (recalculado por el validador, no el que
reporta el método), `referencia` y `tipo_referencia` (óptimo exacto > BKS >
mejor encontrado), `gap_pct`, `tiempo_s`, `expandidos` (nodos expandidos por el
planner), `acciones_ground` (acciones instanciadas), `rutas` (JSON).

## Decisiones de modelado

1. **Visitar = mover + entregar.** Un vehículo solo se mueve a un cliente
   pendiente y lo atiende en el mismo paso. Así el espacio de soluciones es
   exactamente el del CVRP de OR (no se pasa por clientes ya servidos y no se
   divide la demanda), y el plan mide la mitad que con acciones separadas.
2. **Flota limitada.** K vehículos, cada uno sale una sola vez (`disponible`) y
   debe regresar al depósito. No hay recarga.
3. **Flota ilimitada.** Un solo vehículo que regresa y recarga. Con vehículos
   idénticos y costo igual a la distancia total, tiene el mismo óptimo que el
   CVRP con flota ilimitada y no tiene simetría entre vehículos.
4. **Rompimiento de simetría.** Se controla desde el archivo de problema, sin
   cambiar el dominio: con `--simetria`, el vehículo i+1 solo puede salir
   después de que salga el i.
5. **Codificación clásica.** La carga se representa con objetos `n0..nQ` y hechos
   estáticos `(resta ?c ?antes ?despues)`, al estilo del dominio Transport de la
   IPC. El grounding crece con Q.
6. **Distancias.** Euclidianas redondeadas al entero más cercano (convención
   TSPLIB/CVRPLib), para que los costos sean enteros y comparables con los
   valores publicados.

## Resultados hasta ahora

**Hito de validación** (`instancias/hito/`, 4 instancias de 5 y 6 clientes):
en ambas flotas, `enhsp-opt` y `fd-opt` encuentran exactamente el óptimo del
solver exacto, igual que PyVRP. Las configuraciones satisficing quedan entre
0% y 36% arriba del óptimo.

**Escalamiento inicial** (`resultados/escalamiento_inicial.csv`, flota limitada,
K=2, timeout 60 s, una instancia por tamaño):

| Clientes | Exacto | PyVRP | ENHSP opt | Fast Downward opt |
|---|---|---|---|---|
| 8  | 0.00 s | óptimo | 1.2 s (≈19 mil nodos) | 2.3 s (≈3 mil nodos) |
| 10 | 0.01 s | óptimo | 12.4 s (≈247 mil nodos) | 50.4 s (≈19 mil nodos) |
| 12 | 0.08 s | óptimo | timeout | timeout |

Lectura preliminar: los planners óptimos dejan de resolver alrededor de 12
clientes. LM-cut expande unas 13 veces menos nodos que h_max numérico, pero
cada nodo cuesta mucho más (la codificación clásica genera unas 40 veces más
acciones). Con K=2 el rompimiento de simetría casi no cambia nada; hay que
probarlo con K más grande. Es una sola semilla por tamaño: falta repetir con
más instancias antes de sacar conclusiones.
