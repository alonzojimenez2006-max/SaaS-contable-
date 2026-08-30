import uuid
import hashlib
import tkinter as tk

def obtener_huella_universal():
    try:
        # Obtiene la dirección física de la tarjeta de red (única)
        mac = str(uuid.getnode())
        
        # Generamos el hash corto de 16 caracteres
        huella = hashlib.sha256(mac.encode()).hexdigest()[:16].upper()
        return huella
    except Exception:
        return "ERROR_DE_LECTURA"

# ==========================================
# INTERFAZ GRÁFICA (GUI)
# ==========================================
root = tk.Tk()
root.title("Lector HWID - ContaPy")
root.geometry("380x160")
root.eval('tk::PlaceWindow . center')
root.resizable(False, False) # Evita que cambien el tamaño de la ventana

tk.Label(root, text="Huella Única del Equipo:", font=("Arial", 12, "bold")).pack(pady=(20, 10))

# Campo de texto donde se mostrará la huella
entry_huella = tk.Entry(root, font=("Consolas", 16, "bold"), width=22, justify="center")
entry_huella.insert(0, obtener_huella_universal())
entry_huella.pack()
entry_huella.config(state="readonly") # Permite copiar (Ctrl+C) pero no editar

tk.Label(root, text="Copia este código para generar la licencia en tu sistema.", font=("Arial", 9), fg="#555555").pack(pady=(10, 0))

root.mainloop()