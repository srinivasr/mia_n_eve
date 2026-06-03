import sounddevice as sd
import soundfile as sf
data, fs = sf.read('/tmp/test_tts.wav')
sd.play(data, fs)
sd.wait()
print("Played successfully!")
