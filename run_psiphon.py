import subprocess
import os
import sys
import time
import requests 
import json     
import shutil   

# --- Configuration ---
psiphon_binary = "./psiphon-tunnel-core" 
config_file = "client.config"
repo_owner = "Psiphon-Labs"
repo_name = "psiphon-tunnel-core"
asset_keyword = "android-arm64" 
version_file = ".current_psiphon_version" 
# --- End Configuration ---

def get_local_version():
    if os.path.exists(version_file):
        try:
            with open(version_file, 'r') as f:
                return f.read().strip()
        except Exception as e:
            print(f"[Warning] Local version file ဖတ်ရာတွင် အမှားရှိသည်: {e}")
            return None
    return None

def get_latest_release_info():
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
    print(f">>> GitHub မှ နောက်ဆုံး version ကို စစ်ဆေးနေသည်: {api_url}")
    try:
        response = requests.get(api_url, timeout=15) 
        response.raise_for_status() 
        data = response.json()
        latest_version = data.get("tag_name")
        assets = data.get("assets", [])

        download_url = None
        for asset in assets:
            if asset_keyword in asset.get("name", ""):
                download_url = asset.get("browser_download_url")
                print(f">>> Asset ကိုတွေ့ရှိသည်: {asset.get('name')}")
                break

        if not latest_version:
            print("[Warning] API response မှ latest version tag ကို ရှာမတွေ့ပါ။")
            return None, None
        if not download_url:
            print(f"[Warning] API response မှ '{asset_keyword}' ပါသော asset download link ကို ရှာမတွေ့ပါ။")
            return latest_version, None

        return latest_version, download_url

    except requests.exceptions.RequestException as e:
        print(f"[Error] GitHub API သို့ ဆက်သွယ်ရာတွင် အမှားရှိသည်: {e}")
        return None, None
    except json.JSONDecodeError:
        print("[Error] GitHub API response JSON ကို ဖတ်မရပါ။")
        return None, None
    except Exception as e:
        print(f"[Error] နောက်ဆုံး version ရှာရာတွင် မမျှော်လင့်သော အမှားဖြစ်သည်: {e}")
        return None, None

def download_and_update(version, url):
    print(f">>> Version {version} အသစ်ကို download လုပ်နေသည်: {url}")
    temp_download_path = psiphon_binary + ".tmp"
    try:
        with requests.get(url, stream=True, timeout=300) as r: 
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            downloaded_size = 0
            print(f">>> Downloading to {temp_download_path}...")
            with open(temp_download_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if total_size > 0:
                         done = int(50 * downloaded_size / total_size)
                         sys.stdout.write(f"\r[{'=' * done}{' ' * (50-done)}] {downloaded_size / (1024*1024):.2f} MB / {total_size / (1024*1024):.2f} MB ")
                         sys.stdout.flush()
            print("\n>>> Download ပြီးဆုံးပြီ။")

        os.chmod(temp_download_path, 0o755) 
        print(">>> Execute permission ပေးပြီးပြီ။")

        shutil.move(temp_download_path, psiphon_binary)
        print(f">>> Binary အသစ် '{psiphon_binary}' ကို အစားထိုးပြီးပြီ။")

        with open(version_file, 'w') as f:
            f.write(version)
        print(f">>> Local version ကို '{version}' သို့ update လုပ်ပြီးပြီ။")
        return True

    except requests.exceptions.RequestException as e:
        print(f"[Error] Download လုပ်ရာတွင် အမှားရှိသည်: {e}")
    except OSError as e:
        print(f"[Error] File permission သို့မဟုတ် move လုပ်ရာတွင် အမှားရှိသည်: {e}")
    except Exception as e:
        print(f"[Error] Update လုပ်ရာတွင် မမျှော်လင့်သော အမှားဖြစ်သည်: {e}")
    finally:
        if os.path.exists(temp_download_path):
            os.remove(temp_download_path)
    return False

# --- Main Script Logic ---
print(">>> Psiphon Runner Script စတင်သည်...")

local_version = get_local_version()
print(f"+++ လက်ရှိ local version: {local_version or 'မရှိသေးပါ'}")

latest_version, download_url = get_latest_release_info()

update_successful = False
if latest_version and download_url:
    print(f"+++ GitHub မှ နောက်ဆုံး version: {latest_version}")
    if local_version != latest_version:
        print(f">>> Version အသစ် ({latest_version}) ရှိနေသည်။ Update လုပ်ပါမည်။")
        update_successful = download_and_update(latest_version, download_url)
        if not update_successful:
             print("[Warning] Update မအောင်မြင်ပါ။ ရှိနေသော version (ถ้ามี) ကို ဆက်လက် အသုံးပြုပါမည်။")
    else:
        print(">>> သင်၏ Psiphon version သည် နောက်ဆုံးထွက် version ဖြစ်နေပါသည်။")
        update_successful = True 
else:
    print("[Warning] နောက်ဆုံး version ကို စစ်ဆေး၍မရပါ။ Update ကို ကျော်သွားပါမည်။")

# Check if binary exists after potential update attempt or if update failed
if not os.path.exists(psiphon_binary):
    if local_version: # If there was a local version but update failed/was skipped
         print(f"[Warning] Psiphon binary '{psiphon_binary}' ကို ရှာမတွေ့ပါ။ Update မအောင်မြင်ခဲ့၍ ဖြစ်နိုင်ပါသည်။")
    else: # No local version and update failed/skipped
         print(f"[ERROR] Psiphon binary '{psiphon_binary}' ကို ရှာမတွေ့ပါ။ Download/Update မအောင်မြင်ခဲ့ပါ။ Script ကိုရပ်တန့်လိုက်သည်။")
         sys.exit(1)

# Check or create config file
if not os.path.exists(config_file):
     print(f"[Warning] Configuration file '{config_file}' ကို ရှာမတွေ့ပါ။ Default config ဖန်တီးပါမည်။")
     try:
          default_config = {
               "LocalSocksProxyPort": 1080,
               "LocalHttpProxyPort": 8080
          }
          with open(config_file, 'w') as f:
               json.dump(default_config, f, indent=4)
          print(f">>> Default '{config_file}' ကို ဖန်တီးပြီးပါပြီ။ လိုအပ်ပါက ပြင်ဆင်ပါ။")
     except Exception as e:
          print(f"[ERROR] Default config file ဖန်တီးရာတွင် အမှားရှိသည်: {e}")
          sys.exit(1)

# Prepare the command (with potential proxychains)
# Check if proxychains should be used (e.g., based on a flag or environment variable - optional)
# For now, assume it's always used if available or configured in the command below
use_proxychains = True # Set to False or make conditional if needed

if use_proxychains and shutil.which("proxychains-ng"): # Check if proxychains exists in PATH
     command = ["proxychains-ng", psiphon_binary, "-config", config_file]
     print(">>> Proxychains-NG ဖြင့် Psiphon ကို run ပါမည်။")
else:
     if use_proxychains:
          print("[Warning] Proxychains-NG ကို ရှာမတွေ့ပါ။ Psiphon ကို တိုက်ရိုက် run ပါမည်။")
     command = [psiphon_binary, "-config", config_file]
     print(">>> Psiphon ကို တိုက်ရိုက် run ပါမည်။")

process = None 
try:
    print(f">>> Running command: {' '.join(command)}") 
    process = subprocess.Popen(command, 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True, 
                               bufsize=1, 
                               universal_newlines=True) 

    print(f">>> Psiphon ကို Process ID {process.pid} ဖြင့် စတင်လိုက်ပြီ။")
    print(">>> Psiphon output ကို စောင့်ကြည့်နေသည် (ရပ်ရန် Ctrl+C နှိပ်ပါ)...")

    while True:
        output_line = process.stdout.readline()
        error_line = process.stderr.readline()
        if output_line: print(f"[Psiphon Output]: {output_line.strip()}")
        if error_line: print(f"[Psiphon Error]: {error_line.strip()}")
        if process.poll() is not None:
            print(">>> Psiphon process ရပ်တန့်သွားသည်။")
            break
        if not output_line and not error_line:
            time.sleep(0.5)

except FileNotFoundError:
    # Error specific to the executable in the command list
    executable_not_found = command[0]
    print(f"[ERROR] Command '{executable_not_found}' ကို ရှာမတွေ့ပါ သို့မဟုတ် run မရပါ။ PATH သို့မဟုတ် permission စစ်ဆေးပါ။")
    sys.exit(1)
except KeyboardInterrupt:
    print("\n>>> Ctrl+C နှိပ်လိုက်သည်။ Psiphon process ကို ရပ်တန့်နေသည်...")
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
            print(">>> Psiphon process ရပ်တန့်ပြီးပါပြီ (Terminated)။")
        except subprocess.TimeoutExpired:
            print(">>> Psiphon process အချိန်မီ မရပ်တန့်ပါ... Force killing...")
            process.kill()
            print(">>> Psiphon process ရပ်တန့်ပြီးပါပြီ (Killed)။")
    else:
         print(">>> Psiphon process မရှိပါ သို့မဟုတ် ရပ်တန့်ပြီးသားပါ။")
    sys.exit(0) 
except Exception as e:
    print(f"[ERROR] မမျှော်လင့်သော အမှားတစ်ခု ဖြစ်ပွားခဲ့သည်: {e}")
    if process and process.poll() is None:
         process.kill()
    sys.exit(1)
  
