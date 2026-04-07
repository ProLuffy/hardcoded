import os
import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from VideoEncoder import encode_dir, download_dir
from VideoEncoder.utils.database.access_db import db

# Import all necessary functions from your encoding.py
from VideoEncoder.utils.encoding import encode, extract_subs, get_duration, get_thumbnail

# =========================================================
# AUTHORIZATION LOGIC
# =========================================================
MY_USERNAME = "i_killed_my_clan"
UNAUTH_LINKS = [
    "https://t.me/Anime_Crew_Network", 
    "https://t.me/Webtoon_Crew",       
    "https://t.me/Comicktown"          
]

async def check_auth(user_id):
    owner_id = str(os.getenv("OWNER_ID", ""))
    if str(user_id) in owner_id.split(): return True
    
    auth_chats = await db.get_chat()
    if auth_chats and str(user_id) in auth_chats.split(): return True
        
    sudo_users = await db.get_sudo()
    if sudo_users and str(user_id) in sudo_users.split(): return True
    return False

async def is_admin(user_id):
    owner_id = str(os.getenv("OWNER_ID", ""))
    if str(user_id) in owner_id.split(): return True
    
    sudo_users = await db.get_sudo()
    if sudo_users and str(user_id) in sudo_users.split(): return True
    return False

async def auth_filter_func(flt, client, message):
    user_id = message.from_user.id
    if await check_auth(user_id): return True
    
    link = random.choice(UNAUTH_LINKS)
    text = (
        "❌ **Access Denied!**\n\n"
        "You are not authorized to use this bot. Please contact the Admin for access.\n\n"
        f"🔗 **Support/Join:** [Click Here]({link})"
    )
    btn = InlineKeyboardMarkup([[InlineKeyboardButton("Contact Admin 👤", url=f"https://t.me/{MY_USERNAME}")]])
    await message.reply_text(text, reply_markup=btn, disable_web_page_preview=True)
    return False

is_auth = filters.create(auth_filter_func)

USER_ENCODE_STATE = {}
FONT_DIR = "VideoEncoder/utils/extras/fonts"

# Helper to check if message contains a valid video/document
def is_valid_video(message):
    if message.video:
        return True
    if message.document:
        ext = os.path.splitext(message.document.file_name or "")[1].lower()
        if ext in ['.mkv', '.mp4', '.avi', '.webm']:
            return True
    return False

# =========================================================
# FONT HANDLERS
# =========================================================
@Client.on_message(filters.command("addfont") & filters.private)
async def add_custom_font(client, message):
    if not await is_admin(message.from_user.id): 
        return await message.reply_text("❌ Only Admins can add custom fonts.")
        
    if not message.reply_to_message or not message.reply_to_message.document: 
        return await message.reply_text("⚠️ Please reply to a `.ttf` or `.otf` font file with `/addfont [Name]`.")
        
    doc = message.reply_to_message.document
    if not doc.file_name.endswith(('.ttf', '.otf', '.TTF', '.OTF')): 
        return await message.reply_text("⚠️ Only `.ttf` or `.otf` extensions are allowed.")
        
    if len(message.command) < 2: 
        return await message.reply_text("⚠️ Please provide a font name: `/addfont Roboto`")
    
    font_name = " ".join(message.command[1:])
    ext = os.path.splitext(doc.file_name)[1]
    file_name = f"{font_name}{ext}"
    file_path = os.path.join(FONT_DIR, file_name)
    
    status = await message.reply_text("📥 Saving font to Database...")
    if not os.path.isdir(FONT_DIR): os.makedirs(FONT_DIR)
    await message.reply_to_message.download(file_name=file_path)
    
    try:
        await db.add_font(font_name, doc.file_id, file_name)
        await status.edit_text(f"✅ Your font **{font_name}** has been successfully saved to the Database!")
    except Exception as e:
        await status.edit_text("❌ Database error. Make sure `add_font` is in database.py")

@Client.on_message(filters.command("removefont") & filters.private)
async def remove_font(client, message):
    if not await is_admin(message.from_user.id): 
        return await message.reply_text("❌ Only Admins can remove custom fonts.")
    try:
        await db.remove_active_font()
        await message.reply_text("🗑 Custom font has been deactivated. The default font will be used.")
    except:
        await message.reply_text("❌ Database error.")

@Client.on_message(filters.command(["font", "fonts"]) & filters.private)
async def list_fonts(client, message):
    if not await is_admin(message.from_user.id): 
        return await message.reply_text("❌ Only Admins can view fonts.")
    
    try:
        fonts = await db.db.custom_fonts.find().to_list(length=100)
        if not fonts:
            return await message.reply_text("📁 No custom fonts found in the Database.")
            
        text = "🔠 **Saved Fonts:**\n\n"
        for f in fonts:
            status = "✅ Active" if f.get("active") else "❌ Inactive"
            text += f"• **{f['font_name']}** `{f['file_name']}` - {status}\n"
            
        await message.reply_text(text)
    except Exception as e:
        await message.reply_text(f"❌ Error fetching fonts: {e}")

# =========================================================
# ULTIMATE INTERACTIVE ENCODE MENU (STEP BY STEP)
# =========================================================

# STEP 1: Command Initiation
@Client.on_message(filters.command("encode") & filters.private & is_auth)
async def interactive_encode_start(client, message):
    user_id = message.from_user.id
    
    if not message.reply_to_message or not is_valid_video(message.reply_to_message):
        return await message.reply_text("⚠️ Please use the `/encode` command as a reply to a **Video or Document (MKV/MP4)**.")
        
    USER_ENCODE_STATE[user_id] = {
        "video_msg": message.reply_to_message,
        "sub_mode": None,
        "sub_source": None,
        "sub_msg": None,
        "quality": None,
        "waiting_for_sub": False
    }
    
    buttons = [
        [InlineKeyboardButton("🔥 Hardcode Subtitle", callback_data="enc_mode_hard")],
        [InlineKeyboardButton("🎬 Softcode Subtitle", callback_data="enc_mode_soft")],
        [InlineKeyboardButton("🚫 No Subtitle (Direct Encode)", callback_data="enc_mode_none")]
    ]
    await message.reply_text("**Step 1:** What would you like to do with subtitles for this video?", reply_markup=InlineKeyboardMarkup(buttons))


# STEP 2: Choose Mode (Hard/Soft/None)
@Client.on_callback_query(filters.regex(r"^enc_mode_(hard|soft|none)$") & is_auth)
async def handle_encode_mode(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in USER_ENCODE_STATE: 
        return await callback_query.answer("⚠️ Session Expired. Please send /encode again.", show_alert=True)
        
    mode = callback_query.matches[0].group(1)
    USER_ENCODE_STATE[user_id]["sub_mode"] = mode
    
    if mode == "none":
        USER_ENCODE_STATE[user_id]["sub_source"] = "none"
        return await ask_quality_buttons(callback_query.message)
        
    buttons = [
        [InlineKeyboardButton("🎬 Use Existing Video Subtitle", callback_data="enc_src_existing")],
        [InlineKeyboardButton("📁 Upload Custom Subtitle (.srt/.ass)", callback_data="enc_src_custom")]
    ]
    await callback_query.message.edit_text(f"**Step 2 ({mode.capitalize()}code):** Where should we get the subtitle from?", reply_markup=InlineKeyboardMarkup(buttons))


# STEP 3: Choose Source (Existing/Custom)
@Client.on_callback_query(filters.regex(r"^enc_src_(existing|custom)$") & is_auth)
async def handle_encode_source(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in USER_ENCODE_STATE: 
        return await callback_query.answer("⚠️ Session Expired.", show_alert=True)
        
    source = callback_query.matches[0].group(1)
    USER_ENCODE_STATE[user_id]["sub_source"] = source
    
    if source == "existing":
        return await ask_quality_buttons(callback_query.message)
        
    if source == "custom":
        USER_ENCODE_STATE[user_id]["waiting_for_sub"] = True
        await callback_query.message.edit_text("📤 **Waiting for your file...**\n\nPlease send me your translated `.ass` or `.srt` subtitle file now!")


# STEP 3.5: Catch Custom Subtitle File
@Client.on_message(filters.document & filters.private & is_auth)
async def catch_custom_subtitle(client, message):
    user_id = message.from_user.id
    state = USER_ENCODE_STATE.get(user_id)
    
    if state and state.get("waiting_for_sub"):
        file_name = message.document.file_name or ""
        if not file_name.lower().endswith(('.ass', '.srt')): 
            return await message.reply_text("⚠️ Invalid format! Please send a `.ass` or `.srt` file only.")
            
        USER_ENCODE_STATE[user_id]["sub_msg"] = message
        USER_ENCODE_STATE[user_id]["waiting_for_sub"] = False
        
        await message.reply_text("✅ Custom Subtitle received!")
        await ask_quality_buttons(message)


# STEP 4: Ask For Quality
async def ask_quality_buttons(message_obj):
    buttons = [
        [InlineKeyboardButton("🌟 Original Quality", callback_data="enc_qual_OG")],
        [InlineKeyboardButton("📺 2160p (4K)", callback_data="enc_qual_2160"), InlineKeyboardButton("🖥 1080p", callback_data="enc_qual_1080")],
        [InlineKeyboardButton("📱 720p", callback_data="enc_qual_720"), InlineKeyboardButton("📻 480p", callback_data="enc_qual_480")]
    ]
    text = "**Final Step:** Please select the compression/quality resolution for the video:"
    if hasattr(message_obj, "edit_text"):
        await message_obj.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message_obj.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


# STEP 5: Final Execution 
@Client.on_callback_query(filters.regex(r"^enc_qual_(OG|2160|1080|720|480)$") & is_auth)
async def interactive_encode_execute(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in USER_ENCODE_STATE: 
        return await callback_query.answer("⚠️ Session Expired. Please send /encode again.", show_alert=True)
    
    quality = callback_query.matches[0].group(1)
    state = USER_ENCODE_STATE[user_id]
    
    sub_mode = state["sub_mode"]
    sub_source = state["sub_source"]
    
    status_msg = await callback_query.message.edit_text("⏳ **Processing Started!**\n📥 Downloading Video...")
    
    try:
        # 1. Download Video
        video_path = await state["video_msg"].download()
        sub_path = None
        
        # 2. Handle Subtitle Fetching based on user choice
        if sub_mode != "none":
            if sub_source == "custom":
                await status_msg.edit_text("📥 Downloading your Custom Subtitle...")
                sub_msg = state["sub_msg"]
                sub_path = await sub_msg.download(file_name=os.path.join(encode_dir, sub_msg.document.file_name))
            
            elif sub_source == "existing" and sub_mode == "hard":
                await status_msg.edit_text("⏳ Extracting existing subtitle from video for Hardcoding...")
                sub_path = await extract_subs(video_path, callback_query.message, user_id)
                if not sub_path or not os.path.exists(sub_path):
                    await status_msg.edit_text("⚠️ Warning: No default subtitle found in this video to hardcode. Encoding without subtitle...")
                    sub_mode = "none"
        
        # 3. Start Encoding
        await status_msg.edit_text(f"⚙️ **Encoding Started...**\nQuality: {quality}p | Mode: {sub_mode.capitalize()}code\n*(Please wait, this may take a while)*")
        
        out_file = await encode(video_path, callback_query.message, status_msg, custom_sub_path=sub_path, sub_mode=sub_mode, custom_quality=quality)
        
        # 4. Upload Result
        if out_file and os.path.exists(out_file):
            await status_msg.edit_text("📤 **Uploading...**")
            
            # Thumbnail Logic Fix
            thumb_path = None
            dur = get_duration(out_file)
            if dur > 0:
                thumb_path = get_thumbnail(out_file, encode_dir, dur // 2)
            
            await client.send_video(
                chat_id=callback_query.message.chat.id,
                video=out_file,
                caption=f"✅ **Encoded Successfully!**\n⚙️ Quality: {quality}p\n📝 Mode: {sub_mode.capitalize()}code",
                thumb=thumb_path,
                duration=dur,
                supports_streaming=True
            )
            await status_msg.delete()
            os.remove(out_file)
            
            if thumb_path and os.path.exists(thumb_path):
                os.remove(thumb_path)
        else:
            await status_msg.edit_text("❌ Encoding failed! Output file was not generated. (Possible Codec or FFmpeg issue)")
            
        # Cleanup Memory
        if os.path.exists(video_path): 
            os.remove(video_path)
        if sub_path and os.path.exists(sub_path): 
            os.remove(sub_path)
            
        # Clear state safely
        if user_id in USER_ENCODE_STATE:
            del USER_ENCODE_STATE[user_id]

    except Exception as e:
        await status_msg.edit_text(f"❌ An error occurred during the process:\n`{e}`")
        if user_id in USER_ENCODE_STATE:
            del USER_ENCODE_STATE[user_id]
