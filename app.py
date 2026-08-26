import streamlit as st
import pandas as pd
import json
import datetime
import os
from google import genai
import plotly.express as px
import requests
import gspread
from google.oauth2.service_account import Credentials

# ==============================================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTÉTICA
# ==============================================================
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

# ==============================================================
# 2. CONEXIÓN A GOOGLE SHEETS
# ==============================================================
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def get_google_client():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
    client = gspread.authorize(creds)
    url = st.secrets["URL_EXCEL"]
    return client.open_by_url(url)

def get_or_create_worksheet(sh, title, headers):
    try:
        return sh.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=title, rows="1000", cols=str(len(headers)))
        ws.append_row(headers)
        return ws

def load_config(key, default):
    try:
        sh = get_google_client()
        ws = get_or_create_worksheet(sh, "Configuraciones", ["Clave", "Datos_JSON"])
        cell = ws.find(key, in_column=1)
        val = ws.cell(cell.row, 2).value
        return json.loads(val)
    except Exception:
        return default

def save_config(key, data):
    try:
        sh = get_google_client()
        ws = get_or_create_worksheet(sh, "Configuraciones", ["Clave", "Datos_JSON"])
        data_str = json.dumps(data, ensure_ascii=False)
        try:
            cell = ws.find(key, in_column=1)
            ws.update_cell(cell.row, 2, data_str)
        except Exception:
            ws.append_row([key, data_str])
    except Exception as e:
        st.error(f"Error guardando configuración: {e}")

def load_table(ws_title, headers, json_cols=[]):
    try:
        sh = get_google_client()
        ws = get_or_create_worksheet(sh, ws_title, headers)
        records = ws.get_all_records()
        for r in records:
            for col in json_cols:
                if col in r and isinstance(r[col], str):
                    try:
                        r[col] = json.loads(r[col])
                    except:
                        r[col] = []
        return records
    except Exception as e:
        return []

def save_table(ws_title, headers, data_list, json_cols=[]):
    try:
        sh = get_google_client()
        ws = get_or_create_worksheet(sh, ws_title, headers)
        ws.clear()
        
        data_matrix = [headers]
        for row in data_list:
            row_data = []
            for h in headers:
                val = row.get(h, "")
                if h in json_cols:
                    val = json.dumps(val, ensure_ascii=False)
                row_data.append(val)
            data_matrix.append(row_data)
            
        try:
            ws.update(values=data_matrix, range_name="A1")
        except TypeError:
            ws.update(data_matrix)
            
    except Exception as e:
        st.error(f"Error guardando tabla {ws_title}: {e}")

# ==============================================================
# FUNCIONES AUXILIARES Y DE ESTADO
# ==============================================================
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
    for key in ["categories", "transactions", "savings", "thoughts", "pendings", "returns", "last_added", "recomendacion_ia"]:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.usuario_autenticado = usuario
    st.rerun()

def cerrar_sesion():
    st.session_state.usuario_autenticado = None
    for key in ["categories", "transactions", "savings", "thoughts", "pendings", "returns", "last_added", "recomendacion_ia"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

passwords_guardadas = load_config("pins_security", {})

if "usuario_autenticado" not in st.session_state:
    st.session_state.usuario_autenticado = None

if "login_user_selected" not in st.session_state:
    st.session_state.login_user_selected = None

# ==============================================================
# PANTALLA DE LOGIN RENOVADA
# ==============================================================
if st.session_state.usuario_autenticado is None:
    st.markdown("<h1 style='text-align: center; font-size: 3.5rem;'>¡Hola! 👋</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: gray;'>Finanzas & Cerebro</h3>", unsafe_allow_html=True)
    st.divider()
    
    # 1. Pantalla de Selección de Íconos
    if st.session_state.login_user_selected is None:
        st.markdown("<h4 style='text-align: center;'>¿Quién está entrando?</h4><br>", unsafe_allow_html=True)
        
        # Hacemos 4 columnas para centrar los dos botones grandes en el medio
        c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
        with c2:
            if st.button("🍊 Fermín", use_container_width=True):
                st.session_state.login_user_selected = "Fermín"
                st.rerun()
        with c3:
            if st.button("🌸 Irina", use_container_width=True):
                st.session_state.login_user_selected = "Irina"
                st.rerun()
                
    # 2. Pantalla de PIN (después de elegir usuario)
    else:
        usuario_seleccionado = st.session_state.login_user_selected
        icono_login = "🍊" if usuario_seleccionado == "Fermín" else "🌸"
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(f"<h3 style='text-align: center;'>{icono_login} Perfil de {usuario_seleccionado}</h3>", unsafe_allow_html=True)
            
            if usuario_seleccionado in passwords_guardadas:
                pin_ingresado = st.text_input("Ingresa tu PIN numérico", type="password")
                
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("⬅️ Volver", use_container_width=True):
                        st.session_state.login_user_selected = None
                        st.rerun()
                with b2:
                    if st.button("Entrar", type="primary", use_container_width=True):
                        if pin_ingresado == passwords_guardadas[usuario_seleccionado]:
                            st.session_state.login_user_selected = None
                            iniciar_sesion(usuario_seleccionado)
                        else:
                            st.error("PIN incorrecto. Inténtalo de nuevo.")
            else:
                st.info("Crea un PIN numérico para proteger tus datos.")
                nuevo_pin = st.text_input("Ingresa un nuevo PIN", type="password")
                confirmar_pin = st.text_input("Confirma tu PIN", type="password")
                
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("⬅️ Volver", use_container_width=True):
                        st.session_state.login_user_selected = None
                        st.rerun()
                with b2:
                    if st.button("Crear y Entrar", type="primary", use_container_width=True):
                        if nuevo_pin and nuevo_pin.isdigit():
                            if nuevo_pin == confirmar_pin:
                                passwords_guardadas[usuario_seleccionado] = nuevo_pin
                                save_config("pins_security", passwords_guardadas)
                                st.success("¡PIN creado con éxito!")
                                st.session_state.login_user_selected = None
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
sufijo = "Fermin" if usuario_actual == "Fermín" else "Irina"

# Día de cierre según el usuario (Fermín = 28, Irina = 22)
DIA_CIERRE = 28 if usuario_actual == "Fermín" else 22

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

# CARGA DE TABLAS
if "categories" not in st.session_state:
    st.session_state.categories = load_config(f"categorias_{sufijo}", obtener_categorias_iniciales(usuario_actual))
if "transactions" not in st.session_state:
    st.session_state.transactions = load_table(f"Gastos_{sufijo}", ["timestamp", "tipo", "monto", "descripcion", "categoria"])
if "savings" not in st.session_state:
    st.session_state.savings = load_table(f"Ahorros_{sufijo}", ["fecha", "pesos_ahorrados", "cotizacion_blue", "dolares"])
if "pendings" not in st.session_state:
    st.session_state.pendings = load_table(f"Pendientes_{sufijo}", ["id", "concepto", "monto", "fecha", "estado"])
if "returns" not in st.session_state:
    st.session_state.returns = load_table(f"Devoluciones_{sufijo}", ["id", "concepto", "monto", "fecha", "estado"])
if "thoughts" not in st.session_state:
    st.session_state.thoughts = load_table(f"Cerebro_{sufijo}", ["id", "titulo", "categoria", "creado", "mensajes"], json_cols=["mensajes"])
if "recomendacion_ia" not in st.session_state:
    st.session_state.recomendacion_ia = ""

st.sidebar.header("⚙️ Configuración")
api_key = st.sidebar.text_input("Gemini API Key", type="password", value=os.environ.get("GEMINI_API_KEY", ""))
st.sidebar.divider()
if st.sidebar.button("🚪 Cerrar Sesión", type="primary"):
    cerrar_sesion()

dolar_blue_venta = get_dolar_blue()

# CÁLCULO DE CICLOS PERSONALIZADOS
now = datetime.datetime.now()
if now.day >= DIA_CIERRE:
    current_cycle_start = datetime.datetime(now.year, now.month, DIA_CIERRE)
    if now.month == 12:
        next_cycle_start = datetime.datetime(now.year + 1, 1, DIA_CIERRE)
    else:
        next_cycle_start = datetime.datetime(now.year, now.month + 1, DIA_CIERRE)
else:
    if now.month == 1:
        current_cycle_start = datetime.datetime(now.year - 1, 12, DIA_CIERRE)
    else:
        current_cycle_start = datetime.datetime(now.year, now.month - 1, DIA_CIERRE)
    next_cycle_start = datetime.datetime(now.year, now.month, DIA_CIERRE)

# FORMATEO DE FECHA EN ESPAÑOL
dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
meses_anio = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
fecha_linda = f"{dias_semana[now.weekday()]} {now.day} de {meses_anio[now.month - 1]}"

icono = "🍊" if usuario_actual == "Fermín" else "🌸"

# Saludo inicial y fecha
st.markdown(f"<h1>¡Hola, {usuario_actual}! {icono}</h1>", unsafe_allow_html=True)
st.markdown(f"### 📅 {fecha_linda}")

dias_faltantes = (next_cycle_start - datetime.datetime.now()).days
st.caption(f"Faltan **{max(0, dias_faltantes)} días** para el final de tu ciclo (Cierre día {DIA_CIERRE}).")

# CARTEL DE COBRO
is_cierre_day = (now.day == DIA_CIERRE)
if is_cierre_day:
    st.warning(f"💰 **¡Es día de cierre ({DIA_CIERRE})!** Registra tu sueldo y decide qué hacer con el saldo sobrante en la pestaña 'Ciclos'.")

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

# CÁLCULO DE SALDO NETO
total_pendientes_activos = sum([p["monto"] for p in st.session_state.pendings if p.get("estado", "pendiente") == "pendiente"])
total_devoluciones_activas = sum([r["monto"] for r in st.session_state.returns if r.get("estado", "pendiente") == "pendiente"])
saldo_neto = saldo_actual - total_pendientes_activos + total_devoluciones_activas

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
                    Saldo actual: ${saldo_actual}. Días hasta cobrar (cierre {DIA_CIERRE}): {dias_faltantes}.
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
                        model='gemini-3.6-flash', 
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
                    
                    save_table(f"Gastos_{sufijo}", ["timestamp", "tipo", "monto", "descripcion", "categoria"], st.session_state.transactions) 
                    
                    st.session_state["last_added"] = new_txs
                    st.session_state.recomendacion_ia = recomendacion
                    st.rerun()
                except Exception as e:
                    st.error(f"Error de conexión con IA: {e}")

    st.divider()
    
    # SECCIÓN DE GESTIÓN DE PAGOS Y DEVOLUCIONES PENDIENTES
    col_izq, col_der = st.columns(2)
    
    with col_izq:
        st.subheader("📌 Pagos Pendientes")
        with st.expander("➕ Agregar pago"):
            with st.form("pending_form", clear_on_submit=True):
                p_concepto = st.text_input("Concepto (Ej: Sala de ensayo)")
                p_monto = st.number_input("Monto ($)", min_value=0.0, step=1000.0, key="m_p")
                p_fecha = st.date_input("Fecha límite", value=datetime.date.today(), key="f_p")
                
                if st.form_submit_button("Guardar") and p_concepto:
                    st.session_state.pendings.append({
                        "id": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
                        "concepto": p_concepto,
                        "monto": p_monto,
                        "fecha": str(p_fecha),
                        "estado": "pendiente"
                    })
                    save_table(f"Pendientes_{sufijo}", ["id", "concepto", "monto", "fecha", "estado"], st.session_state.pendings)
                    st.success("¡Guardado!")
                    st.rerun()

        pendientes_activos = [p for p in st.session_state.pendings if p.get("estado", "pendiente") == "pendiente"]
        if pendientes_activos:
            for row in pendientes_activos:
                st.markdown(f"**{row['concepto']}** - \${row['monto']:,.0f} <br><small>{row['fecha']}</small>", unsafe_allow_html=True)
                if st.button("✅ Pagado", key=f"pagar_{row['id']}"):
                    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state.transactions.append({
                        "timestamp": ts,
                        "tipo": "gasto",
                        "monto": row["monto"],
                        "descripcion": f"Pago pendiente: {row['concepto']}",
                        "categoria": "Otros"
                    })
                    save_table(f"Gastos_{sufijo}", ["timestamp", "tipo", "monto", "descripcion", "categoria"], st.session_state.transactions)
                    
                    for p in st.session_state.pendings:
                        if p["id"] == row["id"]:
                            p["estado"] = "pagado"
                    save_table(f"Pendientes_{sufijo}", ["id", "concepto", "monto", "fecha", "estado"], st.session_state.pendings)
                    st.rerun()
                st.divider()
        else:
            st.info("Sin pagos pendientes.")

    with col_der:
        st.subheader("📥 Devoluciones")
        with st.expander("➕ Agregar devolución"):
            with st.form("return_form", clear_on_submit=True):
                r_concepto = st.text_input("Concepto (Ej: Amigo debe entrada)", key="c_r")
                r_monto = st.number_input("Monto ($)", min_value=0.0, step=1000.0, key="m_r")
                r_fecha = st.date_input("Fecha estimada", value=datetime.date.today(), key="f_r")
                
                if st.form_submit_button("Guardar") and r_concepto:
                    st.session_state.returns.append({
                        "id": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
                        "concepto": r_concepto,
                        "monto": r_monto,
                        "fecha": str(r_fecha),
                        "estado": "pendiente"
                    })
                    save_table(f"Devoluciones_{sufijo}", ["id", "concepto", "monto", "fecha", "estado"], st.session_state.returns)
                    st.success("¡Guardado!")
                    st.rerun()

        devoluciones_activas = [r for r in st.session_state.returns if r.get("estado", "pendiente") == "pendiente"]
        if devoluciones_activas:
            for row in devoluciones_activas:
                st.markdown(f"**{row['concepto']}** - \${row['monto']:,.0f} <br><small>{row['fecha']}</small>", unsafe_allow_html=True)
                if st.button("📥 Devuelto", key=f"devolver_{row['id']}"):
                    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state.transactions.append({
                        "timestamp": ts,
                        "tipo": "ingreso",
                        "monto": row["monto"],
                        "descripcion": f"Devolución recibida: {row['concepto']}",
                        "categoria": "Devoluciones"
                    })
                    save_table(f"Gastos_{sufijo}", ["timestamp", "tipo", "monto", "descripcion", "categoria"], st.session_state.transactions)
                    
                    for r in st.session_state.returns:
                        if r["id"] == row["id"]:
                            r["estado"] = "devuelto"
                    save_table(f"Devoluciones_{sufijo}", ["id", "concepto", "monto", "fecha", "estado"], st.session_state.returns)
                    st.rerun()
                st.divider()
        else:
            st.info("Sin devoluciones pendientes.")

    st.subheader("📊 Resumen Financiero")
    col1, col2, col3 = st.columns(3)
    col1.metric("Saldo Real", f"${saldo_actual:,.0f}")
    col2.metric("Saldo Neto (Ajustado)", f"${saldo_neto:,.0f}")
    col3.metric("Gastos del Ciclo", f"${total_gastos:,.0f}")

# ==============================================================
# PESTAÑA 2: BALANCE
# ==============================================================
with tab2:
    st.subheader("📊 Gastos por Categoría")
    if not df_cycle.empty:
        df_g = df_cycle[df_cycle["tipo"] == "gasto"]
        if not df_g.empty:
            df_grouped = df_g.groupby("categoria")["monto"].sum().reset_index()
            df_grouped = df_grouped.sort_values(by="monto", ascending=False)
            
            fig = px.pie(
                df_grouped, values="monto", names="categoria", hole=0.4, 
                color_discrete_sequence=px.colors.qualitative.Set1
            )
            fig.update_traces(textinfo='label+value', texttemplate='%{label}: $%{value:,.0f}')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay gastos registrados en este ciclo mensual.")
    else:
        st.info("No hay registros en este ciclo.")

# ==============================================================
# PESTAÑA 3: HISTORIAL 
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
                save_table(f"Gastos_{sufijo}", ["timestamp", "tipo", "monto", "descripcion", "categoria"], st.session_state.transactions)
                st.success("Movimiento borrado exitosamente.")
                st.session_state.recomendacion_ia = ""
                st.rerun()
    else:
        st.write("Sin movimientos.")

# ==============================================================
# PESTAÑA 4: CICLOS Y AHORROS
# ==============================================================
with tab4:
    st.subheader(f"📅 Cierre de Mes (Día {DIA_CIERRE})")
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
                save_table(f"Ahorros_{sufijo}", ["fecha", "pesos_ahorrados", "cotizacion_blue", "dolares"], st.session_state.savings)
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
            save_config(f"categorias_{sufijo}", st.session_state.categories)
            st.success("Categoría agregada correctamente.")
            st.rerun()
            
    for cat, keys in st.session_state.categories.items():
        st.markdown(f"- **{cat}**: {', '.join(keys)}")

# ==============================================================
# PESTAÑA 6: SEGUNDO CEREBRO 
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
                        model='gemini-3.6-flash', 
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
                    
                    save_table(f"Cerebro_{sufijo}", ["id", "titulo", "categoria", "creado", "mensajes"], st.session_state.thoughts, json_cols=["mensajes"])
                    st.success("¡Hilos creados y guardados!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error procesando idea: {e}")

    st.divider()
    
    if st.session_state.thoughts:
        hilos_ordenados = sorted(st.session_state.thoughts, key=lambda x: x["id"], reverse=True)
        
        for t in hilos_ordenados:
            with st.expander(f"📌 [{t['categoria']}] {t['titulo']} ({t['creado']})"):
                
                for msg in t["mensajes"]:
                    with st.chat_message("user" if msg["autor"]=="usuario" else "assistant"):
                        st.write(msg["texto"])
                
                with st.form(f"chat_form_{t['id']}", clear_on_submit=True):
                    reply = st.text_input("Agregar nota a este hilo...", key=f"input_{t['id']}")
                    if st.form_submit_button("Enviar"):
                        if reply:
                            for orig_t in st.session_state.thoughts:
                                if orig_t["id"] == t["id"]:
                                    orig_t["mensajes"].append({"autor": "usuario", "texto": reply})
                            save_table(f"Cerebro_{sufijo}", ["id", "titulo", "categoria", "creado", "mensajes"], st.session_state.thoughts, json_cols=["mensajes"])
                            st.rerun()
                
                if st.button("🗑️ Eliminar hilo completo", key=f"del_{t['id']}"):
                    st.session_state.thoughts = [orig_t for orig_t in st.session_state.thoughts if orig_t["id"] != t["id"]]
                    save_table(f"Cerebro_{sufijo}", ["id", "titulo", "categoria", "creado", "mensajes"], st.session_state.thoughts, json_cols=["mensajes"])
                    st.rerun()
    else:
        st.info("Aún no tienes notas guardadas en tu Segundo Cerebro.")
