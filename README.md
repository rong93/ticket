# tixCraft 拓元搶票選區票數監控與自動跳轉工具

本專案是一個基於 Python 與 Selenium (undetected-chromedriver) 開發的 **tixCraft 拓元售票系統** 選區剩餘票數監控工具。當發現目標選區有剩餘票券時，程式會發出蜂鳴聲並自動跳轉至該選區的張數填寫與驗證碼輸入頁面，協助您第一時間進入購票程序。

為了防止瀏覽器的自動化防爬蟲機制阻擋，本工具採用了 `undetected-chromedriver`，並支援在 **本機環境** 與 **Docker 容器化環境**（透過 X11 轉發圖形界面）中執行。

---

## 🌟 核心功能

- **防自動化偵測**：使用 `undetected-chromedriver` 模擬真實瀏覽器操作，避免被拓元系統判定為機器人。
- **Cookie/Session 保持**：自動建立並載入 `./chrome_profile` 使用者設定檔，登入後即可儲存登入狀態，下次啟動時免重複登入。
- **自動狀態判定與登入引導**：
  - 開啟網頁後自動偵測是否已登入。
  - 若未登入，會優先嘗試透過頁面上的 Google / Facebook 登入按鈕自動點選。
  - 若需手動完成驗證，程式會暫停並等待使用者完成登入後，自動返回目標頁面繼續監控。
- **選區票數解析與篩選**：
  - 自動解析所有選區的區域名稱、販售狀態（如熱賣中、剩餘張數、已售完）。
  - 自動過濾並排除身障席、輪椅席等非一般座位區。
- **智慧優先權排序**：
  - 當多個選區同時有票時，會依優先度排序（例如：優先選擇剩餘 2 張票的選區，其次是熱賣中、未知剩餘數量，最後是 1 張票的選區）。
- **即時通知與自動跳轉**：
  - 發現有票的選區時，終端機會發出 5 次嗶聲警示音。
  - 自動跳轉至購票填寫介面，並保持瀏覽器視窗開啟，讓您立即進行後續的手動輸入驗證碼與結帳。
- **精準定時/對時重新整理**：
  - 支援「固定時間間隔」重新整理模式。
  - 支援「對時（Clock Alignment）模式」：可精準對齊時鐘的倍數時間進行重新整理（例如每 10 秒的 00s, 10s, 20s...），並可設定微調偏差（Offset），避免提早或錯過搶票時間。

---

## 🛠️ 環境需求

### 方案 A：使用 Docker 執行（推薦，免安裝 Python 依賴套件）
- **作業系統**：Linux（支援 X11 顯示服務，如 Ubuntu）
- **必備軟體**：
  - [Docker](https://docs.docker.com/get-docker/)
  - [Docker Compose](https://docs.docker.com/compose/install/)

### 方案 B：直接於本機執行
- **作業系統**：Windows / macOS / Linux
- **必備軟體**：
  - Python 3.10+
  - Google Chrome 瀏覽器

---

## 🚀 快速開始

### 方案 A：使用 Docker 執行（推薦）

專案中已設定好 Docker Compose 與 X11 圖形界面授權腳本，可在容器中順暢啟動有圖形界面的 Chrome 瀏覽器。

1. **賦予啟動腳本執行權限**：
   ```bash
   chmod +x run_docker.sh
   ```

2. **執行啟動腳本**：
   ```bash
   ./run_docker.sh
   ```
   *此腳本會自動授權 Docker 容器存取您主機的 X11 顯示服務，並透過 `docker compose up --build` 啟動容器，結束時會自動撤銷授權以策安全。*

---

### 方案 B：直接於本機執行

1. **啟用虛擬環境 (Virtual Environment)**：
   本專案目錄已包含虛擬環境資料夾 `venv`，請依您的作業系統與終端機執行對應指令啟用：

   - **PowerShell (Windows 預設)**：
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
     *(若遇到執行原則錯誤，請先執行 `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process`)*

   - **Command Prompt (cmd.exe)**：
     ```cmd
     venv\Scripts\activate.bat
     ```

   - **Git Bash / macOS / Linux (Bash)**：
     ```bash
     source venv/Scripts/activate
     ```

2. **安裝 Python 依賴套件**：
   啟用虛擬環境後，安裝所需套件：
   ```bash
   pip install selenium undetected-chromedriver beautifulsoup4
   ```

3. **修改 `automate.py` 中的目標網址**：
   編輯 [automate.py](file:///c:/Users/2512485/project/ticket/automate.py) 的 `target_url` 為您要搶票的選區網址：
   ```python
   target_url = "https://tixcraft.com/ticket/area/26_btskns/22510"
   ```

4. **執行監控腳本**：
   ```bash
   python automate.py
   ```

---

## ⚙️ 參數設定

您可以透過環境變數（在 `docker-compose.yml` 中或本機終端機）調整監控行為：

| 環境變數 | 說明 | 預設值 |
|---|---|---|
| `REFRESH_INTERVAL` | 瀏覽器重新整理的時間間隔（秒）。 | `10.0` |
| `SYNC_MODE` | 重新整理模式，可設定為 `clock`（定時對齊時鐘）或 `fixed`（固定等待間隔）。 | `clock` |
| `SYNC_OFFSET` | `clock` 模式下的偏差微調（秒）。例如 `-0.5` 代表提早半秒重新整理。 | `0.0` |

---

## ⚠️ 注意事項

1. **登入狀態保存**：
   登入資訊與 Session Cookies 會儲存在專案目錄下的 `chrome_profile/` 資料夾中（該目錄已加入 `.gitignore`）。請勿隨意刪除此資料夾，否則下次啟動時需要重新登入。
2. **多重瀏覽器衝突**：
   若啟動時遇到 Chrome 衝突錯誤，請確認沒有其他正在執行且佔用同一個 `chrome_profile` 的 Chrome 實例。Docker 啟動腳本會在啟動前自動清除上次意外結束時殘留的 Chrome 鎖定檔（如 `SingletonLock`）。
3. **安全提醒**：
   本工具僅用於選區狀態的監控與自動跳轉，**不包含** 自動辨識驗證碼（CAPTCHA）與自動結帳功能，確保符合合理使用規範，避免因全自動搶票導致帳號遭受官方封鎖。
