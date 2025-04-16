import subprocess
import os
import sys
import time
import json
import shutil

# --- Configuration ---
script_dir = os.path.dirname(os.path.abspath(__file__)) 
config_file_path = os.path.join(script_dir, "client.config")
psiphon_binary_path = os.path.expanduser("~/go/bin/ConsoleClient") 
# Use the specific branch suggested by Psiphon documentation for module use
psiphon_package_spec = "github.com/Psiphon-Labs/psiphon-tunnel-core/ConsoleClient@staging-client" 
use_proxychains = True 
# --- End Configuration ---

def run_command(command_list, check=True, capture_output=False, text=True, cwd=None, env=None):
    """Helper function to run shell commands."""
    print(f">>> Running command: {' '.join(command_list)}")
    merged_env = os.environ.copy()
    if env: merged_env.update(env)
    go_bin_path = os.path.expanduser("~/go/bin")
    if go_bin_path not in merged_env.get("PATH", ""):
         print(f"--- Adding {go_bin_path} to PATH for this command execution")
         merged_env["PATH"] = f"{go_bin_path}:{merged_env.get('PATH', '')}"
    try:
        result = subprocess.run(command_list, check=check, capture_output=capture_output, text=text, cwd=cwd, env=merged_env) 
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
                 print("[Error] Failed to install required packages.", file=sys.stderr); sys.exit(1)
            print(f"--- Successfully installed: {package_string}")
        except Exception as e: print(f"[Error] Failed during package installation: {e}", file=sys.stderr); sys.exit(1)
    else: print("--- Required packages (git, golang) are already installed.")

def install_psiphon_binary():
    """Installs the Psiphon ConsoleClient binary using 'go install' with specific branch."""
    print(f"--- Attempting to install psiphon binary using 'go install {psiphon_package_spec}'...")
    # Use the specific branch/tag in the install command
    install_command = ["go", "install", psiphon_package_spec] 
    result = run_command(install_command, check=False, capture_output=True) # Run with check=False first to see output
    
    # Check result and existence separately
    if result is None or result.returncode != 0:
        print("[Error] Failed to install Psiphon binary using 'go install'. See output above.", file=sys.stderr)
        print("--- Please check your Go installation and network connection.", file=sys.stderr)
        run_command(["go", "env"], check=False) 
        return False
        
    if not os.path.exists(psiphon_binary_path):
         print(f"[Error] 'go install' completed but binary not found at expected path: {psiphon_binary_path}", file=sys.stderr)
         print("--- Check your $GOPATH and $GOBIN environment variables.", file=sys.stderr)
         run_command(["go", "env", "GOPATH", "GOBIN"], check=False)
         return False
         
    print(f"--- Successfully installed binary to: {psiphon_binary_path}")
    try: os.chmod(psiphon_binary_path, 0o755)
    except Exception as e: print(f"[Warning] Could not set execute permission: {e}", file=sys.stderr)
    return True

# --- Main Script Logic ---
print(">>> Starting Psiphon Runner Script...")
install_packages()

if not os.path.exists(psiphon_binary_path):
    print(f"--- Psiphon binary not found at '{psiphon_binary_path}'. Attempting to install...")
    if not install_psiphon_binary():
        print("[Critical] Failed to obtain Psiphon binary. Exiting.", file=sys.stderr); sys.exit(1)
else:
    print(f"--- Found existing Psiphon binary: {psiphon_binary_path}")
    # Consider adding --update flag logic here to force re-run install_psiphon_binary()

if not os.path.exists(config_file_path):
     print(f"--- Configuration file '{config_file_path}' not found. Creating default config.")
     try:
          default_config = {"LocalSocksProxyPort": 1080, "LocalHttpProxyPort": 8080}
          with open(config_file_path, 'w') as f: json.dump(default_config, f, indent=4)
          print(f">>> Created default '{config_file_path}'.")
     except Exception as e: print(f"[Error] Failed to create default config file: {e}", file=sys.stderr); sys.exit(1)
else: print(f"--- Using existing configuration file: {config_file_path}")

command_to_run = []
proxychains_path = shutil.which("proxychains-ng")
if use_proxychains and proxychains_path:
     command_to_run.append(proxychains_path)
     print(f"--- Will use proxychains-ng found at: {proxychains_path}")
     print("--- Make sure '/data/data/com.termux/files/usr/etc/proxychains.conf' is configured correctly.")
elif use_proxychains: print("[Warning] 'use_proxychains' is True, but 'proxychains-ng' not found.")
command_to_run.extend([psiphon_binary_path, "-config", config_file_path]) 

process = None 
try:
    print(f">>> Executing command: {' '.join(command_to_run)}") 
    process = subprocess.Popen(command_to_run, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True) 
    print(f">>> Psiphon started with Process ID: {process.pid}")
    print(">>> Monitoring Psiphon output (Press Ctrl+C to stop)...")
    while True:
        output_line = process.stdout.readline()
        if output_line: print(f"[Psiphon Output]: {output_line.strip()}")
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
    print(f"[Critical Error] Command '{executable_not_found}' not found or not executable.", file=sys.stderr)
    if not os.path.exists(psiphon_binary_path): print(f"--- Binary expected at '{psiphon_binary_path}' does not exist.", file=sys.stderr)
    sys.exit(1)
except KeyboardInterrupt:
    print("\n>>> Ctrl+C detected. Stopping Psiphon process...")
    if process and process.poll() is None: 
        process.terminate() 
        try: process.wait(timeout=5); print(">>> Psiphon process stopped (Terminated).")
        except subprocess.TimeoutExpired: print(">>> Killing Psiphon process..."); process.kill(); print(">>> Psiphon process stopped (Killed).")
    else: print(">>> Psiphon process was not running or already stopped.")
    sys.exit(0) 
except Exception as e:
    print(f"[Critical Error] An unexpected error occurred: {e}", file=sys.stderr)
    if process and process.poll() is None: print(">>> Attempting to kill Psiphon process..."); process.kill()
    sys.exit(1) 
