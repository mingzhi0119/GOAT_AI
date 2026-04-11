#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    path::Path,
    process::Child,
    sync::{Arc, Mutex},
    thread,
    time::{Duration, Instant},
};
#[cfg(debug_assertions)]
use std::{
    path::PathBuf,
    process::{Command, Stdio},
};

use tauri::Manager;
#[cfg(not(debug_assertions))]
use std::fs;
#[cfg(not(debug_assertions))]
use tauri_plugin_shell::{process::CommandChild, process::CommandEvent, ShellExt};

const DEFAULT_BACKEND_HOST: &str = "127.0.0.1";
const DEFAULT_BACKEND_PORT: &str = "62606";
const HEALTH_TIMEOUT_SEC: u64 = 25;

#[derive(Clone, Default)]
struct BackendProcessState(Arc<Mutex<Option<BackendProcessHandle>>>);

enum BackendProcessHandle {
    Dev(Child),
    #[cfg(not(debug_assertions))]
    Release(CommandChild),
}

fn backend_host() -> String {
    std::env::var("GOAT_DESKTOP_BACKEND_HOST")
        .ok()
        .and_then(|value| {
            let trimmed = value.trim().to_string();
            if trimmed.is_empty() {
                None
            } else {
                Some(trimmed)
            }
        })
        .unwrap_or_else(|| DEFAULT_BACKEND_HOST.to_string())
}

fn backend_port() -> String {
    std::env::var("GOAT_DESKTOP_BACKEND_PORT")
        .ok()
        .and_then(|value| {
            let trimmed = value.trim().to_string();
            if trimmed.is_empty() {
                None
            } else {
                Some(trimmed)
            }
        })
        .unwrap_or_else(|| DEFAULT_BACKEND_PORT.to_string())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendProcessState::default())
        .setup(|app| {
            let backend_host = backend_host();
            let backend_port = backend_port();
            let window = app
                .get_webview_window("main")
                .ok_or("missing desktop main window")?;
            let health_url = format!("http://{}:{}/api/health", backend_host, backend_port);

            match spawn_backend(app.handle()) {
                Ok(child) => {
                    let state = app.state::<BackendProcessState>().inner().clone();
                    if let Ok(mut slot) = state.0.lock() {
                        *slot = Some(child);
                    }
                    let app_handle = app.handle().clone();
                    thread::spawn(move || {
                        wait_for_backend(&health_url, Duration::from_secs(HEALTH_TIMEOUT_SEC));
                        if let Some(window) = app_handle.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    });
                }
                Err(err) => {
                    eprintln!("GOAT desktop failed to start backend: {err}");
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }

            Ok(())
        })
        .on_window_event(|window, event| {
            if matches!(event, tauri::WindowEvent::Destroyed) {
                let state = window.app_handle().state::<BackendProcessState>().inner().clone();
                let lock_result = state.0.lock();
                if let Ok(mut slot) = lock_result {
                    if let Some(child) = slot.take() {
                        child.kill();
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running GOAT AI desktop shell");
}

impl BackendProcessHandle {
    fn kill(self) {
        match self {
            Self::Dev(mut child) => {
                let _ = child.kill();
            }
            #[cfg(not(debug_assertions))]
            Self::Release(child) => {
                let _ = child.kill();
            }
        }
    }
}

fn spawn_backend<R: tauri::Runtime>(
    app_handle: &tauri::AppHandle<R>,
) -> Result<BackendProcessHandle, String> {
    #[cfg(debug_assertions)]
    {
        let _ = app_handle;
        spawn_dev_backend().map(BackendProcessHandle::Dev)
    }

    #[cfg(not(debug_assertions))]
    {
        spawn_release_backend(app_handle).map(BackendProcessHandle::Release)
    }
}

#[cfg(debug_assertions)]
fn spawn_dev_backend() -> Result<Child, String> {
    let repo_root =
        repo_root().ok_or_else(|| "could not resolve GOAT AI repository root".to_string())?;
    let python_candidates = python_candidates();
    let mut errors: Vec<String> = Vec::new();
    let backend_host = backend_host();
    let backend_port = backend_port();

    for candidate in python_candidates {
        let mut command = Command::new(&candidate);
        command
            .current_dir(&repo_root)
            .args([
                "-m",
                "uvicorn",
                "server:app",
                "--host",
                &backend_host,
                "--port",
                &backend_port,
            ])
            .env("GOAT_SERVER_PORT", &backend_port)
            .env("GOAT_LOCAL_PORT", &backend_port)
            .stdin(Stdio::null())
            .stdout(Stdio::inherit())
            .stderr(Stdio::inherit());

        match command.spawn() {
            Ok(child) => return Ok(child),
            Err(err) => errors.push(format!("{candidate}: {err}")),
        }
    }

    Err(format!(
        "no backend launcher succeeded; tried {}",
        errors.join(", ")
    ))
}

#[cfg(debug_assertions)]
fn python_candidates() -> Vec<String> {
    if let Ok(explicit) = std::env::var("GOAT_DESKTOP_BACKEND_PYTHON") {
        let trimmed = explicit.trim();
        if !trimmed.is_empty() {
            return vec![trimmed.to_string()];
        }
    }

    #[cfg(target_os = "windows")]
    {
        vec!["python".into(), "py".into()]
    }

    #[cfg(not(target_os = "windows"))]
    {
        vec!["python3".into(), "python".into()]
    }
}

#[cfg(debug_assertions)]
fn repo_root() -> Option<PathBuf> {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let frontend_root = manifest_dir.parent()?;
    let repo_root = frontend_root.parent()?;
    Some(repo_root.to_path_buf())
}

fn wait_for_backend(health_url: &str, timeout: Duration) {
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        if backend_ready(health_url) {
            return;
        }
        thread::sleep(Duration::from_millis(350));
    }
}

fn backend_ready(health_url: &str) -> bool {
    match reqwest::blocking::get(health_url) {
        Ok(response) => response.status().is_success(),
        Err(_) => false,
    }
}

#[allow(dead_code)]
fn _path_exists(path: &Path) -> bool {
    path.exists()
}

#[cfg(not(debug_assertions))]
fn spawn_release_backend<R: tauri::Runtime>(
    app_handle: &tauri::AppHandle<R>,
) -> Result<CommandChild, String> {
    let backend_host = backend_host();
    let backend_port = backend_port();
    let data_root = app_handle
        .path()
        .app_local_data_dir()
        .map_err(|err| format!("could not resolve app data dir: {err}"))?;
    let logs_dir = app_handle
        .path()
        .app_log_dir()
        .map_err(|err| format!("could not resolve app log dir: {err}"))?;
    fs::create_dir_all(&data_root)
        .map_err(|err| format!("could not create app data dir {}: {err}", data_root.display()))?;
    fs::create_dir_all(&logs_dir)
        .map_err(|err| format!("could not create app log dir {}: {err}", logs_dir.display()))?;

    let mut sidecar = app_handle
        .shell()
        .sidecar("goat-backend")
        .map_err(|err| format!("could not resolve bundled backend sidecar: {err}"))?;

    sidecar = sidecar
        .args(["--host", &backend_host, "--port", &backend_port])
        .env("GOAT_DESKTOP_APP_DATA_DIR", data_root.as_os_str())
        .env("GOAT_LOG_PATH", data_root.join("chat_logs.db").as_os_str())
        .env("GOAT_DATA_DIR", data_root.join("data").as_os_str())
        .env("GOAT_SERVER_PORT", &backend_port)
        .env("GOAT_LOCAL_PORT", &backend_port)
        .env("GOAT_DEPLOY_TARGET", "local");

    let (mut rx, child) = sidecar
        .spawn()
        .map_err(|err| format!("failed to spawn bundled backend sidecar: {err}"))?;

    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    eprintln!("GOAT backend stdout: {}", String::from_utf8_lossy(&line));
                }
                CommandEvent::Stderr(line) => {
                    eprintln!("GOAT backend stderr: {}", String::from_utf8_lossy(&line));
                }
                _ => {}
            }
        }
    });

    Ok(child)
}
