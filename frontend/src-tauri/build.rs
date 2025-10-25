fn main() -> Result<(), Box<dyn std::error::Error>> {
    // First, run tauri build
    tauri_build::build();

    // Commenting out proto compilation for now
    // Your Python backend will handle gRPC communication
    // Uncomment when you need Rust gRPC client
    
    /*
    let proto_root = std::path::Path::new("../../protos");
    
    if !proto_root.exists() {
        println!("cargo:warning=Proto directory not found at: {}. Skipping proto compilation.", proto_root.display());
        return Ok(());
    }
    
    let protos = vec![
        proto_root.join("chat.proto"),
    ];

    for proto in &protos {
        if !proto.exists() {
            println!("cargo:warning=Proto file not found: {}. Skipping.", proto.display());
            return Ok(());
        }
    }

    let proto_paths: Vec<String> = protos.iter()
        .map(|p| p.to_string_lossy().into_owned())
        .collect();

    println!("cargo:rerun-if-changed={}", proto_root.display());
    for p in &proto_paths {
        println!("cargo:rerun-if-changed={}", p);
    }

    tonic_build::configure()
        .build_server(false)
        .type_attribute(".", "#[derive(serde::Serialize, serde::Deserialize)]")
        .compile(
            &proto_paths.iter().map(|s| s.as_str()).collect::<Vec<_>>(),
            &[proto_root.to_string_lossy().as_ref()],
        )?;
    */

    Ok(())
}