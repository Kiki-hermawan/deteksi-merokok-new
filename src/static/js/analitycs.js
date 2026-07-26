document.addEventListener("DOMContentLoaded", function () {
  initAnalyticsCharts();
  loadReportInsights();
  setInterval(loadReportInsights, 10000);
});

let chartStatus = null;
let chartCamera = null;
let chartTrend = null;
let chartConfidence = null;

function initAnalyticsCharts() {
  if (typeof Chart === "undefined") {
    console.warn("Chart.js not loaded; skipping charts.");
    return;
  }

  const statusCanvas = document.getElementById("chart-status");
  const cameraCanvas = document.getElementById("chart-camera");
  const trendCanvas = document.getElementById("chart-trend");
  const confidenceCanvas = document.getElementById("chart-confidence");

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

  if (statusCanvas) {
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
  }

  if (cameraCanvas) {
    chartCamera = new Chart(cameraCanvas, {
      type: "bar",
      data: {
        labels: [],
        datasets: [{
          label: "Jumlah Deteksi",
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
  }

  // Trend line: jumlah deteksi per jam, dihitung dari log yang tersedia.
  if (trendCanvas) {
    chartTrend = new Chart(trendCanvas, {
      type: "line",
      data: {
        labels: [],
        datasets: [{
          label: "Deteksi per Jam",
          data: [],
          borderColor: "#d92d20",
          backgroundColor: "rgba(217, 45, 32, 0.12)",
          fill: true,
          tension: 0.35,
          pointRadius: 3,
          pointBackgroundColor: "#d92d20"
        }]
      },
      options: {
        ...commonOptions,
        plugins: {
          ...commonOptions.plugins,
          tooltip: {
            ...commonOptions.plugins.tooltip,
            callbacks: {
              label: (ctx) => `${ctx.raw} deteksi`
            }
          }
        },
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
  }

  // Histogram keyakinan (confidence): membantu menilai apakah model banyak ragu-ragu.
  if (confidenceCanvas) {
    chartConfidence = new Chart(confidenceCanvas, {
      type: "bar",
      data: {
        labels: ["<50%", "50–70%", "70–90%", "90–100%"],
        datasets: [{
          label: "Jumlah Deteksi",
          data: [0, 0, 0, 0],
          backgroundColor: ["#d92d20", "#e8590c", "#f2a900", "#12805c"],
          borderRadius: 6,
          barThickness: 36
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
            ticks: { font: { family: "'Inter', sans-serif", size: 11 }, maxRotation: 0 },
            grid: { display: false }
          }
        }
      }
    });
  }

  refreshStatCharts();
  setInterval(refreshStatCharts, 5000);
}

async function refreshStatCharts() {
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
      const merged = normalizeCameraBreakdown(stats.camera_breakdown);
      chartCamera.data.labels = merged.map((c) => c.name);
      chartCamera.data.datasets[0].data = merged.map((c) => c.count);
      chartCamera.update();
    }
  } catch (err) {
    console.error("Gagal memuat statistik:", err);
  }
}

// Menggabungkan entri kamera yang sebenarnya sama tapi namanya beda-beda
// karena diambil dari nama file (mis. "Camera 1", "camera1", " Camera 1 ").
// Catatan: typo seperti "Cameara 1" tidak bisa dideteksi otomatis dengan aman;
// idealnya nama kamera dikunci lewat konfigurasi/ID di backend, bukan dari filename.
function normalizeCameraBreakdown(breakdown) {
  const groups = new Map();
  breakdown.forEach((c) => {
    const key = (c.name || "").trim().toLowerCase().replace(/[\s_-]+/g, "");
    if (!groups.has(key)) {
      groups.set(key, { name: (c.name || "").trim(), count: 0 });
    }
    groups.get(key).count += c.count || 0;
  });
  return Array.from(groups.values()).sort((a, b) => b.count - a.count);
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

// --- Laporan & insight otomatis, dihitung dari log deteksi ---
// Catatan: /detection_log saat ini hanya mengembalikan beberapa kejadian
// terakhir (lihat hint "50 kejadian terakhir" di dashboard). Untuk laporan
// jangka panjang (mingguan/bulanan) yang akurat, backend perlu endpoint log
// dengan rentang tanggal (mis. /api/detections?from=...&to=...).
async function loadReportInsights() {
  try {
    const res = await fetch("/detection_log", { credentials: "same-origin" });
    if (!res.ok) return;
    const html = await res.text();
    const doc = new DOMParser().parseFromString(html, "text/html");
    const rows = Array.from(doc.querySelectorAll("table.log-table tbody tr[data-key]"));

    renderInsights(rows);
    if (chartTrend) refreshTrendChart(rows);
    if (chartConfidence) refreshConfidenceChart(rows);
  } catch (err) {
    console.error("Gagal memuat data laporan:", err);
  }
}

function renderInsights(rows) {
  const el = document.getElementById("report-insights");
  if (!el) return;

  if (rows.length === 0) {
    el.innerHTML = '<li>Belum ada data deteksi untuk dianalisis.</li>';
    return;
  }

  // Jam dengan deteksi terbanyak
  const hourCounts = new Map();
  rows.forEach((row) => {
    const cell = row.querySelector("td");
    if (!cell) return;
    const d = new Date(cell.textContent.trim().replace(" ", "T"));
    if (isNaN(d.getTime())) return;
    const hour = d.getHours();
    hourCounts.set(hour, (hourCounts.get(hour) || 0) + 1);
  });
  let peakHour = null, peakHourCount = 0;
  hourCounts.forEach((count, hour) => {
    if (count > peakHourCount) { peakHourCount = count; peakHour = hour; }
  });

  // Kamera paling aktif
  const cameraCounts = new Map();
  rows.forEach((row) => {
    const cells = row.querySelectorAll("td");
    if (cells.length < 2) return;
    const name = cells[1].textContent.trim();
    cameraCounts.set(name, (cameraCounts.get(name) || 0) + 1);
  });
  let topCamera = null, topCameraCount = 0;
  cameraCounts.forEach((count, name) => {
    if (count > topCameraCount) { topCameraCount = count; topCamera = name; }
  });

  // Rata-rata keyakinan dari log yang tampil
  let confSum = 0, confN = 0;
  rows.forEach((row) => {
    const cells = row.querySelectorAll("td");
    if (cells.length < 4) return;
    const match = cells[3].textContent.trim().match(/(\d+(\.\d+)?)/);
    if (!match) return;
    confSum += parseFloat(match[1]);
    confN++;
  });
  const avgConf = confN ? Math.round(confSum / confN) : null;

  const items = [];
  items.push(`<li>Tercatat <strong>${rows.length}</strong> kejadian deteksi dalam log terkini.</li>`);
  if (peakHour !== null) {
    items.push(`<li>Jam dengan deteksi terbanyak: <strong>${String(peakHour).padStart(2, "0")}:00–${String(peakHour).padStart(2, "0")}:59</strong> (${peakHourCount} kejadian).</li>`);
  }
  if (topCamera) {
    items.push(`<li>Kamera dengan deteksi terbanyak: <strong>${topCamera}</strong> (${topCameraCount} kejadian).</li>`);
  }
  if (avgConf !== null) {
    const tone = avgConf >= 70 ? "cukup tinggi" : "tergolong rendah, pertimbangkan tinjau ulang threshold model";
    items.push(`<li>Rata-rata keyakinan deteksi pada log ini: <strong>${avgConf}%</strong> — ${tone}.</li>`);
  }

  el.innerHTML = items.join("");
}

function refreshTrendChart(rows) {
  if (!chartTrend) return;
  const counts = new Map(); // "YYYY-MM-DD HH:00" -> count

  rows.forEach((row) => {
    const cell = row.querySelector("td");
    if (!cell) return;
    const raw = cell.textContent.trim();
    const d = new Date(raw.replace(" ", "T"));
    if (isNaN(d.getTime())) return;
    d.setMinutes(0, 0, 0);
    const key = d.toISOString();
    counts.set(key, (counts.get(key) || 0) + 1);
  });

  const sortedKeys = Array.from(counts.keys()).sort();
  const labels = sortedKeys.map((k) => {
    const d = new Date(k);
    return d.toLocaleString("id-ID", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  });
  const data = sortedKeys.map((k) => counts.get(k));

  chartTrend.data.labels = labels;
  chartTrend.data.datasets[0].data = data;
  chartTrend.update();
}

function refreshConfidenceChart(rows) {
  if (!chartConfidence) return;
  const buckets = [0, 0, 0, 0]; // <50, 50-70, 70-90, 90-100

  rows.forEach((row) => {
    const cells = row.querySelectorAll("td");
    if (cells.length < 4) return;
    const text = cells[3].textContent.trim(); // kolom "Keyakinan", mis. "92%"
    const match = text.match(/(\d+(\.\d+)?)/);
    if (!match) return;
    const val = parseFloat(match[1]);
    if (val < 50) buckets[0]++;
    else if (val < 70) buckets[1]++;
    else if (val < 90) buckets[2]++;
    else buckets[3]++;
  });

  chartConfidence.data.datasets[0].data = buckets;
  chartConfidence.update();
}