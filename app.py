import streamlit as st
import pandas as pd
from github import Github
import io
import requests
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

st.set_page_config(page_title="AppFinanzas Pro", layout="wide")

# --- SEGURIDAD PIN 1602 ---
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
            repo.create_file(path_img, f"Archivo {nombre_img}", imagen_bytes)
        except: pass
    csv_content = df.to_csv(index=False)
    if sha_csv:
        repo.update_file(FILE_PATH, "Sincronización multimedia", csv_content, sha_csv)
    else:
        repo.create_file(FILE_PATH, "Carga inicial", csv_content)

# --- APP PRINCIPAL ---
if check_password():
    st.title("💰 AppFinanzas Pro")
    df, sha = cargar_datos_de_github()

    # --- MÉTRICAS DE BALANCE ---
    if not df.empty:
        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
        t_i = df[df['Tipo'] == 'Ingreso']['Monto'].sum()
        t_g = df[df['Tipo'] == 'Gasto']['Monto'].sum()
        st.columns(3)[0].metric("Ingresos", f"${t_i:,.2f}")
        st.columns(3)[1].metric("Gastos", f"${t_g:,.2f}", delta=f"-${t_g:,.2f}", delta_color="inverse")
        st.columns(3)[2].metric("Balance", f"${t_i - t_g:,.2f}")
        st.divider()

    with st.sidebar:
        st.header("➕ Nuevo Registro")
        fecha = st.date_input("Fecha", datetime.now())
        tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
        concepto = st.text_input("Concepto")
        monto = st.number_input("Monto ($)", min_value=0.0, format="%.2f")
        cat = st.selectbox("Categoría", ["Otros", "Alimentación", "Sueldo", "Vivienda", "Salud", "Transporte"])
        metodo = st.radio("Comprobante:", ["Subir archivo (Galería)", "Cámara en vivo"], index=0)
        archivo = st.camera_input("Capturar") if metodo == "Cámara en vivo" else st.file_uploader("Adjuntar", type=["jpg", "png", "jpeg", "pdf"])
        
        if st.button("Guardar Registro"):
            if concepto:
                nuevo_id = int(df["ID"].max() + 1) if not df.empty else 1
                ext = archivo.name.split('.')[-1] if (archivo and hasattr(archivo, 'name')) else "png"
                nombre_img = f"doc_{nuevo_id}.{ext}" if archivo else "Sin imagen"
                nueva_fila = pd.DataFrame([{"ID": nuevo_id, "Fecha": fecha.strftime("%Y-%m-%d"), "Tipo": tipo, "Concepto": concepto, "Monto": monto, "Categoria": cat, "Imagen": nombre_img}])
                df = pd.concat([df, nueva_fila], ignore_index=True)
                guardar_todo_en_github(df, sha, archivo.getvalue() if archivo else None, nombre_img)
                st.success("✅ Guardado")
                st.rerun()

    # --- HISTORIAL CON CLIC PARA DESCARGAR ---
    if not df.empty:
        st.subheader("📋 Historial (Haz clic en la imagen para descargar)")
        
        # Creamos una copia para mostrar con enlaces
        df_display = df.copy()
        base_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{FOLDER_IMAGES}/"
        
        # Transformamos el nombre de la imagen en un link de descarga real
        df_display['Descargar'] = df_display['Imagen'].apply(
            lambda x: f"{base_url}{x}" if x != "Sin imagen" else None
        )

        # Configuramos st.data_editor para que la columna 'Descargar' sea un link clickeable
        st.data_editor(
            df_display.sort_values("ID", ascending=False),
            column_config={
                "Descargar": st.column_config.LinkColumn(
                    "Enlace de Imagen",
                    help="Haz clic para descargar el archivo directamente",
                    validate="^https://.*",
                    display_text="Descargar archivo"
                )
            },
            disabled=True, # Evita que se editen las celdas
            use_container_width=True,
            hide_index=True
        )

        # BOTÓN EXCEL Y BORRADO
        col1, col2 = st.columns(2)
        with col1:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 Descargar Tabla Completa (Excel)", buffer.getvalue(), "Finanzas.xlsx")
        with col2:
            with st.expander("🗑️ Borrar"):
                id_b = st.number_input("ID a eliminar:", min_value=1, step=1)
                if st.button("Confirmar"):
                    df = df[df["ID"] != id_b]
                    guardar_todo_en_github(df, sha)
                    st.rerun()

    if st.sidebar.button("Cerrar Sesión"):
        st.session_state["password_correct"] = False
        st.rerun()
