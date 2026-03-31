import logging
import sys
import requests
import json
import asyncio
import base64
import math
import httpx

from aiohttp import web
from app.keyboards import Back, Cancelled, giftsKeyboard
from aiogram import Bot, Dispatcher
from aiogram.types import  BufferedInputFile
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from app.handlers import bot, router, transactionDict, isFragmentAvailable, WALLET, MerchantId, Secret, lock, wallet_cache, admin
from app.database.models import async_main, async_shut_main
from playwright.async_api import async_playwright
from pytoniq import WalletV5R1, LiteBalancer
from pytoniq_core import Cell
from aiogram.enums import ParseMode
import app.database.requests as rq

lock2 = asyncio.Lock()
lock3 = asyncio.Lock()
lock5 = asyncio.Lock()

queue = asyncio.Queue(maxsize=1000)

async def edit_message_after_purchase(arr, arg):
    try:
        if arg == 'wallet':
            wallet = wallet_cache.get(str(arr[0]))
            await bot.edit_message_text(chat_id=arr[0], text=f'✅Вы приобрели {arr[2][1:]} TON на кошелек {wallet}. Перевод будет зачислен в течение 5 минут.\n\nПоддержка: @gift_supplier', message_id = arr[3], reply_markup= await giftsKeyboard(str(arr[2])))
        elif arg == 'ton':
            await bot.edit_message_text(chat_id=arr[0], text=f'✅Вы приобрели {arr[2][1:]} TON для {arr[1]}. Перевод будет зачислен в течение 5 минут.\n\nПоддержка: @gift_supplier', message_id = arr[3], reply_markup= await giftsKeyboard(str(arr[2])))
        else:
            await bot.edit_message_text(chat_id=arr[0], text=f'✅Вы приобрели {arr[2]} звезд для {arr[1]}. Звезды будут начислены в течение 5 минут.\n\nПоддержка: @gift_supplier', message_id = arr[3], reply_markup= await giftsKeyboard(str(arr[2])))
    except Exception as e:
        await bot.send_message(chat_id=admin, text=f'Ошибка редактирования сообщения после покупки: {e}')


async def worker():
    while True:
        data = await queue.get()
        bot = data[0]
        try:
            if not await process_data(data[0], data[1], data[2], data[3], data[4]):
                await bot.send_message(chat_id=admin, text=f'result = False, ДОБАВЛЕНО В КОНЕЦ ОЧЕРЕДИ')
                await queue.put(data)     
        except Exception as e:
            await bot.send_message(chat_id=admin, text=f'Ошибка выполения задания в очереди, НЕ ДОБАВЛЕНО В КОНЕЦ ОЧЕРЕДИ: {e}')
        finally:
            queue.task_done()

async def process_data(bot, page2, data, config, arr):
    rub = data.get("amount")
    if arr[2].startswith('#'):
        quantity = arr[2][1:]
    else:
        quantity = arr[2]
    if not await rq.update_purchase(arr[0], int(quantity), rub, bot):
        await bot.send_message(chat_id=admin, text=f'ОШИБКА ЗАПИСИ В БД от {arr[0]} для {arr[1]}  {arr[2]} звезд {data.get("amount")}')    
    await rq.create_purchase(arr[0], arr[1], rub, arr[2], TON, bot)
    if arr[2].startswith('#'):
        if arr[1] == 'wallet':
            wallet = wallet_cache.get(str(arr[0]))
            if wallet:
                await edit_message_after_purchase(arr, 'wallet')
                b64_payload = "te6ccgEBAQEAAgAAAA=="
                nanoTon = int(arr[2][1:])* 10**9
                result = False
                attempts = 0
                while not result and attempts < 3:
                    result = await send_transaction(wallet, b64_payload, nanoTon, arr[0], arr[2], config)
                    attempts += 1
            else:
                await bot.send_message(chat_id=admin, text=f'КОШЕЛЕК НЕ НАЙДЕН от {arr[0]} для {arr[1]}  {arr[2]} ton за {data.get("amount")}')            
                result = False
        else:
            await edit_message_after_purchase(arr, 'ton')
            result = await my_recursive_function(arr[1], arr[2], page2, config)

    else:
        await edit_message_after_purchase(arr, 'stars')
        await bot.send_message(chat_id=admin, text=f'отправка {arr[0]} {arr[1]} {arr[2]} звезд {data.get("amount")}') 
        if not data.get('id') == 'test':
            result = await my_recursive_function(arr[1], arr[2], page2, config)
    if not result:
        await bot.send_message(chat_id=admin, text=f'НЕ ОТПРАВИЛОСЬ от {arr[0]} для {arr[1]}  {arr[2]} звезд {data.get("amount")}, добавлено в конец очереди')  
    return result              

WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = 3000
WEBHOOK_PATH = "/bot"
WEBHOOK_SECRET = "my-secret"
BASE_WEBHOOK_URL = "https://fff.engbot.ru"
TON = {'TON': 130}

async def getConf():
    # Используем асинхронный контекст для загрузки конфига
    async with httpx.AsyncClient() as http_client:
        try:
            resp = await http_client.get('https://ton.org/global.config.json')
            return resp.json()
        except Exception as e:
            print(f'ошибка загрузки конфига {e}')
            return None



# функция отправки транзакции
async def send_transaction(dest_addr, b64_payload, amount_ton, username, amount, config):
    MNEMONIC1 = WALLET.split() # Ваша сид-фраза (24 слова
    try:
        client = LiteBalancer.from_config(config)
        await client.start_up()     
    except Exception as e:
        await bot.send_message(chat_id=admin, text=f'Ошибка сети/конфига для {username}: {e}')
        return False
    try:
        ans = False
        wallet = await WalletV5R1.from_mnemonic(client, MNEMONIC1, network_global_id= -239)
        old_seqno = await wallet.get_seqno()
        payload_bytes = base64.urlsafe_b64decode(b64_payload + '=='[:len(b64_payload) % 4])
        body_cell = Cell.one_from_boc(payload_bytes)
        current_balance = await wallet.get_balance()
        if current_balance < int(amount_ton) + 50000000: 
            await bot.send_message(chat_id=admin, text= 'НЕДОСТАТОЧНЫЙ БАЛАНС')
            await client.close()
            return False 
        await wallet.transfer(
            destination=dest_addr,
            amount=int(amount_ton), #нанотоны
            body=body_cell
        )
        for _ in range(7):
            await asyncio.sleep(3)
            try:
                current_seqno = await wallet.get_seqno()
                if current_seqno > old_seqno:
                    await bot.send_message(chat_id=admin, text= f'транзакция в сети {amount} звезд для {username}')
                    ans = True
                    break
            except Exception as e:
                await bot.send_message(chat_id=admin, text= f'SEQNO {amount} звезд для {username} {str(e)}')
                continue
            
        if not ans:
            ans = True
            await bot.send_message(chat_id=admin, text= f'транзакция не прошла проверку но скорее всего все ок, ПРОВЕРЬ {amount} звезд для {username}')
        
    except Exception as e:
            await bot.send_message(chat_id=admin, text= f'не удалось отправить транзакцию в сеть при отправке {amount} звезд для {username} {str(e)}')
            ans = False
    finally:
        await client.close_all()
    return ans

async def takeScreen(page, caption):
    try:
        screenshot_bytes = await page.screenshot()
        photo = BufferedInputFile(screenshot_bytes, filename="payment.png")
        await bot.send_photo(chat_id=admin, photo=photo, caption = caption)
    except Exception as e:
        await bot.send_message(chat_id=admin, text= f'не удалось сделать скрин: {str(e)}')
        

async def reloadPage(page, caption, address): 
    await takeScreen(page, caption)
    try:
        response = await page.goto(address, wait_until="commit")
        error = 0
        while not response.ok and error < 5:
            await takeScreen(page, 'error500')
            response = await page.goto(address, wait_until="commit")
            error +=1
        if response.ok:
            await takeScreen(page, 'successupdated')
            return True
    except:     
        return False


         
async def fillOutStars(username, amount, page2, attempts=0):
    if attempts == 3:
        return False
    try:    
        btn = await page2.query_selector(".js-more-stars-btn")
        ton = await page2.query_selector(".js-more-funds-btn")
        if btn:
            await btn.click()
            print("Кнопка найдена и нажата")
            await asyncio.sleep(1)
            await page2.get_by_text("Buy Stars Package", exact=True).click()
            await asyncio.sleep(1)
        elif ton:
            await ton.click()
            await asyncio.sleep(1)
            if not await reloadPage(page2, 'switchpage', 'https://fragment.com/stars/buy'):
                attempts += 1
                return await fillOutStars(username, amount, attempts)
        else:
            if not page2.url.endswith('stars/buy'):
                if not await reloadPage(page2, 'changepage', 'https://fragment.com/stars/buy'):
                    attempts += 1
                    return await fillOutStars(username, amount, attempts)
        username_input =  page2.get_by_placeholder("Enter Telegram username...")
        await username_input.wait_for(state="visible", timeout=7000)
        await username_input.fill(username)
        await page2.click(".icon-options-more")
        await page2.get_by_text(f"{int(amount)} Stars", exact=True).click()
        await username_input.press("Enter")
        await page2.wait_for_function(
            """(selector) => {
                const el = document.querySelector(selector);
                return el.classList.contains('found') || el.classList.contains('error');
            }""",
            arg=".js-stars-search-field"
        )
        field = page2.locator(".js-stars-search-field")
        classes = await field.evaluate("el => el.className")
        if "found" in classes: 
            pass
        elif "error" in classes:
            await bot.send_message(chat_id=admin, text= f'ошибка юзернейм при отправке {amount} звезд для {username}') 
            return False
        await page2.click(".js-stars-buy-btn")
        await asyncio.sleep(1)
        await page2.click(".tm-checkbox-label")
        return True
    except Exception as e:
        await page2.goto(f"https://fragment.com/stars/buy", wait_until="commit")
        attempts += 1
        return await fillOutStars(username, amount, attempts)

async def fillOutTon(username, amount, page2, attempts=0):
    if attempts == 3:
        return False
    try:    
        btn = await page2.query_selector(".js-more-stars-btn")
        ton = await page2.query_selector(".js-more-funds-btn")
        if btn:
            if not await reloadPage(page2, 'switchpage', 'https://fragment.com/ads/topup'):
                attempts += 1
                return await fillOutTon(username, amount, attempts)
        elif ton:
            await ton.click()
            await asyncio.sleep(1)
        else:
            if not page2.url.endswith('ads/topup'):
                if not await reloadPage(page2, 'changepage', 'https://fragment.com/ads/topup'):
                    attempts += 1
                    return await fillOutTon(username, amount, attempts)
        username_input =  page2.get_by_placeholder("Enter Telegram username...")
        await username_input.wait_for(state="visible", timeout=7000)
        await username_input.fill(username)
        await username_input.press("Enter")
        ton_input = page2.get_by_placeholder("Enter any amount in TON")
        await ton_input.fill(str(amount)) 
        await ton_input.press("Enter")
        await page2.wait_for_function(
            """(selector) => {
                const el = document.querySelector(selector);
                return el.classList.contains('found') || el.classList.contains('error');
            }""",
            arg=".js-ads-topup-search-field"
        )
        field = page2.locator(".js-ads-topup-search-field")
        classes = await field.evaluate("el => el.className")
        if "found" in classes: 
            pass
        elif "error" in classes:
            await bot.send_message(chat_id=admin, text= f'ошибка юзернейм при отправке {amount} звезд для {username}') 
            return False
        await page2.click(".js-ads-topup-btn")
        await asyncio.sleep(1)
        await page2.click(".tm-checkbox-label")
        return True
    except Exception as e:
        await page2.goto(f"https://fragment.com/ads/topup", wait_until="commit")
        attempts += 1
        return await fillOutTon(username, amount, attempts)

async def my_recursive_function(username, amount, page2, config):
    async with lock2:
        async with lock3:
            return await send_stars(username, amount, page2, config, attempts=0)        
        
async def send_stars(username, amount, page2, config, attempts):
    catched = [False]
    async def handle_response(response):
        try:
            if "fragment.com/api?" in response.url:
                data = await response.json()
                if data.get("ok") and data.get("transaction"):
                    if catched[0]:
                        if not found_target.done():
                            found_target.set_result(False)
                        return
                    catched[0] = True
                    tx = data["transaction"]["messages"]
                    result = await send_transaction(tx[0]["address"], tx[0]["payload"], tx[0]["amount"], username, amount, config)
                    if result:
                        if not found_target.done():
                            found_target.set_result(True)
                    else:
                        found_target.set_result(False)          
                elif data.get("error") :
                    await bot.send_message(chat_id=admin, text= f"Ошибка API Fragment: {data.get('error')}")
                    if not catched[0]:
                        catched[0] = True
                        found_target.set_result(False)
        except Exception as e:
            await bot.send_message(chat_id=admin, text=f"Не удалось перехватить ответ handle_response: {e}")
    try: 
        await takeScreen(page2, 'start')
        if amount.startswith('#'):
            filled = await fillOutTon(username, int(amount[1:]), page2)
        else:
            filled = await fillOutStars(username, int(amount), page2)
        if not filled:
            return False
        
        found_target = asyncio.Future()
        page2.on("response", handle_response)          
        await asyncio.sleep(1)
        if not amount.startswith('#'):
            await page2.click(".js-buy-stars-button")
        else:    
            await page2.click(".js-add-funds-button")
        try:
            result = await asyncio.wait_for(found_target, timeout=45.0)
            await takeScreen(page2, 'waiting')
            if result: # успешная оплата
                await takeScreen(page2, 'successfullpayment')         
                page2.remove_listener("response", handle_response)
                return True
            else:
                page2.remove_listener("response", handle_response)
                if attempts < 3:
                    reloaded = await reloadPage(page2, 'failurepayment', 'https://fragment.com/stars/buy')
                    if reloaded:
                        attempts +=1
                        return await send_stars(username, amount, page2, config, attempts)
                    else:
                        await bot.send_message(chat_id=admin, text= f'страница не обновлена, транзакция не отправлена')
                else:
                    await bot.send_message(chat_id=admin, text= f'3 попытки закончились')
                    return False

        except asyncio.TimeoutError:
            page2.remove_listener("response", handle_response)
            if attempts < 3:
                reloaded = await reloadPage(page2, 'asyncio timeout', 'https://fragment.com/stars/buy')
                if reloaded:
                    attempts +=1
                    return await send_stars(username, amount, page2, config, attempts)
                else:
                    await bot.send_message(chat_id=admin, text= f'страница не обновлена, транзакция не отправлена')
            else:
                    await bot.send_message(chat_id=admin, text= f'3 попытки закончились')
                    return False
    
    except Exception as e:
            er = 'as e  page ' + str(e)
            try:
                page2.remove_listener("response", handle_response)
            except:
                await bot.send_message(chat_id=admin, text= f'слушатель не убран')

            if attempts < 3:
                reloaded = await reloadPage(page2, er, 'https://fragment.com/stars/buy')
                if reloaded:
                    attempts +=1
                    return await send_stars(username, amount, page2, config, attempts)
                else:
                    await bot.send_message(chat_id=admin, text= f'страница не обновлена, транзакция не отправлена')
            else:
                    await bot.send_message(chat_id=admin, text= f'3 попытки закончились') 
                    return False 

async def checkHeaders(Merchant, S):
    if Merchant != MerchantId or S != Secret:
        return False
    return True 

async def handle_post_request(request: web.Request):
    S = request.headers.get('X-Secret')
    M = request.headers.get('X-MerchantId')
    if not await checkHeaders(M, S):
        await bot.send_message(chat_id=admin, text=f'попытка взлома headers {data.get("id")} {data.get("amount")}')
        return web.json_response({"ok": False})
    bot = request.app['bot']
    page2 = request.app['page2']
    data = await request.json()
    config = request.app['config']
    if data.get('status') == 'PENDING':
        await bot.send_message(chat_id=admin, text=f'PENDING {data.get("id")} {data.get("amount")}')
    elif data.get('status') == 'CANCELED':
        await bot.send_message(chat_id=admin, text=f'CANCELED {data.get("id")} {data.get("amount")}') 
        arr = transactionDict.get(data.get('id'))
        if arr:
            if len(arr) == 5:
                try:
                    await bot.edit_message_text(chat_id=arr[0], text=arr[4], message_id = arr[3], parse_mode= ParseMode.HTML, reply_markup= await Cancelled())
                except:
                    pass
            transactionDict.pop(data.get('id'))    
    elif data.get('status') == 'CONFIRMED':
        await bot.send_message(chat_id=admin, text=f'CONFIRMED {data.get("id")} {data.get("payload")}')
        arr = transactionDict.get(data.get('id'))
        if arr:
            transactionDict.pop(data.get('id'))
            await queue.put([bot, page2, data, config, arr])
        else:
            await bot.send_message(chat_id=admin, text=f'нет информации о платеже {data.get('id')} НЕ ОТПРАВЛЕНО')

    elif data.get('status') == 'CHARGEBACKED':
        await bot.send_message(chat_id=admin, text=f'CHARGEBACKED {data.get("id")} {data.get("amount")}')
    return web.json_response({"ok": True})





async def get_pages():
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",                                   
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",                        
            "--disable-web-security",                        
            "--disable-features=IsolateOrigins,site-per-process",
        ])
    browser2 = await p.chromium.launch(headless=True,  
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",                                   
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",                        
            "--disable-web-security",                         
            "--disable-features=IsolateOrigins,site-per-process",
        ])
    context = await browser.new_context(
        storage_state="fragment_auth.json",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    context2 = await browser2.new_context(
        storage_state="fragment_auth2.json",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )        
    page = await context.new_page()
    page2 = await context2.new_page()
    page3 = await context.new_page()
    try:
        await page.goto(f"https://fragment.com/stars/buy", wait_until="commit")
        await page2.goto(f"https://fragment.com/stars/buy", wait_until="commit")
        await page3.goto(f"https://crypto.ru/ton-rub", wait_until="commit")
    except Exception as e:
        isFragmentAvailable['ok'] = False
        await bot.send_message(chat_id=8401558948, text=f'ошибка перехода на фрагмент или коинмаркеткап при запуске бота {e}')
        
    return page, page2, page3, browser, browser2, p

async def my_recursive_function2(page):
    async with lock:
        async with lock5:
            return await reloadFragment(page)
        
async def my_recursive_function3(page3):
    async with lock:
        async with lock5:
            return await reloadCrypto(page3)        

async def reloadCrypto(page, attempts = 0):
    global TON
    if attempts == 3:
        return False
    try:    
        await page.goto(f"https://crypto.ru/ton-rub", wait_until="commit")
        price_elm = page.locator('.coin__price-value[data-id="66715"]')
        await price_elm.wait_for(state="visible", timeout=4000)
        await asyncio.sleep(3)
        pricestring = await price_elm.inner_text()
        TON['TON'] = float(pricestring.replace(',', '.').replace('\xa0', '').strip())
        return True

    except Exception as e: 
        attempts += 1
        await bot.send_message(8401558948, text=f'попытка обновить crypto {attempts} {e}')
        await takeScreen(page, 'tonpriceerror')
        return await reloadCrypto(page, attempts)
    
     


async def reloadFragment(page, attempts = 0):
        if attempts == 3:
            return False
        try:    
            await page.goto(f"https://fragment.com/stars/buy", wait_until="commit")
            username_input =  page.get_by_placeholder("Enter Telegram username...")
            await username_input.wait_for(state="visible", timeout=5000) 
            return True
        except Exception as e: 
            attempts += 1
            await bot.send_message(8401558948, text=f'попытка обновить fragment {attempts} {e}')
            await takeScreen(page, 'не обновлен')
            return await reloadFragment(page, attempts)
        
        

async def reloadFragmentTask(page, page3):
    while True:
        try:
            reload = await my_recursive_function2(page)
            if not reload:
                if isFragmentAvailable['ok']:
                    isFragmentAvailable['ok'] = False
                    await bot.send_message(admin, text='фрагмент недоступен, функции оплаты и поиска юзернейм выключены')
            else:
                if not isFragmentAvailable['ok']:
                    isFragmentAvailable['ok'] = True
                    await bot.send_message(admin, text='фрагмент стал доступен, функции оплаты и поиска юзернейм включены')
            if not await my_recursive_function3(page3):
                await bot.send_message(admin, text='курс TON не обновлен')
            await asyncio.sleep(180)        
        except asyncio.CancelledError:
            logging.info("Фоновая задача остановлена")
            break      
        except Exception as e:
            logging.error(f"Ошибка в фоновой задаче: {e}")
            await asyncio.sleep(10)           


async def reloadFragment(page, attempts = 0):
        if attempts == 3:
            return False
        try:    
            await page.goto(f"https://fragment.com/stars/buy", wait_until="commit")
            username_input =  page.get_by_placeholder("Enter Telegram username...")
            await username_input.wait_for(state="visible", timeout=5000) 
            return True
        except Exception as e: 
            attempts += 1
            await bot.send_message(8401558948, text=f'попытка обновить fragment {attempts} {e}')
            await takeScreen(page, 'не обновлен')
            return await reloadFragment(page, attempts)
        

async def on_startup(app: web.Application) -> None:
    config = await getConf()
    page, page2, page3, browser, browser2, p = await get_pages()
    bot: Bot = app['bot']
    await bot.delete_webhook(drop_pending_updates=True)
    dp: Dispatcher = app['dispatcher']
    app['browser'] = browser
    app['browser2'] = browser2
    app['playwright'] = p
    app['config'] = config
    dp['config'] = config
    dp['page'] = page
    dp['page3'] = page3
    dp['TON'] = TON
    dp['transactionDict'] = transactionDict
    dp['isfragmentAvailable'] = isFragmentAvailable
    dp['reloadFragmentTask'] = asyncio.create_task(reloadFragmentTask(page, page3))
    app['worker'] = asyncio.create_task(worker())
    app['page2'] = page2
    await async_main()
    app['http_client'] = httpx.AsyncClient(
        timeout=httpx.Timeout(10.0), 
        headers={"Content-Type": "application/json"}
    )
    await bot.set_webhook(f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}", secret_token=WEBHOOK_SECRET, allowed_updates=["message", "callback_query", "chat_member", "pre_checkout_query"])



async def on_shutdown(app: web.Application) -> None:
    dp: Dispatcher = app['dispatcher']
    task = dp.get('reloadFragmentTask')
    if task:
        task.cancel()
    worker = app.get('worker')  
    if worker:
        worker.cancel()  
    bot: Bot = app['bot']
    await app['http_client'].aclose()
    browser = app.get('browser')
    browser2 = app.get('browser2')
    p = app.get('playwright')
    if browser:
        await browser.close()
    if browser2:
        await browser2.close()    
    if p:
        await p.stop()
    await bot.delete_webhook()
    await async_shut_main()
    await browser.close()
    await p.stop()     

def main() -> None:
    dp = Dispatcher()
    dp.include_router(router)
    app = web.Application()
    app['bot'] = bot
    app['dispatcher'] = dp
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    app.router.add_post("/handleStatus", handle_post_request)
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    main()



























































































