from flask import Flask
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    print("Received:", data)
    socketio.emit("data", data)

mqtt_client = mqtt.Client()
mqtt_client.on_message = on_message
mqtt_client.connect("localhost", 1883)
mqtt_client.subscribe("test/data")
mqtt_client.loop_start()

if __name__ == "__main__":
    socketio.run(app, port=5000)
