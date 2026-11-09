# Manual targets across restarts

Manual temperature holds use Thermostat Pro Timeline's saved room pauses, so
they survive Home Assistant restarts without changing schedule blocks.

Changing a scheduled climate entity's target creates a saved, timed pause for
that room until its next schedule block starts or ends, or midnight rollover.
This also covers physical dial changes forwarded to the scheduled climate by an
existing thermostat integration or automation. Other rooms keep their schedules.

The thermostat remains responsible for restoring its own target after a Home
Assistant restart. Timeline respects the saved pause during startup and late
entity recovery, then resumes its schedule when the hold expires. If Home
Assistant is stopped across the expiry, the current schedule applies on startup.

Returning the manual target to the currently scheduled temperature cancels the
generated hold. Explicit user pauses and disabled schedule rows are preserved.
Scheduled temperature writes do not create new manual holds.

Generated entries use the existing `settings.room_pause` mapping and native
`set_store` service. They include `source: manual_target` and `target_c` alongside
the standard `indef` and `until_ms` fields. No internal storage files are edited.

## Validation

```sh
python3 -m unittest discover -s tests -v
node --test tests/*.test.cjs
```

The existing regression workflow runs these checks on pushes and pull requests.
The manual-target tests cover startup and delayed reconciliation, late entity
recovery, expiry and missed boundaries, independent rooms, explicit pauses,
superseded events, stable listeners, midnight, and Fahrenheit conversion.

