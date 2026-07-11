(function attachChangeAuditFeedback(root, factory) {
  "use strict";
  const api = factory();
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
  if (root) {
    root.ChangeAuditFeedback = api;
    if (root.document) {
      api.init(root.document, root);
    }
  }
})(typeof window !== "undefined" ? window : null, function createChangeAuditFeedback() {
  "use strict";

  const PREFIX = "change-audit.feedback.v1";
  const SEVERITIES = new Set(["high", "medium", "low", "note"]);

  function storageKey(identity) {
    return [PREFIX, identity.graph_id, identity.run_id, identity.fingerprint]
      .map((value) => encodeURIComponent(String(value)))
      .join(":");
  }

  function defaultState(identity) {
    return {
      graph_id: identity.graph_id,
      run_id: identity.run_id,
      target_type: "finding",
      target_id: identity.target_id,
      fingerprint: identity.fingerprint,
      disposition: null,
      comment: "",
      severity_override: null,
      timestamps: {},
      updated_at: null,
    };
  }

  function matchesIdentity(state, identity) {
    return state
      && state.graph_id === identity.graph_id
      && state.run_id === identity.run_id
      && state.target_id === identity.target_id
      && state.fingerprint === identity.fingerprint;
  }

  function validState(state, identity) {
    if (!matchesIdentity(state, identity) || state.target_type !== "finding") return false;
    if (![null, "accept", "false_positive"].includes(state.disposition)) return false;
    if (typeof state.comment !== "string") return false;
    if (state.severity_override !== null && !SEVERITIES.has(state.severity_override)) return false;
    if (!state.timestamps || typeof state.timestamps !== "object") return false;
    if (state.disposition && typeof state.timestamps.disposition !== "string") return false;
    if (state.comment && typeof state.timestamps.comment !== "string") return false;
    if (state.severity_override && typeof state.timestamps.severity_override !== "string") return false;
    return true;
  }

  function loadState(storage, identity) {
    try {
      const raw = storage.getItem(storageKey(identity));
      if (!raw) return defaultState(identity);
      const state = JSON.parse(raw);
      return validState(state, identity) ? state : defaultState(identity);
    } catch (_error) {
      return defaultState(identity);
    }
  }

  function saveState(storage, state) {
    storage.setItem(storageKey(state), JSON.stringify(state));
    return state;
  }

  function applyAction(state, action, value, now) {
    const next = JSON.parse(JSON.stringify(state));
    const timestamp = now || new Date().toISOString();
    if (action === "accept" || action === "false_positive") {
      next.disposition = action;
      next.timestamps.disposition = timestamp;
    } else if (action === "comment") {
      next.comment = String(value || "").trim();
      if (next.comment) next.timestamps.comment = timestamp;
      else delete next.timestamps.comment;
    } else if (action === "severity_override") {
      const severity = String(value || "");
      if (severity && !SEVERITIES.has(severity)) {
        throw new Error("invalid severity override");
      }
      next.severity_override = severity || null;
      if (next.severity_override) next.timestamps.severity_override = timestamp;
      else delete next.timestamps.severity_override;
    } else {
      throw new Error("unknown feedback action");
    }
    next.updated_at = timestamp;
    return next;
  }

  function baseEvent(state, action, createdAt) {
    return {
      target_type: "finding",
      target_id: state.target_id,
      action,
      fingerprint: state.fingerprint,
      graph_id: state.graph_id,
      run_id: state.run_id,
      created_at: createdAt,
    };
  }

  function stateToEvents(state) {
    const events = [];
    if (state.disposition) {
      events.push(baseEvent(state, state.disposition, state.timestamps.disposition));
    }
    if (state.comment) {
      events.push({
        ...baseEvent(state, "comment", state.timestamps.comment),
        comment: state.comment,
      });
    }
    if (state.severity_override) {
      events.push({
        ...baseEvent(state, "severity_override", state.timestamps.severity_override),
        severity: state.severity_override,
      });
    }
    return events;
  }

  function exportJsonl(states) {
    const lines = states.flatMap(stateToEvents).map((event) => JSON.stringify(event));
    return lines.length ? `${lines.join("\n")}\n` : "";
  }

  function memoryStorage() {
    const values = new Map();
    return {
      getItem(key) { return values.has(key) ? values.get(key) : null; },
      setItem(key, value) { values.set(key, String(value)); },
    };
  }

  function renderState(panel, state, syncInputs) {
    panel.querySelectorAll("[data-feedback-action='accept'], [data-feedback-action='false_positive']")
      .forEach((button) => {
        button.setAttribute("aria-pressed", String(button.dataset.feedbackAction === state.disposition));
      });
    const badge = panel.querySelector("[data-feedback-state]");
    const displayState = state.disposition
      || (state.comment || state.severity_override ? "edited" : "pending");
    badge.textContent = {
      accept: "已接受",
      false_positive: "已标记误报",
      edited: "已编辑",
      pending: "待决策",
    }[displayState];
    if (syncInputs) {
      panel.querySelector("[data-feedback-comment]").value = state.comment || "";
      panel.querySelector("[data-feedback-severity]").value = state.severity_override || "";
    }
  }

  function init(documentObject, rootObject) {
    const shell = documentObject.querySelector("[data-graph-id][data-run-id]");
    if (!shell) return;
    let storage;
    try {
      storage = rootObject.localStorage;
      const probe = `${PREFIX}:probe`;
      storage.setItem(probe, "1");
      storage.removeItem(probe);
    } catch (_error) {
      storage = memoryStorage();
    }

    const panels = Array.from(documentObject.querySelectorAll("[data-feedback-for][data-fingerprint]"));
    const entries = panels.map((panel) => {
      const identity = {
        graph_id: shell.dataset.graphId,
        run_id: shell.dataset.runId,
        target_id: panel.dataset.feedbackFor,
        fingerprint: panel.dataset.fingerprint,
      };
      let state = loadState(storage, identity);
      renderState(panel, state, true);
      const message = panel.querySelector("[data-feedback-message]");

      panel.querySelectorAll("[data-feedback-action]").forEach((button) => {
        button.addEventListener("click", () => {
          const action = button.dataset.feedbackAction;
          const value = action === "comment"
            ? panel.querySelector("[data-feedback-comment]").value
            : null;
          state = applyAction(state, action, value);
          try { saveState(storage, state); } catch (_error) { /* in-memory state remains usable */ }
          renderState(panel, state, false);
          message.textContent = action === "comment" && !state.comment ? "评论已移除" : "决策已保存在当前浏览器";
        });
      });
      panel.querySelector("[data-feedback-severity]").addEventListener("change", (event) => {
        state = applyAction(state, "severity_override", event.target.value);
        try { saveState(storage, state); } catch (_error) { /* in-memory state remains usable */ }
        renderState(panel, state, false);
        message.textContent = state.severity_override ? "严重度调整已保存" : "已恢复原严重度";
      });
      return { getState: () => state };
    });

    const exportButton = documentObject.querySelector("[data-feedback-export]");
    const exportStatus = documentObject.querySelector("[data-feedback-export-status]");
    if (exportButton && exportStatus) {
      exportButton.addEventListener("click", () => {
        const jsonl = exportJsonl(entries.map((entry) => entry.getState()));
        if (!jsonl) {
          exportStatus.textContent = "暂无可导出的决策";
          return;
        }
        const blob = new rootObject.Blob([jsonl], { type: "application/x-ndjson;charset=utf-8" });
        const url = rootObject.URL.createObjectURL(blob);
        const link = documentObject.createElement("a");
        link.href = url;
        link.download = "audit-feedback.jsonl";
        documentObject.body.appendChild(link);
        link.click();
        link.remove();
        rootObject.URL.revokeObjectURL(url);
        exportStatus.textContent = `已导出 ${jsonl.trimEnd().split("\n").length} 条决策`;
      });
    }
    documentObject.documentElement.dataset.changeAuditReady = "true";
  }

  return {
    PREFIX,
    applyAction,
    defaultState,
    exportJsonl,
    init,
    loadState,
    memoryStorage,
    saveState,
    stateToEvents,
    storageKey,
    validState,
  };
});
