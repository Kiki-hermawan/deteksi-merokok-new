document.addEventListener("DOMContentLoaded", function () {
  initLiveClock();
  initCameraFeeds();
  initLiveLog();
  initAlarm();
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
  // state per kamera: 'live' | 'problem' | 'off'
  const cameraState = {};

  function updateCameraStat() {
    const foot = document.getElementById("stat-cameras-foot");
    const onlineEl = document.getElementById("stat-cameras-online");

    const states = Object.values(cameraState);
    const onlineCount = states.filter((s) => s === "live").length;
    const offCount = states.filter((s) => s === "off").length;
    const problemCount = states.filter((s) => s === "problem").length;

    if (onlineEl) onlineEl.textContent = onlineCount;

    if (foot) {
      const parts = [];
      if (problemCount > 0) parts.push(`${problemCount} kamera bermasalah`);
      if (offCount > 0) parts.push(`${offCount} dimatikan manual`);
      foot.textContent = parts.length ? parts.join(" • ") : "semua terhubung";
    }
  }

  tiles.forEach((tile) => {
    const cameraId = tile.dataset.cameraId;
    const feed = tile.querySelector(".camera-feed");
    const overlay = tile.querySelector(".camera-overlay-msg");
    const rec = tile.querySelector(".rec-indicator");
    const powerBtn = tile.querySelector(".power-btn");
    if (!feed) return;

    const initialState = tile.dataset.initialState === "off" ? "off" : "on";
    cameraState[cameraId] = initialState === "off" ? "off" : "connecting";
    let watchdog = null;
    let pollTimer = null;
    let isOff = initialState === "off";

    function setState(state) {
      if (isOff) return;
      if (state === "connecting") {
        overlay.style.display = "flex";
        overlay.querySelector(".overlay-text").textContent = "Menghubungkan…";
        feed.style.visibility = "hidden";
        rec.classList.add("offline");
        cameraState[cameraId] = "problem";
      } else if (state === "live") {
        overlay.style.display = "none";
        feed.style.visibility = "visible";
        rec.classList.remove("offline");
        cameraState[cameraId] = "live";
      } else {
        overlay.style.display = "flex";
        overlay.querySelector(".overlay-text").textContent =
          "Koneksi terputus — mencoba lagi…";
        feed.style.visibility = "hidden";
        rec.classList.add("offline");
        cameraState[cameraId] = "problem";
      }
      updateCameraStat();
    }

    function reload() {
      if (isOff) return;
      const src = feed.getAttribute("data-src");
      setState("connecting");
      feed.src = src + "?t=" + Date.now();
    }

    function startWatchdog() {
      clearInterval(pollTimer);
      pollTimer = setInterval(() => {
        if (isOff) return;
        if (feed.complete && feed.naturalWidth === 0) {
          setState("offline");
          reload();
        }
      }, 6000);
    }

    function applyOffUI() {
      isOff = true;
      clearTimeout(watchdog);
      clearInterval(pollTimer);
      feed.removeAttribute("src");
      tile.classList.add("is-off");
      overlay.style.display = "flex";
      overlay.querySelector(".overlay-text").textContent = "Kamera dimatikan";
      cameraState[cameraId] = "off";
      if (powerBtn) powerBtn.classList.add("is-off");
      updateCameraStat();
    }

    function applyOnUI() {
      isOff = false;
      tile.classList.remove("is-off");
      if (powerBtn) powerBtn.classList.remove("is-off");
      reload();
      startWatchdog();
    }

    feed.addEventListener("load", () => setState("live"));
    feed.addEventListener("error", () => {
      if (isOff) return;
      setState("offline");
      clearTimeout(watchdog);
      watchdog = setTimeout(reload, 3000);
    });

    if (powerBtn) {
      powerBtn.addEventListener("click", async () => {
        powerBtn.disabled = true;
        try {
          const res = await fetch(`/camera/${cameraId}/toggle`, {
            method: "POST",
            credentials: "same-origin",
          });
          const data = await res.json();
          if (data.running) {
            applyOnUI();
          } else {
            applyOffUI();
          }
        } catch (err) {
          console.error("Gagal toggle kamera:", err);
        } finally {
          powerBtn.disabled = false;
        }
      });
    }

    // Inisialisasi sesuai status awal dari server
    if (isOff) {
      applyOffUI();
    } else {
      startWatchdog();
      reload();
    }

    updateCameraStat();
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
    document.body.addEventListener(evt, unlockAudio, {
      once: true,
      passive: true,
    });
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
  notice.innerHTML =
    "🔇 Audio alarm diblokir browser. Klik tombol <strong>Alarm Aktif</strong> untuk mengaktifkannya.";
  const main = document.querySelector(".main");
  if (main) {
    main.insertBefore(notice, main.firstChild);
    setTimeout(() => notice.remove(), 6000);
  }
}

const DASHBOARD_ROWS_PER_PAGE = 5;
let dashboardAllRows = [];
let dashboardCurrentPage = 1;

function dashboardDisplayPage(pageNum) {
  if (dashboardAllRows.length === 0) return;

  dashboardCurrentPage = pageNum;
  const totalPages = Math.ceil(
    dashboardAllRows.length / DASHBOARD_ROWS_PER_PAGE,
  );

  if (dashboardCurrentPage < 1) dashboardCurrentPage = 1;
  if (dashboardCurrentPage > totalPages) dashboardCurrentPage = totalPages;

  const body = document.getElementById("live-log-body");
  body.innerHTML = "";

  const start = (dashboardCurrentPage - 1) * DASHBOARD_ROWS_PER_PAGE;
  const end = start + DASHBOARD_ROWS_PER_PAGE;

  for (let i = start; i < end && i < dashboardAllRows.length; i++) {
    body.appendChild(dashboardAllRows[i].cloneNode(true));
  }

  // Update pagination info
  document.getElementById("dash-current-page").textContent =
    dashboardCurrentPage;
  document.getElementById("dash-total-pages").textContent = totalPages || 1;
  document.getElementById("dash-page-info").textContent =
    start + 1 + " - " + Math.min(end, dashboardAllRows.length);
  document.getElementById("dash-total-logs").textContent =
    dashboardAllRows.length;

  // Update page numbers
  dashboardUpdatePageNumbers(totalPages);
}

function dashboardUpdatePageNumbers(totalPages) {
  const pageNumbersDiv = document.getElementById("dash-page-numbers");
  pageNumbersDiv.innerHTML = "";

  const maxButtons = 5;
  let startPage = Math.max(
    1,
    dashboardCurrentPage - Math.floor(maxButtons / 2),
  );
  let endPage = Math.min(totalPages, startPage + maxButtons - 1);

  if (endPage - startPage + 1 < maxButtons) {
    startPage = Math.max(1, endPage - maxButtons + 1);
  }

  for (let i = startPage; i <= endPage; i++) {
    const btn = document.createElement("button");
    btn.textContent = i;
    btn.style.padding = "6px 10px";
    btn.style.border = "none";
    btn.style.borderRadius = "4px";
    btn.style.cursor = "pointer";
    btn.style.fontSize = "13px";

    if (i === dashboardCurrentPage) {
      btn.style.backgroundColor = "#4a90e2";
      btn.style.color = "white";
      btn.style.fontWeight = "bold";
    } else {
      btn.style.backgroundColor = "#f0f0f0";
      btn.style.color = "#333";
    }

    btn.onclick = () => dashboardDisplayPage(i);
    pageNumbersDiv.appendChild(btn);
  }
}

function dashboardNextPage() {
  const totalPages = Math.ceil(
    dashboardAllRows.length / DASHBOARD_ROWS_PER_PAGE,
  );
  if (dashboardCurrentPage < totalPages) {
    dashboardDisplayPage(dashboardCurrentPage + 1);
  }
}

function dashboardPreviousPage() {
  if (dashboardCurrentPage > 1) {
    dashboardDisplayPage(dashboardCurrentPage - 1);
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
        return (
          d.getFullYear() === today.getFullYear() &&
          d.getMonth() === today.getMonth() &&
          d.getDate() === today.getDate()
        );
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
      const rows = Array.from(
        doc.querySelectorAll("table.log-table tbody tr[data-key]"),
      );

      if (rows.length === 0) {
        dashboardAllRows = [];
        dashboardDisplayPage(1);
        updateLogStats([]);
        return;
      }

      const nextKnown = new Set();
      let hasNew = false;

      dashboardAllRows = rows.map((row) => {
        const key = row.getAttribute("data-key");
        nextKnown.add(key);
        const clone = row.cloneNode(true);
        if (!firstLoad && !knownKeys.has(key)) {
          clone.classList.add("is-new");
          hasNew = true;
        }
        // Tampilan hanya menampilkan Kamera, Terdeteksi, Keyakinan.
        // Waktu & Gambar (Preview/Download) disembunyikan, tapi datanya tetap
        // dipakai dari "rows" asli (belum dipotong) untuk statistik & grafik tren.
        const tds = clone.querySelectorAll("td");
        if (tds.length >= 5) {
          tds[4].remove(); // Gambar (Preview/Download)
          tds[0].remove(); // Waktu
        }
        return clone;
      });

      if (hasNew && typeof window.triggerAlarm === "function") {
        window.triggerAlarm();
      }

      knownKeys = nextKnown;
      firstLoad = false;
      updateLogStats(rows);

      // Display first page
      dashboardDisplayPage(1);
    } catch (err) {
      console.error("Gagal memuat log deteksi:", err);
    }
  }

  refresh();
  setInterval(refresh, 4000);
}
