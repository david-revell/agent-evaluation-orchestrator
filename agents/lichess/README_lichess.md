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

## Example prompts

Use Lichess usernames (not real names) and provide IDs where needed.

- "Show public profile for username peletis."
- "Get rating history for Hikaru."
- "Get performance stats for MagnusCarlsen in blitz."
- "Show crosstable for user1=Hikaru and user2=MagnusCarlsen."
- "List live streamers."
- "Show the most recent game for username peletis."
- "List games for peletis with rating >= 1800 and opening prefix C20."
- "Export game by id kq8yTfXb."
- "Export games by ids: kq8yTfXb, gKJ9s2qA."
- "Which game is on the classical TV channel right now?"
- "Show best ongoing games for TV channel blitz."
- "Get today’s daily puzzle and show the solution."
- "Get puzzle solution for id 9dJaD."
- "Opening explorer (masters) for FEN: r1bqkbnr/pppppppp/2n5/8/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 2"
- "Tablebase lookup for FEN: 8/8/8/8/8/3k4/3K4/8 w - - 0 1"

## Tokens

This agent prefers `LICHESS_TOKEN` and falls back to any of:
`LICHESS_TOKEN_READ_PREFERENCES`, `LICHESS_TOKEN_READ_EMAIL`,
`LICHESS_TOKEN_FOLLOW_PLAYERS`, `LICHESS_TOKEN_DELETE_STUDY_CHAPTER`.

Token scopes are messy right now; plan to consolidate later.
If you see 401/403 errors, check that the active token has the needed scope.
