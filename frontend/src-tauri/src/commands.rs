use std::{fs, process::{Command, Stdio}};
use std::io::Write;
use std::fs::File;
use tauri::{command, AppHandle, Manager, Emitter};
use base64::Engine;
use base64::engine::general_purpose;
use std::sync::Mutex;
use std::path::PathBuf;
use std::env;
use std::time::{SystemTime, UNIX_EPOCH};

// Store backend process handle if you want later to control lifecycle
lazy_static::lazy_static! {
    static ref BACKEND_ADDR: Mutex<String> = Mutex::new("http://127.0.0.1:50051".to_string());
}

fn resolve_repo_root() -> Option<PathBuf> {
    // Try current dir and up to a few parents to find markers of repo root
    let mut cur = env::current_dir().ok()?;
    for _ in 0..6 {
        let has_backend = cur.join("backend").exists();
        let has_data = cur.join("data").exists();
        if has_backend && has_data {
            return Some(cur.clone());
        }
        if !cur.pop() { break; }
    }
    // Fall back to build-time manifest dir (src-tauri), then go up to repo
    let mut m = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    for _ in 0..3 {
        let candidate = m.clone();
        if candidate.join("backend").exists() && candidate.join("data").exists() {
            return Some(candidate);
        }
        if !m.pop() { break; }
    }
    None
}

/// Save uploaded file to repo data/videos directory and return full path
#[command]
pub fn save_uploaded_file(app_handle: AppHandle, base64_data: String, filename: String) -> Result<String, String> {
    // Prefer saving into repo's data/videos/<new_id>/raw.mp4 so each upload is isolated
    let videos_root = if let Some(root) = resolve_repo_root() {
        root.join("data").join("videos")
    } else {
        // Fallback to app data dir if repo root not found
        let dir = app_handle.path().app_data_dir().map_err(|e| e.to_string())?;
        dir.join("inputs")
    };
    fs::create_dir_all(&videos_root).map_err(|e| e.to_string())?;

    // Generate a simple unique id from timestamp (hex)
    let now = SystemTime::now().duration_since(UNIX_EPOCH).map_err(|e| e.to_string())?;
    let millis = now.as_millis();
    let new_id = format!("{:x}", millis);
    let target_dir = videos_root.join(&new_id);
    fs::create_dir_all(&target_dir).map_err(|e| e.to_string())?;

    // Always name the video raw.mp4 to align with backend ingest expectations
    let filepath = target_dir.join("raw.mp4");

    let bytes = general_purpose::STANDARD.decode(&base64_data).map_err(|e| e.to_string())?;
    let mut file = File::create(&filepath).map_err(|e| e.to_string())?;
    file.write_all(&bytes).map_err(|e| e.to_string())?;

    Ok(filepath.to_string_lossy().to_string())
}

/// Call gRPC backend and stream responses to frontend
#[command]
pub async fn send_message_and_stream(
    app_handle: AppHandle,
    conversation_id: String,
    sender: String,
    text: String,
    attachments: Option<Vec<String>>,
) -> Result<(), String> {
    let addr = "localhost:50051".to_string();  // Chat service address
    
    // Use tokio::process::Command instead of std::process::Command
    use tokio::process::Command as TokioCommand;
    
    let mut cmd = TokioCommand::new("python");
    cmd.arg("../../backend/grpc_client_stream.py")
        .arg("--addr").arg(addr)
        .arg("--conversation").arg(conversation_id)
        .arg("--sender").arg(sender)
        .arg("--text").arg(text);

    if let Some(list) = attachments {
        for a in list {
            cmd.arg("--attachment").arg(a);
        }
    }

    cmd.stdout(Stdio::piped());

    let mut child = cmd.spawn().map_err(|e| e.to_string())?;
    let stdout = child.stdout.take().ok_or("Failed to capture stdout")?;

    use tokio::io::{AsyncBufReadExt, BufReader};
    let reader = BufReader::new(stdout);

    let app = app_handle.clone();
    tokio::spawn(async move {
        let mut lines = reader.lines();
        while let Ok(Some(line)) = lines.next_line().await {
            let _ = app.emit("stream_chunk", line);
        }
    });

    Ok(())
}

/// Fetch chat history via gRPC
#[command]
pub async fn get_history(conversation_id: String) -> Result<String, String> {
    let backend_addr = "localhost:50051".to_string();  // Chat service address
    let output = Command::new("python")
        .arg("backend/grpc_client_get_history.py")
        .arg("--addr").arg(backend_addr)
        .arg("--conversation").arg(conversation_id)
        .output()
        .map_err(|e| e.to_string())?;

    Ok(String::from_utf8_lossy(&output.stdout).to_string())
}

/// List all attachments (PDF, PPTX) in attachments dir
#[command]
pub fn list_attachments(app_handle: AppHandle) -> Result<Vec<String>, String> {
    let dir = app_handle.path().app_data_dir().map_err(|e| e.to_string())?;
    let attachments_dir = dir.join("attachments");
    fs::create_dir_all(&attachments_dir).map_err(|e| e.to_string())?;

    let mut files = vec![];
    for entry in fs::read_dir(&attachments_dir).map_err(|e| e.to_string())? {
        let path = entry.map_err(|e| e.to_string())?.path();
        if path.is_file() {
            files.push(path.to_string_lossy().to_string());
        }
    }
    Ok(files)
}

/// Open a file with OS default application
#[command]
pub fn open_path(path: String) -> Result<(), String> {
    // Use std::process::Command to open file with default application
    #[cfg(target_os = "windows")]
    {
        Command::new("cmd")
            .args(["/C", "start", "", &path])
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    
    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .arg(&path)
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    
    #[cfg(target_os = "linux")]
    {
        Command::new("xdg-open")
            .arg(&path)
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    
    Ok(())
}

/// List artifacts for a given video id under data/videos/<video_id>
#[command]
pub fn list_video_artifacts(video_id: String) -> Result<Vec<String>, String> {
    let root = resolve_repo_root().ok_or("Repo root not found")?;
    let base = root.join("data").join("videos").join(&video_id);
    if !base.exists() {
        return Ok(vec![]);
    }
    let mut files: Vec<String> = Vec::new();
    // helper to push files with basic filtering
    let mut push_files = |dir: &PathBuf| -> Result<(), String> {
        for entry in fs::read_dir(dir).map_err(|e| e.to_string())? {
            let path = entry.map_err(|e| e.to_string())?.path();
            if path.is_file() {
                let name = path.file_name().and_then(|s| s.to_str()).unwrap_or("").to_lowercase();
                if name.starts_with("transcript_") && name.ends_with(".json")
                    || name.ends_with(".pdf")
                    || name.ends_with(".pptx")
                    || name.ends_with(".png")
                    || name.ends_with(".jpg")
                    || name.ends_with(".jpeg") {
                    files.push(path.to_string_lossy().to_string());
                }
            }
        }
        Ok(())
    };
    // base dir
    push_files(&base)?;
    // common subdirs like graphs
    let graphs = base.join("graphs");
    if graphs.exists() {
        push_files(&graphs)?;
    }
    // sort for stable order
    files.sort();
    Ok(files)
}

/// List available video IDs under data/videos sorted by recency
#[command]
pub fn list_video_ids() -> Result<Vec<String>, String> {
    let root = resolve_repo_root().ok_or("Repo root not found")?;
    let base = root.join("data").join("videos");
    if !base.exists() { return Ok(vec![]); }
    let mut items: Vec<(i64, String)> = Vec::new();
    for entry in fs::read_dir(&base).map_err(|e| e.to_string())? {
        let path = entry.map_err(|e| e.to_string())?.path();
        if path.is_dir() {
            let id = path.file_name().and_then(|s| s.to_str()).unwrap_or("").to_string();
            // mtime from meta.json or dir mtime
            let mut ts: i64 = 0;
            let meta = path.join("meta.json");
            if meta.exists() {
                if let Ok(md) = meta.metadata() { if let Ok(t) = md.modified() { if let Ok(d) = t.elapsed() { ts = -(d.as_secs() as i64); } } }
            } else if let Ok(md) = path.metadata() { if let Ok(t) = md.modified() { if let Ok(d) = t.elapsed() { ts = -(d.as_secs() as i64); } }
            }
            items.push((ts, id));
        }
    }
    // sort by ts descending (most recent first)
    items.sort_by(|a,b| b.0.cmp(&a.0));
    Ok(items.into_iter().map(|(_,id)| id).collect())
}