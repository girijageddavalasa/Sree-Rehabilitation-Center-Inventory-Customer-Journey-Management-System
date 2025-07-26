import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pymysql
import datetime
import csv # Import the csv module for CSV download

# Import ReportLab modules for PDF generation
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER # For centering text

# MySQL DB connection details
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = '1234'
DB_NAME = 'sree3'
TABLE_NAME = 'invoice3' # Ensure your table is named 'invoice3' in your database

# --- Fixed Service Prices ---
# (Information based on image_9fbed7.png)
SERVICE_PRICES = {
    "PHYSICAL THERAPY": 100.00,
    "OCCUPATIONAL THERAPY": 200.00,
    "SPEECH AND LANGUAGE THERAPY": 300.00,
    "BEHAVIORAL THERAPY": 400.00,
    "AQUATIC THERAPY": 500.00
}
# --- End Fixed Service Prices ---

class AddRecordForm:
    def __init__(self, parent, app_instance):
        self.app = app_instance
        self.top = tk.Toplevel(parent)
        self.top.title("Add New Invoice Record")
        self.top.grab_set() # Make this window modal

        self.entries = {}
        row_num = 0

        # --- Invoice Number Field (Auto-suggested and Editable) ---
        tk.Label(self.top, text="Invoice No:").grid(row=row_num, column=0, padx=5, pady=2, sticky="w")
        self.invoice_no_entry = tk.Entry(self.top, width=40)
        self.invoice_no_entry.grid(row=row_num, column=1, padx=5, pady=2, sticky="ew")
        self.entries["invoice_no"] = self.invoice_no_entry
        self.populate_next_invoice_no() # Call to get and set the next invoice number
        row_num += 1
        # --- End Invoice Number Field ---

        tk.Label(self.top, text=f"Invoice Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (Auto)").grid(row=row_num, column=0, columnspan=2, padx=5, pady=2, sticky="w")
        row_num += 1

        # Define fields to be created dynamically, excluding service_name and per_session for custom handling
        self.dynamic_fields = [
            ("Due Date & Time (YYYY-MM-DD HH:MM:SS)", "due_date_time", tk.Entry),
            ("Customer ID", "c_id", tk.Entry),
            ("First Name", "c_name_first", tk.Entry),
            ("Last Name", "c_name_last", tk.Entry),
            ("Number of Sessions", "no_of_sessions", tk.Entry),
            ("Customer Mobile", "customer_mobile_number", tk.Entry)
        ]
        
        for label_text, field_name, widget_type in self.dynamic_fields:
            tk.Label(self.top, text=label_text + ":").grid(row=row_num, column=0, padx=5, pady=2, sticky="w")
            entry = widget_type(self.top, width=40)
            entry.grid(row=row_num, column=1, padx=5, pady=2, sticky="ew")
            self.entries[field_name] = entry
            row_num += 1

        # Set default value for due_date_time to current time for convenience
        self.entries["due_date_time"].insert(0, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        # --- Service Name Combobox ---
        tk.Label(self.top, text="Service Name:").grid(row=row_num, column=0, padx=5, pady=2, sticky="w")
        self.service_combobox = ttk.Combobox(self.top, width=37, state="readonly")
        self.service_combobox['values'] = list(SERVICE_PRICES.keys()) # Populate with service names
        self.service_combobox.grid(row=row_num, column=1, padx=5, pady=2, sticky="ew")
        self.service_combobox.bind("<<ComboboxSelected>>", self.update_per_session_cost)
        self.entries["service_name"] = self.service_combobox # Store combobox in entries dict
        row_num += 1
        # --- End Service Name Combobox ---

        # --- Per Session Cost Entry (auto-populated and read-only) ---
        tk.Label(self.top, text="Per Session Cost:").grid(row=row_num, column=0, padx=5, pady=2, sticky="w")
        self.per_session_entry = tk.Entry(self.top, width=40, state="readonly")
        self.per_session_entry.grid(row=row_num, column=1, padx=5, pady=2, sticky="ew")
        self.entries["per_session"] = self.per_session_entry # Store entry in entries dict
        row_num += 1
        # --- End Per Session Cost Entry ---

        # Optionally set a default service and cost when form opens
        if SERVICE_PRICES:
            first_service = list(SERVICE_PRICES.keys())[0]
            self.service_combobox.set(first_service)
            self.update_per_session_cost() # Manually call to populate cost for default service

        tk.Button(self.top, text="Add Record", command=self.save_record).grid(row=row_num, column=0, columnspan=2, pady=10)

    def populate_next_invoice_no(self):
        """Fetches the highest invoice number from the DB and sets the next one."""
        next_id = self.app.get_latest_invoice_no() + 1
        self.invoice_no_entry.delete(0, tk.END)
        self.invoice_no_entry.insert(0, str(next_id))

    def update_per_session_cost(self, event=None):
        """Updates the 'Per Session Cost' based on the selected service."""
        selected_service = self.entries["service_name"].get()
        # Get cost from the SERVICE_PRICES dictionary
        cost = SERVICE_PRICES.get(selected_service, 0.0) # Default to 0.0 if service not found
        
        self.entries["per_session"].config(state="normal") # Temporarily enable to insert
        self.entries["per_session"].delete(0, tk.END)
        self.entries["per_session"].insert(0, str(cost))
        self.entries["per_session"].config(state="readonly")

    def save_record(self):
        """Saves a new invoice record to the database and displays the new invoice number."""
        try:
            invoice_no_str = self.entries["invoice_no"].get()
            if not invoice_no_str:
                messagebox.showerror("Input Error", "Invoice Number cannot be empty.")
                return
            try:
                invoice_no = int(invoice_no_str)
            except ValueError:
                messagebox.showerror("Input Error", "Invoice Number must be a valid integer.")
                return

            date_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            due_date_time = self.entries["due_date_time"].get()
            
            try:
                c_id = int(self.entries["c_id"].get()) 
                no_of_sessions = int(self.entries["no_of_sessions"].get())
            except ValueError:
                messagebox.showerror("Input Error", "Customer ID and Number of Sessions must be valid numbers.")
                return

            # Per session cost is now from the auto-populated field
            try:
                per_session = float(self.entries["per_session"].get())
            except ValueError:
                messagebox.showerror("Input Error", "Per Session Cost must be a valid number (auto-populated). Please select a service.")
                return

            c_name_first = self.entries["c_name_first"].get()
            c_name_last = self.entries["c_name_last"].get()
            service_name = self.entries["service_name"].get() # Get from combobox
            customer_mobile_number = self.entries["customer_mobile_number"].get()

            # Calculate total
            total = no_of_sessions * per_session

            if not all([due_date_time, c_name_first, service_name]):
                messagebox.showerror("Error", "Please fill all required text fields (Due Date, First Name, Service Name).")
                return
            if not service_name: # Check if a service was actually selected
                messagebox.showerror("Error", "Please select a Service Name from the dropdown.")
                return

            # Call add_record_to_db with the invoice_no from the entry
            success = self.app.add_record_to_db(
                invoice_no, date_time, due_date_time, c_id, c_name_first, c_name_last,
                service_name, no_of_sessions, per_session, total, customer_mobile_number
            )
            
            if success:
                messagebox.showinfo("Success", f"Record added successfully! New Invoice No: {invoice_no}")
                self.top.destroy()
            # No else needed, as errors are handled by add_record_to_db messagebox

        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

class UpdateRecordForm:
    def __init__(self, parent, app_instance, current_values):
        self.app = app_instance
        self.top = tk.Toplevel(parent)
        self.top.title("Update Invoice Record")
        self.top.grab_set() # Make this window modal

        self.invoice_no = current_values[0] # Get invoice_no from selected row

        # Mapping of column indices to field names for current_values
        # invoice_no(0), date_time(1), due_date_time(2), c_id(3), c_name_first(4), c_name_last(5),
        # service_name(6), no_of_sessions(7), per_session(8), total(9), customer_mobile_number(10)

        self.field_configs = [
            ("Invoice No:", "invoice_no", "entry", True, 0), # Read-only
            ("Date & Time (YYYY-MM-DD HH:MM:SS)", "date_time", "entry", False, 1),
            ("Due Date & Time (YYYY-MM-DD HH:MM:SS)", "due_date_time", "entry", False, 2),
            ("Customer ID", "c_id", "entry", False, 3),
            ("First Name", "c_name_first", "entry", False, 4),
            ("Last Name", "c_name_last", "entry", False, 5),
            ("Number of Sessions", "no_of_sessions", "entry", False, 7),
            ("Current Total (Calculated)", "total", "entry", True, 9), # Read-only, new total calculated
            ("Customer Mobile", "customer_mobile_number", "entry", False, 10)
        ]
        self.entries = {}

        row_num = 0
        for label_text, field_name, widget_type_str, read_only, value_index in self.field_configs:
            tk.Label(self.top, text=label_text + ":").grid(row=row_num, column=0, padx=5, pady=2, sticky="w")
            
            entry = tk.Entry(self.top, width=40) # Default to Entry
            entry.grid(row=row_num, column=1, padx=5, pady=2, sticky="ew")
            self.entries[field_name] = entry

            if read_only:
                entry.config(state="readonly")
            
            # Populate with current value
            entry.config(state="normal") # Temporarily enable to insert
            val = current_values[value_index]
            if field_name == "c_name_last" or field_name == "customer_mobile_number":
                 entry.insert(0, val if val is not None else "")
            elif field_name == "total" or field_name == "per_session":
                 entry.insert(0, f"{float(val):.2f}")
            else:
                 entry.insert(0, val)
            if read_only:
                entry.config(state="readonly")
            row_num += 1
        
        # --- Service Name Combobox ---
        tk.Label(self.top, text="Service Name:").grid(row=row_num, column=0, padx=5, pady=2, sticky="w")
        self.service_combobox = ttk.Combobox(self.top, width=37, state="readonly")
        self.service_combobox['values'] = list(SERVICE_PRICES.keys()) # Populate with service names
        self.service_combobox.grid(row=row_num, column=1, padx=5, pady=2, sticky="ew")
        self.service_combobox.bind("<<ComboboxSelected>>", self.update_per_session_cost)
        self.entries["service_name"] = self.service_combobox # Store combobox in entries dict
        
        # Set initial value for combobox based on current_values[6]
        initial_service = current_values[6]
        if initial_service in SERVICE_PRICES:
            self.service_combobox.set(initial_service)
        else:
            self.service_combobox.set("Select a Service") # Or leave empty
        row_num += 1
        # --- End Service Name Combobox ---

        # --- Per Session Cost Entry (auto-populated and read-only) ---
        tk.Label(self.top, text="Per Session Cost:").grid(row=row_num, column=0, padx=5, pady=2, sticky="w")
        self.per_session_entry = tk.Entry(self.top, width=40, state="readonly")
        self.per_session_entry.grid(row=row_num, column=1, padx=5, pady=2, sticky="ew")
        self.entries["per_session"] = self.per_session_entry # Store entry in entries dict
        
        # Populate initial per_session cost based on the pre-filled service
        self.update_per_session_cost() 
        row_num += 1
        # --- End Per Session Cost Entry ---


        tk.Button(self.top, text="Save Changes", command=self.save_changes).grid(row=row_num, column=0, columnspan=2, pady=10)

    def update_per_session_cost(self, event=None):
        """Updates the 'Per Session Cost' based on the selected service."""
        selected_service = self.entries["service_name"].get()
        # Get cost from the SERVICE_PRICES dictionary
        cost = SERVICE_PRICES.get(selected_service, 0.0)
        
        self.entries["per_session"].config(state="normal") # Temporarily enable to insert
        self.entries["per_session"].delete(0, tk.END)
        self.entries["per_session"].insert(0, str(cost))
        self.entries["per_session"].config(state="readonly")

    def save_changes(self):
        """Saves changes to an existing invoice record in the database."""
        try:
            date_time = self.entries["date_time"].get()
            due_date_time = self.entries["due_date_time"].get()
            
            try:
                c_id = int(self.entries["c_id"].get())
                no_of_sessions = int(self.entries["no_of_sessions"].get())
            except ValueError:
                messagebox.showerror("Input Error", "Customer ID and Number of Sessions must be valid numbers.")
                return

            # Per session cost is now from the auto-populated field
            try:
                per_session = float(self.entries["per_session"].get())
            except ValueError:
                messagebox.showerror("Input Error", "Per Session Cost must be a valid number (auto-populated). Please select a service.")
                return

            c_name_first = self.entries["c_name_first"].get()
            c_name_last = self.entries["c_name_last"].get()
            service_name = self.entries["service_name"].get() # Get from combobox
            customer_mobile_number = self.entries["customer_mobile_number"].get()

            # Recalculate total
            total = no_of_sessions * per_session

            if not all([date_time, due_date_time, c_name_first, service_name]):
                messagebox.showerror("Error", "Please fill all required fields.")
                return
            if not service_name: # Check if a service was actually selected
                messagebox.showerror("Error", "Please select a Service Name from the dropdown.")
                return

            self.app.update_record_in_db(
                self.invoice_no, date_time, due_date_time, c_id, c_name_first, c_name_last,
                service_name, no_of_sessions, per_session, total, customer_mobile_number
            )
            self.top.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

class FindRecordForm:
    def __init__(self, parent, app_instance):
        self.app = app_instance
        self.top = tk.Toplevel(parent)
        self.top.title("Find Records")
        self.top.grab_set()

        # Find by Customer ID
        tk.Label(self.top, text="Enter Customer ID:").grid(row=0, column=0, padx=5, pady=5)
        self.c_id_entry = tk.Entry(self.top, width=30)
        self.c_id_entry.grid(row=0, column=1, padx=5, pady=5)
        tk.Button(self.top, text="Find by Customer ID", command=self.find_by_c_id).grid(row=0, column=2, padx=5, pady=5)

        # Find by Invoice Number
        tk.Label(self.top, text="Enter Invoice No:").grid(row=1, column=0, padx=5, pady=5)
        self.invoice_no_entry = tk.Entry(self.top, width=30)
        self.invoice_no_entry.grid(row=1, column=1, padx=5, pady=5)
        tk.Button(self.top, text="Find by Invoice No", command=self.find_by_invoice_no).grid(row=1, column=2, padx=5, pady=5)

        tk.Button(self.top, text="Show All Records", command=self.show_all_records).grid(row=2, column=0, columnspan=3, pady=10)

    def find_by_c_id(self):
        """Fetches records based on customer ID."""
        c_id_str = self.c_id_entry.get()
        if not c_id_str:
            messagebox.showwarning("Warning", "Please enter a Customer ID to find.")
            return

        try:
            c_id = int(c_id_str)
            self.app.fetch_data(c_id=c_id) # Call fetch_data with c_id
            self.top.destroy()
        except ValueError:
            messagebox.showerror("Input Error", "Customer ID must be a number.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to find records: {e}")

    def find_by_invoice_no(self):
        """Fetches records based on invoice number."""
        invoice_no_str = self.invoice_no_entry.get()
        if not invoice_no_str:
            messagebox.showwarning("Warning", "Please enter an Invoice Number to find.")
            return

        try:
            invoice_no = int(invoice_no_str)
            self.app.fetch_data(invoice_no=invoice_no) # Call fetch_data with invoice_no
            self.top.destroy()
        except ValueError:
            messagebox.showerror("Input Error", "Invoice Number must be a number.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to find records: {e}")

    def show_all_records(self):
        """Fetches and displays all records."""
        self.app.fetch_data() # Fetch all data without filter
        self.top.destroy()


class InvoiceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Invoice Manager")
        self.root.geometry("1400x750") # Increased window size to accommodate new frames

        # ========== Frame Layout ==========
        top_frame = tk.Frame(root)
        top_frame.pack(fill="x", padx=10, pady=5)

        # Filter frame for column-wise filtering
        self.filter_frame = tk.Frame(root)
        self.filter_frame.pack(fill="x", padx=10, pady=2)

        mid_frame = tk.Frame(root)
        mid_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Bottom section with preview and total amount
        bottom_main_frame = tk.Frame(root)
        bottom_main_frame.pack(fill="x", padx=10, pady=5)

        # Frame for Invoice Preview
        preview_frame = tk.LabelFrame(bottom_main_frame, text="Selected Invoice Details", padx=5, pady=5)
        preview_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        # Frame for Total Amount of Customer
        total_amount_frame = tk.LabelFrame(bottom_main_frame, text="Customer's Total Amount (All Invoices)", padx=5, pady=5)
        total_amount_frame.pack(side="right", fill="y", padx=(5, 0))


        # ========== Treeview ==========
        self.tree = ttk.Treeview(mid_frame, columns=(
            "invoice_no", "date_time", "due_date_time", "c_id", "c_name_first", "c_name_last",
            "service_name", "no_of_sessions", "per_session", "total", "customer_mobile_number"
        ), show='headings')

        # Define column headings and widths
        self.columns_config = {
            "invoice_no": {"text": "Invoice No.", "width": 80, "filter": False},
            "date_time": {"text": "Invoice Date", "width": 150, "filter": True, "filter_label": "Date:"},
            "due_date_time": {"text": "Due Date", "width": 150, "filter": False},
            "c_id": {"text": "Customer ID", "width": 100, "filter": True, "filter_label": "ID:"},
            "c_name_first": {"text": "First Name", "width": 120, "filter": True, "filter_label": "First Name:"},
            "c_name_last": {"text": "Last Name", "width": 120, "filter": True, "filter_label": "Last Name:"},
            "service_name": {"text": "Service", "width": 150, "filter": False},
            "no_of_sessions": {"text": "Sessions", "width": 80, "filter": False},
            "per_session": {"text": "Per Session", "width": 100, "filter": False},
            "total": {"text": "Total", "width": 100, "filter": False},
            "customer_mobile_number": {"text": "Mobile No.", "width": 120, "filter": True, "filter_label": "Mobile No.:"}
        }

        # Add "Filter by:" label
        tk.Label(self.filter_frame, text="Filter by:").pack(side="left", padx=(0, 5), pady=2)

        # Configure columns and add filter entries with specific labels
        self.filter_entries = {}
        for col, config in self.columns_config.items():
            self.tree.heading(col, text=config["text"])
            self.tree.column(col, width=config["width"], anchor="center")

            if config["filter"]:
                # Add individual label for each filter
                tk.Label(self.filter_frame, text=config["filter_label"]).pack(side="left", padx=(5, 2), pady=2)
                
                filter_var = tk.StringVar()
                filter_entry = ttk.Entry(self.filter_frame, textvariable=filter_var, width=int(config["width"] / 9)) # Approximate width
                filter_entry.pack(side="left", padx=2, pady=2)
                filter_entry.bind("<KeyRelease>", self.apply_filters)
                self.filter_entries[col] = {"var": filter_var, "entry": filter_entry}
            else:
                # Add a placeholder label for non-filterable columns to maintain alignment
                pass # No label/entry for non-filterable columns, the layout is handled implicitly by previous elements.

        self.tree.pack(fill="both", expand=True)

        # Add scrollbars to Treeview
        vsb = ttk.Scrollbar(mid_frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vsb.set)

        hsb = ttk.Scrollbar(mid_frame, orient="horizontal", command=self.tree.xview)
        hsb.pack(side="bottom", fill="x")
        self.tree.configure(xscrollcommand=hsb.set)


        # ========== Invoice Preview Section ==========
        self.preview = tk.Text(preview_frame, height=8, wrap="word") # Use wrap="word"
        self.preview.pack(fill="both", expand=True)
        self.preview.config(state="disabled") # Make it read-only

        # --- Print Button near Selected Invoice Frame ---
        self.print_preview_button = tk.Button(preview_frame, text="Print Invoice (PDF)", command=self.print_invoice_pdf)
        self.print_preview_button.pack(pady=5)
        # --- End Print Button ---

        # ========== Total Amount for Selected Customer ==========
        self.total_amount_label = tk.Label(total_amount_frame, text="₹ 0.00", font=("Arial", 24, "bold"), fg="darkgreen")
        self.total_amount_label.pack(expand=True, padx=20, pady=20)


        # Bind treeview selection to update preview and total amount
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # ========== Main Control Buttons (top frame) ==========
        btn_frame = tk.Frame(top_frame)
        btn_frame.pack()

        tk.Button(btn_frame, text="Add Invoice", command=self.add_record).pack(side="left", padx=5, pady=5)
        tk.Button(btn_frame, text="Update Invoice", command=self.update_record).pack(side="left", padx=5, pady=5)
        tk.Button(btn_frame, text="Remove Invoice", command=self.remove_record).pack(side="left", padx=5, pady=5)
        tk.Button(btn_frame, text="Clear Filters", command=self.clear_filters).pack(side="left", padx=5, pady=5) # Renamed from Find to Clear Filters
        tk.Button(btn_frame, text="Refresh All", command=self.fetch_data).pack(side="left", padx=5, pady=5)
        tk.Button(btn_frame, text="Download CSV", command=self.download_csv).pack(side="left", padx=5, pady=5)


        # Initial data fetch
        self.fetch_data()
        self.update_customer_total_amount(None) # Initialize total to 0


    # ========== MySQL Connection ==========
    def connect_db(self):
        """Establishes a connection to the MySQL database."""
        return pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)

    def get_latest_invoice_no(self):
        """Fetches the highest existing invoice number from the database."""
        try:
            con = self.connect_db()
            cur = con.cursor()
            cur.execute(f"SELECT MAX(invoice_no) FROM {TABLE_NAME}")
            result = cur.fetchone()
            con.close()
            if result and result[0] is not None:
                return int(result[0])
            return 0 # No invoices yet, start from 1
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to fetch latest invoice number: {e}")
            return 0 # Default to 0 on error

    # ========== Fetch Records ==========
    def fetch_data(self, c_id=None, invoice_no=None):
        """
        Fetches invoice data from the database and populates the Treeview.
        Applies filters based on the text in the filter entry fields.
        """
        try:
            con = self.connect_db()
            cur = con.cursor()
            query = f"SELECT invoice_no, date_time, due_date_time, c_id, c_name_first, c_name_last, service_name, no_of_sessions, per_session, total, customer_mobile_number FROM {TABLE_NAME}"
            params = []
            
            # Build WHERE clause from filters, prioritizing explicit c_id/invoice_no if provided
            where_clauses = []

            if invoice_no is not None: # Explicit invoice_no search takes precedence
                where_clauses.append("invoice_no = %s")
                params.append(invoice_no)
            elif c_id is not None: # Explicit c_id search
                where_clauses.append("c_id = %s")
                params.append(c_id)
            else: # Apply general filters
                if self.filter_entries["date_time"]["var"].get():
                    where_clauses.append("CAST(date_time AS CHAR) LIKE %s")
                    params.append(f"%{self.filter_entries['date_time']['var'].get()}%")
                if self.filter_entries["c_id"]["var"].get():
                    where_clauses.append("c_id LIKE %s")
                    params.append(f"%{self.filter_entries['c_id']['var'].get()}%")
                if self.filter_entries["c_name_first"]["var"].get():
                    where_clauses.append("c_name_first LIKE %s")
                    params.append(f"%{self.filter_entries['c_name_first']['var'].get()}%")
                if self.filter_entries["c_name_last"]["var"].get():
                    where_clauses.append("c_name_last LIKE %s")
                    params.append(f"%{self.filter_entries['c_name_last']['var'].get()}%")
                if self.filter_entries["customer_mobile_number"]["var"].get():
                    where_clauses.append("customer_mobile_number LIKE %s")
                    params.append(f"%{self.filter_entries['customer_mobile_number']['var'].get()}%")

            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            query += " ORDER BY invoice_no DESC" # Order by invoice number descending
            
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            self.tree.delete(*self.tree.get_children())
            
            if not rows and (c_id is not None or invoice_no is not None or any(filter_entry["var"].get() for filter_entry in self.filter_entries.values())):
                 messagebox.showinfo("No Records Found", "No records found matching your filter/search criteria.")
            
            for row in rows:
                # Format datetime objects for display if they come as objects
                formatted_row = list(row)
                for i in [1, 2]: # indices for date_time and due_date_time
                    if isinstance(formatted_row[i], datetime.datetime):
                        formatted_row[i] = formatted_row[i].strftime('%Y-%m-%d %H:%M:%S')
                self.tree.insert('', 'end', values=formatted_row)
            con.close()
            self.clear_preview()
            self.update_customer_total_amount(None) # Clear total when new data is fetched
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to fetch data: {e}")

    def apply_filters(self, event=None):
        """Applies filters based on the current text in the filter entry fields."""
        self.fetch_data()

    def clear_filters(self):
        """Clears all filter entry fields and refreshes the data."""
        for col_name in self.filter_entries:
            self.filter_entries[col_name]["var"].set("")
        self.fetch_data()

    def download_csv(self):
        """
        Downloads the currently displayed (filtered) data in the Treeview
        to a CSV file.
        """
        if not self.tree.get_children():
            messagebox.showwarning("No Data", "No data to download to CSV.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".csv",
                                               filetypes=[("CSV files", "*.csv")],
                                               initialfile="filtered_invoice_data.csv")
        if not file_path:
            return # User cancelled the save dialog

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)

                # Write headers
                headers = [self.tree.heading(col, "text") for col in self.tree["columns"]]
                csv_writer.writerow(headers)

                # Write data rows
                for item_id in self.tree.get_children():
                    row_values = self.tree.item(item_id, 'values')
                    csv_writer.writerow(row_values)
            
            messagebox.showinfo("Download Complete", f"Data successfully saved to {file_path}")

        except Exception as e:
            messagebox.showerror("Download Error", f"Failed to download CSV: {e}")


    # ========== Add Record to DB ==========
    def add_record_to_db(self, invoice_no, date_time, due_date_time, c_id, c_name_first, c_name_last, service_name, no_of_sessions, per_session, total, customer_mobile_number):
        """
        Inserts a new invoice record into the database using the provided invoice_no.
        Handles duplicate invoice number errors.
        """
        try:
            con = self.connect_db()
            cur = con.cursor()
            sql = f"""
            INSERT INTO {TABLE_NAME} (
                invoice_no, date_time, due_date_time, c_id, c_name_first, c_name_last,
                service_name, no_of_sessions, per_session, total, customer_mobile_number
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(sql, (
                invoice_no, date_time, due_date_time, c_id, c_name_first, c_name_last,
                service_name, no_of_sessions, per_session, total, customer_mobile_number
            ))
            con.commit()
            con.close()
            self.fetch_data() # Refresh Treeview
            return True # Indicate success
        except pymysql.err.IntegrityError as e:
            if "Duplicate entry" in str(e) and "for key 'PRIMARY'" in str(e):
                messagebox.showerror("Database Error", f"Invoice Number {invoice_no} already exists. Please choose a different one.")
            else:
                messagebox.showerror("Database Error", f"Failed to add record due to data integrity issue: {e}")
            return False # Indicate failure
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to add record: {e}")
            return False # Indicate failure

    # ========== Update Record in DB ==========
    def update_record_in_db(self, invoice_no, date_time, due_date_time, c_id, c_name_first, c_name_last, service_name, no_of_sessions, per_session, total, customer_mobile_number):
        """Updates an existing invoice record in the database."""
        try:
            con = self.connect_db()
            cur = con.cursor()
            sql = f"""
            UPDATE {TABLE_NAME} SET
                date_time = %s,
                due_date_time = %s,
                c_id = %s,
                c_name_first = %s,
                c_name_last = %s,
                service_name = %s,
                no_of_sessions = %s,
                per_session = %s,
                total = %s,
                customer_mobile_number = %s
            WHERE invoice_no = %s
            """
            cur.execute(sql, (
                date_time, due_date_time, c_id, c_name_first, c_name_last,
                service_name, no_of_sessions, per_session, total, customer_mobile_number,
                invoice_no
            ))
            con.commit()
            con.close()
            messagebox.showinfo("Success", "Record updated successfully!")
            self.fetch_data() # Refresh Treeview
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to update record: {e}")

    # ========== Calculate and Display Total Amount for a Customer ==========
    def update_customer_total_amount(self, c_id):
        """Calculates and displays the total amount for a given customer ID."""
        total_sum = 0.0
        if c_id is not None:
            try:
                con = self.connect_db()
                cur = con.cursor()
                cur.execute(f"SELECT SUM(total) FROM {TABLE_NAME} WHERE c_id = %s", (c_id,))
                result = cur.fetchone()
                if result and result[0] is not None:
                    total_sum = float(result[0])
                con.close()
            except Exception as e:
                print(f"Error fetching total sum for customer ID {c_id}: {e}") # Print to console for debugging
                total_sum = 0.0 # Reset on error

        self.total_amount_label.config(text=f"₹ {total_sum:,.2f}") # Format with 2 decimal places and comma separator

    # ========== Event Handler for Treeview Selection ==========
    def on_tree_select(self, event=None):
        """Handles selection event in the Treeview to update preview and customer total."""
        self.update_preview() # Update the invoice details preview
        selected_item = self.tree.focus()
        if selected_item:
            values = self.tree.item(selected_item)['values']
            if len(values) > 3: # Ensure c_id column exists
                customer_id = values[3] # c_id is the 4th element (index 3)
                self.update_customer_total_amount(customer_id)
            else:
                self.update_customer_total_amount(None) # Clear total if no valid c_id
        else:
            self.update_customer_total_amount(None) # Clear total if nothing selected


    # ========== Button Commands ==========
    def add_record(self):
        """Opens the form to add a new invoice record."""
        AddRecordForm(self.root, self)

    def remove_record(self):
        """Removes the selected invoice record from the database."""
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Warning", "No record selected to remove.")
            return

        values = self.tree.item(selected)['values']
        invoice_no = values[0]
        
        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete Invoice No. {invoice_no}?"):
            try:
                con = self.connect_db()
                cur = con.cursor()
                cur.execute(f"DELETE FROM {TABLE_NAME} WHERE invoice_no=%s", (invoice_no,))
                con.commit()
                con.close()
                self.fetch_data()
                messagebox.showinfo("Success", "Record deleted successfully!")
            except Exception as e:
                messagebox.showerror("Database Error", f"Failed to delete record: {e}")

    def update_record(self):
        """Opens the form to update the selected invoice record."""
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Warning", "No record selected to update.")
            return
        
        current_values = self.tree.item(selected)['values']
        UpdateRecordForm(self.root, self, current_values)

    def find_record(self):
        """Opens the form to find records by Customer ID or Invoice Number. (This was replaced by clear_filters button)"""
        # This function is no longer directly called by a button, as the find functionality
        # is now integrated into the filters. Keeping it for reference if needed.
        FindRecordForm(self.root, self)
        
    def update_preview(self):
        """Updates the text area with details of the currently selected invoice."""
        selected_item = self.tree.focus()
        if not selected_item:
            self.clear_preview()
            return
        
        values = self.tree.item(selected_item)['values']
        # invoice_no, date_time, due_date_time, c_id, c_name_first, c_name_last,
        # service_name, no_of_sessions, per_session, total, customer_mobile_number
        invoice_details = f"""
Invoice No: {values[0]}
Invoice Date: {values[1]}
Due Date: {values[2]}
Customer ID: {values[3]}
Customer Name: {values[4]} {values[5] if values[5] else ''}
Service: {values[6]}
Sessions: {values[7]}
Cost Per Session: ₹ {float(values[8]):.2f}
Total Amount: ₹ {float(values[9]):.2f}
Customer Mobile: {values[10] if values[10] else 'N/A'}
        """.strip()
        self.preview.config(state="normal")
        self.preview.delete(1.0, tk.END)
        self.preview.insert(tk.END, invoice_details)
        self.preview.config(state="disabled")

    def clear_preview(self):
        """Clears the invoice details preview area."""
        self.preview.config(state="normal")
        self.preview.delete(1.0, tk.END)
        self.preview.insert(tk.END, "Select an invoice from the table to see details here.")
        self.preview.config(state="disabled")

    def print_invoice_pdf(self):
        """Generates a PDF invoice for the selected record."""
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Print Error", "No invoice selected to print.")
            return

        values = self.tree.item(selected_item)['values']
        
        # Ensure values are converted to string safely and correctly formatted for PDF
        invoice_data = {
            "invoice_no": str(values[0]),
            "date_time": str(values[1]),
            "due_date_time": str(values[2]),
            "c_id": str(values[3]),
            "c_name_first": str(values[4]),
            "c_name_last": str(values[5]) if values[5] else '',
            "service_name": str(values[6]),
            "no_of_sessions": str(values[7]),
            "per_session": f"₹{float(values[8]):,.2f}",
            "total": f"₹{float(values[9]):,.2f}",
            "customer_mobile_number": str(values[10]) if values[10] else 'N/A'
        }

        # Ask user where to save the PDF
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"Invoice_{invoice_data['invoice_no']}_{invoice_data['c_name_first']}.pdf"
        )
        if not file_path:
            return # User cancelled

        try:
            doc = SimpleDocTemplate(file_path, pagesize=A4)
            styles = getSampleStyleSheet()

            # Custom style for the main title (centered and larger)
            styles.add(ParagraphStyle(name='CenterTitle',
                                      parent=styles['h1'],
                                      alignment=TA_CENTER,
                                      fontSize=20,
                                      leading=24))
            story = []
            # Add the main title: Sree Rehabilitation Center
            story.append(Paragraph("Sree Rehabilitation Center", styles['CenterTitle']))
            story.append(Spacer(1, 0.3 * inch)) # Add some space after the title

            # Title for invoice details
            story.append(Paragraph("Invoice Details", styles['h2']))
            story.append(Spacer(1, 0.2 * inch))

            # Invoice Header Info
            header_data = [
                ["Invoice No:", invoice_data['invoice_no']],
                ["Invoice Date:", invoice_data['date_time']],
                ["Due Date:", invoice_data['due_date_time']]
            ]
            header_table = Table(header_data, colWidths=[2 * inch, 4 * inch])
            header_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6)
            ]))
            story.append(header_table)
            story.append(Spacer(1, 0.2 * inch))

            # Customer Info
            story.append(Paragraph("Customer Details:", styles['h2']))
            customer_data = [
                ["Customer ID:", invoice_data['c_id']],
                ["Customer Name:", f"{invoice_data['c_name_first']} {invoice_data['c_name_last']}".strip()],
                ["Mobile No.:", invoice_data['customer_mobile_number']]
            ]
            customer_table = Table(customer_data, colWidths=[2 * inch, 4 * inch])
            customer_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6)
            ]))
            story.append(customer_table)
            story.append(Spacer(1, 0.2 * inch))

            # Service Details
            story.append(Paragraph("Service Details:", styles['h2']))
            service_data = [
                ["Service Name", "Sessions", "Per Session Cost", "Total Amount"],
                [invoice_data['service_name'], invoice_data['no_of_sessions'], invoice_data['per_session'], invoice_data['total']]
            ]
            service_table = Table(service_data, colWidths=[2.5 * inch, 1.2 * inch, 1.5 * inch, 1.5 * inch])
            service_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), # Header row bold
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ]))
            story.append(service_table)
            story.append(Spacer(1, 0.5 * inch))

            # Grand Total
            story.append(Paragraph(f"<b>Grand Total: {invoice_data['total']}</b>", styles['h2']))


            doc.build(story)
            messagebox.showinfo("PDF Generated", f"Invoice saved to:\n{file_path}")

        except Exception as e:
            messagebox.showerror("PDF Error", f"Failed to generate PDF: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = InvoiceApp(root)
    root.mainloop()
