document.addEventListener("DOMContentLoaded", function () {
  initLiveClock();
  initCameraFeeds();
  initLiveLog();
  initAlarm();
  initCharts();
});


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

    setInterval(() => {
      if (feed.complete && feed.naturalWidth === 0) {
        setState("offline");
        reload();
      }
    }, 6000);

    reload();
  });
}


const ALARM_COOLDOWN_MS = 10000; // minimum time between alarm sounds

function initAlarm() {
  const alarm = document.getElementById("alarm-sound");
  const muteBtn = document.getElementById("alarm-mute-btn");
  const muteIcon = document.getElementById("alarm-mute-icon");
  const muteLabel = document.getElementById("alarm-mute-label");
  if (!alarm || !muteBtn) {
    console.warn("Alarm elements not found");
    return;
  }

  let muted = localStorage.getItem("alarm-muted") === "true";
  let audioUnlocked = false;
  let lastAlarmTime = 0;
  let alarmReady = false;

  function updateMuteUI() {
    muteBtn.classList.toggle("is-muted", muted);
    muteIcon.classList.toggle("muted", muted);
    muteLabel.textContent = muted ? "Alarm Mati" : "Alarm Aktif";
  }

  function unlockAudio() {
    if (audioUnlocked) return;
    // Browsers block audio until user interacts. Try to unlock silently.
    alarm.volume = 0.01;
    const playPromise = alarm.play();
    if (playPromise !== undefined) {
      playPromise
        .then(() => {
          alarm.pause();
          alarm.currentTime = 0;
          alarm.volume = 1.0;
          audioUnlocked = true;
          console.log("Audio unlocked");
        })
        .catch((err) => {
          console.warn("Audio unlock failed (needs user interaction):", err);
        });
    }
  }

  // Unlock audio on the first user gesture anywhere on the page.
  ["click", "touchstart", "keydown"].forEach((evt) => {
    document.body.addEventListener(evt, unlockAudio, { once: true, passive: true });
  });

  // Also unlock when the mute button is clicked.
  muteBtn.addEventListener("click", () => {
    muted = !muted;
    localStorage.setItem("alarm-muted", muted);
    updateMuteUI();
    if (!muted) {
      unlockAudio();
      // Play a short test beep so the user knows it works.
      alarm.currentTime = 0;
      alarm.volume = 1.0;
      alarm.play().catch((err) => console.warn("Test beep blocked:", err));
    }
  });

  alarm.addEventListener("canplaythrough", () => {
    alarmReady = true;
    console.log("Alarm audio ready");
  });

  alarm.addEventListener("error", (e) => {
    console.error("Alarm audio failed to load:", e);
  });

  updateMuteUI();

  window.triggerAlarm = function () {
    if (muted) {
      console.log("Alarm muted; skipping");
      return;
    }
    const now = Date.now();
    if (now - lastAlarmTime < ALARM_COOLDOWN_MS) {
      console.log("Alarm cooldown active");
      return;
    }
    lastAlarmTime = now;

    if (!alarmReady) {
      console.warn("Alarm audio not ready yet");
    }

    alarm.currentTime = 0;
    alarm.volume = 1.0;
    const playPromise = alarm.play();
    if (playPromise !== undefined) {
      playPromise.catch((err) => {
        console.warn("Alarm play blocked by browser:", err);
        // Show a visual nudge if audio cannot play.
        showAlarmBlockedNotice();
      });
    }
    console.log("Alarm triggered");
  };
}

function showAlarmBlockedNotice() {
  const existing = document.getElementById("alarm-blocked-notice");
  if (existing) return;
  const notice = document.createElement("div");
  notice.id = "alarm-blocked-notice";
  notice.className = "flash";
  notice.innerHTML = "🔇 Audio alarm diblokir browser. Klik tombol <strong>Alarm Aktif</strong> untuk mengaktifkannya.";
  const main = document.querySelector(".main");
  if (main) {
    main.insertBefore(notice, main.firstChild);
    setTimeout(() => notice.remove(), 6000);
  }
}

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
      const today = new Date();
      const isToday = (cellText) => {
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

      if (rows.length === 0) {
        body.innerHTML = '<tr><td colspan="5" style="color: var(--ink-400); font-family: var(--font-body);">Belum ada deteksi yang tercatat.</td></tr>';
        updateLogStats([]);
        return;
      }

      body.innerHTML = "";
      const nextKnown = new Set();
      let hasNew = false;

      rows.forEach((row) => {
        const key = row.getAttribute("data-key");
        nextKnown.add(key);
        const clone = row.cloneNode(true);
        if (!firstLoad && !knownKeys.has(key)) {
          clone.classList.add("is-new");
          hasNew = true;
        }
        body.appendChild(clone);
      });

      if (hasNew && typeof window.triggerAlarm === "function") {
        window.triggerAlarm();
      }

      knownKeys = nextKnown;
      firstLoad = false;
      updateLogStats(rows);
    } catch (err) {
      console.error("Gagal memuat log deteksi:", err);
    }
  }

  refresh();
  setInterval(refresh, 4000);
}

let chartStatus = null;
let chartCamera = null;

function initCharts() {
  if (typeof Chart === "undefined") {
    console.warn("Chart.js not loaded; skipping charts.");
    return;
  }

  const statusCanvas = document.getElementById("chart-status");
  const cameraCanvas = document.getElementById("chart-camera");
  if (!statusCanvas || !cameraCanvas) return;

  const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: "rgba(23, 26, 33, 0.92)",
        titleFont: { family: "'Space Grotesk', sans-serif", size: 13 },
        bodyFont: { family: "'Inter', sans-serif", size: 12.5 },
        padding: 10,
        cornerRadius: 8,
        callbacks: {
          label: (ctx) => {
            const label = ctx.label || "";
            const value = ctx.raw || 0;
            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
            const pct = total ? Math.round((value / total) * 100) : 0;
            return `${label}: ${value} (${pct}%)`;
          }
        }
      }
    }
  };

  chartStatus = new Chart(statusCanvas, {
    type: "doughnut",
    data: {
      labels: ["Perokok Terdeteksi", "Tidak Terdeteksi"],
      datasets: [{
        data: [0, 0],
        backgroundColor: ["#d92d20", "#12805c"],
        borderWidth: 0,
        hoverOffset: 6
      }]
    },
    options: {
      ...commonOptions,
      cutout: "62%"
    }
  });

  chartCamera = new Chart(cameraCanvas, {
    type: "bar",
    data: {
      labels: [],
      datasets: [{
        label: "Jumlah Orang Terdeteksi",
        data: [],
        backgroundColor: "#e8590c",
        borderRadius: 6,
        barThickness: 28
      }]
    },
    options: {
      ...commonOptions,
      scales: {
        y: {
          beginAtZero: true,
          ticks: { stepSize: 1, font: { family: "'JetBrains Mono', monospace", size: 11 } },
          grid: { color: "#eef0f3" }
        },
        x: {
          ticks: { font: { family: "'Inter', sans-serif", size: 11 }, maxRotation: 0, autoSkip: true },
          grid: { display: false }
        }
      }
    }
  });

  refreshCharts();
  setInterval(refreshCharts, 5000);
}

async function refreshCharts() {
  try {
    const res = await fetch("/api/stats", { credentials: "same-origin" });
    if (!res.ok) return;
    const stats = await res.json();

    const avgEl = document.getElementById("stat-avg-confidence");
    if (avgEl && stats.avg_confidence !== undefined) {
      avgEl.textContent = (stats.avg_confidence * 100).toFixed(0) + "%";
    }

    if (chartStatus) {
      chartStatus.data.datasets[0].data = [
        stats.detection_status?.detected || 0,
        stats.detection_status?.not_detected || 0
      ];
      chartStatus.update();
      renderStatusLegend(stats.detection_status);
    }

    if (chartCamera && stats.camera_breakdown) {
      chartCamera.data.labels = stats.camera_breakdown.map((c) => c.name);
      chartCamera.data.datasets[0].data = stats.camera_breakdown.map((c) => c.count);
      chartCamera.update();
    }
  } catch (err) {
    console.error("Gagal memuat statistik:", err);
  }
}

function renderStatusLegend(status) {
  const legend = document.getElementById("chart-status-legend");
  if (!legend || !status) return;
  const total = status.detected + status.not_detected;
  const pct = total ? Math.round((status.detected / total) * 100) : 0;
  legend.innerHTML = `
    <div class="legend-item">
      <span class="legend-dot" style="background:#d92d20"></span>
      <span class="legend-text">Perokok terdeteksi: <strong>${status.detected}</strong> (${pct}%)</span>
    </div>
    <div class="legend-item">
      <span class="legend-dot" style="background:#12805c"></span>
      <span class="legend-text">Tidak terdeteksi: <strong>${status.not_detected}</strong> (${100 - pct}%)</span>
    </div>
  `;
}
