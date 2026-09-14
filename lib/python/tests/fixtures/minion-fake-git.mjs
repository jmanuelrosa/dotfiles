#!/usr/bin/env node

import { existsSync, lstatSync, readFileSync, readdirSync, readlinkSync, writeFileSync } from "node:fs";
import { join, relative } from "node:path";

const args = process.argv.slice(2);
const cwd = args[0] === "-C" ? args[1] : process.cwd();
const command = args[0] === "-C" ? args.slice(2) : args;

const HEAD = "0000000000000000000000000000000000000001";

function statePath(root) {
  return join(root, ".git", "minion-fake-state.json");
}

function readState(root) {
  const path = statePath(root);
  if (existsSync(path)) {
    const state = JSON.parse(readFileSync(path, "utf8"));
    if (!state.committedManifest) {
      state.committedManifest = manifest(root);
      writeState(root, state);
    }
    return state;
  }
  const branch = process.env.MINION_FAKE_GIT_BRANCH ?? "main";
  const initial = { branch, head: HEAD, branches: { [branch]: HEAD }, committedManifest: manifest(root), commitCount: 1 };
  writeState(root, initial);
  return initial;
}

function writeState(root, state) {
  writeFileSync(statePath(root), `${JSON.stringify(state, null, 2)}\n`);
}

function manifest(directory, root = directory) {
  const entries = [];
  for (const name of readdirSync(directory).sort()) {
    if (name === ".git") continue;
    const path = join(directory, name);
    const stat = lstatSync(path);
    if (stat.isDirectory()) {
      entries.push(...manifest(path, root));
    } else if (stat.isSymbolicLink()) {
      entries.push([relative(root, path), "link", readlinkSync(path)]);
    } else {
      entries.push([relative(root, path), "file", readFileSync(path).toString("base64")]);
    }
  }
  return entries;
}

function fail(message, code = 128) {
  process.stderr.write(`${message}\n`);
  process.exitCode = code;
}

if (command[0] === "rev-parse" && command[1] === "--show-toplevel") {
  process.stdout.write(`${cwd}\n`);
} else if (command[0] === "rev-parse" && command[1] === "HEAD") {
  process.stdout.write(`${readState(cwd).head}\n`);
} else if (command[0] === "rev-parse" && command[1] === "--git-path") {
  process.stdout.write(`${join(cwd, ".git", command[2])}\n`);
} else if (command[0] === "rev-parse" && command[1] === "--verify") {
  const state = readState(cwd);
  const name = command[2];
  if (state.branches[name]) process.stdout.write(`${state.branches[name]}\n`);
  else fail("fatal: Needed a single revision");
} else if (command[0] === "rev-parse" && command.length === 2) {
  const state = readState(cwd);
  const ref = command[1];
  if (ref.startsWith("refs/heads/")) {
    const branch = ref.slice("refs/heads/".length);
    if (state.branches[branch]) process.stdout.write(`${state.branches[branch]}\n`);
    else fail("fatal: Needed a single revision");
  } else if (state.branches[ref]) {
    process.stdout.write(`${state.branches[ref]}\n`);
  } else {
    fail(`Unsupported fake git rev-parse: ${ref}`, 2);
  }
} else if (command[0] === "branch" && command[1] === "--show-current") {
  process.stdout.write(`${readState(cwd).branch}\n`);
} else if (command[0] === "branch" && command[1] === "-d") {
  const state = readState(cwd);
  const branch = command[2];
  if (state.branch === branch || !state.branches[branch]) {
    fail(`error: branch '${branch}' cannot be deleted`);
  } else {
    delete state.branches[branch];
    writeState(cwd, state);
  }
} else if (command[0] === "switch") {
  const state = readState(cwd);
  const create = command[1] === "-c";
  const branch = create ? command[2] : command[1];
  if (create) {
    if (state.branches[branch]) fail(`fatal: A branch named '${branch}' already exists.`);
    else {
      state.branches[branch] = state.head;
      state.branch = branch;
      writeState(cwd, state);
    }
  } else if (!state.branches[branch]) {
    fail(`fatal: invalid reference: ${branch}`);
  } else {
    state.branch = branch;
    writeState(cwd, state);
  }
} else if (command[0] === "status") {
  const status = process.env.MINION_FAKE_GIT_STATUS;
  if (status) {
    process.stdout.write(`${status}\0`);
  } else if (JSON.stringify(manifest(cwd)) !== JSON.stringify(readState(cwd).committedManifest)) {
    process.stdout.write(" M minion-fake-change\0");
  }
} else if (command[0] === "diff") {
  if (!command.includes("--cached")) {
    const current = manifest(cwd);
    if (JSON.stringify(current) !== JSON.stringify(readState(cwd).committedManifest)) {
      process.stdout.write(JSON.stringify(current));
    }
  }
} else if (command[0] === "add") {
  process.exitCode = 0;
} else if (command[0] === "commit") {
  const state = readState(cwd);
  state.commitCount = (state.commitCount ?? 1) + 1;
  state.head = state.commitCount.toString(16).padStart(40, "0");
  state.branches[state.branch] = state.head;
  state.committedManifest = manifest(cwd);
  writeState(cwd, state);
  process.stdout.write(`[${state.branch} ${state.head.slice(0, 7)}] fake commit\n`);
} else {
  fail(`Unsupported fake git command: ${command.join(" ")}`, 2);
}
