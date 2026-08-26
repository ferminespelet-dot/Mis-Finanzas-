import streamlit as st
import pandas as pd
import json
import datetime
import os
from google import genai
import plotly.express as px
import requests

# 1. CONFIGURACIÓN DE PÁGINA Y ESTÉTICA
st.set_page_config(page_title="Finanzas & Cerebro", page_icon="🍊", layout="centered")

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

# 2. FUNCIONES BASE
def load_json(filename, default):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_dolar_blue():
    try:
        url = "https://dolarapi.com/v1/dolares/blue"
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            return res.json().get("venta", 1300)
    except:
        pass
    return 1300

def iniciar_sesion(usuario):
    for key in ["categories", "transactions", "savings", "thoughts", "pendings", "last_added", "recomendacion_ia"]:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.usuario_autenticado = usuario
    st.rerun()

def cerrar_sesion():
    st.session_state.usuario_autenticado = None
    for key in ["categories", "transactions", "savings", "thoughts", "pendings", "last_added", "recomendacion_ia"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# 3. GESTIÓN DE SEGURIDAD (PIN)
PINS_FILE = "pins_security.json"
passwords_guardadas = load_json(PINS_FILE, {})

if "usuario_autenticado" not in st.session_state:
    st.session_state.usuario_autenticado = None

# ==============================================================
# PANTALLA DE LOGIN
# ==============================================================
if st.session_state.usuario_autenticado is None:
    st.markdown("<h1 style='text-align: center;'>Finanzas & Cerebro 🧠</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Selecciona tu perfil para ingresar</p>", unsafe_allow_html=True)
    st.divider()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        usuario_seleccionado = st.radio("Perfil:", ["Fermín", "Irina"], horizontal=True, label_visibility="collapsed")
        st.markdown("<br>", unsafe_allow_html=True)
        
        if usuario_seleccionado in passwords_guardadas:
            st.markdown(f"#### 🔒 Ingresar como {usuario_seleccionado}")
            pin_ingresado = st.text_input("Ingresa tu PIN numérico", type="password")
            if st.button("Entrar", type="primary", use_container_width=True):
                if pin_ingresado == passwords_guardadas[usuario_seleccionado]:
                    iniciar_sesion(usuario_seleccionado)
                else:
                    st.error("PIN incorrecto. Inténtalo de nuevo.")
        else:
            st.markdown(f"#### 🆕 Crear perfil: {usuario_seleccionado}")
            st.info("Crea un PIN numérico para proteger tus datos.")
            nuevo_pin = st.text_input("Ingresa un nuevo PIN", type="password")
            confirmar_pin = st.text_input("Confirma tu PIN", type="password")
            if st.button("Crear perfil y Entrar", type="primary", use_container_width=True):
                if nuevo_pin and nuevo_pin.isdigit():
                    if nuevo_pin == confirmar_pin:
                        passwords_guardadas[usuario_seleccionado] = nuevo_pin
                        save_json(PINS_FILE, passwords_guardadas)
                        st.success("¡PIN creado con éxito!")
                        iniciar_sesion(usuario_seleccionado)
                    else:
                        st.error("Los PINs no coinciden.")
                else:
                    st.error("El PIN debe contener únicamente números.")
    
    st.stop()

# ==============================================================
# PANTALLA PRINCIPAL DE LA APP
# ==============================================================
usuario_actual = st.session_state.usuario_autenticado

# 100% INDEPENDENCIA DE ARCHIVOS
sufijo = "" if usuario_actual == "Fermín" else "_irina"
DATA_FILE = f"transactions{sufijo}.json"
CATEGORIES_FILE = f"categories{sufijo}.json"
SAVINGS_FILE = f"savings{sufijo}.json"
THOUGHTS_FILE = f"thoughts{sufijo}.json"
PENDINGS_FILE = f"pendings{sufijo}.json"

def obtener_categorias_iniciales(usuario):
    base = {
        "Fútbol y Cancha": ["futbol", "fútbol", "cancha", "pelota", "choripan", "entrada", "estudiantes", "el pincha", "pincha", "estadio"],
        "Paseos y Salidas": ["museos", "museo", "paseo", "capital", "buenos aires", "helado", "barcito", "salidas", "cine", "teatro"],
        "Bolucompras": ["bolucompras", "boludeces", "chucherias", "kiosco", "alfajor", "gomitas", "energizante"],
        "Librería y Facu": ["libreria", "librería", "útiles escolares", "fotocopias", "gomaeva", "articulos para el jardin", "marionetas", "tela", "temperas", "pintura", "jardín", "apuntes"],
        "Supermercado": ["supermercado", "super", "almacén", "verdulería", "hiper", "carnicería"],
        "Comida y Delivery": ["comida", "hamburguesa", "pizza", "delivery", "pedidosya", "rappi", "almuerzo", "cena"],
        "Café y panadería": ["café", "merienda", "torta", "panadería", "facturas", "medialunas", "desayuno"],
        "Bazar": ["bazar", "poster", "póster", "sahumerios", "plantas", "detalles", "decoración", "regalería"],
        "Bebida": ["vino", "cerveza", "alcohol", "fernet", "vodka", "escabio", "tragos"],
        "Transporte": ["sube", "colectivo", "tren", "uber", "taxi", "nafta", "peaje"],
        "Suscripciones": ["netflix", "spotify", "gimnasio", "internet", "celular"],
        "Tabaco": ["cigarrillos", "tabaco", "filtros", "pucho", "papelillos"],
        "Música": ["cuerdas", "púas", "cables", "sala", "música", "recitales", "ensayo"],
        "Devoluciones": ["devuelve", "devolvió", "reembolso"],
        "Otros": ["ropa", "perdí", "stickers", "varios"]
    }
    
    if usuario == "Fermín":
        base["Irina"] = ["irina", "iri", "novia", "amor", "regalos", "flores a iri", "ella"]
    else:
        base["Fermín"] = ["fermin", "fer", "novio", "amor", "regalos", "él"]
        
    return base

if "categories" not in st.session_state:
    st.session_state.categories = load_json(CATEGORIES_FILE, obtener_categorias_iniciales(usuario_actual))
if "transactions" not in st.session_state:
    st.session_state.transactions = load_json(DATA_FILE, [])
if "savings" not in st.session_state:
    st.session_state.savings = load_json(SAVINGS_FILE, [])
if "thoughts" not in st.session_state:
    st.session_state.thoughts = load_json(THOUGHTS_FILE, [])
if "pendings" not in st.session_state:
    st.session_state.pendings = load_json(PENDINGS_FILE, [])
if "recomendacion_ia" not in st.session_state:
    st.session_state.recomendacion_ia = ""

st.sidebar.header("⚙️ Configuración")
api_key = st.sidebar.text_input("Gemini API Key", type="password", value=os.environ.get("GEMINI_API_KEY", ""))
st.sidebar.divider()
if st.sidebar.button("🚪 Cerrar Sesión", type="primary"):
    cerrar_sesion()

dolar_blue_venta = get_dolar_blue()

now = datetime.datetime.now()
if now.day >= 28:
    current_cycle_start = datetime.datetime(now.year, now.month, 28)
    if now.month == 12:
        next_cycle_start = datetime.datetime(now.year + 1, 1, 28)
    else:
        next_cycle_start = datetime.datetime(now.year, now.month + 1, 28)
else:
    if now.month == 1:
        current_cycle_start = datetime.datetime(now.year - 1, 12, 28)
    else:
        current_cycle_start = datetime.datetime(now.year, now.month - 1, 28)
    next_cycle_start = datetime.datetime(now.year, now.month, 28)

icono = "🍊" if usuario_actual == "Fermín" else "🌸"
st.title(f"Hola, {usuario_actual} {icono}")
st.caption(f"Tu espacio de Finanzas & Cerebro (Sesión Privada)")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "💬 Registro", "📊 Balance", "📜 Historial", "📅 Ciclos", "🏷️ Categorías", "🧠 Cerebro"
])

df_tx = pd.DataFrame(st.session_state.transactions)
if not df_tx.empty:
    df_tx["timestamp_dt"] = pd.to_datetime(df_tx["timestamp"])
    mask = (df_tx["timestamp_dt"] >= current_cycle_start) & (df_tx["timestamp_dt"] < next_cycle_start)
    df_cycle = df_tx[mask]
else:
    df_cycle = pd.DataFrame(columns=["tipo", "monto", "descripcion", "categoria", "timestamp"])

total_ingresos = 0
total_gastos = 0
if not df_cycle.empty:
    total_ingresos = df_cycle[df_cycle["tipo"] == "ingreso"]["monto"].sum()
    total_gastos = df_cycle[df_cycle["tipo"] == "gasto"]["monto"].sum()

saldo_actual = total_ingresos - total_gastos
dias_faltantes = (next_cycle_start - datetime.datetime.now()).days

# ==============================================================
# PESTAÑA 1: REGISTRO 
# ==============================================================
with tab1:
    st.markdown("### 🎙️ Registro Rápido")
    
    user_input = st.text_area("Registro", placeholder="Ej: Dos choripanes en la cancha por 5000...", height=100, label_visibility="collapsed")
    
    col1, col2 = st.columns(2)
    with col1:
        mic_btn = st.button("🎙️ Usar Micrófono", use_container_width=True)
    with col2:
        procesar = st.button("✨ Procesar", type="primary", use_container_width=True)

    if mic_btn:
        st.info("💡 Usa el micrófono del teclado de tu celular para dictar el gasto.")

    if st.session_state.recomendacion_ia:
        st.warning(f"💡 **Consejo de tu IA:** {st.session_state.recomendacion_ia}")

    if procesar:
        if not api_key:
            st.error("Falta tu API Key de Gemini en los Secretos.")
        elif not user_input.strip():
            st.warning("Escribe o dicta algo para registrar.")
        else:
            with st.spinner("La IA está procesando y pensando..."):
                try:
                    client = genai.Client(api_key=api_key)
                    cat_list = list(st.session_state.categories.keys())
                    
                    historial_reciente = ""
                    if not df_cycle.empty:
                        ultimos_gastos = df_cycle.tail(10)[["descripcion", "categoria", "monto"]].to_dict('records')
                        historial_reciente = f"Tus últimos 10 gastos fueron: {ultimos_gastos}."
                    
                    prompt = f"""
                    Eres un asistente financiero personal experto de {usuario_actual}. 
                    Categorías válidas: {json.dumps(cat_list, ensure_ascii=False)}.
                    Saldo actual: ${saldo_actual}. Días hasta cobrar (cierre 28): {dias_faltantes}.
                    {historial_reciente}
                    
                    Analiza este nuevo texto: "{user_input}"
                    
                    Devuelve ESTRICTAMENTE este JSON:
                    {{
                        "movimientos": [
                            {{"tipo": "gasto" o "ingreso", "monto": numero_exacto, "descripcion": "detalle", "categoria": "CATEGORIA_VALIDA"}}
                        ],
                        "recomendacion": "OPCIONAL. Escribe un mensaje (con un emoji) SOLO si el usuario está gastando muy rápido dado su saldo y días restantes, o si notas un patrón repetitivo nuevo. Si todo está normal, debes dejar esto completamente vacío ''."
                    }}
                    """
                    
                    response = client.models.generate_content(
                        model='gemini-1.5-flash', 
                        contents=prompt
                    )
                    
                    text_res = response.text.strip()
                    text_res = text_res.replace("```json", "").replace("```", "").strip()
                    
                    data = json.loads(text_res)
                    new_txs = data.get("movimientos", [])
                    recomendacion = data.get("recomendacion", "")
                    
                    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    for tx in new_txs:
                        tx["timestamp"] = ts
                        st.session_state.transactions.append(tx)
                    
                    save_json(DATA_FILE, st.session_state.transactions)
                    
                    st.session_state["last_added"] = new_txs
                    st.session_state.recomendacion_ia = recomendacion
                    st.rerun()
                except Exception as e:
                    st.error(f"Error de conexión con IA: {e}")

    st.divider()
    
    st.subheader("📌 Vencimientos")
    with st.expander("➕ Agregar nuevo pago pendiente"):
        with st.form("pending_form", clear_on_submit=True):
            p_concepto = st.text_input("Concepto (Ej: Sala de ensayo, Spotify)")
            p_monto = st.number_input("Monto estimado ($)", min_value=0.0, step=1000.0)
            val_fecha = datetime.date.today() + datetime.timedelta(days=5)
            p_fecha = st.date_input("Fecha límite", value=val_fecha)
            
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
            hoy = pd.to_datetime(datetime.date.today())
            fecha_v = pd.to_datetime(row["fecha"])
            d_left = (fecha_v - hoy).days
            
            badge = f"⚠️ Faltan {d_left} días" if d_left >= 0 else "❗ VENCIDO"
                
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(
                    f"**{row['concepto']}** - \${row['monto']:,.0f} <br>"
                    f"<small>{row['fecha']} | *{badge}*</small>", 
                    unsafe_allow_html=True
                )
            with col_b:
                if st.button("✅ Pagado", key=f"del_p_{row['id']}"):
                    st.session_state.pendings = [p for p in st.session_state.pendings if p["id"] != row["id"]]
                    save_json(PENDINGS_FILE, st.session_state.pendings)
                    st.rerun()
            st.divider()

    st.subheader("📊 Resumen del Ciclo")
    col1, col2, col3 = st.columns(3)
    col1.metric("Saldo Disp.", f"${saldo_actual:,.0f}")
    col2.metric("Gastos", f"${total_gastos:,.0f}")
    
    total_dias = (next_cycle_start - current_cycle_start).days
    dias_pasados = (datetime.datetime.now() - current_cycle_start).days
    progreso = min(1.0, max(0.0, dias_pasados / total_dias))
    
    col3.progress(progreso, text=f"Faltan {max(0, dias_faltantes)} d.")

# ==============================================================
# PESTAÑA 2: BALANCE
# ==============================================================
with tab2:
    st.subheader("📊 Gastos por Categoría")
    if not df_cycle.empty:
        df_g = df_cycle[df_cycle["tipo"] == "gasto"]
        if not df_g.empty:
            fig = px.pie(
                df_g, values="monto", names="categoria", hole=0.4, 
                color_discrete_sequence=px.colors.sequential.Oranges
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay gastos registrados en este ciclo mensual.")
    else:
        st.info("No hay registros en este ciclo.")

# ==============================================================
# PESTAÑA 3: HISTORIAL (CON EXPORTACIÓN A EXCEL)
# ==============================================================
with tab3:
    st.subheader("📜 Todos los Movimientos")
    if not df_cycle.empty:
        q = st.text_input("🔍 Buscar por palabra clave")
        df_show = df_cycle[["timestamp", "tipo", "categoria", "descripcion", "monto"]].sort_values(by="timestamp", ascending=False)
        
        if q:
            filtro_desc = df_show["descripcion"].str.contains(q, case=False, na=False)
            filtro_cat = df_show["categoria"].str.contains(q, case=False, na=False)
            df_show = df_show[filtro_desc | filtro_cat]
            
        st.dataframe(df_show, use_container_width=True)
        
        # EL BOTÓN MÁGICO DE EXPORTACIÓN (CSV para abrir en Excel)
        csv = df_show.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Historial en Excel (CSV)",
            data=csv,
            file_name=f"historial_finanzas_{usuario_actual}.csv",
            mime="text/csv",
        )
        st.divider()
        
        if st.button("🗑️ Deshacer / Borrar último movimiento"):
            if st.session_state.transactions:
                st.session_state.transactions.pop()
                save_json(DATA_FILE, st.session_state.transactions)
                st.success("Movimiento borrado exitosamente.")
                st.session_state.recomendacion_ia = ""
                st.rerun()
    else:
        st.write("Sin movimientos.")

# ==============================================================
# PESTAÑA 4: CICLOS Y AHORROS
# ==============================================================
with tab4:
    st.subheader("📅 Cierre de Mes (Día 28)")
    st.markdown(f"💱 **Dólar Blue Actual:** \${dolar_blue_venta:,.2f} ARS")
    leftover = st.number_input("Saldo sobrante a guardar ($):", min_value=0.0, value=float(max(0, saldo_actual)), step=1000.0)
    
    ca, cb = st.columns(2)
    with ca:
        if st.button("💎 Ahorrar (Convertir a USD)", use_container_width=True):
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
                st.success(f"¡Guardados US$ {usd:.2f} en tu alcancía!")
    with cb:
        if st.button("📥 Mantener como saldo", use_container_width=True):
            st.info("Saldo retenido para el próximo mes.")
            
    st.divider()
    st.subheader("💰 Tu Alcancía en Dólares")
    if st.session_state.savings:
        df_s = pd.DataFrame(st.session_state.savings)
        st.metric("Total Dólares Ahorrados", f"US$ {df_s['dolares'].sum():.2f}")
        st.dataframe(df_s, use_container_width=True)
    else:
        st.info("No hay ahorros registrados aún.")

# ==============================================================
# PESTAÑA 5: CATEGORÍAS
# ==============================================================
with tab5:
    st.subheader("🏷️ Gestionar Categorías")
    with st.form("nc"):
        n_name = st.text_input("Nombre de la nueva categoría")
        n_keys = st.text_input("Palabras clave asociadas (separadas por coma)")
        if st.form_submit_button("Agregar Categoría") and n_name:
            lista_keys = [k.strip().lower() for k in n_keys.split(",")]
            st.session_state.categories[n_name.strip()] = lista_keys
            save_json(CATEGORIES_FILE, st.session_state.categories)
            st.success("Categoría agregada correctamente.")
            st.rerun()
            
    for cat, keys in st.session_state.categories.items():
        st.markdown(f"- **{cat}**: {', '.join(keys)}")

# ==============================================================
# PESTAÑA 6: SEGUNDO CEREBRO (NOTAS)
# ==============================================================
with tab6:
    st.subheader("🧠 Segundo Cerebro")
    st.markdown("Caja para tus ideas libres, pendientes o wishlist.")
    
    raw_thought = st.text_area("Notas", placeholder="Ej: Pensé en un riff... o me gustaría comprar X...", label_visibility="collapsed")
    if st.button("✨ Organizar Idea con IA", type="primary", use_container_width=True):
        if not api_key:
            st.error("Falta tu API Key de Gemini en los Secretos.")
        elif not raw_thought.strip():
            st.warning("Escribe algo para poder organizarlo.")
        else:
            with st.spinner("Procesando tus pensamientos..."):
                try:
                    client = genai.Client(api_key=api_key)
                    prompt = (
                        "Analiza el texto. Sepáralo en ideas independientes. "
                        "Determina para cada una: 'titulo', 'categoria' (Música, "
                        "Universidad, Compras, Random) y 'contenido'. "
                        "Devuelve ÚNICAMENTE un JSON válido (lista de objetos). "
                        f"Texto: '{raw_thought}'"
                    )
                    resp = client.models.generate_content(
                        model='gemini-1.5-flash', 
                        contents=prompt
                    )
                    
                    tr = resp.text.strip()
                    tr = tr.replace("```json", "").replace("```", "").strip()
                    
                    new_thoughts = json.loads(tr)
                    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    for item in new_thoughts:
                        thread_obj = {
                            "id": datetime.datetime.now().strftime("%Y%m%d%H%M%S%f"),
                            "titulo": item.get("titulo", "Idea sin título"),
                            "categoria": item.get("categoria", "Random"),
                            "creado": ts,
                            "mensajes": [{
                                "autor": "usuario", 
                                "texto": item.get("contenido", "")
                            }]
                        }
                        st.session_state.thoughts.append(thread_obj)
                    
                    save_json(THOUGHTS_FILE, st.session_state.thoughts)
                    st.success("¡Hilos creados y guardados!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error procesando idea: {e}")

    st.divider()
    if st.session_state.thoughts:
        opciones_hilos = list({t["id"]: f"[{t['categoria']}] {t['titulo']}" for t in st.session_state.thoughts}.keys())
        
        def format_hilo(x):
            for t in st.session_state.thoughts:
                if t["id"] == x:
                    return f"[{t['categoria']}] {t['titulo']}"
            return x
            
        selected_id = st.selectbox("Tus hilos guardados:", options=opciones_hilos, format_func=format_hilo)
        current_thread = next((t for t in st.session_state.thoughts if t["id"] == selected_id), None)
        
        if current_thread:
            st.markdown(f"### 💬 {current_thread['titulo']}")
            for msg in current_thread["mensajes"]:
                with st.chat_message("user" if msg["autor"]=="usuario" else "assistant"):
                    st.write(msg["texto"])
            
            with st.form(f"chat_form_{selected_id}", clear_on_submit=True):
                reply = st.text_input("Continuar escribiendo en este hilo...")
                if st.form_submit_button("Agregar Nota") and reply:
                    current_thread["mensajes"].append({"autor": "usuario", "texto": reply})
                    save_json(THOUGHTS_FILE, st.session_state.thoughts)
                    st.rerun()
            
            if st.button("🗑️ Eliminar este hilo por completo"):
                st.session_state.thoughts = [t for t in st.session_state.thoughts if t["id"] != selected_id]
                save_json(THOUGHTS_FILE, st.session_state.thoughts)
                st.rerun()
    else:
        st.info("Aún no tienes notas guardadas en tu Segundo Cerebro.")
