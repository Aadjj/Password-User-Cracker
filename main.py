import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
import requests
import threading
import random
import time
from datetime import datetime
from queue import Queue
from tkinter import ttk

class AdvancedLoginTesterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Login Tester")

        # UI Components
        self.create_widgets()

        # Queue and threading setup
        self.queue = Queue()
        self.threads = []
        self.running = False
        self.stop_testing = False

    def create_widgets(self):
        # URL Entry
        tk.Label(self.root, text="Login URL:").grid(row=0, column=0, sticky=tk.W)
        self.url_entry = tk.Entry(self.root, width=50)
        self.url_entry.grid(row=0, column=1, padx=10, pady=5)

        # Usernames Entry
        tk.Label(self.root, text="Usernames (comma-separated):").grid(row=1, column=0, sticky=tk.W)
        self.usernames_entry = tk.Entry(self.root, width=50)
        self.usernames_entry.grid(row=1, column=1, padx=10, pady=5)

        # Passwords Entry
        tk.Label(self.root, text="Passwords (comma-separated):").grid(row=2, column=0, sticky=tk.W)
        self.passwords_entry = tk.Entry(self.root, width=50)
        self.passwords_entry.grid(row=2, column=1, padx=10, pady=5)

        # Threads Entry
        tk.Label(self.root, text="Number of Threads:").grid(row=3, column=0, sticky=tk.W)
        self.threads_entry = tk.Entry(self.root, width=10)
        self.threads_entry.grid(row=3, column=1, sticky=tk.W, padx=10, pady=5)

        # Proxies Entry
        tk.Label(self.root, text="Proxies (comma-separated, optional):").grid(row=4, column=0, sticky=tk.W)
        self.proxies_entry = tk.Entry(self.root, width=50)
        self.proxies_entry.grid(row=4, column=1, padx=10, pady=5)

        # Delay Entry
        tk.Label(self.root, text="Delay Range (min-max seconds):").grid(row=5, column=0, sticky=tk.W)
        self.delay_entry = tk.Entry(self.root, width=20)
        self.delay_entry.grid(row=5, column=1, sticky=tk.W, padx=10, pady=5)

        # Start and Stop Buttons
        self.start_button = tk.Button(self.root, text="Start Testing", command=self.start_testing)
        self.start_button.grid(row=6, column=0, padx=10, pady=10)
        self.stop_button = tk.Button(self.root, text="Stop Testing", command=self.stop_testing, state=tk.DISABLED)
        self.stop_button.grid(row=6, column=1, padx=10, pady=10)

        # Progress Bar
        self.progress = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress, maximum=100)
        self.progress_bar.grid(row=7, column=0, columnspan=2, sticky=tk.W+tk.E, padx=10, pady=5)

        # Log Display
        self.log_display = scrolledtext.ScrolledText(self.root, width=80, height=20)
        self.log_display.grid(row=8, column=0, columnspan=2, padx=10, pady=5)

        # Save Log Button
        self.save_button = tk.Button(self.root, text="Save Log", command=self.save_log)
        self.save_button.grid(row=9, column=0, columnspan=2, pady=10)

    def start_testing(self):
        if self.running:
            messagebox.showinfo("Info", "Testing is already running.")
            return

        self.running = True
        self.stop_testing = False
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.log_display.delete(1.0, tk.END)
        self.progress.set(0)

        login_url = self.url_entry.get().strip()
        usernames = [u.strip() for u in self.usernames_entry.get().split(',') if u.strip()]
        passwords = [p.strip() for p in self.passwords_entry.get().split(',') if p.strip()]

        if not login_url or not usernames or not passwords:
            messagebox.showerror("Error", "Login URL, usernames, and passwords must be provided.")
            self.running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            return

        try:
            num_threads = int(self.threads_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Number of threads must be an integer.")
            self.running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            return

        proxies = [p.strip() for p in self.proxies_entry.get().split(',')] if self.proxies_entry.get() else []

        # Parse delay range
        try:
            delay_range = tuple(map(int, self.delay_entry.get().split('-')))
            if len(delay_range) != 2:
                raise ValueError("Delay range must have two values.")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid delay range: {e}")
            self.running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            return

        total_attempts = len(usernames) * len(passwords)
        self.progress_bar.config(maximum=total_attempts)
        self.completed_attempts = 0

        for username in usernames:
            for password in passwords:
                self.queue.put((username, password))

        for _ in range(num_threads):
            thread = threading.Thread(target=self.worker, args=(login_url, proxies, delay_range))
            thread.start()
            self.threads.append(thread)

    def stop_testing(self):
        self.stop_testing = True
        self.running = False
        self.stop_button.config(state=tk.DISABLED)
        self.start_button.config(state=tk.NORMAL)
        messagebox.showinfo("Info", "Testing stopped.")

    def worker(self, login_url, proxies, delay_range):
        while not self.queue.empty() and not self.stop_testing:
            username, password = self.queue.get()
            response = self.attempt_login(login_url, username, password, proxies)
            if response:
                success = 'Login successful' in response.text
                self.log_attempt(username, password, success, response.status_code)
                if success:
                    self.update_log_display(f'Successful login with {username}:{password}\n')
                else:
                    self.update_log_display(f'Failed login with {username}:{password}\n')
            self.completed_attempts += 1
            self.progress.set(self.completed_attempts)
            time.sleep(random.uniform(*delay_range))  # Dynamic delay
            self.queue.task_done()

        self.running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        if not self.stop_testing:
            messagebox.showinfo("Info", "Testing completed.")

    def attempt_login(self, login_url, username, password, proxies):
        data = {
            'username': username,
            'password': password
        }
        proxy = random.choice(proxies) if proxies else None
        try:
            response = requests.post(login_url, data=data, proxies={"http": proxy, "https": proxy}, timeout=10)
            return response
        except requests.RequestException as e:
            self.update_log_display(f'Request failed: {e}\n')
            return None

    def log_attempt(self, username, password, success, status_code):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f'{timestamp} - {username}:{password} - {"Success" if success else "Failed"} - Status Code: {status_code}\n'
        self.update_log_display(log_entry)

    def update_log_display(self, message):
        # Schedule UI updates in the main thread
        self.root.after(0, lambda: self.log_display.insert(tk.END, message))

    def save_log(self):
        log_content = self.log_display.get(1.0, tk.END)
        file_path = filedialog.asksaveasfilename(defaultextension=".log", filetypes=[("Log files", "*.log"), ("All files", "*.*")])
        if file_path:
            with open(file_path, 'w') as file:
                file.write(log_content)
            messagebox.showinfo("Info", f"Log saved to {file_path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = AdvancedLoginTesterApp(root)
    root.mainloop()
