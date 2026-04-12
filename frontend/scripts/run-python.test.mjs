// @vitest-environment node

import { describe, expect, it, vi } from "vitest";

import {
  buildPythonArgs,
  buildPythonVersionArgs,
  findPython,
  pythonCandidates,
  runPythonCli,
} from "./run-python.mjs";

describe("run-python", () => {
  it("prefers an explicit GOAT_DESKTOP_PYTHON on Windows", () => {
    const candidates = pythonCandidates({
      env: {
        GOAT_DESKTOP_PYTHON: "C:\\Python314\\python.exe",
        LOCALAPPDATA: "C:\\Users\\goat\\AppData\\Local",
      },
      homeDir: "C:\\Users\\goat",
      platform: "win32",
    });

    expect(candidates[0]).toBe("C:\\Python314\\python.exe");
  });

  it("prefers actions/setup-python interpreter paths on Windows runners", () => {
    const candidates = pythonCandidates({
      env: {
        pythonLocation: "C:\\hostedtoolcache\\windows\\Python\\3.14.3\\x64",
        Python3_ROOT_DIR: "C:\\hostedtoolcache\\windows\\Python\\3.14.3\\x64",
        LOCALAPPDATA: "C:\\Users\\goat\\AppData\\Local",
      },
      homeDir: "C:\\Users\\goat",
      platform: "win32",
    });

    expect(candidates[0]).toBe("C:\\hostedtoolcache\\windows\\Python\\3.14.3\\x64\\python.exe");
    expect(
      candidates.filter(candidate => candidate === "C:\\hostedtoolcache\\windows\\Python\\3.14.3\\x64\\python.exe"),
    ).toHaveLength(1);
    expect(candidates).toContain("python.exe");
  });

  it("uses py launcher version args on Windows", () => {
    expect(buildPythonVersionArgs({ candidate: "py", platform: "win32" })).toEqual([
      "-3.14",
      "--version",
    ]);
    expect(buildPythonArgs({ python: "py", rawArgs: ["tool.py"], platform: "win32" })).toEqual([
      "-3.14",
      "tool.py",
    ]);
  });

  it("skips missing path-like candidates and returns the first usable interpreter", () => {
    const spawn = vi
      .fn()
      .mockReturnValueOnce({ status: 1 })
      .mockReturnValueOnce({ status: 0 });

    const found = findPython({
      cwd: "/repo/frontend",
      env: { LOCALAPPDATA: "C:\\Users\\goat\\AppData\\Local" },
      exists: candidate => !candidate.includes("pythoncore-3.14-64"),
      homeDir: "C:\\Users\\goat",
      platform: "win32",
      spawn,
    });

    expect(found).toBe("python.exe");
    expect(spawn).toHaveBeenNthCalledWith(
      1,
      "C:\\Users\\goat\\AppData\\Local\\Programs\\Python\\Python314\\python.exe",
      ["--version"],
      expect.objectContaining({
        cwd: "/repo/frontend",
        env: { LOCALAPPDATA: "C:\\Users\\goat\\AppData\\Local" },
        shell: false,
        stdio: "ignore",
      }),
    );
    expect(spawn).toHaveBeenNthCalledWith(
      2,
      "python.exe",
      ["--version"],
      expect.objectContaining({
        cwd: "/repo/frontend",
        env: { LOCALAPPDATA: "C:\\Users\\goat\\AppData\\Local" },
        shell: false,
        stdio: "ignore",
      }),
    );
  });

  it("returns an actionable error when no interpreter is found", () => {
    const result = runPythonCli({
      cwd: "/repo/frontend",
      env: {},
      exists: () => false,
      homeDir: "/home/goat",
      platform: "linux",
      rawArgs: ["../tools/desktop/build_desktop_sidecar.py"],
      spawn: vi.fn().mockReturnValue({ status: 1 }),
    });

    expect(result).toEqual({
      exitCode: 1,
      errorMessage: "Failed to locate a usable Python interpreter for desktop build tooling.",
    });
  });

  it("executes with the resolved interpreter and preserves raw args", () => {
    const spawn = vi
      .fn()
      .mockReturnValueOnce({ status: 0 })
      .mockReturnValueOnce({ status: 0 });

    const result = runPythonCli({
      cwd: "/repo/frontend",
      env: {},
      exists: () => true,
      homeDir: "/home/goat",
      platform: "linux",
      rawArgs: ["../tools/desktop/build_desktop_sidecar.py", "--clean"],
      spawn,
    });

    expect(result).toEqual({ exitCode: 0 });
    expect(spawn).toHaveBeenNthCalledWith(
      2,
      "python3",
      ["../tools/desktop/build_desktop_sidecar.py", "--clean"],
      expect.objectContaining({
        cwd: "/repo/frontend",
        env: {},
        shell: false,
        stdio: "inherit",
      }),
    );
  });

  it("surfaces launch failures from spawn", () => {
    const spawn = vi
      .fn()
      .mockReturnValueOnce({ status: 0 })
      .mockReturnValueOnce({ status: null, error: new Error("boom") });

    const result = runPythonCli({
      cwd: "/repo/frontend",
      env: {},
      exists: () => true,
      homeDir: "/home/goat",
      platform: "linux",
      rawArgs: ["tool.py"],
      spawn,
    });

    expect(result).toEqual({
      exitCode: 1,
      errorMessage: "Failed to launch Python: boom",
    });
  });
});
