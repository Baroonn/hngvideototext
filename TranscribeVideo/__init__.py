import logging
import azure.functions as func
from moviepy.editor import VideoFileClip
import azure.cognitiveservices.speech as speechsdk
import time
import os
from pathlib import Path

root = os.environ["root"]
logging.warning("Current Directory: " + os.getcwd())
external = os.environ["external"]

subscription_key = os.environ["speech_sub_key"]
speech_region = "eastus"
file_name = ""
speech_config = None
audio_config = None
speech_recognizer = None
done = False
results = list()

def stopp_cb(evt: speechsdk.SessionEventArgs):
        """callback that signals to stop continuous recognition upon receiving an event `evt`"""
        print('CLOSING on {}'.format(evt))
        global done 
        done = True
def stop_cb(evt):
    """callback that stops continuous recognition upon receiving an event `evt`"""
    print(f"CLOSING on {evt}")
    speech_recognizer.stop_continuous_recognition()
    # Let the function modify the flag defined outside this function
    global done
    done = True
    print(f"CLOSED on {evt}")



def recognised(evt):
    """Callback to process a single transcription"""
    recognised_text = evt.result.text
    # Simply append the new transcription to the running list
    results.append(recognised_text)
    print(f"Audio transcription: '{recognised_text}'")



def main(msg: func.QueueMessage) -> None:
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg.get_body().decode('utf-8'))
    global done
    global results
    done = False
    results = list()
    message = msg.get_body().decode('utf-8')
    filename = Path(message).stem
    video_filename = f"{external}/videos/{message}"
    audio_filename = f"{root}/audios/{filename}.wav"
    transcript_filename = f"{external}/transcripts/{filename}.txt"
    video = VideoFileClip(video_filename)
    audio = video.audio
    audio.write_audiofile(audio_filename)

    speech_config = speechsdk.SpeechConfig(subscription_key, speech_region)
    audio_config = speechsdk.AudioConfig(filename=audio_filename)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config, audio_config)

    speech_recognizer.recognizing.connect(lambda evt: print('RECOGNIZING: {}'.format(evt)))
    speech_recognizer.recognized.connect(lambda evt: results.append('{}'.format(evt.result.text)))
    speech_recognizer.session_started.connect(lambda evt: print('SESSION STARTED: {}'.format(evt)))
    speech_recognizer.session_stopped.connect(lambda evt: print('SESSION STOPPED {}'.format(evt)))
    speech_recognizer.canceled.connect(lambda evt: print('CANCELED {}'.format(evt)))
    # stop continuous recognition on either session stopped or canceled events
    speech_recognizer.session_stopped.connect(stopp_cb)
    speech_recognizer.canceled.connect(stopp_cb)

    # Start continuous speech recognition
    speech_recognizer.start_continuous_recognition()
    
    while not done:
        time.sleep(.5)

    speech_recognizer.stop_continuous_recognition()

    with open(transcript_filename, "w") as file:
        file.write("\n".join(results))
        print("Transcription dumped")
    os.remove(audio_filename)