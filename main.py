import os
import subprocess
import requests
import telebot
from telebot import types
from yt_dlp import YoutubeDL

# Render ပေါ်ရှိ Environment Variable မှ Token ကို ယူမည်
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
user_data = {}


def download_tiktok(url, output_path):
    api_url = f"https://www.tikwm.com/api/?url={url}"
    try:
        res = requests.get(api_url).json()
        if res.get("code") == 0:
            video_url = res["data"]["play"]
            r = requests.get(video_url, stream=True)
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
            return True
    except Exception as e:
        print(f"TikTok Error: {e}")
    return False


def download_youtube(url, output_path):
    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": output_path,
        "quiet": True,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True
    except Exception as e:
        print(f"YouTube Error: {e}")
    return False


def trim_video(input_path, output_path, duration_seconds):
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        "00:00:00",
        "-i",
        input_path,
        "-t",
        str(duration_seconds),
        "-c",
        "copy",
        output_path,
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return res.returncode == 0


def get_trim_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_3m = types.InlineKeyboardButton("⏱ ၃ မိနစ် ဖြတ်မည်", callback_data="trim_180")
    btn_5m = types.InlineKeyboardButton("⏱ ၅ မိနစ် ဖြတ်မည်", callback_data="trim_300")
    btn_10m = types.InlineKeyboardButton(
        "⏱ ၁၀ မိနစ် ဖြတ်မည်", callback_data="trim_600"
    )
    btn_full = types.InlineKeyboardButton("🎬 မဖြတ်ဘဲ ယူမည်", callback_data="full")
    markup.add(btn_3m, btn_5m, btn_10m, btn_full)
    return markup


@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(
        message,
        "မင်္ဂလာပါ! ဗီဒီယိုဖိုင် တိုက်ရိုက်ပို့ပေးနိုင်သလို YouTube / TikTok link ပို့ပေးပါကလည်း ၃ မိနစ်၊ ၅ မိနစ်၊ ၁၀ မိနစ် အပိုင်းများအဖြစ် ဖြတ်တောက်ပေးပါမည်။",
    )


@bot.message_handler(content_types=["video"])
def handle_uploaded_video(message):
    chat_id = message.chat.id
    status_msg = bot.reply_to(
        message, "ဗီဒီယိုဖိုင်ကို သိမ်းဆည်းနေပါသည်၊ ခေတ္တစောင့်ပေးပါ..."
    )

    file_info = bot.get_file(message.video.file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    raw_path = os.path.join(DOWNLOAD_DIR, f"{chat_id}_raw.mp4")
    with open(raw_path, "wb") as f:
        f.write(downloaded_file)

    user_data[chat_id] = raw_path
    bot.edit_message_text(
        "ဗီဒီယိုကို မိနစ် မည်မျှဖြတ်လိုပါသလဲ ရွေးချယ်ပါ:",
        chat_id=chat_id,
        message_id=status_msg.message_id,
        reply_markup=get_trim_keyboard(),
    )


@bot.message_handler(func=lambda message: True)
def handle_links(message):
    url = message.text.strip()
    chat_id = message.chat.id
    raw_path = os.path.join(DOWNLOAD_DIR, f"{chat_id}_raw.mp4")

    if "tiktok.com" in url:
        status_msg = bot.reply_to(message, "TikTok မှ ဗီဒီယိုကို ရယူနေပါသည်...")
        success = download_tiktok(url, raw_path)
    elif "youtube.com" in url or "youtu.be" in url:
        status_msg = bot.reply_to(message, "YouTube မှ ဗီဒီယိုကို ရယူနေပါသည်...")
        success = download_youtube(url, raw_path)
    else:
        bot.reply_to(
            message,
            "ကျေးဇူးပြု၍ ဗီဒီယိုဖိုင် သို့မဟုတ် YouTube/TikTok link ကိုသာ ပို့ပေးပါ။",
        )
        return

    if success:
        user_data[chat_id] = raw_path
        bot.edit_message_text(
            "ဗီဒီယို ရရှိပါပြီ။ မည်မျှ ဖြတ်တောက်လိုပါသလဲ ရွေးချယ်ပါ:",
            chat_id=chat_id,
            message_id=status_msg.message_id,
            reply_markup=get_trim_keyboard(),
        )
    else:
        bot.edit_message_text(
            "ဗီဒီယိုကို ဒေါင်းလုဒ်မရနိုင်ပါ။ Link မှန်ကန်မှု ရှိမရှိ စစ်ဆေးပေးပါ။",
            chat_id=chat_id,
            message_id=status_msg.message_id,
        )


@bot.callback_query_handler(func=lambda call: True)
def process_trim(call):
    chat_id = call.message.chat.id
    raw_path = user_data.get(chat_id)

    if not raw_path or not os.path.exists(raw_path):
        bot.send_message(
            chat_id, "ဗီဒီယိုဖိုင် မရှိတော့ပါ။ link သို့မဟုတ် ဗီဒီယို ပြန်ပို့ပေးပါ။"
        )
        return

    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        "ဗီဒီယို ဖြတ်တောက်နေပါသည်၊ ခေတ္တစောင့်ပေးပါ...",
        chat_id=chat_id,
        message_id=call.message.message_id,
    )

    action = call.data
    final_output = os.path.join(DOWNLOAD_DIR, f"{chat_id}_final.mp4")

    if action == "full":
        final_output = raw_path
    else:
        seconds = int(action.split("_")[1])
        trim_video(raw_path, final_output, seconds)

    try:
        with open(final_output, "rb") as vid:
            bot.send_video(chat_id, vid, caption="သင့်ဗီဒီယို ရပါပြီ!")
    except Exception as e:
        bot.send_message(
            chat_id, f"ပို့ဆောင်ရာတွင် အမှားဖြစ်သွားပါသည် (ဖိုင်ဆိုဒ်ကြီးလွန်းခြင်း ဖြစ်နိုင်ပါသည်): {e}"
        )

    for f in [raw_path, final_output]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except:
                pass
    user_data.pop(chat_id, None)


bot.infinity_polling()
