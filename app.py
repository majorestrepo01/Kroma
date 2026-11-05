import json
import time
import streamlit as st
from textblob import TextBlob
import paho.mqtt.client as paho
from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events
import librosa
import numpy as np

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
        <p>Transforma la atmósfera física de tu habitación combinando tu estado emocional (texto) y el análisis acústico de la canción (audio).</p>
    </div>
""", unsafe_allow_html=True)

st.markdown("""
### 🧭 ¿Qué debes hacer?
1. **Describe tu estado de ánimo:** Escribe en el cuadro de texto cómo te sientes o qué necesitas.
2. **Analiza el sonido ambiente/musical:** Sube un archivo de audio (MP3/WAV) para que **Librosa** analice el tempo (BPM) y las características acústicas del sonido.
3. **Genera tu ambiente:** El sistema calculará el color y la intensidad ideal y los enviará vía **MQTT** a tus luces LED en Wokwi.
""")

st.markdown("---")

# Inicializar estados de sesión
if "recording_active" not in st.session_state:
    st.session_state.recording_active = False
if "audio_analyzed" not in st.session_state:
    st.session_state.audio_analyzed = False
if "tempo_bpm" not in st.session_state:
    st.session_state.tempo_bpm = 0.0
if "spectral_centroid" not in st.session_state:
    st.session_state.spectral_centroid = 0.0

col1, col2 = st.columns(2, gap="large")

with col1:
    st.subheader("📝 1. Análisis de Sentimientos (Texto)")
    user_text = st.text_area(
        "¿Cómo te sientes hoy?",
        placeholder="Ej. Me siento cansado y necesito concentrarme...",
        height=130
    )

with col2:
    st.subheader("🎙️ 2. Análisis Acústico de Audio (Librosa)")
    st.write("Sube una canción o fragmento de audio para analizar su sonido real:")
    
    # Subida de archivo de audio para análisis de sonido real con librosa
    uploaded_audio = st.file_uploader("Sube tu archivo de audio (WAV, MP3)", type=["wav", "mp3"])

    if uploaded_audio is not None:
        # Indicador visual de que se está procesando / grabando o analizando
        st.info("🔴 **Grabación / Audio cargado:** Procesando propiedades acústicas del sonido con Librosa...")
        st.audio(uploaded_audio)

        # Botón para parar/procesar o reiniciar
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("⏹️ Parar y Analizar Audio"):
                try:
                    # Guardar temporalmente el archivo para que librosa pueda leerlo
                    with open("temp_audio.mp3", "wb") as f:
                        f.write(uploaded_audio.getbuffer())
                    
                    # Análisis acústico real usando Librosa (Tempo y Espectro)
                    y, sr = librosa.load("temp_audio.mp3", duration=30)
                    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
                    
                    # Manejar si tempo es un array o escalar
                    if isinstance(tempo, np.ndarray):
                        tempo = float(tempo[0])
                    else:
                        tempo = float(tempo)
                        
                    spec_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))

                    st.session_state.tempo_bpm = tempo
                    st.session_state.spectral_centroid = spec_centroid
                    st.session_state.audio_analyzed = True
                    st.success("✅ **¡Canción analizada con éxito!** Las propiedades acústicas están listas.")
                except Exception as e:
                    st.error(f"Error procesando el audio con librosa: {e}")

        with col_btn2:
            if st.button("🔄 Reiniciar Grabación / Audio"):
                st.session_state.audio_analyzed = False
                st.session_state.tempo_bpm = 0.0
                st.session_state.spectral_centroid = 0.0
                st.rerun()

        if st.session_state.audio_analyzed:
            st.write(f"📊 **Resultados Acústicos (Librosa):** Tempo: `{st.session_state.tempo_bpm:.1f} BPM` | Brillo Sonoro: `{st.session_state.spectral_centroid:.1f} Hz`")

st.markdown("---")

# Botón principal para procesar y enviar la salida física
if st.button("✨ Generar Ambiente y Actualizar Habitación", type="primary", use_container_width=True):
    if not user_text and not st.session_state.audio_analyzed:
        st.warning("⚠️ Por favor ingresa texto y analiza un archivo de audio antes de continuar.")
    else:
        # 1. Análisis de polaridad del texto usando TextBlob
        analysis = TextBlob(user_text if user_text else "neutral")
        polarity = analysis.sentiment.polarity

        # 2. Lógica de combinación multimodal (Texto + Acústica con Librosa)
        r, g, b = 0, 206, 209
        brightness = 180
        mood_label = "Balance y Enfoque"

        if polarity < -0.1:
            r, g, b = 138, 43, 226  # Violeta relajante
            brightness = 110
            mood_label = "Calma y Relajación"
        elif polarity > 0.2:
            r, g, b = 255, 140, 0   # Naranja dinámico
            brightness = 255
            mood_label = "Energía y Vitalidad"

        # Modulación basada puramente en el sonido analizado por Librosa (BPM / Brillo)
        if st.session_state.audio_analyzed:
            bpm = st.session_state.tempo_bpm
            if bpm > 130:  # Ritmo rápido / enérgico
                r, g, b = 255, 0, 127  # Fucsia vibrante
                brightness = 255
            elif bpm < 90:  # Ritmo lento / chill
                r, g, b = 70, 130, 180  # Azul suave
                brightness = 140

        st.success(f"🎯 **Ambiente Calculado:** {mood_label} | **Audio (Librosa):** {st.session_state.tempo_bpm:.1f} BPM")

        # Visualizador en la interfaz web
        st.markdown(
            f"""
            <div style="background-color: rgb({r}, {g}, {b}); 
                        width: 100%; height: 90px; border-radius: 14px; 
                        display: flex; align-items: center; justify-content: center; 
                        color: white; font-weight: bold; font-size: 20px;
                        box-shadow: 0 6px 20px rgba(0,0,0,0.25); margin-top: 15px;">
                Iluminación Generada: RGB({r}, {g}, {b}) — Brillo: {brightness}
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
            st.success(f"🚀 **¡Señal enviada con éxito vía MQTT al tópico `{topic}`!** Tu simulación en Wokwi reflejará los cambios.")
        except Exception as e:
            st.error(f"Error al conectar o publicar en el broker MQTT: {e}")
