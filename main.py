from flask import Flask, render_template, request, jsonify
from rov import Rov, clear_buffers
import serial.tools.list_ports
import time

app = Flask(__name__)

rov = None
commandData = None
receivedData = None

def list_com_ports():
    ports = serial.tools.list_ports.comports()
    com_ports = []
    for port in ports:
        if 'CH341' in port.description:
            com_ports.append(f"{port.device} (önerilen)")
        else:
            com_ports.append(port.device)
    return com_ports

@app.route('/')
def index():
    com_ports = list_com_ports()
    return render_template('index.html', com_ports=com_ports)

@app.route('/connect', methods=['POST'])
def connect():
    global rov, commandData
    try:
        com_port = request.json.get('com_port')
        if not com_port:
            raise ValueError("COM portu seçilmedi.")
        rov = Rov(port=com_port, rate_hz=20)  # Seçilen COM portunu kullan
        clear_buffers(rov.link)
        commandData = rov.commandData  # commandData nesnesini güncelle
        rov.arm()  # Aracı kullanmaya hazır hale getir
        return jsonify({"status": "success", "message": f"Bağlantı kuruldu: {com_port}"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Bağlantı kurulamadı: {e}"})

@app.route('/disarm', methods=['POST'])
def disarm():
    global rov
    try:
        if rov is None:
            raise ValueError("ROV bağlantısı kurulamadı.")
        rov.disarm()
        return jsonify({"status": "success", "message": "ROV disarm edildi."})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Hata: {e}"})

@app.route('/move', methods=['POST'])
def move():
    global rov
    try:
        if rov is None:
            raise ValueError("ROV bağlantısı kurulamadı.")
        heave = int(request.json.get('heave', '0') or '0')
        strafe = int(request.json.get('strafe', '0') or '0')
        surge = int(request.json.get('surge', '0') or '0')
        rov.move(heave, strafe, surge)
        return jsonify({"status": "success", "message": f"ROV hareket ettirildi: Heave={heave}, Strafe={strafe}, Surge={surge}"})
    except ValueError as e:
        return jsonify({"status": "error", "message": f"Geçersiz hareket değeri: {e}"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Hata: {e}"})

@app.route('/turn', methods=['POST'])
def turn():
    global rov
    try:
        if rov is None:
            raise ValueError("ROV bağlantısı kurulamadı.")
        angle = int(request.json.get('angle', '0') or '0')
        rov.turn(angle)
        return jsonify({"status": "success", "message": f"ROV {angle} dereceye döndürüldü."})
    except ValueError as e:
        return jsonify({"status": "error", "message": f"Geçersiz açı değeri: {e}"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Hata: {e}"})

@app.route('/turn_degrees', methods=['POST'])
def turn_degrees():
    global rov
    try:
        if rov is None:
            raise ValueError("ROV bağlantısı kurulamadı.")
        degrees = int(request.json.get('degrees', '0') or '0')
        rov.turnDegrees(degrees)
        return jsonify({"status": "success", "message": f"ROV {degrees} derece döndürüldü."})
    except ValueError as e:
        return jsonify({"status": "error", "message": f"Geçersiz derece değeri: {e}"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Hata: {e}"})

@app.route('/start_autonomous_control', methods=['POST'])
def start_autonomous_control():
    global rov
    commands = request.json.get('commands', [])
    for command in commands:
        if command.strip():  # Boş komutları atla
            try:
                direction, distance_cm = command.split()
                distance_cm = int(distance_cm)
                autonomous_control(rov, direction, distance_cm)
            except ValueError:
                return jsonify({"status": "error", "message": f"Geçersiz komut formatı: {command}"})
    return jsonify({"status": "success"})

@app.route('/set_lights', methods=['POST'])
def set_lights():
    global rov
    try:
        if rov is None:
            raise ValueError("ROV bağlantısı kurulamadı.")
        light_intensity = int(request.json.get('light_intensity', '0') or '0')
        rov.lightControl(light_intensity)
        return jsonify({"status": "success", "message": f"Işıklar {light_intensity} seviyesine ayarlandı!"})
    except ValueError as e:
        return jsonify({"status": "error", "message": f"Geçersiz ışık değeri: {e}"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Hata: {e}"})

@app.route('/set_movement', methods=['POST'])
def set_movement():
    global commandData
    try:
        commandData.surge = int(request.json.get('surge', '0') or '0')
        commandData.strafe = int(request.json.get('strafe', '0') or '0')
        commandData.heave = int(request.json.get('heave', '0') or '0')
        return jsonify({"status": "success", "message": f"Hareket değerleri ayarlandı: Surge={commandData.surge}, Strafe={commandData.strafe}, Heave={commandData.heave}"})
    except ValueError as e:
        return jsonify({"status": "error", "message": f"Geçersiz hareket değeri: {e}"})

@app.route('/reset_gyro', methods=['POST'])
def reset_gyro():
    global commandData, receivedData
    if receivedData is not None:
        commandData.heading = receivedData.yaw
        commandData.pitch = receivedData.pitch
        commandData.roll = receivedData.roll
        message = f"Jiroskop sıfırlandı: Heading={commandData.heading}, Pitch={commandData.pitch}, Roll={commandData.roll}"
        return jsonify({"status": "success", "message": message})
    else:
        return jsonify({"status": "error", "message": "Sensör verileri alınamadı."})

@app.route('/toggle_strobe', methods=['POST'])
def toggle_strobe():
    global rov, commandData
    try:
        if rov is None:
            raise ValueError("ROV bağlantısı kurulamadı.")
        if commandData is None:
            raise ValueError("commandData nesnesi bulunamadı.")
        # Çakar ışıklarını kontrol etmek için gerekli kodu buraya ekleyin
        for _ in range(3):  # Işıkları 3 kez çak
            commandData.lightControl = 255  # Işıkları aç
            rov.send()
            time.sleep(0.1)
            commandData.lightControl = 0  # Işıkları kapat
            rov.send()
            time.sleep(0.1)
        return jsonify({"status": "success", "message": "Çakar ışıkları değiştirildi!"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Hata: {e}"})

@app.route('/get_sensor_data', methods=['GET'])
def get_sensor_data():
    global receivedData
    if receivedData is not None:
        data = {
            "rovState": receivedData.rovState,
            "pitch": receivedData.pitch,
            "roll": receivedData.roll,
            "yaw": receivedData.yaw,
            "accelX": receivedData.accelX,
            "accelY": receivedData.accelY,
            "accelZ": receivedData.accelZ,
            "depth": receivedData.depth,
            "battV": receivedData.battV,
            "battA": receivedData.battA,
            "waterTemp": receivedData.waterTemp,
            "internalTemp": receivedData.internalTemp,
            "errCode": receivedData.errCode
        }
        return jsonify(data)
    else:
        return jsonify({"status": "error", "message": "Sensör verileri alınamadı."})

def autonomous_control(rov, direction, distance_cm):
    try:
        if rov is None:
            raise ValueError("ROV bağlantısı kurulamadı.")
        CM_TO_SPEED = 10
        if direction == "forward":
            surge = int(distance_cm * CM_TO_SPEED)
            rov.move(0, 0, surge)
        elif direction == "backward":
            surge = int(-distance_cm * CM_TO_SPEED)
            rov.move(0, 0, surge)
        elif direction == "left":
            strafe = int(-distance_cm * CM_TO_SPEED)
            rov.move(0, strafe, 0)
        elif direction == "right":
            strafe = int(distance_cm * CM_TO_SPEED)
            rov.move(0, strafe, 0)
        elif direction == "up":
            heave = int(distance_cm * CM_TO_SPEED)
            rov.move(heave, 0, 0)
        elif direction == "down":
            heave = int(-distance_cm * CM_TO_SPEED)
            rov.move(heave, 0, 0)
        time.sleep(2)
        stop_motors(rov)
    except Exception as e:
        print(f"autonomous_control içinde hata: {e}")
        stop_motors(rov)

def stop_motors(rov):
    if rov is not None:
        rov.move(0, 0, 0)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)