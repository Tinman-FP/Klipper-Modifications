import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "klippy"))
sys.path.insert(0, str(REPO_ROOT))

from extras import beacon  # noqa: E402


class FakeGCode:
    def __init__(self):
        self.commands = {}
        self.responses = []

    def register_command(self, cmd, func, when_not_ready=False, desc=None):
        self.commands[cmd] = {
            "func": func,
            "when_not_ready": when_not_ready,
            "desc": desc,
        }


class FakeWebhooks:
    def __init__(self):
        self.endpoints = {}

    def register_endpoint(self, path, callback):
        self.endpoints[path] = callback


class FakePins:
    def __init__(self):
        self.chips = {}
        self.calls = []

    def register_chip(self, name, chip):
        self.chips[name] = chip
        self.calls.append((name, chip))


class FakePrinter:
    command_error = RuntimeError

    def __init__(self):
        self.objects = {
            "gcode": FakeGCode(),
            "webhooks": FakeWebhooks(),
            "pins": FakePins(),
        }
        self.added = []

    def lookup_object(self, name, default=None):
        return self.objects.get(name, default)

    def add_object(self, name, obj):
        self.objects[name] = obj
        self.added.append((name, obj))


class FakeConfig:
    def __init__(self, printer):
        self._printer = printer

    def get_printer(self):
        return self._printer


class FakeGcmd:
    def __init__(self, params=None):
        self.params = params or {}
        self.responses = []

    def get(self, key, default=None):
        return self.params.get(key, default)

    def error(self, msg):
        return RuntimeError(msg)

    def respond_info(self, msg):
        self.responses.append(msg)


class FakeReq:
    def __init__(self, method, params=None):
        self.method = method
        self.params = params or {}

    def get(self, key, default=None):
        return self.params.get(key, default)

    def error(self, msg):
        return RuntimeError(msg)


class FakeProbeWrapper:
    def __init__(self, label):
        self.label = label
        self.calls = []

    def multi_probe_begin(self):
        self.calls.append(("multi_probe_begin",))
        return f"{self.label}:multi_probe_begin"

    def multi_probe_end(self):
        self.calls.append(("multi_probe_end",))
        return f"{self.label}:multi_probe_end"

    def get_offsets(self, gcmd=None):
        self.calls.append(("get_offsets", gcmd))
        return (1, 2, 3) if self.label == "t0" else (4, 5, 6)

    def get_lift_speed(self, gcmd=None):
        self.calls.append(("get_lift_speed", gcmd))
        return 20 if self.label == "t0" else 40

    def run_probe(self, gcmd, *args, **kwargs):
        self.calls.append(("run_probe", gcmd))
        return f"{self.label}:run_probe"

    def get_probe_params(self, gcmd=None):
        self.calls.append(("get_probe_params", gcmd))
        return {"lift_speed": self.get_lift_speed(gcmd)}

    def start_probe_session(self, gcmd):
        self.calls.append(("start_probe_session", gcmd))
        return self

    def get_status(self, eventtime):
        return {"name": self.label}


class FakeMcuProbe:
    def __init__(self, label):
        self.label = label
        self.steppers = []

    def get_mcu(self):
        return f"mcu:{self.label}"

    def add_stepper(self, stepper):
        self.steppers.append(stepper)

    def get_steppers(self):
        return list(self.steppers)

    def home_start(self, *args, **kwargs):
        return f"{self.label}:home_start"

    def home_wait(self, *args, **kwargs):
        return f"{self.label}:home_wait"

    def query_endstop(self, *args, **kwargs):
        return f"{self.label}:query_endstop"

    def get_position_endstop(self):
        return f"{self.label}:position_endstop"


class FakeBeacon:
    def __init__(self, tracker, name):
        self.id = beacon.BeaconId(name, tracker)
        self.probe_wrapper = FakeProbeWrapper(
            "default" if name is None else name)
        self.mcu_probe = FakeMcuProbe("default" if name is None else name)


class BeaconMultiSensorTests(unittest.TestCase):
    def make_tracker(self):
        printer = FakePrinter()
        config = FakeConfig(printer)
        return beacon.BeaconTracker(config, printer), printer

    def test_tracker_registers_management_commands(self):
        tracker, printer = self.make_tracker()
        self.assertIn("BEACON_SELECT", printer.lookup_object("gcode").commands)
        self.assertIn("BEACON_LIST", printer.lookup_object("gcode").commands)
        self.assertIn("BEACON_STATUS", printer.lookup_object("gcode").commands)
        self.assertEqual(tracker.get_status(0)["sensors"], [])

    def test_dispatch_gcode_uses_active_named_sensor_without_default(self):
        tracker, _printer = self.make_tracker()
        calls = []
        handlers = {
            "t0": lambda gcmd: calls.append("t0"),
            "t1": lambda gcmd: calls.append("t1"),
        }
        tracker.sensors = {"t0": object(), "t1": object()}
        tracker.active_sensor = "t1"
        tracker.dispatch_gcode(handlers, FakeGcmd())
        self.assertEqual(calls, ["t1"])

    def test_beacon_select_overrides_unnamed_default(self):
        tracker, _printer = self.make_tracker()
        calls = []
        handlers = {
            None: lambda gcmd: calls.append("default"),
            "t1": lambda gcmd: calls.append("t1"),
        }
        tracker.sensors = {None: object(), "t1": object()}
        tracker.active_sensor = "t1"
        tracker.dispatch_gcode(handlers, FakeGcmd())
        self.assertEqual(calls, ["t1"])

    def test_dispatch_webhook_uses_active_sensor(self):
        tracker, _printer = self.make_tracker()
        calls = []
        tracker.endpoints["beacon/status"] = {
            "t0": lambda req: calls.append("t0"),
            "t1": lambda req: calls.append("t1"),
        }
        tracker.sensors = {"t0": object(), "t1": object()}
        tracker.active_sensor = "t1"
        tracker.dispatch_webhook(FakeReq("beacon/status"))
        self.assertEqual(calls, ["t1"])

    def test_register_probe_sensor_installs_router_once_and_tracks_active(self):
        tracker, printer = self.make_tracker()
        t0 = FakeBeacon(tracker, "t0")
        t1 = FakeBeacon(tracker, "t1")
        tracker.sensors = {"t0": t0, "t1": t1}

        tracker.register_probe_sensor(t0)
        tracker.register_probe_sensor(t1)

        pins = printer.lookup_object("pins")
        self.assertEqual(len(pins.calls), 1)
        self.assertIn("probe", printer.objects)
        self.assertIs(tracker.probe_router, printer.lookup_object("probe"))
        self.assertEqual(tracker.get_active_sensor_name(
            require_probe=True), "t0")

    def test_probe_router_delegates_to_selected_sensor(self):
        tracker, printer = self.make_tracker()
        t0 = FakeBeacon(tracker, "t0")
        t1 = FakeBeacon(tracker, "t1")
        tracker.sensors = {"t0": t0, "t1": t1}
        tracker.register_probe_sensor(t0)
        tracker.register_probe_sensor(t1)
        tracker.set_active_sensor("t1")

        router = printer.lookup_object("probe")
        self.assertEqual(router.get_offsets(), (4, 5, 6))
        self.assertEqual(router.get_lift_speed(), 40)
        self.assertEqual(router.run_probe(FakeGcmd()), "t1:run_probe")
        self.assertEqual(router.start_probe_session(
            FakeGcmd()), t1.probe_wrapper)

        mcu_probe = router.setup_pin(
            "endstop", {"pin": "z_virtual_endstop",
                "invert": False, "pullup": False}
        )
        self.assertEqual(mcu_probe.get_mcu(), "mcu:t1")
        self.assertEqual(mcu_probe.get_position_endstop(),
                         "t1:position_endstop")

    def test_endstop_router_deduplicates_steppers(self):
        tracker, printer = self.make_tracker()
        t0 = FakeBeacon(tracker, "t0")
        t1 = FakeBeacon(tracker, "t1")
        tracker.sensors = {"t0": t0, "t1": t1}
        tracker.register_probe_sensor(t0)
        tracker.register_probe_sensor(t1)

        router = printer.lookup_object("probe")
        endstop = router.setup_pin(
            "endstop", {"pin": "z_virtual_endstop",
                "invert": False, "pullup": False}
        )
        endstop.add_stepper("stepper_z")
        self.assertEqual(t0.mcu_probe.get_steppers(), ["stepper_z"])
        self.assertEqual(t1.mcu_probe.get_steppers(), ["stepper_z"])
        self.assertEqual(endstop.get_steppers(), ["stepper_z"])

    def test_management_commands_report_status(self):
        tracker, _printer = self.make_tracker()
        t0 = FakeBeacon(tracker, None)
        t1 = FakeBeacon(tracker, "t1")
        tracker.sensors = {None: t0, "t1": t1}
        tracker.probe_sensors = {None: t0, "t1": t1}
        tracker.active_sensor = "t1"

        gcmd = FakeGcmd({"SENSOR": "t1"})
        tracker.cmd_BEACON_SELECT(gcmd)
        self.assertIn("Active Beacon sensor set to 't1'", gcmd.responses[0])

        list_cmd = FakeGcmd()
        tracker.cmd_BEACON_LIST(list_cmd)
        self.assertIn("t1 (active, probe)", list_cmd.responses[0])
        self.assertIn("default (probe, unnamed)", list_cmd.responses[0])

        status_cmd = FakeGcmd()
        tracker.cmd_BEACON_STATUS(status_cmd)
        self.assertIn("active sensor: t1", status_cmd.responses[0])
        self.assertIn("active probe sensor: t1", status_cmd.responses[0])

    def test_missing_active_sensor_requires_selection(self):
        tracker, _printer = self.make_tracker()
        tracker.sensors = {"t0": object(), "t1": object()}
        tracker.active_sensor = "ghost"
        with self.assertRaisesRegex(
                RuntimeError, "BEACON_SELECT SENSOR=<name>"):
            tracker.dispatch_gcode(
                {"t0": lambda g: None, "t1": lambda g: None}, FakeGcmd())


if __name__ == "__main__":
    unittest.main()
