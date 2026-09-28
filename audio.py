from gtts import gTTS  # Note the capital TTS
from playsound import playsound

audio = "speech.mp3"
language = "en"

# Note the capital gTTS here too
speech = gTTS(text="my name is teja velli saahayama cheyii babaii", lang=language, slow=False)

speech.save(audio)
playsound(audio)

print("Audio file has been played successfully.")
