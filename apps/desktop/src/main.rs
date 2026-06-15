use std::fs::{File, OpenOptions};
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use tauri::{AppHandle, Manager, RunEvent, WebviewUrl, WebviewWindowBuilder};

struct BackendState(Mutex<Option<Child>>);

/// Max time to wait for the bundled Python sidecar to become healthy.
/// The PyInstaller one-file binary re-extracts its runtime on every launch,
/// which (cold) can take well over the old 10s budget — especially the very
/// first time macOS Gatekeeper assesses an unsigned binary. Keep this generous.
const BACKEND_STARTUP_TIMEOUT: Duration = Duration::from_secs(60);
const HEALTHCHECK_INTERVAL: Duration = Duration::from_millis(250);

fn main() {
    tauri::Builder::default()
        .manage(BackendState(Mutex::new(None)))
        .setup(|app| {
            // Anything that can fail is handled here so we never let an error
            // propagate out of the setup hook (that would abort() the process
            // and produce an ugly crash report). On failure we log and exit
            // cleanly instead.
            if let Err(message) = start_backend_and_window(app) {
                let log_path = sidecar_log_path();
                eprintln!("[mercury] startup failed: {message}");
                eprintln!("[mercury] sidecar log: {}", log_path.display());
                log_line(&format!("startup failed: {message}"));
                // Clean exit — no panic, no abort, no crash report.
                std::process::exit(1);
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building mercury desktop")
        .run(|app_handle, event| {
            if matches!(event, RunEvent::Exit) {
                kill_backend(app_handle);
            }
        });
}

fn start_backend_and_window(app: &tauri::App) -> Result<(), String> {
    let port = reserve_port()?;
    let mut child = spawn_backend(app.handle(), port)?;

    // Wait for the backend, watching for an early exit so we fail fast with a
    // useful message instead of silently burning the whole timeout.
    if let Err(message) = wait_for_backend(&mut child, port) {
        let _ = child.kill();
        return Err(message);
    }

    {
        let state = app.state::<BackendState>();
        let mut guard = state.0.lock().map_err(|_| "failed to lock backend state")?;
        *guard = Some(child);
    }

    WebviewWindowBuilder::new(app, "main", WebviewUrl::default())
        .title("Lumen Desktop")
        .inner_size(1440.0, 900.0)
        .initialization_script(&format!("window.__BACKEND_PORT__ = {};", port))
        .build()
        .map_err(|err| err.to_string())?;

    Ok(())
}

fn reserve_port() -> Result<u16, String> {
    let listener = TcpListener::bind("127.0.0.1:0").map_err(|err| err.to_string())?;
    let port = listener.local_addr().map_err(|err| err.to_string())?.port();
    drop(listener);
    Ok(port)
}

fn spawn_backend(app: &AppHandle, port: u16) -> Result<Child, String> {
    if cfg!(debug_assertions) {
        let backend_dir = repo_root().join("backend");
        return spawn_dev_backend(backend_dir, port);
    }

    let binary_path = sidecar_binary_path(app)?;

    // Redirect the sidecar's stdout/stderr to a log file so a failed startup
    // (missing module, crash, etc.) leaves a trace we can actually read.
    let (stdout, stderr) = sidecar_log_streams();

    Command::new(binary_path)
        .env("MERCURY_PORT", port.to_string())
        .stdout(stdout)
        .stderr(stderr)
        .spawn()
        .map_err(|err| err.to_string())
}

fn spawn_dev_backend(backend_dir: PathBuf, port: u16) -> Result<Child, String> {
    let port_value = port.to_string();

    if let Ok(child) = Command::new("uv")
        .args(["run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", &port_value])
        .env("MERCURY_PORT", &port_value)
        .current_dir(&backend_dir)
        .spawn()
    {
        return Ok(child);
    }

    if let Ok(child) = Command::new("py")
        .args(["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", &port_value])
        .env("MERCURY_PORT", &port_value)
        .current_dir(&backend_dir)
        .spawn()
    {
        return Ok(child);
    }

    Command::new("python")
        .args(["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", &port_value])
        .env("MERCURY_PORT", &port_value)
        .current_dir(backend_dir)
        .spawn()
        .map_err(|err| err.to_string())
}

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
}

fn sidecar_binary_path(app: &AppHandle) -> Result<PathBuf, String> {
    let resource_dir = app
        .path()
        .resource_dir()
        .map_err(|err| err.to_string())?;
    let executable = if cfg!(target_os = "windows") {
        "mercury-backend.exe"
    } else {
        "mercury-backend"
    };
    Ok(resource_dir.join("binaries").join(executable))
}

fn wait_for_backend(child: &mut Child, port: u16) -> Result<(), String> {
    let deadline = Instant::now() + BACKEND_STARTUP_TIMEOUT;

    loop {
        // If the sidecar died on its own, surface that immediately. The reason
        // is in ~/.mercury/sidecar.log.
        if let Some(status) = child.try_wait().map_err(|err| err.to_string())? {
            return Err(format!(
                "backend process exited early ({status}); see {}",
                sidecar_log_path().display()
            ));
        }

        if healthcheck(port) {
            return Ok(());
        }

        if Instant::now() >= deadline {
            return Err(format!(
                "backend did not become healthy on port {} within {}s; see {}",
                port,
                BACKEND_STARTUP_TIMEOUT.as_secs(),
                sidecar_log_path().display()
            ));
        }

        std::thread::sleep(HEALTHCHECK_INTERVAL);
    }
}

fn healthcheck(port: u16) -> bool {
    let address = format!("127.0.0.1:{}", port);
    let mut stream = match TcpStream::connect(address) {
        Ok(stream) => stream,
        Err(_) => return false,
    };

    let request = b"GET /healthz HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n";
    if stream.write_all(request).is_err() {
        return false;
    }

    let mut response = String::new();
    if stream.read_to_string(&mut response).is_err() {
        return false;
    }

    response.contains("\"status\":\"ok\"")
}

/// Directory where the app keeps its data + logs (mirrors the backend's
/// `~/.mercury`). Falls back to the system temp dir if HOME is unset.
fn data_dir() -> PathBuf {
    let home = std::env::var_os("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(std::env::temp_dir);
    home.join(".mercury")
}

fn sidecar_log_path() -> PathBuf {
    data_dir().join("sidecar.log")
}

/// Open (truncating) stdout/stderr log handles for the sidecar. If anything
/// goes wrong we just swallow the output rather than fail the launch.
fn sidecar_log_streams() -> (Stdio, Stdio) {
    let dir = data_dir();
    let _ = std::fs::create_dir_all(&dir);
    let path = sidecar_log_path();

    match File::create(&path) {
        Ok(file) => match file.try_clone() {
            Ok(clone) => (Stdio::from(file), Stdio::from(clone)),
            Err(_) => (Stdio::null(), Stdio::null()),
        },
        Err(_) => (Stdio::null(), Stdio::null()),
    }
}

fn log_line(message: &str) {
    let dir = data_dir();
    let _ = std::fs::create_dir_all(&dir);
    if let Ok(mut file) = OpenOptions::new()
        .create(true)
        .append(true)
        .open(dir.join("desktop.log"))
    {
        let _ = writeln!(file, "{message}");
    }
}

fn kill_backend(app_handle: &AppHandle) {
    let state = app_handle.state::<BackendState>();
    let lock_result = state.0.lock();
    if let Ok(mut guard) = lock_result {
        if let Some(child) = guard.as_mut() {
            let _ = child.kill();
        }
        *guard = None;
    }
}
