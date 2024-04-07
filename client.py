"""External Python Libraries"""
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import socket
import tkinter as tk
from tkinter import messagebox
import sqlite3
from tkinter import ttk
import matplotlib
import pandas as pd
matplotlib.use('TkAgg')

# Defining the Host and Port to make connection
HOST = '127.0.0.1'
PORT = 8000


class CenteredTkWindow:
    # Class to center all the screen window
    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = int((screen_width - width) / 2)
        y = int((screen_height - height) / 2)
        self.geometry(f'{width}x{height}+{x}+{y}')


class PlaceholderEntry(tk.Entry):
    # class for the placeholders
    def __init__(self, master, placeholder, *args, **kwargs):
        # * args - to pass a variable number of arguments to a function
        # **kwargs - to pass a keyworded, variable-length argument dictionary to a function
        # initialization of the class
        super().__init__(master, *args, **kwargs)
        self.placeholder = placeholder
        self.insert(0, self.placeholder)
        self.bind('<FocusIn>', self.clear_placeholder)
        self.bind('<FocusOut>', self.set_placeholder)

    def clear_placeholder(self, event):
        # to clear text when user clicks on input block
        if self.get() == self.placeholder:
            self.delete(0, tk.END)

    def set_placeholder(self, event):
        if not self.get():
            self.insert(0, self.placeholder)


class MainWindow(tk.Tk, CenteredTkWindow):
    # class for main userinterface (GUI)
    def __init__(self):
        # initialization of the class
        super(MainWindow, self).__init__()
        self.title("User Login")  # Title of the window
        self.geometry("500x500")  # window size
        self.center_window()  # calling center window

        """ GUI components - Button, Input Block, Labels"""
        username_label = tk.Label(self, text="Username:")
        username_label.pack()
        self.username_entry = PlaceholderEntry(self, "Enter your username")
        self.username_entry.pack()

        password_label = tk.Label(self, text="Password:")
        password_label.pack()
        self.password_entry = PlaceholderEntry(
            self, "Enter your password", show="*")
        self.password_entry.pack()

        login_button = tk.Button(self, text="Login", command=self.login)
        login_button.pack(pady=10)

        register_button = tk.Button(
            self, text="Register", command=self.register)
        register_button.pack()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        # exit code when user close window

    def login(self):
        # perform this function when user tries to login
        username = self.username_entry.get()  # Get user input
        password = self.password_entry.get()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            request = f'login|{username}|{password}'
            s.sendall(request.encode())  # S - TCP Socket - send data to server
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
        self.quit()  # after register this window will close it self


class RegisterWindow(tk.Toplevel, CenteredTkWindow):
    # Class for the registration process
    def __init__(self, parent):
        # initialization of the class
        super().__init__(parent)
        self.title("Register")
        self.geometry("500x500")
        self.center_window()

        """ GUI components - Button, Input Block, Labels"""
        username_label = tk.Label(self, text="Username:")
        username_label.pack()
        self.username_entry = PlaceholderEntry(self, "Enter your username")
        self.username_entry.pack()

        password_label = tk.Label(self, text="Password:")
        password_label.pack()
        self.password_entry = PlaceholderEntry(
            self, "Enter your password", show="*")
        self.password_entry.pack()

        register_button = tk.Button(
            self, text="Register", command=self.register_user)
        register_button.pack(pady=10)

    def register_user(self):
        # Function logic behind register process
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showerror(
                "Error", "Please enter both username and password")
            return
        elif len(username) < 4 or len(password) < 6:
            messagebox.showerror(
                "Error", "Username must be at least 4 characters and password must be at least 6 characters")
            return

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # send data to server of newly register user
            s.connect((HOST, PORT))
            request = f'register|{username}|{password}'
            s.sendall(request.encode())
            response = s.recv(1024).decode()

        messagebox.showinfo("Registration Result", response)
        self.destroy()
        self.master.deiconify()


class AccountWindow(tk.Toplevel, CenteredTkWindow):
    # Class for the Account Window
    def __init__(self, parent, username, client_id):
        # initialization of the class
        super().__init__(parent)
        self.client_id = client_id
        self.username = username
        self.title(f"{username}'s Account")
        self.geometry("600x600")
        self.protocol("WM_DELETE_WINDOW", self.quit)
        self.center_window()
        """ GUI components - Button, Input Block, Labels"""
        self.portfolio = {"balance": 500, "investments": {}}

        client_id_label = tk.Label(self, text=f"Client ID: {self.client_id}")
        client_id_label.pack()

        self.balance_label = tk.Label(self)
        self.balance_label.pack(pady=10)
        self.balance_label.config(
            text=f"Welcome to your account, {username}! Your current balance: £{self.portfolio['balance']:.2f}"
        )

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
        # Function to perfrom when user try to deposit money
        amount_str = self.amount_entry.get()
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("Amount must be positive")
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute(
                "UPDATE users SET balance = balance + ? WHERE username = ?", (amount, self.username))
            c.execute(
                "INSERT INTO transactions (username, transaction_type, amount) VALUES (?, 'deposit', ?)", (self.username, amount))
            conn.commit()
            conn.close()
            messagebox.showinfo(
                "Deposit Successful", f"${amount} has been deposited to your balance.")
            self.request_update_balance()
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def withdraw_money(self):
        # Function to perform when user try to withdraw money
        amount_str = self.amount_entry.get()
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("Amount must be positive")
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("SELECT balance FROM users WHERE username = ?",
                      (self.username,))
            balance = c.fetchone()[0]
            if balance < amount:
                raise ValueError("Insufficient funds")
            c.execute(
                "UPDATE users SET balance = balance - ? WHERE username = ?", (amount, self.username))
            c.execute(
                "INSERT INTO transactions (username, transaction_type, amount) VALUES (?, 'withdraw', ?)", (self.username, amount))
            conn.commit()
            conn.close()
            messagebox.showinfo(
                "Withdrawal Successful", f"${amount} has been withdrawn from your balance.")
            self.request_update_balance()
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def _update_balance(self, amount_change):
        """Updates the user's balance in the database and records the transaction."""
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        if amount_change > 0:
            transaction_type = 'deposit'
        else:
            transaction_type = 'withdraw'
            amount_change = -amount_change
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
            text=f"Current Balance: ${self.portfolio['balance']:.2f}")

    def request_update_balance(self):
        # Fucntion to resquest balance from server side
        request = f'get_balance|{self.username}'
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(request.encode())
            response = s.recv(1024).decode()
            try:
                balance = float(response)
                self.portfolio['balance'] = balance
                self.update_balance_display()
            except ValueError:
                print("Error fetching balance:", response)

    def open_portfolio(self):
        PortfolioWindow(self, self.username, self.client_id,
                        self.portfolio['balance'])


class PortfolioWindow(tk.Toplevel, CenteredTkWindow):
    # Class for the Portfolio Window
    def __init__(self, parent, username, client_id, balance):
        # initialization of the class
        super().__init__(parent)
        self.username = username
        self.client_id = client_id
        self.balance = balance
        self.investment_option = tk.StringVar(self)
        self.portfolio = {'balance': balance}
        self.title(f"{username}'s Portfolio")
        self.geometry("1400x650")
        self.center_window()

        self.market_files = {
            'Stocks': 'stocks.csv',
            'Cryptocurrency': 'cryptocurrencies.csv'
        }

        self.investment_option.set('Stocks')
        self.create_widgets()
        self.update_graph()

    def create_widgets(self):
        """ GUI components - Button, Input Block, Labels"""
        client_id_label = tk.Label(self, text=f"Client ID: {self.client_id}")
        client_id_label.pack()

        self.balance_label = tk.Label(
            self, text=f"Current Balance: ${self.balance:.2f}")  # :.2f - 2 Decimal place
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
            invest_frame, text="Invest", command=self.open_investment_window_with_selection)
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

    def open_investment_window(self):
        selected_option = self.investment_option.get()
        Investment(self, self.username, selected_option)

    def open_my_investment_window(self):
        MyInvestmentWindow(self, self.username)

    def refresh_investments(self):
        self.populate_investments()
        self.request_update_balance()
        self.update_display()

    def open_investment_window_with_selection(self):
        # Functoin for the selection of the stocks/Crypto
        selected_items = self.tree.selection()
        if selected_items:
            selected_item = selected_items[0]
            item_values = self.tree.item(selected_item, 'values')
            market_name = item_values[0]
            item_price = float(item_values[2].strip('$'))
            Investment(self, self.username, market_name,
                       item_price)
        else:
            messagebox.showwarning(
                "Selection Missing", "Please select a stock or cryptocurrency from the list.")

    def populate_treeview(self, dataframe, market_type):
        """ GUI components - Trss, Labels"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        for index, row in dataframe.iterrows():
            market_name = row['Name']
            quantity = "1"
            if market_type == 'Stocks':
                amount = f"${row['Last Price']:.2f}"
                market_display_name = market_name
            elif market_type == 'Cryptocurrency':
                amount = f"${row['Price']:.2f}"
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
        """ GUI components - To plot stock graph"""
        try:
            stocks_df = pd.read_csv('stocks.csv')
            if not stocks_df.empty:
                self.ax.clear()
                # Use ax.plot for a line graph instead of ax.bar
                self.ax.plot(stocks_df['Name'], stocks_df['Last Price'],
                             color='skyblue', marker='o', linestyle='-', linewidth=2)
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
        """ GUI components - To plot crypto graph"""
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


class Investment(tk.Toplevel, CenteredTkWindow):
    def __init__(self, parent, username, selected_market, item_price):
        # initialization of the class
        super().__init__(parent)
        self.username = username
        self.selected_market = selected_market
        self.item_price = item_price  # Store the price
        self.title("Investment")
        self.geometry("400x400")
        self.trade_option = tk.StringVar(value="Buy")
        self.quantity_var = tk.IntVar(value=1, name='quantity_var')
        self.quantity_var.trace_add(
            'write', self.update_investment_amount_callback)
        self.create_widgets()
        self.update_investment_amount()
        self.center_window()

    def create_widgets(self):
        """ GUI components - Button, Input Block, Labels"""
        tk.Label(self, text=f"Invest in {self.selected_market}").pack(pady=10)

        self.investment_amount_var = tk.StringVar()
        tk.Label(self, text="Amount:").pack(pady=5)
        tk.Entry(self, textvariable=self.investment_amount_var,
                 state='readonly').pack(pady=5)

        tk.Label(self, text="Trade Option:").pack()
        trade_option_frame = tk.Frame(self)
        trade_option_frame.pack(pady=5)

        tk.Label(self, text="Quantity:").pack(pady=5)
        self.quantity_spinbox = tk.Spinbox(
            self, from_=1, to=1000, width=5, textvariable=self.quantity_var)
        self.quantity_spinbox.pack(pady=5)

        self.quantity_spinbox.bind(
            '<KeyRelease>', lambda event: self.update_investment_amount())
        self.quantity_spinbox.bind(
            '<<Increment>>', lambda event: self.update_investment_amount())
        self.quantity_spinbox.bind(
            '<<Decrement>>', lambda event: self.update_investment_amount())

        tk.Radiobutton(trade_option_frame, text="Buy",
                       variable=self.trade_option, value="Buy").pack(side='left', padx=5)
        tk.Radiobutton(trade_option_frame, text="Sell",
                       variable=self.trade_option, value="Sell").pack(side='left', padx=5)

        tk.Button(self, text="Confirm",
                  command=self.confirm_investment).pack(pady=10)
        tk.Button(self, text="Cancel", command=self.destroy).pack(pady=10)

    def update_investment_amount(self, event=None):
        total_amount = self.item_price * self.quantity_var.get()
        self.investment_amount_var.set(f"{total_amount:.2f}")

    def update_investment_amount_callback(self, *args):
        self.update_investment_amount()

    def confirm_investment(self):
        # Function to perfrom when user try to invest
        transaction_type = self.trade_option.get()
        username = self.username
        selected_market = self.selected_market
        quantity = self.quantity_var.get()
        item_price = self.item_price

        total_amount = item_price * quantity

        conn = sqlite3.connect('users.db')
        c = conn.cursor()

        if transaction_type == "Buy":
            c.execute("SELECT balance FROM users WHERE username=?", (username,))
            balance = c.fetchone()[0]
            if balance < total_amount:
                messagebox.showerror("Error", "Insufficient funds")
                return
            else:
                c.execute(
                    "UPDATE users SET balance = balance - ? WHERE username=?", (total_amount, username))
                c.execute("INSERT INTO transactions (username, transaction_type, amount, market) VALUES (?, ?, ?, ?)",
                          (username, 'buy', total_amount, selected_market))
                # Check if the user already owns part of the market
                c.execute("SELECT quantity FROM portfolios WHERE username=? AND market=?",
                          (username, selected_market))
                row = c.fetchone()
                if row:
                    new_quantity = row[0] + quantity
                    c.execute("UPDATE portfolios SET quantity=? WHERE username=? AND market=?",
                              (new_quantity, username, selected_market))
                else:
                    c.execute("INSERT INTO portfolios (username, market, quantity, amount) VALUES (?, ?, ?, ?)",
                              (username, selected_market, quantity, total_amount))
        elif transaction_type == "Sell":
            c.execute("SELECT quantity FROM portfolios WHERE username=? AND market=?",
                      (username, selected_market))
            row = c.fetchone()
            if row and row[0] >= quantity:
                c.execute(
                    "UPDATE users SET balance = balance + ? WHERE username=?", (total_amount, username))
                c.execute("INSERT INTO transactions (username, transaction_type, amount, market) VALUES (?, ?, ?, ?)",
                          (username, 'sell', total_amount, selected_market))
                new_quantity = row[0] - quantity
                if new_quantity > 0:
                    c.execute("UPDATE portfolios SET quantity=? WHERE username=? AND market=?",
                              (new_quantity, username, selected_market))
                else:
                    c.execute(
                        "DELETE FROM portfolios WHERE username=? AND market=?", (username, selected_market))
            else:
                messagebox.showerror(
                    "Error", "You do not own enough of this item to sell")
                conn.close()
                return
        else:
            messagebox.showerror("Error", "Invalid transaction type")
            conn.close()
            return

        conn.commit()
        conn.close()
        messagebox.showinfo(
            "Transaction Complete", f"Your {transaction_type} transaction has been processed.")
        self.destroy()


class MyInvestmentWindow(tk.Toplevel, CenteredTkWindow):
    # initialization of the class
    def __init__(self, parent, username):
        super().__init__(parent)
        self.username = username
        self.title(f"{username}'s Investments")
        self.geometry("600x400")
        self.create_widgets()
        self.populate_investments()
        self.center_window()

    def create_widgets(self):
        """ GUI components - Button, Input Block, Labels"""
        self.tree = ttk.Treeview(self, columns=(
            'Market', 'Quantity', 'Amount'), show='headings')
        self.tree.heading('Market', text='Market')
        self.tree.heading('Quantity', text='Quantity')
        self.tree.heading('Amount', text='Amount')
        self.tree.pack(fill='both', expand=True)

        self.tree.column('Market', anchor='center')
        self.tree.column('Quantity', anchor='center')
        self.tree.column('Amount', anchor='center')

    def populate_investments(self):
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute(
            "SELECT market, quantity, amount FROM portfolios WHERE username=?", (self.username,))
        investments = c.fetchall()
        conn.close()

        for market, quantity, amount in investments:
            formatted_amount = f"${float(amount):.2f}"
            self.tree.insert('', 'end', values=(
                market, quantity, formatted_amount))


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
