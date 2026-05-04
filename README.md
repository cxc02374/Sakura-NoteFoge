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

> **Windows SmartScreen の警告について**
>
> ダウンロード時またはインストール時に「一般的にダウンロードされていません」という警告が表示される場合があります。
> これはコード署名証明書を使用していないオープンソースソフトウェアで一般的に発生するものであり、安全上の問題ではありません。
>
> **回避手順（Edge の場合）:**
> 1. ダウンロードバーの「`…`」→「**保持する**」をクリック
> 2. 「詳細表示」→「**保持する**」で確定
>
> **インストーラー実行時に SmartScreen が出た場合:**
> 1. 「詳細情報」をクリック
> 2. 「**実行する**」をクリック

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
