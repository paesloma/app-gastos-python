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
            st.error("❌ PIN incorrecto")
    return False

# --- FUNCIONES GITHUB ---
def conectar_github():
    return Github(GITHUB_TOKEN).get_repo(REPO_NAME)

def cargar_datos_de_github():
    try:
        repo = conectar_github()
        contents = repo.get_contents(FILE_PATH)
        df = pd.read_csv(io.StringIO(contents.decoded_content.decode('utf-8')))
        
        # Corrección de columna Imagen por si no existe
        if "Imagen" not in df.columns:
            df["Imagen"] = "Sin imagen"
        return df, contents.sha
    except:
        return pd.DataFrame(columns=["ID", "Fecha", "Tipo", "Concepto", "Monto", "Categoria", "Imagen"]), None

def guardar_todo_en_github(df, sha_csv, imagen_bytes=None, nombre_img=None):
    repo = conectar_github()
    if imagen_bytes and nombre_img:
        path_img = f"{FOLDER_IMAGES}/{nombre_img}"
        try:
            repo.create_file(path_img, f"Subida de comprobante {nombre_img}", imagen_bytes)
        except: pass

    csv_content = df.to_csv(index=False)
    if sha_csv:
        repo.update_file(FILE_PATH, "Update multimedia", csv_content, sha_csv)
    else:
        repo.create_file(FILE_PATH, "Carga inicial", csv_content)

# --- APP PRINCIPAL ---
if check_password():
    st.title("💰 AppFinanzas Pro")
    df, sha = cargar_datos_de_github()

    with st.sidebar:
        st.header("➕ Nuevo Registro")
        fecha = st.date_input("Fecha", datetime.now())
        tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
        concepto = st.text_input("Concepto")
        monto = st.number_input("Monto ($)", min_value=0.0)
        cat = st.selectbox("Categoría", ["Alimentación", "Sueldo", "Vivienda", "Salud", "Transporte", "Otros"])
        
        st.divider()
        # MODIFICACIÓN: "Subir archivo" ahora es la opción por defecto (index=0)
        metodo_archivo = st.radio(
            "Seleccionar comprobante:", 
            ["Subir archivo (Galería)", "Cámara en vivo"],
            index=0
        )
        
        archivo_comprobante = None
        if metodo_archivo == "Cámara en vivo":
            archivo_comprobante = st.camera_input("Capturar foto")
        else:
            archivo_comprobante = st.file_uploader("Adjuntar archivo (Imagen o PDF)", type=["jpg", "png", "jpeg", "pdf"])
        
        if st.button("Guardar Registro"):
            if concepto:
                nuevo_id = int(df["ID"].max() + 1) if not df.empty else 1
                nombre_img = f"doc_{nuevo_id}.png" if archivo_comprobante else "Sin imagen"
                
                nueva_fila = pd.DataFrame([{
                    "ID": nuevo_id, "Fecha": fecha.strftime("%Y-%m-%d"),
                    "Tipo": tipo, "Concepto": concepto, "Monto": monto,
                    "Categoria": cat, "Imagen": nombre_img
                }])
                
                df = pd.concat([df, nueva_fila], ignore_index=True)
                datos_archivo = archivo_comprobante.getvalue() if archivo_comprobante else None
                guardar_todo_en_github(df, sha, datos_archivo, nombre_img)
                st.success("✅ ¡Guardado permanentemente!")
                st.rerun()

    # --- HISTORIAL Y GRÁFICOS ---
    st.subheader("📋 Historial")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        
        st.divider()
        col_view, col_graf = st.columns([1, 1])
        
        with col_view:
            id_ver = st.number_input("Ver comprobante de ID:", min_value=1, step=1)
            fila = df[df["ID"] == id_ver]
            if not fila.empty:
                img_name = fila["Imagen"].values[0]
                if img_name != "Sin imagen":
                    url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{FOLDER_IMAGES}/{img_name}"
                    st.image(url, caption=f"Archivo ID {id_ver}", width=350)
                else:
                    st.info("No hay archivo adjunto.")

        with col_graf:
            resumen = df.groupby('Tipo')['Monto'].sum().reset_index()
            # Mapeo de colores: Verde Ingreso, Rojo Gasto
            st.bar_chart(data=resumen, x='Tipo', y='Monto', color='Tipo')

    if st.sidebar.button("Cerrar Sesión"):
        st.session_state["password_correct"] = False
        st.rerun()
