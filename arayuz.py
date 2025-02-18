import tkinter as tk
from tkinter import messagebox, ttk, PhotoImage
from PIL import Image, ImageTk
import serial
import serial.tools.list_ports
import time
import pygame
import cv2
import threading
import numpy as np


# Seri portları tarayıp listeye ekler
def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

# Xbox joystickten veri almak için pygame başlat
def init_joystick():
    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() > 0:
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        messagebox.showinfo("Joystick", "Joystick algılandı!")
        return joystick
    else:
        messagebox.showwarning("Hata", "Joystick bulunamadı!")
        return None

# Seri portu başlatma (seçilen porta göre)
def connect_serial(selected_port):
    try:
        ser = serial.Serial(selected_port, 9600, timeout=1)
        time.sleep(2)  # Bağlantının sağlanması için kısa bir bekleme
        return ser
    except:
        messagebox.showwarning("Hata", "Seri porta bağlanılamadı!")
        return None

# Kameradan veri alıp ekrana yansıtma
def display_camera_feed(cap, camera_frame, renk_tanima_aktif):
    def display_frame():
        ret, frame = cap.read()
        if ret:
            if renk_tanima_aktif:
                renkler = ["mavi", "yesil", "kirmizi", "sari"]
                for renk in renkler:
                    frame = tanimla_renk(frame, renk)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            img = img.resize((800, 600), Image.LANCZOS)
            camera_frame.imgtk = ImageTk.PhotoImage(image=img)
            camera_frame.configure(image=camera_frame.imgtk)
        camera_frame.after(10, display_frame)  # 10 ms sonra yeniden çağır
    display_frame()  # İlk kareyi başlat

# Kamerayı başlat ve beslemeyi göster
def start_camera():
    global cap, camera_button, camera_frame, renk_tanima_aktif
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        messagebox.showerror("Kamera", "Kamera başlatılamadı!")
        return
    camera_frame = tk.Label(root)
    camera_frame.pack(pady=10)
    display_camera_feed(cap, camera_frame, renk_tanima_aktif)

    # Kamera başlatıldığında butonu "Kapat" olarak değiştir
    camera_button.config(text="Kamera Bağlantısını Kapat", command=close_camera)

# Kamerayı kapatma işlevi
def close_camera():
    global cap, camera_button, camera_frame
    if cap and cap.isOpened():
        cap.release()
    camera_button.config(text="Kamera Başlat", command=start_camera)

    # Kamera görüntüsünü temizle
    camera_frame.destroy()  # Mevcut frame'i kaldır
    camera_frame = None  # camera_frame'i sıfırla

# Parametreler sekmesini açan fonksiyon
def show_parameters():
    param_window = tk.Toplevel(root)
    param_window.title("Parametreler")
    param_window.geometry("300x200")
    tk.Label(param_window, text="Parametreleri buradan ayarlayın.", font=("Arial", 12)).pack(pady=10)
    close_button = tk.Button(param_window, text="X", command=param_window.destroy)
    close_button.pack(pady=10)

# Seri portu başlatma fonksiyonu
def start_connection():
    selected_port = port_var.get()
    global ser
    ser = connect_serial(selected_port)
    joystick = init_joystick()
    if ser and joystick:
        # Buton metnini "Bağlantıyı Kapat" olarak değiştir
        start_button.config(text="Bağlantıyı Kapat", command=close_all_connections)
        messagebox.showinfo("Bağlantı", "Seri port ve joystick bağlantısı başarılı!")
    else:
        messagebox.showwarning("Hata", "Bağlantı sağlanamadı!")

# Bağlantıyı kapatma işlevi
def close_all_connections():
    global ser
    if ser:
        ser.close()
        ser = None
    # Buton metnini "Bağlantıyı Başlat" olarak değiştir
    start_button.config(text="Bağlantıyı Başlat", command=start_connection)
    messagebox.showinfo("Bağlantı", "Bağlantı kesildi.")

# Arayüzde renk tanımayı açma/kapama fonksiyonu
def toggle_renk_tanima():
    global renk_tanima_aktif
    renk_tanima_aktif = not renk_tanima_aktif
    if renk_tanima_aktif:
        renk_toggle_button.config(text="Renk Tanımayı Kapat")
    else:
        renk_toggle_button.config(text="Renk Tanımayı Başlat")

# Renk tanıma fonksiyonları
def tanimla_renk(frame, renk_adi):
    renk_isimleri = {
        "mavi": (255, 0, 0),
        "yesil": (0, 255, 0),
        "kirmizi": (0, 0, 255),
        "sari": (0, 255, 255),
    }

    if renk_adi in renk_isimleri:
        renk_kodu = renk_isimleri[renk_adi]
    else:
        print("Geçersiz renk adi!")
        return None

    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    araliklar = renk_alanlari(renk_adi)

    if renk_adi == "kirmizi":
        lower1, upper1, lower2, upper2 = araliklar
        mask1 = cv2.inRange(hsv_frame, lower1, upper1)
        mask2 = cv2.inRange(hsv_frame, lower2, upper2)
        mask = cv2.bitwise_or(mask1, mask2)
    else:
        lower, upper = araliklar
        mask = cv2.inRange(hsv_frame, lower, upper)

    cilt_maskesi = cilt_tonu_maskesi(frame)
    mask = cv2.bitwise_and(mask, cv2.bitwise_not(cilt_maskesi))  

    mask = cv2.GaussianBlur(mask, (5, 5), 0)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 500:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(frame, (x, y), (x + w, y + h), renk_kodu, 2)
            cv2.putText(frame, renk_adi.capitalize(), (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, renk_kodu, 2)

    return frame

def renk_alanlari(renk_adi):
    if renk_adi == "mavi":
        return np.array([105, 150, 50]), np.array([115, 255, 255])  
    elif renk_adi == "yesil":
        return np.array([50, 100, 50]), np.array([70, 255, 255])
    elif renk_adi == "kirmizi":
        lower1 = np.array([0, 120, 100])
        upper1 = np.array([5, 255, 255])
        lower2 = np.array([175, 120, 100])
        upper2 = np.array([180, 255, 255])
        return lower1, upper1, lower2, upper2
    elif renk_adi == "sari":
        return np.array([25, 100, 100]), np.array([35, 255, 255])
    else:
        return None, None

def cilt_tonu_maskesi(frame):
    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower = np.array([0, 20, 50])
    upper = np.array([20, 255, 255])
    mask = cv2.inRange(hsv_frame, lower, upper)
    return mask

# Işık açma/kapama işlevi
def toggle_light():
    global light_on
    light_on = not light_on
    if light_on:
        light_button.config(text="Işık Kapat", bg="red")
    else:
        light_button.config(text="Işık Aç", bg="green")

# Arayüz oluşturma
def create_gui():
    global root, camera_button, start_button, ser, cap, port_var, renk_tanima_aktif, renk_toggle_button, camera_frame, left_logo, right_logo, light_button, light_on
    renk_tanima_aktif = False  # Başlangıçta renk tanıma kapalı
    ser = None
    cap = None
    camera_frame = None
    light_on = False  # Başlangıçta ışık kapalı
    root = tk.Tk()
    root.title("Su Altı Aracı Kontrol Paneli")
    root.geometry("500x500")
    root.configure(bg='black')  # Arka plan rengini siyah yap

    # Sol üst logo
    left_logo = Image.open("mesafe-Photoroom.png")
    left_logo = ImageTk.PhotoImage(left_logo.resize((70, 70)))
    left_logo_label = tk.Label(root, image=left_logo, bg="black")
    left_logo_label.place(x=10, y=10)

    # Sağ üst logo
    right_logo = Image.open("akvalogo.jpg")
    right_logo = ImageTk.PhotoImage(right_logo.resize((70, 70)))
    right_logo_label = tk.Label(root, image=right_logo, bg="black")
    right_logo_label.place(x=1200, y=9)

    # Seri port seçimi
    port_var = tk.StringVar(root)
    port_label = tk.Label(root, text="Seri Port Seçin:", fg="white", bg="black")
    port_label.pack(pady=5)
    port_combobox = ttk.Combobox(root, textvariable=port_var, values=list_serial_ports())
    port_combobox.pack(pady=5)

    # Bağlantı başlatma butonu
    start_button = tk.Button(root, text="Bağlantıyı Başlat", command=start_connection, width=20)
    start_button.pack(pady=10)

    # Parametreler butonu
    param_button = tk.Button(root, text="Parameters", command=show_parameters, width=20)
    param_button.pack(pady=10)

    
    camera_button = tk.Button(root, text="Kamera Başlat", command=start_camera, width=20)
    camera_button.pack(side="bottom", pady=10)

    renk_toggle_button = tk.Button(root, text="Renk Tanımayı Başlat", command=toggle_renk_tanima, width=20)
    renk_toggle_button.pack(side="bottom", pady=10)

    
    light_button = tk.Button(root, text="Işık Aç", command=toggle_light, width=20, bg="green")
    light_button.pack(side="bottom",anchor="w", padx=10, pady=10)

    root.mainloop()

create_gui()
