"""3. ATM Management System - card + PIN login, lockout, limits. Shares bank.db with app 2."""
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from bank_core import SCHEMA, Bank, BankError
from common import Database, guarded, launch, parse_number


class ATMSession:
    DAILY_LIMIT = 20000
    NOTE_MULTIPLE = 100

    def __init__(self, bank, acc_no):
        self.bank, self.acc_no = bank, acc_no

    def withdraw(self, amount):
        if amount <= 0 or amount % self.NOTE_MULTIPLE:
            raise BankError(f"Amount must be a positive multiple of {self.NOTE_MULTIPLE}")
        used = self.bank.db.one(
            "SELECT COALESCE(SUM(amount),0) AS s FROM transactions "
            "WHERE acc_no=? AND kind='ATM Withdrawal' AND date(ts)=date('now')", (self.acc_no,))["s"]
        if used + amount > self.DAILY_LIMIT:
            raise BankError(f"Daily limit {self.DAILY_LIMIT} exceeded (already withdrawn {used:.0f})")
        return self.bank.withdraw(self.acc_no, amount, kind="ATM Withdrawal")


class App:
    def __init__(self, root):
        self.root = root
        self.bank = Bank(Database("bank.db", SCHEMA))
        if not self.bank.accounts():
            acc = self.bank.open_account("Demo User", "1234", 5000)
            self.demo = f"First run: demo account {acc}, PIN 1234"
        else:
            self.demo = ""
        self.frame = ttk.Frame(root, padding=20)
        self.frame.pack(fill="both", expand=True)
        self.session = None
        self.show_login()

    def _reset(self):
        for w in self.frame.winfo_children():
            w.destroy()

    def show_login(self):
        self._reset()
        self.session = None
        ttk.Label(self.frame, text="WELCOME TO THE ATM", font=("Segoe UI", 18, "bold")).pack(pady=15)
        ttk.Label(self.frame, text="Account / card number").pack()
        self.acc = ttk.Entry(self.frame, width=20)
        self.acc.pack(pady=4)
        ttk.Label(self.frame, text="PIN").pack()
        self.pin = ttk.Entry(self.frame, width=20, show="*")
        self.pin.pack(pady=4)
        self.pin.bind("<Return>", lambda _e: self.login())
        ttk.Button(self.frame, text="Insert card / Login", command=self.login).pack(pady=10)
        ttk.Label(self.frame, text=self.demo, foreground="gray").pack()

    @guarded
    def login(self):
        acc = parse_number(self.acc.get(), "Account number", int, 1)
        holder = self.bank.authenticate(acc, self.pin.get())
        self.session = ATMSession(self.bank, acc)
        self.show_menu(holder)

    def show_menu(self, holder):
        self._reset()
        ttk.Label(self.frame, text=f"Hello, {holder}", font=("Segoe UI", 16, "bold")).pack(pady=10)
        grid = ttk.Frame(self.frame)
        grid.pack()
        actions = [("Balance", self.balance), ("Withdraw", self.withdraw), ("Deposit", self.deposit),
                   ("Mini statement", self.mini), ("Change PIN", self.change_pin), ("Exit", self.show_login)]
        for i, (text, cmd) in enumerate(actions):
            ttk.Button(grid, text=text, width=18, command=cmd).grid(row=i // 2, column=i % 2, padx=6, pady=6)
        self.out = tk.Text(self.frame, height=12, width=60, state="disabled", font=("Consolas", 10))
        self.out.pack(pady=10)

    def show(self, text):
        self.out.config(state="normal")
        self.out.delete("1.0", "end")
        self.out.insert("1.0", text)
        self.out.config(state="disabled")

    @guarded
    def balance(self):
        self.show(f"Available balance: {self.bank.balance(self.session.acc_no):.2f}")

    @guarded
    def withdraw(self):
        amt = simpledialog.askinteger("Withdraw", "Amount (multiples of 100):", parent=self.root, minvalue=1)
        if amt:
            self.show(f"Please collect your cash: {amt}\nBalance: {self.session.withdraw(amt):.2f}")

    @guarded
    def deposit(self):
        amt = simpledialog.askfloat("Deposit", "Amount:", parent=self.root, minvalue=0.01)
        if amt:
            self.show(f"Deposited {amt:.2f}\nBalance: {self.bank.deposit(self.session.acc_no, amt, 'ATM Deposit'):.2f}")

    @guarded
    def mini(self):
        rows = self.bank.statement(self.session.acc_no, 5)
        self.show("\n".join(f"{r[0]}  {r[1]:<14}{r[2]:>10.2f}  bal {r[3]:.2f}" for r in rows) or "No transactions")

    @guarded
    def change_pin(self):
        old = simpledialog.askstring("Change PIN", "Current PIN:", show="*", parent=self.root)
        new = simpledialog.askstring("Change PIN", "New 4-digit PIN:", show="*", parent=self.root) if old else None
        if old and new:
            self.bank.change_pin(self.session.acc_no, old, new)
            messagebox.showinfo("Done", "PIN changed")


if __name__ == "__main__":
    launch(App, "ATM", "560x560")
