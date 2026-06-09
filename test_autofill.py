import os
import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

def get_chrome_major_version():
    import platform
    if platform.system() != "Windows":
        return None
    try:
        import winreg
        import subprocess
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe")
        path, _ = winreg.QueryValueEx(key, "")
        winreg.CloseKey(key)
        if path:
            cmd = ["powershell", "-Command", f"(Get-Item '{path}').VersionInfo.ProductVersion"]
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode('utf-8', errors='ignore').strip()
            match = re.match(r"^(\d+)\.", output)
            if match:
                return int(match.group(1))
    except Exception:
        pass
    return None

def autofill_ticket_page(driver):
    try:
        print("\n" + "=" * 50)
        print("[自動化] 偵測到進入填寫資料頁面，開始自動輸入欄位...")
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "quantity-select"))
            )
        except Exception:
            print("[警告] 找不到張數選擇下拉選單。")
            return
            
        try:
            quantity_select_el = driver.find_element(By.CLASS_NAME, "quantity-select")
            quantity_select = Select(quantity_select_el)
            options = [opt.get_attribute("value") for opt in quantity_select.options]
            if "2" in options:
                quantity_select.select_by_value("2")
                print("[自動化] 已自動選擇張數：2 張")
            elif "1" in options:
                quantity_select.select_by_value("1")
                print("[自動化] 已自動選擇張數：1 張")
        except Exception as e:
            print(f"[警告] 自動選擇張數失敗: {e}")
            
        try:
            checkbox = driver.find_element(By.ID, "terms-checkbox")
            if not checkbox.is_selected():
                driver.execute_script("arguments[0].click();", checkbox)
                print("[自動化] 已自動勾選同意服務條款")
        except Exception as e:
            print(f"[警告] 自動勾選服務條款失敗: {e}")
            
        try:
            captcha_image = driver.find_element(By.ID, "captcha-image")
            time.sleep(0.5) # 給予驗證碼載入充裕的時間
            captcha_answer = captcha_image.get_attribute("data-answer")
            
            if captcha_answer:
                print(f"[自動化] 偵測到模擬網頁驗證碼答案: {captcha_answer}")
                captcha_input = driver.find_element(By.ID, "captcha-input")
                captcha_input.clear()
                captcha_input.send_keys(captcha_answer)
                print("[自動化] 已自動填入驗證碼")
                
                # 暫時不自動送出，供使用者確認資料
                # try:
                #     confirm_button = driver.find_element(By.CSS_SELECTOR, "button.confirm-btn")
                #     confirm_button.click()
                #     print("[自動化] 模擬網站表單已自動點擊確認送出！")
                # except Exception:
                #     pass
            else:
                print("[資訊] 此網頁非模擬練習網頁，請手動輸入驗證碼。")
        except Exception as e:
            print(f"[資訊] 驗證碼處理跳過或失敗: {e}")
        print("=" * 50 + "\n")
    except Exception as e:
        print(f"[錯誤] 自動填寫過程發生異常: {e}")

def test_run():
    profile_dir = os.path.abspath("./chrome_profile")
    options = uc.ChromeOptions()
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')
    options.add_argument('--disable-sync')
    
    chrome_version = get_chrome_major_version()
    if chrome_version:
        print(f"[資訊] 偵測到 Chrome 主要版本: {chrome_version}")
        driver = uc.Chrome(user_data_dir=profile_dir, options=options, version_main=chrome_version)
    else:
        driver = uc.Chrome(user_data_dir=profile_dir, options=options)
        
    try:
        url = "https://ticket-training.onrender.com/checking?seat=A1%E5%8D%80&price=9380&color=%23E72718"
        print(f"前往測試網址: {url}")
        driver.get(url)
        
        autofill_ticket_page(driver)
        
        print("測試完成，瀏覽器將保持開啟以供您檢查結果...")
        # 保持開啟 60 秒供確認
        for i in range(60):
            time.sleep(1)
    except Exception as e:
        print("發生錯誤:", e)
    finally:
        driver.quit()

if __name__ == '__main__':
    test_run()
