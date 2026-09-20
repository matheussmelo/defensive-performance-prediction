"""
Funções de junção com estatísticas de partida e seleção por lado (time da
casa/visitante, ou quem atacava/defendia). Copiadas tal como estavam em
threat_score_analysis.ipynb / threat_score_impact_analysis.ipynb — ainda não
estão sendo importadas/usadas lá, só centralizadas aqui pra reaproveitamento
futuro.
"""

from pyspark.sql import functions as F


def join_match_stats(df, df_match_stats):

    # adiciona estatísticas da partida
    return (
        df.join(
            df_match_stats,
            on=[
                "date",
                "homeTeamName",
                "opponentTeamName"
            ],
            how="left"
        )
    )


def build_side_df(df, is_home, avg_cols):

    # filtra mandante ou visitante
    side_filter = F.col('homeTeam') if is_home else ~F.col('homeTeam')

    # mapeamento das colunas conforme o lado
    cols = {
        "teamName": "homeTeamName" if is_home else "opponentTeamName",
        "win": (F.col("FTR") == ('H' if is_home else 'A')),
        "goals": "FTHG" if is_home else "FTAG",
        "shots": "HS" if is_home else "AS",
        "shots_target": "HST" if is_home else "AST",
        "avg_win_odds": "AvgH" if is_home else "AvgA",
    }

    # colunas fixas
    fixed_select = [
        'competitionName',
        'season',
        'gameId',
        "date",
        F.col(cols["teamName"]).alias("teamName"),
    ]

    # métricas agregadas
    avg_select = [F.col(c) for c in avg_cols]

    # estatísticas da partida
    result_select = [
        cols["win"].alias("win"),
        F.col(cols["goals"]).alias("goals"),
        F.col(cols["shots"]).alias("shots"),
        F.col(cols["shots_target"]).alias("shots_target"),
        F.col(cols["avg_win_odds"]).alias("avg_win_odds"),
    ]

    return (
        df
        .filter(side_filter)
        .select(*fixed_select, *avg_select, *result_select)
    )


def build_defending_side_df(df, is_home, avg_cols):
    """
    Espelha build_side_df, mas pra medir threat_score_impact do lado que
    DEFENDEU no ciclo/evento, não do lado que atacava — e associa a esse
    time as estatísticas de partida que ele SOFREU (do adversário), não as
    que ele gerou.

    Por que a perspectiva é invertida (duas inversões, nesta função):

    1) Filtro de lado (linhas -> time): em build_side_df, a flag `homeTeam`
       indica quem tinha a POSSE (estava atacando), e a métrica agregada é
       atribuída a esse mesmo time atacante — faz sentido pro threat_score,
       que mede a ameaça GERADA por quem ataca. threat_score_impact mede o
       efeito de um evento normalmente DEFENSIVO (uma interceptação, um
       desarme) na ameaça — o time relevante pra essa métrica é quem estava
       DEFENDENDO, ou seja, o lado OPOSTO ao indicado por `homeTeam`. Por
       isso `side_filter` aqui é o inverso de build_side_df: is_home=True
       seleciona linhas onde o mandante DEFENDEU (`~homeTeam`, isto é, o
       visitante estava com a posse), não onde ele atacou.

    2) Estatísticas de partida (colunas de resultado): como a métrica agora
       representa o que o time DEFENDEU/evitou, não faz sentido correlacionar
       o impacto defensivo de um time com os gols que ELE fez — o que
       importa é o que ele SOFREU. Por isso "goals"/"shots"/"shots_target"
       apontam pras colunas do ADVERSÁRIO na mesma partida (gols sofridos =
       gols do outro lado, chutes sofridos = chutes do outro lado, etc.), e
       "avg_win_odds" usa a odds de vitória do ADVERSÁRIO — a lógica de
       "o quão favorito era quem eu enfrentei", não "o quão favorito eu era".
       "win" NÃO é espelhado: resultado da própria partida (o time em
       questão venceu ou não) é um fato sobre ele mesmo, não algo "sofrido"
       ou "gerado", então segue igual a build_side_df.
    """
    # filtro de lado INVERTIDO em relação a build_side_df: seleciona quem
    # DEFENDEU (não quem atacou) naquele ciclo/evento
    side_filter = ~F.col('homeTeam') if is_home else F.col('homeTeam')

    # mapeamento das colunas conforme o lado, mas com gols/chutes/odds
    # SOFRIDOS (do adversário na mesma partida), não gerados pelo próprio time
    cols = {
        "teamName": "homeTeamName" if is_home else "opponentTeamName",
        "win": (F.col("FTR") == ('H' if is_home else 'A')),  # resultado da própria partida: não espelha
        "goals": "FTAG" if is_home else "FTHG",              # gols sofridos = gols do adversário
        "shots": "AS" if is_home else "HS",                  # chutes sofridos = chutes do adversário
        "shots_target": "AST" if is_home else "HST",         # chutes a gol sofridos = chutes a gol do adversário
        "avg_win_odds": "AvgA" if is_home else "AvgH",       # odds relevante = odds de vitória do adversário
    }

    # colunas fixas
    fixed_select = [
        'competitionName',
        'season',
        'gameId',
        "date",
        F.col(cols["teamName"]).alias("teamName"),
    ]

    # métricas agregadas
    avg_select = [F.col(c) for c in avg_cols]

    # estatísticas da partida (já "espelhadas" pro adversário via cols acima)
    result_select = [
        cols["win"].alias("win"),
        F.col(cols["goals"]).alias("goals"),
        F.col(cols["shots"]).alias("shots"),
        F.col(cols["shots_target"]).alias("shots_target"),
        F.col(cols["avg_win_odds"]).alias("avg_win_odds"),
    ]

    return (
        df
        .filter(side_filter)
        .select(*fixed_select, *avg_select, *result_select)
    )
