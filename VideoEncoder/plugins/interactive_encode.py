import os
import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from VideoEncoder import encode_dir
from VideoEncoder.utils.database.access_db import db
from VideoEncoder.utils.encoding import encode

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
        "Aap is bot ko use karne ke liye authorized nahi hain. Kripya Admin se sampark karein.\n\n"
        f"🔗 **Support/Join:** [Click Here]({link})"
    )
    btn = InlineKeyboardMarkup([[InlineKeyboardButton("Contact Admin 👤", url=f"https://t.me/{MY_USERNAME}")]])
    await message.reply_text(text, reply_markup=btn, disable_web_page_preview=True)
    return False

is_auth = filters.create(auth_filter_func)

USER_ENCODE_STATE = {}
FONT_DIR = "VideoEncoder/utils/extras/fonts"

# =========================================================
# FONT HANDLERS
# =========================================================
@Client.on_message(filters.command("addfont") & filters.private)
async def add_custom_font(client, message):
    if not await is_admin(message.from_user.id): 
        return await message.reply_text("❌ Only Admins can add custom fonts.")
        
    if not message.reply_to_message or not message.reply_to_message.document: 
        return await message.reply_text("⚠️ Font file (.ttf/.otf) ke reply mein `/addfont [Name]` likhein.")
        
    doc = message.reply_to_message.document
    if not doc.file_name.endswith(('.ttf', '.otf', '.TTF', '.OTF')): 
        return await message.reply_text("⚠️ Sirf `.ttf` ya `.otf` extensions hi allow hain.")
        
    if len(message.command) < 2: 
        return await message.reply_text("⚠️ Kripya font ka naam dein: `/addfont Roboto`")
    
    font_name = " ".join(message.command[1:])
    ext = os.path.splitext(doc.file_name)[1]
    file_name = f"{font_name}{ext}"
    file_path = os.path.join(FONT_DIR, file_name)
    
    status = await message.reply_text("📥 Font ko Database mein save kiya jaa raha hai...")
    if not os.path.isdir(FONT_DIR): os.makedirs(FONT_DIR)
    await message.reply_to_message.download(file_name=file_path)
    
    try:
        await db.add_font(font_name, doc.file_id, file_name)
        await status.edit_text(f"✅ Aapka font **{font_name}** Database mein save ho gaya hai!")
    except Exception as e:
        await status.edit_text("❌ Database error. Make sure `add_font` is in database.py")

@Client.on_message(filters.command("removefont") & filters.private)
async def remove_font(client, message):
    if not await is_admin(message.from_user.id): 
        return await message.reply_text("❌ Only Admins can remove custom fonts.")
    try:
        await db.remove_active_font()
        await message.reply_text("🗑 Custom font deactivate kar diya gaya hai. Ab default font use hoga.")
    except:
        await message.reply_text("❌ Database error.")

@Client.on_message(filters.command(["font", "fonts"]) & filters.private)
async def list_fonts(client, message):
    if not await is_admin(message.from_user.id): 
        return await message.reply_text("❌ Sirf Admins fonts dekh sakte hain.")
    
    try:
        fonts = await db.db.custom_fonts.find().to_list(length=100)
        if not fonts:
            return await message.reply_text("📁 Database mein koi custom font nahi mila.")
            
        text = "🔠 **Saved Fonts:**\n\n"
        for f in fonts:
            status = "✅ Active" if f.get("active") else "❌ Inactive"
            text += f"• **{f['font_name']}** `{f['file_name']}` - {status}\n"
            
        await message.reply_text(text)
    except Exception as e:
        await message.reply_text(f"❌ Error fetching fonts: {e}")

# =========================================================
# INTERACTIVE ENCODE MENU
# =========================================================
@Client.on_message((filters.command("encode") | filters.document) & filters.private & is_auth)
async def interactive_encode_start(client, message):
    user_id = message.from_user.id
    
    if message.document:
        if not message.document.file_name.endswith(('.ass', '.srt')): return 
            
        if not message.reply_to_message or not message.reply_to_message.video:
            return await message.reply_text("⚠️ Apni `.ass/.srt` subtitle file kisi **Video** ke reply mein bhejein!")
        
        USER_ENCODE_STATE[user_id] = {"video_msg": message.reply_to_message, "sub_msg": message, "sub_mode": None, "quality": None}
        buttons = [
            [InlineKeyboardButton("🎬 Softcode Subtitle", callback_data="sub_soft")],
            [InlineKeyboardButton("🔥 Hardcode Subtitle", callback_data="sub_hard")]
        ]
        return await message.reply_text("✅ Custom Subtitle mil gaya!\n\n**Step 1:** Aap isey kaise encode karna chahte hain?", reply_markup=InlineKeyboardMarkup(buttons))

    if message.text and message.text.startswith("/encode"):
        if not message.reply_to_message or not message.reply_to_message.video:
            return await message.reply_text("⚠️ Kisi **Video** par reply karke `/encode` command use karein.")
        
        USER_ENCODE_STATE[user_id] = {"video_msg": message.reply_to_message, "sub_msg": None, "sub_mode": None, "quality": None}
        buttons = [
            [InlineKeyboardButton("🚫 No Subtitle (Direct Encode)", callback_data="sub_none")],
            [InlineKeyboardButton("🎬 Softcode Existing Subtitle", callback_data="sub_soft")],
            [InlineKeyboardButton("🔥 Hardcode Existing Subtitle", callback_data="sub_hard")]
        ]
        await message.reply_text("**Step 1:** Is video mein Subtitle ka kya karna hai?", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r"^sub_(none|soft|hard)$") & is_auth)
async def interactive_encode_quality(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in USER_ENCODE_STATE: 
        return await callback_query.answer("⚠️ Session Expire ho gaya hai. Dobara command bhejein.", show_alert=True)
    
    sub_choice = callback_query.matches[0].group(1)
    USER_ENCODE_STATE[user_id]["sub_mode"] = None if sub_choice == "none" else sub_choice

    buttons = [
        [InlineKeyboardButton("🌟 Original Quality", callback_data="qual_OG")],
        [InlineKeyboardButton("📺 2160p (4K)", callback_data="qual_2160"), InlineKeyboardButton("🖥 1080p", callback_data="qual_1080")],
        [InlineKeyboardButton("📱 720p", callback_data="qual_720"), InlineKeyboardButton("📻 480p", callback_data="qual_480")]
    ]
    await callback_query.message.edit_text("**Step 2:** Video ki compression/quality resolution select karein:", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r"^qual_(OG|2160|1080|720|480)$") & is_auth)
async def interactive_encode_execute(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in USER_ENCODE_STATE: 
        return await callback_query.answer("⚠️ Session Expire ho gaya hai. Dobara command bhejein.", show_alert=True)
    
    quality = callback_query.matches[0].group(1)
    state = USER_ENCODE_STATE[user_id]
    
    status_msg = await callback_query.message.edit_text("⏳ **Processing Shuru ho gayi hai!**\n📥 Video download ho rahi hai...")
    
    try:
        video_path = await state["video_msg"].download()
        sub_path = await state["sub_msg"].download(file_name=os.path.join(encode_dir, state["sub_msg"].document.file_name)) if state["sub_msg"] else None
        
        await status_msg.edit_text(f"⚙️ **Encoding Started...**\nQuality: {quality}p | Mode: {state['sub_mode'] or 'Direct'}\n*(Kripya thoda intezaar karein)*")
        
        out_file = await encode(video_path, callback_query.message, status_msg, custom_sub_path=sub_path, sub_mode=state["sub_mode"], custom_quality=quality)
        
        if out_file and os.path.exists(out_file):
            await status_msg.edit_text("📤 **Upload ho raha hai...**")
            await client.send_video(callback_query.message.chat.id, out_file, caption=f"✅ **Encoded Successfully!**\n⚙️ Quality: {quality}p\n📝 Mode: {state['sub_mode'] or 'Direct'}")
            await status_msg.delete()
            os.remove(out_file)
        else:
            await status_msg.edit_text("❌ Encoding fail ho gayi! Output file nahi bani.")
            
        if os.path.exists(video_path): os.remove(video_path)
        if sub_path and os.path.exists(sub_path): os.remove(sub_path)
        del USER_ENCODE_STATE[user_id]

    except Exception as e:
        await status_msg.edit_text(f"❌ Process ke dauran ek error aagaya:\n`{e}`")
