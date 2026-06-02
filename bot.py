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
    types.BotCommand("leaderboards", "Таблица лидеров 🏆"),
    types.BotCommand("me", "Мой профиль 👤")
])

# Данные о рыбах (баланс редкости: легендарки теперь реально редкие)
FISH_DATA = {
    '🟨🟨🟨🟨🟨🟨 Легендарная': {'rarity': 0.5, 'cost_range': (10000, 50000), 'fishes': ['Мегалодон', 'Посейдон']},
    '🟥🟥🟥🟥🟥 Мифическая': {'rarity': 1.5, 'cost_range': (2000, 5000), 'fishes': ['Золотая рыбка', 'Кракен']},
    '🟪🟪🟪🟪 Эпическая': {'rarity': 5, 'cost_range': (600, 1500), 'fishes': ['Осетр', 'Белуга']},
    '🟦🟦🟦 Сверх редкая': {'rarity': 10, 'cost_range': (200, 500), 'fishes': ['Сом', 'Угорь', 'Стерлядь']},
    '🟩🟩 Редкая': {'rarity': 23, 'cost_range': (60, 150), 'fishes': ['Щука', 'Судак', 'Лещ']},
    '⬜ Обычная': {'rarity': 60, 'cost_range': (10, 50), 'fishes': ['Карась', 'Окунь', 'Плотва']}
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
DATA_FILE = '/data/users.json'

def load_data():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_data():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
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
        'inv_list': [],
        'stats': {'total_caught': 0, 'total_earned': 0}
    }
    for key, value in defaults.items():
        if key not in users[user_id]:
            users[user_id][key] = value
            
    return users[user_id]

# Проверка на админа (ID создателя или юзернейм @Idk_228_288)
def is_admin(user_id, username):
    # Мурзик (6796565840), Клей/Idk (5284051771, 6365672326)
    admin_ids = ['5284051771', '6796565840', '6365672326']
    return str(user_id) in admin_ids or username == 'Idk_228_288'

def get_user_status(user_id, username):
    if is_admin(user_id, username):
        return "<b><i>Создатель✏️</i></b>"
    elif str(user_id) == '5515203520' or username == 'Koilo25':
        return "<b>Тестер🕷</b>"
    return "Участник🎣"

@bot.message_handler(commands=['admin_add_money'])
def admin_add_money(message):
    if not is_admin(message.from_user.id, message.from_user.username):
        return
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "Используй: /admin_add_money [user_id] [amount]", message_thread_id=message.message_thread_id)
        return
    target_id, amount = args[1], int(args[2])
    target_data = get_user_data(target_id)
    target_data['balance'] += amount
    save_data()
    bot.reply_to(message, f"✅ Выдано {amount} 💰 пользователю {target_id}", message_thread_id=message.message_thread_id)

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
    if not is_admin(message.from_user.id, message.from_user.username):
        return
    
    args = message.text.split()
    if len(args) < 4:
        return

    action = args[1].lower()
    target = args[2].replace('@', '')
    try:
        amount = int(args[3])
    except ValueError:
        return

    target_id = None
    if target.isdigit():
        if target in users:
            target_id = target
    else:
        for uid, data in users.items():
            if data.get('username') == target:
                target_id = uid
                break
    
    if target_id:
        target_name = users[target_id].get('username') or f"ID:{target_id}"
        if action == 'give':
            users[target_id]['balance'] += amount
            bot.reply_to(message, f"✅ Выдано {amount} 💰 пользователю {target_name}")
        elif action == 'delete':
            users[target_id]['balance'] = max(0, users[target_id]['balance'] - amount)
            bot.reply_to(message, f"💸 Списано {amount} 💰 у пользователя {target_name}")
        save_data()
    else:
        bot.reply_to(message, "❌ Пользователь не найден")

# (удалено и объединено с основным обработчиком ниже)
@bot.message_handler(commands=['fishingrod'])
def fishingrod_admin_command(message):
    if not is_admin(message.from_user.id, message.from_user.username):
        return
    
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "Используй: /fishingrod [give/delete] [юз] [номер (для give)]")
        return

    action = args[1].lower()
    target_username = args[2].replace('@', '')
    
    target_id = None
    for uid, data in users.items():
        if data.get('username') == target_username:
            target_id = uid
            break
            
    if not target_id:
        bot.reply_to(message, "❌ Пользователь не найден")
        return

    if action == 'delete':
        users[target_id]['rod'] = '0'
        save_data()
        bot.reply_to(message, f"✅ Удочка у @{target_username} аннулирована")
    elif action == 'give':
        if len(args) < 4:
            bot.reply_to(message, "Укажи номер удочки (1-4)")
            return
        rod_id = args[3]
        if rod_id in SHOP_RODS:
            users[target_id]['rod'] = rod_id
            save_data()
            bot.reply_to(message, f"✅ Удочка {SHOP_RODS[rod_id]['name']} выдана @{target_username}")
        else:
            bot.reply_to(message, "❌ Нет такой удочки")

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
    args = message.text.split()
    
    # Если это админская команда удаления рыбы
    if len(args) >= 5 and args[1].lower() == 'delete' and is_admin(message.from_user.id, message.from_user.username):
        target_username = args[2].replace('@', '')
        fish_name_query = args[3].lower()
        try:
            amount_to_del = int(args[4])
        except ValueError:
            return

        target_id = None
        for uid, data in users.items():
            if data.get('username') == target_username:
                target_id = uid
                break
                
        if not target_id:
            bot.reply_to(message, "❌ Пользователь не найден")
            return

        user_inv = users[target_id].get('inventory', {})
        found_fish = None
        for full_name in user_inv.keys():
            if fish_name_query in full_name.lower():
                found_fish = full_name
                break
                
        if found_fish:
            current_count = user_inv[found_fish]['count']
            user_inv[found_fish]['count'] = max(0, current_count - amount_to_del)
            if user_inv[found_fish]['count'] == 0:
                del user_inv[found_fish]
                if 'inv_list' in users[target_id] and found_fish in users[target_id]['inv_list']:
                    users[target_id]['inv_list'].remove(found_fish)
            save_data()
            bot.reply_to(message, f"🗑 Удалено {amount_to_del} шт. {found_fish} у @{target_username}", message_thread_id=message.message_thread_id)
        else:
            bot.reply_to(message, "❌ Такая рыба не найдена в инвентаре", message_thread_id=message.message_thread_id)
        return

    # Обычная логика рыбалки
    user = get_user_data(message.from_user.id, message.from_user.username)
    current_rod = SHOP_RODS.get(user.get('rod', '0'), SHOP_RODS['0'])
    cd = current_rod['cd']
    
    if time.time() - user['last_fish'] < cd:
        wait = round(cd - (time.time() - user['last_fish']), 1)
        warn_msg = bot.send_message(message.chat.id, f"⏳ Удочка еще не готова! Подожди {wait} сек.", message_thread_id=message.message_thread_id)
        delete_after_delay(message.chat.id, [message.message_id, warn_msg.message_id])
        return

    # Сразу обновляем время заброса, чтобы пресечь спам
    user['last_fish'] = time.time()
    save_data()

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
        # Инициализируем список для /sell, если его нет
    # Если рыба уже есть, цену не меняем, чтобы не сбивать бонус от наживки
        if 'inv_list' not in user:
            user['inv_list'] = []
        if full_name not in user['inv_list']:
            user['inv_list'].append(full_name)
            
    user['inventory'][full_name]['count'] += 1
    user['stats']['total_caught'] = user['stats'].get('total_caught', 0) + 1
    save_data()
    result = (f"🎉 Вы выловили рыбу!\n\nРыба: {full_name}\nСтоимость: {cost} 💰\n\nРыба добавлена в инвентарь. Продай её через /sell")
    
    # В личке добавляем кнопки для удобства, в группах — только текст
    markup = None
    if message.chat.type == 'private':
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("🎣 Еще раз", callback_data="cmd_fish"),
            types.InlineKeyboardButton("📦 Инвентарь", callback_data="cmd_inventory")
        )
        markup.row(types.InlineKeyboardButton("💰 Продать всё", callback_data="cmd_sell_all"))

    bot.edit_message_text(result, message.chat.id, msg.message_id, reply_markup=markup)

# Обработка быстрых команд через кнопки в ЛС
@bot.callback_query_handler(func=lambda call: call.data.startswith('cmd_'))
def handle_quick_commands(call):
    cmd = call.data.replace('cmd_', '')
    # Эмулируем объект сообщения для существующих функций
    call.message.from_user = call.from_user 
    if cmd == 'fish':
        get_fish(call.message)
    elif cmd == 'inventory':
        show_inventory(call.message)
    elif cmd == 'sell_all':
        # Создаем временный объект сообщения для команды /sell all
        call.message.text = "/sell all"
        sell_fish(call.message)
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['leaderboards'])
def show_leaderboards(message):
    get_user_data(message.from_user.id, message.from_user.username)
    markup = types.InlineKeyboardMarkup()
    btn_global = types.InlineKeyboardButton("🌍 Глобальный", callback_data="lb_global")
    btn_group = types.InlineKeyboardButton("👥 В этой группе", callback_data="lb_group")
    markup.add(btn_global, btn_group)
    bot.send_message(message.chat.id, "🏆 <b>Выберите таблицу лидеров по деньгам:</b>", reply_markup=markup, parse_mode='HTML', message_thread_id=message.message_thread_id)

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
    total_val = 0
    for i, name in enumerate(user['inv_list'], 1):
        count = user['inventory'][name]['count']
        price = user['inventory'][name]['price']
        text += f"{i}. {name} — {count} шт. (цена: {price})\n"
        total_val += count * price
    
    text += f"\n💰 Баланс: {user['balance']} 💰"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"💰 Продать всё за {total_val} 💰", callback_data="cmd_sell_all"))
    
    bot.send_message(message.chat.id, text, reply_markup=markup, message_thread_id=message.message_thread_id)

@bot.message_handler(commands=['profile', 'me'])
def show_profile(message):
    user = get_user_data(message.from_user.id, message.from_user.username)
    rod_name = SHOP_RODS.get(user['rod'], {}).get('name', '???')
    loc_name = LOCATIONS_DATA.get(user['location'], {}).get('name', '???')
    status = get_user_status(message.from_user.id, message.from_user.username)
    
    text = (
        f"👤 <b>Профиль:</b> {user.get('username')}\n"
        f"🎖 Статус: {status}\n"
        f"━━━━━━━━━━━━━━\n"
        f"💰 Баланс: <b>{user['balance']} 💰</b>\n"
        f"📍 Локация: {loc_name}\n"
        f"🎣 Удочка: {rod_name}\n"
        f"📊 Всего выловлено: {user['stats'].get('total_caught', 0)} шт."
    )
    bot.send_message(message.chat.id, text, parse_mode='HTML', message_thread_id=message.message_thread_id)

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
        bot.edit_message_text("🏆 <b>Выберите таблицу лидеров:</b>", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')
        return

    is_global = call.data == "lb_global"
    text = "🌍 <b>Глобальный топ:</b>\n\n" if is_global else "👥 <b>Топ группы:</b>\n\n"
    
    count = 0
    for uid, data in sorted_users:
        if count >= 10: break
        
        if not is_global:
            # Для топа группы проверяем, состоит ли юзер в чате
            try:
                member = bot.get_chat_member(call.message.chat.id, int(uid))
                if member.status in ['left', 'kicked']: continue
            except:
                continue
        
        count += 1
        name = data.get('username', f'ID {uid}').replace('<', '&lt;').replace('>', '&gt;')
        text += f"{count}. {name} — {data.get('balance', 0)} 💰\n"
        
    bot.answer_callback_query(call.id)
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')

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
        
        # Проверка на даунгрейд
        if int(user['rod']) >= int(item_id):
            bot.answer_callback_query(call.id, "❌ У тебя уже есть удочка получше!", show_alert=True)
            return

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