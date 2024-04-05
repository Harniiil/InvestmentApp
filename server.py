import sqlite3
import socket
import threading
from contextlib import contextmanager
import requests
from bs4 import BeautifulSoup
import csv
import logging
import re

HOST = '127.0.0.1'
PORT = 8000


def create_database_and_tables():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (client_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  balance REAL DEFAULT 0,
                  UNIQUE(username))''')

    c.execute('''CREATE TABLE IF NOT EXISTS portfolios
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT NOT NULL,
                  market TEXT NOT NULL,
                  quantity INTEGER NOT NULL,
                  amount REAL NOT NULL,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (username) REFERENCES accounts(username))''')

    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT NOT NULL,
                  transaction_type TEXT NOT NULL,
                  amount REAL NOT NULL,
                  market TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (username) REFERENCES users(username))''')

    conn.close()


create_database_and_tables()


@contextmanager
def db_connection(database='users.db'):
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    try:
        yield conn, cursor
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def handle_client(conn, addr):
    try:
        with conn:
            print(f'Connected with {addr}')
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                request = data.decode().split('|')
                action = request[0]

                if action == 'login':
                    username = request[1]
                    password = request[2]
                    conn.sendall(authenticate(username, password).encode())

                elif action == 'register':
                    username = request[1]
                    password = request[2]
                    conn.sendall(register_user(username, password).encode())

                elif action == 'deposit':
                    username = request[1]
                    amount = float(request[2])
                    response = deposit(username, amount)
                    conn.sendall(response.encode())

                elif action == 'get_balance':
                    username = request[1]
                    conn.sendall(str(get_balance(username)).encode())

                elif action == 'invest':
                    username = request[1]
                    market = request[2]
                    quantity = int(request[3])
                    amount = float(request[4])
                    transaction_type = request[5]
                    response = invest(username, market,
                                      quantity, amount, transaction_type)
                    conn.sendall(response.encode())

                elif action == 'withdraw':
                    username = request[1]
                    amount = float(request[2])
                    response = withdraw_money(username, amount)
                    conn.sendall(response.encode())

                elif action == 'sell_stock':
                    username, stock, amount = request[1], request[2], int(
                        request[3])
                    response = sell_stock(username, stock, amount)
                    conn.sendall(str(response).encode())
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        print(f'Disconnected from {addr}')


def deposit(username, amount):
    if amount <= 0:
        return 'Deposit amount must be positive.'
    try:
        with db_connection() as (conn, db):
            db.execute(
                "UPDATE users SET balance = balance + ? WHERE username = ?", (amount, username))
            conn.commit()
            return 'Deposit successful.'
    except Exception as e:
        print(f"An error occurred during the deposit operation: {e}")
        return 'Error processing the deposit.'


def withdraw_money(username, amount):
    if amount <= 0:
        return 'Withdrawal amount must be positive'
    try:
        with db_connection() as db:
            db.execute(
                "SELECT balance FROM accounts WHERE username = ?", (username,))
            balance = db.fetchone()[0]
            if balance < amount:
                return 'Insufficient funds'
            db.execute(
                "UPDATE accounts SET balance = balance - ? WHERE username = ?", (amount, username))
            return 'Withdrawal successful'
    except sqlite3.Error as e:
        return f'Database error during withdrawal: {e}'


def authenticate(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT client_id FROM users WHERE username=? AND password=?",
              (username, password))
    result = c.fetchone()
    conn.close()
    if result:
        client_id = result[0]
        return f'Login successful, Client ID: {client_id}'
    else:
        return 'Login failed'


def register_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                  (username, password))
        conn.commit()
        c.execute("SELECT client_id FROM users WHERE username=?", (username,))
        client_id = c.fetchone()[0]
        return f'Registration successful, Client ID: {client_id}'
    except sqlite3.IntegrityError:
        return 'Username already exists'
    finally:
        conn.close()


def get_balance(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE username = ?", (username,))
    balance = c.fetchone()[0]
    conn.close()
    return balance


def invest(username, market, quantity, amount, transaction_type):
    try:
        with db_connection() as (conn, cursor):
            cursor.execute(
                "SELECT balance FROM users WHERE username = ?", (username,))
            balance_result = cursor.fetchone()
            if balance_result and balance_result[0] >= amount:
                cursor.execute(
                    "UPDATE users SET balance = balance - ? WHERE username = ?", (amount, username))
                cursor.execute("INSERT INTO portfolios (username, market, quantity, amount) VALUES (?, ?, ?, ?)",
                               (username, market, quantity, amount))
                cursor.execute("INSERT INTO transactions (username, transaction_type, amount, market) VALUES (?, ?, ?, ?)",
                               (username, transaction_type, amount, market))
                conn.commit()
                return 'Investment successful'
            else:
                return 'Insufficient funds'
    except Exception as e:
        print(f"Error during investment: {e}")
        return f'Error during investment: {e}'


def sell_stock(username, stock, amount):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    c.execute("SELECT price FROM stocks WHERE stock=?", (stock,))
    result = c.fetchone()
    if result:
        stock_price = result[0]
    else:
        return {"status": "failure", "message": "Invalid stock."}

    c.execute(
        "SELECT quantity FROM investments WHERE username=? AND stock=?", (username, stock))
    result = c.fetchone()
    if result and result[0] >= amount:
        new_quantity = result[0] - amount
        if new_quantity > 0:
            c.execute("UPDATE investments SET quantity=? WHERE username=? AND stock=?",
                      (new_quantity, username, stock))
        else:
            c.execute(
                "DELETE FROM investments WHERE username=? AND stock=?", (username, stock))

        total_gain = stock_price * amount
        c.execute("UPDATE users SET balance = balance + ? WHERE username=?",
                  (total_gain, username))
        conn.commit()
        return {"status": "success", "message": "Stock sold successfully."}
    else:
        return {"status": "failure", "message": "Not enough stock to sell."}

    conn.close()


class CryptoScraper:
    def __init__(self, url='https://coinranking.com/'):
        self.url = url
        self.crypto_names = []
        self.crypto_prices = []
        self.crypto_market_caps = []

    def fetch_data(self):
        response = requests.get(self.url)
        webpage = response.text
        soup = BeautifulSoup(webpage, 'html.parser')

        self.crypto_names = soup.find_all(class_="profile__name")[:10]
        all_valuta = soup.find_all(class_="valuta valuta--light")[:20]

        self.crypto_prices = all_valuta[::2]
        self.crypto_market_caps = all_valuta[1::2]

    def write_to_csv(self, filepath='cryptocurrencies.csv'):
        with open(filepath, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Name', 'Price', 'Market Cap'])

            for name, price, market_cap in zip(self.crypto_names, self.crypto_prices, self.crypto_market_caps):
                cleaned_price = price.get_text(strip=True).replace(
                    "\n", "").replace("        ", "")
                cleaned_market_cap = market_cap.get_text(
                    strip=True).replace("\n", "").replace("        ", "")
                writer.writerow([name.get_text(strip=True),
                                cleaned_price, cleaned_market_cap])

        print(f"Data has been written to {filepath}.")


class StockScraper:
    def __init__(self, tick_file, output_file):
        self.base_url = 'https://www.cnbc.com/quotes/'
        self.tick_file = tick_file
        self.output_file = output_file
        logging.basicConfig(filename='webscraping.log', level=logging.DEBUG)

    def read_ticks(self):
        try:
            with open(self.tick_file, 'r') as f:
                return [tick.strip() for tick in f.readlines()[1:]]
        except FileNotFoundError as e:
            logging.error(f"Could not read {self.tick_file} file: {e}")
            return []

    def scrape_data(self):
        tick_list = self.read_ticks()
        urls = [self.base_url + tick for tick in tick_list]

        with open(self.output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Name', 'Last Trade Time', 'Last Price'])
            for url in urls:
                try:
                    response = requests.get(url)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, 'html.parser')
                    name, last_trade_time, last_price = self.parse_page(
                        soup, url)
                    if name and last_price:
                        writer.writerow([name, last_trade_time, last_price])
                except requests.exceptions.RequestException as err:
                    logging.error(f"Request error for {url}: {err}")

    def parse_page(self, soup, url):
        try:
            name = soup.find(class_='QuoteStrip-name').text
            last_trade_time_element = soup.find(
                class_='QuoteStrip-extendedLastTradeTime')
            last_trade_time = last_trade_time_element.text.replace(
                "After Hours: Last | ", "") if last_trade_time_element else "N/A"

            last_price_full = soup.find(
                class_='QuoteStrip-lastPriceStripContainer').text
            last_price = re.search(
                r'[\d,]+\.\d+', last_price_full).group(0) if last_price_full else "N/A"

            return name, last_trade_time, last_price
        except AttributeError as e:
            logging.error(f"Could not find data for {url}: {e}")
            return None, None, None


def update_crypto_data():
    scraper = CryptoScraper()
    scraper.fetch_data()
    scraper.write_to_csv()
    print("Cryptocurrency data updated.")


def update_stock_data():
    scraper = StockScraper('ticks.csv', 'stocks.csv')
    scraper.scrape_data()
    print("Stock data updated.")


def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f'Server listening on {HOST}:{PORT}')

        while True:
            conn, addr = s.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()


if __name__ == '__main__':
    update_stock_data()
    update_crypto_data()
    start_server()
