"""
CC916501 — Encuesta de Reputación de Alcaldes · Colombia 2026
Visor en línea · CCD Área de Innovación
"""
import time
from datetime import datetime
import pandas as pd
import streamlit as st

# ── CONFIGURACIÓN ─────────────────────────────────────────────────────────────
SHEET_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRLCqyVMWlyCtUQI-oR3lTeOl35UeTQq7QhbOIjiccPzytIfSMvlElS7VQV30t283UR6CeHRdLnNVel/pub?output=csv"
EXCLUIDOS = {9, 13, 20}
INTERVALO = 60

# Nombres posibles de cada columna en el CSV exportado de LimeSurvey
COLS = {
    "id":       ["id", "ID de respuesta", "Response ID"],
    "fecha":    ["submitdate", "Fecha de envío", "Date submitted"],
    "municipio":["G01Q01", "municipio", "MUNICIPIO", "Municipio"],
    "alcalde":  ["G01Q02", "alcalde",   "ALCALDE",   "Alcalde"],
    "pp1":      ["PP1", "pp1", "G02Q01"],
    "pp2":      ["PP2", "pp2", "G02Q02"],
    "pp3":      ["PP3", "pp3", "G03Q01", "Rango de edad"],
    "pp4":      ["PP4", "pp4", "G03Q02", "Género", "Genero"],
    "pp5":      ["PP5", "pp5", "G03Q03", "Estrato"],
    "pp6":      ["PP6", "pp6", "G03Q04", "Nivel educativo"],
    "pp7":      ["PP7", "pp7", "G03Q05", "Situación laboral"],
}

def col(df, key):
    for c in COLS[key]:
        if c in df.columns:
            return c
    return None

# ── PÁGINA ────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="CC916501 · Reputación de Alcaldes", page_icon="🏛️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700&family=Inter:wght@400;500;600&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif}
.header{background:#002470;border-radius:10px;padding:18px 24px 14px;margin-bottom:24px;
        border-left:8px solid;border-image:linear-gradient(180deg,#FFD100 33%,#003DA5 33% 66%,#CE1126 66%) 1}
.h-tag{font-size:11px;color:#8B96A9;letter-spacing:.12em;text-transform:uppercase;margin-bottom:4px}
.h-tit{font-family:'Barlow Condensed',sans-serif;font-size:26px;font-weight:700;color:#fff}
.h-sub{font-size:12px;color:#4ade80;margin-top:5px}
.sec{font-size:12px;font-weight:700;color:#8B96A9;letter-spacing:.1em;text-transform:uppercase;margin:16px 0 8px}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header">
  <div class="h-tag">CC916501 · CCD · Colombia 2026</div>
  <div class="h-tit">Encuesta de Reputación de Alcaldes</div>
  <div class="h-sub">● En línea · Actualización automática cada 60 s</div>
</div>
""", unsafe_allow_html=True)

# ── CARGA ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=INTERVALO, show_spinner=False)
def cargar():
    df = pd.read_csv(SHEET_CSV)
    # Excluir IDs
    c_id = col(df, "id")
    if c_id:
        df[c_id] = pd.to_numeric(df[c_id], errors="coerce")
        df = df[~df[c_id].isin(EXCLUIDOS)]
    # Solo completas
    c_f = col(df, "fecha")
    if c_f:
        df = df[df[c_f].notna() & (df[c_f].astype(str).str.strip() != "N")]
    return df.reset_index(drop=True)

with st.spinner("Cargando datos…"):
    try:
        df = cargar()
        error = None
    except Exception as e:
        df = pd.DataFrame()
        error = str(e)

if error:
    st.error(f"⚠️ Error al cargar datos: {error}")
    st.stop()

# ── KPIs ──────────────────────────────────────────────────────────────────────
ahora = datetime.now()
k1, k2, k3, k4 = st.columns(4)
k1.metric("Respuestas completas", len(df), help="Excluidos #9, #13, #20")
c_muni = col(df, "municipio")
c_alc  = col(df, "alcalde")
k2.metric("Municipios", df[c_muni].nunique() if c_muni else "—")
k3.metric("Alcaldes evaluados", df[c_alc].nunique() if c_alc else "—")
k4.metric("Actualización", ahora.strftime("%H:%M"), help=ahora.strftime("%d %b %Y"))

st.divider()

# ── FILTROS ───────────────────────────────────────────────────────────────────
st.markdown('<div class="sec">Filtros</div>', unsafe_allow_html=True)

def opts(c, base=None):
    src = base if base is not None else df
    if not c or c not in src.columns:
        return ["Todos"]
    return ["Todos"] + sorted(src[c].dropna().astype(str).unique().tolist())

fa, fb = st.columns(2)
with fa:
    f_muni = st.selectbox("Municipio", opts(c_muni))

# Filtrar alcaldes según municipio seleccionado
df_muni = df[df[c_muni].astype(str) == f_muni] if f_muni != "Todos" and c_muni else df
with fb:
    alc_opts = opts(c_alc, base=df_muni)
    idx = 1 if len(alc_opts) == 2 else 0
    f_alc = st.selectbox("Alcalde evaluado", alc_opts, index=idx)

st.markdown('<div class="sec">Perfil del encuestado</div>', unsafe_allow_html=True)
g1, g2, g3, g4, g5 = st.columns(5)
with g1: f_pp3 = st.selectbox("PP3 Edad",     opts(col(df,"pp3")))
with g2: f_pp4 = st.selectbox("PP4 Género",   opts(col(df,"pp4")))
with g3: f_pp5 = st.selectbox("PP5 Estrato",  opts(col(df,"pp5")))
with g4: f_pp6 = st.selectbox("PP6 Educación",opts(col(df,"pp6")))
with g5: f_pp7 = st.selectbox("PP7 Laboral",  opts(col(df,"pp7")))

if st.button("↺ Actualizar ahora"):
    st.cache_data.clear()
    st.rerun()

# ── APLICAR FILTROS ───────────────────────────────────────────────────────────
dff = df.copy()
def filtrar(dff, c, v):
    if v != "Todos" and c and c in dff.columns:
        dff = dff[dff[c].astype(str) == v]
    return dff

dff = filtrar(dff, c_muni,        f_muni)
dff = filtrar(dff, c_alc,         f_alc)
dff = filtrar(dff, col(df,"pp3"), f_pp3)
dff = filtrar(dff, col(df,"pp4"), f_pp4)
dff = filtrar(dff, col(df,"pp5"), f_pp5)
dff = filtrar(dff, col(df,"pp6"), f_pp6)
dff = filtrar(dff, col(df,"pp7"), f_pp7)

st.caption(f"Mostrando **{len(dff)}** de **{len(df)}** respuestas completas")

st.divider()

# ── RESULTADOS PP1 y PP2 ──────────────────────────────────────────────────────
st.markdown('<div class="sec">Resultados</div>', unsafe_allow_html=True)

def mostrar_resultado(df, key, titulo, pregunta):
    c = col(df, key)
    if not c or c not in df.columns:
        st.warning(f"{titulo}: columna no encontrada")
        return
    serie = df[c].dropna().astype(str)
    serie = serie[serie.str.strip().str.len() > 0]
    if len(serie) == 0:
        st.info(f"{titulo}: sin respuestas aún")
        return

    total = len(serie)
    vc = serie.value_counts()

    st.markdown(f"**{titulo}**")
    st.caption(pregunta)

    for opcion, cnt in vc.items():
        pct = cnt / total * 100
        col_lbl, col_bar, col_pct = st.columns([2, 5, 1])
        with col_lbl:
            st.markdown(f"<p style='margin:6px 0;font-size:13px'>{opcion}</p>", unsafe_allow_html=True)
        with col_bar:
            st.progress(int(pct))
        with col_pct:
            st.markdown(f"<p style='margin:6px 0;font-size:13px;font-weight:600'>{pct:.1f}%<br/><span style='font-weight:400;color:#888'>({cnt})</span></p>", unsafe_allow_html=True)

r1, r2 = st.columns(2)
with r1:
    mostrar_resultado(dff, "pp1",
        "PP1 — Opinión de la gestión del alcalde",
        "¿Tiene usted una opinión positiva o negativa de la gestión del alcalde?")
with r2:
    mostrar_resultado(dff, "pp2",
        "PP2 — Continuidad vs cambio",
        "¿Preferiría que el próximo alcalde continúe con las obras o establezca nuevas prioridades?")

st.divider()
st.markdown('<div class="sec">Resultados por perfil del encuestado</div>', unsafe_allow_html=True)

def cruce(df, col_perfil, label_perfil, col_resultado, label_resultado):
    cp = col(df, col_perfil)
    cr = col(df, col_resultado)
    if not cp or not cr or cp not in df.columns or cr not in df.columns:
        return
    tmp = df[[cp, cr]].dropna()
    tmp = tmp[tmp[cp].astype(str).str.strip().str.len() > 0]
    tmp = tmp[tmp[cr].astype(str).str.strip().str.len() > 0]
    if len(tmp) == 0:
        return
    tabla = tmp.groupby([cp, cr]).size().unstack(fill_value=0)
    tabla_pct = tabla.div(tabla.sum(axis=1), axis=0) * 100
    st.markdown(f"**{label_perfil} × {label_resultado}**")
    st.bar_chart(tabla_pct, height=220)

st.markdown("##### PP1 — Opinión de gestión según perfil")
c1, c2 = st.columns(2)
with c1:
    cruce(dff, "pp4", "Género",        "pp1", "PP1")
    cruce(dff, "pp5", "Estrato",       "pp1", "PP1")
with c2:
    cruce(dff, "pp3", "Edad",          "pp1", "PP1")
    cruce(dff, "pp6", "Educación",     "pp1", "PP1")
cruce(dff, "pp7", "Situación laboral", "pp1", "PP1")

st.divider()
st.markdown("##### PP2 — Continuidad vs cambio según perfil")
c3, c4 = st.columns(2)
with c3:
    cruce(dff, "pp4", "Género",        "pp2", "PP2")
    cruce(dff, "pp5", "Estrato",       "pp2", "PP2")
with c4:
    cruce(dff, "pp3", "Edad",          "pp2", "PP2")
    cruce(dff, "pp6", "Educación",     "pp2", "PP2")
cruce(dff, "pp7", "Situación laboral", "pp2", "PP2")

# ── AUTO-REFRESCO ─────────────────────────────────────────────────────────────
time.sleep(INTERVALO)
st.rerun()

# ── CRUCES SOCIODEMOGRÁFICOS ──────────────────────────────────────────────────
