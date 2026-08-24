import asyncio
import json
import os
import logging
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from mutagen.id3 import ID3, TPE1, TIT2, APIC, ID3NoHeaderError

logging.basicConfig(level=logging.INFO)

# ============================================================
# TOKEN: Railway'da BOT_TOKEN environment variable orqali beriladi
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8874018629:AAFZs1wFtnVAb7hIdHi80eMZufptvsA0RHw")

# ============================================================
# OBUNA SOZLAMALARI
# ============================================================
FREE_LIMIT = 15  # bepul tayyorlab beriladigan mp3 soni
SUBSCRIPTION_DAYS = 30
SUBSCRIPTION_PRICE_TEXT = "39 000 so'm"

# Karta raqami - Railway'da CARD_NUMBER environment variable orqali bering
CARD_NUMBER = os.environ.get("CARD_NUMBER", "5614 6865 0476 3734 (XAKIMOV MIRODIL)")

# Admin username (@siz) - Railway'da ADMIN_USERNAME orqali bering (@ belgisisiz)
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "miro_lv")

# Adminning Telegram user ID raqami - /confirm buyrug'ini faqat shu odam ishlata oladi
# Railway'da ADMIN_ID environment variable orqali bering
ADMIN_ID = int(os.environ.get("ADMIN_ID", "780886251"))

# ============================================================
# MA'LUMOTLARNI SAQLASH JOYI
# Railway'da bu doim /data bo'lishi kerak (Volume ulanganda),
# lokal kompyuterda esa joriy papka (".") yetarli.
# ============================================================
DATA_DIR = os.environ.get("DATA_DIR", ".")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
PHOTOS_DIR = os.path.join(DATA_DIR, "user_photos")
DOWNLOAD_DIR = os.path.join(DATA_DIR, "downloads")

os.makedirs(PHOTOS_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

MAX_CHANNELS_PER_USER = 10

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Kim qaysi audio faylni yubordi - shu yerda vaqtincha saqlanadi
pending_files = {}


# ------------------------------------------------------------
# Foydalanuvchilar ma'lumotini o'qish / yozish
# ------------------------------------------------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_users(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user_channels(user_id: int):
    data = load_users()
    return data.get(str(user_id), {}).get("channels", {})


def add_user_channel(user_id: int, key: str, name: str, photo_path: str):
    data = load_users()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"channels": {}}
    data[uid]["channels"][key] = {"name": name, "photo": photo_path}
    save_users(data)


def delete_user_channel(user_id: int, key: str):
    data = load_users()
    uid = str(user_id)
    if uid in data and key in data[uid]["channels"]:
        del data[uid]["channels"][key]
        save_users(data)


# ------------------------------------------------------------
# Obuna va limit bilan ishlash
# ------------------------------------------------------------
def get_user_record(user_id: int):
    data = load_users()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"channels": {}}
    record = data[uid]
    record.setdefault("free_used", 0)
    record.setdefault("subscribed_until", None)
    return data, record


def is_subscribed(user_id: int) -> bool:
    _, record = get_user_record(user_id)
    until = record.get("subscribed_until")
    if not until:
        return False
    return datetime.fromisoformat(until) > datetime.now()


def has_access(user_id: int) -> bool:
    if is_subscribed(user_id):
        return True
    _, record = get_user_record(user_id)
    return record.get("free_used", 0) < FREE_LIMIT


def register_free_use(user_id: int):
    if is_subscribed(user_id):
        return  # obuna faol bo'lsa, bepul limitni sarflamaymiz
    data, record = get_user_record(user_id)
    record["free_used"] = record.get("free_used", 0) + 1
    data[str(user_id)] = record
    save_users(data)


def grant_subscription(user_id: int, days: int = SUBSCRIPTION_DAYS):
    data, record = get_user_record(user_id)
    now = datetime.now()
    current_until = record.get("subscribed_until")
    start = now
    if current_until:
        current_dt = datetime.fromisoformat(current_until)
        if current_dt > now:
            start = current_dt  # hali tugamagan bo'lsa, ustiga qo'shamiz
    new_until = start + timedelta(days=days)
    record["subscribed_until"] = new_until.isoformat()
    data[str(user_id)] = record
    save_users(data)
    return new_until


def subscribe_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Click", callback_data="pay:click")],
            [InlineKeyboardButton(text="💳 Payme", callback_data="pay:payme")],
            [InlineKeyboardButton(text="👤 Admin bilan bog'lanish", callback_data="pay:admin")],
        ]
    )


# ------------------------------------------------------------
# Kanal qo'shish jarayoni (FSM - bosqichma-bosqich savol-javob)
# ------------------------------------------------------------
class AddChannel(StatesGroup):
    waiting_name = State()
    waiting_photo = State()


def main_menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="add_channel")],
            [InlineKeyboardButton(text="📋 Kanallarim", callback_data="list_channels")],
        ]
    )


@dp.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Salom! Bu bot musiqa fayllarga siz belgilagan kanal nomi va rasmini avtomatik qo'yib beradi.\n\n"
        "Avval kamida bitta kanal qo'shing, keyin menga musiqa yuboraverasiz.",
        reply_markup=main_menu_keyboard(),
    )


@dp.callback_query(F.data == "add_channel")
async def add_channel_start(callback: CallbackQuery, state: FSMContext):
    channels = get_user_channels(callback.from_user.id)
    if len(channels) >= MAX_CHANNELS_PER_USER:
        await callback.answer(f"Ko'pi bilan {MAX_CHANNELS_PER_USER} ta kanal qo'sha olasiz.", show_alert=True)
        return

    await state.set_state(AddChannel.waiting_name)
    await callback.message.answer(
        "Kanal nomini yozing (bu nom ham tugma sifatida, ham musiqaning artist maydonida ishlatiladi).\n"
        "Masalan: DNRSN"
    )
    await callback.answer()


@dp.message(AddChannel.waiting_name)
async def add_channel_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("Iltimos, matn ko'rinishida nom yuboring.")
        return

    await state.update_data(name=name)
    await state.set_state(AddChannel.waiting_photo)
    await message.answer("Endi shu kanal uchun rasm (logo) yuboring.")


@dp.message(AddChannel.waiting_photo, F.photo)
async def add_channel_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    user_id = message.from_user.id

    channels = get_user_channels(user_id)
    key = f"kanal_{len(channels) + 1}_{message.message_id}"

    photo = message.photo[-1]  # eng katta o'lchamdagi rasm
    file = await bot.get_file(photo.file_id)
    photo_path = os.path.join(PHOTOS_DIR, f"{user_id}_{key}.jpg")
    await bot.download_file(file.file_path, destination=photo_path)

    add_user_channel(user_id, key, name, photo_path)
    await state.clear()

    await message.answer(
        f"✅ \"{name}\" kanali qo'shildi! Endi menga musiqa yuborishingiz mumkin.",
        reply_markup=main_menu_keyboard(),
    )


@dp.message(AddChannel.waiting_photo)
async def add_channel_photo_wrong(message: Message):
    await message.answer("Iltimos, rasm (photo) ko'rinishida yuboring, fayl emas.")


@dp.callback_query(F.data == "list_channels")
async def list_channels(callback: CallbackQuery):
    channels = get_user_channels(callback.from_user.id)
    if not channels:
        await callback.message.answer("Sizda hali kanal yo'q. \"➕ Kanal qo'shish\" orqali qo'shing.")
        await callback.answer()
        return

    buttons = []
    for key, ch in channels.items():
        buttons.append(
            [InlineKeyboardButton(text=f"❌ {ch['name']}", callback_data=f"del:{key}")]
        )
    await callback.message.answer(
        "Kanallaringiz (o'chirish uchun bosing):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("del:"))
async def delete_channel(callback: CallbackQuery):
    key = callback.data.split(":", 1)[1]
    delete_user_channel(callback.from_user.id, key)
    await callback.answer("O'chirildi.")
    await callback.message.edit_text("Kanal o'chirildi. /start orqali qayta ko'ring.")


@dp.callback_query(F.data.startswith("pay:"))
async def payment_chosen(callback: CallbackQuery):
    method = callback.data.split(":", 1)[1]
    user = callback.from_user
    username_part = f"@{user.username}" if user.username else "(username yo'q)"

    method_names = {"click": "Click", "payme": "Payme", "admin": "Admin bilan bog'lanish"}
    method_name = method_names.get(method, method)

    await callback.message.answer(
        f"Obuna narxi: {SUBSCRIPTION_PRICE_TEXT} / {SUBSCRIPTION_DAYS} kun\n\n"
        f"Quyidagi kartaga o'tkazib, screenshot'ni @{ADMIN_USERNAME} ga yuboring:\n"
        f"💳 {CARD_NUMBER}\n\n"
        f"To'lov tasdiqlangach, obunangiz avtomatik faollashadi."
    )
    await callback.answer()

    if ADMIN_ID:
        try:
            await bot.send_message(
                ADMIN_ID,
                f"🔔 To'lov so'rovi\n"
                f"Foydalanuvchi: {username_part} (id: {user.id})\n"
                f"Usul: {method_name}\n\n"
                f"Tasdiqlash uchun: /confirm {user.id}",
            )
        except Exception:
            logging.exception("Adminga xabar yuborib bo'lmadi")


@dp.message(Command("confirm"))
async def confirm_payment(message: Message):
    if message.from_user.id != ADMIN_ID:
        return  # faqat admin ishlata oladi

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("To'g'ri format: /confirm 123456789")
        return

    target_id = int(parts[1])
    new_until = grant_subscription(target_id)

    await message.answer(f"✅ {target_id} uchun obuna {new_until.strftime('%Y-%m-%d')} gacha faollashtirildi.")
    try:
        await bot.send_message(
            target_id,
            f"✅ Obunangiz faollashtirildi! {SUBSCRIPTION_DAYS} kun davomida cheksiz foydalanishingiz mumkin.",
        )
    except Exception:
        logging.exception("Foydalanuvchiga xabar yuborib bo'lmadi")


@dp.message(Command("status"))
async def status_handler(message: Message):
    user_id = message.from_user.id
    _, record = get_user_record(user_id)

    if is_subscribed(user_id):
        until = datetime.fromisoformat(record["subscribed_until"])
        await message.answer(f"✅ Obunangiz faol, {until.strftime('%Y-%m-%d')} gacha.")
    else:
        used = record.get("free_used", 0)
        qolgan = max(FREE_LIMIT - used, 0)
        await message.answer(
            f"Bepul limit: {used}/{FREE_LIMIT} ishlatilgan, {qolgan} ta qoldi.\n"
            f"Obuna: yo'q. {SUBSCRIPTION_PRICE_TEXT} / {SUBSCRIPTION_DAYS} kun uchun /start bosing."
        )


# ------------------------------------------------------------
# Musiqa fayl kelganda
# ------------------------------------------------------------
def build_channel_keyboard(channels: dict):
    buttons = []
    for key, ch in channels.items():
        buttons.append([InlineKeyboardButton(text=ch["name"], callback_data=f"tag:{key}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@dp.message(F.audio)
async def audio_handler(message: Message):
    user_id = message.from_user.id
    channels = get_user_channels(user_id)

    if not channels:
        await message.answer(
            "Sizda hali birorta ham kanal yo'q. Avval \"➕ Kanal qo'shish\" orqali kamida bitta kanal qo'shing.",
            reply_markup=main_menu_keyboard(),
        )
        return

    if not has_access(user_id):
        await message.answer(
            f"Bepul limit ({FREE_LIMIT} ta) tugadi.\n\n"
            f"Obuna: {SUBSCRIPTION_PRICE_TEXT} / {SUBSCRIPTION_DAYS} kun cheksiz foydalanish.\n"
            f"To'lov usulini tanlang:",
            reply_markup=subscribe_keyboard(),
        )
        return

    file_id = message.audio.file_id
    file_name = message.audio.file_name or f"{file_id}.mp3"
    local_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{file_name}")

    tg_file = await bot.get_file(file_id)
    await bot.download_file(tg_file.file_path, destination=local_path)

    pending_files[user_id] = local_path
    await message.answer("Qaysi kanal uchun tayyorlab beray? 👇", reply_markup=build_channel_keyboard(channels))


@dp.callback_query(F.data.startswith("tag:"))
async def channel_chosen(callback: CallbackQuery):
    user_id = callback.from_user.id
    channel_key = callback.data.split(":", 1)[1]

    if user_id not in pending_files:
        await callback.answer("Avval musiqa fayl yuboring.", show_alert=True)
        return

    channels = get_user_channels(user_id)
    channel = channels.get(channel_key)
    if not channel:
        await callback.answer("Bu kanal topilmadi, ehtimol o'chirilgan.", show_alert=True)
        return

    local_path = pending_files.pop(user_id)

    try:
        audio = ID3(local_path)
    except ID3NoHeaderError:
        audio = ID3()

    # Asl sarlavhani (bo'lsa) saqlab qolamiz, keyin BARCHA eski teglarni
    # tozalab, faqat kerakli 3 tasini (sarlavha, artist, rasm) qaytadan
    # yozamiz - shu bilan eski/g'alati teglar aralashib ketmaydi
    original_title = None
    if audio.getall("TIT2"):
        original_title = audio.getall("TIT2")[0].text[0]

    audio.delete(local_path)
    audio = ID3()

    if original_title:
        audio.setall("TIT2", [TIT2(encoding=3, text=[original_title])])

    audio.setall("TPE1", [TPE1(encoding=3, text=[channel["name"]])])

    photo_path = channel.get("photo")
    if photo_path and os.path.exists(photo_path):
        with open(photo_path, "rb") as img:
            audio.setall(
                "APIC",
                [APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=img.read())],
            )

    audio.save(local_path, v1=2, v2_version=3)

    result_file = FSInputFile(local_path)
    thumb_file = FSInputFile(photo_path) if photo_path and os.path.exists(photo_path) else None

    await callback.message.answer_audio(
        result_file,
        performer=channel["name"],
        thumbnail=thumb_file,
    )
    await callback.answer("Tayyor! ✅")

    register_free_use(user_id)
    os.remove(local_path)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())