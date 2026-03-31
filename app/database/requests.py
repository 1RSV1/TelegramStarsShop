from app.database.models import async_session
from app.database.models import Stars, Purchases
from sqlalchemy import select, update
from app.handlers import admin, USDT




async def check_user(tg_id, tg_username, aff=0): 

    if tg_username == None:
        tg_username = ''
    try:
        async with async_session() as session:
            user = await session.scalar(select(Stars).where(Stars.tg_id == tg_id))
            if not user:
                session.add(Stars(tg_id = tg_id, tg_username = tg_username, aff = aff))
                await session.commit()
            return True
    except:
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
        await bot.send_message(chat_id=admin, text=f"Ошибка бд: {e}")
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


async def create_purchase(tg_id, tg_username, amount, item, TON, bot): # создание данных покупки  
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
                star = int(amount)
                net = round(amount * 0.92 - star * 0.015 * USDT['USDT'], 2)
                share = net // 2
                session.add(Purchases(tg_id = tg_id, tg_username = tg_username, amount = amount, star = star, net = net, share = share, affiliate = affiliate))
            if affiliate:
                await session.execute(update(Stars).where(Stars.tg_id == affiliate).values(balance= Stars.balance + share)) # по количеству обновленных строк можно понять прошла ли запись

            await session.commit()
            return True
    except Exception as e:
        await bot.send_message(chat_id=admin, text=f"Ошибка записи покупки бд: {e}")
        return False




