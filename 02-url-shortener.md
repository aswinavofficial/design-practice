# 02 — URL Shortener with Click Stats

Difficulty ★ · Focus: uniqueness & generated keys · redirect semantics · store-vs-compute · your first non-JSON endpoint

Expected effort: one focused session. Builds on [01](01-notes-app.md) (CRUD, error envelope, pagination).

## The brief

> "I keep pasting the same enormous links. I want to paste a long URL and get back something short like `https://sho.rt/aB3xK9` that forwards anyone who visits it. Count every visit — per link I want total clicks, the last-clicked time, and clicks per day for the last 30 days. Sometimes I want to choose my own code: letters, numbers, and dashes only. Links can optionally expire on a date. If I deactivate a link, visitors get a 'link is no longer active' response instead of a redirect. Oh — check that what I paste is actually a valid http(s) URL."

Single operator again. No user accounts (that's project 03); all links belong to "the operator".

## Requirements (user stories)

1. Create a short link from a long URL; get the code back. Reject anything that isn't a well-formed `http`/`https` URL.
2. Visiting `/{code}` redirects to the target URL.
3. Every redirect is recorded as a click: at minimum a timestamp. Decide whether to also keep referrer and user-agent.
4. Stats per link: total clicks, last click at, clicks per day for the last 30 days.
5. Optional custom alias, restricted charset `[a-zA-Z0-9-]`, unique. Some codes are reserved (`api`, `health`, `admin`, `stats`…).
6. Optional expiry date; after it, visiting does not redirect.
7. Deactivate and reactivate a link.
8. List all links, paginated, with their click counts.

## Design decisions to resolve

- **Code generation**: random base62 vs. sequential counter encoded in base62? For a 7-character random code, what's the collision probability at 1M links? What's your collision retry story — and does the `UNIQUE` constraint or your app logic guarantee it?
- **Redirect status**: `301` is cacheable — browsers may never hit your server again, so your click stats silently go wrong. `302`/`307` cost one hop but tell the truth. Commit and know why.
- **Clicks**: one row per click (the truth, but the table grows forever) vs. a counter column on the link (cheap, but you need per-day)? Is there a third option (daily aggregate rows)? You need per-day stats — pick the combination and argue it.
- Should click recording be synchronous in the redirect path (latency on every visit) or async ("eventually counted")? What does the contract have to say about that?
- Expired vs. deactivated: different statuses (`410 Gone` vs `404`)? Or the same, on purpose — do you want the world to learn the difference?
- Click privacy: do you store IPs? Hashed? Not at all? State it in the contract either way — "we store nothing" is a spec decision too.
- Where does the redirect endpoint live in the OpenAPI file? A `302` with a `Location` header and no JSON body is legal — model it.

## Starter ERD

```mermaid
erDiagram
    LINK ||--o{ CLICK : receives

    LINK {
        string id PK
        string code UK "TODO: charset, length, generation"
        string target_url "TODO: validation where?"
        boolean is_active
        date expires_on "TODO: nullable"
        int click_count "TODO: denormalized? source of truth?"
        datetime created_at
    }
    CLICK {
        "TODO: one row per click or aggregates? decide columns"
    }
```

## Suggested API surface (react to it, don't obey it)

- `POST /links` — create (long URL, optional alias, optional expiry)
- `GET /links` — list, paginated
- `GET /links/{code}` — details
- `PATCH /links/{code}` — deactivate/reactivate, change expiry
- `GET /links/{code}/stats` — totals + daily series
- `GET /{code}` — the redirect. Consider `/r/{code}` to keep it out of the JSON API's namespace — decide and justify.

## OpenAPI skeleton

```yaml
openapi: 3.1.0
info:
  title: Shortener API
  version: 0.1.0
paths:
  /links:
    post:
      summary: Create a short link
      # TODO: body {url, alias?, expires_on?}
      # TODO: 201 | 409 alias_taken | 422 invalid_url | 422 reserved_alias
      responses: {}
    get:
      summary: List links
      # TODO: pagination; include click_count?
      responses: {}
  /links/{code}/stats:
    get:
      summary: Click stats for a link
      # TODO: response shape {total_clicks, last_click_at?, daily: [...]}
      # TODO: 404 unknown code
      responses: {}
  /r/{code}:
    get:
      summary: Redirect to target
      # TODO: 302 with Location header (no body) — model the header
      # TODO: 404 unknown | 410 expired | 404 or 410 deactivated — decide
      responses: {}
components:
  schemas:
    Error:
      $ref: "#/components/schemas/Error"   # TODO: reuse the envelope from project 01
```

## Gotchas to test

- Alias casing: is `Abc` the same as `abc`? Does the charset rule answer this for you or not?
- Target URLs with fragments, query strings, unicode — must survive byte-exact.
- A link created today, expiring tomorrow, clicked at 23:59:59 UTC — whose midnight applies to `expires_on`?
- Your own monitoring hitting the redirect — bot traffic in your stats. In scope? Say so in the contract.
- The per-day series when a link has zero clicks on some days — sparse or dense array?

## Self-review checklist

- [ ] The collision story is airtight: constraint + retry, not hope.
- [ ] You can explain what `301` would have done to your stats.
- [ ] Every non-redirect outcome of `GET /r/{code}` has a defined status + body.
- [ ] Stats answer all three questions (total, last, per-day) without full-table scans — say which indexes.
- [ ] The DDL runs; `code` is unique; reserved codes are enforced somewhere deliberate.
