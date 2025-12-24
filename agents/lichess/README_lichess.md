# Lichess Agent

Multi-turn Lichess assistant with tool-backed reads for profile, games, puzzles, and TV.

## Capabilities (read-only)
- Account profile, preferences, email
- User status, public profile, rating history, performance stats, activity, crosstable, live streamers
- Most recent games and filtered games by rating, opening, move prefix
- Daily puzzle and puzzle solution by id
- Lichess TV channels, current channel game, and best ongoing channel games
- Game stream preview (first few events)
- Export one game or multiple games by ID
- Opening explorer (masters, lichess, player)
- Tablebase lookup

Destructive actions (follow/unfollow, delete study chapter) are intentionally excluded for now.

## Reference docs

Lichess API reference files live in `agents/lichess/documentation/`.

## Run

Human input (blocking terminal input) - PowerShell:
```powershell
$env:LICHESS_HUMAN_USER=1; python lichess_runner.py
```

You can type `help` at any time to see supported queries and input requirements.

Scenario-driven (uses the first row unless LICHESS_SCENARIO_NAME is set):
```powershell
$env:LICHESS_SCENARIO_NAME="daily_puzzle"
python lichess_runner.py
```

Optional: `$env:MAX_TURNS=10`.

## Help

Type `help` (or `?`) in the runner to see supported queries and required inputs.
For full details, see the capabilities list above.

## Tokens

This agent prefers `LICHESS_TOKEN` and falls back to any of:
`LICHESS_TOKEN_READ_PREFERENCES`, `LICHESS_TOKEN_READ_EMAIL`,
`LICHESS_TOKEN_FOLLOW_PLAYERS`, `LICHESS_TOKEN_DELETE_STUDY_CHAPTER`.

Token scopes are messy right now; plan to consolidate later.
If you see 401/403 errors, check that the active token has the needed scope.
