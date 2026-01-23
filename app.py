import streamlit as st
import pandas as pd
from github import Github
import io
from datetime import datetime

# --- CONFIGURACIÓN SEGURA ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except Exception:
    st.error("⚠️ Configura el GITHUB_TOKEN en los Secrets de Streamlit.")
    st.stop()

REPO_NAME = "paesloma/app-gastos-python"
FILE_PATH = "finanzas.csv"
FOLDER_IMAGES = "comprobantes"

st.set_page_config(page_title="AppFinanzas Multimedia Pro", layout="wide")

# --- SEGURIDAD PIN ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True
    
    st.markdown("### 🔒 Acceso con PIN")
    pin = st.text_input("Introduce el PIN", type="password")
    if st.button("Ingresar"):
        if pin == "1602":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("PIN incorrecto")
    return False

# --- FUNCIONES GITHUB ---
def conectar_github():
    return Github(GITHUB_TOKEN).get_repo(REPO_NAME)

def cargar_datos_de_github():
    try:
        repo = conectar_github()
        contents = repo.get_contents(FILE_PATH)
        df = pd.read_csv(io.StringIO(contents.decoded_content.decode('utf-8')))
        
        # SOLUCIÓN DEFINITIVA: Asegurar que la columna 'Imagen' exista siempre
        if "Imagen" not in df.columns:
            df["Imagen"] = "Sin imagen"
        return df, contents.sha
    except:
        return pd.DataFrame(columns=["ID", "Fecha", "Tipo", "Concepto", "Monto", "Categoria", "Imagen"]), None

def guardar_todo_en_github(df, sha_csv, imagen_bytes=None, nombre_img=None):
    repo = conectar_github()
    
    # 1. Guardar archivo/foto si existe
    if imagen_bytes and nombre_img:
        path_img = f"{FOLDER_IMAGES}/{nombre_img}"
        try:
            repo.create_file(path_img, f"Archivo comprobante {nombre_img}", imagen_bytes)
        except: 
            pass # Si ya existe no hacemos nada o podrías usar update_file

    # 2. Guardar CSV
    csv_content = df.to_csv(index=False)
    if sha_csv:
        repo.update_file(FILE_PATH, "Sincronización multimedia", csv_content, sha_csv)
    else:
        repo.create_file(FILE_PATH, "Carga inicial", csv_content)

# --- APP PRINCIPAL ---
if check_password():
    st.title("💰 AppFinanzas: Gestión Multimedia")
    df, sha = cargar_datos_de_github()

    with st.sidebar:
        st.header("➕ Nuevo Registro")
        fecha = st.date_input("Fecha", datetime.now())
        tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
        concepto = st.text_input("Concepto")
        monto = st.number_input("Monto ($)", min_value=0.0)
        cat = st.selectbox("Categoría", ["Otros", "Alimentación", "Sueldo", "Vivienda", "Salud", "Transporte"])
        
        # --- NUEVA SECCIÓN MULTIMEDIA DUAL ---
        st.divider()
        metodo_archivo = st.radio("Método de comprobante:", ["Cámara en vivo", "Subir archivo (Galería)"])
        
        archivo_comprobante = None
        if metodo_archivo == "Cámara en vivo":
            archivo_comprobante = st.camera_input("Tomar foto")
        else:
            archivo_comprobante = st.file_uploader("Seleccionar archivo", type=["jpg", "png", "jpeg", "pdf"])
        
        if st.button("Guardar en la Nube"):
            if concepto:
                nuevo_id = int(df["ID"].max() + 1) if not df.empty else 1
                ext = "png" # extensión genérica
                nombre_img = f"comprobante_{nuevo_id}.{ext}" if archivo_comprobante else "Sin imagen"
                
                nueva_fila = pd.DataFrame([{
                    "ID": nuevo_id, "Fecha": fecha.strftime("%Y-%m-%d"),
                    "Tipo": tipo, "Concepto": concepto, "Monto": monto,
                    "Categoria": cat, "Imagen": nombre_img
                }])
                
                df = pd.concat([df, nueva_fila], ignore_index=True)
                
                # Obtener bytes del archivo
                datos_archivo = archivo_comprobante.getvalue() if archivo_comprobante else None
                guardar_todo_en_github(df, sha, datos_archivo, nombre_img)
                
                st.success(f"✅ ¡Registro {nuevo_id} guardado exitosamente!")
                st.rerun()
            else:
                st.error("Por favor escribe un concepto.")

    # --- HISTORIAL Y VISUALIZACIÓN ---
    st.subheader("📋 Historial de Transacciones")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        
        # BUSCADOR Y VISUALIZADOR DE COMPROBANTES
        st.divider()
        col_view, col_info = st.columns([1, 1])
        
        with col_view:
            id_ver = st.number_input("Ver comprobante de ID:", min_value=1, step=1)
            fila = df[df["ID"] == id_ver]
            
            if not fila.empty:
                img_name = fila["Imagen"].values[0]
                if img_name != "Sin imagen":
                    url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{FOLDER_IMAGES}/{img_name}"
                    st.image(url, caption=f"Comprobante ID {id_ver}", width=400)
                else:
                    st.info("Este registro no tiene un comprobante guardado.")
        
        with col_info:
            # Resumen rápido del ID seleccionado
            if not fila.empty:
                st.write(f"**Concepto:** {fila['Concepto'].values[0]}")
                st.write(f"**Monto:** ${fila['Monto'].values[0]:,.2f}")
                st.write(f"**Fecha:** {fila['Fecha'].values[0]}")

    # --- CIERRE DE SESIÓN ---
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state["password_correct"] = False
        st.rerun()
