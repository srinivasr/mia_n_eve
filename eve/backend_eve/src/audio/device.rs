use cpal::traits::{DeviceTrait, HostTrait};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AudioDeviceInfo {
    pub id: String,
    pub name: String,
    pub is_default: bool,
}

pub fn list_input_devices() -> Vec<AudioDeviceInfo> {
    let host = cpal::default_host();
    let default_name = host
        .default_input_device()
        .and_then(|d| d.name().ok())
        .unwrap_or_default();

    host.input_devices()
        .map(|devices| {
            devices
                .filter_map(|d| {
                    let name = d.name().ok()?;
                    let is_default = name == default_name;
                    Some(AudioDeviceInfo {
                        id: name.clone(),
                        name,
                        is_default,
                    })
                })
                .collect()
        })
        .unwrap_or_default()
}

pub fn list_output_devices() -> Vec<AudioDeviceInfo> {
    let host = cpal::default_host();
    let default_name = host
        .default_output_device()
        .and_then(|d| d.name().ok())
        .unwrap_or_default();

    host.output_devices()
        .map(|devices| {
            devices
                .filter_map(|d| {
                    let name = d.name().ok()?;
                    let is_default = name == default_name;
                    Some(AudioDeviceInfo {
                        id: name.clone(),
                        name,
                        is_default,
                    })
                })
                .collect()
        })
        .unwrap_or_default()
}

/// Try to find an input device by name. Falls back to system default.
pub fn resolve_input_device(name: Option<&str>) -> Option<cpal::Device> {
    let host = cpal::default_host();
    if let Some(target) = name {
        if let Ok(devices) = host.input_devices() {
            for device in devices {
                if let Ok(n) = device.name() {
                    if n == target {
                        return Some(device);
                    }
                }
            }
        }
    }
    host.default_input_device()
}

/// Try to find an output device by name. Falls back to system default.
pub fn resolve_output_device(name: Option<&str>) -> Option<cpal::Device> {
    let host = cpal::default_host();
    if let Some(target) = name {
        if let Ok(devices) = host.output_devices() {
            for device in devices {
                if let Ok(n) = device.name() {
                    if n == target {
                        return Some(device);
                    }
                }
            }
        }
    }
    host.default_output_device()
}
