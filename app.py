"""
Projector Screen Control
------------------------
Flask web application that controls motorised projector screens via four
relays connected to a Raspberry Pi.

Relay wiring (BCM numbering):
  North UP   relay trigger → GPIO 17  (physical pin 11)
  North DOWN relay trigger → GPIO 27  (physical pin 13)
  South UP   relay trigger → GPIO 22  (physical pin 15)
  South DOWN relay trigger → GPIO 23  (physical pin 16)
  VCC  (all relays) → 5 V rail (physical pin 2 or 4)
  GND  (all relays) → Ground   (physical pin 6, 9, 14 or 20)

Each relay is energised for RELAY_PULSE_SECONDS (default 1 s) then released.

HTTP endpoints (usable by Stream Deck / Bitfocus Companion):
  GET /up    – trigger the North UP relay
  GET /down  – trigger the North DOWN relay
  GET /up2   – trigger the South UP relay
  GET /down2 – trigger the South DOWN relay
  GET /      – serve the manual-control web page
"""

import threading
import time

from flask import Flask, jsonify, render_template

# ---------------------------------------------------------------------------
# GPIO setup – falls back to a stub when RPi.GPIO is unavailable (dev / CI)
# ---------------------------------------------------------------------------
try:
    import RPi.GPIO as GPIO  # type: ignore[import-untyped]
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False

    class _GPIOStub:
        BCM = "BCM"
        OUT = "OUT"
        HIGH = True
        LOW = False

        def setmode(self, _mode):
            pass

        def setup(self, _pin, _direction):
            pass

        def output(self, pin, state):
            print(f"[GPIO stub] pin {pin} → {'HIGH' if state else 'LOW'}")

        def cleanup(self):
            pass

    GPIO = _GPIOStub()  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
NORTH_UP_PIN = 17        # BCM 17 – physical pin 11
NORTH_DOWN_PIN = 27      # BCM 27 – physical pin 13
SOUTH_UP_PIN = 22        # BCM 22 – physical pin 15
SOUTH_DOWN_PIN = 23      # BCM 23 – physical pin 16
RELAY_PULSE_SECONDS = 1  # how long each relay stays energised

# ---------------------------------------------------------------------------
# GPIO initialisation
# ---------------------------------------------------------------------------
GPIO.setmode(GPIO.BCM)
for _pin in (NORTH_UP_PIN, NORTH_DOWN_PIN, SOUTH_UP_PIN, SOUTH_DOWN_PIN):
    GPIO.setup(_pin, GPIO.OUT)
    GPIO.output(_pin, GPIO.LOW)

# Separate locks prevent overlapping relay pulses per projector
_north_relay_lock = threading.Lock()
_south_relay_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = Flask(__name__)


def _trigger_async(pin: int, lock: threading.Lock) -> bool:
    """
    Start a relay pulse in a background thread.

    Returns True if the pulse was started, False if a pulse is already running.
    The thread is *not* a daemon so the pulse always completes even if the main
    process begins to shut down.
    """
    if not lock.acquire(blocking=False):
        return False
    # Lock was acquired; release it inside the thread after the pulse.
    def _run() -> None:
        try:
            GPIO.output(pin, GPIO.HIGH)
            time.sleep(RELAY_PULSE_SECONDS)
            GPIO.output(pin, GPIO.LOW)
        finally:
            lock.release()

    t = threading.Thread(target=_run, daemon=False)
    t.start()
    return True


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/up", methods=["GET", "POST"])
def relay_up():
    """Trigger the North UP relay (raises the north screen)."""
    if not _trigger_async(NORTH_UP_PIN, _north_relay_lock):
        return jsonify({"status": "busy", "action": "up"}), 409
    return jsonify({"status": "ok", "action": "up"})


@app.route("/down", methods=["GET", "POST"])
def relay_down():
    """Trigger the North DOWN relay (lowers the north screen)."""
    if not _trigger_async(NORTH_DOWN_PIN, _north_relay_lock):
        return jsonify({"status": "busy", "action": "down"}), 409
    return jsonify({"status": "ok", "action": "down"})


@app.route("/up2", methods=["GET", "POST"])
def relay_up2():
    """Trigger the South UP relay (raises the south screen)."""
    if not _trigger_async(SOUTH_UP_PIN, _south_relay_lock):
        return jsonify({"status": "busy", "action": "up2"}), 409
    return jsonify({"status": "ok", "action": "up2"})


@app.route("/down2", methods=["GET", "POST"])
def relay_down2():
    """Trigger the South DOWN relay (lowers the south screen)."""
    if not _trigger_async(SOUTH_DOWN_PIN, _south_relay_lock):
        return jsonify({"status": "busy", "action": "down2"}), 409
    return jsonify({"status": "ok", "action": "down2"})


if __name__ == "__main__":
    try:
        # Bind to all interfaces so the page is reachable on the local network
        app.run(host="0.0.0.0", port=5000, debug=False)
    finally:
        GPIO.cleanup()
