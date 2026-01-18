import json
import os
import requests
import hmac
import hashlib
import base64
import time
import uuid
import asyncio
import websockets
import sys

# Configuration
OPTIONS_FILE = "/data/options.json"
HA_WS_URL = "ws://supervisor/core/websocket"
HA_API_BASE = "http://supervisor/core/api"
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN")

# Print helper to ensure flushing
def log(msg):
    print(msg, flush=True)

def get_switchbot_headers(token, secret):
    t = str(int(round(time.time() * 1000)))
    nonce = str(uuid.uuid4())
    string_to_sign = f"{token}{t}{nonce}"
    signature = base64.b64encode(
        hmac.new(
            secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256
        ).digest()
    ).decode("utf-8").upper()
    
    return {
        "Authorization": token,
        "sign": signature,
        "nonce": nonce,
        "t": t,
        "Content-Type": "application/json"
    }

async def ws_auth(websocket):
    await websocket.send(json.dumps({
        "type": "auth",
        "access_token": SUPERVISOR_TOKEN
    }))
    auth_response = json.loads(await websocket.recv())
    return auth_response.get("type") == "auth_ok"

async def ws_command(websocket, command, **kwargs):
    msg_id = int(time.time() * 1000) % 1000000
    payload = {
        "id": msg_id,
        "type": command,
        **kwargs
    }
    await websocket.send(json.dumps(payload))
    
    while True:
        try:
            response = json.loads(await websocket.recv())
            if response.get("id") == msg_id:
                return response
        except Exception as e:
            log(f"WS受信エラー: {e}")
            return None

async def get_ha_flows_ws():
    try:
        async with websockets.connect(HA_WS_URL) as websocket:
            await websocket.recv() # auth required
            if not await ws_auth(websocket):
                log("WS認証失敗")
                return []
            
            res = await ws_command(websocket, "config_entries/flow/progress")
            if res and res.get("success"):
                return res.get("result", [])
            else:
                return []
    except Exception as e:
        log(f"WSエラー(flows): {e}")
        return []

async def get_ha_devices_ws():
    """デバイスレジストリから全デバイスを取得"""
    try:
        async with websockets.connect(HA_WS_URL) as websocket:
            await websocket.recv()
            if not await ws_auth(websocket):
                return []
            
            res = await ws_command(websocket, "config/device_registry/list")
            if res and res.get("success"):
                return res.get("result", [])
            else:
                return []
    except Exception as e:
        log(f"WSエラー(devices): {e}")
        return []

async def update_device_name_ws(device_id, new_name):
    """デバイス名を更新"""
    try:
        async with websockets.connect(HA_WS_URL) as websocket:
            await websocket.recv()
            if not await ws_auth(websocket):
                return False
            
            res = await ws_command(websocket, "config/device_registry/update", 
                                   device_id=device_id, 
                                   name_by_user=new_name)
            return res and res.get("success")
    except Exception as e:
        log(f"WSエラー(update): {e}")
        return False

def register_flow_rest(flow_id):
    url = f"{HA_API_BASE}/config/config_entries/flow/{flow_id}"
    headers = {
        "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        return requests.post(url, headers=headers, json={}, timeout=20)
    except:
        return None

async def main_async():
    log("==================================================")
    log("SwitchBot Sync v1.1.7 (Restored Backup)")
    log("==================================================")
    
    if not SUPERVISOR_TOKEN:
        log("エラー: SUPERVISOR_TOKENなし")
        return

    # 1. Config
    try:
        with open(OPTIONS_FILE, "r") as f:
            opts = json.load(f)
        sb_token = opts.get("switchbot_token")
        sb_secret = opts.get("switchbot_secret")
        if not sb_token or not sb_secret:
            log("エラー: SwitchBotトークン設定なし")
            return
    except Exception as e:
        log(f"エラー: オプションファイル読み込み失敗: {e}")
        return

    # 2. Get SwitchBot Devices
    log("1. SwitchBotクラウド情報取得...")
    mac_to_name = {}
    try:
        headers = get_switchbot_headers(sb_token, sb_secret)
        res = requests.get("https://api.switch-bot.com/v1.1/devices", headers=headers, timeout=20)
        res.raise_for_status()
        sb_data = res.json()
        for d in sb_data.get("body", {}).get("deviceList", []):
            mac = d["deviceId"].replace(":", "").lower()
            mac_to_name[mac] = d["deviceName"]
        for d in sb_data.get("body", {}).get("remoteInfraredCommands", []):
            mac = d["deviceId"].replace(":", "").lower()
            mac_to_name[mac] = d["deviceName"]
        log(f"取得: {len(mac_to_name)} デバイス")
    except Exception as e:
        log(f"SwitchBot APIエラー: {e}")
        return

    # 3. Rename Existing Devices
    log("2. 既存デバイスの名前同期をチェック...")
    ha_devices = await get_ha_devices_ws()
    log(f"HAデバイス総数: {len(ha_devices)}")
    synced_count = 0
    
    # デバッグ: 全デバイスの識別情報を確認
    log("--- DEBUG: 全デバイスの識別子 ---")
    
    for device in ha_devices:
        target_mac = None
        identifiers = device.get("identifiers", [])
        connections = device.get("connections", [])
        
        # 1. identifiers から探す
        for id_tuple in identifiers:
            for item in id_tuple:
                if isinstance(item, str):
                    clean = item.replace(":", "").lower()
                    if len(clean) == 12 and clean in mac_to_name:
                        target_mac = clean
                        break
            if target_mac: break
            
        # 2. connections から探す (MACアドレスはここにあることが多い)
        if not target_mac:
            for conn_tuple in connections:
                for item in conn_tuple:
                    if isinstance(item, str):
                        clean = item.replace(":", "").lower()
                        if len(clean) == 12 and clean in mac_to_name:
                            target_mac = clean
                            break
                if target_mac: break
        
        # デバッグログ出力
        dev_name = device.get("name_by_user") or device.get("name")
        if target_mac:
            log(f"🔍 発見: {dev_name} -> MAC:{target_mac} (クラウド名:{mac_to_name[target_mac]})")
            
            cloud_name = mac_to_name[target_mac]
            if dev_name != cloud_name:
                log(f"  ⚡ 更新実行: {dev_name} -> {cloud_name}")
                success = await update_device_name_ws(device["id"], cloud_name)
                if success:
                    log(f"    ✅ 成功")
                    synced_count += 1
                else:
                    log(f"    ❌ 失敗")
            else:
                log(f"  ✅ 名前一致済み")
                
    log("---------------------------------------")
    log(f"完了: {synced_count} 台の名前を同期しました。")

    # 4. Register New Flows
    log("3. 新規デバイスの自動登録...")
    flows = await get_ha_flows_ws()
    registered_count = 0
    
    # ハンドラー名（デバッグ用）
    if flows:
        handlers = list(set([str(f.get("handler")) for f in flows]))
        log(f"検出されたハンドラー: {handlers}")

    for flow in flows:
        handler = flow.get("handler")
        # 広めにマッチさせる
        if "switchbot" not in str(handler).lower() and "bluetooth" not in str(handler).lower():
            continue

        context = flow.get("context", {})
        unique_id = context.get("unique_id", "").replace(":", "").lower()
        flow_id = flow["flow_id"]
        
        if unique_id in mac_to_name:
            cloud_name = mac_to_name[unique_id]
            log(f"新規登録: {unique_id} -> {cloud_name}")
            
            res = register_flow_rest(flow_id)
            if res and res.status_code == 200:
                result = res.json()
                entry_id = result.get("result", {}).get("entry_id")
                
                if result.get("type") == "create_entry" and entry_id:
                    log(f"  ✅ 登録成功。名前を即時適用します...")
                    await asyncio.sleep(2) 
                    
                    # 再取得して更新
                    updated_devices = await get_ha_devices_ws()
                    target_device_id = None
                    for dev in updated_devices:
                        if entry_id in dev.get("config_entries", []):
                            target_device_id = dev["id"]
                            break
                    
                    if target_device_id:
                        if await update_device_name_ws(target_device_id, cloud_name):
                            log("  ✅ 名前適用完了")
                        else:
                            log("  ⚠️ 名前適用失敗")
                    else:
                        log("  ⚠️ デバイス探索失敗")
                    registered_count += 1
                else:
                    log(f"  情報: ステップ {result.get('step_id')}")
            else:
                code = res.status_code if res else "None"
                log(f"  ❌ 登録リクエスト失敗 ({code})")
    
    log("==================================================")
    log(f"全工程完了")
    log("==================================================")

def main():
    # 強制flush
    sys.stdout.reconfigure(line_buffering=True)
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
