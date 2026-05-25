# Phone Trackpad

Phone Trackpad は、同じローカルネットワーク上の iPhone ブラウザを
Windows PC のトラックパッドおよび文字入力リモコンとして利用するアプリです。
PC 側プロセスがモバイル向け UI と WebSocket 接続を同一ポートで提供します。

## 機能

- 1 本指のドラッグによるマウス移動と、タップによる左クリック
- 2 本指のドラッグによるスクロールと、2 本指タップによる右クリック
- 左クリック・右クリックの専用ボタン
- Windows クリップボードへの貼り付けを利用した、日本語を含む文字入力
- ランダム PIN 認証、1 時間有効なセッショントークン、接続元 IP 単位の PIN
  連続失敗時ロック
- 起動時 QR コード表示と、切断時の自動再接続
- 既定で RFC1918 の LAN 接続のみ受付

## 必要環境

- Windows 10 以降、Python 3.9 以降
- 同じ信頼できる Wi-Fi ネットワークに接続した Windows PC と iPhone
- `pyautogui` で入力操作が可能な Windows のデスクトップセッション

## インストール

このソースディレクトリで以下を実行します。

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e .
```

`websockets` 14.0 以降が必要です。上記のコマンドでインストールされます。

Windows 環境によっては `pyautogui` が `pygetwindow` などの Windows 向け
補助依存を必要とします。通常は `pip` によるインストール時に解決されます。

## 起動方法

```powershell
phone-trackpad
# または:
python -m phone_trackpad --port 8765 --sensitivity 2.0
```

画像ビューアーで QR コードを開かない場合は `--no-qr` を指定します。
起動時にターミナルへ検出された LAN URL と 4 桁の PIN が表示されます。
iPhone で QR コードを読み取るか、いずれかの URL を開き、表示された PIN
を入力してください。

## Windows Firewall

管理者として PowerShell を起動し、Private ネットワークプロファイルの
ローカルサブネットからの TCP 接続だけを許可します。別の `--port` を
指定する場合はポート番号を変更してください。

```powershell
New-NetFirewallRule -DisplayName "Phone Trackpad (Private LAN)" `
  -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8765 `
  -Profile Private -RemoteAddress LocalSubnet
```

後からこの規則を削除する場合:

```powershell
Remove-NetFirewallRule -DisplayName "Phone Trackpad (Private LAN)"
```

## 画面説明

初期画面には PIN 入力欄と Connect ボタンがあります。認証後は、上部の
接続状態ランプと Keyboard ボタン、中央の大きなトラックパッド領域、
下部の Left Click / Right Click ボタンが表示されます。Keyboard を押すと
文字入力欄と Send ボタンが開きます。

## 操作

| ジェスチャーまたは操作 | 結果 |
| --- | --- |
| パッドを 1 本指でドラッグ | マウスポインター移動 |
| パッドを 1 本指でタップ | 左クリック |
| パッドを 2 本指でドラッグ | スクロール |
| パッドを 2 本指でタップ | 右クリック |
| Keyboard の入力欄から Send | PC のフォーカス位置へ文字を貼り付け |

## セキュリティ上の注意

- 信頼できるプライベート LAN 内でのみ利用してください。HTTP/WebSocket は
  TLS で暗号化されていないため、PIN と操作通信は LAN 上で暗号化されません。
- HTTP UI と WebSocket の接続元は RFC1918 のプライベート IP と
  ループバックに限定していますが、ファイアウォールの代替にはなりません。
- 同じ接続元 IP から PIN 認証に 5 回失敗すると、その IP は 60 秒間
  ロックされます。IPv4-mapped IPv6 は対応する IPv4 として扱われます。
- 認証済みセッショントークンは 3600 秒で期限切れとなり、WebSocket
  接続の終了時にも破棄されます。
- 画面端でも操作できるよう `pyautogui.FAILSAFE` を無効化しています。
  リモート操作を終了する際は PC 側ターミナルで `Ctrl+C` を押してください。
- 入力イベントごとの PyAutoGUI 標準待機時間を入れないよう、
  `pyautogui.PAUSE` を `0.0` に設定しています。
- 文字入力は iPhone で入力された内容を PC のクリップボードにコピーし、
  現在フォーカスされているアプリケーションへ貼り付けます。

## ライセンス

このプロジェクトは MIT License の下で提供されます。詳細は
[LICENSE](LICENSE) を参照してください。
