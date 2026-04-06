import asyncio
import json
import math
import os
import re
import subprocess
import time
import random

from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .. import LOGGER, download_dir, encode_dir
from .database.access_db import db
from .display_progress import TimeFormatter

# =========================================================
# 🔴 AUTHORIZATION SETUP & GLOBALS
# =========================================================

MY_USERNAME = "i_killed_my_clan"
UNAUTH_LINKS = [
    "https://t.me/Anime_Crew_Network", 
    "https://t.me/Webtoon_Crew",       
    "https://t.me/Comicktown"          
]

async def check_auth(user_id):
    owner_id = str(os.getenv("OWNER_ID", "5585016974"))
    if str(user_id) in owner_id.split(): 
        return True
    
    auth_chats = await db.get_chat()
    if auth_chats and str(user_id) in auth_chats.split(): 
        return True
        
    sudo_users = await db.get_sudo()
    if sudo_users and str(user_id) in sudo_users.split(): 
        return True

    return False

async def is_admin(user_id):
    owner_id = str(os.getenv("OWNER_ID", "5585016974"))
    if str(user_id) in owner_id.split(): 
        return True
    
    sudo_users = await db.get_sudo()
    if sudo_users and str(user_id) in sudo_users.split(): 
        return True
        
    return False

async def auth_filter_func(flt, client, message):
    user_id = message.from_user.id
    if await check_auth(user_id):
        return True
    
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

if not os.path.isdir(FONT_DIR):
    os.makedirs(FONT_DIR)

# =========================================================
# ORIGINAL CORE ENCODING FUNCTIONS (UNCUT & ASYNC FIXED)
# =========================================================

def get_codec(filepath, channel='v:0'):
    try:
        output = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', channel,
                                          '-show_entries', 'stream=codec_name,codec_tag_string', '-of',
                                          'default=nokey=1:noprint_wrappers=1', filepath])
        return output.decode('utf-8').split()
    except subprocess.CalledProcessError as e:
        LOGGER.error(f"ffprobe failed for {filepath}: {e}")
        return []
    except Exception as e:
        LOGGER.error(f"ffprobe exception for {filepath}: {e}")
        return []

def get_media_streams(filepath):
    try:
        cmd = ['ffprobe', '-hide_banner', '-print_format', 'json', '-show_streams', filepath]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        return json.loads(output.decode('utf-8')).get('streams', [])
    except Exception as e:
        LOGGER.error(f"Failed to get media streams: {e}")
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
        # ASYNC FIX: Prevent bot freeze during subtitle extraction
        proc = await asyncio.create_subprocess_exec('ffmpeg', '-y', '-i', filepath, '-map', 's:0', output)
        await proc.communicate()
        
        try:
            subprocess.call(['mkvextract', 'attachments', filepath, '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16',
                            '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30', '31', '32', '33', '34', '35', '36', '37', '38', '39', '40'])
        except FileNotFoundError:
            LOGGER.warning("mkvextract not found, skipping attachments extraction.")
        except Exception as e:
            LOGGER.error(f"mkvextract failed: {e}")

        try:
            if os.name != 'nt':
                subprocess.run([f"mv -f *.JFPROJ *.FNT *.PFA *.ETX *.WOFF *.FOT *.TTF *.SFD *.VLW *.VFB *.PFB *.OTF *.GXF *.WOFF2 *.ODTTF *.BF *.CHR *.TTC *.BDF *.FON *.GF *.PMT *.AMFM  *.MF *.PFM *.COMPOSITEFONT *.PF2 *.GDR *.ABF *.VNF *.PCF *.SFP *.MXF *.DFONT *.UFO *.PFR *.TFM *.GLIF *.XFN *.AFM *.TTE *.XFT *.ACFM *.EOT *.FFIL *.PK *.SUIT *.NFTR *.EUF *.TXF *.CHA *.LWFN *.T65 *.MCF *.YTF *.F3F *.FEA *.SFT *.PFT /usr/share/fonts/"], shell=True)
                subprocess.run([f"mv -f *.jfproj *.fnt *.pfa *.etx *.woff *.fot *.ttf *.sfd *.vlw *.vfb *.pfb *.otf *.gxf *.woff2 *.odttf *.bf *.chr *.ttc *.bdf *.fon *.gf *.pmt *.amfm  *.mf *.pfm *.compositefont *.pf2 *.gdr *.abf *.vnf *.pcf *.sfp *.mxf *.dfont *.ufo *.pfr *.tfm *.glif *.xfn *.afm *.tte *.xft *.acfm *.eot *.ffil *.pk *.suit *.nftr *.euf *.txf *.cha *.lwfn *.t65 *.mcf *.ytf *.f3f *.fea *.sft *.pft /usr/share/fonts/ && fc-cache -f"], shell=True)
        except Exception as e:
            LOGGER.warning(f"Font moving failed: {e}")

        return output
    except Exception as e:
        LOGGER.error(f"Extract subs failed: {e}")
        return None

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

    progress_file = os.path.join(download_dir, "process.txt")
    with open(progress_file, 'w') as f:
        pass

    assert(output_filepath != filepath)

    if os.path.isfile(output_filepath):
        LOGGER.warning(f'"{output_filepath}": file already exists')
    else:
        LOGGER.info(filepath)

    x265 = await db.get_hevc(message.from_user.id)
    video_i = get_codec(filepath, channel='v:0')
    if video_i == []:
        codec = ''
    else:
        if x265:
            codec = '-c:v libx265'
        else:
            codec = '-c:v libx264'

    tune = await db.get_tune(message.from_user.id)
    if tune:
        tunevideo = '-tune animation'
    else:
        tunevideo = '-tune film'

    cbb = await db.get_cabac(message.from_user.id)
    if cbb:
        cabac = '-coder 1'
    else:
        cabac = '-coder 0'

    rf = await db.get_reframe(message.from_user.id)
    if rf == '4':
        reframe = '-refs 4'
    elif rf == '8':
        reframe = '-refs 8'
    elif rf == '16':
        reframe = '-refs 16'
    else:
        reframe = ''

    b = await db.get_bits(message.from_user.id)
    if not b:
        codec += ' -pix_fmt yuv420p'
    else:
        codec += ' -pix_fmt yuv420p10le'

    crf = await db.get_crf(message.from_user.id)
    if crf:
        Crf = f'-crf {crf}'
    else:
        await db.set_crf(message.from_user.id, crf=26)
        Crf = '-crf 26'

    fr = await db.get_frame(message.from_user.id)
    if fr == 'ntsc':
        frame = '-r ntsc'
    elif fr == 'pal':
        frame = '-r pal'
    elif fr == 'film':
        frame = '-r film'
    elif fr == '23.976':
        frame = '-r 24000/1001'
    elif fr == '30':
        frame = '-r 30'
    elif fr == '60':
        frame = '-r 60'
    else:
        frame = ''

    ap = await db.get_aspect(message.from_user.id)
    if ap:
        aspect = '-aspect 16:9'
    else:
        aspect = ''

    p = await db.get_preset(message.from_user.id)
    if p == 'uf':
        preset = '-preset ultrafast'
    elif p == 'sf':
        preset = '-preset superfast'
    elif p == 'vf':
        preset = '-preset veryfast'
    elif p == 'f':
        preset = '-preset fast'
    elif p == 'm':
        preset = '-preset medium'
    else:
        preset = '-preset slow'

    if x265:
        video_opts = f'-profile:v main  -map 0:v? -map_chapters 0 -map_metadata 0'
    else:
        video_opts = f'{cabac} {reframe} -profile:v main  -map 0:v? -map_chapters 0 -map_metadata 0'

    m = await db.get_metadata_w(message.from_user.id)
    if m:
        metadata = '-metadata title=Cantarellabots -metadata:s:v title=Cantarellabots -metadata:s:a title=Cantarellabots'
    else:
        metadata = ''

    h = await db.get_hardsub(message.from_user.id)
    s = await db.get_subtitles(message.from_user.id)
    
    extra_inputs = []
    
    if custom_sub_path and sub_mode:
        if sub_mode == 'soft':
            extra_inputs = ['-i', custom_sub_path]
            sub_codec = 'srt' if custom_sub_path.endswith('.srt') else 'ass'
            if ex == 'MP4':
                subtitles = '-map 1:s -c:s mov_text'
            elif ex == 'AVI':
                subtitles = ''
            else:
                subtitles = f'-map 1:s -c:s {sub_codec}'
        elif sub_mode == 'hard':
            subtitles = ''
    else:
        subs_i = get_codec(filepath, channel='s:0')
        if subs_i == []:
            subtitles = ''
        else:
            if s:
                if h:
                    subtitles = ''
                else:
                    if ex == 'MP4':
                        subtitles = '-c:s mov_text -c:t copy -map 0:t? -map 0:s?'
                    elif ex == 'AVI':
                        subtitles = ''
                    else:
                        subtitles = '-c:s copy -c:t copy -map 0:t? -map 0:s?'
            else:
                subtitles = ''

    r = custom_quality if custom_quality else await db.get_resolution(message.from_user.id)
    w = await db.get_watermark(message.from_user.id)
    
    if r == 'OG':
        watermark = ''
    elif r == '2160':
        watermark = '-vf scale=3840:2160'
    elif r == '1080':
        watermark = '-vf scale=1920:1080'
    elif r == '720':
        watermark = '-vf scale=1280:720'
    elif r == '576':
        watermark = '-vf scale=768:576'
    elif r == '480':
        watermark = '-vf scale=852:480'
    else:
        watermark = '-vf scale=852:480'
        
    if w:
        if r == 'OG':
            watermark += '-vf '
        else:
            watermark += ','
        watermark += 'subtitles=VideoEncoder/utils/extras/watermark.ass'

    abs_font_dir = os.path.abspath(FONT_DIR)
    active_font_name = None
    
    try:
        active_font = await db.get_active_font()
        if active_font:
            active_font_name = active_font["font_name"]
            font_path = os.path.join(FONT_DIR, active_font["file_name"])
            if not os.path.exists(font_path) and hasattr(message, '_client'):
                client = message._client
                await client.download_media(active_font["file_id"], file_name=font_path)
    except Exception as e:
        pass

    def get_hardsub_string(path):
        if active_font_name:
            return f"{path}:fontsdir='{abs_font_dir}':force_style='Fontname={active_font_name}'"
        return path

    if custom_sub_path and sub_mode == 'hard':
        if r == 'OG' and not w:
            watermark += '-vf '
        else:
            watermark += ','
        watermark += f"subtitles={get_hardsub_string(custom_sub_path)}"
    elif h and not (custom_sub_path and sub_mode):
        if r == 'OG' and not w:
            watermark += '-vf '
        else:
            watermark += ','
        watermark += f"subtitles={get_hardsub_string(subtitles_path)}"

    sr = await db.get_samplerate(message.from_user.id)
    if sr == '44.1K':
        sample = '-ar 44100'
    elif sr == '48K':
        sample = '-ar 48000'
    else:
        sample = ''

    bit = await db.get_bitrate(message.from_user.id)
    if bit == '400':
        bitrate = '-b:a 400k'
    elif bit == '320':
        bitrate = '-b:a 320k'
    elif bit == '256':
        bitrate = '-b:a 256k'
    elif bit == '224':
        bitrate = '-b:a 224k'
    elif bit == '192':
        bitrate = '-b:a 192k'
    elif bit == '160':
        bitrate = '-b:a 160k'
    elif bit == '128':
        bitrate = '-b:a 128k'
    else:
        bitrate = ''

    a = await db.get_audio(message.from_user.id)
    a_i = get_codec(filepath, channel='a:0')
    if a_i == []:
        audio_opts = ''
    else:
        if a == 'dd':
            audio_opts = f'-c:a ac3 {sample} {bitrate}'
        elif a == 'aac':
            audio_opts = f'-c:a aac {sample} {bitrate}'
        elif a == 'vorbis':
            audio_opts = f'-c:a libvorbis {sample} {bitrate}'
        elif a == 'alac':
            audio_opts = f'-c:a alac {sample} {bitrate}'
        elif a == 'opus':
            audio_opts = f'-c:a libopus -vbr on {sample} {bitrate}'
        else:
            audio_opts = '-c:a copy'

        if audio_map:
            map_opts = ""
            for idx in audio_map:
                map_opts += f" -map 0:{idx}"
            disposition_opts = " -disposition:a:0 default"
            audio_opts = f"{audio_opts} {map_opts} {disposition_opts}"
        else:
             audio_opts += " -map 0:a?"

    c = await db.get_channels(message.from_user.id)
    if '-c:a copy' in audio_opts:
        channels = ''
    elif c == '1.0':
        channels = '-rematrix_maxval 1.0 -ac 1'
    elif c == '2.0':
        channels = '-rematrix_maxval 1.0 -ac 2'
    elif c == '2.1':
        channels = '-rematrix_maxval 1.0 -ac 3'
    elif c == '5.1':
        channels = '-rematrix_maxval 1.0 -ac 6'
    elif c == '7.1':
        channels = '-rematrix_maxval 1.0 -ac 8'
    else:
        channels = ''

    finish = '-threads 8'

    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error',
               '-progress', progress_file, '-hwaccel', 'auto', '-y', '-i', filepath]
               
    if extra_inputs:
        command.extend(extra_inputs)
        
    command.extend((codec.split() + preset.split() + frame.split() + tunevideo.split() + aspect.split() + video_opts.split() + Crf.split() +
                   watermark.split() + metadata.split() + subtitles.split() + audio_opts.split() + channels.split() + finish.split()))
    
    proc = await asyncio.create_subprocess_exec(*command, output_filepath, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    
    # ASYNC FIX: Prevent deadlocks by running progress bar as a background task
    progress_task = asyncio.create_task(handle_progress(proc, msg, message, filepath))
    
    stdout, stderr = await proc.communicate()
    await progress_task # Wait for progress to finish updating
    
    e_response = stderr.decode().strip()
    t_response = stdout.decode().strip()
    
    if e_response:
        LOGGER.error(f"FFmpeg stderr: {e_response}")
    if t_response:
        LOGGER.info(f"FFmpeg stdout: {t_response}")

    if not os.path.isfile(output_filepath) or os.path.getsize(output_filepath) == 0:
        LOGGER.error(f"Encoding failed: {output_filepath} not created or is 0 bytes.")
        if os.path.isfile(output_filepath):
            os.remove(output_filepath)
        return None

    return output_filepath


def get_thumbnail(in_filename, path, ttl):
    out_filename = os.path.join(path, str(time.time()) + ".jpg")
    try:
        command = [
            'ffmpeg', '-hide_banner', '-loglevel', 'error',
            '-ss', str(ttl),
            '-i', in_filename,
            '-vframes', '1',
            '-y', out_filename
        ]
        subprocess.run(command, check=True, capture_output=True)
        if os.path.isfile(out_filename):
            return out_filename
        else:
            LOGGER.warning(f"Thumbnail file not created: {out_filename}")
            return None
    except subprocess.CalledProcessError as e:
        LOGGER.warning(f"Thumbnail generation failed (CalledProcessError): {e.stderr.decode().strip() if e.stderr else e}")
        return None
    except Exception as e:
        LOGGER.warning(f"Thumbnail generation failed: {e}")
        return None


def get_duration(filepath):
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries',
            'format=duration', '-of',
            'default=noprint_wrappers=1:nokey=1', filepath
        ]
        output = subprocess.check_output(cmd).decode('utf-8').strip()
        return int(float(output))
    except Exception as e:
        LOGGER.warning(f"ffprobe duration failed: {e}, falling back to hachoir")
        try:
            metadata = extractMetadata(createParser(filepath))
            if metadata and metadata.has("duration"):
                return metadata.get('duration').seconds
        except Exception as e:
            LOGGER.error(f"hachoir duration failed: {e}")
    return 0


def get_width_height(filepath):
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height', '-of',
            'csv=s=x:p=0', filepath
        ]
        output = subprocess.check_output(cmd).decode('utf-8').strip()
        width, height = map(int, output.split('x'))
        return width, height
    except Exception as e:
        LOGGER.warning(f"ffprobe width/height failed: {e}, falling back to hachoir")
        try:
            metadata = extractMetadata(createParser(filepath))
            if metadata and metadata.has("width") and metadata.has("height"):
                return metadata.get("width"), metadata.get("height")
        except Exception as e:
            LOGGER.error(f"hachoir width/height failed: {e}")
    return (1280, 720)


async def media_info(saved_file_path):
    # ASYNC FIX: Prevent bot freeze by using non-blocking subprocess
    process = await asyncio.create_subprocess_exec(
        'ffmpeg', "-hide_banner", '-i', saved_file_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    stdout, _ = await process.communicate()
    output = stdout.decode().strip()
    
    duration = re.search(r"Duration:\s*(\d*):(\d*):(\d+\.?\d*)[\s\w*$]", output)
    bitrates = re.search(r"bitrate:\s*(\d+)[\s\w*$]", output)

    if duration is not None:
        hours = int(duration.group(1))
        minutes = int(duration.group(2))
        seconds = math.floor(float(duration.group(3)))
        total_seconds = (hours * 60 * 60) + (minutes * 60) + seconds
    else:
        total_seconds = None
        
    if bitrates is not None:
        bitrate = bitrates.group(1)
    else:
        bitrate = None
        
    return total_seconds, bitrate


async def handle_progress(proc, msg, message, filepath):
    name = os.path.basename(filepath)
    COMPRESSION_START_TIME = time.time()
    LOGGER.info("ffmpeg_process: "+str(proc.pid))
    
    # Path fix so it doesn't fail
    status_file = os.path.join(download_dir, "status.json")
    process_file = os.path.join(download_dir, "process.txt")
    
    with open(status_file, 'w') as f:
        statusMsg = {'running': True, 'message': msg.id, 'user': message.from_user.id}
        json.dump(statusMsg, f, indent=2)
        
    with open(status_file, 'r+') as f:
        statusMsg = json.load(f)
        statusMsg['pid'] = proc.pid
        statusMsg['message'] = msg.id
        statusMsg['user'] = message.from_user.id
        f.seek(0)
        json.dump(statusMsg, f, indent=2)
        
# ASYNC FIX: Fetch total time only once to prevent bot lag
    total_time, bitrate = await media_info(filepath)
        
    while proc.returncode is None:
        await asyncio.sleep(5)
        try:
            with open(process_file, 'r') as file:
                text = file.read()
                
            time_in_us_match = re.findall(r"out_time_ms=(\d+)", text)
            speed_match = re.findall(r"speed=(\d+\.?\d*)", text)
            progress_match = re.findall(r"progress=(\w+)", text)
            
            speed = float(speed_match[-1]) if speed_match else 1.0
            time_in_us = int(time_in_us_match[-1]) if time_in_us_match else 0
            
            if progress_match and progress_match[-1] == "end":
                LOGGER.info("Encoding Ended.")
                break
                
            if time_in_us > 0 and total_time and total_time > 0:
                elapsed_time = time_in_us / 1000000
                difference = math.floor((total_time - elapsed_time) / speed) if speed > 0 else 0
                ETA = TimeFormatter(difference) if difference > 0 else "-"
                
                percentage = math.floor((elapsed_time * 100) / total_time)
                percentage = min(percentage, 100) # prevent over 100%
                
                progress_str = "<b>Encoding Video:</b> {0}%\n{1}{2}".format(
                    round(percentage, 2),
                    ''.join(['█' for _ in range(math.floor(percentage / 10))]),
                    ''.join(['░' for _ in range(10 - math.floor(percentage / 10))])
                )
                stats = f'{progress_str} \n• ETA: {ETA}'
                
                await msg.edit(
                    text=stats,
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton('Cancel', callback_data='cancel'), InlineKeyboardButton('Stats', callback_data='stats')]]
                    )
                )
        except Exception as e:
            pass


# =========================================================
# 🔴 FONT HANDLERS (ADMIN ONLY)
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
# 🔴 ULTIMATE INTERACTIVE ENCODE WORKFLOW
# =========================================================

@Client.on_message((filters.command("encode") | filters.document) & filters.private & is_auth)
async def interactive_encode_start(client, message):
    user_id = message.from_user.id
    
    if message.document:
        if not message.document.file_name.endswith(('.ass', '.srt')): 
            return 
            
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
            
        if os.path.exists(video_path): 
            os.remove(video_path)
            
        if sub_path and os.path.exists(sub_path): 
            os.remove(sub_path)
            
        del USER_ENCODE_STATE[user_id]

    except Exception as e:
        await status_msg.edit_text(f"❌ Process ke dauran ek error aagaya:\n`{e}`")
