import pandas as pd

import sys

import asyncio

import time

from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.gradient_client import GradientSportsClient

pd.set_option('display.max_columns', None)

# Concorrência das chamadas à API
SEM_LIMIT = 5
semaphore = asyncio.Semaphore(SEM_LIMIT)

# Para evitar criar centenas de tasks de uma vez
TASKS_BATCH = 50  # ajuste conforme sua máquina

# Base de saída
BASE_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
OUTPUT_PATH = BASE_DATA_DIR / "games_players.csv"

client = GradientSportsClient()

# Dicionário de posições (playerPosition -> descrição + categoria ampla D/M/A),
# baseado em positions.md. GK entra como D (goleiro conta como linha
# defensiva na categoria ampla, conforme o dicionário). LWB/RWB e AM têm
# maior risco de classificação errada por sigla fixa (ver positions.md) —
# mapeados aqui pelo prior da tabela, sem ajuste dinâmico pela posição em campo.
POSITION_INFO = {
    "GK":  ("Goalkeeper", "D"),
    "LB":  ("Left Back", "D"),
    "RB":  ("Right Back", "D"),
    "LCB": ("Left Centre-Back", "D"),
    "RCB": ("Right Centre-Back", "D"),
    "MCB": ("Middle Centre-Back", "D"),
    "D":   ("Defender", "D"),
    "LWB": ("Left Wing-Back", "D"),
    "RWB": ("Right Wing-Back", "D"),
    "DM":  ("Defensive Midfielder", "M"),
    "CM":  ("Central Midfielder", "M"),
    "M":   ("Midfielder", "M"),
    "AM":  ("Attacking Midfielder", "M"),
    "LM":  ("Left Midfielder", "M"),
    "RM":  ("Right Midfielder", "M"),
    "LW":  ("Left Winger", "A"),
    "RW":  ("Right Winger", "A"),
    "F":   ("Forward", "A"),
    "CF":  ("Centre-Forward", "A"),
}


async def fetch_game_players(game_id, index, total):
    async with semaphore:
        print(f"[{index + 1} / {total}] Starting request for game physical metrics: {game_id}")
        start_time = time.perf_counter()

        # pequeno espaçamento para não rajar a API
        await asyncio.sleep(0.2)

        # Offload da chamada síncrona para thread
        df = await asyncio.to_thread(
            client.query_game_physical_metrics,
            game_id,
            possessions=["ALL"],
            as_dataframe=True
        )

        elapsed = time.perf_counter() - start_time
        print(f"[{index + 1} / {total}] Finished request for game {game_id} in {elapsed:.2f} seconds")

    df['gameId'] = game_id

    # Reduz de (jogador x métrica) pra 1 registro por jogador na partida —
    # as colunas de métrica não interessam aqui, só quem jogou por quem
    df = df.drop(['possession', 'updatedAt', 'metric.name', 'metric.p90', 'metric.raw'], axis=1).drop_duplicates()

    return df, game_id


async def fetch_all_games_players(game_ids):
    """
    Busca jogadores/times de todos os jogos em lotes, pra não criar milhares
    de tasks de uma vez (mesmo padrão de extract_possession_events.py).
    """
    dfs = []
    total = len(game_ids)

    for start in range(0, total, TASKS_BATCH):
        batch = game_ids[start:start + TASKS_BATCH]
        tasks = [
            asyncio.create_task(fetch_game_players(game_id, start + i, total))
            for i, game_id in enumerate(batch)
        ]

        for coro in asyncio.as_completed(tasks):
            df, game_id = await coro
            dfs.append(df)
            print(f"Appended game {game_id} ({len(dfs)} / {total})")

    return pd.concat(dfs, ignore_index=True)


async def main():
    # health check
    print(client.get_status())

    games = pd.read_csv(str(BASE_DATA_DIR / "games.csv"))

    # remover jogos das temporadas em andamento (ainda não finalizadas)
    games = games[~games['season'].isin(['2025-2026', '2026'])].reset_index(drop=True)

    game_ids = games['gameId'].unique().tolist()

    df_games_players = await fetch_all_games_players(game_ids)

    # Enriquece playerPosition com descrição e categoria ampla (D/M/A) —
    # playerPosition em si já é o "type"; essas duas colunas viram
    # typeDescription/groupType quando o dado for aninhado em target_engineering.ipynb.
    # Sigla fora de POSITION_INFO (positions.md desatualizado) -> ambas ficam NULL
    unknown_positions = sorted(set(df_games_players["playerPosition"].dropna()) - set(POSITION_INFO))
    if unknown_positions:
        print(f"Atenção: siglas de posição fora de POSITION_INFO (ficarão NULL): {unknown_positions}")

    df_games_players["playerPositionTypeDescription"] = df_games_players["playerPosition"].map(
        lambda p: POSITION_INFO.get(p, (None, None))[0]
    )
    df_games_players["playerPositionGroupType"] = df_games_players["playerPosition"].map(
        lambda p: POSITION_INFO.get(p, (None, None))[1]
    )

    df_games_players.to_csv(str(OUTPUT_PATH), index=False)
    print(f"Saved {OUTPUT_PATH.name} with {len(df_games_players)} rows for {len(game_ids)} games")


if __name__ == "__main__":
    asyncio.run(main())
