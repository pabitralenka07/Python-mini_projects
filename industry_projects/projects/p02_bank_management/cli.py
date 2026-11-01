"""CLI interface for Bank Management System.

================================================================================
Concepts used:
1. Object-Oriented Polymorphism: SavingsAccount and CurrentAccount enforce
   different withdrawal rules polymorphically via a shared Account base class.
2. Atomic Database Transactions: Multi-step transfers run within a single SQLite
   transaction (`with conn:`), guaranteeing that either both accounts update or
   neither does.
3. Integer-Cents Financial Math: All currency operations avoid float inaccuracies
   by operating strictly on integer minor units (cents).
================================================================================
"""

from pathlib import Path

from common.input_helpers import (
    UserExitException,
    confirm_action,
    prompt_choice,
    prompt_int,
    safe_input,
)
from common.money import cents_to_display, parse_money_to_cents
from common.tables import format_table
from projects.p02_bank_management.models import CurrentAccount, SavingsAccount
from projects.p02_bank_management.repository import BankRepository
from projects.p02_bank_management.service import (
    BankError,
    BankService,
)


def get_default_service() -> BankService:
    db_path = Path(__file__).resolve().parent / "data" / "bank.db"
    repo = BankRepository.from_path(db_path)
    return BankService(repo)


def display_menu() -> None:
    print("\n" + "=" * 45)
    print("         BANK MANAGEMENT SYSTEM              ")
    print("=" * 45)
    print(" 1. Register Customer")
    print(" 2. Open Account (Savings / Current)")
    print(" 3. Deposit Funds")
    print(" 4. Withdraw Funds")
    print(" 5. Transfer Funds (Atomic)")
    print(" 6. View Account Statement")
    print(" 7. List Customers & Accounts")
    print(" 8. Close Account")
    print(" 0. Exit")
    print("=" * 45)


def run_cli(service: BankService | None = None) -> None:
    if service is None:
        service = get_default_service()

    while True:
        try:
            display_menu()
            choice = prompt_int("Enter option (0-8)", min_val=0, max_val=8)
        except UserExitException:
            print("\nGoodbye! Exiting Bank Management System.")
            break

        if choice == 0:
            print("\nGoodbye! Exiting Bank Management System.")
            break

        try:
            if choice == 1:
                _handle_register_customer(service)
            elif choice == 2:
                _handle_open_account(service)
            elif choice == 3:
                _handle_deposit(service)
            elif choice == 4:
                _handle_withdraw(service)
            elif choice == 5:
                _handle_transfer(service)
            elif choice == 6:
                _handle_statement(service)
            elif choice == 7:
                _handle_list(service)
            elif choice == 8:
                _handle_close_account(service)
        except UserExitException:
            print("\nReturning to main menu...")
        except BankError as err:
            print(f"\n[Bank Error] {err}")
        except ValueError as err:
            print(f"\n[Validation Error] {err}")
        except Exception as err:
            print(f"\n[Unexpected Error] {err}")


def _handle_register_customer(service: BankService) -> None:
    print("\n--- Register New Customer ---")
    name = safe_input("Enter Customer Name: ")
    email = safe_input("Enter Customer Email: ")
    customer = service.register_customer(name, email)
    print(f"\nSuccess: Customer '{customer.name}' registered with ID {customer.id}!")


def _handle_open_account(service: BankService) -> None:
    print("\n--- Open Bank Account ---")
    cust_id = prompt_int("Enter Customer ID", min_val=1)
    acc_type = prompt_choice("Select Account Type", ["SAVINGS", "CURRENT"])

    if acc_type == "SAVINGS":
        print("Note: Savings account requires minimum opening deposit of $50.00.")
    else:
        print("Note: Current account includes an overdraft limit of $500.00.")

    dep_str = safe_input("Enter Initial Deposit (e.g., $100.00): ")
    deposit_cents = parse_money_to_cents(dep_str)

    account = service.open_account(
        customer_id=cust_id, account_type=acc_type, initial_deposit_cents=deposit_cents
    )
    bal_str = cents_to_display(account.balance_cents)
    print(
        f"\nSuccess: {account.account_type} Account opened! "
        f"Account Number: {account.account_number} | Balance: {bal_str}"
    )


def _handle_deposit(service: BankService) -> None:
    print("\n--- Deposit Funds ---")
    acc_num = safe_input("Enter Account Number: ")
    amt_str = safe_input("Enter Deposit Amount: ")
    cents = parse_money_to_cents(amt_str)

    new_bal = service.deposit(acc_num, cents)
    print(f"\nDeposit Successful! New Balance: {cents_to_display(new_bal)}")


def _handle_withdraw(service: BankService) -> None:
    print("\n--- Withdraw Funds ---")
    acc_num = safe_input("Enter Account Number: ")
    amt_str = safe_input("Enter Withdrawal Amount: ")
    cents = parse_money_to_cents(amt_str)

    new_bal = service.withdraw(acc_num, cents)
    print(f"\nWithdrawal Successful! New Balance: {cents_to_display(new_bal)}")


def _handle_transfer(service: BankService) -> None:
    print("\n--- Transfer Funds (Single Transaction) ---")
    src = safe_input("Source Account Number: ")
    dst = safe_input("Destination Account Number: ")
    amt_str = safe_input("Transfer Amount: ")
    cents = parse_money_to_cents(amt_str)

    src_bal, dst_bal = service.transfer(src, dst, cents)
    print(
        f"\nTransfer Successful!\n"
        f"  Source ({src}) Balance: {cents_to_display(src_bal)}\n"
        f"  Destination ({dst}) Balance: {cents_to_display(dst_bal)}"
    )


def _handle_statement(service: BankService) -> None:
    print("\n--- Account Statement ---")
    acc_num = safe_input("Enter Account Number: ")
    account = service.get_account(acc_num)
    records = service.get_statement(acc_num)

    print(
        f"\nAccount: {account.account_number} | Type: {account.account_type} | "
        f"Current Balance: {cents_to_display(account.balance_cents)} | Status: {account.status}"
    )

    headers = ["ID", "Type", "Amount", "Balance After", "Ref Account", "Timestamp"]
    rows = [
        [
            r.id,
            r.transaction_type,
            cents_to_display(r.amount_cents),
            cents_to_display(r.balance_after_cents),
            r.reference_account or "-",
            r.timestamp,
        ]
        for r in records
    ]
    alignments = ["R", "L", "R", "R", "L", "L"]
    print(format_table(headers, rows, alignments))


def _handle_list(service: BankService) -> None:
    print("\n--- All Customers & Accounts ---")
    customers = service.list_customers()
    accounts = service.list_all_accounts()

    print("\n[Customers]")
    c_headers = ["ID", "Name", "Email", "Registered"]
    c_rows = [[c.id, c.name, c.email, c.created_at] for c in customers]
    print(format_table(c_headers, c_rows, ["R", "L", "L", "L"]))

    print("\n[Accounts]")
    a_headers = ["Account No", "Customer ID", "Type", "Balance", "Special Rule", "Status"]
    a_rows = []
    for a in accounts:
        if isinstance(a, SavingsAccount):
            rule_desc = f"Min Bal {cents_to_display(a.minimum_balance_cents)}"
        elif isinstance(a, CurrentAccount):
            rule_desc = f"Overdraft {cents_to_display(a.overdraft_limit_cents)}"
        else:
            rule_desc = "-"
        a_rows.append(
            [
                a.account_number,
                a.customer_id,
                a.account_type,
                cents_to_display(a.balance_cents),
                rule_desc,
                a.status,
            ]
        )
    print(format_table(a_headers, a_rows, ["L", "R", "L", "R", "L", "L"]))


def _handle_close_account(service: BankService) -> None:
    print("\n--- Close Account ---")
    acc_num = safe_input("Enter Account Number to close: ")
    if not confirm_action(f"Are you sure you want to permanently close account {acc_num}?"):
        print("Closure cancelled.")
        return

    service.close_account(acc_num)
    print(f"\nSuccess: Account {acc_num} has been closed.")
