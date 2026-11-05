import json
import time
import streamlit as st
from textblob import TextBlob
import paho.mqtt.client as paho
from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events

# Configuración de la página
st.set_page_config(
    page_title="Kroma - Estación Sensorial Multimodal",
    page_icon="🎵",
    layout="wide"
)

# Configuración MQTT
broker = "broker.mqttdashboard.com"
port = 1883
topic = "kroma/mood/lights"

def on_publish(client, userdata, result):
    print("El dato ha sido publicado correctamente.\n")

# Estilos CSS personalizados
st.markdown("""
    <style>
    .header-container {
        background: linear-gradient(135deg, #10b981 0%, #3b82f6 50%, #8b5cf6 100%);
        padding: 25px;
        border-radius: 16px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 8px 20px rgba(59, 130, 246, 0.2);
    }
    .header-container h1 {
        margin: 0;
        font-size: 2.3rem;
        font-weight: 800;
        color: white !important;
    }
    .header-container p {
        margin-top: 8px;
        font-size: 1.05rem;
        color: #e0e7ff !important;
    }
    </style>
""", unsafe_allow_html=True)

# Título y Banner explicativo
st.markdown("""
    <div class="header-container">
        <h1>🎵 Kroma — Estación de Ambiente y Entretenimiento Sensorial</h1>
        <p>Transforma la atmósfera física de tu habitación combinando tu estado emocional (texto) y tu contexto musical (reconocimiento de voz).</p>
    </div>
""", unsafe_allow_html=True)

st.markdown("""
### 🧭 ¿Qué debes hacer?
1. **Describe tu estado de ánimo:** Escribe en el cuadro de texto cómo te sientes o qué necesitas en este momento.
2. **Indica tu música:** Presiona el botón del micrófono y di en voz alta el género musical, artista o la canción que estás escuchando.
3. **Avisa y Transforma:** Una vez que la canción haya finalizado o se haya capturado el contexto, el sistema te avisará para que puedas generar tu ambiente lumínico.
""")

st.markdown("---")

# Inicializar estados de sesión para control de audio y avisos
if "music_ready" not in st.session_state:
    st.session_state.music_ready = False
if "music_text" not in st.session_state:
    st.session_state.music_text = ""

# Distribución en dos columnas para las entradas multimodales
col1, col2 = st.columns(2, gap="large")

with col1:
    st.subheader("📝 1. Análisis de Sentimientos (Texto)")
    user_text = st.text_area(
        "¿Cómo te sientes hoy?",
        placeholder="Ej. Me siento cansado y necesito concentrarme para estudiar...",
        height=130
    )

with col2:
    st.subheader("🎙️ 2. Contexto Musical (Micrófono)")
    st.write("Toca el botón y di la música que te acompaña:")
    
    # Botón de reconocimiento de voz con Bokeh Events
    stt_button = Button(label="🎤 Iniciar Captura de Voz", width=260)
    stt_button.js_on_event("button_click", CustomJS(code="""
        var recognition = new webkitSpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        
        recognition.onresult = function (e) {
            var value = "";
            for (var i = e.resultIndex; i < e.results.length; ++i) {
                if (e.results[i].isFinal) {
                    value += e.results[i][0].transcript;
                }
            }
            if (value != "") {
                document.dispatchEvent(new CustomEvent("GET_MUSIC_TEXT", {detail: value}));
            }
        }
        recognition.start();
    """))

    result = streamlit_bokeh_events(
        stt_button,
        events="GET_MUSIC_TEXT",
        key="listen_music_input",
        refresh_on_update=False,
        override_height=75,
        debounce_time=0
    )

    if result and "GET_MUSIC_TEXT" in result:
        st.session_state.music_text = result.get("GET_MUSIC_TEXT").strip()
        st.session_state.music_ready = True

    # Mostrar estado de la música detectada
    if st.session_state.music_ready:
        st.info(f"🎶 **Música/Vibra detectada:** \"{st.session_state.music_text}\"")
        
        # Nueva función interactiva: Aviso de que ya se escuchó la canción y puede proceder
        st.success("✅ **¡Canción escuchada con éxito!** Ya puedes pasar a generar tu ambiente.")
        
        if st.button("🔄 Reiniciar captura de audio"):
            st.session_state.music_ready = False
            st.session_state.music_text = ""
            st.rerun()

st.markdown("---")

# Botón principal para procesar y enviar la salida física
if st.button("✨ Generar Ambiente y Actualizar Habitación", type="primary", use_container_width=True):
    if not user_text and not st.session_state.music_text:
        st.warning("⚠️ Por favor escribe tu estado de ánimo o captura la música con el micrófono antes de continuar.")
    else:
        # 1. Análisis de polaridad del texto usando TextBlob
        analysis = TextBlob(user_text if user_text else "neutral")
        polarity = analysis.sentiment.polarity  # Rango de -1.0 a 1.0

        # 2. Lógica de combinación multimodal para definir color RGB e intensidad
        r, g, b = 0, 206, 209  # Turquesa por defecto
        brightness = 180
        mood_label = "Enfoque y Balance"

        # Modulación según sentimiento en texto
        if polarity < -0.1:
            r, g, b = 138, 43, 226  # Violeta relajante
            brightness = 110
            mood_label = "Calma y Relajación"
        elif polarity > 0.2:
            r, g, b = 255, 140, 0   # Naranja dinámico
            brightness = 255
            mood_label = "Energía y Vitalidad"

        # Modulación secundaria según lo detectado por voz (música)
        music_lower = st.session_state.music_text.lower()
        if "rock" in music_lower or "metal" in music_lower or "intenso" in music_lower:
            r, g, b = 255, 0, 0        # Rojo dinámico
        elif "lofi" in music_lower or "chill" in music_lower or "tranquilo" in music_lower or "clásica" in music_lower:
            r, g, b = 70, 130, 180     # Azul acero suave
        elif "pop" in music_lower or "fiesta" in music_lower or "electrónica" in music_lower:
            r, g, b = 255, 20, 147     # Rosado neón

        st.success(f"🎯 **Ambiente Calculado:** {mood_label} | **Audio/Voz:** {st.session_state.music_text if st.session_state.music_text else 'No especificado'}")

        # Visualizador en la interfaz web acorde al ambiente generado
        st.markdown(
            f"""
            <div style="background-color: rgb({r}, {g}, {b}); 
                        width: 100%; height: 90px; border-radius: 14px; 
                        display: flex; align-items: center; justify-content: center; 
                        color: white; font-weight: bold; font-size: 20px;
                        box-shadow: 0 6px 20px rgba(0,0,0,0.25); margin-top: 15px;">
                Iluminación de Habitación Generada: RGB({r}, {g}, {b}) — Brillo: {brightness}
            </div>
            """,
            unsafe_allow_html=True
        )

        # 3. Envío de la señal física vía MQTT hacia Wokwi
        try:
            client1 = paho.Client("KromaStreamlitClient")
            client1.on_publish = on_publish
            client1.connect(broker, port)
            payload = json.dumps({"r": int(r), "g": int(g), "b": int(b), "brightness": int(brightness)})
            client1.publish(topic, payload)
            client1.disconnect()
            st.success(f"🚀 **¡Señal enviada con éxito vía MQTT al tópico `{topic}`!** Tu simulación en Wokwi reflejará los cambios de inmediato.")
        except Exception as e:
            st.error(f"Error al conectar o publicar en el broker MQTT: {e}")
