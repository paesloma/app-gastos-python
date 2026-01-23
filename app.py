import streamlit as st
import pandas as pd
from github import Github
import io
from datetime import datetime

# --- CONFIGURACIÓN DE ACCESO SEGURA ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except Exception:
    st.error("⚠️ Configura el GITHUB_TOKEN en los Secrets de Streamlit.")
    st.stop()

REPO_NAME = "paesloma/app-gastos-python" 
FILE_PATH = "finanzas.csv"

st.set_page_config(page_title="AppFinanzas Pro - Privado", layout="wide")

# --- FUNCIÓN DE LOGUEO ---
def check_password():
    """Retorna True si el usuario ingresó el PIN correcto."""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    # Interfaz de bloqueo
    st.markdown("### 🔒 Acceso Restringido")
    pin_ingresado = st.text_input("Introduce tu PIN de acceso", type="password")
    
    if st.button("Ingresar"):
        if pin_ingresado == "1602":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ PIN incorrecto. Inténtalo de nuevo.")
    return False

# --- FUNCIONES DE PERSISTENCIA ---
def conectar_github():
    return Github(GITHUB_TOKEN).get_repo(REPO_NAME)

def cargar_datos_de_github():
    try:
        repo = conectar_github()
        contents = repo.get_contents(FILE_PATH)
        df = pd.read_csv(io.StringIO(contents.decoded_content.decode('utf-8')))
        return df, contents.sha
    except Exception:
        return pd.DataFrame(columns=["ID", "Fecha", "Tipo", "Concepto", "Monto", "Categoria"]), None

def guardar_en_github(df, sha):
    repo = conectar_github()
    csv_content = df.to_csv(index=False)
    # CONSULTA SENSIBLE
    st.info(f"🔍 Actualizando base de datos en {REPO_NAME}...")
    if sha:
        repo.update_file(FILE_PATH, "Update App Segura", csv_content, sha)
    else:
        repo.create_file(FILE_PATH, "Carga Inicial Segura", csv_content)

# --- FLUJO PRINCIPAL ---
if check_password():
    # Si el PIN es correcto, se muestra el resto de la App
    st.title("💰 Mi Gestor Financiero (Protegido)")
    df, sha = cargar_datos_de_github()

    # --- SIDEBAR: REGISTRO ---
    with st.sidebar:
        st.header("➕ Nueva Transacción")
        fecha_reg = st.date_input("Fecha", datetime.now())
        tipo = st.selectbox("Tipo", ["Ingreso", "Gasto"])
        concepto = st.text_input("Concepto")
        monto = st.number_input("Monto ($)", min_value=0.0, format="%.2f")
        cat = st.selectbox("Categoría", ["Sueldo", "Alimentación", "Transporte", "Vivienda", "Entretenimiento", "Otros"])
        
        if st.button("Guardar Permanentemente"):
            if concepto:
                nuevo_id = int(df["ID"].max() + 1) if not df.empty else 1
                nueva_fila = pd.DataFrame([{
                    "ID": nuevo_id, "Fecha": fecha_reg.strftime("%Y-%m-%d"),
                    "Tipo": tipo, "Concepto": concepto, "Monto": monto, "Categoria": cat
                }])
                df = pd.concat([df, nueva_fila], ignore_index=True)
                guardar_en_github(df, sha)
                st.success("✅ Datos sincronizados")
                st.rerun()

    # --- CUERPO: DASHBOARD ---
    col1, col2 = st.columns([1.5, 1])

    with col1:
        st.subheader("📋 Historial")
        if not df.empty:
            st.dataframe(df.sort_values("Fecha", ascending=False), use_container_width=True)
            # Botón Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 Descargar Excel", buffer.getvalue(), "reporte.xlsx")

    with col2:
        st.subheader("📊 Gráfico Comparativo")
        if not df.empty:
            resumen = df.groupby('Tipo')['Monto'].sum().reset_index()
            # Verde para ingresos, Rojo para gastos
            st.bar_chart(data=resumen, x='Tipo', y='Monto', color='Tipo')
            
            # Balance
            total_i = df[df['Tipo'] == 'Ingreso']['Monto'].sum()
            total_g = df[df['Tipo'] == 'Gasto']['Monto'].sum()
            st.metric("Balance Neto", f"${(total_i - total_g):,.2f}", delta=f"${total_i:,.2f} Totales")

    # --- BORRADO ---
    with st.expander("🗑️ Zona de Borrado"):
        id_del = st.number_input("ID a eliminar", min_value=1, step=1)
        if st.button("Eliminar"):
            # CONSULTA SENSIBLE
            st.warning(f"Borrando ID {id_del}...")
            df = df[df["ID"] != id_del]
            guardar_en_github(df, sha)
            st.rerun()
            
    # Botón para cerrar sesión
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state["password_correct"] = False
        st.rerun()
