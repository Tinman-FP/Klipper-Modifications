# Dual Z Probe Klipper Modifications

This repository packages a Tinman-maintained Klipper modification for machines
that need two independently selectable Z probe sensors, such as toolchangers,
IDEX printers, dual-carriage systems, or any printer where each toolhead carries
its own Beacon probe.

The working implementation is currently built around Beacon sensors and keeps
the patch set concentrated in `klippy/extras/beacon.py` so the fork remains
easier to rebase against upstream Klipper and Beacon.

## Upstream Bases

- Klipper upstream base inspected from commit `373f200ca`
- Beacon upstream base inspected from commit `7c71e98`
- License: GNU GPLv3, inherited from Klipper and Beacon sources

## What Changed

- Vendored Beacon support into `klippy/extras/beacon.py` instead of relying on a
  symlink or external install step.
- Added a multi-sensor tracker so more than one Beacon can be configured in one
  Klipper instance.
- Added an active probe router that exposes one shared Klipper `probe` object
  while delegating probe operations to the currently selected Beacon sensor.
- Added active-sensor routing for default Beacon gcode commands and Beacon
  webhook routes.
- Added explicit management commands:
  - `BEACON_SELECT SENSOR=<name>` selects the active Z probe sensor.
  - `BEACON_LIST` lists configured Beacon sensors and active/probe flags.
  - `BEACON_STATUS` reports the currently selected sensor and active probe.
- Added sample dual-sensor/toolchanger configuration in
  `config/sample-tinman-multi-beacon-toolchanger.cfg`.
- Added focused regression coverage in `test/test_beacon_multisensor.py`.
- Added documentation for architecture and validation in:
  - `docs/tinman_multi_beacon.md`
  - `docs/tinman_multi_beacon_validation.md`

## Why This Matters

Standard single-probe assumptions are awkward on machines where the active
toolhead changes and each toolhead has a different physical Z probe location.
This modification lets macros select the probe that belongs to the active tool
before normal Klipper probing routines run.

## Advantages

- Better dual-toolhead safety: probing can follow the selected tool instead of
  silently using the wrong sensor.
- Cleaner macros: toolchange macros can switch probes with one explicit
  `BEACON_SELECT` command.
- Compatibility with shared Klipper flows: `PROBE`, `PROBE_ACCURACY`,
  `BED_MESH_CALIBRATE`, `Z_TILT_ADJUST`, `QUAD_GANTRY_LEVEL`, and homing flows
  can operate through the active shared `probe` router.
- Fail-loud behavior: multi-sensor configurations without a valid active sensor
  raise an error instead of falling back silently.
- Rebase-friendly patch shape: most custom behavior is isolated to Beacon
  routing, docs, sample config, and tests.
- Practical path to hardware validation: the validation document lists the
  acceptance sequence before this should be treated as proven on a live printer.

## Suggested Configuration Pattern

```ini
[beacon sensor t0]
serial: /dev/serial/by-id/usb-Beacon_Beacon_RevH_123456789-if00
register_as_probe: True

[beacon sensor t1]
serial: /dev/serial/by-id/usb-Beacon_Beacon_RevH_987654321-if00
register_as_probe: True

[gcode_macro T0]
gcode:
    ACTIVATE_EXTRUDER EXTRUDER=extruder
    BEACON_SELECT SENSOR=t0

[gcode_macro T1]
gcode:
    ACTIVATE_EXTRUDER EXTRUDER=extruder1
    BEACON_SELECT SENSOR=t1
```

## Validation Status

Software-side validation currently covers:

- Python syntax checks for the modified Beacon module and regression test.
- Unit tests for tracker registration, active-sensor routing, probe routing,
  endstop routing, management commands, and fail-loud behavior.
- Manual architecture review against upstream Beacon and Klipper probe flow.

Hardware validation is still required before calling this production-ready.
Recommended live-printer checks are documented in
`docs/tinman_multi_beacon_validation.md`.

## Credits And Attribution

This work stands on the shoulders of several upstream projects and contributors:

- The Klipper project and its contributors for the firmware platform, probe
  infrastructure, documentation, and GPLv3 codebase.
- Beacon3D and the Beacon Klipper contributors for Beacon probing support.
- Beacon source authors credited in `klippy/extras/beacon.py`, including
  Matt Baker, Lasse Dalegaard, and Beacon3D.
- Tinman / William Tinney for the dual-probe use case, integration direction,
  validation goals, and packaging of this modification set.
- OpenAI Codex for implementation assistance, documentation pass, and regression
  scaffolding in this prepared fork.

This repository is not an upstream Klipper or Beacon release. It is a prepared
modification fork intended to make the dual-Z-probe / multi-Beacon workflow easy
to inspect, test, and improve.
