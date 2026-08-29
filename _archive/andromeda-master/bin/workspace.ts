#!/usr/bin/env bun
import { createHash } from "node:crypto";
import {
  createWriteStream,
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  rmSync,
  statSync,
  watch as watchFs,
  writeFileSync,
} from "node:fs";
import { availableParallelism } from "node:os";
import { basename, dirname, join } from "node:path";
import pack from "libnpmpack";
import * as tar from "tar";

// worktrunk only honors worktree-path from user config, so we pass our own via --config.
// Resolved relative to this script (bin/), so it works from worktree or main checkout.
const WT_CONFIG = join(dirname(import.meta.dirname), ".config", "wt-workspace.toml");
const wtConfigArgs = () => (existsSync(WT_CONFIG) ? ["--config", WT_CONFIG] : []);

// Each service's base port. The branch offset is added to every base so all services on
// one branch shift together (serana 7100→71xx, courier 7200→72xx with the SAME xx).
const SERVICE_BASES: Record<string, number> = { lydia: 7000, serana: 7100, courier: 7200 };

// cksum of the branch → stable per-branch offset (0-98), identical across machines/services.
async function branchOffset(branch: string): Promise<number> {
  const out = await new Response(
    Bun.spawn(["cksum"], { stdin: new TextEncoder().encode(branch), stdout: "pipe" }).stdout,
  ).text();
  return Number(out.trim().split(/\s+/)[0]) % 99;
}

const portOf = (service: string, offset: number): number | null =>
  service in SERVICE_BASES ? SERVICE_BASES[service] + offset : null;

// Rewrite a worktree's .env: set this service's SERVER_PORT and its peer URLs to workspace ports.
// Done here (not in the hook) because worktrunk neutralizes shell $VARs in hook commands.
function writePorts(repo: string, service: string, offset: number): void {
  const envPath = join(repo, ".env");
  let env: string;
  try { env = readFileSync(envPath, "utf8"); } catch { return; }

  // 1. This service's own port. SERVER_PORT is added if missing; PORT (read by some frameworks,
  //    e.g. next) is only rewritten when the repo already declares it — never injected.
  const own = portOf(service, offset);
  if (own !== null) {
    const serverRe = /^SERVER_PORT=.*$/m;
    env = serverRe.test(env) ? env.replace(serverRe, `SERVER_PORT=${own}`)
                             : `${env}${env.endsWith("\n") ? "" : "\n"}SERVER_PORT=${own}\n`;
    env = env.replace(/^PORT=.*$/m, `PORT=${own}`);
  }

  // 2. Every localhost:<known-base> URL → localhost:<base + offset>, so own SERVER_URL and any
  //    peer URL (COURIER_URL, SERANA_URI, *_DOMAIN, ...) all shift to workspace ports at once.
  for (const base of Object.values(SERVICE_BASES)) {
    env = env.replaceAll(`localhost:${base}`, `localhost:${base + offset}`);
  }

  writeFileSync(envPath, env);
}

const HELP = `workspace — multi-repo feature worktrees for andromeda

A workspace groups per-repo git worktrees that share one feature branch, under
<andromeda>/.workspaces/<branch>/<repo>. worktrunk (wt) owns per-repo creation and
bootstrap via each repo's .config/wt.toml; this script only orchestrates across repos.
Repos resolve against the main andromeda checkout, even from inside a worktree.

Usage:
  workspace create <branch> <repos...|tag>   Create worktrees on <branch> for each repo
                                             (or every repo under a mani tag), in parallel.
  workspace exec   [branch] -- <cmd...>      Run a command in every repo of the workspace.
  workspace status [branch]                  git status -sb across the workspace.
  workspace diff   [branch]                  git diff across the workspace.
  workspace test   [branch]                  npm test per repo, skipping no-test stubs.
  workspace lint   [branch]                  npm run lint per repo, skipping repos without it.
  workspace ports  [branch]                  List every service -> port in the workspace.
  workspace port   <service> [branch]        Print one service's port.
  workspace sync-deps <branch> [--watch]     Build and install local @refrens dependencies.
  workspace up <branch> [--watch]            Sync dependencies, then run serana and lydia.
  workspace rm     <branch>                  Remove all worktrees in the workspace.

[branch] is optional when run from inside a .workspaces/<branch>/ directory.`;

async function capture(cmd: string, args: string[], cwd?: string): Promise<string> {
  const p = Bun.spawn([cmd, ...args], { cwd, stdout: "pipe", stderr: "pipe" });
  const out = await new Response(p.stdout).text();
  await p.exited;
  return out.trim();
}

async function run(cmd: string, args: string[], cwd?: string): Promise<number> {
  const p = Bun.spawn([cmd, ...args], { cwd, stdout: "inherit", stderr: "inherit" });
  return await p.exited;
}

function die(msg: string): never {
  console.error(`ERROR: ${msg}`);
  process.exit(1);
}

const hr = (name: string) => console.log(`── ${name} ──────────────────────────────`);
const slug = (branch: string) => branch.replace(/[/\\]/g, "-");

async function andromedaRoot(): Promise<string> {
  const d = await capture("git", ["rev-parse", "--path-format=absolute", "--git-common-dir"]);
  return d.replace(/\/\.git$/, "");
}

async function workspaceDir(branch?: string): Promise<string> {
  if (branch) return join(await andromedaRoot(), ".workspaces", slug(branch));
  const here = process.cwd();
  const marker = "/.workspaces/";
  if (here.includes(marker)) {
    const after = here.slice(here.indexOf(marker) + marker.length);
    return here.slice(0, here.indexOf(marker)) + marker + after.split("/")[0];
  }
  die("no branch given and not inside a workspace");
}

async function requireWorkspace(branch?: string): Promise<string> {
  const ws = await workspaceDir(branch);
  if (!existsSync(ws)) die(`No workspace at ${ws}`);
  return ws;
}

const repoWorktrees = (ws: string): string[] =>
  readdirSync(ws, { withFileTypes: true })
    .filter((e) => e.isDirectory())
    .map((e) => join(ws, e.name));

const npmScripts = (repo: string): Record<string, string> => {
  try {
    return JSON.parse(readFileSync(join(repo, "package.json"), "utf8")).scripts ?? {};
  } catch {
    return {};
  }
};

type PackageManifest = {
  readonly name: string;
  readonly dependencies: Readonly<Record<string, string>>;
  readonly scripts: Readonly<Record<string, string>>;
};

type WorkspaceRepo = {
  readonly dir: string;
  readonly path: string;
  readonly manifest: PackageManifest;
};

type DependencyGraph = {
  readonly repos: ReadonlyMap<string, WorkspaceRepo>;
  readonly dependencies: ReadonlyMap<string, ReadonlyArray<string>>;
  readonly consumers: ReadonlyMap<string, ReadonlyArray<string>>;
  readonly relevant: ReadonlyArray<string>;
  readonly levels: ReadonlyArray<ReadonlyArray<string>>;
};

type SyncStateEntry = {
  readonly mtimeHash: string;
  readonly buildConfigHash: string;
  readonly inputFiles: ReadonlyArray<string>;
  readonly syncedAt: number;
};

type SyncState = Readonly<Record<string, SyncStateEntry>>;

type SyncResult = {
  readonly code: number;
  readonly stopWatching?: () => void;
};

type SourceSnapshot = {
  readonly mtimeHash: string;
  readonly buildConfigHash: string;
  readonly inputFiles: ReadonlyArray<string>;
};

type BuildMode = "full" | "incremental" | "none";

const LOCAL_SCOPE = "@refrens/";
const APP_DIRS = ["serana", "lydia"] as const;
const ANSI_RESET = "\x1b[0m";
const SERVICE_COLORS: Readonly<Record<string, string>> = {
  serana: "\x1b[36m",
  lydia: "\x1b[35m",
};

const elapsed = (startedAt: number): string => `${((Date.now() - startedAt) / 1_000).toFixed(2)}s`;

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const stringEntries = (value: unknown): Record<string, string> => {
  if (!isRecord(value)) return {};
  return Object.fromEntries(Object.entries(value).filter((entry): entry is [string, string] =>
    typeof entry[1] === "string",
  ));
};

function packageManifest(repo: string): PackageManifest {
  const parsed: unknown = JSON.parse(readFileSync(join(repo, "package.json"), "utf8"));
  if (!isRecord(parsed) || typeof parsed.name !== "string") die(`Invalid package.json in ${repo}`);
  return {
    name: parsed.name,
    dependencies: stringEntries(parsed.dependencies),
    scripts: stringEntries(parsed.scripts),
  };
}

function workspaceRepos(ws: string): ReadonlyArray<WorkspaceRepo> {
  return repoWorktrees(ws)
    .filter((repo) => existsSync(join(repo, "package.json")))
    .map((repo) => ({ dir: basename(repo), path: repo, manifest: packageManifest(repo) }));
}

function sourceFiles(repo: WorkspaceRepo): ReadonlyArray<string> {
  const output = Bun.spawnSync(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], {
    cwd: repo.path,
  });
  if (output.exitCode !== 0) die(`Could not list tracked files in ${repo.dir}`);
  const files = new TextDecoder().decode(output.stdout)
    .split("\0")
    .filter(Boolean);
  const hasSourceDirectory = existsSync(join(repo.path, "src"));
  return files.filter((file) =>
    existsSync(join(repo.path, file)) && (
      !hasSourceDirectory ||
      file === "package.json" ||
      /^tsconfig.*\.json$/.test(file) ||
      file.startsWith("src/") ||
      (!file.includes("/") && /\.[cm]?js$/.test(file))
    ),
  );
}

function fingerprintFiles(repo: WorkspaceRepo, files: ReadonlyArray<string>): string {
  const hash = createHash("sha1");
  for (const relativePath of files) {
    const stat = statSync(join(repo.path, relativePath));
    hash.update(`${relativePath}:${stat.size}:${stat.mtimeMs}\n`);
  }
  return hash.digest("hex");
}

function sourceSnapshot(repo: WorkspaceRepo): SourceSnapshot {
  const inputFiles = [...sourceFiles(repo)].sort();
  const buildConfigFiles = inputFiles.filter((file) => file === "package.json" || /^tsconfig.*\.json$/.test(file));
  return {
    mtimeHash: fingerprintFiles(repo, inputFiles),
    buildConfigHash: fingerprintFiles(repo, buildConfigFiles),
    inputFiles,
  };
}

const sameFiles = (left: ReadonlyArray<string>, right: ReadonlyArray<string>): boolean =>
  left.length === right.length && left.every((file, index) => file === right[index]);

function dependencyGraph(ws: string): DependencyGraph {
  const allRepos = workspaceRepos(ws);
  const repos = new Map(allRepos.map((repo) => [repo.manifest.name, repo]));
  const dependencies = new Map<string, ReadonlyArray<string>>();
  const consumers = new Map<string, ReadonlyArray<string>>();

  for (const repo of allRepos) {
    const localDependencies = Object.keys(repo.manifest.dependencies)
      .filter((name) => name.startsWith(LOCAL_SCOPE) && repos.has(name));
    dependencies.set(repo.manifest.name, localDependencies);
    for (const dependency of localDependencies) {
      consumers.set(dependency, [...(consumers.get(dependency) ?? []), repo.manifest.name]);
    }
  }

  const targets = APP_DIRS
    .map((dir) => allRepos.find((repo) => repo.dir === dir)?.manifest.name)
    .filter((name): name is string => name !== undefined);
  if (targets.length === 0) die("sync-deps requires a workspace containing serana or lydia");

  const relevant = new Set<string>();
  const visit = (name: string): void => {
    for (const dependency of dependencies.get(name) ?? []) {
      if (relevant.has(dependency)) continue;
      relevant.add(dependency);
      visit(dependency);
    }
  };
  for (const target of targets) visit(target);

  const remainingDependencies = new Map(
    [...relevant].map((name) => [name, new Set((dependencies.get(name) ?? []).filter((dep) => relevant.has(dep)))]),
  );
  const levels: string[][] = [];
  while (remainingDependencies.size > 0) {
    const level = [...remainingDependencies]
      .filter(([, deps]) => deps.size === 0)
      .map(([name]) => name)
      .sort();
    if (level.length === 0) die("Local @refrens dependency graph contains a cycle");
    levels.push(level);
    for (const name of level) remainingDependencies.delete(name);
    for (const deps of remainingDependencies.values()) {
      for (const completed of level) deps.delete(completed);
    }
  }

  return { repos, dependencies, consumers, relevant: [...relevant], levels };
}

function syncState(ws: string): SyncState {
  const statePath = join(ws, ".logs", "sync-state.json");
  if (!existsSync(statePath)) return {};
  try {
    const parsed: unknown = JSON.parse(readFileSync(statePath, "utf8"));
    if (!isRecord(parsed)) return {};
    return Object.fromEntries(Object.entries(parsed).flatMap(([name, entry]) =>
      isRecord(entry) &&
      typeof entry.mtimeHash === "string" &&
      typeof entry.buildConfigHash === "string" &&
      Array.isArray(entry.inputFiles) &&
      entry.inputFiles.every((file) => typeof file === "string") &&
      typeof entry.syncedAt === "number"
        ? [[name, {
          mtimeHash: entry.mtimeHash,
          buildConfigHash: entry.buildConfigHash,
          inputFiles: entry.inputFiles,
          syncedAt: entry.syncedAt,
        }]]
        : [],
    ));
  } catch {
    return {};
  }
}

function writeSyncState(ws: string, state: SyncState): void {
  const logs = join(ws, ".logs");
  mkdirSync(logs, { recursive: true });
  writeFileSync(join(logs, "sync-state.json"), `${JSON.stringify(state, null, 2)}\n`);
}

function localDestination(consumer: WorkspaceRepo, packageName: string): string {
  return join(consumer.path, "node_modules", ...packageName.split("/"));
}

async function extractTarball(tarball: Buffer, destination: string): Promise<void> {
  rmSync(destination, { recursive: true, force: true });
  mkdirSync(destination, { recursive: true });
  await new Promise<void>((resolve, reject) => {
    const extraction = tar.extract({ cwd: destination, strip: 1 });
    extraction.once("close", resolve);
    extraction.once("error", reject);
    extraction.end(tarball);
  });
}

async function installLocalPackage(
  repo: WorkspaceRepo,
  consumers: ReadonlyArray<WorkspaceRepo>,
): Promise<void> {
  // Builds are explicitly orchestrated above. Running npm lifecycle scripts here would
  // rebuild packages (and can erase incremental outputs) after their dependency barrier.
  const tarball = await pack(repo.path, { ignoreScripts: true });
  await Promise.all(consumers.map((consumer) =>
    extractTarball(tarball, localDestination(consumer, repo.manifest.name)),
  ));
}

function supportsIncrementalBuild(repo: WorkspaceRepo): boolean {
  const { scripts } = repo.manifest;
  return !!scripts.prebuild && (!!scripts["build:incr"] || (!!scripts["build:es6"] && !!scripts["build:es5:incr"]));
}

function incrementalCacheDirectory(repo: WorkspaceRepo): string {
  return join(repo.path, "node_modules", ".cache", "refrens-build");
}

function hasIncrementalArtifacts(repo: WorkspaceRepo): boolean {
  const cache = incrementalCacheDirectory(repo);
  return existsSync(join(cache, "es6.tsbuildinfo")) &&
    existsSync(join(cache, "es5.tsbuildinfo")) &&
    existsSync(join(repo.path, "dist", "es6", "index.js")) &&
    existsSync(join(repo.path, "dist", "es5", "index.js"));
}

async function runBuildScript(repo: WorkspaceRepo, script: string, args: ReadonlyArray<string> = []): Promise<void> {
  const status = await run("npm", ["run", script, "--", ...args], repo.path);
  if (status !== 0) die(`${repo.dir}: npm run ${script} failed`);
}

async function incrementalBuild(repo: WorkspaceRepo): Promise<void> {
  const cache = incrementalCacheDirectory(repo);
  mkdirSync(cache, { recursive: true });
  if (repo.manifest.scripts["build:incr"]) {
    await runBuildScript(repo, "build:incr");
    return;
  }
  await runBuildScript(repo, "build:es6", ["--incremental", "--tsBuildInfoFile", join(cache, "es6.tsbuildinfo")]);
  await runBuildScript(repo, "build:es5:incr", ["--tsBuildInfoFile", join(cache, "es5.tsbuildinfo")]);
  if (repo.manifest.scripts["build:icons"]) await runBuildScript(repo, "build:icons");
}

async function buildLocalPackage(repo: WorkspaceRepo, mode: BuildMode): Promise<void> {
  if (!repo.manifest.scripts.build) return;
  if (mode === "none") return;
  if (!supportsIncrementalBuild(repo)) {
    await runBuildScript(repo, "build");
    return;
  }
  if (mode === "full") {
    rmSync(incrementalCacheDirectory(repo), { recursive: true, force: true });
    await runBuildScript(repo, "prebuild");
  }
  await incrementalBuild(repo);
}

function buildMode(
  repo: WorkspaceRepo,
  previous: SyncStateEntry | undefined,
  current: SourceSnapshot,
  requiresBuild: boolean,
): BuildMode {
  if (!repo.manifest.scripts.build || !requiresBuild) return "none";
  if (!supportsIncrementalBuild(repo) || !previous || !hasIncrementalArtifacts(repo)) return "full";
  if (previous.buildConfigHash !== current.buildConfigHash || !sameFiles(previous.inputFiles, current.inputFiles)) {
    return "full";
  }
  return "incremental";
}

async function runLimited<T>(
  values: ReadonlyArray<T>,
  limit: number,
  task: (value: T) => Promise<void>,
): Promise<void> {
  const pending = [...values];
  const worker = async (): Promise<void> => {
    const value = pending.shift();
    if (value === undefined) return;
    await task(value);
    await worker();
  };
  await Promise.all(Array.from({ length: Math.min(limit, values.length) }, worker));
}

function watchOptions(flags: ReadonlyArray<string>): { readonly watch: boolean } {
  if (flags.length === 0) return { watch: false };
  if (flags.length === 1 && flags[0] === "--watch") return { watch: true };
  die(`Unknown sync-deps option: ${flags.join(" ")}`);
}

async function syncDeps(branch: string, options: { readonly watch: boolean }): Promise<SyncResult> {
  const syncStartedAt = Date.now();
  const ws = await requireWorkspace(branch);
  const graph = dependencyGraph(ws);
  const state = syncState(ws);
  const snapshots = new Map(graph.relevant.map((name) => {
    const repo = graph.repos.get(name);
    if (!repo) die(`Missing workspace package ${name}`);
    return [name, sourceSnapshot(repo)];
  }));
  const dirty = new Set<string>();

  for (const name of graph.relevant) {
    const repo = graph.repos.get(name);
    if (!repo) die(`Missing workspace package ${name}`);
    const missingConsumerCopy = (graph.consumers.get(name) ?? []).some((consumerName) => {
      const consumer = graph.repos.get(consumerName);
      return !consumer || !existsSync(localDestination(consumer, name));
    });
    const missingIncrementalOutput = supportsIncrementalBuild(repo) && !hasIncrementalArtifacts(repo);
    if (state[name]?.mtimeHash !== snapshots.get(name)?.mtimeHash || missingConsumerCopy || missingIncrementalOutput) {
      dirty.add(name);
    }
  }

  const nextState: Record<string, SyncStateEntry> = { ...state };
  for (const level of graph.levels) {
    const toSync = level.filter((name) =>
      dirty.has(name) || (graph.dependencies.get(name) ?? []).some((dependency) => dirty.has(dependency)),
    );
    for (const name of toSync) dirty.add(name);
    await runLimited(toSync, Math.max(1, availableParallelism() - 2), async (name) => {
      const repo = graph.repos.get(name);
      if (!repo) die(`Missing workspace package ${name}`);
      const packageStartedAt = Date.now();
      hr(`sync ${repo.dir}`);
      const dependencyChanged = (graph.dependencies.get(name) ?? []).some((dependency) => dirty.has(dependency));
      const currentSnapshot = snapshots.get(name);
      if (!currentSnapshot) die(`Could not fingerprint ${repo.dir}`);
      const sourceChanged = state[name]?.mtimeHash !== currentSnapshot.mtimeHash;
      const buildStartedAt = Date.now();
      const requiresBuild = sourceChanged || dependencyChanged ||
        (supportsIncrementalBuild(repo) && !hasIncrementalArtifacts(repo));
      const mode = buildMode(repo, state[name], currentSnapshot, requiresBuild);
      await buildLocalPackage(repo, mode);
      console.log(`  build ${repo.dir} (${mode}): ${elapsed(buildStartedAt)}`);
      const consumers = (graph.consumers.get(name) ?? [])
        .map((consumerName) => graph.repos.get(consumerName))
        .filter((consumer): consumer is WorkspaceRepo => consumer !== undefined);
      await installLocalPackage(repo, consumers);
      console.log(`  sync ${repo.dir}: ${elapsed(packageStartedAt)}`);
      nextState[name] = { ...currentSnapshot, syncedAt: Date.now() };
    });
  }
  writeSyncState(ws, nextState);
  console.log(
    dirty.size === 0
      ? "Local dependencies are already in sync."
      : `Synced ${dirty.size} local dependencies in ${elapsed(syncStartedAt)}.`,
  );
  return { code: 0, stopWatching: options.watch ? startDependencyWatchers(graph) : undefined };
}

function debounce(callback: () => void, delay = 150): () => void {
  let timer: ReturnType<typeof setTimeout> | undefined;
  return () => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(callback, delay);
  };
}

function startDependencyWatchers(graph: DependencyGraph): () => void {
  const watchers: ReturnType<typeof watchFs>[] = [];
  const buildProcesses: ReturnType<typeof Bun.spawn>[] = [];
  for (const name of graph.relevant) {
    const repo = graph.repos.get(name);
    if (!repo) die(`Missing workspace package ${name}`);
    const consumers = (graph.consumers.get(name) ?? [])
      .map((consumerName) => graph.repos.get(consumerName))
      .filter((consumer): consumer is WorkspaceRepo => consumer !== undefined);
    let syncing = false;
    const sync = debounce(() => {
      if (syncing) return;
      syncing = true;
      installLocalPackage(repo, consumers)
        .catch((error: unknown) => console.error(`Failed to sync ${repo.dir}:`, error))
        .finally(() => { syncing = false; });
    });
    const source = existsSync(join(repo.path, "src")) ? join(repo.path, "src") : repo.path;
    if (!repo.manifest.scripts.build) {
      watchers.push(watchFs(source, { recursive: true }, sync));
      console.log(`  watching ${repo.dir}`);
      continue;
    }
    if (repo.manifest.scripts["build:es6"] && repo.manifest.scripts["build:es5:incr"]) {
      for (const script of ["build:es6", "build:es5:incr"]) {
        buildProcesses.push(Bun.spawn(["npm", "run", script, "--", "--watch"], {
          cwd: repo.path,
          stdout: "inherit",
          stderr: "inherit",
        }));
      }
      const syncBuildOutput = debounce(() => {
        if (syncing) return;
        syncing = true;
        const iconBuild = repo.manifest.scripts["build:icons"]
          ? run("npm", ["run", "build:icons"], repo.path)
          : Promise.resolve(0);
        iconBuild
          .then((status) => {
            if (status !== 0) throw new Error(`npm run build:icons failed for ${repo.dir}`);
            return installLocalPackage(repo, consumers);
          })
          .catch((error: unknown) => console.error(`Failed to sync ${repo.dir}:`, error))
          .finally(() => { syncing = false; });
      });
      watchers.push(watchFs(join(repo.path, "dist"), { recursive: true }, syncBuildOutput));
    } else {
      const rebuild = debounce(() => {
        if (syncing) return;
        syncing = true;
        buildLocalPackage(repo, "full")
          .then(() => installLocalPackage(repo, consumers))
          .catch((error: unknown) => console.error(`Failed to rebuild ${repo.dir}:`, error))
          .finally(() => { syncing = false; });
      });
      watchers.push(watchFs(source, { recursive: true }, rebuild));
    }
    console.log(`  watching ${repo.dir}`);
  }
  const stopWatching = (): void => {
    for (const watcher of watchers) watcher.close();
    for (const process of buildProcesses) process.kill();
    process.off("SIGINT", stopWatching);
    process.off("SIGTERM", stopWatching);
  };
  process.once("SIGINT", stopWatching);
  process.once("SIGTERM", stopWatching);
  return stopWatching;
}

const servicePort = (repo: string): string | null => {
  try {
    const m = readFileSync(join(repo, ".env"), "utf8").match(/^SERVER_PORT=(\d+)/m);
    if (m) return m[1];
  } catch {}
  return null;
};


async function create(branch: string, repoArgs: string[]): Promise<number> {
  if (!branch || repoArgs.length === 0) die("usage: workspace create <branch> <repos...|tag>");
  const root = await andromedaRoot();

  let repos = repoArgs;
  if (repos.length === 1) {
    const out = await capture("mani", ["list", "projects", "--tags", repos[0], "--no-headers"]);
    const tagged = out.split("\n").map((l) => l.trim().split(/\s+/)[0]).filter(Boolean);
    if (tagged.length > 0) repos = tagged;
  }

  console.log(`==> Creating worktrees for '${branch}' across: ${repos.join(", ")}`);

  const offset = await branchOffset(branch);
  const wsRoot = join(root, ".workspaces", slug(branch));

  const results = await Promise.all(
    repos.map(async (repo) => {
      if (!existsSync(join(root, repo, ".git"))) return { repo, ok: false, skipped: true } as const;
      const log = `/tmp/wt-${repo}.log`;
      const p = Bun.spawn(
        ["wt", ...wtConfigArgs(), "-C", join(root, repo), "switch", "--create", "--no-cd", "--yes", branch],
        { stdout: Bun.file(log), stderr: Bun.file(log) },
      );
      const ok = (await p.exited) === 0;
      // Hook copies .env + installs; workspace.ts writes ports (worktrunk neutralizes hook $VARs).
      if (ok) writePorts(join(wsRoot, repo), repo, offset);
      return { repo, ok, skipped: false } as const;
    }),
  );

  let fail = 0;
  for (const r of results) {
    if (r.skipped) console.log(`  [skip] ${r.repo} — not cloned in andromeda (try: just sync)`);
    else if (r.ok) console.log(`  [ok]   ${r.repo}`);
    else { console.log(`  [FAIL] ${r.repo} — see /tmp/wt-${r.repo}.log`); fail = 1; }
  }
  return fail;
}

async function execAcross(branch: string | undefined, cmd: string[]): Promise<number> {
  const ws = await requireWorkspace(branch);
  if (cmd[0] === "--") cmd = cmd.slice(1);
  if (cmd.length === 0) cmd = ["git", "status", "-sb"];
  let fail = 0;
  for (const repo of repoWorktrees(ws)) {
    hr(basename(repo));
    if ((await run(cmd[0], cmd.slice(1), repo)) !== 0) fail = 1;
  }
  return fail;
}

// `exec` args: an optional leading <branch>, then `-- <cmd...>`. When the first
// token is `--` (or absent), there's no branch — fall back to cwd detection.
function execArgs(rest: string[]): [string | undefined, string[]] {
  if (rest.length === 0 || rest[0] === "--") return [undefined, rest];
  return [rest[0], rest.slice(1)];
}

async function status(branch: string): Promise<number> {
  const ws = await requireWorkspace(branch);
  console.log(`Workspace: ${ws}`);
  for (const repo of repoWorktrees(ws)) console.log(`  • ${basename(repo)}`);
  console.log();
  return execAcross(branch, ["git", "status", "-sb"]);
}

const diff = (branch: string) => execAcross(branch, ["git", "--no-pager", "diff"]);

async function runNpm(
  branch: string,
  label: string,
  hasScript: (s: Record<string, string>) => boolean,
  npmArgs: string[],
): Promise<number> {
  const ws = await requireWorkspace(branch);
  let fail = 0;
  for (const repo of repoWorktrees(ws)) {
    const name = basename(repo);
    if (!hasScript(npmScripts(repo))) {
      console.log(`  [skip] ${name} — no real ${label} script`);
      continue;
    }
    hr(`${name}: ${label}`);
    if ((await run("npm", npmArgs, repo)) === 0) console.log(`  [pass] ${name}`);
    else { console.log(`  [FAIL] ${name}`); fail = 1; }
  }
  return fail;
}

const test = (branch: string) =>
  runNpm(branch, "test", (s) => !!s.test && !/^echo no-test/.test(s.test), ["test"]);

const lint = (branch: string) => runNpm(branch, "lint", (s) => !!s.lint, ["run", "lint"]);

async function ports(branch: string): Promise<number> {
  const ws = await requireWorkspace(branch);
  for (const repo of repoWorktrees(ws)) {
    const p = servicePort(repo);
    if (p) console.log(`  ${basename(repo).padEnd(14)} ${p}`);
  }
  return 0;
}

type WritableOutput = {
  readonly isTTY?: boolean;
  write(chunk: string): unknown;
};

const ANSI_ESCAPE = /\x1B(?:[@-_][0-?]*[ -/]*[@-~]|\[[0-?]*[ -/]*[@-~])/g;

const stripAnsi = (value: string): string => value.replace(ANSI_ESCAPE, "");

async function pipePrefixedLogs(
  stream: ReadableStream<Uint8Array>,
  name: string,
  terminal: WritableOutput,
  log: WritableOutput,
): Promise<void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let pending = "";
  const emit = (line: string, newline: boolean): void => {
    const suffix = newline ? "\n" : "";
    const plainOutput = `[${name}] ${stripAnsi(line)}${suffix}`;
    const color = SERVICE_COLORS[name];
    const terminalOutput = terminal.isTTY && color
      ? `[${color}${name}${ANSI_RESET}] ${line}${suffix}`
      : plainOutput;
    terminal.write(terminalOutput);
    log.write(plainOutput);
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    pending += decoder.decode(value, { stream: true });
    let newline = pending.indexOf("\n");
    while (newline !== -1) {
      emit(pending.slice(0, newline), true);
      pending = pending.slice(newline + 1);
      newline = pending.indexOf("\n");
    }
  }
  pending += decoder.decode();
  if (pending) emit(pending, false);
}

// Run serana and lydia in the foreground. Their interleaved output is color-prefixed in
// the terminal and also stored without ANSI codes under <workspace>/.logs/<run-id>/.
async function startApps(branch: string): Promise<number> {
  const ws = await requireWorkspace(branch);
  const apps = APP_DIRS.map((dir) => join(ws, dir)).filter(existsSync);
  if (apps.length === 0) die("up requires a workspace containing serana or lydia");
  return startRepos(ws, apps);
}

async function startRepos(ws: string, repos: ReadonlyArray<string>): Promise<number> {
  const runId = `${new Date().toISOString().replace(/[:.]/g, "-")}-p${process.pid}`;
  const logsDir = join(ws, ".logs", runId);
  mkdirSync(logsDir, { recursive: true });
  console.log(`  run ${runId} → logs: ${logsDir}`);
  const procs = repos.map((repo) => {
    const name = basename(repo);
    const logPath = join(logsDir, `${name}.log`);
    console.log(`  starting ${name} → port ${servicePort(repo) ?? "?"} (log: ${logPath})`);
    const p = servicePort(repo);
    // Only inject ports when we know one — an empty SERVER_PORT="" would be "set" in the
    // child (dotenv won't override it) and the app would read NaN and fail to bind.
    // SERVER_PORT for services that read .env; PORT for those whose script takes -p $PORT (lydia).
    const portEnv = p ? { SERVER_PORT: p, PORT: p } : {};
    const log = createWriteStream(logPath, { flags: "a" });
    log.write(`\n── ${new Date().toISOString()} · npm run watch ──\n`);
    const child = Bun.spawn(["npm", "run", "watch"], {
      cwd: repo,
      env: { ...process.env, ...portEnv },
      stdout: "pipe",
      stderr: "pipe",
    });
    const output = Promise.all([
      pipePrefixedLogs(child.stdout, name, process.stdout, log),
      pipePrefixedLogs(child.stderr, name, process.stderr, log),
    ]);
    return { child, log, output };
  });
  const codes = await Promise.all(procs.map(async ({ child, log, output }) => {
    const code = await child.exited;
    await output;
    await new Promise<void>((resolve) => log.end(resolve));
    return code;
  }));
  return codes.some((code) => code !== 0) ? 1 : 0;
}

async function up(branch: string, options: { readonly watch: boolean }): Promise<number> {
  const sync = await syncDeps(branch, options);
  if (sync.code !== 0) return sync.code;
  try {
    return await startApps(branch);
  } finally {
    sync.stopWatching?.();
  }
}

async function port(service: string, branch: string): Promise<number> {
  if (!service) die("usage: workspace port <service> [branch]");
  const ws = await requireWorkspace(branch);
  if (!existsSync(join(ws, service))) die(`No worktree for ${service} in ${ws}`);
  const p = servicePort(join(ws, service));
  if (!p) die(`No SERVER_PORT written for ${service}`);
  console.log(p);
  return 0;
}

async function remove(branch: string): Promise<number> {
  if (!branch) die("usage: workspace rm <branch>");
  const root = await andromedaRoot();
  const ws = join(root, ".workspaces", slug(branch));
  if (!existsSync(ws)) die(`No workspace at ${ws}`);
  let fail = 0;
  for (const repo of repoWorktrees(ws)) {
    const name = basename(repo);
    if ((await run("wt", [...wtConfigArgs(), "-C", join(root, name), "remove", "--force", branch])) === 0)
      console.log(`  [ok] removed ${name}`);
    else { console.log(`  [FAIL] ${name}`); fail = 1; }
  }
  try { if (readdirSync(ws).length === 0) await run("rmdir", [ws]); } catch {}
  return fail;
}

const [sub, ...rest] = process.argv.slice(2);

let code: number;
switch (sub) {
  case "create": code = await create(rest[0], rest.slice(1)); break;
  case "exec":   code = await execAcross(...execArgs(rest)); break;
  case "status": code = await status(rest[0]); break;
  case "diff":   code = await diff(rest[0]); break;
  case "test":   code = await test(rest[0]); break;
  case "lint":   code = await lint(rest[0]); break;
  case "ports":  code = await ports(rest[0]); break;
  case "port":   code = await port(rest[0], rest[1]); break;
  case "sync-deps": code = (await syncDeps(rest[0], watchOptions(rest.slice(1)))).code; break;
  case "up": code = await up(rest[0], watchOptions(rest.slice(1))); break;
  case "rm":     code = await remove(rest[0]); break;
  case "help": case "--help": case "-h": case undefined: console.log(HELP); code = sub ? 0 : 2; break;
  default: console.error(`unknown subcommand: ${sub}\n\n${HELP}`); code = 2;
}
process.exit(code);
