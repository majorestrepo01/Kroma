import json
import time
import os
import numpy as np
import librosa
import streamlit as st
from textblob import TextBlob
import paho.mqtt.client as paho
from audio_recorder_streamlit import audio_recorder

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
        <p>Transforma la atmósfera física de tu habitación combinando tu estado emocional (texto) y el análisis acústico directo de la canción que escuchas (micrófono + Librosa).</p>
    </div>
""", unsafe_allow_html=True)

st.markdown("""
### 🧭 ¿Qué debes hacer?
1. **Describe tu estado de ánimo:** Escribe en el cuadro de texto cómo te sientes.
2. **Escucha la canción con el micrófono:** Presiona el ícono del micrófono para empezar a grabar la canción que suena en tu habitación. Haz clic nuevamente para detener la grabación.
3. **Analiza y Transforma:** El sistema procesará las ondas sonoras con **Librosa**, calculará el color/brillo y enviará la orden vía **MQTT** a tus luces LED en Wokwi.
""")

st.markdown("---")

# Inicialización del estado de sesión
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
        placeholder="Ej. Me siento cansado y necesito concentrarme para estudiar...",
        height=140
    )

with col2:
    st.subheader("🎙️ 2. Captura y Análisis por Micrófono (Librosa)")
    st.write("Haz clic en el micrófono para empezar a escuchar la canción que suena:")
    
    # Grabador de audio por micrófono directo desde la Web
    audio_bytes = audio_recorder(
        text="Haz clic para grabar / parar",
        recording_color="#e84c3d",
        neutral_color="#6c757d",
        icon_name="microphone",
        icon_size="2x"
    )

    if audio_bytes:
        st.info("🔴 **Micrófono activo / Grabación capturada.** Procesando propiedades acústicas del sonido con Librosa...")
        
        # Reproductor del fragmento grabado
        st.audio(audio_bytes, format="audio/wav")
        
        # Botones para procesar o reiniciar
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("⚙️ Analizar Sonido con Librosa"):
                try:
                    # Guardar temporalmente los bytes capturados por el micrófono
                    temp_filename = "temp_mic_recording.wav"
                    with open(temp_filename, "wb") as f:
                        f.write(audio_bytes)
                    
                    # Cargar con Librosa y extraer características del sonido
                    y, sr = librosa.load(temp_filename, duration=15)
                    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
                    
                    if isinstance(tempo, np.ndarray):
                        tempo = float(tempo[0])
                    else:
                        tempo = float(tempo)
                        
                    spec_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))

                    st.session_state.tempo_bpm = tempo
                    st.session_state.spectral_centroid = spec_centroid
                    st.session_state.audio_analyzed = True
                    
                    # Eliminar archivo temporal tras análisis
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)
                        
                except Exception as e:
                    st.error(f"Error al analizar el audio grabado con Librosa: {e}")

        with col_btn2:
            if st.button("🔄 Reiniciar Grabación"):
                st.session_state.audio_analyzed = False
                st.session_state.tempo_bpm = 0.0
                st.session_state.spectral_centroid = 0.0
                st.rerun()

        if st.session_state.audio_analyzed:
            st.success("✅ **¡Canción escuchada y analizada con éxito!** Ya puedes generar tu ambiente.")
            st.write(f"📊 **Resultados del Sonido:** Ritmo: `{st.session_state.tempo_bpm:.1f} BPM` | Frecuencia Promedio: `{st.session_state.spectral_centroid:.1f} Hz`")

st.markdown("---")

# Botón principal para procesar y enviar la salida física
if st.button("✨ Generar Ambiente y Actualizar Habitación", type="primary", use_container_width=True):
    if not user_text and not st.session_state.audio_analyzed:
        st.warning("⚠️ Por favor escribe tu estado de ánimo o graba un fragmento de la canción con el micrófono antes de continuar.")
    else:
        # 1. Análisis de polaridad del texto (TextBlob)
        analysis = TextBlob(user_text if user_text else "neutral")
        polarity = analysis.sentiment.polarity  # Rango de -1.0 a 1.0

        # 2. Lógica de combinación multimodal (Texto + Acústica en tiempo real)
        r, g, b = 0, 206, 209  # Turquesa neutro
        brightness = 180
        mood_label = "Balance y Enfoque"

        # Ajuste según el estado anímico
        if polarity < -0.1:
            r, g, b = 138, 43, 226  # Purpura/Violeta relajante
            brightness = 110
            mood_label = "Calma y Relajación"
        elif polarity > 0.2:
            r, g, b = 255, 140, 0   # Naranja dinámico
            brightness = 255
            mood_label = "Energía y Vitalidad"

        # Ajuste según las métricas sonoras calculadas por Librosa
        if st.session_state.audio_analyzed:
            bpm = st.session_state.tempo_bpm
            if bpm > 125:  # Música rápida / festiva / rock
                r, g, b = 255, 0, 127  # Fucsia vibrante
                brightness = 255
            elif bpm < 90 and bpm > 0:  # Música lenta / chill / acústica
                r, g, b = 70, 130, 180  # Azul suave
                brightness = 130

        st.success(f"🎯 **Ambiente Calculado:** {mood_label} | **Música (BPM detectados):** {st.session_state.tempo_bpm:.1f} BPM")

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

        # 3. Envío de la señal vía MQTT hacia Wokwi
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
