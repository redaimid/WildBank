import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import json
import os
import time
import datetime
import requests
import threading
import asyncio
import aiohttp
from typing import Dict, Any, Optional

class WildCoinBot:
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.load_config()
        self.load_database()
        
        print(f"Инициализация бота с токеном: {self.config['token'][:10]}...")
        print(f"ID группы: {self.config['id']}")
        
        self.vk_session = vk_api.VkApi(token=self.config['token'])
        self.longpoll = VkBotLongPoll(self.vk_session, self.config['id'])
        self.vk = self.vk_session.get_api()
        
        self.active_requests = {}
        
        # Создаем event loop для асинхронных задач
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Запускаем фоновые задачи
        self.payment_checker_task = None
        self.start_background_tasks()
        
        print("Бот инициализирован!")
    
    def start_background_tasks(self):
        """Запускает фоновые асинхронные задачи"""
        def run_async_tasks():
            asyncio.set_event_loop(self.loop)
            self.payment_checker_task = self.loop.create_task(self.payment_checker())
            self.loop.run_forever()
        
        self.background_thread = threading.Thread(target=run_async_tasks, daemon=True)
        self.background_thread.start()
        print("Фоновые задачи запущены")
    
    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            print("Конфиг загружен")
        else:
            print("Создаю конфиг по умолчанию...")
            self.config = {
                "token": "your_group_token",
                "id": "your_group_id",
                "admin_id": 123456789,
                "reserve_id": 987654321,
                "token_key": "your_secret_token",
                "number": "0000000000000000",
                "bank": "Тинькофф",
                "bay": 1000.0,
                "sell": 950.0,
                "balance": 1000,
                "balance_rub": 50000,
                "owner_id": 376393143,
                "coin_id": "your_coin_id",
                "coin_token": "your_coin_token",
                "api_url": "http://5.129.200.31/"
            }
            self.save_config()
    
    def save_config(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)
        print("Конфиг сохранен")
    
    def load_database(self):
        self.db_files = ['users.json', 'deals.json', 'transactions.json']
        for db_file in self.db_files:
            if not os.path.exists(db_file):
                print(f"Создаю {db_file}...")
                with open(db_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=4)
        
        with open('users.json', 'r', encoding='utf-8') as f:
            self.users = json.load(f)
        
        with open('deals.json', 'r', encoding='utf-8') as f:
            self.deals = json.load(f)
        
        with open('transactions.json', 'r', encoding='utf-8') as f:
            self.transactions = json.load(f)
        
        print("База данных загружена")
    
    def save_database(self, db_name: str):
        if db_name == 'users':
            with open('users.json', 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=4)
        elif db_name == 'deals':
            with open('deals.json', 'w', encoding='utf-8') as f:
                json.dump(self.deals, f, ensure_ascii=False, indent=4)
        elif db_name == 'transactions':
            with open('transactions.json', 'w', encoding='utf-8') as f:
                json.dump(self.transactions, f, ensure_ascii=False, indent=4)
    
    def get_main_keyboard(self):
        keyboard = VkKeyboard(one_time=False)
        keyboard.add_button('Купить', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('Продать', color=VkKeyboardColor.NEGATIVE)
        keyboard.add_line()
        keyboard.add_button('Информация', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('Профиль', color=VkKeyboardColor.SECONDARY)
        return keyboard.get_keyboard()
    
    def get_admin_keyboard(self):
        keyboard = VkKeyboard(one_time=False)
        keyboard.add_button('Изменить курс', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('Изменить баланс', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('Изменить реквизиты', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('Изменить API данные', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('Статистика', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('В главное меню', color=VkKeyboardColor.NEGATIVE)
        return keyboard.get_keyboard()
    
    def get_deal_keyboard(self, deal_id):
        keyboard = VkKeyboard(inline=True)
        keyboard.add_button(f'Подтвердить #{deal_id}', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button(f'Отмена #{deal_id}', color=VkKeyboardColor.NEGATIVE)
        return keyboard.get_keyboard()
    
    def get_process_keyboard(self, deal_id):
        keyboard = VkKeyboard(inline=True)
        keyboard.add_button(f'Обработка #{deal_id}', color=VkKeyboardColor.POSITIVE)
        return keyboard.get_keyboard()
    
    def get_profile_keyboard(self):
        keyboard = VkKeyboard(one_time=False)
        keyboard.add_button('Изменить банк', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('Изменить номер', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('В главное меню', color=VkKeyboardColor.SECONDARY)
        return keyboard.get_keyboard()
    
    def send_message(self, user_id, message, keyboard=None):
        try:
            print(f"Отправка сообщения пользователю {user_id}")
            params = {
                'user_id': user_id,
                'message': message,
                'random_id': 0
            }
            if keyboard:
                params['keyboard'] = keyboard
            result = self.vk.messages.send(**params)
            print(f"Сообщение отправлено успешно")
            return result
        except Exception as e:
            print(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
    
    async def get_balance_async(self):
        """Асинхронное получение баланса"""
        try:
            print("Запрос баланса...")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config['api_url'] + 'balance',
                    json={
                        'user_id': self.config['reserve_id'],
                        'access_token': self.config['coin_token']
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    data = await response.json()
                    print(f"Баланс получен: {data}")
                    return data.get('data', {}).get('balance', 0)
        except Exception as e:
            print(f"Error getting balance: {e}")
            return 0
    
    def get_balance(self):
        """Синхронная обертка для получения баланса"""
        try:
            return asyncio.run_coroutine_threadsafe(self.get_balance_async(), self.loop).result(timeout=10)
        except Exception as e:
            print(f"Ошибка при получении баланса: {e}")
            return 0
    
    async def get_history_async(self, limit=10):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config['api_url'] + 'transactions',
                    json={
                        'user_id': self.config['reserve_id'],
                        'access_token': self.config['coin_token'],
                        'type': 'in',
                        'limit': limit
                    }
                ) as response:
                    data = await response.json()
                    return data.get('data', {}).get('transactions', [])
        except Exception as e:
            print(f"Error getting history: {e}")
            return []
    
    async def send_coins_async(self, recipient_id, amount):
        try:
            print(f"Отправка {amount} коинов пользователю {recipient_id}")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config['api_url'] + 'send',
                    json={
                        'user_id': self.config['reserve_id'],
                        'access_token': self.config['coin_token'],
                        'recipient_id': recipient_id,
                        'amount': float(amount)
                    }
                ) as response:
                    result = await response.json()
                    print(f"Результат отправки: {result}")
                    return result
        except Exception as e:
            print(f"Error sending coins: {e}")
            return {"status": "error", "message": str(e)}
    
    def send_coins(self, recipient_id, amount):
        """Синхронная обертка для отправки коинов"""
        try:
            return asyncio.run_coroutine_threadsafe(self.send_coins_async(recipient_id, amount), self.loop).result(timeout=30)
        except Exception as e:
            print(f"Ошибка при отправке коинов: {e}")
            return {"status": "error", "message": str(e)}
    
    def create_deal(self, user_id, amount, deal_type="buy"):
        deal_number = len(self.deals) + 1
        
        if deal_type == "buy":
            # amount - сумма в рублях
            amount_coins = (amount / self.config['bay']) * 1000
            amount_rub = amount
        else:
            # amount - количество коинов
            amount_coins = amount
            amount_rub = (amount / 1000) * self.config['sell']
        
        deal = {
            'id': deal_number,
            'user_id': user_id,
            'amount_rub': round(amount_rub, 2),
            'amount_coins': round(amount_coins, 2),
            'type': deal_type,
            'status': 'active',
            'created_at': time.time(),
            'expires_at': time.time() + 1800
        }
        
        self.deals[str(deal_number)] = deal
        self.save_database('deals')
        
        print(f"Создана заявка #{deal_number} для пользователя {user_id}")
        
        # Отправляем уведомление админу
        self.notify_admin(deal)
        
        return deal
    
    def notify_admin(self, deal):
        try:
            user_info = self.get_user_info(deal['user_id'])
            
            if deal['type'] == 'buy':
                message = f"НОВАЯ ЗАЯВКА НА ПОКУПКУ #{deal['id']}\n\n"
                message += f"Пользователь: {user_info}\n"
                message += f"Сумма коинов: {deal['amount_coins']:,} WC\n"
                message += f"К оплате: {deal['amount_rub']:,} RUB\n"
                message += f"Реквизиты: {self.config['number']} ({self.config['bank']})\n"
                message += f"Создана: {self.format_time(deal['created_at'])}\n"
                message += f"Истекает: {self.format_time(deal['expires_at'])}\n\n"
                message += f"Статус: Ожидает оплаты"
                
                self.send_message(self.config['admin_id'], message, self.get_deal_keyboard(deal['id']))
                
            else:  # sell
                user_details = self.users.get(str(deal['user_id']), {})
                user_bank = user_details.get('bank', 'Не указан')
                user_number = user_details.get('number', 'Не указан')
                
                message = f"НОВАЯ ЗАЯВКА НА ПРОДАЖУ #{deal['id']}\n\n"
                message += f"Пользователь: {user_info}\n"
                message += f"Продаёт: {deal['amount_coins']:,} WC\n"
                message += f"Получит: {deal['amount_rub']:,} RUB\n"
                message += f"Реквизиты клиента: {user_number} ({user_bank})\n"
                message += f"Создана: {self.format_time(deal['created_at'])}\n"
                message += f"Истекает: {self.format_time(deal['expires_at'])}\n\n"
                message += f"Статус: Ожидает перевода коинов"
                
                self.send_message(self.config['admin_id'], message)
                
            print(f"Уведомление о заявке #{deal['id']} отправлено админу")
        except Exception as e:
            print(f"Ошибка отправки уведомления админу: {e}")
    
    def notify_sell_payment_received(self, deal):
        """Уведомление о получении перевода коинов для продажи"""
        try:
            user_info = self.get_user_info(deal['user_id'])
            user_details = self.users.get(str(deal['user_id']), {})
            user_bank = user_details.get('bank', 'Не указан')
            user_number = user_details.get('number', 'Не указан')
            
            message = f"ПОЛУЧЕН ПЕРЕВОД КОИНОВ #{deal['id']}\n\n"
            message += f"Пользователь: {user_info}\n"
            message += f"Получено коинов: {deal['amount_coins']:,} WC\n"
            message += f"К выплате: {deal['amount_rub']:,} RUB\n"
            message += f"Реквизиты для выплаты: {user_number} ({user_bank})\n\n"
            message += f"Статус: Ожидает выплаты RUB"
            
            self.send_message(self.config['admin_id'], message, self.get_process_keyboard(deal['id']))
            print(f"Уведомление о переводе для заявки #{deal['id']} отправлено админу")
        except Exception as e:
            print(f"Ошибка отправки уведомления о переводе: {e}")
    
    def get_user_info(self, user_id):
        try:
            user = self.vk.users.get(user_ids=user_id)[0]
            return f"{user['first_name']} {user['last_name']} (id{user_id})"
        except Exception as e:
            print(f"Ошибка получения информации о пользователе {user_id}: {e}")
            return f"id{user_id}"
    
    def format_time(self, timestamp):
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime("%H:%M %d.%m.%Y")
    
    def process_payment(self, bank: str, message: str, key: str):
        print(f"Обработка платежа: bank={bank}, message={message}, key={key}")
        
        if key != self.config['token_key']:
            return {"status": "error", "message": "Invalid token"}
        
        import re
        amount_match = re.search(r'(\d+[.,]\d{2})', message)
        if not amount_match:
            return {"status": "error", "message": "Amount not found"}
        
        amount = float(amount_match.group(1).replace(',', '.'))
        print(f"Найдена сумма: {amount}")
        
        for deal_id, deal in self.deals.items():
            if (deal['status'] == 'active' and 
                deal['type'] == 'buy' and
                deal['amount_rub'] == amount and
                time.time() < deal['expires_at']):
                
                print(f"Найдена подходящая заявка #{deal_id}")
                # Переводим коины
                self.complete_buy_deal_sync(deal)
                return {"status": "success", "message": "Payment processed"}
        
        return {"status": "error", "message": "No active deal found"}
    
    def complete_buy_deal_sync(self, deal):
        """Синхронное завершение заявки на покупку"""
        try:
            print(f"Завершение заявки на покупку #{deal['id']}")
            # Переводим коины
            result = self.send_coins(deal['user_id'], deal['amount_coins'])
            
            if result.get('status') == 'success':
                deal['status'] = 'completed'
                deal['completed_at'] = time.time()
                self.save_database('deals')
                
                # Уведомляем пользователя
                self.send_message(deal['user_id'], 
                                f"ЗАЯВКА ВЫПОЛНЕНА! #{deal['id']}\n\n"
                                f"Вам переведено: {deal['amount_coins']:,} WC\n"
                                f"Сумма оплаты: {deal['amount_rub']:,} RUB\n\n"
                                f"Статус: Успешно завершено")
                
                # Уведомляем админа
                self.send_message(self.config['admin_id'], 
                                f"ЗАЯВКА ЗАВЕРШЕНА #{deal['id']}\n\n"
                                f"Переведено коинов: {deal['amount_coins']:,} WC")
            else:
                deal['status'] = 'error'
                deal['error'] = result.get('message', 'Unknown error')
                self.save_database('deals')
                
                self.send_message(deal['user_id'], 
                                f"ОШИБКА В ЗАЯВКЕ #{deal['id']}\n\n"
                                f"Ошибка: {deal['error']}\n\n"
                                f"Обратитесь к администратору")
                
        except Exception as e:
            print(f"Error completing deal: {e}")
    
    async def payment_checker(self):
        """Проверяет переводы для заявок на продажу"""
        while True:
            try:
                print("Проверка платежей для заявок на продажу...")
                history = await self.get_history_async(50)
                for transaction in history:
                    tx_id = transaction.get('id')
                    amount = transaction.get('amount', 0)
                    
                    # Ищем заявку на продажу с такой суммой
                    for deal_id, deal in self.deals.items():
                        if (deal['type'] == 'sell' and 
                            deal['status'] == 'active' and
                            deal['amount_coins'] == amount and
                            not deal.get('tx_checked')):
                            
                            print(f"Найден перевод для заявки на продажу #{deal_id}")
                            # Помечаем как проверенную
                            deal['tx_checked'] = True
                            deal['tx_id'] = tx_id
                            self.save_database('deals')
                            
                            # Уведомляем админа
                            self.notify_sell_payment_received(deal)
                            
                            # Уведомляем пользователя
                            self.send_message(deal['user_id'],
                                            f"ПЕРЕВОД ПОЛУЧЕН! #{deal['id']}\n\n"
                                            f"Получено коинов: {deal['amount_coins']:,} WC\n"
                                            f"К выплате: {deal['amount_rub']:,} RUB\n\n"
                                            f"Статус: Ожидает выплаты RUB")
                            break
                
                await asyncio.sleep(60)
                        
            except Exception as e:
                print(f"Error checking payments: {e}")
                await asyncio.sleep(60)
    
    def process_sell_deal(self, deal_id):
        """Обработка заявки на продажу после нажатия кнопки"""
        deal = self.deals.get(str(deal_id))
        if not deal:
            return
        
        try:
            print(f"Обработка заявки на продажу #{deal_id}")
            
            # Здесь должна быть логика перевода RUB пользователю
            
            deal['status'] = 'completed'
            deal['completed_at'] = time.time()
            deal['processed'] = True
            self.save_database('deals')
            
            user_details = self.users.get(str(deal['user_id']), {})
            user_bank = user_details.get('bank', 'Не указан')
            user_number = user_details.get('number', 'Не указан')
            
            # Уведомляем пользователя
            self.send_message(deal['user_id'],
                            f"ВЫПЛАТА ВЫПОЛНЕНА! #{deal['id']}\n\n"
                            f"Вам переведено: {deal['amount_rub']:,} RUB\n"
                            f"На реквизиты: {user_bank} {user_number}\n\n"
                            f"Продано коинов: {deal['amount_coins']:,} WC\n\n"
                            f"Статус: Успешно завершено")
            
            # Уведомляем админа
            self.send_message(self.config['admin_id'],
                            f"ВЫПЛАТА ВЫПОЛНЕНА #{deal['id']}\n\n"
                            f"Переведено RUB: {deal['amount_rub']:,}\n"
                            f"Получено коинов: {deal['amount_coins']:,} WC")
                                
        except Exception as e:
            print(f"Error processing sell deal: {e}")
    
    def handle_buy(self, user_id):
        print(f"Пользователь {user_id} нажал 'Купить'")
        self.show_buy_info(user_id)
    
    def show_buy_info(self, user_id):
        try:
            balance = self.get_balance()
            bay_rate = self.config['bay']
            
            message = f"Wild Shop(mini) - Покупка\n\n"
            message += f"Доступно коинов: {balance:,} WC\n"
            message += f"Курс покупки: {bay_rate:,} RUB за 1000 WC\n\n"
            message += f"Введите сумму покупки:\n"
            message += f"Пример: 100р (за {100/bay_rate*1000:,.0f} WC)\n"
            message += f"Или: 100к (за {100000/bay_rate*1000:,.0f} WC)\n\n"
            message += f"Форматы: 100р, 100к, 100000"
            
            self.send_message(user_id, message)
            self.users[str(user_id)]['waiting_for'] = 'buy_amount'
            self.save_database('users')
        except Exception as e:
            print(f"Ошибка в show_buy_info: {e}")
            self.send_message(user_id, "Ошибка получения баланса")
    
    def handle_sell(self, user_id):
        print(f"Пользователь {user_id} нажал 'Продать'")
        self.show_sell_info(user_id)
    
    def show_sell_info(self, user_id):
        try:
            sell_rate = self.config['sell']
            
            message = f"Wild Shop(mini) - Продажа\n\n"
            message += f"Курс продажи: {sell_rate:,} RUB за 1000 WC\n\n"
            message += f"Введите количество коинов для продажи:\n"
            message += f"Пример: 1000 (получите {sell_rate:,} RUB)\n"
            message += f"Или: 10к (получите {sell_rate * 10:,} RUB)\n"
            message += f"Или: 1кк (получите {sell_rate * 1000:,} RUB)\n\n"
            message += f"Форматы: 1000, 10к, 1кк"
            
            self.send_message(user_id, message)
            self.users[str(user_id)]['waiting_for'] = 'sell_amount'
            self.save_database('users')
        except Exception as e:
            print(f"Ошибка в show_sell_info: {e}")
            self.send_message(user_id, "Ошибка")
    
    def handle_buy_amount(self, user_id, amount_text):
        # Проверяем, не является ли сообщение кнопкой
        if any(keyword in amount_text for keyword in ['Купить', 'Продать', 'Информация', 'Профиль', 'Отмена', 'Подтвердить']):
            print(f"Игнорируем кнопку: {amount_text}")
            self.send_message(user_id, "Пожалуйста, введите сумму, а не используйте кнопки", self.get_main_keyboard())
            return
            
        try:
            print(f"Обработка суммы покупки от {user_id}: {amount_text}")
            
            # Обработка разных форматов ввода
            if amount_text.endswith('р'):
                # Рубли
                amount = float(amount_text[:-1].strip())
                deal_type = "buy"
            elif amount_text.endswith('к'):
                # Коины (тысячи)
                amount = float(amount_text[:-1].strip()) * 1000
                deal_type = "buy"
            elif amount_text.endswith('кк'):
                # Коины (миллионы)
                amount = float(amount_text[:-2].strip()) * 1000000
                deal_type = "buy"
            else:
                # Число без суффикса - считаем рублями
                amount = float(amount_text)
                deal_type = "buy"
            
            if amount <= 0:
                self.send_message(user_id, "Сумма должна быть больше 0", self.get_main_keyboard())
                return
            
            deal = self.create_deal(user_id, amount, deal_type)
            
            message = f"ЗАЯВКА СОЗДАНА #{deal['id']}\n\n"
            message += f"Сумма покупки: {deal['amount_coins']:,} WC\n"
            message += f"К оплате: {deal['amount_rub']:,} RUB\n\n"
            message += f"Данные для перевода:\n"
            message += f"{self.config['number']}\n"
            message += f"Банк: {self.config['bank']}\n\n"
            message += f"Актуально до: {self.format_time(deal['expires_at'])}\n\n"
            message += f"После оплаты коины будут переведены автоматически"
            
            self.send_message(user_id, message, self.get_main_keyboard())
            
            self.users[str(user_id)]['waiting_for'] = None
            self.save_database('users')
            
        except ValueError as e:
            print(f"Ошибка обработки суммы: {e}")
            self.send_message(user_id, "Неверный формат суммы. Пример: 100р, 100к, 100000", self.get_main_keyboard())
    
    def handle_sell_amount(self, user_id, amount_text):
        # Проверяем, не является ли сообщение кнопкой
        if any(keyword in amount_text for keyword in ['Купить', 'Продать', 'Информация', 'Профиль', 'Отмена', 'Подтвердить']):
            print(f"Игнорируем кнопку: {amount_text}")
            self.send_message(user_id, "Пожалуйста, введите сумму, а не используйте кнопки", self.get_main_keyboard())
            return
            
        try:
            print(f"Обработка суммы продажи от {user_id}: {amount_text}")
            
            # Обработка разных форматов ввода для продажи
            if amount_text.endswith('к'):
                amount_coins = float(amount_text[:-1].strip()) * 1000
            elif amount_text.endswith('кк'):
                amount_coins = float(amount_text[:-2].strip()) * 1000000
            else:
                amount_coins = float(amount_text)
            
            if amount_coins <= 0:
                self.send_message(user_id, "Сумма должна быть больше 0", self.get_main_keyboard())
                return
            
            user_details = self.users.get(str(user_id), {})
            user_bank = user_details.get('bank', 'Не указан')
            user_number = user_details.get('number', 'Не указан')
            
            if user_bank == 'Не указан' or user_number == 'Не указан':
                self.send_message(user_id, 
                                "Укажите ваши реквизиты в разделе 'Профиль' перед продажей", 
                                self.get_main_keyboard())
                return
            
            deal = self.create_deal(user_id, amount_coins, "sell")
            
            message = f"ЗАЯВКА СОЗДАНА #{deal['id']}\n\n"
            message += f"Продаёте: {deal['amount_coins']:,} WC\n"
            message += f"Получите: {deal['amount_rub']:,} RUB\n\n"
            message += f"Ваши реквизиты:\n"
            message += f"{user_number}\n"
            message += f"Банк: {user_bank}\n\n"
            message += f"Переведите коины на:\n"
            message += f"vk.com/id{self.config['reserve_id']}\n\n"
            message += f"Актуально до: {self.format_time(deal['expires_at'])}\n\n"
            message += f"После перевода коинов средства будут зачислены в течение 5 минут"
            
            self.send_message(user_id, message, self.get_main_keyboard())
            
            self.users[str(user_id)]['waiting_for'] = None
            self.save_database('users')
            
        except ValueError as e:
            print(f"Ошибка обработки суммы продажи: {e}")
            self.send_message(user_id, "Неверный формат суммы. Пример: 1000, 10к, 1кк", self.get_main_keyboard())
    
    def handle_profile(self, user_id):
        print(f"Пользователь {user_id} запросил профиль")
        user_data = self.users.get(str(user_id), {})
        bank = user_data.get('bank', 'Не указан')
        number = user_data.get('number', 'Не указан')
        
        message = f"ВАШ ПРОФИЛЬ\n\n"
        message += f"Банк: {bank}\n"
        message += f"Номер счета: {number}\n\n"
        message += f"Используйте кнопки ниже для изменения реквизитов:"
        
        self.send_message(user_id, message, self.get_profile_keyboard())
        self.users[str(user_id)]['waiting_for'] = 'profile_menu'
        self.save_database('users')
    
    def handle_admin_command(self, user_id):
        print(f"Пользователь {user_id} запросил админку")
        if user_id != self.config['admin_id']:
            self.send_message(user_id, "У вас нет прав администратора")
            return
        
        try:
            balance = self.get_balance()
        except:
            balance = "Ошибка"
        
        message = f"АДМИН-ПАНЕЛЬ\n\n"
        message += f"Баланс коинов: {balance:,} WC\n"
        message += f"Баланс RUB: {self.config['balance_rub']:,}\n"
        message += f"Курс покупки: {self.config['bay']:,} RUB/1000 WC\n"
        message += f"Курс продажи: {self.config['sell']:,} RUB/1000 WC\n"
        message += f"Банк: {self.config['bank']}\n"
        message += f"Номер: {self.config['number']}\n"
        message += f"Reserve ID: {self.config['reserve_id']}\n"
        message += f"Coin Token: {self.config['coin_token'][:10]}..."
        
        self.send_message(user_id, message, self.get_admin_keyboard())
        self.users[str(user_id)]['waiting_for'] = 'admin_menu'
        self.save_database('users')
    
    def handle_admin_settings(self, user_id, command):
        print(f"Админ {user_id} выбрал: {command}")
        
        if command == 'Изменить курс':
            message = f"ИЗМЕНЕНИЕ КУРСА\n\n"
            message += f"1. Курс покупки (bay) - текущий: {self.config['bay']:,} RUB/1000 WC\n"
            message += f"2. Курс продажи (sell) - текущий: {self.config['sell']:,} RUB/1000 WC\n\n"
            message += f"Введите номер и значение:\n"
            message += f"Пример: 1 1050"
            
            self.send_message(user_id, message)
            self.users[str(user_id)]['waiting_for'] = 'admin_change_rate'
        
        elif command == 'Изменить баланс':
            message = f"ИЗМЕНЕНИЕ БАЛАНСА\n\n"
            message += f"1. Баланс RUB - текущий: {self.config['balance_rub']:,}\n\n"
            message += f"Введите номер и значение:\n"
            message += f"Пример: 1 50000"
            
            self.send_message(user_id, message)
            self.users[str(user_id)]['waiting_for'] = 'admin_change_balance'
        
        elif command == 'Изменить реквизиты':
            message = f"ИЗМЕНЕНИЕ РЕКВИЗИТОВ\n\n"
            message += f"1. Банк - текущий: {self.config['bank']}\n"
            message += f"2. Номер счета - текущий: {self.config['number']}\n\n"
            message += f"Введите номер и значение:"
            
            self.send_message(user_id, message)
            self.users[str(user_id)]['waiting_for'] = 'admin_change_details'
        
        elif command == 'Изменить API данные':
            message = f"ИЗМЕНЕНИЕ API ДАННЫХ\n\n"
            message += f"1. Reserve ID - текущий: {self.config['reserve_id']}\n"
            message += f"2. Coin Token - текущий: {self.config['coin_token'][:10]}...\n"
            message += f"3. API URL - текущий: {self.config['api_url']}\n\n"
            message += f"Введите номер и значение:"
            
            self.send_message(user_id, message)
            self.users[str(user_id)]['waiting_for'] = 'admin_change_api'
        
        elif command == 'Статистика':
            active_deals = sum(1 for deal in self.deals.values() if deal['status'] == 'active')
            total_deals = len(self.deals)
            total_users = len(self.users)
            
            message = f"СТАТИСТИКА\n\n"
            message += f"Пользователей: {total_users}\n"
            message += f"Всего заявок: {total_deals}\n"
            message += f"Активных заявок: {active_deals}"
            
            self.send_message(user_id, message)
        
        elif command == 'В главное меню':
            self.send_message(user_id, "Возврат в главное меню", self.get_main_keyboard())
            self.users[str(user_id)]['waiting_for'] = None
            self.save_database('users')
    
    def handle_deal_action(self, user_id, message_text):
        """Обработка действий с заявками (подтверждение/отмена/обработка)"""
        try:
            print(f"Обработка действия с заявкой: {message_text}")
            if message_text.startswith('Подтвердить #'):
                deal_id = int(message_text.split('#')[1])
                self.confirm_deal(user_id, deal_id)
            elif message_text.startswith('Отмена #'):
                deal_id = int(message_text.split('#')[1])
                self.cancel_deal(user_id, deal_id)
            elif message_text.startswith('Обработка #'):
                deal_id = int(message_text.split('#')[1])
                self.process_sell_deal(deal_id)
        except (ValueError, IndexError) as e:
            print(f"Ошибка обработки действия с заявкой: {e}")
    
    def confirm_deal(self, user_id, deal_id):
        print(f"Подтверждение заявки #{deal_id} пользователем {user_id}")
        
        if user_id != self.config['admin_id']:
            print(f"Пользователь {user_id} не имеет прав для подтверждения")
            return
        
        deal = self.deals.get(str(deal_id))
        if not deal:
            print(f"Заявка #{deal_id} не найдена")
            return
        
        if deal['type'] == 'buy':
            self.complete_buy_deal_sync(deal)
    
    def cancel_deal(self, user_id, deal_id):
        print(f"Отмена заявки #{deal_id} пользователем {user_id}")
        
        if user_id != self.config['admin_id']:
            print(f"Пользователь {user_id} не имеет прав для отмены")
            return
        
        deal = self.deals.get(str(deal_id))
        if not deal:
            return
        
        deal['status'] = 'cancelled'
        deal['cancelled_at'] = time.time()
        deal['cancelled_by'] = user_id
        self.save_database('deals')
        
        # Уведомляем пользователя
        self.send_message(deal['user_id'], f"ЗАЯВКА ОТМЕНЕНА #{deal_id}")
        
        # Уведомляем админа
        self.send_message(self.config['admin_id'], f"ЗАЯВКА ОТМЕНЕНА #{deal_id}")
    
    def run(self):
        print("Запуск бота...")
        print("Бот начал прослушивание сообщений...")
        
        for event in self.longpoll.listen():
            print(f"Получено событие: {event.type}")
            if event.type == VkBotEventType.MESSAGE_NEW:
                print(f"Новое сообщение: {event.object.message}")
                self.handle_message(event)
    
    def handle_message(self, event):
        user_id = event.object.message['from_id']
        message_text = event.object.message['text']
        
        print(f"Обработка сообщения от {user_id}: {message_text}")
        
        if str(user_id) not in self.users:
            print(f"Новый пользователь: {user_id}")
            self.users[str(user_id)] = {
                'waiting_for': None,
                'created_at': time.time(),
                'bank': 'Не указан',
                'number': 'Не указан'
            }
            self.save_database('users')
        
        user_state = self.users[str(user_id)]['waiting_for']
        print(f"Состояние пользователя: {user_state}")
        
        # Обработка действий с заявками (только для админа)
        if any(x in message_text for x in ['Подтвердить #', 'Отмена #', 'Обработка #']):
            self.handle_deal_action(user_id, message_text)
            return
        
        # Обработка кнопок админки
        if user_state == 'admin_menu':
            if message_text in ['Изменить курс', 'Изменить баланс', 'Изменить реквизиты', 'Изменить API данные', 'Статистика', 'В главное меню']:
                self.handle_admin_settings(user_id, message_text)
                return
        
        # Обработка кнопок профиля
        if user_state == 'profile_menu':
            if message_text == 'Изменить банк':
                self.send_message(user_id, "Введите название вашего банка:")
                self.users[str(user_id)]['waiting_for'] = 'profile_bank'
                self.save_database('users')
                return
            elif message_text == 'Изменить номер':
                self.send_message(user_id, "Введите номер вашего счета:")
                self.users[str(user_id)]['waiting_for'] = 'profile_number'
                self.save_database('users')
                return
            elif message_text == 'В главное меню':
                self.send_message(user_id, "Возврат в главное меню", self.get_main_keyboard())
                self.users[str(user_id)]['waiting_for'] = None
                self.save_database('users')
                return
        
        if user_state and user_state.startswith('admin_'):
            self.handle_admin_input(user_id, message_text)
        elif user_state == 'profile_bank':
            self.update_user_bank(user_id, message_text)
            self.users[str(user_id)]['waiting_for'] = 'profile_menu'
            self.save_database('users')
            self.handle_profile(user_id)
        elif user_state == 'profile_number':
            self.update_user_number(user_id, message_text)
            self.users[str(user_id)]['waiting_for'] = 'profile_menu'
            self.save_database('users')
            self.handle_profile(user_id)
        elif user_state == 'buy_amount':
            self.handle_buy_amount(user_id, message_text)
        elif user_state == 'sell_amount':
            self.handle_sell_amount(user_id, message_text)
        else:
            if message_text.lower() == 'админка':
                self.handle_admin_command(user_id)
            elif message_text == 'Купить':
                self.handle_buy(user_id)
            elif message_text == 'Продать':
                self.handle_sell(user_id)
            elif message_text == 'Информация':
                self.send_info(user_id)
            elif message_text == 'Профиль':
                self.handle_profile(user_id)
            elif message_text.startswith('Банк '):
                self.update_user_bank(user_id, message_text[5:])
            elif message_text.startswith('Номер '):
                self.update_user_number(user_id, message_text[6:])
            elif message_text == 'В главное меню':
                self.send_message(user_id, "Возврат в главное меню", self.get_main_keyboard())
                self.users[str(user_id)]['waiting_for'] = None
                self.save_database('users')
            else:
                self.send_message(user_id, "Wild Shop(mini)\n\nИспользуйте кнопки для навигации", self.get_main_keyboard())
    
    def handle_admin_input(self, user_id, message_text):
        user_state = self.users[str(user_id)]['waiting_for']
        print(f"Обработка админского ввода: {user_state} - {message_text}")
        
        try:
            if user_state == 'admin_change_rate':
                parts = message_text.split()
                if len(parts) == 2:
                    choice, value = parts
                    if choice == '1':
                        self.config['bay'] = float(value)
                        self.save_config()
                        self.send_message(user_id, f"Курс покупки изменен: {value:,} RUB/1000 WC")
                    elif choice == '2':
                        self.config['sell'] = float(value)
                        self.save_config()
                        self.send_message(user_id, f"Курс продажи изменен: {value:,} RUB/1000 WC")
                    else:
                        self.send_message(user_id, "Неверный выбор")
                else:
                    self.send_message(user_id, "Неверный формат")
            
            elif user_state == 'admin_change_balance':
                parts = message_text.split()
                if len(parts) == 2:
                    choice, value = parts
                    if choice == '1':
                        self.config['balance_rub'] = float(value)
                        self.save_config()
                        self.send_message(user_id, f"Баланс RUB изменен: {value:,}")
                    else:
                        self.send_message(user_id, "Неверный выбор")
                else:
                    self.send_message(user_id, "Неверный формат")
            
            elif user_state == 'admin_change_details':
                parts = message_text.split(' ', 1)
                if len(parts) == 2:
                    choice, value = parts
                    if choice == '1':
                        self.config['bank'] = value
                        self.save_config()
                        self.send_message(user_id, f"Банк изменен: {value}")
                    elif choice == '2':
                        self.config['number'] = value
                        self.save_config()
                        self.send_message(user_id, f"Номер счета изменен: {value}")
                    else:
                        self.send_message(user_id, "Неверный выбор")
                else:
                    self.send_message(user_id, "Неверный формат")
            
            elif user_state == 'admin_change_api':
                parts = message_text.split(' ', 1)
                if len(parts) == 2:
                    choice, value = parts
                    if choice == '1':
                        self.config['reserve_id'] = value
                        self.save_config()
                        self.send_message(user_id, f"Reserve ID изменен: {value}")
                    elif choice == '2':
                        self.config['coin_token'] = value
                        self.save_config()
                        self.send_message(user_id, f"Coin Token изменен")
                    elif choice == '3':
                        self.config['api_url'] = value
                        self.save_config()
                        self.send_message(user_id, f"API URL изменен: {value}")
                    else:
                        self.send_message(user_id, "Неверный выбор")
                else:
                    self.send_message(user_id, "Неверный формат")
        
        except ValueError as e:
            print(f"Ошибка обработки админского ввода: {e}")
            self.send_message(user_id, "Неверное значение")
        
        # Возвращаем в админ-меню
        self.users[str(user_id)]['waiting_for'] = 'admin_menu'
        self.save_database('users')
        self.handle_admin_command(user_id)
    
    def update_user_bank(self, user_id, bank_name):
        self.users[str(user_id)]['bank'] = bank_name
        self.save_database('users')
        self.send_message(user_id, f"Банк изменен: {bank_name}")
    
    def update_user_number(self, user_id, number):
        self.users[str(user_id)]['number'] = number
        self.save_database('users')
        self.send_message(user_id, f"Номер счета изменен: {number}")
    
    def send_info(self, user_id):
        print(f"Отправка информации пользователю {user_id}")
        try:
            balance = self.get_balance()
        except:
            balance = "Ошибка"
        
        message = f"Wild Shop(mini)\n\n"
        message += f"Доступно коинов: {balance:,} WC\n"
        message += f"Курс покупки: {self.config['bay']:,} RUB за 1000 WC\n"
        message += f"Курс продажи: {self.config['sell']:,} RUB за 1000 WC\n\n"
        message += f"Быстрые переводы\n"
        message += f"Безопасные сделки\n"
        message += f"Гарантия выполнения\n\n"
        message += f"Разработано RDWeb by @redaimid"
        
        self.send_message(user_id, message)

# Веб-сервер для обработки платежей
from flask import Flask, request, jsonify

app = Flask(__name__)
bot = WildCoinBot()

@app.route('/payment', methods=['POST'])
def handle_payment():
    data = request.get_json()
    bank = data.get('bank')
    message = data.get('message')
    key = data.get('key')
    
    result = bot.process_payment(bank, message, key)
    return jsonify(result)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Bot is running"})

if __name__ == "__main__":
    print("=== ЗАПУСК WILD SHOP BOT ===")
    
    # Запуск Flask сервера в отдельном потоке
    def run_flask():
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("Веб-сервер запущен на порту 5000")
    
    # Запуск бота в основном потоке
    try:
        bot.run()
    except KeyboardInterrupt:
        print("Бот остановлен")
    except Exception as e:
        print(f"Критическая ошибка бота: {e}")
        import traceback
        traceback.print_exc()
