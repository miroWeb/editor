import asyncio
import json
import os
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
from mutagen.id3 import ID3, TPE1, APIC, ID3NoHeaderError

logging.basicConfig(level=logging.INFO)

# ============================================================
# 1) TOKEN: agar server (Railway) BOT_TOKEN environment variable
#    orqali bersa o'shani oladi, aks holda pastdagi qatordan oladi
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8874018629:AAFZs1wFtnVAb7hIdHi80eMZufptvsA0RHw")

# channels.json faylidan 6 ta kanal ma'lumotini o'qiydi
with open("channels.json", "r", encoding="utf-8") as f:
    CHANNELS = json.load(f)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Har bir user qaysi faylni yuborganini vaqtincha shu yerda saqlaymiz
pending_files = {}

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def build_keyboard():
    """channels.json dagi har bir kanal uchun bitta tugma yasaydi"""
    buttons = []
    for key, data in CHANNELS.items():
        buttons.append(
            [InlineKeyboardButton(text=data["button_name"], callback_data=f"channel:{key}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer(
        "Salom! Menga musiqa (audio) fayl yuboring, keyin qaysi kanal uchun "
        "tayyorlab berishimni so'rayman."
    )


@dp.message(F.audio)
async def audio_handler(message: Message):
    """Foydalanuvchi musiqa yuborganda ishga tushadi"""
    file_id = message.audio.file_id
    file_name = message.audio.file_name or f"{file_id}.mp3"

    local_path = os.path.join(DOWNLOAD_DIR, f"{message.from_user.id}_{file_name}")

    tg_file = await bot.get_file(file_id)
    await bot.download_file(tg_file.file_path, destination=local_path)

    # Shu foydalanuvchi uchun faylni "kutish ro'yxati"ga qo'shamiz
    pending_files[message.from_user.id] = local_path

    await message.answer("Qaysi kanal uchun tayyorlab beray? 👇", reply_markup=build_keyboard())


@dp.callback_query(F.data.startswith("channel:"))
async def channel_chosen(callback: CallbackQuery):
    """Foydalanuvchi kanal tugmasini bosganda ishga tushadi"""
    user_id = callback.from_user.id
    channel_key = callback.data.split(":", 1)[1]

    if user_id not in pending_files:
        await callback.answer("Avval musiqa fayl yuboring.", show_alert=True)
        return

    local_path = pending_files.pop(user_id)
    channel = CHANNELS[channel_key]

    # ID3 teglarni o'qiymiz (agar bo'lmasa, yangisini yaratamiz)
    try:
        audio = ID3(local_path)
    except ID3NoHeaderError:
        audio = ID3()

    # Artist maydoniga kanal nomini yozamiz
    audio.setall("TPE1", [TPE1(encoding=3, text=[channel["artist"]])])

    # Agar rasm fayli mavjud bo'lsa, cover sifatida qo'shamiz
    photo_path = channel.get("photo")
    if photo_path and os.path.exists(photo_path):
        with open(photo_path, "rb") as img:
            audio.setall(
                "APIC",
                [APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=img.read())],
            )

    audio.save(local_path, v2_version=3)

    result_file = FSInputFile(local_path)

    # Rasmni ID3 tegga yozish bilan bir qatorda, Telegramga "thumbnail"
    # sifatida ham alohida yuboramiz - shunda rasm doim ko'rinadi
    thumb_file = None
    if photo_path and os.path.exists(photo_path):
        thumb_file = FSInputFile(photo_path)

    await callback.message.answer_audio(
        result_file,
        performer=channel["artist"],
        thumbnail=thumb_file,
    )
    await callback.answer("Tayyor! ✅")

    os.remove(local_path)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())