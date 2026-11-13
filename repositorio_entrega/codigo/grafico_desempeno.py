"""Curva de resultado (base 100) contra las tres referencias y exposición diaria."""
import argparse, os
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import modelo_adaptativo as M

AZUL, NARANJA, GRIS, GRIS_CLARO = "#2a78d6", "#eb6834", "#8a8984", "#c9c8c2"
TINTA, TINTA2, FONDO, GRILLA = "#0b0b0b", "#52514e", "#fcfcfb", "#ecebe7"


def curvas(xlsx, modo, costo, techo, piso, regla_3x, test_desde):
    d = M.cargar(xlsx)
    Z, F = M.señales(d, modo)
    fin_dev = (pd.Timestamp(test_desde) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    per = {"2016-2023": ("2016", "2023"), "2024-fin_dev": ("2024", fin_dev), "TEST": (test_desde, "2100")}
    _, W, t_min = M.elegir(Z, F, per)
    sc, _ = M.score_dinamico(Z, F, W, t_min)
    score_otro = None
    if regla_3x == "consenso":
        otro = "torneo" if modo == "estricto" else "estricto"
        Zo, _ = M.señales(d, otro); _, Wo, to = M.elegir(Zo, F, per)
        score_otro, _ = M.score_dinamico(Zo, F, Wo, to)
    pos = M.exposicion(sc, regla=regla_3x, F=F, score_otro=score_otro, techo=techo, piso=piso)
    p = M.probabilidad(sc, F)
    return pos, p, F, W, t_min


def graficar(pos, p, F, costo, desde, test_desde, titulo, ruta):
    pos = pos[desde:]; pos = pos[F.ret_fwd.reindex(pos.index).notna()]
    _, est = M.pnl(pos, F, costo)
    _, bh = M.pnl(pd.Series(1.0, index=pos.index), F, costo)
    _, x1 = M.pnl(np.sign(p.reindex(pos.index).fillna(0.5) - 0.5) + 0.0, F, costo)
    eq = {k: 100 * (1 + v).cumprod() for k, v in
          {"Estrategia": est, "Exposición uno": x1, "Comprar siempre": bh}.items()}

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5, "axes.edgecolor": GRIS_CLARO,
                         "axes.labelcolor": TINTA2, "xtick.color": TINTA2, "ytick.color": TINTA2})
    fig, ax = plt.subplots(2, 1, figsize=(11, 6.6), sharex=True, facecolor=FONDO,
                           gridspec_kw={"height_ratios": [3.2, 1], "hspace": 0.06})
    a = ax[0]; a.set_facecolor(FONDO)
    # tramos de evaluacion
    t0 = pd.Timestamp(test_desde)
    a.axvspan(t0, pos.index[-1], color="#f1f0ec", lw=0, zorder=0)
    a.axhline(100, color=GRIS_CLARO, lw=1.2, ls=(0, (4, 3)), zorder=1)
    a.plot(eq["Comprar siempre"], color=GRIS, lw=1.0, zorder=2)
    a.plot(eq["Exposición uno"], color=NARANJA, lw=1.0, alpha=.9, zorder=2)
    a.plot(eq["Estrategia"], color=AZUL, lw=2.0, zorder=3)
    # etiquetas directas al final de cada curva
    fin = pos.index[-1]
    etiquetas = [("Estrategia", eq["Estrategia"].iloc[-1], AZUL),
                 ("Exposición uno", eq["Exposición uno"].iloc[-1], NARANJA),
                 ("Comprar siempre", eq["Comprar siempre"].iloc[-1], GRIS),
                 ("No operar", 100.0, GRIS_CLARO)]
    etiquetas.sort(key=lambda x: x[1])
    ys = []; rng = a.get_ylim()[1] - a.get_ylim()[0]; sep = rng * 0.045
    for _, y, _ in etiquetas:
        ys.append(max(y, ys[-1] + sep) if ys else y)
    for (nom, y, c), yt in zip(etiquetas, ys):
        a.annotate(f"{nom}  {y:.0f}", xy=(fin, yt), xytext=(8, 0), textcoords="offset points",
                   annotation_clip=False, color=TINTA, fontsize=9, va="center",
                   bbox=dict(boxstyle="round,pad=0.15", fc=FONDO, ec="none"))
        a.plot([fin], [y], "o", ms=4, color=c, mec=FONDO, mew=1.5, zorder=4)
    ev = pd.Timestamp("2022-07-14")
    if pos.index[0] < ev < pos.index[-1]:
        yv = eq["Estrategia"].asof(ev)
        a.annotate("Anuncio de intervención\ndel Banco Central (jul-2022)", xy=(ev, yv), xytext=(0.30, 0.80), bbox=dict(boxstyle="round,pad=0.2", fc=FONDO, ec="none"),
                   textcoords="axes fraction", fontsize=8, color=TINTA2,
                   arrowprops=dict(arrowstyle="-", color=GRIS, lw=.8))
    a.set_ylabel("Resultado acumulado, base cien")
    a.grid(axis="y", color=GRILLA, lw=.8); a.set_axisbelow(True)
    for s in ["top", "right"]: a.spines[s].set_visible(False)
    a.text(t0, a.get_ylim()[1], "  tramo de prueba", color=TINTA2, fontsize=8.5, va="top")
    a.set_title(titulo, loc="left", color=TINTA, fontsize=12, pad=10)

    b = ax[1]; b.set_facecolor(FONDO)
    b.bar(pos.index, pos.values, width=1.0, color=AZUL, lw=0)
    b.axhline(0, color=GRIS_CLARO, lw=.8)
    lim = 3 if pos.abs().max() > 1 else 1
    b.set_ylim(-lim * 1.15, lim * 1.15); b.set_yticks([-lim, 0, lim] if lim == 1 else [-3, -1, 0, 1, 3])
    b.set_ylabel("Exposición")
    tr = b.get_yaxis_transform()
    b.text(1.01, lim, "compra USD", transform=tr, color=TINTA2, fontsize=8.5, va="center")
    b.text(1.01, -lim, "venta corta USD", transform=tr, color=TINTA2, fontsize=8.5, va="center")
    b.grid(axis="y", color=GRILLA, lw=.8); b.set_axisbelow(True)
    for s in ["top", "right"]: b.spines[s].set_visible(False)
    b.xaxis.set_major_locator(mdates.YearLocator()); b.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.text(0.01, 0.005, f"Neto de carry y de {costo:g} pb de costo por unidad transada. "
             "Exposición uno: misma dirección del modelo, todos los días.", color=TINTA2, fontsize=8)
    fig.subplots_adjust(left=.07, right=.86, top=.93, bottom=.08)
    plt.savefig(ruta, dpi=150, facecolor=FONDO); plt.close()
    return {k: round(float(v.iloc[-1]), 1) for k, v in eq.items()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", default="datos/base_usdclp.xlsx")
    ap.add_argument("--modo", choices=["estricto", "torneo"], default="torneo")
    ap.add_argument("--costo_bps", type=float, default=3.0)
    ap.add_argument("--techo", type=float, default=1.0)
    ap.add_argument("--piso", type=float, default=0.5)
    ap.add_argument("--estrategia", choices=list(M.ESTRATEGIAS), default=None)
    ap.add_argument("--regla_3x", choices=M.REGLAS_3X, default="ninguna")
    ap.add_argument("--test_desde", default="2026-01-01")
    ap.add_argument("--desde", default="2023-01-01")
    ap.add_argument("--salida", default="resultados")
    a = ap.parse_args()
    os.makedirs(a.salida, exist_ok=True)
    if a.estrategia:
        a.piso, a.techo = M.ESTRATEGIAS[a.estrategia]["piso"], M.ESTRATEGIAS[a.estrategia]["techo"]
    pos, p, F, W, t = curvas(a.xlsx, a.modo, a.costo_bps, a.techo, a.piso, a.regla_3x, a.test_desde)
    tit = f"Predictor adaptativo USD/CLP · {a.estrategia or 'original'} · modo {a.modo} (W={W})"
    ruta = os.path.join(a.salida, f"desempeno_{a.modo}_{a.estrategia or 'original'}_{a.desde[:4]}.png")
    print(graficar(pos, p, F, a.costo_bps, a.desde, a.test_desde, tit, ruta), "->", ruta)
