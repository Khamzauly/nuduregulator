from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from datetime import datetime
from telegram import InputFile
import json
import os

json_str = os.getenv("LINK")
{"web":{"client_id":"73898426089-3lfiu34v8g4o3lda3r51qonm6mj0hpnr.apps.googleusercontent.com","project_id":"nudu-398911","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_secret":"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"}}


scopes = ['https://www.googleapis.com/auth/spreadsheets']
google_credentials = json.loads(json_str)
credentials = Credentials.from_service_account_info(google_credentials, scopes=scopes)
service = build('sheets', 'v4', credentials=credentials)
sheet = service.spreadsheets()



zone_photos = {}
photo_zones = ["зоны 1", "зоны 2", "зоны 3"]
current_photo_zone = None

# Функция, которая проверяет, все ли задачи выполнены
def all_tasks_done():
    tasks = get_tasks()
    for task in tasks:
        if len(task) < 2 or task[1] != "TRUE":
            return False
    return True


# Функция для получения задач
def get_tasks():
    result = sheet.values().get(spreadsheetId="1xjphW6Zlc3Hx73h2pTmFgDLeR4-MhVw2xITgjIOLN4w", range="asd!A2:D29").execute()
    return result.get('values', [])

# Функция для обновления задач
def update_task(row, user_name):
    sheet.values().update(
        spreadsheetId="1xjphW6Zlc3Hx73h2pTmFgDLeR4-MhVw2xITgjIOLN4w",
        range=f"asd!B{row}:D{row}",
        body={"values": [[True, user_name, str(datetime.now())]]},
        valueInputOption="RAW"
    ).execute()

# Обработчик команды /start
def start(update: Update, context: CallbackContext):
    keyboard = []
    tasks = get_tasks()
    if tasks:
        for i, task in enumerate(tasks):
            if len(task) > 1:  # Проверка наличия элемента с индексом 1
                status = "✅" if task[1] == "TRUE" else "❌"
                keyboard.append([InlineKeyboardButton(f"{task[0]} {status}", callback_data=str(i))])
            else:
                # Случай, когда у нас недостаточно данных в списке task
                keyboard.append([InlineKeyboardButton(f"{task[0]} ❓", callback_data=str(i))])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text('Выберите задачу:', reply_markup=reply_markup)
    else:
        update.message.reply_text('Задачи не найдены.')


def ask_for_photo(chat_id, context, zone):
    global current_photo_zone
    current_photo_zone = zone
    context.bot.send_message(chat_id=chat_id, text=f"Отправьте фотографию {zone}")

def photo(update: Update, context: CallbackContext):
    global current_photo_zone
    user_id = update.effective_user.id
    if not current_photo_zone:
        return  # Если нет текущей зоны для фото, просто игнорируем

    photo_file = context.bot.getFile(update.message.photo[-1].file_id)
    zone_photos[current_photo_zone] = photo_file.file_path

    # Если это последняя фотография
    if current_photo_zone == photo_zones[-1]:
        send_photos_to_other_bot(zone_photos)
        current_photo_zone = None
    else:
        next_zone = photo_zones[photo_zones.index(current_photo_zone) + 1]
        ask_for_photo(update.effective_chat.id, context, next_zone)

def send_photos_to_other_bot(photos):
    BOT2_TOKEN = "SECOND_BOT"
    CHAT_ID = "CHAT_ID"
    bot2 = Bot(BOT2_TOKEN)

    for zone, photo_url in photos.items():
        bot2.send_photo(chat_id=CHAT_ID, photo=open(photo_url, 'rb'), caption=f"Фото {zone}")

# Обработчик кнопок
def button(update: Update, context: CallbackContext):
    query = update.callback_query
    task_index = int(query.data)
    tasks = get_tasks()
    user_name = update.effective_user.first_name
    
    # Обновление данных в Google Sheets
    update_task(task_index + 2, user_name)
    
    # Создаем новую клавиатуру с обновленными задачами
    new_keyboard = []
    tasks = get_tasks()
    if tasks:
        for i, task in enumerate(tasks):
            if len(task) > 1:
                status = "✅" if task[1] == "TRUE" else "❌"
                new_keyboard.append([InlineKeyboardButton(f"{task[0]} {status}", callback_data=str(i))])
    
    reply_markup = InlineKeyboardMarkup(new_keyboard)

    # Обновляем клавиатуру в сообщении
    query.edit_message_reply_markup(reply_markup=reply_markup)
    
    if all_tasks_done():
        context.bot.send_message(chat_id=update.effective_chat.id, text="Уборка закончена. Спасибо!")
        ask_for_photo(update.effective_chat.id, context, photo_zones[0])


TOKEN = os.getenv("TOKEN")
# Основной код
updater = Updater(TOKEN)

dp = updater.dispatcher

dp.add_handler(CommandHandler("start", start))
dp.add_handler(CallbackQueryHandler(button))
dp.add_handler(MessageHandler(Filters.photo, photo))

updater.start_polling()
updater.idle()

