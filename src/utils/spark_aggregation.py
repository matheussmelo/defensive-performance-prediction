"""
Funções genéricas de agregação de DataFrames Spark, usadas pelos notebooks
de análise (notebooks/3_analysis/). Copiadas tal como estavam nos notebooks
— ainda não estão sendo importadas/usadas lá, só centralizadas aqui pra
reaproveitamento futuro.

Origem:
- build_aggregated_df: threat_score_analysis.ipynb / threat_score_impact_analysis.ipynb
- AGG_FUNCS_FEATURES / AGG_FUNCS_TARGET / build_feature_target_stats_df:
  eda_cycle_start_gk.ipynb / eda_cycle_start_all.ipynb
"""

from pyspark.sql import functions as F


# ---------------------------------------------------------------------------
# build_aggregated_df (threat_score_analysis.ipynb / threat_score_impact_analysis.ipynb)
# ---------------------------------------------------------------------------

def build_aggregated_df(
    df,
    group_cols,
    agg_cols,
    agg_func,
    agg_prefix
):
    """
    Agrega um DataFrame utilizando a função de agregação desejada.
    """

    # expressões de agregação com o prefixo conforme a agregação realizada (ex: média -> avg, máximo -> max)
    agg_exprs = [
        F.round(agg_func(F.col(c)), 3).alias(f"{agg_prefix}_{c}")
        for c in agg_cols
    ]

    # DataFrame agregado
    df_agg = (
        df
        .groupBy(*group_cols)
        .agg(*agg_exprs)
    )

    # nomes das colunas agregadas
    agg_cols_result = [
        f"{agg_prefix}_{c}"
        for c in agg_cols
    ]

    return agg_cols_result, df_agg


# ---------------------------------------------------------------------------
# build_feature_target_stats_df (eda_cycle_start_gk.ipynb / eda_cycle_start_all.ipynb)
# ---------------------------------------------------------------------------

AGG_FUNCS_FEATURES = {
    "avg": F.mean,
    "median": F.median,
    #"var": F.variance,
    "std": F.stddev,
    "min": F.min,
    #"p5":  lambda c: F.percentile_approx(c, 0.05),
    "max": F.max,
    #"p95": lambda c: F.percentile_approx(c, 0.95),
}

AGG_FUNCS_TARGET = {
    "avg": F.mean,
    "sum": F.sum,
    "max": F.max,
}


def build_feature_target_stats_df(df, features, target, group_cols):
    """Agrega features e target por `group_cols` num único groupBy (colunas "{agg}_{coluna}"). Assume que eventos com tracking inconsistente já foram removidos do df."""
    if isinstance(features, str):
        features = [features]

    agg_exprs = []

    for col_name in features:
        for prefix, func in AGG_FUNCS_FEATURES.items():
            alias = f"{prefix}_{col_name}"
            agg_exprs.append(F.round(func(F.col(col_name)), 3).alias(alias))

    for prefix, func in AGG_FUNCS_TARGET.items():
        alias = f"{prefix}_{target}"
        agg_exprs.append(F.round(func(F.col(target)), 3).alias(alias))

    df_agg = df.groupBy(*group_cols).agg(*agg_exprs)

    return df_agg
