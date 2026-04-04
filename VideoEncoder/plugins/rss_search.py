import os
import asyncio
import feedparser
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from urllib.parse import quote
from ..utils.encoding import extract_subs

# Global dictionary for pagination
SEARCH_RESULTS = {}

RSS_URLS = [
    "https://nyaa.si/?page=rss&q={query}&c=0_0&f=0",
    "https://subsplease.org/rss/?r=1080" # Subsplease search api is different, but for nyaa this works best
]

@Client.on_message(filters.command("search"))
async def search_anime(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: /search [anime name]")
    
    query = quote(" ".join(message.command[1:]))
    await message.reply_text("🔍 RSS Feeds mein dhund raha hu...")
    
    results = []
    # Nyaa feed parsing
    feed = feedparser.parse(RSS_URLS[0].format(query=query))
    for entry in feed.entries:
        results.append({
            "title": entry.title,
            "link": entry.link # Magnet/Torrent link
        })
    
    if not results:
        return await message.reply_text("❌ Koi file nahi mili.")
    
    # Save results for pagination
    user_id = message.from_user.id
    SEARCH_RESULTS[user_id] = results
    
    await send_search_page(client, message.chat.id, user_id, 0)

async def send_search_page(client, chat_id, user_id, page):
    results = SEARCH_RESULTS.get(user_id, [])
    if not results:
        return
    
    item = results[page]
    text = f"🎬 **Title:** `{item['title']}`\n\n📄 **Page:** {page+1}/{len(results)}"
    
    buttons = []
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"page_{page-1}"))
    if page < len(results) - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page+1}"))
        
    buttons.append([InlineKeyboardButton("⬇️ Download & Extract Subs", callback_data=f"dl_{page}")])
    if nav_buttons:
        buttons.append(nav_buttons)
        
    await client.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r"^page_(\d+)"))
async def paginate_search(client, callback_query):
    page = int(callback_query.matches[0].group(1))
    user_id = callback_query.from_user.id
    
    results = SEARCH_RESULTS.get(user_id, [])
    item = results[page]
    text = f"🎬 **Title:** `{item['title']}`\n\n📄 **Page:** {page+1}/{len(results)}"
    
    buttons = []
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"page_{page-1}"))
    if page < len(results) - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page+1}"))
        
    buttons.append([InlineKeyboardButton("⬇️ Download & Extract Subs", callback_data=f"dl_{page}")])
    if nav_buttons:
        buttons.append(nav_buttons)
        
    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r"^dl_(\d+)"))
async def download_torrent(client, callback_query):
    page = int(callback_query.matches[0].group(1))
    user_id = callback_query.from_user.id
    item = SEARCH_RESULTS[user_id][page]
    
    await callback_query.answer("Download shuru ho raha hai...", show_alert=True)
    msg = await callback_query.message.reply_text("⏳ Downloading via Aria2c...")
    
    # Note: Yahan tumhe aria2p ka use karke file download karni hogi.
    # Main ek dummy filepath le raha hu integration ke liye:
    downloaded_filepath = await mock_aria2_download(item['link']) # Implement your Aria2 logic here
    
    await msg.edit_text("✅ Download complete! Ab subtitle extract kar raha hu...")
    
    sub_path = await extract_subs(downloaded_filepath, msg, user_id)
    if sub_path and os.path.exists(sub_path):
        await client.send_document(
            chat_id=callback_query.message.chat.id, 
            document=sub_path,
            caption="📁 Yeh rahi original subtitle file. \n\nAb apni **Hindi Subtitle File (.ass/.srt)** mujhe bhejo, aur reply mein us video file ko tag karna."
        )
    else:
        await msg.edit_text("⚠️ Koi subtitle nahi mila is video mein. Tum sidha apni file bhej sakte ho.")
