#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use tauri::{Manager, Window};
use tonic::transport::Channel;
use std::sync::Arc;
use tokio::sync::Mutex;
use serde::{Deserialize, Serialize};
use anyhow::Result;
use std::path::PathBuf;
use std::fs;

mod protos {
    tonic::include_proto!("videoanalyzer.chat"); // package from proto file
}

use protos::chat_service_client::ChatServiceClient;
use protos::{SendMessageRequest, Message, GetHistoryRequest};

static INPUT_DIR: &str = ".video_analyzer_input"; // relative to app dir; choose better path for production
static ATTACH_DIR: &str = ".video_analyzer_attachments";

#[derive(Serialize, Deserialize)]
struct SaveFileResp { path: String }

#[tauri::command]
async fn save_uploaded_file(base64_data: String, filename: String) -> Result<SaveFileResp, String> {
    // decode base64 and save to INPUT_DIR
    let app_dir = tauri::api::path::app_data_dir(&tauri::Config::default())
        .ok_or("failed to get app dir")?;
    let input_dir = app_dir.join(INPUT_DIR);
    std::fs::create_dir_all(&input_dir).map_err(|e| format!("{}", e))?;
    let data = base64::decode(&base64_data).map_err(|e| format!("{}", e))?;
    let target = input_dir.join(&filename);
    std::fs::write(&target, &data).map_err(|e| format!("{}", e))?;
    Ok(SaveFileResp { path: target.to_string_lossy().to_string() })
}

#[tauri::command]
async fn send_message_and_stream(
    window: tauri::Window,
    backend_addr: String,
    conversation_id: String,
    sender: String,
    text: String,
) -> Result<(), String> {
    // Connect to Python gRPC backend (assumes it's listening on backend_addr, e.g. "http://[::1]:50051")
    // Replace with appropriate host:port
    let mut client = ChatServiceClient::connect(backend_addr.clone())
        .await
        .map_err(|e| format!("connect err: {}", e))?;

    // build message proto
    let msg = Message {
        id: "".into(),
        conversation_id: conversation_id.clone(),
        sender: sender.clone(),
        text: text.clone(),
        created_at: 0,
        confidence: 0.0,
        needs_clarification: false,
        attachments: Vec::new(),
        metadata_json: "".into(),
    };

    let req = SendMessageRequest {
        conversation_id: conversation_id.clone(),
        message: Some(msg),
        stream_responses: true,
    };

    // Call streaming RPC StreamResponses
    let mut stream = client.stream_responses(req).await
        .map_err(|e| format!("rpc err: {}", e))?
        .into_inner();

    // read streaming responses and emit to frontend as events
    while let Some(frame) = stream.message().await.map_err(|e| format!("{}", e))? {
        // frame is StreamResponse; we forward its fields as JSON
        let json = serde_json::to_string(&frame).map_err(|e| format!("{}", e))?;
        // emit an event to webview so React can handle partial updates
        window.emit("stream_chunk", json).map_err(|e| format!("{}", e))?;
    }
    Ok(())
}

#[tauri::command]
async fn get_history(backend_addr: String, conversation_id: String) -> Result<serde_json::Value, String> {
    let mut client = ChatServiceClient::connect(backend_addr.clone())
        .await
        .map_err(|e| format!("connect err: {}", e))?;
    let req = tonic::Request::new(GetHistoryRequest {
        conversation_id: conversation_id.clone(),
        limit: 200,
        offset: 0,
    });
    let resp = client.get_history(req).await.map_err(|e| format!("rpc err: {}", e))?;
    let inner = resp.into_inner();
    // serialize to JSON to send to frontend
    let json = serde_json::to_value(&inner).map_err(|e| format!("{}", e))?;
    Ok(json)
}

fn main() {
  tauri::Builder::default()
    .invoke_handler(tauri::generate_handler![
      save_uploaded_file,
      send_message_and_stream,
      get_history,
    ])
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
