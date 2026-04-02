from aiogram.types import  InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import math



star = 1.40
prices = [50, 100, 150, 250, 350, 500, 750, 1000, 1500, 2500, 5000, 10000]
ton_quantities = [1, 5, 10, 20, 50, 100]
recipients = ['🫵Себе', '👥Другу']
payments = [{'🇷🇺 СБП | 4%': 'sbp'}]
edge_values = {'350': 2,
                   '500': 2,
                   '750': 4,
                   '1000': 12,
                   '1500': 12,
                   '2500': 15,
                   '5000': 15,
                   '10000': 15}
ids = {'bear': '5280598054901145762',
        'heart': '5283228279988309088',
        'present': '5280615440928758599',
        'rose': '5280947338821524402',
        'cake': '5280659198055572187',
        'flowers': '5280774333243873175',
        'rocket': '5283080528818360566',
        'shamp': '5451905784734574339',
        'tree': '5345935030143196497',
        'bear2': '5379850840691476775',
        'heart2': '5224628072619216265',
        'bear3': '5226661632259691727',
        'cup': '5280769763398671636',
        'ring': '5280651583078556009',
        'diamond': '5280922999241859582'}

async def mainKeyboard(): 
    keyboard = InlineKeyboardBuilder()     
    keyboard.add(InlineKeyboardButton(text = 'STARS', icon_custom_emoji_id= '5406812184359507637', callback_data= 'stars')) 
    keyboard.add(InlineKeyboardButton(text = 'TON', icon_custom_emoji_id= '5406976471153545018', callback_data= 'ton'))           
    return keyboard.adjust(2).as_markup()

async def withdrawKeyboard(): 
    keyboard = InlineKeyboardBuilder()     
    keyboard.add(InlineKeyboardButton(text = ' ', icon_custom_emoji_id= '5406812184359507637', callback_data= 'withdraw_stars')) 
    keyboard.add(InlineKeyboardButton(text = ' ', icon_custom_emoji_id= '5406976471153545018', callback_data= 'withdraw_ton'))           
    return keyboard.adjust(2).as_markup()
  
async def tonKeyboard(): 
    keyboard = InlineKeyboardBuilder()
    for ton in ton_quantities:     
        keyboard.add(InlineKeyboardButton(text = str(ton), icon_custom_emoji_id= '5406976471153545018', style= 'primary', callback_data= '#' + str(ton))) 
    keyboard.add(InlineKeyboardButton(text = '🔙Назад', callback_data= 'main'))           
    return keyboard.adjust(2).as_markup()

async def pricesKeyboard(): 
    keyboard = InlineKeyboardBuilder()
    for price in prices:     
        keyboard.add(InlineKeyboardButton(text = f'{str(price)} ({str(math.ceil(price*star))} RUB)', icon_custom_emoji_id= '5406812184359507637', style= 'primary', callback_data= str(price))) 
    keyboard.add(InlineKeyboardButton(text = '🔙Назад', callback_data= 'main'))           
    return keyboard.adjust(2).as_markup() 

async def chooseRecipient(stars):
    keyboard = InlineKeyboardBuilder()
    for recipient in recipients:     
        keyboard.add(InlineKeyboardButton(text = recipient, callback_data= recipient + '_' + stars)) 

    keyboard.add(InlineKeyboardButton(text = '🔙Назад', callback_data= 'main'))           
    return keyboard.adjust(2).as_markup() 

async def chooseDestinationTon(amount):
    keyboard = InlineKeyboardBuilder()    
    keyboard.add(InlineKeyboardButton(text = 'На аккаунт', icon_custom_emoji_id= '5857290546459973028', style= 'primary', callback_data= 'recipients' + '_' + amount))
    keyboard.add(InlineKeyboardButton(text = 'На кошелек', icon_custom_emoji_id= '5406976471153545018', style= 'primary', callback_data= 'wallet' + '_' + amount)) 
    keyboard.add(InlineKeyboardButton(text = '🔙Назад', callback_data= 'main'))           
    return keyboard.adjust(1).as_markup()

async def choosePayment(starsUsername, amount): 
    keyboard = InlineKeyboardBuilder()
    for payment in payments:
        for x,y in payment.items():     
            keyboard.add(InlineKeyboardButton(text = x, callback_data= y + '_' + amount + '_' + starsUsername)) 

    keyboard.add(InlineKeyboardButton(text = '🔙Назад', callback_data= 'recipients' + '_' + amount))           
    return keyboard.adjust(1).as_markup()    

async def Pay(starsUsername, amount, transactionId, url= None, icon = None):
    keyboard = InlineKeyboardBuilder()
    if url:
        keyboard.add(InlineKeyboardButton(text = 'Ссылка на оплату по СБП', url= url, icon_custom_emoji_id= str(icon), style= 'success'))    
    keyboard.add(InlineKeyboardButton(text = '🔙Назад', callback_data= 'payment' + '_' + transactionId + '_'+ amount + '_' + starsUsername))
    return keyboard.adjust(1).as_markup()

async def Back():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text = '🔙Назад', callback_data= 'main'))

    return keyboard.adjust(1).as_markup()  

async def Cancelled():
    keyboard = InlineKeyboardBuilder()
    
    keyboard.add(InlineKeyboardButton(text = 'Ссылка на оплату по СБП', callback_data = 'transition', icon_custom_emoji_id= '5406812184359507637', style= 'danger'))    
    keyboard.add(InlineKeyboardButton(text = '🔙Назад', callback_data= 'main'))
    return keyboard.adjust(1).as_markup()


async def giftsKeyboard(stars):
    keyboard = InlineKeyboardBuilder()
    num = edge_values.get(stars)
    if not num:
        keyboard.add(InlineKeyboardButton(text = '🔙Назад', callback_data= 'stars'))
        return keyboard.adjust(1).as_markup()
    count = 0
    for item in ids:
        if count == num:
            break
        keyboard.add(InlineKeyboardButton(text = ' ', icon_custom_emoji_id= ids[item], style= 'success', callback_data= item))
        count += 1
    return keyboard.adjust(2).as_markup()    




