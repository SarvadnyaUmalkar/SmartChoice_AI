/* ============================================================
   SmartChoice AI — chat.js
   Full chat interface logic: messaging, sessions, panels
   ============================================================ */
"use strict";

const Chat = (() => {
  // ── State ────────────────────────────────────────────────────
  let activeSessionId = null;
  let activeDomain    = null;
  let isLoading       = false;
  let scoreChart      = null;

  // ── DOM refs ─────────────────────────────────────────────────
  const $ = id => document.getElementById(id);
  const $q = sel => document.querySelector(sel);

  const chatInput    = $("chatInput");
  const sendBtn      = $("sendBtn");
  const chatMessages = $("chatMessages");
  const chatWelcome  = $("chatWelcome");
  const typingInd    = $("typingIndicator");
  const sessionList  = $("sessionList");
  const scoreCardsBar = $("scoreCardsBar");
  const scoreCardsList = $("scoreCardsList");
  const riskItemsList  = $("riskItemsList");
  const compMatrix     = $("comparisonMatrix");
  const panelMatrix    = $("panelMatrix");
  const charCounter    = $("charCounter");
  const titleEl        = $("chatSessionTitle");
  const domainEl       = $("chatSessionDomain");
  const pdfBtn         = $("downloadPdfBtn");
  const activeDomainSel = $("activeDomainSelect");
  const templatesGrid  = $("templatesGrid");
  const scoreBarCanvas = $("scoreBarChart");

  // ── marked.js config ─────────────────────────────────────────
  if (typeof marked !== "undefined") {
    marked.setOptions({ breaks: true, gfm: true });
  }

  function renderMarkdown(text) {
    return typeof marked !== "undefined" ? marked.parse(text) : text;
  }

  // ── Init ──────────────────────────────────────────────────────
  function init() {
    loadSessions();
    loadTemplates();
    bindEvents();
    checkUrlSession();
  }

  // ── Check for ?session= URL parameter ────────────────────────
  function checkUrlSession() {
    // Support ?session=<id> deep-link AND window._resumeSession from history page
    const urlParams = new URLSearchParams(window.location.search);
    const sid = urlParams.get("session") || window._resumeSession || null;
    if (sid) {
      loadSession(sid);
      // Clean URL without reload
      if (history.replaceState) {
        history.replaceState(null, "", window.location.pathname);
      }
    }
  }

  // ── Event Bindings ────────────────────────────────────────────
  function bindEvents() {
    // Send on button click
    sendBtn?.addEventListener("click", sendMessage);

    // Keyboard shortcuts
    chatInput?.addEventListener("keydown", e => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        sendMessage();
      }
    });

    // Auto-resize textarea & char counter
    chatInput?.addEventListener("input", () => {
      chatInput.style.height = "auto";
      chatInput.style.height = Math.min(chatInput.scrollHeight, 160) + "px";
      const len = chatInput.value.length;
      if (charCounter) charCounter.textContent = `${len} / 4000`;
      if (sendBtn) sendBtn.disabled = len === 0;
    });

    // New session
    $("newSessionBtn")?.addEventListener("click", newSession);

    // Clear chat
    $("clearChatBtn")?.addEventListener("click", newSession);

    // Mobile sidebar toggle
    $("toggleSidebarBtn")?.addEventListener("click", () => {
      $("chatSidebar")?.classList.toggle("mobile-open");
    });

    // Close analysis panel
    $("closePanelBtn")?.addEventListener("click", () => {
      document.getElementById("analysisPanel")?.classList.add("d-none");
    });

    // Domain chip clicks
    document.querySelectorAll(".domain-chip").forEach(chip => {
      chip.addEventListener("click", () => {
        const domain = chip.dataset.domain;
        const prompt = chip.dataset.prompt;
        activeDomain = domain;
        if (activeDomainSel) activeDomainSel.value = domain;
        showChat();
        if (chatInput) {
          chatInput.value = prompt;
          chatInput.dispatchEvent(new Event("input"));
        }
        chatInput?.focus();
      });
    });

    // Domain selector
    activeDomainSel?.addEventListener("change", () => {
      activeDomain = activeDomainSel.value || null;
    });

    // PDF download
    pdfBtn?.addEventListener("click", downloadPDF);

    // Sidebar domain filter
    $("domainFilterSelect")?.addEventListener("change", e => {
      const filterDomain = e.target.value;
      const items = sessionList?.querySelectorAll(".session-item") || [];
      items.forEach(item => {
        if (!filterDomain || item.dataset.domain === filterDomain) {
          item.style.display = "";
        } else {
          item.style.display = "none";
        }
      });
    });

    // Re-render chart on theme toggle to match new color scheme
    document.getElementById("themeToggleBtn")?.addEventListener("click", () => {
      setTimeout(() => {
        if (scoreChart) {
          const data = scoreChart.data.datasets[0].data;
          const labels = scoreChart.data.labels;
          const scores = labels.map((lbl, i) => ({ name: lbl, score: data[i] }));
          updateScoreChart(scores);
        }
      }, 100);
    });
  }

  // ── Load Templates ────────────────────────────────────────────
  async function loadTemplates() {
    if (!templatesGrid) return;
    try {
      const res = await fetch("/api/decisions/templates");
      const data = await res.json();
      const templates = data.templates || [];

      if (!templates.length) {
        templatesGrid.innerHTML = '<p class="text-muted small text-center">No templates available.</p>';
        return;
      }

      templatesGrid.innerHTML = templates.slice(0, 8).map(t => `
        <button class="template-card" data-prompt="${escHtml(t.quick_prompt)}" data-domain="${t.domain}">
          <div class="template-card-icon">${t.icon}</div>
          <div class="template-card-category">${escHtml(t.category)}</div>
          <div class="template-card-title">${escHtml(t.title)}</div>
          <div class="template-card-desc">${escHtml(t.description)}</div>
        </button>
      `).join("");

      templatesGrid.querySelectorAll(".template-card").forEach(card => {
        card.addEventListener("click", () => {
          activeDomain = card.dataset.domain;
          if (activeDomainSel) activeDomainSel.value = activeDomain;
          showChat();
          if (chatInput) {
            chatInput.value = card.dataset.prompt;
            chatInput.dispatchEvent(new Event("input"));
          }
          chatInput?.focus();
        });
      });
    } catch (e) {
      templatesGrid.innerHTML = '<p class="text-muted small text-center">Failed to load templates.</p>';
    }
  }

  // ── Load Sessions ─────────────────────────────────────────────
  async function loadSessions() {
    if (!sessionList) return;
    try {
      const res = await fetch("/api/chat/sessions");
      const data = await res.json();
      renderSessionList(data.sessions || []);
    } catch (e) { /* silent */ }
  }

  function renderSessionList(sessions) {
    if (!sessionList) return;
    if (!sessions.length) {
      sessionList.innerHTML = `
        <div class="session-empty text-center py-4">
          <i class="bi bi-chat-square-dots fs-2 text-muted mb-2 d-block"></i>
          <p class="text-muted small">No sessions yet.</p>
        </div>`;
      return;
    }
    sessionList.innerHTML = sessions.map(s => `
      <div class="session-item ${s.id === activeSessionId ? 'active' : ''}"
           data-id="${s.id}" data-domain="${s.domain}">
        <div class="session-item-title">${escHtml(SC.truncate(s.title, 48))}</div>
        <div class="session-item-meta">
          <span class="session-domain-badge">${SC.domainLabel(s.domain)}</span>
          <span>${SC.fmtDate(s.updated_at).split(",")[0]}</span>
          <span class="ms-auto">
            <span class="status-badge status-${s.status}">${s.status}</span>
          </span>
        </div>
      </div>
    `).join("");

    sessionList.querySelectorAll(".session-item").forEach(item => {
      item.addEventListener("click", () => loadSession(item.dataset.id));
    });
  }

  // ── Load existing session ─────────────────────────────────────
  async function loadSession(sessionId) {
    try {
      const res = await fetch(`/api/chat/sessions/${sessionId}`);
      if (!res.ok) return;
      const data = await res.json();

      activeSessionId = sessionId;
      activeDomain = data.session.domain;

      if (titleEl) titleEl.textContent = data.session.title;
      if (domainEl) domainEl.textContent = SC.domainLabel(data.session.domain);

      showChat();
      chatMessages.innerHTML = "";

      (data.messages || []).forEach(m => appendMessage(m.role, m.content, m.created_at, false));

      if (data.result) {
        updateAnalysisPanel(data.result);
      }

      if (pdfBtn) {
        pdfBtn.style.display = data.result ? "inline-flex" : "none";
        pdfBtn.dataset.sessionId = sessionId;
      }

      chatMessages.scrollTop = chatMessages.scrollHeight;
      loadSessions();
    } catch (e) {
      SC.Toast.show("Failed to load session.", "error");
    }
  }

  // ── New Session ───────────────────────────────────────────────
  function newSession() {
    activeSessionId = null;
    activeDomain = null;
    chatMessages.innerHTML = "";
    chatWelcome.style.display = "flex";
    chatMessages.style.display = "none";
    if (scoreCardsBar) scoreCardsBar.style.display = "none";
    if (scoreCardsList) scoreCardsList.innerHTML = `<p class="text-muted small text-center py-3">Scores will appear after analysis</p>`;
    if (riskItemsList) riskItemsList.innerHTML = `<p class="text-muted small text-center py-3">Risk factors will appear after analysis</p>`;
    if (compMatrix) compMatrix.innerHTML = "";
    if (panelMatrix) panelMatrix.style.display = "none";
    if (pdfBtn) pdfBtn.style.display = "none";
    if (titleEl) titleEl.textContent = "SmartChoice AI Advisor";
    if (domainEl) domainEl.textContent = "Select a template or type your decision";
    if (activeDomainSel) activeDomainSel.value = "";
    if (scoreChart) { scoreChart.destroy(); scoreChart = null; }
    loadSessions();
  }

  // ── Show Chat (hide welcome) ──────────────────────────────────
  function showChat() {
    if (chatWelcome) chatWelcome.style.display = "none";
    if (chatMessages) chatMessages.style.display = "flex";
  }

  // ── Send Message ──────────────────────────────────────────────
  async function sendMessage() {
    const message = chatInput?.value.trim();
    if (!message || isLoading) return;
    if (message.length > 4000) {
      SC.Toast.show("Message too long (max 4000 chars).", "warning");
      return;
    }

    isLoading = true;
    SC.AIStatus.loading();
    showChat();
    if (sendBtn) sendBtn.disabled = true;

    // Optimistic UI: show user message immediately
    appendMessage("user", message, null, true);
    chatInput.value = "";
    chatInput.style.height = "auto";
    if (charCounter) charCounter.textContent = "0 / 4000";

    // Show typing
    if (typingInd) typingInd.style.display = "flex";
    scrollBottom();

    try {
      const body = {
        message,
        session_id: activeSessionId,
        domain: activeDomainSel?.value || activeDomain || null,
        title: activeSessionId ? null : message.slice(0, 60),
      };

      const res = await fetch("/api/chat/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Request failed");
      }

      if (typingInd) typingInd.style.display = "none";

      // Update session state
      activeSessionId = data.session_id;
      activeDomain = data.domain;
      if (activeDomainSel && !activeDomainSel.value) activeDomainSel.value = data.domain;

      appendMessage("assistant", data.message, null, true);

      // Update title
      if (titleEl) titleEl.textContent = SC.truncate(message, 60);
      if (domainEl) domainEl.textContent = SC.domainLabel(data.domain);

      // Update scores
      if (data.scores?.length) {
        renderScoreCardsMini(data.scores);
        renderScoreCardsFull(data.scores);
        updateScoreChart(data.scores);
        if (pdfBtn) {
          pdfBtn.style.display = "inline-flex";
          pdfBtn.dataset.sessionId = activeSessionId;
        }
      }
      // Update risks
      if (data.risks?.length) {
        renderRiskItems(data.risks);
      }

      loadSessions();
      SC.AIStatus.ready();
    } catch (err) {
      if (typingInd) typingInd.style.display = "none";

      // "Failed to fetch" = server is down / not running / crashed
      const isNetworkError = err instanceof TypeError && (
        err.message === "Failed to fetch" ||
        err.message.includes("NetworkError") ||
        err.message.includes("Load failed")
      );

      if (isNetworkError) {
        SC.Toast.show(
          "Cannot reach the server. Make sure Flask is running on port 5000 " +
          "(<code>python run.py</code>) and the page is opened via " +
          "<code>http://localhost:5000</code> — not as a local file.",
          "error",
          8000
        );
      } else {
        SC.Toast.show(err.message || "Failed to get response.", "error");
      }

      // Put the unsent message back in the input so user doesn't lose it
      if (chatInput && !chatInput.value.trim()) {
        chatInput.value = message;
        chatInput.dispatchEvent(new Event("input"));
      }
      // Remove the optimistically-added user bubble on failure
      const bubbles = chatMessages?.querySelectorAll(".user-row");
      if (bubbles?.length) bubbles[bubbles.length - 1].remove();

      SC.AIStatus.error();
    } finally {
      isLoading = false;
      if (sendBtn) sendBtn.disabled = chatInput?.value.trim() === "";
      scrollBottom();
    }
  }

  // ── Append Message ────────────────────────────────────────────
  function appendMessage(role, content, timestamp, animate) {
    if (!chatMessages) return;
    const isAI = role === "assistant";
    const time = timestamp ? SC.fmtDate(timestamp) : new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });

    const row = document.createElement("div");
    row.className = `message-row ${isAI ? "ai-row" : "user-row"}${animate ? "" : ""}`;

    const avatarIcon = isAI ? "bi-cpu-fill" : "bi-person-fill";
    const avatarClass = isAI ? "ai-avatar" : "user-avatar";

    const bubbleContent = isAI ? renderMarkdown(content) : escHtml(content);

    row.innerHTML = `
      <div class="message-avatar ${avatarClass}">
        <i class="bi ${avatarIcon}"></i>
      </div>
      <div class="message-content">
        <div class="message-bubble">${bubbleContent}</div>
        <div class="message-time">${time}</div>
      </div>
    `;

    chatMessages.appendChild(row);
    scrollBottom();
  }

  // ── Score Cards Mini (input bar) ──────────────────────────────
  function renderScoreCardsMini(scores) {
    if (!scoreCardsBar) return;
    scoreCardsBar.style.display = "flex";
    const maxScore = Math.max(...scores.map(s => s.score));
    scoreCardsBar.innerHTML = scores.map(s => `
      <div class="score-card-mini ${s.score === maxScore ? "winner-mini" : ""}">
        <div class="sc-option-name">${escHtml(SC.truncate(s.name, 18))}</div>
        <div class="sc-score-value ${SC.scoreClass(s.score)}">${s.score}</div>
        <div class="sc-score-label">/ 100</div>
      </div>
    `).join("");
  }

  // ── Score Cards Full (panel) ──────────────────────────────────
  function renderScoreCardsFull(scores) {
    if (!scoreCardsList) return;
    const maxScore = Math.max(...scores.map(s => s.score));
    scoreCardsList.innerHTML = scores.map((s, i) => `
      <div class="score-card-full ${s.score === maxScore ? 'winner' : ''}">
        <div class="sc-full-name">${escHtml(s.name)}</div>
        <div class="sc-full-score-row">
          <span class="sc-full-score ${SC.scoreClass(s.score)}">${s.score}</span>
          <span class="sc-full-scale">/ 100</span>
          ${s.score === maxScore ? '<span class="sc-winner-badge ms-auto"><i class="bi bi-trophy-fill me-1"></i> Best Pick</span>' : ""}
        </div>
        <div class="score-bar-bg">
          <div class="score-bar-fill" style="width:${s.score}%;background:${SC.scoreBarColor(s.score)}"></div>
        </div>
      </div>
    `).join("");
  }

  // ── Risk Items ────────────────────────────────────────────────
  function renderRiskItems(risks) {
    if (!riskItemsList) return;
    riskItemsList.innerHTML = risks.map(r => `
      <div class="risk-item ${r.severity || 'MEDIUM'}">
        <span class="risk-badge ${r.severity || 'MEDIUM'}">${r.severity || 'MEDIUM'}</span>
        <span class="risk-text">${escHtml(r.item || "")}</span>
      </div>
    `).join("");
  }

  // ── Score Chart ───────────────────────────────────────────────
  function updateScoreChart(scores) {
    if (!scoreBarCanvas) return;
    const ctx = scoreBarCanvas.getContext("2d");
    if (scoreChart) scoreChart.destroy();

    const isDark = document.documentElement.getAttribute("data-bs-theme") === "dark";
    const textColor = isDark ? "#94a3b8" : "#64748b";
    const gridColor = isDark ? "#2d3748" : "#e2e8f0";

    scoreChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: scores.map(s => SC.truncate(s.name, 14)),
        datasets: [{
          label: "Decision Score",
          data: scores.map(s => s.score),
          backgroundColor: scores.map(s => SC.scoreBarColor(s.score) + "cc"),
          borderColor: scores.map(s => SC.scoreBarColor(s.score)),
          borderWidth: 1.5,
          borderRadius: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx => ` Score: ${ctx.parsed.y}/100`
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true, max: 100,
            ticks: { color: textColor, stepSize: 20 },
            grid: { color: gridColor },
          },
          x: {
            ticks: { color: textColor, font: { size: 11 } },
            grid: { display: false },
          },
        },
      },
    });
  }

  // ── Update Analysis Panel from saved result ───────────────────
  function updateAnalysisPanel(result) {
    if (result?.scores) {
      const scores = Object.entries(result.scores).map(([name, score]) => ({ name, score }));
      renderScoreCardsFull(scores);
      renderScoreCardsMini(scores);
      updateScoreChart(scores);
    }
    if (result?.risks?.length) {
      renderRiskItems(result.risks);
    }
    if (result?.matrix && Object.keys(result.matrix).length) {
      renderMatrix(result.matrix);
    }
  }

  // ── Comparison Matrix ─────────────────────────────────────────
  function renderMatrix(matrixData) {
    if (!compMatrix || !matrixData.options?.length) return;
    if (panelMatrix) panelMatrix.style.display = "block";

    const { options, criteria, matrix, winner_per_criterion } = matrixData;

    let html = `<table class="matrix-table"><thead><tr>
      <th>Criterion</th>
      ${options.map(o => `<th>${escHtml(SC.truncate(o, 18))}</th>`).join("")}
    </tr></thead><tbody>`;

    (criteria || []).forEach(crit => {
      html += `<tr><td style="font-weight:600;font-size:0.78rem">${escHtml(crit.replace(/_/g," "))}</td>`;
      options.forEach(opt => {
        const cell = matrix[opt]?.[crit] || {};
        const isWinner = winner_per_criterion?.[crit] === opt;
        html += `<td class="${isWinner ? "winner-cell" : ""}">
          <div class="matrix-bar-cell">
            <span style="font-size:0.78rem;font-weight:${isWinner?700:400}">${cell.normalized?.toFixed(0) ?? "—"}%</span>
            <div class="matrix-bar-bg">
              <div class="matrix-bar-fill" style="width:${cell.normalized ?? 50}%"></div>
            </div>
          </div>
        </td>`;
      });
      html += "</tr>";
    });

    html += "</tbody></table>";
    compMatrix.innerHTML = html;
  }

  // ── PDF Download ──────────────────────────────────────────────
  function downloadPDF() {
    const sid = pdfBtn?.dataset.sessionId || activeSessionId;
    if (!sid) {
      SC.Toast.show("No active session to export.", "warning");
      return;
    }
    window.open(`/api/reports/${sid}/pdf`, "_blank");
  }

  // ── Utilities ─────────────────────────────────────────────────
  function scrollBottom() {
    setTimeout(() => {
      if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 50);
  }

  function escHtml(str) {
    const div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
  }

  return { init, newSession };
})();

document.addEventListener("DOMContentLoaded", () => Chat.init());
