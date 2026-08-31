import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

import sys
import os

import asyncio

import time
import math

import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.gradient_client import GradientSportsClient

pd.set_option('display.max_columns', None)
os.environ.setdefault("PYARROW_NUM_THREADS", "2")

# Concorrência das chamadas à API
SEM_LIMIT = 5
semaphore = asyncio.Semaphore(SEM_LIMIT)

# Para evitar criar centenas de tasks de uma vez
TASKS_BATCH = 50  # ajuste conforme sua máquina

# Base de saída
BASE_EVENTS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "events_teste"
BASE_EVENTS_DIR.mkdir(parents=True, exist_ok=True)

# Schema fixo pros campos aninhados (homePlayers_parsed/awayPlayers_parsed/balls_parsed/details_parsed) —
# grava já estruturado no parquet, sem passar por JSON string. Substitui o que
# antes só existia como pós-processamento em parse_possession_events.ipynb. Mantém
# o sufixo _parsed nos nomes de coluna por convenção, mesmo já vindo estruturado.
_PA_PLAYER_STRUCT = pa.struct([
    pa.field("x", pa.float32()),
    pa.field("y", pa.float32()),
    pa.field("player", pa.struct([pa.field("name", pa.string())])),
])
_PA_BALL_STRUCT = pa.struct([
    pa.field("x", pa.float32()),
    pa.field("y", pa.float32()),
    pa.field("z", pa.float32()),
])

NESTED_SCHEMA_OVERRIDES = {
    "homePlayers_parsed": pa.list_(_PA_PLAYER_STRUCT),
    "awayPlayers_parsed": pa.list_(_PA_PLAYER_STRUCT),
    "balls_parsed": pa.list_(_PA_BALL_STRUCT),
    "details_parsed": pa.map_(pa.string(), pa.string()),
}

client = GradientSportsClient()

# ============================================================
# Chave de tipo/outcome por eventType dentro de details
# ============================================================
# Cada eventType guarda o "tipo" específico e o "outcome" dele numa chave
# diferente do dict de details. Quando o eventType não tem uma dessas chaves
# (ex: Clearance não tem tipo, kickoff não tem outcome), fica None.
EVENT_TYPE_DESC_KEY = {
    'OTB': 'setpieceTypeDescription',
    'FIRSTKICKOFF': 'setpieceTypeDescription',
    'SECONDKICKOFF': 'setpieceTypeDescription',
    'BC': 'carryTypeDescription',
    'CH': 'challengeTypeDescription',
    'FO': 'challengeTypeDescription',
    'CR': 'crossTypeDescription',
    'PA': 'passTypeDescription',
    'SH': 'shotTypeDescription',
    'TC': 'touchTypeDescription',
    # CL (Clearance) e RE (Rebound) não têm chave de tipo
}

EVENT_OUTCOME_DESC_KEY = {
    'BC': 'ballCarryOutcomeDescription',
    'CH': 'challengeOutcomeTypeDescription',
    'FO': 'challengeOutcomeTypeDescription',
    'CL': 'clearanceOutcomeTypeDescription',
    'CR': 'crossOutcomeTypeDescription',
    'PA': 'passOutcomeTypeDescription',
    'RE': 'reboundOutcomeTypeDescription',
    'SH': 'shotOutcomeTypeDescription',
    'TC': 'touchOutcomeTypeDescription',
    # OTB e os kickoffs não têm chave de outcome
}


def _slim_player(p):
    """Reduz um jogador do tracking só aos campos usados (x, y, player.name)."""
    if not isinstance(p, dict):
        return None
    inner = p.get("player") or {}
    return {
        "x": p.get("x"),
        "y": p.get("y"),
        "player": {"name": inner.get("name") if isinstance(inner, dict) else None},
    }


def _slim_ball(b):
    """Reduz uma posição de bola do tracking só aos campos usados (x, y, z)."""
    if not isinstance(b, dict):
        return None
    return {"x": b.get("x"), "y": b.get("y"), "z": b.get("z")}


def _stringify_details(d):
    """Converte todos os valores de details pra string (map<string,string>)."""
    if not isinstance(d, dict):
        return {}
    return {str(k): (None if v is None else str(v)) for k, v in d.items()}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    - Renomeia colunas com ponto pra camelCase (id -> eventId, player.id -> eventPlayerId, ...).
    - Deriva eventSubTypeDescription/eventOutcomeDescription a partir de details + eventType
      (mesma lógica que antes só existia em parse_possession_events.ipynb).
    - Reduz homePlayers/awayPlayers/balls só aos campos usados e converte os valores de
      details pra string — mas mantém tudo como estrutura nativa (dict/list), sem
      serializar pra JSON string, pra já gravar tipado no parquet (ver NESTED_SCHEMA_OVERRIDES).
      Renomeia essas 4 colunas com sufixo _parsed ao final, por convenção.
    - Tipa homeTeam como boolean nulo e os IDs como inteiros nulos.
    """
    df = df.rename(columns={
        "id": "eventId",
        "player.id": "eventPlayerId",
        "player.name": "eventPlayerName",
        "team.id": "eventTeamId",
        "team.name": "eventTeamName",
    })

    if "details" in df.columns:
        type_keys = df["eventType"].map(EVENT_TYPE_DESC_KEY)
        outcome_keys = df["eventType"].map(EVENT_OUTCOME_DESC_KEY)

        df["eventSubTypeDescription"] = [
            d.get(k) if isinstance(d, dict) and k is not None else None
            for d, k in zip(df["details"], type_keys)
        ]
        df["eventOutcomeDescription"] = [
            d.get(k) if isinstance(d, dict) and k is not None else None
            for d, k in zip(df["details"], outcome_keys)
        ]

        df["details"] = df["details"].map(_stringify_details)

    for c in ["homePlayers", "awayPlayers"]:
        if c in df.columns:
            df[c] = df[c].map(lambda lst: [_slim_player(p) for p in lst] if isinstance(lst, list) else [])

    if "balls" in df.columns:
        df["balls"] = df["balls"].map(lambda lst: [_slim_ball(b) for b in lst] if isinstance(lst, list) else [])

    # homeTeam como boolean nulo
    if "homeTeam" in df.columns:
        df["homeTeam"] = (
            df["homeTeam"]
            .map(lambda v: None if pd.isna(v) else (bool(v) if not isinstance(v, str) else (v.lower() == "true")))
            .astype("boolean")
        )

    # IDs numéricos opcionais como inteiros nulos
    for c in ["eventPlayerId", "eventTeamId"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

    # Estabiliza dtypes das colunas escalares (não mexe em homePlayers/awayPlayers/balls/details)
    scalar_cols = [c for c in df.columns if c not in ("homePlayers", "awayPlayers", "balls", "details")]
    df[scalar_cols] = df[scalar_cols].convert_dtypes()

    df = df.rename(columns={
        "homePlayers": "homePlayers_parsed",
        "awayPlayers": "awayPlayers_parsed",
        "balls": "balls_parsed",
        "details": "details_parsed",
    })

    return df


async def fetch_game_events(game, index, total):
    game_id = game['gameId']
    game_season = game['season']
    game_competition = game['competitionId']

    async with semaphore:
        print(f"[{index + 1} / {total}] Starting request for game: {game_id}, competition id: {game_competition}, season: {game_season}")
        start_time = time.perf_counter()

        # pequeno espaçamento para não rajar a API
        await asyncio.sleep(0.2)

        # Offload da chamada síncrona para thread
        df = await asyncio.to_thread(
            client.get_game_events_flat,
            game_id,
            as_dataframe=True
        )

        elapsed = time.perf_counter() - start_time
        print(f"[{index + 1} / {total}] Finished request for game {game_id} in {elapsed:.2f} seconds")

    # Enriquecimento padronizado
    df['competitionId'] = game_competition
    df['gameId'] = game_id
    df['season'] = game_season

    # Normalização: renomeia colunas, deriva eventSubTypeDescription/eventOutcomeDescription,
    # tipa boolean/ids, e mantém homePlayers_parsed/awayPlayers_parsed/balls_parsed/details_parsed
    # nativos (sem JSON string)
    df = normalize_columns(df)

    return df, game_competition, game_season, game_id


async def write_shard(games_sublist, shard_idx, competition_id, season, events_dir):
    """
    Escreve um shard (metade da temporada) em um único arquivo parquet.
    Cada jogo = 1 row group.
    Retorna o index_map parcial: {gameId: {"file": file_name, "row_group": idx}}
    """
    shard_file = events_dir / f"events_{competition_id}_{season}_part{shard_idx+1}.parquet"
    if shard_file.exists():
        shard_file.unlink(missing_ok=True)

    index_map = {}
    writer = None
    schema = None
    row_group_idx = 0

    # Processa em lotes para não criar muitas tasks de uma vez
    total = len(games_sublist)
    for start in range(0, total, TASKS_BATCH):
        batch = games_sublist[start:start+TASKS_BATCH]
        # Cria tasks de fetch para o batch atual
        tasks = [
            asyncio.create_task(fetch_game_events(game, start + i, len(games_sublist)))
            for i, game in enumerate(batch)
        ]

        # Consome conforme concluírem
        for coro in asyncio.as_completed(tasks):
            df, _, _, game_id = await coro

            if writer is None:
                # Constrói tabela, forçando nullable=True e o schema fixo dos campos
                # aninhados (NESTED_SCHEMA_OVERRIDES), em vez de deixar o pyarrow inferir
                table_first = pa.Table.from_pandas(df, preserve_index=False)
                schema_nullable = pa.schema(
                    [
                        pa.field(f.name, NESTED_SCHEMA_OVERRIDES.get(f.name, f.type), nullable=True)
                        for f in table_first.schema
                    ],
                    metadata=table_first.schema.metadata
                )
                table_first = pa.Table.from_pandas(df, schema=schema_nullable, preserve_index=False)

                schema = schema_nullable
                writer = pq.ParquetWriter(
                    where=str(shard_file),
                    schema=schema,
                    compression="snappy",
                    use_dictionary=True,
                    write_statistics=True
                )
                await asyncio.to_thread(writer.write_table, table_first, row_group_size=len(df))
            else:
                table = pa.Table.from_pandas(df, schema=schema, preserve_index=False)
                await asyncio.to_thread(writer.write_table, table, row_group_size=len(df))

            index_map[str(game_id)] = {"file": shard_file.name, "row_group": row_group_idx}
            row_group_idx += 1

            del df
            print(f"[shard {shard_idx+1}] Appended game {game_id} as row group {row_group_idx - 1}")

    if writer is not None:
        writer.close()

    print(f"[shard {shard_idx+1}] Saved {shard_file.name} with {row_group_idx} row groups")
    return index_map


async def process_group(group_df):
    """
    Para (competitionId, season), grava 2 arquivos Parquet (part1 e part2).
    Cada jogo = 1 row group.
    Gera um índice único {gameId -> {"file": ..., "row_group": ...}} para a temporada.
    """
    games_list = group_df.to_dict("records")
    total = len(games_list)
    if total == 0:
        return

    competition_id = games_list[0]['competitionId']
    season = games_list[0]['season']

    # Diretório por competição/temporada
    events_dir = BASE_EVENTS_DIR / f"{competition_id}" / f"{season}"
    events_dir.mkdir(parents=True, exist_ok=True)

    # Limpa possíveis arquivos/índice anteriores
    for p in events_dir.glob(f"events_{competition_id}_{season}*.parquet"):
        p.unlink(missing_ok=True)
    index_path = events_dir / f"events_{competition_id}_{season}_index.json"
    if index_path.exists():
        index_path.unlink(missing_ok=True)

    # Define split em 2 shards (primeiro recebe o +1 se total for ímpar)
    mid = math.ceil(total / 2)
    shards = [games_list[:mid], games_list[mid:]]

    # Escreve shards sequencialmente para estabilizar I/O
    combined_index = {}
    for shard_idx, sublist in enumerate(shards):
        if not sublist:
            continue
        shard_index = await write_shard(sublist, shard_idx, competition_id, season, events_dir)
        combined_index.update(shard_index)

    # Salva índice único da temporada
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({
            "competitionId": competition_id,
            "season": season,
            "index": combined_index  # gameId -> {file, row_group}
        }, f, ensure_ascii=False, indent=2)

    print(f"Index saved: {index_path.name} with {len(combined_index)} games")


async def main():
    # health check
    print(client.get_status())

    games = pd.read_csv(str(Path(__file__).resolve().parent.parent.parent / "data" / "games.csv"))

    # remover jogos da temporada atual pois não serão usados
    games = games[~games['season'].isin(['2025-2026', '2026'])].reset_index(drop=True)

    # TESTE: restringe a extração à competição 1, temporada 2022-2023
    games = games[
        (games['competitionId'] == 1) & (games['season'] == '2022-2023')
    ].reset_index(drop=True)

    grouped = games.groupby(['competitionId', 'season'])
    for (competition_id, season), group_df in grouped:

        print(f"\nProcessing competition id {competition_id}, season {season} - {len(group_df)} games")

        await process_group(group_df.sort_values('date'))

        print(f"Process completed for competition id {competition_id}, season {season}")


if __name__ == "__main__":
    asyncio.run(main())