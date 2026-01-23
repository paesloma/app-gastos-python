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

st.set_page_config(page_title="AppFinanzas Pro - paesloma", layout="wide")

# --- FUNCIONES DE PERSISTENCIA ---
def conectar_github():
    return Github(GITHUB_TOKEN).get_repo(REPO_NAME)

def cargar_datos_de_github():
    try:
        repo = conectar_github()
        contents = repo.get_contents(FILE_PATH)
        df = pd.read_csv(io.StringIO(contents.decoded_content.decode('utf-8')))
        # Aseguramos que la columna Fecha exista en el DataFrame cargado
        if "Fecha" not in df.columns:
            df["Fecha"] = datetime.now().strftime("%Y-%m-%d")
        return df, contents.sha
    except Exception:
        # Estructura base incluyendo la nueva columna 'Fecha'
        return pd.DataFrame(columns=["ID", "Fecha", "Tipo", "Concepto", "Monto", "Categoria"]), None

def guardar_en_github(df, sha):
    repo = conectar_github()
    csv_content = df.to_csv(index=False)
    
    st.info(f"🔍 Sincronizando con GitHub...")
    
    if sha:
        repo.update_file(FILE_PATH, "Actualización con fecha", csv_content, sha)
    else:
        repo.create_file(FILE_PATH, "Carga inicial con fechas", csv_content)

# --- INICIO DE LA APP ---
st.title("💰 AppFinanzas Pro: Control con Fechas")
df, sha = cargar_datos_de_github()

# --- SIDEBAR: REGISTRO ---
with st.sidebar:
    st.header("➕ Nueva Transacción")
    
    # --- NUEVA CASILLA DE FECHA ---
    fecha_registro = st.date_input("Fecha de Registro", datetime.now())
    
    tipo = st.selectbox("Tipo de Movimiento", ["Ingreso", "Gasto"])
    concepto = st.text_input("Descripción / Concepto")
    monto = st.number_input("Valor ($)", min_value=0.0, format="%.2f")
    categoria = st.selectbox("Categoría", ["Sueldo", "Alimentación", "Transporte", "Vivienda", "Entretenimiento", "Otros"])
    
    if st.button("Guardar en la Nube"):
        if concepto:
            nuevo_id = int(df["ID"].max() + 1) if not df.empty else 1
            nueva_fila = pd.DataFrame([{
                "ID": nuevo_id, 
                "Fecha": fecha_registro.strftime("%Y-%m-%d"), # Guardamos la fecha seleccionada
                "Tipo": tipo, 
                "Concepto": concepto, 
                "Monto": monto, 
                "Categoria": categoria
            }])
            df = pd.concat([df, nueva_fila], ignore_index=True)
            guardar_en_github(df, sha)
            st.success(f"✅ Registrado el {fecha_registro}")
            st.rerun()
        else:
            st.error("Ingresa una descripción.")

# --- CUERPO PRINCIPAL ---
col_stats, col_viz = st.columns([1.5, 1])

with col_stats:
    st.subheader("📋 Historial (Ordenado por Fecha)")
    if not df.empty:
        # Ordenamos el historial para que lo más reciente aparezca arriba
        df_sorted = df.sort_values(by="Fecha", ascending=False)
        st.dataframe(df_sorted, use_container_width=True)
        
        # BOTÓN EXCEL
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Finanzas')
        st.download_button("📥 Descargar Excel", buffer.getvalue(), "finanzas.xlsx", "application/vnd.ms-excel")

with col_viz:
    st.subheader("📊 Resumen Comparativo")
    if not df.empty:
        resumen_tipo = df.groupby('Tipo')['Monto'].sum().reset_index()
        st.bar_chart(data=resumen_tipo, x='Tipo', y='Monto', color='Tipo')
        
        total_ingresos = df[df['Tipo'] == 'Ingreso']['Monto'].sum()
        total_gastos = df[df['Tipo'] == 'Gasto']['Monto'].sum()
        st.metric("Balance Total", f"${(total_ingresos - total_gastos):,.2f}", delta=f"${total_ingresos:,.2f} Ingresos")

# --- BORRADO ---
if not df.empty:
    with st.expander("🗑️ Borrar Registros"):
        id_a_borrar = st.number_input("ID a eliminar", min_value=1, step=1)
        if st.button("Confirmar"):
            st.warning(f"Eliminando registro ID {id_a_borrar}...")
            df = df[df["ID"] != id_a_borrar]
            guardar_en_github(df, sha)
            st.rerun()
