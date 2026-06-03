import pyttsx3
engine = pyttsx3.init()
engine.save_to_file('Hello world', '/tmp/test_tts.wav')
engine.runAndWait()
print("Saved successfully without aplay error!")
