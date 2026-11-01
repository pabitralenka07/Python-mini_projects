"""2. Bank Management System (teller console) - Tkinter + SQLite."""
from tkinter import messagebox, ttk

from bank_core import SCHEMA, Bank
from common import (Database, fill_tree, form_entries, guarded, launch, make_tree,
                    parse_number, selected_id)


class App:
    def __init__(self, root):
        self.bank = Bank(Database("bank.db", SCHEMA))
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True)
        nb.bind("<<NotebookTabChanged>>", lambda _e: self.refresh())

        # --- accounts tab ---
        tab = ttk.Frame(nb)
        nb.add(tab, text="Accounts")
        box = ttk.LabelFrame(tab, text="Open new account")
        box.pack(fill="x", padx=8, pady=6)
        self.new = form_entries(box, ["Holder name", "4-digit PIN", "Opening deposit"])
        self.new["4-digit PIN"].configure(show="*")
        ttk.Button(box, text="Open account", command=self.open_account).grid(row=3, column=1, sticky="w", pady=4)
        ttk.Button(tab, text="Unlock selected account", command=self.unlock).pack(anchor="w", padx=8)
        holder = ttk.Frame(tab)
        holder.pack(fill="both", expand=True, padx=8, pady=6)
        self.acc_tree = make_tree(holder)

        # --- transactions tab ---
        tab = ttk.Frame(nb)
        nb.add(tab, text="Transactions")
        box = ttk.LabelFrame(tab, text="Cash desk")
        box.pack(fill="x", padx=8, pady=6)
        self.tx = form_entries(box, ["Account no", "Amount", "To account (transfer only)"])
        bar = ttk.Frame(box)
        bar.grid(row=3, column=1, sticky="w", pady=6)
        for text, cmd in (("Deposit", self.deposit), ("Withdraw", self.withdraw), ("Transfer", self.transfer)):
            ttk.Button(bar, text=text, command=cmd).pack(side="left", padx=3)
        self.result = ttk.Label(tab, text="", font=("Segoe UI", 11, "bold"))
        self.result.pack(anchor="w", padx=12, pady=8)

        # --- statement tab ---
        tab = ttk.Frame(nb)
        nb.add(tab, text="Statement")
        top = ttk.Frame(tab)
        top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text="Account no").pack(side="left")
        self.st_acc = ttk.Entry(top, width=12)
        self.st_acc.pack(side="left", padx=4)
        ttk.Button(top, text="Show", command=self.statement).pack(side="left")
        holder = ttk.Frame(tab)
        holder.pack(fill="both", expand=True, padx=8, pady=6)
        self.st_tree = make_tree(holder)
        self.refresh()

    def refresh(self):
        fill_tree(self.acc_tree, ["Account", "Holder", "Balance", "Status"], self.bank.accounts())

    @guarded
    def open_account(self):
        opening = parse_number(self.new["Opening deposit"].get() or "0", "Opening deposit", float, 0)
        acc = self.bank.open_account(self.new["Holder name"].get(), self.new["4-digit PIN"].get(), opening)
        messagebox.showinfo("Account opened", f"Account number: {acc}")
        for e in self.new.values():
            e.delete(0, "end")
        self.refresh()

    @guarded
    def unlock(self):
        self.bank.unlock(selected_id(self.acc_tree, "account"))
        self.refresh()

    def _inputs(self):
        return (parse_number(self.tx["Account no"].get(), "Account no", int, 1),
                parse_number(self.tx["Amount"].get(), "Amount", float, 0.01))

    @guarded
    def deposit(self):
        acc, amt = self._inputs()
        self.result.config(text=f"Deposited {amt:.2f}. New balance: {self.bank.deposit(acc, amt):.2f}")

    @guarded
    def withdraw(self):
        acc, amt = self._inputs()
        self.result.config(text=f"Withdrew {amt:.2f}. New balance: {self.bank.withdraw(acc, amt):.2f}")

    @guarded
    def transfer(self):
        acc, amt = self._inputs()
        dst = parse_number(self.tx["To account (transfer only)"].get(), "To account", int, 1)
        self.result.config(text=f"Transferred {amt:.2f} to {dst}. New balance: {self.bank.transfer(acc, dst, amt):.2f}")

    @guarded
    def statement(self):
        acc = parse_number(self.st_acc.get(), "Account no", int, 1)
        self.bank.balance(acc)  # raises if the account does not exist
        fill_tree(self.st_tree, ["Time (UTC)", "Type", "Amount", "Balance", "Note"], self.bank.statement(acc))


if __name__ == "__main__":
    launch(App, "Bank Management System", "820x560")
