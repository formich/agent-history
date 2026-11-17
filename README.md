# ◆ agent-history

A terminal app to **browse, search and resume** every conversation you've had with your coding
agents ([Claude Code](https://docs.claude.com/en/docs/claude-code),
[Codex](https://github.com/openai/codex) and [pi](https://pi.dev/)), across all your projects,
in one list.

![agent-history: agents and projects on the left, conversations grouped by day, preview on the right](docs/screenshot.svg)

Each agent's resume picker only shows its own sessions. `agent-history` gives you the
"chat list" of the desktop apps, in your terminal, for all of them at once:

- **Every session, in one place.** Claude Code, Codex and pi together, grouped by day, with the title
  the agent generated (or the one you gave it), the project, the worktree, the time and how many
  messages you wrote. Each row says which agent it was.
- **Full-text search.** Type to filter titles, folders, branches *and everything you wrote*.
  Matches are highlighted, and when the match is in the text you see the sentence it came from.
- **Preview before you open.** Your messages and the agent's replies, rendered as Markdown.
- **Filter by agent and by project.** Sessions are grouped by repository, so git worktrees
  (`…/worktrees/<repo>/<branch>` or Claude Code's own `<repo>/.claude/worktrees/…`) count as
  the same project.
- **Resume with Enter.** It `cd`s into the original folder and runs `claude --resume <id>`,
  `codex resume <id>` or `pi --session <file>`. If that folder was deleted (a removed worktree), it recreates it so the
  session can still be resumed.
- **Rename** a Claude Code conversation (same record as `/rename`), **copy** the resume command,
  or **open** its folder.
- Fast: the index is cached and only changed sessions are re-read.
- English and Italian UI.

![Searching “retries”: matches highlighted in titles and in the text you wrote](docs/screenshot-search.svg)

## Install

You need [uv](https://docs.astral.sh/uv/) (it fetches Python 3.11+ and
[Textual](https://textual.textualize.io/) on first run, nothing is installed globally).

Download the latest release into a folder on your `PATH`:

```sh
curl -fsSL https://github.com/formich/agent-history/releases/latest/download/agent-history \
  -o ~/.local/bin/agent-history && chmod +x ~/.local/bin/agent-history
```

Run the same command again to update. To pin a version, replace `latest/download` with
`download/v1.0.0`; every [release](https://github.com/formich/agent-history/releases) also
ships a `SHA256SUMS` file if you want to verify the download.

Or, to follow development, clone the repo and symlink the script:

```sh
git clone https://github.com/formich/agent-history.git
ln -s "$PWD/agent-history/agent-history" ~/.local/bin/agent-history
```

Works on macOS and Linux. You only need the agents you actually use: if you have just one of
them, the agents list is hidden.

## Use

```sh
agent-history             # open the app
agent-history webhook     # open it with a search already typed
agent-history --agent codex   # only Codex conversations (or: claude, pi)
agent-history --list      # plain list, for scripts
```

| Key | Action |
|---|---|
| `Enter` | Resume the selected conversation in its folder |
| `a` | Switch agent: All → Claude Code → Codex → pi |
| `/` | Search (`Esc` clears it, `Esc` again goes back to the list) |
| `v` | Toggle the whole conversation / short preview |
| `r` | Rename the conversation, shown with ★ (Claude Code only) |
| `c` | Copy the `cd … && <agent> resume …` command |
| `o` | Open the folder in Finder / your file manager |
| `p` | Jump to the projects list |
| `Tab` | Move between panes |
| `Ctrl+P` | Command palette (themes, quit, …) |
| `q` | Quit |

## Keep your history longer

Claude Code **deletes sessions older than 30 days** by default. To keep them, raise
`cleanupPeriodDays` in `~/.claude/settings.json`:

```json
{
  "cleanupPeriodDays": 365
}
```

## Configuration

All optional, via environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `AGENT_HISTORY_LANG` | from `LANG` | `en` or `it` |
| `AGENT_HISTORY_ROOTS` | `Dev:dev:code:src:projects:repos:git:workspace:Developer` | Folders under `$HOME` that contain your repos; the next path segment becomes the project name |
| `CLAUDE_CONFIG_DIR` | `~/.claude` | Where Claude Code keeps its data |
| `CODEX_HOME` | `~/.codex` | Where Codex keeps its data |
| `PI_CODING_AGENT_DIR` | `~/.pi/agent` | Where pi keeps its data; its `PI_CODING_AGENT_SESSION_DIR` and `sessionDir` setting are honoured too |

## How it works

Each agent stores a session as a JSON Lines file:

- Claude Code: `~/.claude/projects/<folder>/<session-id>.jsonl`
- Codex: `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`, with titles in `~/.codex/session_index.jsonl`
- pi: `~/.pi/agent/sessions/--<folder>--/<timestamp>_<id>.jsonl`, a tree of entries; agent-history
  shows the branch you were last on

`agent-history` reads those files (read-only, except when you rename a Claude Code conversation),
keeps a small index in `~/.cache/agent-history/`, and hands off to the agent's own resume command
when you pick one. Codex sub-agent sessions (such as approval reviews) are hidden.

This is an unofficial tool, not affiliated with Anthropic, OpenAI or Earendil. The session formats are
internal to each agent and may change; if something breaks after an update, please open an issue.

## Screenshots

The screenshots are generated from invented sessions by `scripts/screenshot.py`:

```sh
uv run --with 'textual>=1.0' python scripts/screenshot.py           # docs/screenshot.svg
uv run --with 'textual>=1.0' python scripts/screenshot.py retries   # docs/screenshot-search.svg
```

## License

[MIT](LICENSE)
