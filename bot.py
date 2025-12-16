import requests
import time
import os
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import telebot

# ================== НАСТРОЙКИ ==================

BASE = "https://www.allkpop.com"
LIST_URL = "https://www.allkpop.com/category/news"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# Telegram
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Несколько получателей
CHAT_IDS = [
    "215269880",
    "362321284",
    "6544503730"
]

CHECK_INTERVAL = 60 * 30 * 1  # 4 часа
MAX_ARTICLES = 10            # Только первые 10 новостей

SENT_FILE = "sent.txt"

# ===============================================

bot = telebot.TeleBot(BOT_TOKEN)

# ---------- Работа с отправленными новостями ----------

def load_sent():
    if not os.path.exists(SENT_FILE):
        return set()
    with open(SENT_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_sent(links):
    with open(SENT_FILE, "a", encoding="utf-8") as f:
        for link in links:
            f.write(link + "\n")

# ---------- Перевод ----------

def translate_to_ru(text):
    translator = GoogleTranslator(source="en", target="ru")
    max_len = 4500
    parts = []

    for i in range(0, len(text), max_len):
        chunk = text[i:i + max_len]
        translated = translator.translate(chunk)
        parts.append(translated)

    return "\n".join(parts)

# ---------- Основная логика ----------

def check_news():
    sent_links = load_sent()
    new_sent = set()

    response = requests.get(LIST_URL, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(response.text, "html.parser")

    articles = soup.select("a[href^='/article/']")[:MAX_ARTICLES]

    if not articles:
        print("❌ Новости не найдены")
        return

    for article in articles:
        link = BASE + article["href"]

        if link in sent_links or link in new_sent:
            continue

        print(f"🆕 Новая новость: {link}")

        article_response = requests.get(link, headers=HEADERS, timeout=15)
        article_soup = BeautifulSoup(article_response.text, "html.parser")

        # Заголовок
        title_tag = article_soup.select_one("h1#article-title")
        title = title_tag.get_text(strip=True) if title_tag else "Без заголовка"

        # Контент
        content_block = article_soup.select_one("#article-content .entry_content")
        if not content_block:
            print("⚠️ Контент не найден")
            continue

        paragraphs = content_block.find_all("p")
        text_parts = []

        for p in paragraphs:
            txt = p.get_text(" ", strip=True)
            if not txt:
                continue
            if txt.upper().startswith("SEE ALSO"):
                continue
            text_parts.append(txt)

        full_text = "\n\n".join(text_parts)
        if not full_text:
            print("⚠️ Пустой текст")
            continue

        # Перевод
        ru_text = translate_to_ru(full_text)

        message = (
            f"📰 <b>{title}</b>\n\n"
            f"{ru_text}\n\n"
            f"🔗 <a href='{link}'>Источник</a>"
        )

        for chat_id in CHAT_IDS:
            bot.send_message(
                chat_id,
                message,
                parse_mode="HTML",
                disable_web_page_preview=True
            )

        new_sent.add(link)
        print(f"✅ Отправлено: {title}")

        time.sleep(10)

    if new_sent:
        save_sent(new_sent)

# ---------- ЗАПУСК ----------

if __name__ == "__main__":
    print("🤖 Allkpop bot запущен (Railway)")

    while True:
        try:
            print("🔄 Проверка новостей...")
            check_news()
            print("⏳ Ожидание 4 часа...\n")
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print("❌ Ошибка:", e)
            time.sleep(300)