"""
CC916501 — Encuesta de Reputación de Alcaldes · Colombia 2026
Visor en línea · CCD Área de Innovación
"""
import time
import base64
import json
import io
from datetime import datetime
import requests
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import numpy as np


# ── CONFIGURACIÓN SEGURA ───────────────────────────────────────────────────────
# Las credenciales NO se guardan en este archivo.
# En Streamlit Community Cloud: App → Settings → Secrets.
# En servidor propio: .streamlit/secrets.toml (fuera de Git).
try:
    BASE_URL = st.secrets["limesurvey"]["base_url"]
    USUARIO = st.secrets["limesurvey"]["usuario"]
    PASSWORD = st.secrets["limesurvey"]["password"]
    VIEWER_PASSWORD = st.secrets["app"]["viewer_password"]
except Exception:
    st.error("Faltan los Secrets de Streamlit. Configura [limesurvey] y [app].")
    st.stop()

SURVEY_ID = "916501"
EXCLUIDOS = {9, 13, 20}
INTERVALO = 60

COLS = {
    "id":    ["ID de respuesta", "id"],
    "fecha": ["Fecha de envío", "submitdate"],
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

COLORES_PP1 = {
    "Muy positiva":  "#1a6e35",
    "Positiva":      "#4ade80",
    "Neutra":        "#94a3b8",
    "Negativa":      "#f97316",
    "Muy negativa":  "#CE1126",
    "No sabe / No responde": "#cbd5e1",
}

def get_col(df, key):
    for c in COLS[key]:
        if c in df.columns:
            return c
    return None

# ── PÁGINA ────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="CC916501 · Reputación de Alcaldes", page_icon="🏛️", layout="wide")

# ── CLAVE DE ACCESO ───────────────────────────────────────────────────────────
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700&family=Inter:wght@400;500;600&display=swap');
    html,body,[class*="css"]{font-family:'Inter',sans-serif}
    div.stButton button{background:#002470!important;color:#fff!important;border:none!important;
                        border-radius:8px!important;font-size:15px!important;font-weight:600!important;
                        padding:10px!important;width:100%}
    div.stButton button:hover{background:#003DA5!important}
    </style>
    """, unsafe_allow_html=True)
    _, col_c, _ = st.columns([1, 2, 1])
    with col_c:
        st.markdown("<br/><br/>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#fff;border-radius:14px;border:1px solid #e2e8f0;
                    box-shadow:0 8px 32px rgba(0,36,112,.12);padding:44px 40px;text-align:center">
          <div style="height:6px;border-radius:3px;background:linear-gradient(90deg,#FFD100 33%,#003DA5 33% 66%,#CE1126 66%);margin-bottom:28px"></div>
          <div style="font-size:10px;color:#8B96A9;letter-spacing:.14em;text-transform:uppercase;margin-bottom:6px">CC916501 · CCD · Colombia 2026</div>
          <div style="font-family:'Barlow Condensed',sans-serif;font-size:24px;font-weight:700;color:#002470;margin-bottom:4px">Reputación de Alcaldes</div>
          <div style="font-size:13px;color:#94a3b8;margin-bottom:28px">Ingresa la clave para acceder al visor</div>
        </div>
        """, unsafe_allow_html=True)
        clave = st.text_input("Clave", type="password", placeholder="Clave de acceso",
                              label_visibility="collapsed")
        if st.button("Ingresar", use_container_width=True) or clave == VIEWER_PASSWORD:
            if clave == VIEWER_PASSWORD:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Clave incorrecta")
    st.stop()

# ── ESTILOS ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700&family=Inter:wght@400;500;600&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif}
.header{background:#002470;border-radius:10px;padding:18px 24px 14px;margin-bottom:24px;
        border-left:8px solid;border-image:linear-gradient(180deg,#FFD100 33%,#003DA5 33% 66%,#CE1126 66%) 1}
.h-tag{font-size:11px;color:#8B96A9;letter-spacing:.12em;text-transform:uppercase;margin-bottom:4px}
.h-tit{font-family:'Barlow Condensed',sans-serif;font-size:26px;font-weight:700;color:#fff}
.h-sub{font-size:12px;color:#4ade80;margin-top:5px}
.ficha{background:#002470;border-radius:10px;padding:20px 24px;margin-bottom:20px;
       border-left:8px solid;border-image:linear-gradient(180deg,#FFD100 33%,#003DA5 33% 66%,#CE1126 66%) 1}
.ficha-ciudad{font-size:11px;color:#8B96A9;letter-spacing:.12em;text-transform:uppercase;margin-bottom:2px}
.ficha-alcalde{font-family:'Barlow Condensed',sans-serif;font-size:28px;font-weight:700;color:#fff;line-height:1.1}
.ficha-n{font-size:12px;color:#4ade80;margin-top:6px}
.sec{font-size:11px;font-weight:700;color:#8B96A9;letter-spacing:.1em;text-transform:uppercase;margin:20px 0 8px}
.kpi-box{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px 18px;text-align:center}
.kpi-n{font-family:'Barlow Condensed',sans-serif;font-size:36px;font-weight:700;color:#002470}
.kpi-l{font-size:11px;color:#8B96A9;text-transform:uppercase;letter-spacing:.08em;margin-top:2px}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header">
  <div class="h-tag">CC916501 · CCD · Colombia 2026</div>
  <div class="h-tit">Encuesta de Reputación de Alcaldes</div>
  <div class="h-sub">● En línea · Actualización automática cada 60 s</div>
</div>
""", unsafe_allow_html=True)

# ── API LIMESURVEY ─────────────────────────────────────────────────────────────
def rpc(method, params):
    r = requests.post(BASE_URL,
                      json={"method": method, "params": params, "id": 1},
                      headers={"Content-Type": "application/json"},
                      timeout=30)
    r.raise_for_status()
    result = r.json().get("result")
    if isinstance(result, dict) and "status" in result:
        raise RuntimeError(result["status"])
    return result

SHEET_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRLCqyVMWlyCtUQI-oR3lTeOl35UeTQq7QhbOIjiccPzytIfSMvlElS7VQV30t283UR6CeHRdLnNVel/pub?output=csv"

@st.cache_data(ttl=INTERVALO, show_spinner=False)
def cargar():
    # Intentar LimeSurvey API primero
    key = None
    try:
        key = rpc("get_session_key", [USUARIO, PASSWORD])
        raw = rpc("export_responses", [key, SURVEY_ID, "json", None, "complete", "long", "full"])
        try:
            rpc("release_session_key", [key])
        except Exception:
            pass
        try:
            data = json.loads(base64.b64decode(raw).decode("utf-8"))
        except Exception:
            data = raw if isinstance(raw, dict) else json.loads(raw)
        filas = data.get("responses") or data.get("Responses") or []
        if not isinstance(filas, list):
            filas = list(filas.values())
        df = pd.DataFrame(filas)
    except Exception:
        # Fallback: Google Sheets
        df = pd.read_csv(SHEET_CSV)

    c_id = get_col(df, "id")
    if c_id:
        df[c_id] = pd.to_numeric(df[c_id], errors="coerce")
        df = df[~df[c_id].isin(EXCLUIDOS)]
    c_f = get_col(df, "fecha")
    if c_f:
        df = df[df[c_f].notna() & (df[c_f].astype(str).str.strip() != "N")]
    return df.reset_index(drop=True)

with st.spinner("Consultando datos…"):
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

# ── FILTROS ───────────────────────────────────────────────────────────────────
st.markdown('<div class="sec">Selecciona municipio y alcalde</div>', unsafe_allow_html=True)
fa, fb, fc = st.columns([2, 2, 1])

munis = ["Todos"] + sorted(df[c_muni].dropna().astype(str).unique().tolist()) if c_muni else ["Todos"]
with fa:
    f_muni = st.selectbox("Municipio", munis)

df_muni = df[df[c_muni].astype(str) == f_muni] if f_muni != "Todos" and c_muni else df
alcs = ["Todos"] + sorted(df_muni[c_alc].dropna().astype(str).unique().tolist()) if c_alc else ["Todos"]
idx_alc = 1 if len(alcs) == 2 else 0
with fb:
    f_alc = st.selectbox("Alcalde evaluado", alcs, index=idx_alc)

with fc:
    st.markdown("<br/>", unsafe_allow_html=True)
    if st.button("↺ Actualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ── APLICAR FILTROS ───────────────────────────────────────────────────────────
dff = df.copy()
if f_muni != "Todos" and c_muni:
    dff = dff[dff[c_muni].astype(str) == f_muni]
if f_alc != "Todos" and c_alc:
    dff = dff[dff[c_alc].astype(str) == f_alc]

hay_filtro = f_muni != "Todos" or f_alc != "Todos"

st.divider()

# ── FICHA ─────────────────────────────────────────────────────────────────────
nombre_alcalde = f_alc if f_alc != "Todos" else "Todos los alcaldes"
nombre_ciudad  = f_muni if f_muni != "Todos" else "Colombia"

st.markdown(f"""
<div class="ficha">
  <div class="ficha-ciudad">📍 {nombre_ciudad}</div>
  <div class="ficha-alcalde">{nombre_alcalde}</div>
  <div class="ficha-n">● {len(dff)} respuestas completas analizadas</div>
</div>
""", unsafe_allow_html=True)

# ── KPIs FICHA ────────────────────────────────────────────────────────────────
serie_pp1 = dff[c_pp1].dropna() if c_pp1 else pd.Series()
serie_pp2 = dff[c_pp2].dropna() if c_pp2 else pd.Series()
positivas = serie_pp1.astype(str).str.lower().str.contains("positiv", na=False).sum()
negativas = serie_pp1.astype(str).str.lower().str.contains("negativ", na=False).sum()
continua  = serie_pp2.astype(str).str.lower().str.contains("continu|continúe|continué", na=False).sum()
cambia    = serie_pp2.astype(str).str.lower().str.contains("cambi|nueva|rumbo", na=False).sum()
pct_pos  = f"{positivas/len(serie_pp1)*100:.1f}%" if len(serie_pp1)>0 else "—"
pct_neg  = f"{negativas/len(serie_pp1)*100:.1f}%" if len(serie_pp1)>0 else "—"
pct_cont = f"{continua/len(serie_pp2)*100:.1f}%"  if len(serie_pp2)>0 else "—"
pct_camb = f"{cambia/len(serie_pp2)*100:.1f}%"    if len(serie_pp2)>0 else "—"

k1,k2,k3,k4 = st.columns(4)
with k1: st.markdown(f'<div class="kpi-box"><div class="kpi-n" style="color:#1a6e35">{pct_pos}</div><div class="kpi-l">Opinión positiva</div></div>',unsafe_allow_html=True)
with k2: st.markdown(f'<div class="kpi-box"><div class="kpi-n" style="color:#CE1126">{pct_neg}</div><div class="kpi-l">Opinión negativa</div></div>',unsafe_allow_html=True)
with k3: st.markdown(f'<div class="kpi-box"><div class="kpi-n" style="color:#003DA5">{pct_cont}</div><div class="kpi-l">Quiere continuidad</div></div>',unsafe_allow_html=True)
with k4: st.markdown(f'<div class="kpi-box"><div class="kpi-n" style="color:#7C3AED">{pct_camb}</div><div class="kpi-l">Quiere cambio</div></div>',unsafe_allow_html=True)

st.divider()

# ── FUNCIÓN BARRAS ────────────────────────────────────────────────────────────
def barras(df, col_name, titulo, colores=None, altura=320):
    if not col_name or col_name not in df.columns:
        return
    serie = df[col_name].dropna().astype(str)
    serie = serie[serie.str.strip().str.len()>0]
    if len(serie)==0:
        st.caption(f"{titulo}: sin datos")
        return
    total = len(serie)
    vc = serie.value_counts().reset_index()
    vc.columns = ["Respuesta","Cantidad"]
    vc["Porcentaje"] = (vc["Cantidad"]/total*100).round(1)
    vc = vc.sort_values("Porcentaje", ascending=True)
    color_seq = px.colors.qualitative.Safe
    fig = go.Figure()
    for i, row in vc.iterrows():
        color = colores.get(row["Respuesta"], color_seq[i%len(color_seq)]) if colores else color_seq[i%len(color_seq)]
        fig.add_trace(go.Bar(
            x=[row["Porcentaje"]], y=[row["Respuesta"]],
            orientation="h", marker_color=color,
            text=f"{row['Porcentaje']}%", textposition="outside",
            showlegend=False,
            hovertemplate=f"<b>{row['Respuesta']}</b><br>{row['Cantidad']} resp. ({row['Porcentaje']}%)<extra></extra>",
        ))
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=13, color="#002470")),
        xaxis=dict(range=[0,118], showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(automargin=True, tickfont=dict(size=11)),
        margin=dict(t=40,b=10,l=10,r=55),
        height=altura, plot_bgcolor="white", paper_bgcolor="white", bargap=0.3,
    )
    st.plotly_chart(fig, use_container_width=True)

# ── PP1 Y PP2 — SIEMPRE ───────────────────────────────────────────────────────
st.markdown('<div class="sec">Resultados principales</div>', unsafe_allow_html=True)
r1, r2 = st.columns(2)
with r1:
    barras(dff, c_pp1, "PP1 — Opinión de la gestión del alcalde", COLORES_PP1, altura=280)
with r2:
    barras(dff, c_pp2, "PP2 — Continuidad vs cambio", altura=280)

st.divider()

# ── PERFIL — SIEMPRE ──────────────────────────────────────────────────────────
st.markdown('<div class="sec">Perfil del encuestado</div>', unsafe_allow_html=True)
p1,p2,p3 = st.columns(3)
with p1: barras(dff, c_pp4, "PP4 — Género")
with p2: barras(dff, c_pp3, "PP3 — Rango de edad")
with p3: barras(dff, c_pp5, "PP5 — Estrato")
p4,p5,_ = st.columns(3)
with p4: barras(dff, c_pp6, "PP6 — Nivel educativo")
with p5: barras(dff, c_pp7, "PP7 — Situación laboral")

# ── RANKING Y TABLA — SOLO SIN FILTRO ────────────────────────────────────────
if not hay_filtro:
    st.divider()
    st.markdown('<div class="sec">Ranking nacional — PP1 Opinión de gestión</div>', unsafe_allow_html=True)
    if c_pp1 and c_alc and c_pp1 in df.columns and c_alc in df.columns:
        tmp = df[[c_alc,c_pp1]].dropna()
        tmp = tmp[tmp[c_pp1].astype(str).str.strip().str.len()>0]
        def pct_positiva(serie):
            return serie.astype(str).str.lower().str.contains("positiv",na=False).sum()/len(serie)*100
        ranking = tmp.groupby(c_alc)[c_pp1].apply(pct_positiva).reset_index()
        ranking.columns = ["Alcalde","% Positiva"]
        ranking["% Positiva"] = ranking["% Positiva"].round(1)
        ranking["n"] = tmp.groupby(c_alc)[c_pp1].count().values
        ranking = ranking[ranking["n"]>=20]
        ranking = ranking.sort_values("% Positiva",ascending=False).reset_index(drop=True)
        ciudad_por_alcalde = df.groupby(c_alc)[c_muni].agg(lambda x: x.value_counts().index[0] if len(x)>0 else "—")
        top3  = ranking.head(3).copy()
        peor3 = ranking.tail(3).sort_values("% Positiva",ascending=True).copy()
        st.caption("⚠️ Ranking basado en % de opinión positiva (PP1). Solo alcaldes con mínimo 20 respuestas.")
        ra,rb = st.columns(2)
        with ra:
            st.markdown("🏆 **Mejor calificados**")
            for i,row in top3.iterrows():
                medal=["🥇","🥈","🥉"][i]
                ciudad=ciudad_por_alcalde.get(row["Alcalde"],"—")
                st.markdown(f'<div style="background:#f0fdf4;border-left:4px solid #22c55e;border-radius:6px;padding:10px 14px;margin-bottom:8px"><div style="display:flex;justify-content:space-between;align-items:center"><span style="font-size:13px;font-weight:600">{medal} {row["Alcalde"]}</span><span style="font-size:20px;font-weight:700;color:#15803d">{row["% Positiva"]}%</span></div><div style="font-size:11px;color:#6b7280;margin-top:3px">📍 {ciudad} · {int(row["n"])} respuestas</div></div>',unsafe_allow_html=True)
        with rb:
            st.markdown("⚠️ **Peor calificados**")
            for j,(_,row) in enumerate(peor3.iterrows()):
                medal=["🔴","🟠","🟡"][j]
                ciudad=ciudad_por_alcalde.get(row["Alcalde"],"—")
                st.markdown(f'<div style="background:#fff7f7;border-left:4px solid #ef4444;border-radius:6px;padding:10px 14px;margin-bottom:8px"><div style="display:flex;justify-content:space-between;align-items:center"><span style="font-size:13px;font-weight:600">{medal} {row["Alcalde"]}</span><span style="font-size:20px;font-weight:700;color:#CE1126">{row["% Positiva"]}%</span></div><div style="font-size:11px;color:#6b7280;margin-top:3px">📍 {ciudad} · {int(row["n"])} respuestas</div></div>',unsafe_allow_html=True)
    st.divider()
    st.markdown('<div class="sec">Respuestas por ciudad</div>', unsafe_allow_html=True)
    if c_muni and c_alc and c_muni in df.columns:
        resumen = df.groupby(c_muni).size().reset_index(name="Respuestas")
        resumen.columns = ["Ciudad","Respuestas"]
        alc_ciudad = df.groupby(c_muni)[c_alc].agg(lambda x: x.value_counts().index[0] if len(x)>0 else "—").reset_index()
        alc_ciudad.columns = ["Ciudad","Alcalde"]
        resumen = resumen.merge(alc_ciudad,on="Ciudad").sort_values("Respuestas",ascending=False).reset_index(drop=True)
        resumen.index = resumen.index+1
        resumen["% del total"] = (resumen["Respuestas"]/resumen["Respuestas"].sum()*100).round(1).astype(str)+"%"
        resumen = resumen[["Ciudad","Alcalde","Respuestas","% del total"]]
        st.dataframe(resumen,use_container_width=True,hide_index=False,height=min(420,40+len(resumen)*36))

# ── GENERAR PDF ───────────────────────────────────────────────────────────────
def grafica_barras_pdf(ranking_df, ancho_pts):
    """Gráfica de barras apiladas dibujada con reportlab (sin matplotlib)."""
    AZUL = colors.HexColor("#1F4E9B")
    ROJO = colors.HexColor("#C0392B")
    GRIS = colors.HexColor("#BDBDBD")
    TXT  = colors.HexColor("#333333")

    n = len(ranking_df)
    fila_h    = 15
    margen_iz = 150   # espacio para nombres
    margen_de = 38    # espacio para n=
    top       = 26    # leyenda
    bottom    = 18    # eje x
    barra_w   = ancho_pts - margen_iz - margen_de
    alto      = n * fila_h + top + bottom

    d = Drawing(ancho_pts, alto)

    # Leyenda
    lx = margen_iz
    for color, txt in [(AZUL,"Positiva"), (GRIS,"NS/NR"), (ROJO,"Negativa")]:
        d.add(Rect(lx, alto-14, 9, 9, fillColor=color, strokeColor=None))
        d.add(String(lx+13, alto-12, txt, fontName="Helvetica", fontSize=7, fillColor=TXT))
        lx += 60

    # Línea 50%
    x50 = margen_iz + barra_w*0.5
    d.add(Line(x50, bottom-3, x50, alto-top+3,
               strokeColor=colors.HexColor("#AAAAAA"), strokeWidth=0.6, strokeDashArray=[2,2]))

    # Eje x
    for p in [0,25,50,75,100]:
        xp = margen_iz + barra_w*(p/100)
        d.add(String(xp, bottom-12, f"{p}%", fontName="Helvetica",
                     fontSize=6.5, fillColor=TXT, textAnchor="middle"))

    # Barras (de abajo hacia arriba = peor a mejor)
    for i, (_, row) in enumerate(ranking_df[::-1].iterrows()):
        y = bottom + i*fila_h
        pos  = float(row["% Positiva"])
        neg  = float(row["% Negativa"])
        nsnr = max(0.0, 100.0 - pos - neg)
        bh = fila_h * 0.62

        # Nombre corto
        partes = str(row["Alcalde"]).split()
        nom = f"{partes[0]} {partes[-1]}" if len(partes) > 1 else str(row["Alcalde"])
        etiqueta = f"{nom} ({row['Ciudad']})"
        if len(etiqueta) > 34:
            etiqueta = etiqueta[:33] + "…"
        d.add(String(margen_iz-5, y+3, etiqueta, fontName="Helvetica",
                     fontSize=6.8, fillColor=TXT, textAnchor="end"))

        x = margen_iz
        for valor, color in [(pos,AZUL), (nsnr,GRIS), (neg,ROJO)]:
            w = barra_w * (valor/100.0)
            if w > 0:
                d.add(Rect(x, y, w, bh, fillColor=color, strokeColor=None))
            x += w

        # % positiva dentro de la barra
        if pos > 7:
            d.add(String(margen_iz + barra_w*(pos/200), y+3, f"{int(pos)}%",
                         fontName="Helvetica-Bold", fontSize=6.3,
                         fillColor=colors.white, textAnchor="middle"))
        # n= al final
        d.add(String(margen_iz + barra_w + 4, y+3, f"n={int(row['n'])}",
                     fontName="Helvetica", fontSize=6.3, fillColor=TXT))

    return d

def generar_pdf(df, c_pp1, c_pp2, c_alc, c_muni):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    story = []
    ancho = A4[0] - 4*cm

    # Estilos
    estilos = getSampleStyleSheet()
    titulo_style = ParagraphStyle("titulo", fontName="Helvetica-Bold",
                                   fontSize=16, textColor=colors.HexColor("#002470"),
                                   spaceAfter=4, alignment=TA_LEFT)
    subtitulo_style = ParagraphStyle("subtitulo", fontName="Helvetica",
                                      fontSize=10, textColor=colors.HexColor("#8B96A9"),
                                      spaceAfter=2, alignment=TA_LEFT)
    nota_style = ParagraphStyle("nota", fontName="Helvetica",
                                 fontSize=8, textColor=colors.HexColor("#6b7280"),
                                 spaceAfter=6)
    sec_style = ParagraphStyle("sec", fontName="Helvetica-Bold",
                                fontSize=11, textColor=colors.HexColor("#002470"),
                                spaceBefore=12, spaceAfter=6)

    # Encabezado
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph("Percepción de gestión de alcaldes", titulo_style))
    story.append(Paragraph(f"Avance de la encuesta · corte {ahora}", subtitulo_style))
    story.append(HRFlowable(width=ancho, thickness=3,
                             color=colors.HexColor("#002470"), spaceAfter=10))

    # KPIs globales
    total = len(df)
    s1 = df[c_pp1].dropna().astype(str) if c_pp1 else pd.Series()
    pct_pos  = round(s1.str.lower().str.contains("positiv",na=False).sum()/len(s1)*100,1) if len(s1)>0 else 0
    pct_neg  = round(s1.str.lower().str.contains("negativ",na=False).sum()/len(s1)*100,1) if len(s1)>0 else 0

    s2 = df[c_pp2].dropna().astype(str) if c_pp2 and c_pp2 in df.columns else pd.Series()
    pct_cont = round(s2.str.lower().str.contains("continu",na=False).sum()/len(s2)*100,1) if len(s2)>0 else 0
    pct_camb = round(s2.str.lower().str.contains("cambi|rumbo",na=False).sum()/len(s2)*100,1) if len(s2)>0 else 0

    n_munis = df[c_muni].nunique() if c_muni else 0
    n_alcs  = df[c_alc].nunique()  if c_alc  else 0

    datos_kpi = [
        ["Encuestas válidas", "Opinión positiva", "Opinión negativa", "Prefiere continuidad", "Prefiere cambio"],
        [str(total), f"{pct_pos}%", f"{pct_neg}%", f"{pct_cont}%", f"{pct_camb}%"],
    ]
    t_kpi = Table(datos_kpi, colWidths=[ancho/5]*5)
    t_kpi.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,0), colors.HexColor("#002470")),
        ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
        ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,0), 9),
        ("BACKGROUND",   (0,1), (-1,1), colors.HexColor("#EEF2FA")),
        ("FONTNAME",     (0,1), (-1,1), "Helvetica-Bold"),
        ("FONTSIZE",     (0,1), (-1,1), 14),
        ("TEXTCOLOR",    (0,1), (-1,1), colors.HexColor("#002470")),
        ("ALIGN",        (0,0), (-1,-1), "CENTER"),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[colors.HexColor("#002470"), colors.HexColor("#EEF2FA")]),
        ("GRID",         (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING",   (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0), (-1,-1), 8),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Se han recogido {total} encuestas válidas sobre {n_alcs} alcaldes en {n_munis} municipios.",
        nota_style))
    story.append(Spacer(1, 4))

    # Ranking
    if c_pp1 and c_alc and c_pp1 in df.columns and c_alc in df.columns:
        tmp = df[[c_alc, c_pp1]].dropna()
        tmp = tmp[tmp[c_pp1].astype(str).str.strip().str.len()>0]

        def pct_p(s): return s.astype(str).str.lower().str.contains("positiv",na=False).sum()/len(s)*100
        def pct_n(s): return s.astype(str).str.lower().str.contains("negativ",na=False).sum()/len(s)*100
        def pct_c(s): return s.astype(str).str.lower().str.contains("continu",na=False).sum()/len(s)*100 if c_pp2 else 0

        ranking = pd.DataFrame({
            "Alcalde":      tmp.groupby(c_alc)[c_pp1].apply(lambda x: x.name if False else x.index[0]).index.tolist(),
            "% Positiva":   [round(pct_p(tmp[tmp[c_alc]==a][c_pp1]),0) for a in tmp[c_alc].unique()],
            "% Negativa":   [round(pct_n(tmp[tmp[c_alc]==a][c_pp1]),0) for a in tmp[c_alc].unique()],
            "n":            [len(tmp[tmp[c_alc]==a]) for a in tmp[c_alc].unique()],
        })
        ranking["Alcalde"] = tmp[c_alc].unique()
        c_pp2_pdf = c_pp2
        if c_pp2_pdf and c_pp2_pdf in df.columns:
            tmp2 = df[[c_alc, c_pp2_pdf]].dropna()
            def pct_cont_alc(a):
                s = tmp2[tmp2[c_alc]==a][c_pp2_pdf]
                if len(s)==0: return 0
                return round(s.astype(str).str.lower().str.contains("continu",na=False).sum()/len(s)*100,0)
            ranking["Continuidad"] = [pct_cont_alc(a) for a in ranking["Alcalde"]]
        else:
            ranking["Continuidad"] = 0

        ciudad_por_alcalde = df.groupby(c_alc)[c_muni].agg(lambda x: x.value_counts().index[0] if len(x)>0 else "—")
        ranking["Ciudad"] = ranking["Alcalde"].map(ciudad_por_alcalde)
        ranking["Neto"] = ranking["% Positiva"] - ranking["% Negativa"]
        ranking = ranking[ranking["n"]>=10].sort_values("% Positiva", ascending=False).reset_index(drop=True)
        ranking.index = ranking.index + 1

        # Top 5
        story.append(Paragraph("Top 5 — mejor evaluados", sec_style))
        top5 = ranking.head(5)
        datos_top = [["#", "Alcalde / Municipio", "n", "Positiva", "Negativa", "Neto", "Continuidad"]]
        for i, row in top5.iterrows():
            datos_top.append([
                str(i),
                row["Alcalde"] + "\n" + row["Ciudad"],
                str(int(row['n'])),
                f"{int(row['% Positiva'])}%",
                f"{int(row['% Negativa'])}%",
                f"{'+' if row['Neto']>=0 else ''}{int(row['Neto'])}",
                f"{int(row['Continuidad'])}%",
            ])
        t_top = Table(datos_top, colWidths=[1*cm, 6*cm, 1*cm, 2*cm, 2*cm, 2*cm, 2*cm])
        t_top.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0), colors.HexColor("#002470")),
            ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#F0FDF4")]),
            ("GRID",        (0,0), (-1,-1), 0.3, colors.HexColor("#CBD5E1")),
            ("ALIGN",       (2,0), (-1,-1), "CENTER"),
            ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING",  (0,0), (-1,-1), 5),
            ("BOTTOMPADDING",(0,0), (-1,-1), 5),
            ("TEXTCOLOR",   (3,1), (3,-1), colors.HexColor("#15803d")),
            ("FONTNAME",    (3,1), (3,-1), "Helvetica-Bold"),
        ]))
        story.append(t_top)
        story.append(Spacer(1, 10))

        # Peor 5
        story.append(Paragraph("Top 5 — peor evaluados", sec_style))
        peor5 = ranking.tail(5).sort_values("% Positiva", ascending=True)
        datos_peor = [["#", "Alcalde / Municipio", "n", "Positiva", "Negativa", "Neto", "Continuidad"]]
        for i, row in peor5.iterrows():
            datos_peor.append([
                str(i),
                row["Alcalde"] + "\n" + row["Ciudad"],
                str(int(row['n'])),
                f"{int(row['% Positiva'])}%",
                f"{int(row['% Negativa'])}%",
                f"{'+' if row['Neto']>=0 else ''}{int(row['Neto'])}",
                f"{int(row['Continuidad'])}%",
            ])
        t_peor = Table(datos_peor, colWidths=[1*cm, 6*cm, 1*cm, 2*cm, 2*cm, 2*cm, 2*cm])
        t_peor.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0), colors.HexColor("#002470")),
            ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#FFF7F7")]),
            ("GRID",        (0,0), (-1,-1), 0.3, colors.HexColor("#CBD5E1")),
            ("ALIGN",       (2,0), (-1,-1), "CENTER"),
            ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING",  (0,0), (-1,-1), 5),
            ("BOTTOMPADDING",(0,0), (-1,-1), 5),
            ("TEXTCOLOR",   (3,1), (3,-1), colors.HexColor("#CE1126")),
            ("FONTNAME",    (3,1), (3,-1), "Helvetica-Bold"),
        ]))
        story.append(t_peor)
        story.append(Spacer(1, 10))

        # Gráfica de barras
        story.append(Paragraph("Ranking completo (alcaldes con n ≥ 10)", sec_style))
        story.append(grafica_barras_pdf(ranking, ancho))
        story.append(Spacer(1, 10))
        story.append(Paragraph("Tabla detallada del ranking", sec_style))
        datos_full = [["#", "Alcalde / Municipio", "n", "Positiva", "Negativa", "Neto", "Continuidad"]]
        for i, row in ranking.iterrows():
            datos_full.append([
                str(i),
                row["Alcalde"] + " (" + row["Ciudad"] + ")",
                str(int(row['n'])),
                f"{int(row['% Positiva'])}%",
                f"{int(row['% Negativa'])}%",
                f"{'+' if row['Neto']>=0 else ''}{int(row['Neto'])}",
                f"{int(row['Continuidad'])}%",
            ])
        t_full = Table(datos_full, colWidths=[1*cm, 7*cm, 1*cm, 2*cm, 2*cm, 1.5*cm, 2*cm])
        row_colors = []
        for i in range(1, len(datos_full)):
            pct = ranking.iloc[i-1]["% Positiva"]
            if pct >= 70:
                row_colors.append(colors.HexColor("#F0FDF4"))
            elif pct >= 50:
                row_colors.append(colors.white)
            else:
                row_colors.append(colors.HexColor("#FFF7F7"))
        t_full.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#002470")),
            ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
            ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1), 8),
            ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#CBD5E1")),
            ("ALIGN",         (2,0), (-1,-1), "CENTER"),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(t_full)
        story.append(Spacer(1, 6))

    # Nota metodológica
    story.append(HRFlowable(width=ancho, thickness=0.5,
                             color=colors.HexColor("#CBD5E1"), spaceAfter=6))
    story.append(Paragraph(
        "Positiva/Negativa: PP1, opinión sobre la gestión del alcalde. "
        "Neto = % positiva − % negativa. "
        "Continuidad: PP2, % que prefiere que el próximo alcalde continúe con las obras y prioridades actuales. "
        "Encuesta en línea autoadministrada (WhatsApp/redes), no probabilística.",
        nota_style))

    doc.build(story)
    buffer.seek(0)
    return buffer

# Botón descarga PDF — solo sin filtros
if not hay_filtro and c_pp1 and c_alc:
    st.divider()
    if st.button("📄 Generar informe PDF", use_container_width=False):
        with st.spinner("Generando PDF…"):
            pdf = generar_pdf(df, c_pp1, c_pp2, c_alc, c_muni)
        ahora = datetime.now().strftime("%Y%m%d_%H%M")
        st.download_button(
            label="⬇ Descargar informe PDF",
            data=pdf,
            file_name=f"Informe_Alcaldes_{ahora}.pdf",
            mime="application/pdf",
            use_container_width=False,
        )

# ── AUTO-REFRESCO ──────────────────────────────────────────────────────────────
time.sleep(INTERVALO)
st.rerun()
