# app.py
import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
from io import BytesIO

# -----------------------
# CONFIG
# -----------------------
st.set_page_config(page_title="Gestor de Notas MGEP", layout="wide")
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

ALUMNOS_FILE = os.path.join(DATA_DIR, "alumnos.csv")
GRADES_FILE = os.path.join(DATA_DIR, "grades.csv")        # guarda una fila por alumno-modulo-evaluacion
RA_CONFIG_FILE = os.path.join(DATA_DIR, "ra_config.json") # config por modulo
FEEDBACK_FILE = os.path.join(DATA_DIR, "feedback.csv")    # feedback por alumno-evaluacion

EVALUATIONS = ["Diciembre", "Marzo", "OR1", "OR2"]

MODULES = [
    "Sistema Mekatronikoen Integrazioa",
    "Sistema Pneumatiko eta Hidraulikoak",
    "Fabrikazio Prozesuak",
    "Marrazketa Teknikoa",
    "Digitalizazioa",
    "EIP I",
    "Sistema Elektriko eta Elektronikoak"
]

# -----------------------
# UTIL FUNCTIONS
# -----------------------
def read_csv(path, **kwargs):
    if os.path.exists(path):
        return pd.read_csv(path, **kwargs)
    return pd.DataFrame()

def save_csv(df, path):
    df.to_csv(path, index=False)

def load_ra_config():
    if os.path.exists(RA_CONFIG_FILE):
        with open(RA_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_ra_config(data):
    with open(RA_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def ensure_students_df():
    df = read_csv(ALUMNOS_FILE)
    if df.empty:
        # columnas esperadas
        df = pd.DataFrame(columns=["Nombre", "Apellidos", "IDAL", "Estado"])
    return df

def ensure_grades_df():
    df = read_csv(GRADES_FILE)
    if df.empty:
        # columnas: IDAL, Nombre, Apellidos, Modulo, Evaluacion, NotaFinal, Asistencia, NC (bool), RA_json, timestamp
        df = pd.DataFrame(columns=["IDAL","Nombre","Apellidos","Modulo","Evaluacion","NotaFinal","Asistencia","NC","RA_json","timestamp"])
    return df

def ensure_feedback_df():
    df = read_csv(FEEDBACK_FILE)
    if df.empty:
        df = pd.DataFrame(columns=["IDAL","Nombre","Apellidos","Evaluacion","Feedback","timestamp"])
    return df

def calc_final_from_ras(ras, asistencia):
    """
    ras: list of dicts [{"nombre":..., "peso": float, "nota": float}, ...]
    asistencia: float 0-100
    Returns: (nota_final:int or None if NC, nc_bool)
    Rules:
     - if asistencia < 80 -> NC True (return None, True)
     - if any nota <5 -> final = 4 (nc False)
     - else weighted sum rounded to nearest int
    """
    if asistencia < 80:
        return (None, True)
    notas = [r["nota"] for r in ras]
    if any(n < 5 for n in notas):
        return (4, False)
    total = sum(r["nota"] * (r["peso"]/100.0) for r in ras)
    return (int(round(total)), False)

def pivot_grades_for_evaluation(grades_df, students_df, evaluation):
    """
    Build a table where each row is a student and columns for each module: Grade_ModX and Asist_ModX
    """
    # filter by evaluation
    df_e = grades_df[grades_df["Evaluacion"] == evaluation].copy()
    # ensure RA_json exists
    # create grade column name per module
    data = students_df.copy()
    data = data.rename(columns={"IDAL":"IDAL","Nombre":"Nombre","Apellidos":"Apellidos"})
    # for each module add grade and asistencia columns
    for mod in MODULES:
        col_grade = f"{mod} - Nota"
        col_asist = f"{mod} - Asistencia"
        data[col_grade] = ""
        data[col_asist] = ""
    # fill from df_e
    for _, row in df_e.iterrows():
        idal = str(row["IDAL"])
        mod = row["Modulo"]
        grade = row["NotaFinal"]
        asist = row["Asistencia"]
        mask = data["IDAL"].astype(str) == idal
        if mask.any():
            data.loc[mask, f"{mod} - Nota"] = grade
            data.loc[mask, f"{mod} - Asistencia"] = asist
    return data

def df_to_excel_bytes(df):
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    return out.getvalue()

# -----------------------
# UI
# -----------------------
st.title("📚 Gestor de Notas — MGEP")
st.write("Sistema para gestión de alumnos, configuración de RAs por módulo, introducción de notas y 'Ebaluazio Bilera' para tutores.")
st.markdown("---")

role = st.sidebar.selectbox("Selecciona rola", ["Irakaslea", "Tutorea"])
user_name = st.sidebar.text_input("Zure izena (erabiltzaile):", value="")

# -----------------------
# TUTORE MODE
# -----------------------
if role == "Tutorea":
    st.header("👩‍🏫 Tutore - Kudeaketa eta Ebaluazio Bilera")
    students_df = ensure_students_df()

    st.subheader("1) Ikasleak: inportatu / ikus / editatu")
    col1, col2 = st.columns([2,1])
    with col1:
        uploaded = st.file_uploader("Igo ikasle fitxategia (.xlsx / .xls / .csv). Zutabeak: Nombre, Apellidos, IDAL, Estado", type=["xlsx","xls","csv"])
        if uploaded:
            try:
                if uploaded.name.lower().endswith(".csv"):
                    df_new = pd.read_csv(uploaded)
                else:
                    df_new = pd.read_excel(uploaded)
                # Validate columns
                required = {"Nombre","Apellidos","IDAL","Estado"}
                if not required.issubset(set(df_new.columns)):
                    st.error(f"Fitxategiak beharrezko zutabeak eduki behar ditu: {required}. Zure zutabeak: {list(df_new.columns)}")
                else:
                    save_csv(df_new, ALUMNOS_FILE)
                    students_df = df_new
                    st.success("Ikasleen zerrenda gorde da.")
            except Exception as e:
                st.error("Errorea fitxategia kargatzean: " + str(e))
    with col2:
        if st.button("🗑️ Ezabatu ikasle fitxategia"):
            if os.path.exists(ALUMNOS_FILE):
                os.remove(ALUMNOS_FILE)
            st.success("Ikasle fitxategia ezabatu da.")
            students_df = ensure_students_df()

    st.markdown("### Uneko ikasle zerrenda")
    st.dataframe(students_df)

    st.markdown("---")
    st.subheader("2) Ebaluazio Bilera (tutorearentzako)")

    grades_df = ensure_grades_df()
    feedback_df = ensure_feedback_df()

    eval_choice = st.selectbox("Aukeratu ebaluazioa ikusi/editatzeko:", EVALUATIONS)

    if grades_df.empty:
        st.info("Oraindik ez dago gordetako notarik.")
    else:
        # build pivot table of grades per student for selected evaluation
        pivot = pivot_grades_for_evaluation(grades_df, students_df, eval_choice)

        # merge feedback if exists
        fb = feedback_df[feedback_df["Evaluacion"] == eval_choice]
        if not fb.empty:
            # use IDAL as key
            pivot = pivot.merge(fb[["IDAL","Feedback"]], left_on="IDAL", right_on="IDAL", how="left")
        else:
            pivot["Feedback"] = ""

        st.markdown("### 📊 Gela osoaren taula (moduluak eta asistentziak)")
        # make editable: allow editing only the Feedback column (we'll restrict to that visually)
        # Using st.experimental_data_editor (or st.data_editor) to allow edit. We will not let user edit grade cells in ET.
        edited = st.data_editor(pivot, num_rows="dynamic", use_container_width=True)

        # Save feedback button: extract IDAL + Feedback + Evaluacion
        if st.button("💾 Gorde feedback guztiak"):
            # build feedback df rows
            new_fb_rows = []
            for _, r in edited.iterrows():
                idal = r.get("IDAL")
                feedback_text = r.get("Feedback","")
                if pd.isna(idal):
                    continue
                new_fb_rows.append({
                    "IDAL": idal,
                    "Nombre": r.get("Nombre",""),
                    "Apellidos": r.get("Apellidos",""),
                    "Evaluacion": eval_choice,
                    "Feedback": feedback_text,
                    "timestamp": datetime.now().isoformat()
                })
            if new_fb_rows:
                new_fb_df = pd.DataFrame(new_fb_rows)
                # remove previous feedbacks for this evaluation and replace
                fb_all = ensure_feedback_df()
                fb_all = fb_all[fb_all["Evaluacion"] != eval_choice]
                fb_all = pd.concat([fb_all, new_fb_df], ignore_index=True)
                save_csv(fb_all, FEEDBACK_FILE)
                st.success("Feedback guztiak gorde dira.")
            else:
                st.info("Ez da feedbackik aurkitu gordetzeko.")

        # Export to Excel
        if st.button("📤 Deskargatu ebaluazioaren txostena Excel (.xlsx)"):
            to_export = edited.copy()
            # include timestamp
            to_export["Exported_at"] = datetime.now().isoformat()
            b = df_to_excel_bytes(to_export)
            st.download_button("Deskargatu hemen", data=b, file_name=f"ebaluazioa_{eval_choice}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# -----------------------
# TEACHER MODE
# -----------------------
else:
    st.header("👨‍🏫 Irakaslea - konfigurazioa eta sarrera de notak")
    students_df = ensure_students_df()
    if students_df.empty:
        st.warning("Ez daude ikasleak erregistratuta. Tutoreak gehitu behar ditu lehenik.")
        st.stop()

    ra_config = load_ra_config()
    grades_df = ensure_grades_df()
    feedback_df = ensure_feedback_df()

    # Teacher selects module and evaluation and student
    colA, colB, colC = st.columns([2,2,3])
    with colA:
        mod = st.selectbox("Aukeratu modulua", MODULES)
    with colB:
        evaluation = st.selectbox("Ebaluazioa", EVALUATIONS)
    with colC:
        student_display = st.selectbox("Aukeratu ikaslea", students_df["Nombre"] + " " + students_df["Apellidos"])
        student_idal = students_df.loc[(students_df["Nombre"] + " " + students_df["Apellidos"]) == student_display, "IDAL"].astype(str).values[0]

    st.markdown("---")
    st.subheader(f"1) RA konfigurazioa - {mod}")

    # If no config, ask and save (only once unless edited)
    if mod not in ra_config:
        st.info("Oraindik ez dago modulu honen RA konfiguraziorik. Zehaztu kopurua eta pisuak (batura = 100%).")
        num_ras = st.number_input("Zenbat RA ditu modulu honek?", min_value=1, max_value=12, value=3, step=1)
        temp = []
        total = 0
        for i in range(int(num_ras)):
            col1, col2 = st.columns([3,1])
            with col1:
                name = st.text_input(f"RA {i+1} izena (aukerakoa)", key=f"new_ra_name_{i}")
            with col2:
                peso = st.number_input(f"RA {i+1} pisua (%)", min_value=0, max_value=100, value=int(100/num_ras), key=f"new_ra_peso_{i}")
            temp.append({"nombre": name, "peso": peso})
            total += peso
        if total != 100:
            st.warning(f"Pisuen batura = {total}%. 100% izan behar du.")
        if st.button("💾 Gorde RA konfigurazioa (modulu hau)"):
            if total == 100:
                ra_config[mod] = temp
                save_ra_config(ra_config)
                st.success("RA konfigurazioa gorde da.")
                st.experimental_rerun()
            else:
                st.error("Zuzenketa egin: pisuen batura 100% izan behar da.")
        st.stop()
    else:
        st.write("Modulu honetako RA konfigurazioa (gordeta):")
        cfg = ra_config[mod]
        df_cfg = pd.DataFrame(cfg)
        st.dataframe(df_cfg)

        if st.checkbox("🔁 Editatu RA konfigurazioa"):
            st.warning("Editatzeak eragina izango du ondorengo kalkuluetan; ziurtatu pisuak zuzen daudela.")
            new_list = []
            total2 = 0
            for i, ra in enumerate(cfg):
                col1, col2 = st.columns([3,1])
                with col1:
                    name = st.text_input(f"RA {i+1} izena", value=ra.get("nombre",""), key=f"edit_name_{i}")
                with col2:
                    peso = st.number_input(f"RA {i+1} pisua (%)", min_value=0, max_value=100, value=ra.get("peso",0), key=f"edit_peso_{i}")
                new_list.append({"nombre": name, "peso": peso})
                total2 += peso
            if total2 != 100:
                st.warning(f"Pisuen batura = {total2}%. 100% izan behar da.")
            if st.button("💾 Gorde aldaketak (RA konfigurazioa)"):
                if total2 == 100:
                    ra_config[mod] = new_list
                    save_ra_config(ra_config)
                    st.success("Konfigurazioa eguneratu da.")
                    st.experimental_rerun()
                else:
                    st.error("Zuzenketa egin: pisuen batura 100% izan behar da.")

    st.markdown("---")
    st.subheader("2) Notak sartu - RA bakoitzeko")

    # Get RA config for this module
    ras = ra_config.get(mod, [])
    if not ras:
        st.error("Modulu honetarako ez dago RA konfiguraziorik. Sortu lehendik edo eskatu tutoreari.")
        st.stop()

    # Show RA names and input fields for this student and evaluation
    st.markdown(f"Aukeratutako ikaslea: **{student_display}** (IDAL: {student_idal})")
    st.markdown(f"Modulua: **{mod}** — Ebaluazioa: **{evaluation}**")

    ra_inputs = []
    for i, ra in enumerate(ras):
        name = ra.get("nombre","")
        peso = ra.get("peso",0)
        col1, col2 = st.columns([3,1])
        with col1:
            st.write(f"RA {i+1} - {name}")
        with col2:
            nota = st.number_input(f"RA{i+1} nota (0-10)", min_value=0.0, max_value=10.0, step=0.1, key=f"input_ra_note_{mod}_{student_idal}_{evaluation}_{i}")
        ra_inputs.append({"nombre": name, "peso": peso, "nota": nota})

    asistencia = st.number_input("Asistentzia (%)", min_value=0, max_value=100, step=1, key=f"asist_{mod}_{student_idal}_{evaluation}")

    if st.button("💾 Kalkulatu eta gorde notak"):
        # compute final according to rules
        nota_final, nc = calc_final_from_ras(ra_inputs, asistencia)
        timestamp = datetime.now().isoformat()
        grades_all = ensure_grades_df()
        # remove previous entry for same student-mod-eval
        grades_all = grades_all[~((grades_all["IDAL"].astype(str) == str(student_idal)) & (grades_all["Modulo"] == mod) & (grades_all["Evaluacion"] == evaluation))]
        ra_json = json.dumps(ra_inputs, ensure_ascii=False)
        new_row = {
            "IDAL": student_idal,
            "Nombre": student_display.split(" ")[0],
            "Apellidos": " ".join(student_display.split(" ")[1:]),
            "Modulo": mod,
            "Evaluacion": evaluation,
            "NotaFinal": nota_final,
            "Asistencia": asistencia,
            "NC": nc,
            "RA_json": ra_json,
            "timestamp": timestamp
        }
        grades_all = pd.concat([grades_all, pd.DataFrame([new_row])], ignore_index=True)
        save_csv(grades_all, GRADES_FILE)
        if nc:
            st.warning(f"{student_display} → {mod} ({evaluation}): N.C. (asistentzia {asistencia}%)")
        else:
            if nota_final == 4:
                st.warning(f"{student_display} → {mod} ({evaluation}): NOTA = 4 (RA baten nota < 5).")
            else:
                st.success(f"{student_display} → {mod} ({evaluation}): NOTA = {nota_final}")

    st.markdown("---")
    st.subheader("3) Ikusi eta esportatu notak (gela/irakasle moduan)")

    grades_all = ensure_grades_df()
    if grades_all.empty:
        st.info("Ez dago gordetako notarik.")
    else:
        # allow teacher to filter by module / evaluation
        fcol1, fcol2 = st.columns([2,2])
        with fcol1:
            filt_mod = st.selectbox("Irakasgaiaren filtroa (All = denak)", ["All"] + MODULES)
        with fcol2:
            filt_eval = st.selectbox("Ebaluazio filtroa (All = denak)", ["All"] + EVALUATIONS)
        df_show = grades_all.copy()
        if filt_mod != "All":
            df_show = df_show[df_show["Modulo"] == filt_mod]
        if filt_eval != "All":
            df_show = df_show[df_show["Evaluacion"] == filt_eval]
        # Merge with student names for safety
        students_df["IDAL"] = students_df["IDAL"].astype(str)
        df_show["IDAL"] = df_show["IDAL"].astype(str)
        merged = df_show.merge(students_df, on="IDAL", how="left")
        # display
        display_cols = ["IDAL","Nombre_x","Apellidos_x","Modulo","Evaluacion","NotaFinal","Asistencia","NC"]
        # rename for clarity
        if not merged.empty:
            merged = merged.rename(columns={"Nombre_x":"Nombre","Apellidos_x":"Apellidos"})
            st.dataframe(merged[["IDAL","Nombre","Apellidos","Modulo","Evaluacion","NotaFinal","Asistencia","NC","timestamp"]], use_container_width=True)
            # Export CSV / XLSX
            csv_bytes = merged.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Deskargatu CSV", data=csv_bytes, file_name=f"grades_export.csv", mime="text/csv")
            xlsx_bytes = df_to_excel_bytes(merged)
            st.download_button("📤 Deskargatu Excel (.xlsx)", data=xlsx_bytes, file_name=f"grades_export.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("Ez dago filtrora egokitzen den daturik.")
