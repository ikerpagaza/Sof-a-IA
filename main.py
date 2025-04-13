import os
import logging
import json
import asyncio
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
import openai
from gtts import gTTS

# Configuración básica
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VOICE_MODE = os.getenv("VOICE_MODE", "off") == "on"
openai.api_key = OPENAI_API_KEY

logging.basicConfig(level=logging.INFO)

# Configuración de Flask
app = Flask(__name__)

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
    try:
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        file_path = "/tmp/audio.ogg"
        await file.download_to_drive(file_path)
        logging.info(f"Archivo descargado en {file_path}")

        # Transcribir el audio directamente con Whisper
        texto = transcribe_voice(file_path)
        logging.info(f"Transcripción: {texto}")
        respuesta = procesar_texto(texto)
        logging.info(f"Respuesta IA: {respuesta}")

        if VOICE_MODE:
            audio_path = generar_audio(respuesta)
            await update.message.reply_voice(voice=open(audio_path, "rb"))
        else:
            await update.message.reply_text(respuesta)
    except Exception as e:
        logging.error(f"Error en manejar_audio: {e}")
        await update.message.reply_text("Lo siento, ocurrió un error al procesar tu mensaje.")

# Manejador del comando /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Se ejecutó /start correctamente.")
    await update.message.reply_text("¡Hola! Soy tu nuevo bot.")

# Inicializar la aplicación de Telegram
application = Application.builder().token(TOKEN).build()
application.add_handler(MessageHandler(filters.VOICE, manejar_audio))
application.add_handler(CommandHandler("start", start_command))

# Ruta para manejar el webhook de Telegram
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data(as_text=True)
        update_dict = json.loads(json_str)
        update = Update.de_json(update_dict, Bot(TOKEN))
        application.process_update(update)
        return "OK", 200
    except Exception as e:
        logging.error(f"Error en webhook: {e}")
        return "Error", 500




# Función para configurar el webhook en Telegram de forma asíncrona
async def set_webhook_async():
    bot = Bot(TOKEN)
    # Aquí usamos la variable de entorno RENDER_URL o directamente la URL si prefieres:
    url = f"https://{os.getenv('RENDER_URL')}/webhook"
    await bot.set_webhook(url)
    logging.info("Webhook configurado de forma asíncrona.")

if __name__ == "__main__":
    # Configuramos el webhook automáticamente
    asyncio.run(set_webhook_async())
    # Ejecutar el servidor Flask (Render inyecta la variable PORT)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))


