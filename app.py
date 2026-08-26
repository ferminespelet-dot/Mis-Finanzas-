import streamlit as st
import pandas as pd
import json
import datetime
import os
from google import genai
import plotly.express as px
import requests

# Configuración de página 
st.set_page_config(page_title="Finanzas & Cerebro 🧠", page_icon="🍊", layout="centered")

# Estética Claudeana / Naranjita Minimalista
st.markdown("""
<style>
    .stApp {
        background-color: #FAF8F5;
        color: #38322C;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    .stButton>button {
        background-color: #D97706;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 500;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #B45309;
        border: none;
        color: white;
    }
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E6E0D5;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    /* Estilo para los tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #FFFFFF;
        border-radius: 8px;
        padding: 10px 16px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .stTabs [aria-selected="true"] {
        background-color: #D97706;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

DATA_FILE = "transactions.json"
CATEGORIES_FILE = "categories.json"
SAVINGS_FILE = "savings.json"
THOUGHTS_FILE = "thoughts.json"
PENDINGS_FILE = "pendings.json"

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

# Ciclo financiero (Día 28)
now = datetime.datetime.now()
if now.day >= 28:
    current_cycle_start = datetime.datetime(now.year, now.month, 28)
    next_cycle_start = datetime.datetime(now.year + 1, 1, 28) if now.month == 12 else datetime.datetime(now.year, now.month + 1, 28)
else:
    current_cycle_start = datetime.datetime(now.year - 1, 12, 28) if now.month == 1 else datetime.datetime(now.year, now.month - 1, 28)
    next_cycle_start = datetime.datetime(now.year, now.month, 28)

st.title("Hola, Fermín 🍊")
st.markdown("Tu espacio de Finanzas & Cerebro")

# 6 Pestañas
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "💬 Registrar", "📊 Balance", "📜 Historial", "📅 Ciclos & Ahorros", "🏷️ Categorías", "🧠 Segundo Cerebro"
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

# PESTAÑA 1: REGISTRAR (Cero fricción: Micrófono y Caja de Texto arriba de todo)
with tab1:
    
    col_mic, col_txt = st.columns([1, 4])
    with col_mic:
        st.markdown("<br>", unsafe_allow_html=True)
        mic_clicked = st.button("🎙️", help="Botón de micrófono rápido estilo Gemini", use_container_width=True)
    with col_txt:
        user_input = st.text_area("", placeholder="¿Qué gastaste o ingresaste hoy? Ej: Le compré flores a Irina por 10.000...", height=80, label_visibility="collapsed")
    
    if mic_clicked:
        st.info("🎙️ Micrófono activado (Usa el dictado de voz de tu teclado para escribir en la caja).")

    if st.button("✨ Procesar Movimiento", type="primary", use_container_width=True):
        if not api_key:
            st.error("Configura tu API Key de Gemini en la barra lateral.")
        elif not user_input.strip():
            st.warning("Escribe o dicta algo para registrar.")
        else:
            with st.spinner("Analizando con Gemini..."):
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
                    if text_res.startswith("```json"): text_res = text_res[7:]
                    if text_res.endswith("```"): text_res = text_res[:-3]
                    
                    new_txs = json.loads(text_res.strip())
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    for tx in new_txs:
                        tx["timestamp"] = timestamp
                        st.session_state.transactions.append(tx)
                    
                    save_json(DATA_FILE, st.session_state.transactions)
                    st.success(f"¡Registrado con éxito ({len(new_txs)} movimientos)!")
                    st.session_state["last_added"] = new_txs
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    st.divider()
    
    # SECCIÓN: Vencimientos y Pendientes
    st.subheader("📌 Vencimientos y Pendientes")
    with st.expander("➕ Agregar nuevo vencimiento", expanded=False):
        with st.form("pending_form", clear_on_submit=True):
            p_concepto = st.text_input("Concepto (Ej: Sala de ensayo, Internet)")
            p_monto = st.number_input("Monto estimado ($ ARS)", min_value=0.0, step=1000.0)
            p_fecha = st.date_input("Fecha límite", value=datetime.date.today() + datetime.timedelta(days=5))
            if st.form_submit_button("Guardar Pendiente") and p_concepto:
                st.session_state.pendings.append({
                    "id": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
                    "concepto": p_concepto,
                    "monto": p_monto,
                    "fecha": str(p_fecha)
                })
                save_json(PENDINGS_FILE, st.session_state.pendings)
                st.success("¡Guardado!")
                st.rerun()

    if st.session_state.pendings:
        df_p = pd.DataFrame(st.session_state.pendings)
        df_p["fecha_dt"] = pd.to_datetime(df_p["fecha"])
        df_p = df_p.sort_values(by="fecha_dt")
        for idx, row in df_p.iterrows():
            d_left = (pd.to_datetime(row["fecha"]) - pd.to_datetime(datetime.date.today())).days
            badge = f"⚠️ Vence en {d_left} días" if d_left >= 0 else "❗ VENCIDO"
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f"**{row['concepto']}** - \${row['monto']:,.0f} <br> <small>{row['fecha']} | *{badge}*</small>", unsafe_allow_html=True)
            with col_b:
                if st.button("✅ Pagado", key=f"del_p_{row['id']}"):
                    st.session_state.pendings = [p for p in st.session_state.pendings if p["id"] != row["id"]]
                    save_json(PENDINGS_FILE, st.session_state.pendings)
                    st.rerun()
            st.divider()
    else:
        st.info("No hay vencimientos futuros anotados.")

    st.subheader("📊 Resumen del Ciclo")
    col1, col2, col3 = st.columns(3)
    col1.metric("Saldo Disponible", f"${saldo_actual:,.0f}")
    col2.metric("Gastos Totales", f"${total_gastos:,.0f}")
    
    total_dias = (next_cycle_start - current_cycle_start).days
    dias_pasados = (datetime.datetime.now() - current_cycle_start).days
    progreso = min(1.0, max(0.0, dias_pasados / total_dias))
    col3.progress(progreso, text=f"Faltan {max(0, (next_cycle_start - datetime.datetime.now()).days)} días para el 28")

    if "last_added" in st.session_state:
        st.info("💡 **Último movimiento:**")
        st.json(st.session_state["last_added"])

# PESTAÑA 2: Balance
with tab2:
    st.subheader("📊 Gastos por Categoría")
    if not df_cycle.empty and not df_cycle[df_cycle["tipo"] == "gasto"].empty:
        df_g = df_cycle[df_cycle["tipo"] == "gasto"]
        fig = px.pie(df_g, values="monto", names="categoria", title="Egresos del Ciclo", hole=0.4, color_discrete_sequence=px.colors.sequential.Oranges)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay gastos registrados en este ciclo.")

# PESTAÑA 3: Historial
with tab3:
    st.subheader("📜 Historial de Movimientos")
    if not df_cycle.empty:
        q = st.text_input("🔍 Buscar por descripción o categoría")
        df_show = df_cycle[["timestamp", "tipo", "categoria", "descripcion", "monto"]].sort_values(by="timestamp", ascending=False)
        if q:
            df_show = df_show[df_show["descripcion"].str.contains(q, case=False, na=False) | df_show["categoria"].str.contains(q, case=False, na=False)]
        st.dataframe(df_show, use_container_width=True)
        if st.button("🗑️ Borrar último movimiento"):
            if st.session_state.transactions:
                st.session_state.transactions.pop()
                save_json(DATA_FILE, st.session_state.transactions)
                st.success("Borrado.")
                st.rerun()
    else:
        st.write("Sin movimientos.")

# PESTAÑA 4: Ciclos & Ahorros
with tab4:
    st.subheader("📅 Cierre de Mes (Día 28)")
    st.markdown(f"💱 **Dólar Blue Actual:** \${dolar_blue_venta:,.2f} ARS")
    leftover = st.number_input("Saldo sobrante a evaluar ($ ARS):", min_value=0.0, value=float(max(0, saldo_actual)), step=1000.0)
    
    ca, cb = st.columns(2)
    with ca:
        if st.button("💎 Ahorrar (Pasar a Dólares)"):
            if leftover > 0:
                usd = leftover / dolar_blue_venta
                st.session_state.savings.append({"fecha": datetime.datetime.now().strftime("%Y-%m-%d"), "pesos_ahorrados": leftover, "cotizacion_blue": dolar_blue_venta, "dolares": usd})
                save_json(SAVINGS_FILE, st.session_state.savings)
                st.success(f"¡Guardados US$ {usd:.2f} en tu alcancía!")
    with cb:
        if st.button("📥 Mantener como saldo"):
            st.info("Saldo retenido para el mes siguiente.")
            
    st.divider()
    st.subheader("💰 Alcancía de Ahorros")
    if st.session_state.savings:
        df_s = pd.DataFrame(st.session_state.savings)
        st.metric("Total Dólares", f"US$ {df_s['dolares'].sum():.2f}")
        st.dataframe(df_s, use_container_width=True)
    else:
        st.info("No hay ahorros aún.")

# PESTAÑA 5: Categorías
with tab5:
    st.subheader("🏷️ Gestionar Categorías")
    with st.form("nc"):
        n_name = st.text_input("Nueva categoría")
        n_keys = st.text_input("Palabras clave (separadas por coma)")
        if st.form_submit_button("Agregar") and n_name:
            st.session_state.categories[n_name.strip()] = [k.strip().lower() for k in n_keys.split(",")]
            save_json(CATEGORIES_FILE, st.session_state.categories)
            st.success("Agregada.")
            st.rerun()
    for cat, keys in st.session_state.categories.items():
        st.markdown(f"- **{cat}**: {', '.join(keys)}")

# PESTAÑA 6: Segundo Cerebro
with tab6:
    st.subheader("🧠 Segundo Cerebro")
    st.markdown("Escribí ideas de música, universidad, wishlist o pensamientos intrusivos. La IA creará hilos.")
    
    raw_thought = st.text_area("Caja de pensamientos libres", placeholder="Ej: Pensé en un riff en re menor...", label_visibility="collapsed")
    if st.button("✨ Procesar y Organizar", type="primary"):
        if not api_key:
            st.error("Configura tu API Key.")
        elif not raw_thought.strip():
            st.warning("Escribe algo.")
        else:
            with st.spinner("Organizando hilos..."):
                try:
                    client = genai.Client(api_key=api_key)
                    prompt = f"""
                    Analiza el texto del usuario. Sepáralo en diferentes ideas o notas independientes.
                    Para cada idea, determina:
                    - "titulo": título corto y representativo
                    - "categoria": elige entre ["Música", "Universidad", "Wishlist / Compras", "Ideas Random"]
                    - "contenido": desarrollo del pensamiento
                    Devuelve ÚNICAMENTE JSON válido (lista de objetos).
                    Texto: "{raw_thought}"
                    """
                    resp = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                    tr = resp.text.strip()
                    if tr.startswith("```json"): tr = tr[7:]
                    if tr.endswith("```"): tr = tr[:-3]
                    
                    new_thoughts = json.loads(tr.strip())
                    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    for item in new_thoughts:
                        thread_obj = {
                            "id": datetime.datetime.now().strftime("%Y%m%d%H%M%S%f"),
                            "titulo": item.get("titulo", "Idea sin título"),
                            "categoria": item.get("categoria", "Ideas Random"),
                            "creado": ts,
                            "mensajes": [{"autor": "usuario", "texto": item.get("contenido", "")}]
                        }
                        st.session_state.thoughts.append(thread_obj)
                    
                    save_json(THOUGHTS_FILE, st.session_state.thoughts)
                    st.success("¡Hilos creados!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    st.divider()
    st.subheader("📂 Tus Hilos Guardados")
    if st.session_state.thoughts:
        thought_titles = {t["id"]: f"[{t['categoria']}] {t['titulo']} ({t['creado']})" for t in st.session_state.thoughts}
        selected_id = st.selectbox("Selecciona un hilo:", options=list(thought_titles.keys()), format_func=lambda x: thought_titles[x])
        
        current_thread = next((t for t in st.session_state.thoughts if t["id"] == selected_id), None)
        if current_thread:
            st.markdown(f"### 💬 {current_thread['titulo']}")
            for msg in current_thread["mensajes"]:
                with st.chat_message("user" if msg["autor"]=="usuario" else "assistant"):
                    st.write(msg["texto"])
            
            with st.form(f"chat_form_{selected_id}", clear_on_submit=True):
                reply = st.text_input("Agregar nota al hilo...")
                if st.form_submit_button("Enviar") and reply:
                    current_thread["mensajes"].append({"autor": "usuario", "texto": reply})
                    save_json(THOUGHTS_FILE, st.session_state.thoughts)
                    st.rerun()
            
            if st.button("🗑️ Eliminar hilo"):
                st.session_state.thoughts = [t for t in st.session_state.thoughts if t["id"] != selected_id]
                save_json(THOUGHTS_FILE, st.session_state.thoughts)
                st.rerun()
    else:
        st.info("No hay hilos creados.")
