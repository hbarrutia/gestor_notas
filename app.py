import streamlit as st
import pandas as pd
import os
import math
import json

# ===============================
# KONFIGURAZIOA
# ===============================

st.set_page_config(page_title="Gestor de Notas MGEP", layout="wide")

DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

ALUMNOS_FILE = os.path.join(DATA_DIR, "alumnos.csv")
NOTAS_FILE = os.path.join(DATA_DIR, "notas.csv")
RA_FILE = os.path.join(DATA_DIR, "ra_config.json")

# ===============================
# LAGUNTZA FUNTZIOAK
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

def cargar_ra_config():
    if os.path.exists(RA_FILE):
        with open(RA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_ra_config(data):
    with open(RA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ===============================
# MODULUAK
# ===============================

modulos = [
    "Sistema Mekatronikoen Integrazioa",
    "Sistema Pneumatiko eta Hidraulikoak",
    "Fabrikazio Prozesuak",
    "Marrazketa Teknikoa",
    "Digitalizazioa",
    "EIP I",
    "Sistema Elektriko eta Elektronikoak"
]

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

    ra_config = cargar_ra_config()

    alumno = st.selectbox("Aukeratu ikaslea", alumnos_df["Nombre"] + " " + alumnos_df["Apellidos"])
    modulo = st.selectbox("Aukeratu modulua", modulos)
    evaluacion = st.selectbox("Ebaluazioa", ["Diciembre", "Marzo", "OR1", "OR2"])

    # ===============================
    # 1️⃣ MODULUAREN RA KONFIGURAZIOA
    # ===============================

    if modulo not in ra_config:
        st.subheader(f"⚙️ {modulo} moduluko RA konfigurazioa (lehen aldia)")
        num_ras = st.number_input("Zenbat RA ditu modulu honek?", min_value=1, max_value=10, step=1)
        ra_temp = []
        total_peso = 0
        for i in range(int(num_ras)):
            col1, col2 = st.columns(2)
            with col1:
                pisua = st.number_input(f"RA{i+1} pisua (%)", min_value=0, max_value=100, step=1, key=f"peso_{i}")
            with col2:
                izena = st.text_input(f"RA{i+1} izena (aukerakoa)", key=f"izena_{i}")
            total_peso += pisua
            ra_temp.append({"izena": izena, "pisua": pisua})
        if total_peso != 100:
            st.warning(f"⚠️ Pisuen batura {total_peso}% da, 100% izan behar du.")
        if st.button("💾 Gorde RA konfigurazioa"):
            if total_peso == 100:
                ra_config[modulo] = ra_temp
                guardar_ra_config(ra_config)
                st.success(f"{modulo} moduluko RA konfigurazioa gorde da.")
                st.rerun()
            else:
                st.error("Pisuen batura 100% izan behar du.")
        st.stop()
    else:
        # Berrikusi eta editatu aukera
        if st.checkbox("🔁 Ikusi eta editatu RA konfigurazioa"):
            st.subheader(f"{modulo} moduluko RA konfigurazioa editatu")
            ra_temp = []
            total_peso = 0
            for i, ra in enumerate(ra_config[modulo]):
                col1, col2 = st.columns(2)
                with col1:
                    izena = st.text_input(f"RA{i+1} izena", value=ra['izena'], key=f"edit_izena_{i}")
                with col2:
                    pisua = st.number_input(f"RA{i+1} pisua (%)", min_value=0, max_value=100, step=1, value=ra['pisua'], key=f"edit_pisua_{i}")
                total_peso += pisua
                ra_temp.append({"izena": izena, "pisua": pisua})
            if total_peso != 100:
                st.warning(f"⚠️ Pisuen batura {total_peso}% da, 100% izan behar du.")
            if st.button("💾 Aldaketak gorde"):
                if total_peso == 100:
                    ra_config[modulo] = ra_temp
                    guardar_ra_config(ra_config)
                    st.success("RA konfigurazioa eguneratu da.")
                    st.rerun()
                else:
                    st.error("Pisuen batura 100% izan behar du.")
            st.stop()

    # ===============================
    # 2️⃣ NOTAK ETA KALKULUA
    # ===============================

    st.subheader(f"📊 {modulo} - {evaluacion} ebaluazioa")
    ras = ra_config[modulo]

    notas = []
    total_peso = 0
    for i, ra in enumerate(ras):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**RA{i+1}** {ra['izena'] or ''}")
        with col2:
            nota = st.number_input(f"RA{i+1} nota (0-10)", min_value=0.0, max_value=10.0, step=0.1, key=f"nota_ra_{i}")
        notas.append((ra["pisua"], nota))
        total_peso += ra["pisua"]

    asistencia = st.number_input("Asistentzia (%)", min_value=0, max_value=100, step=1)

    if st.button("💾 Kalkulatu eta gorde nota"):
        if asistencia < 80:
            nota_final = None
            nc = True
        else:
            nota_final = sum(p * n for p, n in notas) / 100
            nota_final = int(round(nota_final))
            nc = False

        idal = alumnos_df.loc[alumnos_df["Nombre"] + " " + alumnos_df["Apellidos"] == alumno, "IDAL"].values[0]
        notas_df = cargar_notas()
        notas_df = notas_df[~((notas_df["IDAL"] == idal) &
                              (notas_df["Modulo"] == modulo) &
                              (notas_df["Evaluacion"] == evaluacion))]
        berria = pd.DataFrame([[idal, modulo, evaluacion, nota_final, asistencia, nc]],
                              columns=["IDAL", "Modulo", "Evaluacion", "NotaFinal", "Asistencia", "NC"])
        notas_df = pd.concat([notas_df, berria], ignore_index=True)
        guardar_notas(notas_df)

        if nc:
            st.warning(f"{alumno} → {modulo} ({evaluacion}): N.C. (asistentzia {asistencia}%)")
        else:
            st.success(f"{alumno} → {modulo} ({evaluacion}) = {nota_final}")

    # ===============================
    # 3️⃣ TAULA OSOA
    # ===============================

    st.subheader("📋 Noten taula osoa")
    notas_df = cargar_notas()
    if not notas_df.empty:
        merged = notas_df.merge(alumnos_df, on="IDAL", how="left")
        st.dataframe(merged[["Nombre","Apellidos","Modulo","Evaluacion","NotaFinal","Asistencia","NC"]])
    else:
        st.info("Oraindik ez dago notarik gordeta.")
