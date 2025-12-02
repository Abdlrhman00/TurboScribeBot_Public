import shutil
import os
from datetime import datetime, timedelta
import requests
import time
from urllib.parse import urlparse, parse_qs
from selenium.webdriver.common.by import By

LANGUAGE_MAP = {
    # --- Common ---
    "en": "English",             # base
    "en-US": "English (US)",
    "en-UK": "English (UK)",
    "es": "Spanish",
    "pt": "Portuguese",
    "fr": "French",
    "it": "Italian",
    "de": "German",
    "nl": "Dutch",
    "pl": "Polish",
    "da": "Danish",
    "ja": "Japanese",
    "ko": "Korean",
    "hu": "Hungarian",
    "cs": "Czech",
    "zh": "Chinese",
    "he": "Hebrew",

    # --- High accuracy group ---
    "az": "Azerbaijani",
    "hy": "Armenian",
    "et": "Estonian",
    "af": "Afrikaans",
    "id": "Indonesian",
    "ur": "Urdu",
    "uk": "Ukrainian",
    "is": "Icelandic",
    "bg": "Bulgarian",
    "bs": "Bosnian",
    "be": "Belarusian",
    "tl": "Tagalog",
    "ta": "Tamil",
    "th": "Thai",
    "tr": "Turkish",
    "gl": "Galician",
    "ru": "Russian",
    "ro": "Romanian",
    "sk": "Slovak",
    "sl": "Slovenian",
    "sw": "Swahili",
    "sv": "Swedish",
    "sr": "Serbian",
    "zh-TW": "Chinese (Traditional)",
    "zh-CN": "Chinese (Simplified)",
    "ar": "Arabic",
    "fa": "Persian",
    "fi": "Finnish",
    "vi": "Vietnamese",
    "kk": "Kazakh",
    "kn": "Kannada",
    "ca": "Catalan",
    "hr": "Croatian",
    "lv": "Latvian",
    "lt": "Lithuanian",
    "mr": "Marathi",
    "mi": "Maori",
    "mk": "Macedonian",
    "ms": "Malay",
    "no": "Norwegian",
    "ne": "Nepali",
    "hi": "Hindi",
    "cy": "Welsh",
    "el": "Greek",

    # --- Other ---
    "as": "Assamese",
    "sq": "Albanian",
    "am": "Amharic",
    "uz": "Uzbek",
    "oc": "Occitan",
    "eu": "Basque",
    "ps": "Pashto",
    "ba": "Bashkir",
    "br": "Breton",
    "pa": "Punjabi",
    "bn": "Bengali",
    "my": "Myanmar",              # same as Burmese
    "my-BE": "Burmese",           # to distinguish if needed
    "bo": "Tibetan",
    "tt": "Tatar",
    "tk": "Turkmen",
    "te": "Telugu",
    "jv": "Javanese",
    "ka": "Georgian",
    "km": "Khmer",
    "sd": "Sindhi",
    "sa": "Sanskrit",
    "si": "Sinhala",
    "su": "Sundanese",
    "so": "Somali",
    "tg": "Tajik",
    "gu": "Gujarati",
    "fo": "Faroese",
    "val": "Valencian",
    "vls": "Flemish",
    "es-ES": "Castilian",
    "ht": "Haitian",
    "ht-cr": "Haitian Creole",
    "la": "Latin",
    "lo": "Lao",
    "haw": "Hawaiian",
    "lb": "Luxembourgish",
    "ln": "Lingala",
    "mt": "Maltese",
    "ml": "Malayalam",
    "mg": "Malagasy",
    "mn": "Mongolian",
    "mo": "Moldovan",
    "nn": "Nynorsk",
    "ha": "Hausa",
    "yi": "Yiddish",
    "yo": "Yoruba",
    "sn": "Shona",
}

def get_language_name(code: str) -> str:
    """
    Get the full language name from a short code.
    Example: 'en-US' -> 'English (US)'
    """
    return LANGUAGE_MAP.get(code, f"Unknown ({code})")

def wait_for_download(directory, timeout=300):
        import time
        import os

        """
        Wait until no .crdownload files exist in the directory.
        """
        #print(directory)
        end_time = time.time() + timeout
        #print(end_time)
        while time.time() < end_time:
            if any(filename.endswith(".crdownload") for filename in os.listdir(directory)):
                time.sleep(1)
            else:
                return True  # Download completed
        raise TimeoutError("Download did not complete within the expected time.")

def period_delete(period_days):
    last_deleted_file = "last_deleted.txt"
    outputs_folder = "outputs"

    if period_days is None:
        print("PERIOD_DELETE_DAYS not set.")
        return

    try:
        period = timedelta(days=int(period_days))
    except ValueError:
        print("Invalid PERIOD_DELETE_DAYS value.")
        return

    now = datetime.now()

    # Step 2: Read the last deletion timestamp
    if os.path.exists(last_deleted_file):
        with open(last_deleted_file, "r") as f:
            last_deleted_str = f.read().strip()
            try:
                last_deleted = datetime.fromisoformat(last_deleted_str)
            except ValueError:
                print("Invalid date format in last_deleted.txt. Resetting.")
                last_deleted = now
                with open(last_deleted_file, "w") as f:
                    f.write(now.isoformat())
                print("Reset last deletion time. Skipping deletion this time.")
                return
    else:
        # First time running: create the timestamp file, no deletion
        with open(last_deleted_file, "w") as f:
            f.write(now.isoformat())
        print("First-time setup. Scheduled next deletion after:", now + period)
        return

    # Step 3: Compare with current time and delete if needed
    if now - last_deleted >= period:
        if os.path.exists(outputs_folder):
            shutil.rmtree(outputs_folder)
            print(f"Deleted '{outputs_folder}' folder.")
        else:
            print(f"'{outputs_folder}' folder does not exist.")
        
        # Save new deletion time
        with open(last_deleted_file, "w") as f:
            f.write(now.isoformat())
    else:
        next_time = last_deleted + period
        print(f"Not time to delete yet. Next deletion scheduled for: {next_time}")

def solve_recaptcha_2captcha(driver, page_url, logger, api_key="13d10e1bdeea888e3b06b15d73d0877e"):
    """
    Solve Google reCAPTCHA (enterprise) using 2Captcha and inject token properly.
    Returns True if injection successful, False otherwise.
    """

    import time
    import requests
    from selenium.common.exceptions import NoSuchElementException

    try:
        # --- Step 1: find iframe and extract sitekey ---
        captcha_iframe = driver.find_element(By.CSS_SELECTOR, "iframe[title='reCAPTCHA']")
        src = captcha_iframe.get_attribute("src")
        sitekey = src.split("k=")[1].split("&")[0]
        logger.info(f"🔑 Extracted sitekey: {sitekey}")

        # --- Step 2: send captcha to 2Captcha ---
        payload = {
            "key": api_key,
            "method": "userrecaptcha",
            "googlekey": sitekey,
            "pageurl": page_url,
            "json": 1,
            "enterprise": 1
        }
        logger.info(f"📤 Sending captcha to 2Captcha: {payload}")
        resp = requests.post("http://2captcha.com/in.php", data=payload).json()
        if resp.get("status") != 1:
            raise RuntimeError(f"2Captcha request failed: {resp}")
        captcha_id = resp["request"]

        # --- Step 3: poll for solution ---
        token = None
        for attempt in range(20):
            time.sleep(5)
            res = requests.get(f"http://2captcha.com/res.php?key={api_key}&action=get&id={captcha_id}&json=1").json()
            if res.get("status") == 1:
                token = res["request"]
                logger.info(f"✅ Captcha solved (attempt {attempt+1}): token received")
                break
            logger.info(f"⏳ Waiting for captcha solution (attempt {attempt+1})...")

        if not token:
            raise RuntimeError("2Captcha failed to solve reCAPTCHA")

        # --- Step 4: inject token into page ---
        driver.save_screenshot("captcha_token_before_injection.png")

        driver.execute_script("""
            let response = document.getElementById('g-recaptcha-response');
            if (!response) {
                response = document.createElement('textarea');
                response.id = 'g-recaptcha-response';
                response.name = 'g-recaptcha-response';
                response.style.display = 'block';
                document.body.appendChild(response);
            }
            response.innerHTML = arguments[0];
            response.value = arguments[0];
            response.dispatchEvent(new Event('change', { bubbles: true }));
        """, token)

        driver.save_screenshot("captcha_token_after_injection.png")
        logger.info(f"📸 Screenshots saved before/after token injection")
        return True

    except NoSuchElementException:
        logger.info("✅ No captcha detected, continuing...")
        return True
    except Exception as e:
        logger.error(f"❌ Captcha solving failed: {e}", exc_info=True)
        driver.save_screenshot("captcha_error.png")
        return False