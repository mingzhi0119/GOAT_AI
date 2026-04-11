import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import os from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const frontendRoot = join(scriptDir, "..");
const cargoBinDir = process.env.CARGO_HOME
  ? join(process.env.CARGO_HOME, "bin")
  : join(os.homedir(), ".cargo", "bin");
const nodeBinDir = dirname(process.execPath);
const pathSeparator = process.platform === "win32" ? ";" : ":";
const env = { ...process.env };

const pathPrefixes = [];
if (existsSync(nodeBinDir)) {
  pathPrefixes.push(nodeBinDir);
}
if (existsSync(cargoBinDir)) {
  pathPrefixes.push(cargoBinDir);
}
if (pathPrefixes.length > 0) {
  const prefix = pathPrefixes.join(pathSeparator);
  env.PATH = env.PATH ? `${prefix}${pathSeparator}${env.PATH}` : prefix;
}

const tauriScript = join(
  frontendRoot,
  "node_modules",
  "@tauri-apps",
  "cli",
  "tauri.js",
);

const result = spawnSync(process.execPath, [tauriScript, ...process.argv.slice(2)], {
  cwd: frontendRoot,
  env,
  stdio: "inherit",
});

if (result.error) {
  console.error(`Failed to launch Tauri CLI: ${result.error.message}`);
  process.exit(1);
}

process.exit(result.status ?? 1);
