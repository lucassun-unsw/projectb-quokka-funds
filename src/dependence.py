"""Joint-tail dependence between equities and crypto (ported from Part A).

Ported from the verified z5594806_projectA/src/dependence.py. The tail-dependence
computations are unchanged and reproduce Part A's exact numbers; the docstrings are
reframed for Part B and one function, ``joint_crash_dates`` (below), is added for
the co-crash stress-test panel. Part A used this descriptively (no funds, no
weights) to establish that equities and crypto crash together more than they rally
together, and that Gaussian risk understates joint downside. Part B reuses two
pieces of this machinery directly:

  - ``empirical_tail_dep`` / the pseudo-observation crash definition, to define
    the "joint-crash day" set the co-crash stress-test panel evaluates every
    fund on (see ``src/portfolios.py::co_crash_returns`` and `OUTLINE.md`).
  - The min-CVaR fund's motivation cites this module's numbers directly (25.9%
    vs 15.5% joint-worst-5%, -10.8% vs -7.1% empirical/Gaussian ES) - see the
    min-CVaR locked decision in `report/OUTLINE.md`.

Fits a bivariate Student-t copula to the equal-weight equity and crypto aggregate
returns and reports tail dependence: the probability that one asset class has an
extreme day GIVEN the other does. Average correlation misses exactly this - two
series can be modestly correlated on average yet crash together.

Scope guards (unchanged from Part A):
  - The inputs are naive equal-weight asset-class aggregates from
    ``features.asset_class_aggregate`` - NOT funds, NOT portfolio weights.
  - scipy/numpy only; every function returns a value, none write to ``results/``.

Method:
  1. Pseudo-observations via the empirical CDF (rank/(n+1)) - copulas separate the
     dependence structure from the marginals, so fat-tailed marginals do not
     contaminate the dependence estimate.
  2. rho from Kendall's tau inversion (rho = sin(pi*tau/2), robust to outliers);
     nu by 1-d profile maximum likelihood.
  3. Closed-form t-copula tail dependence
     lambda = 2 * T_{nu+1}(-sqrt((nu+1)(1-rho)/(1+rho))), identical in both tails.
  4. Empirical exceedance P(both in worst q | one in worst q) as a model-free
     cross-check, and a Gaussian-copula log-likelihood for comparison (the Gaussian
     copula forces lambda = 0, i.e. assumes joint crashes away).
  5. Estimation uncertainty: refit excluding 2020 - the crash sample is small and
     one episode (COVID) carries much of the tail signal.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import optimize, special, stats


# --------------------------------------------------------------------------- #
# 1. Pseudo-observations
# --------------------------------------------------------------------------- #
def pseudo_obs(x: np.ndarray) -> np.ndarray:
    """Empirical-CDF transform: ranks scaled by (n+1), strictly inside (0,1)."""
    x = np.asarray(x, dtype=float)
    return stats.rankdata(x) / (len(x) + 1)


# --------------------------------------------------------------------------- #
# 2. Student-t copula fit (tau-inversion rho + profile-likelihood nu)
# --------------------------------------------------------------------------- #
def _t_copula_negloglik(nu: float, u: np.ndarray, v: np.ndarray, rho: float) -> float:
    """Negative log-likelihood of the bivariate t copula at (rho, nu)."""
    x = stats.t.ppf(u, nu)
    y = stats.t.ppf(v, nu)
    det = 1.0 - rho * rho
    quad = (x * x - 2.0 * rho * x * y + y * y) / (nu * det)
    log_f2 = (special.gammaln((nu + 2.0) / 2.0) - special.gammaln(nu / 2.0)
              - np.log(nu * np.pi) - 0.5 * np.log(det)
              - (nu + 2.0) / 2.0 * np.log1p(quad))
    log_c = log_f2 - stats.t.logpdf(x, nu) - stats.t.logpdf(y, nu)
    return -float(np.sum(log_c))


def _gauss_copula_loglik(u: np.ndarray, v: np.ndarray, rho: float) -> float:
    """Gaussian-copula log-likelihood at the same rho (its tail dependence is 0)."""
    x = stats.norm.ppf(u)
    y = stats.norm.ppf(v)
    det = 1.0 - rho * rho
    log_c = (-0.5 * np.log(det)
             - (rho * rho * (x * x + y * y) - 2.0 * rho * x * y) / (2.0 * det))
    return float(np.sum(log_c))


def t_tail_dependence(rho: float, nu: float) -> float:
    """Closed-form t-copula tail-dependence coefficient (same lower and upper)."""
    arg = -np.sqrt((nu + 1.0) * (1.0 - rho) / (1.0 + rho))
    return float(2.0 * stats.t.cdf(arg, nu + 1.0))


def empirical_tail_dep(x: np.ndarray, y: np.ndarray, q: float = 0.05,
                       tail: str = "lower") -> float:
    """Model-free exceedance estimate: P(both beyond q | one beyond q).

    ``lower``: P(U<=q, V<=q)/q on the pseudo-observations - the joint-crash
    frequency relative to what independence would imply (which is q itself).
    """
    u, v = pseudo_obs(x), pseudo_obs(y)
    if tail == "lower":
        return float(np.mean((u <= q) & (v <= q)) / q)
    return float(np.mean((u >= 1 - q) & (v >= 1 - q)) / q)


def gauss_implied_exceedance(rho: float, q: float = 0.05) -> float:
    """Finite-level exceedance a Gaussian copula with this rho implies.

    P(U<=q, V<=q)/q under the Gaussian copula - the right benchmark for the
    empirical 5% exceedance. The Gaussian ASYMPTOTIC tail dependence is 0, but at
    q=5% ordinary correlation alone already produces joint exceedances well above
    independence (q). Empirical >> this benchmark is evidence of tail thickening
    beyond correlation; empirical ~ this benchmark says correlation explains it.
    """
    z = stats.norm.ppf(q)
    joint = stats.multivariate_normal(mean=[0.0, 0.0],
                                      cov=[[1.0, rho], [rho, 1.0]]).cdf([z, z])
    return float(joint / q)


def fit_t_copula(x: np.ndarray, y: np.ndarray,
                 nu_bounds: tuple[float, float] = (2.05, 100.0)) -> dict:
    """Fit the bivariate Student-t copula to two return series.

    rho comes from Kendall's tau inversion (robust, standard); nu from a bounded
    1-d profile MLE. Returns the parameters, closed-form tail dependence, the
    empirical 5% exceedance cross-checks with the Gaussian-implied benchmark, and
    the t-vs-Gaussian log-likelihood gap (positive = the t copula, which allows
    joint tails, fits better). ``nu_at_bound`` flags a fit that ran into the upper
    nu bound - read that as "indistinguishable from Gaussian", not as a precise nu.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    u, v = pseudo_obs(x), pseudo_obs(y)

    tau = stats.kendalltau(x, y).statistic
    rho = float(np.sin(np.pi * tau / 2.0))

    res = optimize.minimize_scalar(_t_copula_negloglik, args=(u, v, rho),
                                   bounds=nu_bounds, method="bounded")
    nu = float(res.x)
    loglik_t = -float(res.fun)
    loglik_gauss = _gauss_copula_loglik(u, v, rho)

    return {
        "n_obs": len(x),
        "kendall_tau": float(tau),
        "rho": rho,
        "nu": nu,
        "nu_at_bound": bool(nu >= 0.95 * nu_bounds[1]),
        "tail_dependence": t_tail_dependence(rho, nu),
        "emp_lower_5pct": empirical_tail_dep(x, y, 0.05, "lower"),
        "emp_upper_5pct": empirical_tail_dep(x, y, 0.05, "upper"),
        "gauss_implied_5pct": gauss_implied_exceedance(rho, 0.05),
        "loglik_t": loglik_t,
        "loglik_gauss": loglik_gauss,
        "loglik_gap_t_minus_gauss": loglik_t - loglik_gauss,
    }


# --------------------------------------------------------------------------- #
# 3. Main-pair summary (full sample + ex-2020 sensitivity)
# --------------------------------------------------------------------------- #
def dependence_summary(agg: pd.DataFrame) -> pd.DataFrame:
    """Fit the equity-vs-crypto aggregate pair, full sample and excluding 2020.

    ``agg`` is ``features.asset_class_aggregate`` output (equity, crypto columns on
    the equity calendar). The ex-2020 row is the honesty check: the crash sample is
    small and dominated by one episode, so any claim must say how much of the tail
    signal that single year carries.
    """
    pair = agg[["equity", "crypto"]].dropna()
    rows = []
    for label, sub in [("full sample 2020-2023", pair),
                       ("excluding 2020", pair[pair.index.year != 2020])]:
        fit = fit_t_copula(sub["equity"].to_numpy(), sub["crypto"].to_numpy())
        rows.append({"sample": label, **fit})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# 4. Sector x crypto tail-dependence matrix (heatmap data)
# --------------------------------------------------------------------------- #
def sector_crypto_tail_matrix(panel: pd.DataFrame,
                              stat: str = "lambda") -> pd.DataFrame:
    """Tail dependence between each equity sector and each cryptocurrency.

    Rows: the 10 equal-weight sector aggregates; columns: the 10 coins (their own
    returns on equity trading days, from the combined panel).

    ``stat="lambda"``: closed-form asymptotic lambda from a pairwise t-copula fit.
    On this data most pairs fit near-Gaussian (nu at the bound), so the lambdas are
    tiny - honest, but visually flat. ``stat="emp_lower_5pct"``: the model-free
    joint worst-5% exceedance, which shows the sector-level variation in co-crash
    frequency (independence = 0.05); prefer it for a heatmap and quote lambda in
    the table.
    """
    eq = panel[panel["asset_class"] == "equity"].dropna(subset=["ret"])
    sector_rets = (eq.groupby(["date", "sector"])["ret"].mean()
                     .unstack("sector").sort_index())
    cr = panel[panel["asset_class"] == "crypto"].dropna(subset=["ret"])
    coin_rets = cr.pivot(index="date", columns="ticker", values="ret").sort_index()

    out = pd.DataFrame(index=sector_rets.columns, columns=coin_rets.columns,
                       dtype=float)
    if stat not in ("lambda", "emp_lower_5pct"):
        raise ValueError(f"stat must be 'lambda' or 'emp_lower_5pct', got {stat!r}")
    for sec in sector_rets.columns:
        for coin in coin_rets.columns:
            both = pd.concat([sector_rets[sec], coin_rets[coin]], axis=1,
                             sort=True).dropna()
            a = both.iloc[:, 0].to_numpy()
            b = both.iloc[:, 1].to_numpy()
            if stat == "lambda":
                out.loc[sec, coin] = fit_t_copula(a, b)["tail_dependence"]
            else:
                out.loc[sec, coin] = empirical_tail_dep(a, b, 0.05, "lower")
    out.index.name = "sector"
    out.columns.name = "crypto"
    return out


# --------------------------------------------------------------------------- #
# 5. Gaussian-vs-empirical VaR/ES on an illustrative equal-weight basket
# --------------------------------------------------------------------------- #
def var_es_comparison(agg: pd.DataFrame, weights: tuple[float, float] = (0.5, 0.5),
                      levels: tuple[float, ...] = (0.05, 0.01)) -> pd.DataFrame:
    """Daily VaR/ES of a 50/50 equity/crypto basket: Gaussian vs empirical.

    The basket is an ILLUSTRATION of joint downside, not a fund or an allocation
    recommendation - the Part B min-CVaR fund is the constructed-portfolio version
    of this idea. VaR at level a is the a-th return quantile (a negative number);
    ES is the mean return beyond it. The Gaussian rows use the basket's own
    mean/sd - the gap to the empirical rows is the fat-tail understatement, in
    return units.
    """
    pair = agg[["equity", "crypto"]].dropna()
    r = weights[0] * pair["equity"] + weights[1] * pair["crypto"]
    mu, sd = float(r.mean()), float(r.std())

    rows = []
    for a in levels:
        z = stats.norm.ppf(a)
        var_g = mu + sd * z
        es_g = mu - sd * stats.norm.pdf(z) / a
        var_e = float(r.quantile(a))
        es_e = float(r[r <= var_e].mean())
        rows.append({
            "level": f"{a:.0%}",
            "var_gaussian": var_g, "var_empirical": var_e,
            "es_gaussian": es_g, "es_empirical": es_e,
            "es_understatement": es_e - es_g,  # negative = reality worse than normal
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# 6. Joint-crash date flags (new in Part B - the co-crash stress-test panel)
# --------------------------------------------------------------------------- #
def joint_crash_dates(agg: pd.DataFrame, q: float = 0.05) -> pd.Index:
    """Dates where equity AND crypto aggregates are both in their own worst q%.

    Reuses the same pseudo-observation crash definition as ``empirical_tail_dep``
    (Part A, Sec. 4), applied here to return the actual DATES rather than a summary
    ratio, so ``src/portfolios.py::co_crash_returns`` can evaluate any fund's
    return specifically on these days. Not a new definition - the same one Part A
    used to find the 25.9%-vs-15.5% joint-worst-5% asymmetry, now applied to
    select dates instead of just a summary statistic.
    """
    pair = agg[["equity", "crypto"]].dropna()
    u = pseudo_obs(pair["equity"].to_numpy())
    v = pseudo_obs(pair["crypto"].to_numpy())
    mask = (u <= q) & (v <= q)
    return pair.index[mask]
