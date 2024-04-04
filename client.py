import logging
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import socket
import tkinter as tk
from tkinter import messagebox
import sqlite3
from tkinter import ttk
import matplotlib
import pandas as pd
import re
import threading
matplotlib.use('TkAgg')

# Server configuration
HOST = '127.0.0.1'
PORT = 8000

# Custom Entry widget with placeholder


def setup_database():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (client_id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, balance REAL DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, transaction_type TEXT NOT NULL,
                  amount REAL NOT NULL, market TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (username) REFERENCES users(username))''')
    conn.commit()
    conn.close()


setup_database()


def register_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                  (username, password))
        conn.commit()
        return 'Registration successful'
    except sqlite3.IntegrityError:
        return 'Username already exists'
    finally:
        conn.close()


class PlaceholderEntry(tk.Entry):
    def __init__(self, master, placeholder, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.placeholder = placeholder
        self.insert(0, self.placeholder)
        self.bind('<FocusIn>', self.clear_placeholder)
        self.bind('<FocusOut>', self.set_placeholder)

    def clear_placeholder(self, event):
        if self.get() == self.placeholder:
            self.delete(0, tk.END)

    def set_placeholder(self, event):
        if not self.get():
            self.insert(0, self.placeholder)

# Main window class


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("User Login")
        self.geometry("500x500")
        self.center_window()

        # Create labels and entry fields for username and password
        username_label = tk.Label(self, text="Username:")
        username_label.pack()
        self.username_entry = PlaceholderEntry(self, "Enter your username")
        self.username_entry.pack()

        password_label = tk.Label(self, text="Password:")
        password_label.pack()
        self.password_entry = PlaceholderEntry(
            self, "Enter your password", show="*")
        self.password_entry.pack()

        # Create a login button
        login_button = tk.Button(self, text="Login", command=self.login)
        login_button.pack(pady=10)

        # Create a register button
        register_button = tk.Button(
            self, text="Register", command=self.register)
        register_button.pack()

        # Handle window close event
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def center_window(self):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_position = (screen_width // 2) - (500 // 2)
        y_position = (screen_height // 2) - (500 // 2)
        self.geometry(f"500x500+{x_position}+{y_position}")

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            request = f'login|{username}|{password}'
            s.sendall(request.encode())
            response = s.recv(1024).decode()
        if response.startswith('Login successful'):
            client_id = response.split(': ')[-1]  # Correctly extract client ID
            self.withdraw()  # Hide the login window
            account_window = AccountWindow(self, username, client_id.strip())
        else:
            messagebox.showerror("Login Failed", response)

    def register(self):
        RegisterWindow(self)

    def on_closing(self):
        self.quit()

# Register window class


class RegisterWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Register")
        self.geometry("500x500")
        self.center_window()

        # Create labels and entry fields for username and password
        username_label = tk.Label(self, text="Username:")
        username_label.pack()
        self.username_entry = PlaceholderEntry(self, "Enter your username")
        self.username_entry.pack()

        password_label = tk.Label(self, text="Password:")
        password_label.pack()
        self.password_entry = PlaceholderEntry(
            self, "Enter your password", show="*")
        self.password_entry.pack()

        # Create a register button
        register_button = tk.Button(
            self, text="Register", command=self.register_user)
        register_button.pack(pady=10)

    def center_window(self):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_position = (screen_width // 2) - (500 // 2)
        y_position = (screen_height // 2) - (500 // 2)
        self.geometry(f"500x500+{x_position}+{y_position}")

    def register_user(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        # Validate username and password
        if not username or not password:
            messagebox.showerror(
                "Error", "Please enter both username and password")
            return
        elif len(username) < 4 or len(password) < 6:
            messagebox.showerror(
                "Error", "Username must be at least 4 characters and password must be at least 6 characters")
            return

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            request = f'register|{username}|{password}'
            s.sendall(request.encode())
            response = s.recv(1024).decode()

        messagebox.showinfo("Registration Result", response)
        self.destroy()
        self.master.deiconify()  # Show the main window again

# Account window class


class AccountWindow(tk.Toplevel):
    def __init__(self, parent, username, client_id):
        super().__init__(parent)
        self.client_id = client_id
        self.username = username
        self.title(f"{username}'s Account")
        self.geometry("600x600")
        self.protocol("WM_DELETE_WINDOW", self.quit)
        self.center_window()

        self.portfolio = {"balance": 500, "investments": {}}

        client_id_label = tk.Label(self, text=f"Client ID: {self.client_id}")
        client_id_label.pack()

        self.balance_label = tk.Label(self)
        self.balance_label.pack(pady=10)
        self.balance_label.config(
            text=f"Welcome to your account, {username}! Your current balance: £{self.portfolio['balance']}")

        self.amount_entry = PlaceholderEntry(self, "Enter amount")
        self.amount_entry.pack(pady=10)

        button_frame = tk.Frame(self)
        button_frame.pack(pady=10)

        deposit_button = tk.Button(
            button_frame, text="Deposit", command=self.deposit_money)
        deposit_button.pack(side='left', padx=(0, 20))

        withdraw_button = tk.Button(
            button_frame, text="Withdraw", command=self.withdraw_money)
        withdraw_button.pack(side='left')

        portfolio_button = tk.Button(
            self, text="Portfolio Viewing", command=self.open_portfolio)
        portfolio_button.pack(pady=5)

        self.request_update_balance()

    def deposit_money(self):
        amount_str = self.amount_entry.get()
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("Amount must be positive")
            # Connect to the database
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            # Update the user's balance
            c.execute(
                "UPDATE users SET balance = balance + ? WHERE username = ?", (amount, self.username))
            # Log the transaction
            c.execute(
                "INSERT INTO transactions (username, transaction_type, amount) VALUES (?, 'deposit', ?)", (self.username, amount))
            conn.commit()
            conn.close()
            messagebox.showinfo(
                "Deposit Successful", f"${amount} has been deposited to your balance.")
            self.request_update_balance()  # Refresh balance display
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def withdraw_money(self):
        amount_str = self.amount_entry.get()
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("Amount must be positive")
            # Connect to the database
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            # Check if the balance is sufficient
            c.execute("SELECT balance FROM users WHERE username = ?",
                      (self.username,))
            balance = c.fetchone()[0]
            if balance < amount:
                raise ValueError("Insufficient funds")
            # Withdraw the amount
            c.execute(
                "UPDATE users SET balance = balance - ? WHERE username = ?", (amount, self.username))
            # Log the transaction
            c.execute(
                "INSERT INTO transactions (username, transaction_type, amount) VALUES (?, 'withdraw', ?)", (self.username, amount))
            conn.commit()
            conn.close()
            messagebox.showinfo(
                "Withdrawal Successful", f"${amount} has been withdrawn from your balance.")
            self.request_update_balance()  # Refresh balance display
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def _update_balance(self, amount_change):
        """Updates the user's balance in the database and records the transaction."""
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        # Update balance
        if amount_change > 0:
            transaction_type = 'deposit'
        else:
            transaction_type = 'withdraw'
            amount_change = -amount_change  # Make the amount positive for storage
        try:
            c.execute("UPDATE users SET balance = balance + ? WHERE username = ?",
                      (amount_change, self.username))
            c.execute("INSERT INTO transactions (username, transaction_type, amount) VALUES (?, ?, ?)",
                      (self.username, transaction_type, amount_change))
            conn.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))
        finally:
            conn.close()

    def update_balance_display(self):
        """Updates the balance label with the latest balance."""
        self.balance_label.config(
            text=f"Current Balance: ${self.portfolio['balance']}")

    def center_window(self):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_position = (screen_width // 2) - (600 // 2)
        y_position = (screen_height // 2) - (600 // 2)
        self.geometry(f"600x600+{x_position}+{y_position}")

    def request_update_balance(self):
        request = f'get_balance|{self.username}'
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(request.encode())
            response = s.recv(1024).decode()
            try:
                # Attempt to convert the response to a float.
                balance = float(response)
                self.portfolio['balance'] = balance
                self.update_balance_display()
            except ValueError:
                # If the response cannot be converted to a float, log the error.
                print("Error fetching balance:", response)

    def open_portfolio(self):
        # Ensure to pass the client_id and the current balance to the PortfolioWindow
        PortfolioWindow(self, self.username, self.client_id,
                        self.portfolio['balance'])


class PortfolioWindow(tk.Toplevel):
    def __init__(self, parent, username, client_id, balance):
        super().__init__(parent)
        self.username = username
        self.client_id = client_id
        self.balance = balance
        self.investment_option = tk.StringVar(self)
        self.portfolio = {'balance': balance}
        self.title(f"{username}'s Portfolio")
        self.geometry("800x600")
        self.center_window()

        self.market_files = {
            'Stocks': 'stocks.csv',
            'Cryptocurrency': 'cryptocurrencies.csv'
        }

        self.investment_option.set('Stocks')
        self.create_widgets()
        self.update_graph()

    def create_widgets(self):
        client_id_label = tk.Label(self, text=f"Client ID: {self.client_id}")
        client_id_label.pack()

        self.balance_label = tk.Label(
            self, text=f"Current Balance: ${self.balance}")
        self.balance_label.pack(pady=10)

        main_frame = tk.Frame(self)
        main_frame.pack(fill='both', expand=True)

        grid_frame = tk.Frame(main_frame)
        grid_frame.pack(side='left', fill='both', expand=True)

        self.tree = ttk.Treeview(grid_frame, columns=(
            'Market', 'Quantity', 'Amount'), show='headings')
        self.tree.heading('Market', text='Market')
        self.tree.heading('Quantity', text='Quantity')
        self.tree.heading('Amount', text='Amount')

        self.tree.column('Market', anchor='center')
        self.tree.column('Quantity', anchor='center')
        self.tree.column('Amount', anchor='center')

        self.tree.pack(fill='both', expand=True)

        chart_frame = tk.Frame(main_frame)
        chart_frame.pack(side='right', fill='both', expand=True)

        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side='top', fill='both', expand=True)

        invest_frame = tk.Frame(self)
        invest_frame.pack(pady=10)

        invest_button = tk.Button(
            invest_frame, text="Invest", command=self.open_investment_window)
        invest_button.pack(side='left', padx=10)

        self.investment_option = tk.StringVar(self)
        self.investment_option.set('Stocks')

        investment_menu = tk.OptionMenu(
            self, self.investment_option, *self.market_files.keys(), command=self.update_graph
        )
        investment_menu.pack(pady=10)

        my_investment_button = tk.Button(
            invest_frame, text="My Investments", command=self.open_my_investment_window)
        my_investment_button.pack(side='left', padx=10)

        self.investment_option.trace("w", self.update_graph)
        self.request_update_balance()

    def request_update_balance(self):
        request = f'get_balance|{self.username}'
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(request.encode())
            response = s.recv(1024).decode()
            try:
                balance = float(response)
                self.portfolio['balance'] = balance
            except ValueError:
                print("Error fetching balance:", response)

    def update_balance_display(self):
        self.portfolio['balance'] = self.balance
        self.balance_label.config(
            text=f"Current Balance: ${self.portfolio['balance']}")

    def update_display(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for stock, data in self.stocks.items():
            self.tree.insert('', 'end', values=(stock, data[1]))
        self.balance_label.configure(
            text=f"Current Balance: ${self.portfolio['balance']}")

    def update_balance_display(self):
        self.portfolio['balance'] = self.balance
        self.balance_label.config(
            text=f"Current Balance: ${self.portfolio['balance']}")

    def open_investment_window(self):
        selected_option = self.investment_option.get()
        Investment(self, self.username, selected_option)

    def open_my_investment_window(self):
        MyInvestmentWindow(self, self.username)

    def populate_treeview(self, dataframe, market_type):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for index, row in dataframe.iterrows():
            market_name = row['Name']
            quantity = "1"
            if market_type == 'Stocks':
                amount = f"${row['Last Price']}"
                market_display_name = market_name
            elif market_type == 'Cryptocurrency':
                amount = f"${row['Price']}"
                market_display_name = market_name

            self.tree.insert('', 'end', values=(
                market_display_name, quantity, amount))

    def update_graph(self, *args):
        selected_market = self.investment_option.get()
        if selected_market == 'Stocks':
            self.plot_stock_data()
        elif selected_market == 'Cryptocurrency':
            self.plot_crypto_data()
        else:
            print(f"Selected market '{selected_market}' not recognized.")

    def plot_stock_data(self):
        try:
            stocks_df = pd.read_csv('stocks.csv')
            if not stocks_df.empty:
                self.ax.clear()
                self.ax.bar(stocks_df['Name'],
                            stocks_df['Last Price'], color='skyblue')
                self.ax.set_title('Top 10 Stock Prices')
                self.ax.set_xlabel('Stock')
                self.ax.set_ylabel('Last Price')
                self.ax.tick_params(axis='x', rotation=45)
                plt.tight_layout()
                self.canvas.draw()
                self.populate_treeview(stocks_df, 'Stocks')  # Update Treeview
            else:
                print("Stock data file is empty or not found.")
        except Exception as e:
            print(f"Error loading or plotting stock data: {e}")

    def plot_crypto_data(self):
        try:
            cryptos_df = pd.read_csv('cryptocurrencies.csv')
            if not cryptos_df.empty:
                cryptos_df['Price'] = cryptos_df['Price'].replace(
                    '[\$,]', '', regex=True).astype(float)
                self.plot_data(cryptos_df, 'Cryptocurrency Prices')
                self.populate_treeview(
                    cryptos_df, 'Cryptocurrency')  # Update Treeview
            else:
                print("Cryptocurrency data file is empty or not found.")
        except Exception as e:
            print(f"Error loading or plotting cryptocurrency data: {e}")

    def plot_data(self, df, title):
        self.ax.clear()
        self.ax.bar(df['Name'], df['Price'], color='skyblue')
        self.ax.set_title(title)
        self.ax.set_xlabel('Name')
        self.ax.set_ylabel('Price')
        self.ax.tick_params(axis='x', rotation=45)
        plt.tight_layout()
        self.canvas.draw()

    def center_window(self):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = 1400
        window_height = 700
        x_position = (screen_width // 2) - (window_width // 2)
        y_position = (screen_height // 2) - (window_height // 2) - 45
        self.geometry(
            f"{window_width}x{window_height}+{x_position}+{y_position}")


class Investment(tk.Toplevel):
    def __init__(self, parent, username, investment_option):
        super().__init__(parent)
        self.username = username
        self.investment_option = investment_option
        self.title("Investment")
        self.geometry("400x300")
        self.trade_option = tk.StringVar(value="Buy")
        self.create_widgets()

    def create_widgets(self):
        tk.Label(self, text=f"Invest in {self.investment_option}").pack(
            pady=10)

        self.investment_amount = tk.StringVar()
        tk.Entry(self, textvariable=self.investment_amount).pack(pady=10)

        tk.Label(self, text="Trade Option:").pack()
        trade_option_frame = tk.Frame(self)
        trade_option_frame.pack(pady=5)

        tk.Radiobutton(trade_option_frame, text="Buy",
                       variable=self.trade_option, value="Buy").pack(side='left', padx=5)
        tk.Radiobutton(trade_option_frame, text="Sell",
                       variable=self.trade_option, value="Sell").pack(side='left', padx=5)

        tk.Button(self, text="Confirm",
                  command=self.confirm_investment).pack(pady=10)

        tk.Button(self, text="Cancel", command=self.destroy).pack(pady=10)

    def confirm_investment(self):
        print(
            f"Invested {self.investment_amount.get()} in {self.investment_option}")
        self.destroy()


class MyInvestmentWindow(tk.Toplevel):
    def __init__(self, parent, username):
        super().__init__(parent)
        self.username = username
        self.title(f"{username}'s Investments")
        self.geometry("600x400")
        self.create_widgets()
        self.populate_investments()

    def create_widgets(self):
        self.tree = ttk.Treeview(self, columns=(
            'Market', 'Quantity', 'Amount'), show='headings')
        self.tree.heading('Market', text='Market')
        self.tree.heading('Quantity', text='Quantity')
        self.tree.heading('Amount', text='Amount')
        self.tree.pack(fill='both', expand=True)

    def populate_investments(self):
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute(
            "SELECT market, quantity, amount FROM portfolios WHERE username=?", (self.username,))
        investments = c.fetchall()
        conn.close()

        for market, quantity, amount in investments:
            self.tree.insert('', 'end', values=(market, quantity, amount))


# Run the application
if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
