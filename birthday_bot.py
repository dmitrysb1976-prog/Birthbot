import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import asyncio
from telegram import Bot
import logging
import os
import json  # добавили для парсинга JSON из переменной окружения

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = "8373441354:AAGFRXqeet3CmeX0yA7U-fL1Ta_Yjg5D9xo"
CHANNEL_ID = "@testNewTerritory"
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1ldoSSLZKb7nEXb5pKSH90PT3IgKMNc9Rj9JjfAUz0JU/edit?usp=sharing"

# Получаем credentials из переменных окружения
CREDENTIALS_JSON = os.getenv('GOOGLE_CREDENTIALS')

if not CREDENTIALS_JSON:
    logger.critical("Переменная окружения GOOGLE_CREDENTIALS не установлена!")
    raise SystemExit("Нет данных для подключения к Google Sheets")

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

async def init_google_sheets():
    try:
        # Исправлено: используем json.loads вместо eval
        creds_dict = json.loads(CREDENTIALS_JSON)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(GOOGLE_SHEET_URL).sheet1
        logger.info("Успешное подключение к Google Sheets")
        return sheet
    except Exception as e:
        logger.error(f"Ошибка подключения к Google Sheets: {str(e)}")
        raise

bot = Bot(token=TELEGRAM_TOKEN)

async def check_birthdays(sheet):
    try:
        today_str = datetime.now().strftime("%d.%m")
        logger.info(f"Проверяем дни рождения на дату: {today_str}")
        
        data = sheet.get_all_values()
        birthday_people = []

        for row in data[1:]:
            try:
                if len(row) >= 2:
                    name = row[0].strip()
                    date_cell = row[1].strip()
                    parsed_date = None

                    if date_cell.replace(".", "", 1).isdigit():
                        try:
                            serial_number = float(date_cell)
                            parsed_date = datetime(1899, 12, 30) + timedelta(days=serial_number)
                        except Exception as e:
                            logger.warning(f"Ошибка парсинга даты {date_cell}: {str(e)}")
                    else:
                        for fmt in ("%d.%m", "%d.%m.%Y", "%Y-%m-%d", "%m/%d/%Y"):
                            try:
                                parsed_date = datetime.strptime(date_cell, fmt)
                                break
                            except ValueError:
                                continue

                    if not parsed_date:
                        continue

                    if parsed_date.strftime("%d.%m") == today_str:
                        birthday_people.append(name)
                        logger.info(f"Найден день рождения: {name}")

            except Exception as e:
                logger.error(f"Ошибка обработки строки {row}: {str(e)}")
                continue

        if birthday_people:
            if len(birthday_people) > 1:
                names_str = ", ".join(birthday_people)
                message = f"Наши именинники сегодня: {names_str} - поздравляем с Днем Рождения!!! ❤️"
            else:
                message = f"Наши именинники сегодня: {birthday_people[0]} - поздравляем с Днем Рождения!!! ❤️"

            await bot.send_message(chat_id=CHANNEL_ID, text=message)
            logger.info(f"Отправлено сообщение: {message}")
        else:
            logger.info("Сегодня дней рождений нет")

    except Exception as e:
        logger.error(f"Критическая ошибка в check_birthdays: {str(e)}")
        raise

async def main():
    logger.info("Запуск бота...")
    try:
        sheet = await init_google_sheets()
        logger.info("Бот успешно запущен. Начинаем ежедневные проверки.")
        
        while True:
            try:
                await check_birthdays(sheet)
                logger.info("Проверка завершена. Жду 24 часа до следующей проверки...")
                await asyncio.sleep(24 * 60 * 60)  # спим сутки
            except Exception as e:
                logger.error(f"Ошибка в основном цикле: {str(e)}")
                logger.info("Повторная попытка через 1 час...")
                await asyncio.sleep(3600)  # ждем 1 час при ошибке
                
    except Exception as e:
        logger.critical(f"Фатальная ошибка: {str(e)}. Бот остановлен.")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную")
    except Exception as e:
        logger.critical(f"Необработанное исключение: {str(e)}")


