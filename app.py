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
    .stChatMessage {
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
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
        pass

def load_table(ws_title, headers, json_cols=[]):
    try:
        sh = get_google_client()
        ws = get_or_create_worksheet(sh, ws_title, headers)
        records = ws.get_all_records()
        for r in records:
            for col in json_cols:
                if col in r and isinstance(r[col], str):
                    try: r[col] = json.loads(r[col])
                    except: r[col] = []
        return records
    except Exception:
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
                if h in json_cols: val = json.dumps(val, ensure_ascii=False)
                row_data.append(val)
            data_matrix.append(row_data)
        try: ws.update(values=data_matrix, range_name="A1")
        except TypeError: ws.update(data_matrix)
    except Exception as e:
        st.error(f"Error guardando tabla {ws_title}: {e}")

def get_dolar_blue():
    try:
        res = requests.get("https://dolarapi.com/v1/dolares/blue", timeout=3)
        if res.status_code == 200: return res.json().get("venta", 1300)
    except: pass
    return 1300

def iniciar_sesion(usuario):
    for key in list(st.session_state.keys()):
        if key not in ["login_user_selected"]:
            del st.session_state[key]
    st.session_state.usuario_autenticado = usuario
    st.rerun()

def cerrar_sesion():
    st.session_state.usuario_autenticado = None
    st.session_state.login_user_selected = None
    st.rerun()

# ==============================================================
# 3. PANTALLA DE LOGIN DIRECTO
# ==============================================================
if "usuario_autenticado" not in st.session_state:
    st.session_state.usuario_autenticado = None
if "login_user_selected" not in st.session_state:
    st.session_state.login_user_selected = None

if st.session_state.usuario_autenticado is None:
    st.markdown("<h1 style='text-align: center; font-size: 3.5rem;'>¡Hola! 👋</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: gray;'>Finanzas & Cerebro</h3>", unsafe_allow_html=True)
    st.divider()
    
    if st.session_state.login_user_selected is None:
        st.markdown("<h4 style='text-align: center;'>¿Quién está entrando?</h4><br>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
        with c2:
            if st.button("🍊 Fermín", use_container_width=True):
                st.session_state.login_user_selected = "Fermín"
                st.rerun()
        with c3:
            if st.button("🌸 Irina", use_container_width=True):
                st.session_state.login_user_selected = "Irina"
                st.rerun()
    else:
        usuario_intento = st.session_state.login_user_selected
        sufijo_intento = "Fermin" if usuario_intento == "Fermín" else "Irina"
        ajustes_intento = load_config(f"settings_{sufijo_intento}", {"usar_pin": False, "pin": ""})
        
        if ajustes_intento.get("usar_pin", False) and ajustes_intento.get("pin", "") != "":
            st.markdown(f"<h4 style='text-align: center;'>🔒 Ingresa el PIN de {usuario_intento}</h4>", unsafe_allow_html=True)
            pin_ingresado = st.text_input("PIN", type="password")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("⬅️ Volver", use_container_width=True):
                    st.session_state.login_user_selected = None
                    st.rerun()
            with col_b:
                if st.button("Entrar", type="primary", use_container_width=True):
                    if pin_ingresado == ajustes_intento["pin"]:
                        iniciar_sesion(usuario_intento)
                    else:
                        st.error("PIN Incorrecto.")
        else:
            iniciar_sesion(usuario_intento)
    st.stop()

# ==============================================================
# 4. CARGA DE DATOS DEL USUARIO
# ==============================================================
usuario = st.session_state.usuario_autenticado
sufijo = "Fermin" if usuario == "Fermín" else "Irina"
otro_sufijo = "Irina" if usuario == "Fermín" else "Fermin"

user_settings = load_config(f"settings_{sufijo}", {
    "dia_cierre": 28 if usuario == "Fermín" else 22,
    "divisa": "ARS",
    "usar_pin": False,
    "pin": ""
})
DIA_CIERRE = user_settings.get("dia_cierre", 28)
DIVISA = user_settings.get("divisa", "ARS")
simbolo_moneda = "$" if DIVISA == "ARS" else f"{DIVISA} "
simbolo_html = "&#36;" if DIVISA == "ARS" else f"{DIVISA} "

dolar_blue_venta = get_dolar_blue()

def obtener_categorias_iniciales(usr):
    base = {
        "Fútbol y Cancha": ["futbol", "cancha", "entrada", "estadio"],
        "Paseos y Salidas": ["paseo", "salidas", "cine"],
        "Supermercado": ["supermercado", "super", "almacén", "verdulería"],
        "Comida y Delivery": ["comida", "hamburguesa", "pizza", "delivery"],
        "Transporte": ["sube", "colectivo", "tren", "uber", "taxi", "nafta"],
        "Otros": ["varios"]
    }
    if usr == "Fermín": base["Irina"] = ["irina", "novia", "regalos"]
    else: base["Fermín"] = ["fermin", "novio", "regalos"]
    return base

if "transactions" not in st.session_state:
    st.session_state.categories = load_config(f"categorias_{sufijo}", obtener_categorias_iniciales(usuario))
    st.session_state.transactions = load_table(f"Gastos_{sufijo}", ["timestamp", "tipo", "monto", "descripcion", "categoria"])
    st.session_state.pendings = load_table(f"Pendientes_{sufijo}", ["id", "concepto", "monto", "fecha", "estado"])
    st.session_state.returns = load_table(f"Devoluciones_{sufijo}", ["id", "concepto", "monto", "fecha", "estado"])
    st.session_state.thoughts = load_table(f"Cerebro_{sufijo}", ["id", "titulo", "categoria", "creado", "mensajes"], json_cols=["mensajes"])
    st.session_state.wishlist = load_table(f"Wishlist_{sufijo}", ["id", "item", "precio_ars", "precio_usd", "notas"])
    
    st.session_state.bolsillos = load_table(f"Bolsillos_{sufijo}", ["id", "nombre", "ubicacion", "monto", "wishlist_id"])
    if not st.session_state.bolsillos:
        st.session_state.bolsillos = [{"id": "b_default", "nombre": "Ahorro General", "ubicacion": "Cuenta DNI", "monto": 0.0, "wishlist_id": ""}]
        save_table(f"Bolsillos_{sufijo}", ["id", "nombre", "ubicacion", "monto", "wishlist_id"], st.session_state.bolsillos)

    st.session_state.recomendacion_ia = ""

api_key = os.environ.get("GEMINI_API_KEY", "")

# ==============================================================
# CÁLCULO DE CICLOS Y SALDOS
# ==============================================================
now = datetime.datetime.now()
if now.day >= DIA_CIERRE:
    current_cycle_start = datetime.datetime(now.year, now.month, DIA_CIERRE)
    next_cycle_start = datetime.datetime(now.year + 1 if now.month == 12 else now.year, 1 if now.month == 12 else now.month + 1, DIA_CIERRE)
else:
    current_cycle_start = datetime.datetime(now.year - 1 if now.month == 1 else now.year, 12 if now.month == 1 else now.month - 1, DIA_CIERRE)
    next_cycle_start = datetime.datetime(now.year, now.month, DIA_CIERRE)

df_tx = pd.DataFrame(st.session_state.transactions)
if not df_tx.empty:
    df_tx["timestamp_dt"] = pd.to_datetime(df_tx["timestamp"])
    df_cycle = df_tx[(df_tx["timestamp_dt"] >= current_cycle_start) & (df_tx["timestamp_dt"] < next_cycle_start)]
else:
    df_cycle = pd.DataFrame(columns=["tipo", "monto", "descripcion", "categoria", "timestamp"])

total_ingresos = df_cycle[df_cycle["tipo"] == "ingreso"]["monto"].sum() if not df_cycle.empty else 0
total_gastos = df_cycle[df_cycle["tipo"] == "gasto"]["monto"].sum() if not df_cycle.empty else 0
saldo_actual = total_ingresos - total_gastos

tot_pendientes = sum([p["monto"] for p in st.session_state.pendings if p.get("estado") == "pendiente"])
tot_devoluciones = sum([r["monto"] for r in st.session_state.returns if r.get("estado") == "pendiente"])
saldo_neto = saldo_actual - tot_pendientes + tot_devoluciones

# ==============================================================
# ENCABEZADO PRINCIPAL
# ==============================================================
dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
meses_anio = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

st.markdown(f"<h1>¡Hola, {usuario}! {'🍊' if usuario == 'Fermín' else '🌸'}</h1>", unsafe_allow_html=True)
st.markdown(f"### 📅 {dias_semana[now.weekday()]} {now.day} de {meses_anio[now.month - 1]}")
dias_faltantes = (next_cycle_start - now).days
st.caption(f"Faltan **{max(0, dias_faltantes)} días** para el final de tu ciclo (Día {DIA_CIERRE}).")

if now.day == DIA_CIERRE:
    st.warning(f"💰 **¡Es día de cierre!** Revisa tus saldos y mueve tu sobrante a los bolsillos en la pestaña 'Ciclos'.")

tab_registro, tab_cerebro, tab_wishlist, tab_balance, tab_historial, tab_ciclos, tab_categorias, tab_ajustes = st.tabs([
    "💬 Registro", "🧠 Cerebro", "🎁 Wishlist", "📊 Balance", "📜 Historial", "📅 Ciclos", "🏷️ Categorías", "⚙️ Ajustes"
])

def formatear_tarjeta_movimiento(tx):
    color = "#10B981" if tx["tipo"] == "ingreso" else "#EF4444"
    signo = "+" if tx["tipo"] == "ingreso" else "-"
    monto_str = f"{signo} {simbolo_html}{tx['monto']:,.0f}".replace(",", ".")
    cat = str(tx.get("categoria", "Otros")).capitalize()
    desc = str(tx.get("descripcion", "")).capitalize()
    fecha_formateada = tx['timestamp'][:16].replace("-", "/")
    
    st.markdown(f"""
    <div style="padding: 12px; border-radius: 10px; border: 1px solid rgba(217, 119, 6, 0.2); margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; background-color: rgba(217, 119, 6, 0.02);">
        <div style="overflow: hidden; padding-right: 10px;">
            <strong style="font-size: 16px; color: #E0E0E0;">{desc}</strong><br>
            <span style="color: #A0A0A0; font-size: 13px;">{cat} • {fecha_formateada}</span>
        </div>
        <div style="color: {color}; font-weight: bold; font-size: 17px; white-space: nowrap;">
            {monto_str}
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==============================================================
# PESTAÑA 1: REGISTRO (ABRE POR DEFECTO)
# ==============================================================
with tab_registro:
    st.markdown("### 🎙️ Nuevo Registro")
    user_input = st.text_area("Registro", placeholder="Ej: Supermercado 20000, se pagó mitad y mitad...", height=100, label_visibility="collapsed")
    
    col1, col2 = st.columns(2)
    mic_btn = col1.button("🎙️ Usar Micrófono", use_container_width=True)
    procesar = col2.button("✨ Procesar", type="primary", use_container_width=True)

    if st.session_state.recomendacion_ia: st.warning(f"💡 {st.session_state.recomendacion_ia}")

    if procesar and user_input.strip():
        with st.spinner("La IA está procesando..."):
            try:
                client = genai.Client(api_key=api_key)
                cat_list = list(st.session_state.categories.keys())
                prompt = f"""
                Eres un asistente financiero de {usuario}. Divisa actual: {DIVISA}. Categorías: {cat_list}.
                Analiza: "{user_input}"
                SI EL USUARIO DICE EXPLÍCITAMENTE "mitad y mitad" O "mitad cada uno", agrega `"split": true` al JSON.
                Devuelve ESTRICTAMENTE este JSON:
                {{
                    "movimientos": [
                        {{"tipo": "gasto" o "ingreso", "monto": numero, "descripcion": "detalle", "categoria": "CATEGORIA", "split": true o false}}
                    ]
                }}
                """
                response = client.models.generate_content(model='gemini-3.6-flash', contents=prompt)
                text_res = response.text.replace("```json", "").replace("```", "").strip()
                data = json.loads(text_res)
                
                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for tx in data.get("movimientos", []):
                    is_split = tx.get("split", False)
                    final_monto = tx["monto"] / 2 if is_split else tx["monto"]
                    
                    tx_propia = {"timestamp": ts, "tipo": tx["tipo"], "monto": final_monto, "descripcion": tx["descripcion"] + (" (Mitad)" if is_split else ""), "categoria": tx.get("categoria", "Otros")}
                    st.session_state.transactions.append(tx_propia)
                    save_table(f"Gastos_{sufijo}", ["timestamp", "tipo", "monto", "descripcion", "categoria"], st.session_state.transactions)
                    
                    if is_split:
                        tabla_otro = load_table(f"Gastos_{otro_sufijo}", ["timestamp", "tipo", "monto", "descripcion", "categoria"])
                        tabla_otro.append(tx_propia)
                        save_table(f"Gastos_{otro_sufijo}", ["timestamp", "tipo", "monto", "descripcion", "categoria"], tabla_otro)
                        st.success(f"¡Mitad anotada para vos y la otra mitad enviada al historial de {otro_sufijo}!")

                st.rerun()
            except Exception as e:
                st.error(f"Error IA: {e}")

    st.divider()

    st.subheader("⏱️ Última Actividad")
    if st.session_state.transactions:
        tx_ordenadas = sorted(st.session_state.transactions, key=lambda x: x['timestamp'], reverse=True)
        formatear_tarjeta_movimiento(tx_ordenadas[0])
        
        if len(tx_ordenadas) > 1:
            with st.expander("Ver otros recientes..."):
                for tx in tx_ordenadas[1:5]:
                    formatear_tarjeta_movimiento(tx)
    else:
        st.info("Aún no tienes movimientos.")
    
    st.divider()
    
    col_izq, col_der = st.columns(2)
    with col_izq:
        st.subheader("📌 Pendientes")
        with st.expander("➕ Agregar pago"):
            with st.form("pending_form", clear_on_submit=True):
                p_concepto = st.text_input("Concepto")
                p_monto = st.number_input("Monto", min_value=0.0)
                if st.form_submit_button("Guardar") and p_concepto:
                    st.session_state.pendings.append({"id": datetime.datetime.now().strftime("%Y%m%d%H%M%S"), "concepto": p_concepto, "monto": p_monto, "fecha": str(datetime.date.today()), "estado": "pendiente"})
                    save_table(f"Pendientes_{sufijo}", ["id", "concepto", "monto", "fecha", "estado"], st.session_state.pendings)
                    st.rerun()

        for row in [p for p in st.session_state.pendings if p.get("estado") == "pendiente"]:
            st.markdown(f"**{row['concepto']}**<br><span style='color:#EF4444;'>- {simbolo_html}{row['monto']:,.0f}</span>".replace(",", "."), unsafe_allow_html=True)
            if st.button("✅ Pagado", key=f"p_{row['id']}"):
                st.session_state.transactions.append({"timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "tipo": "gasto", "monto": row["monto"], "descripcion": f"Pago: {row['concepto']}", "categoria": "Otros"})
                save_table(f"Gastos_{sufijo}", ["timestamp", "tipo", "monto", "descripcion", "categoria"], st.session_state.transactions)
                row["estado"] = "pagado"
                save_table(f"Pendientes_{sufijo}", ["id", "concepto", "monto", "fecha", "estado"], st.session_state.pendings)
                st.rerun()
            st.divider()

    with col_der:
        st.subheader("📥 Devoluciones")
        with st.expander("➕ Agregar cobro"):
            with st.form("return_form", clear_on_submit=True):
                r_concepto = st.text_input("Concepto")
                r_monto = st.number_input("Monto", min_value=0.0)
                if st.form_submit_button("Guardar") and r_concepto:
                    st.session_state.returns.append({"id": datetime.datetime.now().strftime("%Y%m%d%H%M%S"), "concepto": r_concepto, "monto": r_monto, "fecha": str(datetime.date.today()), "estado": "pendiente"})
                    save_table(f"Devoluciones_{sufijo}", ["id", "concepto", "monto", "fecha", "estado"], st.session_state.returns)
                    st.rerun()

        for row in [r for r in st.session_state.returns if r.get("estado") == "pendiente"]:
            st.markdown(f"**{row['concepto']}**<br><span style='color:#10B981;'>+ {simbolo_html}{row['monto']:,.0f}</span>".replace(",", "."), unsafe_allow_html=True)
            if st.button("📥 Devuelto", key=f"r_{row['id']}"):
                st.session_state.transactions.append({"timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "tipo": "ingreso", "monto": row["monto"], "descripcion": f"Devolución: {row['concepto']}", "categoria": "Devoluciones"})
                save_table(f"Gastos_{sufijo}", ["timestamp", "tipo", "monto", "descripcion", "categoria"], st.session_state.transactions)
                row["estado"] = "devuelto"
                save_table(f"Devoluciones_{sufijo}", ["id", "concepto", "monto", "fecha", "estado"], st.session_state.returns)
                st.rerun()
            st.divider()
    
    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.metric("Saldo Real", f"{simbolo_moneda}{saldo_actual:,.0f}".replace(",", "."))
    col2.metric("Saldo Neto", f"{simbolo_moneda}{saldo_neto:,.0f}".replace(",", "."))
    col3.metric("Gastos Ciclo", f"{simbolo_moneda}{total_gastos:,.0f}".replace(",", "."))

# ==============================================================
# PESTAÑA 2: SEGUNDO CEREBRO
# ==============================================================
with tab_cerebro:
    st.markdown("<h2 style='text-align:center;'>🧠 Segundo Cerebro</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Tus ideas libres. Escribe una nota o escribe <b>'Ey, Cerebro'</b> para invocar a la IA.</p>", unsafe_allow_html=True)
    
    raw_thought = st.text_area("Ideas", placeholder="Ej: Pensé en una receta... o 'Ey Cerebro, hazme una lista de compras'", label_visibility="collapsed")
    if st.button("✨ Iniciar Bloc de Notas", type="primary", use_container_width=True):
        if not api_key:
            st.error("Falta tu API Key de Gemini en los Secretos.")
        elif not raw_thought.strip():
            st.warning("Escribe algo para poder armar el bloc.")
        else:
            with st.spinner("Procesando con IA..."):
                try:
                    client = genai.Client(api_key=api_key)
                    if "ey, cerebro" in raw_thought.lower() or "ey cerebro" in raw_thought.lower():
                        prompt_ia = f"Eres 'Cerebro', la IA personal de {usuario}. Responde a la siguiente consulta del usuario de forma útil, concisa y amigable: {raw_thought}"
                        res_ia = client.models.generate_content(model='gemini-3.6-flash', contents=prompt_ia)
                        respuesta_texto = res_ia.text.strip()
                        
                        prompt_titulo = f"Crea un título corto con un emoji al inicio para esta consulta: '{raw_thought}'. Devuelve solo el texto con el emoji."
                        res_titulo = client.models.generate_content(model='gemini-3.6-flash', contents=prompt_titulo)
                        titulo_con_emoji = res_titulo.text.strip().replace('"', '')
                        
                        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        thread_obj = {
                            "id": datetime.datetime.now().strftime("%Y%m%d%H%M%S%f"),
                            "titulo": titulo_con_emoji,
                            "categoria": "IA Consulta",
                            "creado": ts,
                            "mensajes": [
                                {"autor": "usuario", "texto": raw_thought},
                                {"autor": "assistant", "texto": respuesta_texto}
                            ]
                        }
                        st.session_state.thoughts.append(thread_obj)
                    else:
                        prompt = (
                            "Analiza el texto. Sepáralo en ideas independientes. "
                            "Determina para cada una: 'titulo' (DEBE OBLIGATORIAMENTE EMPEZAR CON UN EMOJI representativo), "
                            "'categoria' y 'contenido'. "
                            "Devuelve ÚNICAMENTE un JSON válido (lista de objetos). "
                            f"Texto: '{raw_thought}'"
                        )
                        resp = client.models.generate_content(model='gemini-3.6-flash', contents=prompt)
                        tr = resp.text.strip().replace("```json", "").replace("```", "").strip()
                        new_thoughts = json.loads(tr)
                        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        
                        for item in new_thoughts:
                            thread_obj = {
                                "id": datetime.datetime.now().strftime("%Y%m%d%H%M%S%f"),
                                "titulo": item.get("titulo", "📝 Nueva Idea"),
                                "categoria": item.get("categoria", "General"),
                                "creado": ts,
                                "mensajes": [{"autor": "usuario", "texto": item.get("contenido", "")}]
                            }
                            st.session_state.thoughts.append(thread_obj)
                    
                    save_table(f"Cerebro_{sufijo}", ["id", "titulo", "categoria", "creado", "mensajes"], st.session_state.thoughts, json_cols=["mensajes"])
                    st.success("¡Blocs creados!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error procesando idea: {e}")

    st.divider()
    
    if st.session_state.thoughts:
        hilos_ordenados = sorted(
            [t for t in st.session_state.thoughts if isinstance(t, dict)], 
            key=lambda x: str(x.get("id", "")), 
            reverse=True
        )
        for t in hilos_ordenados:
            with st.expander(f"{t['titulo']}  (Creado: {t['creado'][:10]})"):
                with st.popover("📄 Ver texto completo (Para copiar)"):
                    texto_completo = "\n\n".join([f"{'Tú' if msg['autor']=='usuario' else 'Cerebro'}: {msg['texto']}" for msg in t["mensajes"]])
                    st.code(texto_completo, language="markdown")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                for msg in t["mensajes"]:
                    if msg["autor"] == "usuario":
                        with st.chat_message("user", avatar="👤"):
                            st.write(msg["texto"])
                    else:
                        with st.chat_message("assistant", avatar="🧠"):
                            st.write(msg["texto"])
                
                with st.form(f"chat_form_{t['id']}", clear_on_submit=True):
                    reply = st.text_area("Nueva nota...", placeholder="Anota algo o escribe 'Ey, Cerebro, dame ideas...'", key=f"input_{t['id']}", height=80)
                    submit_nota = st.form_submit_button("Guardar en el Bloc", use_container_width=True)
                    
                    if submit_nota and reply:
                        t["mensajes"].append({"autor": "usuario", "texto": reply})
                        
                        if "ey, cerebro" in reply.lower() or "ey cerebro" in reply.lower():
                            with st.spinner("Cerebro está procesando tu nota..."):
                                try:
                                    client = genai.Client(api_key=api_key)
                                    historial_texto = "\n".join([f"{'Usuario' if m['autor']=='usuario' else 'Cerebro'}: {m['texto']}" for m in t["mensajes"]])
                                    prompt_ia = f"Eres 'Cerebro', la IA personal de {usuario}. El usuario te acaba de invocar.\n\nEste es el historial del bloc de notas:\n{historial_texto}\n\nResponde a la última petición del usuario de forma útil, concisa y amigable."
                                    res_ia = client.models.generate_content(model='gemini-3.6-flash', contents=prompt_ia)
                                    
                                    t["mensajes"].append({"autor": "assistant", "texto": res_ia.text.strip()})
                                except Exception as e:
                                    t["mensajes"].append({"autor": "assistant", "texto": f"Mmm, tuve un problema procesando eso. Detalles: {e}"})
                        
                        save_table(f"Cerebro_{sufijo}", ["id", "titulo", "categoria", "creado", "mensajes"], st.session_state.thoughts, json_cols=["mensajes"])
                        st.rerun()
                
                if st.button("🗑️ Eliminar este bloc", key=f"del_{t['id']}"):
                    st.session_state.thoughts = [orig_t for orig_t in st.session_state.thoughts if orig_t["id"] != t["id"]]
                    save_table(f"Cerebro_{sufijo}", ["id", "titulo", "categoria", "creado", "mensajes"], st.session_state.thoughts, json_cols=["mensajes"])
                    st.rerun()
    else:
        st.info("Aún no tienes notas guardadas.")

# ==============================================================
# PESTAÑA 3: WISHLIST 
# ==============================================================
with tab_wishlist:
    st.markdown("<h2 style='text-align:center;'>🎁 Lista de Deseos</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Buscá un producto y la IA armará opciones listas para guardar.</p>", unsafe_allow_html=True)
    
    st.subheader("🔍 Asistente de Compras (IA)")
    search_query = st.text_input("¿Qué producto buscás?", placeholder="Ej: PlayStation 5, Zapatillas Nike...")
    
    if st.button("Buscar y Comparar Precios", type="primary", use_container_width=True):
        if not api_key:
            st.error("Falta tu API Key.")
        elif not search_query.strip():
            st.warning("Escribe un producto para buscar.")
        else:
            with st.spinner("Analizando mercado, impuestos y armando tarjetas..."):
                try:
                    client = genai.Client(api_key=api_key)
                    prompt = f"""
                    Actúa como un experto en compras online para un argentino. El usuario busca comprar: '{search_query}'. 
                    El Dólar informal (Blue) está a ${dolar_blue_venta} ARS. 
                    Calcula estimaciones realistas actuales. Evalúa comprarlo localmente (ej. Mercado Libre) vs importarlo (ej. Amazon/Tiendamia).
                    
                    Devuelve ESTRICTAMENTE un JSON con esta estructura exacta (sin comillas invertidas extra):
                    {{
                        "analisis": "Texto breve de 2 líneas comparando las opciones.",
                        "opciones": [
                            {{
                                "origen": "Mercado Libre (Local) o Importado (Amazon)",
                                "item": "Nombre del producto exacto",
                                "precio_base_usd": numero_decimal,
                                "envio_usd": numero_decimal,
                                "impuestos_usd": numero_decimal,
                                "total_usd": numero_decimal,
                                "total_ars": numero_entero,
                                "tiempo_entrega": "Ej: 3 a 5 días",
                                "notas": "Detalle extra muy breve"
                            }}
                        ]
                    }}
                    """
                    res = client.models.generate_content(model='gemini-3.6-flash', contents=prompt)
                    text_res = res.text.replace("```json", "").replace("```", "").strip()
                    st.session_state.wishlist_ia_results = json.loads(text_res)
                except Exception as e:
                    st.error(f"Error procesando los datos de la IA: {e}")

    if "wishlist_ia_results" in st.session_state and st.session_state.wishlist_ia_results:
        data = st.session_state.wishlist_ia_results
        st.info(f"🤖 **Análisis de tu IA:** {data.get('analisis', '')}")
        
        st.markdown("#### 🛒 Opciones listas para guardar:")
        for idx, opc in enumerate(data.get("opciones", [])):
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"### 🛍️ {opc.get('origen', 'Opción')}")
                    st.markdown(f"**{opc.get('item', 'Producto')}**")
                    
                    b_usd = float(opc.get('precio_base_usd', 0))
                    e_usd = float(opc.get('envio_usd', 0))
                    i_usd = float(opc.get('impuestos_usd', 0))
                    t_usd = float(opc.get('total_usd', 0))
                    t_ars = float(opc.get('total_ars', 0))
                    
                    st.markdown(f"""
                    * 📦 **Precio Base:** US$ {b_usd:,.2f}
                    * ✈️ **Envío:** US$ {e_usd:,.2f}
                    * 🏛️ **Imp./Aduana:** US$ {i_usd:,.2f}
                    """)
                    
                    str_ars = f"{t_ars:,.0f}".replace(",", ".")
                    st.markdown(f"#### 💰 Total Final: <span style='color:#10B981;'>{simbolo_html}{str_ars}</span> <span style='font-size:16px; color:#A0A0A0;'>(US&#36; {t_usd:,.2f})</span>", unsafe_allow_html=True)
                    st.caption(f"⏱️ **Entrega estimada:** {opc.get('tiempo_entrega', '')} | 📝 **Notas:** {opc.get('notas', '')}")
                
                with col2:
                    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
                    if st.button("➕ Agregar a Wishlist", key=f"add_wl_ia_{idx}", use_container_width=True):
                        st.session_state.wishlist.append({
                            "id": datetime.datetime.now().strftime("%Y%m%d%H%M%S%f"),
                            "item": f"{opc.get('item', 'Producto')} - {opc.get('origen', '')}",
                            "precio_ars": t_ars,
                            "precio_usd": t_usd,
                            "notas": opc.get("notas", "")
                        })
                        save_table(f"Wishlist_{sufijo}", ["id", "item", "precio_ars", "precio_usd", "notas"], st.session_state.wishlist)
                        st.session_state.wishlist_ia_results = None 
                        st.success("¡Agregado a tu lista de deseos!")
                        st.rerun()

    st.divider()
    with st.expander("➕ Añadir a la Wishlist manualmente"):
        with st.form("manual_wl"):
            c1, c2 = st.columns(2)
            m_item = c1.text_input("Producto / Modelo")
            m_precio = c2.number_input("Precio Estimado (ARS)", min_value=0.0, step=1000.0)
            m_notas = st.text_input("Notas o Link (Opcional)")
            if st.form_submit_button("Guardar en Wishlist"):
                if m_item:
                    usd = m_precio / dolar_blue_venta if dolar_blue_venta > 0 else 0
                    st.session_state.wishlist.append({
                        "id": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
                        "item": m_item,
                        "precio_ars": m_precio,
                        "precio_usd": usd,
                        "notas": m_notas
                    })
                    save_table(f"Wishlist_{sufijo}", ["id", "item", "precio_ars", "precio_usd", "notas"], st.session_state.wishlist)
                    st.success("¡Guardado!")
                    st.rerun()
                else:
                    st.error("Debes ponerle un nombre al producto.")
    
    st.subheader("📌 Mis Deseos Guardados")
    if st.session_state.wishlist:
        for w in st.session_state.wishlist:
            with st.container(border=True): 
                cw1, cw2 = st.columns([3, 1])
                with cw1:
                    st.markdown(f"**{w['item']}**")
                    ars_val = float(w.get('precio_ars', 0))
                    usd_val = float(w.get('precio_usd', 0))
                    str_ars = f"{ars_val:,.0f}".replace(",", ".")
                    st.markdown(f"<h4 style='color:#10B981; margin-top:0px;'>{simbolo_html}{str_ars} <span style='font-size:14px; color:#A0A0A0;'>(US&#36; {usd_val:,.2f})</span></h4>", unsafe_allow_html=True)
                    if w.get('notas'):
                        st.caption(f"📝 {w['notas']}")
                with cw2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑️ Eliminar", key=f"del_w_{w['id']}", use_container_width=True):
                        st.session_state.wishlist = [i for i in st.session_state.wishlist if i["id"] != w["id"]]
                        save_table(f"Wishlist_{sufijo}", ["id", "item", "precio_ars", "precio_usd", "notas"], st.session_state.wishlist)
                        st.rerun()
    else:
        st.info("Tu lista de deseos está vacía.")

# ==============================================================
# PESTAÑA 4: BALANCE
# ==============================================================
with tab_balance:
    st.subheader("📊 Gastos por Categoría")
    if not df_cycle.empty and not df_cycle[df_cycle["tipo"] == "gasto"].empty:
        df_g = df_cycle[df_cycle["tipo"] == "gasto"].groupby("categoria")["monto"].sum().reset_index().sort_values(by="monto", ascending=False)
        
        fig = px.pie(df_g, values="monto", names="categoria", hole=0.45, color_discrete_sequence=px.colors.qualitative.Pastel)
        
        fig.update_traces(
            textinfo='label+value', 
            texttemplate=f'<b>%{{label}}</b><br>{simbolo_moneda}%{{value:,.0f}}',
            textfont_size=15,
            textfont_family="Arial, sans-serif",
            textfont_color="white",
            marker=dict(line=dict(color='#0e1117', width=2))
        )
        
        fig.update_layout(
            showlegend=False,
            margin=dict(t=30, b=30, l=30, r=30),
            separators=".,",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay gastos registrados en este ciclo mensual.")

# ==============================================================
# PESTAÑA 5: HISTORIAL
# ==============================================================
with tab_historial:
    st.subheader("📜 Todos los Movimientos")
    if not df_cycle.empty:
        q = st.text_input("🔍 Buscar por palabra clave")
        df_show = df_cycle.copy().sort_values(by="timestamp", ascending=False)
        
        if q:
            filtro_desc = df_show["descripcion"].str.contains(q, case=False, na=False)
            filtro_cat = df_show["categoria"].str.contains(q, case=False, na=False)
            df_show = df_show[filtro_desc | filtro_cat]
            
        df_display = df_show.copy()
        df_display["Fecha"] = pd.to_datetime(df_display["timestamp"]).dt.strftime("%d/%m/%Y %H:%M")
        df_display["Categoría"] = df_display["categoria"].str.capitalize()
        df_display["Descripción"] = df_display["descripcion"].str.capitalize()
        
        def format_monto(row):
            if row["tipo"] == "ingreso": return f"+ {simbolo_html}{row['monto']:,.0f}".replace(",", ".")
            else: return f"- {simbolo_html}{row['monto']:,.0f}".replace(",", ".")
                
        df_display["Monto"] = df_display.apply(format_monto, axis=1)
        df_display = df_display[["Fecha", "Categoría", "Descripción", "Monto"]]
        
        def color_monto_col(val):
            if isinstance(val, str):
                if val.startswith('+'): return 'color: #10B981; font-weight: bold;'
                if val.startswith('-'): return 'color: #EF4444; font-weight: bold;'
            return ''
            
        styled_df = df_display.style.map(color_monto_col, subset=['Monto'])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        if st.button("🗑️ Borrar último movimiento"):
            st.session_state.transactions.pop()
            save_table(f"Gastos_{sufijo}", ["timestamp", "tipo", "monto", "descripcion", "categoria"], st.session_state.transactions)
            st.rerun()
    else:
        st.info("Sin movimientos.")

# ==============================================================
# PESTAÑA 6: CICLOS Y BOLSILLOS (CON BARRA DE PROGRESO WISHLIST)
# ==============================================================
with tab_ciclos:
    st.subheader(f"📅 Cierre de Mes (Día {DIA_CIERRE})")
    
    # Armar opciones para destinar el sobrante usando los nombres actualizados
    opc_sobrante = {}
    for b in st.session_state.bolsillos:
        d_name = b["nombre"]
        if b.get("wishlist_id"):
            wm = next((w for w in st.session_state.wishlist if w["id"] == b["wishlist_id"]), None)
            if wm: d_name = f"Meta: {wm['item']}"
        opc_sobrante[b["id"]] = d_name

    leftover = st.number_input("Saldo sobrante a guardar:", min_value=0.0, value=float(max(0, saldo_actual)), step=1000.0)
    destino_id = st.selectbox("¿A qué bolsillo va?", options=list(opc_sobrante.keys()), format_func=lambda x: opc_sobrante[x])
    
    if st.button("📥 Guardar en Bolsillo", use_container_width=True) and leftover > 0:
        for b in st.session_state.bolsillos:
            if b["id"] == destino_id:
                b["monto"] += leftover
        save_table(f"Bolsillos_{sufijo}", ["id", "nombre", "ubicacion", "monto", "wishlist_id"], st.session_state.bolsillos)
        st.success(f"¡Guardado en {opc_sobrante[destino_id]}!")
        st.rerun()

    st.divider()
    st.subheader("💰 Mis Bolsillos (Alcancía)")
    total_ahorrado = sum(b["monto"] for b in st.session_state.bolsillos)
    st.metric("Total Ahorrado", f"{simbolo_moneda}{total_ahorrado:,.0f}".replace(",", "."))
    
    with st.expander("➕ Crear nuevo bolsillo"):
        with st.form("new_pocket"):
            # Opciones de Wishlist
            wl_opts = [{"id": "", "label": "🚫 Sin meta (Ahorro Libre)"}] + [{"id": w["id"], "label": f"🎁 {w['item']}"} for w in st.session_state.wishlist]
            wl_sel = st.selectbox("🎯 Vincular a Meta de Wishlist (Opcional)", options=[x["id"] for x in wl_opts], format_func=lambda x: next(item["label"] for item in wl_opts if item["id"] == x))
            
            n_bolsillo = st.text_input("Nombre (Solo si no elegiste meta arriba)", placeholder="Ej: Fondo de Emergencia")
            n_ubicacion = st.text_input("Ubicación Física (Ej: Mercado Pago, Caja Fuerte)")
            
            if st.form_submit_button("Crear Bolsillo"):
                final_name = n_bolsillo
                if wl_sel:
                    wl_match = next((w for w in st.session_state.wishlist if w["id"] == wl_sel), None)
                    if wl_match: final_name = wl_match["item"]
                        
                if not final_name and not wl_sel:
                    st.error("Debes ponerle un nombre o seleccionar una meta.")
                else:
                    st.session_state.bolsillos.append({
                        "id": f"b_{datetime.datetime.now().strftime('%M%S%f')}", 
                        "nombre": final_name, 
                        "ubicacion": n_ubicacion, 
                        "monto": 0.0,
                        "wishlist_id": wl_sel
                    })
                    save_table(f"Bolsillos_{sufijo}", ["id", "nombre", "ubicacion", "monto", "wishlist_id"], st.session_state.bolsillos)
                    st.rerun()

    for b in st.session_state.bolsillos:
        with st.container(border=True):
            wl_id = b.get("wishlist_id", "")
            display_name = b["nombre"]
            target = 0
            
            if wl_id:
                w_match = next((w for w in st.session_state.wishlist if w["id"] == wl_id), None)
                if w_match:
                    display_name = f"🎯 Meta: {w_match['item']}"
                    target = float(w_match.get("precio_ars", 0))
            
            st.markdown(f"### {display_name}")
            st.markdown(f"<h4 style='color:#10B981; margin-top:0px;'>{simbolo_html}{b['monto']:,.0f}</h4>".replace(",", "."), unsafe_allow_html=True)
            
            if target > 0:
                prog_val = min(b["monto"] / target, 1.0)
                st.progress(prog_val)
                st.caption(f"🎯 Precio Meta: {simbolo_html}{target:,.0f} | 📈 Progreso: {prog_val*100:.1f}%".replace(",", "."))
            
            col_ed, col_mov = st.columns(2)
            with col_ed:
                nueva_ubi = st.text_input(f"📍 Ubicación", value=b.get("ubicacion", ""), key=f"ubi_{b['id']}")
                
                # Desplegable para editar la meta a posteriori
                wl_opts = [{"id": "", "label": "🚫 Sin meta"}] + [{"id": w["id"], "label": f"🎁 {w['item']}"} for w in st.session_state.wishlist]
                idx_actual = [x["id"] for x in wl_opts].index(wl_id) if wl_id in [x["id"] for x in wl_opts] else 0
                nuevo_wl = st.selectbox("🎯 Editar Meta", options=[x["id"] for x in wl_opts], format_func=lambda x: next(item["label"] for item in wl_opts if item["id"] == x), index=idx_actual, key=f"wl_{b['id']}")
                
                if nueva_ubi != b.get("ubicacion", "") or nuevo_wl != wl_id:
                    b["ubicacion"] = nueva_ubi
                    b["wishlist_id"] = nuevo_wl
                    if nuevo_wl:
                        w_match2 = next((w for w in st.session_state.wishlist if w["id"] == nuevo_wl), None)
                        if w_match2: b["nombre"] = w_match2["item"]
                    save_table(f"Bolsillos_{sufijo}", ["id", "nombre", "ubicacion", "monto", "wishlist_id"], st.session_state.bolsillos)
                    st.rerun()
                    
            with col_mov:
                mover = st.number_input("💸 Mover plata", min_value=0.0, max_value=float(b["monto"]), key=f"mov_{b['id']}")
                dest = st.selectbox("Destino", [x for x in opc_sobrante.keys() if x != b["id"]], format_func=lambda x: opc_sobrante[x], key=f"dest_{b['id']}")
                if st.button("Transferir", key=f"btn_mov_{b['id']}") and mover > 0:
                    b["monto"] -= mover
                    for dest_b in st.session_state.bolsillos:
                        if dest_b["id"] == dest: dest_b["monto"] += mover
                    save_table(f"Bolsillos_{sufijo}", ["id", "nombre", "ubicacion", "monto", "wishlist_id"], st.session_state.bolsillos)
                    st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================
# PESTAÑA 7: CATEGORÍAS
# ==============================================================
with tab_categorias:
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
# PESTAÑA 8: AJUSTES Y REPORTES
# ==============================================================
with tab_ajustes:
    st.subheader("⚙️ Configuración Personal")
    
    with st.form("settings_form"):
        nuevo_cierre = st.number_input("Día de inicio/cierre de ciclo", min_value=1, max_value=31, value=DIA_CIERRE)
        nueva_divisa = st.selectbox("Divisa Activa", ["ARS", "USD", "EUR"], index=["ARS", "USD", "EUR"].index(DIVISA))
        
        st.markdown("🔒 **Seguridad (Opcional)**")
        usar_pin_input = st.checkbox("Requerir PIN para entrar a mi perfil", value=user_settings.get("usar_pin", False))
        nuevo_pin = st.text_input("PIN Numérico", value=user_settings.get("pin", ""), type="password")
        
        if st.form_submit_button("Guardar Cambios"):
            if usar_pin_input and not nuevo_pin.isdigit():
                st.error("El PIN debe contener únicamente números.")
            else:
                user_settings["dia_cierre"] = nuevo_cierre
                user_settings["divisa"] = nueva_divisa
                user_settings["usar_pin"] = usar_pin_input
                user_settings["pin"] = nuevo_pin if usar_pin_input else ""
                save_config(f"settings_{sufijo}", user_settings)
                st.success("¡Ajustes guardados!")
                st.rerun()
            
    st.divider()
    st.subheader("📄 Exportar Reporte")
    st.info("Genera una vista limpia para imprimir o guardar como PDF desde tu navegador.")
    mes_reporte = st.selectbox("Elegir Mes", [meses_anio[now.month - 1], meses_anio[now.month - 2]])
    if st.button("Generar Reporte Imprimible"):
        st.markdown(f"### Reporte Financiero: {mes_reporte}")
        st.write(f"**Usuario:** {usuario} | **Gastos Totales:** {simbolo_moneda}{total_gastos:,.0f}".replace(",", "."))
        st.dataframe(df_cycle[["timestamp", "categoria", "monto"]].sort_values(by="timestamp"))
        st.components.v1.html("<script>window.print();</script>", height=0)

    st.divider()
    if st.button("Cerrar Sesión", type="primary"):
        cerrar_sesion()
