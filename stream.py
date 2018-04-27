import io
import time
import picamera
import threading
import json
from base64 import b64encode
from datetime import datetime
from websocket import create_connection
from websocket._exceptions import WebSocketBadStatusException


# Default settings
RESOLUTION = (640, 480)
IP = '127.0.0.1'
PORT = 80
KEY = 'SECRET'
STREAM_NAME = 'STREAM'
DEBUG = True
VFLIP = False
HFLIP = False
THREADS = 5


# Override defaults with local_settings
try:
    from local_settings import *
except ImportError:
    pass


def debug(*args):
    if DEBUG:
        print(datetime.now(), *args)


def send(images, cv, error):
    try:
        ws = create_connection('wss://%s/ws/stream/%s/' % (IP, STREAM_NAME))
        while True:
            with cv:
                while not len(images):
                    cv.wait()
                image = images.pop(0)
            image = b64encode(image).decode('ascii')
            ws.send(json.dumps({
               'image': image,
               'key': KEY,
            }))
            debug('Send', threading.current_thread().name)
    except (WebSocketBadStatusException, BrokenPipeError, ConnectionResetError) as e:
        debug('Unable to connect', e)
        error[0] = True


def capture():
    debug('Connecting to %s on port %s' % (IP, PORT))

    cv = threading.Condition()
    stream = io.BytesIO()
    images = []
    error = [False]

    for _ in range(THREADS):
        threading.Thread(target=send, args=(images, cv, error)).start()

    with picamera.PiCamera() as camera:
        camera.resolution = RESOLUTION
        camera.vflip = VFLIP
        camera.hflip = HFLIP

        for _ in camera.capture_continuous(stream, 'jpeg'):
            debug('Capture')
            if error[0]:
                break
            stream.seek(0)
            image = stream.read()
            with cv:
                if len(images) < 3:
                    images.append(image)
                cv.notify_all()
            stream.seek(0)
            stream.truncate()


def main():
    while True:
        capture()
        time.sleep(3)


main()
