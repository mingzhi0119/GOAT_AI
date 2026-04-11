// @vitest-environment node

import { describe, expect, it, vi } from "vitest";

import {
  buildPathPrefixes,
  buildTauriEnv,
  resolveTauriScript,
  runTauriCli,
} from "./run-tauri.mjs";

describe("run-tauri", () => {
  it("builds PATH prefixes from node and cargo bins", () => {
    const prefixes = buildPathPrefixes({
      env: { CARGO_HOME: "/custom-cargo" },
      exists: target => target === "/runtime" || target === "/custom-cargo/bin",
      execPath: "/runtime/node",
      homeDir: "/home/goat",
      platform: "linux",
    });

    expect(prefixes).toEqual(["/runtime", "/custom-cargo/bin"]);
  });

  it("prepends PATH entries using the platform separator", () => {
    const env = buildTauriEnv({
      env: { PATH: "/usr/bin" },
      exists: () => true,
      execPath: "/runtime/node",
      homeDir: "/home/goat",
      platform: "linux",
    });

    expect(env.PATH).toBe("/runtime:/home/goat/.cargo/bin:/usr/bin");
  });

  it("resolves the tauri CLI path under node_modules", () => {
    expect(resolveTauriScript({ cwd: "/repo/frontend", platform: "linux" })).toBe(
      "/repo/frontend/node_modules/@tauri-apps/cli/tauri.js",
    );
  });

  it("spawns the tauri CLI with the node executable and raw args", () => {
    const spawn = vi.fn().mockReturnValue({ status: 0 });

    const result = runTauriCli({
      cwd: "/repo/frontend",
      env: { PATH: "/usr/bin" },
      exists: () => true,
      execPath: "/runtime/node",
      homeDir: "/home/goat",
      platform: "linux",
      rawArgs: ["build", "--config", "src-tauri/tauri.conf.json"],
      spawn,
    });

    expect(result).toEqual({ exitCode: 0 });
    expect(spawn).toHaveBeenCalledWith(
      "/runtime/node",
      [
        "/repo/frontend/node_modules/@tauri-apps/cli/tauri.js",
        "build",
        "--config",
        "src-tauri/tauri.conf.json",
      ],
      expect.objectContaining({
        cwd: "/repo/frontend",
        stdio: "inherit",
        env: expect.objectContaining({
          PATH: "/runtime:/home/goat/.cargo/bin:/usr/bin",
        }),
      }),
    );
  });

  it("surfaces launch errors from the tauri spawn", () => {
    const result = runTauriCli({
      cwd: "/repo/frontend",
      env: {},
      exists: () => true,
      execPath: "/runtime/node",
      homeDir: "/home/goat",
      platform: "linux",
      rawArgs: ["dev"],
      spawn: vi.fn().mockReturnValue({ status: null, error: new Error("tauri missing") }),
    });

    expect(result).toEqual({
      exitCode: 1,
      errorMessage: "Failed to launch Tauri CLI: tauri missing",
    });
  });
});
