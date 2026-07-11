/* ============================================================
   SmartChoice AI — main.js
   Theme management, global utilities, toast notifications
   ============================================================ */
"use strict";

// ── Theme Manager ────────────────────────────────────────────
const ThemeManager = (() => {
  const HTML = document.documentElement;
  const BTN  = document.getElementById("themeToggleBtn");
  const ICON = document.getElementById("themeIcon");
  const KEY  = "sc_theme";

  const THEMES = {
    dark:  { icon: "bi-moon-fill",  label: "Switch to light mode" },
    light: { icon: "bi-sun-fill",   label: "Switch to dark mode"  },
  };

  function apply(theme) {
    HTML.setAttribute("data-bs-theme", theme);
    localStorage.setItem(KEY, theme);
    if (ICON) {
      ICON.className = `bi ${THEMES[theme].icon}`;
    }
    if (BTN) BTN.title = THEMES[theme].label;
  }

  function init() {
    const saved = localStorage.getItem(KEY) || "dark";
    apply(saved);
    BTN?.addEventListener("click", () => {
      const current = HTML.getAttribute("data-bs-theme") || "dark";
      apply(current === "dark" ? "light" : "dark");
    });
  }

  return { init, apply };
})();

// ── Toast Notifications ──────────────────────────────────────
const Toast = (() => {
  const container = document.getElementById("toastContainer");

  function show(message, type = "info", duration = 4000) {
    if (!container) return;
    const colors = {
      success: "#10b981",
      error:   "#ef4444",
      warning: "#f59e0b",
      info:    "#3b82f6",
    };
    const icons = {
      success: "bi-check-circle-fill",
      error:   "bi-x-circle-fill",
      warning: "bi-exclamation-triangle-fill",
      info:    "bi-info-circle-fill",
    };
    const id = `toast-${Date.now()}`;
    const el = document.createElement("div");
    el.id = id;
    el.className = "toast sc-toast show";
    el.setAttribute("role", "alert");
    el.innerHTML = `
      <div class="toast-header">
        <i class="bi ${icons[type] || icons.info} me-2" style="color:${colors[type]}"></i>
        <strong class="me-auto" style="color:${colors[type]}">SmartChoice AI</strong>
        <button type="button" class="btn-close btn-close-sm" data-bs-dismiss="toast"></button>
      </div>
      <div class="toast-body">${message}</div>
    `;
    container.appendChild(el);
    el.querySelector("[data-bs-dismiss]")?.addEventListener("click", () => el.remove());
    setTimeout(() => el.remove(), duration);
  }

  return { show };
})();

// ── AI Status Badge ──────────────────────────────────────────
const AIStatus = {
  badge: document.getElementById("aiStatusBadge"),
  text:  document.querySelector("#aiStatusBadge .status-text"),

  set(state, label) {
    if (!this.badge) return;
    this.badge.className = `ai-status-badge ${state}`;
    if (this.text) this.text.textContent = label;
  },
  ready()   { this.set("",       "AI Ready"); },
  loading() { this.set("loading","Analyzing…"); },
  error()   { this.set("error",  "AI Error"); },
};

// ── Utility: format date ─────────────────────────────────────
function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) +
         " " + d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

// ── Utility: truncate text ───────────────────────────────────
function truncate(str, len = 60) {
  return str?.length > len ? str.slice(0, len) + "…" : (str || "");
}

// ── Utility: domain label ────────────────────────────────────
const DOMAIN_LABELS = {
  education: "🎓 Education",
  career:    "💼 Career",
  investment:"📈 Investment",
  technology:"💻 Technology",
  banking:   "💳 Banking",
  insurance: "🛡️ Insurance",
  business:  "🏢 Business",
  daily_life:"🏠 Daily Life",
  general:   "🔍 General",
};
function domainLabel(d) { return DOMAIN_LABELS[d] || d; }

// ── Utility: score color class ───────────────────────────────
function scoreClass(v) {
  if (v >= 70) return "score-high";
  if (v >= 45) return "score-mid";
  return "score-low";
}

// ── Utility: score bar gradient ──────────────────────────────
function scoreBarColor(v) {
  if (v >= 70) return "#10b981";
  if (v >= 45) return "#f59e0b";
  return "#ef4444";
}

// ── Server Health Check ──────────────────────────────────────
async function checkServerHealth() {
  try {
    const res  = await fetch("/api/health", { cache: "no-store" });
    const data = await res.json();

    if (!data.ready) {
      // Server is up but IBM credentials are missing
      AIStatus.set("error", "No IBM Key");
      const msg = [
        !data.ibm_api_key_set    && "IBM_API_KEY missing",
        !data.ibm_project_id_set && "IBM_PROJECT_ID missing",
      ].filter(Boolean).join(" · ");
      Toast.show(
        `⚠️ IBM credentials not set in <code>.env</code> — ${msg}. ` +
        "Open <code>SmartChoice_AI/.env</code> and add your keys, then restart Flask.",
        "warning",
        10000
      );
    } else {
      AIStatus.ready();
    }
  } catch (e) {
    // fetch itself threw — server is completely unreachable
    AIStatus.set("error", "Server Down");
    Toast.show(
      "⚠️ Flask server is not running. " +
      "Open a terminal in the <code>SmartChoice_AI</code> folder and run: " +
      "<code>python run.py</code> — then refresh this page.",
      "error",
      12000
    );
  }
}

// ── Initialize ───────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  ThemeManager.init();
  checkServerHealth();
});

// ── Export globals ───────────────────────────────────────────
window.SC = { Toast, AIStatus, fmtDate, truncate, domainLabel, scoreClass, scoreBarColor };
