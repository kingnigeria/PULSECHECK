from __future__ import annotations

import json
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import urlparse


HTML_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PulseCheck</title>
  <style>
    :root {
      --bg: #071018;
      --panel: #0d1c25;
      --panel-alt: #132732;
      --line: #284451;
      --ink: #eff8f7;
      --muted: #9bb5be;
      --teal: #58d9bf;
      --red: #ff6a68;
      --gold: #f5c767;
      --mint: #bafce6;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Bahnschrift, "Trebuchet MS", "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(88, 217, 191, 0.18), transparent 24%),
        linear-gradient(180deg, #051018 0%, #0b1820 100%);
    }
    .shell {
      max-width: 1260px;
      margin: 0 auto;
      padding: 24px 18px 40px;
    }
    .hero {
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      background: linear-gradient(135deg, rgba(15, 33, 43, 0.98), rgba(7, 16, 24, 0.98));
    }
    .hero-top {
      display: grid;
      grid-template-columns: 1.5fr 1fr;
      gap: 18px;
      padding: 20px 22px 12px;
      align-items: center;
    }
    h1 {
      margin: 0;
      font-size: clamp(2rem, 4vw, 3.1rem);
      line-height: 1;
    }
    .subtitle {
      margin: 10px 0 0;
      max-width: 62ch;
      color: var(--muted);
      line-height: 1.55;
    }
    .hero-card {
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(0, 0, 0, 0.18);
    }
    .hero-card strong {
      display: block;
      margin-top: 8px;
      font-size: 1.3rem;
    }
    .monitor {
      padding: 0 22px 18px;
    }
    .monitor-strip {
      position: relative;
      height: 88px;
      border-radius: 8px;
      border: 1px solid var(--line);
      background:
        linear-gradient(180deg, rgba(0, 0, 0, 0.24), rgba(0, 0, 0, 0.12)),
        repeating-linear-gradient(
          90deg,
          rgba(255, 255, 255, 0.04) 0,
          rgba(255, 255, 255, 0.04) 1px,
          transparent 1px,
          transparent 40px
        ),
        repeating-linear-gradient(
          0deg,
          rgba(255, 255, 255, 0.03) 0,
          rgba(255, 255, 255, 0.03) 1px,
          transparent 1px,
          transparent 22px
        );
      overflow: hidden;
    }
    .monitor-strip svg {
      position: absolute;
      inset: 0;
      width: 100%; /* Keep this at 100% so it fits the box */
      height: 100%;
    }

    .pulse-path {
      fill: none;
      stroke: var(--red);
      stroke-width: 3.5;
      stroke-linejoin: round;
      stroke-linecap: round;
      filter: drop-shadow(0 0 6px rgba(255, 106, 104, 0.45));
      
      /* Use a very long dash that matches the path length */
      stroke-dasharray: 1000; 
      stroke-dashoffset: 1000;
      animation: draw-pulse 3s linear infinite;
    }

    @keyframes draw-pulse {
      0% {
        stroke-dashoffset: 1000;
      }
      80% {
        stroke-dashoffset: 0;
        opacity: 1;
      }
      /* This creates the "loop" feel by fading out slightly before restarting */
      95% {
        opacity: 0;
      }
      100% {
        stroke-dashoffset: 0;
        opacity: 0;
      }
    }
    .summary {
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }
    .metric {
      min-height: 94px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(0, 0, 0, 0.14);
    }
    .metric-label {
      color: var(--muted);
      font-size: 0.82rem;
      text-transform: uppercase;
    }
    .metric-value {
      margin-top: 10px;
      font-size: 1.8rem;
      font-weight: 700;
    }
    .layout {
      margin-top: 18px;
      display: grid;
      grid-template-columns: 1.3fr 1fr;
      gap: 18px;
    }
    .panel {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: linear-gradient(180deg, rgba(14, 30, 39, 0.98), rgba(8, 17, 24, 0.98));
      overflow: hidden;
    }
    .panel-head {
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
    }
    .panel-head h2 {
      margin: 0;
      font-size: 1.06rem;
    }
    .panel-copy {
      color: var(--muted);
      font-size: 0.92rem;
    }
    .panel-body {
      padding: 14px 16px 16px;
    }
    .stack {
      display: grid;
      gap: 10px;
    }
    .item {
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.02);
    }
    .item-top {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
    }
    .item-name {
      font-size: 1.02rem;
      font-weight: 700;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      padding: 4px 10px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(0, 0, 0, 0.2);
      font-size: 0.8rem;
    }
    .badge.online { color: var(--teal); }
    .badge.visitor { color: var(--gold); }
    .muted {
      color: var(--muted);
    }
    .mini-grid {
      margin-top: 10px;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
    }
    .mini {
      padding: 10px;
      border-radius: 6px;
      background: var(--panel-alt);
      min-height: 72px;
    }
    .mini span {
      display: block;
      color: var(--muted);
      font-size: 0.78rem;
    }
    .mini strong {
      display: block;
      margin-top: 6px;
      font-size: 1rem;
    }
    .instructions {
      display: grid;
      gap: 12px;
    }
    .callout {
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(88, 217, 191, 0.05);
      line-height: 1.55;
    }
    .steps {
      display: grid;
      gap: 10px;
    }
    .step {
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.02);
    }
    code {
      font-family: Consolas, "Courier New", monospace;
      font-size: 0.92em;
      color: var(--mint);
    }
    .note {
      margin-top: 14px;
      color: var(--muted);
      font-size: 0.92rem;
    }
    @media (max-width: 980px) {
      .hero-top, .layout { grid-template-columns: 1fr; }
      .summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .mini-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 640px) {
      .summary, .mini-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="hero-top">
        <div>
          <h1>PulseCheck</h1>
          <p class="subtitle">Welcome to PulseCheck. We built this to show how data moves across a small network. If you open this page, you show up below as a visitor. If a laptop runs our worker program, it sends real CPU, memory, and heartbeat data back to the manager. We use TCP for the reliable worker connection and UDP for quick alerts.</p>
        </div>
        <div class="hero-card">
          <div class="muted">Manager laptop</div>
          <strong id="manager-host">Starting...</strong>
          <div class="note" id="manager-ports">Ports loading...</div>
        </div>
      </div>
      <div class="monitor">
        <div class="monitor-strip" aria-hidden="true">
          <svg viewBox="0 0 560 88" preserveAspectRatio="none">
            <path class="pulse-path" d="M0 50 L58 50 L82 50 L100 22 L118 70 L136 50 L172 50 L196 50 L214 34 L230 60 L248 50 L302 50 L326 50 L344 18 L364 72 L386 50 L432 50 L454 50 L472 36 L488 57 L506 50 L560 50"></path>
          </svg>
        </div>
      </div>
    </section>

    <section class="summary">
      <div class="metric">
        <div class="metric-label">Visitors On This Page</div>
        <div class="metric-value" id="visitor-count">0</div>
      </div>
      <div class="metric">
        <div class="metric-label">Worker Machines</div>
        <div class="metric-value" id="worker-count">0</div>
      </div>
      <div class="metric">
        <div class="metric-label">Alerts</div>
        <div class="metric-value" id="alert-count">0</div>
      </div>
      <div class="metric">
        <div class="metric-label">Last Refresh</div>
        <div class="metric-value" id="last-refresh">--</div>
      </div>
    </section>

    <div class="layout">
      <section class="panel">
        <div class="panel-head">
          <h2>Your Visitor Card</h2>
          <span class="panel-copy">This is the device that opened the page.</span>
        </div>
        <div class="panel-body">
          <div id="current-visitor" class="stack"></div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <h2>How To Try It</h2>
          <span class="panel-copy">What students should do</span>
        </div>
        <div class="panel-body instructions">
          <div class="callout">
            <strong>Join from the same Wi-Fi:</strong><br>
            <code id="share-url"></code>
          </div>
          <div class="steps">
            <div class="step">1. Open this page on your phone or laptop. That makes you show up as a visitor.</div>
            <div class="step">2. Watch the worker machines below send their stats back to the manager.</div>
            <div class="step">3. If you are on one of our demo laptops, run the worker and you will appear in the worker section with live system data.</div>
          </div>
          <div class="callout">
            <strong>Worker command on a demo laptop:</strong><br>
            <code id="worker-command"></code>
          </div>
          <div class="note">Visitors are just viewing the page. Worker machines are the ones running the PulseCheck client and sending real stats over sockets.</div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <h2>Live Visitors</h2>
          <span class="panel-copy">Everyone who opened the page</span>
        </div>
        <div class="panel-body">
          <div id="visitor-list" class="stack"></div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <h2>Worker Machines</h2>
          <span class="panel-copy">These are the machines actually sending stats to the manager.</span>
        </div>
        <div class="panel-body">
          <div id="worker-list" class="stack"></div>
        </div>
      </section>

      <section class="panel" style="grid-column: 1 / -1;">
        <div class="panel-head">
          <h2>Live Activity</h2>
          <span class="panel-copy">Handshakes, heartbeats, tasks, and alerts</span>
        </div>
        <div class="panel-body">
          <div id="event-list" class="stack"></div>
        </div>
      </section>
    </div>
  </div>

  <script>
    const visitorId = localStorage.getItem("pulsecheckVisitorId") || ("visitor-" + Math.random().toString(36).slice(2, 10));
    localStorage.setItem("pulsecheckVisitorId", visitorId);

    async function checkInVisitor() {
      const payload = {
        visitor_id: visitorId,
        label: navigator.platform || "Browser Visitor",
        language: navigator.language || "unknown",
        hardware_threads: navigator.hardwareConcurrency || 0,
        device_memory_gb: navigator.deviceMemory || 0,
        user_agent: navigator.userAgent || "unknown"
      };
      await fetch("/api/checkin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
    }

    function visitorCard(visitor, titleText) {
      return `
        <div class="item">
          <div class="item-top">
            <div>
              <div class="item-name">${titleText || visitor.label}</div>
              <div class="muted">${visitor.ip_address} - ${visitor.language}</div>
            </div>
            <span class="badge visitor">Visitor</span>
          </div>
          <div class="mini-grid">
            <div class="mini"><span>Browser memory</span><strong>${visitor.device_memory_gb || "--"} GB</strong></div>
            <div class="mini"><span>Browser threads</span><strong>${visitor.hardware_threads || "--"}</strong></div>
            <div class="mini"><span>Last seen</span><strong>${visitor.last_seen_age}</strong></div>
            <div class="mini"><span>Visitor id</span><strong>${visitor.visitor_id}</strong></div>
          </div>
        </div>
      `;
    }

    function renderCurrentVisitor(visitors) {
      const current = visitors.find(visitor => visitor.visitor_id === visitorId);
      const mount = document.getElementById("current-visitor");
      if (!current) {
        mount.innerHTML = '<div class="item muted">Open this page from another phone or laptop and the visitor card will appear here in a second or two.</div>';
        return;
      }
      mount.innerHTML = visitorCard(current, "You joined as a visitor");
    }

    function renderVisitors(visitors) {
      const others = visitors.filter(visitor => visitor.visitor_id !== visitorId);
      const list = document.getElementById("visitor-list");
      if (!others.length) {
        list.innerHTML = '<div class="item muted">No other visitors yet. Ask someone nearby to open this page on the same Wi-Fi.</div>';
        return;
      }
      list.innerHTML = others.map(visitor => visitorCard(visitor, visitor.label)).join("");
    }

    function renderWorkers(workers) {
      const list = document.getElementById("worker-list");
      if (!workers.length) {
        list.innerHTML = '<div class="item muted">No worker machines connected yet. Run the PulseCheck worker on this laptop or another demo laptop to send live stats here.</div>';
        return;
      }
      list.innerHTML = workers.map(worker => `
        <div class="item">
          <div class="item-top">
            <div>
              <div class="item-name">${worker.worker_id}</div>
              <div class="muted">${worker.address} - ${worker.platform || "Platform unknown"}</div>
            </div>
            <span class="badge ${worker.online ? "online" : ""}">${worker.online ? "Connected" : "Offline"}</span>
          </div>
          <div class="mini-grid">
            <div class="mini"><span>CPU</span><strong>${worker.metrics.cpu_percent ?? "--"}%</strong></div>
            <div class="mini"><span>Memory</span><strong>${worker.metrics.memory_percent ?? "--"}%</strong></div>
            <div class="mini"><span>Disk</span><strong>${worker.metrics.disk_percent ?? "--"}%</strong></div>
            <div class="mini"><span>Heartbeat</span><strong>${worker.last_heartbeat_age}</strong></div>
          </div>
          <div class="note">Last task result: ${worker.last_task || "No task result yet"}</div>
        </div>
      `).join("");
    }

    function renderEvents(events) {
      const list = document.getElementById("event-list");
      if (!events.length) {
        list.innerHTML = '<div class="item muted">No activity yet.</div>';
        return;
      }
      list.innerHTML = events.map(event => `
        <div class="item">
          <div class="item-top">
            <strong>${event.title}</strong>
            <span class="muted">${event.time}</span>
          </div>
          <div class="note">${event.message}</div>
        </div>
      `).join("");
    }

    async function refreshStatus() {
      const response = await fetch("/api/status");
      const data = await response.json();
      document.getElementById("manager-host").textContent = data.manager_display_host;
      document.getElementById("manager-ports").textContent = `TCP ${data.handshake_port}/${data.data_port} | UDP ${data.alert_port} | WEB ${data.web_port}`;
      document.getElementById("visitor-count").textContent = data.web_visitors.length;
      document.getElementById("worker-count").textContent = data.socket_workers.length;
      document.getElementById("alert-count").textContent = data.alerts.length;
      document.getElementById("last-refresh").textContent = new Date().toLocaleTimeString();
      document.getElementById("share-url").textContent = window.location.href;
      document.getElementById("worker-command").textContent = "python client.py --config config\\\\worker.json";
      renderCurrentVisitor(data.web_visitors);
      renderVisitors(data.web_visitors);
      renderWorkers(data.socket_workers);
      renderEvents(data.events);
    }

    async function boot() {
      try {
        await checkInVisitor();
      } catch (error) {
        console.error("Visitor check-in failed", error);
      }
      await refreshStatus();
      setInterval(checkInVisitor, 12000);
      setInterval(refreshStatus, 2000);
    }

    boot();
  </script>
</body>
</html>
"""


class DashboardServer:
    def __init__(
        self,
        host: str,
        port: int,
        snapshot_provider: Callable[[], dict[str, Any]],
        visitor_recorder: Callable[[dict[str, Any], str], None],
        logger: Any,
    ) -> None:
        self.host = host
        self.port = port
        self.snapshot_provider = snapshot_provider
        self.visitor_recorder = visitor_recorder
        self.log = logger

    def start(self) -> None:
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path == "/":
                    self._send_html(HTML_PAGE)
                    return
                if parsed.path == "/api/status":
                    self._send_json(server.snapshot_provider())
                    return
                if parsed.path == "/healthz":
                    self._send_json({"status": "ok", "time": time.time()})
                    return
                self.send_error(HTTPStatus.NOT_FOUND, "Not found")

            def do_POST(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path != "/api/checkin":
                    self.send_error(HTTPStatus.NOT_FOUND, "Not found")
                    return
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length)
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON")
                    return
                server.visitor_recorder(payload, self.client_address[0])
                self._send_json({"status": "ok"})

            def log_message(self, fmt: str, *args: object) -> None:
                server.log.debug("WEB %s - " + fmt, self.address_string(), *args)

            def _send_html(self, content: str) -> None:
                body = content.encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _send_json(self, payload: dict[str, Any]) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        httpd = ThreadingHTTPServer((self.host, self.port), Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        self.log.info("Web dashboard listening on %s:%s", self.host, self.port)
