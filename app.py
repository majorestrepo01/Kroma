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
        <h1>Kroma</h1>
        <p>Transforma la atmósfera de tu habitación combinando tu estado emocional y la canción que estas escuchando.</p>
    </div>
""", unsafe_allow_html=True)

st.markdown("""
### 🧭 ¿Qué debes hacer?
1. **Describe tu estado de ánimo:** Escribe en el cuadro de texto cómo te sientes.
2. **Captura el audio con el micrófono:** Graba un fragmento de la canción que estas escuchando.
3. **Analiza y Transforma:** El sistema evaluará tu canción, para calcular el ambiente perfecto para tus habitación.
""")

st.markdown("---")

# Inicialización del estado de sesión
if "audio_analyzed" not in st.session_state:
    st.session_state.audio_analyzed = False
if "tempo_bpm" not in st.session_state:
    st.session_state.tempo_bpm = 0.0
if "rms_energy" not in st.session_state:
    st.session_state.rms_energy = 0.0
if "spectral_centroid" not in st.session_state:
    st.session_state.spectral_centroid = 0.0
if "zcr" not in st.session_state:
    st.session_state.zcr = 0.0
if "energy_level" not in st.session_state:
    st.session_state.energy_level = ""
if "rhythm" not in st.session_state:
    st.session_state.rhythm = ""

col1, col2 = st.columns(2, gap="large")

with col1:
    st.subheader("📝 1. Análisis de Sentimientos")
    user_text = st.text_area(
        "¿Cómo te sientes hoy?",
        placeholder="Ej. Me siento cansado, feliz, triste...",
        height=140
    )

with col2:
    st.subheader("🎙️ 2. Análisis de música")
    st.write("Haz clic en el micrófono para grabar la canción:")
    
    # Grabador de audio por micrófono directo
    audio_bytes = audio_recorder(
        text="Haz clic para grabar / parar",
        recording_color="#e84c3d",
        neutral_color="#6c757d",
        icon_name="microphone",
        icon_size="2x"
    )

    if audio_bytes:
        st.info("🔴 **Micrófono activo / Grabación capturada.** Procesando características acústicas con Librosa...")
        st.audio(audio_bytes, format="audio/wav")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("⚙️ Analizar con Librosa"):
                try:
                    temp_filename = "temp_mic_recording.wav"
                    with open(temp_filename, "wb") as f:
                        f.write(audio_bytes)
                    
                    # Carga y análisis completo con Librosa
                    y, sr = librosa.load(temp_filename, duration=15)
                    
                    # 1. Tempo (BPM)
                    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
                    if isinstance(tempo, np.ndarray):
                        tempo = float(tempo[0])
                    else:
                        tempo = float(tempo)
                        
                    # 2. RMS Energy (Intensidad energética)
                    energy = float(np.mean(librosa.feature.rms(y=y)))
                    
                    # 3. Spectral Centroid (Brillo)
                    spec_centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
                    
                    # 4. Zero Crossing Rate (Complemento de sonido)
                    zero_crossing = float(np.mean(librosa.feature.zero_crossing_rate(y)))

                    # Clasificación de Energía según tus reglas
                    if energy < 0.05:
                        energy_level = "Baja"
                    elif energy < 0.12:
                        energy_level = "Media"
                    else:
                        energy_level = "Alta"

                    # Clasificación de Ritmo según tus reglas
                    if tempo < 80:
                        rhythm = "Lento"
                    elif tempo < 120:
                        rhythm = "Moderado"
                    else:
                        rhythm = "Rápido"

                    # Guardar en session_state
                    st.session_state.tempo_bpm = tempo
                    st.session_state.rms_energy = energy
                    st.session_state.spectral_centroid = spec_centroid
                    st.session_state.zcr = zero_crossing
                    st.session_state.energy_level = energy_level
                    st.session_state.rhythm = rhythm
                    st.session_state.audio_analyzed = True
                    
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)
                        
                except Exception as e:
                    st.error(f"Error procesando el audio con Librosa: {e}")

        with col_btn2:
            if st.button("🔄 Reiniciar Grabación"):
                st.session_state.audio_analyzed = False
                st.session_state.tempo_bpm = 0.0
                st.session_state.rms_energy = 0.0
                st.session_state.spectral_centroid = 0.0
                st.session_state.zcr = 0.0
                st.session_state.energy_level = ""
                st.session_state.rhythm = ""
                st.rerun()

        if st.session_state.audio_analyzed:
            st.success("✅ **¡Canción analizada con éxito!**")
            st.markdown(f"""
            * **Tempo:** `{st.session_state.tempo_bpm:.1f} BPM` (*Ritmo: {st.session_state.rhythm}*)
            * **RMS Energy:** `{st.session_state.rms_energy:.3f}` (*Nivel: {st.session_state.energy_level}*)
            * **Spectral Centroid:** `{st.session_state.spectral_centroid:.1f} Hz`
            * **Zero Crossing Rate:** `{st.session_state.zcr:.3f}`
            """)

st.markdown("---")

# Botón principal para procesar y enviar la salida física
if st.button("✨ Generar Ambiente y Actualizar Habitación", type="primary", use_container_width=True):
    if not user_text and not st.session_state.audio_analyzed:
        st.warning("⚠️ Por favor ingresa tu estado de ánimo en texto y graba/analiza la canción con el micrófono.")
    else:
        # 1. Análisis de sentimiento del texto (TextBlob)
        analysis = TextBlob(user_text if user_text else "neutral")
        polarity = analysis.sentiment.polarity

        # Valores por defecto
        r, g, b = 0, 206, 209
        brightness = 180
        mood_label = "Balance y Armonía"

        # 2. Aplicación de las reglas de iluminación basadas en Energía + Ritmo (y texto)
        energy_lvl = st.session_state.energy_level
        rhythm_lvl = st.session_state.rhythm

        if energy_lvl == "Baja" and rhythm_lvl == "Lento":
            # Luz azul o violeta, con intensidad baja
            r, g, b = 138, 43, 226
            brightness = 90
            mood_label = "Calma Profunda / Relajación"
        elif energy_lvl == "Media" and rhythm_lvl == "Moderado":
            # Luz amarilla o cálida
            r, g, b = 255, 215, 0
            brightness = 180
            mood_label = "Enfoque / Calidez Moderada"
        elif energy_lvl == "Alta" and rhythm_lvl == "Rápido":
            # Luz naranja o roja, con intensidad alta
            r, g, b = 255, 69, 0
            brightness = 255
            mood_label = "Energía Alta / Dinamismo"
        else:
            # Regla de respaldo o mixta según polaridad del texto
            if polarity < -0.1:
                r, g, b = 70, 130, 180
                brightness = 120
                mood_label = "Refugio Tranquilo"
            elif polarity > 0.2:
                r, g, b = 255, 140, 0
                brightness = 220
                mood_label = "Optimismo Activo"

        st.success(f"🎯 **Ambiente Generado:** {mood_label} | **Energía:** {energy_lvl} | **Ritmo:** {rhythm_lvl}")

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

        # 3. Envío de la señal MQTT a Wokwi
        try:
            client1 = paho.Client("KromaStreamlitClient")
            client1.on_publish = on_publish
            client1.connect(broker, port)
            payload = json.dumps({"r": int(r), "g": int(g), "b": int(b), "brightness": int(brightness)})
            client1.publish(topic, payload)
            client1.disconnect()
            st.success(f"🚀 **¡Señal enviada vía MQTT al tópico `{topic}`!** Wokwi ha actualizado la tira LED.")
        except Exception as e:
            st.error(f"Error al enviar MQTT: {e}")
