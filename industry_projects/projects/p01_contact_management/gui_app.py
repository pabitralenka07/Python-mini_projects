"""Level 2 Tkinter GUI application for Contact Management System.

================================================================================
Concepts used:
1. Reusable Controller Pattern: ContactGUIController decouples GUI widgets from
   business operations, enabling headless automated unit testing.
2. Form Binding & State Management: Treeview selection auto-populates entry
   fields for seamless viewing and inline editing.
================================================================================
"""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from projects.p01_contact_management.models import Contact
from projects.p01_contact_management.repository import ContactRepository
from projects.p01_contact_management.service import ContactError, ContactService


class ContactGUIController:
    """Headless controller mediating between Tkinter UI and ContactService."""

    def __init__(self, service: ContactService) -> None:
        self.service = service

    def add_contact(self, name: str, phone: str, email: str, address: str) -> Contact:
        return self.service.add_contact(name, phone, email, address)

    def edit_contact(
        self, contact_id: int, name: str, phone: str, email: str, address: str
    ) -> Contact:
        return self.service.edit_contact(contact_id, name, phone, email, address)

    def delete_contact(self, contact_id: int) -> None:
        self.service.delete_contact(contact_id)

    def search_contacts(self, query: str) -> list[Contact]:
        return self.service.search_contacts(query)

    def list_contacts(self) -> list[Contact]:
        return self.service.list_contacts()

    def export_csv(self, path: Path | str) -> int:
        return self.service.export_csv(path)

    def import_csv(self, path: Path | str) -> tuple[int, int, list[str]]:
        return self.service.import_csv(path)


class ContactGUIApp:
    """Desktop window for managing contacts with search and CSV import/export."""

    def __init__(self, root: tk.Tk, controller: ContactGUIController) -> None:
        self.root = root
        self.controller = controller
        self.root.title("Contact Management System")
        self.root.geometry("820x560")
        self.selected_contact_id: int | None = None

        self._build_ui()
        self.refresh_table()

    def _build_ui(self) -> None:
        top_frame = ttk.LabelFrame(self.root, text="Contact Details")
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(top_frame, text="Name:").grid(row=0, column=0, padx=5, pady=5)
        self.entry_name = ttk.Entry(top_frame, width=20)
        self.entry_name.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(top_frame, text="Phone:").grid(row=0, column=2, padx=5, pady=5)
        self.entry_phone = ttk.Entry(top_frame, width=18)
        self.entry_phone.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(top_frame, text="Email:").grid(row=0, column=4, padx=5, pady=5)
        self.entry_email = ttk.Entry(top_frame, width=22)
        self.entry_email.grid(row=0, column=5, padx=5, pady=5)

        ttk.Label(top_frame, text="Address:").grid(row=1, column=0, padx=5, pady=5)
        self.entry_address = ttk.Entry(top_frame, width=40)
        self.entry_address.grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky="w")

        btn_frame = ttk.Frame(top_frame)
        btn_frame.grid(row=1, column=4, columnspan=2, pady=5)

        btn_save = ttk.Button(btn_frame, text="Save / Add", command=self._on_save)
        btn_save.pack(side=tk.LEFT, padx=3)

        btn_clear = ttk.Button(btn_frame, text="Clear Form", command=self._clear_form)
        btn_clear.pack(side=tk.LEFT, padx=3)

        # Search Bar
        search_frame = ttk.Frame(self.root)
        search_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.entry_search = ttk.Entry(search_frame, width=25)
        self.entry_search.pack(side=tk.LEFT, padx=5)

        btn_search = ttk.Button(search_frame, text="Filter", command=self._on_search)
        btn_search.pack(side=tk.LEFT, padx=5)

        btn_reset = ttk.Button(search_frame, text="Reset", command=self.refresh_table)
        btn_reset.pack(side=tk.LEFT, padx=5)

        # CSV actions
        btn_export = ttk.Button(search_frame, text="Export CSV", command=self._on_export)
        btn_export.pack(side=tk.RIGHT, padx=5)

        btn_import = ttk.Button(search_frame, text="Import CSV", command=self._on_import)
        btn_import.pack(side=tk.RIGHT, padx=5)

        # Table
        columns = ("id", "name", "phone", "email", "address", "created")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Name")
        self.tree.heading("phone", text="Phone")
        self.tree.heading("email", text="Email")
        self.tree.heading("address", text="Address")
        self.tree.heading("created", text="Created")

        self.tree.column("id", width=40, anchor=tk.CENTER)
        self.tree.column("name", width=150)
        self.tree.column("phone", width=120)
        self.tree.column("email", width=180)
        self.tree.column("address", width=180)
        self.tree.column("created", width=110)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.tree.bind("<<TreeviewSelect>>", self._on_select_row)

        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(fill=tk.X, padx=10, pady=5)

        btn_del = ttk.Button(bottom_frame, text="Delete Selected Contact", command=self._on_delete)
        btn_del.pack(side=tk.LEFT)

    def _on_save(self) -> None:
        name = self.entry_name.get().strip()
        phone = self.entry_phone.get().strip()
        email = self.entry_email.get().strip()
        address = self.entry_address.get().strip()

        try:
            if self.selected_contact_id is None:
                contact = self.controller.add_contact(name, phone, email, address)
                messagebox.showinfo("Success", f"Contact '{contact.name}' added!")
            else:
                contact = self.controller.edit_contact(
                    self.selected_contact_id, name, phone, email, address
                )
                messagebox.showinfo("Success", f"Contact ID {contact.id} updated!")

            self._clear_form()
            self.refresh_table()
        except ContactError as err:
            messagebox.showerror("Error", str(err))

    def _on_delete(self) -> None:
        if self.selected_contact_id is None:
            messagebox.showwarning("Warning", "Select a contact from the table to delete.")
            return

        if not messagebox.askyesno(
            "Confirm", f"Permanently delete contact ID {self.selected_contact_id}?"
        ):
            return

        try:
            self.controller.delete_contact(self.selected_contact_id)
            messagebox.showinfo("Success", "Contact deleted.")
            self._clear_form()
            self.refresh_table()
        except ContactError as err:
            messagebox.showerror("Error", str(err))

    def _on_search(self) -> None:
        query = self.entry_search.get().strip()
        results = (
            self.controller.search_contacts(query) if query else self.controller.list_contacts()
        )
        self._populate_tree(results)

    def _on_export(self) -> None:
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Export Contacts to Safe CSV",
        )
        if not file_path:
            return

        try:
            count = self.controller.export_csv(file_path)
            messagebox.showinfo("Export Complete", f"Exported {count} contacts.")
        except Exception as err:
            messagebox.showerror("Export Failed", str(err))

    def _on_import(self) -> None:
        file_path = filedialog.askopenfilename(
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Import Contacts from CSV",
        )
        if not file_path:
            return

        try:
            imported, skipped, errors = self.controller.import_csv(file_path)
            msg = f"Successfully imported: {imported}\nSkipped: {skipped}"
            if errors:
                msg += f"\n\nFirst error: {errors[0]}"
            messagebox.showinfo("Import Complete", msg)
            self.refresh_table()
        except Exception as err:
            messagebox.showerror("Import Failed", str(err))

    def _on_select_row(self, _: tk.Event) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        item = self.tree.item(selected[0])
        values = item["values"]
        self.selected_contact_id = int(values[0])

        self.entry_name.delete(0, tk.END)
        self.entry_name.insert(0, values[1])

        self.entry_phone.delete(0, tk.END)
        self.entry_phone.insert(0, str(values[2]))

        self.entry_email.delete(0, tk.END)
        self.entry_email.insert(0, values[3])

        self.entry_address.delete(0, tk.END)
        self.entry_address.insert(0, values[4])

    def _clear_form(self) -> None:
        self.selected_contact_id = None
        self.entry_name.delete(0, tk.END)
        self.entry_phone.delete(0, tk.END)
        self.entry_email.delete(0, tk.END)
        self.entry_address.delete(0, tk.END)

    def refresh_table(self) -> None:
        self._populate_tree(self.controller.list_contacts())

    def _populate_tree(self, contacts: list[Contact]) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        for c in contacts:
            self.tree.insert(
                "", tk.END, values=(c.id, c.name, c.phone, c.email, c.address, c.created_at)
            )


def launch_gui(service: ContactService | None = None) -> None:
    if service is None:
        db_path = Path(__file__).resolve().parent / "data" / "contacts.db"
        repo = ContactRepository.from_path(db_path)
        service = ContactService(repo)

    root = tk.Tk()
    controller = ContactGUIController(service)
    _ = ContactGUIApp(root, controller)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
