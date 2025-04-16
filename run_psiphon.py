import subprocess
import os
import sys
import time
import json
import shutil

# --- Configuration ---
# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__)) 
# Define paths relative to the script directory
psiphon_binary_path = os.path.join(script_dir, "psiphon-tunnel-core") 
config_file_path = os.path.join(script_dir, "client.config")
# Source path (standard Go workspace location)
psiphon_source_path = os.path.expanduser("~/go/src/github.com/Psiphon-Labs/psiphon-tunnel-core/ConsoleClient")
psiphon_repo_url = "github.com/Psiphon-Labs/psiphon-tunnel-core/ConsoleClient"

# Option to use proxychains-ng if available
use_proxychains = True # Set to False if you don't want to use proxychains even if installed
# --- End Configuration ---

def run_command(command_list, check=True, capture_output=False, text=True, cwd=None):
    """Helper function to run shell commands."""
    print(f">>> Running command: {' '.join(command_list)}")
    try:
        result = subprocess.run(command_list, 
                                check=check,        # Raises CalledProcessError on failure if True
                                capture_output=capture_output, 
                                text=text,
                                cwd=cwd)            # Change working directory if specified
        if capture_output:
             print(result.stdout)
             if result.stderr:
                  print(f"[stderr]: {result.stderr}", file=sys.stderr)
        return result
    except FileNotFoundError:
        print(f"[Error] Command not found: {command_list[0]}. Is it installed and in PATH?", file=sys.stderr)
        return None
    except subprocess.CalledProcessError as e:
        print(f"[Error] Command failed with exit code {e.returncode}: {' '.join(command_list)}", file=sys.stderr)
        if capture_output:
             print(f"[stderr]: {e.stderr}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[Error] An unexpected error occurred while running command: {e}", file=sys.stderr)
        return None

def install_packages():
    """Check and install required Termux packages."""
    packages_needed = []
    if not shutil.which("git"):
        packages_needed.append("git")
    if not shutil.which("go"):
        packages_needed.append("golang")
        
    if packages_needed:
        package_string = " ".join(packages_needed)
        print(f"--- Required package(s) missing: {package_string}")
        try:
            # Try to install non-interactively
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

def compile_psiphon():
    """Downloads Psiphon source and compiles the binary."""
    print("--- Attempting to compile psiphon-tunnel-core from source...")
    
    # 1. Download/update source code
    #    Using -d to only download, -u to update dependencies
    print("--- Downloading/updating Psiphon source code...")
    get_command = ["go", "get", "-v", "-u", "-d", psiphon_repo_url]
    if run_command(get_command) is None:
        print("[Error] Failed to download Psiphon source code.", file=sys.stderr)
        return False

    # 2. Change to source directory
    print(f"--- Changing directory to: {psiphon_source_path}")
    original_cwd = os.getcwd()
    try:
        # Ensure the target directory exists
        if not os.path.isdir(psiphon_source_path):
             # If go get -d worked, this path should exist. If not, something is wrong.
             print(f"[Error] Source directory not found after 'go get': {psiphon_source_path}", file=sys.stderr)
             # Attempt to create path just in case GOPATH was weird
             go_get_path = os.path.expanduser("~/go/src/") + psiphon_repo_url
             if os.path.isdir(go_get_path):
                  print(f"[Warning] Using alternative source path: {go_get_path}")
                  psiphon_source_path_actual = go_get_path
             else:
                  print(f"[Error] Cannot find source directory at either expected path.", file=sys.stderr)
                  return False
        else:
             psiphon_source_path_actual = psiphon_source_path

        os.chdir(psiphon_source_path_actual)

        # 3. Compile the binary
        print("--- Compiling the binary...")
        # Build directly into the script's directory
        build_command = ["go", "build", "-ldflags=-s -w", "-o", psiphon_binary_path] 
        if run_command(build_command, cwd=psiphon_source_path_actual) is None:
            print("[Error] Failed to compile Psiphon binary.", file=sys.stderr)
            os.chdir(original_cwd) # Change back CWD even on failure
            return False
            
        print(f"--- Successfully compiled binary to: {psiphon_binary_path}")
        os.chdir(original_cwd) # Change back CWD
        return True

    except FileNotFoundError:
         print(f"[Error] Failed to change directory to '{psiphon_source_path_actual}'. 'go get' might have failed silently.", file=sys.stderr)
         os.chdir(original_cwd)
         return False
    except Exception as e:
        print(f"[Error] An error occurred during compilation process: {e}", file=sys.stderr)
        os.chdir(original_cwd)
        return False

# --- Main Script Logic ---
print(">>> Starting Psiphon Runner Script...")

# 1. Ensure required packages are installed
install_packages()

# 2. Check if Psiphon binary exists, compile if not
if not os.path.exists(psiphon_binary_path):
    print(f"--- Psiphon binary not found at '{psiphon_binary_path}'. Attempting to compile...")
    if not compile_psiphon():
        print("[Critical] Failed to obtain Psiphon binary. Exiting.", file=sys.stderr)
        sys.exit(1)
else:
    print(f"--- Found existing Psiphon binary: {psiphon_binary_path}")
    # Optional: Add logic here to re-compile if user wants to force update
    # e.g., by checking for a command-line argument like --update

# 3. Check or create config file
if not os.path.exists(config_file_path):
     print(f"--- Configuration file '{config_file_path}' not found. Creating default config.")
     try:
          default_config = {
               "LocalSocksProxyPort": 1080,
               "LocalHttpProxyPort": 8080
               # Add other default options from Psiphon docs if needed
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
     
command_to_run.extend([psiphon_binary_path, "-config", config_file_path])

# 5. Run Psiphon
process = None 
try:
    print(f">>> Executing command: {' '.join(command_to_run)}") 
    # Use Popen to run Psiphon in the background
    process = subprocess.Popen(command_to_run, 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True, 
                               bufsize=1, # Line buffered
                               universal_newlines=True) # Ensures text mode works correctly

    print(f">>> Psiphon started with Process ID: {process.pid}")
    print(">>> Monitoring Psiphon output (Press Ctrl+C to stop)...")
    
    # Read and print output/errors line by line
    while True:
        # Check stdout
        output_line = process.stdout.readline()
        if output_line: 
            print(f"[Psiphon Output]: {output_line.strip()}")
            # Optional check for successful proxy listening
            if "ListeningSocksProxyPort" in output_line:
                 print(">>> SOCKS Proxy is listening.")
            if "ListeningHttpProxyPort" in output_line:
                 print(">>> HTTP Proxy is listening.")

        # Check stderr
        error_line = process.stderr.readline()
        if error_line: 
            print(f"[Psiphon Error]: {error_line.strip()}", file=sys.stderr)

        # Check if process terminated unexpectedly
        return_code = process.poll()
        if return_code is not None:
            print(f">>> Psiphon process terminated unexpectedly with exit code: {return_code}")
            # Print any remaining stderr
            remaining_err = process.stderr.read()
            if remaining_err:
                 print(f"[Psiphon Final Error]: {remaining_err.strip()}", file=sys.stderr)
            break 

        # Avoid busy-waiting if no output
        if not output_line and not error_line:
            time.sleep(0.5)

except FileNotFoundError:
    # This error usually means the main executable (psiphon or proxychains) wasn't found
    executable_not_found = command_to_run[0] 
    print(f"[Critical Error] Command '{executable_not_found}' not found or not executable. Check PATH and permissions.", file=sys.stderr)
    sys.exit(1)
except KeyboardInterrupt:
    print("\n>>> Ctrl+C detected. Stopping Psiphon process...")
    if process and process.poll() is None: # Check if process exists and is running
        process.terminate() # Send SIGTERM (try graceful shutdown)
        try:
            process.wait(timeout=5) # Wait up to 5 seconds
            print(">>> Psiphon process stopped (Terminated).")
        except subprocess.TimeoutExpired:
            print(">>> Psiphon process did not terminate gracefully. Killing...")
            process.kill() # Send SIGKILL (force shutdown)
            print(">>> Psiphon process stopped (Killed).")
    else:
         print(">>> Psiphon process was not running or already stopped.")
    sys.exit(0) # Exit script gracefully after Ctrl+C
except Exception as e:
    print(f"[Critical Error] An unexpected error occurred: {e}", file=sys.stderr)
    if process and process.poll() is None:
         print(">>> Attempting to kill Psiphon process due to error...")
         process.kill()
    sys.exit(1) # Exit with error code
