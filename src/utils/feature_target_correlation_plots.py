"""
Heatmaps de correlação feature(s) x target a partir de um DataFrame
agregado por build_feature_target_stats_df (agregações-tipo × feature, ex:
"avg_surface_area"). Copiadas tal como estavam em eda_cycle_start_gk.ipynb /
eda_cycle_start_all.ipynb — ainda não estão sendo importadas/usadas lá, só
centralizadas aqui pra reaproveitamento futuro.

Atenção: existe uma OUTRA família de plots de correlação em
team_match_correlation_plots.py (de threat_score_analysis.ipynb) com uma
`plot_correlation_heatmap` de mesmo nome, mas assinatura/comportamento
diferentes (aquela recebe `corr_cols` prontas; esta aqui expande
combinações agregação×feature via AGG_FUNCS_FEATURES). Não são a mesma
função — por isso ficam em módulos separados, sem tentar unificar os nomes.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy import stats

from src.utils.spark_aggregation import AGG_FUNCS_FEATURES, AGG_FUNCS_TARGET


def _corr_pvalue_matrix(df_pd, cols, method='spearman'):
    """
    Calcula a matriz de correlação e a matriz de p-valor par-a-par pro
    mesmo conjunto de colunas (mesmo padrão de threat_score_analysis.ipynb)
    — usa pares completos (dropna por par de colunas), igual ao .corr() do
    pandas. Reaproveitada por plot_correlation_heatmap e
    plot_correlation_heatmap_by_team.
    """
    corr_func = stats.spearmanr if method == 'spearman' else stats.pearsonr

    corr = df_pd[cols].corr(method=method)

    pvals = pd.DataFrame(np.nan, index=cols, columns=cols)
    for i, col_i in enumerate(cols):
        for j, col_j in enumerate(cols):
            if j < i:
                continue
            if i == j:
                # correlação de uma coluna com ela mesma é trivial (r=1, p=0)
                pvals.loc[col_i, col_j] = 0.0
                continue
            paired = df_pd[[col_i, col_j]].dropna()
            pvalue = np.nan if len(paired) < 3 else corr_func(paired[col_i], paired[col_j])[1]
            pvals.loc[col_i, col_j] = pvalue
            pvals.loc[col_j, col_i] = pvalue

    return corr, pvals


def _corr_text_with_significance(corr, pvals, alpha):
    """Texto da célula = correlação arredondada, com "*" quando p-valor < alpha."""
    text = corr.round(3).astype(str)
    return text.where(pvals >= alpha, text + '*')


def plot_correlation_heatmap(df_agg, features, target, target_aggs=None, title_suffix="", alpha=0.05):
    """
    Monta UM heatmap de correlação (Spearman) cruzando TODAS as agregações
    de TODAS as features pedidas (AGG_FUNCS_FEATURES — avg/median/min/max/
    p95, uma coluna por combinação agregação×feature) com a(s) agregação(ões)
    do target pedida(s) em target_aggs. Aceita uma feature (str) ou várias
    (list) — a chamada é sempre a mesma, só muda quantas colunas entram na
    matriz. Célula recebe um "*" ao lado do valor quando o p-valor daquele
    par é < alpha (default 0.05).

    Parâmetros
    ----------
    df_agg : DataFrame Spark ou pandas retornado por build_feature_target_stats_df.
    features : str ou list[str]
        Nome(s) da(s) feature(s) originais (sem prefixo de agregação).
    target : str
        Nome da coluna alvo original (sem prefixo de agregação).
    target_aggs : str ou list[str]
        Chave(s) de AGG_FUNCS_TARGET a usar pro target (default: todas).
    title_suffix : str
        Texto extra concatenado ao título do heatmap (ex: nome do time,
        quando plotado via plot_correlation_heatmap_by_team).
    alpha : float
        Limiar de significância pro "*" (default 0.05).
    """
    if isinstance(features, str):
        features = [features]
    if target_aggs is None:
        target_aggs = list(AGG_FUNCS_TARGET.keys())
    elif isinstance(target_aggs, str):
        target_aggs = [target_aggs]

    df_agg_pd = df_agg.toPandas() if not isinstance(df_agg, pd.DataFrame) else df_agg

    agg_names = list(AGG_FUNCS_FEATURES.keys())
    feature_cols = [f"{prefix}_{feature}" for feature in features for prefix in agg_names]
    target_cols = [f"{ta}_{target}" for ta in target_aggs]

    corr, pvals = _corr_pvalue_matrix(df_agg_pd, feature_cols + target_cols)
    text = _corr_text_with_significance(corr, pvals, alpha)

    fig = go.Figure(
        data=go.Heatmap(
            z=corr.values,
            x=corr.columns,
            y=corr.columns,
            colorscale='RdBu',
            zmin=-1,
            zmax=1,
            text=text.values,
            texttemplate="%{text}",
            colorbar=dict(title="Correlação"),
        )
    )

    fig.update_layout(
        title=f"Correlação (Spearman) — agregações das features x {'/'.join(target_aggs)}_{target}{title_suffix}",
        template="simple_white",
        height=700,
        width=1000,
        xaxis=dict(tickangle=-45),
    )

    fig.show()


def plot_correlation_heatmap_by_team(df_agg, features, target, team_col, feature_agg, target_aggs='max', max_teams=5, alpha=0.05):
    """
    Um heatmap por time — diferente de plot_correlation_heatmap (que expande
    TODAS as agregações de AGG_FUNCS_FEATURES por feature): aqui cada
    feature entra com UMA única agregação (`feature_agg`, ex: "avg"), a
    mesma pra todas as features, e o target entra com a(s) agregação(ões)
    de `target_aggs` (default "max"). Serve pra ver se a correlação entre
    as features (nessa agregação) e o target se sustenta time a time, ou se
    é puxada por poucos times específicos. Célula recebe um "*" ao lado do
    valor quando o p-valor daquele par é < alpha (default 0.05).

    Parâmetros
    ----------
    df_agg : DataFrame Spark ou pandas retornado por build_feature_target_stats_df,
        contendo a coluna team_col (ex: "defendingTeamName") entre as chaves
        de agrupamento.
    features : str ou list[str]
        Nome(s) da(s) feature(s) originais (sem prefixo de agregação).
    target : str
        Nome da coluna alvo original (sem prefixo de agregação).
    team_col : str
        Nome da coluna de time usada como chave de agrupamento extra.
    feature_agg : str
        Chave de AGG_FUNCS_FEATURES a usar pra TODAS as features (ex: "avg").
    target_aggs : str ou list[str]
        Chave(s) de AGG_FUNCS_TARGET a usar pro target (default "max").
    max_teams : int
        Quantidade máxima de times (heatmaps) a plotar, pra não gerar uma
        lista enorme de gráficos (default 5).
    alpha : float
        Limiar de significância pro "*" (default 0.05).
    """
    if isinstance(features, str):
        features = [features]
    if isinstance(target_aggs, str):
        target_aggs = [target_aggs]

    df_agg_pd = df_agg.toPandas() if not isinstance(df_agg, pd.DataFrame) else df_agg

    feature_cols = [f"{feature_agg}_{feature}" for feature in features]
    target_cols = [f"{ta}_{target}" for ta in target_aggs]

    teams = sorted(df_agg_pd[team_col].dropna().unique())[:max_teams]

    for team in teams:
        df_team_pd = df_agg_pd[df_agg_pd[team_col] == team]
        corr, pvals = _corr_pvalue_matrix(df_team_pd, feature_cols + target_cols)
        text = _corr_text_with_significance(corr, pvals, alpha)

        fig = go.Figure(
            data=go.Heatmap(
                z=corr.values,
                x=corr.columns,
                y=corr.columns,
                colorscale='RdBu',
                zmin=-1,
                zmax=1,
                text=text.values,
                texttemplate="%{text}",
                colorbar=dict(title="Correlação"),
            )
        )

        fig.update_layout(
            title=f"Correlação (Spearman) — features ({feature_agg}) x {'/'.join(target_aggs)}_{target} — {team}",
            template="simple_white",
            height=700,
            width=1000,
            xaxis=dict(tickangle=-45),
        )

        fig.show()


def _plot_position_bin_heatmap(df_agg_pd, features, target, feature_agg, target_agg, bin_col, title_suffix="", alpha=0.05):
    """Monta a matriz features x faixas e desenha UM heatmap — usada por plot_correlation_by_position_bin e plot_correlation_by_position_bin_by_team. Célula recebe "*" quando o p-valor daquele par (feature, faixa) é < alpha."""
    target_col = f"{target_agg}_{target}"
    bin_values = [b for b in df_agg_pd[bin_col].cat.categories if b in df_agg_pd[bin_col].values]

    z = []
    p = []
    for feature in features:
        feature_col = f"{feature_agg}_{feature}"
        row_z = []
        row_p = []
        for b in bin_values:
            df_bin = df_agg_pd[df_agg_pd[bin_col] == b][[feature_col, target_col]].dropna()
            if len(df_bin) >= 3:
                r, pvalue = stats.spearmanr(df_bin[feature_col], df_bin[target_col])
            else:
                r, pvalue = np.nan, np.nan
            row_z.append(r)
            row_p.append(pvalue)
        z.append(row_z)
        p.append(row_p)

    x_labels = [str(b) for b in bin_values]
    z = np.array(z)
    p = np.array(p)

    text = np.where(p < alpha, np.char.add(np.round(z, 3).astype(str), '*'), np.round(z, 3).astype(str))

    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=x_labels,
            y=features,
            colorscale='RdBu',
            zmin=-1,
            zmax=1,
            text=text,
            texttemplate="%{text}",
            colorbar=dict(title="Correlação"),
        )
    )

    fig.update_layout(
        title=f"Correlação (Spearman) por faixa de {bin_col} — features ({feature_agg}) x {target_agg}_{target}{title_suffix}<br><sup>Faixas: {' | '.join(x_labels)}</sup>",
        template="simple_white",
        height=700,
        width=1000,
        xaxis=dict(tickangle=-45),
    )

    fig.show()


def plot_correlation_by_position_bin(df_agg_pd, features, target, feature_agg, target_agg, bin_col, alpha=0.05):
    """
    Um único heatmap: linhas = features, colunas = faixas de bin_col,
    células = correlação (Spearman) daquela feature com o target, calculada
    SEPARADAMENTE dentro de cada faixa (filtra df_agg_pd pela faixa antes de
    rodar .corr()). Serve pra checar se a correlação feature x target se
    sustenta em diferentes zonas do campo, ou se é puxada por confundimento
    posicional — ameaça e compactação defensiva tendem a subir juntas perto
    do próprio gol, então uma correlação alta na base inteira pode ser só
    "as duas coisas acontecem perto do gol", não um efeito real da forma
    defensiva. Ao contrário de plot_correlation_heatmap, aqui cada feature
    entra com UMA única agregação (não expande AGG_FUNCS_FEATURES inteiro),
    já que o objetivo é comparar zonas, não comparar tipos de agregação.
    Célula recebe um "*" ao lado do valor quando o p-valor daquele par é
    < alpha (default 0.05).

    Parâmetros
    ----------
    df_agg_pd : pandas.DataFrame
        Já deve conter as colunas "{agg}_{feature}"/"{target_agg}_{target}"
        e a coluna bin_col (categórica, ex: gerada por pd.cut).
    features : str ou list[str]
        Nome(s) da(s) feature(s) originais (sem prefixo de agregação).
    target : str
        Nome da coluna alvo original (sem prefixo de agregação).
    feature_agg : str
        Chave de AGG_FUNCS_FEATURES a usar — a MESMA agregação pra todas as
        features (ex: "min").
    target_agg : str
        Chave de AGG_FUNCS_TARGET a usar pro target (uma só, ex: "max").
    bin_col : str
        Nome da coluna categórica de faixas de posição (ex: "ball_x_at_max_bin").
    alpha : float
        Limiar de significância pro "*" (default 0.05).
    """
    if isinstance(features, str):
        features = [features]

    _plot_position_bin_heatmap(df_agg_pd, features, target, feature_agg, target_agg, bin_col, alpha=alpha)


def plot_correlation_by_position_bin_by_team(df_agg_pd, features, target, team_col, feature_agg, target_agg, bin_col, max_teams=5, alpha=0.05):
    """
    Igual a plot_correlation_by_position_bin, mas um heatmap por time —
    filtra df_agg_pd pelos valores distintos de team_col (limitado a
    max_teams, pra não gerar uma quantidade enorme de heatmaps) e roda o
    mesmo cálculo por faixa dentro de cada time, com o nome do time no
    título. Serve pra ver se o padrão por zona de campo (visto na base
    inteira) se sustenta time a time.

    Parâmetros
    ----------
    df_agg_pd : pandas.DataFrame
        Já deve conter as colunas "{agg}_{feature}"/"{target_agg}_{target}",
        a coluna bin_col e a coluna team_col.
    features : str ou list[str]
        Nome(s) da(s) feature(s) originais (sem prefixo de agregação).
    target : str
        Nome da coluna alvo original (sem prefixo de agregação).
    team_col : str
        Nome da coluna de time usada como chave de agrupamento extra.
    feature_agg : str
        Chave de AGG_FUNCS_FEATURES a usar — a MESMA agregação pra todas as
        features (ex: "min").
    target_agg : str
        Chave de AGG_FUNCS_TARGET a usar pro target (uma só, ex: "max").
    bin_col : str
        Nome da coluna categórica de faixas de posição (ex: "ball_x_at_max_bin").
    max_teams : int
        Quantidade máxima de times (heatmaps) a plotar (default 5).
    alpha : float
        Limiar de significância pro "*" (default 0.05).
    """
    if isinstance(features, str):
        features = [features]

    teams = sorted(df_agg_pd[team_col].dropna().unique())[:max_teams]

    for team in teams:
        df_team_pd = df_agg_pd[df_agg_pd[team_col] == team]
        _plot_position_bin_heatmap(
            df_team_pd, features, target, feature_agg, target_agg, bin_col, title_suffix=f" — {team}", alpha=alpha
        )
