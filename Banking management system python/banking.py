import mysql.connector
from mysql.connector import Error, IntegrityError
from decimal import Decimal, InvalidOperation
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "YOUR PASSWORD",
    "database": "banking_system",
}

MAX_ACCOUNTS = 100
def connect_db():
    return mysql.connector.connect(**DB_CONFIG)
def setup_database():
    """Create the database and table if they do not exist."""
    config = DB_CONFIG.copy()
    config.pop("database", None)
    conn = mysql.connector.connect(**config)
    cur = conn.cursor()
    try:
        cur.execute(
            "CREATE DATABASE IF NOT EXISTS banking_system "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()

    conn = connect_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                account_number BIGINT PRIMARY KEY,
                customer_name VARCHAR(100) NOT NULL,
                balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
                CONSTRAINT chk_balance_nonnegative CHECK (balance >= 0)
            ) ENGINE=InnoDB
        """)
        conn.commit()
    finally:
        cur.close()
        conn.close()
def get_count(cur):
    cur.execute("SELECT COUNT(*) FROM accounts")
    return cur.fetchone()[0]
def find_account(cur, account_number):
    cur.execute(
        "SELECT account_number, customer_name, balance "
        "FROM accounts WHERE account_number = %s",
        (account_number,),
    )
    return cur.fetchone()
def input_account_number(prompt):
    try:
        number = int(input(prompt).strip())
        if number <= 0:
            raise ValueError
        return number
    except ValueError:
        print("\nInvalid account number. Enter a positive whole number.")
        return None
def input_amount(prompt):
    try:
        amount = Decimal(input(prompt).strip())
        if not amount.is_finite():
            raise InvalidOperation
        amount = amount.quantize(Decimal("0.01"))
        return amount
    except (InvalidOperation, ValueError):
        print("\nInvalid amount. Enter a valid number, for example 250.00.")
        return None
def create_account():
    name = input("\nEnter customer name: ").strip()
    if not name:
        print("\nCustomer name cannot be empty!")
        return
    amount = input_amount("Enter initial amount to be deposited: ")
    if amount is None:
        return
    if amount < 0:
        print("\nInvalid amount!")
        return
    number = input_account_number("Enter account number: ")
    if number is None:
        return
    conn = connect_db()
    cur = conn.cursor()
    try:
        if get_count(cur) >= MAX_ACCOUNTS:
            print("\nAccount storage is full!")
            return
        cur.execute(
            "INSERT INTO accounts (account_number, customer_name, balance) "
            "VALUES (%s, %s, %s)",
            (number, name, amount),
        )
        conn.commit()
        print("\nACCOUNT CREATED SUCCESSFULLY!")
        print(f"Account Number : {number}")
        print(f"Customer Name  : {name}")
        print(f"Balance        : ₹{amount:.2f}")
    except IntegrityError:
        conn.rollback()
        print("\nAccount number already exists!")
    finally:
        cur.close()
        conn.close()
def deposit_money():
    number = input_account_number("\nEnter account number: ")
    if number is None:
        return
    amount = input_amount("Enter amount to be deposited: ")
    if amount is None:
        return
    if amount <= 0:
        print("\nInvalid amount!")
        return
    conn = connect_db()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE accounts SET balance = balance + %s "
            "WHERE account_number = %s",
            (amount, number),
        )
        if cur.rowcount == 0:
            print("\nAccount not found!")
            return
        conn.commit()
        account = find_account(cur, number)
        print("\nAMOUNT DEPOSITED SUCCESSFULLY!")
        print(f"Updated Balance : ₹{Decimal(account[2]):.2f}")
    except Error:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
def withdraw_money():
    number = input_account_number("\nEnter account number: ")
    if number is None:
        return
    amount = input_amount("Enter amount to withdraw: ")
    if amount is None:
        return
    if amount <= 0:
        print("\nInvalid amount!")
        return
    conn = connect_db()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE accounts SET balance = balance - %s "
            "WHERE account_number = %s AND balance >= %s",
            (amount, number, amount),
        )
        if cur.rowcount == 0:
            if find_account(cur, number):
                print("\nInsufficient Balance!")
            else:
                print("\nAccount not found!")
            return
        conn.commit()
        account = find_account(cur, number)
        print("\nAMOUNT WITHDRAWN SUCCESSFULLY!")
        print(f"Updated Balance : ₹{Decimal(account[2]):.2f}")
    except Error:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
def transfer_money():
    sender = input_account_number("\nEnter sender's account number: ")
    if sender is None:
        return
    receiver = input_account_number("Enter receiver's account number: ")
    if receiver is None:
        return
    amount = input_amount("Enter amount to transfer: ")
    if amount is None:
        return
    if sender == receiver:
        print("\nSender and receiver cannot be same!")
        return
    if amount <= 0:
        print("\nInvalid amount! Please enter a valid amount.")
        return
    conn = connect_db()
    cur = conn.cursor()
    try:
        ordered = sorted((sender, receiver))
        cur.execute(
            "SELECT account_number, balance FROM accounts "
            "WHERE account_number IN (%s, %s) "
            "ORDER BY account_number FOR UPDATE",
            (ordered[0], ordered[1]),
        )
        rows = cur.fetchall()
        balances = {row[0]: Decimal(row[1]) for row in rows}

        if sender not in balances:
            conn.rollback()
            print("\nSender account not found!")
            return
        if receiver not in balances:
            conn.rollback()
            print("\nReceiver account not found!")
            return
        if amount > balances[sender]:
            conn.rollback()
            print("\nInsufficient Balance!")
            return
        cur.execute(
            "UPDATE accounts SET balance = balance - %s "
            "WHERE account_number = %s",
            (amount, sender),
        )
        cur.execute(
            "UPDATE accounts SET balance = balance + %s "
            "WHERE account_number = %s",
            (amount, receiver),
        )
        conn.commit()
        sender_account = find_account(cur, sender)
        print("\nAMOUNT TRANSFERRED SUCCESSFULLY!")
        print(f"Transferred Amount : ₹{amount:.2f}")
        print(f"Receiver's Account Number : {receiver}")
        print(f"Remaining Balance : ₹{Decimal(sender_account[2]):.2f}")
    except Error:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
def display_account():
    number = input_account_number("\nEnter account number: ")
    if number is None:
        return
    conn = connect_db()
    cur = conn.cursor()
    try:
        account = find_account(cur, number)
        if account is None:
            print("\nAccount not found!")
            return
        print("\n========== ACCOUNT DETAILS ==========")
        print(f"Account Number : {account[0]}")
        print(f"Customer Name  : {account[1]}")
        print(f"Balance        : ₹{Decimal(account[2]):.2f}")
        print("=====================================")
    finally:
        cur.close()
        conn.close()
def display_all_accounts():
    conn = connect_db()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT account_number, customer_name, balance "
            "FROM accounts ORDER BY account_number"
        )
        accounts = cur.fetchall()
        if not accounts:
            print("\nNo accounts available!")
            return
        print("\n========== ALL ACCOUNTS ==========")
        for index, account in enumerate(accounts, start=1):
            print(f"\nAccount {index}")
            print("---------------------------------")
            print(f"Account Number : {account[0]}")
            print(f"Customer Name  : {account[1]}")
            print(f"Balance        : ₹{Decimal(account[2]):.2f}")
        print("=================================")
    finally:
        cur.close()
        conn.close()
def delete_account():
    number = input_account_number("\nEnter account number to delete: ")
    if number is None:
        return
    confirm = input(
        "Delete this account permanently? Type YES to confirm: "
    ).strip()
    if confirm != "YES":
        print("Deletion cancelled.")
        return
    conn = connect_db()
    cur = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM accounts WHERE account_number = %s",
            (number,),
        )
        if cur.rowcount == 0:
            print("\nAccount not found!")
            return
        conn.commit()
        print("\nACCOUNT DELETED SUCCESSFULLY!")
    except Error:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
def main():
    try:
        setup_database()
        print("MySQL connected successfully.")
        while True:
            print("\n\n========== BANKING MANAGEMENT SYSTEM ==========")
            print("1. Create Account")
            print("2. Deposit Money")
            print("3. Withdraw Money")
            print("4. Transfer Money")
            print("5. Check Balance")
            print("6. Display All Accounts")
            print("7. Delete Account")
            print("8. Exit")

            choice = input("\nEnter your choice: ").strip()
            try:
                if choice == "1":
                    create_account()
                elif choice == "2":
                    deposit_money()
                elif choice == "3":
                    withdraw_money()
                elif choice == "4":
                    transfer_money()
                elif choice == "5":
                    display_account()
                elif choice == "6":
                    display_all_accounts()
                elif choice == "7":
                    delete_account()
                elif choice == "8":
                    print("\nThank you for using Banking Management System!")
                    break
                else:
                    print("\nInvalid choice! Please try again.")
            except Error as error:
                print(f"\nMySQL error: {error}")
                print("Check your MySQL settings and make sure the server is running.")
    except Error as error:
        print(f"\nCould not connect to MySQL: {error}")
        print("Check DB_CONFIG password and confirm MySQL Server is running.")
    except (EOFError, KeyboardInterrupt):
        print("\n\nProgram closed.")
if __name__ == "__main__":
    main()
