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

export function pythonCandidates({
  env = process.env,
  homeDir = os.homedir(),
  platform = process.platform,
} = {}) {
  const candidates = [];
  const explicit = env.GOAT_DESKTOP_PYTHON?.trim();
  if (explicit) {
    candidates.push(explicit);
  }
  const pushCandidate = candidate => {
    const normalized = candidate?.trim();
    if (normalized && !candidates.includes(normalized)) {
      candidates.push(normalized);
    }
  };
  if (platform === "win32") {
    const localAppData = env.LOCALAPPDATA || joinForPlatform(platform, homeDir, "AppData", "Local");
    [
      env.pythonLocation && joinForPlatform(platform, env.pythonLocation, "python.exe"),
      env.Python3_ROOT_DIR && joinForPlatform(platform, env.Python3_ROOT_DIR, "python.exe"),
      env.Python_ROOT_DIR && joinForPlatform(platform, env.Python_ROOT_DIR, "python.exe"),
      joinForPlatform(platform, localAppData, "Python", "pythoncore-3.14-64", "python.exe"),
      joinForPlatform(platform, localAppData, "Programs", "Python", "Python314", "python.exe"),
      "python.exe",
      "python",
      "py",
    ].forEach(pushCandidate);
  } else {
    ["python3", "python"].forEach(pushCandidate);
  }
  return candidates;
}

export function buildPythonVersionArgs({
  candidate,
  platform = process.platform,
}) {
  return platform === "win32" && candidate === "py" ? ["-3.14", "--version"] : ["--version"];
}

export function buildPythonArgs({
  python,
  rawArgs,
  platform = process.platform,
}) {
  return platform === "win32" && python === "py" ? ["-3.14", ...rawArgs] : rawArgs;
}

export function findPython({
  cwd = frontendRoot,
  env = process.env,
  exists = existsSync,
  homeDir = os.homedir(),
  platform = process.platform,
  spawn = spawnSync,
} = {}) {
  for (const candidate of pythonCandidates({ env, homeDir, platform })) {
    const isPathLike = candidate.includes("/") || candidate.includes("\\");
    if (isPathLike && !exists(candidate)) {
      continue;
    }
    const result = spawn(candidate, buildPythonVersionArgs({ candidate, platform }), {
      cwd,
      env,
      stdio: "ignore",
      shell: false,
    });
    if (result.status === 0) {
      return candidate;
    }
  }
  return null;
}

export function runPythonCli({
  cwd = frontendRoot,
  env = process.env,
  exists = existsSync,
  homeDir = os.homedir(),
  platform = process.platform,
  rawArgs = process.argv.slice(2),
  spawn = spawnSync,
} = {}) {
  const python = findPython({
    cwd,
    env,
    exists,
    homeDir,
    platform,
    spawn,
  });
  if (!python) {
    return {
      exitCode: 1,
      errorMessage: "Failed to locate a usable Python interpreter for desktop build tooling.",
    };
  }

  const result = spawn(python, buildPythonArgs({ python, rawArgs, platform }), {
    cwd,
    env,
    stdio: "inherit",
    shell: false,
  });

  if (result.error) {
    return {
      exitCode: 1,
      errorMessage: `Failed to launch Python: ${result.error.message}`,
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
  const result = runPythonCli();
  if (result.errorMessage) {
    console.error(result.errorMessage);
  }
  process.exit(result.exitCode);
}
