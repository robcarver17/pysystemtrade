<!--
Copyright 2026 Google LLC

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

# Automated Roll Status

`run_auto_roll_status` is a non-interactive daily process that updates futures
contract roll states. It is intended to run after multiple/adjusted prices are
updated and before the stack handler, so roll decisions use fresh price data.

It plugs into the `processToRun` framework — same process locking, start/stop
window, dashboard monitoring, and MongoDB finish-status tracking as the other
production jobs. The decision logic is shared with `interactive_update_roll_status`
so the interactive "automatic" cycle mode and the non-interactive job arrive at
the same answers from the same inputs.

The job is shipped opt-in: the crontab line and the `control_config.yaml`
entries exist but are commented out. Uncomment them (or override in
`private_control_config.yaml`) to schedule it.

For motivation and a longer narrative writeup, see
[On a roll state — the auto-roll system](https://managedfutures.substack.com/p/on-a-roll-state-the-auto-roll-system).

---

## Roll states

Each instrument has a roll state stored in the database. The state machine is
defined in `sysobjects/production/roll_state.py`:

| State | Meaning |
|---|---|
| `No_Roll` | Normal trading. Only trade the priced (near) contract. |
| `Passive` | Allow natural roll: close trades in priced contract, open in forward. |
| `Force` | Force roll ASAP using a spread order. |
| `Force_Outright` | Force roll ASAP using two separate outright orders. |
| `Roll_Adjusted` | Roll the adjusted price series from priced to forward contract. Automatically returns to `No_Roll` on success. |
| `Close` | Close position in the near contract only (no forward leg). |
| `No_Open` | Near expiry but forward not liquid. No new opening trades; existing position can still be closed. |

### Transition matrix

Allowable transitions depend on both the current state and whether a position
is held in the priced contract (`0` suffix = no position; `1` suffix = position
held):

| Current state + position | Allowable next states |
|---|---|
| `No_Roll0` | Roll_Adjusted, Passive, No_Roll, No_Open |
| `No_Roll1` | Passive, Force, Force_Outright, No_Roll, Close, No_Open |
| `Passive0` | Roll_Adjusted, Passive, No_Roll, No_Open |
| `Passive1` | Force, Force_Outright, Passive, No_Roll, Close, No_Open |
| `Force0` | Roll_Adjusted, Passive |
| `Force1` | Force, Force_Outright, Passive, No_Roll, Close, No_Open |
| `Force_Outright0` | Roll_Adjusted, Passive |
| `Force_Outright1` | Force, Force_Outright, Passive, No_Roll, Close, No_Open |
| `Close0` | Roll_Adjusted, Passive |
| `Close1` | Close, Force, Force_Outright, Passive, No_Roll, No_Open |
| `Roll_Adjusted0` | No_Roll |
| `Roll_Adjusted1` | Roll_Adjusted |
| `No_Open0` | Roll_Adjusted, Passive, No_Open |
| `No_Open1` | Close, Force, Force_Outright, Passive, No_Roll |

`No_Open0` deliberately does **not** allow `No_Roll` — the instrument stays in
`No_Open` until the forward becomes liquid (→ `Roll_Adjusted`) or a position is
opened (→ `No_Open1`).

---

## Decision logic

Each instrument runs through `process_instrument_roll_status`, which applies a
small set of escalation checks before delegating to `suggest_roll_state_for_instrument`
for the normal liquidity/timing logic. A diagnostic log line is emitted before
every decision recording the priced contract, its actual expiry, the priced-
contract position, roll/expiry timing, and all current DB contract positions
for the instrument.

### Stage 0 — stuck-Force escalation

If the current state is `Force`, a position is held, and the state has been
`Force` for ≥ `force_roll_max_trading_days` trading days without rolling, the
instrument is escalated to `Force_Outright` and the function returns. This
handles spread orders that cannot execute because the spread tick data is
missing or the spread leg is illiquid on the broker.

The check requires a Force timestamp in the database. If the state was set
through a path that did not record a timestamp, the escalation is skipped.

### Stage 1 — expiry escalation

If `days_until_expiry < near_expiry_days` and a position is still held, the
state is forced to `Force` regardless of any other input. `Passive` rolling can
no longer work once the priced contract stops accepting opening orders, and
forcing earlier (`< near_expiry_days`, default 10) gives the stack handler time
to execute the spread roll before the contract disappears.

`Force` is always a valid transition when a position is held, so this path
never hits the invalid-transition guard. The override is logged at CRITICAL so
it surfaces in the email digest.

### Stage 1.5 — late-roll escalation (inside `suggest`)

If a position is held and the desired roll date has passed (`days_until_roll <
0`), urgency is never downgraded:

- Currently `Force`, `Force_Outright` or `Close`: hold it.
- Anything else: escalate to `Force`.

This runs before the normal liquidity/timing logic so the bounded passive
window check cannot interpret negative values as "early passive".

### Stage 1.75 — Roll_Adjusted orphan-position guard

After normal suggestion logic runs but before the state is written, the
process scans **all** current DB contract positions for the instrument. If the
suggested state is `Roll_Adjusted` and any non-zero DB position maps to an
actual expiry inside `near_expiry_days`, the transition is blocked, the
instrument is left unchanged, and a CRITICAL alert is emitted.

This catches the case where the priced contract has rolled forward in metadata
(`position_priced_contract == 0`) but a live position remains in an
expiring non-priced leg. The guard is deliberately conservative: it does not
pick a replacement state because the correct next step depends on
broker/DB reconciliation, which a human needs to drive.

### Stage 2 — normal logic

```
1. Priced contract expired (or any key contract expired) and no position
   and auto_roll_expired=True?
   → Roll_Adjusted  (roll regardless of liquidity)

2. Forward liquid?
   a. No position → Roll_Adjusted
   b. Position held, far from roll date → Passive
   c. Position held, close to roll date → default_roll_state_if_undecided
                                          (Force / Force_Outright / Close / Ask)

3. Forward illiquid:
   a. Position held + within passive window (0 <= days_until_roll < passive_start_days)
      + forward has any volume?
      → Passive  (start natural migration before forced roll)
   b. Close to roll date (< near_expiry_days)?
      → No_Open
   c. Far from roll date:
      → No_Roll  IF allowable from current state
      → current state  OTHERWISE  (e.g. No_Open0 stays No_Open)
```

The expired + position case is handled entirely by Stage 1 — Stage 2 is never
reached for it.

### Liquidity test

The forward contract is **liquid** when either:

- `relative_volume > auto_roll_if_relative_volume_higher_than`, or
- `relative_volume > min_relative_volume` AND `absolute_forward_volume > min_absolute_volume`

where `relative_volume = forward_volume / priced_volume`.

---

## Configuration

Parameters live under `roll_status_auto_update` in `defaults.yaml` (or your
override in `private_config.yaml`):

```yaml
roll_status_auto_update:
  # Relative volume threshold: if forward/priced > this, treat as liquid
  # regardless of absolute volume.
  auto_roll_if_relative_volume_higher_than: 1.0

  # Combined threshold: both must be exceeded for forward to be considered liquid.
  min_relative_volume: 0.01
  min_absolute_volume: 100

  # Days before priced-contract expiry at which:
  #   - No_Roll → No_Open (if forward illiquid and position is held)
  #   - Passive → default_roll_state_if_undecided (if forward liquid and position held)
  #   - any state → Force (Stage 1 expiry escalation when position is held)
  near_expiry_days: 10

  # What to do when liquid + position + close to roll.
  # One of: Force, Force_Outright, Close, or "Ask" (interactive only —
  # non-interactive job auto-resolves Ask to Force and logs CRITICAL).
  default_roll_state_if_undecided: Force

  # Roll adjusted prices when the priced contract has expired and no position
  # is held. Also covers expired carry/forward contracts via the same flag.
  auto_roll_expired: true

  # Days before the desired roll date at which a held position starts passive
  # rolling, provided the forward has *some* volume. Bounded: negative values
  # do not count as "early passive" — they fall under late-roll escalation.
  passive_start_days: 30

  # Max trading days a Force state may persist without rolling before the
  # non-interactive job escalates to Force_Outright.
  force_roll_max_trading_days: 2
```

---

## Safety features

### Stuck-Force escalation

If an instrument has been in `Force` for more than `force_roll_max_trading_days`
trading days without rolling, the job escalates to `Force_Outright` and logs at
CRITICAL:

```
CRITICAL: FORCE ROLL STUCK for <code>: In Force state for 3 trading days
(threshold: 2) without completing roll.
Escalating to Force_Outright to execute outright orders instead of spread.
```

Trading days are counted as weekdays since the Force timestamp was recorded.
If no timestamp exists, escalation is skipped.

### Expiry escalation

If the priced contract is within `near_expiry_days` of expiry and a position
is still held, the state is forced to `Force` regardless of suggestion. Logged
at CRITICAL.

### Transition validation

Before applying any state change, the proposed transition is checked against
the allowable matrix. Invalid transitions are logged at CRITICAL and skipped —
no change is made, preventing the database from drifting into an inconsistent
state:

```
CRITICAL: INVALID TRANSITION for <code>: Cannot change from No_Open to No_Roll (position=0).
Allowable transitions: ['Roll_Adjusted', 'Passive', 'No_Open']. Skipping — manual intervention needed.
```

### `Ask` auto-resolution

If `default_roll_state_if_undecided` is `"Ask"` (intended for interactive use),
the non-interactive job cannot prompt. It auto-resolves to `Force` (the safest
automated choice) and logs at CRITICAL so the operator sees the misconfiguration
and can change the setting.

### Roll_Adjusted forward-fill

The job rolls adjusted prices with `allow_auto_forward_fill=True`, so it never
blocks on stdin. If the normal roll calculation fails, it automatically retries
with forward-fill before giving up and logging a warning.

### Roll_Adjusted orphan-position guard

Before applying `Roll_Adjusted`, all current DB contract positions for the
instrument are scanned. If any non-zero DB position maps to an actual expiry
inside `near_expiry_days`, the transition is blocked and logged at CRITICAL:

```
CRITICAL: ROLL_ADJUSTED BLOCKED for <code>: expiring DB contract positions exist
despite zero priced-contract position: [...].
Leaving roll state unchanged and requiring manual/Force roll review.
```

The guard is deliberately conservative — it leaves the instrument unchanged
rather than guessing a replacement state, because the correct next step depends
on broker/DB reconciliation.

### Exception isolation

Exceptions during processing of any single instrument are caught, logged at
CRITICAL, and the loop continues. One broken instrument never blocks the rest
of the roll cycle.

### Missing-contract tolerance during selection

`check_if_any_key_contract_has_expired` (used to widen the auto-cycle
selection) reads each key contract (carry, priced, forward) from the contracts
DB. Two distinct failure modes are handled:

- **Forward not yet sampled.** A fresh `Roll_Adjusted` advances the forward
  slot in the multiple-prices chain *before* `update_sampled_contracts` writes
  the new contract. The next auto-roll invocation would otherwise raise
  `ContractNotFound` and exit unhandled, leaving `currently_running=True` in
  the process control DB and triggering a spurious "crashed" alert from the
  system monitor. The helper now treats `ContractNotFound` for the forward
  leg as not-expired (logged at DEBUG) and continues.

- **Missing carry or priced contract.** Carry and priced legs should always be
  sampled; a missing one implies a delisted contract, a manual DB deletion, or
  a stale/mistyped multiple-prices entry. The helper logs at CRITICAL and
  skips that leg, so visibility is preserved without crashing the run.

---

## Logging

Every state change is logged with a `reason=` field identifying which decision
branch selected the new state:

```
Auto-updating roll state for <code>: Force -> Force_Outright
reason=force_roll_stuck
position=-1 days_until_expiry=27 days_to_roll=-8 rel_vol=0.0828 fwd_vol=94
```

| `reason` | Meaning |
|---|---|
| `expiry_escalation` | Stage 1 override: contract near/past expiry with position held |
| `force_roll_stuck` | Stage 0 override: Force spread order stuck for too many trading days |
| `late_roll_escalation` | Stage 1.5: past desired roll date with position held |
| `early_passive` | Within passive start window, forward has some volume |
| `forward_illiquid_close_to_roll` | Forward illiquid, close to roll date → No_Open |
| `roll_adjusted` | No position, forward liquid or expired |
| `expired_key_contract_auto_roll` | Carry/key contract expired, no position, auto_roll_expired=True |
| `no_roll` | Forward illiquid, far from roll date |
| `auto_resolved_ask` | Config says `Ask` but running non-interactively |
| `default` | None of the above matched |

A diagnostic log line is emitted **before** each decision, recording priced
contract id, actual expiry, priced-contract position, `days_until_expiry`,
`days_until_roll`, and all current DB contract positions. This line is always
present, even when no state change is made.

---

## Scheduling

The recommended schedule is a **single nightly run**, after
`run_daily_update_multiple_adjusted_prices` so roll decisions use today's
forward-contract volume and liquidity:

```cron
# Nightly full pass — must run after run_daily_update_multiple_adjusted_prices for fresh data.
30 23 * * 1-5 $SCRIPT_PATH/run_auto_roll_status >> $ECHO_PATH/run_auto_roll_status.txt 2>&1
```

One run per day is sufficient: the job is idempotent, and a single late-evening
pass evaluates every instrument with the day's full volume data — which is
what `auto_roll_if_relative_volume_higher_than`, `min_relative_volume`, and
`min_absolute_volume` are testing against.

### Twice-daily setups

A morning safety pass can close the gap between the previous nightly run and
the next morning's expiry checker (`run_daily_fx_and_contract_updates` at
07:05). **Do not simply add a second cron line**: the framework's wait loop
will hold the morning instance in `_start_or_wait` until the configured
`process_configuration_start_time` is reached, at which point it races with
the evening cron. The morning instance is the one that crashed in production
when both fired in the same minute, leaving the process-control record in
`currently_running=True`.

To run a real morning pass, widen the configured window so the morning
instance has its own slot:

```yaml
# syscontrol/control_config.yaml (or private_control_config.yaml)
process_configuration_start_time:
  run_auto_roll_status: '07:00'   # was '23:30' — now allows a morning slot
process_configuration_stop_time:
  run_auto_roll_status: '23:55'
```

Then both cron lines can fire:

```cron
00 07 * * 1-5 $SCRIPT_PATH/run_auto_roll_status >> $ECHO_PATH/run_auto_roll_status.txt 2>&1
30 23 * * 1-5 $SCRIPT_PATH/run_auto_roll_status >> $ECHO_PATH/run_auto_roll_status.txt 2>&1
```

If `process_configuration_start_time` remains at `'23:30'` (the shipped
default), keep only the evening cron line.

The look-ahead window used to select instruments is:

```python
days_ahead = max(passive_start_days, near_expiry_days)
```

so an instrument that needs early-passive rolling is still included even
before it enters the `near_expiry_days` window.

---

## Manual override

When the job logs CRITICAL and skips an instrument, drive the fix interactively:

```bash
python -m sysproduction.interactive_update_roll_status
```

Pick option 1 ("Manually input instrument codes") and enter the code. The tool
shows the current state, allowable transitions, and prompts for the correct
next state.

---

## Common scenarios

### Contract expiring with a position held — expiry escalation

`days_until_expiry < near_expiry_days` (default: 10) and the priced position is
non-zero. The job overrides any other suggested state and sets the instrument
to `Force`. The stack handler picks up a spread roll order on its next cycle.

A CRITICAL email is expected. Check the reconcile report the next day to
confirm the roll completed. If the instrument is already locked by the stack
handler, unlock it via `interactive_order_stack`, post a balance trade to
reconcile, then set `Force` manually.

### Position held past the desired roll date — late-roll escalation

`days_until_roll < 0` with a position held, but `days_until_expiry` is still
≥ `near_expiry_days`. Stage 1.5 fires before normal logic. If the instrument
is already in `Force`, `Force_Outright`, or `Close`, it stays there — no
de-escalation. Anything else is escalated to `Force`.

If the forward is illiquid, the stuck-Force escalation can subsequently promote
the instrument to `Force_Outright` after `force_roll_max_trading_days`. For
instruments with consistently poor spread markets, override per-instrument:

```yaml
roll_status_auto_update_overrides:
  <CODE>:
    default_roll_state_if_undecided: Force_Outright
    force_roll_max_trading_days: 1
```

### `No_Open` with no position, forward still illiquid

The position was closed, but the forward is still illiquid and the roll date
is approaching. `No_Open0` does not allow `No_Roll`, so the job falls back to
the current state (`No_Open`) silently. The instrument stays in `No_Open` until
the forward becomes liquid (→ `Roll_Adjusted`) or a new position is opened.

### Roll_Adjusted needed but forward prices are missing

The roll retries with forward-fill automatically. If that also fails, a warning
is logged and the state is left unchanged.

### Forward contract just rolled but not yet sampled

Immediately after a `Roll_Adjusted` succeeds, the multiple-prices chain
references a new forward contract that `update_sampled_contracts` has not yet
written to the contracts DB. The selection helper handles this silently
(DEBUG log only) — no action needed. The contract will be sampled by the next
`run_daily_fx_and_contract_updates` cycle.

If you see a CRITICAL log such as
`Key contract <code>/<id> (...c|...p) referenced by multiple-prices but
missing from contracts DB`, it is **not** the post-roll case — it indicates a
delisted contract, a manual DB deletion, or a corrupt multiple-prices entry,
and needs investigation.

### Roll_Adjusted blocked by an expiring non-priced DB leg

The suggested state is `Roll_Adjusted` (usually because the priced contract has
no position), but another DB contract position for the same instrument is
non-zero and near actual expiry. The job leaves the roll state unchanged and
emits CRITICAL. Reconcile DB and broker positions before acting: balance out a
genuinely orphaned DB leg, or drive a manual/Force roll if the broker still
holds the position.

### `default_roll_state_if_undecided` is `"Ask"`

Change it to `Force` (or `Force_Outright` / `Close`) in your config:

```yaml
roll_status_auto_update:
  default_roll_state_if_undecided: Force
```

---

## Files

| File | Purpose |
|---|---|
| `sysproduction/run_auto_roll_status.py` | Entry point, `processToRun` integration, escalations, orphan-position guard |
| `sysproduction/interactive_update_roll_status.py` | Shared suggestion logic: `suggest_roll_state_for_instrument`, `modify_roll_state` |
| `sysobjects/production/roll_state.py` | `RollState` enum and transition matrix |
| `tests/test_auto_roll_status.py` | Unit tests for suggestion branches, escalations, transitions |
| `sysdata/config/defaults.yaml` | Default `roll_status_auto_update` parameters |
