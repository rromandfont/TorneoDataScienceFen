"""Predictor de dirección del USD/CLP con coeficientes dinámicos: datos, señales, pesos por IC móvil, exposición, evaluación y CLI."""
import argparse, itertools, json, os, warnings
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
warnings.filterwarnings("ignore")

INICIO = "2005-01-01"
# Señales que cierran en Londres / Nueva York (en modo estricto entran con 1 dia de rezago)
NY_LONDRES = ["emfx_r1", "bbdxy_r1", "vix_d1", "spx_r1", "gold_r1", "hg_r1", "hg_r5", "ndf_basis_z", "mxef_r1",
              "res_em_1"]  # res_em_1 usa BRL/MXN/ZAR del mismo dia (correccion v2)
GRILLA = dict(W=[60, 120, 250], t_min=[0.0, 1.0])

# VERSION 11 VARIABLES: subconjunto elegido por eliminacion hacia atras maximizando el acierto de 2024-2025
# (modo torneo, W=250, t_min=1). Se quitaron: emfx_r1, clp_range_rel, carry_z, vix_d1, spx_r1.
# 2026 no intervino en la eleccion. Para usar las 16 señales originales: --todas
VARIABLES = ["bbdxy_r1", "mxef_r1", "gold_r1", "hg_r1", "hg_r5", "ndf_basis_z", "shcomp_r1",
             "clp_r1", "clp_r5", "res_em_1", "cl5y_d1"]
W_FIJO, TMIN_FIJO = 250, 1.0          # parametros con los que se hizo la eleccion de variables


# =============================================================================================
# 1. DATOS
# =============================================================================================
def cargar(xlsx):
    d = pd.read_excel(xlsx, sheet_name="datos")
    d["fecha"] = pd.to_datetime(d["fecha"])
    return d.set_index("fecha").sort_index()


def construir(d):
    """Calendario, objetivo, carry y señales. Todo calculado con informacion hasta el cierre de t."""
    P = lambda t, f="PX_LAST": d[f"{t}|{f}"].dropna()

    # Calendario = jornadas USD/CLP desde 2004 (antes O=H=L=C, sin rango intradia) sin cotizaciones
    # rancias de feriados chilenos (H==L).
    u = pd.DataFrame({k: P("USDCLP Curncy", f) for k, f in
                      zip("ohlc", ["PX_OPEN", "PX_HIGH", "PX_LOW", "PX_LAST"])}).dropna()
    u = u[(u.index >= "2004-01-01") & (u.h != u.l)]
    idx = u.index

    def lvl(t, f="PX_LAST", lim=5):                 # nivel al cierre de t; relleno hacia adelante acotado
        s = P(t, f)
        return s.reindex(idx.union(s.index)).ffill(limit=lim).reindex(idx)
    lr = lambda t, k=1: np.log(lvl(t)).diff(k)
    z = lambda s, w=250: (s - s.rolling(w, min_periods=120).mean()) / s.rolling(w, min_periods=120).std()

    # Carry: camara overnight (variacion del indice CLICP / dias corridos) - tasa USD
    # (Fed Funds hasta 2018-04, SOFR despues, con 1 dia de rezago porque se publican al dia siguiente).
    icp = P("CLICP Index")
    cam = (icp.pct_change() * 360 / icp.index.to_series().diff().dt.days * 100).rolling(5).median()
    cam = cam.reindex(idx.union(cam.index)).ffill(limit=5).reindex(idx)
    usd = pd.concat([P("FEDL01 Index")[:"2018-04-01"], P("SOFRRATE Index")["2018-04-02":]]).sort_index().shift(1)
    usd = usd.reindex(idx.union(usd.index)).ffill(limit=5).reindex(idx)
    carry = cam - usd                                   # % anual; lo paga el largo en USD

    r = np.log(u.c).diff()
    S = pd.DataFrame(index=idx)
    # --- dolar global / EM / riesgo / commodities (cierre NY o Londres) ---
    S["emfx_r1"] = (z(lr("USDZAR Curncy")) + z(lr("USDMXN Curncy")) + z(lr("USDBRL Curncy"))) / 3
    S["bbdxy_r1"] = lr("BBDXY Index")
    S["vix_d1"] = lvl("VIX Index").diff()
    S["spx_r1"] = lr("SPX Index")
    S["mxef_r1"] = lr("MXEF Index")
    S["gold_r1"] = lr("XAU Curncy")
    S["hg_r1"] = lr("HG1 Comdty")
    S["hg_r5"] = lr("HG1 Comdty", 5)
    S["ndf_basis_z"] = z(lvl("CHNI1M Curncy") - cam)    # rendimiento implicito NDF 1M - camara
    # --- Asia (cierra antes que Santiago) ---
    S["shcomp_r1"] = lr("SHCOMP Index")
    # --- Santiago / propio USD/CLP ---
    S["clp_r1"] = r
    S["clp_r5"] = np.log(u.c).diff(5)
    rng = np.log(u.h / u.l)
    S["clp_range_rel"] = np.log(rng / rng.rolling(60).mean())
    em_raw = (lr("USDZAR Curncy") + lr("USDMXN Curncy") + lr("USDBRL Curncy")) / 3
    beta = (r.rolling(120).cov(em_raw) / em_raw.rolling(120).var()).shift(1)
    S["res_em_1"] = r - beta * em_raw                   # movimiento propio del peso vs pares
    S["cl5y_d1"] = lvl("CHSWP5 Curncy").diff()
    S["carry_z"] = z(carry)

    dias = idx.to_series().diff().shift(-1).dt.days
    F = pd.DataFrame({"ret_fwd": u.c.shift(-1) / u.c - 1,          # objetivo: cierre t -> cierre t+1
                      "carry_fwd": carry / 100 * dias / 360}, index=idx)
    keep = idx >= INICIO
    return S[keep], F[keep]


def señales(d, modo):
    S, F = construir(d)
    if modo == "estricto":
        for c in NY_LONDRES:
            S[c] = S[c].shift(1)
    Z = S / S.rolling(250, min_periods=120).std()
    if VARIABLES:
        Z = Z[VARIABLES]
    return Z.clip(-5, 5), F


# =============================================================================================
# 2. MODELO DE COEFICIENTES DINAMICOS
# =============================================================================================
def score_dinamico(Z, F, W, t_min):
    """peso_i(t) = corr(z_i(s), r(s->s+1)) para s en [t-W, t-1]: el retorno t-1 -> t ya es conocido en t."""
    r = F.ret_fwd
    IC = pd.DataFrame({c: Z[c].shift(1).rolling(W, min_periods=W // 2).corr(r.shift(1)) for c in Z})
    w = IC.where(IC.abs() * np.sqrt(W) > t_min, 0.0)
    return (w * Z).sum(1, min_count=1), w


def probabilidad(score, F, ventana=500, refit=21):
    """Calibracion logistica movil del score -> P(sube). Solo usa pasado. La direccion la fija el score."""
    y = (F.ret_fwd > 0).astype(int)
    p = pd.Series(np.nan, index=score.index)
    pos = np.where(score.notna())[0]
    for k in range(300, len(pos), refit):
        tr = pos[max(0, k - ventana):k]; te = pos[k:k + refit]
        tr = tr[F.ret_fwd.iloc[tr].notna().values]
        m = LogisticRegression(C=1.0).fit(score.iloc[tr].values.reshape(-1, 1), y.iloc[tr])
        p.iloc[te] = m.predict_proba(score.iloc[te].values.reshape(-1, 1))[:, 1]
    return 0.5 + np.sign(score) * (p - 0.5).abs()


REGLAS_3X = ["ninguna", "top10", "banda", "racha", "consenso"]

# Estrategias de exposicion 1x (todas usan la MISMA prediccion de direccion; cambia en que dias se opera)
#   original        : opera solo si |score| >= su mediana movil de 250 dias (~50% de los dias)
#   salvo_extremos  : opera todos los dias salvo cuando |score| supera su percentil 90 movil (~88% de los dias)
#   todos_los_dias  : opera todos los dias con +1 / -1 segun el signo del score (100% de los dias)
ESTRATEGIAS = {"original": dict(piso=0.5, techo=1.0),
               "salvo_extremos": dict(piso=0.0, techo=0.9),
               "todos_los_dias": dict(piso=0.0, techo=1.0)}


def exposicion(score, usar_3x=False, regla="ninguna", F=None, score_otro=None, techo=1.0, piso=0.5):
    """Base: 0 bajo la mediana movil de |score| (250 jornadas, causal); 1x sobre ella.
    Las bases permiten solo -3, -1, 0, 1, 3 (no existe 2x). La regla decide que dias operados suben a 3x:
      ninguna  : nunca 3x (defecto).
      top10    : |score| sobre su percentil 90 (equivale al antiguo --usar_3x). En desarrollo acierta ~50%:
                 la conviccion EXTREMA aparece tras shocks y el peso tiende a corregir.
      banda    : |score| entre los percentiles 75 y 90 (conviccion alta pero no extrema).
      racha    : la estrategia 1x acerto >= 55% en sus ultimos 60 dias operados ya cerrados.
      consenso : el otro modo (estricto/torneo) da la misma direccion y AMBOS |score| estan entre p50 y p90.
                 OJO: usa el score del modo torneo, que incluye cierres de NY/Londres del mismo dia.
    piso: percentil movil de |score| desde el que se opera (0.5 = actual; 0 = operar todos los dias).
    techo < 1: abstenerse (0) cuando |score| supera su percentil movil `techo`. En desarrollo la conviccion
    extrema acierta <50% (aparece tras shocks y el peso corrige), por eso techo=0.9 mejora 2016-2025."""
    if usar_3x and regla == "ninguna":
        regla = "top10"
    qs = lambda s, q: s.abs().rolling(250, min_periods=120).quantile(q).shift(1)
    c = score.abs()
    q50, q75, q90 = qs(score, .5), qs(score, .75), qs(score, .9)
    base = c >= q50 if piso == 0.5 else (c >= qs(score, piso) if piso > 0 else q50.notna() & (c > 0))
    if techo < 1:
        base = base & (c < qs(score, techo))
    if regla == "ninguna":
        tres = pd.Series(False, index=score.index)
    elif regla == "top10":
        tres = c >= q90
    elif regla == "banda":
        tres = (c >= q75) & (c < q90)
    elif regla == "racha":
        r = F.ret_fwd.reindex(score.index)
        pos1 = np.sign(score) * base
        hit = (np.sign(pos1) == np.sign(r)).astype(float).where((pos1 != 0) & r.notna())
        # acierto de los ultimos 60 dias operados; shift(1): el resultado de t solo se conoce en t+1
        rec = hit.shift(1).dropna().rolling(60, min_periods=30).mean().reindex(score.index).ffill()
        tres = rec >= 0.55
    elif regla == "consenso":
        o = score_otro.reindex(score.index); co = o.abs()
        tres = (np.sign(o) == np.sign(score)) & base & (c < q90) & (co >= qs(o, .5)) & (co < qs(o, .9))
    else:
        raise ValueError(regla)
    n = np.where(base & tres, 3, np.where(base, 1, 0))
    return pd.Series(np.sign(score) * n, index=score.index).fillna(0) + 0.0


def lectura_conviccion(pos, F, costo_bps, per):
    """Diagnostico por nivel de exposicion (pedido en las bases): dias, acierto y resultado medio."""
    filas = []
    for k, (a, b) in per.items():
        p = pos[a:b]; p = p[F.ret_fwd.reindex(p.index).notna()]
        _, n = pnl(p, F, costo_bps); r = F.ret_fwd[p.index]
        for nivel in [-3, -1, 0, 1, 3]:
            m = p == nivel
            if m.any():
                filas.append({"periodo": k, "exposicion": nivel, "dias": int(m.sum()),
                              "acierto_%": 100 * (np.sign(r[m]) == np.sign(nivel)).mean() if nivel else np.nan,
                              "mov_abs_medio_pb": 1e4 * r[m].abs().mean(),
                              "resultado_medio_pb": 1e4 * n[m].mean()})
    return pd.DataFrame(filas)


# =============================================================================================
# 3. EVALUACION
# =============================================================================================
def pnl(pos, F, costo_bps):
    Fx = F.loc[pos.index]
    bruto = pos * (Fx.ret_fwd - Fx.carry_fwd)                    # el largo en USD paga el carry
    costo = pos.diff().abs().fillna(pos.abs()) * costo_bps / 1e4
    return bruto, bruto - costo


def diebold_mariano(l1, l2):
    d = np.asarray(l1 - l2); n = len(d); m = d.mean(); L = int(n ** (1 / 3))
    g = [np.mean((d[k:] - m) * (d[:n - k] - m)) for k in range(L + 1)]
    v = (g[0] + 2 * sum((1 - k / (L + 1)) * g[k] for k in range(1, L + 1))) / n
    s = m / np.sqrt(v)
    return s, 2 * stats.norm.sf(abs(s))


def bootstrap(diff, B=3000, bloque=20, seed=0):
    """p-valor unilateral H0: E[diff] <= 0 (bootstrap circular por bloques)."""
    rng = np.random.default_rng(seed); x = np.asarray(diff); n = len(x); nb = int(np.ceil(n / bloque))
    med = np.array([x[(rng.integers(0, n, nb)[:, None] + np.arange(bloque)).ravel()[:n] % n].mean()
                    for _ in range(B)])
    return float(((med - x.mean()) >= x.mean()).mean())


def acierto(score, F, a, b):
    s = score[a:b]; y = F.ret_fwd[a:b]; m = s.notna() & y.notna() & (s != 0) & (y != 0)
    k = int((np.sign(s[m]) == np.sign(y[m])).sum()); n = int(m.sum())
    return 100 * k / n, stats.binomtest(k, n, 0.5, alternative="greater").pvalue, n


def metricas(p, pos, F, costo_bps):
    pos = pos[F.ret_fwd.reindex(pos.index).notna()]
    Fx = F.loc[pos.index]; r = Fx.ret_fwd; p = p.reindex(pos.index).fillna(0.5)
    y = (r > 0).astype(int); hit = np.sign(pos) == np.sign(r); act = pos != 0
    b, n = pnl(pos, F, costo_bps); eq = (1 + n).cumprod()
    _, bh = pnl(pd.Series(1.0, index=pos.index), F, costo_bps)
    _, x1 = pnl(np.sign(p - 0.5) + 0.0, F, costo_bps)
    dm, dmp = diebold_mariano((p - y) ** 2, (0.5 - y) ** 2)
    clim = (F.ret_fwd.shift(1) > 0).astype(float).where(F.ret_fwd.shift(1).notna()).rolling(250, min_periods=120).mean()
    _, dmp_clim = diebold_mariano((p - y) ** 2, (clim.reindex(pos.index).fillna(0.5) - y) ** 2)
    _, cero = pnl(pd.Series(0.0, index=pos.index), F, costo_bps)
    dm_pnl = {f"DM_resultado_p_vs_{k}": diebold_mariano(-n, -ref)[1] for k, ref in
              [("comprar_siempre", bh), ("no_operar", cero), ("exposicion_uno", x1)]}
    return {"acierto_dias_operados_%": 100 * hit[act].mean() if act.any() else np.nan,
            "acierto_x1_%": 100 * hit[pos.abs() == 1].mean() if (pos.abs() == 1).any() else np.nan,
            "acierto_x3_%": 100 * hit[pos.abs() == 3].mean() if (pos.abs() == 3).any() else np.nan,
            "dias_operados_%": 100 * act.mean(), "dias_x1_%": 100 * (pos.abs() == 1).mean(),
            "dias_x3_%": 100 * (pos.abs() == 3).mean(),
            "largo_%_de_operados": 100 * (pos[act] > 0).mean() if act.any() else np.nan,
            "auc": roc_auc_score(y, p), "brier": brier_score_loss(y, p),
            "rotacion_anual": pos.diff().abs().sum() / len(pos) * 252,
            "ret_bruto_%": 100 * ((1 + b).prod() - 1), "ret_neto_%": 100 * (eq.iloc[-1] - 1),
            "sharpe_neto": n.mean() / n.std() * np.sqrt(252) if n.std() > 0 else 0.0,
            "max_dd_%": 100 * (eq / eq.cummax() - 1).min(),
            "DM_p": dmp, "DM_p_vs_frec_historica": dmp_clim, **dm_pnl, "boot_p_vs_comprar_siempre": bootstrap(n - bh),
            "boot_p_vs_no_operar": bootstrap(n), "boot_p_vs_exposicion_uno": bootstrap(n - x1)}


def grafico(pos, F, costo, ruta, test_desde, p=None):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pos = pos["2023":]; pos = pos[F.ret_fwd.reindex(pos.index).notna()]
    _, n = pnl(pos, F, costo); _, bh = pnl(pd.Series(1.0, index=pos.index), F, costo)
    fig, ax = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    ax[0].plot(100 * (1 + n).cumprod(), color="#1f3a93", lw=1.6, label="Estrategia adaptativa")
    ax[0].plot(100 * (1 + bh).cumprod(), color="#999", lw=1, label="Comprar siempre")
    if p is not None:
        _, x1 = pnl(np.sign(p.reindex(pos.index).fillna(0.5) - 0.5) + 0.0, F, costo)
        ax[0].plot(100 * (1 + x1).cumprod(), color="#e67e22", lw=1, label="Exposicion uno (todos los dias)")
    ax[0].axhline(100, color="#ccc", lw=.8, label="No operar")
    for x in ["2024-01-01", test_desde]:
        ax[0].axvline(pd.Timestamp(x), color="#c0392b", ls="--", lw=.8)
    ax[0].set_ylabel("Resultado neto (base 100)"); ax[0].legend(frameon=False); ax[0].grid(alpha=.2)
    ax[1].bar(pos.index, pos.values, width=1.5, color=np.where(pos > 0, "#1f3a93", "#c0392b"))
    ax[1].set_ylabel("Exposicion"); ax[1].grid(alpha=.2)
    plt.tight_layout(); plt.savefig(ruta, dpi=130); plt.close()


# =============================================================================================
# 4. EJECUCION
# =============================================================================================
def elegir(Z, F, per):
    """Grilla W x t_min; se elige por min(acierto 2016-2023, acierto 2024-fin_dev). TEST no interviene."""
    filas = []
    for W, t_min in itertools.product(*GRILLA.values()):
        sc, _ = score_dinamico(Z, F, W, t_min)
        row = dict(W=W, t_min=t_min)
        for k, (a, b) in per.items():
            row[f"acierto {k}"], row[f"p {k}"], _ = acierto(sc, F, a, b)
        row["criterio"] = min(row["acierto 2016-2023"], row["acierto 2024-fin_dev"])
        filas.append(row)
    G = pd.DataFrame(filas).sort_values("criterio", ascending=False)
    return G, int(G.iloc[0].W), float(G.iloc[0].t_min)


def main(xlsx, modo, costo, usar_3x, salida, test_desde, regla_3x="ninguna", techo=1.0, piso=0.5, estrategia=None,
         parametros_fijos=True):
    if estrategia:
        piso, techo = ESTRATEGIAS[estrategia]["piso"], ESTRATEGIAS[estrategia]["techo"]
    os.makedirs(salida, exist_ok=True)
    if usar_3x and regla_3x == "ninguna":
        regla_3x = "top10"
    d = cargar(xlsx)
    Z, F = señales(d, modo)
    fin_dev = (pd.Timestamp(test_desde) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    dev = {"2016-2023": ("2016", "2023"), "2024-fin_dev": ("2024", fin_dev)}
    per = {**dev, "TEST": (test_desde, "2100")}
    rep = {"2023": ("2023", "2023"), "2024-fin_dev": ("2024", fin_dev), "TEST": (test_desde, "2100")}   # periodos reportados
    tag = modo if regla_3x == "ninguna" else f"{modo}_3x-{regla_3x}"
    if estrategia and estrategia != "original":
        tag += f"_{estrategia}"
    elif not estrategia:
        if techo < 1:
            tag += f"_techo{techo}"
        if piso != 0.5:
            tag += f"_piso{piso}"

    # 4.1 eleccion de parametros SOLO con desarrollo
    G, W, t_min = elegir(Z, F, per)
    if parametros_fijos:
        W, t_min = W_FIJO, TMIN_FIJO
    print(f"=== MODO {modo.upper()} | grilla (referencia; parametros fijos: {parametros_fijos}) ===")
    print(G.round(3).to_string(index=False))

    # 4.2 modelo final
    sc, w = score_dinamico(Z, F, W, t_min)
    p = probabilidad(sc, F)
    score_otro = None
    if regla_3x == "consenso":
        otro = "torneo" if modo == "estricto" else "estricto"
        Zo, _ = señales(d, otro); _, Wo, to = elegir(Zo, F, per)
        score_otro, _ = score_dinamico(Zo, F, Wo, to)
        print(f"Consenso con modo {otro} (W={Wo}, t_min={to})")
    pos = exposicion(sc, regla=regla_3x, F=F, score_otro=score_otro, techo=techo, piso=piso)
    res = {}
    for k, (a, b) in rep.items():
        ac, pv, n = acierto(sc, F, a, b)
        res[k] = {"acierto_todos_los_dias_%": ac, "p_binomial_vs_50%": pv, "n_dias": n,
                  **metricas(p, pos[a:b], F, costo)}
    R = pd.DataFrame(res)
    print(f"\nElegido: W={W}, t_min={t_min} | costo {costo} pb por unidad transada | regla 3x: {regla_3x} | piso: {piso} | techo: {techo}")
    print(R.round(3).to_string())
    A = pd.Series({a: acierto(sc, F, str(a), str(a))[0] for a in range(2023, pd.Timestamp.today().year + 1)
                   if F.ret_fwd[str(a):str(a)].notna().any()})
    print("\nAcierto por año (%):\n" + A.round(1).to_frame("acierto").T.to_string())
    L = lectura_conviccion(pos, F, costo, rep)
    print("\nLectura de la conviccion (por nivel de exposicion):\n" + L.round(2).to_string(index=False))
    print("\nPeso medio |IC| por señal (ultimos 2 años):\n" + w.iloc[-500:].abs().mean().sort_values(ascending=False).round(3).to_string())

    # 4.3 señal del dia (ultima fecha con datos)
    ult = sc.dropna().index[-1]
    senal = {"fecha_cierre": str(ult.date()), "prob_sube": round(float(p.loc[ult]), 4) if pd.notna(p.loc[ult]) else None,
             "direccion": "SUBE" if sc.loc[ult] > 0 else "BAJA", "exposicion_sugerida": float(pos.loc[ult]),
             "modo": modo, "W": W, "t_min": t_min}
    if regla_3x != "ninguna":
        senal["regla_3x"] = regla_3x
    if techo < 1:
        senal["techo"] = techo
    if piso != 0.5:
        senal["piso"] = piso
    if estrategia and estrategia != "original":
        senal["estrategia"] = estrategia
    print("\nSEÑAL DEL DIA:", senal)

    G.to_csv(os.path.join(salida, f"grilla_{tag}.csv"), index=False)
    R.to_csv(os.path.join(salida, f"resultados_{tag}.csv"))
    json.dump(senal, open(os.path.join(salida, f"senal_del_dia_{tag}.json"), "w"), indent=1, ensure_ascii=False)
    pd.DataFrame({"score": sc, "prob_sube": p, "exposicion": pos, "ret_fwd": F.ret_fwd}).to_csv(
        os.path.join(salida, f"diario_{tag}.csv"))
    w.to_csv(os.path.join(salida, f"pesos_{tag}.csv"))
    L.to_csv(os.path.join(salida, f"conviccion_{tag}.csv"), index=False)
    grafico(pos, F, costo, os.path.join(salida, f"curva_{tag}.png"), test_desde, p)
    print(f"\nArchivos en: {salida}/")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Predictor adaptativo USD/CLP")
    ap.add_argument("--xlsx", default="datos/base_usdclp.xlsx")
    ap.add_argument("--modo", choices=["estricto", "torneo"], default="torneo")
    ap.add_argument("--costo_bps", type=float, default=3.0)
    ap.add_argument("--usar_3x", action="store_true", help="atajo de --regla_3x top10 (compatibilidad)")
    ap.add_argument("--regla_3x", choices=REGLAS_3X, default="ninguna",
                    help="que dias operados suben a 3x (ver exposicion()); defecto: ninguna")
    ap.add_argument("--techo", type=float, default=1.0,
                    help="abstenerse si |score| supera este percentil movil (ej. 0.9); 1.0 = sin techo")
    ap.add_argument("--estrategia", choices=list(ESTRATEGIAS), default=None,
                    help="original (defecto) | salvo_extremos | todos_los_dias; si se da, reemplaza --piso y --techo")
    ap.add_argument("--piso", type=float, default=0.5,
                    help="operar solo si |score| supera este percentil movil; 0 = operar todos los dias")
    ap.add_argument("--salida", default="resultados")
    ap.add_argument("--test_desde", default="2026-01-01")
    ap.add_argument("--todas", action="store_true", help="usar las 16 señales originales en vez de las 11 elegidas")
    ap.add_argument("--elegir_parametros", action="store_true", help="elegir W y t_min con la grilla en vez de fijarlos en 250 / 1")
    a = ap.parse_args()
    if a.todas:
        VARIABLES = None
    main(a.xlsx, a.modo, a.costo_bps, a.usar_3x, a.salida, a.test_desde, a.regla_3x, a.techo, a.piso, a.estrategia,
         parametros_fijos=not a.elegir_parametros)
