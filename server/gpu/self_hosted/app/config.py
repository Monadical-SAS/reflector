SUPPORTED_FILE_EXTENSIONS = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]
SAMPLE_RATE = 16000
VAD_CONFIG = {
    "batch_max_duration": 30.0,
    "silence_padding": 0.5,
    "window_size": 512,
}

# App-level paths
UPLOADS_PATH = "/tmp/whisper-uploads"
