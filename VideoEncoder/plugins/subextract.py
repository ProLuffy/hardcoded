import os
import time
import math
from pyrogram import Client, filters
from ..utils.encoding import extract_subs

# Live Progress Bar Function
async def progress_bar(current, total, text, message, start_time):
    now = time.time()
    diff = now - start_time
    
    # Har 3 second mein message edit karega (Telegram limit se bachne ke liye)
    if round(diff % 3.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        time_to_completion = round((total - current) / speed) if speed > 0 else 0

        # Data formatting
        def humanbytes(size):
            if not size: return "0 B"
            power = 2**10
            n = 0
            dic = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
            while size > power:
                size /= power
                n += 1
            return f"{round(size, 2)} {dic[n]}"

        # Time formatting
        def time_formatter(seconds):
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            return f"{h}h {m}m {s}s" if h else f"{m}m {s}s"

        progress_str = "[{0}{1}] {2}%\n".format(
            ''.join(["█" for _ in range(math.floor(percentage / 5))]),
            ''.join(["░" for _ in range(20 - math.floor(percentage / 5))]),
            round(percentage, 2)
        )

        msg_text = f"**{text}**\n\n" \
                   f"{progress_str}" \
                   f"📦 **Size:** {humanbytes(current)} / {humanbytes(total)}\n" \
                   f"🚀 **Speed:** {humanbytes(speed)}/s\n" \
                   f"⏱ **ETA:** {time_formatter(time_to_completion)}"
        
        try:
            await message.edit_text(msg_text)
        except:
            pass


@Client.on_message(filters.command("subextract") & filters.private)
async def extract_subtitle_command(client, message):
    media_msg = message.reply_to_message if message.reply_to_message else message
    
    if not (media_msg.video or media_msg.document):
        return await message.reply_text("⚠️ Bhai, kisi video ya document ka reply karke `/subextract` likh.")

    # Original file ka naam nikalna
    original_file_name = "Extracted_Sub"
    if media_msg.video and getattr(media_msg.video, "file_name", None):
        original_file_name = media_msg.video.file_name
    elif media_msg.document and getattr(media_msg.document, "file_name", None):
        original_file_name = media_msg.document.file_name
        
    name_without_ext = os.path.splitext(original_file_name)[0]
    
    status_msg = await message.reply_text("📥 Downloading Started...")
    start_time = time.time()
    
    try:
        # Video Download with Live Progress Bar
        file_path = await media_msg.download(
            progress=progress_bar,
            progress_args=("📥 Downloading Video...", status_msg, start_time)
        )
    except Exception as e:
        return await status_msg.edit_text(f"❌ Download fail ho gaya:\n`{e}`")

    # Extraction message (bar ki zaroorat nahi kyunki ye 2-3 sec mein ho jata hai)
    await status_msg.edit_text("⏳ **Extracting Subtitle...**\n\n*(Note: Isme sirf 2-3 seconds lagenge...)*")
    
    # Subtitle extract karna (Tumhare encoding.py ka function call ho raha hai)
    sub_path = await extract_subs(file_path, status_msg, message.from_user.id)

    if sub_path and os.path.exists(sub_path):
        # Yahan Subtitle file ko uske original video wale naam se Rename kiya jaa raha hai
        sub_extension = os.path.splitext(sub_path)[1] # Generally .ass niklega
        new_sub_path = os.path.join(os.path.dirname(sub_path), f"{name_without_ext}{sub_extension}")
        
        os.rename(sub_path, new_sub_path)
        
        await status_msg.edit_text("✅ Subtitle nikal gaya! Upload kar raha hu...")
        start_time = time.time()
        
        try:
            # Subtitle Upload with Live Progress Bar
            await client.send_document(
                chat_id=message.chat.id,
                document=new_sub_path,
                caption=f"📁 **Name:** `{name_without_ext}`\n✅ Subtitle Successfully Extracted!",
                progress=progress_bar,
                progress_args=("📤 Uploading Subtitle...", status_msg, start_time)
            )
            await status_msg.delete() 
        except Exception as e:
            await status_msg.edit_text(f"❌ Upload fail ho gaya:\n`{e}`")
        finally:
            # Rename ki hui sub file delete karna
            if os.path.exists(new_sub_path):
                os.remove(new_sub_path)
    else:
        await status_msg.edit_text("⚠️ Is video mein koi subtitle file hide (softcode) nahi hai ya extract nahi ho payi.")

    # Original video delete karna server ka space bachane ke liye
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
