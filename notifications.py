# notifications.py
import os
import requests
from datetime import datetime, timedelta


def _push_sct(sckey: str, title: str, content: str) -> bool:
    """ServerChan推送"""
    url = f"https://sctapi.ftqq.com/{sckey}.send"
    data = {'title': title, 'desp': content}
    try:
        response = requests.post(url, data=data, timeout=30)
        return response.json().get("code") == 0
    except Exception as e:
        print(f"ServerChan 推送异常: {e}")
        return False


def _push_plus(token: str, title: str, content: str) -> bool:
    """PushPlus推送"""
    url = "http://www.pushplus.plus/send"
    headers = {'Content-Type': 'application/json'}
    data = {"token": token, 'title': title, 'content': content, "template": "markdown"}
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        return response.json().get('code') == 200
    except Exception as e:
        print(f"PushPlus 推送异常: {e}")
        return False

def _push_tg(bot_token: str, chat_id: str, content: str) -> bool:
    """Telegram推送"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    headers = {'Content-Type': 'application/json'}
    payload = {
        'chat_id': chat_id,
        'text': content,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            return True
        else:
            print(f"Telegram 推送失败: {response.text}")
            return False
    except Exception as e:
        print(f"Telegram 推送异常: {e}")
        return False

def send_notification(title: str, content: str):
    """
    根据环境变量配置自动选择并发送通知。
    """
    # 添加时间戳
    now_bj = datetime.utcnow() + timedelta(hours=8)
    timestamp = now_bj.strftime('%Y-%m-%d %H:%M:%S')
    full_content = f"北京时间{timestamp}\n\n{content}"

    # 获取通知配置（使用新的环境变量名）
    serverchan_key = os.environ.get('SERVERCHAN_KEY')
    pushplus_token = os.environ.get('PUSHPLUS_TOKEN')
    tg_bot_token = os.environ.get('TG_BOT_TOKEN')
    tg_chat_id = os.environ.get('TG_CHAT_ID')

    if not any([serverchan_key, pushplus_token, tg_bot_token and tg_chat_id]):
        print("未配置任何通知方式，跳过推送。")
        return

    push_success = False

    if serverchan_key:
        print("检测到 SERVERCHAN_KEY，尝试通过 ServerChan 推送...")
        if _push_sct(serverchan_key, title, full_content):
            print("ServerChan 推送成功。")
            push_success = True
        else:
            print("ServerChan 推送失败。")

    if pushplus_token:
        print("检测到 PUSHPLUS_TOKEN，尝试通过 PushPlus 推送...")
        if _push_plus(pushplus_token, title, full_content):
            print("PushPlus 推送成功。")
            push_success = True
        else:
            print("PushPlus 推送失败。")

    if tg_bot_token and tg_chat_id:
        print("检测到 TG_BOT_TOKEN 和 TG_CHAT_ID，尝试通过 Telegram 推送...")
        if _push_tg(tg_bot_token, tg_chat_id, full_content):
            print("Telegram 推送成功。")
            push_success = True
        else:
            print("Telegram 推送失败。")

    if not push_success:
        print("所有通知方式都推送失败。")
    else:
        print("至少一种通知方式推送成功。")