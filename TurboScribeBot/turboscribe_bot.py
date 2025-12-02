from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime
import logging
import json, os, re
import requests
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException, WebDriverException
import sys
import time
import tempfile
import uuid
from helper import get_language_name, wait_for_download, solve_recaptcha_2captcha

class TurboScribeBot:
    def __init__(self, id, email, password, options, output_dir):
        self.email = email
        self.password = password
        self.options = options
        self.driver = None
        self.wait = None
        self.id = id
        self.download_dir = output_dir

        # Setup logger specific to this bot instance
        log_filename = os.path.join(output_dir, f"{self.id}.log")
        self.logger = logging.getLogger(f"TurboScribeBot-{self.id}")
        self.logger.setLevel(logging.DEBUG)

        # Avoid adding multiple handlers if logger already has them
        if not self.logger.handlers:
            file_handler = logging.FileHandler(log_filename, mode="a", encoding="utf-8")
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        self.logger.info("TurboScribeBot initialized")

        # Metadata report
        self.report = {
            "job_metadata": {
                "id": self.id,
                "started_at": None,
                "finished_at": None,
                "source": None,
                "title": None,
                "status": "processing"
            },
            "options": options,
            "outputs": {},
            "status_log": []
        }

    # def start_browser(self, headless=False):
    #     try:
    #         self.report["job_metadata"]["started_at"] = datetime.now().isoformat()

    #         options = webdriver.ChromeOptions()
    #         options.headless = headless

    #         prefs = {
    #             "download.default_directory": self.download_dir,  # 👈 Set your download path here
    #             "download.prompt_for_download": False,
    #             "download.directory_upgrade": True,
    #             "safebrowsing.enabled": True,
    #             "profile.default_content_setting_values.automatic_downloads": 1
    #         }
    #         options.add_experimental_option("prefs", prefs)

    #         if headless:
    #             options.add_argument("--headless=new")   # <- new way
    #             options.add_argument("--no-sandbox")
    #             options.add_argument("--disable-dev-shm-usage")
    #             options.add_argument("--disable-gpu")  # helps stability on Linux
    #             options.add_argument("--disable-software-rasterizer")
    #             options.add_argument("--disable-blink-features=AutomationControlled")
    #             options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    #                  "AppleWebKit/537.36 (KHTML, like Gecko) "
    #                  "Chrome/126.0.0.0 Safari/537.36")
    #             options.add_argument("--window-size=1280,800")

    #         self.driver = webdriver.Chrome(options=options)
    #         self.wait = WebDriverWait(self.driver, 30)

    #         self.logger.info("Browser started successfully")

    #     except Exception as e:
    #         self.logger.error(f"Failed to start browser: {str(e)}", exc_info=True)
    #         self.report["job_metadata"]["status"] = "failed"
    #         self.report["job_metadata"]["finished_at"] = datetime.now().isoformat()

    #         # add error message in status_log for easier tracking
    #         self.report["status_log"].append({
    #             "step": "start_browser",
    #             "error": str(e),
    #             "time": datetime.now().isoformat()
    #         })
    #         self.driver.quit()
    #         sys.exit(1)

    #         # re-raise if you want the caller to handle stop/cleanup
    #         raise

    def start_browser(self, headless=False):
        try:
            self.report["job_metadata"]["started_at"] = datetime.now().isoformat()

            options = webdriver.ChromeOptions()
            options.headless = headless

            # safer isolated tmp dirs, but no --user-data-dir
            tmp_dir = tempfile.mkdtemp(prefix=f"chrome_{uuid.uuid4()}_")
            options.add_argument(f"--data-path={tmp_dir}")
            options.add_argument(f"--disk-cache-dir={tmp_dir}")
            options.add_argument(f"--crash-dumps-dir={tmp_dir}")

            prefs = {
                "download.default_directory": self.download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True,
                "profile.default_content_setting_values.automatic_downloads": 1
            }
            options.add_experimental_option("prefs", prefs)

            if headless:
                options.add_argument("--headless=new")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--disable-software-rasterizer")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                                    "Chrome/126.0.0.0 Safari/537.36")
                options.add_argument("--window-size=1280,800")

            self.driver = webdriver.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, 30)

            self.logger.info("Browser started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start browser: {str(e)}", exc_info=True)
            self.report["job_metadata"]["status"] = "failed"
            self.report["job_metadata"]["finished_at"] = datetime.now().isoformat()
            self.report["status_log"].append({
                "step": "start_browser",
                "error": str(e),
                "time": datetime.now().isoformat()
            })
            if getattr(self, "driver", None):
                try:
                    self.driver.quit()
                except:
                    pass
            self.generate_report(self.download_dir, self.id)
            sys.exit(1)


    def external_links(self, source, link, passcode=None):
        if source == "zoom":
            print("passcode", passcode)
            return self.zoom_link(link, passcode)
        elif source == "onedrive":
            print("passcode", passcode)
            return self.onedrive_link(link, passcode)
        else:
            raise ValueError(f"Unsupported source: {source}")


    def zoom_link(self, link, passcode):
        """
        Process a Zoom recording link, enter passcode if required,
        solve captcha if required, and download files.
        Returns the downloaded video path.
        """

        def debug_screenshot(tag):
            """Save screenshot with timestamp for debug"""
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = os.path.join(self.download_dir, f"{tag}_{ts}.png")
            try:
                self.driver.save_screenshot(fname)
                self.logger.info(f"📸 Screenshot saved: {fname}")
            except Exception as e:
                self.logger.warning(f"⚠️ Could not save screenshot ({tag}): {e}")

        self.logger.info(f"Opening Zoom link: {link}")
        self.driver.get(link)
        time.sleep(3)
        debug_screenshot("initial_page")

        # --- STEP 1: Captcha handling ---
        try:
            captcha_iframe = self.driver.find_element(By.CSS_SELECTOR, "iframe[title='reCAPTCHA']")
            self.logger.info("⚠️ Captcha detected, solving with 2Captcha...")
            debug_screenshot("captcha_detected")

            page_url = self.driver.current_url
            sitekey = captcha_iframe.get_attribute("src").split("k=")[1].split("&")[0]

            token = solve_recaptcha_2captcha(self.driver, self.driver.current_url, self.logger, api_key="13d10e1bdeea888e3b06b15d73d0877e")
            # Inject into page
            self.driver.execute_script("""
                document.querySelectorAll("textarea[name='g-recaptcha-response']")
                    .forEach(el => el.value = arguments[0]);
            """, token)
            debug_screenshot("captcha_token_injected")

            self.logger.info("✅ Captcha token injected, form should continue...")
        except NoSuchElementException:
            self.logger.info("✅ No captcha detected, continuing...")
        except Exception as e:
            self.logger.error(f"❌ Captcha handling failed: {e}", exc_info=True)
            debug_screenshot("captcha_error")

        # --- STEP 2: Passcode handling ---
        try:
            passcode_input = self.wait.until(
                EC.presence_of_element_located((By.ID, "passcode"))
            )
            self.logger.info("🔒 Passcode required for this Zoom recording.")

            if not passcode:
                raise ValueError("Passcode is required but not provided.")

            passcode_input.clear()
            for ch in passcode:
                passcode_input.send_keys(ch)
                time.sleep(0.2)  # slow down typing


            watch_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "passcode_btn"))
            )
            watch_button.click()
            self.logger.info("✅ Passcode submitted successfully.")
            debug_screenshot("passcode_submitted")

            time.sleep(5)
        except TimeoutException:
            self.logger.info("🔓 No passcode required, continuing...")
        except Exception as e:
            self.logger.error(f"❌ Passcode handling failed: {e}", exc_info=True)
            debug_screenshot("passcode_error")

        # --- STEP 3: Download handling ---
        try:
            download_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.download-btn"))
            )
            self.logger.info("✅ Download button found. Clicking...")
            debug_screenshot("download_button")
            download_btn.click()

            time.sleep(30)
            self.logger.info("📥 Download(s) initiated... waiting for completion.")
            wait_for_download(self.download_dir)

            wanted_files = []
            mp4_file = ""

            for f in os.listdir(self.download_dir):
                if f.endswith(".mp4"):
                    mp4_file = os.path.join(self.download_dir, f)
                    wanted_files.append(mp4_file)
                elif f.endswith(".vtt") or f.endswith(".txt"):
                    wanted_files.append(os.path.join(self.download_dir, f))

            if wanted_files:
                self.logger.info(f"✅ Kept files: {wanted_files}")
                self.report["outputs"]["source_files"] = wanted_files
                return mp4_file
            else:
                self.logger.warning("⚠️ No matching files found (mp4, vtt, txt).")
                debug_screenshot("no_files_found")
                error_message = "No matching files downloaded (expected .mp4, .vtt, or .txt)."

                self.logger.error(f"❌ {error_message}")

                # Save failure into report
                self.report["job_metadata"]["status"] = "failed"
                self.report["job_metadata"]["finished_at"] = datetime.now().isoformat()
                self.report["status_log"].append({
                    "step": "zoom_link",
                    "error": error_message,
                    "time": datetime.now().isoformat()
                })
                raise


        except Exception as e:
            self.logger.error(f"❌ Failed to extract Zoom downloads: {str(e)}", exc_info=True)
            self.report["job_metadata"]["status"] = "failed"
            self.report["job_metadata"]["finished_at"] = datetime.now().isoformat()
            self.report["status_log"].append({
                "step": "zoom_link",
                "error": str(e),
                "time": datetime.now().isoformat()
            })
            try:
                self.logger.error(f"🌍 Current URL: {self.driver.current_url}")
                self.logger.error("🔎 Current Page HTML:\n" + self.driver.page_source)
            except Exception as dump_err:
                self.logger.error(f"❌ Failed to dump page HTML: {dump_err}")
            debug_screenshot("download_error")
            self.driver.quit()
            self.generate_report(self.download_dir, self.id)
            sys.exit(1)


            

    # def onedrive_link(self, link):
    #     self.logger.info("Processing OneDrive link...")
    #     self.driver.get(link)
    #     time.sleep(10)

    #     try:
    #         # Wait until the download button is present and clickable
    #         download_button = self.wait.until(
    #             EC.element_to_be_clickable((By.ID, "__photo-view-download"))
    #         )
    #         self.logger.info("✅ Download button found. Clicking...")
    #         download_button.click()

    #         # Wait for the toast "Downloading media" to appear
    #         self.logger.info("⏳ Waiting for 'Downloading media' toast to appear...")
    #         self.wait.until(
    #             EC.presence_of_element_located((By.XPATH, "//span[text()='Downloading media']"))
    #         )
    #         self.logger.debug("📥 Download started...")

    #         # Wait until toast disappears (download finished)
    #         self.logger.debug("⏳ Waiting for download to finish...")
    #         self.wait.until_not(
    #             EC.presence_of_element_located((By.XPATH, "//span[text()='Downloading media']"))
    #         )

    #         # Now locate the downloaded .mp4 file in download_dir
    #         transcript_path = ""
    #         for f in os.listdir(self.download_dir):
    #             if f.endswith(".mp4"):
    #                 transcript_path = os.path.join(self.download_dir, f)
    #                 break

    #         if transcript_path:
    #             self.logger.info(f"✅ Download completed. {transcript_path}")
    #             self.report["outputs"]["source"] = transcript_path
    #             return transcript_path
    #         else:
    #             self.logger.error("❌ MP4 file not found in download directory.")
    #             self.driver.quit()
    #             sys.exit(1)

    #     except Exception as e:
    #         self.logger.error(f"Failed to download onedrive video: {str(e)}", exc_info=True)
    #         self.report["job_metadata"]["status"] = "failed"
    #         self.report["job_metadata"]["finished_at"] = datetime.now().isoformat()

    #         # add error message in status_log for easier tracking
    #         self.report["status_log"].append({
    #             "step": "onedrive_link",
    #             "error": str(e),
    #             "time": datetime.now().isoformat()
    #         })
    #         self.driver.quit()
    #         sys.exit(1)

    def onedrive_link(self, onedrive_url, passcode, wait_time=300):
        """
        Automate OneDrive access with specific CSS selectors.
        Handles passcode, waits for session, logs progress, and captures debug screenshots.
        Returns True if successful.
        """

        def debug_screenshot(tag):
            """Save screenshot with timestamp for debugging"""
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = os.path.join(self.download_dir, f"onedrive_{tag}_{ts}.png")
            try:
                self.driver.save_screenshot(fname)
                self.logger.info(f"📸 Screenshot saved: {fname}")
            except Exception as e:
                self.logger.warning(f"⚠️ Could not save screenshot ({tag}): {e}")

        self.logger.info(f"🌐 Opening OneDrive link: {onedrive_url}")

        try:
            self.driver.get(onedrive_url)
            time.sleep(3)
            #debug_screenshot("initial_page")

            wait = WebDriverWait(self.driver, 15)

            # --- STEP 1: Passcode input ---
            try:
                password_input = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type="password"][placeholder="Enter password"]'))
                )
                self.logger.info("🔒 Passcode input detected on OneDrive page.")

                if not passcode:
                    raise ValueError("Passcode is required but not provided.")

                password_input.clear()
                for ch in passcode:
                    password_input.send_keys(ch)
                    time.sleep(0.15)  # type slowly to mimic user

                self.logger.info("✅ Passcode entered successfully.")
                #debug_screenshot("passcode_entered")

                # --- STEP 2: Submit button ---
                try:
                    submit_button = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Enter password"]'))
                    )
                    submit_button.click()
                    self.logger.info("✅ Submit button clicked.")
                    #debug_screenshot("submit_clicked")

                except TimeoutException:
                    self.logger.warning("⚠️ Submit button not found; page might auto-submit.")
                    debug_screenshot("no_submit_button")

                time.sleep(5)

            except TimeoutException:
                self.logger.info("🔓 No passcode field detected — continuing.")
                debug_screenshot("no_passcode_field")

            # # --- STEP 3: Session keeping ---
            # try:
            #     self.logger.info(f"🕒 Holding OneDrive session active for {wait_time} seconds...")
            #     start_time = time.time()
            #     elapsed = 0

            #     while elapsed < wait_time:
            #         time.sleep(30)
            #         elapsed = int(time.time() - start_time)
            #         self.logger.info(f"⏳ Session active... {elapsed}/{wait_time} seconds elapsed.")

            #     self.logger.info("✅ OneDrive session completed successfully.")
            #     debug_screenshot("session_complete")
            #     return True

            # except Exception as e:
            #     self.logger.error(f"❌ Session handling error: {e}", exc_info=True)
            #     debug_screenshot("session_error")
            #     raise
            # --- STEP 2: Download handling ---
            try:
                self.logger.info("🔍 Searching for download button...")
                download_button = self.wait.until(
                    EC.element_to_be_clickable((By.ID, "__photo-view-download"))
                )
                self.logger.info("✅ Download button found. Clicking...")
                #debug_screenshot("download_button")
                download_button.click()

                # Wait for the toast "Downloading media" to appear
                self.logger.info("⏳ Waiting for 'Downloading media' notification...")
                try:
                    self.wait.until(
                        EC.presence_of_element_located((By.XPATH, "//span[text()='Downloading media']"))
                    )
                    self.logger.info("📥 Download started.")
                    #debug_screenshot("download_started")

                    # Wait until the toast disappears (download complete)
                    self.wait.until_not(
                        EC.presence_of_element_located((By.XPATH, "//span[text()='Downloading media']"))
                    )
                    self.logger.info("✅ Download finished signal detected.")
                    #debug_screenshot("download_finished")
                except TimeoutException:
                    self.logger.warning("⚠️ Could not detect download toast; continuing anyway.")

                # Wait for file to appear in the download directory
                self.logger.info("📂 Checking downloaded files...")
                time.sleep(10)

                wanted_files = []
                mp4_file = ""

                for f in os.listdir(self.download_dir):
                    if f.endswith(".mp4"):
                        mp4_file = os.path.join(self.download_dir, f)
                        wanted_files.append(mp4_file)

                if mp4_file:
                    self.logger.info(f"✅ Download completed: {mp4_file}")
                    self.report["outputs"]["source"] = mp4_file
                    return mp4_file
                else:
                    self.logger.warning("⚠️ No MP4 file found in download directory.")
                    debug_screenshot("no_mp4_found")
                    error_message = "No matching files downloaded."

                    self.logger.error(f"❌ {error_message}")
                    
                    # Save failure into report
                    self.report["job_metadata"]["status"] = "failed"
                    self.report["job_metadata"]["finished_at"] = datetime.now().isoformat()
                    self.report["status_log"].append({
                        "step": "onedrive_link",
                        "error": error_message,
                        "time": datetime.now().isoformat()
                    })
                    raise

            except Exception as e:
                self.logger.error(f"❌ OneDrive download failed: {str(e)}", exc_info=True)
                self.report["job_metadata"]["status"] = "failed"
                self.report["job_metadata"]["finished_at"] = datetime.now().isoformat()
                self.report["status_log"].append({
                    "step": "onedrive_download",
                    "error": str(e),
                    "time": datetime.now().isoformat()
                })
                debug_screenshot("download_error")
                raise

        except Exception as e:
            self.logger.error(f"❌ OneDrive automation failed: {str(e)}", exc_info=True)
            self.report["job_metadata"]["status"] = "failed"
            self.report["job_metadata"]["finished_at"] = datetime.now().isoformat()
            self.report["status_log"].append({
                "step": "onedrive_automation",
                "error": str(e),
                "time": datetime.now().isoformat()
            })
            try:
                self.logger.error(f"🌍 Current URL: {self.driver.current_url}")
                self.logger.error("🔎 Current Page HTML:\n" + self.driver.page_source)
            except Exception as dump_err:
                self.logger.error(f"❌ Failed to dump page HTML: {dump_err}")
            debug_screenshot("fatal_error")
            self.driver.quit()
            self.generate_report(self.download_dir, self.id)
            sys.exit(1)

    def login(self):
        try:
            self.logger.info("Navigating to login page...")
            self.driver.get("https://turboscribe.ai/login")

            # Wait for login form
            email_input = self.wait.until(
                EC.presence_of_element_located((By.NAME, "email"))
            )
            password_input = self.driver.find_element(By.NAME, "password")

            # Fill credentials
            email_input.send_keys(self.email)
            password_input.send_keys(self.password)
            password_input.send_keys(Keys.RETURN)

            # Wait until dashboard loads
            self.wait.until(EC.url_contains("turboscribe.ai"))

            self.logger.info("Login successful")

        except Exception as e:
            self.report["job_metadata"]["status"] = "failed"
            # add error message in status_log for easier tracking
            self.report["status_log"].append({
                "step": "login",
                "error": str(e),
                "time": datetime.now().isoformat()
            })
            self.logger.error(f"Login failed: {str(e)}", exc_info=True)
            self.driver.quit()
            self.generate_report(self.download_dir, self.id)
            sys.exit(1)
            raise

    def open_language_menu(self):
        """Click the language toggle button to open the dropdown."""
        self.logger.debug("Opening the language dropdown menu...")
        try:
            button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.dui-btn"))
            )
            button.click()
            self.logger.debug("Language dropdown opened.")
        except Exception:
            self.logger.exception("Failed to open language dropdown.")

    def switch_to_arabic(self):
        self.logger.info("Switching UI language to Arabic...")
        try:
            arabic_options = self.driver.find_elements(By.XPATH, "//li[.//span[contains(text(), 'العربية')]]")
            self.logger.info(f"Found {len(arabic_options)} Arabic option(s).")
            for i, el in enumerate(arabic_options):
                self.logger.debug(f"Option {i}: {el.text}")
            
            # Try clicking the first one
            if arabic_options:
                self.driver.execute_script("arguments[0].scrollIntoView(true);", arabic_options[0])
                time.sleep(0.5)  # let any animation finish
                arabic_options[0].click()
                self.logger.info("Clicked Arabic language option.")
            else:
                self.logger.error("No Arabic language options found.")
        except Exception as e:
            self.logger.exception("Failed to switch language to Arabic")

    def upload_file(self, file_path):
        try:
            self.report["job_metadata"]["source"] = file_path
            self.logger.info(f"Uploading file: {file_path}")

            # Step 1: Click the "Transcribe Your First File" button
            first_btn = self.wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "span.dui-btn.dui-modal-button.dui-btn-primary")
            ))
            first_btn.click()
            self.logger.debug("Clicked 'Transcribe Your First File' button")

            # Step 2: Send file path to the hidden file input
            file_input = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[type='file'].dz-hidden-input")
            ))
            file_input.send_keys(file_path)
            self.logger.debug(f"Sent file path to input: {file_path}")

            # Step 3: Monitor progress
            self.logger.info("⏳ Monitoring upload progress...")

            while True:
                # Check for upload failure
                try:
                    error_elem = self.driver.find_element(By.CSS_SELECTOR, "span[data-dz-errormessage]")
                    error_text = error_elem.text.strip()
                    if error_text:
                        raise Exception(f"❌ Upload failed: {error_text}")
                except Exception:
                    # Element might not exist yet; ignore
                    pass

                # Try reading progress percentage
                try:
                    percentage_elem = self.driver.find_element(By.CSS_SELECTOR, "div[data-dz-uploadprogress-percentage]")
                    percent = percentage_elem.text.strip()
                    self.logger.debug(f"⏳ Uploading... {percent}")
                except Exception:
                    self.logger.debug("Progress element not found (yet).")

                # Check for success checkmark
                try:
                    complete_elem = self.driver.find_element(By.CSS_SELECTOR, "div[data-dz-uploadprogress-complete]")
                    if complete_elem.value_of_css_property("display") != "none":
                        self.logger.info("✅ Upload completed successfully.")
                        break
                except Exception:
                    pass

                time.sleep(2)  # Poll every 2 seconds


        except Exception as e:
            self.report["job_metadata"]["status"] = "failed"
            self.report["status_log"].append({
                "step": "upload_file",
                "error": str(e),
                "time": datetime.now().isoformat()
            })
            self.logger.error(f"❌ File upload failed for {file_path}: {e}", exc_info=True)
            self.driver.quit()
            self.generate_report(self.download_dir, self.id)
            sys.exit(1)
    
    def import_from_link(self, url: str):

        self.report["job_metadata"]["source"] = url

        try:
            self.logger.info(f"🚀 Starting import from link: {url}")

            # Step 1: click "نسخ ملفك الأول" button
            first_btn = self.wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "span.dui-btn.dui-modal-button.dui-btn-primary")
            ))
            first_btn.click()
            self.logger.debug("Clicked 'Transcribe Your First File' button")

            # Step 2: click "Import from Link" button
            import_btn = self.wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[aria-label][title][class*='dui-btn-ghost']")
            ))
            import_btn.click()
            self.logger.debug("Clicked 'Import from Link' button")

            # Step 3: paste the link
            url_input = self.wait.until(EC.presence_of_element_located(
                (By.NAME, "media-url")
            ))
            url_input.clear()
            url_input.send_keys(url)
            self.logger.debug(f"Pasted media link: {url}")

            # Step 4: Click "Import" button
            import_button = self.wait.until(EC.element_to_be_clickable((
                By.XPATH, "//button[@type='submit' and contains(@class,'dui-btn-primary')]//div[normalize-space()='استيراد' or normalize-space()='Import']"
            )))
            import_button.click()
            self.logger.debug("Clicked 'Import' button")

            # Step 5: Wait for file preview to appear
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                    "div.dz-preview.dz-file-preview.dz-success.dz-complete"))
            )
            self.logger.info("✅ Import finished successfully")
            #print("✅ Import finished successfully")

        except (TimeoutException, NoSuchElementException, WebDriverException) as e:
            self.logger.error(f"❌ Import failed: {e}", exc_info=True)

            # Update metadata with error info
            self.report["job_metadata"]["status"] = "failed"
            self.report["status_log"].append({
                "step": "import_from_link",
                "error": str(e),
                "time": datetime.now().isoformat()
            })
            self.driver.quit()
            self.generate_report(self.download_dir, self.id)
            sys.exit(1)

        except Exception as e:
            self.logger.error(f"🔥 Unexpected error: {e}", exc_info=True)

            self.report["job_metadata"]["status"] = "failed"
            self.report["status_log"].append({
                "step": "import_from_link",
                "error": str(e),
                "time": datetime.now().isoformat()
            })
            self.driver.quit()
            self.generate_report(self.download_dir, self.id)
            sys.exit(1)

    # def select_options(self):
    #     time.sleep(0.2)
    #     print(self.options)

    #     try:
    #         # جرّب النص الإنجليزي
    #         element = wait.until(
    #             EC.element_to_be_clickable(
    #                 (By.XPATH, "//div[contains(@class,'cursor-pointer')]//span[normalize-space(text())='Speaker Recognition & More Settings']")
    #             )
    #         )
    #         print("✅ English version found")

    #     except:
    #         try:
    #             # جرّب النص العربي
    #             element = wait.until(
    #                 EC.element_to_be_clickable(
    #                     (By.XPATH, "//div[contains(@class,'cursor-pointer')]//span[normalize-space(text())='التعرف على المتحدث والمزيد من الإعدادات']")
    #                 )
    #             )
    #             print("✅ Arabic version found")

    #         except:
    #             # fallback: الأيقونة 👥
    #             element = self.wait.until(
    #                 EC.element_to_be_clickable(
    #                     (By.XPATH, "//div[contains(@class,'cursor-pointer')]//img[@alt='👥']/ancestor::div[contains(@class,'cursor-pointer')]")
    #                 )
    #             )
    #             print("✅ Fallback to icon 👥")

    #     # اضغط العنصر
    #     element.click()
    #     print("👉 Clicked successfully")

    #     # 1️⃣ اختار اللغة
    #     if "language" in self.options:
    #         lang_dropdown = self.wait.until(
    #             EC.presence_of_element_located((By.NAME, "language"))
    #         )
    #         select = Select(lang_dropdown)
    #         select.select_by_value(self.options["language"])  

    #         print(f"[+] Language selected: {self.options['language']}")
    #         time.sleep(0.2)
        

    #     if "model" in self.options:
    #         # Wait for all available model options
    #         models = self.wait.until(
    #             EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'input[name="whisper-model"]'))
    #         )

    #         model_value = self.options["model"]

    #         # Find the input with the correct value
    #         for model in models:
    #             if model.get_attribute("value") == model_value:
    #                 model_id = model.get_attribute("id")
                    
    #                 # Click its label instead of the hidden input
    #                 label = self.wait.until(
    #                     EC.element_to_be_clickable((By.CSS_SELECTOR, f'label[for="{model_id}"]'))
    #                 )
    #                 self.driver.execute_script("arguments[0].scrollIntoView(true);", label)
    #                 label.click()
    #                 print(f"✅ Selected model: {model_value}")
    #                 break  
    #         time.sleep(0.2)

    #     if self.options["recognize_speakers"] is not None:  # means --speakers was passed
    #         try:
    #             recognize_checkbox = self.wait.until(
    #                 EC.presence_of_element_located((
    #                     By.XPATH,
    #                     "//input[@type='checkbox' and @name='bool:diarize?']"
    #                 ))
    #             )

    #             # ✅ Click checkbox if not already enabled
    #             if not recognize_checkbox.is_selected():
    #                 recognize_checkbox.click()
    #                 print("✅ Recognize Speakers option enabled")
    #             else:
    #                 print("ℹ️ Recognize Speakers already enabled")

    #             # ✅ Handle dropdown for number of speakers
    #             num_speakers = str(self.options["recognize_speakers"])  # must be string for select_by_value
    #             dropdown = self.driver.find_element(By.NAME, "int:num-speakers")
    #             select = Select(dropdown)

    #             # select by value
    #             select.select_by_value(num_speakers)
    #             print(f"🎯 Speakers count set to {num_speakers}")

    #         except Exception as e:
    #             print(f"⚠️ Could not enable Recognize Speakers or select dropdown: {e}")

    #         time.sleep(5)

    #     if self.options["transcribe"] == True:
    #         try:
    #             transcribe_checkbox = self.wait.until(
    #                 EC.presence_of_element_located((
    #                     By.XPATH,
    #                     "//input[@type='checkbox' and @name='bool:translate-to-english?']"
    #                 ))
    #             )

    #             if not transcribe_checkbox.is_selected():
    #                 transcribe_checkbox.click()
    #                 print("✅ Transcribe to English option enabled")
    #             else:
    #                 print("ℹ️ Transcribe to English already enabled")

    #         except Exception as e:
    #             print(f"⚠️ Could not find 'Transcribe to English' checkbox: {e}")

    #         time.sleep(0.2)
        
    #     if self.options["restore_audio"] == True:
    #         try:
    #             transcribe_checkbox = self.wait.until(
    #                 EC.presence_of_element_located((
    #                     By.XPATH,
    #                     "//input[@type='checkbox' and @name='bool:clean-up-audio?']"
    #                 ))
    #             )

    #             if not transcribe_checkbox.is_selected():
    #                 transcribe_checkbox.click()
    #                 print("✅ restore audio option enabled")
    #             else:
    #                 print("ℹ️ restore audio already enabled")

    #         except Exception as e:
    #             print(f"⚠️ Could not find 'restore audio' checkbox: {e}")

    #         time.sleep(0.2)
    #     time.sleep(0.5)

    def select_options(self):
        """
        Selects transcription options (language, model, speakers, etc.)
        Updates report metadata and logs progress/errors.
        """

        self.logger.info("⚙️ Selecting transcription options...")

        try:
            self.logger.debug(f"Options provided: {self.options}")
            # Fallback: 👥 icon
            element = self.wait.until(
                EC.element_to_be_clickable((By.XPATH,
                    "//div[contains(@class,'cursor-pointer')]//img[@alt='👥']/ancestor::div[contains(@class,'cursor-pointer')]"
                ))
            )
            self.logger.info("✅ Fallback: found 👥 icon")

            element.click()
            self.logger.debug("👉 Settings menu clicked")

            # Step 2: Language
            if "language" in self.options:
                lang = get_language_name(self.options["language"])
                lang_dropdown = self.wait.until(
                    EC.presence_of_element_located((By.NAME, "language"))
                )
                select = Select(lang_dropdown)
                select.select_by_value(lang)  
                self.logger.info(f"🌐 Language selected: {lang}")

            # Step 3: Model
            if "model" in self.options:
                models = self.wait.until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'input[name="whisper-model"]'))
                )
                model_value = self.options["model"]

                for model in models:
                    if model.get_attribute("value") == model_value:
                        model_id = model.get_attribute("id")
                        label = self.wait.until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, f'label[for="{model_id}"]'))
                        )
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", label)
                        label.click()
                        self.logger.info(f"🤖 Whisper model selected: {model_value}")
                        break  

            # Step 4: Speaker recognition
            if self.options.get("recognize_speakers") is not None:
                try:
                    recognize_checkbox = self.wait.until(EC.presence_of_element_located((
                        By.XPATH, "//input[@type='checkbox' and @name='bool:diarize?']"
                    )))

                    if not recognize_checkbox.is_selected():
                        recognize_checkbox.click()
                        self.logger.info("✅ Recognize Speakers enabled")
                    else:
                        self.logger.debug("ℹ️ Recognize Speakers already enabled")

                    num_speakers = str(self.options["recognize_speakers"])
                    dropdown = self.driver.find_element(By.NAME, "int:num-speakers")
                    select = Select(dropdown)
                    select.select_by_value(num_speakers)
                    self.logger.info(f"🎯 Speakers count set: {num_speakers}")

                except Exception as e:
                    self.logger.warning(f"⚠️ Could not configure speaker recognition: {e}")

            # Step 5: Transcribe to English
            if self.options.get("transcribe"):
                try:
                    transcribe_checkbox = self.wait.until(EC.presence_of_element_located((
                        By.XPATH, "//input[@type='checkbox' and @name='bool:translate-to-english?']"
                    )))
                    if not transcribe_checkbox.is_selected():
                        transcribe_checkbox.click()
                        self.logger.info("✅ Transcribe to English enabled")
                    else:
                        self.logger.debug("ℹ️ Transcribe already enabled")
                except Exception as e:
                    self.logger.warning(f"⚠️ Could not set transcribe option: {e}")

            # Step 6: Restore audio
            if self.options.get("restore_audio"):
                try:
                    restore_checkbox = self.wait.until(EC.presence_of_element_located((
                        By.XPATH, "//input[@type='checkbox' and @name='bool:clean-up-audio?']"
                    )))
                    if not restore_checkbox.is_selected():
                        restore_checkbox.click()
                        self.logger.info("✅ Restore audio enabled")
                    else:
                        self.logger.debug("ℹ️ Restore audio already enabled")
                except Exception as e:
                    self.logger.warning(f"⚠️ Could not set restore audio: {e}")

            # ✅ Update metadata
            self.logger.info("🎉 Options successfully selected")

        except (TimeoutException, NoSuchElementException, WebDriverException) as e:
            self.logger.error(f"❌ Failed to select options: {e}", exc_info=True)
            self.report["job_metadata"]["status"] = "failed"
            self.report["status_log"].append({
                "step": "selecting_options",
                "error": str(e),
                "time": datetime.now().isoformat()
            })

        except Exception as e:
            self.logger.error(f"🔥 Unexpected error while selecting options: {e}", exc_info=True)
            self.report["job_metadata"]["status"] = "failed"
            self.report["status_log"].append({
                "step": "selecting_options",
                "error": str(e),
                "time": datetime.now().isoformat()
            })

    def start_transcription(self):
        try:
            # Wait until the button with نسخ text is clickable
            # button = self.wait.until(
            #     EC.element_to_be_clickable((
            #         By.XPATH,
            #         "//button[contains(@class,'dui-btn-primary')]//span[text()='نسخ'] | //button[contains(@class,'dui-btn-primary')]//span[text()='TRANSCRIBE']"
            #     ))
            # )
            # button.click()
            button = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[@type='submit' and contains(@class,'dui-btn-primary')]"
                ))
            )
            button.click()

            #print("✅ Submit button clicked successfully!")
            self.logger.info("✅ Submit button clicked successfully!")
        except Exception as e:
            #print("❌ Failed to click submit button:", e)
            self.logger.error(f"🔥 Unexpected error while submiting the file: {e}", exc_info=True)
            self.report["job_metadata"]["status"] = "failed"
            self.report["status_log"].append({
                "step": "start_transcription",
                "error": str(e),
                "time": datetime.now().isoformat()
            })
            self.driver.quit()
            self.generate_report(self.download_dir, self.id)
            sys.exit(1)

        time.sleep(0.5)

    def monitor_proccess(self):
        """
        Monitors the first row in the jobs table until the process finishes.
        Logs updates, updates job metadata, and handles errors gracefully.
        """

        self.logger.info("🔍 Starting to monitor the process...")
        #self.report["job_metadata"]["status"] = "monitoring"
        time.sleep(3)

        try:
            while True:
                # Step 1: get the first row
                first_row = self.wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "table.dui-table tbody tr")
                    )
                )

                # Step 2: get cells
                cells = first_row.find_elements(By.TAG_NAME, "td")
                if self.report["job_metadata"]["title"] == None:
                    title_cell = cells[1]
                    self.report["job_metadata"]["title"] = title_cell.text.strip()
                    #print(title_cell)
                if len(cells) > 5:
                    status_cell = cells[5]
                    status_text = status_cell.text.strip()
                    self.logger.debug(f"📌 Status cell: {status_text}")
                else:
                    self.logger.warning("⚠️ Row does not have enough columns (expected 6).")
                    time.sleep(2)
                    continue

                # Step 3: detect status via SVG class
                try:
                    svg = status_cell.find_element(By.TAG_NAME, "svg")
                    classes = svg.get_attribute("class")
                except NoSuchElementException:
                    classes = ""

                if "text-success" in classes:
                    self.logger.info("✅ Job finished successfully")
                    self.report["job_metadata"]["status"] = "success"

                    # link in 2nd column
                    try:
                        link_el = first_row.find_element(By.CSS_SELECTOR, "td:nth-of-type(2) a")
                        link_url = link_el.get_attribute("href")
                        #self.report["job_metadata"]["result_url"] = link_url
                        self.logger.info(f"🔗 Result URL: {link_url}")

                        self.driver.get(link_url)
                        self.wait.until(EC.url_contains(link_url))
                    except Exception as e:
                        self.logger.warning(f"⚠️ Could not fetch result link: {e}")

                    break

                elif "text-error" in classes:
                    self.logger.error("❌ Job failed")
                    self.report["job_metadata"]["status"] = "failed"
                    break

                else:
                    self.logger.debug("⏳ Still processing...")
                    time.sleep(2)

        except (TimeoutException, WebDriverException) as e:
            self.logger.error(f"🔥 Selenium-related error while monitoring: {e}", exc_info=True)
            self.report["job_metadata"]["status"] = "failed"
            self.report["status_log"].append({
                "step": "monitor_process",
                "error": str(e),
                "time": datetime.now().isoformat()
            })

        except Exception as e:
            self.logger.error(f"🔥 Unexpected error while monitoring: {e}", exc_info=True)
            self.report["job_metadata"]["status"] = "failed"
            self.report["status_log"].append({
                "step": "monitor_process",
                "error": f"Unexpected: {str(e)}",
                "time": datetime.now().isoformat()
            })

        else:
            self.logger.info("📊 Monitoring finished")

    def click_transcript_link(self):
        try:
            toast = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.dui-toast a"))
            )

            # get the transcript link
            link = toast.get_attribute("href")

            # get the title text inside <span class="font-bold">
            title_span = toast.find_element(By.CSS_SELECTOR, "span.font-bold")
            title = title_span.text

            print("Transcript link:", link)
            print("Title:", title)

            self.driver.get(link)
            self.wait.until(EC.url_contains(link))

        except Exception as e:
            print(f"❌ Could not click transcript link for {title}: {e}")

    def export_download(self, output_dir, job_id):
        try:
            self.logger.info(f"📥 Starting download for job_id={job_id}")

            export_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//p[normalize-space()='تصدير متقدم']/ancestor::div[1]"))
            )
            export_button.click()

            self.logger.debug("✅ Clicked 'تصدير متقدم' button")

            # Step 2: Select "تصدير بصيغة TXT" checkbox
            txt_checkbox_label = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[@name='bool:txt?']"))
            )
            txt_checkbox_label.click()
            self.logger.debug("✅ Checked 'تصدير بصيغة TXT'")

            timestamp_checkbox_label = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[@name='bool:timestamps?']"))
            )
            timestamp_checkbox_label.click()
            self.logger.debug("✅ Checked 'علامات الوقت للأقسام'")

            # Step 3: Click the "تنزيل" (Download) button
            download_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[.//span[normalize-space()='تنزيل']]"))
            )
            download_button.click()
            self.logger.info("✅ Download triggered successfully")

            #print(self.download_dir)

            wait_for_download(self.download_dir)
            self.logger.info("✅ Download completed")

            time.sleep(2)

            # Rename downloaded file
            #job_id = self.job_id  # assuming you store it in the class
            transcript_path = os.path.join(self.download_dir, f"file_transcription_{job_id}.txt")
            transcript_path_1 = os.path.join(output_dir, f"file_transcription_{job_id}.txt")
            # Find the latest downloaded .txt file
            for f in os.listdir(self.download_dir):
                if f.endswith(".txt"):
                    downloaded_file = os.path.join(self.download_dir, f)
                    os.rename(downloaded_file, transcript_path)
                    self.logger.info(f"✅ Transcript saved as {transcript_path_1}")
                    break

            self.report["outputs"]["transcription"] = transcript_path_1

            self.driver.refresh()

        except Exception as e:
            self.logger.error(f"❌ Failed to trigger export download: {e}")
            self.report["job_metadata"]["status"] = "failed"
            self.report["status_log"].append({
                "step": "trigger export",
                "error": str(e),
                "time": datetime.now().isoformat()
            })

    def download_results(self, output_dir, job_id):
        try:
            self.logger.info(f"📥 Starting download for job_id={job_id}")

            # Find link and extract URL
            download_link = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '.txt')]"))
            )
            url = download_link.get_attribute("href")
            self.logger.debug(f"Found transcript URL: {url}")

            # Build output path
            transcript_path = os.path.join(output_dir, f"file_transcription_{job_id}.txt")

            # Download directly with requests
            response = requests.get(url, stream=True)
            response.raise_for_status()  # raises HTTPError for bad responses

            with open(transcript_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            #self.report["outputs"]["transcription"] = file_path
            self.logger.info(f"✅ Transcript downloaded → {transcript_path}")

            # Update report metadata
            self.report["outputs"]["transcription"] = transcript_path
            # self.report["job_metadata"]["download_status"] = "success"
            # self.report["job_metadata"]["download_url"] = url

        except requests.exceptions.RequestException as req_err:
            self.logger.error(f"Request error while downloading job_id={job_id}: {req_err}")
            self.report["job_metadata"]["status"] = "failed"
            self.report["status_log"].append({
                "step": "monitor_process",
                "error": f"Unexpected: {str(e)}",
                "time": datetime.now().isoformat()
            })

        except Exception as e:
            self.logger.error(f"Unexpected error while downloading job_id={job_id}: {e}")
            self.report["job_metadata"]["status"] = "failed"
            self.report["status_log"].append({
                "step": "download transcription",
                "error": f"Unexpected: {str(e)}",
                "time": datetime.now().isoformat()
            })

    def chatgpt_click(self):
        try:
            # 1. Click on ChatGPT button
            chatgpt_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(),'ChatGPT')]"))
            )
            chatgpt_btn.click()
            print("✅ Opened ChatGPT section")
        except Exception as e:
            print(f"⚠️ Error clicking on chatGpt button: {e}")
    
    def close_chatgpt(self):
        # try:
        #     # Try using the CSS selector first
        #     close_btn = self.wait.until(
        #         EC.element_to_be_clickable((By.CSS_SELECTOR, "span.dui-btn.dui-btn-md.dui-btn-circle.dui-btn-ghost.absolute.end-4.top-4"))
        #     )
        #     close_btn.click()
        #     print("✅ Closed ChatGPT section using CSS selector")
        # except Exception as e_css:
        #     print(f"⚠️ CSS selector failed: {e_css}")
        try:
            # Fallback: Try using XPath
            # close_btn = self.wait.until(
            #     EC.element_to_be_clickable((By.XPATH, "/html/body/div[11]/label/label/div/div[1]/div[1]/span"))
            # )
            # close_btn.click()
            # close_button = self.wait.until(
            # EC.element_to_be_clickable((
            #     By.XPATH,
            #     "//span[contains(@class, 'dui-btn-circle') and contains(@class, 'top-4') and contains(@class, 'end-4')]"
            #     ))
            # )
            # close_button.click()

            # close_button = self.wait.until(
            #     EC.element_to_be_clickable((By.XPATH, "//span[contains(@class,'dui-btn-circle')]//svg"))
            # )
            # self.driver.execute_script("arguments[0].parentElement.click();", close_button)

            self.driver.refresh()
            time.sleep(1)

            print("✅ Closed ChatGPT section")
        except Exception as e_xpath:
            print(f"❌ Both selectors failed: {e_xpath}")


    def generate_short_summary(self, output_dir, job_id):
        self.logger.info("🔄 Starting short summary generation for job %s", job_id)
        try:
            time.sleep(1)
            try:
                btn = self.driver.find_element(
                    By.XPATH,
                    "//div[@class='grid grid-cols-1 md:grid-cols-3 rounded overflow-hidden']/div[2]//label"
                )
                btn.click()
                self.logger.info("✅ Clicked 'Short Summary' button")
            except Exception as e:
                self.logger.error("❌ Could not find the Short Summary button: %s", e)

            # Wait for summaries
            time.sleep(2)
            textareas = self.driver.find_elements(By.CSS_SELECTOR, "textarea.dui-textarea")

            summaries = [ta.get_attribute("value") for ta in textareas]

            if not summaries:
                self.logger.warning("⚠️ No summaries found for job %s", job_id)
                return

            # Save summaries
            summary_text = "\n\n".join(summaries)
            summary_path = os.path.join(output_dir, f"summary_short_{job_id}.txt")

            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(summary_text)

            self.report["outputs"]["summary_short"] = summary_path

            self.logger.info("📄 Short summary saved: %s", summary_path)

        except Exception as e:
            self.logger.error(f"Unexpected error while generate_short_summary job_id={job_id}: {e}")
            self.report["job_metadata"]["status"] = "failed"
            self.report["status_log"].append({
                "step": "generate_short_summary",
                "error": f"Unexpected: {str(e)}",
                "time": datetime.now().isoformat()
            })

    # def generate_short_summary(self, output_dir, job_id):
    #     try:
    #         time.sleep(2)
    #         try:
    #             # لو ما ظهرش جرّب النص الإنجليزي
    #             btn = self.driver.find_element(
    #                 By.XPATH,
    #                 "//div[@class='grid grid-cols-1 md:grid-cols-3 rounded overflow-hidden']/div[2]//label"
    #             )

    #             btn.click()
    #             print("✅ Clicked 'Short Summary'")
    #         except Exception as e:
    #             print("❌ Could not find the Short Summary button:", e)

    #         #print("✅ Selected short summary option")

    #         # 3. Wait for summaries to appear
    #         time.sleep(5)  # adjust based on how long ChatGPT takes
    #         textareas = self.driver.find_elements(By.CSS_SELECTOR, "textarea.dui-textarea")

    #         summaries = []
    #         for ta in textareas:
    #             summaries.append(ta.get_attribute("value"))

    #         if not summaries:
    #             print("⚠️ No summaries found")
    #             return

    #         # 4. Save to file
    #         summary_text = "\n\n".join(summaries)
    #         summary_path = os.path.join(output_dir, f"summary_short_{job_id}.txt")
    #         with open(summary_path, "w", encoding="utf-8") as f:
    #             f.write(summary_text)

    #         # 5. Update report
    #         self.report["outputs"]["summary_short"] = summary_path
    #         #self.report["status_log"].append(f"Short summary saved at {summary_path}")

    #         print(f"📄 Short summary saved: {summary_path}")
    #         #time.sleep(120)

    #     except Exception as e:
    #         print(f"⚠️ Error generating short summary: {e}")

    def generate_detailed_summary(self, output_dir, job_id):
            try:
                self.logger.info(f"▶️ Starting detailed summary generation for job {job_id}")
                time.sleep(1)

                try:
                    btn = self.driver.find_element(
                        By.XPATH,
                        "//div[@class='grid grid-cols-1 md:grid-cols-3 rounded overflow-hidden']/div[3]//label"
                    )
                    btn.click()
                    self.logger.info("✅ Clicked 'Detailed Summary' button")
                except Exception as e:
                    self.logger.error(f"❌ Could not find 'Detailed Summary' button: {e}")

                # Wait for summaries
                time.sleep(2)
                textareas = self.driver.find_elements(By.CSS_SELECTOR, "textarea.dui-textarea")

                summaries = [ta.get_attribute("value") for ta in textareas]
                if not summaries:
                    self.logger.warning("⚠️ No summaries found")
                    return

                # Save to file
                summary_text = "\n\n".join(summaries)
                summary_path = os.path.join(output_dir, f"summary_detailed_{job_id}.txt")

                with open(summary_path, "w", encoding="utf-8") as f:
                    f.write(summary_text)

                # Update report metadata
                self.report["outputs"]["summary_detailed"] = summary_path

                self.logger.info(f"📄 Detailed summary saved at {summary_path}")
            
            except Exception as e:
                self.logger.error(f"Unexpected error while generate_detailed_summary job_id={job_id}: {e}")
                self.report["job_metadata"]["status"] = "failed"
                self.report["status_log"].append({
                    "step": "generate_detailed_summary",
                    "error": f"Unexpected: {str(e)}",
                    "time": datetime.now().isoformat()
                })

    # def generate_detailed_summary(self, output_dir, job_id):
    #     try:
    #         time.sleep(2)
    #         try:
    #             # لو ما ظهرش جرّب النص الإنجليزي
    #             btn = self.driver.find_element(
    #                 By.XPATH,
    #                 "//div[@class='grid grid-cols-1 md:grid-cols-3 rounded overflow-hidden']/div[3]//label"
    #             )

    #             btn.click()
    #             print("✅ Clicked 'Detailed Summary'")
    #         except Exception as e:
    #             print("❌ Could not find the Detailed Summary button:", e)

    #         # 3. Wait for summaries to appear
    #         time.sleep(5)  # adjust based on how long ChatGPT takes
    #         textareas = self.driver.find_elements(By.CSS_SELECTOR, "textarea.dui-textarea")

    #         summaries = []
    #         for ta in textareas:
    #             summaries.append(ta.get_attribute("value"))

    #         if not summaries:
    #             print("⚠️ No summaries found")
    #             return

    #         # 4. Save to file
    #         summary_text = "\n\n".join(summaries)
    #         summary_path = os.path.join(output_dir, f"summary_detailed_{job_id}.txt")
    #         with open(summary_path, "w", encoding="utf-8") as f:
    #             f.write(summary_text)

    #         # 5. Update report
    #         self.report["outputs"]["summary_detailed"] = summary_path
    #         #self.report["status_log"].append(f"Short summary saved at {summary_path}")

    #         print(f"📄 Detailed summary saved: {summary_path}")
    #         #time.sleep(120)

    #     except Exception as e:
    #         print(f"⚠️ Error generating detailed summary: {e}")

    # def translate(self, target_lang, output_dir, job_id):
    #     if self.options.get("translate"):   
    #         translate_link = self.wait.until(
    #             EC.element_to_be_clickable((By.XPATH, "//div[contains(text(),'Translate') or contains(text(),'ترجمة')]"))
    #         )
    #         translate_link.click()
    #         print("✅ Translate button clicked")

    #         # 2. Switch to new tab
    #         self.driver.switch_to.window(self.driver.window_handles[-1])

    #         current_url = self.driver.current_url

    #         # append Google Translate params
    #         if "_x_tr_tl=" in current_url:
    #             # replace existing translation target
    #             new_url = re.sub(r"_x_tr_tl=\w+", f"_x_tr_tl={target_lang}", current_url)
    #         else:
    #             # add new param if missing
    #             join_char = "&" if "?" in current_url else "?"
    #             new_url = f"{current_url}{join_char}_x_tr_sl=auto&_x_tr_tl={target_lang}&_x_tr_hl=ar"

    #         # navigate to translated page
    #         self.driver.get(new_url)

    #         time.sleep(2)

    #         try:
    #             # Locate the article
    #             article = self.wait.until(
    #                 EC.presence_of_element_located((By.XPATH, "//article[contains(@class,'prose')]"))
    #             )

    #             # Get all text inside spans marked as translate="yes"
    #             translated_parts = article.find_elements(By.XPATH, ".//span[@translate='yes']")
                
    #             # Join them into full text
    #             text = "\n".join([part.text.strip() for part in translated_parts if part.text.strip()])

    #             print("✅ Extracted Translated")

    #             translate_path = os.path.join(output_dir, f"translate_{job_id}.txt")

    #             with open(translate_path, "w", encoding="utf-8") as f:
    #                 f.write(text)
    #             self.report["outputs"]["traslate"] = translate_path

    #         except Exception as e:
    #             print(f"❌ Failed to extract translated text: {e}")

    #         print(f"✅ Translation started into {target_lang}")

    def translate(self, target_lang, output_dir, job_id):
        if not self.options.get("translate"):
            self.logger.info("ℹ️ Translation skipped (disabled in options).")
            return

        try:
            self.logger.info(f"▶️ Starting translation for job {job_id} into {target_lang}")

            # Step 1: Click translate button
            translate_link = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//div[contains(text(),'Translate') or contains(text(),'ترجمة')]")
                )
            )
            translate_link.click()
            self.logger.info("✅ Translate button clicked")

            # Step 2: Switch to new tab
            self.driver.switch_to.window(self.driver.window_handles[-1])
            current_url = self.driver.current_url

            # Step 3: Append Google Translate params
            if "_x_tr_tl=" in current_url:
                new_url = re.sub(r"_x_tr_tl=\w+", f"_x_tr_tl={target_lang}", current_url)
            else:
                join_char = "&" if "?" in current_url else "?"
                new_url = f"{current_url}{join_char}_x_tr_sl=auto&_x_tr_tl={target_lang}&_x_tr_hl=ar"

            self.driver.get(new_url)
            time.sleep(2)

            # Step 4: Extract translated article
            try:
                article = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//article[contains(@class,'prose')]"))
                )
                translated_parts = article.find_elements(By.XPATH, ".//span[@translate='yes']")
                text = "\n".join([part.text.strip() for part in translated_parts if part.text.strip()])

                if not text:
                    raise ValueError("No translated text extracted")

                translate_path = os.path.join(output_dir, f"translate_{job_id}.txt")
                with open(translate_path, "w", encoding="utf-8") as f:
                    f.write(text)

                self.report["outputs"]["translate"] = translate_path
                self.logger.info(f"📄 Translation saved at {translate_path}")

            except Exception as e:
                self.logger.error(f"❌ Failed to extract translated text: {e}", exc_info=True)
                self.report["job_metadata"]["status"] = "failed"
                self.report["status_log"].append({
                    "step": "translate",
                    "error": str(e),
                    "time": datetime.now().isoformat()
                })

        except Exception as e:
            self.logger.error(f"🔥 Unexpected error during translation: {e}", exc_info=True)
            self.report["job_metadata"]["status"] = "failed"
            self.report["status_log"].append({
                "step": "translate",
                "error": str(e),
                "time": datetime.now().isoformat()
            })

    
    def download_audio(self, output_dir, job_id):
        """
        Download transcribed audio file from TurboScribe job page.

        Args:
            output_dir (str): Directory where file will be saved
            job_id (str): Unique job identifier for naming
        """
        try:
            self.logger.info(f"🔍 Looking for audio download link for job {job_id}...")

            # Find the <a> with download attribute
            audio_link = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//a[@download][contains(@href, '.mp3')]"))
            )

            # Extract the URL
            url = audio_link.get_attribute("href")
            file_path = os.path.join(output_dir, f"file_{job_id}.mp3")

            # Download
            logging.info(f"⬇️ Downloading audio from {url} ...")
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # ✅ Update metadata
            #self.report["job_metadata"]["download_url"] = url
            self.report["outputs"]["file"] = file_path
            #self.report["status"] = "success"

            self.logger.info(f"✅ File downloaded successfully: {file_path}")

        except Exception as e:
            # ❌ Update metadata with failure info
            self.report["job_metadata"]["status"] = "failed"
            self.report["status_log"].append({
                "step": "download_audio",
                "error": str(e),
                "time": datetime.now().isoformat()
            })

    def change_owner(self, output_dir, owner):
        """
        Change the owner of a given folder to the specified user.
        Uses self.logger for detailed logs and handles all errors gracefully.
        """
        import pwd, os

        if not owner:
            self.logger.info("ℹ️ No owner specified; skipping ownership change.")
            return

        self.logger.info(f"👤 Attempting to change folder owner to '{owner}' for: {output_dir}")

        try:
            user_info = pwd.getpwnam(owner)
            uid, gid = user_info.pw_uid, user_info.pw_gid
            os.chown(output_dir, uid, gid)
            self.logger.info(f"✅ Folder owner successfully changed to '{owner}'.")
        except KeyError:
            self.logger.error(f"❌ User '{owner}' not found on this system.")
        except PermissionError:
            self.logger.error(f"⚠️ Permission denied. Run as root to change owner to '{owner}'.")
        except Exception as e:
            self.logger.error(f"❌ Unexpected error changing owner to '{owner}': {e}", exc_info=True)


    def generate_report(self, output_dir, id, finished=False):
        if finished:
            self.report["job_metadata"]["finished_at"] = datetime.now().isoformat()
            self.report["job_metadata"]["status"] = "done"
            self.driver.quit()

        report_path = os.path.join(output_dir, f"report_{id}.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self.report, f, ensure_ascii=False, indent=4)

        print(f"📄 Report saved at {report_path}")
        self.logger.info(f"📄 Report saved at {report_path}")
