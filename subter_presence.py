import os
import psutil
import time
import threading
import tkinter as tk
import sys
import ctypes
import logging
from pypresence import Presence
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageTk
import requests
from io import BytesIO
from flask import Flask, request, jsonify

if sys.platform == 'win32':
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

class PresenceState:
    def __init__(self):
        self.game_id = None
        self.game_title = None
        self.client_year = None
        self.start_time = None
        self.last_update = None
        self.stealth_mode = False
        self.custom_icon = "logoremix"
        self.active = False

    def update_game(self, game_id, game_title):
        self.game_id = game_id
        self.game_title = game_title
        self.start_time = int(time.time())
        self.last_update = time.time()
        self.active = True

    def update_client(self, client_year):
        self.client_year = client_year
        self.last_update = time.time()
        self.active = bool(client_year)

    def clear(self):
        self.game_id = None
        self.game_title = None
        self.client_year = None
        self.start_time = None
        self.last_update = None
        self.active = False

    def has_game(self):
        return self.game_id is not None

    def has_client(self):
        return self.client_year is not None

class SubterPresence:
    def __init__(self):
        self.setup_logging()
        self.state = PresenceState()
        self.client_id = '1353747282234707988'
        self.flask_port = 4789
        self.check_interval = 5
        self.RPC = Presence(self.client_id)
        self.connect_rpc()
        self.root = self.create_ui()
        self.setup_tray()
        self.start_threads()

    def setup_logging(self):
        logging.basicConfig(filename='subter_presence.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        with open('subter_presence.log', 'w'):
            pass

    def connect_rpc(self):
        try:
            self.RPC.connect()
        except Exception as e:
            logging.error(f"RPC connection failed: {str(e)}")

    def create_ui(self):
        root = tk.Tk()
        root.title("Subter Presence")
        root.geometry('400x250')
        root.resizable(False, False)
        root.configure(bg='#1e1e1e')

        try:
            icon = Image.open('logo.ico')
            root.iconphoto(False, ImageTk.PhotoImage(icon))
        except Exception:
            pass

        main_frame = tk.Frame(root, bg='#1e1e1e')
        main_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        self.status_label = tk.Label(main_frame, text="Initializing...", font=('Arial', 12, 'bold'), fg='white', bg='#1e1e1e')
        self.status_label.pack(pady=5)

        info_frame = tk.Frame(main_frame, bg='#1e1e1e')
        info_frame.pack(pady=5, fill=tk.X)

        tk.Label(info_frame, text="Game:", font=('Arial', 10), fg='white', bg='#1e1e1e').pack(anchor='w')
        self.game_label = tk.Label(info_frame, text="None", font=('Arial', 10), fg='#4fc3f7', bg='#1e1e1e')
        self.game_label.pack(anchor='w')

        tk.Label(info_frame, text="Client:", font=('Arial', 10), fg='white', bg='#1e1e1e').pack(anchor='w')
        self.client_label = tk.Label(info_frame, text="None", font=('Arial', 10), fg='#4fc3f7', bg='#1e1e1e')
        self.client_label.pack(anchor='w')

        settings_frame = tk.Frame(main_frame, bg='#1e1e1e')
        settings_frame.pack(pady=10, fill=tk.X)

        self.stealth_var = tk.BooleanVar(value=self.state.stealth_mode)
        stealth_check = tk.Checkbutton(settings_frame, text="Stealth Mode", variable=self.stealth_var, command=self.toggle_stealth, fg='white', bg='#1e1e1e', selectcolor='black')
        stealth_check.pack(anchor='w')

        icon_frame = tk.Frame(settings_frame, bg='#1e1e1e')
        icon_frame.pack(anchor='w', pady=5)

        tk.Label(icon_frame, text="Discord Icon:", font=('Arial', 10), fg='white', bg='#1e1e1e').pack(side=tk.LEFT)

        self.icon_var = tk.StringVar(value=self.state.custom_icon)
        icon_options = ["logo", "logoremix"]
        icon_menu = tk.OptionMenu(icon_frame, self.icon_var, *icon_options, command=self.change_icon)
        icon_menu.config(bg='#2e2e2e', fg='white', highlightthickness=0)
        icon_menu.pack(side=tk.LEFT, padx=5)

        self.cooldown_label = tk.Label(root, text="", font=('Arial', 10), fg='yellow', bg='#1e1e1e')
        self.cooldown_label.pack(side=tk.BOTTOM, pady=10, anchor="center")

        root.protocol('WM_DELETE_WINDOW', root.withdraw)
        return root

    def toggle_stealth(self):
        self.state.stealth_mode = self.stealth_var.get()
        self.update_presence_status()
        self.update_ui()

    def change_icon(self, value):
        self.state.custom_icon = value
        self.update_presence_status()

    def setup_tray(self):
        icon_image = self.load_tray_icon()
        menu = Menu(
            MenuItem('Show', lambda: self.root.deiconify()),
            MenuItem('Quit', self.on_quit)
        )
        self.tray_icon = Icon("Subter", icon_image, "Subter Presence", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def load_tray_icon(self):
        try:
            return Image.open('logo.ico')
        except FileNotFoundError:
            try:
                response = requests.get('https://github.com/crawqxx/SubterPresence/raw/main/img/logo.png')
                img = Image.open(BytesIO(response.content))
                img.save('logo.ico', format='ICO')
                return Image.open('logo.ico')
            except Exception:
                return Image.new('RGB', (64, 64), color=(30, 30, 30))

    def start_threads(self):
        threading.Thread(target=self.run_flask, daemon=True).start()
        threading.Thread(target=self.check_client_loop, daemon=True).start()
        threading.Thread(target=self.periodic_checks, daemon=True).start()

    def run_flask(self):
        app = Flask(__name__)

        @app.route('/import_game', methods=['POST'])
        def import_game():
            data = request.json
            if data and 'game_id' in data and 'game_title' in data:
                self.state.update_game(data['game_id'], data['game_title'])
                self.update_ui()
                self.update_presence_status()
                return jsonify({"status": "success"})
            return jsonify({"status": "error"}), 400

        app.run(port=self.flask_port)

    def check_client_loop(self):
        while True:
            self.check_client()
            time.sleep(self.check_interval)

    def check_client(self):
        client_found = False
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            if proc.info['name'].lower() == "subterplayerbeta.exe":
                exe_path = proc.info['exe']
                parent_dir = os.path.basename(os.path.dirname(exe_path))
                if parent_dir.lower().startswith("client"):
                    year = parent_dir[6:]
                    if self.state.client_year != year:
                        self.state.update_client(year)
                        self.update_ui()
                        self.update_presence_status()
                    client_found = True
                    break

        if not client_found and self.state.client_year is not None:
            self.state.update_client(None)
            self.update_ui()
            self.update_presence_status()

    def periodic_checks(self):
        while True:
            self.verify_rpc_connection()
            time.sleep(60)

    def verify_rpc_connection(self):
        try:
            if not self.RPC.sock or not self.RPC.sock.connected:
                self.RPC.connect()
        except Exception as e:
            logging.error(f"RPC reconnect failed: {str(e)}")

    def update_ui(self):
        if self.state.stealth_mode:
            game_text = "Hidden"
        else:
            game_text = self.state.game_title or "None"

        client_text = self.state.client_year or "None"

        self.root.after(0, lambda: self.game_label.config(text=game_text))
        self.root.after(0, lambda: self.client_label.config(text=client_text))

        if self.state.has_game() and self.state.has_client():
            status_text = f"Active: {game_text} ({client_text})"
        elif self.state.has_game():
            status_text = "Game ready - waiting for client..."
        else:
            status_text = "Waiting for game data..."

        self.root.after(0, lambda: self.status_label.config(text=status_text))

    def update_presence_status(self):
        try:
            if self.state.has_game() and self.state.has_client():
                if self.state.stealth_mode:
                    self.RPC.update(
                        details="Subter (Stealth Mode)",
                        state=f"Client {self.state.client_year}",
                        start=self.state.start_time,
                        large_image=self.state.custom_icon
                    )
                else:
                    self.RPC.update(
                        details=self.state.game_title,
                        state=f"Client {self.state.client_year}",
                        start=self.state.start_time,
                        large_image=self.state.custom_icon,
                        buttons=[{"label": "Play Together", "url": f"https://www.subter.org"}]
                    )
            else:
                self.RPC.clear()
        except Exception as e:
            logging.error(f"Presence update failed: {str(e)}")

        self.update_ui()

    def on_quit(self):
        try:
            self.RPC.clear()
            self.tray_icon.stop()
        except Exception:
            pass
        os._exit(0)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = SubterPresence()
    app.run()
