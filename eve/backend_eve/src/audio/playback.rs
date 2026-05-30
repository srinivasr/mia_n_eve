use cpal::traits::{DeviceTrait, StreamTrait};
use cpal::StreamConfig;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::thread;
use tauri::{AppHandle, Emitter};

use super::device::resolve_output_device;
use super::interruption::InterruptHandle;

#[derive(Clone, serde::Serialize)]
pub struct PlaybackDonePayload {
    pub interrupted: bool,
}

pub struct AudioPlayback {
    pub running: Arc<AtomicBool>,
}

impl AudioPlayback {
    pub fn start(
        app: AppHandle,
        samples: Vec<f32>,
        device_name: Option<String>,
        interrupt_handle: InterruptHandle,
    ) -> Result<Self, String> {
        let running = Arc::new(AtomicBool::new(true));
        let running_clone = running.clone();
        let thread_running = running.clone();

        thread::spawn(move || {
            let device = match resolve_output_device(device_name.as_deref()) {
                Some(d) => d,
                None => {
                    eprintln!("[audio playback] no output device found");
                    return;
                }
            };

            let config: StreamConfig = match device.default_output_config() {
                Ok(c) => c.into(),
                Err(e) => {
                    eprintln!("[audio playback] could not get default config: {}", e);
                    return;
                }
            };

            let channels = config.channels as usize;
            let mut sample_index = 0;
            let total_samples = samples.len();

            let stream = match device.build_output_stream(
                &config,
                move |output: &mut [f32], _: &cpal::OutputCallbackInfo| {
                    // check if we got interrupted (barge-in from VAD)
                    if interrupt_handle.is_cancelled() {
                        for s in output.iter_mut() {
                            *s = 0.0;
                        }
                        if running_clone.load(Ordering::Relaxed) {
                            running_clone.store(false, Ordering::SeqCst);
                            let _ = app.emit(
                                "audio://playback_done",
                                PlaybackDonePayload { interrupted: true },
                            );
                        }
                        return;
                    }

                    for frame in output.chunks_mut(channels) {
                        let val = if sample_index < total_samples {
                            let s = samples[sample_index];
                            sample_index += 1;
                            s
                        } else {
                            0.0
                        };
                        for ch in frame.iter_mut() {
                            *ch = val;
                        }
                    }

                    if sample_index >= total_samples && running_clone.load(Ordering::Relaxed) {
                        running_clone.store(false, Ordering::SeqCst);
                        let _ = app.emit(
                            "audio://playback_done",
                            PlaybackDonePayload { interrupted: false },
                        );
                    }
                },
                |err| {
                    eprintln!("[audio playback] stream error: {err}");
                },
                None,
            ) {
                Ok(s) => s,
                Err(e) => {
                    eprintln!("[audio playback] build stream error: {}", e);
                    return;
                }
            };

            if let Err(e) = stream.play() {
                eprintln!("[audio playback] play error: {}", e);
                return;
            }

            while thread_running.load(Ordering::Relaxed) {
                thread::sleep(std::time::Duration::from_millis(50));
            }
        });

        Ok(Self { running })
    }

    pub fn stop(&self) {
        self.running.store(false, Ordering::SeqCst);
    }

    pub fn is_running(&self) -> bool {
        self.running.load(Ordering::Relaxed)
    }
}

impl Drop for AudioPlayback {
    fn drop(&mut self) {
        self.stop();
    }
}
