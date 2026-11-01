"""Level 2 Tkinter GUI Application for Electricity Bill Management System."""

import contextlib
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from common.money import cents_to_display
from projects.p09_electricity_bill.models import BillDetail, Consumer
from projects.p09_electricity_bill.repository import ElectricityRepository
from projects.p09_electricity_bill.service import (
    BillAlreadyPaidError,
    BillNotFoundError,
    ElectricityError,
    ElectricityService,
    NonMonotonicReadingError,
)


class ElectricityBillApp:
    """Rich GUI for customer meter reading, slab bill calculation, and invoice settlement."""

    def __init__(self, root: tk.Tk, service: ElectricityService | None = None) -> None:
        self.root = root
        self.root.title("Electricity Utility Management System")
        self.root.geometry("980x680")
        self.root.minsize(850, 580)

        if service is None:
            db_path = Path(__file__).resolve().parent / "data" / "electricity.db"
            repo = ElectricityRepository.from_path(db_path)
            self.service = ElectricityService(repo)
        else:
            self.service = service

        self._configure_styles()
        self._build_ui()
        self._refresh_all_data()

    def _configure_styles(self) -> None:
        style = ttk.Style()
        with contextlib.suppress(tk.TclError):
            style.theme_use("clam")

        # Color palette
        self.bg_color = "#f8fafc"
        self.card_bg = "#ffffff"
        self.primary_color = "#0284c7"
        self.header_bg = "#0f172a"
        self.text_color = "#1e293b"

        self.root.configure(bg=self.bg_color)

        style.configure("TNotebook", background=self.bg_color, tabmargins=[4, 4, 4, 0])
        style.configure(
            "TNotebook.Tab",
            font=("Helvetica", 10, "bold"),
            padding=[16, 6],
            background="#e2e8f0",
            foreground=self.text_color,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.primary_color)],
            foreground=[("selected", "#ffffff")],
        )

        style.configure("Treeview", rowheight=26, font=("Helvetica", 9))
        style.configure(
            "Treeview.Heading",
            font=("Helvetica", 9, "bold"),
            background="#e2e8f0",
            foreground=self.text_color,
        )

        style.configure("Action.TButton", font=("Helvetica", 9, "bold"), padding=6)
        style.configure(
            "Primary.TButton",
            font=("Helvetica", 9, "bold"),
            background=self.primary_color,
            foreground="#ffffff",
            padding=6,
        )

    def _build_ui(self) -> None:
        # 1. Header Frame
        header = tk.Frame(self.root, bg=self.header_bg, height=60)
        header.pack(fill=tk.X, side=tk.TOP)

        title = tk.Label(
            header,
            text="POWERGRID ELECTRICITY UTILITY - BILLING & METERING",
            font=("Helvetica", 13, "bold"),
            bg=self.header_bg,
            fg="#f8fafc",
            pady=12,
            padx=16,
        )
        title.pack(side=tk.LEFT)

        # 2. Main Tabbed Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        # Tab 1: Billing & Meter Entry
        self.tab_billing = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_billing, text="  Meter Reading & Billing  ")
        self._build_billing_tab()

        # Tab 2: Consumers Directory
        self.tab_consumers = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_consumers, text="  Consumers Directory  ")
        self._build_consumers_tab()

        # Tab 3: Invoice History
        self.tab_invoices = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_invoices, text="  Invoice History & Settle  ")
        self._build_invoices_tab()

        # 3. Status Bar
        self.status_var = tk.StringVar(value="System Ready.")
        status_bar = tk.Label(
            self.root,
            textvariable=self.status_var,
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            font=("Helvetica", 9),
            bg="#e2e8f0",
            fg="#475569",
            padx=8,
            pady=3,
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # --- Tab 1: Billing & Meter Reading ---

    def _build_billing_tab(self) -> None:
        paned = ttk.PanedWindow(self.tab_billing, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Left Column: Input Form
        left_frame = ttk.LabelFrame(paned, text=" Meter Reading Submission ", padding=10)
        paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Select Consumer:").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.consumer_combo = ttk.Combobox(left_frame, state="readonly", width=30)
        self.consumer_combo.grid(row=0, column=1, sticky=tk.EW, pady=4)
        self.consumer_combo.bind("<<ComboboxSelected>>", self._on_consumer_selected)

        ttk.Label(left_frame, text="Meter Number:").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.lbl_meter_no = ttk.Label(left_frame, text="--", font=("Helvetica", 9, "bold"))
        self.lbl_meter_no.grid(row=1, column=1, sticky=tk.W, pady=4)

        ttk.Label(left_frame, text="Tariff Category:").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.lbl_tariff_cat = ttk.Label(left_frame, text="--", font=("Helvetica", 9, "bold"))
        self.lbl_tariff_cat.grid(row=2, column=1, sticky=tk.W, pady=4)

        ttk.Label(left_frame, text="Previous Reading (kWh):").grid(
            row=3, column=0, sticky=tk.W, pady=4
        )
        self.lbl_prev_reading = ttk.Label(
            left_frame, text="--", font=("Helvetica", 10, "bold"), foreground="#0369a1"
        )
        self.lbl_prev_reading.grid(row=3, column=1, sticky=tk.W, pady=4)

        ttk.Label(left_frame, text="Current Reading (kWh):").grid(
            row=4, column=0, sticky=tk.W, pady=4
        )
        self.ent_curr_reading = ttk.Entry(left_frame, width=15)
        self.ent_curr_reading.grid(row=4, column=1, sticky=tk.W, pady=4)

        btn_generate = ttk.Button(
            left_frame,
            text="Calculate & Generate Bill",
            style="Primary.TButton",
            command=self._handle_generate_bill,
        )
        btn_generate.grid(row=5, column=0, columnspan=2, pady=12, sticky=tk.EW)

        # Right Column: Itemized Invoice Preview
        right_frame = ttk.LabelFrame(paned, text=" Itemized Invoice Preview ", padding=10)
        paned.add(right_frame, weight=2)

        self.txt_bill_preview = tk.Text(
            right_frame,
            wrap=tk.WORD,
            font=("Courier", 10),
            bg="#fdfefe",
            fg="#0f172a",
            padx=10,
            pady=10,
        )
        self.txt_bill_preview.pack(fill=tk.BOTH, expand=True)
        self.txt_bill_preview.insert(
            tk.END, "Select a consumer and enter current reading to preview bill.\n"
        )
        self.txt_bill_preview.config(state=tk.DISABLED)

    # --- Tab 2: Consumers Directory ---

    def _build_consumers_tab(self) -> None:
        paned = ttk.PanedWindow(self.tab_consumers, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Left: Register Consumer Form
        left_frame = ttk.LabelFrame(paned, text=" Register New Consumer ", padding=10)
        paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Consumer # (e.g. CON-101):").grid(
            row=0, column=0, sticky=tk.W, pady=4
        )
        self.ent_new_cnum = ttk.Entry(left_frame, width=22)
        self.ent_new_cnum.grid(row=0, column=1, pady=4, sticky=tk.EW)

        ttk.Label(left_frame, text="Full Name:").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.ent_new_name = ttk.Entry(left_frame, width=22)
        self.ent_new_name.grid(row=1, column=1, pady=4, sticky=tk.EW)

        ttk.Label(left_frame, text="Service Address:").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.ent_new_addr = ttk.Entry(left_frame, width=22)
        self.ent_new_addr.grid(row=2, column=1, pady=4, sticky=tk.EW)

        ttk.Label(left_frame, text="Meter # (e.g. MTR-901):").grid(
            row=3, column=0, sticky=tk.W, pady=4
        )
        self.ent_new_meter = ttk.Entry(left_frame, width=22)
        self.ent_new_meter.grid(row=3, column=1, pady=4, sticky=tk.EW)

        ttk.Label(left_frame, text="Tariff Category:").grid(row=4, column=0, sticky=tk.W, pady=4)
        self.combo_new_cat = ttk.Combobox(
            left_frame, state="readonly", values=["RESIDENTIAL", "COMMERCIAL"], width=20
        )
        self.combo_new_cat.set("RESIDENTIAL")
        self.combo_new_cat.grid(row=4, column=1, pady=4, sticky=tk.EW)

        ttk.Label(left_frame, text="Initial Reading (kWh):").grid(
            row=5, column=0, sticky=tk.W, pady=4
        )
        self.ent_new_reading = ttk.Entry(left_frame, width=22)
        self.ent_new_reading.insert(0, "0")
        self.ent_new_reading.grid(row=5, column=1, pady=4, sticky=tk.EW)

        btn_add_consumer = ttk.Button(
            left_frame,
            text="Register Consumer",
            style="Primary.TButton",
            command=self._handle_add_consumer,
        )
        btn_add_consumer.grid(row=6, column=0, columnspan=2, pady=12, sticky=tk.EW)

        # Right: Treeview of Consumers
        right_frame = ttk.LabelFrame(paned, text=" Registered Consumers ", padding=10)
        paned.add(right_frame, weight=3)

        cols = ("id", "cnum", "name", "meter", "cat", "addr")
        self.tree_consumers = ttk.Treeview(right_frame, columns=cols, show="headings")
        self.tree_consumers.heading("id", text="ID")
        self.tree_consumers.heading("cnum", text="Consumer #")
        self.tree_consumers.heading("name", text="Full Name")
        self.tree_consumers.heading("meter", text="Meter #")
        self.tree_consumers.heading("cat", text="Category")
        self.tree_consumers.heading("addr", text="Address")

        self.tree_consumers.column("id", width=40, anchor=tk.CENTER)
        self.tree_consumers.column("cnum", width=90)
        self.tree_consumers.column("name", width=140)
        self.tree_consumers.column("meter", width=90)
        self.tree_consumers.column("cat", width=90)
        self.tree_consumers.column("addr", width=160)

        sb = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.tree_consumers.yview)
        self.tree_consumers.configure(yscrollcommand=sb.set)
        self.tree_consumers.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

    # --- Tab 3: Invoices History & Settle ---

    def _build_invoices_tab(self) -> None:
        toolbar = ttk.Frame(self.tab_invoices, padding=6)
        toolbar.pack(fill=tk.X)

        btn_pay = ttk.Button(
            toolbar,
            text="Settle / Pay Selected Invoice",
            style="Primary.TButton",
            command=self._handle_pay_selected_bill,
        )
        btn_pay.pack(side=tk.LEFT, padx=6)

        btn_refresh = ttk.Button(
            toolbar,
            text="Refresh Invoices",
            style="Action.TButton",
            command=self._refresh_invoices_tree,
        )
        btn_refresh.pack(side=tk.LEFT, padx=6)

        # Invoices Treeview
        tree_frame = ttk.Frame(self.tab_invoices, padding=6)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = (
            "id",
            "bnum",
            "consumer",
            "units",
            "energy",
            "fixed",
            "tax",
            "total",
            "due",
            "status",
        )
        self.tree_invoices = ttk.Treeview(tree_frame, columns=cols, show="headings")
        self.tree_invoices.heading("id", text="ID")
        self.tree_invoices.heading("bnum", text="Bill #")
        self.tree_invoices.heading("consumer", text="Consumer")
        self.tree_invoices.heading("units", text="Units")
        self.tree_invoices.heading("energy", text="Energy")
        self.tree_invoices.heading("fixed", text="Fixed")
        self.tree_invoices.heading("tax", text="Tax")
        self.tree_invoices.heading("total", text="Total Due")
        self.tree_invoices.heading("due", text="Due Date")
        self.tree_invoices.heading("status", text="Status")

        self.tree_invoices.column("id", width=40, anchor=tk.CENTER)
        self.tree_invoices.column("bnum", width=160)
        self.tree_invoices.column("consumer", width=130)
        self.tree_invoices.column("units", width=70, anchor=tk.E)
        self.tree_invoices.column("energy", width=75, anchor=tk.E)
        self.tree_invoices.column("fixed", width=65, anchor=tk.E)
        self.tree_invoices.column("tax", width=65, anchor=tk.E)
        self.tree_invoices.column("total", width=85, anchor=tk.E)
        self.tree_invoices.column("due", width=90, anchor=tk.CENTER)
        self.tree_invoices.column("status", width=75, anchor=tk.CENTER)

        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_invoices.yview)
        self.tree_invoices.configure(yscrollcommand=sb.set)
        self.tree_invoices.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

    # --- Event Handlers & Data Refresh ---

    def _refresh_all_data(self) -> None:
        self._refresh_consumers()
        self._refresh_invoices_tree()

    def _refresh_consumers(self) -> None:
        consumers = self.service.list_consumers()
        self.consumers_map: dict[str, Consumer] = {}
        combo_vals: list[str] = []

        for item in self.tree_consumers.get_children():
            self.tree_consumers.delete(item)

        for c in consumers:
            key = f"{c.consumer_number} - {c.name}"
            self.consumers_map[key] = c
            combo_vals.append(key)

            self.tree_consumers.insert(
                "",
                tk.END,
                values=(
                    c.id,
                    c.consumer_number,
                    c.name,
                    c.meter_number,
                    c.tariff_category,
                    c.address,
                ),
            )

        self.consumer_combo["values"] = combo_vals
        if combo_vals and not self.consumer_combo.get():
            self.consumer_combo.current(0)
            self._on_consumer_selected()

    def _on_consumer_selected(self, _event: object = None) -> None:
        selected_key = self.consumer_combo.get()
        consumer = self.consumers_map.get(selected_key)
        if not consumer or consumer.id is None:
            return

        self.lbl_meter_no.config(text=consumer.meter_number)
        self.lbl_tariff_cat.config(text=consumer.tariff_category)

        latest = self.service.repo.get_latest_meter_reading(consumer.id)
        prev_val = latest.reading_value if latest else 0
        self.lbl_prev_reading.config(text=f"{prev_val} kWh")

    def _handle_generate_bill(self) -> None:
        selected_key = self.consumer_combo.get()
        consumer = self.consumers_map.get(selected_key)
        if not consumer or consumer.id is None:
            messagebox.showwarning("Selection Required", "Please select a consumer.")
            return

        curr_str = self.ent_curr_reading.get().strip()
        try:
            curr_val = int(curr_str)
        except ValueError:
            messagebox.showerror("Invalid Input", "Current reading must be a whole integer.")
            return

        try:
            bill = self.service.generate_bill(consumer.id, curr_val)
            self.status_var.set(f"Bill #{bill.bill_number} generated successfully.")
            self._display_bill_preview(bill.id or 0)
            self._refresh_invoices_tree()
            self._on_consumer_selected()
            self.ent_curr_reading.delete(0, tk.END)
            messagebox.showinfo("Success", f"Bill #{bill.bill_number} generated!")
        except (NonMonotonicReadingError, ElectricityError) as e:
            messagebox.showerror("Billing Error", str(e))

    def _display_bill_preview(self, bill_id: int) -> None:
        detail: BillDetail = self.service.get_bill_detail(bill_id)
        self.txt_bill_preview.config(state=tk.NORMAL)
        self.txt_bill_preview.delete("1.0", tk.END)

        lines = [
            "=" * 44,
            "     POWERGRID ELECTRICITY INVOICE      ",
            "=" * 44,
            f"Bill Number    : {detail.bill_number}",
            f"Status         : {detail.status}",
            f"Consumer       : {detail.consumer_name} ({detail.consumer_number})",
            f"Meter Number   : {detail.meter_number}",
            f"Tariff         : {detail.tariff_category}",
            "-" * 44,
            f"Previous Read  : {detail.previous_reading} kWh",
            f"Current Read   : {detail.current_reading} kWh",
            f"Total Units    : {detail.units_consumed} kWh",
            "-" * 44,
            "Slab Breakdown :",
        ]

        for s in detail.slabs:
            rate_d = cents_to_display(s.rate_per_unit_cents)
            amt_d = cents_to_display(s.amount_cents)
            lines.append(f"  * {s.slab_label:<14} : {s.units_in_slab:>3} kWh @ {rate_d} = {amt_d}")

        lines.extend(
            [
                "-" * 44,
                f"Energy Charges : {cents_to_display(detail.energy_charge_cents)}",
                f"Fixed Service  : {cents_to_display(detail.fixed_charge_cents)}",
                f"Utility Tax 5% : {cents_to_display(detail.tax_cents)}",
                f"TOTAL DUE      : {cents_to_display(detail.total_cents)}",
                f"Due Date       : {detail.due_date}",
                "=" * 44,
            ]
        )

        self.txt_bill_preview.insert(tk.END, "\n".join(lines) + "\n")
        self.txt_bill_preview.config(state=tk.DISABLED)

    def _handle_add_consumer(self) -> None:
        cnum = self.ent_new_cnum.get().strip()
        name = self.ent_new_name.get().strip()
        addr = self.ent_new_addr.get().strip()
        meter = self.ent_new_meter.get().strip()
        cat = self.combo_new_cat.get()
        read_str = self.ent_new_reading.get().strip()

        if not cnum or not name or not addr or not meter:
            messagebox.showerror("Missing Information", "All consumer fields are required.")
            return

        try:
            init_val = int(read_str)
        except ValueError:
            messagebox.showerror("Invalid Input", "Initial meter reading must be an integer.")
            return

        try:
            self.service.register_consumer(cnum, name, addr, meter, cat, init_val)
            self._refresh_consumers()
            self.status_var.set(f"Consumer {cnum} registered.")
            self.ent_new_cnum.delete(0, tk.END)
            self.ent_new_name.delete(0, tk.END)
            self.ent_new_addr.delete(0, tk.END)
            self.ent_new_meter.delete(0, tk.END)
            self.ent_new_reading.delete(0, tk.END)
            self.ent_new_reading.insert(0, "0")
            messagebox.showinfo("Success", f"Consumer {name} ({cnum}) registered!")
        except Exception as e:
            messagebox.showerror("Registration Error", str(e))

    def _refresh_invoices_tree(self) -> None:
        for item in self.tree_invoices.get_children():
            self.tree_invoices.delete(item)

        bills = self.service.list_all_bills()
        for b in bills:
            self.tree_invoices.insert(
                "",
                tk.END,
                values=(
                    b.bill_id,
                    b.bill_number,
                    b.consumer_name,
                    b.units_consumed,
                    cents_to_display(b.energy_charge_cents),
                    cents_to_display(b.fixed_charge_cents),
                    cents_to_display(b.tax_cents),
                    cents_to_display(b.total_cents),
                    b.due_date,
                    b.status,
                ),
            )

    def _handle_pay_selected_bill(self) -> None:
        sel = self.tree_invoices.selection()
        if not sel:
            messagebox.showwarning("Selection Required", "Select an invoice to settle.")
            return

        item = self.tree_invoices.item(sel[0])
        bill_id = int(item["values"][0])
        bill_num = item["values"][1]
        status = item["values"][9]

        if status == "PAID":
            messagebox.showinfo("Already Paid", f"Invoice #{bill_num} is already settled.")
            return

        if not messagebox.askyesno("Confirm Payment", f"Settle invoice #{bill_num}?"):
            return

        try:
            self.service.pay_bill(bill_id)
            self.status_var.set(f"Invoice #{bill_num} marked as PAID.")
            self._refresh_invoices_tree()
            messagebox.showinfo("Payment Successful", f"Invoice #{bill_num} settled!")
        except (BillNotFoundError, BillAlreadyPaidError, ElectricityError) as e:
            messagebox.showerror("Payment Error", str(e))


def run_gui(service: ElectricityService | None = None) -> None:
    root = tk.Tk()
    _app = ElectricityBillApp(root, service=service)
    root.mainloop()


if __name__ == "__main__":
    run_gui()
