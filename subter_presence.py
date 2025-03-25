import os
import psutil
import time
from pypresence import Presence
from pystray import Icon, MenuItem, Menu
from PIL import Image
import threading
import tkinter as tk
import sys
import ctypes
from flask import Flask, request, jsonify
import requests
from io import BytesIO

if sys.platform == 'win32':
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

app = Flask(__name__)
client_id = "1353747282234707988"
RPC = Presence(client_id)
RPC.connect()

game_id = None
game_title = None
start_time = None
client_year = None
has_game_data = False
has_client = False

root = tk.Tk()
root.title("Subter Presence")
root.geometry('300x150')
root.resizable(False, False)
root.configure(bg='#1e1e1e')

status_label = tk.Label(
    root, 
    text="Waiting for game data and client...", 
    font=('Arial', 12), 
    fg='white', 
    bg='#1e1e1e'
)
status_label.pack(expand=True)

def check_client():
    global client_year, has_client
    while True:
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            if proc.info['name'].lower() == "subterplayerbeta.exe":
                exe_path = proc.info['exe']
                parent_dir = os.path.basename(os.path.dirname(exe_path))
                if parent_dir.lower().startswith("client"):
                    client_year = parent_dir[6:]
                    if not has_client:
                        has_client = True
                        update_presence_status()
                    break
        else:
            if has_client:
                has_client = False
                update_presence_status()
        time.sleep(5)

def update_presence_status():
    if has_game_data and has_client:
        start_time = int(time.time())
        RPC.update(
            details=game_title,
            state=f"Playing {client_year}",
            start=start_time,
            buttons=[{"label": "Play Together", "url": f"https://www.subter.org/games/{game_id}"}]
        )
        root.after(0, lambda: status_label.config(text=f"Active: {game_title} ({client_year})"))
    else:
        RPC.clear()
        if has_game_data:
            root.after(0, lambda: status_label.config(text=f"Game data ready - waiting for client..."))
        else:
            root.after(0, lambda: status_label.config(text="Waiting for game data and client..."))

@app.route('/import_game', methods=['POST'])
def import_game():
    global game_id, game_title, has_game_data
    data = request.json
    game_id = data.get('game_id')
    game_title = data.get('game_title')
    has_game_data = True
    update_presence_status()
    return jsonify({"status": "success"})

def load_tray_icon():
    try:
        return Image.open('logo.ico')
    except FileNotFoundError:
        try:
            response = requests.get('https://github.com/crawqxx/SubterPresence/raw/main/img/logo.png')
            img = Image.open(BytesIO(response.content))
            
            img.save('logo.ico', format='ICO')
            return Image.open('logo.ico')
        except Exception as e:
            print(f"Error loading icon: {e}")
            return Image.new('RGB', (64, 64), color=(30, 30, 30))

def on_quit():
    RPC.clear()
    os._exit(0)

def setup_tray():
    icon_image = load_tray_icon()
    menu = Menu(
        MenuItem('Show', lambda: root.deiconify()),
        MenuItem('Quit', on_quit)
    )
    icon = Icon("Subter", icon_image, "Subter Presence", menu)
    icon.run()

def run_flask():
    app.run(port=4789)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    client_thread = threading.Thread(target=check_client, daemon=True)
    client_thread.start()

    root.protocol('WM_DELETE_WINDOW', root.withdraw)
    threading.Thread(target=setup_tray, daemon=True).start()
    root.mainloop()
