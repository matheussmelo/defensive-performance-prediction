# Cliente Gradient Sports API

Cliente Python para a [Physical Performance API](https://interia.gradientsports.com/#tag/Competitions) da Gradient Sports. Fornece acesso a dados de partidas, jogadores, métricas físicas, sprints e corridas de alta velocidade do futebol profissional.

---

## Configuração

### Dependências

```bash
pip install requests pandas python-dotenv
```

### Autenticação

Crie um arquivo `.env` no mesmo diretório do notebook com o token Bearer:

```
BEARER_TOKEN=seu_token_aqui
```

O cliente lê o token automaticamente via `python-dotenv`. Também é possível passá-lo diretamente:

```python
client = GradientSportsClient(token="seu_token_aqui")
```

---

## Instanciação

```python
client = GradientSportsClient()
```

---

## Parâmetro `as_dataframe`

Todos os métodos de busca de dados aceitam o parâmetro `as_dataframe=True`.

- `as_dataframe=False` (padrão): retorna o `dict` JSON bruto da API.
- `as_dataframe=True`: retorna um `pd.DataFrame` no **máximo nível de desagregação** — listas aninhadas são explodidas, dicts aninhados são expandidos com separador `.`.

---

## Tratamento de Erros

Erros HTTP incluem o corpo da resposta da API na mensagem de exceção:

```
HTTPError: 422 Client Error: Unprocessable Entity
API response body: {'errors': [{'title': 'Invalid value', 'source': ...}]}
```

---

## Referência de Métodos

### `get_status()`

Verifica se a API está operacional.

```python
client.get_status()
# → {'data': {'status': 'ok'}}
```

---

### `get_competitions(as_dataframe=False)`

Retorna as competições, temporadas e datasets disponíveis para o usuário autenticado.

```python
client.get_competitions()
client.get_competitions(as_dataframe=True)
```

**Colunas do DataFrame** (`as_dataframe=True`) — 1 linha por (competição × temporada × dataset):

| Coluna | Tipo | Descrição |
|---|---|---|
| `competition.id` | int | ID da competição |
| `competition.name` | str | Nome da competição (ex.: `"Premier League"`) |
| `season` | str | Temporada (ex.: `"2024-2025"`) |
| `datasets` | str | Nome do dataset disponível (ex.: `"physical_metrics"`, `"events"`, `"sprints"`, `"high_speed_runs"`) |

---

### `get_teams(as_dataframe=False)`

Retorna os times e datasets acessíveis pelo usuário.

```python
client.get_teams()
client.get_teams(as_dataframe=True)
```

**Colunas do DataFrame** (`as_dataframe=True`) — 1 linha por (time × competição × dataset):

| Coluna | Tipo | Descrição |
|---|---|---|
| `team.id` | int | ID do time |
| `team.name` | str | Nome do time |
| `competition.id` | int | ID da competição |
| `competition.name` | str | Nome da competição |
| `dataset` | str | Dataset disponível para esse time/competição |

---

### `get_players(as_dataframe=False)`

Retorna a lista completa de jogadores acessíveis.

```python
client.get_players()
client.get_players(as_dataframe=True)
```

**Colunas do DataFrame** (`as_dataframe=True`) — 1 linha por jogador:

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | int | ID único do jogador |
| `name` | str | Nome completo |
| `firstName` | str | Primeiro nome |
| `lastName` | str | Sobrenome |
| `nickname` | str | Apelido |
| `dob` | str | Data de nascimento (`YYYY-MM-DD`) |
| `position` | str | Posição principal |
| `shirtNumber` | str | Número da camisa |
| `athleticismScore` | float | Pontuação de atletismo calculada pela Gradient |
| `transfermarktPlayerId` | int | ID do jogador no Transfermarkt |
| `team.id` | int | ID do time atual |
| `team.name` | str | Nome do time atual |

---

### `get_games(season, competition_id, team_id, as_dataframe=False)`

Retorna a lista de partidas. Todos os filtros são opcionais e combináveis.

```python
client.get_games(season="2024-2025", competition_id=1, as_dataframe=True)
```

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `season` | str | Temporada (ex.: `"2024-2025"`) |
| `competition_id` | int | Filtrar por competição |
| `team_id` | int | Filtrar por time (casa ou visitante) |

**Colunas do DataFrame** (`as_dataframe=True`) — 1 linha por partida:

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | int | ID da partida |
| `date` | str | Data da partida (`YYYY-MM-DD`) |
| `season` | str | Temporada |
| `venueType` | str | Tipo de campo: `TEAM_HOME`, `OPPONENT_HOME`, `NEUTRAL` |
| `teamStartSide` | str | Lado que o time começa: `Left` ou `Right` |
| `teamExtraTimeStartSide` | str | Lado no início da prorrogação |
| `team.id` | int | ID do time principal |
| `team.name` | str | Nome do time principal |
| `competition.id` | int | ID da competição |
| `competition.name` | str | Nome da competição |
| `opponentTeam.id` | int | ID do time adversário |
| `opponentTeam.name` | str | Nome do time adversário |
| `stadium.name` | str | Nome do estádio |
| `stadium.length` | float | Comprimento do campo (metros) |
| `stadium.width` | float | Largura do campo (metros) |

---

### `get_game_events(game_id, as_dataframe=False)`

Retorna os eventos estruturados de uma partida, incluindo detalhes de posse, passes, chutes, duelos e grades de desempenho.

```python
client.get_game_events(game_id=189)
client.get_game_events(game_id=189, as_dataframe=True)
```

**Colunas do DataFrame** (`as_dataframe=True`) — 1 linha por evento de posse:

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | int | ID do game event (evento de jogo pai) |
| `competitionId` | int | ID da competição |
| `gameId` | int | ID da partida |
| `season` | str | Temporada |
| `period` | int | Período: `1` = 1º tempo, `2` = 2º tempo, etc. |
| `periodDescription` | str | Descrição do período (ex.: `"First half"`) |
| `startGameClock` | int | Tempo de início em segundos desde o kick-off |
| `startFormattedGameClock` | str | Tempo de início formatado (ex.: `"45:32"`) |
| `homeTeam` | bool | `True` se o evento é do time da casa |
| `gameEventType` | str | Tipo do game event (ex.: `"FIRSTKICKOFF"`) |
| `gameEventTypeDescription` | str | Descrição do tipo de game event |
| `setpieceType` | str | Código de bola parada (ex.: `"C"` = corner, `"F"` = falta) |
| `setpieceTypeDescription` | str | Descrição da bola parada |
| `touches` | int | Total de toques no game event |
| `touchesInBox` | int | Toques dentro da área |
| `team.id` | int | ID do time no evento |
| `team.name` | str | Nome do time no evento |
| `player.id` | int | ID do jogador principal do evento |
| `player.name` | str | Nome do jogador principal |
| `poss.id` | int | ID do evento de posse |
| `poss.type` | str | Código do tipo de posse (ex.: `"PA"` = passe) |
| `poss.typeDescription` | str | Descrição do tipo de posse |
| `poss.startGameClock` | int | Início do evento de posse (segundos) |
| `poss.endGameClock` | int | Fim do evento de posse (segundos) |
| `poss.period` | int | Período do evento de posse |
| `poss.nonEvent` | bool | `True` se classificado como não-evento |
| `poss.ballHeightType` | str | Altura da bola: `"G"` = no chão |
| `poss.highPointType` | str | Ponto mais alto da bola |
| `poss.bodyType` | str | Parte do corpo usada (ex.: `"RF"` = pé direito) |
| `poss.player.id` | int | ID do jogador do evento de posse |
| `poss.player.name` | str | Nome do jogador do evento de posse |
| `poss.team.id` | int | ID do time do evento de posse |
| `poss.team.name` | str | Nome do time do evento de posse |

---

### `get_game_events_flat(game_id, as_dataframe=False)`

Retorna os eventos de uma partida no formato "achatado" (tracking), com posição e velocidade de cada jogador em campo no momento do evento.

```python
client.get_game_events_flat(game_id=189)
client.get_game_events_flat(game_id=189, as_dataframe=True)
```

**Colunas do DataFrame** (`as_dataframe=True`) — 1 linha por (evento × jogador em campo):

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | int | ID do evento |
| `competitionId` | int | ID da competição |
| `gameId` | int | ID da partida |
| `season` | str | Temporada |
| `period` | int | Período da partida |
| `periodDescription` | str | Descrição do período |
| `eventType` | str | Tipo do evento (ex.: `"FIRSTKICKOFF"`) |
| `eventTypeDescription` | str | Descrição do tipo de evento |
| `startGameClock` | int | Tempo do evento em segundos |
| `startFormattedGameClock` | str | Tempo formatado |
| `homeTeam` | bool | `True` se é o time da casa |
| `player.id` | int | ID do jogador principal do evento |
| `player.name` | str | Nome do jogador principal |
| `team.id` | int | ID do time |
| `team.name` | str | Nome do time |
| `side` | str | `"home"` ou `"away"` — lado do jogador em campo |
| `onpitch.player.id` | int | ID do jogador posicionado em campo |
| `onpitch.player.name` | str | Nome do jogador posicionado em campo |
| `onpitch.jerseyNum` | str | Número da camisa |
| `onpitch.x` | float | Posição X no campo (metros a partir da linha de fundo) |
| `onpitch.y` | float | Posição Y no campo (metros a partir da linha lateral) |
| `onpitch.speed` | float | Velocidade no momento do evento (km/h) |
| `onpitch.visibility` | str | Visibilidade da detecção: `"VISIBLE"`, `"ESTIMATED"` |
| `onpitch.confidence` | str | Confiança da detecção: `"HIGH"`, `"MEDIUM"`, `"LOW"` |

---

### `get_game_physical_metrics(game_id, possessions, as_dataframe=False)`

Retorna métricas físicas por jogador para uma partida via GET. O parâmetro `possessions` é uma string separada por vírgulas.

```python
client.get_game_physical_metrics(game_id=189, possessions="IN,OUT")
client.get_game_physical_metrics(game_id=189, possessions="ALL", as_dataframe=True)
```

### `query_game_physical_metrics(game_id, possessions, as_dataframe=False)`

Versão POST equivalente, com `possessions` como lista.

```python
client.query_game_physical_metrics(game_id=189, possessions=["IN", "OUT"])
client.query_game_physical_metrics(game_id=189, possessions=["ALL"], as_dataframe=True)
```

| Valor `possessions` | Significado |
|---|---|
| `"IN"` | Somente durante posse do time |
| `"OUT"` | Somente fora da posse |
| `"ALL"` | Toda a partida |
| `"NONE"` | Eventos sem posse definida |

**Colunas do DataFrame** (`as_dataframe=True`) — 1 linha por (jogador × métrica):

| Coluna | Tipo | Descrição |
|---|---|---|
| `gameDate` | str | Data da partida (`YYYY-MM-DD`) |
| `season` | str | Temporada |
| `location` | str | `"HOME"` ou `"AWAY"` |
| `possession` | str | Tipo de posse filtrado |
| `playerPosition` | str | Posição do jogador na partida |
| `player.id` | int | ID do jogador |
| `player.name` | str | Nome do jogador |
| `team.id` | int | ID do time |
| `team.name` | str | Nome do time |
| `competition.id` | int | ID da competição |
| `competition.name` | str | Nome da competição |
| `opponentTeam.id` | int | ID do adversário |
| `opponentTeam.name` | str | Nome do adversário |
| `metric.name` | str | Nome da métrica (ver tabela de métricas abaixo) |
| `metric.raw` | float | Valor bruto da métrica na partida |
| `metric.rawPercentile` | float | Percentil do valor bruto em relação ao histórico |

---

### `get_game_sprints(game_id, as_dataframe=False)`

Retorna a lista de sprints da partida.

```python
client.get_game_sprints(game_id=189)
client.get_game_sprints(game_id=189, as_dataframe=True)
```

**Colunas do DataFrame** (`as_dataframe=True`) — 1 linha por sprint:

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | str | ID único do sprint |
| `gameId` | int | ID da partida |
| `gameDate` | str | Data da partida |
| `season` | str | Temporada |
| `period` | int | Período onde ocorreu o sprint |
| `periodElapsedTimeStart` | int | Tempo decorrido no período no início (s) |
| `periodElapsedTimeEnd` | int | Tempo decorrido no período no fim (s) |
| `periodGameClockTimeStart` | int | Tempo do relógio no início (s) |
| `periodGameClockTimeEnd` | int | Tempo do relógio no fim (s) |
| `runTime` | float | Duração do sprint (segundos) |
| `distance` | float | Distância percorrida no sprint (metros) |
| `speedKmh` | float | Velocidade máxima atingida (km/h) |
| `started` | bool | `True` se o sprint foi iniciado dentro do campo |
| `position` | str | Posição do jogador |
| `shirtNumber` | int | Número da camisa |
| `xStart` | float | Posição X de início no campo |
| `yStart` | float | Posição Y de início no campo |
| `xEnd` | float | Posição X de fim no campo |
| `yEnd` | float | Posição Y de fim no campo |
| `videoUrl` | str | URL do clipe de vídeo do sprint |
| `videoStartAt` | float | Tempo de início no vídeo (segundos) |
| `videoEndAt` | float | Tempo de fim no vídeo (segundos) |
| `player.id` | int | ID do jogador |
| `player.name` | str | Nome do jogador |
| `team.id` | int | ID do time |
| `team.name` | str | Nome do time |
| `competition.id` | int | ID da competição |
| `competition.name` | str | Nome da competição |
| `opponentTeam.id` | int | ID do adversário |
| `opponentTeam.name` | str | Nome do adversário |

---

### `get_game_high_speed_runs(game_id, as_dataframe=False)`

Retorna as corridas de alta velocidade (*high speed runs*) da partida. A estrutura de colunas é idêntica à de `get_game_sprints`, porém com limiar de velocidade diferente.

```python
client.get_game_high_speed_runs(game_id=189)
client.get_game_high_speed_runs(game_id=189, as_dataframe=True)
```

> As colunas são as mesmas de `get_game_sprints`. Ver tabela acima.

---

### `get_physical_metrics(seasons, competition_ids, team_ids, positions, possession, as_dataframe=False)`

Retorna métricas físicas agregadas por jogador via GET. Todos os parâmetros são strings separadas por vírgulas.

```python
client.get_physical_metrics(
    seasons="2024-2025",
    competition_ids="1",
    positions="CB,LB,RB",
    possession="ALL",
    as_dataframe=True,
)
```

| Parâmetro | Tipo | Exemplo |
|---|---|---|
| `seasons` | str | `"2024-2025"` ou `"2024-2025,2023-2024"` |
| `competition_ids` | str | `"1"` ou `"1,42"` |
| `team_ids` | str | `"6,10"` |
| `positions` | str | `"GK"`, `"CB,LB"`, etc. |
| `possession` | str | `"IN"`, `"OUT"`, `"ALL"`, `"NONE"` |

### `query_physical_metrics(season, competition_ids, team_ids, positions, possession, age, filters, as_dataframe=False)`

Versão POST com suporte a filtros avançados.

```python
client.query_physical_metrics(
    season="2024-2025",
    competition_ids=[1],
    possession="ALL",
    age={"from": 18, "to": 23},
    filters={
        "and": [
            {"operator": "gt",            "subject": "game_appearances", "value": 10},
            {"operator": "values_between","subject": "total_distance",   "values": [9000, 13000]},
        ]
    },
    as_dataframe=True,
)
```

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `season` | str | Temporada (singular, ex.: `"2024-2025"`) |
| `competition_ids` | list[int] | Lista de IDs de competições |
| `team_ids` | list[int] | Lista de IDs de times |
| `positions` | list[str] | Lista de posições (ver tabela de posições) |
| `possession` | str | `"IN"`, `"OUT"`, `"ALL"`, `"NONE"` |
| `age` | dict | Faixa etária: `{"from": 18, "to": 23}` |
| `filters` | dict | Filtros avançados (ver abaixo) |

#### Filtros avançados

Cada entrada do filtro **deve** conter `"operator"`, `"subject"` e `"value"` ou `"values"`:

| Operador | Campo adicional | Exemplo |
|---|---|---|
| `"gt"` | `"value"` (número) | `{"operator": "gt", "subject": "sprints", "value": 5}` |
| `"lt"` | `"value"` (número) | `{"operator": "lt", "subject": "total_distance", "value": 10000}` |
| `"values_between"` | `"values"` (lista com 2 números) | `{"operator": "values_between", "subject": "total_distance", "values": [8000, 12000]}` |

> ⚠️ O operador `"above_median"` está documentado na API mas retorna erro 422 a menos que seja acompanhado de um campo `"value"` ou `"values"`.

**Colunas do DataFrame** (`as_dataframe=True`) — 1 linha por (jogador × métrica):

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | int | ID do jogador |
| `firstName` | str | Primeiro nome |
| `lastName` | str | Sobrenome |
| `age` | int | Idade |
| `position` | str | Posição principal |
| `playedHistory` | list | Histórico de times e competições (lista bruta) |
| `team.id` | int | ID do time atual |
| `team.name` | str | Nome do time atual |
| `metric.name` | str | Nome da métrica |
| `metric.raw` | float | Valor bruto acumulado no período |
| `metric.rawPercentile` | float | Percentil do valor bruto |
| `metric.p90` | float | Valor normalizado por 90 minutos |
| `metric.p90Percentile` | float | Percentil do valor p90 |

---

### `get_player_physical_metrics(player_id, competition_ids, seasons, team_ids, possessions, as_dataframe=False)`

Retorna as métricas físicas de um jogador específico, partida a partida, via GET.

```python
client.get_player_physical_metrics(
    player_id=42,
    seasons="2024-2025",
    competition_ids="1",
    possessions="ALL",
    as_dataframe=True,
)
```

### `query_player_physical_metrics(player_id, competition_ids, seasons, team_ids, possessions, as_dataframe=False)`

Versão POST equivalente, com parâmetros como listas.

```python
client.query_player_physical_metrics(
    player_id=42,
    seasons=["2024-2025"],
    competition_ids=[1],
    possessions=["ALL"],
    as_dataframe=True,
)
```

**Colunas do DataFrame** (`as_dataframe=True`) — 1 linha por (partida × métrica):

| Coluna | Tipo | Descrição |
|---|---|---|
| `gameId` | int | ID da partida |
| `gameDate` | str | Data da partida (`YYYY-MM-DD`) |
| `season` | str | Temporada |
| `location` | str | `"HOME"` ou `"AWAY"` |
| `possession` | str | Tipo de posse filtrado |
| `playerPosition` | str | Posição na partida |
| `team.id` | int | ID do time |
| `team.name` | str | Nome do time |
| `competition.id` | int | ID da competição |
| `competition.name` | str | Nome da competição |
| `opponentTeam.id` | int | ID do adversário |
| `opponentTeam.name` | str | Nome do adversário |
| `metric.name` | str | Nome da métrica |
| `metric.raw` | float | Valor bruto na partida |
| `metric.rawPercentile` | float | Percentil do valor bruto |

---

## Tabela de Métricas Físicas

As colunas `metric.name` nos DataFrames de métricas físicas podem assumir os seguintes valores:

| `metric.name` | Descrição |
|---|---|
| `total_distance` | Distância total percorrida (metros) |
| `sprints` | Número de sprints |
| `high_speed_runs` | Número de corridas de alta velocidade |
| `sprint_distance` | Distância total em sprints (metros) |
| `high_speed_distance` | Distância total em alta velocidade (metros) |
| `game_appearances` | Número de partidas (disponível em métricas agregadas) |

> A lista exata de métricas depende dos datasets contratados. Use `get_competitions(as_dataframe=True)` para verificar quais datasets estão disponíveis para sua conta.

---

## Tabela de Posições

Valores válidos para o parâmetro `positions` em `query_physical_metrics`:

| Código | Posição |
|---|---|
| `GK` | Goleiro |
| `D` | Defensor (genérico) |
| `CB` | Zagueiro central |
| `LB` | Lateral esquerdo |
| `RB` | Lateral direito |
| `LWB` | Ala-esquerdo defensivo |
| `RWB` | Ala-direito defensivo |
| `LCB` | Zagueiro central esquerdo |
| `RCB` | Zagueiro central direito |
| `MCB` | Zagueiro central médio |
| `CDM` | Volante/Médio defensivo central |
| `M` | Meio-campo (genérico) |
| `DM` | Médio defensivo |
| `CM` | Médio central |
| `AM` | Médio ofensivo |
| `CAM` | Meia ofensivo central |
| `LM` | Meia esquerdo |
| `RM` | Meia direito |
| `LW` | Ponta esquerda |
| `RW` | Ponta direita |
| `CF` | Centroavante |
| `ST` | Atacante |
| `F` | Atacante (genérico) |

---

## Exemplos de Uso Completo

```python
from dotenv import load_dotenv
load_dotenv()

client = GradientSportsClient()

# 1. Ver competições disponíveis
df_comp = client.get_competitions(as_dataframe=True)

# 2. Listar partidas de uma temporada
df_games = client.get_games(season="2024-2025", competition_id=1, as_dataframe=True)

# 3. Métricas físicas de uma partida (por jogador × métrica)
game_id = df_games["id"].iloc[0]
df_metrics = client.query_game_physical_metrics(game_id, possessions=["ALL"], as_dataframe=True)

# 4. Sprints de uma partida
df_sprints = client.get_game_sprints(game_id, as_dataframe=True)

# 5. Ranking de jogadores por total_distance na temporada
df_players = client.get_physical_metrics(
    seasons="2024-2025",
    competition_ids="1",
    possession="ALL",
    as_dataframe=True,
)
df_dist = (
    df_players[df_players["metric.name"] == "total_distance"]
    .sort_values("metric.p90", ascending=False)
    .head(10)
)

# 6. Métricas de um jogador específico ao longo da temporada
player_id = 42
df_player = client.query_player_physical_metrics(
    player_id,
    seasons=["2024-2025"],
    competition_ids=[1],
    possessions=["ALL"],
    as_dataframe=True,
)
```
