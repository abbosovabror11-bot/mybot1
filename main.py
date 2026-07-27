import telebot
from telebot import types
import sqlite3
from datetime import datetime, timedelta

# ==================== SOZLAMALAR ====================
TOKEN = "8764985382:AAH4QBaB5tr0It49E7_K2Q38ZZTku59jPTE"
ADMIN_ID = 8694110588  # O'z Telegram ID raqamingizni yozing

bot = telebot.TeleBot(TOKEN)
forced_channels = []  # Majburiy kanallar ro'yxati (id, link, title, type: 'public' yoki 'request')
user_state = {}
REF_BONUS = 0  # Referal uchun asosiy ball yoki bonus (agar kerak bo'lsa)

# ==================== DATABASE (MA'LUMOTLAR BAZASI) ====================
def init_db():
    conn = sqlite3.connect('ref_bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    # Foydalanuvchilar jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            fullname TEXT,
            referrer INTEGER,
            joined_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect('ref_bot_database.db', check_same_thread=False)

# ==================== YORDAMCHI FUNKSIYALAR ====================
def check_user_sub(user_id):
    if not forced_channels:
        return True, None
    for ch in forced_channels:
        try:
            member = bot.get_chat_member(ch["id"], user_id)
            if member.status not in ['creator', 'administrator', 'member', 'restricted']:
                return False, ch
        except Exception:
            # Agar yopiq kanal/guruh bo'lib, bot admin bo'lmasa yoki tekshirib bo'lmasa
            return False, ch
    return True, None

def send_sub_request(chat_id):
    markup = types.InlineKeyboardMarkup()
    for ch in forced_channels:
        markup.add(types.InlineKeyboardButton(f"📢 {ch.get('title', 'Kanal')}", url=ch["link"]))
    markup.add(types.InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check_subscription"))
    bot.send_message(chat_id, "⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'lishingiz shart 🔔:", reply_markup=markup)

# ==================== START VA MENYULAR ====================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else f"ID:{user_id}"
    fullname = message.from_user.first_name
    args = message.text.split()
    
    referrer = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer = int(args[1].replace("ref_", ""))
        except:
            pass

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    
    if not row:
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ref_id = referrer if (referrer and referrer != user_id) else None
        cursor.execute('INSERT INTO users (user_id, username, fullname, referrer, joined_date) VALUES (?, ?, ?, ?, ?)', 
                       (user_id, username, fullname, ref_id, date_str))
        conn.commit()
        
        if ref_id:
            try:
                bot.send_message(ref_id, f"🎉 Tabriklaymiz! Yangi do'stingiz ({fullname}) sizning havolangiz orqali botga qo'shildi! 👥✨", parse_mode="Markdown")
            except:
                pass
    else:
        cursor.execute('UPDATE users SET username = ?, fullname = ? WHERE user_id = ?', (username, fullname, user_id))
        conn.commit()
    conn.close()

    # Majburiy obunani tekshirish
    is_subbed, _ = check_user_sub(user_id)
    if not is_subbed and user_id != ADMIN_ID:
        send_sub_request(message.chat.id)
        return

    send_main_menu(message.chat.id, user_id)

@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def callback_check_sub(call):
    user_id = call.from_user.id
    is_subbed, _ = check_user_sub(user_id)
    if is_subbed:
        bot.answer_callback_query(call.id, "✅ Obuna tasdiqlandi! 🎉")
        try: bot.delete_message(call.message.chat.id, call.message.message_id) except: pass
        send_main_menu(call.message.chat.id, user_id)
    else:
        bot.answer_callback_query(call.id, "❌ Hali hamma kanalga obuna bo'lmadingiz! ⚠️", show_alert=True)

def send_main_menu(chat_id, user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔗 Referal ssilka olish"), types.KeyboardButton("📊 Mening referallarim"))
    markup.add(types.KeyboardButton("🏆 TOP-10 Referallar"))
    if user_id == ADMIN_ID:
        markup.add(types.KeyboardButton("👨‍💻 Admin Panel"))
    bot.send_message(chat_id, "🎉 Asosiy menyuga xush kelibsiz! Kerakli bo'limni tanlang 👇✨", reply_markup=markup)

# ==================== FOYDALANUVCHI BUYRUQLARI ====================
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text
    state = user_state.get(user_id)

    # --- ADMIN QISMI ---
    if user_id == ADMIN_ID:
        if text == "👨‍💻 Admin Panel":
            send_admin_panel(message.chat.id)
            return
        elif text == "📢 Majburiy kanal qo'shish":
            user_state[user_id] = "add_forced_channel"
            bot.send_message(message.chat.id, "Kanal ma'lumotlarini quyidagi formatda yuboring:\n`@kanalusername | https://t.me/kanal_link | Kanal Nomi`", parse_mode="Markdown")
            return
        elif text == "📋 Kanallar ro'yxati":
            if not forced_channels:
                bot.send_message(message.chat.id, "📭 Hozircha majburiy kanallar yo'q.")
            else:
                markup = types.InlineKeyboardMarkup()
                for idx, ch in enumerate(forced_channels):
                    markup.add(types.InlineKeyboardButton(f"❌ O'chirish: {ch['title']}", callback_data=f"del_ch_{idx}"))
                bot.send_message(message.chat.id, "📋 Majburiy kanallar ro'yxati:", reply_markup=markup)
            return
        elif text == "📊 Statistika":
            show_statistics(message.chat.id)
            return
        elif text == "👥 Foydalanuvchi referallarini ko'rish":
            user_state[user_id] = "check_user_refs_id"
            bot.send_message(message.chat.id, "Tekshirmoqchi bo'lgan foydalanuvchining Telegram ID raqamini kiriting:")
            return
        elif text == "🔄 TOP-10 davriyligini o'zgartirish":
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Har 1 kunda", callback_data="top_period_1"))
            markup.add(types.InlineKeyboardButton("Har 3 kunda", callback_data="top_period_3"))
            markup.add(types.InlineKeyboardButton("Har 7 kunda", callback_data="top_period_7"))
            bot.send_message(message.chat.id, "TOP-10 natijalarini yangilash/ko'rsatish davriyligini tanlang:", reply_markup=markup)
            return
        elif text == "📢 Barchaga xabar yuborish":
            user_state[user_id] = "broadcast_msg"
            bot.send_message(message.chat.id, "Barcha bot a'zolariga yuboriladigan xabarni kiriting:")
            return
        elif text == "🚪 Menuga qaytish":
            send_main_menu(message.chat.id, user_id)
            return

        # State logikalari (Admin uchun)
        if state == "add_forced_channel":
            user_state[user_id] = None
            parts = text.split("|")
            if len(parts) >= 2:
                ch_id = parts[0].strip()
                ch_link = parts[1].strip()
                ch_title = parts[2].strip() if len(parts) > 2 else ch_id
                forced_channels.append({"id": ch_id, "link": ch_link, "title": ch_title})
                bot.send_message(message.chat.id, f"✅ Kanal muvaffaqiyatli qo'shildi: {ch_title} 📢")
            else:
                bot.send_message(message.chat.id, "❌ Noto'g'ri format! Qaytadan urinib ko'ring.")
            send_admin_panel(message.chat.id)
            return

        elif state == "check_user_refs_id":
            user_state[user_id] = None
            if text.isdigit():
                target_id = int(text)
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT fullname, username FROM users WHERE user_id = ?', (target_id,))
                u_info = cursor.fetchone()
                cursor.execute('SELECT fullname, username, joined_date FROM users WHERE referrer = ?', (target_id,))
                refs = cursor.fetchall()
                conn.close()

                if not u_info:
                    bot.send_message(message.chat.id, "❌ Bunday foydalanuvchi topilmadi.")
                else:
                    msg = f"👤 **Foydalanuvchi:** {u_info[0]} ({u_info[1]})\n🆔 ID: `{target_id}`\n👥 Jami taklif qilganlari: **{len(refs)} ta**\n\n"
                    for idx, r in enumerate(refs, 1):
                        msg += f"{idx}. {r[0]} ({r[1]}) — 📅 {r[2]}\n"
                    bot.send_message(message.chat.id, msg, parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, "❌ Faqat raqamli ID kiriting.")
            send_admin_panel(message.chat.id)
            return

        elif state == "broadcast_msg":
            user_state[user_id] = None
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users')
            users_list = cursor.fetchall()
            conn.close()

            success, failed = 0, 0
            for u in users_list:
                try:
                    bot.send_message(u[0], text)
                    success += 1
                except:
                    failed += 1
            bot.send_message(message.chat.id, f"✅ Xabar yuborildi!\nMuvaffaqiyatli: {success} ta\nXatolik: {failed} ta")
            send_admin_panel(message.chat.id)
            return

    # --- ODDIY FOYDALANUVCHI QISMI ---
    if text == "🔗 Referal ssilka olish":
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        bot.send_message(message.chat.id, f"🔗 **Sizning shaxsiy referal havolangiz:**\n\n`{ref_link}`\n\nUshbu havolani do'stlaringizga ulashing va botga taklif qiling! 🚀", parse_mode="Markdown")
        return

    elif text == "📊 Mening referallarim":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users WHERE referrer = ?', (user_id,))
        ref_count = cursor.fetchone()[0]
        cursor.execute('SELECT fullname, username, joined_date FROM users WHERE referrer = ? ORDER BY joined_date DESC LIMIT 10', (user_id,))
        refs = cursor.fetchall()
        conn.close()

        msg = f"📊 **Sizning statistikangiz:**\n\n👥 Jami taklif qilgan do'stlaringiz: **{ref_count} ta**\n\n"
        if refs:
            msg += "📜 *Oxirgi qo'shilgan do'stlaringiz:*\n"
            for idx, r in enumerate(refs, 1):
                msg += f"{idx}. {r[0]} — 📅 {r[2]}\n"
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")
        return

    elif text == "🏆 TOP-10 Referallar":
        show_top_10(message.chat.id)
        return

def send_admin_panel(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📢 Majburiy kanal qo'shish", "📋 Kanallar ro'yxati")
    markup.add("📊 Statistika", "👥 Foydalanuvchi referallarini ko'rish")
    markup.add("🔄 TOP-10 davriyligini o'zgartirish", "📢 Barchaga xabar yuborish")
    markup.add("🚪 Menuga qaytish")
    bot.send_message(chat_id, "👨‍💻 **Admin Panel**ga xush kelibsiz ⚙️", reply_markup=markup, parse_mode="Markdown")

def show_statistics(chat_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.now()
    one_day_ago = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    seven_days_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    one_month_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM users WHERE joined_date >= ?', (one_day_ago,))
    users_1d = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM users WHERE joined_date >= ?', (seven_days_ago,))
    users_7d = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM users WHERE joined_date >= ?', (one_month_ago,))
    users_30d = cursor.fetchone()[0]

    conn.close()

    stat_text = (
        f"📊 **Bot Statistikasi:**\n\n"
        f"👥 Jami foydalanuvchilar: **{total_users}** ta\n"
        f"📅 1 kunda kirganlar: **{users_1d}** ta\n"
        f"📅 7 kunda kirganlar: **{users_7d}** ta\n"
        f"📅 1 oyda kirganlar: **{users_30d}** ta\n"
    )
    bot.send_message(chat_id, stat_text, parse_mode="Markdown")

def show_top_10(chat_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.fullname, u.username, COUNT(r.user_id) as ref_count 
        FROM users u 
        LEFT JOIN users r ON r.referrer = u.user_id 
        GROUP BY u.user_id 
        ORDER BY ref_count DESC 
        LIMIT 10
    ''')
    top_refs = cursor.fetchall()
    conn.close()

    top_text = "🏆 **TOP-10 Eng faol referal yig‘uvchilar:**\n\n"
    for idx, (fullname, uname, count) in enumerate(top_refs, 1):
        name = fullname if fullname else "Foydalanuvchi"
        top_text += f"{idx}. {name} — **{count}** ta do'st 👥\n"
    
    bot.send_message(chat_id, top_text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data

    if data.startswith("del_ch_") and user_id == ADMIN_ID:
        idx = int(data.split("_")[2])
        if 0 <= idx < len(forced_channels):
            forced_channels.pop(idx)
            bot.answer_callback_query(call.id, "✅ Kanal o'chirildi")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="✅ Kanal ro'yxatdan olib tashlandi.")
        return

    if data.startswith("top_period_") and user_id == ADMIN_ID:
        period = data.split("_")[2]
        bot.answer_callback_query(call.id, f"✅ TOP-10 davriyligi {period} kunga sozlndi!")
        bot.send_message(call.message.chat.id, f"✅ TOP-10 natijalarini ko'rsatish davriyligi **{period} kunlik** rejimga o'tkazildi.")
        return

# Botni ishga tushirish
bot.infinity_polling()
