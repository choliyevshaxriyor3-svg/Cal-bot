import os
import logging
import sqlite3
import datetime
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ================== KONFIGURATSIYA ==================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8438296355:AAEfswFCeGvUAjsVi_ud5160pMyxHgFdYhI")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================== BAZA ==================
class Database:
    def __init__(self):
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                plan TEXT DEFAULT 'free',
                images_used INTEGER DEFAULT 0,
                total_images INTEGER DEFAULT 5,
                join_date TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    def get_user(self, user_id):
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                "user_id": user[0], "username": user[1], "plan": user[2],
                "images_used": user[3], "total_images": user[4], "join_date": user[5]
            }
        return None
    
    def create_user(self, user_id, username):
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, username, plan, images_used, total_images, join_date)
            VALUES (?, ?, 'free', 0, 5, ?)
        ''', (user_id, username, datetime.datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    def update_usage(self, user_id):
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET images_used = images_used + 1 WHERE user_id = ?
        ''', (user_id,))
        conn.commit()
        conn.close()
    
    def upgrade_user(self, user_id, plan, total_images):
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET plan = ?, total_images = ?, images_used = 0 
            WHERE user_id = ?
        ''', (plan, total_images, user_id))
        conn.commit()
        conn.close()

# ================== AI GENERATOR ==================
class AIGenerator:
    def generate_image(self, prompt):
        """DALL-E 3 bilan rasm yaratish"""
        try:
            url = "https://api.openai.com/v1/images/generations"
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "dall-e-3",
                "prompt": prompt,
                "size": "1024x1024",
                "quality": "standard",
                "n": 1
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                return result['data'][0]['url'], None
            else:
                error_msg = response.json().get('error', {}).get('message', 'Noma\'lum xatolik')
                return None, f"API xatosi: {error_msg}"
                
        except Exception as e:
            return None, f"Xatolik: {str(e)}"

# ================== BOT HANDLERS ==================
db = Database()
ai = AIGenerator()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    db.create_user(user.id, user.username)
    
    welcome_text = """
🎨 **AI Image Generator PRO** 🤖

✨ **3 SONIADA AJOYIB RASMLAR!**

🆓 **BEPUL:** 5 ta rasm/kun
💎 **PREMIUM:** Cheksiz imkoniyatlar

📝 **Qanday ishlatish:**
`/generate go'zal qiz, anime uslubida`
yoki
`generate oliv'ye salati, realistik`

💳 **Premium plans:** /plans
📊 **Statistika:** /stats
    """
    
    keyboard = [
        [InlineKeyboardButton("🖼 Rasm Yaratish", callback_data="generate")],
        [InlineKeyboardButton("💎 Premium", callback_data="plans"),
         InlineKeyboardButton("📊 Statistika", callback_data="stats")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("📝 Iltimos, rasm tavsifini kiriting:\n\nMisol: `/generate go'zal tabiat manzarasi`")
        return
    
    prompt = " ".join(context.args)
    await generate_image_process(update, prompt)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text.lower().startswith("generate "):
        prompt = text.split(" ", 1)[1]
        await generate_image_process(update, prompt)
    elif text.lower().startswith("yarat "):
        prompt = text.split(" ", 1)[1]
        await generate_image_process(update, prompt)
    else:
        await update.message.reply_text("🎨 Rasm yaratish uchun:\n\n`generate sizning tavsifingiz`\nyoki\n`/generate tavsif`")

async def generate_image_process(update, prompt):
    user = update.message.from_user
    user_data = db.get_user(user.id)
    
    if not user_data:
        db.create_user(user.id, user.username)
        user_data = db.get_user(user.id)
    
    # Limit tekshirish
    if user_data['images_used'] >= user_data['total_images']:
        if user_data['plan'] == 'free':
            await update.message.reply_text(
                f"❌ **Bepul limit tugadi!**\n\n"
                f"Siz {user_data['images_used']}/{user_data['total_images']} ta rasm yaratdingiz.\n\n"
                f"💎 **Premium planlar:** /plans\n"
                f"🔄 **Limit 24 soatdan keyin yangilanadi**"
            )
            return
        else:
            await update.message.reply_text(
                f"❌ **Oylik limit tugadi!**\n\n"
                f"Siz {user_data['images_used']}/{user_data['total_images']} ta rasm yaratdingiz.\n\n"
                f"💳 **Plan yangilash:** /plans"
            )
            return
    
    # Rasm yaratish
    wait_msg = await update.message.reply_text("🔄 AI rasm yaratmoqda... 10-30 soniya")
    
    image_url, error = ai.generate_image(prompt)
    
    if error:
        await wait_msg.delete()
        await update.message.reply_text(f"❌ Xatolik: {error}\n\nQaytadan urinib ko'ring.")
        return
    
    # Bazani yangilash
    db.update_usage(user.id)
    user_data = db.get_user(user.id)
    
    # Rasmni yuborish
    await wait_msg.delete()
    
    caption = f"""🎨 **Yaratilgan rasm**
📝 `{prompt}`

✅ **Model:** DALL-E 3
📊 **Ishlatilgan:** {user_data['images_used']}/{user_data['total_images']}
💎 **Plan:** {user_data['plan'].upper()}

🔄 **Yangi rasm:** /generate
"""
    
    try:
        await update.message.reply_photo(
            photo=image_url,
            caption=caption,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Yangi Rasm", callback_data="generate")],
                [InlineKeyboardButton("💎 Premium", callback_data="plans")]
            ])
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Rasm yuborishda xatolik: {str(e)}")

async def plans_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    plans_text = """
💎 **PREMIUM PLANS**

🆓 **FREE** - 0$
• 5 rasm/kun
• DALL-E 3 model
• Standart sifat

💰 **STARTER** - 5$/oy 💰
• 100 rasm/oy  
• DALL-E 3 + SDXL
• Yuqori sifat
• Tez javob

💼 **PRO** - 10$/oy 🔥
• 500 rasm/oy
• Barcha modellar
• Eksklyuziv access
• Prioritet support

🏢 **BUSINESS** - 20$/oy 🚀
• 2000 rasm/oy  
• Cheksiz deyarli
• Barcha imkoniyatlar
• Shaxsiy yordam

💳 **To'lov usullari:**
• Click, Payme, Uzumbank
• Karta orqali
• Kripto valyuta

📞 **Admin:** @Shaxriyor_web
    """
    
    keyboard = [
        [InlineKeyboardButton("💳 To'lov qilish", url="9860350148428435")],
        [InlineKeyboardButton("📞 Admin bilan bog'lanish", url="@Shaxriyor_web")],
        [InlineKeyboardButton("🔄 Bosh menyu", callback_data="menu")]
    ]
    
    await update.message.reply_text(plans_text, reply_markup=InlineKeyboardMarkup(keyboard))

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_data = db.get_user(user.id)
    
    if user_data:
        remaining = user_data['total_images'] - user_data['images_used']
        stats_text = f"""
📊 **SIZNING STATISTIKANGIZ**

👤 **Foydalanuvchi:** {user.first_name}
💎 **Plan:** {user_data['plan'].upper()}
🖼 **Yaratilgan:** {user_data['images_used']} rasm
🎯 **Qolgan:** {remaining} rasm
📈 **Limit:** {user_data['total_images']} ta

💡 **Maslahat:** {remaining} ta rasm yaratishingiz mumkin!
"""
        if user_data['plan'] == 'free' and remaining == 0:
            stats_text += "\n⏳ **Limit 24 soatdan keyin yangilanadi**"
            
    else:
        stats_text = "❌ Statistika topilmadi. /start ni bosing."
    
    await update.message.reply_text(stats_text)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "generate":
        await query.edit_message_text("📝 Rasm tavsifini yuboring:\n\nMisol: `go'zal qiz, anime uslubida`\nyoki\n`generate sizning tavsifingiz`")
    
    elif query.data == "plans":
        await plans_command(update, context)
    
    elif query.data == "stats":
        await stats_command(update, context)
    
    elif query.data == "menu":
        await start(update, context)

# ================== ASOSIY DASTUR ==================
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlerlar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("generate", generate_command))
    application.add_handler(CommandHandler("plans", plans_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 AI Image Generator Bot ishga tushdi!")
    print("🎨 Endi foydalanuvchilar rasm yarata oladi!")
    print("💰 Daromad olishni boshlashingiz mumkin!")
    
    application.run_polling()

if __name__ == '__main__':
    main()
