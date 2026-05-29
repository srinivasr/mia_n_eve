use anyhow::{anyhow, Result};
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use rustfft::{num_complex::Complex, FftPlanner};
use tauri::{AppHandle, Emitter};

pub fn start_audio_capture(app_handle: AppHandle) {
    std::thread::spawn(move || {
        if let Err(e) = run_audio_loop(app_handle) {
            eprintln!("Audio capture error: {}", e);
        }
    });
}

fn run_audio_loop(app_handle: AppHandle) -> Result<()> {
    let host = cpal::default_host();
    println!("[audio] Using host: {:?}", host.id());

    let device = host
        .default_input_device()
        .ok_or_else(|| anyhow!("No input device available"))?;
    println!("[audio] Input device: {:?}", device.name().unwrap_or_default());

    let config = device.default_input_config()?;
    println!("[audio] Sample format: {:?}, rate: {:?}, channels: {:?}", 
        config.sample_format(), config.sample_rate(), config.channels());

    const FFT_SIZE: usize = 1024;
    const NUM_BINS: usize = 32;

    let (tx, rx) = std::sync::mpsc::channel::<Vec<f32>>();

    let err_fn = |err| eprintln!("[audio] Stream error: {}", err);
    let mut sample_buffer = Vec::with_capacity(FFT_SIZE);
    
    let stream = match config.sample_format() {
        cpal::SampleFormat::F32 => device.build_input_stream(
            &config.into(),
            move |data: &[f32], _: &_| {
                for &sample in data {
                    sample_buffer.push(sample);
                    if sample_buffer.len() >= FFT_SIZE {
                        let _ = tx.send(sample_buffer.clone());
                        sample_buffer.clear();
                    }
                }
            },
            err_fn,
            None,
        )?,
        cpal::SampleFormat::I16 => device.build_input_stream(
            &config.into(),
            move |data: &[i16], _: &_| {
                for &sample in data {
                    let f32_sample = sample as f32 / i16::MAX as f32;
                    sample_buffer.push(f32_sample);
                    if sample_buffer.len() >= FFT_SIZE {
                        let _ = tx.send(sample_buffer.clone());
                        sample_buffer.clear();
                    }
                }
            },
            err_fn,
            None,
        )?,
        other => return Err(anyhow!("Unsupported sample format: {:?}", other)),
    };

    stream.play()?;
    println!("[audio] ✅ Audio stream started! Listening for microphone input...");

    let mut planner = FftPlanner::new();
    let fft = planner.plan_fft_forward(FFT_SIZE);

    for samples in rx {
        let mut buffer: Vec<Complex<f32>> = samples
            .iter()
            .enumerate()
            .map(|(i, &val)| {
                let multiplier = 0.5 * (1.0 - (2.0 * std::f32::consts::PI * i as f32 / (FFT_SIZE - 1) as f32).cos());
                Complex { re: val * multiplier, im: 0.0 }
            })
            .collect();

        fft.process(&mut buffer);

        let mut magnitudes = Vec::with_capacity(FFT_SIZE / 2);
        for c in buffer.iter().take(FFT_SIZE / 2).skip(1) {
            magnitudes.push(c.norm());
        }

        let mut bins = vec![0u8; NUM_BINS];
        let bin_size = magnitudes.len() / NUM_BINS;
        
        for i in 0..NUM_BINS {
            let start = i * bin_size;
            let end = start + bin_size;
            let mut sum = 0.0;
            for mag in magnitudes.iter().take(end).skip(start) {
                sum += mag;
            }
            let avg = sum / bin_size as f32;
            
            let scaled = (avg * 100.0).min(255.0) as u8;
            bins[i] = scaled;
        }
        let _ = app_handle.emit("audio-stream", bins);
    }

    Ok(())
}
