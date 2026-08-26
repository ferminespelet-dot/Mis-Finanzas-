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
    
    st.session_state.bolsillos = load_table(f"Bolsillos_{sufijo}", ["id", "nombre", "ubicacion", "monto"])
    if not st.session_state.bolsillos:
        st.session_state.bolsillos = [{"id": "b_default", "nombre": "Ahorro General", "ubicacion": "Cuenta DNI", "monto": 0.0}]
        save_table(f"Bolsillos_{sufijo}", ["id", "nombre", "ubicacion", "monto"], st.session_state.bolsillos)

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

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "💬 Registro", "📊 Balance", "📜 Historial", "📅 Ciclos", "🏷️ Categorías", "🧠 Cerebro", "⚙️ Ajustes"
])

def formatear_tarjeta_movimiento(tx):
    color = "#10B981" if tx["tipo"] == "ingreso" else "#EF4444"
    signo = "+" if tx["tipo"] == "ingreso" else "-"
    monto_str = f"{signo} {simbolo_moneda}{tx['monto']:,.0f}".replace(",", ".")
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
# PESTAÑA 1: REGISTRO (ARRIBA DE TODO)
# ==============================================================
with tab1:
    # 1. EL REGISTRO VA PRIMERO (Más accesible al dedo)
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

    # 2. ÚLTIMA ACTIVIDAD (Abajo del registro)
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
    
    # 3. PENDIENTES Y DEVOLUCIONES
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
            st.markdown(f"**{row['concepto']}**<br><span style='color:#EF4444;'>- {simbolo_moneda}{row['monto']:,.0f}</span>".replace(",", "."), unsafe_allow_html=True)
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
            st.markdown(f"**{row['concepto']}**<br><span style='color:#10B981;'>+ {simbolo_moneda}{row['monto']:,.0f}</span>".replace(",", "."), unsafe_allow_html=True)
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
# PESTAÑA 2: BALANCE (GRÁFICO MEJORADO)
# ==============================================================
with tab2:
    st.subheader("📊 Gastos por Categoría")
    if not df_cycle.empty and not df_cycle[df_cycle["tipo"] == "gasto"].empty:
        df_g = df_cycle[df_cycle["tipo"] == "gasto"].groupby("categoria")["monto"].sum().reset_index().sort_values(by="monto", ascending=False)
        
        # Diseño Premium para la torta
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
# PESTAÑA 3: HISTORIAL (EMBELLECIDO)
# ==============================================================
with tab3:
    st.subheader("📜 Todos los Movimientos")
    if not df_cycle.empty:
        q = st.text_input("🔍 Buscar por palabra clave")
        df_show = df_cycle.copy().sort_values(by="timestamp", ascending=False)
        
        if q:
            filtro_desc = df_show["descripcion"].str.contains(q, case=False, na=False)
            filtro_cat = df_show["categoria"].str.contains(q, case=False, na=False)
            df_show = df_show[filtro_desc | filtro_cat]
            
        # Preparar datos bonitos para la tabla
        df_display = df_show.copy()
        df_display["Fecha"] = pd.to_datetime(df_display["timestamp"]).dt.strftime("%d/%m/%Y %H:%M")
        df_display["Categoría"] = df_display["categoria"].str.capitalize()
        df_display["Descripción"] = df_display["descripcion"].str.capitalize()
        
        def format_monto(row):
            if row["tipo"] == "ingreso": return f"+ {simbolo_moneda}{row['monto']:,.0f}".replace(",", ".")
            else: return f"- {simbolo_moneda}{row['monto']:,.0f}".replace(",", ".")
                
        df_display["Monto"] = df_display.apply(format_monto, axis=1)
        df_display = df_display[["Fecha", "Categoría", "Descripción", "Monto"]]
        
        # Aplicar colores con Pandas Styler
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
# PESTAÑA 4: CICLOS Y BOLSILLOS
# ==============================================================
with tab4:
    st.subheader(f"📅 Cierre de Mes (Día {DIA_CIERRE})")
    leftover = st.number_input("Saldo sobrante a guardar:", min_value=0.0, value=float(max(0, saldo_actual)), step=1000.0)
    
    opciones_bolsillos = {b["id"]: b["nombre"] for b in st.session_state.bolsillos}
    destino_id = st.selectbox("¿A qué bolsillo va?", options=list(opciones_bolsillos.keys()), format_func=lambda x: opciones_bolsillos[x])
    
    if st.button("📥 Guardar en Bolsillo", use_container_width=True) and leftover > 0:
        for b in st.session_state.bolsillos:
            if b["id"] == destino_id:
                b["monto"] += leftover
        save_table(f"Bolsillos_{sufijo}", ["id", "nombre", "ubicacion", "monto"], st.session_state.bolsillos)
        st.success(f"¡Guardado en {opciones_bolsillos[destino_id]}!")
        st.rerun()

    st.divider()
    st.subheader("💰 Mis Bolsillos (Alcancía)")
    total_ahorrado = sum(b["monto"] for b in st.session_state.bolsillos)
    st.metric("Total Ahorrado", f"{simbolo_moneda}{total_ahorrado:,.0f}".replace(",", "."))
    
    with st.expander("➕ Crear nuevo bolsillo"):
        with st.form("new_pocket"):
            n_bolsillo = st.text_input("Nombre (Ej: Vacaciones)")
            n_ubicacion = st.text_input("Ubicación Física (Ej: Mercado Pago, Caja Fuerte)")
            if st.form_submit_button("Crear") and n_bolsillo:
                st.session_state.bolsillos.append({"id": f"b_{datetime.datetime.now().strftime('%M%S%f')}", "nombre": n_bolsillo, "ubicacion": n_ubicacion, "monto": 0.0})
                save_table(f"Bolsillos_{sufijo}", ["id", "nombre", "ubicacion", "monto"], st.session_state.bolsillos)
                st.rerun()

    for b in st.session_state.bolsillos:
        st.markdown(f"**{b['nombre']}** - {simbolo_moneda}{b['monto']:,.0f}".replace(",", "."))
        col_ed, col_mov = st.columns(2)
        with col_ed:
            nueva_ubi = st.text_input(f"Ubicación", value=b["ubicacion"], key=f"ubi_{b['id']}")
            if nueva_ubi != b["ubicacion"]:
                b["ubicacion"] = nueva_ubi
                save_table(f"Bolsillos_{sufijo}", ["id", "nombre", "ubicacion", "monto"], st.session_state.bolsillos)
        with col_mov:
            mover = st.number_input("Mover plata", min_value=0.0, max_value=float(b["monto"]), key=f"mov_{b['id']}")
            dest = st.selectbox("Destino", [x for x in opciones_bolsillos.keys() if x != b["id"]], format_func=lambda x: opciones_bolsillos[x], key=f"dest_{b['id']}")
            if st.button("Transferir", key=f"btn_mov_{b['id']}") and mover > 0:
                b["monto"] -= mover
                for dest_b in st.session_state.bolsillos:
                    if dest_b["id"] == dest: dest_b["monto"] += mover
                save_table(f"Bolsillos_{sufijo}", ["id", "nombre", "ubicacion", "monto"], st.session_state.bolsillos)
                st.rerun()
        st.divider()

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
                        "Determina para cada una: 'titulo', 'categoria' y 'contenido'. "
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
                            "titulo": item.get("titulo", "Idea sin título"),
                            "categoria": item.get("categoria", "Random"),
                            "creado": ts,
                            "mensajes": [{"autor": "usuario", "texto": item.get("contenido", "")}]
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
                    if st.form_submit_button("Enviar") and reply:
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
        st.info("Aún no tienes notas guardadas.")

# ==============================================================
# PESTAÑA 7: AJUSTES Y REPORTES
# ==============================================================
with tab7:
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
