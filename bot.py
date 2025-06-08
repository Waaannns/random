import io, re, importlib, asyncio, aiohttp, os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Document
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters)
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("TOKEN")
pilihan_sh = {}

def filter_cc_only(text: str) -> str:
    cc_pattern = r'\b\d{15,16}\|\d{1,2}\|\d{2,4}\|\d{3,4}\b'
    matches = re.findall(cc_pattern, text)
    return '\n'.join(matches)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("dogoodshop.org ($5)", callback_data="sh1")],
        [InlineKeyboardButton("maymaymadeit.com ($5)", callback_data="sh2")],
        [InlineKeyboardButton("buildingnewfoundations.com ($10)", callback_data="sh3")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Pilih metode pengecekan:", reply_markup=reply_markup)


async def pilih_sh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    pilihan_sh[user_id] = query.data

    await query.edit_message_text(f"Kamu memilih: {query.data}. Sekarang kirim file .txt")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    pilihan = pilihan_sh.get(user_id)

    if not pilihan:
        await update.message.reply_text("Silakan ketik /start dan pilih metode pengecekan dulu.")
        return
    
    text = update.message.text
    if not text:
        await update.message.reply_text("Tolong kirim teks yang valid.")
        return
    
    try:
        modul = importlib.import_module(pilihan)
        sh_func = modul.sh
    except Exception as e:
        await update.message.reply_text(f"Gagal memuat modul: {e}")
        return
    
    cc = filter_cc_only(text)

    msg = await update.message.reply_text("⏳ Memproses...")

    try:
        hasil = await sh_func(cc)
        await msg.edit_text(hasil)
    except (aiohttp.client_exceptions.ServerDisconnectedError, aiohttp.ClientError, asyncio.TimeoutError) as e:
        await msg.edit_text(f"Card: {text}\nStatus: Error\nResponse: Network error or timeout\n")
    except Exception as e:
        await msg.edit_text(f"Card: {text}\nStatus: Error\nResponse: {e}\n")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    pilihan = pilihan_sh.get(user_id)

    if not pilihan:
        await update.message.reply_text("Silakan ketik /start dan pilih metode pengecekan dulu.")
        return

    try:
        modul = importlib.import_module(pilihan)
        sh_func = modul.sh
    except Exception as e:
        await update.message.reply_text(f"Gagal memuat modul: {e}")
        return

    document: Document = update.message.document
    if document.mime_type != 'text/plain':
        await update.message.reply_text("Tolong kirim file .txt saja.")
        return

    file = await document.get_file()
    file_bytes = await file.download_as_bytearray()
    file_stream = io.StringIO(file_bytes.decode('utf-8'))

    msg = await update.message.reply_text("⏳ Memproses...")

    results = []
    for line in file_stream:
        line = line.strip()
        if not line:
            continue
        try:
            hasil = await sh_func(line)
            await msg.edit_text(hasil)
            results.append(hasil)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            results.append(f"Card: {line}\nStatus: Error\nResponse: Network error or timeout\n")
            await asyncio.sleep(1)
        except Exception as e:
            results.append(f"Card: {line}\nStatus: Error\nResponse: {e}\n")
            await asyncio.sleep(1)

    output_text = "\n".join(results)

    if len(output_text) > 4000:
        output_file = io.BytesIO(output_text.encode('utf-8'))
        output_file.name = "hasil_cek.txt"
        await msg.edit_text("✅ Selesai. Hasil terlalu panjang, dikirim sebagai file.")
        await update.message.reply_document(document=output_file, filename="hasil_cek.txt")
    else:
        await msg.edit_text("✅ Selesai. Mengirim hasil...")
        await update.message.reply_text(f"📋 Hasil:\n\n{output_text}")


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(pilih_sh))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.Document.MimeType("text/plain") & ~filters.COMMAND, handle_document))
    app.run_polling()

if __name__ == '__main__':
    main()
