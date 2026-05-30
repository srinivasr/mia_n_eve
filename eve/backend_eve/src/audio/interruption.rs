use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

/// Simple cancellation flag shared between the capture and playback threads.
/// Lets VAD barge-in interrupt active audio output within one callback cycle.
#[derive(Clone)]
pub struct InterruptHandle {
    cancelled: Arc<AtomicBool>,
}

impl InterruptHandle {
    pub fn new() -> Self {
        Self {
            cancelled: Arc::new(AtomicBool::new(false)),
        }
    }

    pub fn cancel(&self) {
        self.cancelled.store(true, Ordering::SeqCst);
    }

    pub fn reset(&self) {
        self.cancelled.store(false, Ordering::SeqCst);
    }

    pub fn is_cancelled(&self) -> bool {
        self.cancelled.load(Ordering::SeqCst)
    }
}

impl Default for InterruptHandle {
    fn default() -> Self {
        Self::new()
    }
}
