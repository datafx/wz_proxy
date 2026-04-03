# Waze Proxy for SpectreNav

> **⚠️ Disclaimer:** This is a personal workaround for private use. It interacts with Waze's web API in a way that may violate [Waze's Terms of Service](https://www.waze.com/legal/tos). Use at your own risk. This project is not affiliated with or endorsed by Waze or Google.

A workaround for the Waze integration in SpectreNav, caused by Waze adding reCAPTCHA cookie requirements to their `live-map` API in 2026. This solution uses a real Chromium browser session to bypass bot detection and serve Waze alert data locally over your home network.

---

## How It Works

1. A Python script opens a **real visible Chromium window** on your desktop machine and navigates to `https://www.waze.com/live-map`
2. A **Flask web server** runs alongside it, accepting georss requests
3. When a request comes in, the script makes the Waze API call **from within the real browser session** — bypassing bot detection entirely
4. SpectreNav calls the Flask server directly over your **local network or VPN**
5. The browser session **auto-refreshes every 25 minutes** to keep cookies fresh

---

## Requirements

- A desktop/laptop machine that is **always on** when you need SpectreNav
- **Chromium** installed on that machine
- **Python 3** installed
- **chromedriver** matching your Chromium version
- iPhone and desktop on the same network, or connected via **VPN**

---

## Installation

### 1. Install Python dependencies

```bash
python3 -m venv ~/waze_venv
~/waze_venv/bin/pip install selenium flask
```

### 2. Verify chromedriver is installed

```bash
chromedriver --version
```

It should match your Chromium version. On Arch/CachyOS it is included with the `chromium` package.

### 3. Open firewall port 8099

**UFW:**
```bash
sudo ufw allow 8099/tcp
```

**nftables:**
```bash
sudo nft add rule inet filter input tcp dport 8099 accept
```

### 4. Save the proxy script

Save `waze_proxy.py` (see below) to your home directory:

```bash
nano ~/waze_proxy.py
```

### 5. Run the proxy

```bash
~/waze_venv/bin/python3 ~/waze_proxy.py
```

A Chromium window will open and navigate to the Waze live map. You will see `Ready!` in the terminal when it is set up.

### 6. Find your local IP address

```bash
ip addr | grep "inet " | grep -v 127.0.0.1
```

Note your local IP address (e.g. `192.168.1.x`).

### 7. Test it

```bash
curl "http://YOUR_LOCAL_IP:8099/georss?top=34.1&bottom=33.9&left=-118.3&right=-118.1&env=na&types=alerts"
```

You should see Waze alert JSON data returned.

---

## SpectreNav Configuration

### Integration Setup

1. Open SpectreNav → Integrations → Add New Integration
2. Name it: `Wz` (or anything you like)

### Pre-Request Steps

| Step | Type | Name | Details |
|------|------|------|---------|
| 1 | Get Current Location | Get loc | — |
| 2 | Calculate Variable | Get top | `var_top` = `{{latitude}} + 0.1` |
| 3 | Calculate Variable | Get bot | `var_bot` = `{{latitude}} - 0.1` |
| 4 | Calculate Variable | Get left | `var_left` = `{{longitude}} - 0.1` |
| 5 | Calculate Variable | Get right | `var_right` = `{{longitude}} + 0.1` |

### Request Configuration

- **Method:** `GET`
- **URL:**
```
http://YOUR_LOCAL_IP:8099/georss?top={{var_top}}&bottom={{var_bot}}&left={{var_left}}&right={{var_right}}&env=na&types=alerts
```

### Data Processing

- **Root array path:** `alerts`

### Data Mapping

| MapPoint Property | JSON Key Path |
|-------------------|---------------|
| `confidence` | `confidence` |
| `id` | `id` |
| `longitude` | `location.x` |
| `latitude` | `location.y` |
| `value` | `nThumbsUp` |
| `createdAt` | `pubMillis` |
| `description` | `street` |
| `subtype` | `subtype` |
| `type` | `type` |

### Schedule

- **Run Every:** 15 seconds (or your preference)

### Enable

Toggle **Enabled ON** and wait for the first run. You should see alert points appear on the map.

---

## Auto-Start on Boot (Optional)

To have the proxy start automatically when your machine boots, create a systemd service:

```bash
sudo nano /etc/systemd/system/waze-proxy.service
```

```ini
[Unit]
Description=Waze Proxy for SpectreNav
After=network.target graphical.target

[Service]
Type=simple
User=YOUR_USERNAME
Environment=DISPLAY=:0
ExecStart=/home/YOUR_USERNAME/waze_venv/bin/python3 /home/YOUR_USERNAME/waze_proxy.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=graphical.target
```

Replace `YOUR_USERNAME` with your actual username, then enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable waze-proxy
sudo systemctl start waze-proxy
```

---

## Troubleshooting

**Port not reachable from phone:**
- Make sure your phone is on the same WiFi network, or connected via VPN
- Double-check the port number in the SpectreNav URL
- Test with Safari on iPhone: `http://YOUR_LOCAL_IP:8099/health` should return `{"status": "ok"}`

**403 errors from Waze:**
- The browser session may have expired — restart `waze_proxy.py`
- The session auto-refreshes every 25 minutes but may need a manual restart if left running for a long time

**Chromium not found:**
- Edit `waze_proxy.py` and update `options.binary_location` to the correct path: `which chromium`

**chromedriver version mismatch:**
- Make sure chromedriver matches your Chromium version: `chromedriver --version` and `chromium --version` should show the same version number

---

## Why This Works

Waze added reCAPTCHA cookie protection to their `live-map` API. These cookies are:
- Set by JavaScript (not HTTP headers), so simple HTTP proxies can't capture them
- Bound to the browser session that created them, so they can't be extracted and reused elsewhere
- Checked against bot detection signals like the `navigator.webdriver` property

By using a **real visible Chromium window** with `navigator.webdriver` masked, the browser looks identical to a normal user browsing Waze, and the API calls made from within that session are accepted by Waze normally.
