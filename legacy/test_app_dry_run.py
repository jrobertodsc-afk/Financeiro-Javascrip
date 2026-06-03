import os
import sys
import customtkinter as ctk

# Configure stdout and stderr to use UTF-8 coding to prevent Windows CP1252 encode errors
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass  # In case reconfigure isn't supported in this specific execution context

# Ensure workspace is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("Initializing ComSystemApp in dry-run mode...")
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    from gui.app_main import ComSystemApp
    
    try:
        app = ComSystemApp()
        print("[ OK ] App instance created successfully.")
        
        # Test building each tab
        tabs = list(app.tab_configs.keys())
        for tab_name in tabs:
            print(f"Building tab: {tab_name}...")
            app._navigate_to(tab_name, animate=False)
            app.update()
            app.update_idletasks()
            print(f"[ OK ] Tab '{tab_name}' built successfully.")
            
        print("\n=== SUCCESS: All tabs initialized, built, and rendered without any errors! ===")
        app.destroy()
        sys.exit(0)
    except Exception as e:
        import traceback
        print("\n[ ERROR ] Exception occurred during dry-run execution:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
