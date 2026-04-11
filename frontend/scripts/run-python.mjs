import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import os from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const frontendRoot = join(scriptDir, "..");

function pythonCandidates() {
  const candidates = [];
  const explicit = process.env.GOAT_DESKTOP_PYTHON?.trim();
  if (explicit) {
    candidates.push(explicit);
  }
  if (process.platform === "win32") {
    const localAppData = process.env.LOCALAPPDATA || join(os.homedir(), "AppData", "Local");
    candidates.push(
      join(localAppData, "Python", "pythoncore-3.14-64", "python.exe"),
      join(localAppData, "Programs", "Python", "Python314", "python.exe"),
      "python",
      "py",
    );
  } else {
    candidates.push("python3", "python");
  }
  return candidates;
}

function findPython() {
  for (const candidate of pythonCandidates()) {
    const isPathLike = candidate.includes("/") || candidate.includes("\\");
    if (isPathLike && !existsSync(candidate)) {
      continue;
    }
    const versionArgs = process.platform === "win32" && candidate === "py" ? ["-3.14", "--version"] : ["--version"];
    const result = spawnSync(candidate, versionArgs, {
      cwd: frontendRoot,
      stdio: "ignore",
      shell: false,
    });
    if (result.status === 0) {
      return candidate;
    }
  }
  return null;
}

const python = findPython();
if (!python) {
  console.error("Failed to locate a usable Python interpreter for desktop build tooling.");
  process.exit(1);
}

const rawArgs = process.argv.slice(2);
const pythonArgs =
  process.platform === "win32" && python === "py"
    ? ["-3.14", ...rawArgs]
    : rawArgs;

const result = spawnSync(python, pythonArgs, {
  cwd: frontendRoot,
  stdio: "inherit",
  shell: false,
});

if (result.error) {
  console.error(`Failed to launch Python: ${result.error.message}`);
  process.exit(1);
}

process.exit(result.status ?? 1);
