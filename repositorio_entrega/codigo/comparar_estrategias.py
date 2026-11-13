"""Compara las estrategias de exposición del modelo con las tres referencias desde una fecha (base 100)."""
import argparse, os
import numpy as np, pandas as pd
from scipy import stats
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.dates as mdates
import modelo_adaptativo as M

COL = {"original": "#2a78d6", "salvo_extremos": "#0d3366", "todos_los_dias": "#eb6834",
       "comprar_siempre": "#8a8984", "no_operar": "#c9c8c2"}


def main(xlsx, modo, costo, desde, salida, test_desde="2026-01-01"):
    os.makedirs(salida, exist_ok=True)
    Z, F = M.señales(M.cargar(xlsx), modo)
    fin_dev = (pd.Timestamp(test_desde) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    _, W, t_min = M.elegir(Z, F, {"2016-2023": ("2016", "2023"), "2024-fin_dev": ("2024", fin_dev), "TEST": (test_desde, "2100")})
    sc, _ = M.score_dinamico(Z, F, W, t_min)
    r = F.ret_fwd
    idx = sc[desde:].index; idx = idx[r.reindex(idx).notna()]
    P = {k: M.exposicion(sc, **v)[idx] for k, v in M.ESTRATEGIAS.items()}
    P["comprar_siempre"] = pd.Series(1.0, index=idx)
    P["no_operar"] = pd.Series(0.0, index=idx)
    N = {k: M.pnl(p, F, costo)[1] for k, p in P.items()}
    fecha_res = F.index.to_series().shift(-1).reindex(idx)          # el resultado de t se realiza en t+1
    EQ = {k: pd.concat([pd.Series([100.0], index=[idx[0]]), pd.Series((100 * (1 + n).cumprod()).values, index=fecha_res.values)])
          for k, n in N.items()}
    anios = sorted({d.year for d in idx})
    filas = []
    for k, p in P.items():
        n = N[k]; eq = EQ[k]; act = (p != 0) & (r[idx] != 0)
        hit = np.sign(p[act]) == np.sign(r[idx][act]); kk, nn = int(hit.sum()), int(act.sum())
        f = {"estrategia": k, "dias_operados_%": 100 * (p != 0).mean(),
             "acierto_%": 100 * kk / nn if nn else np.nan,
             "p_binomial": stats.binomtest(kk, nn, .5, alternative="greater").pvalue if nn else np.nan}
        for y in anios:
            f[f"neto_{y}_%"] = 100 * ((1 + n[str(y)]).prod() - 1)
        f.update({"neto_total_%": eq.iloc[-1] - 100, "caida_max_%": 100 * (eq / eq.cummax() - 1).min(),
                  "sharpe": n.mean() / n.std() * np.sqrt(252) if n.std() > 0 else 0.0})
        if k in M.ESTRATEGIAS:
            f["boot_p_vs_no_operar"] = M.bootstrap(n.values)
            f["boot_p_vs_comprar_siempre"] = M.bootstrap((n - N["comprar_siempre"]).values)
            if k != "todos_los_dias":
                f["boot_p_vs_todos_los_dias"] = M.bootstrap((n - N["todos_los_dias"]).values)
        filas.append(f)
    T = pd.DataFrame(filas).set_index("estrategia")
    base = os.path.join(salida, f"comparacion_{modo}_{desde[:10]}")
    T.to_csv(base + ".csv")
    pd.set_option("display.width", 250)
    print(f"=== Comparacion desde {idx[0].date()} hasta {fecha_res.iloc[-1].date()} | modo {modo} | costo {costo} pb ===")
    print(T.round(3).to_string())

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5})
    fig, ax = plt.subplots(figsize=(11, 5.8), facecolor="#fcfcfb"); ax.set_facecolor("#fcfcfb")
    for k, eq in EQ.items():
        if k == "no_operar":
            ax.axhline(100, color=COL[k], ls=(0, (4, 3)), lw=1.2); continue
        ax.plot(eq.index, eq.values, color=COL[k], lw=2.2 if k in M.ESTRATEGIAS else 1.1)
    fin = EQ["no_operar"].index[-1]
    ys = []; sep = (ax.get_ylim()[1] - ax.get_ylim()[0]) * .045
    for k, y in sorted([(k, eq.iloc[-1]) for k, eq in EQ.items()], key=lambda x: x[1]):
        yt = max(y, ys[-1] + sep) if ys else y; ys.append(yt)
        ax.annotate(f"{k.replace('_', ' ')}  {y:.0f}", xy=(fin, yt), xytext=(8, 0), textcoords="offset points",
                    va="center", fontsize=9, annotation_clip=False)
        ax.plot([fin], [y], "o", ms=4, color=COL[k])
    for s in ["top", "right"]: ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#ecebe7"); ax.set_ylabel(f"Resultado acumulado, base 100 = {idx[0]:%d-%m-%Y}")
    ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_title(f"Estrategias del modelo vs. referencias, {idx[0]:%d-%m-%Y} a {fin:%d-%m-%Y}", loc="left", fontsize=12)
    fig.text(.01, .01, f"Modo {modo}, neto de carry y {costo:g} pb de costo por unidad transada.", fontsize=8, color="#52514e")
    fig.subplots_adjust(left=.07, right=.79, top=.92, bottom=.1); plt.savefig(base + ".png", dpi=150, facecolor="#fcfcfb")
    print("Archivos:", base + ".csv", base + ".png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Compara estrategias del modelo USD/CLP")
    ap.add_argument("--xlsx", default="datos/base_usdclp.xlsx")
    ap.add_argument("--modo", choices=["estricto", "torneo"], default="torneo")
    ap.add_argument("--costo_bps", type=float, default=3.0)
    ap.add_argument("--desde", default="2023-01-01")
    ap.add_argument("--salida", default="resultados")
    a = ap.parse_args()
    main(a.xlsx, a.modo, a.costo_bps, a.desde, a.salida)
