import os
import subprocess
import sys
import platform

# Function to create a virtual environment
def create_venv():
    print("Creating virtual environment...")
    subprocess.check_call([sys.executable, "-m", "venv", "venv"])

# Function to activate the virtual environment
def activate_venv():
    system_platform = platform.system().lower()
    
    if system_platform == 'windows':
        activate_script = ".\\venv\\Scripts\\activate"
    else:
        activate_script = "source ./venv/bin/activate"
    
    print(f"Activating virtual environment: {activate_script}")
    
    # Here, we can just print the command because activating the venv
    # within the script would only work interactively.
    print(f"Run the following command to activate the virtual environment:")
    print(f"  {activate_script}")
    
# Function to install dependencies
def install_dependencies():
    print("Installing dependencies: Werkzeug and Flask...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "werkzeug", "flask"])

def main():
    create_venv()          # Create the virtual environment
    activate_venv()        # Prompt user on how to activate the virtual environment
    install_dependencies() # Install required packages

if __name__ == "__main__":
    main()
