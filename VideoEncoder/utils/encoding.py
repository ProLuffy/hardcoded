import asyncio
import json
import math
import os
import re
import subprocess
import time

from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .. import LOGGER, download_dir, encode_dir
from .database.access_db import db
from .display_progress import TimeFormatter

FONT_DIR = "VideoEncoder/utils/extras/fonts"
if not os.path.isdir(FONT_DIR):
    os.makedirs(FONT_DIR)

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
    check = get_codec(filepath, channel='s:0')
    if check == [] or check == 'pgs':
        return None
        
    output = os.path.join(encode_dir, str(msg.id) + '.ass')

    try:
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
    progress_file = os.path.join(download_dir, "process.txt")
    with open(progress_file, 'w') as f:
        pass

    assert(output_filepath != filepath)

    if os.path.isfile(output_filepath):
        LOGGER.warning(f'"{output_filepath}": file already exists')

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

    extra_inputs = []
    subtitles_args = []
    
    if sub_mode == 'none':
        subtitles_args = ['-sn']
    elif custom_sub_path and sub_mode == 'soft':
        extra_inputs = ['-i', custom_sub_path]
        sub_codec = 'srt' if custom_sub_path.endswith('.srt') else 'ass'
        subtitles_args = ['-map', '1:s', '-c:s', sub_codec]
    elif not custom_sub_path and sub_mode == 'soft':
        subtitles_args = ['-map', '0:s?', '-c:s', 'copy']
    elif sub_mode == 'hard':
        subtitles_args = ['-sn'] 
    else:
        subtitles_args = []

    vf_filters = []
    
    # Custom Resolution Override
    r = custom_quality if custom_quality else await db.get_resolution(message.from_user.id)
    if r == '2160': vf_filters.append('scale=3840:2160')
    elif r == '1080': vf_filters.append('scale=1920:1080')
    elif r == '720': vf_filters.append('scale=1280:720')
    elif r == '576': vf_filters.append('scale=768:576')
    elif r == '480': vf_filters.append('scale=852:480')

    w = await db.get_watermark(message.from_user.id)
    if w: vf_filters.append("subtitles=VideoEncoder/utils/extras/watermark.ass")
    
    abs_font_dir = os.path.abspath(FONT_DIR)
    active_font_name = None
    try:
        if hasattr(db, 'get_active_font'):
            active_font = await db.get_active_font()
            if active_font:
                active_font_name = active_font["font_name"]
                font_path = os.path.join(FONT_DIR, active_font["file_name"])
                if not os.path.exists(font_path) and hasattr(message, '_client'):
                    client = message._client
                    await client.download_media(active_font["file_id"], file_name=font_path)
    except Exception as e:
        LOGGER.error(f"Font fetch error: {e}")

    if sub_mode == 'hard' and custom_sub_path:
        safe_path = custom_sub_path.replace('\\', '/') 
        font_opt = f":fontsdir='{abs_font_dir}':force_style='Fontname={active_font_name}'" if active_font_name else ""
        vf_filters.append(f"subtitles='{safe_path}'{font_opt}")
    elif sub_mode == 'hard' and not custom_sub_path:
        subtitles_path = os.path.join(encode_dir, str(msg.id) + '.ass')
        safe_path = subtitles_path.replace('\\', '/') 
        font_opt = f":fontsdir='{abs_font_dir}':force_style='Fontname={active_font_name}'" if active_font_name else ""
        vf_filters.append(f"subtitles='{safe_path}'{font_opt}")

    watermark_args = []
    if vf_filters:
        watermark_args = ['-vf', ','.join(vf_filters)]

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
        if a in audios: 
            audio_opts = f'-c:a {audios[a]} {sample} {bitrate}'
        elif a == 'opus': 
            audio_opts = f'-c:a libopus -vbr on {sample} {bitrate}'
        else: 
            audio_opts = '-c:a copy'
        if audio_map:
            map_opts = "".join([f" -map 0:{idx}" for idx in audio_map])
            audio_opts = f"{audio_opts} {map_opts} -disposition:a:0 default"
        else:
            audio_opts += " -map 0:a?"

    c = await db.get_channels(message.from_user.id)
    channels = '' if '-c:a copy' in audio_opts else '-rematrix_maxval 1.0 -ac 1' if c == '1.0' else '-rematrix_maxval 1.0 -ac 2' if c == '2.0' else '-rematrix_maxval 1.0 -ac 3' if c == '2.1' else '-rematrix_maxval 1.0 -ac 6' if c == '5.1' else '-rematrix_maxval 1.0 -ac 8' if c == '7.1' else ''

    finish = '-threads 8'

    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-progress', progress_file, '-hwaccel', 'auto', '-y', '-i', filepath]
    if extra_inputs: 
        command.extend(extra_inputs)
        
    cmd_args = []
    cmd_args.extend(codec.split())
    cmd_args.extend(preset.split())
    cmd_args.extend(frame.split())
    cmd_args.extend(tunevideo.split())
    cmd_args.extend(aspect.split())
    cmd_args.extend(video_opts.split())
    cmd_args.extend(Crf.split())
    cmd_args.extend(metadata.split())
    cmd_args.extend(audio_opts.split())
    cmd_args.extend(channels.split())
    cmd_args.extend(finish.split())

    command.extend(cmd_args)
    command.extend(subtitles_args)
    if watermark_args:
        command.extend(watermark_args)
    
    proc = await asyncio.create_subprocess_exec(*command, output_filepath, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    progress_task = asyncio.create_task(handle_progress(proc, msg, message, filepath))
    
    stdout, stderr = await proc.communicate()
    await progress_task 
    
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
                percentage = min(percentage, 100) 
                
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
