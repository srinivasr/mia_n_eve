/// RMS energy of a float32 audio buffer.
/// Input should be in [-1.0, 1.0], returns [0.0, 1.0].
pub fn compute_rms(samples: &[f32]) -> f32 {
    if samples.is_empty() {
        return 0.0;
    }
    let sum_sq: f32 = samples.iter().map(|s| s * s).sum();
    (sum_sq / samples.len() as f32).sqrt()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rms_silence() {
        let silence = vec![0.0f32; 512];
        assert_eq!(compute_rms(&silence), 0.0);
    }

    #[test]
    fn test_rms_full_scale() {
        let full = vec![1.0f32; 512];
        let rms = compute_rms(&full);
        assert!((rms - 1.0).abs() < 1e-6, "expected 1.0 got {rms}");
    }

    #[test]
    fn test_rms_sine_wave() {
        // rms of a perfect sine is 1/sqrt(2) ≈ 0.707
        let samples: Vec<f32> = (0..4800)
            .map(|i| (2.0 * std::f32::consts::PI * i as f32 / 48.0).sin())
            .collect();
        let rms = compute_rms(&samples);
        assert!((rms - std::f32::consts::FRAC_1_SQRT_2).abs() < 0.01, "got {rms}");
    }
}
