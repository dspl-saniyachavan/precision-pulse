import json
import time
import random
import sqlite3
from datetime import datetime
import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1884
CLIENT_ID = "client-01"

TELEMETRY_TOPIC = f"precisionpulse/{CLIENT_ID}/telemetry"
COMMAND_TOPIC = f"precisionpulse/{CLIENT_ID}/command"
HEARTBEAT_TOPIC = f"precisionpulse/{CLIENT_ID}/heartbeat"

connected = False

# SQLite setup
conn = sqlite3.connect("desktop_local.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS telemetry_buffer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payload TEXT,
    synced INTEGER DEFAULT 0
)
""")
conn.commit()


def generate_data():
    return {
        "client_id": CLIENT_ID,
        "timestamp": datetime.utcnow().isoformat(),
        "temperature": round(random.uniform(20, 30), 2),
        "humidity": round(random.uniform(40, 70), 2),
        "flowrate": round(random.uniform(10, 20), 2)
    }

def store_offline(payload):
    cursor.execute(
        "INSERT INTO telemetry_buffer (payload, synced) VALUES (?, 0)",
        (json.dumps(payload),)
    )
    conn.commit()
    print("Stored offline")

def flush_buffer(client):
    cursor.execute("SELECT id, payload FROM telemetry_buffer WHERE synced=0")
    rows = cursor.fetchall()

    for row in rows:
        record_id, payload = row
        result = client.publish(TELEMETRY_TOPIC, payload, qos=1)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            cursor.execute(
                "UPDATE telemetry_buffer SET synced=1 WHERE id=?",
                (record_id,)
            )
            conn.commit()
            print("Flushed record:", record_id)

def send_heartbeat(client):
    heartbeat = {
        "client_id": CLIENT_ID,
        "timestamp": datetime.utcnow().isoformat(),
        "status": "online"
    }
    client.publish(HEARTBEAT_TOPIC, json.dumps(heartbeat), qos=1)

def on_connect(client, userdata, flags, reason_code, properties):
    global connected
    connected = True
    print("Connected to broker")
    client.subscribe(COMMAND_TOPIC)
    
    flush_buffer(client)

def on_disconnect(client, userdata, reason_code, properties):
    global connected
    connected = False
    print("Disconnected from broker")

def on_message(client, userdata, msg):
    command = json.loads(msg.payload.decode())
    print("Command received:", command)

    if command["type"] == "FORCE_SYNC":
        flush_buffer(client)
    if command["type"] == "FORCE_STOP":
        return 'Force stops'

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect
mqtt_client.on_message = on_message

mqtt_client.connect(BROKER, PORT)
mqtt_client.loop_start()
client = mqtt.Client()
client.connect("localhost", 1883)
client.loop_start()



heartbeat_timer = 0


while True:
    data = generate_data()

    if connected:
        mqtt_client.publish(TELEMETRY_TOPIC, json.dumps(data), qos=1)
        print(generate_data())
        print("Published live")
        client.publish("test/data", json.dumps(data))
        print("Sent:", data)
        time.sleep(1)
    else:
        store_offline(data)

    send_heartbeat(mqtt_client)

    time.sleep(2)
