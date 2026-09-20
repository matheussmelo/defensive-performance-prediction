"""
Heatmaps de correlação a partir de uma lista pronta de colunas (`corr_cols`)
sobre um DataFrame já agregado no nível time-partida. Copiadas tal como
estavam em threat_score_analysis.ipynb — ainda não estão sendo
importadas/usadas lá, só centralizadas aqui pra reaproveitamento futuro.

Atenção: existe uma OUTRA família de plots de correlação em
feature_target_correlation_plots.py (de eda_cycle_start_gk.ipynb /
eda_cycle_start_all.ipynb) com uma `plot_correlation_heatmap` de mesmo nome,
mas assinatura/comportamento diferentes (aquela expande combinações
agregação×feature; esta aqui recebe `corr_cols` prontas). Não são a mesma
função — por isso ficam em módulos separados, sem tentar unificar os nomes.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy import stats


def plot_correlation_heatmap(df_agg, corr_cols):
    """
    Constrói o df agregado (via build_aggregated_df), converte para pandas,
    calcula a matriz de correlação das colunas em `corr_cols` e plota um
    heatmap com Plotly.
    """

    df_agg_pd = df_agg.toPandas()

    corr = df_agg_pd[corr_cols].corr(method='spearman')

    fig = go.Figure(
        data=go.Heatmap(
            z=corr.values,
            x=corr.columns,
            y=corr.columns,
            colorscale='RdBu',
            zmin=-1,
            zmax=1,
            text=corr.round(2).values,
            texttemplate="%{text}",
            colorbar=dict(title="Correlação"),
        )
    )

    fig.update_layout(
        title="Matriz de Correlação",
        template="simple_white",
        width=1500,
        height=900,
        xaxis=dict(tickangle=-45),
    )

    fig.show()


def plot_pvalue_heatmap(df_agg, corr_cols, method='spearman', alpha=0.05):
    """
    Calcula a matriz de p-valor (via scipy) pro mesmo conjunto de colunas
    usado no heatmap de correlação, e plota com Plotly. Célula com
    p-valor < alpha recebe um "*" ao lado do número pra marcar significância.
    Usa pares completos (dropna por par de colunas), igual ao .corr() do pandas.
    """

    df_agg_pd = df_agg.toPandas()

    corr_func = stats.spearmanr if method == 'spearman' else stats.pearsonr

    # matriz de p-valor, mesma ordem/eixos do heatmap de correlação
    pvals = pd.DataFrame(np.nan, index=corr_cols, columns=corr_cols)

    for i, col_i in enumerate(corr_cols):
        for j, col_j in enumerate(corr_cols):
            if j < i:
                continue
            if i == j:
                # correlação de uma coluna com ela mesma é trivial (r=1, p=0);
                # calcular via scipy aqui quebraria (colunas duplicadas no select)
                pvals.loc[col_i, col_j] = 0.0
                continue
            paired = df_agg_pd[[col_i, col_j]].dropna()
            pvalue = np.nan if len(paired) < 3 else corr_func(paired[col_i], paired[col_j])[1]
            pvals.loc[col_i, col_j] = pvalue
            pvals.loc[col_j, col_i] = pvalue

    # texto da célula com "*" pra marcar p-valor < alpha
    text = pvals.round(3).astype(str)
    text = text.where(pvals >= alpha, text + '*')

    fig = go.Figure(
        data=go.Heatmap(
            z=pvals.values,
            x=pvals.columns,
            y=pvals.columns,
            colorscale='Blues',
            reversescale=True,
            zmin=0,
            zmax=1,
            text=text.values,
            texttemplate="%{text}",
            colorbar=dict(title="p-valor"),
        )
    )

    fig.update_layout(
        title=f"Matriz de p-valor ({method}) — * indica p < {alpha}",
        template="simple_white",
        width=1500,
        height=900,
        xaxis=dict(tickangle=-45),
    )

    fig.show()


def plot_correlation_significance_heatmap(df_agg, corr_cols, method='spearman', alpha=0.005):
    """
    Combina plot_correlation_heatmap e plot_pvalue_heatmap num heatmap só:
    a cor e o valor mostrado em cada célula são a correlação (mesma paleta
    RdBu de plot_correlation_heatmap), mas o texto ganha um "*" ao lado
    quando o p-valor daquele par é < alpha — dá pra ver força e
    significância ao mesmo tempo, sem precisar de dois gráficos separados.
    Usa pares completos (dropna por par de colunas), igual ao .corr() do
    pandas e ao plot_pvalue_heatmap.
    """
    df_agg_pd = df_agg.toPandas()

    corr_func = stats.spearmanr if method == 'spearman' else stats.pearsonr

    corr = df_agg_pd[corr_cols].corr(method=method)

    # matriz de p-valor, mesma ordem/eixos da matriz de correlação
    pvals = pd.DataFrame(np.nan, index=corr_cols, columns=corr_cols)
    for i, col_i in enumerate(corr_cols):
        for j, col_j in enumerate(corr_cols):
            if j < i:
                continue
            if i == j:
                # correlação de uma coluna com ela mesma é trivial (r=1, p=0)
                pvals.loc[col_i, col_j] = 0.0
                continue
            paired = df_agg_pd[[col_i, col_j]].dropna()
            pvalue = np.nan if len(paired) < 3 else corr_func(paired[col_i], paired[col_j])[1]
            pvals.loc[col_i, col_j] = pvalue
            pvals.loc[col_j, col_i] = pvalue

    # texto da célula = valor de correlação, com "*" quando p-valor < alpha
    text = corr.round(2).astype(str)
    text = text.where(pvals >= alpha, text + '*')

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
        title=f"Matriz de Correlação ({method}) — * indica p-valor < {alpha}",
        template="simple_white",
        width=1500,
        height=900,
        xaxis=dict(tickangle=-45),
    )

    fig.show()
