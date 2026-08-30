import tkinter as tk
from tkinter import messagebox, filedialog
import hashlib
import os

# Tu clave secreta (NO LA CAMBIES)
CLAVE_SECRETA = "ContaPyPro_Acceso_Seguro_2026_XyZ"

def crear_licencia():
    hwid = entry_hwid.get().strip().upper()
    if not hwid:
        return messagebox.showerror("Error", "Debes ingresar una huella.")
    
    # Encriptamos la huella
    licencia_final = hashlib.sha256((hwid + CLAVE_SECRETA).encode()).hexdigest()
    
    # Abrimos una ventana visual para que elijas dónde guardar el archivo
    ruta_guardado = filedialog.asksaveasfilename(
        defaultextension=".lic",
        initialfile="licencia.lic",
        title="¿Dónde quieres guardar la licencia?",
        filetypes=[("Archivo de Licencia", "*.lic"), ("Todos los archivos", "*.*")]
    )
    
    # Si elegiste una carpeta y no cancelaste la ventana
    if ruta_guardado:
        with open(ruta_guardado, "w") as f:
            f.write(licencia_final)
            
        messagebox.showinfo("Éxito", f"Licencia guardada correctamente en:\n\n{ruta_guardado}")
        entry_hwid.delete(0, 'end')

# ==========================================
# INTERFAZ GRÁFICA (GUI)
# ==========================================
root = tk.Tk()
root.title("Generador Master de Licencias")
root.geometry("400x200")
root.eval('tk::PlaceWindow . center')
root.resizable(False, False)

tk.Label(root, text="Pega el HWID del cliente aquí:", font=("Arial", 12, "bold")).pack(pady=15)

entry_hwid = tk.Entry(root, font=("Consolas", 14), width=25, justify="center")
entry_hwid.pack(pady=5)

tk.Button(root, text="Guardar Archivo .LIC", font=("Arial", 12, "bold"), bg="#00FF41", command=crear_licencia).pack(pady=20)

root.mainloop()