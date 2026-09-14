"""
CC916501 — Encuesta de Reputación de Alcaldes · Colombia 2026
Visor en línea · CCD Área de Innovación
"""

import time
from datetime import datetime

import pandas as pd
import streamlit as st

# ── CONFIGURACIÓN ────────────────────────────────────────────────────────────
SHEET_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRLCqyVMWlyCtUQI-oR3lTeOl35UeTQq7QhbOIjiccPzytIfSMvlElS7VQV30t283UR6CeHRdLnNVel/pub?output=csv"
EXCLUIDOS = {9, 13, 20}
INTERVALO = 60

# Posibles nombres de columna para cada variable (LimeSurvey varía según config)
COLS = {
    "municipio":   ["G01Q01","G01Q001","municipio","MUNICIPIO"],
    "alcalde":     ["G01Q02","G01Q002","alcalde","ALCALDE"],
    "pp1":         ["PP1","G02Q01","pp1"],
    "pp2":         ["PP2","G02Q02","pp2"],
    "pp3_edad":    ["PP3","G03Q01","pp3","edad","EDAD"],
    "pp4_genero":  ["PP4","G03Q02","pp4","genero","GENERO","género"],
    "pp5_estrato": ["PP5","G03Q03","pp5","estrato","ESTRATO"],
    "pp6_educ":    ["PP6","G03Q04","pp6","educacion","EDUCACION","educación"],
    "pp7_laboral": ["PP7","G03Q05","pp7","laboral","LABORAL"],
}

def encontrar_col(df, candidatos):
    for c in candidatos:
        if c in df.columns:
            return c
    return None

# ── PÁGINA ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CC916501 · Reputación de Alcaldes",
    page_icon="🏛️",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700&family=Inter:wght@400;500;600&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif}
.header{background:#002470;border-radius:10px;padding:18px 24px 14px;margin-bottom:24px;
        border-left:8px solid;border-image:linear-gradient(180deg,#FFD100 33%,#003DA5 33% 66%,#CE1126 66%) 1}
.h-tag{font-size:11px;color:#8B96A9;letter-spacing:.12em;text-transform:uppercase;margin-bottom:4px}
.h-tit{font-family:'Barlow Condensed',sans-serif;font-size:26px;font-weight:700;color:#fff}
.h-sub{font-size:12px;color:#4ade80;margin-top:5px}
.excl{background:#FFF0F0;border:1px solid #FFCDD2;color:#CE1126;border-radius:4px;
      padding:3px 10px;font-size:11px;font-weight:600;display:inline-block;margin-bottom:8px}
.sec{font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:700;
     color:#8B96A9;letter-spacing:.1em;text-transform:uppercase;margin:4px 0 8px}
</style>
""", unsafe_allow_html=True)

# ── HEADER ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header">
  <div class="h-tag">CC916501 · CCD · Colombia 2026</div>
  <div class="h-tit">Encuesta de Reputación de Alcaldes</div>
  <div class="h-sub">● En línea · Actualización automática cada 60 s</div>
</div>
""", unsafe_allow_html=True)

# ── API LimeSurvey ────────────────────────────────────────────────────────────

@st.cache_data(ttl=INTERVALO, show_spinner=False)
def cargar_datos():
    """Lee datos desde Google Sheets publicado como CSV."""
    df = pd.read_csv(SHEET_CSV)
    
    # Excluir IDs configurados
    id_col = next((c for c in ["id","ID de respuesta","ID","response_id"] if c in df.columns), None)
    if id_col:
        df[id_col] = pd.to_numeric(df[id_col], errors="coerce")
        df = df[~df[id_col].isin(EXCLUIDOS)]
    
    # Solo completas (tienen fecha de envío válida)
    fecha_col = next((c for c in ["submitdate","Fecha de envío","fecha_envio","Date submitted"] if c in df.columns), None)
    if fecha_col:
        df = df[df[fecha_col].notna() & (df[fecha_col].astype(str) != "N")]
    
    return df.reset_index(drop=True)

# ── CARGA ─────────────────────────────────────────────────────────────────────
with st.spinner("Consultando LimeSurvey…"):
    try:
        df = cargar_datos()
        error = None
    except Exception as e:
        df = pd.DataFrame()
        error = str(e)

if error:
    st.error(f"⚠️ No se pudo conectar: {error}")
    st.stop()

# Detectar columnas reales
col = {k: encontrar_col(df, v) for k, v in COLS.items()}

# ── KPIs ──────────────────────────────────────────────────────────────────────
ahora = datetime.now()
k1, k2, k3, k4 = st.columns(4)
k1.metric("Respuestas completas", len(df), help="Excluidos #9, #13, #20")
k2.metric("Municipios", df[col["municipio"]].nunique() if col["municipio"] else "—")
k3.metric("Alcaldes evaluados", df[col["alcalde"]].nunique() if col["alcalde"] else "—")
k4.metric("Actualización", ahora.strftime("%H:%M"), help=ahora.strftime("%d %b %Y"))

st.divider()

# ── FILTROS ───────────────────────────────────────────────────────────────────
st.markdown('<div class="sec">Filtros de ubicación y resultado</div>', unsafe_allow_html=True)
fa, fb, fc = st.columns(3)

def opts(c, base=None):
    """Opciones únicas de columna c, opcionalmente sobre un df filtrado (base)."""
    src = base if base is not None else df
    if not c or c not in src.columns:
        return ["Todos"]
    return ["Todos"] + sorted(src[c].dropna().astype(str).unique().tolist())

with fa:
    f_muni = st.selectbox("Municipio", opts(col["municipio"]))

# Filtrar el df solo por municipio para alimentar el selector de alcalde
df_por_muni = df.copy()
if f_muni != "Todos" and col["municipio"] and col["municipio"] in df.columns:
    df_por_muni = df_por_muni[df_por_muni[col["municipio"]].astype(str) == f_muni]

with fb:
    opciones_alcalde = opts(col["alcalde"], base=df_por_muni)
    # Si solo hay un alcalde en el municipio lo preseleccionamos
    idx_alcalde = 1 if len(opciones_alcalde) == 2 else 0
    f_alcalde = st.selectbox("Alcalde evaluado", opciones_alcalde, index=idx_alcalde)
with fc:
    f_pp1 = st.selectbox("PP1 — Opinión de gestión", opts(col["pp1"]))

st.markdown('<div class="sec" style="margin-top:12px">Perfil del encuestado</div>', unsafe_allow_html=True)
g1, g2, g3, g4, g5 = st.columns(5)
with g1:
    f_edad    = st.selectbox("PP3 Rango de edad",   opts(col["pp3_edad"]))
with g2:
    f_genero  = st.selectbox("PP4 Género",           opts(col["pp4_genero"]))
with g3:
    f_estrato = st.selectbox("PP5 Estrato",          opts(col["pp5_estrato"]))
with g4:
    f_educ    = st.selectbox("PP6 Nivel educativo",  opts(col["pp6_educ"]))
with g5:
    f_laboral = st.selectbox("PP7 Situación laboral",opts(col["pp7_laboral"]))

# Botones
bc1, bc2, bc3 = st.columns([1,1,4])
with bc1:
    if st.button("↺ Actualizar ahora", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ── APLICAR FILTROS ───────────────────────────────────────────────────────────
dff = df.copy()
def aplicar(dff, col_name, valor):
    if valor != "Todos" and col_name and col_name in dff.columns:
        dff = dff[dff[col_name].astype(str) == valor]
    return dff

dff = aplicar(dff, col["municipio"],    f_muni)
dff = aplicar(dff, col["alcalde"],      f_alcalde)
dff = aplicar(dff, col["pp1"],          f_pp1)
dff = aplicar(dff, col["pp3_edad"],     f_edad)
dff = aplicar(dff, col["pp4_genero"],   f_genero)
dff = aplicar(dff, col["pp5_estrato"],  f_estrato)
dff = aplicar(dff, col["pp6_educ"],     f_educ)
dff = aplicar(dff, col["pp7_laboral"],  f_laboral)

st.caption(f"Mostrando **{len(dff)}** de **{len(df)}** respuestas completas")
st.markdown('<div class="excl">Excluidos: #9 · #13 · #20 · Solo completas</div>', unsafe_allow_html=True)

# ── TABLA ─────────────────────────────────────────────────────────────────────
cols_tabla = []
for k in ["municipio","alcalde","pp1","pp2","pp3_edad","pp4_genero","pp5_estrato","pp6_educ","pp7_laboral"]:
    if col[k]:
        cols_tabla.append(col[k])

meta = {"id","token","submitdate","startdate","datestamp","ipaddr","lastpage","startlanguage","seed","refurl"}
if "id" in dff.columns:
    cols_tabla = ["id"] + [c for c in cols_tabla if c != "id"]

tabla = dff[[c for c in cols_tabla if c in dff.columns]]
st.dataframe(tabla, use_container_width=True, height=380, hide_index=True)

# ── GRÁFICAS PP1 y PP2 ────────────────────────────────────────────────────────
st.divider()
st.subheader("Resultados principales")
g1, g2 = st.columns(2)

with g1:
    if col["pp1"] and col["pp1"] in dff.columns:
        st.markdown("**PP1 — Opinión de la gestión del alcalde**")
        vc1 = dff[col["pp1"]].dropna().value_counts()
        st.bar_chart(vc1, height=260)

with g2:
    if col["pp2"] and col["pp2"] in dff.columns:
        st.markdown("**PP2 — Continuidad vs cambio**")
        vc2 = dff[col["pp2"]].dropna().value_counts()
        st.bar_chart(vc2, height=260)

# ── PERFIL SOCIODEMOGRÁFICO ───────────────────────────────────────────────────
st.divider()
st.subheader("Perfil del encuestado")
p1, p2, p3 = st.columns(3)

with p1:
    if col["pp4_genero"] and col["pp4_genero"] in dff.columns:
        st.markdown("**PP4 — Género**")
        st.bar_chart(dff[col["pp4_genero"]].dropna().value_counts(), height=220)

with p2:
    if col["pp3_edad"] and col["pp3_edad"] in dff.columns:
        st.markdown("**PP3 — Rango de edad**")
        st.bar_chart(dff[col["pp3_edad"]].dropna().value_counts(), height=220)

with p3:
    if col["pp5_estrato"] and col["pp5_estrato"] in dff.columns:
        st.markdown("**PP5 — Estrato socioeconómico**")
        st.bar_chart(dff[col["pp5_estrato"]].dropna().value_counts(), height=220)

p4, p5, _ = st.columns(3)
with p4:
    if col["pp6_educ"] and col["pp6_educ"] in dff.columns:
        st.markdown("**PP6 — Nivel educativo**")
        st.bar_chart(dff[col["pp6_educ"]].dropna().value_counts(), height=220)
with p5:
    if col["pp7_laboral"] and col["pp7_laboral"] in dff.columns:
        st.markdown("**PP7 — Situación laboral**")
        st.bar_chart(dff[col["pp7_laboral"]].dropna().value_counts(), height=220)

# ── DESCARGA ──────────────────────────────────────────────────────────────────
st.divider()
csv = dff.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇ Descargar datos filtrados (.csv)",
    data=csv,
    file_name=f"CC916501_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
    mime="text/csv",
)

# ── AUTO-REFRESCO ─────────────────────────────────────────────────────────────
time.sleep(INTERVALO)
st.rerun()
