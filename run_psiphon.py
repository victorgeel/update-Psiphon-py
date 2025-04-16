import subprocess
import os
import sys
import time
import json
import shutil

# --- Configuration ---
script_dir = os.path.dirname(os.path.abspath(__file__))
# Config file will be in the script's directory
config_file_path = os.path.join(script_dir, "client.config")
# Binary will be built into the script's directory
psiphon_binary_path = os.path.join(script_dir, "psiphon-tunnel-core") 

# --- Paths and URLs for Git Clone and Build ---
# Where to clone the source code
psiphon_local_repo_path = os.path.expanduser("~/psiphon-tunnel-core-source") 
# The specific subdirectory to build within the cloned repo
psiphon_build_path = os.path.join(psiphon_local_repo_path, "ConsoleClient") 
# Git repository URL
psiphon_git_repo_url = "https://github.com/Psiphon-Labs/psiphon-tunnel-core.git"
# Branch to checkout and build
psiphon_branch = "staging-client" 

# Option to use proxychains-ng if available
use_proxychains = True 
# --- End Configuration ---

def run_command(command_list, check=True, capture_output=False, text=True, cwd=None, env=None):
    """Helper function to run shell commands."""
    print(f">>> Running command: {' '.join(command_list)} {'in dir '+cwd if cwd else ''}")
    merged_env = os.environ.copy(); 
    if env: merged_env.update(env)
    # Add ~/go/bin to PATH just in case go itself needs tools from there
    go_bin_path = os.path.expanduser("~/go/bin")
    if go_bin_path not in merged_env.get("PATH", ""):
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
        print(f"[Error] An unexpected error occurred: {e}", file=sys.stderr)
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

def build_psiphon_from_clone():
    """Clones or updates the Psiphon repo and builds the binary."""
    print("--- Building psiphon-tunnel-core from local clone...")
    original_cwd = os.getcwd()
    
    try:
        # 1. Clone or Update Repo
        if os.path.isdir(psiphon_local_repo_path):
            print(f"--- Found existing source directory: {psiphon_local_repo_path}")
            print("--- Attempting to update repository...")
            # Check current branch
            result_branch = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=psiphon_local_repo_path, capture_output=True, check=False)
            current_branch = result_branch.stdout.strip() if result_branch and result_branch.returncode == 0 else None

            # Checkout the correct branch if not already on it
            if current_branch != psiphon_branch:
                 print(f"--- Switching to branch '{psiphon_branch}'...")
                 if run_command(["git", "checkout", psiphon_branch], cwd=psiphon_local_repo_path) is None:
                      print(f"[Error] Failed to checkout branch '{psiphon_branch}'. Trying fetch/pull anyway.")
            
            # Pull latest changes for the branch
            if run_command(["git", "pull", "origin", psiphon_branch], cwd=psiphon_local_repo_path, check=False) is None:
                 print("[Warning] 'git pull' failed. Continuing with existing code.")
                 # Don't return False here, try building anyway

        else:
            print(f"--- Cloning Psiphon repository to: {psiphon_local_repo_path}")
            # Clone only the specific branch with depth 1 for speed
            clone_command = ["git", "clone", "--depth", "1", "--branch", psiphon_branch, psiphon_git_repo_url, psiphon_local_repo_path]
            if run_command(clone_command) is None:
                print("[Error] Failed to clone Psiphon repository.", file=sys.stderr)
                return False

        # 2. Change into the specific build directory within the clone
        print(f"--- Changing directory to build path: {psiphon_build_path}")
        if not os.path.isdir(psiphon_build_path):
             print(f"[Error] Build directory not found: {psiphon_build_path}", file=sys.stderr)
             return False
        os.chdir(psiphon_build_path)

        # 3. Build the binary, outputting to the script's directory
        print(f"--- Compiling the binary to: {psiphon_binary_path}")
        # Build command is run from within psiphon_build_path
        build_command = ["go", "build", "-ldflags=-s -w", "-o", psiphon_binary_path] 
        if run_command(build_command, cwd=psiphon_build_path) is None: 
            print("[Error] Failed to compile Psiphon binary.", file=sys.stderr)
            os.chdir(original_cwd) # Change back CWD even on failure
            return False
            
        print(f"--- Successfully compiled binary to: {psiphon_binary_path}")
        
        # 4. Set execute permission
        try:
             os.chmod(psiphon_binary_path, 0o755)
             print(f">>> Set execute permission on {psiphon_binary_path}")
        except Exception as e:
             print(f"[Warning] Could not set execute permission: {e}", file=sys.stderr)

        os.chdir(original_cwd) # Change back CWD
        return True

    except Exception as e:
        print(f"[Error] An error occurred during the build process: {e}", file=sys.stderr)
        # Ensure we change back directory even if other errors occur
        if os.getcwd() != original_cwd:
            os.chdir(original_cwd)
        return False

# --- Main Script Logic ---
print(">>> Starting Psiphon Runner Script...")
install_packages()

# Check if Psiphon binary exists IN THE SCRIPT DIRECTORY, build if not
if not os.path.exists(psiphon_binary_path): # Check path in script dir
    print(f"--- Psiphon binary not found at '{psiphon_binary_path}'. Attempting to build from local clone...")
    if not build_psiphon_from_clone(): # Call the clone & build function
        print("[Critical] Failed to obtain Psiphon binary via build. Exiting.", file=sys.stderr); sys.exit(1)
else:
    print(f"--- Found existing Psiphon binary: {psiphon_binary_path}") # Path in script dir
    # Optional: Add logic to force rebuild, e.g., --update flag calls build_psiphon_from_clone()

# Check or create config file (in the script's directory)
if not os.path.exists(config_file_path):
     print(f"--- Configuration file '{config_file_path}' not found. Creating default config.")
     try:
          default_config = {"LocalSocksProxyPort": 1080, "LocalHttpProxyPort": 8080}
          with open(config_file_path, 'w') as f: json.dump(default_config, f, indent=4)
          print(f">>> Created default '{config_file_path}'.")
     except Exception as e: print(f"[Error] Failed to create default config file: {e}", file=sys.stderr); sys.exit(1)
else: print(f"--- Using existing configuration file: {config_file_path}")

# Prepare the command to run Psiphon (potentially with proxychains)
command_to_run = []
proxychains_path = shutil.which("proxychains-ng")
if use_proxychains and proxychains_path:
     command_to_run.append(proxychains_path)
     print(f"--- Will use proxychains-ng found at: {proxychains_path}")
     print("--- Make sure '/data/data/com.termux/files/usr/etc/proxychains.conf' is configured correctly.")
elif use_proxychains: print("[Warning] 'use_proxychains' is True, but 'proxychains-ng' not found.")

# Use the binary path IN THE SCRIPT DIRECTORY
command_to_run.extend([psiphon_binary_path, "-config", config_file_path]) 

# Run Psiphon process
process = None 
try:
    print(f">>> Executing command: {' '.join(command_to_run)}") 
    process = subprocess.Popen(command_to_run, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True) 
    print(f">>> Psiphon started with Process ID: {process.pid}")
    print(">>> Monitoring Psiphon output (Press Ctrl+C to stop)...")
    while True: # Output monitoring loop (same as before)
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
        process.terminate(); 
        try: process.wait(timeout=5); print(">>> Psiphon process stopped (Terminated).")
        except subprocess.TimeoutExpired: print(">>> Killing Psiphon process..."); process.kill(); print(">>> Psiphon process stopped (Killed).")
    else: print(">>> Psiphon process was not running or already stopped.")
    sys.exit(0) 
except Exception as e:
    print(f"[Critical Error] An unexpected error occurred: {e}", file=sys.stderr)
    if process and process.poll() is None: print(">>> Attempting to kill Psiphon process..."); process.kill()
    sys.exit(1) 
