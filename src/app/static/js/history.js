/* ============================================================
   SmartChoice AI — history.js
   Decision history timeline with filtering and detail panel
   ============================================================ */
"use strict";

const History = (() => {
  let allHistory  = [];
  let selectedId  = null;

  function init() {
    loadHistory();
    bindFilters();
    bindCloseDetail();
  }

  // ── Load History ─────────────────────────────────────────────
  async function loadHistory() {
    const container = document.getElementById("historyTimeline");
    if (!container) return;

    try {
      const res  = await fetch("/api/history/");
      const data = await res.json();
      allHistory = data.history || [];
      renderTimeline(allHistory);
    } catch (e) {
      container.innerHTML = `<div class="text-center text-muted py-5">
        <i class="bi bi-exclamation-circle fs-3 d-block mb-2"></i>
        Failed to load history. Please refresh.
      </div>`;
    }
  }

  // ── Render Timeline ───────────────────────────────────────────
  function renderTimeline(sessions) {
    const container = document.getElementById("historyTimeline");
    if (!container) return;

    if (!sessions.length) {
      container.innerHTML = `<div class="text-center py-5">
        <i class="bi bi-inbox fs-2 text-muted d-block mb-3"></i>
        <h5 class="text-muted">No decisions found</h5>
        <p class="text-muted small">Start your first analysis on the <a href="/">AI Advisor</a> page.</p>
      </div>`;
      return;
    }

    container.innerHTML = `<div class="timeline">${
      sessions.map(s => timelineItemHTML(s)).join("")
    }</div>`;

    container.querySelectorAll(".timeline-card").forEach(card => {
      card.addEventListener("click", () => showDetail(card.dataset.id));
    });
  }

  function timelineItemHTML(s) {
    const scores = s.scores ? Object.entries(s.scores) : [];
    const scoreChips = scores.slice(0, 3).map(([name, score]) =>
      `<span class="timeline-score-chip ${window.SC?.scoreClass(score)}">${escHtml(truncate(name, 16))}: ${score}</span>`
    ).join("");

    return `
      <div class="timeline-item">
        <div class="timeline-dot ${s.status}"></div>
        <div class="timeline-card ${s.id === selectedId ? 'selected' : ''}" data-id="${s.id}">
          <div class="timeline-title">${escHtml(s.title)}</div>
          <div class="timeline-meta">
            <span class="domain-badge">${window.SC?.domainLabel(s.domain) || s.domain}</span>
            <span class="status-badge status-${s.status}">${s.status}</span>
            <span class="text-muted"><i class="bi bi-clock me-1"></i>${window.SC?.fmtDate(s.updated_at) || s.updated_at}</span>
            <span class="text-muted"><i class="bi bi-chat-square me-1"></i>${s.message_count || 0} messages</span>
          </div>
          ${scoreChips ? `<div class="timeline-scores">${scoreChips}</div>` : ""}
        </div>
      </div>
    `;
  }

  // ── Show Detail Panel ─────────────────────────────────────────
  async function showDetail(sessionId) {
    selectedId = sessionId;
    const panel   = document.getElementById("historyDetailPanel");
    const content = document.getElementById("historyDetailContent");
    if (!panel || !content) return;

    panel.style.display = "block";
    content.innerHTML = `<div class="text-center py-4"><div class="spinner-border text-primary"></div></div>`;

    try {
      const res  = await fetch(`/api/chat/sessions/${sessionId}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Not found");

      const s = data.session;
      const r = data.result;
      const scores = r?.scores ? Object.entries(r.scores) : [];

      content.innerHTML = `
        <div class="mb-3">
          <h6 class="fw-700 mb-1">${escHtml(s.title)}</h6>
          <div class="d-flex flex-wrap gap-2 mb-2">
            <span class="domain-badge">${window.SC?.domainLabel(s.domain) || s.domain}</span>
            <span class="status-badge status-${s.status}">${s.status}</span>
          </div>
          <div class="text-muted small">
            Created: ${window.SC?.fmtDate(s.created_at)}<br>
            Updated: ${window.SC?.fmtDate(s.updated_at)}
          </div>
        </div>

        ${scores.length ? `
        <div class="mb-3">
          <div class="section-title">Decision Scores</div>
          ${scores.map(([name, score]) => `
            <div class="d-flex justify-content-between align-items-center mb-2">
              <small class="fw-600">${escHtml(truncate(name, 24))}</small>
              <strong class="${window.SC?.scoreClass(score)}">${score}/100</strong>
            </div>
            <div class="score-bar-bg mb-3">
              <div class="score-bar-fill" style="width:${score}%;background:${window.SC?.scoreBarColor(score)}"></div>
            </div>
          `).join("")}
        </div>` : ""}

        ${r?.recommendation ? `
        <div class="mb-3">
          <div class="section-title">Recommendation</div>
          <div class="analysis-result-box" style="max-height:200px;font-size:0.8rem">
            ${typeof marked !== 'undefined' ? marked.parse(r.recommendation) : escHtml(r.recommendation)}
          </div>
        </div>` : ""}

        <div class="d-flex flex-column gap-2 mt-3">
          <a href="/" class="btn btn-sm btn-primary w-100"
             onclick="window._resumeSession='${s.id}';return true">
            <i class="bi bi-chat-dots me-1"></i> Resume Session
          </a>
          ${r ? `<a href="/api/reports/${s.id}/pdf" target="_blank" class="btn btn-sm btn-outline-secondary w-100">
            <i class="bi bi-file-earmark-pdf me-1"></i> Download PDF Report
          </a>` : ""}
        </div>
      `;

      // Highlight in timeline
      document.querySelectorAll(".timeline-card").forEach(c => c.classList.remove("selected"));
      document.querySelector(`.timeline-card[data-id="${sessionId}"]`)?.classList.add("selected");

    } catch (e) {
      content.innerHTML = `<p class="text-danger small">Failed to load session detail.</p>`;
    }
  }

  // ── Close Detail ──────────────────────────────────────────────
  function bindCloseDetail() {
    document.getElementById("closeDetailBtn")?.addEventListener("click", () => {
      const panel = document.getElementById("historyDetailPanel");
      if (panel) panel.style.display = "none";
      selectedId = null;
      document.querySelectorAll(".timeline-card").forEach(c => c.classList.remove("selected"));
    });
  }

  // ── Filters ───────────────────────────────────────────────────
  function bindFilters() {
    const search  = document.getElementById("historySearch");
    const domain  = document.getElementById("historyDomainFilter");
    const status  = document.getElementById("historyStatusFilter");

    function applyFilters() {
      const q = search?.value.toLowerCase().trim() || "";
      const d = domain?.value || "";
      const s = status?.value || "";
      const filtered = allHistory.filter(item =>
        (!q || item.title.toLowerCase().includes(q)) &&
        (!d || item.domain === d) &&
        (!s || item.status === s)
      );
      renderTimeline(filtered);
    }

    search?.addEventListener("input", applyFilters);
    domain?.addEventListener("change", applyFilters);
    status?.addEventListener("change", applyFilters);
  }

  // ── Utilities ─────────────────────────────────────────────────
  function escHtml(str) {
    const div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
  }
  function truncate(str, n) { return str?.length > n ? str.slice(0, n) + "…" : (str || ""); }

  return { init };
})();

document.addEventListener("DOMContentLoaded", () => History.init());
