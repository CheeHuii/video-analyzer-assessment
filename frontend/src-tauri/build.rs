fn main() -> Result<(), Box<dyn std::error::Error>> {
    tonic_build::configure()
        .build_server(false) // we only need client in Tauri (tonic client)
        .compile(&["./src/protos/chat.proto"], &["./src/protos"])?;
    Ok(())
}
