# Sakura NoteForge

SakuraMark から独立した Markdown 編集/プレビュー専用ツールです。

![icon](assets/noteforge_icon.png)

## 主要機能
- Markdown 編集（左ペイン）
- ライブプレビュー（右ペイン、Mermaid/コードハイライト対応）
- 見出しアウトライン表示（左ペイン、クリックでジャンプ）
- 検索 (Ctrl+F) / 置換 (Ctrl+H)
- ライト/ダークテーマ切替（`表示 > テーマ`）
- 画像ファイルのドラッグ＆ドロップで `![]()` 自動挿入
- 履歴スナップショット保存（保存時）
- 自動保存（編集中の復旧用）
- PDF 出力（`ファイル > PDFとして出力`）
- ステータスバーに現在のファイルパスを常時表示

## インストール（Windows 10/11）

### EXE インストーラー（推奨）
1. [Releases](https://github.com/cxc02374/Sakura-NoteFoge/releases) から `SakuraNoteForge_Setup_x.x.x.exe` をダウンロード
2. 実行してインストール
3. デスクトップ/スタートメニューのショートカットから起動

> **Windows Defender SmartScreen の警告が出た場合**
>
> 初回ダウンロード時に「信頼できることを確認してください」という警告が出ることがあります。
> これはコード署名証明書なしの実行ファイルに対して Microsoft が自動表示する標準警告であり、直ちに不正ファイルを意味するものではありません。
>
> **対応手順（Edge の場合）:**
> 1. ダウンロード一覧で対象ファイルの「`…`」（メニュー）をクリック
> 2. 「**保存**」を選択
> 3. SmartScreen 警告が表示されたら「削除」右の「`▼`」をクリック
> 4. 「**保持する**」を選択
> 5. ダウンロード完了後、必要に応じてファイルを右クリック →「プロパティ」→「**許可する**」にチェック
> 6. `.exe` を実行し、Windows の実行確認が出たら「**詳細情報**」→「**実行**」
>
> ※ この画面はまず「ダウンロード保持（保存）確認」です。「起動確認」ではありません。

### Python 環境で直接実行
```bash
pip install -r requirements.txt
python -m noteforge.main
```

## ビルド手順（開発者向け）

```powershell
# Windows EXE + インストーラー生成
.\scripts\build_windows_installer.ps1 -AppVersion "1.0.0"
```

必要ツール:
- Python 3.11+（SakuraMark共有 `.venv` を推奨）
- [Inno Setup 6](https://jrsoftware.org/isdl.php)（インストーラー生成時）

生成物:
- `dist/windows/SakuraNoteForge/SakuraNoteForge.exe`
- `dist/installer/SakuraNoteForge_Setup_x.x.x.exe`

## 使い方

- **保存**: `Ctrl+S`
- **PDF出力**: `ファイル > PDFとして出力`
- 画像はエディタにドラッグ＆ドロップしてください。

### 3ペインの見方
- **左（アウトライン）**: `#` 見出し **または** `1. 章タイトル` の番号付き章を一覧表示。クリックで本文へジャンプ。
- **中央（Markdown編集）**: 本文編集エリア。`md/txt` をドラッグ&ドロップするとそのファイルを開きます。
- **右（プレビュー）**: レンダリング結果。入力に合わせて自動更新されます。

### 最短操作フロー
1. `ファイル > 開く` で既存 `.md` を開く（または中央へ `.md` をD&D）
2. 中央ペインで編集する
3. 右ペインで表示を確認する
4. `Ctrl+S` で保存する

### 設計ドキュメントをすぐ始める
- `挿入 > 設計テンプレートを挿入` で、背景/要件/設計/テストの雛形を自動挿入できます。

## ディレクトリ構成
- `src/noteforge/main.py`: エントリポイント
- `src/noteforge/app.py`: メインウィンドウ実装
- `data/`: 自動保存・履歴の保存先（起動時に使用）
