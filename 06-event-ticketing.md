# 06 — Event Ticketing

Difficulty ★★★★ · Focus: holds & expiry · idempotency keys · oversell prevention · payment lifecycle

Expected effort: two to three sessions. Builds on [05](05-library-rental.md) (state machines, concurrency). First Postgres project.

## The brief

> "We sell tickets for events. Each event has one or more ticket tiers — regular, VIP — each with a fixed quantity. A customer picks an event, a tier, and a quantity; we place a temporary hold for 10 minutes so those tickets can't be snatched while they check out. They confirm with payment details; on success the hold becomes a booking with one ticket code per seat. If they abandon it, the hold expires and the tickets go back to the pool. Payment can fail — the hold stays alive until its 10 minutes are up so they can retry. Customers may cancel a confirmed booking up to 24 hours before the event for a refund. And this one is non-negotiable: if the network hiccups and the confirm request arrives twice, we must never create two bookings."

## Requirements (user stories)

1. Manage events (name, venue, `starts_at`, sales open/close times).
2. Manage tiers per event: name, `price_cents`, `quantity`.
3. See availability: remaining tickets per tier, live.
4. Create a hold: event, tier, quantity → hold id + `expires_at` (10 minutes).
5. Confirm a hold → booking. **Requires an `Idempotency-Key` header.** Payment succeeds or fails; failure keeps the hold valid until expiry.
6. A hold whose time ran out is dead: confirm returns an error, tickets are back in the pool.
7. Booking detail: status, tickets with codes.
8. Cancel a confirmed booking up to 24h before `starts_at` → refund recorded. Later: rejected.
9. Under concurrent load, the same last two tickets can never be sold three times.

## Design decisions to resolve

- **Inventory model**: per-tier `quantity` + counters, or one row per individual ticket? Trace "remaining = ?" through each. Which makes holds and oversell prevention simpler — and which makes refunds or tier editing simpler?
- **Oversell prevention** — the core of the project. Pick a mechanism and state the failure mode of the others:
  - `SELECT ... FOR UPDATE` on the tier row, then validate;
  - atomic conditional `UPDATE tiers SET held = held + :qty WHERE remaining >= :qty`;
  - optimistic concurrency (version column, retry on conflict).
- **Hold expiry — sweep or lazy?** A background job that frees expired holds, vs. checking `expires_at` at confirm/availability time. With lazy checks, what does the *availability* endpoint show for holds that expired 30 seconds ago? With a sweep, what does it show 1 second before the sweep runs? (Both work — the availability contract must be honest about one of them.)
- **Idempotency**: the server stores `(key, request hash, response)` and replays the stored response on repeat. Same key + *different body* → `422 idempotency_conflict`. Two concurrent requests with the same key → one wins; what does the loser get? Where does this live in the schema?
- **Payments**: a `payments` table with status `pending|succeeded|failed|refunded` and attempts. A booking may have several payment attempts (retries) — what's the cardinality? Is "refund" a new payment row or a status change?
- **Booking states**: `confirmed → cancelled | refunded`. Is there a `pending_payment` state, or does the booking only exist once payment succeeds? Sketch the machine; every arrow needs a trigger.
- Money again: integer cents, tier price immutable-ish (what happens to an existing hold if the admin changes the price mid-hold?).
- Error codes to define: `hold_expired`, `insufficient_remaining`, `idempotency_conflict`, `cancel_window_closed`, `payment_failed`, `event_closed`…

## Starter ERD

```mermaid
erDiagram
    EVENT ||--o{ TICKET_TIER : sells
    TICKET_TIER ||--o{ HOLD : holds
    TICKET_TIER ||--o{ TICKET : issues
    BOOKING ||--o{ TICKET : contains
    BOOKING ||--o{ PAYMENT : paid_by

    EVENT {
        string id PK
        string name
        string venue
        datetime starts_at
        datetime sales_open_at
        datetime sales_close_at
    }
    TICKET_TIER {
        string id PK
        string event_id FK
        string name
        int price_cents
        int quantity "TODO: sold/held — columns or counts from children?"
    }
    HOLD {
        string id PK
        string tier_id FK
        int quantity
        string status "TODO: active|confirmed|expired|released"
        datetime expires_at
        datetime created_at
    }
    BOOKING {
        string id PK
        string hold_id FK "TODO: 1:1?"
        string status "TODO: confirmed|cancelled|refunded"
        datetime created_at
    }
    TICKET {
        string id PK
        string booking_id FK
        string tier_id FK
        string code UK "TODO: human-presentable?"
    }
    PAYMENT {
        string id PK
        string booking_id FK
        int amount_cents
        string status "TODO: pending|succeeded|failed|refunded"
        int attempt_no
        datetime created_at
    }
    IDEMPOTENCY_KEY {
        "TODO: key UK, request_hash, response snapshot — generic table or per-endpoint?"
    }
```

## Suggested API surface (react to it, don't obey it)

- `GET /events`, `POST /events` (admin), `GET/PATCH /events/{eventId}`
- `GET /events/{eventId}/tiers`, `POST /events/{eventId}/tiers` (admin)
- `GET /events/{eventId}/availability`
- `POST /holds` → `{hold_id, expires_at}`
- `POST /holds/{holdId}/confirm` — **`Idempotency-Key` required**
- `GET /bookings/{bookingId}`
- `POST /bookings/{bookingId}/cancel`

## OpenAPI skeleton

```yaml
openapi: 3.1.0
info:
  title: Ticketing API
  version: 0.1.0
paths:
  /events/{eventId}/availability:
    get:
      # TODO: [{tier_id, remaining}] — and a description of how fresh this number is
      #       (the honest answer depends on your sweep-vs-lazy decision)
      responses: {}
  /holds:
    post:
      # TODO: {tier_id, quantity} → 201 {hold_id, expires_at}
      # TODO: 409 insufficient_remaining | 422 event_closed | 422 sales_not_open
      responses: {}
  /holds/{holdId}/confirm:
    post:
      parameters:
        - name: Idempotency-Key
          in: header
          required: true
          schema: { type: string, format: uuid }
      # TODO: 201 booking | 200 replayed (same key!) | 409 hold_expired
      #       | 422 idempotency_conflict | 402/422 payment_failed — pick one and define the body
      responses: {}
  /bookings/{bookingId}/cancel:
    post:
      # TODO: 200 refunded | 422 cancel_window_closed | 409 already_cancelled
      responses: {}
components:
  schemas:
    Error: {}   # TODO: house envelope; error codes as a documented enum
```

## Gotchas to test

- **The oversell race**: 10 concurrent confirms for the last 2 tickets. Exactly 2 succeed, the rest get the *same* coherent error. Test with `seq`/`xargs -P` or a load script.
- **The idempotent retry**: fire confirm twice with the same key, sequentially and concurrently. Same booking id both times; no duplicate payment row.
- A hold expiring *between* the availability check and the confirm — which error does the client see?
- Cancel at exactly T-24h — inclusive or exclusive? Put the boundary in the spec, not in a code comment.
- Refund of a refunded booking — `409` with which code?

## Self-review checklist

- [ ] The oversell proof exists: a concurrency test you actually ran, not an argument.
- [ ] `Idempotency-Key` behavior fully specified: replay, conflict, concurrent duplicate.
- [ ] Every state machine (hold, booking, payment) is drawn; every arrow names its trigger.
- [ ] Availability's staleness is documented in the endpoint description — no lying contracts.
- [ ] Money never floats; every 4xx has a code from the defined set.
