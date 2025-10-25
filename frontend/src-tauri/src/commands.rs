use std::{fs, process::{Command, Stdio}};
use std::io::Write;
use std::fs::File;
use tauri::{command, AppHandle, Manager, Emitter};
use base64::Engine;
use base64::engine::general_purpose;
use std::sync::Mutex;

// Store backend process handle if you want later to control lifecycle
lazy_static::lazy_static! {
    static ref BACKEND_ADDR: Mutex<String> = Mutex::new("http://127.0.0.1:50051".to_string());
}

/// Save uploaded file to INPUT_DIR and return full path
#[command]
pub fn save_uploaded_file(app_handle: AppHandle, base64_data: String, filename: String) -> Result<String, String> {
    // Tauri v2: use app_handle.path().app_data_dir()
    let dir = app_handle.path().app_data_dir().map_err(|e| e.to_string())?;
    let input_dir = dir.join("inputs");
    fs::create_dir_all(&input_dir).map_err(|e| e.to_string())?;
    let filepath = input_dir.join(filename);

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
) -> Result<(), String> {
    let addr = BACKEND_ADDR.lock().unwrap().clone();
    
    // Use tokio::process::Command instead of std::process::Command
    use tokio::process::Command as TokioCommand;
    
    let mut cmd = TokioCommand::new("python");
    cmd.arg("backend/grpc_client_stream.py")
       .arg("--addr").arg(addr)
       .arg("--conversation").arg(conversation_id)
       .arg("--sender").arg(sender)
       .arg("--text").arg(text)
       .stdout(Stdio::piped());

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
pub async fn get_history(backend_addr: String, conversation_id: String) -> Result<String, String> {
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