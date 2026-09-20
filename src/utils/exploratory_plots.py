"""
Plots exploratórios genéricos (histograma/boxplot/linha) sobre uma coluna de
um DataFrame Spark. Copiadas tal como estavam em threat_score_analysis.ipynb
/ threat_score_impact_analysis.ipynb — ainda não estão sendo
importadas/usadas lá, só centralizadas aqui pra reaproveitamento futuro.
"""

import plotly.graph_objects as go


def plot_histogram(df, column, nbins=None, title=None, color="#2E5EAA"):
    pdf = df.select(column).toPandas()

    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=pdf[column],
            nbinsx=nbins,
            marker=dict(color=color),
            name=column,
        )
    )

    fig.update_layout(
        template="simple_white",
        title=title or f"Distribuição de {column}",
        xaxis_title=column,
        yaxis_title="Frequência",
        height=600,
        width=1000
    )

    fig.show()


def plot_boxplot(df, column, title=None, color="#2E5EAA"):
    pdf = df.select(column).toPandas()

    fig = go.Figure()
    fig.add_trace(
        go.Box(
            y=pdf[column],
            marker=dict(color=color),
            name=column,
            boxpoints="outliers",
        )
    )

    fig.update_layout(
        template="simple_white",
        title=title or f"Boxplot de {column}",
        yaxis_title=column,
        height=600,
        width=1000
    )

    fig.show()


def plot_line(df, column, x=None, title=None, color="#2E5EAA"):
    cols = [x, column] if x is not None else [column]
    pdf = df.select(*cols).toPandas()

    x_values = pdf[x] if x is not None else pdf.index
    median = float(pdf[column].median())

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x_values,
            y=pdf[column],
            mode="lines",
            line=dict(color=color, width=2),
            name=column,
        )
    )

    fig.add_shape(
        type="line",
        xref="paper",
        x0=0,
        x1=1,
        yref="y",
        y0=median,
        y1=median,
        line=dict(color="red", dash="dash", width=2),
    )

    fig.update_layout(
        template="simple_white",
        title=title or f"{column} ao longo do tempo",
        xaxis_title=x or "Índice",
        yaxis_title=column,
        height=600,
        width=1500,
    )

    fig.show()
