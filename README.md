# HKSI 試卷一模擬考試

練習與模擬考試工具，題目來自 2CEXAM 練習題 PDF，考試規格參考 HKSI 溫習手冊試卷一。

## 功能

1. **溫習手冊** — `/manual`，按章／小節閱讀（目前 v2.8，更新至 2016年8月）
2. **按章節練習** — 瀏覽題庫，即時顯示答案
3. **模擬考試** — 60 題／90 分鐘／合格 70%

### 溫習手冊版本資料
- 路徑：`public/data/manual/`
- 目前版本：`v2.8-2016-08`（第二版 2.8，更新至 2016-08）
- 換新版：執行 `npm run extract:manual`（或新增 version 資料夾後改 `index.json` 的 `currentVersion`）

## 兩種練習模式（題庫）

1. **按章節練習** — 瀏覽全部題目，按章節分類，可即時顯示答案與解釋。
2. **模擬考試** — 60 題／90 分鐘／合格 70%；按常見章節比重抽題，交卷後才顯示成績與解釋。

## 開發

```bash
npm install
npm run dev
```

重新由 PDF 擷取題庫（需 macOS Vision OCR 工具 `.tmp/vision_ocr_box`）：

```bash
npm run extract
```

## 資料說明

- 主題庫來自文字版 past paper：`871245770-HKSI-Paper-1-Pastpaper.pdf`（421 題，第 1–9 章）。
- 舊掃描練習冊 OCR 題庫因大量辨識錯誤已備份為 `public/data/questions_scanned_backup.json`，不再作為主資料。


- 溫習手冊訂明：60 條多項選擇題、90 分鐘、合格分數 70%。
- 各章題數分配採常見試卷一比重估算（手冊未列明精確每章題數）。
- 題目由掃描 PDF OCR 匯入；部分羅馬數字選項可能有辨識誤差。
