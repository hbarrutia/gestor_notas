import streamlit as st
import pandas as pd
import os
import math

# ===============================
# KONFIGURAZIO OROKORRA
# ===============================

st.set_page_config(page_title="Gestor de Notas MGEP", layout="wide")

DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

ALUMNOS_FILE = os.path.join(DATA_DIR, "alumnos.csv")
NOTAS_FILE = os.path.join(DATA_DIR, "notas.csv")

# ===============================
# FUNTZIO LAGUNGARRIAK
# ===============================

def cargar_alumnos():
    if os.path.exists(ALUMNOS_FILE):
        return pd.read_csv(ALUMNOS_FILE)
    return pd.DataFrame(columns=["Nombre", "Apellidos", "IDAL", "Estado"])

def guardar_alumnos(df):
    df.to_csv(ALUMNOS_FILE, index=False)

def cargar_notas():
    if os.path.exists(NOTAS_FILE):
        return pd.read_csv(NOTAS_FILE)
    return pd.DataFrame(columns=["IDAL", "Modulo", "Evaluacion", "NotaFinal", "Asistencia", "NC"])

def guardar_notas(df):
    df.to_csv(NOTAS_FILE, index=False)

# ===============================
# MODULUEN ZERRENDA
# ===============================

modulos = {
    "Sistema Mekatronikoen Integrazioa": 1,
    "Sistema Pneumatiko eta Hidraulikoak": 2,
    "Fabrikazio Prozesuak": 3,
    "Marrazketa Teknikoa": 4,
    "Digitalizazioa": 5,
    "EIP I": 6,
    "Sistema Elektriko eta Elektronikoak": 7
}

# ===============================
# SAIOAREN ROLA
# ===============================

st.sidebar.title("Gestor de Notas - MGEP")
rol = st.sidebar.selectbox("Zure rola hautatu", ["Irakaslea", "Tutorea"])
usuario = st.sidebar.text_input("Zure izena (irakaslea/tutorea)")

# ===============================
# TUTOREAREN BLOKEA
# ===============================

if rol == "Tutorea":
    st.header("👩‍🏫 Ikasleen kudeaketa")
    alumnos_df = cargar_alumnos()

    metodo = st.radio("Nola gehitu nahi dituzu ikasleak?", ["Excel fitxategitik", "Eskuzko sarrera"])

    if metodo == "Excel fitxategitik":
        archivo = st.file_uploader("Igo .xls edo .xlsx fitxategia", type=["xls", "xlsx"])
        if archivo:
            df_nuevo = pd.read_excel(archivo)
            beharrezkoak = ["Nombre", "Apellidos", "IDAL", "Estado"]
            if all(c in df_nuevo.columns for c in beharrezkoak):
                guardar_alumnos(df_nuevo)
                alumnos_df = df_nuevo
                st.success("📥 Ikasleen zerrenda eguneratu da fitxategitik!")
            else:
                st.error(f"Fitxategiak zutabe hauek behar ditu: {beharrezkoak}")
    else:
        with st.form("form_alumnos"):
            nombre = st.text_input("Izena")
            apellidos = st.text_input("Abizenak")
            idal = st.text_input("IDAL")
            estado = st.text_input("Egoera (Aktibo/Baja...)")
            submit = st.form_submit_button("Gehitu ikaslea")
            if submit:
                berria = pd.DataFrame([[nombre, apellidos, idal, estado]], columns=["Nombre","Apellidos","IDAL","Estado"])
                alumnos_df = pd.concat([alumnos_df, berria], ignore_index=True)
                guardar_alumnos(alumnos_df)
                st.success(f"{nombre} {apellidos} gehitu da.")

    # Beti erakutsi taula behean
    st.subheader("📋 Ikasleen zerrenda")
    if not alumnos_df.empty:
        st.dataframe(alumnos_df)
    else:
        st.info("Ez dago ikaslerik oraindik.")

# ===============================
# IRAKASLEAREN BLOKEA
# ===============================

elif rol == "Irakaslea":
    st.header("🧮 Noten kudeaketa")

    alumnos_df = cargar_alumnos()
    if alumnos_df.empty:
        st.warning("Ez dago ikaslerik. Tutoreak lehenik zerrenda igo behar du.")
        st.stop()

    alumno = st.selectbox("Aukeratu ikaslea", alumnos_df["Nombre"] + " " + alumnos_df["Apellidos"])
    modulo_nombre = st.selectbox("Aukeratu modulua", list(modulos.keys()))
    evaluacion = st.selectbox("Ebaluazioa", ["Diciembre", "Marzo", "OR1", "OR2"])

    # Zenbat RA ditu?
    num_ras = st.number_input("Zenbat ikas-emaitza (RA) ditu modulu honek?", min_value=1, max_value=10, step=1)

    ras = []
    total_peso = 0
    for i in range(int(num_ras)):
        col1, col2 = st.columns(2)
        with col1:
            peso = st.number_input(f"RA{i+1} pisua (%)", min_value=0, max_value=100, step=1, key=f"peso_{i}")
        with col2:
            nota = st.number_input(f"RA{i+1} nota (0-10)", min_value=0.0, max_value=10.0, step=0.1, key=f"nota_{i}")
        ras.append((peso, nota))
        total_peso += peso

    if total_peso != 100:
        st.warning(f"⚠️ Pisuen batura {total_peso}% da, 100% izan behar du.")

    asistencia = st.number_input("Asistentzia (%)", min_value=0, max_value=100, step=1)

    if st.button("💾 Kalkulatu eta gorde"):
        if total_peso != 100:
            st.error("Pisuen batura ez da 100%.")
        else:
            if asistencia < 80:
                nota_final = None
                nc = True
            else:
                nota_final = sum(p * n for p, n in ras) / 100
                nota_final = int(round(nota_final))
                nc = False

            idal = alumnos_df.loc[alumnos_df["Nombre"] + " " + alumnos_df["Apellidos"] == alumno, "IDAL"].values[0]
            notas_df = cargar_notas()
            notas_df = notas_df[~((notas_df["IDAL"] == idal) & 
                                  (notas_df["Modulo"] == modulo_nombre) &
                                  (notas_df["Evaluacion"] == evaluacion))]
            berria = pd.DataFrame([[idal, modulo_nombre, evaluacion, nota_final, asistencia, nc]],
                                  columns=["IDAL", "Modulo", "Evaluacion", "NotaFinal", "Asistencia", "NC"])
            notas_df = pd.concat([notas_df, berria], ignore_index=True)
            guardar_notas(notas_df)

            if nc:
                st.warning(f"{alumno} → {modulo_nombre} ({evaluacion}): N.C. (asistentzia {asistencia}%)")
            else:
                st.success(f"{alumno} → {modulo_nombre} ({evaluacion}) = {nota_final}")

    st.subheader("📊 Noten taula")
    notas_df = cargar_notas()
    if not notas_df.empty:
        merged = notas_df.merge(alumnos_df, on="IDAL", how="left")
        st.dataframe(merged[["Nombre","Apellidos","Modulo","Evaluacion","NotaFinal","Asistencia","NC"]])
    else:
        st.info("Oraindik ez dago notarik gordeta.")

