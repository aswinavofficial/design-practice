# 01 — Notes App

Difficulty ★ · Focus: entities → tables → CRUD endpoints · join tables · your first OpenAPI · the error envelope

Expected effort: one focused session. This project exists to establish the reflexes every later project reuses.

## The brief

> "I want a place to keep notes. Each note has a title and some text. I organize them with tags — a note can have several tags, and I want to see all notes that share a tag. Tags are short lowercase words I type myself; if I type a tag that doesn't exist yet, just create it. When I delete a note it should be *gone* — no trash bin. Oh, and let me search my notes by word, and the list should be newest-first."

One user. You. No accounts, no roles, no sharing. (Auth arrives in project 03 — don't design it yet.)

## Requirements (user stories)

1. Create a note with a title and a body.
2. Edit any field of an existing note.
3. Delete a note — permanently.
4. List notes, newest first.
5. Filter the list by tag.
6. Search notes by a word appearing in title or body.
7. Attach one or more tags to a note. Retyping an existing tag name reuses it.
8. Rename or delete a tag. Renaming updates every note that uses it.
9. Every note has created and updated timestamps, visible in the API.

## Design decisions to resolve

No answers here. For each, pick one and write a one-sentence defense in your `assumptions.md`.

- **Tags storage**: separate `tags` table + join table, or a text array / CSV column on `notes`? Requirement 8 (rename cascades to all notes) is the pressure test — what breaks under each option?
- Is `title` required? Can a note have zero tags? Can a tag exist with zero notes?
- **DELETE note**: hard or soft? What does the endpoint return — `204` with no body, or `200` with something?
- "Newest first" — by `created_at` or `updated_at`? What's the secondary sort when two notes share a timestamp?
- **Search**: `LIKE '%term%'`? Full-text index? What's the query param — `?q=`?
- **Attach tags**: one endpoint per tag (`POST /notes/{id}/tags`), or replace-the-whole-set (`PUT /notes/{id}/tags`)? What happens to a tag that loses its last note?
- `PUT` vs `PATCH` for editing — what's the semantic difference *in your contract*, and which do you allow?
- A request references a tag **id** that doesn't exist: `400`, `404`, or auto-create? (Requirement 7 auto-creates by *name* — you may still decide differently for ids.)

## Starter ERD

```mermaid
erDiagram
    NOTE ||--o{ NOTE_TAG : has
    TAG  ||--o{ NOTE_TAG : labels

    NOTE {
        string id PK "TODO: type + generation strategy"
        string title "TODO: nullable?"
        text body "TODO: nullable? min length?"
        datetime created_at
        datetime updated_at
    }
    TAG {
        string id PK
        string name UK "TODO: case handling? max length?"
    }
    NOTE_TAG {
        "TODO: what columns does a join table need beyond the two FKs?"
    }
```

## Suggested API surface (react to it, don't obey it)

- `GET /notes` — list, filter by tag, search
- `POST /notes` — create
- `GET /notes/{noteId}`
- `PATCH /notes/{noteId}` (and/or `PUT`)
- `DELETE /notes/{noteId}`
- `PUT /notes/{noteId}/tags` — replace tag set (or `POST`/`DELETE` per tag — you decide)
- `GET /tags`, `PATCH /tags/{tagId}`, `DELETE /tags/{tagId}`

## OpenAPI skeleton

```yaml
openapi: 3.1.0
info:
  title: Notes API
  version: 0.1.0
paths:
  /notes:
    get:
      summary: List notes (newest first)
      parameters:
        - name: q          # TODO: requirement 6 — search
          in: query
          schema: { type: string }
        - name: tag        # TODO: requirement 5 — by id or by name?
          in: query
          schema: { type: string }
        # TODO: pagination params — decide the style now, reuse it in all 9 later projects
      responses:
        "200":
          description: A page of notes
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/NoteList"
    post:
      summary: Create a note
      # TODO: request body schema; does it accept tags inline?
      # TODO: 201 with the new note? Location header? What are the 4xx cases (422?)
      responses: {}
  # TODO: /notes/{noteId} — get, patch/put, delete (define every response)
  # TODO: /notes/{noteId}/tags
  # TODO: /tags — list, rename, delete
components:
  schemas:
    Error:
      # TODO: your error envelope, defined ONCE here, $ref'd everywhere
      type: object
    Note:
      type: object
      # TODO: required fields, nullable fields, formats
      properties:
        id: { type: string }
```

## Gotchas to test

- Duplicate tag names differing only in case — what does UNIQUE mean here?
- Deleting a tag that notes still reference — what does the FK do? Did you *choose* the behavior or inherit it?
- Search matching nothing: `200` with an empty list, or `404`? (There is a right answer. It's `200`.)
- Two clients edit the same note — lost update. Is that acceptable at this scale? ("Last write wins, documented" is a legitimate decision. Silence is not.)

## Self-review checklist

- [ ] Every user story maps to at least one endpoint.
- [ ] Every endpoint maps to at least one user story — no speculative ones.
- [ ] Every 4xx path has a response body defined (the `Error` schema).
- [ ] The DDL runs. Every UNIQUE, NOT NULL, and FK is there because you decided it.
- [ ] You can explain the tags storage choice and what you gave up.
