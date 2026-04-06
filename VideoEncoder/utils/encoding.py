
import asyncio
import json
import math
import os
import re
import subprocess
import time
import random

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .. import LOGGER, download_dir, encode_dir
from .database.access_db import db
from .display_progress import TimeFormatter

# =========================================================
# 🔴 AUTHORIZATION SETUP
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
    if await check_auth(user_id):
        return True
    
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

# Global State for Interactive Encoding
USER_ENCODE_STATE = {}

FONT_DIR = "VideoEncoder/utils/extras/fonts"
if not os.path.isdir(FONT_DIR):
    os.makedirs(FONT_DIR)

# =========================================================
# CORE ENCODING FUNCTIONS
# =========================================================
def get_codec(filepath, channel='v:0'):
    try:
        output = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', channel,
                                          '-show_entries', 'stream=codec_name,codec_tag_string', '-of',
                                          'default=nokey=1:noprint_wrappers=1', filepath])
        return output.decode('utf-8').split()
    except Exception as e:
        return []

def get_media_streams(filepath):
    try:
        cmd = ['ffprobe', '-hide_banner', '-print_format', 'json', '-show_streams', filepath]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        return json.loads(output.decode('utf-8')).get('streams', [])
    except Exception as e:
        return []

async def extract_subs(filepath, msg, user_id):
    path, extension = os.path.splitext(filepath)
    name = os.path.basename(path)
    check = get_codec(filepath, channel='s:0')
    if check == []:
        return None
    elif check == 'pgs':
        return None
    else:
        output = os.path.join(encode_dir, str(msg.id) + '.ass')

    try:
        subprocess.call(['ffmpeg', '-y', '-i', filepath, '-map', 's:0', output])
        try:
            subprocess.call(['mkvextract', 'attachments', filepath, '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16',
                            '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30', '31', '32', '33', '34', '35', '36', '37', '38', '39', '40'])
        except:
            pass
        return output
    except Exception as e:
        return None

# MODIFIED ENCODE FUNCTION
async def encode(filepath, message, msg, audio_map=None, custom_sub_path=None, sub_mode=None, custom_quality=None):
    ex = await db.get_extensions(message.from_user.id)
    path, extension = os.path.splitext(filepath)
    name = os.path.basename(path)

    if ex == 'MP4':
        output_filepathh = os.path.join(encode_dir, name + '.mp4')
    elif ex == 'AVI':
        output_filepathh = os.path.join(encode_dir, name + '.avi')
    else:
        output_filepathh = os.path.join(encode_dir, name + '.mkv')

    output_filepath = output_filepathh
    subtitles_path = os.path.join(encode_dir, str(msg.id) + '.ass')

    progress = os.path.join(download_dir, "process.txt")
    with open(progress, 'w') as f:
        pass

    x265 = await db.get_hevc(message.from_user.id)
    video_i = get_codec(filepath, channel='v:0')
    codec = '-c:v libx265' if x265 else '-c:v libx264' if video_i else ''

    tune = await db.get_tune(message.from_user.id)
    tunevideo = '-tune animation' if tune else '-tune film'

    cbb = await db.get_cabac(message.from_user.id)
    cabac = '-coder 1' if cbb else '-coder 0'

    rf = await db.get_reframe(message.from_user.id)
    reframe = f'-refs {rf}' if rf in ['4', '8', '16'] else ''

    b = await db.get_bits(message.from_user.id)
    codec += ' -pix_fmt yuv420p10le' if b else ' -pix_fmt yuv420p'

    crf = await db.get_crf(message.from_user.id)
    Crf = f'-crf {crf}' if crf else '-crf 26'

    fr = await db.get_frame(message.from_user.id)
    frame = f'-r {fr}' if fr in ['ntsc', 'pal', 'film', '30', '60'] else '-r 24000/1001' if fr == '23.976' else ''

    ap = await db.get_aspect(message.from_user.id)
    aspect = '-aspect 16:9' if ap else ''

    p = await db.get_preset(message.from_user.id)
    presets = {'uf': 'ultrafast', 'sf': 'superfast', 'vf': 'veryfast', 'f': 'fast', 'm': 'medium'}
    preset = f"-preset {presets.get(p, 'slow')}"

    video_opts = f'-profile:v main -map 0:v? -map_chapters 0 -map_metadata 0' if x265 else f'{cabac} {reframe} -profile:v main -map 0:v? -map_chapters 0 -map_metadata 0'

    m = await db.get_metadata_w(message.from_user.id)
    metadata = '-metadata title=Cantarellabots -metadata:s:v title=Cantarellabots -metadata:s:a title=Cantarellabots' if m else ''

    h = await db.get_hardsub(message.from_user.id)
    s = await db.get_subtitles(message.from_user.id)
    
    extra_inputs = []
    if custom_sub_path and sub_mode:
        if sub_mode == 'soft':
            extra_inputs = ['-i', custom_sub_path]
            sub_codec = 'srt' if custom_sub_path.endswith('.srt') else 'ass'
            subtitles = '-map 1:s -c:s mov_text' if ex == 'MP4' else '' if ex == 'AVI' else f'-map 1:s -c:s {sub_codec}'
        elif sub_mode == 'hard':
            subtitles = ''
    else:
        subs_i = get_codec(filepath, channel='s:0')
        subtitles = '' if subs_i == [] else '' if (s and h) else '-c:s mov_text -c:t copy -map 0:t? -map 0:s?' if (s and ex == 'MP4') else '' if (s and ex == 'AVI') else '-c:s copy -c:t copy -map 0:t? -map 0:s?' if s else ''

    # 🔴 QUALITY OVERRIDE LOGIC
    r = custom_quality if custom_quality else await db.get_resolution(message.from_user.id)
    w = await db.get_watermark(message.from_user.id)
    
    if r == 'OG': watermark = ''
    elif r == '2160': watermark = '-vf scale=3840:2160'
    elif r == '1080': watermark = '-vf scale=1920:1080'
    elif r == '720': watermark = '-vf scale=1280:720'
    elif r == '480': watermark = '-vf scale=852:480'
    else: watermark = '-vf scale=852:480'
        
    if w:
        watermark += '-vf ' if r == 'OG' else ','
        watermark += 'subtitles=VideoEncoder/utils/extras/watermark.ass'

    # FONT APPLY LOGIC (Using your updated database.py methods)
    abs_font_dir = os.path.abspath(FONT_DIR)
    active_font_name = None
    
    active_font = await db.get_active_font()

    if active_font:
        active_font_name = active_font["font_name"]
        font_path = os.path.join(FONT_DIR, active_font["file_name"])
        if not os.path.exists(font_path):
            client = message._client
            await client.download_media(active_font["file_id"], file_name=font_path)

    def get_hardsub_string(path):
        return f"{path}:fontsdir='{abs_font_dir}':force_style='Fontname={active_font_name}'" if active_font_name else path

    if custom_sub_path and sub_mode == 'hard':
        watermark += '-vf ' if (r == 'OG' and not w) else ','
        watermark += f"subtitles={get_hardsub_string(custom_sub_path)}"
    elif h and not (custom_sub_path and sub_mode):
        watermark += '-vf ' if (r == 'OG' and not w) else ','
        watermark += f"subtitles={get_hardsub_string(subtitles_path)}"

    sr = await db.get_samplerate(message.from_user.id)
    sample = '-ar 44100' if sr == '44.1K' else '-ar 48000' if sr == '48K' else ''

    bit = await db.get_bitrate(message.from_user.id)
    bitrates_dict = {'400': '400k', '320': '320k', '256': '256k', '224': '224k', '192': '192k', '160': '160k', '128': '128k'}
    bitrate = f"-b:a {bitrates_dict[bit]}" if bit in bitrates_dict else ''

    a = await db.get_audio(message.from_user.id)
    a_i = get_codec(filepath, channel='a:0')
    if a_i == []:
        audio_opts = ''
    else:
        audios = {'dd': 'ac3', 'aac': 'aac', 'vorbis': 'libvorbis', 'alac': 'alac'}
        if a in audios: audio_opts = f'-c:a {audios[a]} {sample} {bitrate}'
        elif a == 'opus': audio_opts = f'-c:a libopus -vbr on {sample} {bitrate}'
        else: audio_opts = '-c:a copy'

        if audio_map:
            map_opts = "".join([f" -map 0:{idx}" for idx in audio_map])
            audio_opts = f"{audio_opts} {map_opts} -disposition:a:0 default"
        else:
             audio_opts += " -map 0:a?"

    c = await db.get_channels(message.from_user.id)
    channels = '' if '-c:a copy' in audio_opts else '-rematrix_maxval 1.0 -ac 1' if c == '1.0' else '-rematrix_maxval 1.0 -ac 2' if c == '2.0' else '-rematrix_maxval 1.0 -ac 3' if c == '2.1' else '-rematrix_maxval 1.0 -ac 6' if c == '5.1' else '-rematrix_maxval 1.0 -ac 8' if c == '7.1' else ''

    finish = '-threads 8'
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-progress', progress, '-hwaccel', 'auto', '-y', '-i', filepath]
    if extra_inputs: command.extend(extra_inputs)
    command.extend((codec.split() + preset.split() + frame.split() + tunevideo.split() + aspect.split() + video_opts.split() + Crf.split() + watermark.split() + metadata.split() + subtitles.split() + audio_opts.split() + channels.split() + finish.split()))
    
    proc = await asyncio.create_subprocess_exec(*command, output_filepath, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await handle_progress(proc, msg, message, filepath)
    
    stdout, stderr = await proc.communicate()
    if not os.path.isfile(output_filepath) or os.path.getsize(output_filepath) == 0:
        if os.path.isfile(output_filepath): os.remove(output_filepath)
        return None
    return output_filepath

async def media_info(saved_file_path):
    process = subprocess.Popen(['ffmpeg', "-hide_banner", '-i', saved_file_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, stderr = process.communicate()
    output = stdout.decode().strip()
    duration = re.search(r"Duration:\s*(\d*):(\d*):(\d+\.?\d*)[\s\w*$]", output)
    bitrates = re.search(r"bitrate:\s*(\d+)[\s\w*$]", output)
    total_seconds = (int(duration.group(1)) * 3600) + (int(duration.group(2)) * 60) + math.floor(float(duration.group(3))) if duration else None
    bitrate = bitrates.group(1) if bitrates else None
    return total_seconds, bitrate

async def handle_progress(proc, msg, message, filepath):
    COMPRESSION_START_TIME = time.time()
    status = download_dir + "status.json"
    with open(status, 'w') as f: json.dump({'running': True, 'message': msg.id, 'user': message.from_user.id}, f, indent=2)
    with open(status, 'r+') as f:
        statusMsg = json.load(f)
        statusMsg.update({'pid': proc.pid, 'message': msg.id, 'user': message.from_user.id})
        f.seek(0)
        json.dump(statusMsg, f, indent=2)
    while proc.returncode == None:
        await asyncio.sleep(5)
        try:
            with open(download_dir + 'process.txt', 'r+') as file:
                text = file.read()
                frame = re.findall(r"frame=(\d+)", text)
                time_in_us = re.findall(r"out_time_ms=(\d+)", text)
                progress = re.findall(r"progress=(\w+)", text)
                speed = re.findall(r"speed=(\d+\.?\d*)", text)
                
                speed = speed[-1] if len(speed) else 1
                time_in_us = time_in_us[-1] if len(time_in_us) else 1
                if len(progress) and progress[-1] == "end": break
                break
                
            elapsed_time = int(time_in_us)/1000000
            total_time, bitrate = await media_info(filepath)
            difference = math.floor((total_time - elapsed_time) / float(speed))
            ETA = TimeFormatter(difference) if difference > 0 else "-"
            percentage = math.floor(elapsed_time * 100 / total_time)
            progress_str = "<b>Encoding Video:</b> {0}%\n{1}{2}".format(
                round(percentage, 2),
                ''.join(['█' for i in range(math.floor(percentage / 10))]),
                ''.join(['░' for i in range(10 - math.floor(percentage / 10))])
            )
            stats = f'{progress_str} \n• ETA: {ETA}'
            await msg.edit(text=stats, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Cancel', callback_data='cancel'), InlineKeyboardButton('Stats', callback_data='stats')]]))
        except:
            pass

# =========================================================
# 🔴 FONT HANDLERS (ADMIN ONLY)
# =========================================================
@Client.on_message(filters.command("addfont"))
async def add_custom_font(client, message):
    if not await is_admin(message.from_user.id): return await message.reply_text("❌ Only Admins can add custom fonts.")
    if not message.reply_to_message or not message.reply_to_message.document: return await message.reply_text("⚠️ Please reply to a `.ttf` or `.otf` font file with `/addfont [Name]`.")
    doc = message.reply_to_message.document
    if not doc.file_name.endswith(('.ttf', '.otf', '.TTF', '.OTF')): return await message.reply_text("⚠️ Only `.ttf` or `.otf` extensions are allowed.")
    if len(message.command) < 2: return await message.reply_text("⚠️ Please provide a font name: `/addfont Roboto`")
    
    font_name = " ".join(message.command[1:])
    ext = os.path.splitext(doc.file_name)[1]
    file_name = f"{font_name}{ext}"
    file_path = os.path.join(FONT_DIR, file_name)
    
    status = await message.reply_text("📥 Saving font to Database...")
    await message.reply_to_message.download(file_name=file_path)
    
    await db.add_font(font_name, doc.file_id, file_name)
    await status.edit_text(f"✅ Your font **{font_name}** has been saved to the Database! It will remain safe even after redeploys.")

@Client.on_message(filters.command("removefont"))
async def remove_font(client, message):
    if not await is_admin(message.from_user.id): return await message.reply_text("❌ Only Admins can remove custom fonts.")
    await db.remove_active_font()
    await message.reply_text("🗑 Custom font has been deactivated. The default font will be used.")


# =========================================================
# 🔴 ULTIMATE INTERACTIVE ENCODE WORKFLOW
# =========================================================

# STEP 1: Command /encode on video or replying with custom subtitle
@Client.on_message((filters.command("encode") | filters.document) & filters.private & is_auth)
async def interactive_encode_start(client, message):
    user_id = message.from_user.id
    
    # CASE A: User replies to a video with a subtitle document
    if message.document:
        if not message.document.file_name.endswith(('.ass', '.srt')): return 
        if not message.reply_to_message or not message.reply_to_message.video:
            return await message.reply_text("⚠️ Please send your `.ass/.srt` subtitle file as a reply to a **Video**!")
        
        USER_ENCODE_STATE[user_id] = {"video_msg": message.reply_to_message, "sub_msg": message, "sub_mode": None, "quality": None}
        buttons = [
            [InlineKeyboardButton("🎬 Softcode Subtitle", callback_data="sub_soft")],
            [InlineKeyboardButton("🔥 Hardcode Subtitle", callback_data="sub_hard")]
        ]
        return await message.reply_text("✅ Custom Subtitle received!\n\n**Step 1:** How would you like to encode this?", reply_markup=InlineKeyboardMarkup(buttons))

    # CASE B: User replies to a video with /encode
    if message.text and message.text.startswith("/encode"):
        if not message.reply_to_message or not message.reply_to_message.video:
            return await message.reply_text("⚠️ Please reply to a **Video** with the `/encode` command.")
        
        USER_ENCODE_STATE[user_id] = {"video_msg": message.reply_to_message, "sub_msg": None, "sub_mode": None, "quality": None}
        buttons = [
            [InlineKeyboardButton("🚫 No Subtitle (Direct Encode)", callback_data="sub_none")],
            [InlineKeyboardButton("🎬 Softcode Existing Subtitle", callback_data="sub_soft")],
            [InlineKeyboardButton("🔥 Hardcode Existing Subtitle", callback_data="sub_hard")]
        ]
        await message.reply_text("**Step 1:** What should we do with the subtitle in this video?", reply_markup=InlineKeyboardMarkup(buttons))

# STEP 2: Handle Subtitle Choice & Ask for Quality
@Client.on_callback_query(filters.regex(r"^sub_(none|soft|hard)$") & is_auth)
async def interactive_encode_quality(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in USER_ENCODE_STATE: return await callback_query.answer("⚠️ Session Expired. Please send the command again.", show_alert=True)
    
    sub_choice = callback_query.matches[0].group(1)
    USER_ENCODE_STATE[user_id]["sub_mode"] = None if sub_choice == "none" else sub_choice

    buttons = [
        [InlineKeyboardButton("🌟 Original Quality", callback_data="qual_OG")],
        [InlineKeyboardButton("📺 2160p (4K)", callback_data="qual_2160"), InlineKeyboardButton("🖥 1080p", callback_data="qual_1080")],
        [InlineKeyboardButton("📱 720p", callback_data="qual_720"), InlineKeyboardButton("📻 480p", callback_data="qual_480")]
    ]
    await callback_query.message.edit_text("**Step 2:** Please select the compression/quality resolution for the video:", reply_markup=InlineKeyboardMarkup(buttons))

# STEP 3: Final Execution (Download -> Encode -> Upload)
@Client.on_callback_query(filters.regex(r"^qual_(OG|2160|1080|720|480)$") & is_auth)
async def interactive_encode_execute(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in USER_ENCODE_STATE: return await callback_query.answer("⚠️ Session Expired. Please send the command again.", show_alert=True)
    
    quality = callback_query.matches[0].group(1)
    state = USER_ENCODE_STATE[user_id]
    
    status_msg = await callback_query.message.edit_text("⏳ **Processing Started!**\n📥 Downloading Video...")
    
    try:
        video_path = await state["video_msg"].download()
        sub_path = await state["sub_msg"].download(file_name=os.path.join(encode_dir, state["sub_msg"].document.file_name)) if state["sub_msg"] else None
        
        await status_msg.edit_text(f"⚙️ **Encoding Started...**\nQuality: {quality}p | Mode: {state['sub_mode'] or 'Direct'}\n*(This may take some time)*")
        
        # Trigger Encode Logic
        out_file = await encode(video_path, callback_query.message, status_msg, custom_sub_path=sub_path, sub_mode=state["sub_mode"], custom_quality=quality)
        
        if out_file and os.path.exists(out_file):
            await status_msg.edit_text("📤 **Uploading...**")
            await client.send_video(callback_query.message.chat.id, out_file, caption=f"✅ **Encoded Successfully!**\n⚙️ Quality: {quality}\n📝 Subtitle: {state['sub_mode'] or 'None'}")
            await status_msg.delete()
            os.remove(out_file)
        else:
            await status_msg.edit_text("❌ Encoding failed! Output file not generated.")
            
        # Clean up memory
        if os.path.exists(video_path): os.remove(video_path)
        if sub_path and os.path.exists(sub_path): os.remove(sub_path)
        del USER_ENCODE_STATE[user_id]

    except Exception as e:
        await status_msg.edit_text(f"❌ An error occurred during the process:\n`{e}`")
