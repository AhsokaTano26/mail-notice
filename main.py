import os
import hmac
import hashlib
import requests
from fastapi import FastAPI, Request, HTTPException, Header
from datetime import datetime, timedelta, timezone

app = FastAPI()

# 环境变量
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
TG_TOPIC_ID = os.getenv("TG_TOPIC_ID")
# Zeabur Email 提供的签名密钥
ZSEND_WEBHOOK_SECRET = os.getenv("ZSEND_WEBHOOK_SECRET")


def format_time(ts: str):
    if not ts:
        return "N/A"
    try:
        # 解析为 UTC 时间
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))

        # 转换为 UTC+8
        utc8 = timezone(timedelta(hours=8))
        dt = dt.astimezone(utc8)

        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return ts


def tg_escape(text: str):
    """简单 HTML 转义"""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_message(payload: dict) -> str:
    event = payload.get("event")
    timestamp = format_time(payload.get("timestamp"))

    email = payload.get("email", {})
    data = payload.get("data", {})

    subject = tg_escape(email.get("subject", ""))
    sender = tg_escape(email.get("from", ""))
    to_list = email.get("to", [])
    to = ", ".join(to_list) if to_list else "N/A"
    msg_id = email.get("message_id", "")
    email_id = email.get("id", "")

    base_info = f"""
<b>📧 邮件事件通知</b>

<b>类型:</b> {event}
<b>时间:</b> {timestamp}

<b>主题:</b> {subject}
<b>发件人:</b> {sender}
<b>收件人:</b> {to}

<b>Message ID:</b> <code>{msg_id}</code>
<b>Email ID:</b> <code>{email_id}</code>
"""

    # === 不同事件处理 ===
    if event == "delivery":
        return base_info + f"""
<b>📬 投递成功</b>

处理时间: {data.get("processing_time_millis", "N/A")} ms
SMTP响应: {tg_escape(data.get("smtp_response", ""))}
"""

    elif event == "bounce":
        recipients = data.get("bounced_recipients", [])
        detail = ""
        for r in recipients:
            detail += f"""
- {r.get("email_address")}
  状态: {r.get("status")}
  原因: {tg_escape(r.get("diagnostic_code", ""))}
"""

        return base_info + f"""
<b>❌ 退信</b>

类型: {data.get("bounce_type")}
子类型: {data.get("bounce_subtype")}

<b>失败地址:</b>
{detail}
"""

    elif event == "complaint":
        complained = ", ".join(data.get("complained_recipients", []))

        return base_info + f"""
<b>⚠️ 投诉</b>

类型: {data.get("complaint_feedback_type")}
投诉用户: {complained}
"""

    elif event == "open":
        return base_info + f"""
<b>👀 邮件被打开</b>

时间: {format_time(data.get("timestamp"))}
IP: {data.get("ip_address")}
设备: {tg_escape(data.get("user_agent", ""))}
"""

    elif event == "click":
        return base_info + f"""
<b>🖱️ 点击链接</b>

时间: {format_time(data.get("timestamp"))}
IP: {data.get("ip_address")}
链接: {tg_escape(data.get("link", ""))}
设备: {tg_escape(data.get("user_agent", ""))}
"""

    else:
        return base_info + "\n<b>未知事件</b>"


def verify_signature(timestamp: str, signature: str, body: bytes):
    """验证 Zeabur Email 的 HMAC-SHA256 签名"""
    if not signature or not timestamp or not ZSEND_WEBHOOK_SECRET:
        return False

    # 构造签名消息: {timestamp}.{body}
    message = f"{timestamp}.".encode('utf-8') + body

    # 计算 HMAC-SHA256
    expected_hash = hmac.new(
        ZSEND_WEBHOOK_SECRET.encode('utf-8'),
        message,
        hashlib.sha256
    ).hexdigest()

    expected_signature = f"sha256={expected_hash}"

    # 使用安全比较
    return hmac.compare_digest(signature, expected_signature)


@app.post("/webhook")
async def handle_zsend_webhook(
        request: Request,
        x_zsend_signature: str = Header(None),
        x_zsend_timestamp: str = Header(None)
):
    # 1. 获取原始 Body 用于签名验证
    body_bytes = await request.body()

    # 2. 签名验证
    if not verify_signature(x_zsend_timestamp, x_zsend_signature, body_bytes):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # 3. 解析 JSON
    payload = await request.json()
    msg = build_message(payload)

    # 5. 发送至 Telegram
    tg_payload = {
        "chat_id": TG_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML",
        "message_thread_id": TG_TOPIC_ID if TG_TOPIC_ID else None
    }

    try:
        requests.post(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage", json=tg_payload)
    except Exception as e:
        print(f"TG 发送失败: {e}")

    return {"received": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)