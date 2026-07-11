/* ============================================================
   SmartChoice AI — dashboard.js
   Dashboard charts, stats, and quick-compare feature
   ============================================================ */
"use strict";

const Dashboard = (() => {
  let domainPieChart   = null;
  let activityChart    = null;
  let recentSessions   = [];

  function init() {
    loadStats();
    loadRecentDecisions();
    bindQuickCompare();
  }

  // ── Load Stats ───────────────────────────────────────────────
  async function loadStats() {
    try {
      const res  = await fetch("/api/history/stats");
      const data = await res.json();
      const s = data.stats || {};

      setText("statTotal",     s.total_decisions ?? 0);
      setText("statCompleted", s.completed        ?? 0);
      setText("statActive",    s.active           ?? 0);
      setText("statDomains",   Object.keys(s.domains_breakdown || {}).length);

      renderDomainPieChart(s.domains_breakdown || {});
    } catch (e) {
      console.warn("Stats load failed:", e);
    }
  }

  // ── Load Recent Decisions ────────────────────────────────────
  async function loadRecentDecisions() {
    try {
      const res  = await fetch("/api/history/");
      const data = await res.json();
      recentSessions = data.history || [];
      renderRecentTable(recentSessions.slice(0, 10));
      renderActivityChart(recentSessions);
    } catch (e) {
      console.warn("History load failed:", e);
    }
  }

  // ── Domain Pie Chart ─────────────────────────────────────────
  function renderDomainPieChart(breakdown) {
    const canvas = document.getElementById("domainPieChart");
    if (!canvas) return;
    if (domainPieChart) domainPieChart.destroy();

    const labels = Object.keys(breakdown);
    const values = Object.values(breakdown);
    if (!labels.length) {
      canvas.parentElement.innerHTML = `<p class="text-muted small text-center py-4">No data yet.</p>`;
      return;
    }

    const PALETTE = ["#3b82f6","#8b5cf6","#10b981","#f59e0b","#ef4444","#06b6d4","#f97316","#ec4899"];
    const isDark = document.documentElement.getAttribute("data-bs-theme") === "dark";

    domainPieChart = new Chart(canvas, {
      type: "doughnut",
      data: {
        labels: labels.map(l => window.SC?.domainLabel(l) || l),
        datasets: [{
          data: values,
          backgroundColor: PALETTE.slice(0, labels.length),
          borderWidth: 2,
          borderColor: isDark ? "#1e2535" : "#ffffff",
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "65%",
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              color: isDark ? "#94a3b8" : "#64748b",
              font: { size: 11 },
              padding: 16,
              usePointStyle: true,
              pointStyleWidth: 10,
            },
          },
          tooltip: {
            callbacks: {
              label: ctx => ` ${ctx.label}: ${ctx.parsed} decision${ctx.parsed !== 1 ? 's' : ''}`
            }
          }
        },
      },
    });
  }

  // ── Activity Line Chart ───────────────────────────────────────
  function renderActivityChart(sessions) {
    const canvas = document.getElementById("activityLineChart");
    if (!canvas) return;
    if (activityChart) activityChart.destroy();

    // Group by day (last 14 days)
    const days = {};
    const now = Date.now();
    for (let i = 13; i >= 0; i--) {
      const d = new Date(now - i * 86400000);
      const key = d.toLocaleDateString("en-IN", { month: "short", day: "2-digit" });
      days[key] = 0;
    }
    sessions.forEach(s => {
      const key = new Date(s.updated_at).toLocaleDateString("en-IN", { month: "short", day: "2-digit" });
      if (key in days) days[key]++;
    });

    const isDark = document.documentElement.getAttribute("data-bs-theme") === "dark";
    const textColor = isDark ? "#94a3b8" : "#64748b";
    const gridColor = isDark ? "#2d3748" : "#e2e8f0";

    activityChart = new Chart(canvas, {
      type: "line",
      data: {
        labels: Object.keys(days),
        datasets: [{
          label: "Decisions",
          data: Object.values(days),
          borderColor: "#3b82f6",
          backgroundColor: "rgba(59,130,246,0.1)",
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointBackgroundColor: "#3b82f6",
          pointRadius: 4,
          pointHoverRadius: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx => ` ${ctx.parsed.y} decision${ctx.parsed.y !== 1 ? 's' : ''}`
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { color: textColor, precision: 0 },
            grid: { color: gridColor },
          },
          x: {
            ticks: { color: textColor, font: { size: 10 }, maxTicksLimit: 7 },
            grid: { display: false },
          },
        },
      },
    });
  }

  // ── Recent Decisions Table ────────────────────────────────────
  function renderRecentTable(sessions) {
    const tbody = document.getElementById("recentDecisionsTable");
    if (!tbody) return;
    if (!sessions.length) return;

    tbody.innerHTML = sessions.map(s => {
      const scores = s.scores ? Object.entries(s.scores) : [];
      const topScore = scores.length ? Math.max(...scores.map(([,v]) => v)) : null;
      return `
        <tr>
          <td>
            <a href="/" class="text-decoration-none fw-600 text-body"
               style="font-weight:600" onclick="loadSessionFromHistory('${s.id}');return false;">
              ${escHtml(window.SC?.truncate(s.title, 50) || s.title)}
            </a>
          </td>
          <td><span class="domain-badge">${window.SC?.domainLabel(s.domain) || s.domain}</span></td>
          <td><span class="status-badge status-${s.status}">${s.status}</span></td>
          <td class="text-muted">${window.SC?.fmtDate(s.updated_at) || s.updated_at}</td>
          <td>
            ${topScore !== null ? `<strong class="${window.SC?.scoreClass(topScore)}">${topScore}/100</strong>` : "—"}
          </td>
        </tr>
      `;
    }).join("");
  }

  // ── Quick Compare ─────────────────────────────────────────────
  function bindQuickCompare() {
    const btn = document.getElementById("quickCompareBtn");
    if (!btn) return;

    btn.addEventListener("click", async () => {
      const rawOptions = document.getElementById("quickCompareOptions")?.value || "";
      const context    = document.getElementById("quickCompareContext")?.value || "";
      const domain     = document.getElementById("quickCompareDomain")?.value || "";

      const options = rawOptions.split(",").map(o => o.trim()).filter(Boolean);
      if (options.length < 2) {
        window.SC?.Toast.show("Enter at least 2 comma-separated options.", "warning");
        return;
      }

      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Analyzing…';

      try {
        const res = await fetch("/api/decisions/compare", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ options, context, domain }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Comparison failed");

        const resultBox = document.getElementById("quickCompareResult");
        const content   = document.getElementById("quickCompareContent");
        if (resultBox) resultBox.style.display = "block";
        if (content) {
          content.innerHTML = typeof marked !== "undefined"
            ? marked.parse(data.analysis || "No analysis returned.")
            : (data.analysis || "No analysis returned.");
        }
        window.SC?.Toast.show("Comparison complete!", "success");
      } catch (err) {
        window.SC?.Toast.show(err.message, "error");
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-arrow-right-circle me-1"></i> Run Comparison';
      }
    });
  }

  // ── Utilities ─────────────────────────────────────────────────
  function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  function escHtml(str) {
    const div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
  }

  return { init };
})();

// Allow loading session from the recent table
window.loadSessionFromHistory = function(sessionId) {
  window.location.href = `/?session=${sessionId}`;
};

document.addEventListener("DOMContentLoaded", () => Dashboard.init());
