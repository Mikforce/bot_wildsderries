import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base

API_TOKEN  = '7078892748:AAG-p8EXzipI6CwdojhAZRGk1jR-r_1ezGs'
DB_URL = "postgresql://user:password@db:5432/dbname"

Base = declarative_base()

class ProductInfo(Base):
    __tablename__ = 'product_info'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    article = Column(String)
    price = Column(Float)
    rating = Column(Float)
    quantity = Column(Integer)

engine = create_engine(DB_URL)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)


bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
loop = asyncio.get_event_loop()

subscriptions = {}  # Словарь для хранения подписок


# async def send_message(article, chat_id):
#     url = f"https://card.wb.ru/cards/v1/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm={article}"
#     response = requests.get(url)
#     data = response.json()
#     product = data['data']['products'][0]
#     message = f"{product['name']}\nАртикул: {product['id']}\nЦена: {product['priceU']}\nРейтинг: {product['rating']}\nКоличество на складах: {product['sizes'][0]['stocks'][0]['qty']}"
#
#     await bot.send_message(chat_id, message, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text="Подписаться", callback_data=f"subscribe_{article}")]
#     ]))
async def send_message(article, chat_id):
    url = f"https://card.wb.ru/cards/v1/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm={article}"
    response = requests.get(url)
    data = response.json()

    product = data['data']['products'][0]

    name = product.get('name', 'Нет информации')
    product_id = product.get('id', 'Нет информации')
    price = product.get('priceU', 'Нет информации')
    rating = product.get('rating', 'Нет информации')

    # Проверяем наличие данных о размерах и количестве на складе
    sizes = product.get('sizes', [])
    qty = 'Нет информации'
    if sizes and sizes[0]['stocks']:
        qty = sizes[0]['stocks'][0].get('qty', 'Нет информации')

    message = f"{name}\nАртикул: {product_id}\nЦена: {price}\nРейтинг: {rating}\nКоличество на складах: {qty}"

    try:
        await bot.send_message(chat_id, message, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подписаться", callback_data=f"subscribe_{article}")]
        ]))

        # Сохранение информации о товаре в базе данных
        session = Session()
        new_product = ProductInfo(title=name, article=product_id, price=price, rating=rating, quantity=qty)
        session.add(new_product)
        session.commit()
        session.close()

    except Exception as e:
        # Обработка ошибок при отправке сообщения или записи в базу данных
        print(f"Ошибка при отправке сообщения и сохранении данных в базе: {e}")


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("Получить информацию по товару"))
    keyboard.add(types.KeyboardButton("Остановить уведомления"))
    keyboard.add(types.KeyboardButton("Получить информацию из БД"))
    await message.answer("Выберите действие:", reply_markup=keyboard)


@dp.message_handler(lambda message: message.text == "Получить информацию по товару")
async def get_product_info(message: types.Message):
    await message.answer("Введите артикул товара с Wildberries:")
    dp.register_message_handler(get_product_article, content_types=types.ContentType.TEXT)


async def get_product_article(message: types.Message):
    article = message.text
    chat_id = message.chat.id
    await send_message(article, chat_id)


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('subscribe_'))
async def subscribe(callback_query: types.CallbackQuery):
    article = callback_query.data.split('_')[1]
    chat_id = callback_query.message.chat.id
    subscriptions[chat_id] = article
    await callback_query.answer("Вы подписались на уведомления. Буду присылать информацию каждые 5 минут.")
    loop.create_task(send_periodic_updates(article, chat_id))


async def send_periodic_updates(article, chat_id):
    while chat_id in subscriptions and subscriptions[chat_id] == article:
        await send_message(article, chat_id)
        await asyncio.sleep(300)  # 5 minutes


@dp.message_handler(lambda message: message.text == "Остановить уведомления")
async def stop_notifications(message: types.Message):
    chat_id = message.chat.id
    if chat_id in subscriptions:
        del subscriptions[chat_id]
        await message.answer("Уведомления остановлены.")
    else:
        await message.answer("У вас нет активных подписок.")


@dp.message_handler(lambda message: message.text == "Получить информацию из БД")
async def get_info_from_db(message: types.Message):
    session = Session()
    products = session.query(ProductInfo).order_by(ProductInfo.id.desc()).limit(5).all()
    info = "\n\n".join([f"Название: {product.title}\nАртикул: {product.article}\nЦена: {product.price}\nРейтинг: {product.rating}\nКоличество: {product.quantity}" for product in products])
    await message.answer("Последние записи из БД:\n\n" + info)


if __name__ == '__main__':
    dp.middleware.setup(LoggingMiddleware())
    loop.run_until_complete(dp.start_polling())