# SwitchBot Bulk Register & Name Sync for Home Assistant

SwitchBotクラウドに登録されているデバイス情報を取得し、Home Assistant上のデバイス名と同期させたり、新規デバイスを自動登録するためのHome Assistantアドオンです。
特に、Home AssistantにBluetooth統合などで検出されたSwitchBotデバイスの「名前」を、SwitchBotアプリ側で設定した名前と一括で合わせたい場合に便利です。

## 機能
- **名称同期**: HA上に既に存在するSwitchBotデバイスの名前を、SwitchBotクラウド（アプリ）上の名前にリネームします。
- **一括登録**: 未登録のSwitchBot関連のデバイス（統合内の発見）が見つかった場合、自動的に登録処理を行い、名前を同期します。

## 前提条件
このアドオンを使用するには、以下の情報が必要です：
1. **SwitchBot アプリのトークン**
2. **SwitchBot アプリのクライアントシークレット**

### トークンとシークレットの取得方法
1. SwitchBotアプリをスマホで開きます。
2. プロフィール > 設定 > アプリバージョン を10回タップします。
3. 「開発者向けオプション」が表示されるので、そこからトークンとクライアントシークレットをコピーしてください。

> [!WARNING]
> **セキュリティ警告**: 取得したトークンとシークレットは、絶対に他人に教えたり、公開の場（Gitなど）に貼り付けないでください。このアドオンの設定画面以外に入力しないでください。

## インストール方法

### GitHubリポジトリからインストールする場合
1. Home Assistantの **設定** > **アドオン** > **アドオンストア** を開きます。
2. 右上のメニュー（縦の三点リーダー）から **リポジトリ** を選択します。
3. 以下のURLを入力して「追加」をクリックします：
   `https://github.com/666mk3/SwitchBot-Bulk-Register-Name-Sync-for-Home-Assistant`
4. ストアの画面を更新（再読み込み）し、リストに表示される「SwitchBot Bulk Register & Name Sync」を選択してインストールします。

### ローカルアドオンとしてインストールする場合
1. Home Assistantの `addons/` フォルダ（または `local_addons/`）に、このリポジトリのファイル一式を配置したフォルダ（例: `switchbot_bulk_register`）をコピーします。
2. Home Assistantの設定 > アドオン > アドオンストア から、右上のメニューで「更新を確認」をクリックします。
3. 「Local Add-ons」セクションに「SwitchBot Bulk Register & Name Sync」が表示されるのでインストールします。

### 設定
アドオンの「設定」タブで以下を入力してください：

<img width="1313" height="514" alt="image" src="https://github.com/user-attachments/assets/6bc106a3-4e23-4fca-8697-97a5800f211b" />


`switchbot_token`  SwitchBotアプリから取得したトークン 

`switchbot_secret` SwitchBotアプリから取得したシークレット 

## 使い方
1. 設定を保存したらアドオンを起動します。
2. 「ログ」タブを確認してください。
3. 接続に成功すると、デバイスの取得、名前の比較、更新処理が自動的に行われます。
4. 処理が完了すると、自動的に終了します（常駐はしません）。デバイスを追加・変更した際に都度実行してください。

## ライセンス
MIT License
