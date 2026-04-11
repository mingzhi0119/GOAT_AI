import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import os from "node:os";
import { dirname, join, posix as pathPosix, win32 as pathWin32 } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const frontendRoot = join(scriptDir, "..");

function joinForPlatform(platform, ...parts) {
  return platform === "win32" ? pathWin32.join(...parts) : pathPosix.join(...parts);
}

export function buildPathPrefixes({
  env = process.env,
  exists = existsSync,
  execPath = process.execPath,
  homeDir = os.homedir(),
  platform = process.platform,
} = {}) {
  const cargoBinDir = env.CARGO_HOME
    ? joinForPlatform(platform, env.CARGO_HOME, "bin")
    : joinForPlatform(platform, homeDir, ".cargo", "bin");
  const nodeBinDir = dirname(execPath);
  const pathPrefixes = [];

  if (exists(nodeBinDir)) {
    pathPrefixes.push(nodeBinDir);
  }
  if (exists(cargoBinDir)) {
    pathPrefixes.push(cargoBinDir);
  }

  return pathPrefixes;
}

export function buildTauriEnv({
  env = process.env,
  exists = existsSync,
  execPath = process.execPath,
  homeDir = os.homedir(),
  platform = process.platform,
} = {}) {
  const tauriEnv = { ...env };
  const pathPrefixes = buildPathPrefixes({ env, exists, execPath, homeDir, platform });

  if (pathPrefixes.length > 0) {
    const pathSeparator = platform === "win32" ? ";" : ":";
    const prefix = pathPrefixes.join(pathSeparator);
    tauriEnv.PATH = tauriEnv.PATH ? `${prefix}${pathSeparator}${tauriEnv.PATH}` : prefix;
  }

  return tauriEnv;
}

export function resolveTauriScript({
  cwd = frontendRoot,
  platform = process.platform,
} = {}) {
  return joinForPlatform(platform, cwd, "node_modules", "@tauri-apps", "cli", "tauri.js");
}

export function runTauriCli({
  cwd = frontendRoot,
  env = process.env,
  exists = existsSync,
  execPath = process.execPath,
  homeDir = os.homedir(),
  platform = process.platform,
  rawArgs = process.argv.slice(2),
  spawn = spawnSync,
} = {}) {
  const result = spawn(execPath, [resolveTauriScript({ cwd, platform }), ...rawArgs], {
    cwd,
    env: buildTauriEnv({
      env,
      exists,
      execPath,
      homeDir,
      platform,
    }),
    stdio: "inherit",
  });

  if (result.error) {
    return {
      exitCode: 1,
      errorMessage: `Failed to launch Tauri CLI: ${result.error.message}`,
    };
  }

  return {
    exitCode: result.status ?? 1,
  };
}

function isMainModule() {
  const entry = process.argv[1];
  return Boolean(entry) && import.meta.url === pathToFileURL(entry).href;
}

if (isMainModule()) {
  const result = runTauriCli();
  if (result.errorMessage) {
    console.error(result.errorMessage);
  }
  process.exit(result.exitCode);
}
