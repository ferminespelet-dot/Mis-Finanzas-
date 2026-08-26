import streamlit as st
import pandas as pd
import json
import datetime
import os
from google import genai
import plotly.express as px
import requests

st.set_page_config(
    page_title="Finanzas",
    page_icon="🍊",
    layout="centered"
)

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
        background-color: rgba(217,119,6,0.05);
        padding: 10px;
        border-radius: 10px;
        border: 1px solid rgba(217,119,6,0.1);
    }
</style>
""", unsafe_allow_html=True)

# SISTEMA DE PERFILES
st.markdown(
    "<div style='text-align: center;'>", 
    unsafe_allow_html=True
)
usuario_actual = st.radio(
    "👤 ¿Quién está usando la app?", 
    ["Fermín", "Irina"], 
    horizontal=True
)
st.markdown("</div>", unsafe_allow_html=True)

if "usuario_previo" not in st.session_state:
    st.session_state.usuario_previo = usuario_actual

if st.session_state.usuario_previo != usuario_actual:
    keys_to_delete = [
        "categories", "transactions", "savings", 
        "thoughts", "pendings", "last_added"
    ]
    for key in keys_to_delete:
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
    "Irina": [
        "irina", "iri", "novia", "romántico", 
        "regalos", "ella"
    ],
    "Futbol": [
        "futbol", "fútbol", "cancha", "pelota"
    ],
    "Supermercado": [
        "supermercado", "super", "almacén"
    ],
    "Comida": [
        "comida", "hamburguesa", "pizza", "delivery"
    ],
    "Kiosco": [
        "coquita", "alfajor", "gomitas", "sube"
    ],
    "Tabaco": [
        "cigarrillos", "tabaco", "filtros", "pucho"
    ],
    "Café y panadería": [
        "café", "merienda", "torta", "facturas"
    ],
    "Bazar": [
        "bazar", "poster", "sahumerios", "librería"
    ],
    "Salidas": [
        "cerveza", "boliche", "salidas", "barcito"
    ],
    "Bebida": [
        "vino", "cerveza", "alcohol"
    ],
    "Otros": [
        "libro", "ropa", "stickers", "perdí"
    ],
    "Música": [
        "cuerdas", "púas", "cables", "sala", "música"
    ],
    "Devoluciones": [
        "devuelve", "devolvió", "reembolso"
    ]
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
    st.session_state.categories = load_json(
        CATEGORIES_FILE, DEFAULT_CATEGORIES
    )
if "transactions" not in st.session_state:
    st.session_state.transactions = load_json(DATA_FILE, [])
if "savings" not in st.session_state:
    st.session_state.savings = load_json(SAVINGS_FILE, [])
if "thoughts" not in st.session_state:
    st.session_state.thoughts = load_json(THOUGHTS_FILE, [])
if "pendings" not in st.session_state:
    st.session_state.pendings = load_json(PENDINGS_FILE, [])

st.sidebar.header("⚙️ Configuración")
api_key = st.sidebar.text_input(
    "Gemini API Key", 
    type="password", 
    value=os.environ.get("GEMINI_API_KEY", "")
)

def get_dolar_blue():
    try:
        url = "https://dolarapi.com/v1/dolares/blue"
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            return res.json().get("venta", 1300)
    except:
        pass
    return 1300

dolar_blue_venta = get_dolar_blue()

now = datetime.datetime.now()
if now.day >= 28:
    current_cycle_start = datetime.datetime(
        now.year, now.month, 28
    )
    if now.month == 12:
        next_cycle_start = datetime.datetime(
            now.year + 1, 1, 28
        )
    else:
        next_cycle_start = datetime.datetime(
            now.year, now.month + 1, 28
        )
else:
    if now.month == 1:
        current_cycle_start = datetime.datetime(
            now.year - 1, 12, 28
        )
    else:
        current_cycle_start = datetime.datetime(
            now.year, now.month - 1, 28
        )
    next_cycle_start = datetime.datetime(
        now.year, now.month, 28
    )

icono = "🍊" if usuario_actual == "Fermín" else "🌸"
st.title(f"Hola, {usuario_actual} {icono}")
st.caption("Tu espacio de Finanzas & Cerebro")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "💬 Registro", "📊 Balance", "📜 Historial", 
    "📅 Ciclos", "🏷️ Categorías", "🧠 Cerebro"
])

df_tx = pd.DataFrame(st.session_state.transactions)
if not df_tx.empty:
    df_tx["timestamp_dt"] = pd.to_datetime(
        df_tx["timestamp"]
    )
    
    mask = (
        (df_tx["timestamp_dt"] >= current_cycle_start) & 
        (df_tx["timestamp_dt"] < next_cycle_start)
    )
    df_cycle = df_tx[mask]
else:
    df_cycle = pd.DataFrame(
        columns=["tipo", "monto", "descripcion", "categoria", "timestamp"]
    )

total_ingresos = 0
total_gastos = 0
if not df_cycle.empty:
    mask_ingreso = df_cycle["tipo"] == "ingreso"
    total_ingresos = df_cycle[mask_ingreso]["monto"].sum()
    
    mask_gasto = df_cycle["tipo"] == "gasto"
    total_gastos = df_cycle[mask_gasto]["monto"].sum()

saldo_actual = total_ingresos - total_gastos

with tab1:
    st.markdown("### 🎙️ Registro Rápido")
    
    user_input = st.text_area(
        "Registro", 
        placeholder="Ej: Compré un alfajor por 2000...", 
        height=100, 
        label_visibility="collapsed"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        mic_btn = st.button("🎙️ Micrófono", use_container_width=True)
    with col2:
        procesar = st.button("✨ Procesar", type="primary", use_container_width=True)

    if mic_btn:
        st.info("💡 Usa el micrófono del teclado de tu celular.")

    if procesar:
        if not api_key:
            st.error("Configura tu API Key lateral.")
        elif not user_input.strip():
            st.warning("Escribe algo para registrar.")
        else:
            with st.spinner("Analizando..."):
                try:
                    client = genai.Client(api_key=api_key)
                    cat_list = list(
                        st.session_state.categories.keys()
                    )
                    prompt = (
                        "Analiza el texto. Categorías: "
                        f"{json.dumps(cat_list)}. "
                        "Devuelve un JSON con lista de objetos: "
                        "'tipo'(gasto/ingreso), 'monto'(numero), "
                        "'descripcion', 'categoria'. "
                        f"Texto: '{user_input}'"
                    )
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash', 
                        contents=prompt
                    )
                    
                    text_res = response.text.strip()
                    text_res = text_res.replace(
                        "```json", ""
                    )
                    text_res = text_res.replace(
                        "```", ""
                    )
                    text_res = text_res.strip()
                    
                    new_txs = json.loads(text_res)
                    ts = datetime.datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    
                    for tx in new_txs:
                        tx["timestamp"] = ts
                        st.session_state.transactions.append(tx)
                    
                    save_json(DATA_FILE, st.session_state.transactions)
                    st.success("¡Registrado con éxito!")
                    st.session_state["last_added"] = new_txs
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    st.divider()
    
    st.subheader("📌 Vencimientos")
    with st.expander("➕ Agregar nuevo pago"):
        with st.form("pending_form", clear_on_submit=True):
            p_concepto = st.text_input("Concepto")
            p_monto = st.number_input(
                "Monto ($)", min_value=0.0, step=1000.0
            )
            val_fecha = datetime.date.today() + datetime.timedelta(days=5)
            p_fecha = st.date_input("Fecha límite", value=val_fecha)
            
            if st.form_submit_button("Guardar") and p_concepto:
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
            hoy = pd.to_datetime(datetime.date.today())
            fecha_v = pd.to_datetime(row["fecha"])
            d_left = (fecha_v - hoy).days
            
            if d_left >= 0:
                badge = f"⚠️ Faltan {d_left} días"
            else:
                badge = "❗ VENCIDO"
                
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(
                    f"**{row['concepto']}** - \${row['monto']:,.0f} <br>"
                    f"<small>{row['fecha']} | *{badge}*</small>", 
                    unsafe_allow_html=True
                )
            with col_b:
                if st.button("✅", key=f"del_p_{row['id']}"):
                    st.session_state.pendings = [
                        p for p in st.session_state.pendings 
                        if p["id"] != row["id"]
                    ]
                    save_json(PENDINGS_FILE, st.session_state.pendings)
                    st.rerun()
            st.divider()

    st.subheader("📊 Resumen del Ciclo")
    col1, col2, col3 = st.columns(3)
    col1.metric("Saldo", f"${saldo_actual:,.0f}")
    col2.metric("Gastos", f"${total_gastos:,.0f}")
    
    total_dias = (next_cycle_start - current_cycle_start).days
    dias_pasados = (datetime.datetime.now() - current_cycle_start).days
    progreso = min(1.0, max(0.0, dias_pasados / total_dias))
    
    dias_faltantes = (next_cycle_start - datetime.datetime.now()).days
    col3.progress(progreso, text=f"Faltan {max(0, dias_faltantes)} d.")

with tab2:
    st.subheader("📊 Gastos por Categoría")
    if not df_cycle.empty:
        df_g = df_cycle[df_cycle["tipo"] == "gasto"]
        if not df_g.empty:
            fig = px.pie(
                df_g, values="monto", names="categoria", 
                hole=0.4, 
                color_discrete_sequence=px.colors.sequential.Oranges
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin gastos.")
    else:
        st.info("Sin registros.")

with tab3:
    st.subheader("📜 Movimientos")
    if not df_cycle.empty:
        q = st.text_input("🔍 Buscar")
        df_show = df_cycle[
            ["timestamp", "tipo", "categoria", "descripcion", "monto"]
        ].sort_values(by="timestamp", ascending=False)
        
        if q:
            filtro_desc = df_show["descripcion"].str.contains(
                q, case=False, na=False
            )
            filtro_cat = df_show["categoria"].str.contains(
                q, case=False, na=False
            )
            df_show = df_show[filtro_desc | filtro_cat]
            
        st.dataframe(df_show, use_container_width=True)
        
        if st.button("🗑️ Borrar último"):
            if st.session_state.transactions:
                st.session_state.transactions.pop()
                save_json(DATA_FILE, st.session_state.transactions)
                st.success("Borrado.")
                st.rerun()
    else:
        st.write("Sin movimientos.")

with tab4:
    st.subheader("📅 Cierre de Mes (Día 28)")
    st.markdown(f"💱 **Dólar Blue:** \${dolar_blue_venta:,.2f} ARS")
    leftover = st.number_input(
        "Saldo sobrante ($):", 
        min_value=0.0, 
        value=float(max(0, saldo_actual)), 
        step=1000.0
    )
    
    ca, cb = st.columns(2)
    with ca:
        if st.button("💎 Ahorrar (USD)", use_container_width=True):
            if leftover > 0:
                usd = leftover / dolar_blue_venta
                fecha_ahorro = datetime.datetime.now().strftime("%Y-%m-%d")
                st.session_state.savings.append({
                    "fecha": fecha_ahorro, 
                    "pesos_ahorrados": leftover, 
                    "cotizacion_blue": dolar_blue_venta, 
                    "dolares": usd
                })
                save_json(SAVINGS_FILE, st.session_state.savings)
                st.success(f"¡Guardados US$ {usd:.2f}!")
    with cb:
        if st.button("📥 Mantener saldo", use_container_width=True):
            st.info("Saldo retenido.")
            
    st.divider()
    st.subheader("💰 Alcancía")
    if st.session_state.savings:
        df_s = pd.DataFrame(st.session_state.savings)
        st.metric("Total USD", f"US$ {df_s['dolares'].sum():.2f}")
        st.dataframe(df_s, use_container_width=True)
    else:
        st.info("No hay ahorros aún.")

with tab5:
    st.subheader("🏷️ Categorías")
    with st.form("nc"):
        n_name = st.text_input("Nueva categoría")
        n_keys = st.text_input("Palabras clave (por coma)")
        if st.form_submit_button("Agregar") and n_name:
            lista_keys = [k.strip().lower() for k in n_keys.split(",")]
            st.session_state.categories[n_name.strip()] = lista_keys
            save_json(CATEGORIES_FILE, st.session_state.categories)
            st.success("Agregada.")
            st.rerun()
            
    for cat, keys in st.session_state.categories.items():
        st.markdown(f"- **{cat}**: {', '.join(keys)}")

with tab6:
    st.subheader("🧠 Segundo Cerebro")
    st.markdown("Ideas, pendientes o notas.")
    
    raw_thought = st.text_area(
        "Notas", 
        placeholder="Ej: Pensé en un riff...", 
        label_visibility="collapsed"
    )
    if st.button("✨ Procesar Idea", type="primary", use_container_width=True):
        if not api_key:
            st.error("Falta API Key.")
        elif not raw_thought.strip():
            st.warning("Escribe algo.")
        else:
            with st.spinner("Procesando..."):
                try:
                    client = genai.Client(api_key=api_key)
                    prompt = (
                        "Analiza el texto y sepáralo en ideas. "
                        "Determina: 'titulo', 'categoria' (Música, "
                        "Universidad, Compras, Random), 'contenido'. "
                        "Devuelve ÚNICAMENTE JSON (lista de objetos). "
                        f"Texto: '{raw_thought}'"
                    )
                    resp = client.models.generate_content(
                        model='gemini-2.5-flash', 
                        contents=prompt
                    )
                    
                    tr = resp.text.strip()
                    tr = tr.replace("```json", "")
                    tr = tr.replace("```", "")
                    tr = tr.strip()
                    
                    new_thoughts = json.loads(tr)
                    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    for item in new_thoughts:
                        thread_obj = {
                            "id": datetime.datetime.now().strftime(
                                "%Y%m%d%H%M%S%f"
                            ),
                            "titulo": item.get("titulo", "Sin título"),
                            "categoria": item.get("categoria", "Random"),
                            "creado": ts,
                            "mensajes": [{
                                "autor": "usuario", 
                                "texto": item.get("contenido", "")
                            }]
                        }
                        st.session_state.thoughts.append(thread_obj)
                    
                    save_json(THOUGHTS_FILE, st.session_state.thoughts)
                    st.success("¡Hilos creados!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    st.divider()
    if st.session_state.thoughts:
        opciones_hilos = list(
            {t["id"]: f"[{t['categoria']}] {t['titulo']}" 
             for t in st.session_state.thoughts}.keys()
        )
        
        def format_hilo(x):
            for t in st.session_state.thoughts:
                if t["id"] == x:
                    return f"[{t['categoria']}] {t['titulo']}"
            return x
            
        selected_id = st.selectbox(
            "Tus hilos guardados:", 
            options=opciones_hilos, 
            format_func=format_hilo
        )
        
        current_thread = next(
            (t for t in st.session_state.thoughts if t["id"] == selected_id), 
            None
        )
        
        if current_thread:
            st.markdown(f"### 💬 {current_thread['titulo']}")
            for msg in current_thread["mensajes"]:
                with st.chat_message(
                    "user" if msg["autor"]=="usuario" else "assistant"
                ):
                    st.write(msg["texto"])
            
            with st.form(f"chat_form_{selected_id}", clear_on_submit=True):
                reply = st.text_input("Agregar nota...")
                if st.form_submit_button("Enviar") and reply:
                    current_thread["mensajes"].append(
                        {"autor": "usuario", "texto": reply}
                    )
                    save_json(THOUGHTS_FILE, st.session_state.thoughts)
                    st.rerun()
            
            if st.button("🗑️ Eliminar hilo"):
                st.session_state.thoughts = [
                    t for t in st.session_state.thoughts 
                    if t["id"] != selected_id
                ]
                save_json(THOUGHTS_FILE, st.session_state.thoughts)
                st.rerun()
    else:
        st.info("No hay hilos.")
