---
status: draft
---

<!--
SPDX-FileCopyrightText: 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science
SPDX-FileCopyrightText: 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>

SPDX-License-Identifier: EUPL-1.2
-->

# claude-fleet-trust-gate

Upstream Claude Code bug (observed on v2.1.214): the agent view (`claude agents`) executes `WorktreeRemove` hooks only when **its own working directory** is a trusted project, and reports the refusal as a hook failure. Deleting a background session then fails with `Worktree kept at <path> — could not be removed (WorktreeRemove hook failed); the session was not deleted`, even though the hook was never run.

## Behaviour

The trust gate checks the fleet process's launch directory, not the target session's project. A fleet launched from an untrusted directory (e.g. `$HOME`) cannot delete any worktree-bound session; the same session deletes fine seconds later from a fleet launched in a trusted directory, or via `claude rm`. Worktree-less sessions are unaffected — deletion without a worktree involves no hook and no trust check.

## Evidence

An inotify watch on the hook directory records zero opens of the configured hook script during failing attempts (a control invocation seconds later shows up), and system-wide 50 ms process sampling shows no child processes spawned — the "failed" hook is never executed. A/B on one identical session: fleet from untrusted `$HOME` fails with the hook-failure message, fleet from a trusted work directory deletes the session and removes the worktree.

## Upstream asks

- The gate should consult the target session's project trust (or the worktree's), not the fleet's cwd.
- The error message should say hooks were skipped for an untrusted directory instead of claiming the hook failed.
- Related upstream issues: [#23109](https://github.com/anthropics/claude-code/issues/23109) (central pre-trust / `trustedWorkspacePatterns`), [#12100](https://github.com/anthropics/claude-code/issues/12100) (hooks blocked before trust), [#36403](https://github.com/anthropics/claude-code/issues/36403) (trust flags in `~/.claude.json` wiped by exit-time rewrites).

## Local mitigation

The `claude_code` role's opt-in `trust-work-dirs` SessionStart hook asserts trust for the work base directories (default `/work`) in the user's `~/.claude.json`; ancestor inheritance covers every pad and worktree below. Fleets must be launched from a trusted directory — a work directory, or a directory whose trust dialog was accepted once. `claude rm <id>` works regardless of fleet trust.

# Considerations

## Reproduction recipe

Disposable haiku background sessions in a scratch repo (`/srv/repos/test.git` + `/work/test`, deployed via pod's `system.yaml`) reproduce every variant cheaply: spawn with `claude --bg --model haiku --permission-mode acceptEdits -- "<task>"`, drive the fleet in tmux (`tmux send-keys C-x`, twice — Ctrl-X is a double-press confirm with a ~2 s window), capture with `tmux capture-pane`. The unpushed pre-check ("worktree has commits that are not pushed anywhere") runs before the trust-gated hook step and counts merged-to-local-main as unpushed when no remote-tracking ref covers the commits.

## Why not seed trust per directory

Trust is inherited from ancestors, so one trusted base entry suffices. Freshly written per-directory flags also lose a race: exiting Claude Code processes rewrite `~/.claude.json` from their startup snapshot after all hooks (measured 19 s after SessionEnd), wiping entries seeded after they started. A single long-lived base entry is present in every process's snapshot and survives; per-directory seeding, a seeded-dirs record file, SessionEnd re-asserts, and a systemd path unit were all tried and dropped.
