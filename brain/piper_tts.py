import pyttsx3
import threading
import queue
import re

class SentenceBuffer:
    def __init__(self):
        self.buffer = ""

    def add(self, text):
        """
        Adds text to the buffer and returns any complete sentences.
        """
        self.buffer += text
        sentences = []
        # Split by punctuation followed by space
        parts = re.split(r'(?<=[.!?])\s+', self.buffer)
        if len(parts) > 1:
            sentences = parts[:-1]
            self.buffer = parts[-1]
        return sentences

    def flush(self):
        """
        Returns whatever is left in the buffer.
        """
        res = self.buffer.strip()
        self.buffer = ""
        return res

class PiperTTS:
    def __init__(self):
        self.enabled = True
        self.q = queue.Queue()
        self._thread = None
        self._stop_event = threading.Event()
        self._current_process = None

    def initialize(self):
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def _worker(self):
        import tempfile
        import os
        import subprocess
        
        while not self._stop_event.is_set():
            try:
                # Use a timeout so we can check the stop event
                text = self.q.get(timeout=0.5)
                if text is None:
                    break
                if self.enabled and text.strip():
                    # Generate temporary file path
                    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
                    os.close(tmp_fd)
                    
                    try:
                        # Use local Piper TTS with high-quality Lessac voice
                        import subprocess
                        self._current_process = subprocess.Popen([
                            "/home/lev/repos/mialocal/brain/venv/bin/piper",
                            "--model", "/home/lev/repos/mialocal/brain/piper_voices/en_US-lessac-medium.onnx",
                            "--output_file", tmp_path
                        ], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        self._current_process.communicate(input=text.encode('utf-8'))
                        
                        # Play using ffplay
                        self._current_process = subprocess.Popen([
                            "ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", tmp_path
                        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        self._current_process.wait()
                        
                    except Exception as e:
                        print(f"TTS Error: {e}")
                    finally:
                        self._current_process = None
                        # Cleanup temp file
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                            
                self.q.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Queue Error: {e}")

    def queue_sentence(self, sentence):
        if self.enabled and sentence.strip():
            self.q.put(sentence)

    def wait_for_completion(self):
        self.q.join()

    def stop(self):
        """Stops current playback and clears the queue."""
        # Clear the queue
        try:
            while True:
                self.q.get_nowait()
                self.q.task_done()
        except queue.Empty:
            pass
        
        # Terminate current running process (piper or ffplay)
        if self._current_process:
            try:
                self._current_process.terminate()
            except Exception:
                pass

    def shutdown(self):
        self._stop_event.set()
        self.stop()
        if self._thread:
            self.q.put(None)
            self._thread.join(timeout=2)
