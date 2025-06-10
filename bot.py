import io, re, importlib, asyncio, aiohttp, os
import aiohttp.client_exceptions
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Document, BotCommand
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters)
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("TOKEN")
cc_pattern = re.compile(r'\b\d{15,16}\|\d{1,2}\|\d{2,4}\|\d{3,4}\b')
pilihan_sh = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("($1)", callback_data="sh6"), InlineKeyboardButton("($1)", callback_data="sh7")],
        [InlineKeyboardButton("($1)", callback_data="sh4")],
        [InlineKeyboardButton("($5)", callback_data="sh1"), InlineKeyboardButton("($5)", callback_data="sh2")],
        [InlineKeyboardButton("($10)", callback_data="sh3"), InlineKeyboardButton("($10)", callback_data="sh5")],
        [InlineKeyboardButton("($10)", callback_data="sh8"), InlineKeyboardButton("($10)", callback_data="sh9")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choice url shopify:", reply_markup=reply_markup)

async def check_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    pilihan = pilihan_sh.get(user_id, "No method selected")
    await update.message.reply_text(f"Current method check: {pilihan}")

async def set_commands(app):
    commands = [
        BotCommand("start", "Change method check"),
        BotCommand("method", "Current method check"),
    ]
    await app.bot.set_my_commands(commands)

async def pilih_sh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    pilihan_sh[user_id] = query.data

    await query.edit_message_text(f"You choice: {query.data}. Now Send the file .txt")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    pilihan = pilihan_sh.get(user_id)

    if not pilihan:
        await update.message.reply_text("Please type /start and select the check method first.")
        return
    
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("Please send a valid card format like '4111111111111111|08|2026|123'.")
        return
    
    try:
        modul = importlib.import_module(pilihan)
        sh_func = modul.sh
    except Exception as e:
        await update.message.reply_text(f"Failed to load module: {e}")
        return
    
    cc_matches = cc_pattern.findall(text)

    if len(cc_matches) > 1:
        msg = await update.message.reply_text("⏳ Processing multiple cards...")
        results = []

        for cc in cc_matches:
            try:
                hasil = await sh_func(cc)
                await msg.edit_text(hasil)
                results.append(hasil)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                result = await sh_func(hasil)
                await msg.edit_text(result)
            except Exception as e:
                results.append(f"Card: {cc}\nStatus: Error\nResponse: {e}\n\n")
                await asyncio.sleep(1)

        full_result = "".join(results)
        if len(full_result) > 4000:
            file = io.BytesIO(full_result.encode('utf-8'))
            file.name = f"result_{user_id}.txt"
            await msg.edit_text("✅ Done. The result is too long, so it's been sent as a file.")
            await update.message.reply_document(document=file)
        else:
            await msg.edit_text("✅ Done. Sending results...")
            await update.message.reply_text(f"📋 Result: {len(cc_matches)} Cards\n\n{full_result}")
    elif len(cc_matches) == 1:
        cc = cc_matches[0]
        msg = await update.message.reply_text("⏳ Processing...")
        try:
            hasil = await sh_func(cc)
            await msg.edit_text(hasil)
        except (aiohttp.client_exceptions.ServerDisconnectedError, aiohttp.ClientError, asyncio.TimeoutError) as e:
            result = await sh_func(hasil)
            await msg.edit_text(result)
        except Exception as e:
            await msg.edit_text(f"Card: {cc}\nStatus: Error\nResponse: {e}\n\n")
    else:
        await update.message.reply_text("No valid card found in the text. Please send a valid card format like '4111111111111111|08|2026|123'.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    pilihan = pilihan_sh.get(user_id)

    if not pilihan:
        await update.message.reply_text("Please type /start and select the check method first.")
        return

    try:
        modul = importlib.import_module(pilihan)
        sh_func = modul.sh
    except Exception as e:
        await update.message.reply_text(f"Failed to load module: {e}")
        return

    document: Document = update.message.document
    if document.mime_type != 'text/plain':
        await update.message.reply_text("Please send only .txt files.")
        return

    file = await document.get_file()
    file_bytes = await file.download_as_bytearray()
    file_stream = io.StringIO(file_bytes.decode('utf-8'))

    msg = await update.message.reply_text("⏳ Processing...")

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
            result = await sh_func(hasil)
            await msg.edit_text(result)
        except Exception as e:
            results.append(f"Card: {line}\nStatus: Error\nResponse: {e}\n")
            await asyncio.sleep(1)

    output_text = "\n".join(results)

    if len(output_text) > 4000:
        output_file = io.BytesIO(output_text.encode('utf-8'))
        output_file.name = f"result_{user_id}.txt"
        await msg.edit_text("✅ Done. The result is too long, so it's been sent as a file.")
        await update.message.reply_document(document=output_file)
    else:
        await msg.edit_text("✅ Done. Sending results...")
        await update.message.reply_text(f"📋 Result:\n\n{output_text}")


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("method", check_method))
    app.add_handler(CallbackQueryHandler(pilih_sh))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.Document.MimeType("text/plain") & ~filters.COMMAND, handle_document))
    app.post_init = set_commands
    app.run_polling()

if __name__ == '__main__':
    main()
