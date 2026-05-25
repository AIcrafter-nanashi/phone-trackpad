# phone_trackpad 実装計画書

## 概要
iPhoneのブラウザからWindowsのマウスをコントロールするトラックパッドアプリ。
WebSocketでリアルタイム通信し、PIN認証でセキュリティを確保する。

---

## 1. ファイル構成

```
c:\トレード\products\phone_trackpad\
├── phone_trackpad/              # メインパッケージ
│   ├── __init__.py
│   ├── server.py                # WebSocketサーバー + HTTPサーバー
│   ├── mouse_controller.py      # pyautogui操作ラッパー
│   ├── qr_generator.py          # QRコード生成・表示
│   ├── auth.py                  # PIN認証ロジック
│   ├── config.py                # 設定値（ポート・感度など）
│   └── static/
│       └── index.html           # スマホ側UI（HTML5 + Vanilla JS）
├── main.py                      # エントリーポイント（python -m phone_trackpad）
├── setup.py                     # pip install 用
├── pyproject.toml               # PEP 517 ビルド設定
├── requirements.txt             # 依存パッケージ
├── README.md                    # 英語README
├── README_ja.md                 # 日本語README
└── PLAN.md                      # 本計画書
```

---

## 2. 各ファイルの役割と主要クラス設計

### server.py
- `TrackpadServer` クラス
  - `start()`: HTTP + WebSocket サーバー同時起動
  - `handle_websocket(websocket, path)`: WebSocket接続ハンドラー
  - `serve_static(request)`: `index.html` を返すHTTPハンドラー
  - `broadcast_status(connected_count)`: 接続状態をクライアントに通知
- ポート: HTTP=8765, WebSocket=8766（同一ポートで切り替えも可）
  - `asyncio` + `websockets` で実装
  - 実際には同一ポートにHTTPとWSを共存させる（websockets v10+ の `serve` + `http_handler`）

### mouse_controller.py
- `MouseController` クラス
  - `move(dx, dy)`: 相対移動（現在位置 + dx/dy）
  - `left_click()`: 左クリック
  - `right_click()`: 右クリック
  - `scroll(dx, dy)`: スクロール（pyautogui.scroll）
  - `type_text(text)`: テキスト入力（pyautogui.typewrite）
  - 感度係数 `sensitivity` を設定から読み込む
  - `FAILSAFE = False` で画面端での強制停止を無効化

### qr_generator.py
- `generate_qr(url)`: `qrcode` ライブラリでQR生成
- `display_qr_terminal(url)`: ターミナルにASCIIアートで表示
- `display_qr_window(url)`: PIL で画像ウィンドウ表示（オプション）
- LAN IPアドレス自動検出: `socket.getsockname()` / `socket.connect` trick

### auth.py
- `AuthManager` クラス
  - `generate_pin(length=4)`: ランダム4桁PIN生成
  - `verify_pin(input_pin)`: PIN照合（タイミングアタック対策: `hmac.compare_digest`）
  - `get_pin()`: 現在のPIN取得（サーバー起動時に1回生成・表示）
  - セッショントークン: PIN認証成功後にUUID発行、以降WSメッセージにトークン添付

### config.py
- `Config` データクラス
  - `port: int = 8765`
  - `sensitivity: float = 1.5`
  - `pin_length: int = 4`
  - `lan_only: bool = True`（LAN以外の接続を拒否）
  - `scroll_speed: float = 3.0`

---

## 3. WebSocket通信プロトコル

### 接続確立フロー
```
Client → Server: {"type": "auth", "pin": "1234"}
Server → Client: {"type": "auth_result", "success": true, "token": "uuid-v4"}
Server → Client: {"type": "auth_result", "success": false, "message": "Invalid PIN"}
```

### 認証後の操作メッセージ（全て token 付き）
```json
// マウス移動
{"type": "move", "dx": 10.5, "dy": -3.2, "token": "uuid"}

// 左クリック
{"type": "left_click", "token": "uuid"}

// 右クリック
{"type": "right_click", "token": "uuid"}

// スクロール
{"type": "scroll", "dx": 0, "dy": -2.0, "token": "uuid"}

// テキスト入力
{"type": "type", "text": "hello", "token": "uuid"}

// 接続状態確認
{"type": "ping", "token": "uuid"}
Server → Client: {"type": "pong"}
```

### サーバーからクライアントへの通知
```json
// 接続状態
{"type": "status", "connected": true, "client_count": 1}

// エラー
{"type": "error", "message": "Unauthorized"}
```

---

## 4. PIN認証フロー

```
1. サーバー起動時: AuthManager.generate_pin() → ターミナルに表示
2. QRコードURL: http://{LAN_IP}:{PORT}/
3. クライアント: ブラウザでURL開く → PIN入力画面
4. クライアント: {"type": "auth", "pin": "1234"} 送信
5. サーバー: hmac.compare_digest で照合
   成功: UUID v4 トークン発行・返却
   失敗: {"success": false} + 試行回数カウント（5回失敗で60秒ロック）
6. 以降: 全メッセージに token を添付、サーバー側で毎回検証
```

---

## 5. QRコード生成フロー

```
1. socket.create_connection(("8.8.8.8", 80)) でLAN IPを自動検出
2. URL: "http://{IP}:{PORT}/"
3. qrcode.make(url) でQR生成
4. ターミナルにASCIIアートで表示（qrcode[terminal] またはカスタム）
5. 起動メッセージ: "Scan QR code or open http://IP:PORT on your iPhone"
6. PINも同時に表示: "PIN: 1234"
```

---

## 6. タッチイベント処理（index.html / Vanilla JS）

### タッチ判定ロジック
```
touchstart:
  - touches.length == 1 → シングルタッチ開始（lastX/Y記録）
  - touches.length == 2 → マルチタッチ開始（lastY記録・スクロール用）

touchmove:
  - touches.length == 1 → move イベント送信（dx/dy計算）
  - touches.length == 2 → scroll イベント送信（2点の平均Y変化量）

touchend:
  - 移動量 < 5px かつ 時間 < 250ms → タップ判定
    - touches前の指数 == 1 → left_click
    - touches前の指数 == 2 → right_click
```

### 送信レート制限
- `requestAnimationFrame` ベースの間引き（60fps上限）
- `mousemove` イベントは連続送信ではなくdx/dy累積後にrAFで一括送信

### WebSocket接続管理
- 切断時: 3秒後に自動再接続（最大5回）
- 接続状態: 画面上部にインジケーター表示（緑/赤）
- 再認証: 再接続時に保存済みPINで自動再認証試行

---

## 7. UI設計（index.html）

### 画面構成
```
┌─────────────────────────┐
│ [●] PhoneTrackpad  [⌨] │  ← ヘッダー（接続状態 + キーボードトグル）
├─────────────────────────┤
│                         │
│   タッチパッド エリア    │  ← メイン操作エリア（画面の70%）
│   (ダークグレー背景)    │
│                         │
├─────────────────────────┤
│  [L Click] [R Click]   │  ← ボタンバー（明示的クリック）
└─────────────────────────┘

キーボードモード時:
├─────────────────────────┤
│ [テキスト入力フィールド] │
│ [送信ボタン]            │
└─────────────────────────┘
```

### スタイル方針
- ダークテーマ（#1a1a2e / #16213e / #0f3460）
- iOS SafeArea 対応（env(safe-area-inset-*)）
- タッチ遅延無効（touch-action: none; user-select: none）
- Font: system-ui（インストール不要）

---

## 8. セキュリティ考慮事項

1. **LAN限定チェック**: 接続元IPが RFC1918（10.x/172.16-31.x/192.168.x）でなければ即切断
2. **PIN認証**: 4桁ランダム + タイミング安全比較 + ブルートフォース防御（5回ロック）
3. **トークン検証**: 全操作メッセージにトークン添付・毎回サーバー検証
4. **HTTPS非使用の明記**: LAN内専用のため HTTP、SSL証明書不要
5. **pyautogui FAILSAFE**: 起動時に無効化（`pyautogui.FAILSAFE = False`）するが、ユーザー向けにドキュメント明記

---

## 9. 依存パッケージ

```
websockets>=10.0
pyautogui>=0.9.54
qrcode[pil]>=7.0
Pillow>=9.0
```

オプション:
```
qrcode[terminal]  # ターミナルASCII QR用
```

---

## 10. 実装フェーズ

### Phase 1: コア機能（最小動作確認）
1. `config.py` - 設定クラス
2. `mouse_controller.py` - pyautigui ラッパー
3. `auth.py` - PIN生成・検証
4. `server.py` - WebSocket + HTTPサーバー（基本）
5. `static/index.html` - 最小限UI（接続・移動・クリック）

### Phase 2: 全機能実装
6. スクロール・右クリック・テキスト入力
7. QRコード生成・表示
8. UI改善（ダークテーマ・接続状態表示）
9. 自動再接続ロジック

### Phase 3: パッケージング
10. `setup.py` / `pyproject.toml`
11. `main.py` エントリーポイント（`__main__.py`）
12. `requirements.txt`
13. README.md / README_ja.md

### Phase 4: 品質向上
14. エラーハンドリング強化
15. ログ出力
16. 動作テスト

---

## 11. 起動コマンド（完成後）

```bash
pip install phone-trackpad
phone-trackpad          # デフォルト起動
phone-trackpad --port 8765 --sensitivity 2.0
```

または:
```bash
python -m phone_trackpad
```
