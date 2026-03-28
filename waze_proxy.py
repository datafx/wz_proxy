import time
import threading
from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

app = Flask(__name__)
driver_lock = threading.Lock()
driver = None

def create_driver():
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.binary_location = "/usr/bin/chromium"
    service = Service("/usr/bin/chromedriver")
    d = webdriver.Chrome(service=service, options=options)
    d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    })
    return d

def init_driver():
    global driver
    print("Opening Chromium and visiting Waze...")
    driver = create_driver()
    driver.get("https://www.waze.com/live-map")
    time.sleep(8)
    print("Ready!")

def refresh_session():
    global driver
    while True:
        time.sleep(1500)  # Refresh every 25 minutes
        print("Refreshing Waze session...")
        with driver_lock:
            driver.get("https://www.waze.com/live-map")
            time.sleep(8)
        print("Session refreshed!")

@app.route("/georss")
def georss():
    params = request.query_string.decode()
    georss_url = f"https://www.waze.com/live-map/api/georss?{params}"

    try:
        with driver_lock:
            result = driver.execute_async_script("""
                const callback = arguments[arguments.length - 1];
                fetch(arguments[0], {
                    headers: {
                        'Referer': 'https://www.waze.com/live-map',
                        'Accept': 'application/json, text/plain, */*',
                        'Origin': 'https://www.waze.com'
                    }
                })
                .then(r => r.text())
                .then(data => callback(data))
                .catch(err => callback('ERROR: ' + err));
            """, georss_url)

        return app.response_class(
            response=result,
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    init_driver()
    refresh_thread = threading.Thread(target=refresh_session, daemon=True)
    refresh_thread.start()
    app.run(host="0.0.0.0", port=8099)
