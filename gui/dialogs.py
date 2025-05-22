import tkinter as tk
from tkinter import Toplevel, simpledialog
from tkinter import ttk, messagebox
from core.auth import AuthManager
from core.permissions import PermissionManager
class DocumentDialog(simpledialog.Dialog):
    def __init__(self, parent, title=None, document=None):
        self.document = document or {}
        super().__init__(parent, title)
        self.geometry("400x300")
        self.auth_manager = AuthManager
        
        # User list
        self.user_listbox = tk.Listbox(self)
        self.user_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self._refresh_user_list()
        
        # Buttons frame
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            button_frame,
            text="Add User",
            command=self._add_user
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            button_frame,
            text="Delete User",
            command=self._delete_user
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            button_frame,
            text="Edit Roles",
            command=self._edit_roles
        ).pack(side=tk.LEFT, padx=2)
        
    
    def body(self, master):
        tk.Label(master, text="Document JSON:").grid(row=0)
        
        self.text = tk.Text(master, width=50, height=20)
        self.text.grid(row=1, padx=5, pady=5)
        
        if self.document:
            import json
            self.text.insert(tk.END, json.dumps(self.document, indent=2))
        
        return self.text
    
    def apply(self):
        import json
        text = self.text.get("1.0", tk.END)
        try:
            self.result = json.loads(text)
        except json.JSONDecodeError:
            self.result = None
            
    def _refresh_user_list(self):
        self.user_listbox.delete(0, tk.END)
        for username in self.auth_manager.users:
            self.user_listbox.insert(tk.END, username)
    
    def _add_user(self):
        dialog = Toplevel(self)
        dialog.title("Add User")
        
        ttk.Label(dialog, text="Username:").grid(row=0, column=0, padx=5, pady=5)
        username_entry = ttk.Entry(dialog)
        username_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(dialog, text="Password:").grid(row=1, column=0, padx=5, pady=5)
        password_entry = ttk.Entry(dialog, show="*")
        password_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(dialog, text="Roles:").grid(row=2, column=0, padx=5, pady=5)
        roles_entry = ttk.Entry(dialog)
        roles_entry.grid(row=2, column=1, padx=5, pady=5)
        roles_entry.insert(0, "read")  # Default role
        
        def save():
            try:
                roles = [r.strip() for r in roles_entry.get().split(",")]
                self.auth_manager.create_user(
                    username_entry.get(),
                    password_entry.get(),
                    roles
                )
                self._refresh_user_list()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        ttk.Button(dialog, text="Save", command=save).grid(row=3, columnspan=2, pady=10)
    
    def _delete_user(self):
        selection = self.user_listbox.curselection()
        if selection:
            username = self.user_listbox.get(selection[0])
            if messagebox.askyesno("Confirm", f"Delete user {username}?"):
                try:
                    self.auth_manager.delete_user(username)
                    self._refresh_user_list()
                except Exception as e:
                    messagebox.showerror("Error", str(e))
    
    def _edit_roles(self):
        selection = self.user_listbox.curselection()
        if selection:
            username = self.user_listbox.get(selection[0])
            user = self.auth_manager.users.get(username)
            
            dialog = Toplevel(self)
            dialog.title(f"Edit Roles for {username}")
            
            # Create checkboxes for each role
            role_vars = {}
            for i, role in enumerate(PermissionManager().roles.keys()):
                var = tk.BooleanVar(value=role in user.roles)
                role_vars[role] = var
                cb = ttk.Checkbutton(dialog, text=role, variable=var)
                cb.grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            
            def save():
                try:
                    selected_roles = [role for role, var in role_vars.items() if var.get()]
                    self.auth_manager.update_user_roles(username, selected_roles)
                    dialog.destroy()
                except Exception as e:
                    messagebox.showerror("Error", str(e))
            
            ttk.Button(dialog, text="Save", command=save).grid(
                row=len(role_vars)+1, column=0, pady=10
            )