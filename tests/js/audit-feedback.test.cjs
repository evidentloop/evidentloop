"use strict";

const assert = require("node:assert/strict");
const feedback = require("../../change_audit/renderers/static/audit.js");

const identity = {
  graph_id: "audit:graph/一",
  run_id: "run-001",
  target_id: "finding-001",
  fingerprint: "sha256:" + "a".repeat(64),
};
const otherRun = { ...identity, run_id: "run-002" };
const otherGraph = { ...identity, graph_id: "audit:other" };
const otherFingerprint = { ...identity, fingerprint: "sha256:" + "b".repeat(64) };

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
assert.equal(feedback.stateToEvents(state).filter((event) => event.action === "accept").length, 1);
assert.equal(feedback.stateToEvents(state)[0].created_at, "2026-07-10T00:01:00Z");

state = feedback.applyAction(state, "false_positive", null, "2026-07-10T00:02:00Z");
assert.equal(state.disposition, "false_positive");
assert.equal(feedback.stateToEvents(state).some((event) => event.action === "accept"), false);

const special = '特殊字符 <>& \\" quote\n第二行';
state = feedback.applyAction(state, "comment", special, "2026-07-10T00:03:00Z");
state = feedback.applyAction(state, "severity_override", "medium", "2026-07-10T00:04:00Z");
const jsonl = feedback.exportJsonl([state]);
const events = jsonl.trimEnd().split("\n").map((line) => JSON.parse(line));
assert.equal(events.length, 3);
assert.equal(events.find((event) => event.action === "comment").comment, special);
assert.equal(events.find((event) => event.action === "severity_override").severity, "medium");

state = feedback.applyAction(state, "comment", "   ", "2026-07-10T00:05:00Z");
assert.equal(state.comment, "");
assert.equal(feedback.stateToEvents(state).some((event) => event.action === "comment"), false);

state = feedback.applyAction(state, "severity_override", "", "2026-07-10T00:06:00Z");
assert.equal(state.severity_override, null);
assert.throws(() => feedback.applyAction(state, "severity_override", "critical"));

storage.setItem(feedback.storageKey(identity), "{not json");
assert.equal(feedback.loadState(storage, identity).disposition, null);
storage.setItem(feedback.storageKey(identity), JSON.stringify({ ...state, disposition: "accept", timestamps: {} }));
assert.equal(feedback.loadState(storage, identity).disposition, null);
assert.equal(feedback.exportJsonl([]), "");

console.log("audit feedback behavior: PASS");
