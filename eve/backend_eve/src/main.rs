// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod audio;

use audio::{
    capture::AudioCapture,
    device::{list_input_devices, list_output_devices, AudioDeviceInfo},
    interruption::InterruptHandle,
    playback::AudioPlayback,
    stt_client::{spawn_stt_client, SttRequest},
};
use serde::Serialize;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use tauri::{AppHandle, State};
use tokio::sync::mpsc;

pub struct AudioState {
    pub capture: Mutex<Option<AudioCapture>>,
    pub playback: Mutex<Option<AudioPlayback>>,
    pub interrupt_handle: InterruptHandle,
    pub playback_running: Arc<AtomicBool>,
    pub input_device: Mutex<Option<String>>,
    pub output_device: Mutex<Option<String>>,
    pub stt_tx: Mutex<Option<mpsc::UnboundedSender<SttRequest>>>,
}

impl Default for AudioState {
    fn default() -> Self {
        Self {
            capture: Mutex::new(None),
            playback: Mutex::new(None),
            interrupt_handle: InterruptHandle::new(),
            playback_running: Arc::new(AtomicBool::new(false)),
            input_device: Mutex::new(None),
            output_device: Mutex::new(None),
            stt_tx: Mutex::new(None),
        }
    }
}

#[tauri::command]
fn list_audio_devices() -> (Vec<AudioDeviceInfo>, Vec<AudioDeviceInfo>) {
    (list_input_devices(), list_output_devices())
}

#[tauri::command]
fn start_capture(
    app: AppHandle,
    state: State<'_, AudioState>,
) -> Result<(), String> {
    println!("[main] start_capture called!");
    let mut capture_lock = state.capture.lock().unwrap();
    if capture_lock.as_ref().map(|c| c.is_running()).unwrap_or(false) {
        println!("[main] capture already running, returning.");
        return Ok(());
    }

    let device_name = state.input_device.lock().unwrap().clone();
    println!("[main] requested device name: {:?}", device_name);
    let interrupt = state.interrupt_handle.clone();
    let playback_running = state.playback_running.clone();

    // STT client is lazy-init'd on first capture start
    let stt_tx = {
        let mut tx_lock = state.stt_tx.lock().unwrap();
        if tx_lock.is_none() {
            *tx_lock = Some(spawn_stt_client(app.clone()));
        }
        tx_lock.as_ref().unwrap().clone()
    };

    let capture = AudioCapture::start(app, device_name, interrupt, playback_running, stt_tx)?;
    *capture_lock = Some(capture);
    Ok(())
}

#[tauri::command]
fn stop_capture(state: State<'_, AudioState>) {
    let mut capture_lock = state.capture.lock().unwrap();
    if let Some(c) = capture_lock.as_ref() {
        c.stop();
    }
    *capture_lock = None;
}

#[tauri::command]
fn start_playback(
    app: AppHandle,
    samples: Vec<f32>,
    state: State<'_, AudioState>,
) -> Result<(), String> {
    state.interrupt_handle.reset();
    state.playback_running.store(true, Ordering::SeqCst);

    let device_name = state.output_device.lock().unwrap().clone();
    let interrupt = state.interrupt_handle.clone();

    let playback = AudioPlayback::start(app, samples, device_name, interrupt)?;

    let mut playback_lock = state.playback.lock().unwrap();
    *playback_lock = Some(playback);
    Ok(())
}

#[tauri::command]
fn stop_playback(state: State<'_, AudioState>) {
    let lock = state.playback.lock().unwrap();
    if let Some(p) = lock.as_ref() {
        p.stop();
    }
    state.playback_running.store(false, Ordering::SeqCst);
}

#[tauri::command]
fn interrupt_playback(state: State<'_, AudioState>) {
    state.interrupt_handle.cancel();
    state.playback_running.store(false, Ordering::SeqCst);
}

#[derive(Serialize)]
struct AudioMetrics {
    capture_running: bool,
    playback_running: bool,
}

#[tauri::command]
fn get_audio_metrics(state: State<'_, AudioState>) -> AudioMetrics {
    AudioMetrics {
        capture_running: state
            .capture
            .lock()
            .unwrap()
            .as_ref()
            .map(|c| c.is_running())
            .unwrap_or(false),
        playback_running: state.playback_running.load(Ordering::Relaxed),
    }
}

#[tauri::command]
fn set_input_device(name: Option<String>, state: State<'_, AudioState>) {
    *state.input_device.lock().unwrap() = name;
}

#[tauri::command]
fn set_output_device(name: Option<String>, state: State<'_, AudioState>) {
    *state.output_device.lock().unwrap() = name;
}

fn main() {
    // Enable GPU-accelerated compositing for smooth animations.
    // WEBKIT_DISABLE_DMABUF_RENDERER=0 enables DMA-BUF (hardware compositing via GPU).
    // WEBKIT_FORCE_COMPOSITING_MODE=1 ensures the compositor always runs on GPU.
    // If you get rendering glitches on Nvidia, set DISABLE_DMABUF=1 and FORCE=0.
    std::env::set_var("WEBKIT_DISABLE_DMABUF_RENDERER", "0");
    std::env::set_var("WEBKIT_FORCE_COMPOSITING_MODE", "1");

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(AudioState::default())
        .invoke_handler(tauri::generate_handler![
            list_audio_devices,
            start_capture,
            stop_capture,
            start_playback,
            stop_playback,
            interrupt_playback,
            get_audio_metrics,
            set_input_device,
            set_output_device,
        ])
        .setup(|_app| {
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
