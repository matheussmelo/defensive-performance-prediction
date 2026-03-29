"""
Gradient Sports Physical Performance API — Python client.
https://interia.gradientsports.com/#tag/Competitions

Usage
-----
    from gradient_client import GradientSportsClient

    client = GradientSportsClient()          # reads BEARER_TOKEN from .env
    df = client.get_games(season="2024-2025", competition_id=1, as_dataframe=True)

Authentication
--------------
Set BEARER_TOKEN in a .env file next to this module, or pass it directly:

    client = GradientSportsClient(token="your_token_here")
"""

from __future__ import annotations

import os
from typing import Optional, Union

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class GradientSportsClient:
    """
    Thin wrapper around the Gradient Sports Physical Performance API.

    Every data-fetching method accepts ``as_dataframe=True`` to return a
    fully deaggregated ``pd.DataFrame`` instead of the raw JSON ``dict``.
    Nested dicts are dot-expanded; nested lists are exploded so that each
    row represents the most granular unit of data for that endpoint.
    """

    BASE_URL = "https://interia.gradientsports.com/api/v1"

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def __init__(self, token: Optional[str] = None) -> None:
        self.token = token or os.getenv("BEARER_TOKEN")
        if not self.token:
            raise ValueError(
                "Bearer token not found. "
                "Set BEARER_TOKEN in your .env file or pass token= directly."
            )
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        """Re-raise HTTPError with the API response body in the message."""
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise requests.HTTPError(
                f"{exc}\nAPI response body: {body}",
                response=response,
            ) from exc

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        url = f"{self.BASE_URL}{path}"
        response = self.session.get(url, params=params)
        self._raise_for_status(response)
        return response.json()

    def _post(self, path: str, payload: dict) -> dict:
        url = f"{self.BASE_URL}{path}"
        response = self.session.post(url, json=payload)
        self._raise_for_status(response)
        return response.json()

    # ------------------------------------------------------------------
    # DataFrame normalisation helpers (one per response shape)
    # ------------------------------------------------------------------

    @staticmethod
    def _flat_df(records: list) -> pd.DataFrame:
        """
        One row per record.
        Nested dicts are dot-expanded; list columns are kept as-is.

        Used by: get_games, get_players, get_game_sprints,
                 get_game_high_speed_runs.
        """
        return pd.json_normalize(records, sep=".")

    @staticmethod
    def _metrics_df(records: list) -> pd.DataFrame:
        """
        One row per (record × metric).

        Explodes the nested ``metrics`` list so each metric name becomes
        its own row, prefixed with ``metric.``.

        Used by: get_physical_metrics, query_physical_metrics,
                 get_game_physical_metrics, query_game_physical_metrics,
                 get_player_physical_metrics, query_player_physical_metrics.
        """
        base = pd.json_normalize(records, sep=".")
        if "metrics" not in base.columns:
            return base
        exploded = base.explode("metrics").reset_index(drop=True)
        metric_cols = pd.json_normalize(exploded["metrics"]).add_prefix("metric.")
        return pd.concat(
            [exploded.drop(columns=["metrics"]).reset_index(drop=True), metric_cols],
            axis=1,
        )

    @staticmethod
    def _competitions_df(competitions: list) -> pd.DataFrame:
        """
        One row per (competition × season × dataset).

        Input shape: [{id, name, seasons: [{season, datasets: [str]}]}]
        """
        df = pd.json_normalize(
            competitions,
            record_path="seasons",
            meta=["id", "name"],
            meta_prefix="competition.",
            sep=".",
        )
        return df.explode("datasets").reset_index(drop=True)

    @staticmethod
    def _teams_df(teams: list) -> pd.DataFrame:
        """
        One row per (team × competition × dataset).

        Input shape: [{id, name, competitions: [{id, name}], datasets: [str]}]
        """
        rows = []
        for t in teams:
            for comp in t.get("competitions", [{}]):
                for ds in t.get("datasets", [None]):
                    rows.append(
                        {
                            "team.id": t.get("id"),
                            "team.name": t.get("name"),
                            "competition.id": comp.get("id"),
                            "competition.name": comp.get("name"),
                            "dataset": ds,
                        }
                    )
        return pd.DataFrame(rows)

    @staticmethod
    def _game_events_flat_df(game_events: list) -> pd.DataFrame:
        """
        One row per (event × player on pitch).

        Source: GET /games/{id}/events — tracking-style flat events
        that include every player's position and speed at the moment
        of each event.
        """
        scalar_fields = [
            "id",
            "competitionId",
            "gameId",
            "season",
            "period",
            "periodDescription",
            "eventType",
            "eventTypeDescription",
            "startGameClock",
            "startFormattedGameClock",
            "homeTeam",
            "details",
            "homePlayers",
            "awayPlayers",
            "balls"
        ]
        rows = []
        for ev in game_events:
            base = {f: ev.get(f) for f in scalar_fields}
            if ev.get("player"):
                base["player.id"] = ev["player"].get("id", None)
                base["player.name"] = ev["player"].get("name", None)
            else:
                base["player.id"] = None
                base["player.name"] = None
                
            if ev.get("team"):
                base["team.id"] = ev["team"].get("id", None)
                base["team.name"] = ev["team"].get("name", None)
            else:
                base["team.id"] = None
                base["team.name"] = None
            
            rows.append(base)                
        return pd.DataFrame(rows)

    @staticmethod
    def _game_events_structured_df(game_events: list) -> pd.DataFrame:
        """
        One row per possession event (deepest atomic unit).

        Source: GET /games/{id}/game_events — structured events
        that include possession detail, grades, passes, shots, etc.
        """
        event_scalars = [
            "id",
            "competitionId",
            "gameId",
            "season",
            "period",
            "periodDescription",
            "startGameClock",
            "startFormattedGameClock",
            "homeTeam",
            "gameEventType",
            "gameEventTypeDescription",
            "setpieceType",
            "setpieceTypeDescription",
            "touches",
            "touchesInBox",
            "videoMissing"
            "possessionEvents",
            "homePlayers",
            "awayPlayers",
            "balls"
        ]
        rows = []
        for ev in game_events:
            base = {f: ev.get(f) for f in event_scalars}
            if ev.get("team"):
                base["team.id"] = ev["team"].get("id", None)
                base["team.name"] = ev["team"].get("name", None)
            else:
                base["team.id"] = None
                base["team.name"] = None                
                
            if ev.get("player"):
                base["player.id"] = ev["player"].get("id", None)
                base["player.name"] = ev["player"].get("name", None)
            else:
                base["player.id"] = None
                base["player.name"] = None                

            rows.append(base)
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """
        GET /api/v1/status

        Returns the current application status.

        Returns
        -------
        dict
            Example: {'data': {'status': 'ok'}}
        """
        return self._get("/status")

    # ------------------------------------------------------------------
    # Competitions
    # ------------------------------------------------------------------

    def get_competitions(
        self,
        as_dataframe: bool = False,
    ) -> Union[dict, pd.DataFrame]:
        """
        GET /api/v1/competitions

        Returns competitions, seasons and datasets the user has access to.

        Parameters
        ----------
        as_dataframe : bool
            If True, returns a DataFrame with one row per
            (competition × season × dataset).

        DataFrame columns
        -----------------
        competition.id   int   – Competition ID
        competition.name str   – Competition name
        season           str   – Season  (e.g. "2024-2025")
        datasets         str   – Available dataset name
        """
        raw = self._get("/competitions")
        if as_dataframe:
            return self._competitions_df(raw["data"]["competitions"])
        return raw

    # ------------------------------------------------------------------
    # Teams
    # ------------------------------------------------------------------

    def get_teams(
        self,
        as_dataframe: bool = False,
    ) -> Union[dict, pd.DataFrame]:
        """
        GET /api/v1/teams

        Returns teams and datasets the user has access to.

        Parameters
        ----------
        as_dataframe : bool
            If True, returns a DataFrame with one row per
            (team × competition × dataset).

        DataFrame columns
        -----------------
        team.id          int  – Team ID
        team.name        str  – Team name
        competition.id   int  – Competition ID
        competition.name str  – Competition name
        dataset          str  – Available dataset name
        """
        raw = self._get("/teams")
        if as_dataframe:
            return self._teams_df(raw["data"]["teams"])
        return raw

    # ------------------------------------------------------------------
    # Players
    # ------------------------------------------------------------------

    def get_players(
        self,
        as_dataframe: bool = False,
    ) -> Union[dict, pd.DataFrame]:
        """
        GET /api/v1/players

        Returns the full list of players.

        Parameters
        ----------
        as_dataframe : bool
            If True, returns a DataFrame with one row per player.

        DataFrame columns
        -----------------
        id                   int   – Player ID
        name                 str   – Full name
        firstName            str   – First name
        lastName             str   – Last name
        nickname             str   – Nickname
        dob                  str   – Date of birth (YYYY-MM-DD)
        position             str   – Primary position code
        shirtNumber          str   – Shirt number
        athleticismScore     float – Gradient athleticism score
        transfermarktPlayerId int  – Transfermarkt ID
        team.id              int   – Current team ID
        team.name            str   – Current team name
        """
        raw = self._get("/players")
        if as_dataframe:
            return self._flat_df(raw["data"]["players"])
        return raw

    def get_player_physical_metrics(
        self,
        player_id: int,
        competition_ids: Optional[str] = None,
        seasons: Optional[str] = None,
        team_ids: Optional[str] = None,
        possessions: Optional[str] = None,
        as_dataframe: bool = False,
    ) -> Union[dict, pd.DataFrame]:
        """
        GET /api/v1/players/{id}/physical_metrics

        Returns physical metrics for a single player, game by game.

        Parameters
        ----------
        player_id       : int
        competition_ids : str  Comma-separated IDs, e.g. "1,42"
        seasons         : str  Comma-separated seasons, e.g. "2024-2025"
        team_ids        : str  Comma-separated IDs, e.g. "6,10"
        possessions     : str  Comma-separated, e.g. "IN,OUT"
        as_dataframe    : bool If True → one row per (game × metric)

        DataFrame columns
        -----------------
        gameId           int   – Game ID
        gameDate         str   – Game date (YYYY-MM-DD)
        season           str   – Season
        location         str   – "HOME" or "AWAY"
        possession       str   – Possession filter applied
        playerPosition   str   – Position in that game
        player.id / .name
        team.id / .name
        competition.id / .name
        opponentTeam.id / .name
        metric.name      str   – Metric name (e.g. "total_distance")
        metric.raw       float – Raw value for the game
        metric.rawPercentile float – Percentile vs. historical
        """
        params = {
            k: v
            for k, v in {
                "competition_ids": competition_ids,
                "seasons": seasons,
                "team_ids": team_ids,
                "possessions": possessions,
            }.items()
            if v is not None
        }
        raw = self._get(f"/players/{player_id}/physical_metrics", params=params)
        if as_dataframe:
            return self._metrics_df(raw["data"])
        return raw

    def query_player_physical_metrics(
        self,
        player_id: int,
        competition_ids: Optional[list[int]] = None,
        seasons: Optional[list[str]] = None,
        team_ids: Optional[list[int]] = None,
        possessions: Optional[list[str]] = None,
        as_dataframe: bool = False,
    ) -> Union[dict, pd.DataFrame]:
        """
        POST /api/v1/players/{id}/physical_metrics/query

        Same as get_player_physical_metrics but accepts list parameters
        instead of comma-separated strings.

        Parameters
        ----------
        player_id       : int
        competition_ids : list[int]
        seasons         : list[str]
        team_ids        : list[int]
        possessions     : list[str]  "IN" | "OUT" | "ALL" | "NONE"
        as_dataframe    : bool  If True → one row per (game × metric)
        """
        payload: dict = {}
        if competition_ids:
            payload["competitionIds"] = competition_ids
        if seasons:
            payload["seasons"] = seasons
        if team_ids:
            payload["teamIds"] = team_ids
        if possessions:
            payload["possessions"] = possessions
        raw = self._post(f"/players/{player_id}/physical_metrics/query", payload)
        if as_dataframe:
            return self._metrics_df(raw["data"])
        return raw

    # ------------------------------------------------------------------
    # Games
    # ------------------------------------------------------------------

    def get_games(
        self,
        season: Optional[str] = None,
        competition_id: Optional[int] = None,
        team_id: Optional[int] = None,
        as_dataframe: bool = False,
    ) -> Union[dict, pd.DataFrame]:
        """
        GET /api/v1/games

        Returns the list of games. All filters are optional.

        Parameters
        ----------
        season         : str  e.g. "2024-2025"
        competition_id : int  Filter by competition
        team_id        : int  Filter by team (home or away)
        as_dataframe   : bool If True → one row per game

        DataFrame columns
        -----------------
        id                       int   – Game ID
        date                     str   – Date (YYYY-MM-DD)
        season                   str   – Season
        venueType                str   – TEAM_HOME | OPPONENT_HOME | NEUTRAL
        teamStartSide            str   – "Left" or "Right"
        teamExtraTimeStartSide   str   – Side in extra time
        team.id / .name
        competition.id / .name
        opponentTeam.id / .name
        stadium.name             str   – Stadium name
        stadium.length           float – Field length (metres)
        stadium.width            float – Field width (metres)
        """
        params = {
            k: v
            for k, v in {
                "season": season,
                "competition_id": competition_id,
                "team_id": team_id,
            }.items()
            if v is not None
        }
        raw = self._get("/games", params=params)
        if as_dataframe:
            return self._flat_df(raw["data"]["games"])
        return raw

    def get_game_events(
        self,
        game_id: int,
        as_dataframe: bool = False,
    ) -> Union[dict, pd.DataFrame]:
        """
        GET /api/v1/games/{id}/game_events

        Returns structured game events with full possession detail
        (passes, shots, duels, grades, etc.).

        Parameters
        ----------
        game_id      : int
        as_dataframe : bool  If True → one row per possession event

        DataFrame columns
        -----------------
        id / competitionId / gameId / season
        period / periodDescription
        startGameClock / startFormattedGameClock
        homeTeam                 bool
        gameEventType / gameEventTypeDescription
        setpieceType / setpieceTypeDescription
        touches / touchesInBox   int
        team.id / .name
        player.id / .name
        """
        raw = self._get(f"/games/{game_id}/game_events")
        if as_dataframe:
            return self._game_events_structured_df(raw["data"]["gameEvents"])
        return raw

    def get_game_events_flat(
        self,
        game_id: int,
        as_dataframe: bool = False,
    ) -> Union[dict, pd.DataFrame]:
        """
        GET /api/v1/games/{id}/events

        Returns flattened (tracking-style) game events: each event
        includes every player's position and speed on the pitch.

        Parameters
        ----------
        game_id      : int
        as_dataframe : bool  If True → one row per (event × player on pitch)

        DataFrame columns
        -----------------
        id / competitionId / gameId / season
        period / periodDescription
        eventType / eventTypeDescription
        startGameClock / startFormattedGameClock
        homePlayers / awayPlayers / balls
        homeTeam                 bool
        player.id / .name        – Principal player of the event
        team.id / .name
        """
        raw = self._get(f"/games/{game_id}/events")
        if as_dataframe:
            return self._game_events_flat_df(raw["data"]["gameEvents"])
        return raw

    def get_game_physical_metrics(
        self,
        game_id: int,
        possessions: Optional[str] = None,
        as_dataframe: bool = False,
    ) -> Union[dict, pd.DataFrame]:
        """
        GET /api/v1/games/{id}/physical_metrics

        Returns physical metrics per player for a game.

        Parameters
        ----------
        game_id      : int
        possessions  : str  Comma-separated, e.g. "IN,OUT"
        as_dataframe : bool  If True → one row per (player × metric)
        """
        params: dict = {}
        if possessions:
            params["possessions"] = possessions
        raw = self._get(f"/games/{game_id}/physical_metrics", params=params)
        if as_dataframe:
            return self._metrics_df(raw["data"])
        return raw

    def query_game_physical_metrics(
        self,
        game_id: int,
        possessions: Optional[list[str]] = None,
        as_dataframe: bool = False,
    ) -> Union[dict, pd.DataFrame]:
        """
        POST /api/v1/games/{id}/physical_metrics/query

        Same as get_game_physical_metrics but uses POST with a JSON body.

        Parameters
        ----------
        game_id      : int
        possessions  : list[str]  "IN" | "OUT" | "ALL" | "NONE"
        as_dataframe : bool  If True → one row per (player × metric)

        DataFrame columns
        -----------------
        gameDate / season / location / possession / playerPosition
        player.id / .name
        team.id / .name
        competition.id / .name
        opponentTeam.id / .name
        metric.name          str   – Metric name
        metric.raw           float – Raw value for the game
        metric.rawPercentile float – Percentile vs. historical
        """
        payload: dict = {}
        if possessions:
            payload["possessions"] = possessions
        raw = self._post(f"/games/{game_id}/physical_metrics/query", payload)
        if as_dataframe:
            return self._metrics_df(raw["data"])
        return raw

    def get_game_sprints(
        self,
        game_id: int,
        as_dataframe: bool = False,
    ) -> Union[dict, pd.DataFrame]:
        """
        GET /api/v1/games/{id}/sprints

        Returns individual sprints for a game.

        Parameters
        ----------
        game_id      : int
        as_dataframe : bool  If True → one row per sprint

        DataFrame columns
        -----------------
        id / gameId / gameDate / season
        period
        periodElapsedTimeStart / End   int – Elapsed time in period (s)
        periodGameClockTimeStart / End int – Game clock time (s)
        runTime          float – Sprint duration (seconds)
        distance         float – Distance covered (metres)
        speedKmh         float – Max speed reached (km/h)
        started          bool  – True if started inside the pitch
        position         str   – Player position
        shirtNumber      int
        xStart/yStart/xEnd/yEnd  float – Pitch coordinates
        videoUrl         str
        videoStartAt / videoEndAt  float – Seconds into the video clip
        player.id / .name
        team.id / .name
        competition.id / .name
        opponentTeam.id / .name
        """
        raw = self._get(f"/games/{game_id}/sprints")
        if as_dataframe:
            return self._flat_df(raw["data"]["sprints"])
        return raw

    def get_game_high_speed_runs(
        self,
        game_id: int,
        as_dataframe: bool = False,
    ) -> Union[dict, pd.DataFrame]:
        """
        GET /api/v1/games/{id}/high_speed_runs

        Returns high-speed runs for a game (same schema as sprints,
        different speed threshold).

        Parameters
        ----------
        game_id      : int
        as_dataframe : bool  If True → one row per high-speed run

        DataFrame columns: same as get_game_sprints.
        """
        raw = self._get(f"/games/{game_id}/high_speed_runs")
        if as_dataframe:
            return self._flat_df(raw["data"]["highSpeedRuns"])
        return raw

    # ------------------------------------------------------------------
    # Physical metrics (cross-player)
    # ------------------------------------------------------------------

    def get_physical_metrics(
        self,
        seasons: Optional[str] = None,
        competition_ids: Optional[str] = None,
        team_ids: Optional[str] = None,
        positions: Optional[str] = None,
        possession: Optional[str] = None,
        as_dataframe: bool = False,
    ) -> Union[dict, pd.DataFrame]:
        """
        GET /api/v1/physical_metrics

        Returns aggregated physical metrics across all accessible players.
        All filter parameters are comma-separated strings.

        Parameters
        ----------
        seasons         : str  e.g. "2024-2025" or "2024-2025,2023-2024"
        competition_ids : str  e.g. "1" or "1,42"
        team_ids        : str  e.g. "6,10"
        positions       : str  e.g. "GK,CB,LB"
        possession      : str  "IN" | "OUT" | "ALL" | "NONE"
        as_dataframe    : bool If True → one row per (player × metric)

        DataFrame columns
        -----------------
        id / firstName / lastName / age / position
        playedHistory    list  – Raw list of team/competition history
        team.id / .name
        metric.name      str   – Metric name
        metric.raw       float – Raw accumulated value
        metric.rawPercentile float
        metric.p90       float – Per-90-minutes value
        metric.p90Percentile float
        """
        params = {
            k: v
            for k, v in {
                "seasons": seasons,
                "competition_ids": competition_ids,
                "team_ids": team_ids,
                "positions": positions,
                "possession": possession,
            }.items()
            if v is not None
        }
        raw = self._get("/physical_metrics", params=params)
        if as_dataframe:
            return self._metrics_df(raw["data"])
        return raw

    def query_physical_metrics(
        self,
        season: Optional[str] = None,
        competition_ids: Optional[list[int]] = None,
        team_ids: Optional[list[int]] = None,
        positions: Optional[list[str]] = None,
        possession: Optional[str] = None,
        age: Optional[dict] = None,
        filters: Optional[dict] = None,
        as_dataframe: bool = False,
    ) -> Union[dict, pd.DataFrame]:
        """
        POST /api/v1/physical_metrics/query

        Advanced query with filtering support.

        Parameters
        ----------
        season          : str        Single season, e.g. "2024-2025"
                                     NOTE: the API uses the singular key "season",
                                     not "seasons".
        competition_ids : list[int]
        team_ids        : list[int]
        positions       : list[str]  Valid codes: GK D CB LB RB LWB RWB LCB RCB
                                     MCB CDM M DM CM AM CAM LM RM LW RW CF ST F
        possession      : str        "IN" | "OUT" | "ALL" | "NONE"
        age             : dict       {"from": 18, "to": 23}
        filters         : dict       GroupAndFilter object.
                                     EVERY entry must have "value" (scalar) or
                                     "values" (list).
                                     Working operators:
                                       "gt"            → value  (scalar)
                                       "lt"            → value  (scalar)
                                       "values_between"→ values (2-element list)
                                     WARNING: "above_median" returns 422 unless
                                     accompanied by a "value"/"values" key.
        as_dataframe    : bool       If True → one row per (player × metric)

        Example
        -------
        client.query_physical_metrics(
            season="2024-2025",
            competition_ids=[1],
            possession="ALL",
            age={"from": 18, "to": 23},
            filters={
                "and": [
                    {"operator": "gt",             "subject": "game_appearances", "value": 10},
                    {"operator": "values_between", "subject": "total_distance",   "values": [9000, 13000]},
                ]
            },
            as_dataframe=True,
        )
        """
        payload: dict = {}
        if season:
            payload["season"] = season
        if competition_ids:
            payload["competitionIds"] = competition_ids
        if team_ids:
            payload["teamIds"] = team_ids
        if positions:
            payload["positions"] = positions
        if possession:
            payload["possession"] = possession
        if age:
            payload["age"] = age
        if filters:
            payload["filters"] = filters
        raw = self._post("/physical_metrics/query", payload)
        if as_dataframe:
            return self._metrics_df(raw["data"])
        return raw
