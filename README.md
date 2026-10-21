# API Design Practice — from requirements to schema & contract

The skill you're training: turning vague human requirements into two precise artifacts.

1. **Schema** (ERD + DDL) — the shape of truth
2. **API contract** (OpenAPI) — the promise of behavior

Code is downstream of both. These 10 projects train the upstream translation: brief → entities → tables → contract. Difficulty climbs from ★ (one join table) to ★★★★★ (double-entry ledgers and multi-tenancy).

## How each project file works

Every project file has the same sections:

| Section | What it is |
|---|---|
| **The brief** | The client's words — prose on purpose, with ambiguities baked in |
| **Requirements** | User stories distilled from the brief (the input to your modeling) |
| **Design decisions to resolve** | The forks in the road. **No answers given** — pick one, write down why |
| **Starter ERD** | Entities and relationships sketched, attributes left as TODOs |
| **Suggested API surface** | A path list to react to — reorganize it if you disagree |
| **OpenAPI skeleton** | Partial spec with TODO markers; you finish it |
| **Gotchas to test** | Edge cases your design must survive |
| **Self-review checklist** | The bar to clear before calling it done |

The answers are deliberately not in the files. If a decision isn't listed, it's either obvious or a trap — both are good practice.

## The workflow (per project, in this order)

1. **Restate** — rewrite the brief as a numbered list of *entities* (nouns), *actions* (verbs), *rules* (invariants), and *roles* (who does what). State every assumption explicitly: "I assume notes are private per user; no sharing."
2. **ERD** — draw entities and relationships (Mermaid in the file, or [dbdiagram.io](https://dbdiagram.io)). Mark PK, FK, UNIQUE, and every nullable field.
3. **DDL** — write `CREATE TABLE` statements and *actually run them* (SQLite for 1–5, Postgres for 6+). A constraint you didn't write doesn't exist.
4. **Contract** — write the OpenAPI YAML. Every endpoint: parameters, request body, and *every* response — the 200/201/204 **and** each 4xx, with bodies.
5. **Prove it** — mock it (`prism mock openapi.yaml`) and hit it with curl; or feed the spec to Schemathesis against your implementation.
6. **Self-review** — run the checklist. Then re-read "Design decisions to resolve": anything you can't state as *choice + reason* wasn't designed, it was defaulted.

Suggested repo layout for your work:

```
api-design-practice/
├── README.md            ← you are here
├── 01-notes-app.md
├── ...
├── 10-ledger-api.md
└── solutions/           ← your work
    └── 01-notes/
        ├── assumptions.md
        ├── erd.md
        ├── schema.sql
        └── openapi.yaml
```

## Rules of the game

- **Contract first.** The OpenAPI file is the deliverable. Imagine a frontend dev implements against it with no way to ask you questions.
- **Specify failure.** Every 4xx response has a defined body with a machine-readable error code.
- **No accidental nulls.** For every field you can answer: can it be missing, and why?
- **Consistency compounds.** The house conventions below apply to all 10 projects. Define them once; stop re-deciding.

## House conventions (adopt once, use everywhere)

| Concern | Convention |
|---|---|
| IDs | Opaque strings (UUID/ULID) in the API — never expose autoincrement integers |
| Timestamps | ISO 8601 UTC, fields end in `_at` |
| Dates | `YYYY-MM-DD`, fields end in `_on` or `_date` |
| Money | Integer minor units + ISO 4217 currency code; fields end in `_cents` |
| Enums | `lower_snake_case` strings, declared as OpenAPI `enum` |
| Errors | `{ "error": { "code": "machine_code", "message": "human sentence", "details": {} } }` |
| Pagination | `?limit=&cursor=` → `{ "data": [ ... ], "next_cursor": "..." }` (offset allowed before project 09 *if you justify it*) |
| URLs | kebab-case, plural resources; JSON fields `snake_case` |

## The ladder

| # | Project | Difficulty | New skills |
|---|---|---|---|
| 01 | [Notes App](01-notes-app.md) | ★ | Entities → tables, join tables, first OpenAPI, error envelope |
| 02 | [URL Shortener](02-url-shortener.md) | ★ | Uniqueness, generated keys, redirect semantics, store-vs-compute |
| 03 | [Todos with Projects](03-todo-projects.md) | ★★ | Auth, ownership, filtering/sorting/pagination, PATCH semantics, enums |
| 04 | [Expense Splitter](04-expense-splitter.md) | ★★★ | Derived data, money integrity, split invariants, settlements |
| 05 | [Library Rental](05-library-rental.md) | ★★★ | State machines, book-vs-copy modeling, row-level concurrency, business rules → error codes |
| 06 | [Event Ticketing](06-event-ticketing.md) | ★★★★ | Holds & expiry, idempotency keys, oversell prevention, payment lifecycle |
| 07 | [E-commerce Orders](07-ecommerce-orders.md) | ★★★★ | Price snapshots, catalog filter contract, checkout transactions, order lifecycle |
| 08 | [Job Board with Roles](08-job-board.md) | ★★★★ | RBAC-shaped API, 404 vs 403, append-only audit events, visibility rules |
| 09 | [Multi-tenant Tracker](09-multi-tenant-tracker.md) | ★★★★★ | Tenancy strategy, versioning, cursor pagination at scale, rate limits, webhook contracts |
| 10 | [Ledger API](10-ledger-api.md) | ★★★★★ | Immutability, double-entry invariants, idempotent writes, keyset pagination, reconciliation |

## Tooling

- **Diagrams**: mermaid.live, dbdiagram.io
- **Spec editing**: Swagger Editor, Stoplight, or the OpenAPI extension for VS Code
- **Mocking**: `npx @stoplight/prism-cli mock openapi.yaml`
- **Contract testing**: Schemathesis
- **Databases**: SQLite for projects 01–05; Postgres from 06 on (you'll want partial indexes, CHECK constraints, and real transactions)

## Pacing

Do **01–03 fully** — they build the reflexes. Skim 04–05 (ERD + decisions only) if time is short. Then pick **two** of 06–10 and go deep. Every project assumes the conventions of the ones before it.
