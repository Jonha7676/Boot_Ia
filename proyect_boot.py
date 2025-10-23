# proyect_boot_estilo.py
import os
import threading
import queue
import textwrap
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image, ImageTk
import tkinter as tk
import tkinter.messagebox as msgbox
import customtkinter as ctk

# ------------------ CARGAR CONFIG ------------------
load_dotenv()
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise RuntimeError("No se encontró API_KEY en .env — crea .env con API_KEY=tu_api_key")

import google.generativeai as genai
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(model_name="models/gemini-2.5-pro")

# ------------------ VENTANA / ESTILO ------------------
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.geometry("1200x800")
app.title("🧠 IA de JONY - Resolución Inteligente")
app.configure(bg="#ffffff")  # fondo blanco

# Cola para comunicación segura entre hilos (thread -> UI)
ui_queue = queue.Queue()

# ------------------ UTILIDADES ------------------
def generar_prompt_resolucion(problema: str) -> str:
    return f"""
Resuelve el siguiente problema siguiendo estos 8 pasos de análisis lógico:

1. Identifique y clarifique el problema.
2. Analice el problema recopilando hechos e información.
3. Desarrolle soluciones alternativas.
4. Seleccione la mejor solución.
5. Diseñe un plan de acción.
6. Implemente la solución.
7. Describa brevemente cómo se evaluará la solución.
8. Evalúe la solución elegida mostrando una tabla visual y colorida con puntuaciones del 1 al 10 en los siguientes criterios:
   - ⚡ Eficiencia
   - 🚀 Rapidez
   - 🎯 Calidad

La tabla debe ser muy visual, usando emojis, bloques gráficos, barras de progreso o cualquier elemento que la haga clara, atractiva y fácil de entender.

Problema: {problema}
"""

def safe_wrap_lines(text, width=95):
    wrapped = []
    for paragraph in text.split("\n"):
        if paragraph.strip() == "":
            wrapped.append("")
        else:
            wrapped += textwrap.wrap(paragraph, width=width)
    return "\n".join(wrapped)

# ------------------ FUNCIONES DE UI ------------------
def escribir_en_output(texto: str, tag: str = None):
    output.configure(state="normal")
    if tag:
        output.insert("end", texto + "\n", tag)
    else:
        output.insert("end", texto + "\n")
    output.see("end")
    output.configure(state="disabled")

def mostrar_info_ia():
    msgbox.showinfo(
        title="Sobre IA de JONY",
        message="🧠 IA de JONY - Resolución Inteligente\nVersión 1.0\n\nTu asistente para resolver problemas paso a paso con estilo, claridad y motivación."
    )

# ------------------ LOGO SIEMPRE VISIBLE ------------------
def crear_logo():
    global logo_label
    logo_frame = tk.Frame(app, bg="#ffffff")  # Frame blanco, transparente visualmente
    logo_frame.place(relx=1.0, rely=0.0, anchor="ne")
    try:
        ubuntu_img = Image.open("ubuntu_logo.png").resize((30,30))
        ubuntu_photo = ImageTk.PhotoImage(ubuntu_img)
        logo_label = tk.Label(logo_frame, image=ubuntu_photo, bg="#ffffff")
        logo_label.image = ubuntu_photo
        logo_label.pack()
        logo_label.bind("<Button-1>", lambda e: mostrar_info_ia())
        logo_frame.tkraise()  # Siempre encima
    except Exception as e:
        print(f"No se pudo cargar el logo: {e}")

crear_logo()


# ------------------ PANEL DE CHAT ------------------
def mostrar_chat():
    welcome_label.pack_forget()

    chat_frame = tk.Frame(app, bg="#ffffff")
    chat_frame.pack(fill="both", expand=True, padx=20, pady=20)

    global output
    output = tk.Text(chat_frame, height=20, wrap="word", bg="#ffffff", fg="#000000", font=("Arial", 14))
    output.configure(state="disabled", padx=8, pady=8, relief="solid", borderwidth=1)
    output.pack(side="top", fill="both", expand=True, pady=(0,5))

    scrollbar = tk.Scrollbar(chat_frame, command=output.yview)
    scrollbar.pack(side="right", fill="y", pady=(0,5))
    output.configure(yscrollcommand=scrollbar.set)

    bottom_frame = tk.Frame(chat_frame, bg="#ffffff")
    bottom_frame.pack(side="bottom", fill="x", pady=5)

    entry = tk.Entry(bottom_frame, font=("Arial", 16), width=40)
    entry.pack(side="left", fill="x", expand=True, padx=(0,5), pady=5)

    btn_frame = tk.Frame(bottom_frame, bg="#ffffff")
    btn_frame.pack(side="right", padx=(5,0))

    btn_options = [
        ("📨 Enviar", enviar, 16),
        ("🆕 Nuevo Chat", limpiar_output, 16),
        ("📄 Guardar PDF", guardar_pdf, 16),
        ("💾 Guardar", guardar_conversacion, 16)
    ]

    for i, (text, func, font_size) in enumerate(btn_options):
        b = tk.Button(btn_frame, text=text, command=lambda f=func, e=entry: f(e) if f==enviar else f(),
                      bg="#63b1e5", fg="#ffffff", font=("Arial", font_size, "bold"), padx=20, pady=5)
        b.grid(row=0, column=i, padx=3)

    poll_queue()

# ------------------ FUNCIONES ------------------
def limpiar_output():
    output.configure(state="normal")
    output.delete("1.0", "end")
    output.configure(state="disabled")

def hilo_obtener_respuesta(problema: str):
    try:
        prompt = generar_prompt_resolucion(problema)
        respuesta = model.generate_content(prompt)
        texto = getattr(respuesta, "text", str(respuesta))
        texto = safe_wrap_lines(texto, width=90)
        ui_queue.put(("response", texto))
        ui_queue.put(("mascota", problema))
    except Exception as e:
        ui_queue.put(("error", f"❌ Error al obtener respuesta de la IA: {e}"))

def enviar(entry_widget):
    problema = entry_widget.get().strip()
    if not problema:
        msgbox.showwarning("Aviso", "Escribe primero el problema.")
        return
    entry_widget.delete(0, "end")
    ui_queue.put(("user", problema))
    t = threading.Thread(target=hilo_obtener_respuesta, args=(problema,), daemon=True)
    t.start()

def poll_queue():
    try:
        while True:
            item = ui_queue.get_nowait()
            tipo, contenido = item
            if tipo == "user":
                escribir_en_output(f"👤 Tú: {contenido}")
            elif tipo == "response":
                escribir_en_output("🤖 IA de JONY:\n")
                escribir_en_output(contenido)
            elif tipo == "error":
                escribir_en_output(contenido)
            elif tipo == "mascota":
                mostrar_mascota(contenido)
    except queue.Empty:
        pass
    app.after(150, poll_queue)

def guardar_pdf():
    contenido = output.get("1.0", "end").strip()
    if not contenido:
        msgbox.showinfo("Info", "No hay contenido para guardar.")
        return
    try:
        filename = "analisis_jony.pdf"
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter
        margin = 50
        y = height - margin
        c.setFont("Helvetica", 11)
        lines = safe_wrap_lines(contenido, width=95).split("\n")
        for line in lines:
            if y < margin:
                c.showPage()
                y = height - margin
                c.setFont("Helvetica", 11)
            c.drawString(margin, y, line)
            y -= 14
        c.save()
        escribir_en_output(f"📄 PDF guardado como '{filename}'")
    except Exception as e:
        escribir_en_output(f"❌ Error al guardar PDF: {e}")

def guardar_conversacion():
    contenido = output.get("1.0", "end").strip()
    if not contenido:
        msgbox.showinfo("Info", "No hay contenido para guardar.")
        return
    try:
        filename = "conversacion_jony.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(contenido)
        escribir_en_output(f"💾 Conversación guardada en '{filename}'")
    except Exception as e:
        escribir_en_output(f"❌ Error al guardar conversación: {e}")

# ------------------ PANTALLA DE BIENVENIDA ------------------
welcome_label = tk.Label(app, text="🧠 Bienvenido a tu inteligencia artificial", font=("Arial Bold", 30),
                         bg="#ffffff", fg="#000000")
welcome_label.pack(pady=250)

app.after(2000, mostrar_chat)
app.mainloop()
