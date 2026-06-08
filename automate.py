import os
import time
import re
from bs4 import BeautifulSoup

try:
    import selenium
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    print("=" * 60)
    print("錯誤：缺少必要的 Python 套件！")
    print("請先手動執行以下命令進行安裝：")
    print("  pip3 install selenium undetected-chromedriver beautifulsoup4")
    print("=" * 60)
    exit(1)

def check_login(driver):
    """
    透過檢查頁面原始碼中是否含有登出等連結，判斷使用者是否已成功登入。
    """
    try:
        page_source = driver.page_source.lower()
        # 檢查中英日等多種常見的登出關鍵字，避免因語系不同而誤判
        # 注意：已移除 "member"、"my tickets" 等可能在登出狀態下也會出現在選單中的字眼
        keywords = ["/logout", "logout", "sign out", "signout", "登出", "ログアウト"]
        for kw in keywords:
            if kw in page_source:
                return True
    except Exception:
        pass
    return False

def parse_tickets(html_content):
    """
    解析選區頁面的 HTML 結構，獲取每個區域的名稱、狀態與剩餘票數。
    支援解析可購買區域（含有超連結 <a>）與已售完區域（僅為純文字 <li>）。
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 尋找所有選區列表 (ul.area-list)
    area_lists = soup.select('ul.area-list')
    
    results = []
    
    for al in area_lists:
        li_items = al.find_all('li')
        for li in li_items:
            # 取得該項目內的所有文字
            full_text = li.get_text(separator=' ', strip=True)
            
            # 判斷是否含有超連結 (代表有票或剩餘票數較少，可進行點選)
            a_tag = li.find('a')
            href = None
            
            if a_tag:
                href = a_tag.get('href', '')
                link_text = a_tag.get_text(separator=' ', strip=True)
                status_span = a_tag.find('span', class_=re.compile(r'label'))
                
                status_text = "未知"
                if status_span:
                    status_text = status_span.text.strip()
                    area_name = link_text.replace(status_text, '').strip()
                else:
                    area_name = link_text
                    if "熱賣中" in link_text:
                        status_text = "熱賣中"
                        area_name = link_text.replace("熱賣中", "").strip()
                    elif "剩餘" in link_text:
                        match = re.search(r'剩餘\s*\d+', link_text)
                        if match:
                            status_text = match.group(0)
                            area_name = link_text.replace(status_text, "").strip()
                
                # 解析剩餘票數
                if "熱賣中" in status_text:
                    remaining = "有票 (熱賣中)"
                elif "剩餘" in status_text:
                    digits = re.findall(r'\d+', status_text)
                    remaining = int(digits[0]) if digits else "有票 (剩餘少量)"
                else:
                    remaining = "有票 (未知數量)"
            else:
                # 沒有超連結，通常代表已售完 (呈現灰色純文字)
                status_text = "已售完"
                remaining = 0
                area_name = full_text
                
                if "Sold out" in full_text:
                    status_text = "已售完 (Sold out)"
                    area_name = full_text.replace("Sold out", "").strip()
                elif "已售完" in full_text:
                    status_text = "已售完"
                    area_name = full_text.replace("已售完", "").strip()
            
            # 清理區域名稱中的多餘空格與符號
            area_name = re.sub(r'\s+', ' ', area_name).strip()
            
            # 排除非區域的雜訊項目
            if not area_name or area_name.lower() == "sold out":
                continue
                
            results.append({
                'area': area_name,
                'status': status_text,
                'remaining': remaining,
                'href': href
            })
            
    # 備用方案：若沒有找到任何區域，嘗試直接比對含有特定購票連結的 <a>
    if not results:
        area_links = soup.find_all('a', href=re.compile(r'/ticket/ticket/'))
        for link in area_links:
            full_text = link.get_text(separator=' ', strip=True)
            results.append({
                'area': full_text,
                'status': "有票",
                'remaining': "未知",
                'href': link.get('href', '')
            })
            
    return results

def main():
    # 使用者指定的目標網址
    target_url = "https://tixcraft.com/ticket/area/26_btskns/22510"
    login_url = "https://tixcraft.com/user/login"
    
    # 讀取重新整理與對時的相關設定
    try:
        refresh_interval = float(os.environ.get("REFRESH_INTERVAL", "10.0"))
    except ValueError:
        refresh_interval = 10.0

    sync_mode = os.environ.get("SYNC_MODE", "clock").lower()
    
    try:
        sync_offset = float(os.environ.get("SYNC_OFFSET", "0.0"))
    except ValueError:
        sync_offset = 0.0
    
    print("=" * 60)
    print("        tixCraft 拓元選區剩餘票數監控程式")
    print("=" * 60)
    print("正在啟動 Chrome 瀏覽器 (已套用防自動化偵測機制)...")
    
    # 設定 Chrome 使用者設定檔目錄以保存登入 Cookie 與 Session
    profile_dir = os.path.abspath("/app/chrome_profile" if os.environ.get("IN_DOCKER") == "true" else "./chrome_profile")
    print(f"[資訊] 使用 Chrome 設定檔路徑: {profile_dir}")
    
    # 清除上次 Docker 意外結束（例如 Ctrl+C 終止）時殘留的 Chrome 鎖定檔
    # 若不清除，Chrome 再次開啟時會被鎖定，導致無法載入已存檔的 Profile/Cookie 登入狀態
    if os.path.exists(profile_dir):
        lock_files = ["SingletonLock", "SingletonSocket", "SingletonCookie", "lock"]
        for lock_name in lock_files:
            lock_path = os.path.join(profile_dir, lock_name)
            if os.path.exists(lock_path) or os.path.islink(lock_path):
                try:
                    os.unlink(lock_path)
                    print(f"[資訊] 已自動清理 Chrome 鎖定檔案: {lock_name}")
                except Exception as e:
                    print(f"[警告] 無法清除鎖定檔案 {lock_name}: {e}")
                    
    options = uc.ChromeOptions()
    
    # 支援 Docker 環境所需的參數
    if os.environ.get("IN_DOCKER") == "true":
        print("[資訊] 偵測到 Docker 環境，啟用 --no-sandbox 與 --disable-dev-shm-usage")
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-software-rasterizer')
        # 額外輕量化參數，降低記憶體消耗以防止 WSL 崩潰
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-default-apps')
        options.add_argument('--no-default-browser-check')
        options.add_argument('--no-first-run')
        options.add_argument('--disable-background-networking')
        options.add_argument('--disable-sync')
        options.add_argument('--disable-translate')
        options.add_argument('--mute-audio')
    
    try:
        driver = uc.Chrome(user_data_dir=profile_dir, options=options)
    except Exception as e:
        print(f"\n[錯誤] 無法啟動 Chrome：{e}")
        print("原因可能為：")
        print("1. 您的電腦未安裝 Google Chrome 瀏覽器。")
        print("2. Chrome 瀏覽器目前有其他視窗正在執行，導致驅動衝突。")
        print("3. `chromedriver` 正在執行中，請嘗試關閉它後再重新執行本程式。")
        return
        
    try:
        print(f"\n步驟 1: 嘗試直接前往目標選區網頁...")
        print(f"目標網址: {target_url}")
        driver.get(target_url)
        
        # 等待網頁載入並判斷登入狀態
        print("[資訊] 正在判定登入狀態，請稍候...")
        try:
            WebDriverWait(driver, 10).until(
                lambda d: check_login(d) or d.find_elements(By.XPATH, "//a[contains(@href, 'login') or contains(text(), '登入') or contains(text(), 'Sign In') or contains(text(), 'sign in')]")
            )
        except Exception:
            pass
        
        # 檢查是否處於未登入狀態
        if not check_login(driver):
            print("[資訊] 偵測到未登入狀態，正在嘗試點選頁面上的登入按鈕...")
            
            # 優先嘗試在當前頁面（如選區頁內嵌的登入 Modal）直接尋找並點擊 Google/FB 登入按鈕
            logged_in = False
            try:
                # 優先尋找 Google 登入按鈕
                google_btn = driver.find_element(By.XPATH, "//a[contains(@href, 'login/google') or contains(@href, 'login-google') or contains(@href, 'google')]")
                print("[資訊] 偵測到 Google 登入按鈕，正在嘗試點選...")
                driver.execute_script("arguments[0].click();", google_btn)
                time.sleep(3.5) # 等待 OAuth 認證與重導向
                if check_login(driver):
                    logged_in = True
            except Exception as e:
                print(f"[資訊] 無法直接在當前頁面點選 Google 登入按鈕 ({e})，嘗試使用 Facebook...")
                try:
                    fb_btn = driver.find_element(By.XPATH, "//a[contains(@href, 'login/facebook') or contains(@href, 'login-facebook') or contains(@href, 'facebook')]")
                    print("[資訊] 偵測到 Facebook 登入按鈕，正在嘗試點選...")
                    driver.execute_script("arguments[0].click();", fb_btn)
                    time.sleep(3.5)
                    if check_login(driver):
                        logged_in = True
                except Exception:
                    pass
            
            # 如果直接點擊失敗，或者當前頁面根本找不到登入按鈕，才跳轉到官方登入頁面
            if not logged_in and not check_login(driver):
                curr_url = driver.current_url or ""
                if "/user/login" not in curr_url:
                    print("[資訊] 前往登入頁面...")
                    driver.get(login_url)
                
                print("[資訊] 等待登入網頁載入...")
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'google') or contains(@href, 'facebook')]"))
                    )
                except Exception as e:
                    print(f"[警告] 等待登入按鈕載入超時: {e}")
                
                try:
                    google_btn = driver.find_element(By.XPATH, "//a[contains(@href, 'google')]")
                    print("[資訊] 正在嘗試自動點選 Google 登入...")
                    driver.execute_script("arguments[0].click();", google_btn)
                    time.sleep(3.5)
                except Exception:
                    try:
                        fb_btn = driver.find_element(By.XPATH, "//a[contains(@href, 'facebook')]")
                        print("[資訊] 正在嘗試自動點選 Facebook 登入...")
                        driver.execute_script("arguments[0].click();", fb_btn)
                        time.sleep(3.5)
                    except Exception:
                        pass
            
            # 若自動登入仍未完成，提示使用者手動登入
            if not check_login(driver):
                print(f"\n[除錯] 自動登入未完成，目前瀏覽器網址: {driver.current_url or ''}")
                try:
                    print(f"[除錯] 目前網頁標題: {driver.title}")
                except Exception:
                    pass
                print("【無法自動完成登入，請在瀏覽器視窗中手動輸入您的帳密並登入】")
                while not check_login(driver):
                    print("等待登入中... (完成登入後，程式會自動前往目標選區頁面)", end='\r')
                    time.sleep(1.5)
            
            print("\n[成功] 偵測到會員已成功登入！")
            
            # 確保最後回到了目標選區網頁
            curr_url = driver.current_url or ""
            if "/ticket/area/" not in curr_url:
                print(f"\n重新前往目標選區網頁...")
                driver.get(target_url)
        else:
            print("\n[成功] 偵測到已處於登入狀態，直接進入選區頁面！")
        
        if sync_mode == "clock":
            print(f"\n[開始監控] 對時模式已啟用，每 {refresh_interval} 秒對齊時鐘刷新 (微調偏差: {sync_offset} 秒)。")
        else:
            print(f"\n[開始監控] 固定間隔模式已啟用，每 {refresh_interval} 秒重新整理一次。")
        print("欲終止程式，請在終端機按下 Ctrl+C 結束監控。\n")
        
        while True:
            # 確保瀏覽器目前確實載入了該選區頁面
            current_url = driver.current_url or ""
            if "/ticket/area/" not in current_url:
                print(f"[{time.strftime('%H:%M:%S')}] 偵測到目前網址不符，正在重新導向至目標頁面...")
                driver.get(target_url)
                
            # 等待 body 載入
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except:
                pass
                
            html_content = driver.page_source
            results = parse_tickets(html_content)
            
            # 列印結果至終端機
            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 票券即時狀態:")
            print("-" * 65)
            if not results:
                print("未偵測到任何購票區域資訊。請確認頁面是否已正常載入，或該活動目前是否已售完/尚未開放。")
                try:
                    debug_file = os.path.join(profile_dir, "debug_page.html")
                    with open(debug_file, "w", encoding="utf-8") as f:
                        f.write(html_content)
                    print(f"[除錯] 已自動將網頁原始碼儲存至: {debug_file}")
                except Exception as e:
                    print(f"[警告] 無法儲存除錯網頁: {e}")
            else:
                for res in results:
                    status = res['status']
                    # 依據狀態套用終端機顏色
                    if "已售完" in status:
                        # 灰色
                        status_str = f"\033[90m{status:<10}\033[0m"
                    elif "熱賣中" in status:
                        # 綠色
                        status_str = f"\033[92m{status:<10}\033[0m"
                    else:
                        # 黃色 / 剩餘票數
                        status_str = f"\033[93m{status:<10}\033[0m"
                        
                    print(f"區域: {res['area']:<25} | 狀態: {status_str} | 剩餘票數: {res['remaining']}")
            print("-" * 65)
            
            # 篩選所有可購買且排除身障相關的區域
            valid_areas = []
            if results:
                for res in results:
                    if res.get('href'):
                        area_name = res.get('area', '')
                        # 自動排除身障席、輪椅席等非一般座位
                        if any(kw in area_name for kw in ["身障", "身心障礙", "輪椅", "wheelchair"]):
                            continue
                        valid_areas.append(res)
            
            # 優先排序偏好區域 (優先選擇剩餘 2 張票的選區)
            available_area = None
            if valid_areas:
                def get_priority_score(item):
                    rem = item.get('remaining')
                    if rem == 2:
                        return 100
                    if rem == "有票 (熱賣中)":
                        return 90
                    if isinstance(rem, int) and rem > 2:
                        return 80
                    if rem in ["有票 (未知數量)", "有票 (剩餘少量)"]:
                        return 70
                    if rem == 1:
                        return 10
                    return 50
                
                valid_areas.sort(key=get_priority_score, reverse=True)
                available_area = valid_areas[0]
            
            if available_area:
                print("\n" + "!" * 60)
                print(f" 🚨 發現有票區域：{available_area['area']} 🚨")
                print(f" 正在自動跳轉至購票頁面：{available_area['href']}")
                print("!" * 60 + "\n")
                
                # 取得絕對跳轉網址
                target_href = available_area['href']
                if not target_href.startswith("http"):
                    target_href = "https://tixcraft.com" + target_href
                
                driver.get(target_href)
                
                # 發出系統嗶聲提醒使用者
                for _ in range(5):
                    print("\a", end="", flush=True)
                    time.sleep(0.15)
                
                print("\n【已自動進入該區域購票填寫介面，請立刻手動輸入張數、驗證碼並進行結帳！】")
                print("程式已暫停監控，保留瀏覽器視窗供您操作。")
                
                # 進入無限循環，保持瀏覽器視窗開啟不關閉
                while True:
                    time.sleep(1)
            
            # 計算下一次重新整理的時間，並精準等待
            if sync_mode == "clock":
                import math
                now = time.time()
                # 依據現在時間，計算下一個對齊點 (now - sync_offset 的下一個倍數)
                target = math.ceil((now - sync_offset) / refresh_interval) * refresh_interval + sync_offset
                sleep_time = target - now
                if sleep_time < 0.1:
                    sleep_time += refresh_interval
                
                print(f"[{time.strftime('%H:%M:%S')}] 對時模式：下一次對齊刷新時間為 {time.strftime('%H:%M:%S', time.localtime(target))} (等待 {sleep_time:.2f} 秒)...")
                time.sleep(sleep_time)
            else:
                print(f"[{time.strftime('%H:%M:%S')}] 固定間隔模式：等待 {refresh_interval} 秒...")
                time.sleep(refresh_interval)
                
            driver.refresh()
            
    except KeyboardInterrupt:
        print("\n\n監控已由使用者手動中止。")
    except Exception as e:
        print(f"\n執行過程中發生錯誤：{e}")
    finally:
        print("正在關閉 Chrome 瀏覽器...")
        try:
            driver.quit()
        except:
            pass

if __name__ == '__main__':
    main()
