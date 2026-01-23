import streamlit as st
import pandas as pd
from github import Github
import io
from datetime import datetime

# --- CONFIGURACIÓN SEGURA ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except Exception:
    st.error("⚠️ Configura el GITHUB_TOKEN en los Secrets.")
    st.stop()

REPO_NAME = "paesloma/app-gastos-python"
FILE_PATH = "finanzas.csv"
FOLDER_IMAGES = "comprobantes" # Carpeta donde se guardarán las fotos

st.set_page_config(page_title="AppFinanzas Pro - Multimedia", layout="wide")

# --- SEGURIDAD ---
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
        return df, contents.sha
    except:
        return pd.DataFrame(columns=["ID", "Fecha", "Tipo", "Concepto", "Monto", "Categoria", "Imagen"]), None

def guardar_todo_en_github(df, sha_csv, imagen_bytes=None, nombre_img=None):
    repo = conectar_github()
    
    # 1. Guardar la Imagen si existe
    if imagen_bytes and nombre_img:
        path_img = f"{FOLDER_IMAGES}/{nombre_img}"
        try:
            repo.create_file(path_img, f"Subida de foto {nombre_img}", imagen_bytes)
        except:
            st.warning("La imagen ya existe o hubo un error al subirla.")

    # 2. Guardar el CSV actualizado
    csv_content = df.to_csv(index=False)
    if sha_csv:
        repo.update_file(FILE_PATH, "Update con multimedia", csv_content, sha_csv)
    else:
        repo.create_file(FILE_PATH, "Carga inicial multimedia", csv_content)

# --- APP PRINCIPAL ---
if check_password():
    st.title("💰 AppFinanzas Pro + Comprobantes")
    df, sha = cargar_datos_de_github()

    with st.sidebar:
        st.header("➕ Nuevo Registro")
        fecha = st.date_input("Fecha", datetime.now())
        tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
        concepto = st.text_input("Concepto")
        monto = st.number_input("Monto ($)", min_value=0.0)
        cat = st.selectbox("Categoría", ["Alimentación", "Sueldo", "Vivienda", "Salud", "Otros"])
        
        # --- CARGADOR DE FOTOS ---
        foto = st.file_uploader("Subir Comprobante (Opcional)", type=["jpg", "png", "jpeg"])
        
        if st.button("Guardar"):
            if concepto:
                nuevo_id = int(df["ID"].max() + 1) if not df.empty else 1
                nombre_archivo_foto = f"img_{nuevo_id}.png" if foto else "Sin imagen"
                
                nueva_fila = pd.DataFrame([{
                    "ID": nuevo_id, "Fecha": fecha.strftime("%Y-%m-%d"),
                    "Tipo": tipo, "Concepto": concepto, "Monto": monto,
                    "Categoria": cat, "Imagen": nombre_archivo_foto
                }])
                
                df = pd.concat([df, nueva_fila], ignore_index=True)
                
                # Sincronizar
                img_data = foto.getvalue() if foto else None
                guardar_todo_en_github(df, sha, img_data, nombre_archivo_foto)
                st.success("✅ Registro y Foto guardados")
                st.rerun()

    # --- VISUALIZACIÓN ---
    st.subheader("📋 Historial con Multimedia")
    if not df.empty:
        # Mostramos la tabla
        st.dataframe(df, use_container_width=True)
        
        # Lógica para ver la foto de un registro
        id_ver = st.number_input("Ingresa el ID para ver su comprobante", min_value=1, step=1)
        fila = df[df["ID"] == id_ver]
        
        if not fila.empty:
            img_name = fila["Imagen"].values[0]
            if img_name != "Sin imagen":
                url_img = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{FOLDER_IMAGES}/{img_name}"
                st.image(url_img, caption=f"Comprobante ID {id_ver}", width=400)
            else:
                st.info("Este registro no tiene foto asociada.")

    # --- GRÁFICOS ---
    resumen = df.groupby('Tipo')['Monto'].sum().reset_index()
    st.bar_chart(data=resumen, x='Tipo', y='Monto', color='Tipo')
