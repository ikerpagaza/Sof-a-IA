import os
import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
import openai
from gtts import gTTS

# Configuración básica
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VOICE_MODE = os.getenv("VOICE_MODE", "off") == "on"
openai.api_key = OPENAI_API_KEY

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

# Función para responder a mensajes de texto (comando /start)
def send_welcome(update, context):
    chat_id = update.message.chat_id
    context.bot.send_message(chat_id=chat_id, text="¡Hola! Soy Sofía, tu asistente de IA.")

# Manejador de mensajes de voz
async def manejar_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    file_path = "/tmp/audio.ogg"
    await file.download_to_drive(file_path)

    # Transcribir el audio directamente con Whisper
    texto = transcribe_voice(file_path)
    respuesta = procesar_texto(texto)

    if VOICE_MODE:
        audio_path = generar_audio(respuesta)
        await update.message.reply_voice(voice=open(audio_path, "rb"))
    else:
        await update.message.reply_text(respuesta)

# Ruta para manejar el webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == "POST":
        json_str = request.get_data(as_text=True)
        update = Update.de_json(json_str, Bot(TOKEN))
        application.process_update(update)
        return "OK"

# Inicializar la aplicación de Telegram
application = ApplicationBuilder().token(TOKEN).build()
dispatcher = application.dispatcher

# Agregar el comando /start
dispatcher.add_handler(CommandHandler("start", send_welcome))

# Agregar el manejador de voz
dispatcher.add_handler(MessageHandler(filters.VOICE, manejar_audio))

# Configurar el webhook
def set_webhook():
    bot = Bot(TOKEN)
    url = f"https://{os.getenv('RENDER_URL')}/webhook"  # Usar la URL pública de Render
    bot.set_webhook(url)

# Ejecutar Flask y el bot
if __name__ == "__main__":
    set_webhook()  # Configurar el webhook con Telegram
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))  # Flask servidor
