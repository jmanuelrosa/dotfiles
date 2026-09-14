import { readFileSync, writeFileSync, renameSync } from "node:fs";

const [phase, kind] = process.argv.slice(2);
const { target, candidate } = JSON.parse(readFileSync(new URL("./minion-policy-case.json", import.meta.url), "utf8"));
const paths = {
  "global-sandbox": "../agent/sandbox.json",
  "global-permission": "../agent/extensions/pi-permission-system/config.json",
  "project-sandbox": "./.pi/sandbox.json",
  "absent-project-sandbox": "./.pi/sandbox.json",
};
const destination = new URL(phase === "control" ? "./ordinary.json" : paths[target], import.meta.url);
const record = new URL(`./${phase}.child.json`, import.meta.url);
const evidence = { phase, kind, destination: destination.pathname, reached: true, completed: false, code: null, syscall: null };
const replacement = new URL(`./${phase}.replacement.json`, import.meta.url);
if (kind === "shell-replace") writeFileSync(replacement, candidate);
writeFileSync(record, JSON.stringify(evidence));
try {
  if (kind === "shell-write") writeFileSync(destination, candidate);
  else renameSync(replacement, destination);
  evidence.completed = true;
} catch (error) {
  evidence.code = error.code;
  evidence.syscall = error.syscall;
  evidence.error = String(error);
  process.exitCode = 1;
}
writeFileSync(record, JSON.stringify(evidence));
process.stdout.write(JSON.stringify(evidence));
