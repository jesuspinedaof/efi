"""
EFI App - Demo
----------------------
Aplicación de escritorio para eliminar fondos de imágenes con IA.

Autor: Jesús Pineda
Correo: tornioficial@gmail.com
GitHub: https://github.com/jesuspinedaof
Linktree: https://linktr.ee/jesuspinedaof

Licencia: MIT License
"""


import cv2
import sys
import numpy as np
import webbrowser
import os
import threading
import requests
from io import BytesIO
import time
import random
from pathlib import Path
import certifi
from plyer import notification

# --- UI ---
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
from tkinter.ttk import Button, Label, Progressbar, Style

# --- Imagen ---
from PIL import Image, ImageTk, ImageOps, ImageDraw

# --- IA / Remoción de fondo ---
from rembg import remove, new_session

def resource_path(relative_path: str) -> str:
    """
    Devuelve la ruta absoluta a un recurso dentro de un .exe (PyInstaller)
    o en modo normal (carpeta del proyecto).
    """
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)

MODEL_URLS = {
    "objetos": "https://github.com/jesuspinedaof/efi/releases/download/v1.0/u2net.onnx"
}
def get_cache_dir():
    if sys.platform.startswith('win'):
        base = os.getenv('LOCALAPPDATA') or os.path.expanduser(r"~\AppData\Local")
    elif sys.platform == 'darwin':
        base = os.path.expanduser("~/Library/Caches")
    else:
        base = os.getenv('XDG_CACHE_HOME') or os.path.expanduser("~/.cache")
    return os.path.join(base, "BackgroundRemover", "model_cache")

CACHE_DIR = get_cache_dir()
os.makedirs(CACHE_DIR, exist_ok=True)

# MUY IMPORTANTE: decirle a rembg dónde están/irán los modelos
os.environ.setdefault("U2NET_HOME", CACHE_DIR)

class BackgroundRemoverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Eliminar fondo de imagen")
        self.root.geometry("700x500")
        self.root.resizable(False, False)
        
        self.processing = False
        self.current_image = None
        self.output_path = ""
        self.mode = "objetos"
        
        self.setup_ui()
        
    def setup_ui(self):
        try:
            self.root.iconbitmap(resource_path("resources/efi-icon.ico"))

        except:
            pass
        
        main_frame = tk.Frame(self.root, padx=20, pady=20, bg="#f5f5f5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title_label = tk.Label(
            main_frame, 
            text="EFI AI - DEMO", 
            font=("Segoe UI", 22, "bold"),
            fg="#2c3e50",
            bg="#f5f5f5"
        )
        title_label.pack(pady=(0, 10))
        
        mode_frame = tk.Frame(main_frame, bg="#f5f5f5")
        mode_frame.pack(pady=(0, 15))
        
        self.mode_var = tk.StringVar(value="objetos")
        
        tk.Radiobutton(
            mode_frame, 
            text="Modo Objetos", 
            variable=self.mode_var,
            value="objetos",
            font=("Segoe UI", 10),
            bg="#f5f5f5",
            command=self.update_mode
        ).pack(side=tk.LEFT, padx=10)
        
        tk.Radiobutton(
            mode_frame, 
            text="Modo Personas", 
            variable=self.mode_var,
            value="mensaje-pmd",
            font=("Segoe UI", 10),
            bg="#f5f5f5",
            command=self._show_mensaje_alert
        ).pack(side=tk.LEFT, padx=10)
        
        tk.Radiobutton(
            mode_frame, 
            text="Seleccionar área", 
            variable=self.mode_var,
            value="mensaje-pmd",
            font=("Segoe UI", 10),
            bg="#f5f5f5",
            command=self._show_mensaje_alert
        ).pack(side=tk.LEFT, padx=10)
        
        self.btn_select = Button(
            main_frame, 
            text="📷 Seleccionar Imagen", 
            command=self.select_image,
            style="Accent.TButton"
        )
        self.btn_select.pack(pady=15, ipadx=15, ipady=5)
        
        self.progress = Progressbar(
            main_frame, 
            orient=tk.HORIZONTAL, 
            length=350, 
            mode='determinate'
        )
        self.progress.pack(pady=10)
        self.progress.pack_forget()
        
        self.status_label = tk.Label(
            main_frame, 
            text="Sube tu imagen, elige un modo…", 
            font=("Segoe UI", 11), 
            fg="#7f8c8d",
            bg="#f5f5f5",
            wraplength=500
        )
        self.status_label.pack(pady=10)
        
        self.result_frame = tk.Frame(main_frame, bg="#f5f5f5")
        self.result_frame.pack(pady=10)
        
        self.btn_preview = Button(
            self.result_frame,
            text="Vista Previa",
            command=self.show_preview,
            state=tk.DISABLED,
            style="TButton"
        )
        self.btn_preview.pack(side=tk.LEFT, padx=10)
        
        self.btn_save = Button(
            self.result_frame,
            text="Guardar Imagen",
            command=self.save_result,
            state=tk.DISABLED,
            style="TButton"
        )
        self.btn_save.pack(side=tk.LEFT, padx=10)
        
        footer_frame = tk.Frame(main_frame, bg="#f5f5f5")
        footer_frame.pack(side=tk.BOTTOM, pady=(20, 0))
        
        author_label = tk.Label(
            footer_frame, 
            text="By Jesús Pineda", 
            font=("Segoe UI", 10),
            fg="#535353",
            bg="#f5f5f5"
        )
        author_label.pack(side=tk.LEFT, padx=5)
        
        donate_btn = Button(
            footer_frame, 
            text="Acerca de", 
            command=self._about_window,
            style="Toolbutton"
        )
        donate_btn.pack(side=tk.LEFT, padx=5)
        
        donate_btn = Button(
            footer_frame, 
            text="Donar", 
            command=self.donate,
            style="Toolbutton"
        )
        donate_btn.pack(side=tk.LEFT, padx=5)
        
        
        style = Style()
        style.configure('TButton', font=('Segoe UI', 10))
        style.configure('Accent.TButton', font=('Segoe UI', 11, 'bold'), 
                        foreground='white', background='#3498db')
        style.map('Accent.TButton', background=[('active', '#2980b9')])
    
    def _show_mensaje_alert(self):
        messagebox.showinfo("Personas", "Función en desarrollo. ¡Próximamente!")
        
    # --------------- About window ----------------------------
    def _about_window(self):
        win = tk.Toplevel()
        win.title("Acerca de la aplicación")
        win.geometry("750x550")
        win.resizable(False, False)
        win.configure(bg="#f5f5f5")
        
        try:
            win.iconbitmap(resource_path("resources/efi-icon.ico"))
        except:
            pass

        content = tk.Frame(win, bg="#f5f5f5")
        content.pack(fill="both", expand=True, padx=16, pady=16)

        title_label = tk.Label(
            content,
            text="Acerca de la aplicación",
            font=("Segoe UI", 18, "bold"),
            fg="#2c3e50",
            bg="#f5f5f5"
        )
        title_label.pack(pady=(8, 4))

        desc_label = tk.Label(
            content,
            text=(
                "EFI es una aplicación diseñada para ofrecer una experiencia sencilla y eficiente,\n"
                "solo selecciona una imagen y el sistema se encarga de procesarla automáticamente,\n"
                "removiendo el fondo de manera precisa. El programa funciona sin conexión a internet\n"
                "una vez que el modelo ha sido descargado por primera vez, lo que permite usarlo en\n"
                "cualquier entorno sin depender de servicios externos."
                "\n"
                "Actualmente incluye un modo optimizado para objetos, mientras que la opción de\n"
                "detección de personas está en desarrollo. El sistema utiliza el motor de segmentación\n"
                "`rembg`, gracias al trabajo de Daniel Gatis, a quien extendemos un especial\n"
                "agradecimiento por su aporte a la comunidad.\n"
                "\n"
                "El objetivo principal de esta aplicación es servir como demostración tecnológica,\n"
                "con distintos recursos de hardware. En caso de que tu computadora no cuente con\n"
                "aceleración gráfica, el sistema se ajustará automáticamente para ejecutarse en CPU.\n"
                "\n"
                "Para consultas, colaboraciones, contratos o reportar problemas, puedes escribir\n"
                "al correo oficial. Estaré encantado de recibir tus comentarios y mejorar la aplicación."
            ),
            justify="left",
            font=("Segoe UI", 12),
            fg="#2c3e50",
            bg="#f5f5f5"
        )
        desc_label.pack(pady=(0, 12), padx=10)

        links_frame = tk.Frame(content, bg="#f5f5f5")
        links_frame.pack(side="bottom", pady=(20, 6))

        def link(txt, url):
            return ttk.Button(links_frame, text=txt, style='Toolbutton',
                            command=lambda: webbrowser.open(url))
        link("Documentacion", (Path(resource_path('resources/documentacion_efi.html')).as_uri())).pack(side="left", padx=6)
        ttk.Button(links_frame, text="Instrucciones", style="Toolbutton",
           command=self._instructions_window).pack(side="left", padx=6)
        link("GitHub",   "https://github.com/jesuspinedaof").pack(side="left", padx=6)
        link("WhatsApp","https://wa.me/584160601607").pack(side="left", padx=6)
        link("Email","mailto:tornioficial@gmail.com").pack(side="left", padx=6)
        link("Linktree","https://linktr.ee/jesuspinedaof").pack(side="left", padx=6)

        version_label = tk.Label(
            content,
            text="v1.0\n"
                "By Jesús Pineda",
            font=("Segoe UI", 10),
            fg="gray40",
            bg="#f5f5f5"
        )
        version_label.pack(side="bottom", pady=(10, 0))
        
    def _instructions_window(self):
        win = tk.Toplevel()
        win.title("Instrucciones de la aplicación")
        win.geometry("750x650")
        win.resizable(False, False)
        win.configure(bg="#f5f5f5")
        
        try:
            win.iconbitmap(resource_path("resources/efi-icon.ico"))
        except:
            pass

        content = tk.Frame(win, bg="#f5f5f5")
        content.pack(fill="both", expand=True, padx=16, pady=16)

        title_label = tk.Label(
            content,
            text="Instrucciones",
            font=("Segoe UI", 18, "bold"),
            fg="#2c3e50",
            bg="#f5f5f5"
        )
        title_label.pack(pady=(8, 4))

        desc_label = tk.Label(
            content,
            text=(
                "Requisitos del sistema:\n"
                "\n"
                "• Sistema operativo: Windows 7/8/10/11 (64 bits recomendado).\n"
                "• Memoria RAM: 1 GB (Puede correr perfectamente).\n"
                "• No se requiere instalación de Python ni librerías externas.\n"
                "• Conexión a internet solo la primera vez (para descargar el modelo U²-Net)."
                "\n"
                "\n"
                "Pasos de uso:\n"
                "\n"
                "1. Selecciona el modo de procesamiento (actualmente disponible: Objetos).\n"
                "2. Haz clic en '📷 Seleccionar Imagen' y elige una imagen desde tu computadora.\n"
                "3. El sistema procesará la imagen y removerá el fondo automáticamente.\n"
                "4. Visualiza el resultado con la opción **Vista Previa**.\n"
                "5. Guarda tu imagen en formato **PNG transparente** o **JPG con fondo blanco**.\n"
                "\n"
                "Consejos:\n"
                "\n"
                "Si es tu primera vez, la aplicación descargará el modelo de IA (esto puede tardar unos minutos).\n"
                "Imágenes mayores a 10 MB pueden tardar en procesarse, pero el programa te avisará.\n"
                "Usa la vista previa antes de guardar para asegurarte de que el resultado cumple tus expectativas."
            ),
            justify="left",
            font=("Segoe UI", 12),
            fg="#2c3e50",
            bg="#f5f5f5"
        )
        desc_label.pack(pady=(0, 12), padx=10)

        links_frame = tk.Frame(content, bg="#f5f5f5")
        links_frame.pack(side="bottom", pady=(20, 6))

        def link(txt, url):
            return ttk.Button(links_frame, text=txt, style='Toolbutton',
                            command=lambda: webbrowser.open(url))
        link("Documentacion", f"file://{os.path.abspath('resources/documentacion_efi.html')}").pack(side="left", padx=6)
        link("GitHub",   "https://github.com/jesuspinedaof").pack(side="left", padx=6)
        link("Linktree","https://linktr.ee/jesuspinedaof").pack(side="left", padx=6)

        version_label = tk.Label(
            content,
            text="v1.0\n"
                "By Jesús Pineda",
            font=("Segoe UI", 10),
            fg="gray40",
            bg="#f5f5f5"
        )
        version_label.pack(side="bottom", pady=(10, 0))
    
    def update_mode(self):
        self.mode = self.mode_var.get()
        self.status_label.config(text=f"Modo seleccionado: {'Personas' if self.mode == 'personas' else 'Objetos'}")
        
    def select_image(self):
        if self.processing:
            messagebox.showwarning("Advertencia", "Ya hay un proceso en ejecución")
            return
            
        filetypes = [
            ("Imágenes", "*.png;*.jpg;*.jpeg;*.bmp")
        ]
        
        input_path = filedialog.askopenfilename(filetypes=filetypes)
        if input_path:
            img_size = os.path.getsize(input_path) / (1024 * 1024)  # MB
            if img_size > 10:
                if not messagebox.askyesno(
                    "Advertencia", 
                    f"La imagen es grande ({img_size:.1f}MB) y puede tardar. ¿Continuar?"
                ):
                    return
            
            self.processing = True
            self.btn_select.config(state=tk.DISABLED)
            self.status_label.config(text="Descargando modelo de IA...")
            self.root.update_idletasks()
            
            threading.Thread(
                target=self.process_image,
                args=(input_path,),
                daemon=True
            ).start()
    
    def process_image(self, input_path):
        try:
            model_filename = "u2net_human_seg.onnx" if self.mode == "personas" else "u2net.onnx"
            model_path = os.path.join(CACHE_DIR, model_filename)
            
            # MOSTRAR la barra de progreso ANTES de verificar/descargar el modelo
            self.progress.pack()
            self.progress['value'] = 0
            self.root.update_idletasks()
            
            if not os.path.exists(model_path):
                self.download_model(model_path)  # Esta función ya actualiza la barra
            
            self.status_label.config(text="Procesando imagen (esto puede tardar)...")
            self.progress['value'] = 50  # Progreso intermedio
            self.root.update_idletasks()
            
            start_time = time.time()
            with open(input_path, 'rb') as f:
                input_image = f.read()
            
            session = new_session("u2net_human_seg" if self.mode == "personas" else "u2net")
            output_image = remove(
                input_image, 
                session=session,
                alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=10,
                alpha_matting_erode_size=10
            )
            
            processing_time = time.time() - start_time
            self.progress['value'] = 100
            self.root.update_idletasks()
            
            self.current_image = Image.open(BytesIO(output_image))
            base_name = os.path.splitext(input_path)[0]
            self.output_path = f"{base_name}_sin_fondo.png"
            self.status_label.config(
                text=f"¡Procesado en {processing_time:.1f}s!\nModo: {'Personas' if self.mode == 'personas' else 'Objetos'}\n"
            )
            
            notification.notify(
                title='Fondo Removido',
                message=f"¡La imagen ha sido procesada!",
                timeout=10,
                app_name="EFI",
                app_icon=resource_path("resources/efi-icon.ico")
            )
            
            self.btn_preview.config(state=tk.NORMAL)
            self.btn_save.config(state=tk.NORMAL)
            
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}")
            messagebox.showerror("Error", f"Ocurrió un error: {str(e)}")
        finally:
            self.processing = False
            self.progress.pack_forget()  # OCULTAR la barra al final
            self.btn_select.config(state=tk.NORMAL)
            self.root.update_idletasks()
    
    def download_model(self, model_path):
        try:
            key = "personas" if model_path.endswith("u2net_human_seg.onnx") else "objetos"
            model_url = MODEL_URLS[key]

            response = requests.get(model_url, stream=True, timeout=60, verify=certifi.where())
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(model_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            progress = int((downloaded / total_size) * 100)
                            self.progress['value'] = progress
                            self.root.update_idletasks()

            if os.path.getsize(model_path) < 50_000_000:
                raise ValueError("El modelo descargado está incompleto")

        except Exception as e:
            raise ValueError(f"Error al descargar el modelo: {e}")
    
    def show_preview(self):
        if not self.current_image:
            return
        
        preview_window = tk.Toplevel(self.root)
        preview_window.title("Vista Previa - Fondo Eliminado")
        
        try:
            preview_window.iconbitmap(resource_path("resources/jp.ico"))
        except:
            pass
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        img_width, img_height = self.current_image.size
        max_width = int(screen_width * 0.8)
        max_height = int(screen_height * 0.8)
        
        ratio = min(max_width/img_width, max_height/img_height)
        new_size = (int(img_width * ratio), int(img_height * ratio))
        
        preview_image = self.current_image.resize(new_size, Image.LANCZOS)
        
        checker = self.create_checkerboard()
        bg = self.tile_pattern(preview_image.size, checker)
        bg.paste(preview_image, (0, 0), preview_image if preview_image.mode == 'RGBA' else None)
        
        preview_photo = ImageTk.PhotoImage(bg)
        preview_label = tk.Label(preview_window, image=preview_photo)
        preview_label.image = preview_photo
        preview_label.pack(padx=10, pady=10)
        
        btn_frame = tk.Frame(preview_window)
        btn_frame.pack(pady=(0, 10))
        
        Button(
            btn_frame, 
            text="Guardar Como", 
            command=self.save_image_as
        ).pack(side=tk.LEFT, padx=5)
    
    def create_checkerboard(self, size=20):
        tile = Image.new('RGB', (size*2, size*2), (255, 255, 255))
        draw = ImageDraw.Draw(tile)
        draw.rectangle([0, 0, size, size], fill=(220, 220, 220))
        draw.rectangle([size, size, size*2, size*2], fill=(220, 220, 220))
        return tile
    
    def tile_pattern(self, image_size, pattern):
        width, height = image_size
        pattern_width, pattern_height = pattern.size
        tiles_x = (width // pattern_width) + 2
        tiles_y = (height // pattern_height) + 2
        
        bg = Image.new('RGB', 
                      (pattern_width * tiles_x, pattern_height * tiles_y))
        for y in range(tiles_y):
            for x in range(tiles_x):
                bg.paste(pattern, (x * pattern_width, y * pattern_height))
        
        return bg.crop((0, 0, width, height))
    
    def save_result(self):
        if self.current_image and self.output_path:
            try:
                self.current_image.save(self.output_path)
                messagebox.showinfo("Éxito", f"Imagen guardada en:\n{self.output_path}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar: {e}")
    
    def save_image_as(self):
        if not self.current_image:
            return
            
        save_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG transparente", "*.png"),
                ("JPEG con fondo blanco", "*.jpg"),
                ("Todos los archivos", "*.*")
            ]
        )
        
        if save_path:
            try:
                if save_path.lower().endswith(('.jpg', '.jpeg')):
                    background = Image.new('RGB', self.current_image.size, (255, 255, 255))
                    background.paste(self.current_image, (0, 0), self.current_image)
                    background.save(save_path, quality=95)
                else:
                    self.current_image.save(save_path)
                
                messagebox.showinfo("Éxito", f"Imagen guardada en:\n{save_path}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar: {e}")
    
    def donate(self):
        webbrowser.open("https://www.paypal.com/paypalme/tuamigoprogramador")
        
if __name__ == "__main__":
    root = tk.Tk()
    app = BackgroundRemoverApp(root)
    root.mainloop()
    print("EFI App iniciada")
    print("Todos los derechos reservados - 2025")