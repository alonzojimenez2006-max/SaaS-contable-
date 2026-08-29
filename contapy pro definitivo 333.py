import os
import platform
import sqlite3
import customtkinter as ctk
from tkinter import messagebox, ttk
import tkinter as tk
from tkcalendar import DateEntry
from datetime import datetime

# --- LIBRERÍAS DE SEGURIDAD ---
import subprocess
import hashlib
import sys

import barcode                     
from barcode.writer import ImageWriter

# ==========================================
# --- PANTALLA DE CARGA (SPLASH SCREEN) ---
# ==========================================
ctk.set_appearance_mode("light")
splash = ctk.CTk()
splash.overrideredirect(True) # Oculta la barra de cerrar/minimizar
ancho, alto = 450, 260
x = (splash.winfo_screenwidth() // 2) - (ancho // 2)
y = (splash.winfo_screenheight() // 2) - (alto // 2)
splash.geometry(f"{ancho}x{alto}+{x}+{y}")
splash.configure(fg_color="#FFFFFF") # Fondo Blanco Limpio

# Ruta segura temporal para leer el logo antes de inicializar la Base de Datos
if getattr(sys, 'frozen', False):
    splash_base_dir = os.path.dirname(sys.executable)
else:
    splash_base_dir = os.path.dirname(os.path.abspath(__file__))

# Importamos PIL momentáneamente para renderizar el logo en el Splash
from PIL import Image

try:
    ruta_logo_splash = os.path.join(splash_base_dir, "logocontapy.png")
    img_logo_splash = Image.open(ruta_logo_splash)
    logo_splash_ctk = ctk.CTkImage(light_image=img_logo_splash, dark_image=img_logo_splash, size=(220, 90))
    lbl_logo_splash = ctk.CTkLabel(splash, text="", image=logo_splash_ctk)
    lbl_logo_splash.pack(pady=(35, 10))
except Exception as e:
    # Respaldo de texto si por alguna razón el archivo PNG no está en la carpeta
    ctk.CTkLabel(splash, text="CONTAPY PRO", font=("Arial", 36, "bold"), text_color="#008060").pack(pady=(35, 10))

ctk.CTkLabel(splash, text="Iniciando sistema y cargando módulos...", font=("Arial", 12, "bold"), text_color="#666666").pack(pady=5)

# --- NUEVO: Barra de progreso animada ---
progress_bar = ctk.CTkProgressBar(splash, width=320, height=14, progress_color="#008060")
progress_bar.pack(pady=15)
progress_bar.set(0) # Inicia vacía

splash.update() # Fuerza a que la pantalla aparezca ANTES de cargar lo demás

# Simulamos un pequeño progreso visual mientras cargan las librerías pesadas
import time
for i in range(1, 101):
    progress_bar.set(i / 100)
    splash.update()
    time.sleep(0.01) # Velocidad de carga fluida

# --- LIBRERÍAS PESADAS (Se cargan mientras el usuario ve el Splash) ---
import pandas as pd
from PIL import Image
from fpdf import FPDF
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg



class Database:
    def __init__(self):
        # --- RUTA COMPARTIDA FIJA PARA GERENCIA Y CAJA ---
        self.SHARED_DIR = r"C:\ContaPy_Datos"
        os.makedirs(self.SHARED_DIR, exist_ok=True)
        
        self.db_path = os.path.join(self.SHARED_DIR, "contapy.db")
        
        self.assets_dir = os.path.join(self.SHARED_DIR, "assets")
        self.barcodes_dir = os.path.join(self.assets_dir, "barcodes")
        self.tickets_dir = os.path.join(self.assets_dir, "tickets")
        
        os.makedirs(self.barcodes_dir, exist_ok=True)
        os.makedirs(self.tickets_dir, exist_ok=True)
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.crear_tablas()

    def crear_tablas(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS configuracion (clave TEXT PRIMARY KEY, valor TEXT)")
        self.cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('tasa_dolar', '1.0')")
        
        # --- Textos configurables del ticket en la Base de Datos ---
        self.cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('empresa_nombre', 'COCINAS Y MUEBLES CARRARO, C.A.')")
        self.cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('empresa_rif', 'RIF: J297863559')")
        self.cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('empresa_direccion', 'Av. Miranda con Calle Boyaca, Edif. Costantino\nPiso PB, Local 4 y 5, Sector Centro\nMaturin, Monagas')")
        
        # --- NUEVO: Parámetros del Hardware de Impresión (Etiquetas) ---
        self.cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('etiqueta_ancho', '40')")
        self.cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('etiqueta_alto', '20')")
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                nombre TEXT UNIQUE NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS transacciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                tipo TEXT NOT NULL,
                categoria TEXT NOT NULL,
                monto REAL NOT NULL,
                forma_pago TEXT NOT NULL,
                descripcion TEXT,
                producto_id INTEGER,
                cantidad_producto INTEGER,
                FOREIGN KEY (producto_id) REFERENCES productos(id)
            )
        """)
        
        self.cursor.execute("CREATE TABLE IF NOT EXISTS empleados (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, cargo TEXT NOT NULL, sueldo_base REAL NOT NULL)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS metas (id INTEGER PRIMARY KEY AUTOINCREMENT, categoria TEXT NOT NULL, tipo TEXT NOT NULL, monto_meta REAL NOT NULL)")
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rif TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                direccion TEXT,
                telefono TEXT,
                eliminado INTEGER DEFAULT 0
            )
        """)
        
        self.cursor.execute("PRAGMA table_info(transacciones)")
        columnas_trans = [col[1] for col in self.cursor.fetchall()]
        if "cliente_id" not in columnas_trans:
            try: self.cursor.execute("ALTER TABLE transacciones ADD COLUMN cliente_id INTEGER")
            except: pass

        self.conn.commit()

        tablas = ["productos", "transacciones", "empleados", "metas"]
        for tabla in tablas:
            self.cursor.execute(f"PRAGMA table_info({tabla})")
            columnas = [col[1] for col in self.cursor.fetchall()]
            if "eliminado" not in columnas:
                try: self.cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN eliminado INTEGER DEFAULT 0")
                except: pass

        self.cursor.execute("PRAGMA table_info(transacciones)")
        columnas_trans = [col[1] for col in self.cursor.fetchall()]
        for col in ["producto_id", "cantidad_producto"]:
            if col not in columnas_trans:
                try: self.cursor.execute(f"ALTER TABLE transacciones ADD COLUMN {col} INTEGER")
                except: pass
                
        for col, col_type, default in [("factura", "TEXT", "NULL"), ("hora", "TEXT", "NULL"), ("caja", "TEXT", "'Caja Principal'"), ("detalle_factura", "TEXT", "''"), ("estado", "TEXT", "'Pagado / Completado'")]:
            if col not in columnas_trans:
                try: self.cursor.execute(f"ALTER TABLE transacciones ADD COLUMN {col} {col_type} DEFAULT {default}")
                except: pass

        self.cursor.execute("PRAGMA table_info(productos)")
        columnas_prod = [col[1] for col in self.cursor.fetchall()]
        if "precio_adquisicion" not in columnas_prod:
            try: self.cursor.execute("ALTER TABLE productos ADD COLUMN precio_adquisicion REAL DEFAULT 0.0")
            except: pass

        if "precio_venta" not in columnas_prod:
            try: self.cursor.execute("ALTER TABLE productos ADD COLUMN precio_venta REAL DEFAULT 0.0")
            except: pass

        # --- NUEVAS COLUMNAS (CÉDULA, CORREO Y DEUDA DE PRÉSTAMOS) ---
        self.cursor.execute("PRAGMA table_info(empleados)")
        columnas_emp = [col[1] for col in self.cursor.fetchall()]
        if "cedula" not in columnas_emp:
            try: self.cursor.execute("ALTER TABLE empleados ADD COLUMN cedula TEXT DEFAULT 'N/A'")
            except: pass
        if "deuda" not in columnas_emp:
            try: self.cursor.execute("ALTER TABLE empleados ADD COLUMN deuda REAL DEFAULT 0.0")
            except: pass

        self.cursor.execute("PRAGMA table_info(clientes)")
        columnas_cli = [col[1] for col in self.cursor.fetchall()]
        if "correo" not in columnas_cli:
            try: self.cursor.execute("ALTER TABLE clientes ADD COLUMN correo TEXT DEFAULT 'N/A'")
            except: pass

        # --- NUEVO: Tabla de Historial de Tasas y Columna Congelada ---
        self.cursor.execute("CREATE TABLE IF NOT EXISTS historial_tasas (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, hora TEXT, tasa REAL)")
        
        self.cursor.execute("PRAGMA table_info(transacciones)")
        columnas_trans = [col[1] for col in self.cursor.fetchall()]
        if "tasa_aplicada" not in columnas_trans:
            try: self.cursor.execute("ALTER TABLE transacciones ADD COLUMN tasa_aplicada REAL DEFAULT NULL")
            except: pass

        # Gatillo Automático: Cada vez que haces una transacción, "congela" la tasa de ese segundo
        self.cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_transacciones_tasa
            AFTER INSERT ON transacciones
            FOR EACH ROW
            WHEN NEW.tasa_aplicada IS NULL
            BEGIN
                UPDATE transacciones
                SET tasa_aplicada = (SELECT CAST(valor AS REAL) FROM configuracion WHERE clave = 'tasa_dolar')
                WHERE id = NEW.id;
            END;
        """)

        self.conn.commit()

    def obtener_tasa(self):
        self.cursor.execute("SELECT valor FROM configuracion WHERE clave = 'tasa_dolar'")
        resultado = self.cursor.fetchone()
        return float(resultado[0]) if resultado else 1.0

    def actualizar_tasa(self, nueva_tasa):
        self.cursor.execute("UPDATE configuracion SET valor = ? WHERE clave = 'tasa_dolar'", (str(nueva_tasa),))
        
        # --- NUEVO: Guarda en el historial de tasas con hora exacta ---
        fecha = datetime.now().strftime("%Y-%m-%d")
        hora = datetime.now().strftime("%H:%M:%S")
        self.cursor.execute("INSERT INTO historial_tasas (fecha, hora, tasa) VALUES (?, ?, ?)", (fecha, hora, float(nueva_tasa)))
        
        self.conn.commit()

    # --- NUEVO: Funciones secretas de la base de datos ---
    def obtener_datos_empresa(self):
        n = self.cursor.execute("SELECT valor FROM configuracion WHERE clave='empresa_nombre'").fetchone()[0]
        r = self.cursor.execute("SELECT valor FROM configuracion WHERE clave='empresa_rif'").fetchone()[0]
        d = self.cursor.execute("SELECT valor FROM configuracion WHERE clave='empresa_direccion'").fetchone()[0]
        return n, r, d

    def actualizar_datos_empresa(self, n, r, d):
        self.cursor.execute("UPDATE configuracion SET valor=? WHERE clave='empresa_nombre'", (n,))
        self.cursor.execute("UPDATE configuracion SET valor=? WHERE clave='empresa_rif'", (r,))
        self.cursor.execute("UPDATE configuracion SET valor=? WHERE clave='empresa_direccion'", (d,))
        self.conn.commit()

    # --- NUEVO: Método para leer el historial de tasas ---
    def obtener_historial_tasas(self):
        return pd.read_sql_query("SELECT * FROM historial_tasas ORDER BY id DESC", self.conn)

    def obtener_todas_transacciones(self):
        return pd.read_sql_query("SELECT * FROM transacciones WHERE eliminado = 0 ORDER BY fecha DESC, id DESC", self.conn)

    def obtener_transacciones_eliminadas(self):
        return pd.read_sql_query("SELECT * FROM transacciones WHERE eliminado = 1 ORDER BY fecha DESC", self.conn)

    def obtener_productos(self):
        return pd.read_sql_query("SELECT * FROM productos WHERE eliminado = 0 ORDER BY nombre ASC", self.conn)

    def obtener_productos_eliminados(self):
        return pd.read_sql_query("SELECT id, codigo, nombre FROM productos WHERE eliminado = 1", self.conn)

    def buscar_productos(self, texto):
        texto = f"%{texto}%"
        return pd.read_sql_query("SELECT * FROM productos WHERE eliminado = 0 AND (nombre LIKE ? OR codigo LIKE ?) ORDER BY nombre ASC", self.conn, params=(texto, texto))

    # --- NUEVO: Funciones para la calibración del Hardware Térmico ---
    def obtener_medidas_etiqueta(self):
        ancho = self.cursor.execute("SELECT valor FROM configuracion WHERE clave='etiqueta_ancho'").fetchone()
        alto = self.cursor.execute("SELECT valor FROM configuracion WHERE clave='etiqueta_alto'").fetchone()
        return float(ancho[0]) if ancho else 40.0, float(alto[0]) if alto else 20.0

    def actualizar_medidas_etiqueta(self, ancho, alto):
        self.cursor.execute("UPDATE configuracion SET valor=? WHERE clave='etiqueta_ancho'", (str(ancho),))
        self.cursor.execute("UPDATE configuracion SET valor=? WHERE clave='etiqueta_alto'", (str(alto),))
        self.conn.commit()

    # --- ACTUALIZADO: Renderizado vectorizado en HD ---
    def generar_imagen_barcode(self, codigo_producto):
        try:
            EAN = barcode.get_barcode_class('code128')
            ean = EAN(str(codigo_producto), writer=ImageWriter())
            os.makedirs(self.barcodes_dir, exist_ok=True)
            ruta_guardado = os.path.join(self.barcodes_dir, str(codigo_producto))
            
            # Ajustes matemáticos puros para que el láser lea rápido y el texto se vea bien
            opciones_termicas = {
                "module_width": 0.3,   # Grosor limpio para el láser
                "module_height": 10.0, # Altura equilibrada
                "quiet_zone": 3.0,     # Zonas blancas laterales (necesarias para el láser)
                "font_size": 10,       # Tamaño de letra visible
                "text_distance": 4.0,  # Separa los números de las barras para que no se pisen
                "dpi": 300             # 300 DPI elimina el "texturizado" o pixelado
            }
            
            ean.save(ruta_guardado, options=opciones_termicas)
        except Exception:
            pass

    def generar_ticket_pdf(self, transaccion_id):
        try:
            from fpdf import FPDF
            
            self.cursor.execute("SELECT factura, fecha, hora, monto, forma_pago, detalle_factura, caja, tasa_aplicada FROM transacciones WHERE id = ?", (transaccion_id,))
            r = self.cursor.fetchone()
            if not r: return None
            
            factura, fecha, hora, monto, pago, detalle, caja, tasa_aplicada = r
            factura = factura if factura else f"TICKET-{transaccion_id}"
            detalle = detalle if detalle else "Venta Simple"
            
            tasa = tasa_aplicada if tasa_aplicada else self.obtener_tasa()
            monto_bs = monto * tasa
            
            emp_nombre, emp_rif, emp_dir = self.obtener_datos_empresa()
            
            # --- CORRECCIÓN: Cálculo de Altura Dinámica y Márgenes ---
            # 1. Calculamos cuántas líneas tiene el ticket para no desperdiciar papel
            lineas_productos = len(detalle.split('\n'))
            # 65mm de base (encabezados y totales) + 4mm por cada renglón de producto
            alto_ticket = 65 + (lineas_productos * 4.0)
            
            pdf = FPDF(format=(80, alto_ticket)) 
            
            # --- CORRECCIÓN MÁRGENES: 2mm a cada lado para un centrado real ---
            pdf.set_margins(left=2, top=2, right=2)
            pdf.set_auto_page_break(auto=False)
            pdf.add_page()
            
            # Al tener 80mm de ancho con 2mm de margen por lado, nos quedan 76mm útiles
            w_celda = 76
            
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(w_celda, 6, emp_nombre, ln=True, align='C')
            pdf.set_font("Arial", 'B', 8)
            pdf.cell(w_celda, 4, emp_rif, ln=True, align='C')
            pdf.set_font("Arial", '', 7)
            pdf.multi_cell(w_celda, 3, emp_dir, align='C') 
            
            pdf.set_font("Arial", 'B', 8)
            pdf.cell(w_celda, 4, f"Fecha: {fecha}  Hora: {hora}", ln=True, align='C')
            pdf.cell(w_celda, 4, f"Caja: {caja} | Fac: {factura}", ln=True, align='C')
            pdf.cell(w_celda, 4, "-"*50, ln=True, align='C')
            
            pdf.set_font("Arial", 'B', 7)
            for linea in detalle.split('\n'):
                pdf.multi_cell(w_celda, 4, linea, align='L')
                
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(w_celda, 4, "-"*50, ln=True, align='C')
            
            pdf.set_font("Arial", 'B', 8)
            pdf.multi_cell(w_celda, 4, f"METODO DE PAGO: {pago.upper()}", align='C')
            
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(w_celda, 6, f"TOTAL: Bs. {monto_bs:,.2f}", ln=True, align='C')
            
            pdf.cell(w_celda, 6, "GRACIAS POR SU COMPRA", ln=True, align='C')
            
            ruta_pdf = os.path.join(self.tickets_dir, f"{factura}.pdf")
            pdf.output(ruta_pdf)
            return ruta_pdf
        
        except Exception as e:
            print(f"Error PDF: {e}")
            return None

    def crear_producto(self, nombre, stock_inicial, codigo=None, precio_adq=0.0, precio_venta=0.0):
        if not codigo or codigo.strip() == "":
            self.cursor.execute("SELECT MAX(id) FROM productos")
            resultado = self.cursor.fetchone()[0]
            codigo = f"PROD-{(resultado + 1) if resultado is not None else 1:04d}"
        
        self.cursor.execute("INSERT INTO productos (codigo, nombre, stock, precio_adquisicion, precio_venta, eliminado) VALUES (?, ?, ?, ?, ?, 0)", (codigo, nombre, stock_inicial, precio_adq, precio_venta))
        self.conn.commit()
        
        self.generar_imagen_barcode(codigo)
        return codigo

    def actualizar_stock(self, producto_id, cantidad):
        self.cursor.execute("UPDATE productos SET stock = stock + ? WHERE id = ? AND eliminado = 0", (cantidad, producto_id))
        self.conn.commit()
        
    def actualizar_stock_y_precios(self, producto_id, cantidad, precio_adq, precio_venta):
        self.cursor.execute("UPDATE productos SET stock = stock + ?, precio_adquisicion = ?, precio_venta = ? WHERE id = ? AND eliminado = 0", (cantidad, precio_adq, precio_venta, producto_id))
        self.conn.commit()

    def crear_empleado(self, cedula, nombre, cargo, sueldo_base):
        self.cursor.execute("INSERT INTO empleados (cedula, nombre, cargo, sueldo_base, eliminado) VALUES (?, ?, ?, ?, 0)", (cedula, nombre, cargo, sueldo_base))
        self.conn.commit()

    def obtener_empleados(self):
        return pd.read_sql_query("SELECT * FROM empleados WHERE eliminado = 0 ORDER BY nombre ASC", self.conn)
    
    def eliminar_empleado(self, emp_id):
        self.cursor.execute("UPDATE empleados SET eliminado = 1 WHERE id = ?", (emp_id,))
        self.conn.commit()

    def crear_meta(self, categoria, tipo, monto_meta):
        self.cursor.execute("UPDATE metas SET eliminado = 1 WHERE categoria = ?", (categoria,))
        self.cursor.execute("INSERT INTO metas (categoria, tipo, monto_meta, eliminado) VALUES (?, ?, ?, 0)", (categoria, tipo, monto_meta))
        self.conn.commit()

    def obtener_metas(self):
        return pd.read_sql_query("SELECT * FROM metas WHERE eliminado = 0", self.conn)
    
    def eliminar_meta(self, meta_id):
        self.cursor.execute("UPDATE metas SET eliminado = 1 WHERE id = ?", (meta_id,))
        self.conn.commit()

    def soft_delete(self, tabla, item_id):
        self.cursor.execute(f"UPDATE {tabla} SET eliminado = 1 WHERE id = ?", (item_id,))
        self.conn.commit()

    def restaurar_registro(self, tabla, item_id):
        self.cursor.execute(f"UPDATE {tabla} SET eliminado = 0 WHERE id = ?", (item_id,))
        self.conn.commit()

    def eliminar_permanente(self, tabla, item_id):
        self.cursor.execute(f"DELETE FROM {tabla} WHERE id = ?", (item_id,))
        self.conn.commit()

    def crear_cliente(self, rif, nombre, direccion, telefono, correo):
        self.cursor.execute("INSERT INTO clientes (rif, nombre, direccion, telefono, correo, eliminado) VALUES (?, ?, ?, ?, ?, 0)", (rif, nombre, direccion, telefono, correo))
        self.conn.commit()

    def obtener_clientes(self):
        return pd.read_sql_query("SELECT * FROM clientes WHERE eliminado = 0 ORDER BY nombre ASC", self.conn)

    def obtener_clientes_eliminados(self):
        return pd.read_sql_query("SELECT id, rif, nombre FROM clientes WHERE eliminado = 1", self.conn)

    def generar_factura_b2b_pdf(self, factura_codigo, cliente_info, carrito, totales, fecha, hora):
        # ==========================================
        try:
            # 1. Filtro de seguridad: Limpia acentos y símbolos (ñ, tildes, emojis) que rompen FPDF
            def limpiar(texto):
                return str(texto).encode('latin-1', 'replace').decode('latin-1')

            # --- NUEVO: Extraemos dinámicamente los datos configurados en el panel secreto ---
            emp_nombre, emp_rif, emp_dir = self.obtener_datos_empresa()

            pdf = FPDF(format='A4')
            pdf.add_page()
            
            # --- ENCABEZADO DE EMPRESA DINÁMICO ---
            pdf.set_font("Arial", 'B', 18)
            pdf.set_text_color(0, 128, 96) # Verde oscuro
            pdf.cell(0, 8, limpiar(emp_nombre), ln=True, align='L')
            
            pdf.set_font("Arial", 'B', 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 5, limpiar(emp_rif), ln=True, align='L')
            pdf.set_font("Arial", '', 9)
            # Reemplazamos los saltos de línea para que se organicen bien en una sola línea horizontal o párrafo corto
            dir_limpia = emp_dir.replace('\n', ', ')
            pdf.cell(0, 5, limpiar(f"Dir: {dir_limpia}"), ln=True, align='L')
            
            # --- DATOS DE LA FACTURA ---
            pdf.set_y(10)
            pdf.set_font("Arial", 'B', 14)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 10, limpiar(f"FACTURA NRO: {factura_codigo}"), ln=True, align='R')
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 5, limpiar(f"Fecha: {fecha}"), ln=True, align='R')
            pdf.cell(0, 5, limpiar(f"Hora: {hora}"), ln=True, align='R')
            pdf.ln(10)

            # --- CAJA DEL CLIENTE ---
            pdf.set_fill_color(240, 244, 249)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, limpiar(" DATOS DEL CLIENTE"), border=1, ln=True, fill=True)
            pdf.set_font("Arial", '', 10)
            
            # 2. Extracción segura con get() para evitar errores si falta un dato
            c_nom = limpiar(cliente_info.get('nombre', ''))
            c_rif = limpiar(cliente_info.get('rif', ''))
            c_dir = limpiar(cliente_info.get('direccion', ''))
            c_tel = limpiar(cliente_info.get('telefono', ''))
            c_correo = limpiar(cliente_info.get('correo', 'No especificado'))
            
            pdf.multi_cell(0, 6, f" Razon Social: {c_nom}\n RIF/CI: {c_rif}\n Direccion: {c_dir}\n Telefono: {c_tel}\n Correo: {c_correo}", border=1)
            pdf.ln(10)

            # --- TABLA DE PRODUCTOS ---
            pdf.set_font("Arial", 'B', 10)
            pdf.set_fill_color(0, 128, 96)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(30, 8, limpiar("Codigo"), border=1, fill=True, align='C')
            pdf.cell(80, 8, limpiar("Descripcion del Producto"), border=1, fill=True, align='C')
            pdf.cell(20, 8, limpiar("Cant."), border=1, fill=True, align='C')
            pdf.cell(30, 8, limpiar("Precio Unit."), border=1, fill=True, align='C')
            pdf.cell(30, 8, limpiar("Total"), border=1, fill=True, align='C', ln=True)

            pdf.set_font("Arial", '', 10)
            pdf.set_text_color(0, 0, 0)
            for item in carrito:
                pdf.cell(30, 8, limpiar(str(item.get('codigo', ''))), border=1, align='C')
                
                n_orig = item.get('nombre', '')
                n_corto = n_orig[:35] + '...' if len(n_orig) > 35 else n_orig
                pdf.cell(80, 8, f" {limpiar(n_corto)}", border=1, align='L')
                
                pdf.cell(20, 8, limpiar(str(item.get('cant', 0))), border=1, align='C')
                pdf.cell(30, 8, f"${item.get('p_unit', 0):,.2f}", border=1, align='R')
                pdf.cell(30, 8, f"${item.get('subtotal', 0):,.2f}", border=1, align='R', ln=True)

            # --- TOTALES ---
            # 3. Compatible tanto con el subtotal viejo como el subtotal_bruto nuevo
            sub_bruto = totales.get('subtotal_bruto', totales.get('subtotal', 0.0))
            monto_desc = totales.get('monto_descuento', 0.0)
            desc_porc = totales.get('desc_porc', 0.0)
            iva = totales.get('iva', 0.0)
            t_usd = totales.get('total_usd', 0.0)
            t_bs = totales.get('total_bs', 0.0)
            tasa = totales.get('tasa', 0.0)

            pdf.ln(5)
            pdf.set_x(130)
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(30, 8, limpiar("Subtotal:"), border=1)
            pdf.set_font("Arial", '', 10)
            pdf.cell(30, 8, f"${sub_bruto:,.2f}", border=1, align='R', ln=True)
            
            if monto_desc > 0:
                pdf.set_x(130)
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(30, 8, limpiar(f"Desc. ({desc_porc}%):"), border=1)
                pdf.set_font("Arial", '', 10)
                pdf.cell(30, 8, f"-${monto_desc:,.2f}", border=1, align='R', ln=True)
            
            pdf.set_x(130)
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(30, 8, limpiar("IVA (16%):"), border=1)
            pdf.set_font("Arial", '', 10)
            pdf.cell(30, 8, f"${iva:,.2f}", border=1, align='R', ln=True)

            pdf.set_x(130)
            pdf.set_font("Arial", 'B', 12)
            pdf.set_fill_color(240, 244, 249)
            pdf.cell(30, 10, limpiar("TOTAL USD:"), border=1, fill=True)
            pdf.set_text_color(0, 128, 96)
            pdf.cell(30, 10, f"${t_usd:,.2f}", border=1, fill=True, align='R', ln=True)

            pdf.set_x(130)
            pdf.set_font("Arial", 'I', 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(60, 8, limpiar(f"Tasa BCV: {tasa} | Bs. {t_bs:,.2f}"), align='R', ln=True)

            # 1. Dibujar el Método de Pago
            metodo_pago = totales.get('metodo', 'No especificado')
            pdf.ln(5)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 8, limpiar(f"METODO DE PAGO: {metodo_pago}"), ln=True, align='L')
            
            # 2. Espaciado vertical para las firmas
            pdf.ln(25) 
            y_firmas = pdf.get_y()
            
            # Línea Izquierda (Vendedor)
            pdf.line(20, y_firmas, 80, y_firmas)
            pdf.set_xy(20, y_firmas + 2)
            pdf.set_font("Arial", '', 10)
            pdf.cell(60, 5, "Firma Vendedor (Emisor)", align='C')
            
            # Línea Derecha (Comprador)
            pdf.line(130, y_firmas, 190, y_firmas)
            pdf.set_xy(130, y_firmas + 2)
            pdf.cell(60, 5, "Firma Comprador (Cliente)", align='C')
            pdf.ln(10)

            # --- GUARDAR PDF ---
            ruta_pdf = os.path.join(self.tickets_dir, f"{factura_codigo}_B2B.pdf")
            pdf.output(ruta_pdf)
            return ruta_pdf
            
        except Exception as e:
            # 4. Si el PDF vuelve a fallar, te mostrará una ventana con el ERROR REAL.
            from tkinter import messagebox
            messagebox.showerror("Error Interno PDF", f"Falló la creación del PDF por este motivo:\n\n{str(e)}")
            return None
        
class ContaPyApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ContaPy Pro - Gestión Integral")
        self.geometry("1200x850")
        self.db = Database()
        self.tasa_actual = self.db.obtener_tasa()

        # Paleta de colores ajustada a TEMA CLARO
        self.color_bg = "#F4F6F9"
        self.color_card = "#FFFFFF"
        self.verde_neon = "#008060"    # Color de ingreso
        self.rojo_neon = "#FF0000"     # Color de egreso
        self.color_acento = "#007BFF"  
        self.configure(fg_color=self.color_bg)

        # --- LÍNEAS RESTAURADAS CORRECTAMENTE ---
        self.cats_ingreso = ["Ventas de Mercancía", "Cuentas por Cobrar", "Servicios", "Inversiones", "Otros Ingresos"]
        self.cats_egreso = ["Gastos Operativos", "Nómina", "Impuestos", "Cuentas por Pagar", "Compra de Mercancía", "Otros Egresos"]
        self.metodos_pago = ["Efectivo Dólares", "Efectivo Bolívares", "Punto de Venta", "Pago Móvil", "Transferencia", "Biopago", "Binance", "Zelle", "PayPal"]
        self.estados_transaccion = ["Pagado / Completado", "Cuentas por Pagar", "Cuentas por Cobrar", "Ingreso Operacional"]

        self.var_iva_pos = ctk.BooleanVar(value=True)
        self.var_iva_b2b = ctk.BooleanVar(value=True)

        # Estilo Global de Treeview para Tema Claro (TODO EN NEGRITA)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=self.color_card, foreground="black", fieldbackground=self.color_card, borderwidth=0, rowheight=30, font=("Arial", 10, "bold"))
        style.map("Treeview", background=[("selected", "#E4E6EB")], foreground=[("selected", "black")])
        style.configure("Treeview.Heading", background="#E4E6EB", foreground="black", font=("Arial", 10, "bold"))

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # NUEVO: Se cambia a CTkScrollableFrame para activar la barra de desplazamiento en el menú
        self.sidebar = ctk.CTkScrollableFrame(self, width=240, corner_radius=0, fg_color="#FFFFFF")
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # REEMPLAZO POR EL LOGO SOLICITADO
        # --- CARGA DE LOGO (CORREGIDA) ---
        try:
            # 1. Calculamos la ruta base de forma segura (funciona en .py y en .exe)
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                
            # 2. Unimos la ruta base con el nombre de tu imagen
            ruta_logo = os.path.join(base_dir, "logocontapy.png")
            
            # 3. Cargamos y mostramos la imagen
            img_logo = Image.open(ruta_logo)
            self.logo_sidebar = ctk.CTkImage(light_image=img_logo, dark_image=img_logo, size=(190, 80))
            lbl_logo = ctk.CTkLabel(self.sidebar, text="", image=self.logo_sidebar)
            lbl_logo.pack(pady=(40, 10))
            
        except Exception as e:
            # Este respaldo ahora SOLO se mostrará si el archivo "logocontapy.png" realmente no está en la carpeta
            lbl_logo = ctk.CTkLabel(self.sidebar, text="CONTAPY POS", font=("Arial", 24, "bold"), text_color=self.verde_neon)
            lbl_logo.pack(pady=(40, 10))
        
        frame_tasa = ctk.CTkFrame(self.sidebar, fg_color="#F4F6F9", corner_radius=10)
        frame_tasa.pack(pady=15, padx=15, fill="x")
        
        # --- NUEVO: Aislamos el texto en una variable y le asignamos el gatillo fantasma ---
        self.lbl_tasa_texto = ctk.CTkLabel(frame_tasa, text="Tasa Actual", font=("Arial", 11, "bold"), text_color="#666666")
        self.lbl_tasa_texto.pack(pady=(10,0))
        self.lbl_tasa_texto.bind("<Double-Button-1>", self.abrir_config_secreta) # El Easter Egg
        
        self.lbl_tasa_display = ctk.CTkLabel(frame_tasa, text=f"Bs. {self.tasa_actual:,.2f}", font=("Arial", 18, "bold"), text_color="black")
        self.lbl_tasa_display.pack(pady=5)
        
        box_act_tasa = ctk.CTkFrame(frame_tasa, fg_color="transparent")
        box_act_tasa.pack(pady=(0,10))
        self.entry_nueva_tasa = ctk.CTkEntry(box_act_tasa, width=80, height=28, placeholder_text="0.00", font=("Arial", 12, "bold"))
        self.entry_nueva_tasa.grid(row=0, column=0, padx=5)
        ctk.CTkButton(box_act_tasa, text="✓", width=30, height=28, fg_color=self.verde_neon, text_color="white", font=("Arial", 12, "bold"), command=self.actualizar_tasa_bcv).grid(row=0, column=1)

        # --- NUEVO: Botón del historial de tasas ---
        btn_hist = ctk.CTkButton(frame_tasa, text="📅 Ver Historial", fg_color="transparent", text_color=self.color_acento, font=("Arial", 11, "bold", "underline"), command=self.abrir_historial_tasas)
        btn_hist.pack(pady=(0, 5))

        # --- NUEVO: Botón de la Calculadora Flotante ---
        btn_calc = ctk.CTkButton(frame_tasa, text="🧮 Calculadora Divisas", fg_color=self.color_acento, text_color="white", font=("Arial", 12, "bold"), command=self.abrir_calculadora_divisas)
        btn_calc.pack(pady=(5, 10), padx=15, fill="x")

        self.crear_boton_menu("🖥️ Dashboard", lambda: self.mostrar_frame("dash"))
        self.crear_boton_menu("➕ Transacción Simple", lambda: self.mostrar_frame("reg"))
        self.crear_boton_menu("🏢 Ventas al Mayor (B2B)", lambda: self.mostrar_frame("mayor"))
        self.crear_boton_menu("👥 Clientes B2B", lambda: self.mostrar_frame("clientes")) # <-- NUEVO BOTÓN
        
        btn_pos = ctk.CTkButton(self.sidebar, text="🛒 Punto de Venta (POS)", fg_color=self.color_acento, text_color="white", font=("Arial", 14, "bold"), anchor="center", hover_color="#0056b3", command=self.abrir_pos)
        btn_pos.pack(pady=15, padx=20, fill="x")

        self.crear_boton_menu("📝 Movimientos", lambda: self.mostrar_frame("movimientos"))
        self.crear_boton_menu("📅 Resumen Financiero", lambda: self.mostrar_frame("mensual"))
        self.crear_boton_menu("🧾 Historial de Ventas", lambda: self.mostrar_frame("ventas"))
        self.crear_boton_menu("📚 Historial B2B", lambda: self.mostrar_frame("historial_b2b"))
        self.crear_boton_menu("📦 Inventario y codigos", lambda: self.mostrar_frame("inventario"))
        self.crear_boton_menu("🛍️ Ingreso Mercancía", lambda: self.mostrar_frame("ing_merc"))
        self.crear_boton_menu("👥 Nómina", lambda: self.mostrar_frame("nomina"))
        self.crear_boton_menu("🌡️ Termómetro", lambda: self.mostrar_frame("termometro"))
        self.crear_boton_menu("📊 Análisis Velas", lambda: self.mostrar_frame("velas"))
        self.crear_boton_menu("📈 Rendimiento", lambda: self.mostrar_frame("rendimiento"))
        self.crear_boton_menu("🗑️ Papelera", lambda: self.mostrar_frame("papelera"))

        self.container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1, minsize=800) 

        self.frames = {}
        # TODAS LAS PANTALLAS CREADAS E INICIALIZADAS
        self.setup_dash()
        self.setup_registro()
        self.setup_movimientos()
        self.setup_ventas()
        self.setup_inventario()
        self.setup_ingreso_mercancia()
        self.setup_nomina()
        self.setup_termometro()
        self.setup_velas()
        self.setup_rendimiento()
        self.setup_papelera()
        self.setup_resumen_mensual()
        self.setup_clientes()
        self.setup_ventas_mayor()
        self.setup_historial_b2b()
        
        self.mostrar_frame("dash")
        self.protocol("WM_DELETE_WINDOW", self.cerrar_app)

    def cerrar_app(self):
        try: self.db.conn.close()
        except: pass
        self.destroy()

    def crear_boton_menu(self, texto, comando):
        btn = ctk.CTkButton(self.sidebar, text=texto, font=("Arial", 12, "bold"), text_color="black", fg_color="transparent", anchor="w", hover_color="#F0F2F5", command=comando)
        btn.pack(pady=5, padx=20, fill="x")

    def actualizar_tasa_bcv(self):
        try:
            nueva = float(self.entry_nueva_tasa.get().replace(',', '.'))
            if nueva > 0:
                self.db.actualizar_tasa(nueva)
                self.tasa_actual = nueva
                self.lbl_tasa_display.configure(text=f"Bs. {self.tasa_actual:,.2f}")
                self.entry_nueva_tasa.delete(0, 'end')
                messagebox.showinfo("Tasa Actualizada", f"Nueva tasa fijada: Bs. {nueva:,.2f}")
                if hasattr(self, 'pos_window') and self.pos_window.winfo_exists():
                    self.actualizar_ui_carrito()
                self.mostrar_frame("movimientos") 
        except ValueError:
            messagebox.showerror("Error", "Ingrese una tasa válida (solo números).")

    # ==========================================
    # PUNTO DE VENTA (POS)
    # ==========================================
    def abrir_pos(self):
        if hasattr(self, 'pos_window') and self.pos_window.winfo_exists():
            self.pos_window.focus()
            return

        self.pos_window = ctk.CTkToplevel(self)
        self.pos_window.title("Punto de Venta - Facturación (POS)")
        self.pos_window.geometry("1100x750")
        # Eliminamos el grab_set() para que la ventana sea libre y puedas usar la calculadora

        self.carrito_pos = []

        top_f = ctk.CTkFrame(self.pos_window, fg_color=self.color_card, corner_radius=15)
        top_f.pack(fill="x", padx=20, pady=20, ipady=15)
        
        self.lbl_pos_total_usd = ctk.CTkLabel(top_f, text="TOTAL: $0.00", font=("Arial", 45, "bold"), text_color=self.verde_neon)
        self.lbl_pos_total_usd.pack(pady=(10,0))
        self.lbl_pos_total_bs = ctk.CTkLabel(top_f, text="Bs. 0.00", font=("Arial", 20, "bold"), text_color="#666666")
        self.lbl_pos_total_bs.pack()

        mid_f = ctk.CTkFrame(self.pos_window, fg_color="transparent")
        mid_f.pack(fill="both", expand=True, padx=20)
        mid_f.grid_columnconfigure(1, weight=1)

        left_panel = ctk.CTkFrame(mid_f, fg_color=self.color_card, width=350, corner_radius=10)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_panel.grid_propagate(False)

        ctk.CTkLabel(left_panel, text="AGREGAR PRODUCTO", font=("Arial", 16, "bold"), text_color="black").pack(pady=15)
        
        self.pos_scan = ctk.CTkEntry(left_panel, placeholder_text="📟 Lector Código de Barras", font=("Arial", 12, "bold"), height=40)
        self.pos_scan.pack(fill="x", padx=20, pady=10)
        self.pos_scan.bind("<Return>", self.on_pos_barcode)

        # Buscador
        buscador_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        buscador_frame.pack(fill="x", padx=20, pady=(10, 5))
        
        ctk.CTkLabel(buscador_frame, text="🔍 Buscar:", font=("Arial", 12, "bold"), text_color="black").pack(side="left", padx=(0, 5))
        
        self.entry_buscador = ctk.CTkEntry(buscador_frame, placeholder_text="Nombre o código...", font=("Arial", 12, "bold"))
        self.entry_buscador.pack(side="left", fill="x", expand=True)
        self.entry_buscador.bind("<KeyRelease>", self.filtrar_productos_buscador)
        
        self.lista_resultados = tk.Listbox(left_panel, height=5, font=("Arial", 12, "bold"), bg="white", fg="black", selectbackground=self.verde_neon, selectforeground="white", relief="flat", highlightthickness=1, highlightcolor="#D1D5DB")
        self.lista_resultados.bind("<Double-Button-1>", self.seleccionar_producto_lista)
        self.lista_resultados.bind("<Return>", self.seleccionar_producto_lista)
        
        self.pos_cant = ctk.CTkEntry(left_panel, placeholder_text="Cantidad", font=("Arial", 12, "bold"), height=40)
        self.pos_cant.pack(fill="x", padx=20, pady=10)
        self.pos_cant.insert(0, "1")

        self.switch_iva_pos = ctk.CTkSwitch(left_panel, text="Aplicar IVA (16%)", font=("Arial", 12, "bold"), command=self.actualizar_ui_carrito)
        self.switch_iva_pos.select() 
        self.switch_iva_pos.pack(pady=5)

        ctk.CTkButton(left_panel, text="➕ Agregar al Carrito", height=45, fg_color=self.color_acento, text_color="white", font=("Arial", 14, "bold"), command=self.pos_agregar_carrito).pack(fill="x", padx=20, pady=20)

        right_panel = ctk.CTkFrame(mid_f, fg_color="transparent")
        right_panel.grid(row=0, column=1, sticky="nsew")

        col_c = ("ID", "Código", "Nombre", "Cant", "P.Unit ($)", "Subtotal ($)")
        self.tabla_pos = ttk.Treeview(right_panel, columns=col_c, show="headings")
        anchos_c = {"ID": 0, "Código": 100, "Nombre": 200, "Cant": 60, "P.Unit ($)": 90, "Subtotal ($)": 100}
        for c in col_c: 
            self.tabla_pos.heading(c, text=c)
            self.tabla_pos.column(c, width=anchos_c[c], stretch=True if c == "Nombre" else False, anchor="center")
        self.tabla_pos.column("ID", width=0, stretch=False)
        self.tabla_pos.pack(fill="both", expand=True)

        ctk.CTkButton(right_panel, text="🗑️ Quitar Seleccionado", font=("Arial", 12, "bold"), fg_color=self.rojo_neon, text_color="white", hover_color="#CC0000", command=self.pos_quitar_carrito).pack(anchor="e", pady=10)

        bot_f = ctk.CTkFrame(self.pos_window, fg_color=self.color_card, corner_radius=10)
        bot_f.pack(fill="x", padx=20, pady=20)
        
        box_ajustes = ctk.CTkFrame(bot_f, fg_color="transparent")
        box_ajustes.pack(side="left", padx=20, pady=15)
        
        ctk.CTkLabel(box_ajustes, text="Descuento (%):", font=("Arial", 12, "bold"), text_color="black").grid(row=0, column=0, padx=5)
        self.pos_desc = ctk.CTkEntry(box_ajustes, width=80, font=("Arial", 12, "bold"))
        self.pos_desc.grid(row=0, column=1, padx=5)
        self.pos_desc.insert(0, "0")
        self.pos_desc.bind("<KeyRelease>", lambda e: self.actualizar_ui_carrito())

        ctk.CTkLabel(box_ajustes, text="Recargo ($):", font=("Arial", 12, "bold"), text_color="black").grid(row=0, column=2, padx=(20,5))
        self.pos_recargo = ctk.CTkEntry(box_ajustes, width=80, font=("Arial", 12, "bold"))
        self.pos_recargo.grid(row=0, column=3, padx=5)
        self.pos_recargo.insert(0, "0")
        self.pos_recargo.bind("<KeyRelease>", lambda e: self.actualizar_ui_carrito())

        self.lbl_pos_iva = ctk.CTkLabel(box_ajustes, text="IVA (16%): $0.00", font=("Arial", 12, "bold"), text_color="#666666")
        self.lbl_pos_iva.grid(row=1, column=0, columnspan=4, sticky="w", padx=5, pady=5)

        # --- NUEVO: Selección de dos métodos de pago en POS ---
        # --- MÉTODOS DE PAGO MIXTOS ---
        box_pago = ctk.CTkFrame(bot_f, fg_color="transparent")
        box_pago.pack(side="right", padx=10, pady=10)

        self.pos_metodo = ctk.CTkComboBox(box_pago, values=self.metodos_pago, width=130, font=("Arial", 11, "bold"))
        self.pos_metodo.grid(row=0, column=0, padx=5, pady=2)
        self.pos_metodo.set("Efectivo Dólares") # <-- Cambiado para que coincida con la lista

        # Monto Método 1
        self.pos_monto1 = ctk.CTkEntry(box_pago, placeholder_text="Monto 1 ($)", width=100, font=("Arial", 11, "bold"))
        self.pos_monto1.grid(row=0, column=1, padx=5, pady=2)
        self.pos_monto1.bind("<KeyRelease>", self.autocompletar_pago_pos) # <-- NUEVO: Activa el cálculo automático

        # Método 2
        self.pos_metodo2 = ctk.CTkComboBox(box_pago, values=["Ninguno"] + self.metodos_pago, width=130, font=("Arial", 11, "bold"))
        self.pos_metodo2.grid(row=1, column=0, padx=5, pady=2)
        self.pos_metodo2.set("Ninguno")

        # Monto Método 2
        self.pos_monto2 = ctk.CTkEntry(box_pago, placeholder_text="Monto 2 ($)", width=100, font=("Arial", 11, "bold"))
        self.pos_monto2.grid(row=1, column=1, padx=5, pady=2)

        ctk.CTkButton(box_pago, text="💳 PROCESAR VENTA", height=45, fg_color=self.verde_neon, text_color="white", font=("Arial", 13, "bold"), command=self.procesar_venta_pos).grid(row=0, column=2, rowspan=2, padx=10)

    def filtrar_productos_buscador(self, event=None):
        texto_busqueda = self.entry_buscador.get().lower()
        
        if not texto_busqueda:
            self.lista_resultados.place_forget()
            return
            
        df_prod = self.db.obtener_productos()
        if df_prod.empty: return
        
        self.lista_resultados.delete(0, 'end') 
        coincidencias = 0
        
        for _, r in df_prod.iterrows():
            nombre_prod = str(r.get("nombre", "")).lower()
            codigo_prod = str(r.get("codigo", "")).lower() 
            
            if texto_busqueda in nombre_prod or texto_busqueda in codigo_prod:
                p_id = r.get("id", "0")
                p_nom = r.get("nombre", "Desconocido")
                p_stock = r.get("stock", 0)
                p_precio = float(r.get("precio_venta", 0.0)) 
                
                formato_lista = f"{p_id} - {p_nom} (Stock: {p_stock}) - ${p_precio:,.2f}"
                self.lista_resultados.insert('end', formato_lista)
                coincidencias += 1
                
        if coincidencias > 0:
            self.lista_resultados.place(in_=self.entry_buscador, x=0, rely=1, relwidth=1.0)
            self.lista_resultados.lift()
            self.lista_resultados.config(height=min(coincidencias, 6))
        else:
            self.lista_resultados.place_forget()

    def seleccionar_producto_lista(self, event=None):
        seleccion = self.lista_resultados.curselection()
        if not seleccion: return
        
        producto_seleccionado = self.lista_resultados.get(seleccion[0])
        self.entry_buscador.delete(0, 'end')
        self.entry_buscador.insert(0, producto_seleccionado)
        self.lista_resultados.place_forget()

    def on_pos_barcode(self, event=None):
        codigo = self.pos_scan.get().strip()
        if not codigo: return
        df = self.db.obtener_productos()
        fila = df[df["codigo"] == codigo]
        if not fila.empty:
            r = fila.iloc[0]
            # --- CORRECCIÓN: Autocompletar en el buscador del POS y añadir al carrito ---
            self.entry_buscador.delete(0, 'end')
            self.entry_buscador.insert(0, f"{r['id']} - {r['nombre']} (Stock: {r['stock']}) - ${r['precio_venta']:,.2f}")
            
            # Forzamos la cantidad a 1
            self.pos_cant.delete(0, "end")
            self.pos_cant.insert(0, "1")
            
            # Añadimos al carrito automáticamente
            self.pos_agregar_carrito()
            
            # Limpiamos el lector para escanear el siguiente artículo rápídamente
            self.pos_scan.delete(0, "end")
            self.pos_scan.focus()
        else: messagebox.showerror("Error", f"No se encontró código: {codigo}")

    def pos_agregar_carrito(self):
        texto = self.entry_buscador.get().strip()
        if not texto: return
        
        try:
            producto_id_str = texto.split(" - ")[0].strip()
            producto_id = int(producto_id_str)
        except ValueError:
            return messagebox.showerror("Error", "Seleccione un producto válido de la lista.")
        
        df = self.db.obtener_productos()
        fila = df[df["id"] == producto_id]
        if fila.empty: return
        p = fila.iloc[0]
        
        try: 
            cant_solicitada = int(self.pos_cant.get())
        except ValueError: 
            return messagebox.showerror("Error", "Cantidad inválida. Ingrese un número entero.")
            
        if cant_solicitada <= 0: 
            return messagebox.showerror("Error", "La cantidad a agregar debe ser mayor a 0.")
        
        stock_disponible = int(p['stock'])
        cant_en_carrito = sum([int(item['cant']) for item in self.carrito_pos if item['id'] == producto_id])
        
        if (cant_en_carrito + cant_solicitada) > stock_disponible:
            faltan = (cant_en_carrito + cant_solicitada) - stock_disponible
            messagebox.showerror("❌ Stock Insuficiente", f"Stock Total Disponible: {stock_disponible}\nEn carrito: {cant_en_carrito}\nFaltan {faltan} unidades.")
            return

        agregado = False
        for item in self.carrito_pos:
            if item['id'] == producto_id:
                item['cant'] += cant_solicitada
                item['subtotal'] = item['cant'] * item['p_unit']
                agregado = True
                break
        
        if not agregado:
            self.carrito_pos.append({
                "id": producto_id, 
                "codigo": str(p['codigo']), 
                "nombre": str(p['nombre']),
                "cant": cant_solicitada, 
                "p_unit": float(p['precio_venta']), 
                "subtotal": float(cant_solicitada * p['precio_venta'])
            })
            
        self.pos_cant.delete(0, "end")
        self.pos_cant.insert(0, "1")
        self.entry_buscador.delete(0, "end")
        self.actualizar_ui_carrito()

    def pos_quitar_carrito(self):
        seleccion = self.tabla_pos.selection()
        if not seleccion: return
        item_tree = self.tabla_pos.item(seleccion[0])
        p_id = int(item_tree["values"][0])
        self.carrito_pos = [item for item in self.carrito_pos if item['id'] != p_id]
        self.actualizar_ui_carrito()

    # --- NUEVO: Calcula el monto restante en POS ---
    def autocompletar_pago_pos(self, event=None):
        if self.pos_metodo2.get() != "Ninguno":
            try:
                texto_total = self.lbl_pos_total_usd.cget("text")
                total = float(texto_total.replace("TOTAL: $", "").replace(",", ""))
                m1 = float(self.pos_monto1.get())
                if m1 <= total:
                    self.pos_monto2.delete(0, "end")
                    self.pos_monto2.insert(0, f"{(total - m1):.2f}")
            except ValueError:
                pass

    def actualizar_ui_carrito(self):
        for item in self.tabla_pos.get_children(): self.tabla_pos.delete(item)

        subtotal_bruto = 0.0
        for item in self.carrito_pos:
            self.tabla_pos.insert("", "end", values=(
                item["id"], item["codigo"], item["nombre"], item["cant"], 
                f"${item['p_unit']:,.2f}", f"${item['subtotal']:,.2f}"
            ))
            subtotal_bruto += item["subtotal"]

        try: desc_porc = float(self.pos_desc.get() or 0)
        except: desc_porc = 0.0
        try: recargo_usd = float(self.pos_recargo.get() or 0)
        except: recargo_usd = 0.0

        descuento_usd = subtotal_bruto * (desc_porc / 100)
        subtotal_neto = subtotal_bruto - descuento_usd + recargo_usd

        aplicar_iva = self.switch_iva_pos.get() == 1 if hasattr(self, 'switch_iva_pos') else True
        iva_usd = (subtotal_neto * 0.16) if aplicar_iva else 0.0
        total_final_usd = subtotal_neto + iva_usd

        if hasattr(self, 'lbl_pos_iva'):
            self.lbl_pos_iva.configure(text=f"IVA (16%): ${iva_usd:,.2f}")

        self.lbl_pos_total_usd.configure(text=f"TOTAL: ${total_final_usd:,.2f}")
        self.lbl_pos_total_bs.configure(text=f"Bs. {(total_final_usd * self.tasa_actual):,.2f}")
        
        return total_final_usd, subtotal_bruto, descuento_usd, recargo_usd, desc_porc, iva_usd

    def procesar_venta_pos(self):
        if not self.carrito_pos:
            return messagebox.showerror("Carrito Vacío", "No hay productos para facturar.")
        
        total_neto, sub_b, desc_u, rec_u, desc_p, iva_usd = self.actualizar_ui_carrito()
        if total_neto < 0: return messagebox.showerror("Error", "El total no puede ser negativo.")

        df_prod = self.db.obtener_productos()
        for item in self.carrito_pos:
            fila_prod = df_prod[df_prod["id"] == item["id"]]
            if not fila_prod.empty:
                stock_real = int(fila_prod.iloc[0]["stock"])
                if stock_real < item["cant"]:
                    return messagebox.showerror("Error Crítico de Stock", f"El inventario de '{item['nombre']}' fue modificado.\nDisponible real: {stock_real}\nSolicitado: {item['cant']}")
            else:
                return messagebox.showerror("Error", f"El producto '{item['nombre']}' ya no existe en el sistema.")

        self.db.cursor.execute("SELECT COUNT(*) FROM transacciones WHERE categoria = 'Ventas de Mercancía'")
        num_ventas = self.db.cursor.fetchone()[0] + 1
        factura_codigo = f"FAC-{num_ventas:06d}"

        detalle_str = ""
        for item in self.carrito_pos:
            # Eliminamos la variable [item['codigo']] para que solo muestre el nombre del producto
            detalle_str += f"{item['nombre']} | Cant: {item['cant']} x ${item['p_unit']:,.2f} = ${item['subtotal']:,.2f}\n"
        
        detalle_str += "----------------------------------------\n"
        detalle_str += f"Subtotal Bruto: ${sub_b:,.2f}\n"
        if desc_u > 0: detalle_str += f"Descuento ({desc_p}%): -${desc_u:,.2f}\n"
        if rec_u > 0: detalle_str += f"Sobrecargo/Envío: +${rec_u:,.2f}\n"
        detalle_str += f"IVA (16%): ${iva_usd:,.2f}\n" 
        detalle_str += f"TOTAL PAGADO: ${total_neto:,.2f}"

        fecha = datetime.now().strftime("%Y-%m-%d")
        hora = datetime.now().strftime("%H:%M:%S")
        caja = "Caja Principal"
        
        # --- NUEVA LÓGICA: Pagos Mixtos POS ---
        m1_t = self.pos_metodo.get()
        m2_t = self.pos_metodo2.get()
        
        if m2_t != "Ninguno":
            try:
                # Si la caja está vacía asume el total, sino toma el número
                v1 = float(self.pos_monto1.get()) if self.pos_monto1.get() else total_neto
                v2 = float(self.pos_monto2.get()) if self.pos_monto2.get() else 0.0
                if abs((v1 + v2) - total_neto) > 0.05:
                    return messagebox.showerror("Error de Pagos", f"La suma de los montos (${v1 + v2:,.2f}) no coincide con el total (${total_neto:,.2f}).")
                metodo = f"{m1_t}: ${v1:,.2f} | {m2_t}: ${v2:,.2f}"
            except ValueError:
                return messagebox.showerror("Error", "Ingrese montos numéricos válidos en los métodos de pago.")
        else:
            metodo = m1_t

        descripcion_venta = f"Venta POS - Factura {factura_codigo}"
        
        self.db.cursor.execute("""
            INSERT INTO transacciones (fecha, tipo, categoria, monto, forma_pago, descripcion, factura, hora, caja, detalle_factura, estado, eliminado)
            VALUES (?, 'Ingreso', 'Ventas de Mercancía', ?, ?, ?, ?, ?, ?, ?, 'Pagado / Completado', 0)
        """, (fecha, total_neto, metodo, descripcion_venta, factura_codigo, hora, caja, detalle_str))
        
        transaccion_id = self.db.cursor.lastrowid 

        for item in self.carrito_pos:
            self.db.actualizar_stock(int(item["id"]), -int(item["cant"]))

        self.db.conn.commit()
        
        ruta_pdf = self.db.generar_ticket_pdf(transaccion_id)
        if ruta_pdf and os.path.exists(ruta_pdf):
            try:
                if platform.system() == 'Windows':
                    try:
                        # Intenta imprimir silenciosamente
                        os.startfile(ruta_pdf, "print")
                    except OSError:
                        # Respaldo: Si Windows lo bloquea, abre el PDF en pantalla y avisa
                        os.startfile(ruta_pdf)
                        messagebox.showwarning("Aviso de Windows", "Windows bloqueó la impresión automática. El ticket se abrió en pantalla para que lo imprimas manualmente.")
            except Exception:
                pass

        messagebox.showinfo("Venta Procesada", f"La {factura_codigo} se ha cobrado exitosamente.")
        
        # --- CORRECCIÓN: Vaciar el carrito en lugar de cerrar el programa ---
        self.carrito_pos = []
        if hasattr(self, 'entry_buscador'): self.entry_buscador.delete(0, 'end')
        self.pos_desc.delete(0, 'end'); self.pos_desc.insert(0, "0")
        self.pos_recargo.delete(0, 'end'); self.pos_recargo.insert(0, "0")
        self.actualizar_ui_carrito()
            
        if hasattr(self, 'actualizar_dashboard_data'): self.actualizar_dashboard_data()
        if hasattr(self, 'actualizar_inventario'): self.actualizar_inventario()
        if hasattr(self, 'cargar_tabla_ventas'): self.cargar_tabla_ventas()
        if hasattr(self, 'cargar_tabla_movimientos'): self.cargar_tabla_movimientos()

    # ==========================================
    # DASHBOARD
    # ==========================================
    def setup_dash(self):
        f = ctk.CTkFrame(self.container, fg_color="transparent")
        self.frames["dash"] = f
        f.grid(row=0, column=0, sticky="nsew")
        
        cards_f = ctk.CTkFrame(f, fg_color="transparent")
        cards_f.pack(fill="x", pady=10)
        cards_f.grid_columnconfigure((0, 1, 2), weight=1)
        self.card_in = self.crear_tarjeta(cards_f, "INGRESOS TOTALES ($)", "$0.00", self.verde_neon, 0)
        self.card_out = self.crear_tarjeta(cards_f, "EGRESOS TOTALES ($)", "$0.00", self.rojo_neon, 1)
        self.card_neto = self.crear_tarjeta(cards_f, "NETO TOTAL ($)", "$0.00", "black", 2)

        breakdown_f = ctk.CTkFrame(f, fg_color=self.color_card, corner_radius=15, border_width=1, border_color="#E4E6EB")
        breakdown_f.pack(fill="both", expand=True, pady=15)
        breakdown_f.grid_columnconfigure((0, 1), weight=1)
        breakdown_f.grid_rowconfigure(0, weight=1)

        ing_metodos_frame = ctk.CTkScrollableFrame(breakdown_f, fg_color="transparent")
        ing_metodos_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        ctk.CTkLabel(ing_metodos_frame, text="📥 INGRESOS POR MÉTODO", font=("Arial", 16, "bold"), text_color=self.verde_neon).pack(anchor="w", pady=(0, 15))
        
        self.lbls_ing_metodos = {}
        for metodo in self.metodos_pago:
            row = ctk.CTkFrame(ing_metodos_frame, fg_color="transparent")
            row.pack(fill="x", pady=6)
            ctk.CTkLabel(row, text=metodo, font=("Arial", 13, "bold"), text_color="#666666").pack(side="left")
            lbl_monto = ctk.CTkLabel(row, text="$0.00", font=("Arial", 13, "bold"), text_color="black")
            lbl_monto.pack(side="right")
            self.lbls_ing_metodos[metodo] = lbl_monto

        egr_metodos_frame = ctk.CTkScrollableFrame(breakdown_f, fg_color="transparent")
        egr_metodos_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        ctk.CTkLabel(egr_metodos_frame, text="📤 EGRESOS POR MÉTODO", font=("Arial", 16, "bold"), text_color=self.rojo_neon).pack(anchor="w", pady=(0, 15))
        
        self.lbls_egr_metodos = {}
        for metodo in self.metodos_pago:
            row = ctk.CTkFrame(egr_metodos_frame, fg_color="transparent")
            row.pack(fill="x", pady=6)
            ctk.CTkLabel(row, text=metodo, font=("Arial", 13, "bold"), text_color="#666666").pack(side="left")
            lbl_monto = ctk.CTkLabel(row, text="$0.00", font=("Arial", 13, "bold"), text_color="black")
            lbl_monto.pack(side="right")
            self.lbls_egr_metodos[metodo] = lbl_monto

        breakdown_cats_f = ctk.CTkFrame(f, fg_color=self.color_card, corner_radius=15, border_width=1, border_color="#E4E6EB")
        breakdown_cats_f.pack(fill="both", expand=True, pady=(0, 15))
        breakdown_cats_f.grid_columnconfigure((0, 1), weight=1)
        breakdown_cats_f.grid_rowconfigure(0, weight=1)

        ing_cats_frame = ctk.CTkScrollableFrame(breakdown_cats_f, fg_color="transparent")
        ing_cats_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        ctk.CTkLabel(ing_cats_frame, text="📥 INGRESOS POR CUENTA", font=("Arial", 16, "bold"), text_color=self.verde_neon).pack(anchor="w", pady=(0, 15))
        
        self.lbls_ing_cats = {}
        for cat in self.cats_ingreso:
            row = ctk.CTkFrame(ing_cats_frame, fg_color="transparent")
            row.pack(fill="x", pady=6)
            ctk.CTkLabel(row, text=cat, font=("Arial", 13, "bold"), text_color="#666666").pack(side="left")
            lbl_monto = ctk.CTkLabel(row, text="$0.00", font=("Arial", 13, "bold"), text_color="black")
            lbl_monto.pack(side="right")
            self.lbls_ing_cats[cat] = lbl_monto

        egr_cats_frame = ctk.CTkScrollableFrame(breakdown_cats_f, fg_color="transparent")
        egr_cats_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        ctk.CTkLabel(egr_cats_frame, text="📤 EGRESOS POR CUENTA", font=("Arial", 16, "bold"), text_color=self.rojo_neon).pack(anchor="w", pady=(0, 15))
        
        self.lbls_egr_cats = {}
        for cat in self.cats_egreso:
            row = ctk.CTkFrame(egr_cats_frame, fg_color="transparent")
            row.pack(fill="x", pady=6)
            ctk.CTkLabel(row, text=cat, font=("Arial", 13, "bold"), text_color="#666666").pack(side="left")
            lbl_monto = ctk.CTkLabel(row, text="$0.00", font=("Arial", 13, "bold"), text_color="black")
            lbl_monto.pack(side="right")
            self.lbls_egr_cats[cat] = lbl_monto

    def crear_tarjeta(self, master, titulo, valor, color, col):
        card = ctk.CTkFrame(master, fg_color=self.color_card, height=130, corner_radius=15, border_width=1, border_color="#E4E6EB")
        card.grid(row=0, column=col, padx=10, sticky="nsew")
        card.grid_propagate(False)
        ctk.CTkLabel(card, text=titulo, font=("Arial", 12, "bold"), text_color="#666666").pack(pady=(20, 0))
        lbl_v = ctk.CTkLabel(card, text=valor, font=("Arial", 26, "bold"), text_color=color)
        lbl_v.pack(pady=10)
        return lbl_v

    def actualizar_dashboard_data(self):
        df = self.db.obtener_todas_transacciones()
        if df.empty: 
            for c in [self.card_in, self.card_out, self.card_neto]: c.configure(text="$0.00")
            for m in self.metodos_pago:
                self.lbls_ing_metodos[m].configure(text="$0.00")
                self.lbls_egr_metodos[m].configure(text="$0.00")
            for c in self.cats_ingreso: self.lbls_ing_cats[c].configure(text="$0.00")
            for c in self.cats_egreso: self.lbls_egr_cats[c].configure(text="$0.00")
            return
            
        ing, egr = df[df["tipo"] == "Ingreso"]["monto"].sum(), df[df["tipo"] == "Egreso"]["monto"].sum()
        self.card_in.configure(text=f"${ing:,.2f}")
        self.card_out.configure(text=f"${egr:,.2f}")
        self.card_neto.configure(text=f"${ing-egr:,.2f}", text_color=self.verde_neon if ing-egr >= 0 else self.rojo_neon)
        
        for m in self.metodos_pago:
            self.lbls_ing_metodos[m].configure(text=f"${df[(df['tipo'] == 'Ingreso') & (df['forma_pago'] == m)]['monto'].sum():,.2f}")
            self.lbls_egr_metodos[m].configure(text=f"${df[(df['tipo'] == 'Egreso') & (df['forma_pago'] == m)]['monto'].sum():,.2f}")

        for c in self.cats_ingreso:
            self.lbls_ing_cats[c].configure(text=f"${df[(df['tipo'] == 'Ingreso') & (df['categoria'] == c)]['monto'].sum():,.2f}")
        for c in self.cats_egreso:
            self.lbls_egr_cats[c].configure(text=f"${df[(df['tipo'] == 'Egreso') & (df['categoria'] == c)]['monto'].sum():,.2f}")

    # ==========================================
    # REGISTRO MANUAL
    # ==========================================
    def setup_registro(self):
        f = ctk.CTkFrame(self.container, corner_radius=20, border_width=2, fg_color=self.color_card)
        self.frames["reg"] = f
        f.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(f, text="REGISTRO MANUAL", font=("Arial", 20, "bold"), text_color="black").pack(pady=(15, 0))
        
        self.var_tipo = ctk.StringVar(value="Ingreso")
        self.seg_btn = ctk.CTkSegmentedButton(f, values=["Ingreso", "Egreso"], variable=self.var_tipo, command=self.actualizar_tema_registro, selected_color=self.verde_neon, unselected_color="#E4E6EB", text_color="black", font=("Arial", 12, "bold"))
        self.seg_btn.pack(pady=20)
        
        form_frame = ctk.CTkFrame(f, fg_color="transparent")
        form_frame.pack(pady=10)
        
        self.cal_fecha = DateEntry(form_frame, width=38, background="white", foreground="black", bordercolor="#CCCCCC", headersbackground=self.verde_neon, headersforeground="white", borderwidth=1, date_pattern="yyyy-mm-dd", font=("Arial", 12, "bold"))
        self.cal_fecha.grid(row=0, column=0, pady=(0, 15), ipady=8)
        
        self.var_pago = ctk.StringVar(value="Efectivo")
        self.pago_menu = ctk.CTkOptionMenu(form_frame, values=self.metodos_pago, variable=self.var_pago, width=400, height=45, font=("Arial", 12, "bold"))
        self.pago_menu.grid(row=1, column=0, pady=10)
        
        self.combo_cat = ctk.CTkComboBox(form_frame, width=400, height=45, command=self.on_categoria_change, font=("Arial", 12, "bold"))
        self.combo_cat.grid(row=2, column=0, pady=10)

        self.combo_estado_reg = ctk.CTkComboBox(form_frame, values=self.estados_transaccion, width=400, height=45, font=("Arial", 12, "bold"))
        self.combo_estado_reg.grid(row=3, column=0, pady=10)
        self.combo_estado_reg.set(self.estados_transaccion[0])
        
        self.entry_monto = ctk.CTkEntry(form_frame, placeholder_text="Monto en Dólares ($)", width=400, height=45, font=("Arial", 12, "bold"))
        self.entry_monto.grid(row=4, column=0, pady=10)
        
        self.entry_desc = ctk.CTkEntry(form_frame, placeholder_text="Descripción breve", width=400, height=45, font=("Arial", 12, "bold"))
        self.entry_desc.grid(row=5, column=0, pady=10)
        
        # --- NUEVO: Atajos de teclado para guardar rápido ---
        self.entry_monto.bind("<Return>", lambda e: self.guardar())
        self.entry_desc.bind("<Return>", lambda e: self.guardar())
        
        self.producto_frame = ctk.CTkFrame(f, fg_color="transparent")

        self.lbl_scan_venta = ctk.CTkLabel(self.producto_frame, text="📟 Escanear", text_color="black", font=("Arial", 12, "bold"))
        self.lbl_scan_venta.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.entry_scan_venta = ctk.CTkEntry(self.producto_frame, placeholder_text="Lector...", width=250, height=40, font=("Arial", 12, "bold"))
        self.entry_scan_venta.grid(row=0, column=1, padx=5, pady=5)
        self.entry_scan_venta.bind("<Return>", self.on_barcode_venta)

        self.lbl_producto = ctk.CTkLabel(self.producto_frame, text="Producto", text_color="black", font=("Arial", 12, "bold"))
        self.lbl_producto.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.combo_producto = ctk.CTkComboBox(self.producto_frame, width=250, height=40, command=self.calcular_monto_venta_combo, font=("Arial", 12, "bold"))
        self.combo_producto.grid(row=1, column=1, padx=5, pady=5)
        
        self.lbl_cantidad = ctk.CTkLabel(self.producto_frame, text="Cantidad", text_color="black", font=("Arial", 12, "bold"))
        self.lbl_cantidad.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.entry_cantidad_producto = ctk.CTkEntry(self.producto_frame, placeholder_text="Cant.", width=250, height=40, font=("Arial", 12, "bold"))
        self.entry_cantidad_producto.grid(row=2, column=1, padx=5, pady=5)
        self.entry_cantidad_producto.bind("<KeyRelease>", self.calcular_monto_venta)
        
        self.producto_frame.pack_forget()
        self.btn_save = ctk.CTkButton(f, text="CONFIRMAR MOVIMIENTO", width=400, height=55, font=("Arial", 16, "bold"), text_color="white", command=self.guardar)
        self.btn_save.pack(pady=20)
        self.actualizar_tema_registro("Ingreso")

    def on_barcode_venta(self, event=None):
        codigo = self.entry_scan_venta.get().strip()
        if not codigo: return
        df = self.db.obtener_productos()
        fila = df[df["codigo"] == codigo]
        if not fila.empty:
            r = fila.iloc[0]
            texto_combo = f"{r['codigo']} - {r['nombre']} (Stock: {r['stock']} | ${r['precio_venta']})"
            valores_actuales = self.combo_producto.cget("values")
            if texto_combo not in valores_actuales:
                self.combo_producto.configure(values=list(valores_actuales) + [texto_combo])
            self.combo_producto.set(texto_combo)
            self.entry_cantidad_producto.delete(0, "end")
            self.entry_monto.delete(0, "end")
            self.entry_cantidad_producto.focus()
            self.entry_scan_venta.delete(0, "end")
        else: messagebox.showerror("Error", f"No se encontró código: {codigo}")

    def calcular_monto_venta_combo(self, valor): self.calcular_monto_venta()
        
    def calcular_monto_venta(self, event=None):
        if self.var_tipo.get() == "Ingreso" and self.combo_cat.get() == "Ventas de Mercancía":
            producto = self.obtener_producto_seleccionado()
            if producto is not None:
                try:
                    cant_texto = self.entry_cantidad_producto.get()
                    if cant_texto:
                        cant = int(cant_texto)
                        if cant > 0:
                            total = cant * float(producto["precio_venta"])
                            self.entry_monto.delete(0, "end")
                            self.entry_monto.insert(0, f"{total:.2f}")
                except ValueError: pass

    def on_categoria_change(self, valor=None): self.actualizar_tema_registro(self.var_tipo.get())

    def actualizar_tema_registro(self, tipo):
        color = self.verde_neon if tipo == "Ingreso" else self.rojo_neon
        self.frames["reg"].configure(border_color=color)
        self.btn_save.configure(fg_color=color, text_color="white")
        self.pago_menu.configure(button_color=color, button_hover_color=color)
        cats = self.cats_ingreso if tipo == "Ingreso" else self.cats_egreso
        self.combo_cat.configure(values=cats)
        if self.combo_cat.get() not in cats: self.combo_cat.set(cats[0])
        self.cargar_productos_combo()
        self.mostrar_ocultar_productos()

    def mostrar_ocultar_productos(self):
        if self.combo_cat.get() == "Ventas de Mercancía": self.producto_frame.pack(pady=10)
        else: self.producto_frame.pack_forget()

    def cargar_productos_combo(self):
        df = self.db.obtener_productos()
        valores = [f"{r['codigo']} - {r['nombre']} (Stock: {r['stock']} | ${r['precio_venta']})" for _, r in df.iterrows()]
        self.combo_producto.configure(values=valores)
        if valores and not self.combo_producto.get(): self.combo_producto.set(valores[0])

    def obtener_producto_seleccionado(self):
        texto = self.combo_producto.get().strip()
        if not texto: return None
        codigo = texto.split(" - ")[0].strip()
        df = self.db.obtener_productos()
        fila = df[df["codigo"] == codigo]
        return fila.iloc[0] if not fila.empty else None

    def guardar(self):
        try:
            monto_texto = self.entry_monto.get().replace("$", "").replace(",", "")
            monto = float(monto_texto)
            if monto <= 0: raise ValueError
            
            fecha = self.cal_fecha.get_date().strftime("%Y-%m-%d")
            tipo = self.var_tipo.get()
            categoria = self.combo_cat.get()
            estado = self.combo_estado_reg.get()
            forma_pago = self.var_pago.get()
            descripcion = self.entry_desc.get().strip()
            
            producto_id, cantidad_producto = None, None
            detalle_factura_str = ""
            hora_actual = datetime.now().strftime("%H:%M:%S")
            caja_actual = "Caja Principal" 
            factura_codigo = None

            if categoria == "Ventas de Mercancía":
                producto = self.obtener_producto_seleccionado()
                if producto is None: return messagebox.showerror("Error", "Selecciona un producto.")
                try:
                    cantidad_producto = int(self.entry_cantidad_producto.get())
                    if cantidad_producto <= 0: raise ValueError
                except: return messagebox.showerror("Error", "Cantidad inválida.")
                
                producto_id = int(producto["id"])
                if int(producto["stock"]) < cantidad_producto: return messagebox.showerror("Error", "Stock insuficiente.")
                
                # Eliminamos la variable [producto['codigo']] de la cadena de texto
                detalle_factura_str = f"{producto['nombre']} | Cant: {cantidad_producto} x ${producto['precio_venta']:,.2f} = ${monto:,.2f}\n"
                detalle_factura_str += f"----------------------------------------\nTOTAL PAGADO: ${monto:,.2f}"

                self.db.actualizar_stock(producto_id, -cantidad_producto)

                self.db.actualizar_stock(producto_id, -cantidad_producto)

                if tipo == "Ingreso":
                    self.db.cursor.execute("SELECT COUNT(*) FROM transacciones WHERE categoria = 'Ventas de Mercancía'")
                    num_ventas = self.db.cursor.fetchone()[0] + 1
                    factura_codigo = f"FAC-{num_ventas:06d}"

            self.db.cursor.execute("""
                INSERT INTO transacciones (fecha, tipo, categoria, monto, forma_pago, descripcion, producto_id, cantidad_producto, factura, hora, caja, detalle_factura, estado, eliminado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (fecha, tipo, categoria, monto, forma_pago, descripcion, producto_id, cantidad_producto, factura_codigo, hora_actual, caja_actual, detalle_factura_str, estado))
            
            self.db.conn.commit()
            messagebox.showinfo("Éxito", "Movimiento registrado exitosamente.")
            
            self.entry_monto.delete(0, "end")
            self.entry_desc.delete(0, "end")
            self.entry_cantidad_producto.delete(0, "end")
            if hasattr(self, 'entry_scan_venta'): self.entry_scan_venta.delete(0, "end")
            self.actualizar_dashboard_data()
            self.cargar_tabla_ventas()
        except ValueError:
            messagebox.showerror("Error", "Monto inválido.")

    def exportar_movimientos_pdf(self):
        df = self.db.obtener_todas_transacciones()
        
        if df.empty:
            return messagebox.showerror("Error", "No hay movimientos registrados para exportar.")
            
        try:
            def limpiar(texto):
                return str(texto).encode('latin-1', 'replace').decode('latin-1')

            from tkinter import filedialog
            ruta_guardado = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                initialfile=f"Historial_Movimientos_{datetime.now().strftime('%Y%m%d')}.pdf",
                title="Guardar Historial de Movimientos",
                filetypes=[("Archivo PDF", "*.pdf")]
            )
            
            if not ruta_guardado: return
                
            # --- NUEVO: Extraemos los datos dinámicos ---
            emp_nombre, _, _ = self.db.obtener_datos_empresa()

            pdf = FPDF(orientation='L', format='A4')
            pdf.add_page()
            
            pdf.set_font("Arial", 'B', 16)
            pdf.set_text_color(0, 128, 96)
            pdf.cell(0, 10, limpiar(f"LIBRO DIARIO DE MOVIMIENTOS - {emp_nombre.upper()}"), ln=True, align='C')
            
            pdf.set_font("Arial", 'I', 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 5, limpiar(f"Fecha de Exportación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"), ln=True, align='C')
            pdf.ln(5)
            
            pdf.set_font("Arial", 'B', 9)
            pdf.set_fill_color(0, 128, 96)
            pdf.set_text_color(255, 255, 255)
            
            # Ajuste de columnas para incluir Estado
            anchos = [20, 20, 35, 30, 25, 30, 115] # ID, Fecha, Categoria, Estado, Monto, Metodo, Descripcion
            
            pdf.cell(anchos[0], 8, "ID", border=1, fill=True, align='C')
            pdf.cell(anchos[1], 8, "Fecha", border=1, fill=True, align='C')
            pdf.cell(anchos[2], 8, "Categoria", border=1, fill=True, align='C')
            pdf.cell(anchos[3], 8, "Estado", border=1, fill=True, align='C')
            pdf.cell(anchos[4], 8, "Monto ($)", border=1, fill=True, align='C')
            pdf.cell(anchos[5], 8, "Metodo", border=1, fill=True, align='C')
            pdf.cell(anchos[6], 8, "Descripcion", border=1, fill=True, align='C', ln=True)

            pdf.set_font("Arial", '', 8)
            total_ingresos = 0.0
            total_egresos = 0.0
            
            for _, r in df.iterrows():
                if r['tipo'] == 'Ingreso':
                    pdf.set_text_color(0, 128, 0)
                    total_ingresos += float(r['monto'])
                else:
                    pdf.set_text_color(200, 0, 0)
                    total_egresos += float(r['monto'])
                    
                desc = limpiar(str(r.get('descripcion', '')))
                desc_corta = desc[:75] + "..." if len(desc) > 75 else desc
                cat = limpiar(str(r.get('categoria', '')))
                cat_corta = cat[:18] + "..." if len(cat) > 18 else cat
                estado = limpiar(str(r.get('estado', '')))

                pdf.cell(anchos[0], 8, str(r.get('id', '')), border=1, align='C')
                pdf.cell(anchos[1], 8, str(r.get('fecha', '')), border=1, align='C')
                pdf.cell(anchos[2], 8, cat_corta, border=1, align='L')
                pdf.cell(anchos[3], 8, estado, border=1, align='C')
                pdf.cell(anchos[4], 8, f"${float(r.get('monto', 0)):,.2f}", border=1, align='R')
                pdf.cell(anchos[5], 8, limpiar(str(r.get('forma_pago', ''))), border=1, align='C')
                pdf.cell(anchos[6], 8, desc_corta, border=1, align='L', ln=True)

            pdf.ln(5)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 8, "RESUMEN DE MOVIMIENTOS", ln=True)
            
            pdf.set_font("Arial", '', 11)
            pdf.cell(100, 8, f"Total Ingresos: ${total_ingresos:,.2f}", ln=True)
            pdf.cell(100, 8, f"Total Egresos: ${total_egresos:,.2f}", ln=True)
            
            neto = total_ingresos - total_egresos
            pdf.set_font("Arial", 'B', 12)
            pdf.set_text_color(0, 128, 0 if neto >= 0 else 200)
            pdf.cell(100, 8, f"BALANCE NETO: ${neto:,.2f}", ln=True)

            pdf.output(ruta_guardado)
            
            if platform.system() == 'Windows':
                os.startfile(ruta_guardado)
                
            messagebox.showinfo("Éxito", "El historial de movimientos fue exportado a PDF exitosamente.")
            
        except Exception as e:
            messagebox.showerror("Error Interno PDF", f"Falló la creación del PDF:\n\n{str(e)}")



    def actualizar_periodos_disponibles(self, *args):
        df = self.db.obtener_todas_transacciones()
        
        if df.empty:
            self.combo_periodo.configure(values=["Sin datos"])
            self.combo_periodo.set("Sin datos")
            self.cargar_datos_periodo("Sin datos")
            return
            
        modo = self.modo_resumen_var.get()
        
        # Filtramos extrayendo caracteres de la fecha YYYY-MM-DD
        if modo == "Diario":
            periodos = sorted(df['fecha'].unique().tolist(), reverse=True)
        elif modo == "Mensual":
            df['periodo'] = df['fecha'].str[:7] # Extrae YYYY-MM
            periodos = sorted(df['periodo'].unique().tolist(), reverse=True)
        elif modo == "Anual":
            df['periodo'] = df['fecha'].str[:4] # Extrae YYYY
            periodos = sorted(df['periodo'].unique().tolist(), reverse=True)
        
        if periodos:
            self.combo_periodo.configure(values=periodos)
            self.combo_periodo.set(periodos[0])
            self.cargar_datos_periodo(periodos[0])
        else:
            self.combo_periodo.configure(values=["Sin datos"])
            self.combo_periodo.set("Sin datos")
            self.cargar_datos_periodo("Sin datos")

    def cargar_datos_periodo(self, periodo_seleccionado):
        for item in self.tabla_rm.get_children(): self.tabla_rm.delete(item)
            
        if periodo_seleccionado == "Sin datos" or not periodo_seleccionado:
            self.card_rm_ing.configure(text="$0.00")
            self.card_rm_egr.configure(text="$0.00")
            self.card_rm_bal.configure(text="$0.00", text_color="black")
            return
            
        df = self.db.obtener_todas_transacciones()
        # Magia de Pandas: str.startswith funciona igual de bien buscando "2026", "2026-07" o "2026-07-10"
        df_per = df[df['fecha'].str.startswith(periodo_seleccionado)]
        
        if df_per.empty:
            self.card_rm_ing.configure(text="$0.00")
            self.card_rm_egr.configure(text="$0.00")
            self.card_rm_bal.configure(text="$0.00", text_color="black")
            return

        ingresos = df_per[df_per["tipo"] == "Ingreso"]["monto"].sum()
        egresos = df_per[df_per["tipo"] == "Egreso"]["monto"].sum()
        balance = ingresos - egresos
        
        self.card_rm_ing.configure(text=f"${ingresos:,.2f}")
        self.card_rm_egr.configure(text=f"${egresos:,.2f}")
        self.card_rm_bal.configure(text=f"${balance:,.2f}", text_color=self.verde_neon if balance >= 0 else self.rojo_neon)
        
        for _, r in df_per.iterrows():
            tag = "ingreso" if r["tipo"] == "Ingreso" else "egreso"
            str_monto = f"${r['monto']:,.2f}"
            desc = r["descripcion"] if pd.notna(r["descripcion"]) else ""
            self.tabla_rm.insert("", "end", values=(r["fecha"], r["tipo"], r["categoria"], str_monto, desc), tags=(tag,))

    # ==========================================
    # MOVIMIENTOS Y BUSCADOR
    # ==========================================
    def setup_movimientos(self):
        f = ctk.CTkFrame(self.container, fg_color="transparent")
        self.frames["movimientos"] = f
        f.grid(row=0, column=0, sticky="nsew")
        
        top_frame = ctk.CTkFrame(f, fg_color="transparent")
        top_frame.pack(fill="x", pady=(0, 10))
        
        self.filtro_estado_var = ctk.StringVar(value="Todos")
        seg_btn_filtro = ctk.CTkSegmentedButton(top_frame, values=["Todos"] + self.estados_transaccion, variable=self.filtro_estado_var, command=lambda e: self.cargar_tabla_movimientos(), selected_color="#D1D5DB", text_color="black", font=("Arial", 12, "bold"))
        seg_btn_filtro.pack(side="left", padx=5)

        ctk.CTkButton(top_frame, text="🗑️ Mover a Papelera", font=("Arial", 12, "bold"), fg_color=self.rojo_neon, text_color="white", hover_color="#CC0000", command=self.eliminar_movimiento).pack(side="right")
        
        ctk.CTkButton(top_frame, text="📄 Exportar a PDF", font=("Arial", 12, "bold"), fg_color=self.verde_neon, text_color="white", command=self.exportar_movimientos_pdf).pack(side="right", padx=10)

        buscador_f = ctk.CTkFrame(f, fg_color=self.color_card, corner_radius=10)
        buscador_f.pack(fill="x", pady=(0, 10), ipady=5)

        ctk.CTkLabel(buscador_f, text="🔍 Buscar por:", font=("Arial", 12, "bold"), text_color="black").pack(side="left", padx=(15, 5))

        self.combo_param_mov = ctk.CTkComboBox(buscador_f, values=["Todos", "Fecha", "Tipo", "Estado", "Categoría", "Monto", "Método de Pago", "Descripción"], width=130, command=lambda e: self.cargar_tabla_movimientos(), font=("Arial", 12, "bold"))
        self.combo_param_mov.pack(side="left", padx=5)

        self.entry_buscar_mov = ctk.CTkEntry(buscador_f, placeholder_text="Escriba para buscar...", width=300, font=("Arial", 12, "bold"))
        self.entry_buscar_mov.pack(side="left", fill="x", expand=True, padx=(5, 15))
        self.entry_buscar_mov.bind("<KeyRelease>", self.cargar_tabla_movimientos)

        columnas = ("ID", "Fecha", "Tipo", "Estado", "Categoría", "Monto ($ | Bs.)", "Método de Pago", "Descripción")
        self.tabla = ttk.Treeview(f, columns=columnas, show="headings", height=18)
        self.tabla.column("ID", width=0, stretch=False)
        anchos = {"Fecha": 80, "Tipo": 70, "Estado": 110, "Categoría": 110, "Monto ($ | Bs.)": 130, "Método de Pago": 110, "Descripción": 190}
        for col in columnas[1:]:
            self.tabla.heading(col, text=col); self.tabla.column(col, width=anchos.get(col, 120), anchor="center")

        self.tabla.tag_configure("ingreso", foreground=self.verde_neon)
        self.tabla.tag_configure("egreso", foreground=self.rojo_neon)
        
        # --- MEJORA DE RESPONSIVIDAD: Padding adaptativo ---
        self.tabla.pack(fill="both", expand=True, padx=5, pady=5)
        self.tabla.bind("<Double-1>", self.abrir_detalle_movimiento) # <-- NUEVO: Escucha el doble clic

    def cargar_tabla_movimientos(self, event=None):
        for item in self.tabla.get_children(): self.tabla.delete(item)
        df = self.db.obtener_todas_transacciones()
        if df.empty: return

        filtro_est = self.filtro_estado_var.get()
        if filtro_est != "Todos": df = df[df["estado"] == filtro_est]

        if hasattr(self, 'entry_buscar_mov') and hasattr(self, 'combo_param_mov'):
            texto = self.entry_buscar_mov.get().strip().lower()
            parametro = self.combo_param_mov.get()
            if texto:
                mapa_cols = {"Fecha": "fecha", "Tipo": "tipo", "Estado": "estado", "Categoría": "categoria", "Monto": "monto", "Método de Pago": "forma_pago", "Descripción": "descripcion"}
                if parametro == "Todos":
                    mask = pd.Series(False, index=df.index)
                    for col in mapa_cols.values(): mask = mask | df[col].astype(str).str.lower().str.contains(texto, na=False)
                    df = df[mask]
                else:
                    col_db = mapa_cols.get(parametro)
                    if col_db: df = df[df[col_db].astype(str).str.lower().str.contains(texto, na=False)]

        for _, r in df.iterrows():
            tag = "ingreso" if r["tipo"] == "Ingreso" else "egreso"
            monto_usd = r['monto']
            # --- NUEVO: Leer tasa congelada o actual si es antigua ---
            tasa_usada = r.get("tasa_aplicada", self.tasa_actual)
            if pd.isna(tasa_usada): tasa_usada = self.tasa_actual
            monto_bs = monto_usd * float(tasa_usada)
            str_monto = f"${monto_usd:,.2f} | Bs. {monto_bs:,.2f}"
            
            # Capturamos el método de pago
            metodo_pago = str(r.get("forma_pago", "N/A"))
            
            # Lo insertamos en la tabla en el orden correcto
            self.tabla.insert("", "end", values=(r["id"], r["fecha"], r["tipo"], r.get("estado", "Completado"), r["categoria"], str_monto, metodo_pago, r["descripcion"] if pd.notna(r["descripcion"]) else ""), tags=(tag,))


    # --- NUEVO: Ventana modal para ver todos los detalles al hacer doble clic ---
    def abrir_detalle_movimiento(self, event=None):
        seleccion = self.tabla.selection()
        if not seleccion: return
        
        # Extraemos el ID oculto de la transacción seleccionada
        trans_id = self.tabla.item(seleccion[0])["values"][0]
        
        # Buscamos toda la información original en la base de datos
        df = pd.read_sql_query(f"SELECT * FROM transacciones WHERE id = {trans_id}", self.db.conn)
        if df.empty: return
        r = df.iloc[0]
        
        # Creamos la ventana emergente (Modal)
        modal = ctk.CTkToplevel(self)
        modal.title(f"Auditoría de Movimiento #{trans_id}")
        modal.geometry("550x650")
        modal.grab_set() # Bloquea la ventana principal hasta que se cierre esta
        
        ctk.CTkLabel(modal, text="DETALLE DE TRANSACCIÓN", font=("Arial", 20, "bold"), text_color=self.color_acento).pack(pady=(20, 10))
        
        scroll = ctk.CTkScrollableFrame(modal, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Función interna para dibujar las filas bonitas
        def agregar_fila(lbl, val, es_monto=False):
            f = ctk.CTkFrame(scroll, fg_color="transparent")
            f.pack(fill="x", pady=4)
            ctk.CTkLabel(f, text=lbl, font=("Arial", 13, "bold"), width=130, anchor="w", text_color="#555555").pack(side="left")
            color = self.verde_neon if (lbl=="Tipo:" and val=="Ingreso") or (es_monto and r.get('tipo')=="Ingreso") else (self.rojo_neon if (lbl=="Tipo:" and val=="Egreso") or (es_monto and r.get('tipo')=="Egreso") else "black")
            fnt = ("Arial", 14, "bold") if es_monto else ("Arial", 13)
            ctk.CTkLabel(f, text=str(val), font=fnt, text_color=color, justify="left", wraplength=320).pack(side="left", fill="x", expand=True)

        # Inyectamos los datos leídos de la DB
        agregar_fila("ID / Recibo:", f"#{r.get('id', '')}  |  Fac: {r.get('factura') if pd.notna(r.get('factura')) else 'N/A'}")
        agregar_fila("Fecha y Hora:", f"{r.get('fecha', '')} a las {r.get('hora') if pd.notna(r.get('hora')) else 'N/A'}")
        agregar_fila("Tipo:", r.get('tipo', ''))
        agregar_fila("Categoría:", r.get('categoria', ''))
        agregar_fila("Estado:", r.get('estado', ''))
        agregar_fila("Monto USD:", f"${float(r.get('monto', 0)):,.2f}", es_monto=True)
        agregar_fila("Monto Bs:", f"Bs. {(float(r.get('monto', 0)) * self.tasa_actual):,.2f}")
        agregar_fila("Método(s) de Pago:", r.get('forma_pago', ''))
        agregar_fila("Descripción:", r.get('descripcion', ''))
        
        # Si la transacción tiene una lista de artículos (Ventas o B2B), la mostramos en un cuadro de texto
        det = r.get('detalle_factura', '')
        if det and pd.notna(det) and str(det).strip() != "":
            ctk.CTkLabel(scroll, text="Conceptos y Artículos de la Factura:", font=("Arial", 13, "bold"), text_color="black", anchor="w").pack(fill="x", pady=(20, 5))
            txt = ctk.CTkTextbox(scroll, height=180, fg_color="#F4F6F9", text_color="black", font=("Consolas", 12))
            txt.pack(fill="x")
            txt.insert("1.0", str(det))
            txt.configure(state="disabled") # Solo lectura
            
        ctk.CTkButton(modal, text="Cerrar Detalles", fg_color="#333333", hover_color="#555555", font=("Arial", 14, "bold"), command=modal.destroy).pack(pady=20)
    
    def eliminar_movimiento(self):
        seleccion = self.tabla.selection()
        if not seleccion: return messagebox.showwarning("Aviso", "Selecciona al menos un movimiento.")
        
        msg = f"¿Enviar {len(seleccion)} movimiento(s) a la papelera?" if len(seleccion) > 1 else "¿Enviar este movimiento a la papelera?"
        if messagebox.askyesno("Confirmar", msg):
            try:
                for item in seleccion:
                    item_id = self.tabla.item(item)["values"][0]
                    self.db.soft_delete("transacciones", item_id)
                    
                self.cargar_tabla_movimientos()
                self.actualizar_dashboard_data()
                self.cargar_tabla_ventas()
                messagebox.showinfo("Éxito", f"{len(seleccion)} movimiento(s) enviado(s) a la papelera.")
            except Exception as e: 
                messagebox.showerror("Error", str(e))

    # ==========================================
    # VENTAS E IMPRESIÓN 
    # ==========================================
    def setup_ventas(self):
        f = ctk.CTkFrame(self.container, fg_color="transparent")
        self.frames["ventas"] = f
        f.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(f, text="HISTORIAL DE VENTAS Y TICKETS", font=("Arial", 24, "bold"), text_color=self.verde_neon).pack(pady=(0, 10))
        
        top_v = ctk.CTkFrame(f, fg_color="transparent")
        top_v.pack(fill="both", expand=True)

        filtros_f = ctk.CTkFrame(top_v, fg_color=self.color_card, corner_radius=10)
        filtros_f.pack(fill="x", pady=(0,10), ipady=5)
        
        ctk.CTkLabel(filtros_f, text="Día:", font=("Arial", 12, "bold"), text_color="black").pack(side="left", padx=(15, 5), pady=10)
        self.filtro_dia = ctk.CTkComboBox(filtros_f, values=[""] + [f"{i:02d}" for i in range(1, 32)], width=70, font=("Arial", 12, "bold"))
        self.filtro_dia.pack(side="left", padx=5)

        ctk.CTkLabel(filtros_f, text="Mes:", font=("Arial", 12, "bold"), text_color="black").pack(side="left", padx=5)
        self.filtro_mes = ctk.CTkComboBox(filtros_f, values=[""] + [f"{i:02d}" for i in range(1, 13)], width=70, font=("Arial", 12, "bold"))
        self.filtro_mes.pack(side="left", padx=5)

        ctk.CTkLabel(filtros_f, text="Año:", font=("Arial", 12, "bold"), text_color="black").pack(side="left", padx=5)
        anios = [str(a) for a in range(datetime.now().year - 2, datetime.now().year + 3)]
        self.filtro_anio = ctk.CTkComboBox(filtros_f, values=[""] + anios, width=90, font=("Arial", 12, "bold"))
        self.filtro_anio.pack(side="left", padx=5)

        ctk.CTkButton(filtros_f, text="🔍 Filtrar", width=100, font=("Arial", 12, "bold"), fg_color=self.color_acento, text_color="white", command=self.cargar_tabla_ventas).pack(side="left", padx=15)
        ctk.CTkButton(filtros_f, text="Limpiar", width=80, font=("Arial", 12, "bold"), fg_color="#555555", text_color="white", command=self.limpiar_filtros_ventas).pack(side="left", padx=5)

        self.tabla_ventas = ttk.Treeview(top_v, columns=("ID_Trans", "Factura", "Fecha", "Hora", "Método", "Total"), show="headings", height=10)
        for col in ("ID_Trans", "Factura", "Fecha", "Hora", "Método", "Total"): 
            self.tabla_ventas.heading(col, text=col)
            self.tabla_ventas.column(col, anchor="center")

        self.tabla_ventas.column("ID_Trans", width=0, stretch=False)
        
        # --- MEJORA DE RESPONSIVIDAD: Expansión fluida de la tabla de ventas ---
        self.tabla_ventas.pack(fill="both", expand=True, padx=5, pady=5)
        self.tabla_ventas.bind("<<TreeviewSelect>>", self.mostrar_detalle_venta)
        
        bot_v = ctk.CTkFrame(f, fg_color=self.color_card, corner_radius=15)
        bot_v.pack(fill="x", pady=10)
        ctk.CTkLabel(bot_v, text="📋 Detalle de la Factura", font=("Arial", 16, "bold"), text_color="black").pack(pady=(10, 0))
        
        self.txt_detalle_venta = ctk.CTkTextbox(bot_v, height=130, fg_color="#F4F6F9", text_color="black", font=("Consolas", 14, "bold"))
        self.txt_detalle_venta.pack(fill="x", padx=15, pady=(15, 5))
        
        botones_f = ctk.CTkFrame(bot_v, fg_color="transparent")
        botones_f.pack(pady=10)
        
        self.btn_exportar_pdf = ctk.CTkButton(botones_f, text="📄 Ver Ticket PDF", fg_color=self.verde_neon, text_color="white", font=("Arial", 14, "bold"), state="disabled", command=self.exportar_ticket_pdf)
        self.btn_exportar_pdf.pack(side="left", padx=10)
        
        self.btn_imprimir_pdf = ctk.CTkButton(botones_f, text="🖨️ Imprimir Automático", fg_color=self.color_acento, text_color="white", font=("Arial", 14, "bold"), state="disabled", command=self.imprimir_ticket_directo)
        self.btn_imprimir_pdf.pack(side="left", padx=10)
        
        self.diccionario_detalles = {} 

    def limpiar_filtros_ventas(self):
        self.filtro_dia.set(""); self.filtro_mes.set(""); self.filtro_anio.set("")
        self.cargar_tabla_ventas()

    def cargar_tabla_ventas(self):
        for item in self.tabla_ventas.get_children(): self.tabla_ventas.delete(item)
        self.diccionario_detalles.clear()
        self.txt_detalle_venta.delete("1.0", "end")
        
        df_ventas = self.db.obtener_todas_transacciones()
        if df_ventas.empty: return
        
        df_ventas = df_ventas[(df_ventas["categoria"] == "Ventas de Mercancía") & (df_ventas["caja"] != "B2B/Mayor")]

        f_dia, f_mes, f_anio = self.filtro_dia.get(), self.filtro_mes.get(), self.filtro_anio.get()

        for _, r in df_ventas.iterrows():
            f_parts = r["fecha"].split("-") 
            if (f_anio and f_parts[0] != f_anio) or (f_mes and f_parts[1] != f_mes) or (f_dia and len(f_parts)>2 and f_parts[2] != f_dia): continue
            
            monto_usd = r['monto']
            monto_bs = monto_usd * self.tasa_actual
            str_total_bimoneda = f"${monto_usd:,.2f} | Bs. {monto_bs:,.2f}"
            
            self.tabla_ventas.insert("", "end", values=(
                r["id"], r["factura"] or "S/N", r["fecha"], r["hora"] or "00:00:00", 
                r["forma_pago"], str_total_bimoneda
            ))
            
            det = r.get("detalle_factura", "")
            self.diccionario_detalles[r["id"]] = det if det else f"Venta Simple. ID Prod: {r['producto_id']} | Cant: {r['cantidad_producto']}"

    def mostrar_detalle_venta(self, event):
        seleccion = self.tabla_ventas.selection()
        if seleccion:
            tree_id = self.tabla_ventas.item(seleccion[0])["values"][0]
            detalle = self.diccionario_detalles.get(tree_id, "Sin detalles registrados.")
            self.txt_detalle_venta.delete("1.0", "end")
            self.txt_detalle_venta.insert("end", detalle)
            self.btn_exportar_pdf.configure(state="normal")
            self.btn_imprimir_pdf.configure(state="normal")
        else:
            self.btn_exportar_pdf.configure(state="disabled")
            self.btn_imprimir_pdf.configure(state="disabled")

    def exportar_ticket_pdf(self):
        seleccion = self.tabla_ventas.selection()
        if not seleccion: return
        trans_id = self.tabla_ventas.item(seleccion[0])["values"][0]
        
        ruta_pdf = self.db.generar_ticket_pdf(trans_id)
        
        if ruta_pdf and os.path.exists(ruta_pdf):
            try:
                if platform.system() == 'Windows':
                    os.startfile(ruta_pdf)
                elif platform.system() == 'Darwin':
                    import subprocess
                    subprocess.call(('open', ruta_pdf))
                else:
                    import subprocess
                    subprocess.call(('xdg-open', ruta_pdf))
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir el PDF: {e}")
        else:
            messagebox.showerror("Error", "No se pudo generar el ticket PDF.")

    def imprimir_ticket_directo(self):
        seleccion = self.tabla_ventas.selection()
        if not seleccion: return
        trans_id = self.tabla_ventas.item(seleccion[0])["values"][0]
        ruta_pdf = self.db.generar_ticket_pdf(trans_id)
        
        if ruta_pdf and os.path.exists(ruta_pdf):
            try:
                if platform.system() == 'Windows':
                    try:
                        # Intenta imprimir silenciosamente
                        os.startfile(ruta_pdf, "print")
                    except OSError:
                        # Respaldo: Si Windows lo bloquea, abre el PDF en pantalla y avisa
                        os.startfile(ruta_pdf)
                        messagebox.showwarning("Aviso de Windows", "Windows bloqueó la impresión automática. El ticket se abrió en pantalla para que lo imprimas manualmente.")
                else:
                    messagebox.showwarning("Aviso", "La impresión automática directa solo está soportada nativamente en Windows.")
            except Exception:
                pass
        else:
            messagebox.showerror("Error", "No se pudo generar el ticket para imprimir.")

    # ==========================================
    # NÓMINA
    # ==========================================
    # ==========================================
    # NÓMINA Y ADELANTOS
    # ==========================================
    def setup_nomina(self):
        f = ctk.CTkFrame(self.container, fg_color=self.color_card, corner_radius=20)
        self.frames["nomina"] = f
        f.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(f, text="CONTROL DE NÓMINA Y ADELANTOS", font=("Arial", 24, "bold"), text_color="black").pack(pady=(20, 10))
        
        self.tabs_nomina = ctk.CTkTabview(f, width=800, height=600, segmented_button_selected_color="#D1D5DB")
        self.tabs_nomina.pack(pady=10, fill="both", expand=True, padx=20)
        self.tabs_nomina.add("Gestión de Empleados")
        self.tabs_nomina.add("Préstamos y Adelantos") # <-- NUEVA PESTAÑA
        self.tabs_nomina.add("Pago de Nómina")
        
        # --- TAB 1: GESTIÓN DE EMPLEADOS ---
        form_emp = ctk.CTkFrame(self.tabs_nomina.tab("Gestión de Empleados"), fg_color="transparent")
        form_emp.pack(pady=10)
        self.ent_emp_cedula = ctk.CTkEntry(form_emp, placeholder_text="Cédula", width=120, font=("Arial", 12, "bold"))
        self.ent_emp_cedula.grid(row=0, column=0, padx=5, pady=10)
        self.ent_emp_nombre = ctk.CTkEntry(form_emp, placeholder_text="Nombre del Empleado", width=200, font=("Arial", 12, "bold"))
        self.ent_emp_nombre.grid(row=0, column=1, padx=5, pady=10)
        self.ent_emp_cargo = ctk.CTkEntry(form_emp, placeholder_text="Cargo", width=150, font=("Arial", 12, "bold"))
        self.ent_emp_cargo.grid(row=0, column=2, padx=5, pady=10)
        self.ent_emp_sueldo = ctk.CTkEntry(form_emp, placeholder_text="Sueldo ($)", width=100, font=("Arial", 12, "bold"))
        self.ent_emp_sueldo.grid(row=0, column=3, padx=5, pady=10)
        self.ent_emp_sueldo.bind("<Return>", lambda e: self.guardar_empleado()) 
        ctk.CTkButton(form_emp, text="Guardar", font=("Arial", 12, "bold"), fg_color=self.verde_neon, text_color="white", command=self.guardar_empleado).grid(row=0, column=4, padx=10, pady=10)
        
        columnas_emp = ("ID", "Cédula", "Nombre", "Cargo", "Sueldo Base", "Deuda Adelantos") # Nueva columna

        self.tabla_emp = ttk.Treeview(self.tabs_nomina.tab("Gestión de Empleados"), columns=columnas_emp, show="headings", height=10)
        for col in columnas_emp: self.tabla_emp.heading(col, text=col)
        self.tabla_emp.column("ID", width=0, stretch=False)
        self.tabla_emp.pack(fill="both", expand=True, pady=10)
        ctk.CTkButton(self.tabs_nomina.tab("Gestión de Empleados"), text="🗑️ Eliminar Empleado", font=("Arial", 12, "bold"), fg_color=self.rojo_neon, text_color="white", command=self.eliminar_empleado).pack(pady=10)
        
        # --- TAB 2: PRÉSTAMOS Y ADELANTOS ---
        prest_f = ctk.CTkFrame(self.tabs_nomina.tab("Préstamos y Adelantos"), fg_color="transparent")
        prest_f.pack(pady=40)
        
        ctk.CTkLabel(prest_f, text="Empleado:", font=("Arial", 12, "bold"), text_color="black").grid(row=0, column=0, padx=10, pady=10)
        self.combo_emp_prestamo = ctk.CTkComboBox(prest_f, width=300, font=("Arial", 12, "bold"))
        self.combo_emp_prestamo.grid(row=0, column=1, padx=10, pady=10)
        
        ctk.CTkLabel(prest_f, text="Monto del Adelanto ($):", font=("Arial", 12, "bold"), text_color="black").grid(row=1, column=0, padx=10, pady=10)
        self.ent_monto_prestamo = ctk.CTkEntry(prest_f, width=300, font=("Arial", 12, "bold"), placeholder_text="Ej: 20.00")
        self.ent_monto_prestamo.grid(row=1, column=1, padx=10, pady=10)
        
        ctk.CTkButton(prest_f, text="💰 OTORGAR ADELANTO", height=45, fg_color=self.rojo_neon, text_color="white", font=("Arial", 14, "bold"), command=self.otorgar_prestamo).grid(row=2, column=0, columnspan=2, pady=20, sticky="ew")

        # --- TAB 3: PAGO DE NÓMINA ---
        pago_f = ctk.CTkFrame(self.tabs_nomina.tab("Pago de Nómina"), fg_color="transparent")
        pago_f.pack(pady=20)
        
        ctk.CTkLabel(pago_f, text="Empleado:", font=("Arial", 12, "bold"), text_color="black").grid(row=0, column=0, padx=10, pady=10)
        self.combo_emp_pago = ctk.CTkComboBox(pago_f, width=250, font=("Arial", 12, "bold"), command=self.calcular_pago_neto)
        self.combo_emp_pago.grid(row=0, column=1, padx=10, pady=10)
        
        ctk.CTkLabel(pago_f, text="Horas Extras:", font=("Arial", 12, "bold"), text_color="black").grid(row=1, column=0, padx=10, pady=10)
        self.ent_emp_horas = ctk.CTkEntry(pago_f, width=250, font=("Arial", 12, "bold"), placeholder_text="Ej: 5")
        self.ent_emp_horas.grid(row=1, column=1, padx=10, pady=10)
        self.ent_emp_horas.bind("<KeyRelease>", self.calcular_pago_neto)
        
        ctk.CTkLabel(pago_f, text="Valor Hora Extra ($):", font=("Arial", 12, "bold"), text_color="black").grid(row=2, column=0, padx=10, pady=10)
        self.ent_emp_valor_hora = ctk.CTkEntry(pago_f, width=250, font=("Arial", 12, "bold"), placeholder_text="Ej: 15")
        self.ent_emp_valor_hora.grid(row=2, column=1, padx=10, pady=10)
        self.ent_emp_valor_hora.bind("<KeyRelease>", self.calcular_pago_neto)
        
        ctk.CTkLabel(pago_f, text="Bonificaciones ($):", font=("Arial", 12, "bold"), text_color="black").grid(row=3, column=0, padx=10, pady=10)
        self.ent_emp_bono = ctk.CTkEntry(pago_f, width=250, font=("Arial", 12, "bold"), placeholder_text="Ej: 50.00")
        self.ent_emp_bono.grid(row=3, column=1, padx=10, pady=10)
        self.ent_emp_bono.bind("<KeyRelease>", self.calcular_pago_neto)
        self.ent_emp_bono.bind("<Return>", lambda e: self.registrar_pago_nomina()) 

        self.lbl_pago_neto = ctk.CTkLabel(pago_f, text="BRUTO: $0.00 | DEUDA: -$0.00\nTOTAL A PAGAR: $0.00", font=("Arial", 16, "bold"), text_color=self.color_acento)
        self.lbl_pago_neto.grid(row=4, column=0, columnspan=2, pady=15)
        ctk.CTkButton(pago_f, text="REGISTRAR PAGO (NÓMINA)", height=45, fg_color=self.verde_neon, text_color="white", font=("Arial", 14, "bold"), command=self.registrar_pago_nomina).grid(row=5, column=0, columnspan=2, pady=10, sticky="ew")

    def guardar_empleado(self):
        cedula = self.ent_emp_cedula.get().strip()
        nombre = self.ent_emp_nombre.get().strip()
        cargo = self.ent_emp_cargo.get().strip()
        try:
            sueldo = float(self.ent_emp_sueldo.get())
            if cedula and nombre and cargo and sueldo > 0:
                self.db.crear_empleado(cedula, nombre, cargo, sueldo)
                self.actualizar_empleados()
                self.ent_emp_cedula.delete(0, "end"); self.ent_emp_nombre.delete(0, "end")
                self.ent_emp_cargo.delete(0, "end"); self.ent_emp_sueldo.delete(0, "end")
                messagebox.showinfo("Éxito", "Empleado registrado.")
            else: messagebox.showerror("Error", "Datos incompletos o sueldo inválido.")
        except: messagebox.showerror("Error", "Sueldo inválido.")

    def actualizar_empleados(self):
        for item in self.tabla_emp.get_children(): self.tabla_emp.delete(item)
        df = self.db.obtener_empleados()
        valores_combo = []
        for _, r in df.iterrows():
            ced = str(r.get("cedula", "N/A"))
            deuda = float(r.get("deuda", 0.0))
            self.tabla_emp.insert("", "end", values=(r["id"], ced, r["nombre"], r["cargo"], f"${r['sueldo_base']:,.2f}", f"${deuda:,.2f}"))
            # Combo incluye la ID al principio oculta visualmente
            valores_combo.append(f"{r['id']} - {ced} - {r['nombre']}")
        
        self.combo_emp_pago.configure(values=valores_combo if valores_combo else [""])
        self.combo_emp_prestamo.configure(values=valores_combo if valores_combo else [""])
        
        if valores_combo: 
            self.combo_emp_pago.set(valores_combo[0])
            self.combo_emp_prestamo.set(valores_combo[0])

    def eliminar_empleado(self):
        seleccion = self.tabla_emp.selection()
        if seleccion:
            item = self.tabla_emp.item(seleccion[0])
            self.db.eliminar_empleado(item["values"][0])
            self.actualizar_empleados()

    def otorgar_prestamo(self):
        seleccion = self.combo_emp_prestamo.get()
        if not seleccion or " - " not in seleccion: 
            return messagebox.showwarning("Aviso", "Seleccione un empleado válido.")
        
        try:
            monto = float(self.ent_monto_prestamo.get())
            if monto <= 0: raise ValueError
            
            # --- CORRECCIÓN: Separación a prueba de fallos ---
            partes = seleccion.split(" - ", 2)
            emp_id = int(partes[0])
            nombre_emp = partes[2] if len(partes) > 2 else (partes[1] if len(partes) > 1 else "Empleado")
            
            # 1. Sumar a la deuda del empleado
            self.db.cursor.execute("UPDATE empleados SET deuda = deuda + ? WHERE id = ?", (monto, emp_id))
            
            # 2. Registrar el egreso del dinero de la caja
            fecha = datetime.now().strftime("%Y-%m-%d")
            hora = datetime.now().strftime("%H:%M:%S")
            desc = f"Adelanto/Préstamo de Nómina: {nombre_emp}"
            self.db.cursor.execute("INSERT INTO transacciones (fecha, tipo, categoria, monto, forma_pago, descripcion, hora, estado, eliminado) VALUES (?, 'Egreso', 'Nómina', ?, 'Efectivo', ?, ?, 'Pagado / Completado', 0)", (fecha, monto, desc, hora))
            
            self.db.conn.commit()
            messagebox.showinfo("Éxito", f"Adelanto de ${monto:,.2f} otorgado a {nombre_emp}.")
            
            self.ent_monto_prestamo.delete(0, "end")
            self.actualizar_empleados()
            self.calcular_pago_neto()
            if hasattr(self, 'actualizar_dashboard_data'): self.actualizar_dashboard_data()
            if hasattr(self, 'cargar_tabla_movimientos'): self.cargar_tabla_movimientos()
            
        except ValueError:
            messagebox.showerror("Error", "Ingrese un monto numérico válido.")

    def calcular_pago_neto(self, event=None):
        seleccion = self.combo_emp_pago.get()
        if not seleccion: return None
        try:
            emp_id = int(seleccion.split(" - ")[0])
            df_emp = self.db.obtener_empleados()
            fila = df_emp[df_emp['id'] == emp_id].iloc[0]
            
            sueldo_base = float(fila['sueldo_base'])
            deuda_actual = float(fila['deuda'])
            
            horas = float(self.ent_emp_horas.get()) if self.ent_emp_horas.get() else 0.0
            valor_hora = float(self.ent_emp_valor_hora.get()) if self.ent_emp_valor_hora.get() else 0.0
            bono = float(self.ent_emp_bono.get()) if self.ent_emp_bono.get() else 0.0
            
            total_bruto = sueldo_base + (horas * valor_hora) + bono
            
            # Descuento automático: Cobra hasta donde alcance el sueldo
            descuento = min(total_bruto, deuda_actual)
            total_neto = total_bruto - descuento
            
            self.lbl_pago_neto.configure(text=f"Sueldo Bruto: ${total_bruto:,.2f} | Deuda cobrada: -${descuento:,.2f}\nTOTAL A PAGAR: ${total_neto:,.2f}")
            return total_neto, bono, descuento, emp_id, sueldo_base, horas, valor_hora, deuda_actual
        except:
            self.lbl_pago_neto.configure(text="TOTAL A PAGAR: Error")
            return None
    
    def generar_recibo_nomina_pdf(self, nombre_emp, cedula_emp, sueldo_base, horas, valor_hora, bono, descuento, total):
        try:
            def limpiar(texto): return str(texto).encode('latin-1', 'replace').decode('latin-1')
            from tkinter import filedialog
            from fpdf import FPDF
            
            fecha = datetime.now().strftime("%Y-%m-%d")
            ruta_guardado = filedialog.asksaveasfilename(
                defaultextension=".pdf", 
                initialfile=f"Recibo_Nomina_{nombre_emp.replace(' ', '_')}_{fecha}.pdf",
                title="Guardar Recibo de Nómina", 
                filetypes=[("Archivo PDF", "*.pdf")]
            )
            
            if not ruta_guardado: return
            
            # --- NUEVO: Solicitamos los datos dinámicos a la base de datos ---
            emp_nombre, emp_rif, emp_dir = self.db.obtener_datos_empresa()

            pdf = FPDF(orientation='P', format='A5')
            pdf.add_page()
            
            # --- ENCABEZADO EMPRESA DINÁMICO ---
            pdf.set_font("Arial", 'B', 14)
            pdf.set_text_color(0, 128, 96)
            pdf.cell(0, 8, limpiar(emp_nombre), ln=True, align='C')
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(0, 5, limpiar(emp_rif), ln=True, align='C')
            pdf.set_font("Arial", '', 8)
            pdf.set_text_color(100, 100, 100)
            # Reemplazamos los saltos de línea por comas para optimizar el espacio compacto del formato A5
            dir_limpia = emp_dir.replace('\n', ', ')
            pdf.cell(0, 4, limpiar(dir_limpia), ln=True, align='C')
            pdf.ln(3)

            # --- TÍTULO RECIBO ---
            pdf.set_font("Arial", 'B', 12)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 8, limpiar("RECIBO DE PAGO DE NÓMINA"), ln=True, align='C')
            pdf.ln(2)
            
            # Datos principales
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 5, limpiar(f"Fecha de Emisión: {fecha}"), ln=True)
            pdf.cell(0, 5, limpiar(f"Trabajador: {nombre_emp} | C.I: {cedula_emp}"), ln=True)
            pdf.ln(5)
            
            # Cabecera de la tabla de detalles
            pdf.set_fill_color(240, 244, 249)
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(90, 8, "Concepto Desglosado", border=1, fill=True)
            pdf.cell(38, 8, "Monto ($)", border=1, fill=True, ln=True, align='C')
            
            # Filas de conceptos
            pdf.set_font("Arial", '', 10)
            pdf.cell(90, 8, "Sueldo Base Acordado", border=1)
            pdf.cell(38, 8, f"${sueldo_base:,.2f}", border=1, align='R', ln=True)
            
            if horas > 0:
                pdf.cell(90, 8, limpiar(f"Horas Extras (Trabajadas: {horas} | Valor: ${valor_hora:,.2f})"), border=1)
                pdf.cell(38, 8, f"${(horas * valor_hora):,.2f}", border=1, align='R', ln=True)
            
            if bono > 0:
                pdf.cell(90, 8, "Bonificaciones", border=1)
                pdf.cell(38, 8, f"${bono:,.2f}", border=1, align='R', ln=True)
                
            if descuento > 0:
                pdf.set_text_color(200, 0, 0)
                pdf.cell(90, 8, limpiar("Descuento Automático por Adelanto"), border=1)
                pdf.cell(38, 8, f"-${descuento:,.2f}", border=1, align='R', ln=True)
                
            pdf.set_font("Arial", 'B', 11)
            pdf.set_text_color(0, 128, 0)
            pdf.cell(90, 8, "TOTAL NETO A PAGAR", border=1)
            pdf.cell(38, 8, f"${total:,.2f}", border=1, align='R', ln=True)
            
            pdf.ln(25)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", '', 10)
            y_firmas = pdf.get_y()
            
            pdf.line(15, y_firmas, 65, y_firmas)
            pdf.set_xy(15, y_firmas + 2)
            pdf.cell(50, 5, "Firma del Empleador (Sello)", align='C')
            
            pdf.line(80, y_firmas, 130, y_firmas)
            pdf.set_xy(80, y_firmas + 2)
            pdf.cell(50, 5, "Firma del Trabajador", align='C')
            
            pdf.output(ruta_guardado)
            if platform.system() == 'Windows': 
                os.startfile(ruta_guardado)
                
        except Exception as e:
            messagebox.showerror("Error Crítico PDF", f"Fallo al construir el recibo:\n{str(e)}")

    def registrar_pago_nomina(self):
        datos = self.calcular_pago_neto()
        if datos and datos[0] is not None:
            total_neto, bono, descuento, emp_id, sueldo_base, horas, valor_hora, deuda_actual = datos
            
            seleccion = self.combo_emp_pago.get()
            if not seleccion or " - " not in seleccion:
                return messagebox.showwarning("Aviso", "Seleccione un empleado válido.")
            
            # --- CORRECCIÓN: Lógica de extracción blindada ---
            partes = seleccion.split(" - ", 2)
            cedula_emp = partes[1] if len(partes) > 1 else "N/A"
            nombre_emp = partes[2] if len(partes) > 2 else "Empleado"
            
            fecha = datetime.now().strftime("%Y-%m-%d")
            desc = f"Pago de nómina: {nombre_emp}"
            if bono > 0: desc += f" | Bono incl: ${bono:,.2f}"
            if descuento > 0: desc += f" | Descuento cobrado: -${descuento:,.2f}"
            hora_actual = datetime.now().strftime("%H:%M:%S")
            
            # Registrar el egreso del pago NETO (solo lo que sale realmente en físico/transferencia)
            self.db.cursor.execute("INSERT INTO transacciones (fecha, tipo, categoria, monto, forma_pago, descripcion, hora, estado, eliminado) VALUES (?, 'Egreso', 'Nómina', ?, 'Transferencia', ?, ?, 'Pagado / Completado', 0)", (fecha, total_neto, desc, hora_actual))
            
            # Si se cobró algo, descontarlo de la base de datos del empleado
            if descuento > 0:
                self.db.cursor.execute("UPDATE empleados SET deuda = deuda - ? WHERE id = ?", (descuento, emp_id))
            
            self.db.conn.commit()
            
            messagebox.showinfo("Éxito", f"Pago de nómina registrado. Deuda pendiente: ${deuda_actual - descuento:,.2f}.")
            
            # Generar Recibo incluyendo el descuento
            self.generar_recibo_nomina_pdf(nombre_emp, cedula_emp, sueldo_base, horas, valor_hora, bono, descuento, total_neto)
            
            self.ent_emp_horas.delete(0, "end"); self.ent_emp_valor_hora.delete(0, "end"); self.ent_emp_bono.delete(0, "end")
            self.actualizar_empleados()
            self.calcular_pago_neto()
            if hasattr(self, 'actualizar_dashboard_data'): self.actualizar_dashboard_data()
            if hasattr(self, 'cargar_tabla_movimientos'): self.cargar_tabla_movimientos()
        else: 
            messagebox.showerror("Error", "Monto a pagar inválido.")
    # ==========================================
    # INVENTARIO
    # ==========================================
    def setup_inventario(self):
        f = ctk.CTkFrame(self.container, fg_color="transparent")
        self.frames["inventario"] = f
        f.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(f, text="INVENTARIO Y CÓDIGOS DE BARRAS", font=("Arial", 24, "bold"), text_color="black").pack(pady=(0, 10))
        
        split_f = ctk.CTkFrame(f, fg_color="transparent")
        split_f.pack(fill="both", expand=True)
        split_f.grid_columnconfigure(0, weight=3) 
        split_f.grid_columnconfigure(1, weight=1) 
        split_f.grid_rowconfigure(0, weight=1)

        left_p = ctk.CTkFrame(split_f, fg_color="transparent")
        left_p.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        buscador_f = ctk.CTkFrame(left_p, fg_color="transparent")
        buscador_f.pack(fill="x", pady=(0, 10))
        self.entry_buscar_inv = ctk.CTkEntry(buscador_f, placeholder_text="🔍 Buscar producto...", height=40, font=("Arial", 12, "bold"))
        self.entry_buscar_inv.pack(side="left", fill="x", expand=True)
        self.entry_buscar_inv.bind("<KeyRelease>", lambda e: self.actualizar_inventario())

        columnas = ("ID", "Código", "Nombre", "Stock", "Costo", "Venta", "Margen")
        self.tabla_inventario = ttk.Treeview(left_p, columns=columnas, show="headings", height=20)
        for col in columnas:
            self.tabla_inventario.heading(col, text=col)
            self.tabla_inventario.column(col, width=90, anchor="center")
        self.tabla_inventario.column("ID", width=0, stretch=False)
        self.tabla_inventario.pack(fill="both", expand=True)
        self.tabla_inventario.bind("<<TreeviewSelect>>", self.mostrar_barcode_seleccionado)

        ctk.CTkButton(left_p, text="🗑️ Mover a Papelera", font=("Arial", 12, "bold"), fg_color=self.rojo_neon, text_color="white", hover_color="#CC0000", command=self.eliminar_producto_inventario).pack(pady=10)

        right_p = ctk.CTkFrame(split_f, fg_color=self.color_card, corner_radius=15)
        right_p.grid(row=0, column=1, sticky="nsew")
        
        ctk.CTkLabel(right_p, text="🏷️ Etiqueta", font=("Arial", 16, "bold"), text_color=self.color_acento).pack(pady=20)
        
        self.empty_barcode_img = ctk.CTkImage(Image.new("RGBA", (250, 100), (0, 0, 0, 0)), size=(250, 100))
        
        self.lbl_barcode_img = ctk.CTkLabel(right_p, text="Seleccione un producto\npara ver su código", font=("Arial", 12, "bold"), text_color="gray", width=250, height=150, corner_radius=10, fg_color="#F4F6F9", image=self.empty_barcode_img)
        self.lbl_barcode_img.pack(pady=20, padx=20)
        
        self.btn_exportar_codigo = ctk.CTkButton(right_p, text="🖨️ Imprimir Etiqueta", font=("Arial", 14, "bold"), fg_color=self.verde_neon, text_color="white", state="disabled", command=self.abrir_etiqueta)
        self.btn_exportar_codigo.pack(pady=10, padx=20, fill="x")
        
        self.codigo_actual_seleccionado = None

    def mostrar_barcode_seleccionado(self, event):
        seleccion = self.tabla_inventario.selection()
        if not seleccion: return
        
        codigo = self.tabla_inventario.item(seleccion[0])["values"][1]
        self.codigo_actual_seleccionado = codigo
        ruta_img = os.path.join(self.db.barcodes_dir, f"{codigo}.png")
        
        if not os.path.exists(ruta_img): 
            self.db.generar_imagen_barcode(codigo)
            
        if os.path.exists(ruta_img):
            imagen_original = Image.open(ruta_img)
            imagen_en_memoria = imagen_original.copy()
            imagen_original.close()
            
            self.current_barcode_img = ctk.CTkImage(light_image=imagen_en_memoria, dark_image=imagen_en_memoria, size=(250, 100))
            self.lbl_barcode_img.configure(image=self.current_barcode_img, text="")
            self.btn_exportar_codigo.configure(state="normal")
        else: 
            self.lbl_barcode_img.configure(image=self.empty_barcode_img, text="Error cargando código")
            self.btn_exportar_codigo.configure(state="disabled")
    
    # --- ACTUALIZADO: Motor de impresión térmica EXTENDIDA (Widescreen) ---
    # --- ACTUALIZADO: Motor de impresión térmica EXTENDIDA (Widescreen) ---
    def abrir_etiqueta(self):
        if self.codigo_actual_seleccionado:
            ruta_img = os.path.join(self.db.barcodes_dir, f"{self.codigo_actual_seleccionado}.png")
            
            if os.path.exists(ruta_img):
                try:
                    from fpdf import FPDF
                    import platform
                    import subprocess
                    from PIL import Image # <-- IMPORTANTE: Lo usamos para leer la imagen original
                    
                    # 1. Traemos la calibración física de TU PANEL SECRETO
                    ancho_mm, alto_mm = self.db.obtener_medidas_etiqueta()
                    
                    # 2. Corrección FPDF
                    lado_corto = min(ancho_mm, alto_mm)
                    lado_largo = max(ancho_mm, alto_mm)
                    orientacion = 'L' if ancho_mm > alto_mm else 'P'
                    
                    pdf = FPDF(orientation=orientacion, unit='mm', format=(lado_corto, lado_largo))
                    pdf.set_margins(0, 0, 0)
                    pdf.set_auto_page_break(auto=False, margin=0) 
                    pdf.add_page()
                    
                    # 3. LECTURA INTELIGENTE DE PROPORCIONES
                    with Image.open(ruta_img) as img:
                        img_w, img_h = img.size
                        
                    # Espacio máximo que podemos usar en el papel (dejando márgenes para que no se caiga)
                    max_w = ancho_mm * 0.90
                    max_h = alto_mm - 4.0 
                    
                    # Calculamos el factor de escala matemático para NO aplastar ni cortar la imagen
                    ratio = min(max_w / img_w, max_h / img_h)
                    
                    # Medidas perfectas finales
                    final_w = img_w * ratio
                    final_h = img_h * ratio
                    
                    # 4. Centrado absoluto
                    x_center = (ancho_mm - final_w) / 2.0
                    y_center = (alto_mm - final_h) / 2.0
                    
                    # 5. Inyectamos la imagen con ALTO y ANCHO exactos calculados matemáticamente
                    pdf.image(ruta_img, x=x_center, y=y_center, w=final_w, h=final_h)
                    
                    # 6. Guardado y apertura
                    nombre_archivo = f"E_{self.codigo_actual_seleccionado}.pdf"
                    ruta_pdf = os.path.join(self.db.tickets_dir, nombre_archivo)
                    pdf.output(ruta_pdf)
                    
                    if platform.system() == 'Windows':
                        os.startfile(ruta_pdf)
                    elif platform.system() == 'Darwin':
                        subprocess.call(('open', ruta_pdf))
                    else:
                        subprocess.call(('xdg-open', ruta_pdf))
                        
                except Exception as e:
                    messagebox.showerror("Error Térmico", f"Fallo en la calibración/impresión del código:\n{e}")
            else:
                messagebox.showerror("Archivo no encontrado", "Primero debe generarse el PNG del código seleccionando el producto.")

    def actualizar_inventario(self):
        for item in self.tabla_inventario.get_children(): self.tabla_inventario.delete(item)
        
        texto_busqueda = ""
        if hasattr(self, 'entry_buscar_inv'):
            texto_busqueda = self.entry_buscar_inv.get().strip()

        if texto_busqueda:
            df = self.db.buscar_productos(texto_busqueda)
        else:
            df = self.db.obtener_productos()

        for _, r in df.iterrows():
            c_adq = r['precio_adquisicion']
            p_ven = r['precio_venta']
            if c_adq > 0: margen = ((p_ven - c_adq) / c_adq) * 100
            elif p_ven > 0: margen = 100.0
            else: margen = 0.0
            self.tabla_inventario.insert("", "end", values=(r["id"], r["codigo"], r["nombre"], r["stock"], f"${c_adq:,.2f}", f"${p_ven:,.2f}", f"{margen:.1f}%"))

    def eliminar_producto_inventario(self):
        seleccion = self.tabla_inventario.selection()
        if not seleccion: return messagebox.showwarning("Aviso", "Selecciona un producto.")
        if messagebox.askyesno("Confirmar", "¿Enviar producto a la papelera?"):
            self.db.soft_delete("productos", self.tabla_inventario.item(seleccion[0])["values"][0])
            self.actualizar_inventario(); self.actualizar_combos_ingreso()

    # ==========================================
    # GESTIÓN DE ENTRADAS
    # ==========================================
    def setup_ingreso_mercancia(self):
        f = ctk.CTkFrame(self.container, fg_color=self.color_card, corner_radius=20)
        self.frames["ing_merc"] = f
        f.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(f, text="GESTIÓN DE ENTRADAS", font=("Arial", 24, "bold"), text_color=self.rojo_neon).pack(pady=(20, 10))
        self.tab_ingreso = ctk.CTkTabview(f, width=800, height=540, segmented_button_selected_color="#D1D5DB")
        self.tab_ingreso.pack(pady=10, padx=20, fill="both")
        self.tab_ingreso.add("Restock (Sumar a existente)")
        self.tab_ingreso.add("Crear Producto Nuevo")

        f_restock = self.tab_ingreso.tab("Restock (Sumar a existente)")
        self.entry_scan_restock = ctk.CTkEntry(f_restock, placeholder_text="📟 Escanear código...", width=400, height=45, font=("Arial", 12, "bold"))
        self.entry_scan_restock.pack(pady=10)
        self.combo_restock = ctk.CTkComboBox(f_restock, width=400, height=45, font=("Arial", 12, "bold"))
        self.combo_restock.pack(pady=10)
        
        precios_frame_restock = ctk.CTkFrame(f_restock, fg_color="transparent")
        precios_frame_restock.pack(pady=5)
        self.entry_restock_precio_adq = ctk.CTkEntry(precios_frame_restock, placeholder_text="Costo Adq. ($)", width=195, height=45, font=("Arial", 12, "bold"))
        self.entry_restock_precio_adq.grid(row=0, column=0, padx=5)
        self.entry_restock_precio_venta = ctk.CTkEntry(precios_frame_restock, placeholder_text="Precio Venta ($)", width=195, height=45, font=("Arial", 12, "bold"))
        self.entry_restock_precio_venta.grid(row=0, column=1, padx=5)
        self.entry_restock_cant = ctk.CTkEntry(f_restock, placeholder_text="Cantidad a ingresar", width=400, height=45, font=("Arial", 12, "bold"))
        self.entry_restock_cant.pack(pady=10)
        self.entry_restock_cant.bind("<Return>", lambda e: self.ejecutar_restock()) # <-- ATAJO AÑADIDO
        ctk.CTkButton(f_restock, text="ACTUALIZAR STOCK", width=400, height=50, fg_color=self.verde_neon, text_color="white", font=("Arial", 16, "bold"), command=self.ejecutar_restock).pack(pady=15)

        f_nuevo = self.tab_ingreso.tab("Crear Producto Nuevo")
        self.entry_prod_codigo = ctk.CTkEntry(f_nuevo, placeholder_text="Código (Vacío = auto)", width=400, height=45, font=("Arial", 12, "bold"))
        self.entry_prod_codigo.pack(pady=10)
        self.entry_prod_nombre = ctk.CTkEntry(f_nuevo, placeholder_text="Nombre del nuevo producto", width=400, height=45, font=("Arial", 12, "bold"))
        self.entry_prod_nombre.pack(pady=10)
        self.entry_prod_stock = ctk.CTkEntry(f_nuevo, placeholder_text="Stock inicial", width=400, height=45, font=("Arial", 12, "bold"))
        self.entry_prod_stock.pack(pady=10)
        
        precios_frame_nuevo = ctk.CTkFrame(f_nuevo, fg_color="transparent")
        precios_frame_nuevo.pack(pady=5)
        self.entry_prod_precio_adq = ctk.CTkEntry(precios_frame_nuevo, placeholder_text="Costo Adq. ($)", width=195, height=45, font=("Arial", 12, "bold"))
        self.entry_prod_precio_adq.grid(row=0, column=0, padx=5)
        self.entry_prod_precio_venta = ctk.CTkEntry(precios_frame_nuevo, placeholder_text="Precio Venta ($)", width=195, height=45, font=("Arial", 12, "bold"))
        self.entry_prod_precio_venta.grid(row=0, column=1, padx=5)
        self.entry_prod_precio_venta.bind("<Return>", lambda e: self.registrar_producto()) # <-- ATAJO AÑADIDO
        ctk.CTkButton(f_nuevo, text="REGISTRAR NUEVO", width=400, height=50, fg_color=self.color_acento, text_color="white", font=("Arial", 16, "bold"), command=self.registrar_producto).pack(pady=15)

    def actualizar_combos_ingreso(self):
        df = self.db.obtener_productos()
        valores = [f"{r['codigo']} - {r['nombre']} (Actual: {r['stock']})" for _, r in df.iterrows()]
        self.combo_restock.configure(values=valores)
        if valores: self.combo_restock.set(valores[0])

    def ejecutar_restock(self):
        try:
            seleccion = self.combo_restock.get()
            if not seleccion: return
            codigo = seleccion.split(" - ")[0]
            cantidad = int(self.entry_restock_cant.get())
            p_adq = float(self.entry_restock_precio_adq.get()) if self.entry_restock_precio_adq.get() else 0.0
            p_venta = float(self.entry_restock_precio_venta.get()) if self.entry_restock_precio_venta.get() else 0.0
            
            # Extraemos el producto completo para usar su nombre en la descripción
            fila_prod = self.db.obtener_productos()[self.db.obtener_productos()["codigo"] == codigo].iloc[0]
            p_id = int(fila_prod["id"])
            nombre_prod = str(fila_prod["nombre"])
            
            self.db.actualizar_stock_y_precios(p_id, cantidad, p_adq, p_venta)
            
            total_compra = cantidad * p_adq
            if total_compra > 0:
                if messagebox.askyesno("Debitar Automáticamente", f"El costo de este restock es de ${total_compra:,.2f}.\n¿Desea debitar este monto automáticamente de sus cuentas?"):
                    fecha = datetime.now().strftime("%Y-%m-%d")
                    hora = datetime.now().strftime("%H:%M:%S")
                    self.db.cursor.execute("""
                        INSERT INTO transacciones (fecha, tipo, categoria, monto, forma_pago, descripcion, hora, estado, caja, eliminado)
                        VALUES (?, 'Egreso', 'Compra de Mercancía', ?, 'Efectivo', ?, ?, 'Pagado / Completado', 'Caja Principal', 0)
                    """, (fecha, total_compra, f"Ingreso automático de stock: {nombre_prod}", hora))
                    self.db.conn.commit()

            messagebox.showinfo("Éxito", "Stock actualizado correctamente.")
            
            self.entry_restock_cant.delete(0, 'end')
            self.entry_restock_precio_adq.delete(0, 'end')
            self.entry_restock_precio_venta.delete(0, 'end')
            
            self.actualizar_combos_ingreso()
            if hasattr(self, 'pos_window') and self.pos_window.winfo_exists(): self.cargar_productos_combo_pos()
        except: messagebox.showerror("Error", "Datos inválidos.")

    def registrar_producto(self):
        try:
            nombre, codigo_ingresado = self.entry_prod_nombre.get().strip(), self.entry_prod_codigo.get().strip()
            stock = int(self.entry_prod_stock.get()) if self.entry_prod_stock.get() else 0
            p_adq = float(self.entry_prod_precio_adq.get()) if self.entry_prod_precio_adq.get() else 0.0
            p_venta = float(self.entry_prod_precio_venta.get()) if self.entry_prod_precio_venta.get() else 0.0
            
            if not nombre or stock < 0: raise ValueError
            codigo_final = self.db.crear_producto(nombre, stock, codigo_ingresado, p_adq, p_venta)
            
            total_compra = stock * p_adq
            if total_compra > 0:
                if messagebox.askyesno("Debitar Automáticamente", f"El costo inicial de este inventario es de ${total_compra:,.2f}.\n¿Desea debitar este monto automáticamente de sus cuentas?"):
                    fecha = datetime.now().strftime("%Y-%m-%d")
                    hora = datetime.now().strftime("%H:%M:%S")
                    self.db.cursor.execute("""
                        INSERT INTO transacciones (fecha, tipo, categoria, monto, forma_pago, descripcion, hora, estado, caja, eliminado)
                        VALUES (?, 'Egreso', 'Compra de Mercancía', ?, 'Efectivo', ?, ?, 'Pagado / Completado', 'Caja Principal', 0)
                    """, (fecha, total_compra, f"Registro inicial de inventario: {nombre}", hora))
                    self.db.conn.commit()
            
            messagebox.showinfo("Éxito", f"Producto '{nombre}' registrado correctamente.")
            self.entry_prod_nombre.delete(0, 'end'); self.entry_prod_codigo.delete(0, 'end')
            self.entry_prod_stock.delete(0, 'end'); self.entry_prod_precio_adq.delete(0, 'end')
            self.entry_prod_precio_venta.delete(0, 'end')
            self.actualizar_combos_ingreso()
        except Exception as e: messagebox.showerror("Error", f"Verifique los datos: {e}")

    # ==========================================
    # TERMÓMETRO (RESTAURADO Y ADAPTADO)
    # ==========================================
    def setup_termometro(self):
        f = ctk.CTkFrame(self.container, fg_color=self.color_card, corner_radius=20)
        self.frames["termometro"] = f
        f.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(f, text="TERMÓMETRO FINANCIERO", font=("Arial", 24, "bold"), text_color="black").pack(pady=(20, 10))
        form_meta = ctk.CTkFrame(f, fg_color="transparent")
        form_meta.pack(pady=10)
        self.var_tipo_meta = ctk.StringVar(value="Meta de Ingresos")
        ctk.CTkOptionMenu(form_meta, values=["Meta de Ingresos", "Límite de Egresos"], variable=self.var_tipo_meta, font=("Arial", 12, "bold"), command=self.actualizar_cat_termometro).grid(row=0, column=0, padx=10, pady=10)
        self.combo_cat_meta = ctk.CTkComboBox(form_meta, values=self.cats_ingreso, width=200, font=("Arial", 12, "bold"))
        self.combo_cat_meta.grid(row=0, column=1, padx=10, pady=10)
        self.ent_monto_meta = ctk.CTkEntry(form_meta, placeholder_text="Monto ($)", width=150, font=("Arial", 12, "bold"))
        self.ent_monto_meta.grid(row=0, column=2, padx=10, pady=10)
        self.ent_monto_meta.bind("<Return>", lambda e: self.guardar_meta()) # <-- ATAJO AÑADIDO
        ctk.CTkButton(form_meta, text="Establecer Meta", font=("Arial", 12, "bold"), text_color="white", fg_color=self.color_acento, command=self.guardar_meta).grid(row=0, column=3, padx=10, pady=10)
        self.scroll_termometos = ctk.CTkScrollableFrame(f, width=800, height=500, fg_color="transparent")
        self.scroll_termometos.pack(pady=20, fill="both", expand=True)

    def actualizar_cat_termometro(self, valor):
        cats = self.cats_ingreso if valor == "Meta de Ingresos" else self.cats_egreso
        self.combo_cat_meta.configure(values=cats)
        self.combo_cat_meta.set(cats[0])

    def guardar_meta(self):
        try:
            monto = float(self.ent_monto_meta.get())
            if monto > 0:
                self.db.crear_meta(self.combo_cat_meta.get(), "Ingreso" if self.var_tipo_meta.get() == "Meta de Ingresos" else "Egreso", monto)
                self.ent_monto_meta.delete(0, "end")
                self.renderizar_termometros()
            else: messagebox.showerror("Error", "El monto debe ser mayor a cero.")
        except: messagebox.showerror("Error", "Monto inválido.")

    def renderizar_termometros(self):
        for w in self.scroll_termometos.winfo_children(): w.destroy()
        df_metas = self.db.obtener_metas()
        if df_metas.empty:
            ctk.CTkLabel(self.scroll_termometos, text="Aún no has establecido metas.", font=("Arial", 12, "bold"), text_color="gray").pack(pady=20)
            return
        df_trans = self.db.obtener_todas_transacciones()
        for _, meta in df_metas.iterrows():
            total_actual = df_trans[(df_trans["categoria"] == meta["categoria"]) & (df_trans["tipo"] == meta["tipo"])]["monto"].sum() if not df_trans.empty else 0
            porcentaje = min((total_actual / meta["monto_meta"]), 1.0) if meta["monto_meta"] > 0 else 0
            card = ctk.CTkFrame(self.scroll_termometos, fg_color="#F4F6F9", corner_radius=10, border_width=1, border_color="#E4E6EB")
            card.pack(fill="x", pady=10, padx=10, ipady=10)
            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=15, pady=(10, 5))
            ctk.CTkLabel(top, text=f"{'🏆 META: ' if meta['tipo'] == 'Ingreso' else '🛑 LÍMITE: '}{meta['categoria']}", font=("Arial", 16, "bold"), text_color="black").pack(side="left")
            ctk.CTkButton(top, text="X", width=30, height=30, font=("Arial", 12, "bold"), fg_color=self.rojo_neon, text_color="white", command=lambda i=meta["id"]: self.eliminar_y_recargar_meta(i)).pack(side="right")
            color_barra = self.verde_neon if meta["tipo"] == "Ingreso" else (self.rojo_neon if porcentaje >= 1.0 else "#FFA500")
            bar = ctk.CTkProgressBar(card, width=600, height=15, progress_color=color_barra)
            bar.pack(padx=15, pady=5)
            bar.set(porcentaje)
            ctk.CTkLabel(card, text=f"Actual: ${total_actual:,.2f} / Objetivo: ${meta['monto_meta']:,.2f}", font=("Arial", 12, "bold"), text_color="#666666").pack(anchor="w", padx=15)

    def eliminar_y_recargar_meta(self, meta_id):
        self.db.eliminar_meta(meta_id)
        self.renderizar_termometros()

    # ==========================================
    # ANÁLISIS DE VELAS (RESTAURADO Y ADAPTADO)
    # ==========================================
    def setup_velas(self):
        f = ctk.CTkFrame(self.container, fg_color=self.color_card, corner_radius=20)
        self.frames["velas"] = f
        f.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(f, text="ANÁLISIS DE VELAS (CATEGORÍAS)", font=("Arial", 24, "bold"), text_color="black").pack(pady=(20, 10))
        self.canvas_frame_velas = ctk.CTkFrame(f, fg_color="transparent")
        self.canvas_frame_velas.pack(fill="both", expand=True, padx=20, pady=20)

    def generar_grafico_velas(self):
        for w in self.canvas_frame_velas.winfo_children(): w.destroy()
        df = self.db.obtener_todas_transacciones()
        if df.empty: return
        
        plt.close('all') # --- BLINDAJE: Limpia la memoria gráfica ---
        
        resumen = df.groupby(["tipo", "categoria"])["monto"].sum().reset_index()
        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor(self.color_card)
        ax.set_facecolor(self.color_card)
        colores = [self.verde_neon if t == "Ingreso" else self.rojo_neon for t in resumen["tipo"]]
        ax.bar(resumen["categoria"].astype(str).str[:12], resumen["monto"], color=colores)
        ax.tick_params(colors="black", labelsize=8)
        for spine in ax.spines.values(): spine.set_color("#CCCCCC")
        canvas = FigureCanvasTkAgg(fig, master=self.canvas_frame_velas)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # ==========================================
    # RENDIMIENTO ACUMULADO (RESTAURADO Y ADAPTADO)
    # ==========================================
    def setup_rendimiento(self):
        f = ctk.CTkFrame(self.container, fg_color=self.color_card, corner_radius=20)
        self.frames["rendimiento"] = f
        f.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(f, text="RENDIMIENTO HISTÓRICO ACUMULADO", font=("Arial", 24, "bold"), text_color="black").pack(pady=(20, 10))
        ctk.CTkLabel(f, text="(Ingresos vs Egresos a lo largo del tiempo)", font=("Arial", 12, "bold"), text_color="gray").pack(pady=(0, 10))
        self.canvas_frame_rendimiento = ctk.CTkFrame(f, fg_color="transparent")
        self.canvas_frame_rendimiento.pack(fill="both", expand=True, padx=20, pady=20)

    def generar_grafico_rendimiento(self):
        for w in self.canvas_frame_rendimiento.winfo_children(): w.destroy()
        df = self.db.obtener_todas_transacciones()
        if df.empty: 
            ctk.CTkLabel(self.canvas_frame_rendimiento, text="No hay suficientes datos para graficar.", font=("Arial", 12, "bold"), text_color="gray").pack(pady=50)
            return

        plt.close('all') # --- BLINDAJE: Limpia la memoria gráfica ---

        df['monto_real'] = df.apply(lambda row: row['monto'] if row['tipo'] == 'Ingreso' else -row['monto'], axis=1)
        df['fecha'] = pd.to_datetime(df['fecha'])
        resumen = df.groupby(df['fecha'].dt.to_period('M'))['monto_real'].sum().reset_index()
        resumen['fecha_str'] = resumen['fecha'].astype(str)
        resumen['acumulado'] = resumen['monto_real'].cumsum()

        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor(self.color_card)
        ax.set_facecolor(self.color_card)

        x = range(len(resumen['fecha_str']))
        y = resumen['acumulado']

        ax.plot(x, y, color="black", linewidth=1.5)
        ax.fill_between(x, y, 0, where=(y >= 0), color=self.verde_neon, alpha=0.3, interpolate=True)
        ax.fill_between(x, y, 0, where=(y < 0), color=self.rojo_neon, alpha=0.3, interpolate=True)

        ax.set_xticks(x)
        ax.set_xticklabels(resumen['fecha_str'], rotation=45, ha="right", color="black")
        ax.tick_params(colors="black", labelsize=10)
        
        ax.grid(color='#E0E0E0', linestyle='--', linewidth=0.5)

        for spine in ax.spines.values(): 
            spine.set_color("#CCCCCC")

        plt.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.canvas_frame_rendimiento)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # ==========================================
    # PAPELERA DE RECICLAJE (RESTAURADA Y ADAPTADA)
    # ==========================================
    def setup_papelera(self):
        f = ctk.CTkFrame(self.container, fg_color="transparent")
        self.frames["papelera"] = f
        f.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(f, text="♻️ PAPELERA DE RECICLAJE", font=("Arial", 24, "bold"), text_color="black").pack(pady=(0, 10))
        
        self.tab_papelera = ctk.CTkTabview(f, width=800, height=600, segmented_button_selected_color="#D1D5DB")
        self.tab_papelera.pack(pady=10, fill="both", expand=True)
        
        self.tab_papelera.add("Transacciones Eliminadas")
        self.tab_papelera.add("Productos Eliminados")
        self.tab_papelera.add("Clientes Eliminados")

        col_t = ("ID", "Fecha", "Tipo", "Monto", "Descripción")

        self.tabla_pap_trans = ttk.Treeview(self.tab_papelera.tab("Transacciones Eliminadas"), columns=col_t, show="headings", height=15)
        for c in col_t: 
            self.tabla_pap_trans.heading(c, text=c)
        self.tabla_pap_trans.column("ID", width=0, stretch=False)
        self.tabla_pap_trans.pack(fill="both", expand=True, pady=10)
        
        btn_frame_t = ctk.CTkFrame(self.tab_papelera.tab("Transacciones Eliminadas"), fg_color="transparent")
        btn_frame_t.pack(pady=10)
        ctk.CTkButton(btn_frame_t, text="🔄 Restaurar Transacción", font=("Arial", 12, "bold"), fg_color=self.verde_neon, text_color="white", command=lambda: self.restaurar_item("transacciones", self.tabla_pap_trans)).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame_t, text="❌ Eliminar Permanentemente", font=("Arial", 12, "bold"), fg_color=self.rojo_neon, text_color="white", command=lambda: self.eliminar_definitivo_item("transacciones", self.tabla_pap_trans)).pack(side="left", padx=10)

        col_p = ("ID", "Código", "Nombre")
        self.tabla_pap_prod = ttk.Treeview(self.tab_papelera.tab("Productos Eliminados"), columns=col_p, show="headings", height=15)
        for c in col_p: 
            self.tabla_pap_prod.heading(c, text=c)
        self.tabla_pap_prod.column("ID", width=0, stretch=False)
        self.tabla_pap_prod.pack(fill="both", expand=True, pady=10)
        
        btn_frame_p = ctk.CTkFrame(self.tab_papelera.tab("Productos Eliminados"), fg_color="transparent")
        btn_frame_p.pack(pady=10)
        
        ctk.CTkButton(btn_frame_p, text="🔄 Restaurar Producto", font=("Arial", 12, "bold"), fg_color=self.verde_neon, text_color="white", command=lambda: self.restaurar_item("productos", self.tabla_pap_prod)).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame_p, text="❌ Eliminar Permanentemente", font=("Arial", 12, "bold"), fg_color=self.rojo_neon, text_color="white", command=lambda: self.eliminar_definitivo_item("productos", self.tabla_pap_prod)).pack(side="left", padx=10)

        # Tabla de Clientes en la papelera
        col_c = ("ID", "RIF", "Nombre")
        self.tabla_pap_cli = ttk.Treeview(self.tab_papelera.tab("Clientes Eliminados"), columns=col_c, show="headings", height=15)
        for c in col_c: self.tabla_pap_cli.heading(c, text=c)
        self.tabla_pap_cli.column("ID", width=0, stretch=False)
        self.tabla_pap_cli.pack(fill="both", expand=True, pady=10)

        btn_frame_c = ctk.CTkFrame(self.tab_papelera.tab("Clientes Eliminados"), fg_color="transparent")
        btn_frame_c.pack(pady=10)
        ctk.CTkButton(btn_frame_c, text="🔄 Restaurar Cliente", font=("Arial", 12, "bold"), fg_color=self.verde_neon, text_color="white", command=lambda: self.restaurar_item("clientes", self.tabla_pap_cli)).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame_c, text="❌ Eliminar Permanentemente", font=("Arial", 12, "bold"), fg_color=self.rojo_neon, text_color="white", command=lambda: self.eliminar_definitivo_item("clientes", self.tabla_pap_cli)).pack(side="left", padx=10)

    def cargar_papelera(self):
        for item in self.tabla_pap_trans.get_children(): self.tabla_pap_trans.delete(item)
        for item in self.tabla_pap_prod.get_children(): self.tabla_pap_prod.delete(item)
        if hasattr(self, 'tabla_pap_cli'):
            for item in self.tabla_pap_cli.get_children(): self.tabla_pap_cli.delete(item)

        for _, r in self.db.obtener_transacciones_eliminadas().iterrows():
            self.tabla_pap_trans.insert("", "end", values=(r["id"], r["fecha"], r["tipo"], f"${r['monto']:,.2f}", r["descripcion"]))

        for _, r in self.db.obtener_productos_eliminados().iterrows():
            self.tabla_pap_prod.insert("", "end", values=(r["id"], r["codigo"], r["nombre"]))
            
        for _, r in self.db.obtener_clientes_eliminados().iterrows():
            self.tabla_pap_cli.insert("", "end", values=(r["id"], r["rif"], r["nombre"]))
        

    def restaurar_item(self, tabla, treeview):
        seleccion = treeview.selection()
        if not seleccion: return messagebox.showwarning("Aviso", "Selecciona al menos un registro para restaurar.")
        
        for item in seleccion:
            item_id = treeview.item(item)["values"][0]
            self.db.restaurar_registro(tabla, item_id)
            
        messagebox.showinfo("Restaurado", f"{len(seleccion)} registro(s) restaurado(s) exitosamente.")
        self.cargar_papelera()
        self.actualizar_dashboard_data()
        self.cargar_tabla_movimientos()
        self.actualizar_inventario()
        if hasattr(self, 'cargar_tabla_clientes'): self.cargar_tabla_clientes() 
        if hasattr(self, 'actualizar_combos_mayor'): self.actualizar_combos_mayor()

    def eliminar_definitivo_item(self, tabla, treeview):
        seleccion = treeview.selection()
        if not seleccion: 
            return messagebox.showwarning("Aviso", "Selecciona al menos un registro para eliminar.")
        
        if messagebox.askyesno("Advertencia Crítica", f"⚠️ Esta acción es IRREVERSIBLE.\n\n¿Estás seguro de eliminar {len(seleccion)} registro(s) para siempre?"):
            errores = 0
            for item in seleccion:
                item_id = treeview.item(item)["values"][0]
                try:
                    self.db.eliminar_permanente(tabla, item_id)
                except sqlite3.IntegrityError:
                    errores += 1
                    
            if errores > 0:
                messagebox.showwarning("Bloqueo de Seguridad", f"Se eliminaron los registros permitidos, pero {errores} no pudieron borrarse por estar vinculados a facturas (motivos contables).")
            else:
                messagebox.showinfo("Eliminado", f"{len(seleccion)} registro(s) eliminado(s) definitivamente.")
            
            self.cargar_papelera()

    # ==========================================
    # --- MÓDULO RESUMEN FINANCIERO DINÁMICO ---
    # ==========================================
    def setup_resumen_mensual(self): 
        f = ctk.CTkFrame(self.container, fg_color="transparent")
        self.frames["mensual"] = f
        f.grid(row=0, column=0, sticky="nsew")

        top_f = ctk.CTkFrame(f, fg_color="transparent")
        top_f.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(top_f, text="📊 RESUMEN FINANCIERO", font=("Arial", 24, "bold"), text_color="black").pack(side="left")
        
        ctk.CTkButton(top_f, text="📄 Exportar Resumen a PDF", font=("Arial", 12, "bold"), fg_color=self.verde_neon, text_color="white", command=self.exportar_resumen_pdf).pack(side="right", padx=10)

        filtros_f = ctk.CTkFrame(f, fg_color=self.color_card, corner_radius=10)
        filtros_f.pack(fill="x", pady=5, ipady=5)

        ctk.CTkLabel(filtros_f, text="Ver por:", font=("Arial", 14, "bold"), text_color="black").pack(side="left", padx=(15, 5))
        
        self.modo_resumen_var = ctk.StringVar(value="Mensual")
        self.seg_modo_res = ctk.CTkSegmentedButton(filtros_f, values=["Diario", "Mensual", "Anual"], variable=self.modo_resumen_var, command=self.actualizar_periodos_disponibles, font=("Arial", 12, "bold"), selected_color="#D1D5DB", text_color="black")
        self.seg_modo_res.pack(side="left", padx=10)
        
        ctk.CTkLabel(filtros_f, text="Seleccione Período:", font=("Arial", 14, "bold"), text_color="black").pack(side="left", padx=(15, 5))
        
        self.combo_periodo = ctk.CTkComboBox(filtros_f, width=150, font=("Arial", 12, "bold"), command=self.cargar_datos_periodo)
        self.combo_periodo.pack(side="left", padx=10)

        cards_f = ctk.CTkFrame(f, fg_color="transparent")
        cards_f.pack(fill="x", pady=15)
        cards_f.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.card_rm_ing = self.crear_tarjeta(cards_f, "INGRESOS", "$0.00", self.verde_neon, 0)
        self.card_rm_egr = self.crear_tarjeta(cards_f, "EGRESOS", "$0.00", self.rojo_neon, 1)
        self.card_rm_bal = self.crear_tarjeta(cards_f, "BALANCE NETO", "$0.00", "black", 2)

        columnas = ("Fecha", "Tipo", "Categoría", "Monto", "Método", "Concepto")
        self.tabla_rm = ttk.Treeview(f, columns=columnas, show="headings", height=15)
        anchos = {"Fecha": 90, "Tipo": 70, "Categoría": 130, "Monto": 110, "Método": 100, "Concepto": 200}
        for col in columnas:
            self.tabla_rm.heading(col, text=col)
            self.tabla_rm.column(col, width=anchos[col], anchor="center")
            
        self.tabla_rm.tag_configure("ingreso", foreground=self.verde_neon)
        self.tabla_rm.tag_configure("egreso", foreground=self.rojo_neon)
        self.tabla_rm.pack(fill="both", expand=True, pady=10)

    def actualizar_periodos_disponibles(self, *args):
        df = self.db.obtener_todas_transacciones()
        
        if df.empty:
            self.combo_periodo.configure(values=["Sin datos"])
            self.combo_periodo.set("Sin datos")
            self.cargar_datos_periodo("Sin datos")
            return
            
        modo = self.modo_resumen_var.get()
        if modo == "Diario": periodos = sorted(df['fecha'].unique().tolist(), reverse=True)
        elif modo == "Mensual":
            df['periodo'] = df['fecha'].str[:7]
            periodos = sorted(df['periodo'].unique().tolist(), reverse=True)
        elif modo == "Anual":
            df['periodo'] = df['fecha'].str[:4]
            periodos = sorted(df['periodo'].unique().tolist(), reverse=True)
        
        if periodos:
            self.combo_periodo.configure(values=periodos)
            self.combo_periodo.set(periodos[0])
            self.cargar_datos_periodo(periodos[0])
        else:
            self.combo_periodo.configure(values=["Sin datos"])
            self.combo_periodo.set("Sin datos")
            self.cargar_datos_periodo("Sin datos")

    def cargar_datos_periodo(self, periodo_seleccionado):
        for item in self.tabla_rm.get_children(): self.tabla_rm.delete(item)
            
        if periodo_seleccionado == "Sin datos" or not periodo_seleccionado:
            self.card_rm_ing.configure(text="$0.00")
            self.card_rm_egr.configure(text="$0.00")
            self.card_rm_bal.configure(text="$0.00", text_color="black")
            return
            
        df = self.db.obtener_todas_transacciones()
        df_per = df[df['fecha'].str.startswith(periodo_seleccionado)]
        
        if df_per.empty:
            self.card_rm_ing.configure(text="$0.00")
            self.card_rm_egr.configure(text="$0.00")
            self.card_rm_bal.configure(text="$0.00", text_color="black")
            return

        ingresos = df_per[df_per["tipo"] == "Ingreso"]["monto"].sum()
        egresos = df_per[df_per["tipo"] == "Egreso"]["monto"].sum()
        balance = ingresos - egresos
        
        self.card_rm_ing.configure(text=f"${ingresos:,.2f}")
        self.card_rm_egr.configure(text=f"${egresos:,.2f}")
        self.card_rm_bal.configure(text=f"${balance:,.2f}", text_color=self.verde_neon if balance >= 0 else self.rojo_neon)
        
        for _, r in df_per.iterrows():
            tag = "ingreso" if r["tipo"] == "Ingreso" else "egreso"
            str_monto = f"${r['monto']:,.2f}"
            desc = r["descripcion"] if pd.notna(r["descripcion"]) else ""
            
            # Capturamos el método de pago
            metodo_pago = str(r.get("forma_pago", "N/A"))
            
            # Insertamos respetando el nuevo orden (Monto, Método, Concepto)
            self.tabla_rm.insert("", "end", values=(r["fecha"], r["tipo"], r["categoria"], str_monto, metodo_pago, desc), tags=(tag,))

    def exportar_resumen_pdf(self):
        periodo = self.combo_periodo.get()
        modo = self.modo_resumen_var.get()
        
        if periodo == "Sin datos" or not periodo:
            return messagebox.showerror("Error", "No hay datos para exportar.")
            
        df = self.db.obtener_todas_transacciones()
        df_per = df[df['fecha'].str.startswith(periodo)]
        if df_per.empty: return messagebox.showerror("Error", "No hay movimientos.")
            
        try:
            def limpiar(texto): return str(texto).encode('latin-1', 'replace').decode('latin-1')
            from tkinter import filedialog
            ruta_guardado = filedialog.asksaveasfilename(
                defaultextension=".pdf", initialfile=f"Reporte_{modo}_{periodo}.pdf",
                title="Guardar Resumen", filetypes=[("Archivo PDF", "*.pdf")]
            )
            if not ruta_guardado: return
                
            pdf = FPDF(orientation='P', format='A4')
            pdf.add_page()
            
            pdf.set_font("Arial", 'B', 16)
            pdf.set_text_color(0, 128, 96)
            pdf.cell(0, 10, limpiar("REPORTE FINANCIERO - CONTAPY PRO"), ln=True, align='C')
            
            pdf.set_font("Arial", 'B', 12)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 8, limpiar(f"Tipo de Reporte: {modo.upper()}"), ln=True, align='C')
            pdf.cell(0, 8, limpiar(f"Periodo Analizado: {periodo}"), ln=True, align='C')
            pdf.ln(5)
            
            ingresos = df_per[df_per["tipo"] == "Ingreso"]["monto"].sum()
            egresos = df_per[df_per["tipo"] == "Egreso"]["monto"].sum()
            balance = ingresos - egresos

            pdf.set_fill_color(240, 244, 249)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, limpiar(" BALANCE DEL PERIODO"), border=1, ln=True, fill=True)
            pdf.set_font("Arial", '', 11)
            pdf.cell(63, 10, limpiar(f"Ingresos: ${ingresos:,.2f}"), border=1, align='C')
            pdf.cell(63, 10, limpiar(f"Egresos: ${egresos:,.2f}"), border=1, align='C')
            pdf.set_text_color(0, 128, 0 if balance >= 0 else 200)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(64, 10, limpiar(f"Neto: ${balance:,.2f}"), border=1, align='C', ln=True)
            pdf.ln(10)
            
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", 'B', 9)
            pdf.set_fill_color(0, 128, 96)
            # Ancho total 190 en A4 vertical
            anchos = [20, 15, 32, 22, 25, 76] 
            pdf.cell(anchos[0], 8, "Fecha", border=1, fill=True, align='C')
            pdf.cell(anchos[1], 8, "Tipo", border=1, fill=True, align='C')
            pdf.cell(anchos[2], 8, "Categoria", border=1, fill=True, align='C')
            pdf.cell(anchos[3], 8, "Monto ($)", border=1, fill=True, align='C')
            pdf.cell(anchos[4], 8, "Metodo", border=1, fill=True, align='C')
            pdf.cell(anchos[5], 8, "Concepto", border=1, fill=True, align='C', ln=True)

            pdf.set_font("Arial", '', 8)
            for _, r in df_per.iterrows():
                if r['tipo'] == 'Ingreso': pdf.set_text_color(0, 128, 0)
                else: pdf.set_text_color(200, 0, 0)
                
                desc = limpiar(str(r.get('descripcion', '')))
                desc_corta = desc[:50] + "..." if len(desc) > 50 else desc
                cat = limpiar(str(r.get('categoria', '')))
                cat_corta = cat[:18] + "..." if len(cat) > 18 else cat
                metodo_pago = limpiar(str(r.get('forma_pago', 'N/A')))

                pdf.cell(anchos[0], 8, str(r.get('fecha', '')), border=1, align='C')
                pdf.cell(anchos[1], 8, str(r.get('tipo', '')), border=1, align='C')
                pdf.cell(anchos[2], 8, cat_corta, border=1, align='L')
                pdf.cell(anchos[3], 8, f"${float(r.get('monto', 0)):,.2f}", border=1, align='R')
                pdf.cell(anchos[4], 8, metodo_pago, border=1, align='C')
                pdf.cell(anchos[5], 8, desc_corta, border=1, align='L', ln=True)

            pdf.output(ruta_guardado)
            if platform.system() == 'Windows': os.startfile(ruta_guardado)
        except Exception as e:
            messagebox.showerror("Error", f"Falló el PDF:\n{str(e)}")

    def setup_clientes(self):
        f = ctk.CTkFrame(self.container, fg_color="transparent")
        self.frames["clientes"] = f
        f.grid(row=0, column=0, sticky="nsew")

        top_f = ctk.CTkFrame(f, fg_color="transparent")
        top_f.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(top_f, text="👥 GESTIÓN DE CLIENTES B2B", font=("Arial", 24, "bold"), text_color="black").pack(side="left")

        ctk.CTkButton(top_f, text="➕ Nuevo Cliente", font=("Arial", 12, "bold"), fg_color=self.color_acento, text_color="white", command=self.abrir_modal_cliente).pack(side="right", padx=10)
        ctk.CTkButton(top_f, text="🗑️ Eliminar Cliente", font=("Arial", 12, "bold"), fg_color=self.rojo_neon, text_color="white", command=self.eliminar_cliente).pack(side="right", padx=10)

        columnas = ("ID", "RIF", "Razón Social", "Dirección", "Teléfono", "Correo")
        self.tabla_clientes = ttk.Treeview(f, columns=columnas, show="headings", height=18)
        self.tabla_clientes.column("ID", width=0, stretch=False)
        anchos = {"RIF": 100, "Razón Social": 200, "Dirección": 220, "Teléfono": 120, "Correo": 180}
        for col in columnas[1:]:
            self.tabla_clientes.heading(col, text=col)
            self.tabla_clientes.column(col, width=anchos.get(col, 150), anchor="center")
        
        self.tabla_clientes.pack(fill="both", expand=True, pady=10)

    def cargar_tabla_clientes(self):
        for item in self.tabla_clientes.get_children(): self.tabla_clientes.delete(item)
        df = self.db.obtener_clientes()
        if df.empty: return
        for _, r in df.iterrows():
            correo = str(r.get("correo", "N/A"))
            self.tabla_clientes.insert("", "end", values=(r["id"], r["rif"], r["nombre"], r["direccion"], r["telefono"], correo))

    def eliminar_cliente(self):
        seleccion = self.tabla_clientes.selection()
        if not seleccion: return messagebox.showwarning("Aviso", "Selecciona un cliente.")
        try:
            item_id = self.tabla_clientes.item(seleccion[0])["values"][0]
            self.db.soft_delete("clientes", item_id)
            self.cargar_tabla_clientes()
            self.actualizar_combos_mayor()
            messagebox.showinfo("Éxito", "Cliente enviado a la papelera.")
        except Exception as e: 
            messagebox.showerror("Error", str(e))

    def setup_ventas_mayor(self):
        f = ctk.CTkFrame(self.container, fg_color="transparent")
        self.frames["mayor"] = f
        f.grid(row=0, column=0, sticky="nsew")
        
        self.carrito_b2b = []
        
        header_f = ctk.CTkFrame(f, fg_color="transparent")
        header_f.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(header_f, text="VENTAS AL MAYOR (FACTURACIÓN B2B)", font=("Arial", 24, "bold"), text_color="black").pack(side="left")

        client_f = ctk.CTkFrame(f, fg_color=self.color_card, corner_radius=15, border_width=1, border_color="#E4E6EB")
        client_f.pack(fill="x", pady=5, ipady=10)
        
        ctk.CTkLabel(client_f, text="👤 Cliente:", font=("Arial", 14, "bold"), text_color="black").grid(row=0, column=0, padx=20, pady=10, sticky="w")
        self.combo_clientes_b2b = ctk.CTkComboBox(client_f, width=400, height=40, font=("Arial", 12, "bold"))
        self.combo_clientes_b2b.grid(row=0, column=1, padx=10, pady=10)
        
        ctk.CTkButton(client_f, text="➕ Nuevo Cliente", font=("Arial", 12, "bold"), fg_color=self.color_acento, text_color="white", command=self.abrir_modal_cliente).grid(row=0, column=2, padx=10, pady=10)

        split_f = ctk.CTkFrame(f, fg_color="transparent")
        split_f.pack(fill="both", expand=True, pady=10)
        split_f.grid_columnconfigure(1, weight=1)

        left_p = ctk.CTkFrame(split_f, fg_color=self.color_card, width=350, corner_radius=10)
        left_p.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_p.grid_propagate(False)

        ctk.CTkLabel(left_p, text="AGREGAR AL PEDIDO", font=("Arial", 16, "bold"), text_color="black").pack(pady=15)

        self.scan_b2b = ctk.CTkEntry(left_p, placeholder_text="📟 Escanear código...", height=40, width=310, font=("Arial", 12, "bold"))
        self.scan_b2b.pack(pady=(0, 10), padx=20)
        self.scan_b2b.bind("<Return>", self.on_b2b_barcode)
        
        self.combo_prod_b2b = ctk.CTkComboBox(left_p, width=310, height=40, font=("Arial", 12, "bold"))
        self.combo_prod_b2b.pack(pady=10, padx=20)
        
        self.cant_b2b = ctk.CTkEntry(left_p, placeholder_text="Cantidad", height=40, width=310, font=("Arial", 12, "bold"))
        self.cant_b2b.pack(pady=10, padx=20)

        self.cant_b2b.bind("<Return>", lambda e: self.b2b_agregar_carrito())
        
        ctk.CTkButton(left_p, text="⬇️ Añadir a Factura", height=45, width=310, fg_color="#333333", text_color="white", font=("Arial", 14, "bold"), command=self.b2b_agregar_carrito).pack(pady=20, padx=20)

        ctk.CTkButton(left_p, text="📄 EMITIR FACTURA", height=45, width=310, fg_color=self.verde_neon, text_color="white", font=("Arial", 14, "bold"), command=self.procesar_venta_mayor).pack(pady=(10, 20), padx=20)

        right_p = ctk.CTkFrame(split_f, fg_color="transparent")
        right_p.grid(row=0, column=1, sticky="nsew")

        col_c = ("ID", "Código", "Nombre", "Cant", "P.Unit ($)", "Subtotal ($)")
        self.tabla_b2b = ttk.Treeview(right_p, columns=col_c, show="headings", height=8)
        anchos_c = {"ID": 0, "Código": 100, "Nombre": 200, "Cant": 60, "P.Unit ($)": 90, "Subtotal ($)": 100}
        for c in col_c: 
            self.tabla_b2b.heading(c, text=c)
            self.tabla_b2b.column(c, width=anchos_c[c], stretch=True if c == "Nombre" else False, anchor="center")
        self.tabla_b2b.column("ID", width=0, stretch=False)
        self.tabla_b2b.pack(fill="both", expand=True)

        ctk.CTkButton(right_p, text="🗑️ Quitar Ítem", font=("Arial", 12, "bold"), fg_color=self.rojo_neon, text_color="white", hover_color="#CC0000", command=self.b2b_quitar_carrito).pack(anchor="e", pady=5)

        bot_f = ctk.CTkFrame(f, fg_color=self.color_card, corner_radius=10)
        bot_f.pack(fill="x", pady=5, ipady=5)

        box_ajustes_b2b = ctk.CTkFrame(bot_f, fg_color="transparent")
        box_ajustes_b2b.pack(side="left", padx=20)
        
        ctk.CTkLabel(box_ajustes_b2b, text="Descuento a la Factura (%):", font=("Arial", 12, "bold"), text_color="black").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.desc_factura_b2b = ctk.CTkEntry(box_ajustes_b2b, width=80, font=("Arial", 12, "bold"))
        self.desc_factura_b2b.grid(row=0, column=1, padx=5, pady=5)
        self.desc_factura_b2b.insert(0, "0")
        self.desc_factura_b2b.bind("<KeyRelease>", lambda e: self.b2b_actualizar_ui_carrito())

        self.lbl_b2b_totales = ctk.CTkLabel(bot_f, text="Subtotal: $0.00 | IVA (16%): $0.00 | TOTAL: $0.00", font=("Arial", 16, "bold"), text_color=self.verde_neon)
        self.lbl_b2b_totales.pack(side="left", padx=20)

        # Botón del IVA
        self.switch_iva_b2b = ctk.CTkSwitch(bot_f, text="Aplicar IVA (16%)", font=("Arial", 12, "bold"), command=self.b2b_actualizar_ui_carrito)
        self.switch_iva_b2b.select()
        self.switch_iva_b2b.pack(side="left", padx=10)

        metodos_b2b = self.metodos_pago + ["Crédito (Por Cobrar)"]
        
        # --- NUEVO: Métodos de pago duales en B2B ---
        box_pagos_b2b = ctk.CTkFrame(bot_f, fg_color="transparent")
        box_pagos_b2b.pack(side="right", padx=10, pady=5)
        
        self.combo_metodo_b2b = ctk.CTkComboBox(box_pagos_b2b, values=metodos_b2b, width=140, font=("Arial", 11, "bold"))
        self.combo_metodo_b2b.grid(row=0, column=0, padx=4, pady=2)
        
        self.b2b_monto1 = ctk.CTkEntry(box_pagos_b2b, placeholder_text="Monto 1", width=90, font=("Arial", 11, "bold"))
        self.b2b_monto1.grid(row=0, column=1, padx=4, pady=2)
        self.b2b_monto1.bind("<KeyRelease>", self.autocompletar_pago_b2b) # <-- NUEVO: Activa el cálculo automático

        self.combo_metodo_b2b2 = ctk.CTkComboBox(box_pagos_b2b, values=["Ninguno"] + metodos_b2b, width=140, font=("Arial", 11, "bold"))
        self.combo_metodo_b2b2.grid(row=1, column=0, padx=4, pady=2)
        self.combo_metodo_b2b2.set("Ninguno")

        self.b2b_monto2 = ctk.CTkEntry(box_pagos_b2b, placeholder_text="Monto 2", width=90, font=("Arial", 11, "bold"))
        self.b2b_monto2.grid(row=1, column=1, padx=4, pady=2)

    def on_b2b_barcode(self, event=None):
        codigo = self.scan_b2b.get().strip()
        if not codigo: return
        df = self.db.obtener_productos()
        fila = df[df["codigo"] == codigo]
        if not fila.empty:
            r = fila.iloc[0]
            texto_combo = f"{r['codigo']} - {r['nombre']} (Stock: {r['stock']} | ${r['precio_venta']})"
            
            valores_actuales = self.combo_prod_b2b.cget("values")
            if texto_combo not in valores_actuales:
                self.combo_prod_b2b.configure(values=list(valores_actuales) + [texto_combo])
            
            self.combo_prod_b2b.set(texto_combo)
            
            # --- NUEVO: Autocompletar cantidad a 1 y agregar directo a la factura ---
            self.cant_b2b.delete(0, "end")
            self.cant_b2b.insert(0, "1")
            self.b2b_agregar_carrito()
            
            # Limpiar y mantener el foco en el escáner para escaneos rápidos y seguidos
            self.scan_b2b.delete(0, "end")
            self.scan_b2b.focus() 
        else: 
            messagebox.showerror("Error", f"No se encontró código: {codigo}")
        
        
    def actualizar_combos_mayor(self):
        df_cli = self.db.obtener_clientes()
        vals_cli = [f"{r['rif']} - {r['nombre']}" for _, r in df_cli.iterrows()]
        self.combo_clientes_b2b.configure(values=vals_cli if vals_cli else ["Sin clientes registrados"])
        if vals_cli: self.combo_clientes_b2b.set(vals_cli[0])
        
        df_prod = self.db.obtener_productos()
        vals_prod = [f"{r['codigo']} - {r['nombre']} (Stock: {r['stock']} | ${r['precio_venta']})" for _, r in df_prod.iterrows()]
        self.combo_prod_b2b.configure(values=vals_prod)
        if vals_prod: self.combo_prod_b2b.set(vals_prod[0])

    # --- NUEVO: Ventana de Registro Histórico de Tasas (Con borrado múltiple) ---
    def abrir_historial_tasas(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Historial de Tasas")
        modal.geometry("420x500") # Hicimos la ventana un poco más ancha y alta
        modal.grab_set()
        
        ctk.CTkLabel(modal, text="📊 Registro Histórico de Tasas", font=("Arial", 16, "bold"), text_color=self.verde_neon).pack(pady=15)
        
        # 1. Agregamos la columna "ID" pero la ocultamos visualmente
        col = ("ID", "Fecha", "Hora", "Tasa (Bs)")
        tabla_t = ttk.Treeview(modal, columns=col, show="headings", height=15)
        for c in col[1:]: # Iteramos saltando el ID para mostrar solo el resto
            tabla_t.heading(c, text=c)
            tabla_t.column(c, anchor="center", width=110)
        tabla_t.column("ID", width=0, stretch=False) # Oculta la columna ID
        tabla_t.pack(fill="both", expand=True, padx=20, pady=10)
        
        # 2. Función interna que carga y recarga las tasas en la tabla
        def cargar_tasas():
            for item in tabla_t.get_children(): tabla_t.delete(item)
            df = self.db.obtener_historial_tasas()
            for _, r in df.iterrows():
                tabla_t.insert("", "end", values=(r["id"], r["fecha"], r["hora"], f"Bs. {r['tasa']:,.2f}"))

        # 3. Función interna conectada al botón para borrar
        def borrar_tasa():
            seleccion = tabla_t.selection()
            if not seleccion: return messagebox.showwarning("Aviso", "Selecciona al menos una tasa.", parent=modal)
            
            if messagebox.askyesno("Confirmar", f"¿Eliminar {len(seleccion)} tasa(s) del historial?", parent=modal):
                for item in seleccion:
                    # Extraemos el ID oculto de la tasa seleccionada
                    t_id = tabla_t.item(item)["values"][0]
                    # La borramos de la base de datos
                    self.db.cursor.execute("DELETE FROM historial_tasas WHERE id = ?", (t_id,))
                self.db.conn.commit()
                cargar_tasas() # Recargamos la tabla visualmente

        # 4. El nuevo botón rojo de eliminar
        ctk.CTkButton(modal, text="🗑️ Eliminar Seleccionadas", fg_color=self.rojo_neon, text_color="white", font=("Arial", 12, "bold"), command=borrar_tasa).pack(pady=(0, 15))
        
        # Llamamos a la función de carga la primera vez que se abre la ventana
        cargar_tasas()

    # ==========================================
    # --- CALCULADORA FLOTANTE DE DIVISAS ---
    # ==========================================
    def abrir_calculadora_divisas(self):
        # Evitar que se abran múltiples ventanas iguales
        if hasattr(self, 'calc_window') and self.calc_window.winfo_exists():
            self.calc_window.focus()
            return

        self.calc_window = ctk.CTkToplevel(self)
        self.calc_window.title("Calculadora Rápida")
        self.calc_window.geometry("320x350")
        # Esto mantiene la calculadora SIEMPRE por encima del sistema
        self.calc_window.attributes("-topmost", True) 
        
        ctk.CTkLabel(self.calc_window, text="🧮 Convertidor a Tasa del Día", font=("Arial", 16, "bold"), text_color=self.verde_neon).pack(pady=(20, 5))
        ctk.CTkLabel(self.calc_window, text=f"Tasa Aplicada: Bs. {self.tasa_actual:,.2f}", font=("Arial", 12, "bold"), text_color="gray").pack(pady=(0, 15))
        
        # Selector de Modo (Switch)
        self.modo_calc = ctk.StringVar(value="USD ➔ BS")
        seg_modo = ctk.CTkSegmentedButton(
            self.calc_window, 
            values=["USD ➔ BS", "BS ➔ USD"], 
            variable=self.modo_calc, 
            command=lambda e: calcular_conversion(), 
            font=("Arial", 12, "bold"), 
            selected_color=self.color_acento
        )
        seg_modo.pack(pady=10, padx=20, fill="x")
        
        # Caja de ingreso del monto
        self.ent_monto_calc = ctk.CTkEntry(self.calc_window, placeholder_text="Ingrese monto...", font=("Arial", 18, "bold"), justify="center", height=45)
        self.ent_monto_calc.pack(pady=10, padx=20, fill="x")
        
        # Resultado en grande
        self.lbl_resultado_calc = ctk.CTkLabel(self.calc_window, text="Bs. 0.00", font=("Arial", 38, "bold"), text_color="black")
        self.lbl_resultado_calc.pack(pady=20)
        
        # Función matemática automática
        def calcular_conversion(event=None):
            try:
                # Permite usar comas o puntos indistintamente
                texto = self.ent_monto_calc.get().replace(",", ".")
                monto = float(texto) if texto else 0.0
                    
                if self.modo_calc.get() == "USD ➔ BS":
                    resultado = monto * self.tasa_actual
                    self.lbl_resultado_calc.configure(text=f"Bs. {resultado:,.2f}", text_color="black")
                else:
                    resultado = monto / self.tasa_actual
                    self.lbl_resultado_calc.configure(text=f"$ {resultado:,.2f}", text_color=self.verde_neon)
            except ValueError:
                self.lbl_resultado_calc.configure(text="Error", text_color=self.rojo_neon)
        
        # El gatillo que calcula mientras escribes
        self.ent_monto_calc.bind("<KeyRelease>", calcular_conversion)
        self.ent_monto_calc.focus() # Pone el cursor directo en la caja

    # --- ACTUALIZADO: VENTANA SECRETA (EASTER EGG + HARDWARE) ---
    def abrir_config_secreta(self, event=None):
        modal = ctk.CTkToplevel(self)
        modal.title("Sistema Base")
        modal.geometry("480x500")
        modal.grab_set()
        
        ctk.CTkLabel(modal, text="⚙️ Configuración del Core (Top Secret)", font=("Arial", 16, "bold"), text_color=self.rojo_neon).pack(pady=(15, 5))
        
        # Implementación del Tabview
        tabs_config = ctk.CTkTabview(modal, width=420, height=350, segmented_button_selected_color=self.color_acento)
        tabs_config.pack(pady=5, padx=20, fill="both", expand=True)
        
        tabs_config.add("Datos de Facturación")
        tabs_config.add("Hardware y Etiquetas")
        
        # --- TAB 1: Facturación ---
        tab_fact = tabs_config.tab("Datos de Facturación")
        n, r, d = self.db.obtener_datos_empresa()
        
        ctk.CTkLabel(tab_fact, text="Nombre de la Empresa:", font=("Arial", 12, "bold")).pack(anchor="w", padx=15, pady=(10, 0))
        e_nom = ctk.CTkEntry(tab_fact, width=380, font=("Arial", 12, "bold"))
        e_nom.pack(pady=(0, 10))
        e_nom.insert(0, n)
        
        ctk.CTkLabel(tab_fact, text="RIF / Identificación:", font=("Arial", 12, "bold")).pack(anchor="w", padx=15)
        e_rif = ctk.CTkEntry(tab_fact, width=380, font=("Arial", 12, "bold"))
        e_rif.pack(pady=(0, 10))
        e_rif.insert(0, r)
        
        ctk.CTkLabel(tab_fact, text="Dirección (Usa Enter para saltos):", font=("Arial", 12, "bold")).pack(anchor="w", padx=15)
        t_dir = ctk.CTkTextbox(tab_fact, width=380, height=80, font=("Arial", 12))
        t_dir.pack(pady=(0, 10))
        t_dir.insert("1.0", d)
        
        # --- TAB 2: Hardware Térmico ---
        tab_hard = tabs_config.tab("Hardware y Etiquetas")
        ancho_act, alto_act = self.db.obtener_medidas_etiqueta()
        
        ctk.CTkLabel(tab_hard, text="Calibración de Impresión", font=("Arial", 15, "bold"), text_color=self.color_acento).pack(pady=(15, 10))
        ctk.CTkLabel(tab_hard, text="Define las medidas físicas exactas de las etiquetas\ninstaladas en tu impresora térmica.", font=("Arial", 11, "bold"), text_color="gray", justify="center").pack(pady=(0, 15))
        
        ctk.CTkLabel(tab_hard, text="Ancho de la etiqueta (mm):", font=("Arial", 12, "bold")).pack(anchor="w", padx=15)
        e_ancho = ctk.CTkEntry(tab_hard, width=380, font=("Arial", 12, "bold"))
        e_ancho.pack(pady=(0, 15))
        e_ancho.insert(0, str(ancho_act))
        
        ctk.CTkLabel(tab_hard, text="Alto de la etiqueta (mm):", font=("Arial", 12, "bold")).pack(anchor="w", padx=15)
        e_alto = ctk.CTkEntry(tab_hard, width=380, font=("Arial", 12, "bold"))
        e_alto.pack(pady=(0, 10))
        e_alto.insert(0, str(alto_act))
        
        def guardar_secreto():
            try:
                # 1. Extracción y conversión segura de flotantes (admitiendo comas)
                val_ancho = float(e_ancho.get().strip().replace(",", "."))
                val_alto = float(e_alto.get().strip().replace(",", "."))
                
                # 2. Validación obligatoria > 0 para FPDF
                if val_ancho <= 0 or val_alto <= 0:
                    raise ValueError("Las medidas de hardware deben ser positivas.")
                
                # 3. Guardado concurrente en BD
                self.db.actualizar_datos_empresa(e_nom.get().strip(), e_rif.get().strip(), t_dir.get("1.0", "end-1c").strip())
                self.db.actualizar_medidas_etiqueta(val_ancho, val_alto)
                
                messagebox.showinfo("Éxito", "Configuración de sistema y hardware actualizadas en silencio.", parent=modal)
                modal.destroy()
                
            except ValueError:
                messagebox.showerror("Error de Calibración", "Asegúrese de ingresar números válidos y mayores a cero en las medidas de hardware.", parent=modal)
            except Exception as e:
                messagebox.showerror("Error Interno", f"Ocurrió un error inesperado:\n{e}", parent=modal)
                
        ctk.CTkButton(modal, text="Guardar Cambios Maestros", fg_color="#333333", text_color="white", font=("Arial", 13, "bold"), height=40, command=guardar_secreto).pack(pady=15)

    def abrir_modal_cliente(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Nuevo Cliente Comercial")
        modal.geometry("400x500") # Aumentado el tamaño para que quepa el nuevo campo
        modal.grab_set()
        
        ctk.CTkLabel(modal, text="Datos del Cliente", font=("Arial", 18, "bold")).pack(pady=20)
        
        e_rif = ctk.CTkEntry(modal, placeholder_text="RIF o Cédula (Ej: J-123456)", width=300, font=("Arial", 12, "bold"))
        e_rif.pack(pady=10)
        e_nom = ctk.CTkEntry(modal, placeholder_text="Razón Social / Nombre", width=300, font=("Arial", 12, "bold"))
        e_nom.pack(pady=10)
        e_dir = ctk.CTkEntry(modal, placeholder_text="Dirección Fiscal", width=300, font=("Arial", 12, "bold"))
        e_dir.pack(pady=10)
        e_tel = ctk.CTkEntry(modal, placeholder_text="Teléfono", width=300, font=("Arial", 12, "bold"))
        e_tel.pack(pady=10)
        
        # --- NUEVO: Campo de correo añadido ---
        e_correo = ctk.CTkEntry(modal, placeholder_text="Correo Electrónico (Obligatorio)", width=300, font=("Arial", 12, "bold"))
        e_correo.pack(pady=10)
        
        def guardar_cli():
            rif, nom = e_rif.get().strip(), e_nom.get().strip()
            correo = e_correo.get().strip()
            if not rif or not nom or not correo: 
                return messagebox.showerror("Error", "RIF, Nombre y Correo son obligatorios.", parent=modal)
            try:
                self.db.crear_cliente(rif, nom, e_dir.get().strip(), e_tel.get().strip(), correo)
                self.actualizar_combos_mayor()
                if hasattr(self, 'cargar_tabla_clientes'): self.cargar_tabla_clientes()
                modal.destroy()
                messagebox.showinfo("Éxito", "Cliente registrado.")
            except:
                messagebox.showerror("Error", "El RIF ya existe o hubo un error.", parent=modal)
                
        ctk.CTkButton(modal, text="Guardar Cliente", fg_color=self.color_acento, font=("Arial", 14, "bold"), command=guardar_cli).pack(pady=20)

    def b2b_agregar_carrito(self):
        texto = self.combo_prod_b2b.get()
        if not texto: return
        codigo = texto.split(" - ")[0].strip()
        
        df = self.db.obtener_productos()
        fila = df[df["codigo"] == codigo]
        if fila.empty: return
        p = fila.iloc[0]
        
        try: cant_solicitada = int(self.cant_b2b.get())
        except: return messagebox.showerror("Error", "Cantidad inválida.")
        if cant_solicitada <= 0: return messagebox.showerror("Error", "Debe ser mayor a 0.")

        precio_final = float(p['precio_venta'])
        
        stock_disp = int(p['stock'])
        cant_en_carrito = sum([int(item['cant']) for item in self.carrito_b2b if item['id'] == p['id']])
        
        if (cant_en_carrito + cant_solicitada) > stock_disp:
            return messagebox.showerror("❌ Stock Insuficiente", f"Stock: {stock_disp}\nFaltan {(cant_en_carrito + cant_solicitada) - stock_disp} unidades.")

        agregado = False
        for item in self.carrito_b2b:
            if item['id'] == p['id']:
                item['cant'] += cant_solicitada
                item['subtotal'] = item['cant'] * item['p_unit']
                agregado = True
                break
        
        if not agregado:
            self.carrito_b2b.append({
                "id": p['id'], "codigo": p['codigo'], "nombre": p['nombre'],
                "cant": cant_solicitada, "p_unit": float(p['precio_venta']), 
                "subtotal": float(cant_solicitada * p['precio_venta'])
            })
            
        self.cant_b2b.delete(0, "end")
        self.b2b_actualizar_ui_carrito()

    def exportar_resumen_pdf(self):
        periodo = self.combo_periodo.get()
        modo = self.modo_resumen_var.get()
        
        if periodo == "Sin datos" or not periodo:
            return messagebox.showerror("Error", "No hay datos para exportar en este período.")
            
        df = self.db.obtener_todas_transacciones()
        df_per = df[df['fecha'].str.startswith(periodo)]
        
        if df_per.empty:
            return messagebox.showerror("Error", "No hay movimientos registrados en este bloque.")
            
        try:
            def limpiar(texto):
                return str(texto).encode('latin-1', 'replace').decode('latin-1')

            from tkinter import filedialog
            ruta_guardado = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                initialfile=f"Reporte_{modo}_{periodo}.pdf",
                title="Guardar Resumen Financiero",
                filetypes=[("Archivo PDF", "*.pdf")]
            )
            
            if not ruta_guardado: return
                
            # --- NUEVO: Extraemos los datos dinámicos ---
            emp_nombre, _, _ = self.db.obtener_datos_empresa()

            pdf = FPDF(orientation='P', format='A4') # Formato Vertical
            pdf.add_page()
            
            # Encabezado
            pdf.set_font("Arial", 'B', 16)
            pdf.set_text_color(0, 128, 96)
            pdf.cell(0, 10, limpiar(f"REPORTE FINANCIERO - {emp_nombre.upper()}"), ln=True, align='C')
            
            pdf.set_font("Arial", 'B', 12)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 8, limpiar(f"Tipo de Reporte: {modo.upper()}"), ln=True, align='C')
            pdf.cell(0, 8, limpiar(f"Período Analizado: {periodo}"), ln=True, align='C')
            pdf.ln(5)
            
            # Tarjetas de Totales (Cuadro resumen)
            ingresos = df_per[df_per["tipo"] == "Ingreso"]["monto"].sum()
            egresos = df_per[df_per["tipo"] == "Egreso"]["monto"].sum()
            balance = ingresos - egresos

            pdf.set_fill_color(240, 244, 249)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, limpiar(" BALANCE DEL PERÍODO"), border=1, ln=True, fill=True)
            
            pdf.set_font("Arial", '', 11)
            pdf.cell(63, 10, limpiar(f"Ingresos: ${ingresos:,.2f}"), border=1, align='C')
            pdf.cell(63, 10, limpiar(f"Egresos: ${egresos:,.2f}"), border=1, align='C')
            
            pdf.set_text_color(0, 128, 0 if balance >= 0 else 200)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(64, 10, limpiar(f"Neto: ${balance:,.2f}"), border=1, align='C', ln=True)
            pdf.ln(10)
            
            # Cabeceras de la tabla
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", 'B', 9)
            pdf.set_fill_color(0, 128, 96)
            
            # Ancho total en A4 Vertical es aprox 190
            anchos = [25, 20, 35, 25, 85] 
            
            pdf.cell(anchos[0], 8, "Fecha", border=1, fill=True, align='C')
            pdf.cell(anchos[1], 8, "Tipo", border=1, fill=True, align='C')
            pdf.cell(anchos[2], 8, "Categoria", border=1, fill=True, align='C')
            pdf.cell(anchos[3], 8, "Monto ($)", border=1, fill=True, align='C')
            pdf.cell(anchos[4], 8, "Concepto", border=1, fill=True, align='C', ln=True)

            pdf.set_font("Arial", '', 8)
            
            for _, r in df_per.iterrows():
                if r['tipo'] == 'Ingreso':
                    pdf.set_text_color(0, 128, 0)
                else:
                    pdf.set_text_color(200, 0, 0)
                    
                desc = limpiar(str(r.get('descripcion', '')))
                desc_corta = desc[:55] + "..." if len(desc) > 55 else desc
                cat = limpiar(str(r.get('categoria', '')))
                cat_corta = cat[:20] + "..." if len(cat) > 20 else cat

                pdf.cell(anchos[0], 8, str(r.get('fecha', '')), border=1, align='C')
                pdf.cell(anchos[1], 8, str(r.get('tipo', '')), border=1, align='C')
                pdf.cell(anchos[2], 8, cat_corta, border=1, align='L')
                pdf.cell(anchos[3], 8, f"${float(r.get('monto', 0)):,.2f}", border=1, align='R')
                pdf.cell(anchos[4], 8, desc_corta, border=1, align='L', ln=True)

            pdf.output(ruta_guardado)
            
            if platform.system() == 'Windows':
                os.startfile(ruta_guardado)
                
            messagebox.showinfo("Éxito", f"El resumen {modo.lower()} fue exportado a PDF exitosamente.")
            
        except Exception as e:
            messagebox.showerror("Error Interno PDF", f"Falló la creación del PDF:\n\n{str(e)}")

    def b2b_quitar_carrito(self):
        seleccion = self.tabla_b2b.selection()
        if not seleccion: return
        p_id = int(self.tabla_b2b.item(seleccion[0])["values"][0])
        self.carrito_b2b = [item for item in self.carrito_b2b if item['id'] != p_id]
        self.b2b_actualizar_ui_carrito()

    # --- NUEVO: Calcula el monto restante en B2B ---
    def autocompletar_pago_b2b(self, event=None):
        if self.combo_metodo_b2b2.get() != "Ninguno":
            try:
                texto_total = self.lbl_b2b_totales.cget("text")
                total = float(texto_total.split("TOTAL: $")[1].replace(",", ""))
                m1 = float(self.b2b_monto1.get())
                if m1 <= total:
                    self.b2b_monto2.delete(0, "end")
                    self.b2b_monto2.insert(0, f"{(total - m1):.2f}")
            except ValueError:
                pass

    def b2b_actualizar_ui_carrito(self):
        for item in self.tabla_b2b.get_children(): self.tabla_b2b.delete(item)
        subtotal_bruto = 0.0
        for item in self.carrito_b2b:
            self.tabla_b2b.insert("", "end", values=(item["id"], item["codigo"], item["nombre"], item["cant"], f"${item['p_unit']:,.2f}", f"${item['subtotal']:,.2f}"))
            subtotal_bruto += item["subtotal"]

        try: desc_porc = float(self.desc_factura_b2b.get() or 0)
        except: desc_porc = 0.0

        monto_descuento = subtotal_bruto * (desc_porc / 100)
        subtotal_neto = subtotal_bruto - monto_descuento

        aplicar_iva = self.switch_iva_b2b.get() == 1 if hasattr(self, 'switch_iva_b2b') else True
        iva = (subtotal_neto * 0.16) if aplicar_iva else 0.0
        total = subtotal_neto + iva
        
        self.lbl_b2b_totales.configure(text=f"Sub: ${subtotal_bruto:,.2f} | Desc: -${monto_descuento:,.2f} | IVA: ${iva:,.2f} | TOTAL: ${total:,.2f}")
        return subtotal_bruto, monto_descuento, desc_porc, iva, total

    
    def procesar_venta_mayor(self):
        if not self.carrito_b2b: return messagebox.showerror("Error", "El pedido está vacío.")
        cli_texto = self.combo_clientes_b2b.get()
        if "Sin clientes" in cli_texto or not cli_texto: return messagebox.showerror("Error", "Debe seleccionar un cliente.")
        rif_cliente = cli_texto.split(" - ")[0].strip()

        
        # Variables corregidas y sin duplicar
        subtotal_bruto, monto_descuento, desc_porc, iva, total_usd = self.b2b_actualizar_ui_carrito()
        total_bs = total_usd * self.tasa_actual
        
        # --- NUEVA LÓGICA: Pagos Mixtos B2B ---
        m1_t = self.combo_metodo_b2b.get()
        m2_t = self.combo_metodo_b2b2.get()
        
        if m2_t != "Ninguno":
            try:
                v1 = float(self.b2b_monto1.get()) if self.b2b_monto1.get() else total_usd
                v2 = float(self.b2b_monto2.get()) if self.b2b_monto2.get() else 0.0
                if abs((v1 + v2) - total_usd) > 0.05:
                    return messagebox.showerror("Error de Pagos", f"La suma de los montos (${v1 + v2:,.2f}) no coincide con el total (${total_usd:,.2f}).")
                metodo = f"{m1_t}: ${v1:,.2f} | {m2_t}: ${v2:,.2f}"
            except ValueError:
                return messagebox.showerror("Error", "Ingrese montos numéricos válidos en los métodos de pago.")
        else:
            metodo = m1_t

        estado_trans = "Cuentas por Cobrar" if "Crédito" in metodo else "Pagado / Completado"
        
        df_cli = self.db.obtener_clientes()
        cliente_row = df_cli[df_cli["rif"] == rif_cliente].iloc[0]
        cliente_id = int(cliente_row["id"])
        
        self.db.cursor.execute("SELECT COUNT(*) FROM transacciones WHERE categoria = 'Ventas de Mercancía'")
        num_ventas = self.db.cursor.fetchone()[0] + 1
        factura_codigo = f"FAC-B2B-{num_ventas:06d}"
        
        detalle_str = f"Cliente B2B: {cliente_row['nombre']} ({cliente_row['rif']})\n"
        for item in self.carrito_b2b: 
            # Cambiamos item['codigo'] por item['nombre'] para que la factura B2B sea legible
            detalle_str += f"{item['nombre']} | Cant: {item['cant']} - ${item['subtotal']:,.2f}\n"

        fecha, hora = datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M:%S")
        
        self.db.cursor.execute("""
            INSERT INTO transacciones (fecha, tipo, categoria, monto, forma_pago, descripcion, factura, hora, caja, detalle_factura, estado, cliente_id, eliminado)
            VALUES (?, 'Ingreso', 'Ventas de Mercancía', ?, ?, ?, ?, ?, 'B2B/Mayor', ?, ?, ?, 0)
        """, (fecha, total_usd, metodo, f"Venta Corporativa - {cliente_row['nombre']}", factura_codigo, hora, detalle_str, estado_trans, cliente_id))
        
        for item in self.carrito_b2b: self.db.actualizar_stock(int(item["id"]), -int(item["cant"]))
        self.db.conn.commit()
        
        # --- NUEVO: Extraemos el correo para pasarlo al PDF ---
        correo_cli = str(cliente_row.get("correo", "No especificado"))
        info_cli_dict = {"nombre": cliente_row["nombre"], "rif": cliente_row["rif"], "direccion": cliente_row["direccion"], "telefono": cliente_row["telefono"], "correo": correo_cli}
        
        totales_dict = {
            "subtotal_bruto": subtotal_bruto,
            "monto_descuento": monto_descuento,
            "desc_porc": desc_porc,
            "iva": iva,
            "total_usd": total_usd,
            "total_bs": total_bs,
            "tasa": self.tasa_actual,
            "metodo": metodo
        }
        
        # Generación de PDF corregida (una sola vez)
        ruta_pdf = self.db.generar_factura_b2b_pdf(factura_codigo, info_cli_dict, self.carrito_b2b, totales_dict, fecha, hora)
        
        self.carrito_b2b = []
        self.b2b_actualizar_ui_carrito()
        if hasattr(self, 'actualizar_dashboard_data'): self.actualizar_dashboard_data()
        if hasattr(self, 'cargar_tabla_ventas'): self.cargar_tabla_ventas()
        if hasattr(self, 'cargar_tabla_historial_b2b'): self.cargar_tabla_historial_b2b() # Actualiza el historial
        
        if ruta_pdf and os.path.exists(ruta_pdf):
            try:
                if platform.system() == 'Windows': os.startfile(ruta_pdf)
            except: pass
            messagebox.showinfo("Éxito", f"Factura {factura_codigo} emitida.")
        else:
            messagebox.showwarning("Advertencia", "Venta registrada, pero falló la generación del PDF.")

    # ==========================================
    # --- MÓDULO HISTORIAL B2B ---
    # ==========================================
    def setup_historial_b2b(self):
        f = ctk.CTkFrame(self.container, fg_color="transparent")
        self.frames["historial_b2b"] = f
        f.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(f, text="HISTORIAL DE VENTAS AL MAYOR (B2B)", font=("Arial", 24, "bold"), text_color=self.color_acento).pack(pady=(0, 10))
        
        top_v = ctk.CTkFrame(f, fg_color="transparent")
        top_v.pack(fill="both", expand=True)

        self.tabla_historial_b2b = ttk.Treeview(top_v, columns=("ID", "Factura", "Fecha", "Cliente", "Método", "Total USD"), show="headings", height=15)
        anchos = {"ID": 0, "Factura": 150, "Fecha": 100, "Cliente": 250, "Método": 150, "Total USD": 120}
        for col in anchos:
            self.tabla_historial_b2b.heading(col, text=col)
            self.tabla_historial_b2b.column(col, width=anchos[col], stretch=True if col=="Cliente" else False, anchor="center")
        self.tabla_historial_b2b.column("ID", width=0, stretch=False)
        self.tabla_historial_b2b.pack(fill="both", expand=True)
        self.tabla_historial_b2b.bind("<<TreeviewSelect>>", self.seleccionar_factura_b2b)

        bot_v = ctk.CTkFrame(f, fg_color=self.color_card, corner_radius=15)
        bot_v.pack(fill="x", pady=10)
        
        self.btn_ver_pdf_b2b = ctk.CTkButton(bot_v, text="📄 Abrir Factura Original A4", fg_color=self.verde_neon, text_color="white", font=("Arial", 14, "bold"), state="disabled", command=self.abrir_pdf_b2b)
        self.btn_ver_pdf_b2b.pack(pady=15)

    def cargar_tabla_historial_b2b(self):
        for item in self.tabla_historial_b2b.get_children(): self.tabla_historial_b2b.delete(item)
        
        df_ventas = self.db.obtener_todas_transacciones()
        if df_ventas.empty: return
        
        # Filtramos para que solo muestre las emitidas por la caja B2B
        df_b2b = df_ventas[df_ventas["caja"] == "B2B/Mayor"]
        
        for _, r in df_b2b.iterrows():
            str_total = f"${r['monto']:,.2f}"
            
            # Limpiamos la descripción para que solo muestre el nombre del cliente
            desc = r["descripcion"] if pd.notna(r["descripcion"]) else ""
            if "Venta Corporativa - " in desc:
                desc = desc.replace("Venta Corporativa - ", "")
            
            self.tabla_historial_b2b.insert("", "end", values=(
                r["id"], r["factura"], r["fecha"], desc, r["forma_pago"], str_total
            ))

    def seleccionar_factura_b2b(self, event):
        seleccion = self.tabla_historial_b2b.selection()
        if seleccion:
            self.btn_ver_pdf_b2b.configure(state="normal")
        else:
            self.btn_ver_pdf_b2b.configure(state="disabled")

    def abrir_pdf_b2b(self):
        seleccion = self.tabla_historial_b2b.selection()
        if not seleccion: return
        factura_codigo = self.tabla_historial_b2b.item(seleccion[0])["values"][1]
        
        ruta_pdf = os.path.join(self.db.tickets_dir, f"{factura_codigo}_B2B.pdf")
        
        if os.path.exists(ruta_pdf):
            try:
                if platform.system() == 'Windows': os.startfile(ruta_pdf)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir el PDF: {e}")
        else:
            messagebox.showerror("Archivo no encontrado", f"El archivo PDF no existe.")

    # ==========================================
    # MANEJADOR DE PANTALLAS (RESTAURADO COMPLETO)
    # ==========================================
    def mostrar_frame(self, nombre):
        for f in self.frames.values(): f.grid_remove()
        if nombre in self.frames:
            # --- MEJORA DE RESPONSIVIDAD: Forzamos expansión total por cuadrícula ---
            self.frames[nombre].grid(row=0, column=0, sticky="nsew")
        
        # Aquí es donde se le da la orden de cargar la data al hacer click en el menú lateral
        if nombre == "dash": self.actualizar_dashboard_data()
        elif nombre == "movimientos": self.cargar_tabla_movimientos()
        elif nombre == "ventas": self.cargar_tabla_ventas()
        elif nombre == "inventario":
            if hasattr(self, 'empty_barcode_img'):
                self.lbl_barcode_img.configure(image=self.empty_barcode_img, text="Seleccione un producto\npara ver su código")
            self.btn_exportar_codigo.configure(state="disabled")
            self.actualizar_inventario()
        elif nombre == "ing_merc": self.actualizar_combos_ingreso()
        elif nombre == "velas": self.generar_grafico_velas()
        elif nombre == "rendimiento": self.generar_grafico_rendimiento()
        elif nombre == "nomina": self.actualizar_empleados()
        elif nombre == "termometro": self.renderizar_termometros()
        elif nombre == "papelera": self.cargar_papelera()
        elif nombre == "mensual": self.actualizar_periodos_disponibles()
        elif nombre == "clientes": self.cargar_tabla_clientes()
        elif nombre == "mayor": self.actualizar_combos_mayor()
        elif nombre == "historial_b2b": self.cargar_tabla_historial_b2b()

# ==========================================
# --- SISTEMA DE SEGURIDAD Y LICENCIA ---
# ==========================================
CLAVE_SECRETA = "ContaPyPro_Acceso_Seguro_2026_XyZ" 

def validar_licencia_seguridad():
    try:
        # 1. Leer la máquina actual (Mismo método que el Lector HWID)
        import uuid
        mac = str(uuid.getnode())
        huella_local = hashlib.sha256(mac.encode()).hexdigest()[:16].upper()
        
        # 2. Calcular cuál debería ser la licencia correcta para ESTA máquina
        licencia_esperada = hashlib.sha256((huella_local + CLAVE_SECRETA).encode()).hexdigest()
        
        # 3. Buscar el archivo licencia.lic
        if getattr(sys, 'frozen', False):
            BASE_DIR = os.path.dirname(sys.executable)
        else:
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            
        ruta_lic = os.path.join(BASE_DIR, "licencia.lic")
        
        if not os.path.exists(ruta_lic):
            messagebox.showerror("Acceso Denegado", "No se encontró licencia de ContaPy Pro.\nContacte al proveedor.")
            sys.exit() 
            
        with open(ruta_lic, "r") as f:
            licencia_instalada = f.read().strip()
            
        # 4. Comparar
        if licencia_esperada != licencia_instalada:
            messagebox.showerror("Violación de Seguridad", "Esta licencia no pertenece a este equipo.\nEl software ha sido bloqueado.")
            sys.exit() 
            
    except Exception as e:
        messagebox.showerror("Error Crítico", "Fallo al validar los componentes físicos del equipo.")
        sys.exit()

if __name__ == "__main__":
    # 1. Llama a la validación de seguridad
    validar_licencia_seguridad()
    
    # 2. IMPORTANTE: Destruimos el splash ANTES de crear la app principal
    # Esto evita el error "pyimage doesn't exist" y resetea la memoria visual
    splash.destroy() 
    
    # 3. Prepara y muestra la interfaz principal del sistema
    app = ContaPyApp()
    app.mainloop()