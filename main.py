import telebot
from telebot import types
import sqlite3
import time
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask
from multiprocessing import Process

# ==================== WEB SERVER (RENDER UYQUGA KETishining Oldini Olish Uchun) ====================
app = Flask('')

@app.route('/')
def home():
    return "Bot is active and running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Process(target=run_web)
    t.start()

# ==================== SOZLAMALAR ====================
TOKEN = "8603136006:AAEIz36hQq2m5gZhTL4kUruFLgS-3EZQoSk" # O'z tokeningizni yozing
ADMIN_ID = 8694110588                       # O'z Telegram ID raqamingiz

bot = telebot.TeleBot(TOKEN)
REF_BONUS = 1                               # Referal uchun ball

# ==================== DATABASE (MA'LUMOTLAR BAZASI) ====================
def init_db():
    conn = sqlite3.connect('ref_bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 0,
            invited_by INTEGER,
            referrals_count INTEGER DEFAULT 0,
            joined_date TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            channel_id TEXT PRIMARY KEY,
            channel_title TEXT,
            channel_type TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# ==================== MAJBURIY OBUNANI TEKSHIRISH ====================
def check_subscriptions(user_id):
    conn = sqlite3.connect('ref_bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT channel_id, channel_title, channel_type FROM channels')
    channels = cursor.fetchall()
    conn.close()
    
    not_subbed = []
    for ch in channels:
        ch_id, ch_title, ch_type = ch
        try:
            member = bot.get_chat_member(ch_id, user_id)
            if member.status not in ['creator', 'administrator', 'member']:
                not_subbed.append((ch_id, ch_title))
        except Exception:
            pass
    return not_subbed

# ==================== ASOSIY MENYU ====================
def send_main_menu(chat_id, user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🔗 Referal havola olish"),
        types.KeyboardButton("📊 Mening referallarim"),
        types.KeyboardButton("🏆 TOP-10 Referallar")
    )
    if user_id == ADMIN_ID:
        markup.add(types.KeyboardButton("👨‍💻 Admin Panel"))
    
    bot.send_message(
        chat_id, 
        "✨ **Assalomu alaykum!** Botimizga xush kelibsiz. 🚀\n\n"
        "Quyidagi tugmalar yordamida do'stlaringizni taklif qiling va mukofotlarga ega bo'ling! 👇", 
        reply_markup=markup, 
        parse_mode="Markdown"
    )

# ==================== START BUYRUG'I ====================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username
    args = message.text.split()
    
    conn = sqlite3.connect('ref_bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    # Agar foydalanuvchi birinchi marta kirayotgan bo'lsa
    if not user:
        invited_by = None
        if len(args) > 1 and args[1].isdigit():
            ref_id = int(args[1])
            if ref_id != user_id:
                cursor.execute('SELECT * FROM users WHERE user_id = ?', (ref_id,))
                if cursor.fetchone():
                    invited_by = ref_id
                    # Taklif qilgan odamning referallar sonini va balansini oshiramiz
                    cursor.execute('UPDATE users SET balance = balance + ?, referrals_count = referrals_count + 1 WHERE user_id = ?', (REF_BONUS, ref_id))
                    conn.commit()
                    try:
                        bot.send_message(ref_id, f"🔥 **Tabriklaymiz!** Sizning havolangiz orqali yangi do'stingiz qo'shildi va balansingizga `+{REF_BONUS}` ball qo'shildi! 🎁", parse_mode="Markdown")
                    except:
                        pass

        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('INSERT INTO users (user_id, username, invited_by, joined_date) VALUES (?, ?, ?, ?)', (user_id, username, invited_by, current_date))
        conn.commit()
    
    conn.close()

    # Kanallarga obuna tekshiruvi
    not_subbed = check_subscriptions(user_id)
    if not_subbed:
        markup = types.InlineKeyboardMarkup()
        for ch_id, ch_title in not_subbed:
            link = f"https://t.me/{ch_id.replace('@', '')}" if ch_id.startswith('@') else f"https://t.me/c/{str(ch_id).replace('-100', '')}/1"
            markup.add(types.InlineKeyboardButton(f"📢 {ch_title} kanaliga obuna bo'lish", url=link))
        
        markup.add(types.InlineKeyboardButton("🔄 Obunani tekshirish", callback_data="check_sub"))
        
        bot.send_message(
            user_id, 
            "⚠️ **Diqqat!** Botimizdan to'liq foydalanish va sovrinlarni yutib olish uchun quyidagi homiy kanallarga obuna bo'lishingiz shart! 👇", 
            reply_markup=markup, 
            parse_mode="Markdown"
        )
        return

    send_main_menu(user_id, user_id)

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def callback_check_sub(call):
    user_id = call.from_user.id
    not_subbed = check_subscriptions(user_id)
    
    if not_subbed:
        try:
            bot.answer_callback_query(call.id, "❌ Hali barcha kanallarga to'liq obuna bo'lmadingiz!", show_alert=True)
        except:
            pass
    else:
        try:
            bot.delete_message(call.message.chat.id, call.message.message.id)
        except:
            pass
        
        bot.send_message(user_id, "✅ **Obunangiz muvaffaqiyatli tasdiqlandi!** 🎉", parse_mode="Markdown")
        send_main_menu(user_id, user_id)

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.from_user.id
    text = message.text
    
    not_subbed = check_subscriptions(user_id)
    if not_subbed and text != "👨‍💻 Admin Panel":
        markup = types.InlineKeyboardMarkup()
        for ch_id, ch_title in not_subbed:
            link = f"https://t.me/{ch_id.replace('@', '')}" if ch_id.startswith('@') else f"https://t.me/c/{str(ch_id).replace('-100', '')}/1"
            markup.add(types.InlineKeyboardButton(f"📢 {ch_title} kanaliga obuna bo'lish", url=link))
        markup.add(types.InlineKeyboardButton("🔄 Obunani tekshirish", callback_data="check_sub"))
        bot.send_message(user_id, "⚠️ Botdan foydalanishni davom ettirish uchun yuqoridagi kanallarga obuna bo'ling!", reply_markup=markup)
        return

    if text == "🔗 Referal havola olish":
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        bot.send_message(user_id, f"🔗 **Sizning shaxsiy taklif havolangiz:**\n\n`{ref_link}`\n\n💡 *Do'stlaringizga ulashing!*", parse_mode="Markdown")
        
    elif text == "📊 Mening referallarim":
        conn = sqlite3.connect('ref_bot_database.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('SELECT balance, referrals_count FROM users WHERE user_id = ?', (user_id,))
        res = cursor.fetchone()
        conn.close()
        
        if res:
            balance, ref_count = res
            bot.send_message(user_id, f"👤 **Sizning statistikangiz:**\n\n🆔 ID: `{user_id}`\n💰 Ballar: `{balance}`\n👥 Referallar: `{ref_count}` ta", parse_mode="Markdown")
        else:
            bot.send_message(user_id, "Siz hali ro'yxatdan o'tmagansiz. /start buyrug'ini bosing.")
            
    elif text == "🏆 TOP-10 Referallar":
        conn = sqlite3.connect('ref_bot_database.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('SELECT username, referrals_count FROM users ORDER BY referrals_count DESC LIMIT 10')
        top_users = cursor.fetchall()
        conn.close()
        
        msg = "🏆 **Eng faol referal yig'uvchilar (TOP-10):**\n\n"
        for i, u in enumerate(top_users, 1):
            uname = f"@{u[0]}" if u[0] else "Noma'lum"
            msg += f"{i}. {uname} — {u[1]} ta\n"
        bot.send_message(user_id, msg)

    elif text == "👨‍💻 Admin Panel" and user_id == ADMIN_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton("📊 Vaqtli Statistika"),
            types.KeyboardButton("👥 Foydalanuvchini tekshirish"),
            types.KeyboardButton("🔄 TOP-10 Filtrlarini boshqarish"),
            types.KeyboardButton("📢 Hammaga xabar yuborish"),
            types.KeyboardButton("➕ Kanal qo'shish (Zayafka/Yopiq)"),
            types.KeyboardButton("🔙 Orqaga")
        )
        bot.send_message(user_id, "🛠 **Admin panel:**", reply_markup=markup, parse_mode="Markdown")
        
    elif user_id == ADMIN_ID:
        if text == "📊 Vaqtli Statistika":
            conn = sqlite3.connect('ref_bot_database.db', check_same_thread=False)
            cursor = conn.cursor()
            now = datetime.now()
            d_1 = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
            d_7 = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            d_30 = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute('SELECT COUNT(*) FROM users')
            total = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM users WHERE joined_date >= ?', (d_1,))
            c_1 = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM users WHERE joined_date >= ?', (d_7,))
            c_7 = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM users WHERE joined_date >= ?', (d_30,))
            c_30 = cursor.fetchone()[0]
            conn.close()
            
            bot.send_message(user_id, f"📈 **Statistika:**\n\nJami: `{total}`\n1 kunda: `{c_1}`\n7 kunda: `{c_7}`\n1 oyda: `{c_30}`", parse_mode="Markdown")
            
        elif text == "👥 Foydalanuvchini tekshirish":
            bot.send_message(user_id, "Foydalanuvchi ID yoki username'ini yuboring:")
            bot.register_next_step_handler(message, inspect_user)
            
        elif text == "🔄 TOP-10 Filtrlarini boshqarish":
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("1 Kunlik TOP", callback_data="top_filter_1"))
            markup.add(types.InlineKeyboardButton("3 Kunlik TOP", callback_data="top_filter_3"))
            markup.add(types.InlineKeyboardButton("7 Kunlik TOP", callback_data="top_filter_7"))
            bot.send_message(user_id, "TOP vaqt oralig'ini tanlang:", reply_markup=markup)
            
        elif text == "➕ Kanal qo'shish (Zayafka/Yopiq)":
            bot.send_message(user_id, "Format: `@kanal, Nomi, type`\n(type: `public` yoki `private_request`)")
            bot.register_next_step_handler(message, save_channel)
            
        elif text == "📢 Hammaga xabar yuborish":
            bot.send_message(user_id, "Xabar matnini yuboring:")
            bot.register_next_step_handler(message, broadcast_message)
            
        elif text == "🔙 Orqaga":
            send_main_menu(user_id, user_id)

def inspect_user(message):
    if message.from_user.id != ADMIN_ID:
        return
    query = message.text.strip().replace('@', '')
    conn = sqlite3.connect('ref_bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    if query.isdigit():
        cursor.execute('SELECT user_id, username, balance, referrals_count, joined_date FROM users WHERE user_id = ?', (int(query),))
    else:
        cursor.execute('SELECT user_id, username, balance, referrals_count, joined_date FROM users WHERE username = ?', (query,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        bot.send_message(ADMIN_ID, f"ID: `{user[0]}`\nUsername: @{user[1]}\nBall: {user[2]}\nReferal: {user[3]}", parse_mode="Markdown")
    else:
        bot.send_message(ADMIN_ID, "Topilmadi!")
    send_main_menu(ADMIN_ID, ADMIN_ID)

@bot.callback_query_handler(func=lambda call: call.data.startswith('top_filter_'))
def callback_top_filter(call):
    days = int(call.data.split('_')[2])
    conn = sqlite3.connect('ref_bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT username, referrals_count FROM users ORDER BY referrals_count DESC LIMIT 10')
    top_users = cursor.fetchall()
    conn.close()
    msg = f"🏆 **TOP-10 ({days} kun):**\n\n"
    for i, u in enumerate(top_users, 1):
        msg += f"{i}. @{u[0]} — {u[1]} ta\n"
    bot.send_message(ADMIN_ID, msg)

def save_channel(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split(',')
        conn = sqlite3.connect('ref_bot_database.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO channels (channel_id, channel_title, channel_type) VALUES (?, ?, ?)', (parts[0].strip(), parts[1].strip(), parts[2].strip()))
        conn.commit()
        conn.close()
        bot.send_message(ADMIN_ID, "✅ Kanal qo'shildi!")
    except:
        bot.send_message(ADMIN_ID, "⚠️ Xato format!")
    send_main_menu(ADMIN_ID, ADMIN_ID)

def broadcast_message(message):
    if message.from_user.id != ADMIN_ID:
        return
    def send_to_all():
        conn = sqlite3.connect('ref_bot_database.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        users = cursor.fetchall()
        conn.close()
        for u in users:
            try:
                bot.copy_message(u[0], message.chat.id, message.message_id)
                time.sleep(0.04)
            except:
                pass
        bot.send_message(ADMIN_ID, "📢 Xabar yuborildi!")
    Thread(target=send_to_all).start()
    bot.send_message(ADMIN_ID, "⏳ Yuborilmoqda...")
    send_main_menu(ADMIN_ID, ADMIN_ID)

# ==================== BOTNI ISHGA TUSHIRISH ====================
if __name__ == '__main__':
    keep_alive()
    print("Bot va veb-server ishga tushdi...")
    bot.infinity_polling()
