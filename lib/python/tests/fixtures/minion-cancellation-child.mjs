import { appendFileSync, existsSync, renameSync, writeFileSync } from "node:fs";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const [role, mode, deadlineText, pollText] = process.argv.slice(2);
const deadline = Number(deadlineText);
const pollMs = Number(pollText);
const directory = new URL(`./${mode}/`, import.meta.url);
const record = (name, value) => {
  const target = new URL(name, directory);
  const temporary = new URL(`${name}.tmp`, directory);
  writeFileSync(temporary, JSON.stringify(value));
  renameSync(temporary, target);
};
const finish = reason => {
  record(`${role}.exit.json`, { pid: process.pid, reason, at: Date.now() });
  process.exit(0);
};
const finishAtDeadline = () => {
  const remaining = deadline - Date.now();
  if (remaining > 0) {
    setTimeout(finishAtDeadline, remaining);
    return;
  }
  finish("deadline");
};
setTimeout(finishAtDeadline, Math.max(0, deadline - Date.now()));
if (existsSync(new URL("cleanup", directory))) finish("probe-cleanup");
if (role === "launcher") {
  const child = spawn(process.execPath, [fileURLToPath(import.meta.url), "writer", mode, deadlineText, pollText], {
    detached: mode === "detached-group", stdio: "ignore",
  });
  child.unref();
}
if (role === "writer") appendFileSync(new URL("writes.txt", directory), `${Date.now()}\n`);
record(`${role}.ready.json`, { pid: process.pid, ppid: process.ppid, at: Date.now(), deadline });
setInterval(() => {
  if (existsSync(new URL("cleanup", directory))) finish("probe-cleanup");
  if (role === "writer") appendFileSync(new URL("writes.txt", directory), `${Date.now()}\n`);
}, pollMs);
