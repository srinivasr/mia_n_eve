use cpal::traits::{DeviceTrait, StreamTrait};
use cpal::StreamConfig;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use tauri::{AppHandle, Emitter};
use tokio::sync::mpsc;

use super::device::resolve_input_device;
use super::interruption::InterruptHandle;
use super::rms::compute_rms;
use super::vad::{VadDetector, VadState};
use super::stt_client::SttRequest;

#[derive(Clone, serde::Serialize)]
pub struct RmsPayload {
    pub rms: f32,
}

#[derive(Clone, serde::Serialize)]
pub struct VadPayload {
    pub active: bool,
}

pub struct AudioCapture {
    running: Arc<AtomicBool>,
}

impl AudioCapture {
    pub fn start(
        app: AppHandle,
        device_name: Option<String>,
        interrupt_handle: InterruptHandle,
        playback_running: Arc<AtomicBool>,
        stt_tx: mpsc::UnboundedSender<SttRequest>,
    ) -> Result<Self, String> {
        let running = Arc::new(AtomicBool::new(true));
        let running_clone = running.clone();
        let thread_running = running.clone();

        thread::spawn(move || {
            let device = match resolve_input_device(device_name.as_deref()) {
                Some(d) => d,
                None => {
                    eprintln!("[audio capture] No input device found");
                    return;
                }
            };

            let device_name = device.name().unwrap_or_default();
            println!("[audio capture] opening device: {}", device_name);

            let config: StreamConfig = match device.default_input_config() {
                Ok(c) => c.into(),
                Err(e) => {
                    eprintln!("[audio capture] could not get default config: {}", e);
                    return;
                }
            };

            let vad = Arc::new(Mutex::new(VadDetector::default()));
            let last_vad_state = Arc::new(Mutex::new(VadState::Silence));
            let speech_buffer = Arc::new(Mutex::new(Vec::<f32>::new()));

            let channels = config.channels as usize;
            let sample_rate = config.sample_rate.0;

            let stream = match device.default_input_config().map(|c| c.sample_format()) {
                Ok(cpal::SampleFormat::F32) => device.build_input_stream(
                    &config,
                    move |data: &[f32], _: &cpal::InputCallbackInfo| {
                        if !running_clone.load(Ordering::Relaxed) {
                            return;
                        }

                        // if there's multiple channels, mix down to mono
                        let mono: Vec<f32> = if channels > 1 {
                            data.chunks(channels).map(|c| c.iter().sum::<f32>() / channels as f32).collect()
                        } else {
                            data.to_vec()
                        };
                        let samples = mono.as_slice();

                        let rms = compute_rms(samples);

                        // this is useful for debugging mic levels
                        // TODO: remove or gate behind a flag
                        // static mut LOG_COUNTER: usize = 0;
                        // unsafe {
                        //     LOG_COUNTER += 1;
                        //     if LOG_COUNTER % 100 == 0 {
                        //         println!("[audio capture] RMS: {:.5}", rms);
                        //     }
                        // }

                        let _ = app.emit("audio://rms", RmsPayload { rms });

                        let new_state = {
                            let mut detector = vad.lock().unwrap();
                            detector.process(samples)
                        };

                        if new_state == VadState::Speech {
                            speech_buffer.lock().unwrap().extend_from_slice(samples);
                        }

                        let mut last = last_vad_state.lock().unwrap();
                        if new_state != *last {
                            *last = new_state;
                            let active = new_state == VadState::Speech;
                            let _ = app.emit("audio://vad", VadPayload { active });

                            if active {
                                // barge-in: user started talking while we were playing audio
                                if playback_running.load(Ordering::Relaxed) {
                                    interrupt_handle.cancel();
                                }
                            } else {
                                // user stopped talking — ship the buffer to STT
                                let mut buf = speech_buffer.lock().unwrap();

                                if buf.len() > (sample_rate as usize) / 4 {
                                    let samples = std::mem::take(&mut *buf);
                                    println!("[audio capture] sending {} samples to STT", samples.len());
                                    let _ = stt_tx.send(SttRequest {
                                        audio_samples: samples,
                                        sample_rate,
                                    });
                                } else {
                                    // too short, probably a click or mouth noise
                                    buf.clear();
                                }
                            }
                        }
                    },
                    |err| {
                        eprintln!("[audio capture] stream error: {err}");
                    },
                    None,
                ),
                Ok(cpal::SampleFormat::I16) => device.build_input_stream(
                    &config,
                    move |data: &[i16], _: &cpal::InputCallbackInfo| {
                        if !running_clone.load(Ordering::Relaxed) {
                            return;
                        }

                        let mono: Vec<f32> = if channels > 1 {
                            data.chunks(channels).map(|c| c.iter().map(|&s| s as f32 / i16::MAX as f32).sum::<f32>() / channels as f32).collect()
                        } else {
                            data.iter().map(|&s| s as f32 / i16::MAX as f32).collect()
                        };
                        let samples = mono.as_slice();

                        let rms = compute_rms(samples);

                        let _ = app.emit("audio://rms", RmsPayload { rms });

                        let new_state = {
                            let mut detector = vad.lock().unwrap();
                            detector.process(samples)
                        };

                        if new_state == VadState::Speech {
                            speech_buffer.lock().unwrap().extend_from_slice(samples);
                        }

                        let mut last = last_vad_state.lock().unwrap();
                        if new_state != *last {
                            *last = new_state;
                            let active = new_state == VadState::Speech;
                            let _ = app.emit("audio://vad", VadPayload { active });

                            if active {
                                if playback_running.load(Ordering::Relaxed) {
                                    interrupt_handle.cancel();
                                }
                            } else {
                                let mut buf = speech_buffer.lock().unwrap();
                                if buf.len() > (sample_rate as usize) / 4 {
                                    let samples = std::mem::take(&mut *buf);
                                    println!("[audio capture] sending {} samples to STT", samples.len());
                                    let _ = stt_tx.send(SttRequest {
                                        audio_samples: samples,
                                        sample_rate,
                                    });
                                } else {
                                    buf.clear();
                                }
                            }
                        }
                    },
                    |err| {
                        eprintln!("[audio capture] stream error: {err}");
                    },
                    None,
                ),
                _ => Err(cpal::BuildStreamError::StreamConfigNotSupported),
            };

            let stream = match stream {
                Ok(s) => s,
                Err(e) => {
                    eprintln!("[audio capture] build stream error: {}", e);
                    return;
                }
            };

            if let Err(e) = stream.play() {
                eprintln!("[audio capture] play error: {}", e);
                return;
            }

            println!("[audio capture] capture started on {}", device_name);

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

impl Drop for AudioCapture {
    fn drop(&mut self) {
        self.stop();
    }
}
