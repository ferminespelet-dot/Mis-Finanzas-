import streamlit as st
import pandas as pd
import json
import datetime
import os
from google import genai
import plotly.express as px
import requests

st.set_page_config(page_title="Finanzas & Cerebro", page_icon="🍊", layout="centered")

# Estética limpia
st.markdown("""
<style>
    .stButton>button[kind="primary"] {
        background-color: #D97706;
        color: white;
        border-radius: 8px;
        border: none;
    }
    .stButton>button[kind="primary"]:hover {
        background-color: #B45309;
        color: white;
    }
    div[data-testid="stMetric"] {
        background-color: rgba(217, 119, 6, 0.05);
        padding: 10px;
        border-radius: 10px;
        border: 1px solid rgba(217, 119, 6, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# SISTEMA DE PERFILES
# ==========================================
st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
usuario_actual = st.radio("👤 ¿Quién está usando la app?", ["Fermín", "Irina"], horizontal=True)
st.markdown("</div>", unsafe_allow_html=True)

if "usuario_previo" not in st.session_state:
    st.session_state.usuario_previo = usuario_actual

if st.session_state.usuario_previo != usuario_actual:
    for key in ["categories", "transactions", "savings", "thoughts", "pendings", "last_added"]:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.usuario_previo = usuario_actual

sufijo = "" if usuario_actual == "Fermín" else "_irina"
DATA_FILE = f"transactions{sufijo}.json"
CATEGORIES_FILE = f"categories{sufijo}.json"
SAVINGS_FILE = f"savings{sufijo}.json"
THOUGHTS_FILE = f"thoughts{sufijo}.json"
PENDINGS_FILE = f"pendings{sufijo}.json"

DEFAULT_CATEGORIES = {
    "Irina": ["irina", "iri", "novia", "romántico", "regalos", "compré a ella", "ella"],
    "Futbol": ["futbol", "fútbol", "cancha", "pelota", "partido"],
    "Supermercado": ["supermercado", "super", "almacén", "verdulería", "hiper"],
    "Comida": ["comida", "hamburguesa", "pizza", "almuerzo", "cena", "delivery", "restaurant"],
    "Kiosco": ["coquita", "alfajor", "gomitas", "golosinas", "energizante", "sube", "kiosco"],
    "Tabaco": ["cigarrillos", "tabaco", "papelillos", "filtros", "pucho"],
    "Café y panadería": ["café", "merienda", "torta", "panadería", "facturas", "medialunas"],
    "Bazar": ["bazar", "poster", "póster", "sahumerios", "librería", "plantas", "detalles"],
    "Salidas": ["cerveza", "boliche", "salidas", "barcito", "salir", "trago"],
    "Bebida": ["vino", "cerveza para tomar", "bebida alcohol"],
    "Otros": ["libro", "ropa", "stickers", "mercado libre", "cumpleaños", "perdí"],
    "Música": ["cuerdas", "púas", "cables", "sala de ensayo", "pilas", "recitales", "música"],
    "Devoluciones": ["devuelve", "devolvió", "reembolso"]
}

def load_json(filename, default):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if "categories" not in st.session_state:
    st.session_state.categories = load_json(CATEGORIES_FILE, DEFAULT_CATEGORIES)
if "transactions" not in st.session_state:
    st.session_state.transactions = load_json(DATA_FILE, [])
if "savings" not in st.session_state:
    st.session_state.savings = load_json(SAVINGS_FILE, [])
if "thoughts" not in st.session_state:
    st.session_state.thoughts = load_json(THOUGHTS_FILE, [])
if "pendings" not in st.session_state:
    st.session_state.pendings = load_json(PENDINGS_FILE, [])

st.sidebar.header("⚙️ Configuración")
api_key = st.sidebar.text_input("Gemini API Key", type="password", value=os.environ.get("GEMINI_API_KEY", ""))

def get_dolar_blue():
    try:
        res = requests.get("https://dolarapi.com/v1/dolares/blue", timeout=3)
        if res.status_code == 200:
            return res.json().get("venta", 1300)
    except:
        pass
    return 1300

dolar_blue_venta = get_dolar_blue()

now = datetime.datetime.now()
if now.day >= 28:
    current_cycle_start = datetime.datetime(now.year, now.month, 28)
    next_cycle_start = datetime.datetime(now.year + 1, 1, 28) if now.month == 12 else datetime.datetime(now.year, now.month + 1, 28)
else:
    current_cycle_start = datetime.datetime(now.year - 1, 12, 28) if now.month == 1 else datetime.datetime(now.year, now.month - 1, 28)
    next_cycle_start = datetime.datetime(now.year, now.month, 28)

icono = "🍊" if usuario_actual == "Fermín" else "🌸"
st.title(f"Hola, {usuario_actual} {icono}")
st.caption("Tu espacio de Finanzas & Cerebro")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "💬 Registrar", "📊 Balance", "📜 Historial", "📅 Ciclos", "🏷️ Categorías", "🧠 Cerebro"
])

df_tx = pd.DataFrame(st.session_state.transactions)
if not df_tx.empty:
    df_tx["timestamp_dt"] = pd.to_datetime(df_tx["timestamp"])
    df_cycle = df_tx[(df_tx["timestamp_dt"] >= pd.to_datetime(current_cycle_start)) & (df_tx["timestamp_dt"] < pd.to_datetime(next_cycle_start))]
else:
    df_cycle = pd.DataFrame(columns=["tipo", "monto", "descripcion", "categoria", "timestamp"])

total_ingresos = df_cycle[df_cycle["tipo"] == "ingreso"]["monto"].sum() if not df_cycle.empty else 0
total_gastos = df_cycle[df_cycle["tipo"] == "gasto"]["monto"].sum() if not df_cycle.empty else 0
saldo_actual = total_ingresos - total_gastos

with tab1:
    st.markdown("### 🎙️ Registro Rápido")
    
    user_input = st.text_area("Registro", placeholder="Ej: Compré un alfajor por 2000...", height=100, label_visibility="collapsed")
    
    col1, col2 = st.columns(2)
    with col1:
        mic_clicked = st.button("🎙️ Usar Micrófono", use_container_width=True)
    with col2:
        procesar = st.button("✨ Procesar", type="primary", use_container_width=True)

    if mic_clicked:
        st.info("💡 Consejo: Toca la caja de texto y presiona el ícono del micrófono en el teclado de tu celular.")

    if procesar:
        if not api_key:
            st.error("Configura tu API Key de Gemini en la barra lateral.")
        elif not user_input.strip():
            st.warning("Escribe o dicta algo para registrar.")
        else:
            with st.spinner("Analizando..."):
                try:
                    client = genai.Client(api_key=api_key)
                    categories_list = list(st.session_state.categories.keys())
                    prompt = f"""
                    Analiza el siguiente texto de finanzas personales. Categorías disponibles: {json.dumps(categories_list, ensure_ascii=False)}.
                    Devuelve un JSON estricto con una lista de objetos que contengan:
                    - "tipo": "gasto" o "ingreso"
                    - "monto": número exacto
                    - "descripcion": detalle breve
                    - "categoria": una de las categorías válidas
                    Texto: "{user_input}"
                    """
                    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                    
                    text_res = response.text.strip()
                    text_res = text_res.replace("```json", "")
                    text_res = text_res.replace("
