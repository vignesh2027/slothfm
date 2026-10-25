"""A sloth conserves energy: the night shift only works when the laptop is plugged in."""
import subprocess


def on_ac_power():
    try:
        out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return True                    # not a Mac, or no battery: treat as plugged in
    return "AC Power" in out or "Battery Power" not in out
