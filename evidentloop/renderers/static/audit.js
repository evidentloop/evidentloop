(function attachEvidentLoopFeedback(root, factory) {
  "use strict";
  const api = factory();
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
  if (root) {
    root.EvidentLoopFeedback = api;
    if (root.document) {
      api.init(root.document, root);
    }
  }
})(typeof window !== "undefined" ? window : null, function createEvidentLoopFeedback() {
  "use strict";

  const PREFIX = "evidentloop.feedback.v2";
  const SEVERITIES = new Set(["high", "medium", "low", "note"]);
  const MACHINE_BLOCK_BEGIN = "<<<EVIDENTLOOP_FEEDBACK_JSONL>>>";
  const MACHINE_BLOCK_END = "<<<END_EVIDENTLOOP_FEEDBACK_JSONL>>>";
  const COPY_INSTRUCTION = "请使用 EvidentLoop 按以下裁定更新当前报告；不要修改业务代码，也不要重新审查代码。";

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
      comment: null,
      comment_changed: false,
      severity_override: null,
      severity_changed: false,
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
    if (state.comment !== null && typeof state.comment !== "string") return false;
    if (typeof state.comment_changed !== "boolean") return false;
    if (state.severity_override !== null && !SEVERITIES.has(state.severity_override)) return false;
    if (typeof state.severity_changed !== "boolean") return false;
    if (!state.timestamps || typeof state.timestamps !== "object") return false;
    if (state.disposition && typeof state.timestamps.disposition !== "string") return false;
    if (state.comment_changed && typeof state.timestamps.comment !== "string") return false;
    if (state.severity_changed && typeof state.timestamps.severity_override !== "string") return false;
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
      next.comment = String(value || "").trim() || null;
      next.comment_changed = true;
      next.timestamps.comment = timestamp;
    } else if (action === "severity_override") {
      const severity = String(value || "");
      if (severity && !SEVERITIES.has(severity)) {
        throw new Error("invalid severity override");
      }
      next.severity_override = severity || null;
      next.severity_changed = true;
      next.timestamps.severity_override = timestamp;
    } else {
      throw new Error("unknown feedback action");
    }
    next.updated_at = timestamp;
    return next;
  }

  function clearPending(state, field) {
    const next = JSON.parse(JSON.stringify(state));
    if (field === "disposition") {
      next.disposition = null;
      delete next.timestamps.disposition;
    } else if (field === "comment") {
      next.comment = null;
      next.comment_changed = false;
      delete next.timestamps.comment;
    } else if (field === "severity_override") {
      next.severity_override = null;
      next.severity_changed = false;
      delete next.timestamps.severity_override;
    } else {
      throw new Error("unknown pending field");
    }
    next.updated_at = new Date().toISOString();
    return next;
  }

  function applyPendingChange(state, action, value, appliedValue, now) {
    if ((action === "accept" || action === "false_positive") && action === appliedValue) {
      return clearPending(state, "disposition");
    }
    if (action === "comment" && String(value || "").trim() === (appliedValue || "")) {
      return clearPending(state, "comment");
    }
    if (action === "severity_override" && String(value || "") === (appliedValue || "")) {
      return clearPending(state, "severity_override");
    }
    return applyAction(state, action, value, now);
  }

  function baseEvent(state, action, createdAt, sourceAuditSha256) {
    return {
      target_type: "finding",
      target_id: state.target_id,
      action,
      fingerprint: state.fingerprint,
      graph_id: state.graph_id,
      run_id: state.run_id,
      created_at: createdAt,
      source_audit_sha256: sourceAuditSha256,
    };
  }

  function stateToEvents(state, sourceAuditSha256) {
    const events = [];
    if (state.disposition) {
      events.push(baseEvent(state, state.disposition, state.timestamps.disposition, sourceAuditSha256));
    }
    if (state.comment_changed) {
      events.push({
        ...baseEvent(state, "comment", state.timestamps.comment, sourceAuditSha256),
        comment: state.comment,
      });
    }
    if (state.severity_changed) {
      events.push({
        ...baseEvent(state, "severity_override", state.timestamps.severity_override, sourceAuditSha256),
        severity: state.severity_override,
      });
    }
    return events;
  }

  function exportJsonl(states, sourceAuditSha256) {
    const lines = states
      .flatMap((state) => stateToEvents(state, sourceAuditSha256))
      .map((event) => JSON.stringify(event));
    return lines.length ? `${lines.join("\n")}\n` : "";
  }

  function buildCopyText(states, sourceAuditSha256) {
    const jsonl = exportJsonl(states, sourceAuditSha256);
    if (!jsonl) return "";
    return `${COPY_INSTRUCTION}\n\n${MACHINE_BLOCK_BEGIN}\n${jsonl}${MACHINE_BLOCK_END}`;
  }

  function feedbackCounts(states, sourceAuditSha256) {
    const events = states.flatMap((state) => stateToEvents(state, sourceAuditSha256));
    return {
      decisions: events.filter((event) => event.action !== "comment").length,
      comments: events.filter((event) => event.action === "comment").length,
      total: events.length,
    };
  }

  function memoryStorage() {
    const values = new Map();
    return {
      getItem(key) { return values.has(key) ? values.get(key) : null; },
      setItem(key, value) { values.set(key, String(value)); },
      removeItem(key) { values.delete(key); },
    };
  }

  function appliedState(panel) {
    return {
      disposition: panel.dataset.appliedDisposition || null,
      comment: panel.dataset.appliedComment || null,
      severity_override: panel.dataset.appliedSeverity || null,
    };
  }

  function renderState(panel, state, applied, syncInputs) {
    const disposition = state.disposition || applied.disposition;
    panel.querySelectorAll("[data-feedback-action='accept'], [data-feedback-action='false_positive']")
      .forEach((button) => {
        button.setAttribute("aria-pressed", String(button.dataset.feedbackAction === disposition));
      });
    const badge = panel.querySelector("[data-feedback-state]");
    const hasPending = state.disposition || state.comment_changed || state.severity_changed;
    const hasApplied = applied.disposition || applied.comment || applied.severity_override;
    badge.textContent = hasPending ? "有待更新裁定" : hasApplied ? "已应用" : "待决策";
    if (syncInputs) {
      panel.querySelector("[data-feedback-comment]").value = state.comment_changed
        ? state.comment || ""
        : applied.comment || "";
      panel.querySelector("[data-feedback-severity]").value = state.severity_changed
        ? state.severity_override || ""
        : applied.severity_override || "";
    }
  }

  async function copyText(documentObject, rootObject, value) {
    if (
      rootObject.navigator
      && rootObject.navigator.clipboard
      && typeof rootObject.navigator.clipboard.writeText === "function"
    ) {
      await rootObject.navigator.clipboard.writeText(value);
      return;
    }
    const textarea = documentObject.createElement("textarea");
    textarea.value = value;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    documentObject.body.appendChild(textarea);
    textarea.select();
    const copied = documentObject.execCommand && documentObject.execCommand("copy");
    textarea.remove();
    if (!copied) throw new Error("clipboard unavailable");
  }

  function init(documentObject, rootObject) {
    const shell = documentObject.querySelector("[data-graph-id][data-run-id]");
    if (!shell) return;
    let storage;
    let persistentStorage = true;
    try {
      storage = rootObject.localStorage;
      const probe = `${PREFIX}:probe`;
      storage.setItem(probe, "1");
      storage.removeItem(probe);
    } catch (_error) {
      storage = memoryStorage();
      persistentStorage = false;
    }

    const sourceAuditSha256 = shell.dataset.auditSha256;
    const storageStatus = documentObject.querySelector("[data-feedback-storage-status]");
    if (storageStatus && !persistentStorage) {
      storageStatus.textContent = "仅临时保存，刷新会丢失";
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
      const applied = appliedState(panel);
      renderState(panel, state, applied, true);
      const message = panel.querySelector("[data-feedback-message]");

      panel.querySelectorAll("[data-feedback-action]").forEach((button) => {
        button.addEventListener("click", () => {
          const action = button.dataset.feedbackAction;
          const value = action === "comment"
            ? panel.querySelector("[data-feedback-comment]").value
            : null;
          const appliedValue = action === "comment"
            ? applied.comment
            : applied.disposition;
          state = applyPendingChange(state, action, value, appliedValue);
          try { saveState(storage, state); } catch (_error) { /* in-memory state remains usable */ }
          renderState(panel, state, applied, false);
          message.textContent = action === "comment" && state.comment_changed && !state.comment
            ? "待移除当前评论"
            : "待更新裁定已保存在当前浏览器";
          updateToolbar();
        });
      });
      panel.querySelector("[data-feedback-severity]").addEventListener("change", (event) => {
        state = applyPendingChange(
          state,
          "severity_override",
          event.target.value,
          applied.severity_override,
        );
        try { saveState(storage, state); } catch (_error) { /* in-memory state remains usable */ }
        renderState(panel, state, applied, false);
        message.textContent = state.severity_changed ? "严重度变化待更新" : "已恢复当前报告值";
        updateToolbar();
      });
      return { getState: () => state };
    });

    const exportButton = documentObject.querySelector("[data-feedback-export]");
    const copyButton = documentObject.querySelector("[data-feedback-copy]");
    const exportStatus = documentObject.querySelector("[data-feedback-export-status]");
    const summary = documentObject.querySelector("[data-feedback-summary]");
    function currentStates() {
      return entries.map((entry) => entry.getState());
    }
    function updateToolbar() {
      if (!summary) return;
      const counts = feedbackCounts(currentStates(), sourceAuditSha256);
      summary.textContent = `${counts.decisions} 项决策 · ${counts.comments} 条评论 · 不自动上传`;
    }
    if (copyButton && exportStatus) {
      copyButton.addEventListener("click", async () => {
        const text = buildCopyText(currentStates(), sourceAuditSha256);
        if (!text) {
          exportStatus.textContent = "暂无待更新裁定";
          return;
        }
        try {
          await copyText(documentObject, rootObject, text);
          exportStatus.textContent = "已复制，请粘贴给 AI 更新报告";
        } catch (_error) {
          exportStatus.textContent = "复制失败，请改用下载 JSONL";
        }
      });
    }
    if (exportButton && exportStatus) {
      exportButton.addEventListener("click", () => {
        const jsonl = exportJsonl(currentStates(), sourceAuditSha256);
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
        exportStatus.textContent = `已下载 ${jsonl.trimEnd().split("\n").length} 条反馈`;
      });
    }
    updateToolbar();
    documentObject.documentElement.dataset.evidentloopReady = "true";
  }

  return {
    PREFIX,
    MACHINE_BLOCK_BEGIN,
    MACHINE_BLOCK_END,
    applyAction,
    applyPendingChange,
    buildCopyText,
    clearPending,
    defaultState,
    exportJsonl,
    feedbackCounts,
    init,
    loadState,
    memoryStorage,
    saveState,
    stateToEvents,
    storageKey,
    validState,
  };
});
