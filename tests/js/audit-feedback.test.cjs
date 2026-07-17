"use strict";

const assert = require("node:assert/strict");
const feedback = require("../../evidentloop/renderers/static/audit.js");

assert.equal(feedback.PREFIX, "evidentloop.feedback.v2");

const identity = {
  graph_id: "audit:graph/一",
  run_id: "run-001",
  target_id: "finding-001",
  fingerprint: "sha256:" + "a".repeat(64),
};
const otherRun = { ...identity, run_id: "run-002" };
const otherGraph = { ...identity, graph_id: "audit:other" };
const otherFingerprint = { ...identity, fingerprint: "sha256:" + "b".repeat(64) };
const sourceHash = "sha256:" + "c".repeat(64);

assert.notEqual(feedback.storageKey(identity), feedback.storageKey(otherRun));
assert.notEqual(feedback.storageKey(identity), feedback.storageKey(otherGraph));
assert.notEqual(feedback.storageKey(identity), feedback.storageKey(otherFingerprint));

const storage = feedback.memoryStorage();
let state = feedback.defaultState(identity);
state = feedback.applyAction(state, "accept", null, "2026-07-10T00:00:00Z");
feedback.saveState(storage, state);
assert.deepEqual(feedback.loadState(storage, identity), state);
assert.equal(feedback.loadState(storage, otherRun).disposition, null);

state = feedback.applyAction(state, "accept", null, "2026-07-10T00:01:00Z");
assert.equal(feedback.stateToEvents(state, sourceHash).filter((event) => event.action === "accept").length, 1);
assert.equal(feedback.stateToEvents(state, sourceHash)[0].created_at, "2026-07-10T00:01:00Z");

state = feedback.applyAction(state, "false_positive", null, "2026-07-10T00:02:00Z");
assert.equal(state.disposition, "false_positive");
assert.equal(feedback.stateToEvents(state, sourceHash).some((event) => event.action === "accept"), false);

const special = '特殊字符 <>& \\" quote\n第二行';
state = feedback.applyAction(state, "comment", special, "2026-07-10T00:03:00Z");
state = feedback.applyAction(state, "severity_override", "medium", "2026-07-10T00:04:00Z");
const jsonl = feedback.exportJsonl([state], sourceHash);
const events = jsonl.trimEnd().split("\n").map((line) => JSON.parse(line));
assert.equal(events.length, 3);
assert.equal(events.every((event) => event.source_audit_sha256 === sourceHash), true);
assert.equal(events.find((event) => event.action === "comment").comment, special);
assert.equal(events.find((event) => event.action === "severity_override").severity, "medium");

state = feedback.applyAction(state, "comment", "   ", "2026-07-10T00:05:00Z");
assert.equal(state.comment, null);
assert.equal(feedback.stateToEvents(state, sourceHash).find((event) => event.action === "comment").comment, null);

state = feedback.applyAction(state, "severity_override", "", "2026-07-10T00:06:00Z");
assert.equal(state.severity_override, null);
assert.equal(feedback.stateToEvents(state, sourceHash).find((event) => event.action === "severity_override").severity, null);
assert.throws(() => feedback.applyAction(state, "severity_override", "critical"));

let delta = feedback.defaultState(identity);
delta = feedback.applyPendingChange(delta, "false_positive", null, "false_positive", "2026-07-10T00:07:00Z");
assert.deepEqual(feedback.stateToEvents(delta, sourceHash), []);
delta = feedback.applyPendingChange(delta, "comment", "", "已有评论", "2026-07-10T00:08:00Z");
assert.equal(feedback.stateToEvents(delta, sourceHash)[0].comment, null);
delta = feedback.applyPendingChange(delta, "comment", "已有评论", "已有评论", "2026-07-10T00:09:00Z");
assert.deepEqual(feedback.stateToEvents(delta, sourceHash), []);
delta = feedback.applyPendingChange(delta, "severity_override", "", "low", "2026-07-10T00:10:00Z");
assert.equal(feedback.stateToEvents(delta, sourceHash)[0].severity, null);
delta = feedback.applyPendingChange(delta, "severity_override", "low", "low", "2026-07-10T00:11:00Z");
assert.deepEqual(feedback.stateToEvents(delta, sourceHash), []);

let copyState = feedback.defaultState(identity);
copyState = feedback.applyAction(copyState, "accept", null, "2026-07-10T00:12:00Z");
const copyText = feedback.buildCopyText([copyState], sourceHash);
assert.equal(copyText.startsWith("请使用 EvidentLoop"), true);
assert.equal(copyText.includes(feedback.MACHINE_BLOCK_BEGIN), true);
assert.equal(copyText.endsWith(feedback.MACHINE_BLOCK_END), true);
assert.equal(copyText.includes(sourceHash), true);
assert.equal(copyText.includes("/Users/"), false);

storage.setItem(feedback.storageKey(identity), "{not json");
assert.equal(feedback.loadState(storage, identity).disposition, null);
storage.setItem(feedback.storageKey(identity), JSON.stringify({ ...state, disposition: "accept", timestamps: {} }));
assert.equal(feedback.loadState(storage, identity).disposition, null);
assert.equal(feedback.exportJsonl([], sourceHash), "");

console.log("audit feedback behavior: PASS");
