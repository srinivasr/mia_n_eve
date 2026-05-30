import asyncio
import websockets
from typing import Any
import json
from .multimodal.stt import process_audio_base64

async def process_request(path, request_headers):
    print("received headers:", request_headers)
    return None

async def handle_connection(websocket: Any) -> None:
    print("edge device connected to brain server.")
    try:
        async for message in websocket:
            try:
                payload = json.loads(message)
                if payload.get("type") == "stt_request":
                    b64_data = payload.get("data", "")
                    sample_rate = payload.get("sample_rate", 44100)

                    print(f"got audio chunk ({len(b64_data)} bytes base64, {sample_rate}Hz)")
                    text = process_audio_base64(b64_data, sample_rate)
                    print(f"transcription: {text}")

                    response = {
                        "type": "stt_result",
                        "text": text
                    }
                    await websocket.send(json.dumps(response))
            except json.JSONDecodeError:
                print("received invalid json")
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"error handling message: {e}")

    except websockets.exceptions.ConnectionClosed as e:
        print(f"edge device disconnected. reason: {e}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"unexpected connection error: {e}")

async def main() -> None:
    print("Starting EVE Brain Orchestrator on ws://127.0.0.1:8765...")
    async with websockets.serve(handle_connection, "127.0.0.1", 8765, max_size=10_485_760, process_request=process_request):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
