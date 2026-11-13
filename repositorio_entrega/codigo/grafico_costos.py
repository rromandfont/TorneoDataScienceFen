"""Resultado acumulado de la estrategia con distintos costos de transacción."""
import argparse, os
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.dates as mdates
import modelo_adaptativo as M

TINTA, TINTA2, FONDO, GRILLA, GRIS_CLARO = "#0b0b0b", "#52514e", "#fcfcfb", "#ecebe7", "#c9c8c2"
AZULES = ["#a9c9f0", "#7aa9e6", "#4a89dc", "#2a6fc4", "#164f95", "#0d3366"]   # claro = barato, oscuro = caro

ap = argparse.ArgumentParser()
ap.add_argument("--xlsx", default="datos/base_usdclp.xlsx"); ap.add_argument("--modo", default="torneo")
ap.add_argument("--desde", default="2026-01-01"); ap.add_argument("--costos", type=float, nargs="+", default=[0, 1, 2, 3, 5])
ap.add_argument("--techo", type=float, default=1.0); ap.add_argument("--piso", type=float, default=0.5)
ap.add_argument("--estrategia", choices=list(M.ESTRATEGIAS), default=None); ap.add_argument("--test_desde", default="2026-01-01"); ap.add_argument("--salida", default="resultados")
a = ap.parse_args(); os.makedirs(a.salida, exist_ok=True)
if a.estrategia:
    a.piso, a.techo = M.ESTRATEGIAS[a.estrategia]["piso"], M.ESTRATEGIAS[a.estrategia]["techo"]

Z, F = M.señales(M.cargar(a.xlsx), a.modo)
fin_dev = (pd.Timestamp(a.test_desde) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
_, W, t = M.elegir(Z, F, {"2016-2023": ("2016", "2023"), "2024-fin_dev": ("2024", fin_dev), "TEST": (a.test_desde, "2100")})
sc, _ = M.score_dinamico(Z, F, W, t)
pos = M.exposicion(sc, techo=a.techo, piso=a.piso)[a.desde:]
pos = pos[F.ret_fwd.reindex(pos.index).notna()]
fechas = pos.index + pd.offsets.BDay(0)
fecha_res = F.index.to_series().shift(-1).reindex(pos.index)       # el resultado de t se realiza en t+1

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5, "axes.edgecolor": GRIS_CLARO,
                     "axes.labelcolor": TINTA2, "xtick.color": TINTA2, "ytick.color": TINTA2})
fig, ax = plt.subplots(figsize=(11, 5.8), facecolor=FONDO); ax.set_facecolor(FONDO)
ax.axhline(100, color=GRIS_CLARO, lw=1.2, ls=(0, (4, 3)))
cols = AZULES[-len(a.costos):] if len(a.costos) <= len(AZULES) else AZULES
finales = []
for c, col in zip(sorted(a.costos), cols):
    _, n = M.pnl(pos, F, c)
    eq = pd.concat([pd.Series([100.0], index=[pos.index[0]]), 100 * (1 + n).cumprod().set_axis(fecha_res.values)])
    ax.plot(eq.index, eq.values, color=col, lw=2.2 if c == 3 else 1.6, zorder=3)
    finales.append((c, eq.iloc[-1], col, eq.index[-1]))
fin = finales[0][3]
ys = []; sep = (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.05
for c, y, col, _ in sorted(finales, key=lambda x: x[1]):
    yt = max(y, ys[-1] + sep) if ys else y; ys.append(yt)
    txt = f"{c:g} pb  {y - 100:+.1f}%" + ("  (supuesto)" if c == 3 else "")
    ax.annotate(txt, xy=(fin, yt), xytext=(8, 0), textcoords="offset points", va="center", color=TINTA,
                fontsize=9, annotation_clip=False)
    ax.plot([fin], [y], "o", ms=4, color=col, mec=FONDO, mew=1.5, zorder=4)
ax.set_ylabel("Resultado acumulado, base cien")
ax.grid(axis="y", color=GRILLA, lw=.8); ax.set_axisbelow(True)
for s in ["top", "right"]: ax.spines[s].set_visible(False)
ax.xaxis.set_major_locator(mdates.MonthLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
rot = pos.diff().abs().fillna(pos.abs()).sum()
ax.set_title(f"Estrategia USD/CLP según el costo de transacción · {pos.index[0]:%d-%m-%Y} a {fin:%d-%m-%Y}",
             loc="left", color=TINTA, fontsize=12, pad=10)
fig.text(0.01, 0.01, f"Modo {a.modo}, exposición 1x, neto de carry. {int(rot)} unidades transadas en el periodo "
         f"({(pos != 0).mean()*100:.0f}% de los días con posición). Costo por unidad transada.", color=TINTA2, fontsize=8)
fig.subplots_adjust(left=.07, right=.83, top=.91, bottom=.1)
ruta = os.path.join(a.salida, f"costos_{a.modo}_{a.estrategia or 'original'}_{a.desde[:4]}.png"); plt.savefig(ruta, dpi=150, facecolor=FONDO)
print({c: round(y - 100, 2) for c, y, _, _ in finales}, "unidades transadas:", rot, "->", ruta)
