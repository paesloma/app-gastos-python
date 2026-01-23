import streamlit as st
import pandas as pd
from github import Github
import io

# --- CONFIGURACIÓN DE ACCESO SEGURA ---
# Se intenta leer desde los Secrets de Streamlit Cloud para evitar bloqueos de seguridad
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except Exception:
    st.error("⚠️ No se encontró 'GITHUB_TOKEN' en los Secrets de Streamlit. Configúralo en Settings > Secrets.")
    st.stop()

REPO_NAME = "paesloma/app-gastos-python" 
FILE_PATH = "finanzas.csv"

# Configuración de la interfaz
st.set_page_config(page_title="AppFinanzas - Persistencia GitHub", layout="wide")

# --- FUNCIONES DE PERSISTENCIA ---
def conectar_github():
    g = Github(GITHUB_TOKEN)
    return g.get_repo(REPO_NAME)

def cargar_datos_de_github():
    try:
        repo = conectar_github()
        contents = repo.get_contents(FILE_PATH)
        data = contents.decoded_content.decode('utf-8')
        df = pd.read_csv(io.StringIO(data))
        return df, contents.sha
    except Exception:
        # Crea estructura base si el archivo no existe en el repo
        return pd.DataFrame(columns=["ID", "Tipo", "Concepto", "Monto", "Categoria"]), None

def guardar_en_github(df, sha):
    repo = conectar_github()
    csv_content = df.to_csv(index=False)
    
    # MOSTRAR CONSULTA SENSIBLE
    st.info(f"🔍 Sincronizando datos con GitHub...")
    
    if sha:
        repo.update_file(FILE_PATH, "Actualización desde App", csv_content, sha)
    else:
        repo.create_file(FILE_PATH, "Carga inicial de datos", csv_content)

# --- LÓGICA DE LA APP ---
st.title("💰 Gestor de Gastos - Persistencia Real")

# Cargar datos al inicio
df, sha = cargar_datos_de_github()

# --- SIDEBAR: REGISTRO ---
with st.sidebar:
    st.header("➕ Nueva Transacción")
    tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
    concepto = st.text_input("Concepto")
    monto = st.number_input("Valor", min_value=0.0, format="%.2f")
    categoria = st.selectbox("Categoría", ["Alimentación", "Transporte", "Vivienda", "Sueldo", "Entretenimiento", "Otros"])
    
    if st.button("Guardar en GitHub"):
        if concepto:
            nuevo_id = int(df["ID"].max() + 1) if not df.empty else 1
            nueva_fila = pd.DataFrame([{"ID": nuevo_id, "Tipo": tipo, "Concepto": concepto, "Monto": monto, "Categoria": categoria}])
            df = pd.concat([df, nueva_fila], ignore_index=True)
            guardar_en_github(df, sha)
            st.success("✅ ¡Datos guardados permanentemente!")
            st.rerun()
        else:
            st.warning("Escribe un concepto antes de guardar.")

# --- CUERPO: TABLA Y BORRADO ---
if not df.empty:
    st.subheader("Historial de Movimientos")
    st.dataframe(df, use_container_width=True)
    
    # Borrado de registros
    id_a_borrar = st.number_input("ID a eliminar", min_value=1, step=1)
    if st.button("🗑️ Eliminar Registro"):
        # MOSTRAR CONSULTA SENSIBLE
        st.warning(f"Eliminando registro ID {id_a_borrar}...")
        df = df[df["ID"] != id_a_borrar]
        guardar_en_github(df, sha)
        st.rerun()
else:
    st.info("No hay datos en el repositorio.")
