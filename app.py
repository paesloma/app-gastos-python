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

st.set_page_config(page_title="AppFinanzas Pro - Multimedia", layout="wide")

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
            repo.create_file(path_img, f"Archivo comprobante {nombre_img}", imagen_bytes)
        except: pass

    csv_content = df.to_csv(index=False)
    if sha_csv:
        repo.update_file(FILE_PATH, "Sincronización completa", csv_content, sha_csv)
    else:
        repo.create_file(FILE_PATH, "Carga inicial", csv_content)

# --- APP PRINCIPAL ---
if check_password():
    st.title("💰 AppFinanzas Pro: Gestión Total")
    df, sha = cargar_datos_de_github()

    # --- MÉTRICAS DE BALANCE ---
    if not df.empty:
        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
        total_i = df[df['Tipo'] == 'Ingreso']['Monto'].sum()
        total_g = df[df['Tipo'] == 'Gasto']['Monto'].sum()
        balance = total_i - total_g

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Total Ingresos", f"${total_i:,.2f}")
        col_m2.metric("Total Gastos", f"${total_g:,.2f}", delta=f"-${total_g:,.2f}", delta_color="inverse")
        col_m3.metric("Balance Neto", f"${balance:,.2f}", delta=f"${balance:,.2f}")
        st.divider()

    with st.sidebar:
        st.header("➕ Nuevo Registro")
        fecha = st.date_input("Fecha", datetime.now())
        tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
        concepto = st.text_input("Concepto")
        monto = st.number_input("Monto ($)", min_value=0.0, format="%.2f")
        cat = st.selectbox("Categoría", ["Otros", "Alimentación", "Sueldo", "Vivienda", "Salud", "Transporte"])
        
        st.divider()
        metodo = st.radio("Comprobante:", ["Subir archivo (Galería)", "Cámara en vivo"], index=0)
        archivo = st.camera_input("Capturar") if metodo == "Cámara en vivo" else st.file_uploader("Adjuntar", type=["jpg", "png", "jpeg", "pdf"])
        
        if st.button("Guardar Registro"):
            if concepto:
                nuevo_id = int(df["ID"].max() + 1) if not df.empty else 1
                # Guardamos con la extensión original si es archivo
                ext = archivo.name.split('.')[-1] if (archivo and hasattr(archivo, 'name')) else "png"
                nombre_img = f"doc_{nuevo_id}.{ext}" if archivo else "Sin imagen"
                
                nueva_fila = pd.DataFrame([{
                    "ID": nuevo_id, "Fecha": fecha.strftime("%Y-%m-%d"),
                    "Tipo": tipo, "Concepto": concepto, "Monto": monto,
                    "Categoria": cat, "Imagen": nombre_img
                }])
                df = pd.concat([df, nueva_fila], ignore_index=True)
                datos = archivo.getvalue() if archivo else None
                guardar_todo_en_github(df, sha, datos, nombre_img)
                st.success("✅ ¡Guardado!")
                st.rerun()

    # --- HISTORIAL Y BOTONES DE ACCIÓN ---
    if not df.empty:
        st.subheader("📋 Historial de Movimientos")
        st.dataframe(df.sort_values("ID", ascending=False), use_container_width=True)
        
        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Finanzas')
            st.download_button("📥 Descargar Reporte Excel", buffer.getvalue(), f"Finanzas_{datetime.now().strftime('%Y%m%d')}.xlsx", "application/vnd.ms-excel")

        with col_btn2:
            with st.expander("🗑️ Eliminar un registro"):
                id_borrar = st.number_input("ID a eliminar:", min_value=1, step=1)
                if st.button("Confirmar Borrado"):
                    df = df[df["ID"] != id_borrar]
                    guardar_todo_en_github(df, sha)
                    st.rerun()

        # --- VISUALIZACIÓN Y DESCARGA DE IMAGEN ---
        st.divider()
        st.subheader("🖼️ Visor de Comprobantes")
        id_ver = st.number_input("Ingresa ID para ver/descargar comprobante:", min_value=1, step=1)
        fila_img = df[df["ID"] == id_ver]
        
        if not fila_img.empty:
            img_name = fila_img["Imagen"].values[0]
            if img_name != "Sin imagen":
                url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{FOLDER_IMAGES}/{img_name}"
                
                # Mostrar imagen
                st.image(url, width=400)
                
                # BOTÓN DE DESCARGA PARA LA IMAGEN
                try:
                    response = requests.get(url)
                    st.download_button(
                        label=f"📥 Descargar archivo: {img_name}",
                        data=response.content,
                        file_name=img_name,
                        mime="image/png"
                    )
                except:
                    st.error("No se pudo preparar la descarga de la imagen.")
            else:
                st.info("Este registro no tiene un archivo adjunto.")

    if st.sidebar.button("Cerrar Sesión"):
        st.session_state["password_correct"] = False
        st.rerun()
