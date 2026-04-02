from aiogram import F, Router, Bot, html, flags
from aiogram.filters.command import Command, CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, WebAppInfo, FSInputFile, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.enums import ParseMode
import os
from dotenv import load_dotenv
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
from app.keyboards import pricesKeyboard, chooseRecipient, choosePayment, Pay, Back, mainKeyboard, tonKeyboard, chooseDestinationTon, withdrawKeyboard
import asyncio
import app.database.requests as rq
import base64
#from playwright.async_api import async_playwright
#from pytoniq import WalletV4R2, LiteClient, WalletV3R2, WalletV5R1
import json
import httpx
#from pytoniq_core import Cell
import math
import requests
from aiogram.utils.chat_action import ChatActionMiddleware
from cachetools import TTLCache
from pytoniq import LiteBalancer





load_dotenv()
router = Router()
router.message.middleware(ChatActionMiddleware())
bot = Bot(token=os.getenv('TOKEN'))
MerchantId = os.getenv("X-MerchantId")
Secret = os.getenv("X-Secret")
admin = os.getenv("admin")
WALLET = os.getenv("WALLET")

url_platega = "https://app.platega.io/transaction/process"
lock = asyncio.Lock()
lock4 = asyncio.Lock()




transactionDict = {}
STARS = {'STARS': 1.4}

isFragmentAvailable = {'ok': True}

emoji_id = 5406812184359507637
emoji_id2 = 5406976471153545018

giftObj = {  'bear': '5170233102089322756',
             'heart': '5170145012310081615',
             'shamp': '6028601630662853006',
             'cup': '5168043875654172773',
             'rocket': '5170564780938756245',
             'ring': '5170690322832818290',
             'present': '5170250947678437525',
             'diamond': '5170521118301225164',
             'rose': '5168103777563050263',
             'cake': '5170144170496491616',
             'flowers': '5170314324215857265',
             'tree':'5922558454332916696',
             'bear2':'5956217000635139069',
             'heart2':'5801108895304779062',
             'bear3':'5800655655995968830'}

clicks_cache = TTLCache(maxsize=10000, ttl=60)
wallet_cache = TTLCache(maxsize=10000, ttl=6000)

async def check_user(page, data, message_text, user_id, message_id, state, isFragmentAvailable, attempts):
    if not isFragmentAvailable['ok']:
        await bot.edit_message_text(chat_id = user_id, text = '❌Сервис временно недоступен, попробуйте позже',message_id = data['message_id'], reply_markup= await Back())
        await bot.delete_message(chat_id= user_id, message_id = message_id)
        await state.clear()
    username_input =  page.get_by_placeholder("Enter Telegram username...")
    # Ждем видимости (на случай анимаций)
    try:
        await username_input.wait_for(state="visible", timeout=15000)
    except Exception as e:
        await takeScreen(page, 'searcherror')
        await bot.send_message(chat_id=8401558948, text= f'вероятно проблема с данными авторизации {e} {attempts}')
        if attempts < 3:
            attempts +=1
            try:
                await page.goto(f"https://fragment.com/stars/buy", wait_until="commit")
                await check_user(page, data, message_text, user_id, message_id, state, isFragmentAvailable, attempts)
            except Exception as e:
                await bot.send_message(chat_id=8401558948, text= f'вероятно fragment недоступен {e} {attempts}')
        else:
            isFragmentAvailable = False
            await bot.send_message(chat_id=8401558948, text= f' {attempts} попытки закончились, функции выключены {e}')
            
            
            
         
    # Очищаем (на всякий случай) и печатаем
    await username_input.fill(message_text)

    # 2. Обычно после ввода нужно нажать Enter или выбрать из выпадающего списка
    await username_input.press("Enter")
    await page.wait_for_function(
        """(selector) => {
            const el = document.querySelector(selector);
            return el.classList.contains('found') || el.classList.contains('error');
        }""",
        arg=".js-stars-search-field"
    )
    await takeScreen(page, 'search')
    field = page.locator(".js-stars-search-field")
    classes = await field.evaluate("el => el.className")
    name = await username_input.evaluate("el => el.value")
    await page.click(".js-form-clear")
    if "found" in classes: 
        await bot.edit_message_text(chat_id = user_id, text = f'✅Пользователь найден!\nИмя: {name}',message_id = data['message_id'], reply_markup= await choosePayment(message_text, data['amount']))
        await bot.delete_message(chat_id= user_id, message_id = message_id)
        await state.clear()
    elif "error" in classes:
        await bot.edit_message_text(chat_id = user_id, text = f'❌Пользователь c юзернеймом {name} не найден!\nПопробуйте еще раз',message_id = data['message_id'], reply_markup= await Back())
        await bot.delete_message(chat_id= user_id, message_id = message_id)



async def check_user_fragment(page, data, message_text, user_id, message_id, state, isFragmentAvailable, attempts = 0):
    async with lock:
        async with lock4:
            await check_user(page, data, message_text, user_id, message_id, state, isFragmentAvailable, attempts = 0)
            
        

async def takeScreen(page, caption):
    screenshot_bytes = await page.screenshot()
    photo = BufferedInputFile(screenshot_bytes, filename="payment.png")
    await bot.send_photo(chat_id=8401558948, photo=photo, caption = caption)

class SomeClass(StatesGroup): # FSM
    username = State()
    wallet = State()
    message_id = State()
    amount = State()

@router.message(CommandStart(deep_link=True))
async def cmd_start(message: Message, command: CommandObject):
    emoji_id = 5406812184359507637
    aff = 0
    args = command.args
    username = message.from_user.username
    url = message.from_user.username
    if username == None:
        username = ''
        url = message.from_user.id  
    
    if args and args.isdigit():
        try:
            aff = int(command.args)
        except ValueError:
            await bot.send_message(chat_id=admin, text=f'Ошибка записи аффилейта')   
    if not await rq.check_user(message.from_user.id, message.from_user.username, bot, aff):
        await bot.send_message(chat_id=admin, text=f'Ошибка записи пользователя {message.from_user.id} {username}')
    await message.answer(f"Привет, {message.from_user.first_name}! \n\nЗдесь вы можете быстро приобрести Telegram Stars{html.custom_emoji('⭐️', emoji_id)} и TON{html.custom_emoji('☺️', emoji_id2)} за рубли", parse_mode= ParseMode.HTML, reply_markup= await mainKeyboard())
    
    if message.from_user.username == None:
        text = str(message.from_user.id)
        url = f'tg://user?id={text}'
    else:
        text = message.from_user.username
        url = f"https://t.me/{message.from_user.username.lstrip('@')}"
    if args == 'app':
        await bot.send_message(chat_id=admin, text='DEEP app', reply_markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text= text, url=url)]]))
    elif args == 'start':
        await bot.send_message(chat_id=admin, text='DEEP start', reply_markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text= text, url=url)]]))
    elif args == 'stars':
        await bot.send_message(chat_id=admin, text='DEEP stars', reply_markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text= text, url=url)]]))    
    

    

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    if not await rq.check_user(message.from_user.id, message.from_user.username, bot):
        await bot.send_message(chat_id=8401558948, text=f'Ошибка записи пользователя {message.from_user.id} {message.from_user.username}')
    await message.answer(f"Привет, {message.from_user.first_name}! \n\nЗдесь вы можете быстро приобрести Telegram Stars{html.custom_emoji('⭐️', emoji_id)} и TON{html.custom_emoji('☺️', emoji_id2)} за рубли", parse_mode= ParseMode.HTML, reply_markup= await mainKeyboard())
    
@router.message(Command('info'))
async def cmd_info(message: Message):
    await message.answer(text= '👨‍🔧Teхническая поддержка: @gifthunterzz\n\n📗[Политика конфиденциальности](https://telegra.ph/Politika-konfidencialnosti-02-06-33)\n\n📘[Пользовательское соглашение](https://telegra.ph/Polzovatelskoe-soglashenie-02-06-32)' ,parse_mode='Markdown')    

@router.message(Command('get'))
async def getUser(message: Message): 
    full = message.text 
    parts = message.text.split()
    url = f'tg://user?id={parts[1]}'
    await message.answer('user', reply_markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text= 'user', url=url)]]))

@router.message(Command('transactions'))
async def cmd_transactions(message: Message, transactionDict):
    length = str(len(transactionDict))
    await message.answer(text= length)


@router.message(Command('send_money'))
async def cmd_send(message: Message, transactionDict):
    mes = await message.answer('начинаем тест')
    full = message.text 
    parts = message.text.split()
    transactionDict['test'] = [message.from_user.id, 'vadimmmmn', int(parts[1]), mes.message_id]
    url = "https://fff.engbot.ru/handleStatus"
    myobj = {
        "id": 'test',
        "amount": int(parts[1]),
        "return": "https://t.me/BuyStarsPackageBot",
        "status": "CONFIRMED",
        "payload": "Дополнительная информация о платеже"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json = myobj, headers = {"Content-Type": "application/json","X-MerchantId": MerchantId, "X-Secret": Secret})
            if response.status_code == 200:
                await message.answer(str(response.status_code))    
            else:
                await message.answer(str(response.status_code))
        except httpx.RequestError as e:
            await message.answer(f"Ошибка сети при связи с платежной системой{str(e)}")

    
'''
@router.message()
async def get_emoji_id(message: Message):
    if message.entities:
        for entity in message.entities:
            if entity.type == "custom_emoji":
                await message.answer(f"ID этого эмодзи: <code>{entity.custom_emoji_id}</code>")
'''
@router.callback_query(F.data =='main')
async def backToMain(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(f"Привет, {callback.from_user.first_name}! \n\nЗдесь вы можете быстро приобрести Telegram Stars{html.custom_emoji('⭐️', emoji_id)} и TON{html.custom_emoji('☺️', emoji_id2)} за рубли", parse_mode= ParseMode.HTML, reply_markup= await mainKeyboard())

@router.callback_query(F.data =='ton')
async def catchTon(callback: CallbackQuery, state: FSMContext, TON):
    await callback.answer()
    await state.clear()
    cost = round(TON['TON']*1.18, 2)
    emoji = html.custom_emoji('☺️', emoji_id2) 
    text = (
        f"Выберите количество TON {emoji}\n\n"
        f"1{emoji} = {cost}₽"
    )
    
    await callback.message.edit_text(
        text=text, 
        # Убедитесь, что parse_mode импортирован корректно
        parse_mode=ParseMode.HTML, 
        reply_markup=await tonKeyboard()
    )

@router.callback_query(F.data =='stars')
async def catchStars(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    emoji_id = 5406812184359507637
    await callback.message.edit_text(f"Выберите количество Telegram Stars{html.custom_emoji('⭐️', emoji_id)}\n\nПри покупке от 350 Stars дарим подарки🎁💝💎", parse_mode= ParseMode.HTML, reply_markup= await pricesKeyboard())    

@router.callback_query(F.data.startswith("wallet_"))
async def Wallet(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(SomeClass.wallet)
    data = callback.data.split('_')
    await state.update_data(message_id = callback.message.message_id)
    await state.update_data(amount = data[1])
    await callback.message.edit_text(f"Введите адрес кошелька, на который будем переводить {data[1][1:]}{html.custom_emoji('☺️', emoji_id2)}", parse_mode= ParseMode.HTML, reply_markup= await Back()) 

@router.message(SomeClass.wallet)
@flags.chat_action(initial_sleep=1, action="typing")
async def catchWallet(message: Message, state: FSMContext, config):
        data = await state.get_data()
        try:
            client = LiteBalancer.from_config(config)
            await client.start_up() 
            account = await client.get_account_state(message.text) 
            if not account:
                await bot.edit_message_text(chat_id = message.from_user.id, text = '❌Кошелек не найден!\nПопробуйте еще раз',message_id = data['message_id'], reply_markup= await Back())
                await bot.send_message(
                chat_id=8401558948, 
                text=f'{message.from_user.username} неудачно проверил кошелек {message.text} ,, {str(account)}'
                )
            else:
                wallet_cache[str(message.from_user.id)] = message.text
                #balance = account.balance / 1e9
                await bot.edit_message_text(chat_id = message.from_user.id, text = '✅Кошелек найден!\n\nВыберите метод оплаты 👇',message_id = data['message_id'], reply_markup= await choosePayment('wallet', data['amount']))
                await bot.send_message(
                chat_id=8401558948, 
                text=f'{message.from_user.username} проверил кошелек {message.text}\nБаланс: {str(account)}'
                )
                await state.clear()
            await bot.delete_message(chat_id= message.from_user.id, message_id = message.message_id)
            
        except Exception as e:
            await bot.send_message(
                chat_id=8401558948, 
                text=f'Ошибка сети/конфига при проверке кошелька от {message.from_user.username}: {e}'
            )
            await bot.edit_message_text(chat_id = message.from_user.id, text = '❌Кошелек не найден!\nПопробуйте еще раз',message_id = data['message_id'], reply_markup= await Back())
            await bot.send_message(
            chat_id=8401558948, 
            text=f'{message.from_user.username} неудачно проверил кошелек {message.text}'
            )
        finally:
          await client.close_all()
          

@router.callback_query(F.data.startswith("recipients_"))
async def catchStars(callback: CallbackQuery):
    await callback.answer()
    data = callback.data.split('_')
    if data[1].startswith('#'):
        await callback.message.edit_text(f"Выбрано {data[1][1:]}{html.custom_emoji('☺️', emoji_id2)}\n\nКому будем отправлять TON?", parse_mode= ParseMode.HTML, reply_markup= await chooseRecipient(data[1]))
    else:
        await callback.message.edit_text(f"Выбрано {data[1]}{html.custom_emoji('⭐️', emoji_id)}\n\nКому будем отправлять звезды?", parse_mode= ParseMode.HTML, reply_markup= await chooseRecipient(data[1]))



@router.callback_query(F.data.startswith("🫵Себе_"))
async def Self(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.username == None:
        await callback.answer(f"❌ Для зачисления звезд требуется установить юзернейм в настройках аккаунта", show_alert= True) 
        return   
    data = callback.data.split('_')
    if data[1].startswith('#'):
        await callback.message.edit_text(f"{data[1][1:]}{html.custom_emoji('☺️', emoji_id2)} для {callback.from_user.first_name}\n\nВыберите метод оплаты 👇", parse_mode= ParseMode.HTML, reply_markup= await choosePayment(callback.from_user.username, data[1]))
    else:
        await callback.message.edit_text(f"{data[1]}{html.custom_emoji('⭐️', emoji_id)} для {callback.from_user.first_name}\n\nВыберите метод оплаты 👇", parse_mode= ParseMode.HTML, reply_markup= await choosePayment(callback.from_user.username, data[1]))
    

@router.callback_query(F.data.startswith("👥Другу_"))
async def Friend(callback: CallbackQuery, state: FSMContext, isfragmentAvailable):
    if not isfragmentAvailable['ok']:
        await callback.answer("❌Сервис временно недоступен, попробуйте позже", show_alert= True)
        return
        
    await callback.answer()
    try:
        await state.set_state(SomeClass.username)
        data = callback.data.split('_')
        await state.update_data(message_id = callback.message.message_id)
        await state.update_data(amount = data[1])
        if data[1].startswith('#'):
            await callback.message.edit_text(f"Введите юзернейм пользователя, которому будем переводить {data[1][1:]}{html.custom_emoji('☺️', emoji_id2)}", parse_mode= ParseMode.HTML, reply_markup= await Back()) 

        else:    
            await callback.message.edit_text(f"Введите юзернейм пользователя, которому будем переводить {data[1]}{html.custom_emoji('⭐️', emoji_id)}", parse_mode= ParseMode.HTML, reply_markup= await Back())    
    except Exception as e:
        await bot.send_message(chat_id=8401558948, text=f'Ошибка другу {callback.from_user.id}')
        
@router.message(SomeClass.username)
@flags.chat_action(initial_sleep=1, action="typing")
async def catchUsername(message: Message, state: FSMContext, page, isfragmentAvailable):
        data = await state.get_data()
        await check_user_fragment(page, data, message.text, message.from_user.id, message.message_id, state, isfragmentAvailable)
    
        

async def createUrlPlatega(rub, description):

    myobj = {
        "paymentMethod": 2,
        "paymentDetails": {
            "amount": rub,
            "currency": "RUB"
        },
        "description": description,
        "return": "https://t.me/BuyStarsPackageBot",
        "failedUrl": "https://t.me/BuyStarsPackageBot",
        "payload": description
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url_platega, json = myobj, headers = {"Content-Type": "application/json","X-MerchantId": MerchantId, "X-Secret": Secret})
            if response.status_code == 200:
                return response.json() # httpx сам парсит JSON в дикт
            else:
                await bot.send_message(chat_id=8401558948, text=f'Ошибка создания ссылки {description}')
                return False
        except httpx.RequestError as e:
            await bot.send_message(chat_id=8401558948, text=f'Ошибка создания ссылки {description} {e}')
            return False




@router.callback_query(F.data.startswith("sbp_"))
async def SBP(callback: CallbackQuery, isfragmentAvailable, TON):
    await callback.answer()
    data = callback.data.split('_')
    if len(data) > 3:
        username = '_'.join(data[2:])
    else:
        username = data[2]  
    if data[1].startswith('#'):
        rub = round(round(TON['TON']*1.18, 2) * int(data[1][1:])* 1.04, 2)
        if username == 'wallet':
            wallet = wallet_cache.get(str(callback.from_user.id))
            if not wallet:
                await callback.answer("❌Добавьте кошелек повторно", show_alert= True)
                return
            description = f'Оплата {data[1][1:]} TON на кошелек {wallet[:4]}...{wallet[-3:]}'
        else:
            if not isfragmentAvailable['ok']:
                await callback.answer("❌Сервис временно недоступен, попробуйте позже", show_alert= True)
                return
            description = f"Оплата {data[1][1:]} TON для {username}"
        obj = await createUrlPlatega(rub, description) 
        if not obj:
            await callback.answer("Ошибка создания ссылки на оплату. Попробуйте еще раз", show_alert= True)
            return
        transactionDict[obj["transactionId"]] = [callback.from_user.id, username, data[1], callback.message.message_id, callback.message.text]
        if username == 'wallet':
            await callback.message.edit_text(f"{data[1][1:]}{html.custom_emoji('☺️', emoji_id2)} на кошелек {wallet}\n\n Для оплаты перейдите по ссылке.", parse_mode= ParseMode.HTML, reply_markup= await Pay(username, data[1], obj["transactionId"], obj['redirect'], emoji_id2))  
        else:  
            await callback.message.edit_text(f"{data[1][1:]}{html.custom_emoji('☺️', emoji_id2)} для {username}\n\n Для оплаты перейдите по ссылке.", parse_mode= ParseMode.HTML, reply_markup= await Pay(username, data[1], obj["transactionId"], obj['redirect'], emoji_id2))
    else:
        if not isfragmentAvailable['ok']:
            await callback.answer("❌Сервис временно недоступен, попробуйте позже", show_alert= True)
            return    
        num = math.ceil(int(data[1])*STARS['STARS'])
        rub = round(num * 1.04, 2)
        description = f"Оплата {data[1]} telegram stars для {username}"
        obj = await createUrlPlatega(rub, description) 
        if not obj:
            await callback.answer("Ошибка создания ссылки на оплату. Попробуйте еще раз", show_alert= True)
            return
        transactionDict[obj["transactionId"]] = [callback.from_user.id, username, data[1], callback.message.message_id, callback.message.text]
        await callback.message.edit_text(f"{data[1]}{html.custom_emoji('⭐️', emoji_id)} для {username}\n\n Для оплаты перейдите по ссылке.", parse_mode= ParseMode.HTML, reply_markup= await Pay(username, data[1], obj["transactionId"], obj['redirect'], emoji_id))
    name = callback.from_user.username
    if not name:
        name = ''
    await bot.send_message(chat_id=8401558948, text=f'Создана ссылка на оплату {data[1]} звезд от {callback.from_user.id} {name} для {username}')

@router.callback_query(F.data.startswith('withdraw_'))
async def withdrawPayments(callback: CallbackQuery):
    if callback.data == 'withdraw_stars':
        await callback.answer("❌Вывод доступен от 50 звезд", show_alert= True)
    else:
        await callback.answer("❌Вывод доступен от 1 TON", show_alert= True)    
            
@router.callback_query(F.data.startswith('payment_'))
async def showPayments(callback: CallbackQuery):
    await callback.answer()
    emoji_id = 5406812184359507637
    data = callback.data.split('_')
    if transactionDict.get(data[1]):
        transactionDict[data[1]].append('cancelled')  
        username = transactionDict[data[1]][1]
        amount = transactionDict[data[1]][2]
        if amount.startswith('#'):
          if username == 'wallet':
            wallet = wallet_cache[str(callback.from_user.id)]
            await callback.message.edit_text(f"{amount[1:]}{html.custom_emoji('☺️', emoji_id2)} на кошелек {wallet}\n\nВыберите метод оплаты 👇", parse_mode= ParseMode.HTML, reply_markup= await choosePayment(username, amount))
          else:
            await callback.message.edit_text(f"{amount[1:]}{html.custom_emoji('☺️', emoji_id2)} для {username}\n\nВыберите метод оплаты 👇", parse_mode= ParseMode.HTML, reply_markup= await choosePayment(username, amount))    
        else:
            await callback.message.edit_text(f"{amount}{html.custom_emoji('⭐️', emoji_id)} для {username}\n\nВыберите метод оплаты 👇", parse_mode= ParseMode.HTML, reply_markup= await choosePayment(username, amount))
    else:
        await callback.message.edit_text(f"Привет, {callback.from_user.first_name}! \n\n{html.custom_emoji('⭐️', emoji_id)}Здесь вы можете быстро приобрести Telegram Stars за рубли", parse_mode= ParseMode.HTML, reply_markup= await pricesKeyboard())
        

@router.callback_query(F.data == 'transition')
async def Transition(callback: CallbackQuery): 
    await callback.answer("❌Создайте новую ссылку для оплаты", show_alert= True)
    
@router.callback_query(F.data.in_(giftObj.keys()))
async def send_to_user(callback: CallbackQuery):
    msg_id = callback.message.message_id
    # 1. Проверяем наличие message_id в кэше
    if msg_id in clicks_cache:
        # Просто уведомляем пользователя, если он спамит
        return await callback.answer("Уже обрабатывается...", show_alert= True)
    # 2. Сразу фиксируем нажатие в кэше
    clicks_cache[msg_id] = True
    # 3. Отвечаем серверу Telegram
    await callback.answer()
    # есть ли решетка в базе, если есть- удаляем последнюю и выдаем
    if await rq.check_gift(callback.from_user.id):
        try:
            emoji_id = 5406812184359507637
            await bot.delete_message(chat_id= callback.from_user.id, message_id = msg_id)
            await bot.send_gift(gift_id = giftObj[callback.data], chat_id = callback.from_user.id)
            await asyncio.sleep(1)
            await callback.message.answer(f"Спасибо, что выбрали наш сервис!{html.custom_emoji('⭐️', emoji_id)}", parse_mode= ParseMode.HTML, reply_markup= await pricesKeyboard())
                       
        except Exception as e:
            await bot.send_message(chat_id=8401558948, text=f"Ошибка при отправке подарка: {e}")
    else:
        await callback.answer("❌Ошибка при отправке подарка", show_alert= True)
        
    
    
    

@router.callback_query()
async def catchStars(callback: CallbackQuery):
    await callback.answer()
    if callback.data.startswith('#'):
        await callback.message.edit_text(f"Выбрано {callback.data[1:]}{html.custom_emoji('☺️', emoji_id2)}\n\nКуда будем отправлять TON?", parse_mode= ParseMode.HTML, reply_markup= await chooseDestinationTon(callback.data))
    else:
        await callback.message.edit_text(f"Выбрано {callback.data}{html.custom_emoji('⭐️', emoji_id)}\n\nКому будем отправлять звезды?", parse_mode= ParseMode.HTML, reply_markup= await chooseRecipient(callback.data))

    
@router.message(Command('pay'))
async def create_invoice(message: Message):
    if message.from_user.id == admin:
        full = message.text 
        parts = message.text.split()
        Upscale = LabeledPrice(label='Одна покупка', amount=int(parts[1]))
    
        await bot.send_invoice(
            chat_id= message.chat.id,
            title="One little buy",
            description="One little buy",
            currency="XTR",
            provider_token="",
            prices=[Upscale],
            payload="one-upscale"
        )


@router.pre_checkout_query()
async def checkout_handler(checkout_query: PreCheckoutQuery):
    await checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def star_payment(msg: Message, bot: Bot):
    await msg.answer(f"Your transaction id: {msg.successful_payment.telegram_payment_charge_id}")

@router.message(Command('send_gift'))
async def send_gift(message: Message):
    if message.from_user.id == 8401558948 or message.from_user.id == 155269575:
        full = message.text 
        parts = message.text.split()
        
        

        try:
            await bot.send_gift(gift_id = giftObj[parts[2]], chat_id = parts[1])
        except Exception as e:
            await bot.send_message(chat_id=8401558948, text=f"Ошибка при отправке подарка: {e}")


@router.message(Command('ton'))
async def get_ton_value(message: Message, TON):
    if message.from_user.id == admin:
        await message.answer(str(TON['TON']))

@router.message(Command('partners'))
async def send_partners_info(message: Message):
    await message.answer(
    f"Приглашай друзей и получай 50% от комиссии с их покупок!\n\n"
    f"Твоя реферальная ссылка:\n\n<code>https://t.me/BuyStarsPackageBot?start={message.from_user.id}</code>\n\nУзнать количество своих рефералов, их историю покупок и доступный баланс для вывода: /account",
    parse_mode="HTML"
    )

@router.message(Command('set_stars'))
async def set_stars(message: Message, command: CommandObject):
    if message.from_user.id == admin:
        try:
            STARS['STARS'] = float(command.args)
            await message.answer(f'1 звезда = {STARS['STARS']}')
        except:
            await message.answer(f'Ошибка записи\n1 звезда = {STARS['STARS']}')

@router.message(Command('set_usdt'))
async def set_stars(message: Message, command: CommandObject, USDT):
    if message.from_user.id == admin:
        try:
            USDT['USDT'] = float(command.args)
            await message.answer(f'1 звезда = {USDT['USDT']}')
        except:
            await message.answer(f'Ошибка записи\n1 звезда = {USDT['USDT']}')        

@router.message(Command('account'))
async def get_partners_info(message: Message, TON):
    num_ref = await rq.retrieve_referrals(message.from_user.id, bot)
    data = await rq.retrieve_partner_info(message.from_user.id, bot, STARS['STARS'], TON['TON'])
    if data:
        balance, total, last_purchases = data
        text = f"Количество рефералов: {num_ref}\nСделано покупок рефералами: {total}\nИстория:\n\n{last_purchases}Доступный баланс в звездах: {balance//STARS['STARS']}\nДоступный баланс в TON: {round(balance/TON['TON'], 6)}"
        await message.answer(text = text, reply_markup = await withdrawKeyboard())
    

  
  
















































