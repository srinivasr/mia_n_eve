import pyttsx3
engine = pyttsx3.init()
try:
    engine.setProperty('voice', 'gmw/en-us+f3')
    engine.save_to_file('This is a female voice.', '/tmp/test_female.wav')
    engine.runAndWait()
    print("Success: set female voice!")
except Exception as e:
    print("Error:", e)
