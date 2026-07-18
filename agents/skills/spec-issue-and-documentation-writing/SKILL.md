---
# SPDX-FileCopyrightText: 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science
# SPDX-FileCopyrightText: 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>
#
# SPDX-License-Identifier: EUPL-1.2

name: spec-issue-and-documentation-writing
description: When writing or editing specs, issue files, or documentation markdown. Brainstorm freely, but never invent content into the file without approval; format, structure, and edit are trusted. Keep negative / "we decided not to" / rationale-only material in a deletable `# Considerations` section at the bottom. Docs themselves stay in positive, declarative voice.
---

# Spec, issue and documentation writing

You're structuring a markdown file someone else owns.

## Don't invent content. Format and structure freely.

Substantive content — new sections, new rules, reworded paragraphs, anything that adds claims to the file — goes in only with explicit approval. Brainstorm in the chat, surface options, let the user pick. Then edit.

Formatting and structural edits are trusted: tidy whitespace, fix heading levels, renumber, dedupe cross-references, move already-approved material between sections, flatten lists into prose when prose reads better. No need to ask first for these.

If you're unsure whether a change counts as substantive, treat it as substantive and ask.

## Voice

Documentation reads in positive, declarative voice. "This is what the feature does. This is the expected behaviour. These are the edge cases the program avoids." Not "we considered X but didn't go that way because…", not "originally we did A then switched to B", not "it might be tempting to Y but Z is wrong."

That second pile is real and useful. It just isn't documentation. It goes in `# Considerations` (below).

A short positive "why" is fine in the body — one sentence that names the rule's purpose helps a reader who's wondering. Once the why grows past that — alternatives, defensive justification, "the reason for this is that…" walks — it's Considerations material. The body keeps the rule; the rambling moves down.

## Prose first

Default to well-separated paragraphs, often with a bold lead-in word or two ("**Anchoring**: …") instead of a bullet. 

Lists are fine when they're genuine enumerations — file paths, options, sequence of steps, comparison tables — but resist using them just because there are three things to say.

## Don't hard-wrap paragraphs

Write each paragraph as one long line. The user's editor wraps it visually; markdown renderers wrap it on output. Hard line breaks inside a paragraph make diffs noisy and force reflowing every time a sentence changes. Break content by writing more paragraphs, not by inserting linebreaks.

## `# Considerations` section

A single section at the very end of the file, below `# References` / `# Sources` if those exist. Match the file's existing heading convention (H1 or H2). Holds decisions to not do something and the reasoning, rejected alternatives, historical "we used to do X" notes, and any "why not Y" discussion that isn't actionable.

The whole section is designed to be deletable. When the spec or docs ship, the maintainer should be able to delete `# Considerations` and the rest still reads cleanly. So nothing in the non-considerations body refers to anything inside it.

## Avoid redundancies

Each fact lives in one place. If you find the same rule, definition, or example stated twice, fold the duplicates and cross-reference. The doc gets shorter and harder to drift out of sync.

## Keep yourself short

Don't be a blabbermouth auntie claudie.

> Claudie writes too much
> about not writing too much.
> The wind moves the tree.

## Example

A little feature spec as an example for good style.

````markdown
# `retry` — exponential backoff for transient failures

The `retry` helper re-runs a fallible operation with growing delays between attempts. Default behaviour: try, wait, try again, wait longer, give up after a cap.

## Behaviour

`retry(op)` calls `op()` and returns its result if it succeeds. On a failure flagged as transient, it sleeps for the current delay, multiplies the delay, and tries again — until either `op()` succeeds or the attempt limit is reached. A non-transient failure propagates immediately without sleeping.

The clock measuring the delays starts on each call, not at process start; concurrent `retry` calls don't share state.

## Knobs

- `initial_delay` — wait before the second attempt. Defaults to 100 ms.
- `multiplier` — factor the delay grows by between attempts. Defaults to 2.
- `max_attempts` — total tries including the first. Defaults to 5.
- `is_transient(err)` — predicate that decides whether to retry. Defaults to "true for any timeout or 5xx, false otherwise".

## Cancellation

If the caller's context is cancelled mid-sleep, `retry` aborts the sleep and returns the context's error. In-flight `op()` calls run to completion — `retry` doesn't cancel them.

# Considerations

## No jitter by default

A herd of clients backing off in lockstep can synchronise and spike the dependency. Adding jitter (random ±20% per delay) smears them out. The default stays jitter-free because the most common caller is a single user-facing request where a deterministic timeline reads cleaner in logs. Pass `jitter=true` when retrying from a server-side worker pool.

## No unlimited retries

`max_attempts` has no "infinite" value. An operation that can never succeed shouldn't spin forever; surface the failure and let the caller decide.
````

