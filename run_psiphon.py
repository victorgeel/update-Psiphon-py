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

# --- Paths related to compilation and execution ---
# Source path for official ConsoleClient (where 'go get' downloads to)
psiphon_source_path = os.path.expanduser("~/go/src/github.com/Psiphon-Labs/psiphon-tunnel-core/ConsoleClient")
psiphon_repo_url = "github.com/Psiphon-Labs/psiphon-tunnel-core/ConsoleClient"

# --- NEW Target path for the compiled binary (inside YOUR repo structure) ---
# Using the structure from your example URL, corrected for duplication
user_repo_base_path = os.path.expanduser("~/go/src/github.com/victorgeel/update-Psiphon-py") 
# The final path where the script will look for and execute the binary
psiphon_binary_path = os.path.join(user_repo_base_path, "psiphon-tunnel-core") 
# --- End NEW Target Path ---

# Option to use proxychains-ng if available
use_proxychains = True # Set to False if you don't want to use proxychains even if installed
# --- End Configuration ---

def run_command(command_list, check=True, capture_output=False, text=True, cwd=None, env=None):
    """Helper function to run shell commands."""
    print(f">>> Running command: {' '.join(command_list)}")
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    if 'GOPATH' not in merged_env:
         merged_env['GOPATH'] = os.path.expanduser("~/go")
         print(f"--- Temporarily setting GOPATH to: {merged_env['GOPATH']}")
         
    try:
        result = subprocess.run(command_list, 
                                check=check,        
                                capture_output=capture_output, 
                                text=text,
                                cwd=cwd,
                                env=merged_env) 
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

def compile_psiphon():
    """Downloads Psiphon source and compiles the binary to the user's specified repo path."""
    print("--- Attempting to compile psiphon-tunnel-core from source...")
    
    # 1. Download/update source code (using deprecated 'go get -d')
    print("--- Downloading/updating Psiphon source code (using 'go get -d')...")
    go_env = os.environ.copy()
    go_env['GOPATH'] = os.path.expanduser("~/go") 
    get_command = ["go", "get", "-v", "-u", "-d", psiphon_repo_url]
    result_get = run_command(get_command, check=False, capture_output=True, env=go_env) 
    if result_get is None: return False
    if result_get.returncode != 0:
         if "no longer supported outside a module" in result_get.stderr:
              print("[Warning] 'go get -d' showed deprecation warning as expected. Assuming source exists and proceeding.")
         else:
              print("[Error] Failed to download/update Psiphon source code.", file=sys.stderr)
              return False
    else:
         print("--- 'go get -d' completed.")

    # 2. Ensure the TARGET directory for the binary exists (Parent of psiphon_binary_path)
    target_binary_dir = os.path.dirname(psiphon_binary_path) 
    print(f"--- Ensuring target directory for binary exists: {target_binary_dir}")
    try:
        os.makedirs(target_binary_dir, exist_ok=True) 
    except OSError as e:
        print(f"[Error] Failed to create target directory '{target_binary_dir}': {e}", file=sys.stderr)
        return False

    # 3. Change to the official Psiphon source directory
    print(f"--- Changing directory to source: {psiphon_source_path}")
    original_cwd = os.getcwd()
    try:
        if not os.path.isdir(psiphon_source_path):
             print(f"[Error] Source directory not found: {psiphon_source_path}. 'go get -d' might have failed.", file=sys.stderr)
             return False
        os.chdir(psiphon_source_path)

        # 4. Compile the binary, placing the output in the NEW specified path
        print(f"--- Compiling the binary to target path: {psiphon_binary_path}")
        build_command = ["go", "build", "-ldflags=-s -w", "-o", psiphon_binary_path] 
        if run_command(build_command) is None: 
            print("[Error] Failed to compile Psiphon binary.", file=sys.stderr)
            os.chdir(original_cwd) 
            return False
            
        print(f"--- Successfully compiled binary to: {psiphon_binary_path}")
        
        # 5. Set execute permission on the NEW binary path
        try:
             os.chmod(psiphon_binary_path, 0o755)
             print(f">>> Set execute permission on {psiphon_binary_path}")
        except Exception as e:
             print(f"[Warning] Could not set execute permission on {psiphon_binary_path}: {e}", file=sys.stderr)

        os.chdir(original_cwd) 
        return True

    except Exception as e:
        print(f"[Error] An error occurred during compilation process: {e}", file=sys.stderr)
        if os.getcwd() != original_cwd:
            os.chdir(original_cwd)
        return False

# --- Main Script Logic ---
print(">>> Starting Psiphon Runner Script...")

# 1. Ensure required packages are installed
install_packages()

# 2. Check if Psiphon binary exists AT THE NEW TARGET PATH, compile if not
if not os.path.exists(psiphon_binary_path): #<-- Check NEW path
    print(f"--- Psiphon binary not found at target path '{psiphon_binary_path}'. Attempting to compile...")
    if not compile_psiphon():
        print("[Critical] Failed to obtain Psiphon binary via compilation. Exiting.", file=sys.stderr)
        sys.exit(1)
else:
    print(f"--- Found existing Psiphon binary at target path: {psiphon_binary_path}") #<-- Check NEW path

# 3. Check or create config file (still in the script's directory)
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
     
# Use the NEW SPECIFIC binary path for execution
command_to_run.extend([psiphon_binary_path, "-config", config_file_path]) #<-- Uses NEW path

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
    # Specific check for the binary path if the main command fails
    if not os.path.exists(psiphon_binary_path):
         print(f"--- Also note: The binary expected at '{psiphon_binary_path}' does not exist.", file=sys.stderr)
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
