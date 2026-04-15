#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    path::Path,
    sync::{
        atomic::{AtomicBool, AtomicU8, Ordering},
        Arc, Mutex,
    },
    thread,
    time::{Duration, Instant},
};
#[cfg(debug_assertions)]
use std::{
    path::PathBuf,
    process::{Child, Command, Stdio},
};

#[cfg(not(debug_assertions))]
use std::{
    fs::{self, OpenOptions},
    io::Write,
    path::PathBuf,
};
use tauri::Manager;
#[cfg(not(debug_assertions))]
use tauri_plugin_shell::{process::CommandChild, process::CommandEvent, ShellExt};

const DEFAULT_BACKEND_HOST: &str = "127.0.0.1";
const DEFAULT_BACKEND_PORT: &str = "62606";
const HEALTH_TIMEOUT_SEC: u64 = 25;
const FRONTEND_BOOTSTRAP_TIMEOUT_SEC: u64 = 15;
const PRE_READY_RESTART_LIMIT: usize = 2;
const PRE_READY_RESTART_BACKOFF_MS: u64 = 750;
const INTERNAL_TEST_FLAG: &str = "GOAT_DESKTOP_INTERNAL_TEST";
const INTERNAL_TEST_HEALTH_TIMEOUT_SEC_ENV: &str = "GOAT_DESKTOP_INTERNAL_TEST_HEALTH_TIMEOUT_SEC";
const INTERNAL_TEST_PRE_READY_RESTART_LIMIT_ENV: &str =
    "GOAT_DESKTOP_INTERNAL_TEST_PRE_READY_RESTART_LIMIT";
const INTERNAL_TEST_PRE_READY_BACKOFF_MS_ENV: &str =
    "GOAT_DESKTOP_INTERNAL_TEST_PRE_READY_BACKOFF_MS";
#[cfg_attr(debug_assertions, allow(dead_code))]
const DESKTOP_APP_DATA_DIR_ENV: &str = "GOAT_DESKTOP_APP_DATA_DIR";
const DESKTOP_SHELL_LOG_PATH_ENV: &str = "GOAT_DESKTOP_SHELL_LOG_PATH";
#[cfg_attr(debug_assertions, allow(dead_code))]
const LOG_DIR_ENV: &str = "GOAT_LOG_DIR";
const LOG_PATH_ENV: &str = "GOAT_LOG_PATH";
const DATA_DIR_ENV: &str = "GOAT_DATA_DIR";

#[derive(Clone, Default)]
struct BackendProcessState(Arc<Mutex<Option<BackendProcessHandle>>>);

#[derive(Clone, Default)]
struct BackendReadyState(Arc<AtomicBool>);

#[derive(Clone, Default)]
struct BackendShutdownState(Arc<AtomicBool>);

#[derive(Clone, Default)]
struct BackendStartupFailureState(Arc<AtomicBool>);

#[derive(Clone)]
struct FrontendBootstrapState(Arc<AtomicU8>);

impl Default for FrontendBootstrapState {
    fn default() -> Self {
        Self(Arc::new(AtomicU8::new(
            FrontendBootstrapStatus::Pending.as_u8(),
        )))
    }
}

enum BackendProcessHandle {
    #[cfg(debug_assertions)]
    Dev(Child),
    #[cfg(not(debug_assertions))]
    Release(CommandChild),
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum BackendStartupWaitOutcome {
    Ready,
    FailedEarly,
    TimedOut,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum BackendLaunchDisposition {
    ReuseExisting,
    SpawnNew,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum FrontendBootstrapStatus {
    Pending,
    Ready,
    Failed,
}

impl FrontendBootstrapStatus {
    fn as_u8(self) -> u8 {
        match self {
            Self::Pending => 0,
            Self::Ready => 1,
            Self::Failed => 2,
        }
    }

    fn from_u8(value: u8) -> Self {
        match value {
            1 => Self::Ready,
            2 => Self::Failed,
            _ => Self::Pending,
        }
    }

    fn from_str(value: &str) -> Option<Self> {
        match value.trim() {
            "ready" => Some(Self::Ready),
            "failed" => Some(Self::Failed),
            "pending" => Some(Self::Pending),
            _ => None,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum FrontendBootstrapWaitOutcome {
    Ready,
    Failed,
    TimedOut,
}

fn normalize_configured_value(value: Option<String>, default: &str) -> String {
    value
        .and_then(|raw| {
            let trimmed = raw.trim().to_string();
            if trimmed.is_empty() {
                None
            } else {
                Some(trimmed)
            }
        })
        .unwrap_or_else(|| default.to_string())
}

fn backend_host() -> String {
    normalize_configured_value(
        std::env::var("GOAT_DESKTOP_BACKEND_HOST").ok(),
        DEFAULT_BACKEND_HOST,
    )
}

fn backend_port() -> String {
    normalize_configured_value(
        std::env::var("GOAT_DESKTOP_BACKEND_PORT").ok(),
        DEFAULT_BACKEND_PORT,
    )
}

fn backend_health_url(host: &str, port: &str) -> String {
    format!("http://{}:{}/api/health", host, port)
}

fn existing_backend_reuse_diagnostic(health_url: &str) -> String {
    format!(
        "Reusing already-running GOAT desktop backend at {health_url} instead of spawning a second sidecar."
    )
}

fn startup_failure_diagnostic(stage: &str, health_url: &str, detail: Option<&str>) -> String {
    let mut message = format!(
        "GOAT desktop startup issue [{}]: backend health probe did not become ready at {}.",
        stage, health_url
    );
    if let Some(detail) = detail {
        let trimmed = detail.trim();
        if !trimmed.is_empty() {
            message.push_str(" Detail: ");
            message.push_str(trimmed);
        }
    }
    message
}

fn backend_termination_diagnostic(
    ready: bool,
    shutdown_requested: bool,
    code: Option<i32>,
    signal: Option<i32>,
    detail: Option<&str>,
) -> String {
    let lifecycle = if shutdown_requested {
        "terminated during desktop shutdown"
    } else if ready {
        "terminated after startup"
    } else {
        "terminated before startup completed"
    };
    let mut message = format!(
        "GOAT desktop backend sidecar {} (code={:?}, signal={:?}).",
        lifecycle, code, signal
    );
    if let Some(detail) = detail {
        let trimmed = detail.trim();
        if !trimmed.is_empty() {
            message.push_str(" Detail: ");
            message.push_str(trimmed);
        }
    }
    message
}

fn parse_positive_u64_override(raw: Option<String>) -> Option<u64> {
    raw.and_then(|value| {
        let trimmed = value.trim();
        if trimmed.is_empty() {
            return None;
        }
        trimmed.parse::<u64>().ok().filter(|parsed| *parsed > 0)
    })
}

fn internal_test_enabled() -> bool {
    matches!(std::env::var(INTERNAL_TEST_FLAG).ok().as_deref(), Some("1"))
}

fn internal_test_numeric_override(name: &str) -> Option<u64> {
    if !internal_test_enabled() {
        return None;
    }
    parse_positive_u64_override(std::env::var(name).ok())
}

fn configured_health_timeout_sec() -> u64 {
    internal_test_numeric_override(INTERNAL_TEST_HEALTH_TIMEOUT_SEC_ENV)
        .unwrap_or(HEALTH_TIMEOUT_SEC)
}

fn configured_pre_ready_restart_limit() -> usize {
    internal_test_numeric_override(INTERNAL_TEST_PRE_READY_RESTART_LIMIT_ENV)
        .and_then(|value| usize::try_from(value).ok())
        .unwrap_or(PRE_READY_RESTART_LIMIT)
}

fn configured_pre_ready_restart_backoff_ms() -> u64 {
    internal_test_numeric_override(INTERNAL_TEST_PRE_READY_BACKOFF_MS_ENV)
        .unwrap_or(PRE_READY_RESTART_BACKOFF_MS)
}

fn pre_ready_restart_backoff(attempt_index: usize) -> Duration {
    Duration::from_millis((attempt_index as u64) * configured_pre_ready_restart_backoff_ms())
}

fn terminate_desktop_process<R: tauri::Runtime>(app_handle: &tauri::AppHandle<R>, exit_code: i32) {
    #[cfg(not(debug_assertions))]
    {
        app_handle.cleanup_before_exit();
        std::process::exit(exit_code);
    }

    #[cfg(debug_assertions)]
    {
        app_handle.exit(exit_code);
    }
}

fn activate_existing_main_window_with<F, G>(mut show: F, mut focus: G) -> bool
where
    F: FnMut(),
    G: FnMut(),
{
    show();
    focus();
    true
}

fn reveal_main_window<R: tauri::Runtime>(app_handle: &tauri::AppHandle<R>) -> bool {
    if let Some(window) = app_handle.get_webview_window("main") {
        return activate_existing_main_window_with(
            || {
                let _ = window.show();
            },
            || {
                let _ = window.set_focus();
            },
        );
    }
    false
}

fn store_frontend_bootstrap_status(
    state: &FrontendBootstrapState,
    status: FrontendBootstrapStatus,
) {
    state.0.store(status.as_u8(), Ordering::SeqCst);
}

fn load_frontend_bootstrap_status(state: &FrontendBootstrapState) -> FrontendBootstrapStatus {
    FrontendBootstrapStatus::from_u8(state.0.load(Ordering::SeqCst))
}

fn frontend_bootstrap_timeout_diagnostic() -> String {
    format!(
        "GOAT desktop startup issue [frontend_bootstrap_timeout]: frontend bootstrap did not report ready or failed within {} seconds; revealing the main window as a fallback.",
        FRONTEND_BOOTSTRAP_TIMEOUT_SEC
    )
}

fn store_backend_process(state: &BackendProcessState, child: BackendProcessHandle) {
    if let Ok(mut slot) = state.0.lock() {
        *slot = Some(child);
    }
}

fn resolve_backend_launch_disposition_with_probe<F>(
    mut backend_ready_probe: F,
) -> BackendLaunchDisposition
where
    F: FnMut() -> bool,
{
    if backend_ready_probe() {
        BackendLaunchDisposition::ReuseExisting
    } else {
        BackendLaunchDisposition::SpawnNew
    }
}

fn resolve_backend_launch_disposition(health_url: &str) -> BackendLaunchDisposition {
    resolve_backend_launch_disposition_with_probe(|| backend_ready(health_url))
}

fn stop_active_backend_process(state: &BackendProcessState) {
    if let Ok(mut slot) = state.0.lock() {
        if let Some(child) = slot.take() {
            child.kill();
        }
    }
}

fn next_retry_detail(current_attempt_index: usize, total_attempts: usize) -> Option<String> {
    if current_attempt_index + 1 >= total_attempts {
        return None;
    }
    let next_attempt = current_attempt_index + 2;
    let backoff = pre_ready_restart_backoff(current_attempt_index + 1);
    Some(format!(
        "Retrying before window reveal after {} ms backoff (next attempt {}/{}).",
        backoff.as_millis(),
        next_attempt,
        total_attempts
    ))
}

fn configured_path_override(name: &str) -> Option<PathBuf> {
    std::env::var(name).ok().and_then(|value| {
        let trimmed = value.trim();
        if trimmed.is_empty() {
            None
        } else {
            Some(PathBuf::from(trimmed))
        }
    })
}

fn configured_log_db_path(data_root: &Path) -> PathBuf {
    configured_path_override(LOG_PATH_ENV).unwrap_or_else(|| data_root.join("chat_logs.db"))
}

fn configured_data_dir(data_root: &Path) -> PathBuf {
    configured_path_override(DATA_DIR_ENV).unwrap_or_else(|| data_root.join("data"))
}

#[cfg(not(debug_assertions))]
fn desktop_log_path(logs_dir: &Path) -> PathBuf {
    logs_dir.join("desktop-shell.log")
}

fn configured_desktop_log_path(default_log_path: &Path) -> PathBuf {
    configured_path_override(DESKTOP_SHELL_LOG_PATH_ENV)
        .unwrap_or_else(|| default_log_path.to_path_buf())
}

#[cfg(not(debug_assertions))]
fn append_desktop_log(log_path: &Path, message: &str) {
    if let Some(parent) = log_path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(log_path) {
        let _ = writeln!(file, "{}", message.trim_end());
    }
}

#[cfg(debug_assertions)]
fn append_desktop_log(_log_path: &Path, _message: &str) {}

#[cfg(not(debug_assertions))]
fn resolve_release_data_root<R: tauri::Runtime>(
    app_handle: &tauri::AppHandle<R>,
) -> Result<PathBuf, String> {
    let data_root = configured_path_override(DESKTOP_APP_DATA_DIR_ENV)
        .or_else(|| app_handle.path().app_local_data_dir().ok())
        .ok_or_else(|| "could not resolve app data dir".to_string())?;
    fs::create_dir_all(&data_root).map_err(|err| {
        format!(
            "could not create app data dir {}: {err}",
            data_root.display()
        )
    })?;
    Ok(data_root)
}

#[cfg(not(debug_assertions))]
fn resolve_release_log_dir<R: tauri::Runtime>(
    app_handle: &tauri::AppHandle<R>,
) -> Result<PathBuf, String> {
    let logs_dir = configured_path_override(LOG_DIR_ENV)
        .or_else(|| app_handle.path().app_log_dir().ok())
        .ok_or_else(|| "could not resolve app log dir".to_string())?;
    fs::create_dir_all(&logs_dir)
        .map_err(|err| format!("could not create app log dir {}: {err}", logs_dir.display()))?;
    Ok(logs_dir)
}

#[cfg(not(debug_assertions))]
fn resolve_desktop_log_path<R: tauri::Runtime>(
    app_handle: &tauri::AppHandle<R>,
) -> Result<PathBuf, String> {
    let logs_dir = resolve_release_log_dir(app_handle)?;
    let log_path = configured_desktop_log_path(&desktop_log_path(&logs_dir));
    if let Some(parent) = log_path.parent() {
        fs::create_dir_all(parent)
            .map_err(|err| format!("could not create app log dir {}: {err}", parent.display()))?;
    }
    Ok(log_path)
}

fn arm_frontend_bootstrap_window_reveal<R: tauri::Runtime>(
    app_handle: tauri::AppHandle<R>,
    frontend_bootstrap_state: FrontendBootstrapState,
    shutdown_state: BackendShutdownState,
    desktop_log_path: Option<PathBuf>,
) {
    thread::spawn(move || {
        let outcome = wait_for_frontend_bootstrap(
            Duration::from_secs(FRONTEND_BOOTSTRAP_TIMEOUT_SEC),
            &frontend_bootstrap_state,
        );
        if shutdown_state.0.load(Ordering::SeqCst) {
            return;
        }
        if matches!(outcome, FrontendBootstrapWaitOutcome::TimedOut) {
            let diagnostic = frontend_bootstrap_timeout_diagnostic();
            if let Some(log_path) = desktop_log_path.as_ref() {
                append_desktop_log(log_path, &diagnostic);
            }
            eprintln!("{diagnostic}");
        }
        reveal_main_window(&app_handle);
    });
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _argv, _cwd| {
            reveal_main_window(app);
        }))
        .plugin(tauri_plugin_shell::init())
        .manage(BackendProcessState::default())
        .manage(BackendReadyState::default())
        .manage(BackendShutdownState::default())
        .manage(BackendStartupFailureState::default())
        .manage(FrontendBootstrapState::default())
        .invoke_handler(tauri::generate_handler![report_frontend_bootstrap_status])
        .setup(|app| {
            let backend_host = backend_host();
            let backend_port = backend_port();
            app.get_webview_window("main")
                .ok_or_else(|| "missing desktop main window".to_string())?;
            let health_url = backend_health_url(&backend_host, &backend_port);
            #[cfg(not(debug_assertions))]
            let packaged_desktop_log_path = Some(resolve_desktop_log_path(app.handle())?);
            #[cfg(debug_assertions)]
            let packaged_desktop_log_path: Option<PathBuf> = None;
            let process_state = app.state::<BackendProcessState>().inner().clone();
            let ready_state = app.state::<BackendReadyState>().inner().clone();
            let shutdown_state = app.state::<BackendShutdownState>().inner().clone();
            let startup_failure_state = app.state::<BackendStartupFailureState>().inner().clone();
            let frontend_bootstrap_state = app.state::<FrontendBootstrapState>().inner().clone();
            let app_handle = app.handle().clone();
            let desktop_log_path = packaged_desktop_log_path.clone();
            thread::spawn(move || {
                let total_attempts = configured_pre_ready_restart_limit() + 1;
                for attempt_index in 0..total_attempts {
                    if shutdown_state.0.load(Ordering::SeqCst) {
                        stop_active_backend_process(&process_state);
                        return;
                    }
                    startup_failure_state.0.store(false, Ordering::SeqCst);
                    store_frontend_bootstrap_status(
                        &frontend_bootstrap_state,
                        FrontendBootstrapStatus::Pending,
                    );

                    if matches!(
                        resolve_backend_launch_disposition(&health_url),
                        BackendLaunchDisposition::ReuseExisting
                    ) {
                        let diagnostic = existing_backend_reuse_diagnostic(&health_url);
                        if let Some(log_path) = desktop_log_path.as_ref() {
                            append_desktop_log(log_path, &diagnostic);
                        }
                        eprintln!("{diagnostic}");
                        ready_state.0.store(true, Ordering::SeqCst);
                        arm_frontend_bootstrap_window_reveal(
                            app_handle.clone(),
                            frontend_bootstrap_state.clone(),
                            shutdown_state.clone(),
                            desktop_log_path.clone(),
                        );
                        return;
                    }

                    match spawn_backend(&app_handle) {
                        Ok(child) => store_backend_process(&process_state, child),
                        Err(err) => {
                            let detail = match next_retry_detail(attempt_index, total_attempts) {
                                Some(retry) => format!("{err} {retry}"),
                                None => err,
                            };
                            let diagnostic = startup_failure_diagnostic(
                                "backend_spawn_failed",
                                &health_url,
                                Some(&detail),
                            );
                            if let Some(log_path) = desktop_log_path.as_ref() {
                                append_desktop_log(log_path, &diagnostic);
                            }
                            eprintln!("{diagnostic}");
                            if attempt_index + 1 >= total_attempts {
                                terminate_desktop_process(&app_handle, 1);
                                return;
                            }
                            thread::sleep(pre_ready_restart_backoff(attempt_index + 1));
                            continue;
                        }
                    }

                    match wait_for_backend_startup(
                        &health_url,
                        Duration::from_secs(configured_health_timeout_sec()),
                        &startup_failure_state,
                    ) {
                        BackendStartupWaitOutcome::Ready => {
                            ready_state.0.store(true, Ordering::SeqCst);
                            arm_frontend_bootstrap_window_reveal(
                                app_handle.clone(),
                                frontend_bootstrap_state.clone(),
                                shutdown_state.clone(),
                                desktop_log_path.clone(),
                            );
                            return;
                        }
                        BackendStartupWaitOutcome::FailedEarly => {
                            stop_active_backend_process(&process_state);
                            let detail =
                                match next_retry_detail(attempt_index, total_attempts) {
                                    Some(retry) => format!(
                                        "Bundled backend exited before readiness completed. {retry}"
                                    ),
                                    None => {
                                        "Bundled backend exited before readiness completed."
                                            .to_string()
                                    }
                                };
                            let diagnostic = startup_failure_diagnostic(
                                "backend_terminated_before_ready",
                                &health_url,
                                Some(&detail),
                            );
                            if let Some(log_path) = desktop_log_path.as_ref() {
                                append_desktop_log(log_path, &diagnostic);
                            }
                            eprintln!("{diagnostic}");
                            if attempt_index + 1 >= total_attempts {
                                terminate_desktop_process(&app_handle, 1);
                                return;
                            }
                            thread::sleep(pre_ready_restart_backoff(attempt_index + 1));
                        }
                        BackendStartupWaitOutcome::TimedOut => {
                            stop_active_backend_process(&process_state);
                            let detail =
                                match next_retry_detail(attempt_index, total_attempts) {
                                    Some(retry) => format!(
                                        "Timed out while waiting for the bundled backend to answer /api/health. {retry}"
                                    ),
                                    None => {
                                        "Timed out while waiting for the bundled backend to answer /api/health."
                                            .to_string()
                                    }
                                };
                            let diagnostic = startup_failure_diagnostic(
                                "health_wait_timeout",
                                &health_url,
                                Some(&detail),
                            );
                            if let Some(log_path) = desktop_log_path.as_ref() {
                                append_desktop_log(log_path, &diagnostic);
                            }
                            eprintln!("{diagnostic}");
                            if attempt_index + 1 >= total_attempts {
                                terminate_desktop_process(&app_handle, 1);
                                return;
                            }
                            thread::sleep(pre_ready_restart_backoff(attempt_index + 1));
                        }
                    }
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if matches!(event, tauri::WindowEvent::Destroyed) {
                let shutdown_state = window
                    .app_handle()
                    .state::<BackendShutdownState>()
                    .inner()
                    .clone();
                shutdown_state.0.store(true, Ordering::SeqCst);
                let state = window.app_handle().state::<BackendProcessState>().inner().clone();
                stop_active_backend_process(&state);
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running GOAT AI desktop shell");
}

impl BackendProcessHandle {
    fn kill(self) {
        match self {
            #[cfg(debug_assertions)]
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
                "server:create_app",
                "--factory",
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

#[allow(dead_code)]
fn wait_for_backend_with_probe<F>(timeout: Duration, interval: Duration, mut probe: F) -> bool
where
    F: FnMut() -> bool,
{
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        if probe() {
            return true;
        }
        thread::sleep(interval);
    }
    false
}

fn wait_for_backend_startup_with_probes<F, G>(
    timeout: Duration,
    interval: Duration,
    mut ready_probe: F,
    mut startup_failed: G,
) -> BackendStartupWaitOutcome
where
    F: FnMut() -> bool,
    G: FnMut() -> bool,
{
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        if ready_probe() {
            return BackendStartupWaitOutcome::Ready;
        }
        if startup_failed() {
            return BackendStartupWaitOutcome::FailedEarly;
        }
        thread::sleep(interval);
    }
    BackendStartupWaitOutcome::TimedOut
}

fn wait_for_backend_startup(
    health_url: &str,
    timeout: Duration,
    startup_failure_state: &BackendStartupFailureState,
) -> BackendStartupWaitOutcome {
    wait_for_backend_startup_with_probes(
        timeout,
        Duration::from_millis(350),
        || backend_ready(health_url),
        || startup_failure_state.0.load(Ordering::SeqCst),
    )
}

fn wait_for_frontend_bootstrap_with_probes<F>(
    timeout: Duration,
    interval: Duration,
    mut status_probe: F,
) -> FrontendBootstrapWaitOutcome
where
    F: FnMut() -> FrontendBootstrapStatus,
{
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        match status_probe() {
            FrontendBootstrapStatus::Ready => return FrontendBootstrapWaitOutcome::Ready,
            FrontendBootstrapStatus::Failed => return FrontendBootstrapWaitOutcome::Failed,
            FrontendBootstrapStatus::Pending => thread::sleep(interval),
        }
    }
    FrontendBootstrapWaitOutcome::TimedOut
}

fn wait_for_frontend_bootstrap(
    timeout: Duration,
    frontend_bootstrap_state: &FrontendBootstrapState,
) -> FrontendBootstrapWaitOutcome {
    wait_for_frontend_bootstrap_with_probes(timeout, Duration::from_millis(100), || {
        load_frontend_bootstrap_status(frontend_bootstrap_state)
    })
}

fn backend_ready(health_url: &str) -> bool {
    match reqwest::blocking::get(health_url) {
        Ok(response) => response.status().is_success(),
        Err(_) => false,
    }
}

#[tauri::command]
fn report_frontend_bootstrap_status(
    app_handle: tauri::AppHandle,
    frontend_bootstrap_state: tauri::State<'_, FrontendBootstrapState>,
    status: String,
) -> Result<(), String> {
    let parsed = FrontendBootstrapStatus::from_str(&status)
        .ok_or_else(|| format!("unsupported frontend bootstrap status: {status}"))?;
    store_frontend_bootstrap_status(frontend_bootstrap_state.inner(), parsed);
    if matches!(
        parsed,
        FrontendBootstrapStatus::Ready | FrontendBootstrapStatus::Failed
    ) {
        reveal_main_window(&app_handle);
    }
    Ok(())
}

#[allow(dead_code)]
fn _path_exists(path: &Path) -> bool {
    path.exists()
}

#[cfg(test)]
mod tests {
    use super::{
        activate_existing_main_window_with, backend_health_url, backend_termination_diagnostic,
        configured_data_dir, configured_desktop_log_path, configured_log_db_path,
        configured_path_override, existing_backend_reuse_diagnostic,
        frontend_bootstrap_timeout_diagnostic, load_frontend_bootstrap_status,
        normalize_configured_value, parse_positive_u64_override, pre_ready_restart_backoff,
        resolve_backend_launch_disposition_with_probe, startup_failure_diagnostic,
        store_frontend_bootstrap_status, wait_for_backend_startup_with_probes,
        wait_for_backend_with_probe, wait_for_frontend_bootstrap_with_probes,
        BackendLaunchDisposition, BackendStartupWaitOutcome, FrontendBootstrapState,
        FrontendBootstrapStatus, FrontendBootstrapWaitOutcome, DATA_DIR_ENV,
        DESKTOP_SHELL_LOG_PATH_ENV, LOG_PATH_ENV,
    };
    use std::{
        path::PathBuf,
        sync::{Arc, Mutex, OnceLock},
        time::Duration,
    };

    static ENV_LOCK: OnceLock<Mutex<()>> = OnceLock::new();

    fn env_lock() -> std::sync::MutexGuard<'static, ()> {
        ENV_LOCK
            .get_or_init(|| Mutex::new(()))
            .lock()
            .expect("failed to acquire test env lock")
    }

    fn snapshot_env(keys: &[&str]) -> Vec<(String, Option<String>)> {
        keys.iter()
            .map(|name| (name.to_string(), std::env::var(name).ok()))
            .collect()
    }

    fn restore_env(snapshot: Vec<(String, Option<String>)>) {
        for (name, value) in snapshot {
            match value {
                Some(value) => unsafe { std::env::set_var(name, value) },
                None => unsafe { std::env::remove_var(name) },
            }
        }
    }

    #[test]
    fn normalize_configured_value_trims_and_falls_back() {
        assert_eq!(
            normalize_configured_value(Some(" 127.0.0.1 ".into()), "fallback"),
            "127.0.0.1"
        );
        assert_eq!(
            normalize_configured_value(Some("   ".into()), "fallback"),
            "fallback"
        );
        assert_eq!(normalize_configured_value(None, "fallback"), "fallback");
    }

    #[test]
    fn backend_health_url_formats_expected_path() {
        assert_eq!(
            backend_health_url("127.0.0.1", "62606"),
            "http://127.0.0.1:62606/api/health"
        );
    }

    #[test]
    fn wait_for_backend_with_probe_succeeds_before_timeout() {
        let mut attempts = 0;
        let ready = wait_for_backend_with_probe(
            Duration::from_millis(50),
            Duration::from_millis(0),
            || {
                attempts += 1;
                attempts >= 3
            },
        );

        assert!(ready);
        assert_eq!(attempts, 3);
    }

    #[test]
    fn wait_for_backend_with_probe_times_out_when_probe_never_succeeds() {
        let ready =
            wait_for_backend_with_probe(Duration::from_millis(1), Duration::from_millis(0), || {
                false
            });

        assert!(!ready);
    }

    #[test]
    fn startup_failure_diagnostic_includes_stage_url_and_detail() {
        let message = startup_failure_diagnostic(
            "health_wait_timeout",
            "http://127.0.0.1:62606/api/health",
            Some("Timed out"),
        );

        assert!(message.contains("health_wait_timeout"));
        assert!(message.contains("http://127.0.0.1:62606/api/health"));
        assert!(message.contains("Timed out"));
    }

    #[test]
    fn configured_path_override_trims_and_rejects_blank_values() {
        let _guard = env_lock();
        let snapshot = snapshot_env(&[DESKTOP_SHELL_LOG_PATH_ENV]);
        unsafe {
            std::env::set_var(
                DESKTOP_SHELL_LOG_PATH_ENV,
                " C:/GOAT/logs/desktop-shell.log ",
            );
        }
        assert_eq!(
            configured_path_override(DESKTOP_SHELL_LOG_PATH_ENV),
            Some(PathBuf::from("C:/GOAT/logs/desktop-shell.log"))
        );

        unsafe {
            std::env::set_var(DESKTOP_SHELL_LOG_PATH_ENV, "   ");
        }
        assert_eq!(configured_path_override(DESKTOP_SHELL_LOG_PATH_ENV), None);

        unsafe {
            std::env::remove_var(DESKTOP_SHELL_LOG_PATH_ENV);
        }
        restore_env(snapshot);
    }

    #[test]
    fn configured_release_paths_prefer_explicit_runtime_overrides() {
        let _guard = env_lock();
        let snapshot = snapshot_env(&[LOG_PATH_ENV, DATA_DIR_ENV, DESKTOP_SHELL_LOG_PATH_ENV]);
        unsafe {
            std::env::set_var(LOG_PATH_ENV, "C:/GOAT/runtime/chat_logs.db");
            std::env::set_var(DATA_DIR_ENV, "C:/GOAT/runtime/data");
            std::env::set_var(
                DESKTOP_SHELL_LOG_PATH_ENV,
                "C:/GOAT/runtime/logs/desktop-shell.log",
            );
        }
        let data_root = PathBuf::from("C:/fallback");

        assert_eq!(
            configured_log_db_path(&data_root),
            PathBuf::from("C:/GOAT/runtime/chat_logs.db")
        );
        assert_eq!(
            configured_data_dir(&data_root),
            PathBuf::from("C:/GOAT/runtime/data")
        );
        assert_eq!(
            configured_desktop_log_path(&data_root.join("desktop-shell.log")),
            PathBuf::from("C:/GOAT/runtime/logs/desktop-shell.log")
        );

        unsafe {
            std::env::remove_var(LOG_PATH_ENV);
            std::env::remove_var(DATA_DIR_ENV);
            std::env::remove_var(DESKTOP_SHELL_LOG_PATH_ENV);
        }
        restore_env(snapshot);
    }

    #[test]
    fn backend_termination_diagnostic_distinguishes_startup_and_shutdown() {
        let startup =
            backend_termination_diagnostic(false, false, Some(1), None, Some("spawn failed"));
        let shutdown = backend_termination_diagnostic(true, true, Some(0), None, None);

        assert!(startup.contains("before startup completed"));
        assert!(startup.contains("spawn failed"));
        assert!(shutdown.contains("during desktop shutdown"));
    }

    #[test]
    fn pre_ready_restart_backoff_scales_with_attempt_number() {
        assert_eq!(pre_ready_restart_backoff(1), Duration::from_millis(750));
        assert_eq!(pre_ready_restart_backoff(2), Duration::from_millis(1500));
    }

    #[test]
    fn parse_positive_u64_override_accepts_positive_integers_only() {
        assert_eq!(parse_positive_u64_override(Some("5".into())), Some(5));
        assert_eq!(parse_positive_u64_override(Some(" 7 ".into())), Some(7));
        assert_eq!(parse_positive_u64_override(Some("0".into())), None);
        assert_eq!(parse_positive_u64_override(Some("".into())), None);
        assert_eq!(parse_positive_u64_override(Some("bad".into())), None);
        assert_eq!(parse_positive_u64_override(None), None);
    }

    #[test]
    fn wait_for_backend_startup_returns_failed_early_before_timeout() {
        let mut attempts = 0;
        let outcome = wait_for_backend_startup_with_probes(
            Duration::from_millis(50),
            Duration::from_millis(0),
            || false,
            || {
                attempts += 1;
                attempts >= 3
            },
        );

        assert_eq!(outcome, BackendStartupWaitOutcome::FailedEarly);
        assert_eq!(attempts, 3);
    }

    #[test]
    fn wait_for_backend_startup_returns_ready_when_probe_succeeds_first() {
        let outcome = wait_for_backend_startup_with_probes(
            Duration::from_millis(50),
            Duration::from_millis(0),
            || true,
            || false,
        );

        assert_eq!(outcome, BackendStartupWaitOutcome::Ready);
    }

    #[test]
    fn wait_for_backend_startup_times_out_when_neither_probe_trips() {
        let outcome = wait_for_backend_startup_with_probes(
            Duration::from_millis(1),
            Duration::from_millis(0),
            || false,
            || false,
        );

        assert_eq!(outcome, BackendStartupWaitOutcome::TimedOut);
    }

    #[test]
    fn frontend_bootstrap_status_round_trips_through_state() {
        let state = FrontendBootstrapState::default();

        assert_eq!(
            load_frontend_bootstrap_status(&state),
            FrontendBootstrapStatus::Pending
        );
        store_frontend_bootstrap_status(&state, FrontendBootstrapStatus::Ready);
        assert_eq!(
            load_frontend_bootstrap_status(&state),
            FrontendBootstrapStatus::Ready
        );
        store_frontend_bootstrap_status(&state, FrontendBootstrapStatus::Failed);
        assert_eq!(
            load_frontend_bootstrap_status(&state),
            FrontendBootstrapStatus::Failed
        );
    }

    #[test]
    fn wait_for_frontend_bootstrap_returns_ready_when_status_reports_ready() {
        let outcome = wait_for_frontend_bootstrap_with_probes(
            Duration::from_millis(50),
            Duration::from_millis(0),
            || FrontendBootstrapStatus::Ready,
        );

        assert_eq!(outcome, FrontendBootstrapWaitOutcome::Ready);
    }

    #[test]
    fn wait_for_frontend_bootstrap_returns_failed_when_status_reports_failed() {
        let mut attempts = 0;
        let outcome = wait_for_frontend_bootstrap_with_probes(
            Duration::from_millis(50),
            Duration::from_millis(0),
            || {
                attempts += 1;
                if attempts >= 3 {
                    FrontendBootstrapStatus::Failed
                } else {
                    FrontendBootstrapStatus::Pending
                }
            },
        );

        assert_eq!(outcome, FrontendBootstrapWaitOutcome::Failed);
    }

    #[test]
    fn wait_for_frontend_bootstrap_times_out_when_status_never_changes() {
        let outcome = wait_for_frontend_bootstrap_with_probes(
            Duration::from_millis(1),
            Duration::from_millis(0),
            || FrontendBootstrapStatus::Pending,
        );

        assert_eq!(outcome, FrontendBootstrapWaitOutcome::TimedOut);
    }

    #[test]
    fn backend_launch_disposition_reuses_existing_healthy_backend() {
        let disposition = resolve_backend_launch_disposition_with_probe(|| true);

        assert_eq!(disposition, BackendLaunchDisposition::ReuseExisting);
    }

    #[test]
    fn backend_launch_disposition_spawns_when_no_backend_is_ready() {
        let disposition = resolve_backend_launch_disposition_with_probe(|| false);

        assert_eq!(disposition, BackendLaunchDisposition::SpawnNew);
    }

    #[test]
    fn activate_existing_main_window_calls_show_and_focus() {
        let calls = Arc::new(Mutex::new(Vec::new()));
        let show_calls = calls.clone();
        let focus_calls = calls.clone();

        let activated = activate_existing_main_window_with(
            move || {
                show_calls.lock().expect("show calls lock").push("show");
            },
            move || {
                focus_calls.lock().expect("focus calls lock").push("focus");
            },
        );

        assert!(activated);
        assert_eq!(
            calls.lock().expect("calls lock").as_slice(),
            ["show", "focus"]
        );
    }

    #[test]
    fn frontend_bootstrap_timeout_diagnostic_mentions_fallback_window_reveal() {
        let message = frontend_bootstrap_timeout_diagnostic();

        assert!(message.contains("frontend_bootstrap_timeout"));
        assert!(message.contains("revealing the main window"));
    }

    #[test]
    fn existing_backend_reuse_diagnostic_mentions_reusing_running_backend() {
        let message = existing_backend_reuse_diagnostic("http://127.0.0.1:62606/api/health");

        assert!(message.contains("Reusing already-running GOAT desktop backend"));
        assert!(message.contains("http://127.0.0.1:62606/api/health"));
    }
}

#[cfg(not(debug_assertions))]
fn spawn_release_backend<R: tauri::Runtime>(
    app_handle: &tauri::AppHandle<R>,
) -> Result<CommandChild, String> {
    let backend_host = backend_host();
    let backend_port = backend_port();
    let data_root = resolve_release_data_root(app_handle)?;
    let logs_dir = resolve_release_log_dir(app_handle)?;
    let desktop_log = resolve_desktop_log_path(app_handle)?;
    let data_root_arg = data_root.to_string_lossy().to_string();
    let log_db_path = configured_log_db_path(&data_root);
    let data_dir = configured_data_dir(&data_root);
    append_desktop_log(&desktop_log, "Starting bundled backend sidecar.");

    let mut sidecar = app_handle
        .shell()
        .sidecar("goat-backend")
        .map_err(|err| format!("could not resolve bundled backend sidecar: {err}"))?;

    sidecar = sidecar
        .args([
            "--host",
            &backend_host,
            "--port",
            &backend_port,
            "--data-root",
            &data_root_arg,
        ])
        .env(DESKTOP_APP_DATA_DIR_ENV, data_root.as_os_str())
        .env("GOAT_RUNTIME_ROOT", data_root.as_os_str())
        .env(LOG_DIR_ENV, logs_dir.as_os_str())
        .env(LOG_PATH_ENV, log_db_path.as_os_str())
        .env(DATA_DIR_ENV, data_dir.as_os_str())
        .env(DESKTOP_SHELL_LOG_PATH_ENV, desktop_log.as_os_str())
        .env("GOAT_SERVER_PORT", &backend_port)
        .env("GOAT_LOCAL_PORT", &backend_port)
        .env("GOAT_DEPLOY_MODE", "0");

    let (mut rx, child) = sidecar
        .spawn()
        .map_err(|err| format!("failed to spawn bundled backend sidecar: {err}"))?;
    append_desktop_log(&desktop_log, "Bundled backend sidecar spawned.");

    let event_log_path = desktop_log.clone();
    let ready_state = app_handle.state::<BackendReadyState>().inner().clone();
    let shutdown_state = app_handle.state::<BackendShutdownState>().inner().clone();
    let startup_failure_state = app_handle
        .state::<BackendStartupFailureState>()
        .inner()
        .clone();
    let app_handle_for_events = app_handle.clone();
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    let rendered =
                        format!("GOAT backend stdout: {}", String::from_utf8_lossy(&line));
                    append_desktop_log(&event_log_path, &rendered);
                    eprintln!("{rendered}");
                }
                CommandEvent::Stderr(line) => {
                    let rendered =
                        format!("GOAT backend stderr: {}", String::from_utf8_lossy(&line));
                    append_desktop_log(&event_log_path, &rendered);
                    eprintln!("{rendered}");
                }
                CommandEvent::Terminated(payload) => {
                    let ready = ready_state.0.load(Ordering::SeqCst);
                    let shutdown_requested = shutdown_state.0.load(Ordering::SeqCst);
                    let diagnostic = backend_termination_diagnostic(
                        ready,
                        shutdown_requested,
                        payload.code,
                        payload.signal,
                        None,
                    );
                    append_desktop_log(&event_log_path, &diagnostic);
                    eprintln!("{diagnostic}");
                    if !shutdown_requested && !ready {
                        startup_failure_state.0.store(true, Ordering::SeqCst);
                    }
                    if !shutdown_requested && ready {
                        terminate_desktop_process(&app_handle_for_events, 1);
                    }
                }
                CommandEvent::Error(error) => {
                    let ready = ready_state.0.load(Ordering::SeqCst);
                    let shutdown_requested = shutdown_state.0.load(Ordering::SeqCst);
                    let diagnostic = backend_termination_diagnostic(
                        ready,
                        shutdown_requested,
                        None,
                        None,
                        Some(&error),
                    );
                    append_desktop_log(&event_log_path, &diagnostic);
                    eprintln!("{diagnostic}");
                    if !shutdown_requested && !ready {
                        startup_failure_state.0.store(true, Ordering::SeqCst);
                    }
                    if !shutdown_requested && ready {
                        terminate_desktop_process(&app_handle_for_events, 1);
                    }
                }
                _ => {}
            }
        }
    });

    Ok(child)
}
