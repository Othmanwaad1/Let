import os
import sys
import time
import signal
import subprocess
import telebot
from telebot import types

BOT_TOKEN = "8899589013:AAGmdocfLvpdEFqsjTT4EqLpfN-8BC0s-O0"
ADMIN_ID = 7114992169

FOLDER = os.path.join(os.path.expanduser("~"), "sfiles")
os.makedirs(FOLDER, exist_ok=True)

bot = telebot.TeleBot(BOT_TOKEN)
procs = {}

def is_admin(cid):
    return cid == ADMIN_ID

def list_scripts():
    return sorted([f for f in os.listdir(FOLDER) if f.endswith(".py")])

def kill_pid(pid):
    try:
        os.kill(pid, signal.SIGTERM)
        procs.pop(pid, None)
        return True
    except Exception:
        return False

@bot.message_handler(commands=["start", "help"])
def cmd_start(msg):
    if not is_admin(msg.chat.id):
        return
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.add("قائمة الملفات", "العمليات", "ايقاف الكل")
    bot.send_message(msg.chat.id, "بوت تشغيل بايثون ✅\nارسل ملف .py لرفعه، ثم اختره من القائمة.", reply_markup=mk)

@bot.message_handler(content_types=["document"])
def upload(msg):
    if not is_admin(msg.chat.id):
        return
    name = msg.document.file_name
    if not name.endswith(".py"):
        bot.reply_to(msg, "فقط ملفات .py")
        return
    path = os.path.join(FOLDER, name)
    if os.path.exists(path):
        bot.reply_to(msg, "الملف موجود مسبقا")
        return
    fi = bot.get_file(msg.document.file_id)
    bot.download_file(fi.file_path, path)
    bot.reply_to(msg, "تم الرفع: " + name)

@bot.message_handler(func=lambda m: m.text == "قائمة الملفات")
def menu_files(msg):
    if not is_admin(msg.chat.id):
        return
    files = list_scripts()
    if not files:
        bot.send_message(msg.chat.id, "لا توجد ملفات")
        return
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for f in files:
        mk.add(types.KeyboardButton("تشغيل " + f),
               types.KeyboardButton("ايقاف " + f),
               types.KeyboardButton("حذف " + f))
    bot.send_message(msg.chat.id, "اختر ملف:", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text and m.text.startswith("تشغيل "))
def run_script(msg):
    if not is_admin(msg.chat.id):
        return
    name = msg.text[len("تشغيل "):].strip()
    path = os.path.join(FOLDER, name)
    if not os.path.exists(path):
        bot.send_message(msg.chat.id, "الملف غير موجود")
        return
    try:
        proc = subprocess.Popen(
            [sys.executable, path],
            cwd=FOLDER,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True
        )
        procs[proc.pid] = {"name": name}
        time.sleep(5)
        if proc.poll() is not None:
            out, err = proc.communicate()
            bot.send_message(msg.chat.id, "انتهى بخطا:\n" + (err.decode("utf-8", "ignore") if err else str(out))[:1500])
            return
        bot.send_message(msg.chat.id, "يعمل الان: " + name + " (PID " + str(proc.pid) + ")")
    except Exception as e:
        bot.send_message(msg.chat.id, "فشل: " + str(e))

@bot.message_handler(func=lambda m: m.text and m.text.startswith("ايقاف "))
def stop_script(msg):
    if not is_admin(msg.chat.id):
        return
    name = msg.text[len("ايقاف "):].strip()
    for pid, p in list(procs.items()):
        if p["name"] == name:
            kill_pid(pid)
            bot.send_message(msg.chat.id, "اوقفت: " + name)
            return
    bot.send_message(msg.chat.id, "لا يوجد تشغيل بهذا الاسم")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("حذف "))
def delete_script(msg):
    if not is_admin(msg.chat.id):
        return
    name = msg.text[len("حذف "):].strip()
    path = os.path.join(FOLDER, name)
    if os.path.exists(path):
        os.remove(path)
        bot.send_message(msg.chat.id, "حذفت: " + name)
    else:
        bot.send_message(msg.chat.id, "غير موجود")

@bot.message_handler(func=lambda m: m.text == "العمليات")
def list_procs_cmd(msg):
    if not is_admin(msg.chat.id):
        return
    if not procs:
        bot.send_message(msg.chat.id, "لا عمليات تعمل")
        return
    bot.send_message(msg.chat.id, "\n".join(str(pid) + ": " + p["name"] for pid, p in procs.items()))

@bot.message_handler(func=lambda m: m.text == "ايقاف الكل")
def kill_all(msg):
    if not is_admin(msg.chat.id):
        return
    for pid in list(procs):
        kill_pid(pid)
    bot.send_message(msg.chat.id, "اوقفت كل العمليات")

if __name__ == "__main__":
    while True:
        try:
            bot.polling(none_stop=True, timeout=60)
        except Exception:
            time.sleep(5)
