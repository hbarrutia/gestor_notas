import streamlit as st
import pandas as pd
import os

# ===============================
# CONFIGURACIÓN INICIAL
# ===============================

st.set_page_config(page_title="Gestor de Notas", layout="wide")

# Carpeta donde se guardarán los datos
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

ALUMNOS_FILE = os.path.join(DATA_DIR, "alumnos.csv")
NOTAS_FILE = os.path.join(DATA_DIR, "notas.csv")

# ===============================
# FUNCIONES AUXILIARES
# ===============================

def cargar_alumnos():
    if os.path.exists(ALUMNOS_FILE):
        return pd.read_csv(ALUMNOS_FILE)
    else:
        return pd.DataFrame(columns=["Nombre", "Apellidos", "IDAL", "Estado"])

def guardar_alumnos(df):
    df.to_csv(ALUMNOS_FILE, index=False)

def cargar_notas():
    if os.path.exists(NOTAS_FILE):
        return pd.read_csv(NOTAS_FILE)
    else:
        return pd.DataFrame(columns=["IDAL", "Modulo", "Evaluacion", "Nota"])

def guardar_notas(df):
    df.to_csv(NOTAS_FILE, index=False)

# ===============================
# ROLES Y USUARIOS
# ===============================

st.sidebar.title("Gestor de Notas - MGEP")
rol = st.sidebar.selectbox("Zure rola hautatu", ["Irakaslea", "Tutorea"])
usuario = st.sidebar.text_input("Zure izena (irakaslea)")

# ===============================
# BLOQUE DEL TUTOR
# ===============================

if rol == "Tutorea":
    st.header("👩‍🏫 Kudeatu ikasleen zerrenda")

    alumnos_df = cargar_alumnos()

    metodo = st.radio("Nola gehitu nahi dituzu ikasleak?", ["Excel fitxategitik", "Eskuzko sarrera"])

    if metodo == "Excel fitxategitik":
        archivo = st.file_uploader("Igo .xls edo .xlsx fitxategia", type=["xls", "xlsx"])
        if archivo:
            df_nuevo = pd.read_excel(archivo)
            columnas_esperadas = ["Nombre", "Apellidos", "IDAL", "Estado"]
            if all(col in df_nuevo.columns for col in columnas_esperadas):
                guardar_alumnos(df_nuevo)
                st.success("📥 Ikasleen zerrenda eguneratu da fitxategitik!")
            else:
                st.error(f"Fitxategiak ez ditu beharrezko zutabeak: {columnas_esperadas}")
    else:
        with st.form("form_alumnos"):
            nombre = st.text_input("Izena")
            apellidos = st.text_input("Abizenak")
            idal = st.text_input("IDAL (matrikula zenbakia)")
            estado = st.text_input("Egoera (aktibo, baja...)")
            submit = st.form_submit_button("Gehitu ikaslea")
            if submit:
                nuevo = pd.DataFrame([[nombre, apellidos, idal, estado]], columns=["Nombre", "Apellidos", "IDAL", "Estado"])
                alumnos_df = pd.concat([alumnos_df, nuevo], ignore_index=True)
                guardar_alumnos(alumnos_df)
                st.success(f"{nombre} {apellidos} gehitu da.")

    st.subheader("📋 Uneko ikasleen zerrenda")
    st.dataframe(alumnos_df)

# ===============================
# BLOQUE DEL PROFESOR
# ===============================

elif rol == "Irakaslea":
    st.header("🧮 Sartu ikasleen notak")

    alumnos_df = cargar_alumnos()

    if alumnos_df.empty:
        st.warning("Ez dago ikaslerik erregistratuta. Tutoreak lehenik zerrenda igo behar du.")
        st.stop()

    # --- Módulos con nombres ---
    modulos = {
        "Sistema Mekatronikoen Integrazioa": 1,
        "Sistema Pneumatiko eta Hidraulikoak": 2,
        "Fabrikazio Prozesuak": 3,
        "Marrazketa Teknikoa": 4,
        "Digitalizazioa": 5,
        "EIP I": 6,
        "Sistema Elektriko eta Elektronikoak": 7
    }

    # Selección de alumno y módulo
    alumno = st.selectbox("Aukeratu ikaslea", alumnos_df["Nombre"] + " " + alumnos_df["Apellidos"])
    modulo_nombre = st.selectbox("Aukeratu modulua", list(modulos.keys()))
    modulo = modulos[modulo_nombre]

    evaluacion = st.selectbox("Ebaluazioa", ["Diciembre", "Marzo", "OR1", "OR2"])
    nota = st.number_input("Sartu nota (0-10)", 0.0, 10.0, step=0.1)

    if st.button("💾 Gorde nota"):
        notas_df = cargar_notas()
        idal = alumnos_df.loc[alumnos_df["Nombre"] + " " + alumnos_df["Apellidos"] == alumno, "IDAL"].values[0]

        # Si ya existe nota, la reemplaza
        notas_df = notas_df[
            ~((notas_df["IDAL"] == idal) &
              (notas_df["Modulo"] == modulo) &
              (notas_df["Evaluacion"] == evaluacion))
        ]

        nueva_nota = pd.DataFrame([[idal, modulo, evaluacion, nota]], columns=["IDAL", "Modulo", "Evaluacion", "Nota"])
        notas_df = pd.concat([notas_df, nueva_nota], ignore_index=True)
        guardar_notas(notas_df)

        st.success(f"{alumno} ikaslearen nota gorde da {modulo_nombre} ({evaluacion}) moduluan.")

    # --- Mostrar todas las notas ---
    st.subheader("📊 Noten taula osoa")
    notas_df = cargar_notas()
    if not notas_df.empty:
        notas_merged = notas_df.merge(alumnos_df, on="IDAL", how="left")
        notas_merged["Modulo"] = notas_merged["Modulo"].map({v: k for k, v in modulos.items()})
        st.dataframe(notas_merged[["Nombre", "Apellidos", "Modulo", "Evaluacion", "Nota"]])
    else:
        st.info("Oraindik ez dago notarik gordeta.")
