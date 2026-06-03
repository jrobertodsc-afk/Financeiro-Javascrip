import customtkinter as ctk
from gui.app_main import ComSystemApp

def trigger_and_inspect(app):
    print("Before click:", app._sidebar.winfo_width())
    app._sidebar._toggle_collapse()
    
    def check():
        print("After click:", app._sidebar.winfo_width())
        print("Col 0 weight:", app._body.grid_columnconfigure(0))
        print("Col 2 weight:", app._body.grid_columnconfigure(2))
        app.destroy()
        
    app.after(500, check)

app = ComSystemApp()
app.after(1000, lambda: trigger_and_inspect(app))
app.mainloop()
