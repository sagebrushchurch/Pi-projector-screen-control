"""
Projector Screen Control
------------------------
Flask web application that controls a motorised projector screen via two
relays connected to a Raspberry Pi.

Relay wiring (BCM numbering):
  UP   relay trigger → GPIO 17  (physical pin 11)
  DOWN relay trigger → GPIO 27  (physical pin 13)
  VCC  (both relays) → 5 V rail (physical pin 2 or 4)
  GND  (both relays) → Ground   (physical pin 6, 9, 14 or 20)

Each relay is energised for RELAY_PULSE_SECONDS (default 1 s) then released.

HTTP endpoints (usable by Stream Deck / Bitfocus Companion):
  GET /up    – trigger the UP relay
  GET /down  – trigger the DOWN relay
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
UP_PIN = 17          # BCM 17 – physical pin 11
DOWN_PIN = 27        # BCM 27 – physical pin 13
RELAY_PULSE_SECONDS = 1  # how long each relay stays energised

# ---------------------------------------------------------------------------
# GPIO initialisation
# ---------------------------------------------------------------------------
GPIO.setmode(GPIO.BCM)
GPIO.setup(UP_PIN, GPIO.OUT)
GPIO.setup(DOWN_PIN, GPIO.OUT)
GPIO.output(UP_PIN, GPIO.LOW)
GPIO.output(DOWN_PIN, GPIO.LOW)

# Lock prevents overlapping relay pulses
_relay_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = Flask(__name__)


def _trigger_async(pin: int) -> bool:
    """
    Start a relay pulse in a background thread.

    Returns True if the pulse was started, False if a pulse is already running.
    The thread is *not* a daemon so the pulse always completes even if the main
    process begins to shut down.
    """
    if not _relay_lock.acquire(blocking=False):
        return False
    # Lock was acquired; release it inside the thread after the pulse.
    def _run() -> None:
        try:
            GPIO.output(pin, GPIO.HIGH)
            time.sleep(RELAY_PULSE_SECONDS)
            GPIO.output(pin, GPIO.LOW)
        finally:
            _relay_lock.release()

    t = threading.Thread(target=_run, daemon=False)
    t.start()
    return True


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/up", methods=["GET", "POST"])
def relay_up():
    """Trigger the UP relay (raises the screen)."""
    if not _trigger_async(UP_PIN):
        return jsonify({"status": "busy", "action": "up"}), 409
    return jsonify({"status": "ok", "action": "up"})


@app.route("/down", methods=["GET", "POST"])
def relay_down():
    """Trigger the DOWN relay (lowers the screen)."""
    if not _trigger_async(DOWN_PIN):
        return jsonify({"status": "busy", "action": "down"}), 409
    return jsonify({"status": "ok", "action": "down"})


if __name__ == "__main__":
    try:
        # Bind to all interfaces so the page is reachable on the local network
        app.run(host="0.0.0.0", port=5000, debug=False)
    finally:
        GPIO.cleanup()
