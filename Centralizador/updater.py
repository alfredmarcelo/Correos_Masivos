"""
Auto-actualizador via GitHub Releases.
Revisa si hay una versión nueva del ejecutable en GitHub y lo descarga automáticamente.

Uso:
  1. Crea un repositorio en GitHub (ej: tu-usuario/SaludYCorreos)
  2. Sube releases con un tag de versión (ej: v1.0.0, v1.1.0)
  3. Adjunta el .exe como asset del release
  4. Cambia GITHUB_REPO abajo con tu usuario/repo
"""

import os
import sys
import json
import shutil
import subprocess
import tempfile
from urllib.request import urlopen, Request
from urllib.error import URLError

# ══════════════════════════════════════════════════════════
# CONFIGURACIÓN — Cambia estos valores con tu repositorio
# ══════════════════════════════════════════════════════════
GITHUB_REPO = "alfredmarcelo/Correos_Masivos"  # ← Cambiar por tu repo real
CURRENT_VERSION = "1.0.0"                  # ← Incrementar con cada release
EXE_NAME = "Centralizador.exe"            # ← Nombre del .exe en el release
# ══════════════════════════════════════════════════════════


def _parse_version(version_str):
    """Convierte 'v1.2.3' o '1.2.3' en tupla (1, 2, 3) para comparar."""
    clean = version_str.strip().lstrip("v")
    try:
        return tuple(int(x) for x in clean.split("."))
    except ValueError:
        return (0, 0, 0)


def check_for_update():
    """Consulta la API de GitHub para ver si hay una versión nueva.
    
    Returns:
        dict con info de la actualización, o None si no hay actualización.
        Ejemplo: {
            "version": "1.1.0",
            "download_url": "https://github.com/.../SaludYCorreos.exe",
            "release_notes": "Correcciones de bugs..."
        }
    """
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    
    try:
        req = Request(api_url, headers={"Accept": "application/vnd.github.v3+json"})
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (URLError, json.JSONDecodeError, TimeoutError) as e:
        print(f"[Updater] No se pudo verificar actualizaciones: {e}")
        return None

    latest_version = data.get("tag_name", "0.0.0")
    
    # Comparar versiones
    if _parse_version(latest_version) <= _parse_version(CURRENT_VERSION):
        print(f"[Updater] Versión actual ({CURRENT_VERSION}) está al día.")
        return None

    # Buscar el .exe en los assets del release
    download_url = None
    for asset in data.get("assets", []):
        if asset["name"].lower() == EXE_NAME.lower():
            download_url = asset["browser_download_url"]
            break

    if not download_url:
        print(f"[Updater] Release {latest_version} encontrado pero no tiene '{EXE_NAME}' adjunto.")
        return None

    return {
        "version": latest_version.lstrip("v"),
        "download_url": download_url,
        "release_notes": data.get("body", "Sin notas de la versión."),
    }


def download_update(download_url, progress_callback=None):
    """Descarga el nuevo ejecutable a un archivo temporal.
    
    Args:
        download_url: URL directa del .exe en GitHub.
        progress_callback: Función opcional que recibe (bytes_descargados, bytes_totales).
    
    Returns:
        Ruta al archivo temporal descargado, o None si falla.
    """
    try:
        req = Request(download_url, headers={
            "Accept": "application/octet-stream",
            "User-Agent": "Centralizador-Updater"
        })
        
        with urlopen(req, timeout=120) as response:
            total_size = int(response.headers.get("Content-Length", 0))
            
            # Descargar a archivo temporal en el mismo directorio
            # (para que el rename sea atómico en el mismo filesystem)
            app_dir = os.path.dirname(os.path.abspath(sys.executable))
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".exe.tmp", dir=app_dir)
            
            downloaded = 0
            chunk_size = 65536  # 64KB por chunk
            
            with os.fdopen(tmp_fd, "wb") as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size:
                        progress_callback(downloaded, total_size)
        
        print(f"[Updater] Descarga completada: {downloaded:,} bytes")
        return tmp_path
        
    except Exception as e:
        print(f"[Updater] Error descargando actualización: {e}")
        return None


def apply_update(tmp_path):
    """Reemplaza el ejecutable actual con el nuevo y reinicia la app.
    
    Usa un script .bat auxiliar porque Windows no permite sobreescribir
    un .exe mientras se está ejecutando.
    """
    current_exe = os.path.abspath(sys.executable)
    app_dir = os.path.dirname(current_exe)
    backup_path = current_exe + ".backup"
    
    # Crear un script batch que:
    # 1. Espera a que el proceso actual termine
    # 2. Renombra el exe actual como backup
    # 3. Mueve el nuevo exe al lugar del anterior
    # 4. Ejecuta el nuevo exe
    # 5. Elimina el backup y el propio script
    bat_content = f"""@echo off
echo Aplicando actualizacion...
timeout /t 2 /nobreak > nul
del "{backup_path}" 2>nul
move /Y "{current_exe}" "{backup_path}"
move /Y "{tmp_path}" "{current_exe}"
echo Reiniciando...
start "" "{current_exe}"
del "{backup_path}" 2>nul
del "%~f0"
"""
    
    bat_path = os.path.join(app_dir, "_update.bat")
    with open(bat_path, "w") as f:
        f.write(bat_content)
    
    # Ejecutar el script y cerrar la app
    subprocess.Popen(
        ["cmd", "/c", bat_path],
        creationflags=subprocess.CREATE_NO_WINDOW,
        cwd=app_dir
    )
    
    print("[Updater] Reiniciando para aplicar actualización...")
    sys.exit(0)


def check_and_prompt_update(parent_widget=None):
    """Función principal: verifica, descarga y aplica actualizaciones.
    Muestra diálogos Qt si parent_widget es proporcionado.
    
    Llamar al inicio de la app, antes de mostrar la ventana principal.
    """
    from PyQt6.QtWidgets import QMessageBox, QProgressDialog
    from PyQt6.QtCore import Qt
    
    # Verificar si estamos corriendo como .exe empaquetado
    if not getattr(sys, 'frozen', False):
        print("[Updater] No es un ejecutable empaquetado, omitiendo actualización.")
        return False
    
    update_info = check_for_update()
    if not update_info:
        return False
    
    # Preguntar al usuario
    reply = QMessageBox.question(
        parent_widget,
        "Actualización disponible",
        f"Hay una nueva versión disponible: v{update_info['version']}\n"
        f"Versión actual: v{CURRENT_VERSION}\n\n"
        f"{update_info['release_notes'][:300]}\n\n"  
        f"¿Deseas actualizar ahora?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes
    )
    
    if reply != QMessageBox.StandardButton.Yes:
        return False
    
    # Mostrar progreso de descarga
    progress = QProgressDialog(
        "Descargando actualización...", "Cancelar", 0, 100, parent_widget
    )
    progress.setWindowTitle("Actualizando Centralizador")
    progress.setWindowModality(Qt.WindowModality.WindowModal)
    progress.setMinimumDuration(0)
    progress.show()
    
    def on_progress(downloaded, total):
        percent = int((downloaded / total) * 100)
        progress.setValue(percent)
        progress.setLabelText(
            f"Descargando: {downloaded // 1024 // 1024}MB / {total // 1024 // 1024}MB"
        )
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
    
    tmp_path = download_update(update_info["download_url"], on_progress)
    progress.close()
    
    if not tmp_path:
        QMessageBox.warning(
            parent_widget,
            "Error",
            "No se pudo descargar la actualización. Intenta más tarde."
        )
        return False
    
    # Aplicar la actualización
    apply_update(tmp_path)
    return True  # No debería llegar aquí porque apply_update hace sys.exit
