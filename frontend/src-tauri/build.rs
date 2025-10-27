fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Run tauri build
    tauri_build::build();

    Ok(())
}