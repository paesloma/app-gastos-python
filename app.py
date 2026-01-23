import streamlit as st
import pandas as pd
from github import Github
import io

# --- CONFIGURACIÓN DE ACCESO SEGURA ---
try:
    # Lee el token desde los Secrets de Streamlit Cloud
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except Exception:
    st.error("⚠️ Configura el GITHUB_TOKEN en los Secrets de Streamlit (Settings > Secrets).")
    st.stop()

# Configuración del repositorio
REPO_NAME = "paesloma/app-gastos-python" 
FILE_PATH = "finanzas.csv"

# Configuración de la página (Layout ancho como en tu diseño)
st.set_page_config(page_title="AppFinanzas Pro - paesloma", layout="wide")

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
        # Crea la estructura base si el archivo no existe
        return pd.DataFrame(columns=["ID", "Tipo", "Concepto", "Monto", "Categoria"]), None

def guardar_en_github(df, sha):
    repo = conectar_github()
    csv_content = df.to_csv(index=False)
    
    # MOSTRAR CONSULTA SENSIBLE
    st.info(f"🔍 Sincronizando con el repositorio: {REPO_NAME}")
    
    if sha:
        repo.update_file(FILE_PATH, "Actualización desde AppFinanzas", csv_content, sha)
    else:
        repo.create_file(FILE_PATH, "Carga inicial de datos", csv_content)

# --- INICIO DE LA APLICACIÓN ---
st.title("💰 AppFinanzas Pro: Dashboard de Control")
df, sha = cargar_datos_de_github()

# --- SIDEBAR: REGISTRO DE TRANSACCIONES ---
with st.sidebar:
    st.header("➕ Nueva Transacción")
    tipo = st.selectbox("Tipo de Movimiento", ["Ingreso", "Gasto"])
    concepto = st.text_input("Descripción / Concepto")
    monto = st.number_input("Valor ($)", min_value=0.0, format="%.2f")
    categoria = st.selectbox("Categoría", ["Sueldo", "Alimentación", "Transporte", "Vivienda", "Entretenimiento", "Otros"])
    
    if st.button("Guardar en la Nube"):
        if concepto:
            nuevo_id = int(df["ID"].max() + 1) if not df.empty else 1
            nueva_fila = pd.DataFrame([{
                "ID": nuevo_id, 
                "Tipo": tipo, 
                "Concepto": concepto, 
                "Monto": monto, 
                "Categoria": categoria
            }])
            df = pd.concat([df, nueva_fila], ignore_index=True)
            guardar_en_github(df, sha)
            st.success("✅ ¡Sincronizado con GitHub!")
            st.rerun()
        else:
            st.error("Ingresa una descripción.")

# --- CUERPO PRINCIPAL: DASHBOARD Y REPORTES ---
col_stats, col_viz = st.columns([1.5, 1])

with col_stats:
    st.subheader("📋 Historial de Movimientos")
    st.dataframe(df, use_container_width=True)
    
    # BOTÓN DE DESCARGA EXCEL
    if not df.empty:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='MisFinanzas')
        
        st.download_button(
            label="📥 Descargar Reporte en Excel",
            data=buffer.getvalue(),
            file_name=f"Finanzas_{REPO_NAME.split('/')[0]}.xlsx",
            mime="application/vnd.ms-excel"
        )

with col_viz:
    st.subheader("📊 Resumen Comparativo")
    if not df.empty:
        # Agrupamos por tipo para el gráfico de barras
        resumen_tipo = df.groupby('Tipo')['Monto'].sum().reset_index()
        
        # Mapeo de colores: Ingreso -> Verde, Gasto -> Rojo
        color_map = {'Ingreso': '#28a745', 'Gasto': '#dc3545'}
        
        # Gráfico Comparativo Ingresos vs Gastos
        st.bar_chart(
            data=resumen_tipo, 
            x='Tipo', 
            y='Monto', 
            color='Tipo',
            use_container_width=True
        )
        
        # Mostrar totales en texto
        total_ingresos = df[df['Tipo'] == 'Ingreso']['Monto'].sum()
        total_gastos = df[df['Tipo'] == 'Gasto']['Monto'].sum()
        st.metric("Total Ingresos", f"${total_ingresos:,.2f}")
        st.metric("Total Gastos", f"${total_gastos:,.2f}", delta=f"-${total_gastos:,.2f}", delta_color="inverse")

# --- SECCIÓN DE BORRADO ---
if not df.empty:
    with st.expander("🗑️ Gestionar Registros (Borrar)"):
        id_a_borrar = st.number_input("ID del registro a eliminar", min_value=1, step=1)
        if st.button("Confirmar Eliminación"):
            # CONSULTA SENSIBLE
            st.warning(f"Eliminando permanentemente el ID {id_a_borrar}...")
            df = df[df["ID"] != id_a_borrar]
            guardar_en_github(df, sha)
            st.rerun()
