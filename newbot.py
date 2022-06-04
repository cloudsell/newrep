"""

██╗░░░░░░█████╗░███╗░░██╗███████╗██████╗░ ░██████╗░█████╗░███████╗████████╗
██║░░░░░██╔══██╗████╗░██║██╔════╝██╔══██╗ ██╔════╝██╔══██╗██╔════╝╚══██╔══╝
██║░░░░░███████║██╔██╗██║█████╗░░██████╔╝ ╚█████╗░██║░░██║█████╗░░░░░██║░░░
██║░░░░░██╔══██║██║╚████║██╔══╝░░██╔══██╗ ░╚═══██╗██║░░██║██╔══╝░░░░░██║░░░
███████╗██║░░██║██║░╚███║███████╗██║░░██║ ██████╔╝╚█████╔╝██║░░░░░░░░██║░░░
╚══════╝╚═╝░░╚═╝╚═╝░░╚══╝╚══════╝╚═╝░░╚═╝ ╚═════╝░░╚════╝░╚═╝░░░░░░░░╚═╝░░░

Главный файл. (Сам бот)

"""
import random
from text import *
import psutil
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from app.payments.crystalpay import CrystalPay
from app.payments.lolz import LolzPayment
from app.keyboards import *
from app.filemanager import *
from app.sqliteshort import SQLite
from app.config import Config
from loguru import logger
from pyqiwip2p import QiwiP2P
from app.payments.lava import LavaPayment
logger.success("Библиотеки успешно загружены.")

SQLite.create_base()
logger.success("База подключена.")

config = Config()
if config.payment_settings_lolz_token:
    lolzpayment = LolzPayment(config.payment_settings_lolz_token)
    lolzaccount = lolzpayment.me()
    logger.debug(f"\nАккаунт LOLZ:\nИмя: {lolzaccount['username']}\nАйди: {lolzaccount['user_id']}\nБаланс: {lolzaccount['balance']}\nХолд: {lolzaccount['hold']}\n")

if config.payment_settings_crystal_pay_login and config.payment_settings_crystal_pay_secret_1:
    crystalpay = CrystalPay(config.payment_settings_crystal_pay_login, config.payment_settings_crystal_pay_secret_1)
    crystalpaybalances = crystalpay.get_balance()
    logger.debug("\nАккаунт Crystal Pay:\n" + crystalpaybalances)

if config.payment_settings_qiwi_p2p_token:
    p2p = QiwiP2P(auth_key=config.payment_settings_qiwi_p2p_token)

if config.payment_settings_lava_token:
    lava = LavaPayment(config.payment_settings_lava_token)
    lava_balance = lava.get_balance()
    logger.debug("\nАккаунт Lava:\n" + lava_balance)

logger.success("Подключены выбранные способы оплаты.")

logger.debug("Нагрузка процессора: %"+str(psutil.cpu_percent()))
logger.debug("Нагрузка опертивной памяти: %"+str(psutil.virtual_memory().percent))

storage = MemoryStorage()
bot = Bot(token=config.telegram_settings_token)
dp = Dispatcher(bot, storage=storage)

admin_stage = 0
admin_storage = ""
upload_logs = ""

formater = lambda a: "%.2f" % a
logger.success("Успешная авторизация Telegram.")


async def check_subscribtion(message):
    """Проверяем подписку на канал"""

    if not config.telegram_settings_channel_id: return True
    try:
        get_user_id = await bot.get_chat_member(chat_id=config.telegram_settings_channel_id,
                                                user_id=message.from_user.id)
        if get_user_id["status"] == "left":
            await bot.send_message(
                chat_id=message.from_user.id,
                text=CHANNEL_TEXT,
                parse_mode='markdown',
                reply_markup=cancel()
            )
            logger.debug(f"{message.from_user.id} | {message.from_user.username}: Пользователь не вступил в телеграм канал.")
            return False
    except:
        await bot.send_message(
            chat_id=message.from_user.id,
            text=CHANNEL_TEXT,
            parse_mode='markdown',
            reply_markup=cancel()
        )

        logger.debug(f"{message.from_user.id} | {message.from_user.username}: Пользователь не вступил в телеграм канал.")
        return False

    return True


async def setup_bot_commands(_):
    """Ставими команды боту."""

    logger.info("Бот работает")
    bot_commands = [
        types.BotCommand(command="/start", description="Запустить бота."),
        types.BotCommand(command="/admin", description="Админ меню."),
    ]
    logger.debug("Команды бота установлены.")
    await bot.set_my_commands(bot_commands)


async def hello_throttled(*args, **kwargs):
    """Защита от спама."""

    message = args[0]
    await message.answer(NO_SPAM_TEXT, parse_mode='markdown')

    logger.info(f"{message.from_user.id} | {message.from_user.username}: Защита от спама!")


async def hello_throttled_callback(*args, **kwargs):
    """Защита от спама. (Для инлайн кнопок)"""

    callback_query = args[0]
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(chat_id=callback_query.from_user.id,
                           text=NO_SPAM_TEXT,
                           parse_mode='markdown')

    logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Защита от спама!")


@dp.message_handler(commands=['start'])
@dp.throttled(hello_throttled, rate=1)
async def start_command(message: types.Message):
    """Главное меню."""

    if not await check_subscribtion(message): return

    SQLite.get_user(message.from_user.id)

    await message.answer(
        START_TEXT.replace('{userfirstname}',message.from_user.first_name),
        parse_mode=config.telegram_settings_parse_mode,
        reply_markup=main()
    )

    logger.info(f"{message.from_user.id} | {message.from_user.username}: Start.")


@dp.message_handler(commands=['admin'])
@dp.throttled(hello_throttled, rate=1)
async def admin_command(message: types.Message):
    """Админ панель."""

    if message.from_user.id != int(config.telegram_settings_admin_id): return

    await message.answer(
        ADMIN_TEXT.replace('{cpu}', str(psutil.cpu_percent())).replace('{ram}',str(psutil.virtual_memory().percent)),
        parse_mode=config.telegram_settings_parse_mode,
        reply_markup=admin()
    )

    logger.info(f"{message.from_user.id} | {message.from_user.username}: Admin.")


@dp.message_handler(lambda message: message.text and '📜правила📜' in message.text.lower())
@dp.throttled(hello_throttled, rate=1)
async def rules_command(message: types.Message):
    """Правила"""

    if not await check_subscribtion(message): return

    await message.answer(
        RULES_TEXT.replace('{userfirstname}', message.from_user.first_name),
        parse_mode=config.telegram_settings_parse_mode
    )

    logger.info(f"{message.from_user.id} | {message.from_user.username}: Rules.")


@dp.message_handler(lambda message: message.text and '💳пополнить💳' in message.text.lower())
@dp.throttled(hello_throttled, rate=1)
async def payment_command(message: types.Message):
    """Выбор способы оплаты."""

    if not await check_subscribtion(message): return

    await message.answer(
        PAYMENT_TEXT.replace('{userfirstname}', message.from_user.first_name),
        parse_mode=config.telegram_settings_parse_mode,
        reply_markup=deposit()
    )

    logger.info(f"{message.from_user.id} | {message.from_user.username}: Payment.")


@dp.message_handler(lambda message: message.text and '🛒купить логи🛒' in message.text.lower())
@dp.throttled(hello_throttled, rate=1)
async def payment_command(message: types.Message):
    """Выбор способы оплаты."""

    if not await check_subscribtion(message): return

    data = SQLite.get_user(message.from_user.id)

    logsinformation_send = ""

    categories = SQLite.get_categories()
    for category in categories:
        get_logs = SQLite.get_logs(category[1])
        logsinformation_send += logsinformation.replace('{category}',category[0])\
                                .replace('{amount}',formater(category[2]))\
                                .replace('{count}', str(len(get_logs)))+ '\n'

    await message.answer(
        LOGS_MENU.replace('{userfirstname}', message.from_user.first_name).replace('{logsinformation}', logsinformation_send.strip())\
            .replace('{balance}',formater(data[1])),
        parse_mode=config.telegram_settings_parse_mode,
        reply_markup=buy_logs(SQLite.get_categories())
    )

    logger.info(f"{message.from_user.id} | {message.from_user.username}: Buy logs.")


@dp.callback_query_handler(lambda callback: callback.data == 'cancel')
async def cancel_command(callback_query: types.CallbackQuery):
    """Отмена."""

    global admin_stage
    global admin_storage

    await callback_query.answer()

    if callback_query.from_user.id == int(config.telegram_settings_admin_id):
        admin_stage = 0
        admin_storage = ""

    SQLite.want_log(callback_query.from_user.id, '')
    SQLite.want_pay(callback_query.from_user.id, '')

    try:
        await bot.delete_message(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id)
    except:
        pass

    logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Cancel.")


@dp.callback_query_handler(lambda callback: callback.data == 'add_category')
@dp.throttled(hello_throttled_callback, rate=1)
async def add_category_command(callback_query: types.CallbackQuery):
    """Добавить категорию."""

    global admin_stage

    await callback_query.answer()

    if callback_query.from_user.id != int(config.telegram_settings_admin_id): return

    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text=CREATE_CATEGORY_TEXT,
        reply_markup=cancel(),
        parse_mode=config.telegram_settings_parse_mode

    )
    admin_stage = 5

    logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Create new category.")

@dp.callback_query_handler(lambda callback: callback.data == 'settings')
@dp.throttled(hello_throttled_callback, rate=1)
async def settings_command(callback_query: types.CallbackQuery):
    """Настройки категорий."""

    await callback_query.answer()

    if callback_query.from_user.id != int(config.telegram_settings_admin_id): return

    try:
        category = SQLite.get_category(upload_logs)[0][0]
    except:
        category = 'ERROR'

    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text=SETTINGS_TEXT.replace('{category}',category),
        reply_markup=categories_edit(),
        parse_mode=config.telegram_settings_parse_mode

    )

    logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Settings.")


@dp.callback_query_handler(lambda callback: callback.data[:10] == 'upload_to_')
@dp.throttled(hello_throttled_callback, rate=1)
async def upload_to_command(callback_query: types.CallbackQuery):
    """ВЫбрать категироию куда загружать логи."""

    global upload_logs

    await callback_query.answer()

    if callback_query.from_user.id != int(config.telegram_settings_admin_id): return

    upload_logs = callback_query.data[10:]
    data = SQLite.get_category(upload_logs)

    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text=SETUP_CATEGORY_TEXT,
        reply_markup=cancel(),
        parse_mode=config.telegram_settings_parse_mode

    )

    logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Set Category.")


@dp.callback_query_handler(lambda callback: callback.data[:16] == 'delete_category_')
@dp.throttled(hello_throttled_callback, rate=1)
async def del_category_command(callback_query: types.CallbackQuery):
    """Удалить категорию."""

    await callback_query.answer()

    if callback_query.from_user.id != int(config.telegram_settings_admin_id): return

    category = callback_query.data[16:]

    SQLite.del_category(category)

    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text=CATEGORY_DELETED_TEXT,
        reply_markup=cancel(),
        parse_mode=config.telegram_settings_parse_mode

    )

    logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Category delete.")


@dp.callback_query_handler(lambda callback: callback.data == 'set_category')
@dp.throttled(hello_throttled_callback, rate=1)
async def del_category_command(callback_query: types.CallbackQuery):
    """Поставить категорию для загрузки."""

    await callback_query.answer()

    if callback_query.from_user.id != int(config.telegram_settings_admin_id): return

    categories = SQLite.get_categories()
    if not categories:

        await bot.send_message(
            chat_id=callback_query.from_user.id,
            text=CATEGORY_NOT_SET_TEXT,
            reply_markup=cancel(),
            parse_mode=config.telegram_settings_parse_mode

        )
        logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: All Categories has deleted.")
        return

    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text=SET_CATEGORY_TEXT,
        reply_markup=categories_set(categories),
        parse_mode=config.telegram_settings_parse_mode

    )
    logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Categories set.")


@dp.callback_query_handler(lambda callback: callback.data == 'del_category')
@dp.throttled(hello_throttled_callback, rate=1)
async def del_category_command(callback_query: types.CallbackQuery):
    """Удалить категорию."""

    await callback_query.answer()

    if callback_query.from_user.id != int(config.telegram_settings_admin_id): return

    categories = SQLite.get_categories()
    if not categories:

        await bot.send_message(
            chat_id=callback_query.from_user.id,
            text=CATEGORY_NOT_DELETE_TEXT,
            reply_markup=cancel(),
            parse_mode=config.telegram_settings_parse_mode

        )
        logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: All Categories has deleted.")
        return

    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text=CATEGORY_CHOICE_DELETE_TEXT,
        reply_markup=category_delete(categories),
        parse_mode=config.telegram_settings_parse_mode

    )
    logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Categories delete.")


@dp.callback_query_handler(lambda callback: callback.data[:11] == 'user_clear_')
@dp.throttled(hello_throttled_callback, rate=1)
async def profile_clear_command(callback_query: types.CallbackQuery):
    """Стереть баланс с профиля."""

    await callback_query.answer()

    if callback_query.from_user.id != int(config.telegram_settings_admin_id): return

    SQLite.clear_balance(callback_query.data[11:])

    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text=BALANCE_CLEAR_CHECK_TEXT,
        reply_markup=cancel(),
        parse_mode=config.telegram_settings_parse_mode

    )

    logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Balance clear {callback_query.data[11:]}.")


@dp.callback_query_handler(lambda callback: callback.data == 'sends')
@dp.throttled(hello_throttled_callback, rate=1)
async def sends_command(callback_query: types.CallbackQuery):
    """Рассылка."""

    global admin_stage

    await callback_query.answer()

    if callback_query.from_user.id != int(config.telegram_settings_admin_id): return

    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text=SENDS_TEXT,
        reply_markup=cancel(),
        parse_mode=config.telegram_settings_parse_mode

    )

    admin_stage = 2

    logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Check user.")


@dp.callback_query_handler(lambda callback: callback.data == 'download')
@dp.throttled(hello_throttled_callback, rate=1)
async def download_base_command(callback_query: types.CallbackQuery):
    """Скачать базу."""

    global admin_stage

    await callback_query.answer()

    if callback_query.from_user.id != int(config.telegram_settings_admin_id): return

    await bot.send_document(chat_id=callback_query.from_user.id, document=open('base.db', 'rb'))

    logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username} | Upload base.")


@dp.callback_query_handler(lambda callback: callback.data[:12] == 'user_delete_')
@dp.throttled(hello_throttled_callback, rate=1)
async def del_balance_command(callback_query: types.CallbackQuery):
    """Удалить баланс юзеру."""

    global admin_stage
    global admin_storage

    await callback_query.answer()

    if callback_query.from_user.id != int(config.telegram_settings_admin_id): return

    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text=BALANCE_DEL_TEXT,
        reply_markup=cancel(),
        parse_mode=config.telegram_settings_parse_mode

    )

    admin_stage = 4
    admin_storage = callback_query.data[12:]

    logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Del user balance.")


@dp.callback_query_handler(lambda callback: callback.data == 'balance')
@dp.throttled(hello_throttled_callback, rate=1)
async def balance_command(callback_query: types.CallbackQuery):
    """Баланс кошельков."""

    await callback_query.answer()

    if callback_query.from_user.id != int(config.telegram_settings_admin_id): return

    res = ""

    if config.payment_settings_lolz_token:
        lolzpayment = LolzPayment(config.payment_settings_lolz_token)
        lolzaccount = lolzpayment.me()
        res += f"\n*Аккаунт LOLZ:*\nИмя: {lolzaccount['username']}\nАйди: {lolzaccount['user_id']}\nБаланс: {lolzaccount['balance']}\nХолд: {lolzaccount['hold']}\n"

    if config.payment_settings_crystal_pay_login and config.payment_settings_crystal_pay_secret_1:
        crystalpay = CrystalPay(config.payment_settings_crystal_pay_login, config.payment_settings_crystal_pay_secret_1)
        crystalpaybalances = crystalpay.get_balance()
        res += "\n*Аккаунт Crystal Pay:*\n" + crystalpaybalances

    if config.payment_settings_lava_token:
        lava = LavaPayment(config.payment_settings_lava_token)
        lava_balance = lava.get_balance()
        res += "\n*Аккаунт Lava:*\n" + lava_balance

    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text=res,
        parse_mode=config.telegram_settings_parse_mode
    )

    logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Admin balance.")


@dp.callback_query_handler(lambda callback: callback.data[:10] == 'user_give_')
@dp.throttled(hello_throttled_callback, rate=1)
async def give_balance_command(callback_query: types.CallbackQuery):
    """Добавить баланс юзеру."""

    global admin_stage
    global admin_storage

    await callback_query.answer()

    if callback_query.from_user.id != int(config.telegram_settings_admin_id): return

    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text=BALANCE_ADD_TEXT,
        reply_markup=cancel(),
        parse_mode=config.telegram_settings_parse_mode

    )

    admin_stage = 3
    admin_storage = callback_query.data[10:]

    logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Give user balance.")


@dp.callback_query_handler(lambda callback: callback.data == 'profile_check')
@dp.throttled(hello_throttled_callback, rate=1)
async def profile_check_command(callback_query: types.CallbackQuery):
    """Просмотреть информацию о пользователе."""

    global admin_stage

    await callback_query.answer()

    if callback_query.from_user.id != int(config.telegram_settings_admin_id): return

    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text=GIVE_PROFILE_CHECK_TEXT,
        reply_markup=cancel(),
        parse_mode=config.telegram_settings_parse_mode

    )

    admin_stage = 1

    logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Check user.")


@dp.callback_query_handler(lambda callback: callback.data[:6] == 'check_')
@dp.throttled(hello_throttled_callback, rate=1)
async def payment_check_command(callback_query: types.CallbackQuery):
    """Проверка платежей"""

    data = callback_query.data[6:].split('_')
    method = data[0]
    payment_id = data[1]

    logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Check payment...")

    if method == 'lava':
        if not config.payment_settings_lava_token:
            await bot.send_message(
                chat_id=callback_query.from_user.id,
                text=ERROR_PAYMENT_TEXT,
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
            logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Error payment.")
            return

        if SQLite.check_payment(method, payment_id):
            await bot.send_message(
                chat_id=callback_query.from_user.id,
                text=OLD_PAYMENT_TEXT,
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
            logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Old payment.")
            return

        check = lava.check_payment(payment_id)

        if not check:
            await bot.send_message(
                chat_id=callback_query.from_user.id,
                text=NO_PAYMENT_TEXT,
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
            logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: No payment.")
            return

        SQLite.add_payment(method,payment_id)
        SQLite.add_balance(callback_query.from_user.id, check[1])

        await bot.send_message(
                chat_id=callback_query.from_user.id,
                text=NEW_PAYMENT_TEXT.replace('{balance}',formater(check[1])),
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
        logger.success(f"{callback_query.from_user.id} | {callback_query.from_user.username}: +{check[1]} rub.")
        return

    if method == 'lolz':
        if not config.payment_settings_lolz_token:
            await bot.send_message(
                chat_id=callback_query.from_user.id,
                text=ERROR_PAYMENT_TEXT,
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
            logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Error payment.")
            return

        if SQLite.check_payment(method, payment_id):
            await bot.send_message(
                chat_id=callback_query.from_user.id,
                text=OLD_PAYMENT_TEXT,
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
            logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Old payment.")
            return

        check = lolzpayment.check_payment(payment_id, data[3])

        if not check:
            await bot.send_message(
                chat_id=callback_query.from_user.id,
                text=NO_PAYMENT_TEXT,
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
            logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: No payment.")
            return

        SQLite.add_payment(method,payment_id)
        SQLite.add_balance(callback_query.from_user.id, data[3])

        await bot.send_message(
                chat_id=callback_query.from_user.id,
                text=NEW_PAYMENT_TEXT.replace('{balance}',formater(check[1])),
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
        logger.success(f"{callback_query.from_user.id} | {callback_query.from_user.username}: +{data[3]} rub.")
        return

    if method == 'crystalpay':
        if not config.payment_settings_crystal_pay_login:
            await bot.send_message(
                chat_id=callback_query.from_user.id,
                text=ERROR_PAYMENT_TEXT,
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
            logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Error payment.")
            return

        if SQLite.check_payment(method, payment_id):
            await bot.send_message(
                chat_id=callback_query.from_user.id,
                text=OLD_PAYMENT_TEXT,
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
            logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Old payment.")
            return

        check = crystalpay.get_pay_status(payment_id)

        if not check[0]:
            await bot.send_message(
                chat_id=callback_query.from_user.id,
                text=NO_PAYMENT_TEXT,
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
            logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: No payment.")
            return

        SQLite.add_payment(method,payment_id)
        SQLite.add_balance(callback_query.from_user.id, int(check[1]))

        await bot.send_message(
                chat_id=callback_query.from_user.id,
                text=NEW_PAYMENT_TEXT.replace('{balance}',formater(check[1])),
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
        logger.success(f"{callback_query.from_user.id} | {callback_query.from_user.username}: +{check[1]} rub.")
        return

    if method == 'qiwi':
        if not config.payment_settings_qiwi_p2p_token:
            await bot.send_message(
                chat_id=callback_query.from_user.id,
                text=ERROR_PAYMENT_TEXT,
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
            logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Error payment.")
            return

        if SQLite.check_payment(method, payment_id):
            await bot.send_message(
                chat_id=callback_query.from_user.id,
                text=OLD_PAYMENT_TEXT,
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
            logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Old payment.")
            return

        check = p2p.check(bill_id=payment_id)

        if check.status != "paid":
            await bot.send_message(
                chat_id=callback_query.from_user.id,
                text=NO_PAYMENT_TEXT,
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
            logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: No payment.")
            return

        SQLite.add_payment(method,payment_id)
        SQLite.add_balance(callback_query.from_user.id, int(check.amount))

        await bot.send_message(
                chat_id=callback_query.from_user.id,
                text=NEW_PAYMENT_TEXT.replace('{balance}',formater(check[1])),
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
        logger.success(f"{callback_query.from_user.id} | {callback_query.from_user.username}: +{check.amount} rub.")
        return


@dp.message_handler(content_types='document')
async def download_file(message: types.Message):
    """Загружаем логи."""

    if not upload_logs:
        await message.answer(
            text=LOG_ADDED_ERROR_TEXT,
            reply_markup=cancel(),
            parse_mode=config.telegram_settings_parse_mode
        )
        logger.info(f"{message.from_user.id} | {message.from_user.username} | Add log error.")
        return

    if message.from_user.id != int(config.telegram_settings_admin_id):
        return

    file_id = message.document.file_id
    try:
        SQLite.add_log(upload_logs, message.document.file_name)
    except:
        await message.answer(
            text=UPLOAD_CATEGORY_ERROR_TEXT,
            reply_markup=cancel(),
            parse_mode=config.telegram_settings_parse_mode
        )
        logger.info(f"{message.from_user.id} | {message.from_user.username} | Error add log.")
        return

    await bot.download_file_by_id(destination=fr"logs/{message.document.file_name}", file_id=file_id)

    await message.answer(
        text=LOG_ADDED_TEXT,
        reply_markup=cancel(),
        parse_mode=config.telegram_settings_parse_mode
    )
    logger.info(f"{message.from_user.id} | {message.from_user.username} | Add log.")
    return


@dp.callback_query_handler(lambda callback: callback.data == 'qiwi_pay')
@dp.callback_query_handler(lambda callback: callback.data == 'lolz_pay')
@dp.callback_query_handler(lambda callback: callback.data == 'lava_pay')
@dp.callback_query_handler(lambda callback: callback.data == 'crystalpay')
@dp.throttled(hello_throttled_callback, rate=1)
async def payment_command(callback_query: types.CallbackQuery):
    """Оплата."""

    if not await check_subscribtion(callback_query): return

    await callback_query.answer()
    SQLite.want_pay(callback_query.from_user.id,callback_query.data)

    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text=PAYMENT_COUNT_TEXT.replace('{minimal}', formater(int(config.payment_settings_minimal_amount))),
        reply_markup=cancel(),
        parse_mode=config.telegram_settings_parse_mode

    )

    logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Payment summ.")


@dp.callback_query_handler(lambda callback: callback.data[:9] == 'buy_logs_')
@dp.throttled(hello_throttled_callback, rate=1)
async def buy_logs_command(callback_query: types.CallbackQuery):
    """Чекаем логи, их наличие, и продаем если есть (просим пользователя указать количество)"""

    await callback_query.answer()

    if not await check_subscribtion(callback_query): return

    log_type = callback_query.data[9:]
    try:
        data_logs = SQLite.get_logs(log_type)
    except:
        await bot.send_message(
        chat_id=callback_query.from_user.id,
        text=NO_CATEGORY_TEXT,
        reply_markup=cancel(),
        parse_mode=config.telegram_settings_parse_mode

        )
        logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Category not found.")
        return

    count_logs = len(data_logs)
    category = SQLite.get_category(log_type)

    if not count_logs:
        await bot.send_message(
            chat_id=callback_query.from_user.id,
            text=NO_LOGS_TEXT,
            reply_markup=cancel(),
            parse_mode=config.telegram_settings_parse_mode

            )
        logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: No logs.")
        return

    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text=LOGS_COUNT_TEXT.replace('{category}',str(category[0][0])).replace('{count}',str(count_logs))\
        .replace('{amount}', formater(category[0][2])),
        reply_markup=cancel(),
        parse_mode=config.telegram_settings_parse_mode

        )

    SQLite.want_log(callback_query.from_user.id, log_type)

    logger.info(f"{callback_query.from_user.id} | {callback_query.from_user.username}: Buying logs...")
    return


@dp.message_handler()
@dp.throttled(hello_throttled, rate=1)
async def talk(message: types.Message):
    """Просто текст который идет от пользователя."""

    global admin_stage
    global admin_storage

    logger.info(f"{message.from_user.id} | {message.from_user.username}: {message.text}")

    data = SQLite.get_user(message.from_user.id)
    SQLite.want_pay(message.from_user.id,'')
    SQLite.want_log(message.from_user.id,'')

    if data[2]:
        if not await check_subscribtion(message): return

        log_type = data[2]
        try:
            data_logs = SQLite.get_logs(log_type)
        except:
            await message.answer(
            text=NO_CATEGORY_TEXT,
            reply_markup=cancel(),
            parse_mode=config.telegram_settings_parse_mode

            )
            logger.info(f"{message.from_user.id} | {message.from_user.username}: Category not found.")
            return

        count_logs = len(data_logs)
        category = SQLite.get_category(log_type)

        try:
            if int(message.text) > 0:
                pass
            else:
                await message.answer(
                    text=ERROR_AMOUNT_LOGS_TEXT,
                    parse_mode=config.telegram_settings_parse_mode,
                    reply_markup=cancel()
                )
                return
        except:
            await message.answer(
                text=ERROR_AMOUNT_LOGS_TEXT,
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
            return

        if not count_logs:
            await message.answer(
                text=NO_LOGS_TEXT,
                reply_markup=cancel(),
                parse_mode=config.telegram_settings_parse_mode

                )
            logger.info(f"{message.from_user.id} | {message.from_user.username}: No logs.")
            return

        if int(message.text)*category[0][2] > data[1]:
            await message.answer(
                text=NO_MONEY_TEXT.replace('{need}', formater(int(message.text)*category[0][2]-data[1])),
                reply_markup=cancel(),
                parse_mode=config.telegram_settings_parse_mode

                )
            logger.info(f"{message.from_user.id} | {message.from_user.username}: No money.")
            return


        await message.answer(
            text=SUCCESS_PURCHASE_TEXT.replace('{count}',str(int(message.text)))\
            .replace('{spend}',formater(int(message.text)*category[0][2])),
            reply_markup=cancel(),
            parse_mode=config.telegram_settings_parse_mode

            )

        SQLite.del_balance(message.from_user.id, int(message.text)*category[0][2])

        files = []

        for _ in range(int(message.text)):
            get_logs = SQLite.get_logs(data[2])
            SQLite.del_log(data[2],get_logs[0][0])
            files.append(get_logs[0][0])

        name = create_archive(files)
        await message.answer_document(open(fr'cache_zip/{name[0]}', 'rb'))
        delete_files(f'cache_zip/{name[0]}',f"cache/{name[1]}")

        logger.success(f"{message.from_user.id} | {message.from_user.username}: Buy logs: {message.text} count...")
        return

    if data[3]:
        try:
            if int(message.text) > 0:
                pass
            else:
                await message.answer(
                    text=ERROR_AMOUNT_TEXT,
                    parse_mode=config.telegram_settings_parse_mode,
                    reply_markup=cancel()
                )
                return
        except:
            await message.answer(
                text=ERROR_AMOUNT_TEXT,
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
            return

        if int(message.text) < int(config.payment_settings_minimal_amount):
            await message.answer(
                text=MINIMAL_AMOUNT_ERROR_TEXT.replace('{minimal}', formater(int(config.payment_settings_minimal_amount))),
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
            return

    if data[3] == 'lolz_pay':
        if not config.payment_settings_lolz_token:
            await message.answer(
                text=ERROR_PAYMENT_TEXT,
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
            return

        await message.answer(
                text=LOLZ_PAY_TEXT.replace('{amount}',formater(int(message.text))),
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=check_payment_lolz(payment_id=random.randint(0,999999999), link='https://lolz.guru/members/' + str(lolzaccount['user_id']), amount=message.text)
            )
        return

    if data[3] == 'qiwi_pay':
        if not config.payment_settings_qiwi_p2p_token:
            await message.answer(
                text=ERROR_PAYMENT_TEXT,
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
            return

        new_bill = p2p.bill(bill_id=random.randint(0,999999999), amount=int(message.text), lifetime=60)

        await message.answer(
                text=QIWI_PAY_TEXT.replace('{amount}',formater(int(message.text))),
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=check_payment_qiwi(new_bill.bill_id , new_bill.pay_url)
            )
        return

    if data[3] == 'crystalpay':
        if not config.payment_settings_qiwi_p2p_token:
            await message.answer(
                text=ERROR_PAYMENT_TEXT,
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
            return

        response = crystalpay.generate_pay_link(int(message.text))

        await message.answer(
                text=CRYSTAL_PAY_TEXT.replace('{amount}',formater(int(message.text))),
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=check_payment_crystal_pay(response[0] , response[1])
            )
        return

    if data[3] == 'lava':
        if not config.payment_settings_lava_token:
            await message.answer(
                text=ERROR_PAYMENT_TEXT,
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
            return

        response = lava.create_payment(int(message.text))

        await message.answer(
                text=LAVA_PAY_TEXT.replace('{amount}',formater(int(message.text))),
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=check_payment_lava(response[0] , response[1])
            )
        return

    if message.from_user.id != int(config.telegram_settings_admin_id): return

    if admin_stage == 1:
        try:
            get_user = await bot.get_chat_member(chat_id=int(message.text.strip()), user_id=int(message.text.strip()))

            data = SQLite.get_user(get_user.user.id)

            await message.answer(
                text=PROFILE_CHECK_TEXT.replace('{username}', str(get_user.user.username))\
                .replace('{balance}', formater(data[1])).replace('{userid}',str(get_user.user.id)),
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=profile(get_user.user.id)
            )

            admin_stage = 0
        except:
            await message.answer(
                text=NO_PROFILE_CHECK_TEXT,
                parse_mode=config.telegram_settings_parse_mode
            )

            admin_stage = 0

    if admin_stage == 2:
        admin_stage = 0

        users = SQLite.get_users()

        for user in users:
            try:
                await bot.send_message(chat_id=user[0], text=message.text)
            except:
                pass

        await message.answer(
            text=SENDS_END_TEXT,
            reply_markup=cancel(),
            parse_mode=config.telegram_settings_parse_mode

        )
        logger.info(f"{message.from_user.id} | {message.from_user.username} | Sends.")

    if admin_stage == 3:
        admin_stage = 0
        if not admin_storage:
            return

        try:
             if int(message.text) > 0:
                 pass
             else:
                 await message.answer(
                     text=ERROR_AMOUNT_TEXT,
                     parse_mode=config.telegram_settings_parse_mode,
                     reply_markup=cancel()
                 )
                 admin_storage = ""
                 return
        except:
            await message.answer(
                text=ERROR_AMOUNT_TEXT,
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
            admin_storage = ""
            return

        SQLite.add_balance(int(admin_storage),int(message.text))
        get_user = await bot.get_chat_member(chat_id=int(admin_storage), user_id=int(admin_storage))
        get_user_data = SQLite.get_user(int(admin_storage))

        admin_storage = ""

        await message.answer(
             text=BALANCE_ADDED_CHECK_TEXT.replace("{username}" ,str(get_user.user.username))
                .replace('{balance}', formater(get_user_data[1])),
             parse_mode=config.telegram_settings_parse_mode,
             reply_markup=cancel()
         )

        try:
            await bot.send_message(
                 text=NEW_PAYMENT_TEXT.replace('{balance}', formater(int(message.text))),
                 parse_mode=config.telegram_settings_parse_mode,
                 reply_markup=cancel()
            )
        except:
            pass

        return

    if admin_stage == 4:
        admin_stage = 0
        if not admin_storage:
            return

        try:
             if int(message.text) > 0:
                 pass
             else:
                 await message.answer(
                     text=ERROR_AMOUNT_TEXT,
                     parse_mode=config.telegram_settings_parse_mode,
                     reply_markup=cancel()
                 )
                 admin_storage = ""
                 return
        except:
            await message.answer(
                text=ERROR_AMOUNT_TEXT,
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
            admin_storage = ""
            return

        get_user = await bot.get_chat_member(chat_id=int(admin_storage), user_id=int(admin_storage))
        get_user_data = SQLite.get_user(int(admin_storage))

        SQLite.del_balance(int(admin_storage),int(message.text))
        admin_storage = ""

        await message.answer(
             text=BALANCE_DELETED_CHECK_TEXT.replace("{username}" ,str(get_user.user.username))
                .replace('{balance}', formater(get_user_data[1])),
             parse_mode=config.telegram_settings_parse_mode,
             reply_markup=cancel()
         )
        return

    if admin_stage == 5:
        admin_stage = 6

        admin_storage = message.text

        await message.answer(
             text=LOGS_CATEGORY_AMOUNT_TEXT,
             parse_mode=config.telegram_settings_parse_mode,
             reply_markup=cancel()
         )
        return

    if admin_stage == 6:
        try:
            if int(message.text) > 0:
                pass
            else:
                await message.answer(
                    text=ERROR_AMOUNT_CATEGORY_TEXT,
                    parse_mode=config.telegram_settings_parse_mode,
                    reply_markup=cancel()
                )
                return
        except:
            await message.answer(
                text=ERROR_AMOUNT_CATEGORY_TEXT,
                parse_mode=config.telegram_settings_parse_mode,
                reply_markup=cancel()
            )
            return

        data = ''
        for _ in range(10):
            data += random.choice(list('qwertyuiop1234567890'))

        SQLite.create_category(admin_storage, data, int(message.text))
        await message.answer(
             text=CATEGORY_CREATED_TEXT,
             parse_mode=config.telegram_settings_parse_mode,
             reply_markup=cancel()
         )
        return


executor.start_polling(dp, skip_updates=True, on_startup=setup_bot_commands)
