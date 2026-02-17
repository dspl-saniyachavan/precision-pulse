import json
import threading
from datetime import datetime
from flask import Flask, jsonify, request
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt

socketio = SocketIO(cors_allowed_origins="*")
clients_status = {}

MQTT_BROKER = "mqtt"
MQTT_PORT = 1883

mqtt_client = None

def create_app():
    app = Flask(__name__)
    socketio.init_app(app)

    setup_mqtt()

    @app.route("/api/command/<client_id>", methods=["POST"])
    def send_command(client_id):
        data = request.json
        topic = f"precisionpulse/{client_id}/command"
        mqtt_client.publish(topic, json.dumps(data), qos=1)
        return jsonify({"status": "sent"})

    @app.route("/api/clients")
    def get_clients():
        return jsonify(clients_status)

    return app
def start_monitor_thread():
    def monitor():
        while True:
            now = datetime.utcnow()
            for client_id, last_seen in list(clients_status.items()):
                if (now - last_seen).seconds > 10:
                    socketio.emit("client_offline", {"client_id": client_id})
            socketio.sleep(5)

    threading.Thread(target=monitor, daemon=True).start()


def setup_mqtt():
    global mqtt_client

    def on_connect(client, userdata, flags, reason_code, properties):
        print("MQTT Connected")
        client.subscribe("precisionpulse/+/telemetry")
        client.subscribe("precisionpulse/+/heartbeat")

    def on_message(client, userdata, msg):
        topic = msg.topic
        payload = json.loads(msg.payload.decode())

        if "telemetry" in topic:
            socketio.emit("telemetry_update", payload)

        if "heartbeat" in topic:
            clients_status[payload["client_id"]] = datetime.utcnow()
            socketio.emit("heartbeat_update", payload)

    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
    mqtt_client.loop_start()

    start_monitor_thread()

def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    print("Received:", data)
    socketio.emit("data", data)



# JWT TOKEN----------------
# from flask import Flask, redirect, request, jsonify, make_response, render_template, session, flash, url_for
# import jwt
# from datetime import datetime, timedelta
# from functools import wraps

# app = Flask(__name__)
# app.config['SECRET_KEY'] = 'KEEP_IT_A_SECRET'

# @app.route('/public')
# def public():
#  return 'Anyone can access this'

# def token_required(func):
#     @wraps(func)
#     def decorated(*args, **kwargs):
#         token = request.args.get('token')
#         if not token:
#             return jsonify({'message': 'Token is missing!'}), 401

#         try:
#             data = jwt.decode(token, app.config['SECRET_KEY'])
#         except:
#             return jsonify({'message': 'Invalid token'}), 403

#         return func(*args, **kwargs)

#     return decorated

# @app.route('/private')
# @token_required
# def private():
#  return 'Only token can access'

# @app.route('/login', methods=['GET','POST'])
# def login():
#     if request.method == "GET":
#         return render_template("index.html")
    
#     if request.form['username'] and request.form['password'] == '123456':
#         session['logged_in'] = True
#         token = jwt.encode({
#             'user': request.form['username'],
#             'expiration': str(datetime.utcnow() + timedelta(minutes=50))
#         }, app.config['SECRET_KEY'])

#         return jsonify({'token': token})
#     else:
#         return make_response('Unable to verify', 403, {'WWW-Authenticate': 'Basic realm: "Authentication Failed"'})
    
# @app.route('/logout')
# def logout():
#     session.pop('logged_in', None)
#     return redirect(url_for('login'))

    
