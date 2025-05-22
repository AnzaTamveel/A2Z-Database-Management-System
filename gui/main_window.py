
# main_window.py
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, Toplevel
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from core.database import Database
from core.collection import Collection
import json
from core.auth import AuthManager
import time
import os
from core.decorators import requires_auth
from core.permissions import Permission
from core.query import Query
from utils.logger import logger

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("A2Z Database Management System")
        self.geometry("1000x700")
        self.indexing_enabled = False
        self.query_time = tk.StringVar()
        self.transaction_status = tk.StringVar()
        self.query_time.set("Ready")
        self.transaction_status.set("No active transaction")
        self.script_tabs = {}
        self.current_db: Optional[Database] = None
        self.current_collection: Optional[Collection] = None
        self.current_script_tab = None
        self.auth_manager = AuthManager()
        self.current_user = None
        self._create_login_dialog()
        # Set window icon if available
        try:
            icon_path = 'C:/Users/3 Stars Laptop/Desktop/DB task/icon.png'
            self.icon_image = tk.PhotoImage(file=icon_path)
            self.wm_iconphoto(True, self.icon_image)
        except Exception as e:
            logger.log_operation(
                "GUI_ICON",
                "SET_ICON",
                "FAILED",
                f"Failed to load icon.png: {str(e)}"
            )
            print(f"Error loading icon.png: {str(e)}")

        self._configure_theme()
        self._create_menu_bar()
        self._create_widgets()
        self._refresh_databases()
        logger.log_operation(
            "GUI_INIT",
            "STATUS",
            "SUCCESS",
            "Initialized GUI"
        )
        self._update_transaction_status_in_info()
    def _create_login_dialog(self):
        
        self.login_dialog = Toplevel(self)
        self.login_dialog.title("Login to Database System")
        self.login_dialog.geometry("400x370")
        self.login_dialog.resizable(False, False)
        
        # Center the dialog on screen
        window_width = self.login_dialog.winfo_reqwidth()
        window_height = self.login_dialog.winfo_reqheight()
        position_right = int(self.login_dialog.winfo_screenwidth()/2 - window_width/2)
        position_down = int(self.login_dialog.winfo_screenheight()/2 - window_height/2)
        self.login_dialog.geometry(f"+{position_right}+{position_down}")
        
        # Brown theme styling
        bg_color = "#f5e9dc"  # Very light brown/cream
        accent_color = "#a67c52"  # Medium brown
        text_color = "#4a3c30"  # Dark brown text
        entry_bg = "#f0e0c9"  # Slightly darker cream
        highlight_color = "#c9a87c"  # Light medium brown
        
        self.login_dialog.configure(bg=bg_color)
        
        # Header frame with logo/text
        header_frame = tk.Frame(self.login_dialog, bg=bg_color)
        header_frame.pack(pady=20, fill='x')
        
        tk.Label(
            header_frame, 
            text="DATABASE SYSTEM", 
            font=('Segoe UI', 16, 'bold'), 
            fg=accent_color, 
            bg=bg_color
        ).pack()
        
        tk.Label(
            header_frame, 
            text="Please login to continue", 
            font=('Segoe UI', 10), 
            fg=text_color, 
            bg=bg_color
        ).pack(pady=(5, 20))
        
        # Form frame
        form_frame = tk.Frame(self.login_dialog, bg=bg_color)
        form_frame.pack(padx=40, pady=10, fill='x')
        
        # Username field
        tk.Label(
            form_frame, 
            text="Username:", 
            font=('Segoe UI', 9), 
            fg=text_color, 
            bg=bg_color,
            anchor='w'
        ).pack(fill='x', pady=(5, 0))
        
        self.username_entry = ttk.Entry(
            form_frame,
            font=('Segoe UI', 10),
            style='Login.TEntry'
        )
        self.username_entry.pack(fill='x', pady=5, ipady=5)
        
        # Password field
        tk.Label(
            form_frame, 
            text="Password:", 
            font=('Segoe UI', 9), 
            fg=text_color, 
            bg=bg_color,
            anchor='w'
        ).pack(fill='x', pady=(10, 0))
        
        self.password_entry = ttk.Entry(
            form_frame,
            show="*",
            font=('Segoe UI', 10),
            style='Login.TEntry'
        )
        self.password_entry.pack(fill='x', pady=5, ipady=5)
        
        # Login button
        login_btn = ttk.Button(
            form_frame,
            text="LOGIN",
            command=self._handle_login,
            style='Login.TButton'
        )
        login_btn.pack(fill='x', pady=20, ipady=5)
        
        # Footer
        footer_frame = tk.Frame(self.login_dialog, bg=bg_color)
        footer_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(
            footer_frame, 
            text="© 2023 Database System", 
            font=('Segoe UI', 8), 
            fg=text_color, 
            bg=bg_color
        ).pack()
        
        # Set focus to username field
        self.username_entry.focus_set()
        
        # Bind Enter key to login
        self.login_dialog.bind('<Return>', lambda e: self._handle_login())
        
        self.login_dialog.protocol("WM_DELETE_WINDOW", self.quit)
        self.login_dialog.transient(self)
        self.login_dialog.grab_set()
        
    
                    
    def _handle_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        try:
            self.current_user = self.auth_manager.authenticate(username, password)
            if self.current_user:
                self.login_dialog.destroy()
                self.deiconify()
                self._update_status_bar()
            else:
                messagebox.showerror("Error", "Invalid credentials")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            
    def _update_status_bar(self):
        if hasattr(self, 'status_bar'):
            self.status_bar.config(
                text=f"Logged in as {self.current_user.username} | Roles: {', '.join(self.current_user.roles)}"
            )


    def _update_transaction_status_in_info(self):
        """Update the transaction status in the Database Info tab."""
        self.info_text.delete(1.0, tk.END)
        status = f"Query Status: {self.query_time.get()}\nTransaction Status: {self.transaction_status.get()}"
        self.info_text.insert(tk.END, status)
        self.results_notebook.select(self.info_tab)
        logger.log_operation(
            "GUI_STATUS",
            "UPDATE",
            "SUCCESS",
            f"Status updated: {status}"
        )

    def _configure_theme(self):
        # Light brown color scheme
        self.bg_color = "#f5e9dc"  # Very light brown/cream
        self.secondary_bg = "#e8d5b5"  # Light brown
        self.text_color = "#4a3c30"  # Dark brown (almost black but not pure black)
        self.accent_color = "#a67c52"  # Medium brown
        self.highlight_color = "#c9a87c"  # Lighter medium brown
        self.success_color = "#8ba888"  # Muted green
        self.error_color = "#c77d7d"  # Muted red
        self.entry_bg = "#f0e0c9"  # Slightly darker cream

        style = ttk.Style(self)
        style.theme_use('clam')

        self.configure(bg=self.bg_color)
        style.configure('.', 
                    background=self.bg_color,
                    foreground=self.text_color,
                    font=('Segoe UI', 10))
        
        style.configure('TNotebook', background=self.secondary_bg)
        style.configure('TNotebook.Tab', 
                    padding=[15, 5], 
                    background=self.secondary_bg,
                    foreground=self.text_color,
                    font=('Segoe UI', 9, 'bold'))
        style.map('TNotebook.Tab', 
                background=[('selected', self.accent_color)],
                foreground=[('selected', '#ffffff')])  # White text when selected

        style.configure('Treeview',
                    background=self.entry_bg,
                    foreground=self.text_color,
                    fieldbackground=self.entry_bg,
                    rowheight=25,
                    bordercolor=self.secondary_bg,
                    borderwidth=1)
        style.map('Treeview', 
                background=[('selected', self.accent_color)],
                foreground=[('selected', '#ffffff')])  # White text when selected
        style.configure('Treeview.Heading',
                    background=self.secondary_bg,
                    foreground=self.text_color,
                    relief='flat',
                    font=('Segoe UI', 9, 'bold'))

        style.configure('TButton',
                    background=self.secondary_bg,
                    foreground=self.text_color,
                    padding=6,
                    relief='flat',
                    font=('Segoe UI', 9))
        style.map('TButton',
                background=[('active', self.highlight_color)],
                foreground=[('active', self.text_color)])

        style.configure('TEntry',
                    fieldbackground=self.entry_bg,
                    foreground=self.text_color,
                    insertcolor=self.text_color,
                    bordercolor=self.secondary_bg,
                    lightcolor=self.secondary_bg,
                    darkcolor=self.secondary_bg)
        style.configure('TCombobox',
                    fieldbackground=self.entry_bg,
                    foreground=self.text_color,
                    selectbackground=self.highlight_color)

        style.configure('TPanedwindow', background=self.bg_color)

        style.configure('Vertical.TScrollbar', 
                    background=self.secondary_bg,
                    troughcolor=self.bg_color,
                    bordercolor=self.secondary_bg,
                    arrowcolor=self.text_color)
        style.configure('Horizontal.TScrollbar', 
                    background=self.secondary_bg,
                    troughcolor=self.bg_color,
                    bordercolor=self.secondary_bg,
                    arrowcolor=self.text_color)

        # Configure styles for login dialog
        style.configure('Login.TButton', 
                    font=('Segoe UI', 10, 'bold'),
                    foreground='#ffffff',
                    background=self.accent_color,
                    borderwidth=0)
        style.map('Login.TButton',
                background=[('active', self.highlight_color)])
        
        style.configure('Login.TEntry',
                    fieldbackground=self.entry_bg,
                    foreground=self.text_color,
                    insertcolor=self.text_color,
                    borderwidth=1,
                    relief='solid',
                    padding=5,
                    bordercolor=self.secondary_bg)
        
    
    def _create_menu_bar(self):
        menubar = tk.Menu(self, bg=self.secondary_bg, fg=self.text_color, 
                         activebackground=self.highlight_color, activeforeground=self.text_color)

        file_menu = tk.Menu(menubar, tearoff=0, bg=self.secondary_bg, fg=self.text_color,
                           activebackground=self.highlight_color, activeforeground=self.text_color)
        file_menu.add_command(label="New Script", command=self._new_script_tab)
        file_menu.add_command(label="Open Script", command=self._open_script)
        file_menu.add_command(label="Save Script", command=self._save_current_script)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0, bg=self.secondary_bg, fg=self.text_color,
                          activebackground=self.highlight_color, activeforeground=self.text_color)
        edit_menu.add_command(label="Cut", command=self._cut_text)
        edit_menu.add_command(label="Copy", command=self._copy_text)
        edit_menu.add_command(label="Paste", command=self._paste_text)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        help_menu = tk.Menu(menubar, tearoff=0, bg=self.secondary_bg, fg=self.text_color,
                          activebackground=self.highlight_color, activeforeground=self.text_color)
        help_menu.add_command(label="View Commands", command=self._show_help)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    def _create_widgets(self):
        self.main_container = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.sidebar = ttk.Frame(self.main_container, width=250, style='TFrame')
        self.main_container.add(self.sidebar)

        self.db_tree = ttk.Treeview(self.sidebar, style='Treeview')
        self.db_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.db_tree.heading("#0", text="Databases", anchor=tk.W)
        self.db_tree.bind("<<TreeviewSelect>>", self._on_db_tree_select)

        self.right_pane = ttk.PanedWindow(self.main_container, orient=tk.VERTICAL)
        self.main_container.add(self.right_pane)

        self.script_notebook = ttk.Notebook(self.right_pane)
        self.right_pane.add(self.script_notebook, weight=1)
        self.script_notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self._new_script_tab()

        self.results_frame = ttk.Frame(self.right_pane)
        self.right_pane.add(self.results_frame, weight=1)

        self.results_notebook = ttk.Notebook(self.results_frame)
        self.results_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.documents_tab = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.documents_tab, text="Documents")
        
        doc_frame = ttk.Frame(self.documents_tab)
        doc_frame.pack(fill=tk.BOTH, expand=True)
        
        y_scroll = ttk.Scrollbar(doc_frame)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        x_scroll = ttk.Scrollbar(doc_frame, orient=tk.HORIZONTAL)
        x_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.document_list = ttk.Treeview(doc_frame, show="headings",
                                        yscrollcommand=y_scroll.set,
                                        xscrollcommand=x_scroll.set)
        self.document_list.pack(fill=tk.BOTH, expand=True)
        
        y_scroll.config(command=self.document_list.yview)
        x_scroll.config(command=self.document_list.xview)

        self.aggregation_tab = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.aggregation_tab, text="Aggregation")
        
        agg_frame = ttk.Frame(self.aggregation_tab)
        agg_frame.pack(fill=tk.BOTH, expand=True)
        
        y_scroll_agg = ttk.Scrollbar(agg_frame)
        y_scroll_agg.pack(side=tk.RIGHT, fill=tk.Y)
        
        x_scroll_agg = ttk.Scrollbar(agg_frame, orient=tk.HORIZONTAL)
        x_scroll_agg.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.aggregation_results = ttk.Treeview(agg_frame, show="headings",
                                              yscrollcommand=y_scroll_agg.set,
                                              xscrollcommand=x_scroll_agg.set)
        self.aggregation_results.pack(fill=tk.BOTH, expand=True)
        
        y_scroll_agg.config(command=self.aggregation_results.yview)
        x_scroll_agg.config(command=self.aggregation_results.xview)

        self.info_tab = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.info_tab, text="Database Info")
        self.info_text = scrolledtext.ScrolledText(
            self.info_tab, 
            wrap=tk.WORD, 
            bg="#4a3c30", 
            fg="#ffffff", 
            insertbackground="#ffffff", 
            font=('Consolas', 10),
            padx=10,
            pady=10
        )
        self.info_text.pack(fill=tk.BOTH, expand=True)

    def _new_script_tab(self, filename="Untitled", content=""):
        tab_frame = ttk.Frame(self.script_notebook)
        
        # Create a unique ID for this tab
        tab_id = str(tab_frame.winfo_id())
        
        query_entry = scrolledtext.ScrolledText(
            tab_frame, 
            wrap=tk.WORD, 
            height=8, 
            bg="#4a3c30", 
            fg="#dcdcdc",
            insertbackground="#ffffff", 
            font=("Consolas", 11),
            padx=10,
            pady=10,
            highlightthickness=0,
            bd=0
        )
        query_entry.pack(fill=tk.BOTH, expand=True)
        
        if content:
            query_entry.insert(tk.END, content)

        button_frame = ttk.Frame(tab_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        execute_button = ttk.Button(
            button_frame, 
            text="Execute", 
            command=lambda: self._execute_query_from_tab(tab_id),
            style='TButton'
        )
        execute_button.pack(side=tk.LEFT, padx=5)

        status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            button_frame, 
            textvariable=status_var, 
            relief=tk.SUNKEN, 
            anchor=tk.W,
            style='TLabel'
        )
        status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Store tab data
        self.script_tabs[tab_id] = {
            'frame': tab_frame,
            'entry': query_entry,
            'status': status_var,
            'filename': filename,
            'modified': False
        }

        display_name = f"{self._shorten_filename(filename)}   ✕"
        self.script_notebook.add(tab_frame, text=display_name)
        self.script_notebook.select(tab_frame)
        
        # Update current tab reference
        self.current_script_tab = tab_id
        
        # Create a custom close button instead of using the text symbol
        close_btn = ttk.Button(tab_frame, text="✕", width=2, 
                            command=lambda: self._close_script_tab(tab_id),
                            style='TButton')
        close_btn.place(relx=1.0, rely=0.0, anchor='ne', x=-5, y=5)

    def _on_tab_changed(self, event):
        """Handle tab changes to update current_script_tab"""
        if not self.script_tabs:
            self.current_script_tab = None
            return
            
        # Get currently selected tab widget
        selected_tab = self.script_notebook.select()
        if not selected_tab:
            return
            
        # Find which tab_id corresponds to this widget
        for tab_id, tab_data in self.script_tabs.items():
            if str(tab_data['frame']) == selected_tab:
                self.current_script_tab = tab_id
                break

    def _close_script_tab(self, tab_id):
        if tab_id not in self.script_tabs:
            return
            
        tab_data = self.script_tabs[tab_id]
        
        # Check if tab needs saving
        if tab_data['modified']:
            if not messagebox.askyesno("Save Changes", f"Save changes to {tab_data['filename']} before closing?"):
                return
        
        # Remove the tab
        self.script_notebook.forget(tab_data['frame'])
        del self.script_tabs[tab_id]
        
        # Update current tab reference
        if self.current_script_tab == tab_id:
            if self.script_tabs:
                # Switch to another tab
                self.current_script_tab = next(iter(self.script_tabs))
                self.script_notebook.select(self.script_tabs[self.current_script_tab]['frame'])
            else:
                self.current_script_tab = None
                # Create new empty tab if we closed the last one
                self._new_script_tab()
                

        
    def _on_tab_click(self, event):
        x, y = event.x, event.y
        tab_index = self.script_notebook.index(f"@{x},{y}")
        bbox = self.script_notebook.bbox(tab_index)

        if not bbox:
            return

        tab_text = self.script_notebook.tab(tab_index, "text")

        # Estimate close button area (rightmost ~20px of tab)
        if tab_text.endswith("✕") and x >= bbox[0] + bbox[2] - 20:
            for tid, data in self.script_tabs.items():
                expected_text = f"{data['filename']}   ✕"
                if self.script_notebook.tab(data['frame'], "text") == expected_text:
                    self._close_script_tab(tid)
                    break

    def _execute_query_from_tab(self, tab_id):
        if tab_id not in self.script_tabs:
            return
        
        tab = self.script_tabs[tab_id]
        query_text = tab['entry'].get("1.0", tk.END).strip()
        
        if not query_text or query_text.startswith("#"):
            return
        
        tab['status'].set("Executing...")
        self.update()  # Force UI update
        
        try:
            parsed = Query.parse(query_text)
            operation = parsed["operation"]
            start_time = time.perf_counter()
            
            # Execute the operation
            operation_method = getattr(self, f"_handle_{operation}", None)
            if operation_method:
                # Remove operation from parsed dict to pass remaining as kwargs
                operation_args = {k: v for k, v in parsed.items() if k != "operation"}
                operation_method(**operation_args)
            else:
                raise ValueError(f"Unsupported operation: {operation}")
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            tab['status'].set(f"Operation completed in {elapsed_ms:.2f}ms")
            
        except Exception as e:
            tab['status'].set(f"Error: {str(e)}")
            self.transaction_status.set("No active transaction" if not (self.current_db and self.current_db._active_transaction) 
                                    else f"Transaction {self.current_db._active_transaction} active")
            self._update_transaction_status_in_info()
            messagebox.showerror("Query Error", str(e))
            logger.log_operation(
                "GUI_QUERY_EXECUTE",
                "ERROR",
                "FAILED",
                f"query:{query_text}, error:{str(e)}"
            )
            
    def _save_current_script(self):
        if not self.current_script_tab:
            return
        tab = self.script_tabs[self.current_script_tab]
        content = tab['entry'].get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("Warning", "No content to save")
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".dbq",
            filetypes=[("Database Script", "*.dbq"), ("All Files", "*.*")],
            initialfile=tab['filename']
        )
        if filepath:
            try:
                with open(filepath, 'w') as f:
                    f.write(content)
                new_filename = os.path.basename(filepath)
                tab['filename'] = new_filename
                tab['modified'] = False
                display_name = f"{self._shorten_filename(new_filename)}   ✕"
                self.script_notebook.tab(tab['frame'], text=display_name)
                tab['status'].set(f"Script saved: {new_filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save script: {str(e)}")

    def _shorten_filename(self, filename: str, max_length=20) -> str:
        return (filename[:max_length] + "...") if len(filename) > max_length else filename

    def _open_script(self):
        filepath = filedialog.askopenfilename(
            defaultextension=".dbq",
            filetypes=[("Database Script", "*.dbq"), ("All Files", "*.*")]
        )
        if filepath:
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                filename = os.path.basename(filepath)
                self._new_script_tab(filename, content)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open script: {str(e)}")

    def _cut_text(self):
        if self.current_script_tab:
            widget = self.script_tabs[self.current_script_tab]['entry']
            widget.event_generate("<<Cut>>")

    def _copy_text(self):
        if self.current_script_tab:
            widget = self.script_tabs[self.current_script_tab]['entry']
            widget.event_generate("<<Copy>>")

    def _paste_text(self):
        if self.current_script_tab:
            widget = self.script_tabs[self.current_script_tab]['entry']
            widget.event_generate("<<Paste>>")

    def _show_help(self):
        """Display a help window with all commands and their descriptions."""
        help_window = Toplevel(self)
        help_window.title("Help - Command Reference")
        help_window.geometry("1000x700")  # Larger window to accommodate table
        help_window.configure(bg=self.bg_color)

        # Create a notebook for different help views
        help_notebook = ttk.Notebook(help_window)
        help_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab 1: Command Reference (detailed view)
        ref_frame = ttk.Frame(help_notebook)
        help_notebook.add(ref_frame, text="Detailed Reference")

        # Tab 2: Quick Reference Table
        table_frame = ttk.Frame(help_notebook)
        help_notebook.add(table_frame, text="Quick Reference")

        # Create detailed reference view
        help_text = scrolledtext.ScrolledText(
            ref_frame,
            wrap=tk.WORD,
            bg="#252526",
            fg="#ffffff",
            insertbackground="#ffffff",
            font=('Consolas', 10),
            padx=10,
            pady=10
        )
        help_text.pack(fill=tk.BOTH, expand=True)

        # Command list with descriptions (updated to match query parser)
        commands = {
            # Transaction operations
            "BEGIN TX": "Start a new transaction.",
            "COMMIT": "Commit the current transaction.",
            "ROLLBACK": "Roll back the current transaction.",
            
            # Database operations
            "NAVA DATABASE BANAO <name>": "Create a new database with the given name.",
            "DATABASE NU MITAO <name>": "Delete the specified database.",
            "DATABASE CHALAO <name>": "Switch to the specified database.",
            
            # Collection operations
            "NAVA COLLECTION BANAO <name>": "Create a new collection in the current database.",
            "COLLECTION NU MITAO <name>": "Delete the specified collection from the current database.",
            
            # Index operations
            "INDEX BANAO <field> <collection>": "Create an index on the specified field in the given collection.",
            "INDEX DIKHAO <collection>": "List all indexes in the specified collection.",
            "INDEX CHALO KARO": "Enable indexing for the current collection.",
            "INDEX BAND KARO": "Disable indexing for the current collection.",
            
            # Document operations
            "DAKHIL KARO <collection> {document}": "Insert a single document into the specified collection.",
            "DAKHIL KARO <collection> [documents]": "Insert multiple documents into the specified collection.",
            "BADLO <collection> {query} {update}": "Update documents in the specified collection matching the query with the update operation.",
            "MITAO <collection> {query}": "Delete documents from the specified collection matching the query.",
            
            # Query operations
            "LABBO <collection> {query}": "Retrieve documents from the specified collection matching the query.",
            "LABBO <collection>": "Retrieve all documents from the specified collection (empty query).",
            
            # Aggregation
            "AGGREGATE IN <collection> [pipeline]": "Perform an aggregation operation on the specified collection with the given pipeline.",
            
            # Backup operations
            "BACKUP BANAO": "Create a backup of the current database.",
            "RESTORE KARO <name>": "Restore a database from a backup with the given name."
        }

        # Create quick reference table
        table_data = [
            ("English Command", "Punjabi Command", "Meaning"),
            ("CREATE DATABASE", "NAVA DATABASE BANAO", "Create a new database"),
            ("DROP DATABASE", "DATABASE NU MITAO", "Delete a database"),
            ("USE DATABASE", "DATABASE CHALAO", "Use/activate a database"),
            ("CREATE COLLECTION", "NAVA COLLECTION BANAO", "Create a new collection"),
            ("DROP COLLECTION", "COLLECTION NU MITAO", "Delete a collection"),
            ("INSERT", "DAKHIL KARO", "Insert data"),
            ("UPDATE", "BADLO", "Update/change data"),
            ("DELETE", "MITAO", "Delete data"),
            ("FIND", "LABBO", "Find/search data"),
            ("CREATE INDEX", "INDEX BANAO", "Create an index"),
            ("BEGIN TRANSACTION", "SHURU KARO", "Start a transaction"),
            ("COMMIT", "PAKKA KARO", "Confirm/commit changes"),
            ("ROLLBACK", "PICHHE HATO", "Rollback/undo changes"),
            ("BACKUP", "BACKUP BANAO", "Create a backup"),
            ("RESTORE", "RESTORE KARO", "Restore data")
        ]

        # Create table in the second tab
        table = ttk.Treeview(table_frame, columns=("english", "punjabi", "meaning"), show="headings")
        table.heading("english", text="English Command")
        table.heading("punjabi", text="Punjabi Command")
        table.heading("meaning", text="Meaning")
        
        # Configure column widths
        table.column("english", width=200, anchor=tk.W)
        table.column("punjabi", width=200, anchor=tk.W)
        table.column("meaning", width=400, anchor=tk.W)
        
        # Add data to table (skip header row)
        for row in table_data[1:]:
            table.insert("", tk.END, values=row)
        
        # Add scrollbars
        yscroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=table.yview)
        xscroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=table.xview)
        table.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        
        # Grid layout
        table.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        
        # Configure grid weights
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Populate the detailed help text with categorized commands
        help_text.insert(tk.END, "=== COMMAND REFERENCE ===\n\n")
        
        categories = {
            "Transaction Operations": ["BEGIN TX", "COMMIT", "ROLLBACK"],
            "Database Operations": ["NAVA DATABASE BANAO", "DATABASE NU MITAO", "DATABASE CHALAO"],
            "Collection Operations": ["NAVA COLLECTION BANAO", "COLLECTION NU MITAO"],
            "Index Operations": ["INDEX BANAO", "INDEX DIKHAO", "INDEX CHALO KARO", "INDEX BAND KARO"],
            "Document Operations": ["DAKHIL KARO", "BADLO", "MITAO"],
            "Query Operations": ["LABBO"],
            "Aggregation": ["AGGREGATE IN"],
            "Backup/Restore": ["BACKUP BANAO", "RESTORE KARO"]
        }

        for category, cmd_list in categories.items():
            help_text.insert(tk.END, f"◆ {category} ◆\n", "category")
            for cmd_key in cmd_list:
                full_cmd = next((c for c in commands.keys() if c.startswith(cmd_key)), None)
                if full_cmd:
                    help_text.insert(tk.END, f"\n{full_cmd}\n", "command")
                    help_text.insert(tk.END, f"  ➔ {commands[full_cmd]}\n")
            help_text.insert(tk.END, "\n")
        
        # Add JSON formatting examples
        help_text.insert(tk.END, "\n=== JSON FORMATTING EXAMPLES ===\n\n", "category")
        help_text.insert(tk.END, "Single document:\n", "command")
        help_text.insert(tk.END, '  {"name": "John", "age": 30, "active": true}\n\n')
        help_text.insert(tk.END, "Multiple documents:\n", "command")
        help_text.insert(tk.END, '  [{"name": "John"}, {"name": "Jane"}]\n\n')
        help_text.insert(tk.END, "Query with operators:\n", "command")
        help_text.insert(tk.END, '  {"age": {"$gt": 25}, "active": true}\n\n')
        help_text.insert(tk.END, "Update operation:\n", "command")
        help_text.insert(tk.END, '  {"$set": {"status": "active"}, "$inc": {"count": 1}}\n')

        # Configure tags for styling
        help_text.tag_config("category", foreground="#4ec9b0", font=('Consolas', 11, 'bold'))
        help_text.tag_config("command", foreground="#dcdcaa", font=('Consolas', 10, 'bold'))
        
        help_text.configure(state='disabled')  # Make it read-only

        # Add a close button
        close_button = ttk.Button(
            help_window, 
            text="Close", 
            command=help_window.destroy,
            style='TButton'
        )
        close_button.pack(pady=5)
        
    def _show_about(self):
        messagebox.showinfo("About", "A2Z Database Management System\nVersion 1.0")

    def _handle_begin_transaction(self):
        if not self.current_db:
            raise ValueError("No database selected. Use: USE DATABASE dbname")
        transaction_id = self.current_db.begin_transaction()
        self.transaction_status.set(f"Transaction {transaction_id} active")
        self.query_time.set(f"Transaction {transaction_id} started")
        self._update_transaction_status_in_info()
        logger.log_operation(
            "GUI_TRANSACTION",
            "BEGIN",
            "SUCCESS",
            f"database:{self.current_db.name}, transaction_id:{transaction_id}"
        )

    def _handle_commit(self):
        if not self.current_db:
            raise ValueError("No database selected. Use: USE DATABASE dbname")
        success = self.current_db.commit()
        self.transaction_status.set("No active transaction")
        self.query_time.set("Transaction committed" if success else "Commit failed")
        self._update_transaction_status_in_info()
        logger.log_operation(
            "GUI_TRANSACTION",
            "COMMIT",
            "SUCCESS" if success else "FAILED",
            f"database:{self.current_db.name}"
        )

    def _handle_rollback(self):
        if not self.current_db:
            raise ValueError("No database selected. Use: USE DATABASE dbname")
        success = self.current_db.rollback()
        self.transaction_status.set("No active transaction")
        self.query_time.set("Transaction rolled back" if success else "Rollback failed")
        self._update_transaction_status_in_info()
        logger.log_operation(
            "GUI_TRANSACTION",
            "ROLLBACK",
            "SUCCESS" if success else "FAILED",
            f"database:{self.current_db.name}"
        )
    @requires_auth(Permission.USE_DATABASE)
    def _handle_use_db(self, name):
        self.current_db = Database(name)
        self.current_collection = None
        self._refresh_databases()
        self.transaction_status.set(f"Transaction {self.current_db._active_transaction} active" if self.current_db._active_transaction else "No active transaction")
        self.query_time.set(f"Using database '{name}'")
        self._update_transaction_status_in_info()

    @requires_auth(Permission.CREATE_DATABASE)
    def _handle_create_db(self, name):
        Database(name)
        self._refresh_databases()
        self.transaction_status.set("No active transaction")
        self.query_time.set(f"Database '{name}' created")
        self._update_transaction_status_in_info()

    @requires_auth(Permission.CREATE_COLLECTION)
    def _handle_create_collection(self, name):
        if not self.current_db:
            raise ValueError("No database selected. Use: USE DATABASE dbname")
        self.current_db.create_collection(name)
        self._refresh_collections()
        self.query_time.set(f"Collection '{name}' created")
        self._update_transaction_status_in_info()

    @requires_auth(Permission.DROP_COLLECTION)
    def _handle_drop_collection(self, name):
        if not self.current_db:
            raise ValueError("No database selected. Use: USE DATABASE dbname")
        if messagebox.askyesno("Confirm", f"Delete collection '{name}'?"):
            self.current_db.drop_collection(name)
            if self.current_collection and self.current_collection.name == name:
                self.current_collection = None
            self._refresh_collections()
            self.query_time.set(f"Collection '{name}' deleted")
            self._update_transaction_status_in_info()

    def _on_db_tree_select(self, event):
        selected = self.db_tree.focus()
        if not selected:
            return
        item = self.db_tree.item(selected)
        text = item['text']
        if item['tags'] and 'database' in item['tags']:
            self._handle_use_db(text)
        elif item['tags'] and 'collection' in item['tags']:
            parent = self.db_tree.parent(selected)
            db_name = self.db_tree.item(parent)['text']
            self._handle_use_db(db_name)
            self._handle_find(text, {})

    def _refresh_databases(self):
        self.db_tree.delete(*self.db_tree.get_children())
        db_path = Path("db")
        if db_path.exists():
            for db_dir in sorted(db_path.iterdir()):
                if db_dir.is_dir():
                    db_node = self.db_tree.insert("", "end", 
                                              text=db_dir.name,
                                              tags=("database",))
                    if self.current_db and db_dir.name == self.current_db.name:
                        self.db_tree.item(db_node, open=True)
                        for col in sorted(Database(db_dir.name).list_collections()):
                            self.db_tree.insert(db_node, "end", 
                                            text=col,
                                            tags=("collection",))
                            if self.current_collection and col == self.current_collection.name:
                                self.db_tree.selection_set(self.db_tree.get_children(db_node)[-1])

    def _refresh_collections(self):
        if not self.current_db:
            return
        for child in self.db_tree.get_children():
            if self.db_tree.item(child)['text'] == self.current_db.name:
                for col in self.db_tree.get_children(child):
                    self.db_tree.delete(col)
                for col in sorted(self.current_db.list_collections()):
                    self.db_tree.insert(child, "end", 
                                     text=col,
                                     tags=("collection",))
                self.db_tree.item(child, open=True)
                break

    def _handle_insert_many(self, collection, documents):
        if not self.current_db:
            raise ValueError("No database selected. Use: USE DATABASE dbname")
        collection = self.current_db.get_collection(collection)
        if not collection:
            raise ValueError(f"Collection '{collection}' not found")
        doc_ids = collection.insert_many(documents)
        self._refresh_documents(collection)
        self.query_time.set(f"Inserted {len(doc_ids)} documents with IDs: {', '.join(doc_ids[:5])}" + 
                        ("..." if len(doc_ids) > 5 else ""))
        self._update_transaction_status_in_info()
    def _refresh_documents(self, collection):
        """Refresh the documents displayed in the Documents tab for the given collection."""
        if not collection:
            return
        documents = collection.find({})
        self._display_documents(documents)
        
    def _execute_query(self):
        # Note: This method is not used in the current implementation but kept for compatibility
        query_text = self.query_entry.get("1.0", tk.END).strip()
        if not query_text or query_text.startswith("#"):
            return
        try:
            start_time = time.perf_counter()
            parsed = Query.parse(query_text)
            operation = parsed["operation"]
            if operation == "begin_transaction":
                self._handle_begin_transaction()
            elif operation == "commit":
                self._handle_commit()
            elif operation == "rollback":
                self._handle_rollback()
            elif operation == "create_db":
                self._handle_create_db(parsed["name"])
            elif operation == "drop_db":
                self._handle_drop_db(parsed["name"])
            elif operation == "use_db":
                self._handle_use_db(parsed["name"])
            elif operation == "create_collection":
                self._handle_create_collection(parsed["name"])
            elif operation == "drop_collection":
                self._handle_drop_collection(parsed["name"])
            elif operation == "create_index":
                self._handle_create_index(parsed["field"], parsed["collection"])
            elif operation == "insert":
                self._handle_insert(parsed["collection"], parsed["document"])
            elif operation == "insert_many":
                self._handle_insert_many(parsed["collection"], parsed["documents"])
            elif operation == "update":
                self._handle_update(parsed["collection"], parsed["query"], parsed["update"])
            elif operation == "delete":
                self._handle_delete(parsed["collection"], parsed["query"])
            elif operation == "find":
                self._handle_find(parsed["collection"], parsed["query"])
            elif operation == "aggregate":
                self._handle_aggregate(parsed["collection"], parsed["pipeline"])
            elif operation == "backup":
                self._handle_backup(parsed["name"])
            elif operation == "restore":
                self._handle_restore(parsed["name"])
            elif operation == "list_indexes":
                self._handle_list_indexes(parsed["collection"])
            elif operation == "enable_indexing":
                self._handle_enable_indexing(parsed["enable"])
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self.query_time.set(f"Operation completed in {elapsed_ms:.2f}ms")
            self._update_transaction_status_in_info()
        except Exception as e:
            self.transaction_status.set("No active transaction" if not (self.current_db and self.current_db._active_transaction) else f"Transaction {self.current_db._active_transaction} active")
            self.query_time.set(f"Error: {str(e)}")
            self._update_transaction_status_in_info()
            messagebox.showerror("Query Error", str(e))
    
    @requires_auth(Permission.DROP_DATABASE)
    def _handle_drop_db(self, name):
        if messagebox.askyesno("Confirm", f"Delete database '{name}'?"):
            db = Database(name)
            db.drop_database()
            if self.current_db and self.current_db.name == name:
                self.current_db = None
                self.current_collection = None
                self.transaction_status.set("No active transaction")
            self._refresh_databases()
            self.query_time.set(f"Database '{name}' deleted")
            self._update_transaction_status_in_info()

    def _handle_create_index(self, field, collection):
        if not self.current_db:
            raise ValueError("No database selected. Use: USE DATABASE dbname")
        collection = self.current_db.get_collection(collection)
        if not collection:
            raise ValueError(f"Collection '{collection}' not found")
        collection.create_index(field)
        self.query_time.set(f"Index created on field '{field}' in collection '{collection}'")
        self._update_transaction_status_in_info()

    @requires_auth(Permission.INSERT_DOCUMENT)
    def _handle_insert(self, collection, document):  # Changed from collection_name to collection
        if not self.current_db:
            raise ValueError("No database selected. Use: USE DATABASE dbname")
        collection_obj = self.current_db.get_collection(collection)  # Changed variable name
        if not collection_obj:
            raise ValueError(f"Collection '{collection}' not found")
        doc_id = collection_obj.insert_one(document)
        self._refresh_documents(collection_obj)
        self.query_time.set(f"Document inserted with ID: {doc_id}")
        self._update_transaction_status_in_info()

    def _handle_update(self, collection, query, update):
        if not self.current_db:
            raise ValueError("No database selected. Use: USE DATABASE dbname")
        collection = self.current_db.get_collection(collection)
        if not collection:
            raise ValueError(f"Collection '{collection}' not found")
        if "$set" not in update and "$unset" not in update:
            update = {"$set": update}
        count = collection.update_many(query, update)
        self._refresh_documents(collection)
        self.query_time.set(f"Updated {count} documents")
        self._update_transaction_status_in_info()

    def _handle_delete(self, collection, query):
        if not self.current_db:
            raise ValueError("No database selected. Use: USE DATABASE dbname")
        collection = self.current_db.get_collection(collection)
        if not collection:
            raise ValueError(f"Collection '{collection}' not found")
        if messagebox.askyesno("Confirm", f"Delete documents matching {query}?"):
            count = collection.delete_many(query)
            self._refresh_documents(collection)
            self.query_time.set(f"Deleted {count} documents")
            self._update_transaction_status_in_info()

    def _handle_find(self, collection, query):
        if not self.current_db:
            raise ValueError("No database selected. Use: USE DATABASE dbname")
        
        collection = self.current_db.get_collection(collection)
        if not collection:
            raise ValueError(f"Collection '{collection}' not found")
        
        self.current_collection = collection
        
        # Time the query execution
        start_time = time.perf_counter()
        documents = collection.find(query)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        # Determine if index was used
        used_index = False
        if collection.indexing_enabled and len(query) == 1:
            field = next(iter(query))
            if field in collection.indexes:
                used_index = True
        
        # Display results
        self._display_documents(documents)
        
        # Build performance message
        perf_msg = f"Found {len(documents)} documents in {elapsed_ms:.2f}ms"
        if used_index:
            perf_msg += " (used index)"
        else:
            perf_msg += " (full scan)"
        
        self.query_time.set(perf_msg)
        self._update_transaction_status_in_info()
        
    def _handle_aggregate(self, collection, pipeline):
        if not self.current_db:
            raise ValueError("No database selected. Use: USE DATABASE dbname")
        collection = self.current_db.get_collection(collection)
        if not collection:
            raise ValueError(f"Collection '{collection}' not found")
        results = collection.aggregate(pipeline)
        self._display_aggregation(results)
        self.query_time.set(f"Aggregation completed with {len(results)} results")
        self._update_transaction_status_in_info()

    def _handle_backup(self, name):
        print("Backup handler called with name:", name)  # Debug line
        from core.backup_manager import BackupManager
        backup_manager = BackupManager()
        backup_path = backup_manager.create_backup(name)
        self.query_time.set(f"Backup created at: {backup_path}")
        self._update_transaction_status_in_info()

    def _handle_restore(self, name):
        from core.backup_manager import BackupManager
        backup_manager = BackupManager()
        backup_manager.restore_backup(name, name)
        self._refresh_databases()
        self.query_time.set(f"Database '{name}' restored")
        self._update_transaction_status_in_info()

    def _handle_list_indexes(self, collection):
        if not self.current_db:
            raise ValueError("No database selected. Use: USE DATABASE dbname")
        collection = self.current_db.get_collection(collection)
        if not collection:
            raise ValueError(f"Collection '{collection}' not found")
        indexes = collection.list_indexes()
        self._display_info("\n".join(
            f"{idx['name']}: {idx['key']}" for idx in indexes
        ))
        self.query_time.set(f"Found {len(indexes)} indexes")
        self._update_transaction_status_in_info()

    def _handle_enable_indexing(self, enable):
        if not self.current_collection:
            raise ValueError("No collection selected")
        self.current_collection.enable_indexing(enable)
        self.indexing_enabled = enable
        status = "enabled" if enable else "disabled"
        self.query_time.set(f"Indexing {status}")
        self._update_transaction_status_in_info()

    def _display_documents(self, documents):
        self.document_list.delete(*self.document_list.get_children())
        for col in self.document_list["columns"]:
            self.document_list.heading(col, text="")
            self.document_list.column(col, width=0)
        self.document_list["columns"] = []
        self.results_notebook.select(self.documents_tab)
        if not documents:
            return
        columns = set()
        for doc in documents:
            columns.update(doc.keys())
        columns = sorted(columns)
        self.document_list["columns"] = columns
        self.document_list.column("#0", width=0, stretch=tk.NO)
        for col in columns:
            self.document_list.heading(col, text=col)
            self.document_list.column(col, width=100, anchor=tk.W)
        for doc in documents:
            values = [str(doc.get(col, "")) for col in columns]
            self.document_list.insert("", "end", values=values)

    def _display_aggregation(self, results):
        self.aggregation_results.delete(*self.aggregation_results.get_children())
        self.results_notebook.select(self.aggregation_tab)
        if not results:
            return
        columns = list(results[0].keys())
        self.aggregation_results["columns"] = columns
        for col in columns:
            self.aggregation_results.heading(col, text=col)
            self.aggregation_results.column(col, width=100)
        for doc in results:
            values = [str(doc.get(col, "")) for col in columns]
            self.aggregation_results.insert("", "end", values=values)

    def _display_info(self, info):
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, info)
        self.results_notebook.select(self.info_tab)
