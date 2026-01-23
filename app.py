import streamlit as st
import pandas as pd
import os
import subprocess

# --- CONFIGURACIÓN Y CARGA DE DATOS ---
ARCHIVO = "finanzas.csv"

def cargar_datos():
    if os.path.exists(ARCHIVO):
        return pd.read_csv(ARCHIVO)
    return pd.DataFrame(columns=["ID", "Tipo", "Concepto", "Monto", "Categoria"])

def sincronizar_github():
    try:
        subprocess.run(["git", "add", ARCHIVO])
        subprocess.run(["git", "commit", "-m", "Sincronización automática de datos"])
        subprocess.run(["git", "push", "origin", "main"])
        return True
    except:
        return False

# UI
st.title("💰 App Financiera Enlazada")
df = cargar_datos()

# --- SECCIÓN: AGREGAR ---
with st.sidebar:
    st.header("Registrar")
    tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
    concepto = st.text_input("Concepto")
    monto = st.number_input("Monto", min_value=0.0)
    cat = st.text_input("Categoría")
    
    if st.button("Guardar"):
        nuevo_id = df["ID"].max() + 1 if not df.empty else 1
        nueva_fila = pd.DataFrame([{"ID": nuevo_id, "Tipo": tipo, "Concepto": concepto, "Monto": monto, "Categoria": cat}])
        df = pd.concat([df, nueva_fila], ignore_index=True)
        df.to_csv(ARCHIVO, index=False)
        sincronizar_github()
        st.success("¡Registrado y subido a GitHub!")
        st.rerun()

# --- SECCIÓN: MOSTRAR Y BORRAR ---
st.subheader("Registros Actuales")
st.dataframe(df, use_container_width=True)

if not df.empty:
    id_para_borrar = st.number_input("Ingresa el ID para borrar", min_value=int(df["ID"].min()), step=1)
    if st.button("🗑️ Borrar Registro"):
        # CONSULTA SENSIBLE
        st.warning(f"Eliminando registro ID: {id_para_borrar}")
        df = df[df["ID"] != id_para_borrar]
        df.to_csv(ARCHIVO, index=False)
        sincronizar_github()
        st.rerun()
