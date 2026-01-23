import streamlit as st
import pandas as pd
from github import Github
import io

# --- CONFIGURACIÓN DE ACCESO ---
# Usando tu llave y ruta de repositorio proporcionadas
GITHUB_TOKEN = "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"
REPO_NAME = "paesloma/app-gastos-python" 
FILE_PATH = "finanzas.csv"

# Configuración visual de Streamlit
st.set_page_config(page_title="AppFinanzas - paesloma", layout="wide")

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
        # Si el archivo no existe aún en el repo, creamos la estructura base
        return pd.DataFrame(columns=["ID", "Tipo", "Concepto", "Monto", "Categoria"]), None

def guardar_en_github(df, sha):
    repo = conectar_github()
    csv_content = df.to_csv(index=False)
    
    # MOSTRAR CONSULTA SENSIBLE (Instrucción de usuario)
    st.info(f"🔍 Ejecutando actualización en GitHub: {REPO_NAME}")
    
    if sha:
        repo.update_file(FILE_PATH, "Actualización de gastos (Streamlit)", csv_content, sha)
    else:
        repo.create_file(FILE_PATH, "Archivo inicial de finanzas", csv_content)

# --- LÓGICA DE LA APLICACIÓN ---
st.title("💰 Gestor de Gastos - Persistencia en GitHub")

# Cargar datos desde la nube al iniciar o refrescar
df, sha = cargar_datos_de_github()

# --- PANEL LATERAL: ENTRADA DE DATOS ---
with st.sidebar:
    st.header("➕ Nueva Transacción")
    tipo = st.selectbox("Tipo de Movimiento", ["Gasto", "Ingreso"])
    concepto = st.text_input("Descripción / Concepto")
    monto = st.number_input("Valor ($)", min_value=0.0, format="%.2f")
    categoria = st.selectbox("Categoría", ["Alimentación", "Transporte", "Vivienda", "Sueldo", "Entretenimiento", "Salud", "Otros"])
    
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
            
            # Persistencia: Sincroniza con GitHub inmediatamente
            guardar_en_github(df, sha)
            st.success("✅ ¡Sincronizado con paesloma/app-gastos-python!")
            st.rerun()
        else:
            st.error("Por favor, ingresa un concepto.")

# --- CUERPO PRINCIPAL: TABLA Y GRÁFICO ---
col_tabla, col_grafico = st.columns([2, 1])

with col_tabla:
    st.subheader("📊 Historial de Movimientos")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        
        # FUNCIONALIDAD DE BORRADO
        st.divider()
        id_a_borrar = st.number_input("ID del registro a eliminar", min_value=1, step=1)
        if st.button("🗑️ Eliminar Definitivamente"):
            if id_a_borrar in df["ID"].values:
                # MOSTRAR CONSULTA SENSIBLE
                st.warning(f"Eliminando registro ID {id_a_borrar} de GitHub...")
                df = df[df["ID"] != id_a_borrar]
                guardar_en_github(df, sha)
                st.rerun()
            else:
                st.error("El ID no existe.")
    else:
        st.write("No hay datos registrados en el repositorio.")

with col_grafico:
    st.subheader("📈 Resumen Visual")
    if not df.empty:
        # Gráfico simple de gastos por categoría
        gastos_only = df[df['Tipo'] == 'Gasto']
        if not gastos_only.empty:
            resumen = gastos_only.groupby('Categoria')['Monto'].sum()
            st.bar_chart(resumen)
        else:
            st.write("Registra al menos un gasto para ver el gráfico.")
