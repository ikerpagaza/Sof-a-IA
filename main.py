import os
import logging
from telegram import Update, Voice
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import openai
import requests
from gtts import gTTS

# Configuración básica
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VOICE_MODE = os.getenv("VOICE_MODE", "off") == "on"
openai.api_key = OPENAI_API_KEY

logging.basicConfig(level=logging.INFO)

# Función para transcribir audio usando Whisper API
def transcribe_voice(file_path):
    with open(file_path, "rb") as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
        return transcript["text"]

# Función para procesar texto con IA
def procesar_texto(texto):
    respuesta = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": texto}]
    )
    return respuesta.choices[0].message.content.strip()

# Función para generar audio con gTTS
def generar_audio(texto, output_path="respuesta.mp3"):
    tts = gTTS(text=texto, lang='es', tld='es')
    tts.save(output_path)
    return output_path

# Manejador de mensajes de voz
async def manejar_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice: Voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    file_path = "/tmp/audio.ogg"
    await file.download_to_drive(file_path)

    # Convertir ogg a mp3 para Whisper
    from pydub import AudioSegment
    mp3_path = "/tmp/audio.mp3"
    AudioSegment.from_ogg(file_path).export(mp3_path, format="mp3")

    texto = transcribe_voice(mp3_path)
    respuesta = procesar_texto(texto)

    if VOICE_MODE:
        audio_path = generar_audio(respuesta)
        await update.message.reply_voice(voice=open(audio_path, "rb"))
    else:
        await update.message.reply_text(respuesta)

# Inicialización del bot
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.VOICE, manejar_audio))
    print("Sofía IA está escuchando...")
    app.run_polling()
