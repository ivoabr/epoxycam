
from flask import Flask, Response, send_file
from picamera2 import Picamera2
from libcamera import Transform
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
import threading
import time
import os
from datetime import datetime

app = Flask(__name__)
picam2 = Picamera2()
video_file_path = "recordings/video.h264"
is_recording = False
timestamp_thread = None
stop_timestamp = threading.Event()

def read_temperature():
    try:
        base_path = '/sys/bus/w1/devices/'
        device_folder = [f for f in os.listdir(base_path) if f.startswith('28-')][0]
        device_file = os.path.join(base_path, device_folder, 'w1_slave'
        )
        with open(device_file, 'r') as f:
            lines = f.readlines()
            if lines[0].strip()[-3:] != 'YES':
                return "Temp?°C"
            equals_pos = lines[1].find('t=')
            if equals_pos != -1:
                temp_string = lines[1][equals_pos + 2:]
                temp_c = float(temp_string) / 1000.0
                return f"{temp_c:.1f}°C"
    except Exception as e:
        return "Error°C"

def fetch_tide_and_moon():
    # Placeholder: In production, replace with real API calls or parsed data
    tide_info = "High Tide at 12:50 PM"
    moon_phase = "Waxing Gibbous"
    return tide_info, moon_phase

def update_overlay():
    while not stop_timestamp.is_set():
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        temp = read_temperature()
        tide_info, moon_phase = fetch_tide_and_moon()
        overlay_text = f"{timestamp} | {temp} | {tide_info} | {moon_phase}"
        picam2.set_overlay_text(overlay_text, size=32, colour=(255, 255, 255))
        time.sleep(60)

@app.route('/start')
def start_recording():
    global is_recording, timestamp_thread, stop_timestamp

    if is_recording:
        return "Already recording"

    config = picam2.create_video_configuration(main={"size": (1280, 720)})
    picam2.configure(config)
    encoder = H264Encoder()
    picam2.encoder = encoder
    picam2.output = FileOutput(video_file_path)
    picam2.start()
    picam2.start_encoder()

    stop_timestamp.clear()
    timestamp_thread = threading.Thread(target=update_overlay)
    timestamp_thread.start()

    is_recording = True
    return "Recording started"

@app.route('/stop')
def stop_recording():
    global is_recording, stop_timestamp, timestamp_thread

    if not is_recording:
        return "Not recording"

    stop_timestamp.set()
    if timestamp_thread:
        timestamp_thread.join()

    picam2.stop_encoder()
    picam2.stop()

    is_recording = False
    return "Recording stopped"

@app.route('/download')
def download_video():
    if os.path.exists(video_file_path):
        return send_file(video_file_path, as_attachment=True)
    else:
        return "No video recorded yet", 404

if __name__ == '__main__':
    os.makedirs("recordings", exist_ok=True)
    app.run(host='0.0.0.0', port=5000)
