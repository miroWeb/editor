# Musiqa avto-tag bot — to'liq qo'llanma (boshidan oxirigacha)

Bu papkada 4 ta fayl bor:
- `bot.py` — botning asosiy kodi
- `channels.json` — 6 ta kanalingizning nomi va rasmi shu yerda saqlanadi
- `requirements.txt` — kerakli kutubxonalar ro'yxati
- `photos/` — kanal rasmlarini shu papkaga tashlaysiz

Quyidagi qadamlarni ketma-ket, hech birini o'tkazib yubormasdan bajaring.

---

## 1-QADAM: Python o'rnatish

1. https://www.python.org/downloads/ ga kiring
2. "Download Python 3.12" (yoki eng oxirgi versiya) tugmasini bosing
3. Yuklab olingan faylni ishga tushiring
4. **MUHIM:** o'rnatish oynasining pastida "Add python.exe to PATH" (yoki "Add Python to PATH") degan katakchani albatta belgilang, keyin "Install Now" bosing
5. O'rnatilgach, tekshirish uchun: Windows tugmasi bosing, "cmd" deb yozing, Command Prompt oching va shu yerga yozing:
   ```
   python --version
   ```
   Agar "Python 3.12.x" kabi narsa chiqsa — o'rnatildi, davom etamiz.

## 2-QADAM: Kod muharriri (ixtiyoriy, lekin tavsiya qilinadi)

Siz JavaScript yozgansiz, demak VS Code sizga tanish bo'lishi mumkin:
- https://code.visualstudio.com/ dan yuklab oling va o'rnating
- VS Code ochib, bu `music_tag_bot` papkasini "Open Folder" orqali oching

## 3-QADAM: Telegram botini yaratish (token olish)

1. Telegram'da **@BotFather** ni toping (rasmiy, ko'k belgili)
2. `/newbot` deb yozing
3. Botingizga bir nom bering (masalan: "Mening Music Tag Bot")
4. Keyin bot uchun username so'raydi — oxiri "bot" bilan tugashi kerak (masalan: `mening_music_tag_bot`)
5. BotFather sizga uzun bir **token** beradi, masalan:
   ```
   7123456789:AAHf3kd82jsKal9dksoaJKLxzUw92mska
   ```
   Buni saqlab qo'ying — hech kimga bermang, bu botingizning "paroli".

## 4-QADAM: Faylni sozlash — tokenni joylashtirish

1. `bot.py` faylini oching (VS Code yoki oddiy Notepad bilan)
2. Bu qatorni toping:
   ```python
   BOT_TOKEN = "SIZNING_BOT_TOKENINGIZ_BU_YERGA"
   ```
3. Tirnoq ichidagi matnni BotFather bergan tokeningizga almashtiring:
   ```python
   BOT_TOKEN = "7123456789:AAHf3kd82jsKal9dksoaJKLxzUw92mska"
   ```
4. Faylni saqlang (Ctrl+S)

## 5-QADAM: Kerakli kutubxonalarni o'rnatish

1. Command Prompt (yoki VS Code'dagi Terminal) oching
2. Shu `music_tag_bot` papkasiga o'ting, masalan agar Downloads ichida bo'lsa:
   ```
   cd Downloads\music_tag_bot
   ```
3. Shu buyruqni yozing:
   ```
   pip install -r requirements.txt
   ```
   Bu `aiogram` (Telegram bot kutubxonasi) va `mutagen` (musiqa teglarini o'zgartiruvchi kutubxona) ni o'rnatadi.

## 6-QADAM: Kanallaringizni sozlash (channels.json)

`channels.json` faylini oching. Hozir ichida 6 ta placeholder (vaqtinchalik) kanal bor:

```json
"kanal1": {
    "button_name": "Kanal 1",
    "artist": "Kanal 1 nomi",
    "photo": "photos/kanal1.jpg"
}
```

Har bir kanal uchun 3 ta narsani o'zgartirasiz:
- `button_name` — bot ichida chiqadigan tugma nomi (masalan: "DNRSN")
- `artist` — musiqaga yoziladigan artist/kanal nomi (masalan: "DNRSN")
- `photo` — kanal rasmi joylashgan yo'l (quyidagi qadamga qarang)

**Rasmlarni qo'shish:** har bir kanalning logotipini (jpg yoki png) `photos/` papkasiga tashlang, masalan `photos/dnrsn.jpg`, va `channels.json` da shu yo'lni ko'rsating:
```json
"photo": "photos/dnrsn.jpg"
```

Hoziroq to'ldirmasangiz ham bo'ladi — bot baribir ishlайdi, faqat rasm o'rniga hech narsa qo'ymaydi. Keyinroq to'ldirib, faylni saqlab, botni qayta ishga tushirsangiz yetarli.

## 7-QADAM: Botni ishga tushirish

Terminal/Command Prompt'da (hali `music_tag_bot` papkasida turganingizda):
```
python bot.py
```

Agar hech qanday xatolik chiqmasa, bot ishga tushdi degani. Endi Telegram'da o'z botingizni toping (username orqali), `/start` bosing, keyin unga bitta musiqa yuboring — tugmalar chiqishi kerak.

**Diqqat:** botni ishlab turishi uchun bu terminal oynasi ochiq turishi kerak. Oynani yopsangiz, bot to'xtaydi. Doim ishlab turishi uchun 8-qadamga qarang.

## 8-QADAM (ixtiyoriy): Botni 24/7 bepul serverda ishga tushirish

Kompyuteringizni doim yoqib qo'ymaslik uchun botni bepul hostingga joylashingiz mumkin:

- **Railway.app** — GitHub'ga loyihangizni yuklaysiz, Railway'da "New Project" → "Deploy from GitHub repo" qilasiz, `BOT_TOKEN`ni Railway'ning "Environment Variables" bo'limiga qo'yasiz (kodda ham shunga moslashtirish kerak bo'ladi — xohlasangiz shu qadamda ham yordam beraman)
- **PythonAnywhere.com** — bepul tarifda ham doimiy ishlaydigan "Always-on task" imkoniyati bor

Bu qadam ixtiyoriy — avval kompyuteringizda ishlab ko'ring, keyin xohlasangiz serverga chiqaramiz.

---

## Xatolik chiqsa nima qilish kerak?

- `pip: command not found` → Python PATH'ga qo'shilmagan, 1-qadamni qaytadan qiling, "Add to PATH" katakchasini belgilashni unutmang
- `ModuleNotFoundError: No module named 'aiogram'` → 5-qadamdagi `pip install -r requirements.txt` buyrug'ini bajarmagansiz yoki boshqa papkada turibsiz
- Bot javob bermayapti → `bot.py` ishga tushirilgan terminalda xatolik matni bor-yo'qligini tekshiring, va tokenni to'g'ri joylashtirganingizni tekshiring
