# Pi Projector Screen Control

A lightweight Python/Flask application that controls two motorised projector screens (North and South) via four relays on a Raspberry Pi. A built-in web page provides manual Up/Down buttons for each screen, and simple HTTP endpoints let Bitfocus Companion (Stream Deck) trigger the relays remotely.

---

## Hardware

### Raspberry Pi GPIO pins

| Function | BCM number | Physical pin |
|----------|-----------|--------------|
| **North UP relay trigger** | GPIO **17** | Pin **11** |
| **North DOWN relay trigger** | GPIO **27** | Pin **13** |
| **South UP relay trigger** | GPIO **22** | Pin **15** |
| **South DOWN relay trigger** | GPIO **23** | Pin **16** |
| VCC (all relays) | — | Pin **2** or **4** (5 V) |
| GND (all relays) | — | Pin **6**, **9**, **14**, or **20** |

> The relays only need **VCC**, **GND**, and one **trigger** pin each.  
> The trigger pin is pulled HIGH for 1 second to activate the relay, then returned LOW.  
> The North and South relays each have an independent lock, so both screens can be operated simultaneously.

### Wiring diagram (pin numbers are physical / board numbers)

```
Raspberry Pi             Relay module
─────────────────        ────────────
Pin  2  (5 V)   ──────►  VCC  (all relays share the rail)
Pin  6  (GND)   ──────►  GND  (all relays share the rail)
Pin 11  (GPIO17)──────►  IN1  (North UP relay trigger)
Pin 13  (GPIO27)──────►  IN2  (North DOWN relay trigger)
Pin 15  (GPIO22)──────►  IN3  (South UP relay trigger)
Pin 16  (GPIO23)──────►  IN4  (South DOWN relay trigger)
```

---

## Software

### Requirements

- Python 3.8+
- `RPi.GPIO` (pre-installed on Raspberry Pi OS) or any compatible GPIO library
- Flask 3.x

### Installation

```bash
# Clone the repo (if you haven't already)
git clone https://github.com/sagebrushchurch/Pi-projector-screen-control.git
cd Pi-projector-screen-control

# Create a virtual environment
# --system-site-packages is required so the venv can access RPi.GPIO,
# which is pre-installed as a system package on Raspberry Pi OS
python3 -m venv --system-site-packages venv

# Activate the virtual environment
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### Running the server

```bash
# Activate the virtual environment (if not already active)
source venv/bin/activate

python app.py
```

The server starts on port **5000** and binds to all interfaces, so it is reachable at `http://<pi-ip-address>:5000` from any device on the local network.

### Auto-start on boot (optional)

Create a systemd service so the app starts automatically:

```ini
# /etc/systemd/system/screen-control.service
[Unit]
Description=Projector Screen Control
After=network.target

[Service]
ExecStart=/home/pi/Pi-projector-screen-control/venv/bin/python /home/pi/Pi-projector-screen-control/app.py
WorkingDirectory=/home/pi/Pi-projector-screen-control
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable screen-control
sudo systemctl start screen-control
```

---

## HTTP API

All endpoints accept `GET` **or** `POST` requests and return JSON.

| Endpoint | Action |
|----------|--------|
| `GET /` | Serve the manual-control web page |
| `GET /up` or `POST /up` | Energise the **North UP** relay for 1 second |
| `GET /down` or `POST /down` | Energise the **North DOWN** relay for 1 second |
| `GET /up2` or `POST /up2` | Energise the **South UP** relay for 1 second |
| `GET /down2` or `POST /down2` | Energise the **South DOWN** relay for 1 second |

### Example responses

```json
{ "status": "ok", "action": "up" }
{ "status": "ok", "action": "down" }
{ "status": "ok", "action": "up2" }
{ "status": "ok", "action": "down2" }
```

If a relay pulse is already in progress for that screen, the endpoint returns HTTP **409** with:

```json
{ "status": "busy", "action": "up" }
```

### Stream Deck / Bitfocus Companion

Use the **HTTP Request** action (or the generic **GET/POST URL** action) and point it at the desired endpoint:

- North screen: `http://<pi-ip>:5000/up` or `http://<pi-ip>:5000/down`
- South screen: `http://<pi-ip>:5000/up2` or `http://<pi-ip>:5000/down2`

---

## Web UI

Open `http://<pi-ip-address>:5000` in a browser. The page shows two sections — one for each projector — each containing two large circular buttons:

- **▲ Up** – raises the screen (triggers the UP relay for that projector)  
- **▼ Down** – lowers the screen (triggers the DOWN relay for that projector)

### North Projector

Controls the North screen via the `/up` and `/down` endpoints.

### South Projector

Controls the South screen via the `/up2` and `/down2` endpoints.

Buttons are disabled for ~1.2 seconds after each press to prevent accidental double-triggers. The North and South projector controls operate independently of each other.