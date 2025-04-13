import os
import logging
import json
import asyncio
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
import openai
from gtts import gTTS

# Configuración básica y variables de entorno
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VOICE_MODE = os.getenv("VOICE_MODE", "off") == "on"
openai.api_key = OPENAI_API_KEY

logging.basicConfig(level=logging.INFO)

# Inicializar Flask
app = Flask(__name__)

# Función para transcribir audio usando la API de Whisper de OpenAI
def transcribe_voice(file_path):
    with open(file_path, "rb") as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
        return transcript["text"]

# Función para procesar texto usando GPT-3.5
def procesar_texto(texto):
    respuesta = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": texto}]
    )
    return respuesta.choices[0].message.content.strip()

# Función para generar audio con gTTS (si VOICE_MODE está activado)
def generar_audio(texto, output_path="respuesta.mp3"):
    tts = gTTS(text=texto, lang='es', tld='es')
    tts.save(output_path)
    return output_path

# Manejador de mensajes de voz
async def manejar_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        file_path = "/tmp/audio.ogg"
        await file.download_to_drive(file_path)
        logging.info("Archivo descargado en: " + file_path)
        
        # Transcribir y procesar el audio
        texto = transcribe_voice(file_path)
        logging.info("Transcripción: " + texto)
        respuesta = procesar_texto(texto)
        logging.info("Respuesta IA: " + respuesta)
        
        if VOICE_MODE:
            audio_path = generar_audio(respuesta)
            await update.message.reply_voice(voice=open(audio_path, "rb"))
        else:
            await update.message.reply_text(respuesta)
    except Exception as e:
        logging.error("Error en manejar_audio: " + str(e))
        await update.message.reply_text("Lo siento, ocurrió un error al procesar tu mensaje.")

# Manejador del comando /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Se ejecutó /start correctamente.")
    await update.message.reply_text("¡Hola! Soy tu nuevo bot.")

# Inicializar la aplicación de Telegram (usando python-telegram-bot v20)
application = Application.builder().token(TOKEN).build()
application.add_handler(MessageHandler(filters.VOICE, manejar_audio))
application.add_handler(CommandHandler("start", start_command))

# Ruta del webhook en Flask
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data(as_text=True)
        update_dict = json.loads(json_str)
        update_obj = Update.de_json(update_dict, Bot(TOKEN))
        application.process_update(update_obj)
        return "OK", 200
    except Exception as e:
        logging.error("Error en webhook: " + str(e))
        return "Error", 500

# Función para configurar el webhook en Telegram de forma asíncrona
async def set_webhook_async():
    bot = Bot(TOKEN)
    # Construimos la URL del webhook usando la variable RENDER_URL
    webhook_url = f"https://{os.getenv('RENDER_URL')}/webhook"
    await bot.set_webhook(webhook_url)
    logging.info("Webhook configurado: " + webhook_url)

if __name__ == "__main__":
    # Configurar el webhook
    asyncio.run(set_webhook_async())
    # Iniciar el servidor Flask (Render inyecta la variable PORT o se usa 8080 por defecto)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

