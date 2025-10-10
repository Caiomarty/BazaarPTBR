import tkinter as tk
from tkinter import ttk, messagebox
import requests
import zipfile
import io
import os
import shutil
import threading

OWNER = "Fesantt"
REPO = "HardenedEntropyCipher"
ASSET_NAME = "v11"

DEST_DIR = os.path.join(os.path.expanduser("~"), "AppData", "LocalLow", "The Bazaar", "prod", "cache")
VERSION_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "version.txt")

def get_current_version():
    """Lê a versão atual do arquivo local ou retorna uma versão padrão."""
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r") as f:
            return f.read().strip()
    return "v0.0.0"

def save_new_version(new_version):
    """Salva a nova versão no arquivo local."""
    with open(VERSION_FILE, "w") as f:
        f.write(new_version)

def check_latest_release(status_label, update_button, cur_ver_label):
    """Consulta a última release no GitHub em uma thread separada."""
    status_label.config(text="🔍 Verificando GitHub...")
    update_button.config(state=tk.DISABLED)
    current_version = get_current_version()

    try:
        url = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
        r = requests.get(url)
        r.raise_for_status()
        release = r.json()
        latest_version = release["tag_name"]
        
        asset_url = next(
            (asset["browser_download_url"] for asset in release.get("assets", []) if asset["name"] == ASSET_NAME),
            None,
        )

        if asset_url and latest_version != current_version:
            status_label.config(text=f"⚡ Nova versão disponível: {latest_version}")
            update_button.config(state=tk.NORMAL)
            return asset_url, latest_version
        elif latest_version == current_version:
            status_label.config(text="✅ Você já está na última versão.")
        else:
            status_label.config(text="❌ Arquivo de atualização não encontrado na release.")
            
    except Exception as e:
        status_label.config(text=f"❌ Erro: {e}")
        
    return None, None

def download_and_extract(asset_url, new_version, status_label, update_button, cur_ver_label):
    """Baixa e extrai o ZIP em uma thread separada."""
    status_label.config(text="🔄 Baixando atualização...")
    update_button.config(state=tk.DISABLED)
    try:
        r = requests.get(asset_url)
        r.raise_for_status()
        z = zipfile.ZipFile(io.BytesIO(r.content))

        if os.path.exists(DEST_DIR):
            shutil.rmtree(DEST_DIR)
        os.makedirs(DEST_DIR, exist_ok=True)
        z.extractall(DEST_DIR)

        save_new_version(new_version)
        cur_ver_label.config(text=f"Versão atual: {new_version}")

        status_label.config(text="✨ Atualização concluída com sucesso!")
        messagebox.showinfo("Atualização", "Arquivos atualizados com sucesso!")
    except Exception as e:
        status_label.config(text=f"❌ Erro de download: {e}")
    finally:
        update_button.config(state=tk.NORMAL)

# --- Interface do Tkinter ---
def create_gui():
    root = tk.Tk()
    root.title("The Bazaar - Atualizador de Tradução")
    root.geometry("400x200")
    root.resizable(False, False)

    frame = ttk.Frame(root, padding="10")
    frame.pack(fill=tk.BOTH, expand=True)

    title_label = ttk.Label(frame, text="Instalar/Atualizar Tradução", font=("Helvetica", 16, "bold"))
    title_label.pack(pady=5)

    cur_ver_label = ttk.Label(frame, text=f"Versão atual: {get_current_version()}")
    cur_ver_label.pack(pady=2)

    status_label = ttk.Label(frame, text="Aguardando verificação...", font=("Helvetica", 10, "italic"))
    status_label.pack(pady=10)

    button_frame = ttk.Frame(frame)
    button_frame.pack(pady=5)

    update_button = ttk.Button(button_frame, text="Atualizar", state=tk.DISABLED)
    check_button = ttk.Button(button_frame, text="Verificar Atualizações")

    def on_check():
        threading.Thread(target=lambda: check_and_update(status_label, update_button, cur_ver_label)).start()

    def check_and_update(status_label, update_button, cur_ver_label):
        asset_url, new_version = check_latest_release(status_label, update_button, cur_ver_label)
        if asset_url and new_version:
            update_button.config(command=lambda: threading.Thread(target=download_and_extract, args=(asset_url, new_version, status_label, update_button, cur_ver_label)).start())

    check_button.config(command=on_check)

    check_button.pack(side=tk.LEFT, padx=5)
    update_button.pack(side=tk.RIGHT, padx=5)

    root.mainloop()

if __name__ == "__main__":
    create_gui()