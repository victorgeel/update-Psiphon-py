import subprocess
import os
import sys
import time
import json
import shutil

# --- Configuration ---
# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__)) 
# Define config file path relative to the script directory
config_file_path = os.path.join(script_dir, "client.config")
# Define binary path where 'go install' places it
psiphon_binary_path = os.path.expanduser("~/go/bin/ConsoleClient") 
# Psiphon ConsoleClient package path for 'go install'
psiphon_package_url = "github.com/Psiphon-Labs/psiphon-tunnel-core/ConsoleClient"

# Option to use proxychains-ng if available
use_proxychains = True # Set to False if you don't want to use proxychains even if installed
# --- End Configuration ---

def run_command(command_list, check=True, capture_output=False, text=True, cwd=None, env=None):
    """Helper function to run shell commands."""
    print(f">>> Running command: {' '.join(command_list)}")
    # Ensure GOPATH/GOBIN are potentially set if needed, inherit environment
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
        
    # Make sure GOBIN is in PATH if go install is used
    go_bin_path = os.path.expanduser("~/go/bin")
    if go_bin_path not in merged_env.get("PATH", ""):
         print(f"--- Adding {go_bin_path} to PATH for this command execution")
         merged_env["PATH"] = f"{go_bin_path}:{merged_env.get('PATH', '')}"
         
    try:
        result = subprocess.run(command_list, 
                                check=check,        
                                capture_output=capture_output, 
                                text=text,
                                cwd=cwd,
                                env=merged_env) # Pass environment
        if capture_output:
             if result.stdout and result.stdout.strip(): print(result.stdout)
             if result.stderr and result.stderr.strip(): print(f"[stderr]: {result.stderr.strip()}", file=sys.stderr)
        return result
    except FileNotFoundError:
        print(f"[Error] Command not found: {command_list[0]}. Is it installed and in PATH?", file=sys.stderr)
        return None
    except subprocess.CalledProcessError as e:
        print(f"[Error] Command failed with exit code {e.returncode}: {' '.join(command_list)}", file=sys.stderr)
        if capture_output:
             if e.stderr and e.stderr.strip(): print(f"[stderr]: {e.stderr.strip()}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[Error] An unexpected error occurred while running command: {e}", file=sys.stderr)
        return None

def install_packages():
    """Check and install required Termux packages."""
    packages_needed = []
    if not shutil.which("git"): packages_needed.append("git")
    if not shutil.which("go"): packages_needed.append("golang")
        
    if packages_needed:
        package_string = " ".join(packages_needed)
        print(f"--- Required package(s) missing: {package_string}")
        try:
            result = run_command(["pkg", "install", "-y"] + packages_needed)
            if result is None or result.returncode != 0:
                 print("[Error] Failed to install required packages. Please install them manually.", file=sys.stderr)
                 print(f"Command: pkg install {package_string}", file=sys.stderr)
                 sys.exit(1)
            print(f"--- Successfully installed: {package_string}")
        except Exception as e:
             print(f"[Error] Failed during package installation: {e}", file=sys.stderr)
             sys.exit(1)
    else:
        print("--- Required packages (git, golang) are already installed.")

def install_psiphon_binary():
    """Installs the Psiphon ConsoleClient binary using 'go install'."""
    # This function now uses the modern 'go install' command
    print(f"--- Attempting to install psiphon binary using 'go install' to {os.path.expanduser('~/go/bin/')}...")
    
    install_command = ["go", "install", f"{psiphon_package_url}@latest"]
    result = run_command(install_command) 
    
    if result is None or result.returncode != 0:
        print("[Error] Failed to install Psiphon binary using 'go install'.", file=sys.stderr)
        print("--- Please check your Go installation and network connection.", file=sys.stderr)
        run_command(["go", "env"], check=False) 
        return False
        
    if not os.path.exists(psiphon_binary_path):
         print(f"[Error] 'go install' completed but binary not found at expected path: {psiphon_binary_path}", file=sys.stderr)
         print("--- Check your $GOPATH and $GOBIN environment variables.", file=sys.stderr)
         run_command(["go", "env", "GOPATH", "GOBIN"], check=False)
         return False
         
    print(f"--- Successfully installed binary to: {psiphon_binary_path}")
    try:
         os.chmod(psiphon_binary_path, 0o755)
    except Exception as e:
         print(f"[Warning] Could not set execute permission on {psiphon_binary_path}: {e}", file=sys.stderr)
         
    return True

# --- Main Script Logic ---
print(">>> Starting Psiphon Runner Script...")

# 1. Ensure required packages are installed
install_packages()

# 2. Check if Psiphon binary exists (at the 'go install' path), install if not
if not os.path.exists(psiphon_binary_path):
    print(f"--- Psiphon binary not found at '{psiphon_binary_path}'. Attempting to install...")
    if not install_psiphon_binary(): # Call the function using 'go install'
        print("[Critical] Failed to obtain Psiphon binary. Exiting.", file=sys.stderr)
        sys.exit(1)
else:
    print(f"--- Found existing Psiphon binary: {psiphon_binary_path}")
    # You might want to add a way to force re-installation/update here later
    # For example: check for a command line argument like --update
    # if '--update' in sys.argv:
    #    print("--- '--update' flag detected. Forcing re-installation...")
    #    if not install_psiphon_binary():
    #         print("[Error] Failed to update Psiphon binary. Using existing one if possible.")
    #    # Continue even if update fails, maybe? Or exit? Decide based on need.


# 3. Check or create config file (in the script's directory)
if not os.path.exists(config_file_path):
     print(f"--- Configuration file '{config_file_path}' not found. Creating default config.")
     try:
          default_config = {
               "LocalSocksProxyPort": 1080,
               "LocalHttpProxyPort": 8080
          }
          with open(config_file_path, 'w') as f:
               json.dump(default_config, f, indent=4)
          print(f">>> Created default '{config_file_path}'. You may edit it if needed.")
     except Exception as e:
          print(f"[Error] Failed to create default config file: {e}", file=sys.stderr)
          sys.exit(1)
else:
     print(f"--- Using existing configuration file: {config_file_path}")

# 4. Prepare the command to run Psiphon (potentially with proxychains)
command_to_run = []
proxychains_path = shutil.which("proxychains-ng")

if use_proxychains and proxychains_path:
     command_to_run.append(proxychains_path)
     print(f"--- Will use proxychains-ng found at: {proxychains_path}")
     print("--- Make sure '/data/data/com.termux/files/usr/etc/proxychains.conf' is configured correctly.")
elif use_proxychains:
     print("[Warning] 'use_proxychains' is True, but 'proxychains-ng' command was not found in PATH. Psiphon will run directly.")
     
# Use the correct binary path from 'go install'
command_to_run.extend([psiphon_binary_path, "-config", config_file_path]) 

# 5. Run Psiphon
process = None 
try:
    print(f">>> Executing command: {' '.join(command_to_run)}") 
    process = subprocess.Popen(command_to_run, 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True, 
                               bufsize=1, 
                               universal_newlines=True) 

    print(f">>> Psiphon started with Process ID: {process.pid}")
    print(">>> Monitoring Psiphon output (Press Ctrl+C to stop)...")
    
    # Read and print output/errors line by line (Same as before)
    while True:
        output_line = process.stdout.readline()
        if output_line: 
            print(f"[Psiphon Output]: {output_line.strip()}")
            if "ListeningSocksProxyPort" in output_line: print(">>> SOCKS Proxy is listening.")
            if "ListeningHttpProxyPort" in output_line: print(">>> HTTP Proxy is listening.")
        error_line = process.stderr.readline()
        if error_line: print(f"[Psiphon Error]: {error_line.strip()}", file=sys.stderr)
        return_code = process.poll()
        if return_code is not None:
            print(f">>> Psiphon process terminated unexpectedly with exit code: {return_code}")
            remaining_err = process.stderr.read()
            if remaining_err: print(f"[Psiphon Final Error]: {remaining_err.strip()}", file=sys.stderr)
            break 
        if not output_line and not error_line: time.sleep(0.5)

except FileNotFoundError:
    executable_not_found = command_to_run[0] 
    print(f"[Critical Error] Command '{executable_not_found}' not found or not executable. Check PATH and permissions.", file=sys.stderr)
    if not os.path.exists(psiphon_binary_path):
         print(f"--- Also note: The binary expected at '{psiphon_binary_path}' does not exist. 'go install' might have failed.", file=sys.stderr)
    sys.exit(1)
except KeyboardInterrupt:
    print("\n>>> Ctrl+C detected. Stopping Psiphon process...")
    if process and process.poll() is None: 
        process.terminate() 
        try:
            process.wait(timeout=5) 
            print(">>> Psiphon process stopped (Terminated).")
        except subprocess.TimeoutExpired:
            print(">>> Psiphon process did not terminate gracefully. Killing...")
            process.kill() 
            print(">>> Psiphon process stopped (Killed).")
    else:
         print(">>> Psiphon process was not running or already stopped.")
    sys.exit(0) 
except Exception as e:
    print(f"[Critical Error] An unexpected error occurred: {e}", file=sys.stderr)
    if process and process.poll() is None:
         print(">>> Attempting to kill Psiphon process due to error...")
         process.kill()
    sys.exit(1) 
