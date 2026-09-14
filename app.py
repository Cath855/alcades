"""
CC916501 — Encuesta de Reputación de Alcaldes · Colombia 2026
Visor en línea · CCD Área de Innovación
"""
import time
import pandas as pd
import streamlit as st
import plotly.express as px

SHEET_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRLCqyVMWlyCtUQI-oR3lTeOl35UeTQq7QhbOIjiccPzytIfSMvlElS7VQV30t283UR6CeHRdLnNVel/pub?output=csv"
EXCLUIDOS = {9, 13, 20}
INTERVALO = 60

COLS = {
    "id":    ["ID de respuesta"],
    "fecha": ["Fecha de envío"],
    "municipio": ["Municipio", "PF2. ¿En qué ciudad reside actualmente?"],
    "alcalde":   ["Alcalde"],
    "pp1": ["PP1. En general, ¿tiene usted una opinión positiva o negativa de la gestión del alcalde {PF2ALCAL.shown}?"],
    "pp2": ["PP2. Pensando en las próximas elecciones, ¿usted preferiría que el próximo alcalde continúe con las obras y prioridades de la actual administración, o que establezca nuevas prioridades y realice cambios en la gestión?"],
    "pp3": ["PP3. ¿Cuál es su rango de edad?"],
    "pp4": ["PP4. ¿Con cuál género se identifica?"],
    "pp5": ["PP5. ¿En qué estrato socioeconómico está clasificada su vivienda?"],
    "pp6": ["PP6. ¿Cuál es su nivel educativo más alto completado?"],
    "pp7": ["PP7. ¿Cuál es su situación laboral actual?"],
}

def get_col(df, key):
    for c in COLS[key]:
        if c in df.columns:
            return c
    return None

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
.sec{font-size:12px;font-weight:700;color:#8B96A9;letter-spacing:.1em;text-transform:uppercase;margin:20px 0 8px}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header">
  <div class="h-tag">CC916501 · CCD · Colombia 2026</div>
  <div class="h-tit">Encuesta de Reputación de Alcaldes</div>
  <div class="h-sub">● En línea · Actualización automática cada 60 s</div>
</div>
""", unsafe_allow_html=True)

@st.cache_data(ttl=INTERVALO, show_spinner=False)
def cargar():
    df = pd.read_csv(SHEET_CSV)
    c_id = get_col(df, "id")
    if c_id:
        df[c_id] = pd.to_numeric(df[c_id], errors="coerce")
        df = df[~df[c_id].isin(EXCLUIDOS)]
    c_f = get_col(df, "fecha")
    if c_f:
        df = df[df[c_f].notna() & (df[c_f].astype(str).str.strip() != "N")]
    return df.reset_index(drop=True)

with st.spinner("Cargando datos…"):
    try:
        df = cargar()
    except Exception as e:
        st.error(f"⚠️ Error: {e}")
        st.stop()

c_muni = get_col(df, "municipio")
c_alc  = get_col(df, "alcalde")
c_pp1  = get_col(df, "pp1")
c_pp2  = get_col(df, "pp2")
c_pp3  = get_col(df, "pp3")
c_pp4  = get_col(df, "pp4")
c_pp5  = get_col(df, "pp5")
c_pp6  = get_col(df, "pp6")
c_pp7  = get_col(df, "pp7")

# ── KPIs GLOBALES ─────────────────────────────────────────────────────────────
k1, k2, k3 = st.columns(3)
k1.metric("Respuestas completas", len(df), help="Excluidos #9, #13, #20")
k2.metric("Municipios", df[c_muni].nunique() if c_muni else "—")
k3.metric("Alcaldes evaluados", df[c_alc].nunique() if c_alc else "—")

st.divider()

# ── FILTROS ENCADENADOS ───────────────────────────────────────────────────────
st.markdown('<div class="sec">Selecciona municipio y alcalde</div>', unsafe_allow_html=True)

fa, fb = st.columns(2)

munis = ["Todos"] + sorted(df[c_muni].dropna().astype(str).unique().tolist()) if c_muni else ["Todos"]
with fa:
    f_muni = st.selectbox("Municipio", munis)

df_muni = df[df[c_muni].astype(str) == f_muni] if f_muni != "Todos" and c_muni else df
alcs = ["Todos"] + sorted(df_muni[c_alc].dropna().astype(str).unique().tolist()) if c_alc else ["Todos"]
idx_alc = 1 if len(alcs) == 2 else 0
with fb:
    f_alc = st.selectbox("Alcalde evaluado", alcs, index=idx_alc)

if st.button("↺ Actualizar ahora"):
    st.cache_data.clear()
    st.rerun()

# Aplicar filtros
dff = df.copy()
if f_muni != "Todos" and c_muni:
    dff = dff[dff[c_muni].astype(str) == f_muni]
if f_alc != "Todos" and c_alc:
    dff = dff[dff[c_alc].astype(str) == f_alc]

alcalde_titulo = f_alc if f_alc != "Todos" else (f_muni if f_muni != "Todos" else "Colombia")
st.caption(f"Mostrando **{len(dff)}** respuestas — **{alcalde_titulo}**")

st.divider()

# ── FUNCIÓN PASTEL ─────────────────────────────────────────────────────────────
def pastel(df, col_name, titulo):
    if not col_name or col_name not in df.columns:
        return
    serie = df[col_name].dropna().astype(str)
    serie = serie[serie.str.strip().str.len() > 0]
    if len(serie) == 0:
        st.info(f"{titulo}: sin datos")
        return
    vc = serie.value_counts().reset_index()
    vc.columns = ["Respuesta", "Cantidad"]
    fig = px.pie(
        vc, values="Cantidad", names="Respuesta",
        title=titulo,
        color_discrete_sequence=px.colors.qualitative.Safe,
        hole=0.35,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="v", x=1, y=0.5),
        margin=dict(t=40, b=10, l=10, r=10),
        height=320,
    )
    st.plotly_chart(fig, use_container_width=True)

# ── RESULTADOS PP1 y PP2 ───────────────────────────────────────────────────────
st.markdown('<div class="sec">Resultados principales</div>', unsafe_allow_html=True)

r1, r2 = st.columns(2)
with r1:
    pastel(dff, c_pp1, "PP1 — Opinión de la gestión")
with r2:
    pastel(dff, c_pp2, "PP2 — Continuidad vs cambio")

st.divider()

# ── PERFIL DEL ENCUESTADO ──────────────────────────────────────────────────────
st.markdown('<div class="sec">Perfil del encuestado</div>', unsafe_allow_html=True)

p1, p2, p3 = st.columns(3)
with p1:
    pastel(dff, c_pp4, "PP4 — Género")
with p2:
    pastel(dff, c_pp3, "PP3 — Rango de edad")
with p3:
    pastel(dff, c_pp5, "PP5 — Estrato")

p4, p5, _ = st.columns(3)
with p4:
    pastel(dff, c_pp6, "PP6 — Nivel educativo")
with p5:
    pastel(dff, c_pp7, "PP7 — Situación laboral")

# ── AUTO-REFRESCO ──────────────────────────────────────────────────────────────
time.sleep(INTERVALO)
st.rerun()
