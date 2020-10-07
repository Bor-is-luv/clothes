# -*- coding: utf-8 -*-

import telebot
from flask import request

from models import User, Clothes

from app import db, app

from func import func

from values import values, types

import pyowm

import os

token = os.environ.get('TELEGRAM_TOKEN', '')
bot = telebot.TeleBot(token, threaded=False)

URL = 'https://api.telegram.org/bot' + token + '/'
secret = ''
url = 'https://3b3b95dc.ngrok.io' + secret
# bot.remove_webhook()
# bot.set_webhook(url=url)
states = {'start': 1, 'init': 2, 'query': 3, 'add': 4, 'city': 5, 'del': 6}

markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=False, resize_keyboard=True)
itembtn1 = telebot.types.KeyboardButton('Получить список одежды')
itembtn2 = telebot.types.KeyboardButton('Добавит предмет в гардероб')
itembtn3 = telebot.types.KeyboardButton('Удалить предмет')
itembtn4 = telebot.types.KeyboardButton('Установить город')
itembtn5 = telebot.types.KeyboardButton('Подобрать одежду на сегодня')
markup.row(itembtn1, itembtn2)
markup.row(itembtn3, itembtn4)
markup.row(itembtn5)

owm = pyowm.OWM('370baafacdbb4a1468e5cef4e6c46a5e')


@app.route('/' + secret, methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return 'ok', 200


@bot.message_handler(commands=['start'])
def start(message):
    user = User.query.filter(User.id == message.chat.id).first()
    if user is None:
        user = User(message.chat.id, message.chat.username)
        user.state = states['start']

        try:
            db.session.add(user)
            db.session.commit()
        except:
            db.session.rollback()
            bot.send_message(message.chat.id,
                             'что-то пошло не так')
            return

    bot.send_message(message.chat.id,
                     f'Здравствуйте, {user.username}. Пожалуйста, введите имеющийся у Вас гардероб в'
                     f' формате <Цвет Вид одежды> так, чтобы каждый предмет находился на новой строке')


@bot.message_handler(
    func=lambda message: User.query.filter(User.id == message.chat.id).first().state == states['start'] or
                         User.query.filter(User.id == message.chat.id).first().state == states['add']
)
def init(message):
    user = User.query.filter(User.id == message.chat.id).first()
    text = message.text
    items = text.split('\n')
    for item in items:
        new_item = item.split()

        if len(new_item) != 2:
            bot.send_message(message.chat.id, 'введите, пожалуйста, все вещи в правильном формате')
            user.state = states['add']
            db.session.commit()
            return

        exist = False
        for typ in types:
            if new_item[1] in types[typ]:
                exist = True
                break

        if not exist:
            bot.send_message(message.chat.id, 'такой вещи не бывает')
            user.state = states['add']
            db.session.commit()
            return

        cloth = Clothes.query.filter_by(color=new_item[0]).filter_by(kind=new_item[1]).first()
        if cloth is None:
            clothes = Clothes(new_item[0], new_item[1])
            for typ in types:
                if new_item[1] in types[typ]:
                    clothes.clothes_type = typ
                    clothes.points = values[new_item[1]]
                    break
            try:
                user.clothes.append(clothes)
                user.state = states['init']
                db.session.commit()
            except:
                db.session.rollback()
                bot.send_message(message.chat.id, 'что-то пошло не так')
                return
        else:
            try:
                user.clothes.append(cloth)
                user.state = states['init']
                db.session.commit()
            except:
                db.session.rollback()
                bot.send_message(message.chat.id, 'что-то пошло не так')
                return

    bot.send_message(message.chat.id, 'Вещи успешно добавлены в гардероб', reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Получить список одежды')
def get_clothes(message):
    user = User.query.filter(User.id == message.chat.id).first()
    clothes = user.clothes
    for clothe in clothes:
        bot.send_message(message.chat.id, clothe, reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Добавит предмет в гардероб')
def add_item_invite(message):
    user = User.query.filter(User.id == message.chat.id).first()
    user.state = states['add']
    db.session.commit()
    bot.send_message(message.chat.id,
                     'Пожалуйста, введите имеющийся у Вас гардероб в'
                     ' формате <Цвет Вид одежды> так, чтобы каждый предмет находился на новой строке')


@bot.message_handler(func=lambda message: message.text == 'Установить город')
def city(message):
    user = User.query.filter(User.id == message.chat.id).first()
    user.state = states['city']
    db.session.commit()
    bot.send_message(message.chat.id, 'Пожалуйста, введите город')


@bot.message_handler(func=lambda message: User.query.filter(User.id == message.chat.id).first().state == states['city'])
def add_city(message):
    user = User.query.filter(User.id == message.chat.id).first()
    user.city = message.text
    user.state = states['init']
    db.session.commit()
    bot.send_message(message.chat.id, 'Город успешно добавлен')


@bot.message_handler(func=lambda message: message.text == "Подобрать одежду на сегодня")
def clothes(message):
    user = User.query.filter(User.id == message.chat.id).first()
    if user.city is None:
        bot.send_message(message.chat.id, 'Пожалуйста, установите город, нажав на кнопку'
                                          ' "Установить город"')
        return

    clothes = user.clothes
    weather = owm.weather_at_place(f'{user.city},Russia')
    w = weather.get_weather()
    temperature = w.get_temperature("celsius")["temp"]
    print(temperature)
    detail_status = w.get_detailed_status()
    new_clothes = func(temperature, clothes)
    for item in new_clothes:
        bot.send_message(message.chat.id, f'{item}')


@bot.message_handler(func=lambda message: User.query.filter(User.id == message.chat.id).first().state == states['init']
                                          and message.text=='Удалить предмет')
def delete(message):
    user = User.query.filter(User.id == message.chat.id).first()
    user.state = states['del']
    clothes = user.clothes
    for clothe in clothes:
        bot.send_message(message.chat.id, str(clothe.id) + '. ' + str(clothe), reply_markup=markup)
    bot.send_message(message.chat.id, 'Пожалуйста, введите номера проедметов из списка через пробел'
                                      ' или ввведите -1, чтобы удалить все')
    db.session.commit()


@bot.message_handler(func=lambda message: User.query.filter(User.id == message.chat.id).first().state == states['del'])
def delete_clothes(message):
    user = User.query.filter(User.id == message.chat.id).first()
    if message.text == str(-1):
        user.clothes = []
        user.state = states['init']
        db.session.commit()
        bot.send_message(message.chat.id, 'Успешно удалены все вещи')
        return

    try:
        nums = [int(num) for num in message.text.split()]
    except ValueError:
        user.state = states['init']
        db.session.commit()
        bot.send_message(message.chat.id, 'Неверный ввод')
        return
    clothes = user.clothes
    for num in nums:
        clo = list(filter(lambda cl: cl.id == num, clothes))[0]
        clothes.remove(clo)

    user.state = states['init']
    db.session.commit()
    bot.send_message(message.chat.id, 'Предмет удалён')



