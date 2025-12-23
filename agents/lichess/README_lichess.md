# Lichess Agent

Multi-turn Lichess assistant with tool-backed reads for profile, games, puzzles, and TV.

## Capabilities (read-only)
- Account profile, preferences, email
- User status and most recent games
- Filtered games by rating, opening, move prefix
- Daily puzzle and puzzle solution by id
- Lichess TV channels and current channel game
- Game stream preview (first few events)

Destructive actions (follow/unfollow, delete study chapter) are intentionally excluded for now.

## Run

Human input (blocking terminal input) - PowerShell:
```powershell
$env:LICHESS_HUMAN_USER=1; python lichess_runner.py
```

Scenario-driven (uses the first row unless LICHESS_SCENARIO_NAME is set):
```powershell
$env:LICHESS_SCENARIO_NAME="daily_puzzle"
python lichess_runner.py
```

Optional: `$env:MAX_TURNS=10`.

## Tokens

This agent prefers `LICHESS_TOKEN` and falls back to any of:
`LICHESS_TOKEN_READ_PREFERENCES`, `LICHESS_TOKEN_READ_EMAIL`,
`LICHESS_TOKEN_FOLLOW_PLAYERS`, `LICHESS_TOKEN_DELETE_STUDY_CHAPTER`.

Token scopes are messy right now; plan to consolidate later.
If you see 401/403 errors, check that the active token has the needed scope.
