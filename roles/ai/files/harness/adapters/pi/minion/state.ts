import { renameSync, unlinkSync, writeFileSync } from "node:fs";
import { mkdir, readFile, rename, unlink, writeFile } from "node:fs/promises";
import { join } from "node:path";

import type { DeliveryAuthority, DeliveryState } from "./delivery.ts";

const MISSION_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

export type RunnerState = "starting" | "running" | "done" | "blocked" | "cancelled" | "limit-reached" | "crashed";

export interface LaunchRecord {
  id: string;
  cwd: string;
  branch: string;
  checkoutFingerprint: string;
  leasePath: string;
  goal: string;
  deliveryAuthority: DeliveryAuthority;
  missionBranchCreated: boolean;
  createdAt: string;
  token: string;
  runnerPath: string;
  sdkPath: string;
  model: { provider: string; id: string };
  thinkingLevel?: string;
  maxRuntimeMs: number;
  heartbeatMs: number;
  maxCycles: number;
  maxNoProgressCycles: number;
}

export interface RunnerStatus {
  id: string;
  state: RunnerState;
  cwd: string;
  branch: string;
  goal: string;
  deliveryAuthority: DeliveryAuthority;
  deliveryState: DeliveryState;
  createdAt: string;
  lastActivityAt: string;
  heartbeat: number;
  cycle: number;
  noProgressCycles: number;
  pid: number | null;
  token: string;
  runnerPath: string;
  missionDir: string;
  sessionPath?: string;
  commitSha?: string;
  pullRequestUrl?: string;
  result?: string;
}

export interface MissionPaths {
  missionDir: string;
  launchPath: string;
  statusPath: string;
  logPath: string;
}

function missionsDir(agentDir: string): string {
  return join(agentDir, "minion", "missions");
}

function latestPath(agentDir: string): string {
  return join(agentDir, "minion", "latest");
}

function assertMissionId(id: string): void {
  if (!MISSION_ID.test(id)) throw new Error(`Invalid Minion mission id: ${id}`);
}

export function missionPaths(agentDir: string, id: string): MissionPaths {
  assertMissionId(id);
  const missionDir = join(missionsDir(agentDir), id);
  return {
    missionDir,
    launchPath: join(missionDir, "launch.json"),
    statusPath: join(missionDir, "status.json"),
    logPath: join(missionDir, "session.log"),
  };
}

async function writeJsonAtomic(path: string, value: unknown): Promise<void> {
  const temporary = `${path}.${process.pid}.tmp`;
  try {
    await writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
    await rename(temporary, path);
  } finally {
    await unlink(temporary).catch(() => {});
  }
}

export async function createMission(agentDir: string, launch: LaunchRecord): Promise<MissionPaths> {
  const root = missionsDir(agentDir);
  const paths = missionPaths(agentDir, launch.id);
  await mkdir(root, { recursive: true, mode: 0o700 });
  await mkdir(paths.missionDir, { mode: 0o700 });
  await writeFile(paths.launchPath, `${JSON.stringify(launch, null, 2)}\n`, { flag: "wx", mode: 0o600 });
  await writeJsonAtomic(latestPath(agentDir), { id: launch.id });
  return paths;
}

export async function writeMissionStatus(statusPath: string, status: RunnerStatus): Promise<void> {
  await writeJsonAtomic(statusPath, status);
}

export function writeMissionStatusSync(statusPath: string, status: RunnerStatus): void {
  const temporary = `${statusPath}.${process.pid}.sync.tmp`;
  try {
    writeFileSync(temporary, `${JSON.stringify(status, null, 2)}\n`, { mode: 0o600 });
    renameSync(temporary, statusPath);
  } finally {
    try {
      unlinkSync(temporary);
    } catch {}
  }
}

export async function readLaunch(launchPath: string): Promise<LaunchRecord> {
  return JSON.parse(await readFile(launchPath, "utf8")) as LaunchRecord;
}

export async function resolveMissionId(agentDir: string, id?: string): Promise<string> {
  if (id) {
    assertMissionId(id);
    return id;
  }
  const latest = JSON.parse(await readFile(latestPath(agentDir), "utf8")) as { id: string };
  assertMissionId(latest.id);
  return latest.id;
}

export async function readMissionStatus(agentDir: string, id?: string): Promise<RunnerStatus> {
  const resolved = await resolveMissionId(agentDir, id);
  return JSON.parse(await readFile(missionPaths(agentDir, resolved).statusPath, "utf8")) as RunnerStatus;
}

export async function readMissionLog(agentDir: string, id?: string): Promise<string> {
  const resolved = await resolveMissionId(agentDir, id);
  return readFile(missionPaths(agentDir, resolved).logPath, "utf8");
}
