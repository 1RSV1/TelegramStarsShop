from app.database.models import async_session
from app.database.models import Stars, Purchases
from sqlalchemy import select, update




async def check_user(tg_id, tg_username, bot, aff=0): 

    if tg_username == None:
        tg_username = ''
    try:
        async with async_session() as session:
            user = await session.scalar(select(Stars).where(Stars.tg_id == tg_id))
            if not user:
                session.add(Stars(tg_id = tg_id, tg_username = tg_username, aff = aff))
                await session.commit()
            return True
    except Exception as e:
        await bot.send_message(chat_id=8401558948, text= f'ОШИБКА ЗАПИСИ:{e}')
        return False   

async def update_purchase(tg_id, item, value, bot): # обновление данных покупки
    try:
        async with async_session() as session:
            if item.startswith('#'):
                await session.execute(update(Stars).where(Stars.tg_id == tg_id).values(stars=Stars.ton + int(item[1:]), deposits=Stars.deposits + int(value)))
            else:
                isGift = ''
                if int(item) >= 350:
                    isGift = '#'
                await session.execute(update(Stars).where(Stars.tg_id == tg_id).values(stars=Stars.stars + int(item), deposits=Stars.deposits + int(value), gifts=Stars.gifts + isGift))
            await session.commit()
            return True
    except Exception as e:
        await bot.send_message(chat_id=155269575, text=f"Ошибка бд: {e}")
        return False
    


async def check_gift(tg_id): 
    try:
        async with async_session() as session:
            user = await session.scalar(select(Stars).where(Stars.tg_id == tg_id))
            if not user:    
                return False
            if user.gifts[-1] == '#':
                newline = user.gifts[0: -1]
                await session.execute(update(Stars).where(Stars.tg_id == tg_id).values(gifts= newline))
                await session.commit()
                return True 
            else:
                return False
    except:
        return False   


async def create_purchase(tg_id, tg_username, amount, item, TON, USDT, bot): # создание данных покупки  
    try:
        async with async_session() as session:
            user = await session.scalar(select(Stars).where(Stars.tg_id == tg_id))
            affiliate = user.aff
            if item.startswith('#'):
                ton = int(item[1:])
                net = round(amount * 0.92 - TON['TON'] * ton, 2)
                share = net // 2
                session.add(Purchases(tg_id = tg_id, tg_username = tg_username, amount = amount, ton = ton, net = net, share = share, affiliate = affiliate))
            else:
                stars = int(item)
                net = round(amount * 0.92 - stars * 0.015 * USDT['USDT'], 2)
                share = net // 2
                session.add(Purchases(tg_id = tg_id, tg_username = tg_username, amount = amount, stars = stars, net = net, share = share, affiliate = affiliate))
            if affiliate:
                await session.execute(update(Stars).where(Stars.tg_id == affiliate).values(balance= Stars.balance + share)) # по количеству обновленных строк можно понять прошла ли запись

            await session.commit()
            return True
    except Exception as e:
        await bot.send_message(chat_id=155269575, text=f"Ошибка записи покупки бд: {e}")
        return False

async def retrieve_partner_info(tg_id, bot, stars, TON):
    try:
        async with async_session() as session:
            user = await session.scalar(select(Stars).where(Stars.tg_id == tg_id))
            purchases = (await session.scalars(select(Purchases).where(Purchases.affiliate == tg_id))).all()
            balance = user.balance
            last_purchases = 'Покупок пока что не было\n\n'
            total = len(purchases)
            if purchases:
                last_purchases = ''
                for p in purchases[-5:]:
                    star = p.share // stars
                    ton = round(p.share / TON, 6)
                    if p.stars:
                        last_purchases += f' -{p.stars} звезд -- Комиссия:{star} -- Дата: {p.createdAt.strftime("%d.%m.%Y")}\n\n'
                    else:
                        last_purchases += f' -{p.ton} TON -- Комиссия:{ton} -- Дата: {p.createdAt.strftime("%d.%m.%Y")}\n\n'
            return balance, total, last_purchases        
    except Exception as e:
        await bot.send_message(chat_id=8401558948, text=f"Ошибка извлечения инфы о партнере: {e}")
        return False

async def retrieve_referrals(tg_id, bot):
    try:
        async with async_session() as session:
            referrals = (await session.scalars(select(Stars).where(Stars.aff == tg_id))).all()
            return len(referrals)    
    except Exception as e:
        await bot.send_message(chat_id=8401558948, text=f"Ошибка извлечения количества рефералов: {e}")
        return 0        

async def retrieve_all_users():
    async with async_session() as session:
        listt = []
        users_object = await session.execute(select(Purchases.tg_id, Purchases.tg_username))
        for tupl in users_object:
          dict = {'tg_id': tupl[0], 'tg_username': tupl[1]}
          listt.append(dict)
        return listt            




