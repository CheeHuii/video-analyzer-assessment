use tauri::Manager;

mod commands;

// Commenting out proto generation for now - we'll use Python for gRPC client
// Uncomment when you need Rust gRPC client functionality
// pub mod chat {
//     tonic::include_proto!("chat");
// }

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .setup(|app| {
            // Get app data dir and create necessary folders
            let app_data_dir = app.path().app_data_dir()?;
            
            std::fs::create_dir_all(app_data_dir.join("inputs"))?;
            std::fs::create_dir_all(app_data_dir.join("attachments"))?;
            std::fs::create_dir_all(app_data_dir.join("history"))?;

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::save_uploaded_file,
            commands::send_message_and_stream,
            commands::get_history,
            commands::list_attachments,
            commands::open_path
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

// Binary entry point
fn main() {
    run();
}