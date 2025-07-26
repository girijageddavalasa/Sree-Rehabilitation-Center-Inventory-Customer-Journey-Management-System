import tkinter as tk
from tkinter import messagebox, simpledialog, ttk, filedialog
from datetime import datetime, timedelta
import csv

# Constants
APPOINTMENT_DURATION = timedelta(minutes=20)
BREAK_DURATION = timedelta(minutes=5)
START_TIME = datetime.strptime("09:00", "%H:%M").time()
END_TIME = datetime.strptime("17:00", "%H:%M").time()
LUNCH_START = datetime.strptime("12:30", "%H:%M").time()
LUNCH_END = datetime.strptime("13:00", "%H:%M").time()
THERAPY_TYPES = [
    "PHYSICAL THERAPY",
    "OCCUPATIONAL THERAPY",
    "SPEECH AND LANGUAGE THERAPY",
    "BEHAVIORAL THERAPY",
    "AQUATIC THERAPY"
]

class SchedulerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sree Rehabilitation Center")
        self.geometry("1700x900")
        self.bookings = {}  # slot_key -> {'phone': ..., 'therapy': ...}
        self.slot_buttons = {}

        title = tk.Label(self, text="Sree Rehabilitation Center – Schedule Your Appointment!",
                         font=("Helvetica", 18, "bold"), fg="#2c3e50")
        title.pack(pady=10)

        self.main_frame = tk.Frame(self)
        self.main_frame.pack(fill="both", expand=True)

        self.render_user_booking_panel()
        self.render_customer_view() # Moved this call before render_therapist_panel
        self.render_therapist_panel()

    def render_user_booking_panel(self):
        frame = tk.Frame(self.main_frame)
        frame.pack(side="left", fill="both", expand=True)

        canvas = tk.Canvas(frame)
        scroll_x = tk.Scrollbar(frame, orient="horizontal", command=canvas.xview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(xscrollcommand=scroll_x.set)

        canvas.pack(fill="both", expand=True)
        scroll_x.pack(fill="x")

        today = datetime.today().date()
        for col in range(365):
            day_date = today + timedelta(days=col)
            label = tk.Label(scrollable_frame, text=day_date.strftime("%a\n%d %b"), font=("Arial", 10, "bold"))

            if day_date.weekday() == 6:
                label.configure(fg="gray")
                label.grid(row=0, column=col, padx=8, pady=5)
                tk.Label(scrollable_frame, text="Closed", fg="gray").grid(row=1, column=col)
            else:
                label.grid(row=0, column=col, padx=8, pady=5)
                self.render_slots_for_day(scrollable_frame, day_date, col)

    def render_slots_for_day(self, frame, day_date, col):
        current_time = datetime.combine(day_date, START_TIME)
        end_of_day = datetime.combine(day_date, END_TIME)
        lunch_start = datetime.combine(day_date, LUNCH_START)
        lunch_end = datetime.combine(day_date, LUNCH_END)

        row = 1
        while current_time + APPOINTMENT_DURATION <= end_of_day:
            if lunch_start <= current_time < lunch_end:
                current_time = lunch_end
                continue

            start_str = current_time.strftime("%H:%M")
            end_str = (current_time + APPOINTMENT_DURATION).strftime("%H:%M")
            slot_key = f"{day_date}_{start_str}"

            btn = tk.Button(frame, text=f"{start_str}-{end_str}", width=12,
                            bg="lightgreen", command=lambda k=slot_key, d=day_date, s=start_str, e=end_str: self.handle_slot(k, d, s, e))
            btn.grid(row=row, column=col, pady=2)
            self.slot_buttons[slot_key] = btn

            row += 1
            current_time += APPOINTMENT_DURATION + BREAK_DURATION

    def handle_slot(self, slot_key, day, start_time, end_time):
        if slot_key in self.bookings:
            phone = simpledialog.askstring("Cancel Slot", "This slot is already booked. Enter your mobile number to cancel:")
            if phone and self.bookings[slot_key]['phone'] == phone:
                # Directly reset the button color for the cancelled slot
                self.slot_buttons[slot_key].configure(bg="lightgreen")
                del self.bookings[slot_key]
                self.update_therapist_schedule() # Re-evaluate colors for all slots
                self.update_customer_schedule(phone)
                messagebox.showinfo("Cancelled", "Your appointment has been cancelled.")
            else:
                messagebox.showwarning("Mismatch", "Mobile number does not match the booking.")
            return

        top = tk.Toplevel(self)
        top.title("Book Appointment")

        tk.Label(top, text=f"🗅 Date: {day.strftime('%B %d, %Y')}", font=("Arial", 12)).pack(pady=2)
        tk.Label(top, text=f"🕒 Time: {start_time} - {end_time}", font=("Arial", 12)).pack(pady=2)

        tk.Label(top, text="📱 Enter Mobile Number:").pack()
        phone_entry = tk.Entry(top)
        phone_entry.pack(pady=5)

        tk.Label(top, text="💆 Select Therapy Type:").pack()
        selected = tk.StringVar(value="Select service")
        dropdown = ttk.Combobox(top, values=["Select service"] + THERAPY_TYPES, textvariable=selected, state="readonly")
        dropdown.pack(pady=5)

        def confirm():
            phone = phone_entry.get()
            therapy = selected.get()
            if not phone:
                messagebox.showwarning("Missing Info", "Mobile number required!")
                return
            if therapy == "Select service":
                messagebox.showwarning("Missing Info", "Please select a therapy type.")
                return

            self.bookings[slot_key] = {'phone': phone, 'therapy': therapy}
            # The button's color will be set by update_therapist_schedule/update_customer_schedule
            # which is called right after this.
            # self.slot_buttons[slot_key].configure(bg="red") # This line is no longer strictly needed here
            self.update_therapist_schedule()
            self.update_customer_schedule(phone)
            messagebox.showinfo("Booked", f"Appointment booked for {therapy} on {day.strftime('%A')} at {start_time}.")
            top.destroy()

        tk.Button(top, text="✔ Book Slot", command=confirm).pack(pady=10)

    def render_therapist_panel(self):
        frame = tk.Frame(self.main_frame, relief="ridge", bd=2, width=300)
        frame.pack(side="right", fill="y", padx=10)

        tk.Label(frame, text="👨‍⚕️ Therapist View", font=("Arial", 14, "bold")).pack(pady=10)
        # Set default value to "Select Department"
        self.therapist_type = tk.StringVar(value="Select Department")
        # Add "Select Department" to the start of the values list
        dropdown = ttk.Combobox(frame, values=["Select Department"] + THERAPY_TYPES, textvariable=self.therapist_type, state="readonly")
        dropdown.pack(pady=5)
        dropdown.bind("<<ComboboxSelected>>", lambda e: self.update_therapist_schedule())

        self.schedule_list = tk.Listbox(frame, width=45, height=30)
        self.schedule_list.pack(pady=10)

        scrollbar = tk.Scrollbar(frame, orient="vertical", command=self.schedule_list.yview)
        scrollbar.pack(side="right", fill="y")
        self.schedule_list.configure(yscrollcommand=scrollbar.set)

        export_btn = tk.Button(frame, text="📤 Export to CSV", command=self.export_csv)
        export_btn.pack(pady=10)

        # Call update schedule initially to reflect the "Select Department" state
        self.update_therapist_schedule()

    def update_therapist_schedule(self):
        selected_type = self.therapist_type.get()
        self.schedule_list.delete(0, tk.END)
        # Check if customer_entry exists before trying to get its value
        current_customer_phone = self.customer_entry.get() if hasattr(self, 'customer_entry') else ""

        # Iterate through all slot buttons to apply correct coloring
        for slot, btn in self.slot_buttons.items():
            if slot in self.bookings:
                # If the slot is booked by the current customer and a phone is entered, make it yellow
                if self.bookings[slot]['phone'] == current_customer_phone and current_customer_phone:
                    btn.configure(bg="yellow")
                # If "Select Department" is chosen, all booked slots that are not yellow should be red
                elif selected_type == "Select Department":
                    btn.configure(bg="red")
                # If a specific therapy type is selected and the slot's therapy matches, make it purple
                elif self.bookings[slot]['therapy'] == selected_type:
                    btn.configure(bg="purple")
                # Otherwise, it's booked by someone else (not the current customer being viewed, and not the selected therapy type)
                else:
                    btn.configure(bg="red")
            else:
                # If the slot is not booked at all, make it lightgreen
                btn.configure(bg="lightgreen")

        # Populate the therapist's schedule list based on selected type
        if selected_type != "Select Department":
            for slot, info in self.bookings.items():
                if info['therapy'] == selected_type:
                    date_str, time_str = slot.split("_")
                    self.schedule_list.insert(tk.END, f"{date_str} at {time_str}")
        else:
            # When "Select Department" is chosen, show all booked appointments in the list
            for slot, info in self.bookings.items():
                date_str, time_str = slot.split("_")
                self.schedule_list.insert(tk.END, f"{date_str} at {time_str} ({info['therapy']}) - {info['phone']}")


    def render_customer_view(self):
        frame = tk.Frame(self.main_frame, relief="ridge", bd=2)
        frame.pack(side="bottom", fill="x")

        tk.Label(frame, text="📋 Your Appointments", font=("Arial", 12, "bold")).pack()
        tk.Label(frame, text="📱 Enter your Mobile Number to View Slots:").pack()

        self.customer_entry = tk.Entry(frame)
        self.customer_entry.pack(pady=5)

        btn_frame = tk.Frame(frame) # New frame for buttons
        btn_frame.pack(pady=5)

        btn_view = tk.Button(btn_frame, text="View My Slots", command=self.show_customer_slots)
        btn_view.pack(side="left", padx=5)

        # New button to clear customer view and reset colors
        btn_clear = tk.Button(btn_frame, text="Clear My Slots", command=self.clear_customer_display)
        btn_clear.pack(side="left", padx=5)

        self.customer_list = tk.Listbox(frame, height=5, width=100)
        self.customer_list.pack(pady=5)

        scroll = tk.Scrollbar(frame, orient="vertical", command=self.customer_list.yview)
        scroll.pack(side="right", fill="y")
        self.customer_list.config(yscrollcommand=scroll.set)

        self.yellow_note = tk.Label(frame, text="🔹 Yellow color indicates your booked slots.", font=("Arial", 9, "italic"), fg="darkgoldenrod")
        self.yellow_note.pack(pady=2)

    def show_customer_slots(self):
        phone = self.customer_entry.get()
        self.customer_list.delete(0, tk.END)
        
        # Update therapist schedule to apply yellow highlights for the entered phone number
        self.update_therapist_schedule()

        # Populate customer's listbox
        for slot, info in self.bookings.items():
            if info['phone'] == phone:
                self.customer_list.insert(tk.END, f"{slot.replace('_', ' at ')} | {info['therapy']}")

    def clear_customer_display(self):
        """Clears the customer mobile number entry and list, and resets slot colors."""
        self.customer_entry.delete(0, tk.END)
        self.customer_list.delete(0, tk.END)
        # Call update_therapist_schedule to re-evaluate all colors based on the now empty customer phone
        self.update_therapist_schedule()
        messagebox.showinfo("Cleared", "Customer view cleared and yellow highlights reset.")

    def update_customer_schedule(self, phone):
        # This function is called after a booking/cancellation.
        # If the customer_entry matches the phone of the action, refresh their view.
        if self.customer_entry.get() == phone:
            self.show_customer_slots()
        else:
            # If the phone in customer_entry doesn't match the action,
            # we should still ensure the general color scheme is updated.
            # This is already handled by update_therapist_schedule being called elsewhere.
            pass


    def export_csv(self):
        selected_type = self.therapist_type.get()
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[["CSV Files", "*.csv"]])
        if not filepath:
            return

        with open(filepath, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Date", "Time", "Therapy Type", "Customer Mobile"])
            
            # Export all bookings if "Select Department" is chosen, otherwise filter by selected type
            bookings_to_export = []
            if selected_type == "Select Department":
                bookings_to_export = [(s, i) for s, i in self.bookings.items()]
            else:
                bookings_to_export = [(s, i) for s, i in self.bookings.items() if i['therapy'] == selected_type]

            for slot, info in bookings_to_export:
                date_str, time_str = slot.split("_")
                writer.writerow([date_str, time_str, info['therapy'], info['phone']])

        messagebox.showinfo("Exported", f"Schedule exported to {filepath}")

if __name__ == "__main__":
    app = SchedulerApp()
    app.mainloop()
