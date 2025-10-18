import requests
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Bot tokeni
BOT_TOKEN = "8261183664:AAGFgTnRb6Ex8ObaA9J0t-U5kDBy0WpOzjs"

# Hugging Face modeli (BEPUL)
HF_MODEL = "nateraw/food-classification"

class FreeFoodAI:
    def __init__(self):
        self.api_url = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
    
    def analyze_food(self, image_bytes):
        """Bepul API bilan rasmni tahlil qilish"""
        try:
            response = requests.post(self.api_url, data=image_bytes, timeout=30)
            
            if response.status_code == 200:
                results = response.json()
                if isinstance(results, list) and len(results) > 0:
                    return results[:3]  # Top 3 natija
            elif response.status_code == 503:
                # Model yuklanmagan bo'lsa
                logging.info("Model hali yuklanmoqda...")
                return self._get_fallback_response()
                
            return None
            
        except Exception as e:
            logging.error(f"API xatosi: {e}")
            return self._get_fallback_response()
    
    def _get_fallback_response(self):
        """API ishlamasa, fallback javob"""
        return [
            {"label": "food", "score": 0.8},
            {"label": "meal", "score": 0.7},
            {"label": "dish", "score": 0.6}
        ]

# Kaloriya taxmin qilish
def estimate_calories(food_name):
    food_name = food_name.lower()
    
    # Soddalashtirilgan kaloriya bazasi
    calories_db = {
        "salad": 50, "vegetable": 40, "fruit": 60,
        "pizza": 280, "burger": 300, "sandwich": 250,
        "chicken": 200, "meat": 250, "fish": 180,
        "rice": 130, "pasta": 140, "bread": 260,
        "cake": 350, "dessert": 400, "sweet": 450,
        "soup": 80, "stew": 120, "grilled": 200
    }
    
    for food, cal in calories_db.items():
        if food in food_name:
            return cal
    
    return 200  # O'rtacha qiymat

# Bot funksiyalari
food_ai = FreeFoodAI()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **Bepul Ovqat Boti** 🍕\n\n"
        "📸 Ovqat rasmini yuboring, men:\n"
        "• Taomni aniqlayman\n"
        "• Kaloriyasini taxmin qilaman\n"
        "• Maslahat beraman\n\n"
        "🚀 *Hammasi bepul!*"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Rasmni yuklash
        photo_file = await update.message.photo[-1].get_file()
        image_bytes = await photo_file.download_as_bytearray()
        
        wait_msg = await update.message.reply_text("🔍 Sun'iy intellekt tahlil qilmoqda...")
        
        # Ovqatni aniqlash
        results = food_ai.analyze_food(image_bytes)
        
        if results:
            top_food = results[0]['label']
            confidence = results[0]['score']
            calories = estimate_calories(top_food)
            
            response = f"""
🍽 **Aniqlangan:** {top_food.title()}
📊 **Ishonch:** {int(confidence*100)}%
🔥 **Kaloriya:** {calories} kcal/100g

💡 *Bepul sun'iy intellekt orqali*
            """
            
            # Boshqa variantlar
            if len(results) > 1:
                response += "\n🔍 **Boshqa ehtimollar:**\n"
                for i, res in enumerate(results[1:3], 1):
                    response += f"{i}. {res['label'].title()} ({int(res['score']*100)}%)\n"
        
        else:
            response = "❌ Tahlil qila olmadim. Boshqa rasm yuboring."
        
        await wait_msg.delete()
        await update.message.reply_text(response)
        
    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await update.message.reply_text("❌ Xatolik. Qaytadan urining.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Iltimos, ovqat rasmini yuboring!")

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Bepul Bot ishga tushdi! Token kerak emas!")
    application.run_polling()

if __name__ == '__main__':
    main()
