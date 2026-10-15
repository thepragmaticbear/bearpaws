# Privacy

Bearpaws is a set of skills, one subagent, slash commands, and local hooks. It has no server, no account, no telemetry, and no MCP servers or connectors.

## What it sends

Nothing. No skill, hook, or script in the plugin makes a network request. The plugin's text is loaded into your agent's context the same way as any other skill, and your agent provider handles that context under its own terms.

## What it stores

Only the `risk-gate` hook (Claude Code only) writes files, and only on your machine:

- **Session log** (`<session id>.log`): the paths of files edited during the session, plus markers for review dispatches. It is deleted when a reply is accepted. If a reply ends with elevated-risk work marked INCOMPLETE and no review, the log stays until a later reply is accepted.
- **Work-tree fingerprint** (`<session id>.<repo hash>.tree`): one hash of file names, sizes, and modification times per git repo, used to notice edits made through shell commands. It holds no file contents or names in readable form, and it is kept between replies.

Both live in `$CLAUDE_PLUGIN_DATA/risk-gate/` (or `$TMPDIR/risk-gate/` when that is unset). They are readable only by your user account. Set `BEARPAWS_ENFORCE=0` to turn the hook off, and delete that directory to remove what it stored.

## Personal data

Bearpaws does not collect, read, or store personal data such as names, emails, or addresses.

## Contact

Questions: open an issue at https://github.com/thepragmaticbear/bearpaws/issues.
