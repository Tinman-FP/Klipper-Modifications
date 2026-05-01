Tinman Multi-Beacon Fork
========================

Purpose
-------

This fork starts from upstream Klipper and vendors Beacon into the tree so that
Beacon can support multiple configured sensors without forcing every workflow to
address them with `SENSOR=` every time.

The first-pass goal is not to rewrite Klipper core. It is to keep the fork easy
to rebase while making multi-tool Beacon setups practical for toolchangers,
IDEX, and similar machines.

Upstream Sources
----------------

- Klipper upstream base inspected from commit `373f200ca`
- Beacon upstream base inspected from commit `7c71e98`

Architecture
------------

The fork keeps all of the new behavior localized in `klippy/extras/beacon.py`.

Key ideas:

1. Beacon is vendored directly into `klippy/extras/beacon.py` instead of being
   installed by symlink.
2. A `BeaconTracker` manages every configured Beacon sensor.
3. A single global `probe` object is exposed through a router.
4. The router delegates probing to the currently active Beacon sensor.
5. Default Beacon commands and webhook routes fall back to the active sensor
   when there is no unnamed `[beacon]` section.
6. If an unnamed `[beacon]` section exists, `BEACON_SELECT` still takes
   precedence so toolchange macros can override the default sensor at runtime.

New Commands
------------

- `BEACON_SELECT SENSOR=<name>`
  - sets the active Beacon sensor
- `BEACON_LIST`
  - lists configured Beacon sensors and flags `active` / `probe`
- `BEACON_STATUS`
  - reports the current active sensor and the active probe sensor

Config Shape
------------

Current upstream Beacon supports named sensors using the `sensor` prefix.

Use:

- `[beacon]` for the unnamed default sensor
- `[beacon sensor t0]`
- `[beacon sensor t1]`

Do not use older local shorthand such as `[beacon beacon_t1]`. That syntax does
not match current upstream Beacon parsing.

Recommended Toolchanger Pattern
-------------------------------

1. Configure one Beacon section per toolhead.
2. Set `register_as_probe: True` on each sensor that must be usable as the
   active Z probe.
3. In each toolchange macro, call `BEACON_SELECT SENSOR=<tool-sensor-name>`.
4. Let shared commands such as `PROBE`, `BED_MESH_CALIBRATE`, and bed leveling
   flows use the active router.

Example:

```ini
[gcode_macro T0]
gcode:
    ACTIVATE_EXTRUDER EXTRUDER=extruder
    BEACON_SELECT SENSOR=t0

[gcode_macro T1]
gcode:
    ACTIVATE_EXTRUDER EXTRUDER=extruder1
    BEACON_SELECT SENSOR=t1
```

Rebase Strategy
---------------

Keep this fork maintainable by treating it as:

- upstream Klipper
- plus a vendored Beacon module
- plus a small Tinman patch set concentrated in Beacon routing

Suggested workflow:

1. `git fetch upstream beacon-upstream`
2. `git rebase upstream/master`
3. compare current `klippy/extras/beacon.py` against `beacon-upstream/master:beacon.py`
4. reapply or refresh the Tinman routing changes
5. run a syntax pass and a printer config smoke test

The design intent is that most future merge work should stay inside:

- `klippy/extras/beacon.py`
- this document
- any example configs or macros added for multi-Beacon usage

Known Limits In This First Pass
-------------------------------

- The active sensor model is intentionally simple: one global active Beacon at a
  time.
- Toolchange macros are expected to switch the active sensor explicitly.
- The fork does not yet add per-tool automatic sensor switching in Klipper core.
- The fork does not yet add automated regression tests for multi-Beacon flows.

Next Good Steps
---------------

1. Add printer-side regression configs for a two-tool Beacon setup.
2. Exercise `Z_TILT_ADJUST`, `QUAD_GANTRY_LEVEL`, and `BED_MESH_CALIBRATE`
   against active-sensor switching.
3. Decide whether contact mode needs dedicated routing helpers per tool.
4. Break Tinman-specific changes into a minimal patch series for easier rebases.
