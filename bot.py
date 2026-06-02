import telebot
import random
import time
import json
import os
import threading
from telebot import types
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Берем токен из переменной окружения
API_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(API_TOKEN)

# Установка команд в меню
bot.set_my_commands([
    types.BotCommand("start", "Запустить бота 🚀"),
    types.BotCommand("fish", "Закинуть удочку 🎣"),
    types.BotCommand("inventory", "Посмотреть улов 📦"),
    types.BotCommand("sell", "Продать рыбу 💰"),
    types.BotCommand("shop", "Магазин снаряжения 🛒"),
    types.BotCommand("location", "Сменить локацию 🗺️"),
    types.BotCommand("index", "Список всех рыб 🐟"),
    types.BotCommand("leaderboards", "Таблица лидеров 🏆")
])

# Данные о рыбах
FISH_DATA = {
    '⬜ Обычная': {'rarity': 60, 'cost_range': (10, 50), 'fishes': ['Карась', 'Окунь', 'Плотва']},
    '🟩🟩 Редкая': {'rarity': 25, 'cost_range': (60, 150), 'fishes': ['Щука', 'Судак', 'Лещ']},
    '🟦🟦🟦 Сверх редкая': {'rarity': 10, 'cost_range': (200, 500), 'fishes': ['Сом', 'Угорь', 'Стерлядь']},
    '🟪🟪🟪🟪 Эпическая': {'rarity': 4, 'cost_range': (600, 1500), 'fishes': ['Осетр', 'Белуга']},
    '🟥🟥🟥🟥🟥 Мифическая': {'rarity': 0.9, 'cost_range': (2000, 5000), 'fishes': ['Золотая рыбка', 'Кракен']},
    '🟨🟨🟨🟨🟨🟨 Легендарная': {'rarity': 0.1, 'cost_range': (10000, 50000), 'fishes': ['Мегалодон', 'Посейдон']}
}

SHOP_RODS = {
    '0': {'name': '🪱 Стартовая палка', 'cost': 0, 'cd': 5},
    '1': {'name': '🎋 Бамбуковая удочка', 'cost': 1000, 'cd': 4},
    '2': {'name': '🎣 Современная удочка', 'cost': 5000, 'cd': 3},
    '3': {'name': '🦾 Титановая удочка', 'cost': 20000, 'cd': 2},
    '4': {'name': '⚛️ Квантовая удочка', 'cost': 100000, 'cd': 1}
}

SHOP_BAITS = {
    '1': {'name': '🪱 Обычный червяк', 'cost': 500, 'amount': 10, 'multiplier': 1.2},
    '2': {'name': '🐛 Живой опарыш', 'cost': 1500, 'amount': 10, 'multiplier': 1.5},
    '3': {'name': '✨ Золотая блесна', 'cost': 7890, 'amount': 5, 'multiplier': 2.5},
    '4': {'name': '🧪 Атрактант Х', 'cost': 50000, 'amount': 3, 'multiplier': 5.0}
}

LOCATIONS_DATA = {
    '0': {'name': '🏖️ Обычный берег', 'cost': 0, 'luck': 1.0},
    '1': {'name': '🏚️ Заброшенный пруд', 'cost': 10000, 'luck': 1.2},
    '2': {'name': '🏔️ Горная река', 'cost': 50000, 'luck': 1.5},
    '3': {'name': '🌌 Таинственное озеро', 'cost': 250000, 'luck': 2.0},
    '4': {'name': '🌋 Океанская бездна', 'cost': 1000000, 'luck': 3.5}
}

# База данных пользователей
DATA_FILE = '/data/users_data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

users = load_data()

# Вспомогательная функция для удаления сообщений в фоне
def delete_after_delay(chat_id, message_ids, delay=3):
    def work():
        time.sleep(delay)
        for mid in message_ids:
            try:
                bot.delete_message(chat_id, mid)
            except:
                pass
    threading.Thread(target=work).start()

def get_user_data(user_id, username=None):
    user_id = str(user_id)
    if user_id not in users:
        users[user_id] = {
            'balance': 0,
            'inventory': {},
            'last_fish': 0,
            'rod': '0',
            'location': '0',
            'unlocked_locations': ['0'],
            'baits': {},
            'username': username or f"ID {user_id}",
            'stats': {'total_caught': 0, 'total_earned': 0}
        }
        save_data()
    
    # Миграция и обновление ника
    if username and users[user_id].get('username') != username:
        users[user_id]['username'] = username
        save_data()
        
    defaults = {
        'inventory': {},
        'last_fish': 0,
        'rod': '0',
        'location': '0',
        'unlocked_locations': ['0'],
        'baits': {},
        'stats': {'total_caught': 0, 'total_earned': 0}
    }
    for key, value in defaults.items():
        if key not in users[user_id]:
            users[user_id][key] = value
            
    return users[user_id]

# Проверка на админа (ID создателя или юзернейм @Idk_228_288)
def is_admin(user_id, username):
    return str(user_id) == '5284051771' or username == 'Idk_228_288'

@bot.message_handler(commands=['admin_add_money'])
def admin_add_money(message):
    if not is_admin(message.from_user.id, message.from_user.username):
        return
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "Используй: /admin_add_money [user_id] [amount]")
        return
    target_id, amount = args[1], int(args[2])
    target_data = get_user_data(target_id)
    target_data['balance'] += amount
    save_data()
    bot.reply_to(message, f"✅ Выдано {amount} 💰 пользователю {target_id}")

@bot.message_handler(commands=['admin_set_rod'])
def admin_set_rod(message):
    if not is_admin(message.from_user.id, message.from_user.username):
        return
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "Используй: /admin_set_rod [user_id] [rod_id 0-4]")
        return
    target_id, rod_id = args[1], args[2]
    if rod_id in SHOP_RODS:
        target_data = get_user_data(target_id)
        target_data['rod'] = rod_id
        save_data()
        bot.reply_to(message, f"✅ Пользователю {target_id} установлена удочка: {SHOP_RODS[rod_id]['name']}")

@bot.message_handler(commands=['admin_add_bait'])
def admin_add_bait(message):
    if not is_admin(message.from_user.id, message.from_user.username):
        return
    args = message.text.split()
    if len(args) < 4:
        bot.reply_to(message, "Используй: /admin_add_bait [user_id] [bait_id 1-4] [amount]")
        return
    target_id, bait_id, amount = args[1], args[2], int(args[3])
    if bait_id in SHOP_BAITS:
        target_data = get_user_data(target_id)
        target_data['baits'][bait_id] = target_data['baits'].get(bait_id, 0) + amount
        save_data()
        bot.reply_to(message, f"✅ Выдано {amount} шт. наживки {SHOP_BAITS[bait_id]['name']} пользователю {target_id}")

@bot.message_handler(commands=['start'])
def start(message):
    get_user_data(message.from_user.id, message.from_user.username)
    remove_keyboard = types.ReplyKeyboardRemove(selective=False)
    bot.send_message(
        message.chat.id, 
        "Привет! Я бот-рыбалка. Старая нижняя кнопка успешно удалена! 🧹\n\nИспользуй кнопки меню или команды:\n/fish — Рыбалка 🎣\n/inventory — Инвентарь 📦\n/shop — Магазин 🛒", 
        reply_markup=remove_keyboard, 
        message_thread_id=message.message_thread_id
    )

@bot.message_handler(commands=['money'])
def money_admin_command(message):
    if message.from_user.username != 'Idk_228_288':
        return
    
    args = message.text.split()
    if len(args) < 4 or args[1] != 'give':
        return

    target_username = args[2].replace('@', '')
    try:
        amount = int(args[3])
    except ValueError:
        return

    target_id = None
    for uid, data in users.items():
        if data.get('username') == target_username:
            target_id = uid
            break
    
    if target_id:
        users[target_id]['balance'] += amount
        save_data()
        bot.reply_to(message, f"✅ Выдано {amount} 💰 пользователю @{target_username}")
    else:
        bot.reply_to(message, "❌ Пользователь не найден в базе (он должен хоть раз запустить бота)")

@bot.message_handler(commands=['sell'])
def sell_fish(message):
    user = get_user_data(message.from_user.id)
    args = message.text.split()
    if not user['inventory']:
        bot.send_message(message.chat.id, "📦 Твой инвентарь пуст", message_thread_id=message.message_thread_id)
        return
    if len(args) > 1 and args[1] == 'all':
        total_pay = 0
        fish_count = 0
        for name, data in list(user['inventory'].items()):
            total_pay += data['price'] * data['count']
            fish_count += data['count']
        user['balance'] += total_pay
        user['inventory'] = {}
        if 'inv_list' in user:
            user['inv_list'] = []
        save_data()
        bot.send_message(message.chat.id, f"✅ Продано всё! ({fish_count} шт.)\n💰 Получено: {total_pay} 💰", message_thread_id=message.message_thread_id)
        return
    if len(args) < 3:
        bot.send_message(message.chat.id, "❌ Используй: /sell [номер] [количество] или /sell all", message_thread_id=message.message_thread_id)
        return
    try:
        idx = int(args[1]) - 1
        amount = int(args[2])
        if 'inv_list' not in user or idx < 0 or idx >= len(user['inv_list']):
            bot.send_message(message.chat.id, "❌ Неверный номер рыбы. Загляни в /inventory", message_thread_id=message.message_thread_id)
            return
        fish_name = user['inv_list'][idx]
        if amount <= 0 or amount > user['inventory'][fish_name]['count']:
            bot.send_message(message.chat.id, "❌ У тебя нет столько рыбы", message_thread_id=message.message_thread_id)
            return
        price_per_one = user['inventory'][fish_name]['price']
        total_pay = price_per_one * amount
        user['balance'] += total_pay
        user['inventory'][fish_name]['count'] -= amount
        if user['inventory'][fish_name]['count'] <= 0:
            del user['inventory'][fish_name]
            if 'inv_list' in user:
                user['inv_list'].remove(fish_name)
        save_data()
        bot.send_message(message.chat.id, f"✅ Продано {amount} шт. {fish_name} за {total_pay} 💰", message_thread_id=message.message_thread_id)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Вводи числа, а не буквы", message_thread_id=message.message_thread_id)

@bot.message_handler(commands=['fish'])
@bot.message_handler(func=lambda m: m.text == 'Закинуть удочку 🎣')
def get_fish(message):
    user = get_user_data(message.from_user.id, message.from_user.username)
    current_rod = SHOP_RODS.get(user.get('rod', '0'), SHOP_RODS['0'])
    cd = current_rod['cd']
    if time.time() - user['last_fish'] < cd:
        wait = round(cd - (time.time() - user['last_fish']), 1)
        warn_msg = bot.send_message(message.chat.id, f"⏳ Удочка еще не готова! Подожди {wait} сек.", message_thread_id=message.message_thread_id)
        delete_after_delay(message.chat.id, [message.message_id, warn_msg.message_id])
        return
    multiplier = 1.0
    bait_text = ""
    available_baits = [bid for bid, count in user['baits'].items() if count > 0]
    if available_baits:
        active_bait_id = max(available_baits, key=lambda b: SHOP_BAITS[b]['multiplier'])
        bait_info = SHOP_BAITS[active_bait_id]
        multiplier = bait_info['multiplier']
        user['baits'][active_bait_id] -= 1
        bait_text = f"\n✨ Наживка: {bait_info['name']} (x{multiplier})"
    
    current_loc = LOCATIONS_DATA.get(user.get('location', '0'), LOCATIONS_DATA['0'])
    luck = current_loc['luck']
    
    msg = bot.send_message(message.chat.id, f"📍 {current_loc['name']}\nУдочка: {current_rod['name']}🎣{bait_text}\nЗакидываем...", message_thread_id=message.message_thread_id)
    
    # Удача влияет на шанс: делим ролл на коэффициент удачи
    rand = (random.random() * 100) / luck
    cumulative = 0
    selected_rarity = '⬜ Обычная'
    for rarity, data in FISH_DATA.items():
        cumulative += data['rarity']
        if rand <= cumulative:
            selected_rarity = rarity
            break
    fish_info = FISH_DATA[selected_rarity]
    fish_name = random.choice(fish_info['fishes'])
    base_cost = random.randint(*fish_info['cost_range'])
    cost = int(base_cost * multiplier)
    full_name = f"{selected_rarity} {fish_name}"
    if full_name not in user['inventory']:
        user['inventory'][full_name] = {'count': 0, 'price': cost}
    user['inventory'][full_name]['count'] += 1
    user['last_fish'] = time.time()
    save_data()
    result = (f"🎉 Вы выловили рыбу!\n\nРыба: {full_name}\nСтоимость: {cost} 💰\n\nРыба добавлена в инвентарь. Продай её через /sell")
    bot.edit_message_text(result, message.chat.id, msg.message_id)

@bot.message_handler(commands=['leaderboards'])
def show_leaderboards(message):
    markup = types.InlineKeyboardMarkup()
    btn_global = types.InlineKeyboardButton("🌍 Глобальный", callback_data="lb_global")
    btn_group = types.InlineKeyboardButton("👥 В этой группе", callback_data="lb_group")
    markup.add(btn_global, btn_group)
    bot.send_message(message.chat.id, "🏆 **Выберите таблицу лидеров по деньгам:**", reply_markup=markup, parse_mode='Markdown', message_thread_id=message.message_thread_id)

@bot.message_handler(commands=['location'])
def show_locations(message):
    user = get_user_data(message.from_user.id, message.from_user.username)
    markup = types.InlineKeyboardMarkup()
    text = "🗺️ **Доступные локации:**\n\n"
    
    for loc_id, loc in LOCATIONS_DATA.items():
        is_unlocked = loc_id in user.get('unlocked_locations', ['0'])
        status = "✅ Выбрано" if user.get('location') == loc_id else ("🔓 Открыто" if is_unlocked else f"💰 {loc['cost']}")
        text += f"*{loc['name']}*\n— Удача: x{loc['luck']}\n— Статус: {status}\n\n"
        
        if user.get('location') != loc_id:
            btn_text = f"Переехать в {loc['name']}" if is_unlocked else f"Купить {loc['name']}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"loc_{loc_id}"))
            
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown', message_thread_id=message.message_thread_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('loc_'))
def handle_location_change(call):
    user = get_user_data(call.from_user.id)
    loc_id = call.data.split('_')[1]
    loc = LOCATIONS_DATA[loc_id]
    
    unlocked = user.get('unlocked_locations', ['0'])
    
    if loc_id in unlocked:
        user['location'] = loc_id
        save_data()
        bot.answer_callback_query(call.id, f"🚀 Вы переехали в {loc['name']}")
    else:
        if user['balance'] >= loc['cost']:
            user['balance'] -= loc['cost']
            user['unlocked_locations'].append(loc_id)
            user['location'] = loc_id
            save_data()
            bot.answer_callback_query(call.id, f"🎉 Локация {loc['name']} куплена и выбрана!")
        else:
            bot.answer_callback_query(call.id, "❌ Недостаточно средств для переезда!")
    
    # Обновляем сообщение (повторный вызов логики отрисовки)
    try:
        new_text = "🗺️ **Доступные локации:**\n\n"
        markup = types.InlineKeyboardMarkup()
        for lid, linfo in LOCATIONS_DATA.items():
            is_unlocked = lid in user.get('unlocked_locations', ['0'])
            status = "✅ Выбрано" if user.get('location') == lid else ("🔓 Открыто" if is_unlocked else f"💰 {linfo['cost']}")
            new_text += f"*{linfo['name']}*\n— Удача: x{linfo['luck']}\n— Статус: {status}\n\n"
            if user.get('location') != lid:
                btn_txt = f"Переехать в {linfo['name']}" if is_unlocked else f"Купить {linfo['name']}"
                markup.add(types.InlineKeyboardButton(btn_txt, callback_data=f"loc_{lid}"))
        bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    except:
        pass

@bot.message_handler(commands=['index'])
def show_index(message):
    text = "🐟 **Список всех рыб по редкости:**\n\n"
    for rarity, data in FISH_DATA.items():
        text += f"{rarity} ({data['rarity']}%)\n— {', '.join(data['fishes'])}\n\n"
    bot.send_message(message.chat.id, text, parse_mode='Markdown', message_thread_id=message.message_thread_id)

@bot.message_handler(commands=['inventory'])
def show_inventory(message):
    user = get_user_data(message.from_user.id, message.from_user.username)
    last_cmd = user.get('last_cmd_time', 0)
    if time.time() - last_cmd < 3:
        warn = bot.send_message(message.chat.id, "⏳ Не так часто!", message_thread_id=message.message_thread_id)
        delete_after_delay(message.chat.id, [message.message_id, warn.message_id])
        return
    user['last_cmd_time'] = time.time()
    if not user['inventory']:
        bot.send_message(message.chat.id, f"📦 Твой инвентарь пуст\n💰 Баланс: {user['balance']} 💰", message_thread_id=message.message_thread_id)
        return
    text = f"📦 Твой инвентарь:\n\n"
    user['inv_list'] = list(user['inventory'].keys())
    for i, name in enumerate(user['inv_list'], 1):
        text += f"{i}. {name} — {user['inventory'][name]['count']} шт. (цена: {user['inventory'][name]['price']})\n"
    text += f"\n💰 Баланс: {user['balance']} 💰\n\nПродать: /sell [номер] [кол-во]"
    bot.send_message(message.chat.id, text, message_thread_id=message.message_thread_id)

@bot.message_handler(commands=['shop'])
def show_shop(message):
    user = get_user_data(message.from_user.id, message.from_user.username)
    if time.time() - user.get('last_cmd_time', 0) < 3:
        warn = bot.send_message(message.chat.id, "⏳ Подожди.", message_thread_id=message.message_thread_id)
        delete_after_delay(message.chat.id, [message.message_id, warn.message_id])
        return
    user['last_cmd_time'] = time.time()
    send_shop_page(message.chat.id, 1, message.from_user.id, message.message_thread_id)

def send_shop_page(chat_id, page, user_id, thread_id=None, message_id=None):
    user = get_user_data(user_id)
    markup = types.InlineKeyboardMarkup()
    if page == 1:
        text = "🛒 **Магазин: Удочки**\n\n"
        for id, item in SHOP_RODS.items():
            if id == '0': continue
            text += f"{item['name']}\n— КД: {item['cd']} сек.\n— Цена: {item['cost']}\n\n"
            if user['rod'] != id:
                markup.add(types.InlineKeyboardButton(f"Купить {item['name']}", callback_data=f"buy_rod_{id}"))
        markup.add(types.InlineKeyboardButton("➡️ Снасти", callback_data="shop_page_2"))
    else:
        text = "🛒 **Магазин: Снасти**\n\n"
        for id, item in SHOP_BAITS.items():
            text += f"{item['name']}\n— x{item['multiplier']}\n— Цена: {item['cost']}\n— У тебя: {user['baits'].get(id, 0)} шт.\n\n"
            markup.add(types.InlineKeyboardButton(f"Купить {item['name']}", callback_data=f"buy_bait_{id}"))
        markup.add(types.InlineKeyboardButton("⬅️ Удочки", callback_data="shop_page_1"))
    if message_id:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode='Markdown')
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='Markdown', message_thread_id=thread_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lb_'))
def handle_leaderboards(call):
    sorted_users = sorted(users.items(), key=lambda x: x[1].get('balance', 0), reverse=True)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="lb_menu"))
    if call.data == "lb_menu":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🌍 Глобальный", callback_data="lb_global"), types.InlineKeyboardButton("👥 Группа", callback_data="lb_group"))
        bot.edit_message_text("🏆 **Выберите таблицу лидеров:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        return
    text = "🌍 **Глобальный топ:**\n\n" if call.data == "lb_global" else "👥 **Топ группы:**\n\n"
    for i, (uid, data) in enumerate(sorted_users[:10], 1):
        name = data.get('username', f'ID {uid}')
        text += f"{i}. {name} — {data.get('balance', 0)} 💰\n"
    bot.answer_callback_query(call.id)
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('shop_page_'))
def shop_nav(call):
    page = int(call.data.split('_')[-1])
    send_shop_page(call.message.chat.id, page, call.from_user.id, message_id=call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def buy_item(call):
    user = get_user_data(call.from_user.id)
    parts = call.data.split('_')
    item_type, item_id = parts[1], parts[2]
    if item_type == 'rod':
        item = SHOP_RODS[item_id]
        if user['balance'] >= item['cost']:
            user['balance'] -= item['cost']
            user['rod'] = item_id
            save_data()
            bot.answer_callback_query(call.id, "✅ Удочка куплена!")
            send_shop_page(call.message.chat.id, 1, call.from_user.id, message_id=call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ Мало денег!")
    elif item_type == 'bait':
        item = SHOP_BAITS[item_id]
        if user['balance'] >= item['cost']:
            user['balance'] -= item['cost']
            user['baits'][item_id] = user['baits'].get(item_id, 0) + item['amount']
            save_data()
            bot.answer_callback_query(call.id, "✅ Наживка куплена!")
            send_shop_page(call.message.chat.id, 2, call.from_user.id, message_id=call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ Мало денег!")

if __name__ == '__main__':
    bot.polling(none_stop=True)