"""
Statistical procedures of report Section 4.5, shared by the analysis notebooks.

Run-level variables (one value per run, 30 runs per strategy):
  1. Assumptions: Shapiro-Wilk per strategy, median-centred Levene across strategies.
     If normality fails, the same checks are repeated on the logarithm of the values,
     and the tests use the log values when that makes the data normal.
  2. Omnibus test: one-way ANOVA (equal variances) or Welch's ANOVA (unequal) when
     normality holds, Kruskal-Wallis otherwise.
  3. Pairwise tests, only after a significant omnibus test: Student's or Welch's
     t-test, or Mann-Whitney U, with Cohen's d or Cliff's delta as effect size.
"""

from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.oneway import anova_oneway

ALPHA = 0.05


def describe(runs: pd.DataFrame, variable: str) -> pd.DataFrame:
    """The descriptive statistics listed in the report, per strategy."""
    grouped = runs.groupby("strategy", observed=True)[variable]
    table = grouped.agg(["count", "mean", "median", "std", "var", "min", "max"])
    table["iqr"] = grouped.quantile(0.75) - grouped.quantile(0.25)
    return table


def groups(runs: pd.DataFrame, variable: str) -> dict[str, np.ndarray]:
    return {strategy: values.to_numpy()
            for strategy, values in runs.groupby("strategy", observed=True)[variable]}


def check_assumptions(samples: dict[str, np.ndarray]) -> dict:
    shapiro = {strategy: stats.shapiro(values).pvalue for strategy, values in samples.items()}
    levene = stats.levene(*samples.values(), center="median").pvalue
    return {"normal": all(p >= ALPHA for p in shapiro.values()),
            "equal_variances": levene >= ALPHA,
            "shapiro_p": shapiro, "levene_p": levene}


def omnibus(samples: dict[str, np.ndarray], normal: bool, equal_variances: bool) -> tuple[str, float]:
    """Return (test name, p-value) of the test that the strategies have equal means."""
    if not normal:
        return "Kruskal-Wallis", stats.kruskal(*samples.values()).pvalue
    if equal_variances:
        return "one-way ANOVA", stats.f_oneway(*samples.values()).pvalue
    return "Welch's ANOVA", anova_oneway(list(samples.values()), use_var="unequal").pvalue


def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    pooled_sd = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1))
                        / (len(a) + len(b) - 2))
    return (a.mean() - b.mean()) / pooled_sd


def cliffs_delta(a: np.ndarray, b: np.ndarray) -> float:
    """P(a > b) - P(a < b) over all pairs; -1..1."""
    difference = a[:, None] - b[None, :]
    return (np.sign(difference)).mean()


def mean_difference_ci(a: np.ndarray, b: np.ndarray, equal_variances: bool) -> tuple[float, float]:
    """95% confidence interval of mean(a) - mean(b), matching the t-test used."""
    result = stats.ttest_ind(a, b, equal_var=equal_variances)
    interval = result.confidence_interval(0.95)
    return interval.low, interval.high


def pairwise(samples: dict[str, np.ndarray], tested: dict[str, np.ndarray],
             normal: bool, equal_variances: bool) -> pd.DataFrame:
    """Two-sided pairwise comparisons, first strategy minus second.

    Differences are in the original units (samples); tests and effect sizes use
    the values that were tested (tested: the samples or their logarithm).
    """
    rows = []
    for first, second in combinations(samples, 2):
        a, b = samples[first], samples[second]
        row = {"comparison": f"{first} - {second}",
               "mean_difference": a.mean() - b.mean(),
               "percent_vs_second": 100 * (a.mean() / b.mean() - 1)}
        a, b = tested[first], tested[second]
        if normal:
            row["test"] = "Student's t" if equal_variances else "Welch's t"
            row["p"] = stats.ttest_ind(a, b, equal_var=equal_variances).pvalue
            if tested is samples:  # a confidence interval of log values is not in original units
                row["ci95_low"], row["ci95_high"] = mean_difference_ci(a, b, equal_variances)
            row["effect_size"], row["effect"] = cohens_d(a, b), "Cohen's d"
        else:
            row["test"] = "Mann-Whitney U"
            row["p"] = stats.mannwhitneyu(a, b).pvalue
            row["effect_size"], row["effect"] = cliffs_delta(a, b), "Cliff's delta"
        rows.append(row)
    return pd.DataFrame(rows)


def analyse(runs: pd.DataFrame, variable: str) -> dict:
    """The full procedure for one run-level variable; pairwise is None when not performed."""
    samples = groups(runs, variable)
    if any(values.std() == 0 for values in samples.values()):
        return {"variable": variable, "test": "descriptive only (constant within a strategy)",
                "p": np.nan, "pairwise": None}
    tested, transform = samples, "none"
    assumptions = check_assumptions(samples)
    if not assumptions["normal"]:
        logged = {strategy: np.log(values) for strategy, values in samples.items()}
        if (log_assumptions := check_assumptions(logged))["normal"]:
            tested, transform, assumptions = logged, "log", log_assumptions
    normal, equal_variances = assumptions["normal"], assumptions["equal_variances"]
    test, p = omnibus(tested, normal, equal_variances)
    comparisons = pairwise(samples, tested, normal, equal_variances) if p < ALPHA else None
    return {"variable": variable, "transform": transform, **assumptions,
            "test": test, "p": p, "pairwise": comparisons}
