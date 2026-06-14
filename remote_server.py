#!/usr/bin/env python3
"""
PC Remote Control Server - no dependencies, uses only built-in Python modules.
Run this on your PC. Open http://<pc-ip>:5050 on your phone (same WiFi).
"""

import datetime
import getpass
import http.server
import json
import os
import platform
import subprocess
import tempfile
import threading
import time

# CONFIGURATION
PIN = "8034"   # CHANGE THIS to your own PIN
PORT = 5050
disableAdmins = False  # Set True to also log out admin users during disable mode

OS = platform.system()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DISABLE_STATE_FILE = os.path.join(BASE_DIR, "disable_state.json")
LOG_FILE = os.path.join(BASE_DIR, "remote_actions.log")


def run_cmd(cmd):
    subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_later(delay_seconds, cmd):
    if delay_seconds > 0:
        threading.Timer(delay_seconds, run_cmd, args=[cmd]).start()
    else:
        run_cmd(cmd)


def parse_minutes(value, default=0):
    try:
        return max(0, min(int(value), 1440))
    except (TypeError, ValueError):
        return default


def wait_text(action_text, delay_minutes, instant_text):
    if delay_minutes <= 0:
        return instant_text
    if delay_minutes == 60:
        return f"{action_text} in 1 hour..."
    if delay_minutes % 60 == 0:
        return f"{action_text} in {delay_minutes // 60} hours..."
    return f"{action_text} in {delay_minutes} min..."


def minutes_text(minutes):
    if minutes == 60:
        return "1 hour"
    if minutes > 60 and minutes % 60 == 0:
        return f"{minutes // 60} hours"
    return f"{minutes} min"


def current_user():
    try:
        return getpass.getuser()
    except Exception:
        return "Unknown"


def log_action(user, action, client_ip, message):
    if action == "ping":
        return

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} | user={user} | ip={client_ip or 'unknown'} | action={action or 'unknown'}\n"
    if message:
        line = f"{timestamp} | user={user} | ip={client_ip or 'unknown'} | action={action or 'unknown'} | message={message or 'unknown'}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def is_current_user_admin():
    if OS == "Windows":
        try:
            groups = subprocess.check_output(
                "whoami /groups",
                shell=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                stderr=subprocess.DEVNULL,
            )
            if "S-1-5-32-544" in groups:
                return True
        except Exception:
            pass

        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    if hasattr(os, "geteuid") and os.geteuid() == 0:
        return True

    try:
        groups = subprocess.check_output(
            "id -Gn",
            shell=True,
            text=True,
            errors="ignore",
            stderr=subprocess.DEVNULL,
        ).split()
        return any(group in ("admin", "sudo", "wheel") for group in groups)
    except Exception:
        return False


def logout_command():
    if OS == "Windows":
        return "shutdown /l /f"
    if OS == "Darwin":
        return "osascript -e 'tell application \"System Events\" to log out'"
    return "pkill -KILL -u $(whoami)"


def load_disable_state():
    try:
        with open(DISABLE_STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        return state if isinstance(state, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def save_disable_state(until_ts, duration_minutes):
    state = {
        "disabled_until": until_ts,
        "duration_minutes": duration_minutes,
        "created_at": time.time(),
    }
    with open(DISABLE_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)


def clear_disable_state():
    try:
        os.remove(DISABLE_STATE_FILE)
    except FileNotFoundError:
        pass
    except Exception:
        with open(DISABLE_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)


def disable_status():
    state = load_disable_state()
    until_ts = float(state.get("disabled_until", 0) or 0)
    now = time.time()
    if until_ts <= now:
        if until_ts:
            clear_disable_state()
        return {"active": False, "remaining_seconds": 0, "until": 0}

    return {
        "active": True,
        "remaining_seconds": int(until_ts - now),
        "until": until_ts,
    }


def enforce_disable_if_needed():
    status = disable_status()
    admin = is_current_user_admin()
    if status["active"] and (disableAdmins or not admin):
        threading.Timer(1, run_cmd, args=[logout_command()]).start()
        return True, admin, status
    return False, admin, status


def handle_action(data):
    action = data.get("action", "")
    delay_minutes = parse_minutes(data.get("delay", 0))
    delay_seconds = delay_minutes * 60

    if action == "ping":
        kicked, admin, status = enforce_disable_if_needed()
        msg = f"PC is online ({OS})"
        if kicked:
            msg = "Access disabled - logging out user" if disableAdmins else "Access disabled - logging out non-admin user"
        return {
            "ok": True,
            "msg": msg,
            "user": current_user(),
            "admin": admin,
            "disabled": status["active"],
            "disableRemaining": status["remaining_seconds"],
        }

    if action == "lock":
        if OS == "Windows":
            cmd = "rundll32.exe user32.dll,LockWorkStation"
        elif OS == "Darwin":
            cmd = "/System/Library/CoreServices/Menu\\ Extras/User.menu/Contents/Resources/CGSession -suspend"
        else:
            cmd = "loginctl lock-session"
        run_later(delay_seconds, cmd)
        return {"ok": True, "msg": wait_text("Locking screen", delay_minutes, "Locking screen...")}

    if action == "logout":
        run_later(delay_seconds, logout_command())
        return {"ok": True, "msg": wait_text("Logging out", delay_minutes, "Logging out...")}

    if action == "restart":
        if OS == "Windows":
            seconds = delay_seconds if delay_seconds > 0 else 5
            run_cmd(f"shutdown /r /f /t {seconds}")
        elif OS == "Darwin":
            run_cmd(f"sudo shutdown -r +{delay_minutes}" if delay_minutes > 0 else "sudo shutdown -r +0")
        else:
            run_cmd(f"sudo shutdown -r +{delay_minutes}" if delay_minutes > 0 else "sudo shutdown -r now")
        return {"ok": True, "msg": wait_text("Restarting", delay_minutes, "Restarting in 5 seconds...")}

    if action == "shutdown":
        if OS == "Windows":
            seconds = delay_seconds if delay_seconds > 0 else 5
            run_cmd(f"shutdown /s /f /t {seconds}")
        elif OS == "Darwin":
            run_cmd(f"sudo shutdown -h +{delay_minutes}" if delay_minutes > 0 else "sudo shutdown -h +0")
        else:
            run_cmd(f"sudo shutdown -h +{delay_minutes}" if delay_minutes > 0 else "sudo shutdown -h now")
        return {"ok": True, "msg": wait_text("Shutting down", delay_minutes, "Shutting down in 5 seconds...")}

    if action == "message":
        message = str(data.get("message", "")).strip()
        if not message:
            return {"ok": False, "msg": "Message is empty"}

        if OS == "Windows":
            import base64

            ps_path = os.path.join(tempfile.gettempdir(), "pc_remote_message.ps1")
            msg_b64 = base64.b64encode(message.encode("utf-8")).decode("ascii")
            ps = f"""$msg = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{msg_b64}'))
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$form = New-Object System.Windows.Forms.Form
$form.Text = 'Message'
$form.TopMost = $true
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.StartPosition = 'CenterScreen'
$form.Width = 420
$form.Height = 220
$form.Padding = New-Object System.Windows.Forms.Padding(16)
$label = New-Object System.Windows.Forms.Label
$label.Text = $msg
$label.AutoSize = $false
$label.Dock = 'Fill'
$label.TextAlign = 'MiddleCenter'
$label.Font = New-Object System.Drawing.Font('Segoe UI', 10)
$form.Controls.Add($label)
$button = New-Object System.Windows.Forms.Button
$button.Text = 'OK'
$button.Dock = 'Bottom'
$button.Height = 36
$button.Add_Click({{ $form.Close() }})
$form.Controls.Add($button)
$form.Add_Shown({{
    $form.Activate()
    $form.BringToFront()
    $form.Focus()
    [void][System.Windows.Forms.Application]::DoEvents()
}})
[void]$form.ShowDialog()
"""
            with open(ps_path, "w", encoding="utf-8", newline="\r\n") as f:
                f.write(ps)
            run_later(
                delay_seconds,
                f'powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "{ps_path}"',
            )
        elif OS == "Darwin":
            safe_message = message.replace("\\", "\\\\").replace('"', '\\"')
            run_later(delay_seconds, f'osascript -e \'display dialog "{safe_message}" with title "Message"\'')
        else:
            safe_message = message.replace("\\", "\\\\").replace('"', '\\"')
            run_later(delay_seconds, f'notify-send "Message" "{safe_message}"')
        return {"ok": True, "msg": wait_text("Showing message", delay_minutes, "Message sent")}

    if action == "disable":
        duration_minutes = parse_minutes(data.get("duration", data.get("delay", 60)), default=60)
        if duration_minutes <= 0:
            return {"ok": False, "msg": "Choose a disable duration"}

        until_ts = time.time() + (duration_minutes * 60)
        try:
            save_disable_state(until_ts, duration_minutes)
        except Exception as e:
            return {"ok": False, "msg": f"Could not save disable state: {e}"}

        admin = is_current_user_admin()
        if disableAdmins or not admin:
            threading.Timer(1, run_cmd, args=[logout_command()]).start()
            target = "user" if admin else "non-admin user"
            return {"ok": True, "msg": f"Disabled for {minutes_text(duration_minutes)}. Logging out {target}..."}

        return {"ok": True, "msg": f"Disabled for {minutes_text(duration_minutes)}. Admin user remains allowed."}

    if action == "enable":
        clear_disable_state()
        return {"ok": True, "msg": "Computer re-enabled"}

    return {"ok": False, "msg": "Unknown action"}


class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, *args):
        pass

    def send_json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/" or path == "/index.html":
            filepath = os.path.join(BASE_DIR, "pc_remote_ui.html")
            if os.path.exists(filepath):
                with open(filepath, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", len(data))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_json(404, {"error": "pc_remote_ui.html not found next to server script"})
        else:
            self.send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/action":
            self.send_json(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(length))
        except Exception:
            self.send_json(400, {"ok": False, "msg": "Bad JSON"})
            return

        if data.get("pin") != PIN:
            self.send_json(403, {"ok": False, "msg": "Wrong PIN"})
            return

        result = handle_action(data)
        message = data.get("message", "")
        log_action(current_user(), data.get("action", ""), self.client_address[0] if self.client_address else "unknown", message if message else None)
        self.send_json(200, result)


if __name__ == "__main__":
    kicked, admin, status = enforce_disable_if_needed()
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"\n  PC Remote Control - port {PORT} - no dependencies needed")
    print(f"  Open http://<this-pc-ip>:{PORT} on your phone")
    if status["active"]:
        print(f"  Disable mode active. Admin={admin}. Non-admin logout scheduled={kicked}.")
    print()
    server.serve_forever()
