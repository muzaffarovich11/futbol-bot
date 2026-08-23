import os
import asyncio
import requests
import json
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from deep_translator import GoogleTranslator
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE = os.getenv("SOURCE_CHANNEL")
TARGET = os.getenv("TARGET_CHANNEL")

client = TelegramClient("session_name", API_ID, API_HASH)
translator = GoogleTranslator(source="en", target="uz")

def translate_text(text: str) -> str:
    if not text or not text.strip():
        return ""
    try:
        return translator.translate(text)
    except Exception as e:
        print("Translation error:", e)
        return text

def send_text(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TARGET,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    requests.post(url, data=data)

def send_photo(file_path: str, caption: str = ""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(file_path, "rb") as f:
        files = {"photo": f}
        data = {
            "chat_id": TARGET,
            "caption": caption,
            "parse_mode": "HTML"
        }
        requests.post(url, data=data, files=files)

def send_video(file_path: str, caption: str = ""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    with open(file_path, "rb") as f:
        files = {"video": f}
        data = {
            "chat_id": TARGET,
            "caption": caption,
            "parse_mode": "HTML",
            "supports_streaming": True
        }
        requests.post(url, data=data, files=files)

def send_media_group(media_list: list, caption: str = ""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMediaGroup"
    media = []
    files = {}

    for i, (path, is_video) in enumerate(media_list):
        file_key = f"file{i}"
        media_type = "video" if is_video else "photo"
        item = {
            "type": media_type,
            "media": f"attach://{file_key}"
        }
        if i == 0 and caption:
            item["caption"] = caption
            item["parse_mode"] = "HTML"
        media.append(item)
        files[file_key] = open(path, "rb")

    response = requests.post(
        url,
        data={"chat_id": TARGET, "media": json.dumps(media)},
        files=files
    )

    for f in files.values():
        f.close()

    for path, _ in media_list:
        try:
            os.remove(path)
        except:
            pass

    return response

@client.on(events.NewMessage(chats=SOURCE))
async def handler(event):
    message = event.message

    if message.grouped_id:
        return

    original_caption = message.text or message.message or ""
    translated = translate_text(original_caption)
    final_caption = f"{translated}\n\n———\nManba: @{SOURCE}" if translated else f"———\nManba: @{SOURCE}"

    if not message.media:
        send_text(final_caption)
        print("Posted text")
        return

    if isinstance(message.media, MessageMediaPhoto):
        path = await message.download_media()
        send_photo(path, final_caption)
        os.remove(path)
        print("Posted single photo")
        return

    if isinstance(message.media, MessageMediaDocument):
        mime = getattr(message.media.document, "mime_type", "") or ""
        if mime.startswith("video/"):
            path = await message.download_media()
            send_video(path, final_caption)
            os.remove(path)
            print("Posted single video")
            return
        else:
            print("Skipped unsupported media")
            return

@client.on(events.Album(chats=SOURCE))
async def album_handler(event):
    messages = event.messages

    original_caption = ""
    for msg in messages:
        if msg.text or msg.message:
            original_caption = msg.text or msg.message
            break

    translated = translate_text(original_caption)
    final_caption = f"{translated}\n\n———\nManba: @{SOURCE}" if translated else f"———\nManba: @{SOURCE}"

    media_list = []

    for msg in messages:
        if isinstance(msg.media, MessageMediaPhoto):
            path = await msg.download_media()
            media_list.append((path, False))
        elif isinstance(msg.media, MessageMediaDocument):
            mime = getattr(msg.media.document, "mime_type", "") or ""
            if mime.startswith("video/"):
                path = await msg.download_media()
                media_list.append((path, True))

    if media_list:
        send_media_group(media_list, final_caption)
        print(f"Posted album with {len(media_list)} items")
    else:
        print("Album had no supported media")

async def main():
    print("Bot started... Listening to @" + SOURCE)
    await client.start(bot_token="7956754958:AAHRhXnkuVEJWd-6fsS5qkfAaaLMvUh_1NY")
    print("Successfully connected!")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
