/* Ruang Kendali — dashboard.js
 * - Live clock
 * - Per-camera MJPEG feed watchdog (auto reconnect on stall/error)
 * - Live detection log: polls the existing /detection_log page and
 *   re-renders the rows into the dashboard's own panel, no backend change.
 * - KPI cards: derived client-side from camera feed state + log rows,
 *   since the backend does not expose separate stats endpoints.
 */

document.addEventListener("DOMContentLoaded", function () {
  initLiveClock();
  initCameraFeeds();
  initLiveLog();
});

/* ---------------------------------------------------------------------- */
/* Live clock                                                             */
/* ---------------------------------------------------------------------- */

function initLiveClock() {
  const el = document.getElementById("live-clock");
  if (!el) return;
  function tick() {
    const now = new Date();
    el.textContent = now.toLocaleTimeString("id-ID", { hour12: false });
  }
  tick();
  setInterval(tick, 1000);
}

/* ---------------------------------------------------------------------- */
/* Camera feeds                                                           */
/* ---------------------------------------------------------------------- */

function initCameraFeeds() {
  const tiles = document.querySelectorAll(".camera-tile");
  const total = tiles.length;
  const onlineState = {};

  function updateCameraStat() {
    const foot = document.getElementById("stat-cameras-foot");
    const onlineEl = document.getElementById("stat-cameras-online");
    const onlineCount = Object.values(onlineState).filter(Boolean).length;
    if (onlineEl) onlineEl.textContent = onlineCount;
    if (foot) foot.textContent = onlineCount === total ? "semua terhubung" : (total - onlineCount) + " kamera bermasalah";
  }

  tiles.forEach((tile) => {
    const cameraId = tile.dataset.cameraId;
    const feed = tile.querySelector(".camera-feed");
    const overlay = tile.querySelector(".camera-overlay-msg");
    const rec = tile.querySelector(".rec-indicator");
    if (!feed) return;

    onlineState[cameraId] = false;
    let watchdog = null;

    function setState(state) {
      // state: 'connecting' | 'live' | 'offline'
      if (state === "connecting") {
        overlay.style.display = "flex";
        overlay.querySelector(".overlay-text").textContent = "Menghubungkan…";
        feed.style.visibility = "hidden";
        rec.classList.add("offline");
        onlineState[cameraId] = false;
      } else if (state === "live") {
        overlay.style.display = "none";
        feed.style.visibility = "visible";
        rec.classList.remove("offline");
        onlineState[cameraId] = true;
      } else {
        overlay.style.display = "flex";
        overlay.querySelector(".overlay-text").textContent = "Koneksi terputus — mencoba lagi…";
        feed.style.visibility = "hidden";
        rec.classList.add("offline");
        onlineState[cameraId] = false;
      }
      updateCameraStat();
    }

    function reload() {
      const src = feed.getAttribute("data-src");
      setState("connecting");
      feed.src = src + "?t=" + Date.now();
    }

    feed.addEventListener("load", () => setState("live"));
    feed.addEventListener("error", () => {
      setState("offline");
      clearTimeout(watchdog);
      watchdog = setTimeout(reload, 3000);
    });

    // Periodically confirm the stream is still delivering frames.
    setInterval(() => {
      if (feed.complete && feed.naturalWidth === 0) {
        setState("offline");
        reload();
      }
    }, 6000);

    reload();
  });
}

/* ---------------------------------------------------------------------- */
/* Live detection log + KPI derived from it                               */
/* ---------------------------------------------------------------------- */

function initLiveLog() {
  const body = document.getElementById("live-log-body");
  if (!body) return;

  let knownKeys = new Set();
  let firstLoad = true;

  function updateLogStats(rows) {
    const totalEl = document.getElementById("stat-detections-total");
    const todayEl = document.getElementById("stat-detections-today");
    if (totalEl) totalEl.textContent = rows.length;
    if (todayEl) {
      const todayStr = new Date().toLocaleDateString("id-ID"); // used only for grouping, not display
      const today = new Date();
      const isToday = (cellText) => {
        // cellText format: YYYY-MM-DD HH:MM:SS
        const d = new Date(cellText.replace(" ", "T"));
        return d.getFullYear() === today.getFullYear() &&
               d.getMonth() === today.getMonth() &&
               d.getDate() === today.getDate();
      };
      const count = rows.filter((row) => {
        const cell = row.querySelector("td");
        return cell && isToday(cell.textContent.trim());
      }).length;
      todayEl.textContent = count;
    }
  }

  async function refresh() {
    try {
      const res = await fetch("/detection_log", { credentials: "same-origin" });
      if (!res.ok) return;
      const html = await res.text();
      const doc = new DOMParser().parseFromString(html, "text/html");
      const rows = Array.from(doc.querySelectorAll("table.log-table tbody tr[data-key]"));

      if (rows.length === 0) return;

      body.innerHTML = "";
      const nextKnown = new Set();

      rows.forEach((row) => {
        const key = row.getAttribute("data-key");
        nextKnown.add(key);
        const clone = row.cloneNode(true);
        if (!firstLoad && !knownKeys.has(key)) {
          clone.classList.add("is-new");
        }
        body.appendChild(clone);
      });

      knownKeys = nextKnown;
      firstLoad = false;
      updateLogStats(rows);
    } catch (err) {
      // Silently retry on next interval; keep last known rows visible.
      console.error("Gagal memuat log deteksi:", err);
    }
  }

  refresh();
  setInterval(refresh, 4000);
}
