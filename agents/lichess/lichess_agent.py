"""
Script: lichess_agent.py
Version: v1

Multi-turn Lichess agent with tool-backed actions.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Iterable, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from agents import Agent, function_tool

DEFAULT_AGENT_MODEL = os.getenv("LICHESS_AGENT_MODEL", "gpt-5-nano")

load_dotenv()

TOKEN_ENV_ORDER = [
    "LICHESS_TOKEN",
    "LICHESS_TOKEN_READ_PREFERENCES",
    "LICHESS_TOKEN_READ_EMAIL",
    "LICHESS_TOKEN_FOLLOW_PLAYERS",
    "LICHESS_TOKEN_DELETE_STUDY_CHAPTER",
]


def pick_token(env_names: Iterable[str]) -> Tuple[Optional[str], Optional[str]]:
    for name in env_names:
        value = os.getenv(name)
        if value:
            return value, name
    return None, None


def auth_headers(env_names: Iterable[str], required: bool) -> Tuple[Dict[str, str], Optional[str], Optional[str]]:
    token, token_name = pick_token(env_names)
    if not token:
        if required:
            return {}, None, f"Missing Lichess token. Set one of: {', '.join(env_names)}."
        return {}, None, None
    return {"Authorization": f"Bearer {token}"}, token_name, None


def truncate(text: str, limit: int = 1200) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."


def format_http_error(action: str, status_code: int, text: str, token_name: Optional[str]) -> str:
    hint = ""
    if status_code in {401, 403} and token_name:
        hint = f" Check token scopes for {token_name}."
    return f"{action} failed (HTTP {status_code}).{hint} {truncate(text)}"


def parse_ndjson_lines(lines: Iterable[bytes]) -> List[dict]:
    games: List[dict] = []
    for line in lines:
        if not line:
            continue
        try:
            games.append(json.loads(line.decode("utf-8")))
        except Exception:
            continue
    return games


def summarize_game(game: dict) -> str:
    game_id = game.get("id", "unknown")
    perf = game.get("perf") or game.get("speed") or "unknown"
    opening = (game.get("opening") or {}).get("name")
    white = (game.get("players") or {}).get("white", {})
    black = (game.get("players") or {}).get("black", {})
    white_name = white.get("user", {}).get("name") or white.get("name") or "white"
    black_name = black.get("user", {}).get("name") or black.get("name") or "black"
    white_rating = white.get("rating")
    black_rating = black.get("rating")
    winner = game.get("winner")
    rating_text = f"{white_name} ({white_rating}) vs {black_name} ({black_rating})"
    details = f"id={game_id}, perf={perf}, {rating_text}"
    if opening:
        details += f", opening={opening}"
    if winner:
        details += f", winner={winner}"
    return details


def summarize_games(games: List[dict], limit: int = 5) -> str:
    if not games:
        return "No games found."
    lines = [summarize_game(g) for g in games[:limit]]
    extra = ""
    if len(games) > limit:
        extra = f"\nShowing {limit} of {len(games)} games."
    return "\n".join(lines) + extra


def fetch_games(
    username: str,
    max_games: int,
    token_envs: Iterable[str],
    include_moves: bool = False,
) -> Tuple[Optional[List[dict]], Optional[str]]:
    headers, token_name, error = auth_headers(token_envs, required=False)
    if error:
        return None, error
    headers["Accept"] = "application/x-ndjson"
    params = {
        "max": max_games,
        "opening": True,
        "pgnInJson": True,
        "moves": include_moves,
    }
    resp = requests.get(
        f"https://lichess.org/api/games/user/{username}",
        headers=headers,
        params=params,
        stream=True,
        timeout=20,
    )
    if resp.status_code != 200:
        return None, format_http_error("Fetching games", resp.status_code, resp.text, token_name)
    return parse_ndjson_lines(resp.iter_lines()), None


def matches_rating(game: dict, rating_min: int) -> bool:
    white = game.get("players", {}).get("white", {})
    black = game.get("players", {}).get("black", {})
    white_rating = white.get("rating")
    black_rating = black.get("rating")
    if white_rating is None or black_rating is None:
        return False
    return white_rating >= rating_min and black_rating >= rating_min


def matches_opening(game: dict, opening_prefix: Optional[str]) -> bool:
    if not opening_prefix:
        return True
    opening = game.get("opening", {})
    name = opening.get("name", "")
    eco = opening.get("eco", "")
    return name.startswith(opening_prefix) or eco.startswith(opening_prefix)


def matches_move_prefix(game: dict, move_prefix: Optional[str]) -> bool:
    if not move_prefix:
        return True
    moves = game.get("moves", "").split()
    prefix = move_prefix.split()
    return moves[: len(prefix)] == prefix


@function_tool
def get_profile() -> str:
    headers, token_name, error = auth_headers(TOKEN_ENV_ORDER, required=True)
    if error:
        return error
    resp = requests.get("https://lichess.org/api/account", headers=headers, timeout=20)
    if resp.status_code != 200:
        return format_http_error("Fetching profile", resp.status_code, resp.text, token_name)
    data = resp.json()
    return truncate(json.dumps(data, indent=2))


@function_tool
def get_account_preferences() -> str:
    headers, token_name, error = auth_headers(TOKEN_ENV_ORDER, required=True)
    if error:
        return error
    resp = requests.get("https://lichess.org/api/account/preferences", headers=headers, timeout=20)
    if resp.status_code != 200:
        return format_http_error("Fetching preferences", resp.status_code, resp.text, token_name)
    data = resp.json()
    return truncate(json.dumps(data, indent=2))


@function_tool
def get_email() -> str:
    headers, token_name, error = auth_headers(TOKEN_ENV_ORDER, required=True)
    if error:
        return error
    resp = requests.get("https://lichess.org/api/account/email", headers=headers, timeout=20)
    if resp.status_code != 200:
        return format_http_error("Fetching email", resp.status_code, resp.text, token_name)
    data = resp.json()
    email = data.get("email")
    return f"Account email: {email}" if email else truncate(json.dumps(data, indent=2))


@function_tool
def get_user_status(usernames: str, with_game_ids: bool = True, with_game_metas: bool = False) -> str:
    headers, token_name, _ = auth_headers(TOKEN_ENV_ORDER, required=False)
    params = {
        "ids": usernames,
        "withGameIds": str(with_game_ids).lower(),
        "withGameMetas": str(with_game_metas).lower(),
    }
    resp = requests.get("https://lichess.org/api/users/status", headers=headers, params=params, timeout=20)
    if resp.status_code != 200:
        return format_http_error("Fetching user status", resp.status_code, resp.text, token_name)
    data = resp.json()
    return truncate(json.dumps(data, indent=2))


@function_tool
def get_most_recent_games(username: str, max_games: int = 1) -> str:
    games, error = fetch_games(username, max_games=max_games, token_envs=TOKEN_ENV_ORDER, include_moves=False)
    if error:
        return error
    if games is None:
        return "No games found."
    return summarize_games(games, limit=max_games)


@function_tool
def get_filtered_games(
    username: str,
    max_games: int = 50,
    rating_min: int = 0,
    opening_prefix: Optional[str] = None,
    move_prefix: Optional[str] = None,
) -> str:
    games, error = fetch_games(username, max_games=max_games, token_envs=TOKEN_ENV_ORDER, include_moves=True)
    if error:
        return error
    if not games:
        return "No games found."
    filtered = [
        g
        for g in games
        if matches_rating(g, rating_min)
        and matches_opening(g, opening_prefix)
        and matches_move_prefix(g, move_prefix)
    ]
    if not filtered:
        return "No games matched the filter conditions."
    return summarize_games(filtered, limit=min(10, len(filtered)))


@function_tool
def get_daily_puzzle(min_rating: Optional[int] = None, required_theme: Optional[str] = None) -> str:
    headers, token_name, _ = auth_headers(TOKEN_ENV_ORDER, required=False)
    resp = requests.get("https://lichess.org/api/puzzle/daily", headers=headers, timeout=20)
    if resp.status_code != 200:
        return format_http_error("Fetching daily puzzle", resp.status_code, resp.text, token_name)
    data = resp.json()
    puzzle = data.get("puzzle") or data
    rating = puzzle.get("rating")
    themes = puzzle.get("themes") or []
    if min_rating is not None and rating is not None and rating < min_rating:
        return "Daily puzzle did not meet the rating filter."
    if required_theme and required_theme not in themes:
        return "Daily puzzle did not meet the theme filter."
    payload = {
        "puzzle_id": puzzle.get("id"),
        "rating": rating,
        "themes": themes,
        "solution": puzzle.get("solution"),
        "game_id": (data.get("game") or {}).get("id"),
        "initial_ply": puzzle.get("initialPly"),
    }
    return truncate(json.dumps(payload, indent=2))


@function_tool
def get_puzzle_solution_by_id(puzzle_id: str) -> str:
    headers, token_name, _ = auth_headers(TOKEN_ENV_ORDER, required=False)
    resp = requests.get(f"https://lichess.org/api/puzzle/{puzzle_id}", headers=headers, timeout=20)
    if resp.status_code != 200:
        return format_http_error("Fetching puzzle", resp.status_code, resp.text, token_name)
    data = resp.json()
    puzzle = data.get("puzzle") or data
    solution = puzzle.get("solution")
    return f"Puzzle {puzzle_id} solution (UCI): {solution}"


@function_tool
def get_tv_channels() -> str:
    resp = requests.get("https://lichess.org/api/tv/channels", timeout=20)
    if resp.status_code != 200:
        return format_http_error("Fetching TV channels", resp.status_code, resp.text, None)
    data = resp.json()
    summary = {name: {"gameId": info.get("gameId"), "name": info.get("name")} for name, info in data.items()}
    return truncate(json.dumps(summary, indent=2))


@function_tool
def get_tv_channel_game(channel: str) -> str:
    resp = requests.get("https://lichess.org/api/tv/channels", timeout=20)
    if resp.status_code != 200:
        return format_http_error("Fetching TV channel game", resp.status_code, resp.text, None)
    data = resp.json()
    info = data.get(channel)
    if not info:
        available = ", ".join(sorted(data.keys()))
        return f"Channel '{channel}' not found. Available: {available}"
    payload = {
        "channel": channel,
        "gameId": info.get("gameId") or info.get("id"),
        "name": info.get("name"),
        "players": info.get("players"),
        "perf": info.get("perf"),
    }
    return truncate(json.dumps(payload, indent=2))


@function_tool
def get_game_stream_preview(game_id: str, max_events: int = 5) -> str:
    headers, token_name, _ = auth_headers(TOKEN_ENV_ORDER, required=False)
    resp = requests.get(
        f"https://lichess.org/api/stream/game/{game_id}",
        headers=headers,
        stream=True,
        timeout=20,
    )
    if resp.status_code != 200:
        return format_http_error("Fetching game stream", resp.status_code, resp.text, token_name)
    lines: List[str] = []
    for line in resp.iter_lines():
        if not line:
            continue
        try:
            lines.append(line.decode("utf-8"))
        except Exception:
            lines.append(str(line))
        if len(lines) >= max_events:
            break
    if not lines:
        return "No stream events received."
    return "Stream preview:\n" + "\n".join(lines)


@function_tool
def get_user_public_data(username: str) -> str:
    resp = requests.get(f"https://lichess.org/api/user/{username}", timeout=20)
    if resp.status_code != 200:
        return format_http_error("Fetching user public data", resp.status_code, resp.text, None)
    data = resp.json()
    return truncate(json.dumps(data, indent=2))


@function_tool
def get_rating_history(username: str) -> str:
    resp = requests.get(f"https://lichess.org/api/user/{username}/rating-history", timeout=20)
    if resp.status_code != 200:
        return format_http_error("Fetching rating history", resp.status_code, resp.text, None)
    data = resp.json()
    return truncate(json.dumps(data, indent=2))


@function_tool
def get_performance_stats(username: str, perf: str) -> str:
    resp = requests.get(f"https://lichess.org/api/user/{username}/perf/{perf}", timeout=20)
    if resp.status_code != 200:
        return format_http_error("Fetching performance stats", resp.status_code, resp.text, None)
    data = resp.json()
    return truncate(json.dumps(data, indent=2))


@function_tool
def get_user_activity(username: str) -> str:
    resp = requests.get(f"https://lichess.org/api/user/{username}/activity", timeout=20)
    if resp.status_code != 200:
        return format_http_error("Fetching user activity", resp.status_code, resp.text, None)
    data = resp.json()
    return truncate(json.dumps(data, indent=2))


@function_tool
def get_crosstable(user1: str, user2: str) -> str:
    resp = requests.get(f"https://lichess.org/api/crosstable/{user1}/{user2}", timeout=20)
    if resp.status_code != 200:
        return format_http_error("Fetching crosstable", resp.status_code, resp.text, None)
    data = resp.json()
    return truncate(json.dumps(data, indent=2))


@function_tool
def get_live_streamers() -> str:
    resp = requests.get("https://lichess.org/api/streamer/live", timeout=20)
    if resp.status_code != 200:
        return format_http_error("Fetching live streamers", resp.status_code, resp.text, None)
    data = resp.json()
    return truncate(json.dumps(data, indent=2))


@function_tool
def export_game(
    game_id: str,
    clocks: bool = False,
    evals: bool = False,
    opening: bool = True,
    moves: bool = True,
) -> str:
    headers, token_name, _ = auth_headers(TOKEN_ENV_ORDER, required=False)
    params = {
        "clocks": str(clocks).lower(),
        "evals": str(evals).lower(),
        "opening": str(opening).lower(),
        "moves": str(moves).lower(),
    }
    resp = requests.get(
        f"https://lichess.org/game/export/{game_id}",
        headers=headers,
        params=params,
        timeout=20,
    )
    if resp.status_code != 200:
        return format_http_error("Exporting game", resp.status_code, resp.text, token_name)
    return truncate(resp.text)


@function_tool
def export_games_by_ids(game_ids: str, max_games: int = 5) -> str:
    headers, token_name, _ = auth_headers(TOKEN_ENV_ORDER, required=False)
    headers["Accept"] = "application/x-ndjson"
    ids = [gid.strip() for gid in game_ids.replace("\n", ",").split(",") if gid.strip()]
    if not ids:
        return "No game IDs provided."
    resp = requests.post(
        "https://lichess.org/games/export/_ids",
        headers=headers,
        params={"pgnInJson": True, "opening": True},
        data=",".join(ids),
        timeout=20,
    )
    if resp.status_code != 200:
        return format_http_error("Exporting games", resp.status_code, resp.text, token_name)
    games = parse_ndjson_lines(resp.iter_lines())
    if games:
        return summarize_games(games, limit=min(max_games, len(games)))
    return truncate(resp.text)


@function_tool
def get_tv_channel_best_games(channel: str) -> str:
    resp = requests.get(f"https://lichess.org/api/tv/{channel}", stream=True, timeout=20)
    if resp.status_code != 200:
        return format_http_error("Fetching TV channel games", resp.status_code, resp.text, None)
    games = parse_ndjson_lines(resp.iter_lines())
    if not games:
        return "No channel games returned."
    return summarize_games(games, limit=min(5, len(games)))


@function_tool
def opening_explorer_masters(fen: str) -> str:
    resp = requests.get("https://explorer.lichess.ovh/masters", params={"fen": fen}, timeout=20)
    if resp.status_code != 200:
        return format_http_error("Opening explorer (masters)", resp.status_code, resp.text, None)
    data = resp.json()
    return truncate(json.dumps(data, indent=2))


@function_tool
def opening_explorer_lichess(fen: str, speeds: Optional[str] = None, ratings: Optional[str] = None) -> str:
    params = {"fen": fen}
    if speeds:
        params["speeds"] = speeds
    if ratings:
        params["ratings"] = ratings
    resp = requests.get("https://explorer.lichess.ovh/lichess", params=params, timeout=20)
    if resp.status_code != 200:
        return format_http_error("Opening explorer (lichess)", resp.status_code, resp.text, None)
    data = resp.json()
    return truncate(json.dumps(data, indent=2))


@function_tool
def opening_explorer_player(
    fen: str,
    player: str,
    color: str = "white",
) -> str:
    params = {"fen": fen, "player": player, "color": color}
    resp = requests.get("https://explorer.lichess.ovh/player", params=params, timeout=20)
    if resp.status_code != 200:
        return format_http_error("Opening explorer (player)", resp.status_code, resp.text, None)
    data = resp.json()
    return truncate(json.dumps(data, indent=2))


@function_tool
def tablebase_lookup(fen: str, variant: str = "standard") -> str:
    resp = requests.get(f"https://tablebase.lichess.ovh/{variant}", params={"fen": fen}, timeout=20)
    if resp.status_code != 200:
        return format_http_error("Tablebase lookup", resp.status_code, resp.text, None)
    data = resp.json()
    return truncate(json.dumps(data, indent=2))


def help_text() -> str:
    return (
        "Lichess agent capabilities (read-only):\n"
        "- Profile/preferences/email (requires auth token)\n"
        "- Public user data: profile, rating history, perf stats, activity, crosstable\n"
        "- Live streamers\n"
        "- Games: most recent, filtered by rating/opening/move prefix\n"
        "- Export a game by ID or export multiple games by IDs\n"
        "- TV: channels, current channel game, best ongoing channel games\n"
        "- Puzzles: daily puzzle, puzzle by id\n"
        "- Opening explorer (masters/lichess/player) and tablebase lookup\n"
        "Notes: usernames must be Lichess usernames (not real names). "
        "For full details see agents/lichess/README_lichess.md."
    )


lichess_agent = Agent(
    name="LichessAgent",
    model=DEFAULT_AGENT_MODEL,
    instructions="""
You are a helpful Lichess assistant for David. Use tools to fetch Lichess data and answer
questions clearly and concisely. Stay strictly on Lichess-related tasks.

Scope guard:
- If the user asks for something non-Lichess, politely decline and redirect to Lichess help in one short sentence.

Non-overclaim rule:
- You can only perform actions supported by the provided tools. If the user asks for something
  that is not supported, say so and offer a close alternative that is possible.

Guidelines:
- Ask for missing required details (username, puzzle id, channel name) before calling tools.
- For game lists, summarize briefly rather than dumping huge payloads.
- For token or permission errors, explain that token scopes may be missing and suggest setting LICHESS_TOKEN.

Final answer format:
- Respond in plain text (no JSON). Keep it to 1-3 short sentences unless the user asked for detailed output.
""",
    tools=[
        get_profile,
        get_account_preferences,
        get_email,
        get_user_status,
        get_most_recent_games,
        get_filtered_games,
        get_daily_puzzle,
        get_puzzle_solution_by_id,
        get_tv_channels,
        get_tv_channel_game,
        get_tv_channel_best_games,
        get_game_stream_preview,
        get_user_public_data,
        get_rating_history,
        get_performance_stats,
        get_user_activity,
        get_crosstable,
        get_live_streamers,
        export_game,
        export_games_by_ids,
        opening_explorer_masters,
        opening_explorer_lichess,
        opening_explorer_player,
        tablebase_lookup,
    ],
)
