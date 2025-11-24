from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo, BotCommand
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, UserNotFound
import os
import re
import sqlite3

TOKEN = '8463514817:AAFiTj3GewMNveJHg5A1rL-9KMYacKW4zXA'
USERNAME = 'regribot'
PASSWORD = 'mmmmmm11mm11'
SESSION = 'session.json'

bot = TeleBot(TOKEN, parse_mode='HTML')
bot.set_my_commands([BotCommand("start", "شروع ربات")])

cl = Client()
cl.delay_range = [0.5, 2]

conn = sqlite3.connect('users.db', check_same_thread=False)
cur = conn.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS users (username TEXT UNIQUE)')
conn.commit()


def add_user(username):
    if username:
        cur.execute("INSERT OR IGNORE INTO users (username) VALUES (?)", (username,))
        conn.commit()


def login():
    try:
        if os.path.exists(SESSION):
            cl.load_settings(SESSION)
        cl.login(USERNAME, PASSWORD)
        cl.dump_settings(SESSION)
    except LoginRequired:
        if os.path.exists(SESSION):
            os.remove(SESSION)
        cl.login(USERNAME, PASSWORD)
        cl.dump_settings(SESSION)
    except Exception as e:
        print(f"خطا در لاگین: {e}")


def get_caption(username=""):
    return f"🍭 Download by<a href='https://t.me/RegriBot'> RegriBot</a>"



def detect_input(text):
    text = text.strip()
    if text.startswith(('http://', 'https://')):
        if 'instagram.com' in text:
            if '/p/' in text or '/reel' in text:
                return 'post'
            elif '/stories/' in text:
                return 'story_link'
            elif 'instagram.com/' in text:
                return 'profile_link'
    elif re.match(r'^@?[A-Za-z0-9_.]{3,30}$', text):
        return 'username'
    return 'unknown'


@bot.message_handler(commands=['start'])
def start(m):
    add_user(m.from_user.username)
    bot.reply_to(m, "سلام! لینک پست، ریلز، استوری یا یوزرنیم اینستاگرام بفرست\n\nسریع | با کیفیت | بدون محدودیت")


@bot.message_handler(func=lambda m: True)
def handle(m):
    text = m.text.strip()
    chat_id = m.chat.id
    user_id = m.from_user.id
    msg = bot.send_message(chat_id, "در حال پردازش...")

    try:
        login()
        add_user(m.from_user.username)

        input_type = detect_input(text)

        if input_type == 'post':
            match = re.search(r'(?:instagram\.com|instagr\.am)/(?:p|reel|reels)/([A-Za-z0-9_-]{11})', text)
            if not match:
                bot.edit_message_text("لینک نامعتبر", chat_id, msg.message_id)
                return
            shortcode = match.group(1)
            media = cl.media_info(cl.media_pk_from_code(shortcode))

            caption = f"{(media.caption_text or '')[:300]}{'...' if media.caption_text and len(media.caption_text) > 300 else ''}\n\n{get_caption(media.user.username)}"

            if media.media_type == 8:
                items = []
                for i, res in enumerate(media.resources):
                    url = res.video_url if res.media_type == 2 else res.thumbnail_url
                    item = InputMediaVideo(url) if res.media_type == 2 else InputMediaPhoto(url)
                    if i == len(media.resources) - 1:
                        item.caption = caption
                        item.parse_mode = 'HTML'
                    items.append(item)
                bot.send_media_group(chat_id, items)
            else:
                url = media.video_url if media.media_type == 2 else media.thumbnail_url
                if media.media_type == 2:
                    bot.send_video(chat_id, url, caption=caption, supports_streaming=True)
                else:
                    bot.send_photo(chat_id, url, caption=caption)

        # 2. لینک استوری
        elif input_type == 'story_link':
            match = re.search(r'instagram\.com/stories/([A-Za-z0-9_.]+)/(\d+)', text)
            if not match:
                bot.edit_message_text("لینک استوری نامعتبر", chat_id, msg.message_id)
                return
            username, story_id = match.groups()
            story = cl.story_info(int(story_id))
            url = story.video_url if story.media_type == 2 else story.thumbnail_url
            caption = f"استوری @{username}\n\n{get_caption()}"
            if story.media_type == 2:
                bot.send_video(chat_id, url, caption=caption, supports_streaming=True)
            else:
                bot.send_photo(chat_id, url, caption=caption)

        # 3. لینک پروفایل یا یوزرنیم
        elif input_type in ['profile_link', 'username']:
            username = re.sub(r'^@|https?://.*/|\?.*', '', text).strip('/')
            if not username:
                bot.edit_message_text("یوزرنیم نامعتبر", chat_id, msg.message_id)
                return
            if bot.get_state(user_id) == f"confirmed_{username}":
                send_profile(chat_id, username)
                bot.delete_message(chat_id, msg.message_id)
                return
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("آره✅", callback_data=f"yes_profile:{username}"),
                InlineKeyboardButton("نه❌", callback_data="no_profile")
            )
            bot.edit_message_text(
                "این آیدی اینستاگرامه؟",
                chat_id, msg.message_id, reply_markup=markup, parse_mode='HTML'
            )
        else:
            bot.edit_message_text("لینک یا یوزرنیم معتبر بفرست", chat_id, msg.message_id)
            return


    except UserNotFound:
        bot.edit_message_text("یوزرنیم پیدا نشد", chat_id, msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"خطا: {str(e)}", chat_id, msg.message_id)
        print(e)


def send_profile(chat_id, username):
    try:
        msg = bot.send_message(chat_id, 'در حال دریافت اطلاعات...')
        user = cl.user_info_by_username(username)
        pp_url = user.profile_pic_url_hd or user.profile_pic_url

        caption = f'{user.full_name or username}\n{user.biography or "---"}\nFollower:{user.follower_count}\nFollowing:{user.following_count}\nNumber Of Post:{user.media_count}\nStatus:{'Private' if user.is_private else 'Public'}\n\n{get_caption()}'

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("دانلود استوری‌ها", callback_data=f"story:{username}"))
        bot.delete_message(chat_id, msg.message_id)
        bot.send_photo(chat_id, pp_url, caption=caption, reply_markup=markup)
    except Exception as e:
        bot.edit_message_text(f"خطا در دریافت پروفایل: {str(e)}", chat_id, msg.message_id)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    try:
        if call.data == "no_profile":
            bot.answer_callback_query(call.id, "اوکی")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            return

        if call.data.startswith("yes_profile:"):
            username = call.data.split(":")[1]
            send_profile(call.message.chat.id, username)
            bot.delete_message(call.message.chat.id, call.message.message_id)
            return

        if call.data.startswith("story:"):
            username = call.data.split(":")[1]
            bot.answer_callback_query(call.id, "در حال دانلود استوری‌ها...")
            stories = cl.user_stories(cl.user_id_from_username(username))
            if not stories:
                bot.send_message(call.message.chat.id, "استوری موجود نیست یا اکانت خصوصی است")
                return
            for story in stories:
                url = story.video_url if story.media_type == 2 else story.thumbnail_url
                caption = f"استوری @{username}\n\n{get_caption()}"
                if story.media_type == 2:
                    bot.send_video(call.message.chat.id, url, caption=caption)
                else:
                    bot.send_photo(call.message.chat.id, url, caption=caption)

    except Exception as e:
        bot.send_message(call.message.chat.id, f"خطا: {str(e)}")

login()
bot.infinity_polling()
