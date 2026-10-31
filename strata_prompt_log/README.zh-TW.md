# Strata 直接記錄收到的 API prompt

Strata 已內建 `/api-monitor`。若只需查看最近 100 筆，不必改程式碼：在 `C:\Strata-main.2\strata-nvfp4-nvfp4.json` 加入 `"api_monitor": true`，重啟 Strata，然後在 Windows 開啟 `http://127.0.0.1:8081/api-monitor`。內容只保存在記憶體，重啟後消失。

此套件適用於先前版本及 2026-10-31 的 Strata `main`（0.2.8，提交 `870aedd9`）。它讓 Strata 把收到的 API JSON 請求逐筆存到硬碟；預設不啟用，執行安裝程式後才啟用。只記錄通過 API key 驗證的 `/v1/chat/completions`、`/v1/messages` 和 `/v1/responses`。記錄包含完整請求 JSON，例如 `messages`、`system`、`input`、工具設定；不記錄 HTTP 標頭，因此不會把 Bearer API key 寫入檔案。它記的是 Strata 收到並解析的 API 請求，不是聊天模板展開後送入模型的內部文字。

## 安裝

1. 把 ZIP 解壓縮到 `C:\Strata-main.2`，確認出現 `C:\Strata-main.2\strata_prompt_log\INSTALL.py`。停止目前運行的 Strata；不要刪除模型或重新 setup。
2. 在 Windows PowerShell 執行：

       & 'C:\Python313\python.exe' 'C:\Strata-main.2\strata_prompt_log\INSTALL.py'

3. 重新啟動 Strata，照常從 WSL 的 OpenClaw／Hermes 發問。它們的 API 位址仍是 `http://172.22.160.1:8081/v1`，不用改成代理。
4. 在 Windows PowerShell 查看最新一筆記錄：

       Get-Content 'C:\Strata-main.2\strata-api-requests.jsonl' -Tail 1

日誌是一行一筆的 JSONL，欄位為 `time`、`path`、`request`。檔案可能含私人對話、工具參數和大型圖片資料，也會持續增長；請只在排查期間啟用，不要分享日誌。Windows 的檔案讀取權限取決於資料夾的 ACL，請把此檔保留在私人資料夾。

安裝程式會先備份 `serve\server.py` 和模型 JSON 設定檔，並檢查程式碼位置。如果你的 Strata 版本和本套件對應的程式碼不同，它會停止，不會覆蓋整個 `server.py`。若以前安裝過本套件，重新安裝不會覆寫舊備份；當新版 Strata 的檔案與舊備份不同時，會建立帶有雜湊值的新備份，例如 `server.py.prompt-log-original.123456789abc.bak`。原始備份不要刪除。

## 停止記錄

停止 Strata，在 Windows PowerShell 執行，然後重新啟動：

    & 'C:\Python313\python.exe' 'C:\Strata-main.2\strata_prompt_log\INSTALL.py' --disable

這會從模型設定檔移除 `api_request_log`。程式碼仍保留，但預設不寫日誌。若要刪除舊記錄，先確認不再需要，再刪除 `C:\Strata-main.2\strata-api-requests.jsonl`。

## 完整還原原本的 Strata 程式碼

先停止 Strata，再執行：

    & 'C:\Python313\python.exe' 'C:\Strata-main.2\strata_prompt_log\RESTORE.py'

還原程式會比對目前 `server.py` 與所有備份，只使用能**確切重建目前補丁版本**的備份；所以先前版本的舊備份不會覆蓋你更新後的 Strata。它也會移除設定檔的 `api_request_log`；若設定檔其餘內容未改，會還原原始檔案；若安裝後你改過其他設定，則只移除這個記錄選項並保留其他修改。還原前會再備份目前檔案。若程式碼在安裝後又被手動修改，還原工具會停止，不會猜測要覆蓋哪份程式。完成後重新啟動 Strata。已有的 `strata-api-requests.jsonl` 日誌不會自動刪除。

安裝與還原程式會自動使用 `strata_prompt_log` 所在目錄的上一層作為 Strata 根目錄；若日後把工具放在別處，也可加上 `--root 'C:\Strata-main.2'` 明確指定。這些操作不會搬動模型資料目錄。
