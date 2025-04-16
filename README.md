# Psiphon Runner for Termux (Python)

Termux ပေါ်တွင် Psiphon command-line client (`psiphon-tunnel-core`) ကို အလွယ်တကူ run နိုင်ရန်နှင့် နောက်ဆုံး version သို့ အလိုအလျောက် update လုပ်နိုင်ရန် ရေးသားထားသော Python script ဖြစ်သည်။ `Proxychains-NG` ကို အသုံးပြု၍ အခြား SOCKS proxy မှတဆင့် ချိတ်ဆက်နိုင်သည်။

## လိုအပ်ချက်များ

* Termux
* Python (`pkg install python`)
* Git (`pkg install git`)
* pip (Python နှင့်အတူ ပါလာသည်)
* Proxychains-NG (`pkg install proxychains-ng`) - အခြား SOCKS proxy မှတဆင့် ချိတ်ဆက်လိုမှသာ လိုအပ်သည်။

## Installation

1.  ဤ repository ကို Termux တွင် clone လုပ်ပါ:

    ```bash
    
    git clone https://github.com/victorgeel/update-Psiphon-py
    ```
3.  Clone လုပ်ထားသော directory ထဲသို့ ဝင်ပါ:

    ```bash
    cd update-Psiphon-py
    ```
5.  လိုအပ်သော Python library ကို install လုပ်ပါ:

    ```bash
    pip install -r requirements.txt
    ```
7.  (Optional) Proxychains-NG ကို install လုပ်ပါ (အခြား proxy မှတဆင့် မသုံးလျှင် မလိုပါ):

    ```bash
    pkg install proxychains-ng -y
    ```

## Proxychains Configuration (အခြား Proxy မှတဆင့် သုံးလိုလျှင်)

1.  Proxychains config ဖိုင်ကိုဖွင့်ပါ:

    ```bash
    nano /data/data/com.termux/files/usr/etc/proxychains.conf
    ```
3.  ဖိုင်အောက်ဆုံးရှိ `[ProxyList]` အောက်တွင်၊ ရှိပြီးသား နမူနာများကို `#` ဖြင့် comment ပိတ်ပြီး သင်အသုံးပြုလိုသော **အခြား VPN/Service ၏ SOCKS proxy** အချက်အလက်ကို ထည့်ပါ (ဥပမာ):

    ```conf
    [ProxyList]
    # socks4  127.0.0.1 9050
    socks5  127.0.0.1 9050  # <-- သင့် VPN proxy အချက်အလက် အမှန်ထည့်ပါ
    ```
5.  ဖိုင်ကို Save ပါ (`Ctrl+X`, `Y`, `Enter`)။

## အသုံးပြုပုံ

1.  (Optional) အကယ်၍ အခြား VPN ၏ SOCKS proxy မှတဆင့် သုံးမည်ဆိုပါက ထို VPN/proxy ကို **အရင် run** ထားပါ။
2.  `run_psiphon.py` script ကို run ပါ:
    ```bash
    python run_psiphon.py
    ```
3.  Script သည် GitHub မှ နောက်ဆုံး Psiphon version ကို စစ်ဆေးပြီး လိုအပ်ပါက download/update လုပ်ပါလိမ့်မည်။
4.  `client.config` ဖိုင် မရှိသေးပါက default settings (SOCKS port 1080, HTTP port 8080) ဖြင့် အလိုအလျောက် ဖန်တီးပေးပါမည်။ *(Script ထဲမှာ ဒီ logic ပါမှ အလုပ်လုပ်ပါမည်)*
5.  Proxychains သုံးရန် script ကို ပြင်ထားပြီး `proxychains-ng` ကို install လုပ်ထားပါက Psiphon သည် သင် configure လုပ်ထားသော proxy မှတဆင့် စတင်ချိတ်ဆက်ပါမည်။ မဟုတ်ပါက တိုက်ရိုက် ချိတ်ဆက်ပါမည်။
6.  Psiphon စတင်လည်ပတ်ပြီး output များကို ပြသပါလိမ့်မည်။
7.  ရပ်တန့်လိုပါက `Ctrl+C` ကို နှိပ်ပါ။

## SOCKS/HTTP Proxy အသုံးပြုခြင်း

* Psiphon လည်ပတ်နေချိန်တွင် SOCKS proxy ကို `127.0.0.1` port `1080` (default) တွင် ရရှိနိုင်ပါသည်။
* HTTP proxy ကို `127.0.0.1` port `8080` (default) တွင် ရရှိနိုင်ပါသည်။
* SockDroid ကဲ့သို့သော app များ သို့မဟုတ် proxy setting ကို support လုပ်သော application များတွင် ဤ address နှင့် port ကို ထည့်သွင်း အသုံးပြုနိုင်ပါသည်။

## မှတ်ချက်

* `psiphon-tunnel-core` binary ဖိုင်ကို script မှ အလိုအလျောက် download/update လုပ်ပါမည်။
* `.current_psiphon_version` ဖိုင်သည် လက်ရှိ local version ကို မှတ်သားထားရန် ဖြစ်သည်။ (Git ထဲမထည့်ပါ)
* Update စစ်ဆေးရန်နှင့် download လုပ်ရန် အင်တာနက် connection လိုအပ်ပါသည်။
* Proxychains မှတဆင့် သုံးပါက speed/latency အနည်းငယ် သက်ရောက်မှု ရှိနိုင်ပါသည်။ Proxychains config ကို မှန်ကန်စွာ ပြင်ဆင်ရန် အရေးကြီးသည်။

