use super::rms::compute_rms;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum VadState {
    Silence,
    Speech,
}

/// Energy-based VAD with a hold timer so we don't flicker on every pause.
pub struct VadDetector {
    pub threshold: f32,
    pub hold_frames: usize,
    state: VadState,
    hold_counter: usize,
}

impl VadDetector {
    pub fn new(threshold: f32, hold_frames: usize) -> Self {
        Self {
            threshold,
            hold_frames,
            state: VadState::Silence,
            hold_counter: 0,
        }
    }

    pub fn process(&mut self, samples: &[f32]) -> VadState {
        let rms = compute_rms(samples);
        let above = rms >= self.threshold;

        match self.state {
            VadState::Silence => {
                if above {
                    self.state = VadState::Speech;
                    self.hold_counter = self.hold_frames;
                }
            }
            VadState::Speech => {
                if above {
                    self.hold_counter = self.hold_frames;
                } else if self.hold_counter > 0 {
                    self.hold_counter -= 1;
                } else {
                    self.state = VadState::Silence;
                }
            }
        }

        self.state
    }
}

impl Default for VadDetector {
    fn default() -> Self {
        Self::new(0.015, 50)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_silence_stays_silent() {
        let mut vad = VadDetector::new(0.02, 5);
        let silence = vec![0.0f32; 512];
        assert_eq!(vad.process(&silence), VadState::Silence);
    }

    #[test]
    fn test_loud_signal_triggers_speech() {
        let mut vad = VadDetector::new(0.02, 5);
        let loud: Vec<f32> = vec![0.5f32; 512];
        assert_eq!(vad.process(&loud), VadState::Speech);
    }

    #[test]
    fn test_hold_prevents_immediate_drop() {
        let mut vad = VadDetector::new(0.02, 3);
        let loud: Vec<f32> = vec![0.5f32; 512];
        let silence: Vec<f32> = vec![0.0f32; 512];

        vad.process(&loud);
        assert_eq!(vad.process(&silence), VadState::Speech);
        assert_eq!(vad.process(&silence), VadState::Speech);
        assert_eq!(vad.process(&silence), VadState::Speech);
        assert_eq!(vad.process(&silence), VadState::Silence);
    }
}
