Tinman Multi-Beacon Validation Notes
====================================

Current Verification State
--------------------------

The fork has been validated in three layers so far:

1. Syntax validation
   - `python3 -m py_compile klippy/extras/beacon.py`
   - `python3 -m py_compile test/test_beacon_multisensor.py`
2. Focused regression tests
   - `python3 -m unittest test.test_beacon_multisensor`
3. Manual architecture review against upstream Beacon and Klipper probe flow

What The Regression Tests Cover
-------------------------------

The regression suite in `test/test_beacon_multisensor.py` covers:

- Beacon tracker command registration
- active-sensor routing for Beacon gcode commands
- active-sensor routing for Beacon webhooks
- override behavior when an unnamed default Beacon exists
- one-time installation of the shared `probe` router
- probe router delegation to the selected active sensor
- endstop router stepper fanout / de-duplication
- management command status output
- fail-loud behavior when there are multiple sensors and no valid active sensor

What Is Still Not Proven
------------------------

The current test coverage does not yet prove:

- live MCU communication with two physical Beacon devices
- contact probing on multiple tools
- end-to-end `BED_MESH_CALIBRATE` on a real machine
- `QUAD_GANTRY_LEVEL`, `Z_TILT_ADJUST`, or `SCREWS_TILT_ADJUST` on live hardware
- interaction with real toolchange macros, parking, offsets, and bed compensation
- startup / restart behavior on a printer using two full Beacon configs

Recommended Hardware Acceptance Sequence
----------------------------------------

Use this order on the first real printer:

1. Boot / config parse
   - confirm both Beacon sensors load
   - run `BEACON_LIST`
   - run `BEACON_STATUS`
2. Sensor selection
   - run `BEACON_SELECT SENSOR=t0`
   - confirm `BEACON_QUERY` uses `t0`
   - run `BEACON_SELECT SENSOR=t1`
   - confirm `BEACON_QUERY` uses `t1`
3. Basic probing
   - with each tool active, run `PROBE`
   - with each tool active, run `PROBE_ACCURACY`
4. Z-homing and safe home
   - verify `G28 Z` uses the currently selected Beacon
5. Bed mesh
   - run `BED_MESH_CALIBRATE` after selecting each tool
6. Leveling routines
   - if used on the machine, validate `Z_TILT_ADJUST`
   - if used on the machine, validate `QUAD_GANTRY_LEVEL`
   - if used on the machine, validate `SCREWS_TILT_ADJUST`
7. Toolchange workflow
   - trigger actual `T0` / `T1` macros
   - confirm the active Beacon follows the toolchange every time
8. Restart persistence
   - restart Klipper
   - verify expected startup default and manual reselection behavior

Suggested Pass Criteria
-----------------------

Do not publish as "working" until the following are true:

- both sensors enumerate cleanly after restart
- toolchange macros consistently update the active Beacon
- probing and homing never use the wrong tool
- bed mesh and leveling routines complete with each selected tool
- no silent fallback occurs when the active sensor is invalid

Practical Next Step
-------------------

The software-side routing logic is now regression tested. The next real proof
point is a printer config smoke test on target hardware with two Beacon sensors
and repeatable `T0` / `T1` switching.
