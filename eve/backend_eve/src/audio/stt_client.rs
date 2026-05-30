use base64::{Engine as _, engine::general_purpose::STANDARD};
use futures_util::{SinkExt, StreamExt};
use serde_json::json;
use tauri::{AppHandle, Emitter};
use tokio::sync::mpsc;
use tokio_tungstenite::connect_async;
use tokio_tungstenite::tungstenite::Message;

pub struct SttRequest {
    pub audio_samples: Vec<f32>,
    pub sample_rate: u32,
}

#[derive(Clone, serde::Serialize)]
pub struct SttResultPayload {
    pub text: String,
}

/// Spawns a background task that connects to the python brain server
/// and sends audio chunks for transcription. Returns the channel sender.
pub fn spawn_stt_client(app: AppHandle) -> mpsc::UnboundedSender<SttRequest> {
    let (tx, mut rx) = mpsc::unbounded_channel::<SttRequest>();

    tauri::async_runtime::spawn(async move {
        loop {
            // wait for the first request before trying to connect
            let request = match rx.recv().await {
                Some(req) => req,
                None => break,
            };

            let ws_url = "ws://127.0.0.1:8765";

            let ws_stream = match connect_async(ws_url).await {
                Ok((stream, _)) => stream,
                Err(e) => {
                    eprintln!("[STT] could not connect to brain server: {}", e);
                    continue;
                }
            };

            let (mut write, mut read) = ws_stream.split();

            // send the first request right away
            send_request(&mut write, request).await;

            // then handle responses interleaved with more requests
            loop {
                tokio::select! {
                    msg = read.next() => {
                        match msg {
                            Some(Ok(Message::Text(t))) => {
                                if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(&t) {
                                    if parsed["type"] == "stt_result" {
                                        if let Some(text) = parsed["text"].as_str() {
                                            if !text.is_empty() {
                                                let _ = app.emit("audio://stt_result", SttResultPayload {
                                                    text: text.to_string(),
                                                });
                                            }
                                        }
                                    }
                                }
                            }
                            Some(Ok(Message::Close(_))) | None => {
                                eprintln!("[STT] server closed the connection");
                                break;
                            }
                            Some(Err(e)) => {
                                eprintln!("[STT] websocket error: {}", e);
                                break;
                            }
                            _ => {}
                        }
                    },
                    Some(req) = rx.recv() => {
                        send_request(&mut write, req).await;
                    }
                }
            }

            // wait a bit before reconnecting
            tokio::time::sleep(std::time::Duration::from_millis(500)).await;
        }
    });

    tx
}

async fn send_request(
    write: &mut futures_util::stream::SplitSink<
        tokio_tungstenite::WebSocketStream<tokio_tungstenite::MaybeTlsStream<tokio::net::TcpStream>>,
        Message,
    >,
    req: SttRequest,
) {
    // serialize f32 samples to little-endian bytes, then base64
    let byte_len = req.audio_samples.len() * 4;
    let mut bytes = Vec::with_capacity(byte_len);
    for sample in req.audio_samples {
        bytes.extend_from_slice(&sample.to_le_bytes());
    }

    let b64 = STANDARD.encode(&bytes);

    let payload = json!({
        "type": "stt_request",
        "sample_rate": req.sample_rate,
        "data": b64
    });

    if let Err(e) = write.send(Message::Text(payload.to_string())).await {
        eprintln!("[STT] failed to send request: {}", e);
    }
}
