# app.py
import streamlit as st
import pandas as pd
import sqlite3
import json
from datetime import datetime
from io import BytesIO

# -----------------------
# Configuración
# -----------------------
DB_FILE = "notas_modulos.db"
import streamlit as st
import os
TUTOR_PASSWORD = st.secrets.get("TUTOR_PASSWORD", "tutor123")
# TUTOR_PASSWORD = "tutor123"  # Cambia esto si quieres otra contraseña de tutor

PERIODOS = ["Diciembre", "Marzo", "OR1", "OR2"]

# -----------------------
# Inicialización DB
# -----------------------
def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    # Tabla alumnos
    c.execute("""
    CREATE TABLE IF NOT EXISTS alumnos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        apellidos TEXT,
        idal TEXT UNIQUE,
        estado TEXT
    )
    """)
    # Tabla resultados (una fila por alumno, módulo, periodo)
    c.execute("""
    CREATE TABLE IF NOT EXISTS resultados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        profesor TEXT,
        alumno_id INTEGER,
        alumno_nombre TEXT,
        modulo INTEGER,
        periodo TEXT,
        ra_json TEXT,          -- JSON con lista de RAs y sus notas/pesos: [{"nombre":"RA1","peso":30,"nota":7.5}, ...]
        asistencia REAL,
        nota_final TEXT,
        FOREIGN KEY (alumno_id) REFERENCES alumnos(id)
    )
    """)
    conn.commit()
    return conn

conn = init_db()

# -----------------------
# Utilidades DB
# -----------------------
def add_alumno(nombre, apellidos, idal, estado=""):
    c = conn.cursor()
    try:
        c.execute("INSERT INTO alumnos (nombre, apellidos, idal, estado) VALUES (?, ?, ?, ?)",
                  (nombre.strip(), apellidos.strip(), idal.strip(), estado.strip()))
        conn.commit()
        return True, None
    except Exception as e:
        return False, str(e)

def update_alumno(alumno_id, nombre, apellidos, idal, estado=""):
    c = conn.cursor()
    try:
        c.execute("UPDATE alumnos SET nombre=?, apellidos=?, idal=?, estado=? WHERE id=?",
                  (nombre.strip(), apellidos.strip(), idal.strip(), estado.strip(), alumno_id))
        conn.commit()
        return True, None
    except Exception as e:
        return False, str(e)

def delete_alumno(alumno_id):
    c = conn.cursor()
    try:
        c.execute("DELETE FROM alumnos WHERE id=?", (alumno_id,))
        conn.commit()
        return True, None
    except Exception as e:
        return False, str(e)

def list_alumnos():
    c = conn.cursor()
    c.execute("SELECT id, nombre, apellidos, idal, estado FROM alumnos ORDER BY nombre, apellidos")
    rows = c.fetchall()
    df = pd.DataFrame(rows, columns=["id", "nombre", "apellidos", "idal", "estado"])
    return df

def save_result(profesor, alumno_id, alumno_nombre, modulo, periodo, ra_list, asistencia, nota_final):
    c = conn.cursor()
    fecha = datetime.now().isoformat()
    ra_json = json.dumps(ra_list, ensure_ascii=False)
    c.execute("""
        INSERT INTO resultados (fecha, profesor, alumno_id, alumno_nombre, modulo, periodo, ra_json, asistencia, nota_final)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (fecha, profesor, alumno_id, alumno_nombre, modulo, periodo, ra_json, asistencia, str(nota_final)))
    conn.commit()

def load_results(filter_profesor=None, filter_modulo=None, filter_periodo=None):
    c = conn.cursor()
    query = "SELECT id, fecha, profesor, alumno_id, alumno_nombre, modulo, periodo, ra_json, asistencia, nota_final FROM resultados WHERE 1=1"
    params = []
    if filter_profesor:
        query += " AND profesor = ?"
        params.append(filter_profesor)
    if filter_modulo:
        query += " AND modulo = ?"
        params.append(filter_modulo)
    if filter_periodo:
        query += " AND periodo = ?"
        params.append(filter_periodo)
    query += " ORDER BY fecha DESC"
    c.execute(query, params)
    rows = c.fetchall()
    data = []
    for r in rows:
        id_, fecha, profesor, alumno_id, alumno_nombre, modulo, periodo, ra_json, asistencia, nota_final = r
        try:
            ra_list = json.loads(ra_json)
        except:
            ra_list = []
        data.append({
            "id": id_,
            "fecha": fecha,
            "profesor": profesor,
            "alumno_id": alumno_id,
            "alumno_nombre": alumno_nombre,
            "modulo": modulo,
            "periodo": periodo,
            "ra_list": ra_list,
            "asistencia": asistencia,
            "nota_final": nota_final
        })
    return pd.DataFrame(data)

# -----------------------
# Cálculo de nota
# -----------------------
def calcular_nota_final_por_periodo(ra_list, asistencia):
    """
    ra_list: list de dicts {"nombre": str, "peso": float, "nota": float}  (nota para el periodo actual)
    asistencia: porcentaje (0-100)
    Returns: int redondeado o "N.C"
    """
    if asistencia < 80:
        return "N.C"
    total = 0.0
    for ra in ra_list:
        nota = float(ra.get("nota", 0))
        peso = float(ra.get("peso", 0))
        total += nota * (peso / 100.0)
    return int(round(total))

# -----------------------
# Export helpers
# -----------------------
def dataframe_from_results(df):
    rows = []
    for _, r in df.iterrows():
        base = {
            "id": r["id"],
            "fecha": r["fecha"],
            "profesor": r["profesor"],
            "alumno_id": r["alumno_id"],
            "alumno_nombre": r["alumno_nombre"],
            "modulo": r["modulo"],
            "periodo": r["periodo"],
            "asistencia": r["asistencia"],
            "nota_final": r["nota_final"]
        }
        ra_list = r["ra_list"]
        for i, ra in enumerate(ra_list, start=1):
            base[f"RA{i}_nombre"] = ra.get("nombre", "")
            base[f"RA{i}_nota"] = ra.get("nota", "")
            base[f"RA{i}_peso"] = ra.get("peso", "")
        rows.append(base)
    return pd.DataFrame(rows)

def to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="resultados")
    return output.getvalue()

# -----------------------
# Streamlit UI
# -----------------------
st.set_page_config(page_title="Gestor de Notas - Versión Web (Multi-roles)", layout="wide")
st.title("📚 Gestor de Notas por Módulo — Multiusuario (Tutor / Profesor)")

# ---- Login / selección de rol ----
st.sidebar.header("Acceso")
username = st.sidebar.text_input("Nombre de usuario (profesor/tutor)", value=st.session_state.get("username", ""))
role = st.sidebar.selectbox("Rol", options=["Profesor", "Tutor"], index=0)
if role == "Tutor":
    pwd = st.sidebar.text_input("Contraseña de tutor", type="password")
else:
    pwd = None

if st.sidebar.button("Entrar / Actualizar sesión"):
    # Simple check: si role==Tutor, validar contraseña
    if role == "Tutor" and pwd != TUTOR_PASSWORD:
        st.sidebar.error("Contraseña de tutor incorrecta.")
    elif not username.strip():
        st.sidebar.error("Introduce tu nombre de usuario.")
    else:
        st.session_state["username"] = username.strip()
        st.session_state["role"] = role
        st.sidebar.success(f"Sesión iniciada como {username.strip()} ({role})")
        st.rerun()

if "username" not in st.session_state:
    st.info("Introduce nombre y rol en la barra lateral y pulsa 'Entrar / Actualizar sesión' para iniciar.")
    st.stop()

username = st.session_state["username"]
role = st.session_state["role"]

st.write(f"Sesión: **{username}** — **{role}**")
st.markdown("---")

# ---- Tutor: gestión de alumnos ----
if role == "Tutor":
    st.header("Gestión de alumnos (Tutor)")
    tab1, tab2, tab3 = st.tabs(["Añadir alumno", "Importar desde Excel", "Lista y edición"])
    # Añadir uno a uno
    with tab1:
        st.subheader("Añadir alumno (uno a uno)")
        with st.form("form_add"):
            anombre = st.text_input("Nombre")
            aapellidos = st.text_input("Apellidos")
            aidal = st.text_input("IDAL (nº matrícula)")
            aestado = st.text_input("Estado (opcional)")
            add_sub = st.form_submit_button("Añadir alumno")
            if add_sub:
                if not anombre.strip() or not aidal.strip():
                    st.error("Nombre y IDAL son obligatorios.")
                else:
                    ok, err = add_alumno(anombre, aapellidos, aidal, aestado)
                    if ok:
                        st.success("Alumno añadido.")
                    else:
                        st.error("Error al añadir alumno: " + str(err))

    # Importar desde Excel
    with tab2:
        st.subheader("Importar alumnos desde un fichero Excel (.xls / .xlsx)")
        st.markdown("El fichero debe tener columnas con nombres (case-insensitive): **nombre**, **apellidos**, **idal**, **estado** (estado opcional).")
        uploaded = st.file_uploader("Selecciona el fichero Excel", type=["xls", "xlsx"])
        if st.button("Importar archivo"):
            if uploaded is None:
                st.error("Selecciona un fichero primero.")
            else:
                try:
                    df_in = pd.read_excel(uploaded)
                    cols = {c.lower().strip(): c for c in df_in.columns}
                    # Buscar columnas obligatorias
                    if "nombre" not in cols or "idal" not in cols:
                        st.error("El fichero debe contener, como mínimo, las columnas 'nombre' y 'idal' (los nombres de columna no distinguen mayúsc/minúsc).")
                    else:
                        # Mapear columnas
                        col_nombre = cols.get("nombre")
                        col_apellidos = cols.get("apellidos", None)
                        col_idal = cols.get("idal")
                        col_estado = cols.get("estado", None)
                        added = 0
                        errors = []
                        for _, row in df_in.iterrows():
                            nombre = str(row[col_nombre]) if pd.notna(row[col_nombre]) else ""
                            apellidos = str(row[col_apellidos]) if col_apellidos and pd.notna(row[col_apellidos]) else ""
                            idal = str(row[col_idal]) if pd.notna(row[col_idal]) else ""
                            estado = str(row[col_estado]) if col_estado and pd.notna(row[col_estado]) else ""
                            if not nombre.strip() or not idal.strip():
                                errors.append(f"Fila con nombre/idal vacío: nombre='{nombre}', idal='{idal}'")
                                continue
                            ok, err = add_alumno(nombre, apellidos, idal, estado)
                            if ok:
                                added += 1
                            else:
                                errors.append(f"Error al añadir {nombre} ({idal}): {err}")
                        st.success(f"Importación finalizada: {added} alumnos añadidos.")
                        if errors:
                            st.warning("Algunos problemas ocurrieron:")
                            for e in errors[:10]:
                                st.write("-", e)
                except Exception as e:
                    st.error("Error leyendo el fichero: " + str(e))

    # Lista y edición
    with tab3:
        st.subheader("Lista de alumnos (editar / eliminar)")
        df_al = list_alumnos()
        if df_al.empty:
            st.info("No hay alumnos en la base de datos todavía.")
        else:
            st.dataframe(df_al, use_container_width=True)
            st.markdown("### Editar un alumno")
            sel_id = st.selectbox("Selecciona alumno (por id) para editar", options=df_al["id"].tolist())
            if sel_id:
                row = df_al[df_al["id"] == sel_id].iloc[0]
                enombre = st.text_input("Nombre", value=row["nombre"], key="edit_nombre")
                eapellidos = st.text_input("Apellidos", value=row["apellidos"], key="edit_apellidos")
                eidal = st.text_input("IDAL", value=row["idal"], key="edit_idal")
                eestado = st.text_input("Estado", value=row["estado"], key="edit_estado")
                if st.button("Guardar cambios"):
                    ok, err = update_alumno(sel_id, enombre, eapellidos, eidal, eestado)
                    if ok:
                        st.success("Alumno actualizado.")
                    else:
                        st.error("Error: " + str(err))
                if st.button("Eliminar alumno"):
                    ok, err = delete_alumno(sel_id)
                    if ok:
                        st.success("Alumno eliminado.")
                    else:
                        st.error("Error al eliminar: " + str(err))

    st.markdown("---")

# ---- Profesor: calificar (pero también lo puede hacer el Tutor) ----
st.header("Introducir / Calcular notas (Profesores)")

df_alumnos = list_alumnos()
if df_alumnos.empty:
    st.warning("No hay alumnos en la base de datos. Pide al tutor que añada alumnos primero.")
    st.stop()

col1, col2 = st.columns([2,1])
with col1:
    alumno_sel = st.selectbox("Selecciona alumno", options=df_alumnos.apply(lambda r: f"{r['id']} - {r['nombre']} {r['apellidos']} ({r['idal']})", axis=1).tolist())
    alumno_id = int(alumno_sel.split(" - ")[0])
    alumno_row = df_alumnos[df_alumnos["id"] == alumno_id].iloc[0]
with col2:
    modulo = st.selectbox("Módulo (1-7)", options=list(range(1,8)), index=0)

st.markdown("Define el número de RAs y especifica nombre, peso (%) y las notas para cada periodo.")
num_ras = st.number_input("Número de RAs", min_value=1, max_value=20, value=3, step=1)

# Cabecera tabla RA
header_cols = st.columns([2,1] + [1]*len(PERIODOS))
headers = ["Nombre RA", "Peso (%)"] + PERIODOS
for i, h in enumerate(headers):
    header_cols[i].markdown(f"**{h}**")

# Inputs RA
ra_list_template = []
for i in range(1, int(num_ras)+1):
    cols = st.columns([2,1] + [1]*len(PERIODOS))
    default_name = st.session_state.get(f"ra_{i}_name", f"RA{i}")
    default_peso = st.session_state.get(f"ra_{i}_peso", round(100.0/num_ras, 2))
    name = cols[0].text_input(f"RA {i} nombre", value=default_name, key=f"ra_{i}_name")
    peso = cols[1].number_input(f"RA {i} peso", min_value=0.0, max_value=100.0, value=float(default_peso), step=0.5, format="%.1f", key=f"ra_{i}_peso")
    notas_periodo = {}
    for j, periodo in enumerate(PERIODOS):
        notas_periodo[periodo] = cols[2+j].number_input(f"RA{i} nota {periodo}", min_value=0.0, max_value=10.0, value=0.0, step=0.1, format="%.1f", key=f"ra_{i}_nota_{periodo}")
    ra_list_template.append({"nombre": name, "peso": peso, "notas": notas_periodo})

# Asistencia: permitimos una asistencia por periodo (flexible)
st.markdown("Introduce la asistencia (%). Si la asistencia en un periodo es < 80, la nota de ese periodo será 'N.C'.")
asistencia_periodos = {}
cols_att = st.columns(len(PERIODOS))
for i, periodo in enumerate(PERIODOS):
    asistencia_periodos[periodo] = cols_att[i].number_input(f"Asistencia {periodo} (%)", min_value=0.0, max_value=100.0, value=100.0, step=1.0, key=f"asist_{periodo}")

# Botón calcular y guardar (guardado por periodo)
if st.button("Calcular notas por periodo y mostrar (no guarda)"):
    suma_pesos = sum([float(r["peso"]) for r in ra_list_template])
    if abs(suma_pesos - 100.0) > 0.01:
        st.warning(f"La suma de pesos es {suma_pesos:.2f}%. Debe ser 100%. Ajusta los pesos.")
    else:
        st.success("Cálculos realizados. A continuación verás la nota final por cada periodo:")
        resultados_mostrados = []
        for periodo in PERIODOS:
            # crear lista RA con la nota correspondiente a este periodo
            ra_for_period = []
            for ra in ra_list_template:
                ra_for_period.append({
                    "nombre": ra["nombre"],
                    "peso": ra["peso"],
                    "nota": ra["notas"][periodo]
                })
            asistencia = asistencia_periodos[periodo]
            nota_final = calcular_nota_final_por_periodo(ra_for_period, asistencia)
            resultados_mostrados.append((periodo, nota_final, asistencia, ra_for_period))
        # Mostrar tabla resumida
        df_show = pd.DataFrame([{
            "Periodo": r[0],
            "Asistencia": r[2],
            "Nota final": r[1]
        } for r in resultados_mostrados])
        st.table(df_show)

# Guardar resultados: guardará una fila por periodo
if st.button("Guardar resultados en la base de datos (por periodo)"):
    suma_pesos = sum([float(r["peso"]) for r in ra_list_template])
    if abs(suma_pesos - 100.0) > 0.01:
        st.warning(f"La suma de pesos es {suma_pesos:.2f}%. Debe ser 100%. Ajusta los pesos.")
    else:
        alumno_nombre_full = f"{alumno_row['nombre']} {alumno_row['apellidos']}"
        saved_count = 0
        for periodo in PERIODOS:
            ra_for_period = []
            for ra in ra_list_template:
                ra_for_period.append({
                    "nombre": ra["nombre"],
                    "peso": ra["peso"],
                    "nota": ra["notas"][periodo]
                })
            asistencia = asistencia_periodos[periodo]
            nota_final = calcular_nota_final_por_periodo(ra_for_period, asistencia)
            save_result(username, alumno_id, alumno_nombre_full, modulo, periodo, ra_for_period, asistencia, nota_final)
            saved_count += 1
        st.success(f"Resultados guardados: {saved_count} registros (uno por periodo).")

st.markdown("---")

# ---- Ver / Exportar resultados ----
st.header("Ver y exportar resultados guardados")

filter_prof = st.text_input("Filtrar por profesor (opcional)")
filter_mod = st.selectbox("Filtrar por módulo (opcional)", options=["Todos"] + list(range(1,8)), index=0)
filter_per = st.selectbox("Filtrar por periodo (opcional)", options=["Todos"] + PERIODOS, index=0)

filter_modulo = None if filter_mod == "Todos" else filter_mod
filter_periodo = None if filter_per == "Todos" else filter_per
df_results = load_results(filter_profesor=(filter_prof if filter_prof.strip() else None),
                          filter_modulo=filter_modulo,
                          filter_periodo=filter_periodo)
if df_results.empty:
    st.info("No hay resultados que coincidan con los filtros.")
else:
    st.write(f"Mostrando {len(df_results)} resultados.")
    df_export = dataframe_from_results(df_results)
    st.dataframe(df_export, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        csv = df_export.to_csv(index=False).encode('utf-8')
        st.download_button("Exportar CSV", data=csv, file_name="resultados_notas.csv", mime="text/csv")
    with c2:
        try:
            xlsx_bytes = to_excel_bytes(df_export)
            st.download_button("Exportar Excel (.xlsx)", data=xlsx_bytes, file_name="resultados_notas.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception as e:
            st.error("Fallo al generar Excel: " + str(e))

st.markdown("---")
st.write("ℹ️ Notas finales:")
st.write("- Si la asistencia en un periodo es menor que 80%, la nota de ese periodo queda como 'N.C' (No calificable).")
st.write("- Los pesos de RAs deben sumar 100% para que el cálculo sea válido.")
st.write("- Para un uso multiusuario serio y concurrencia elevada, se recomienda migrar a PostgreSQL y añadir autenticación real.")
