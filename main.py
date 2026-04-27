import os
import hmac
import hashlib
import requests
from fastapi import FastAPI, Request, HTTPException, Header

app = FastAPI()

# 环境变量
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
TG_TOPIC_ID = os.getenv("TG_TOPIC_ID")
# Zeabur Email 提供的签名密钥
ZSEND_WEBHOOK_SECRET = os.getenv("ZSEND_WEBHOOK_SECRET")


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
    event = payload.get("event", "unknown")
    email = payload.get("email", {})
    data = payload.get("data", {})

    # 4. 根据事件类型定制消息内容
    status_emoji = {
        "send": "📩", "delivery": "✅", "bounce": "❌",
        "complaint": "⚠️", "reject": "🚫", "open": "👀", "click": "🖱️"
    }.get(event, "🔔")

    # 基础信息
    msg_lines = [
        f"{status_emoji} **Zeabur Email: {event.upper()}**",
        f"📧 **主题**: `{email.get('subject')}`",
        f"👤 **收件人**: `{', '.join(email.get('to', []))}`",
    ]

    # 针对性解析 data 字段
    if event == "bounce":
        msg_lines.append(f"❗ **退信类型**: {data.get('bounce_type')} ({data.get('bounce_subtype')})")
        for rcpt in data.get("bounced_recipients", []):
            msg_lines.append(f"🚩 **诊断码**: `{rcpt.get('diagnostic_code')}`")

    elif event == "click":
        msg_lines.append(f"🔗 **点击链接**: {data.get('link')}")

    elif event == "delivery":
        msg_lines.append(f"⏱️ **处理耗时**: {data.get('processing_time_millis')}ms")

    # 5. 发送至 Telegram
    tg_text = "\n".join(msg_lines)

    tg_payload = {
        "chat_id": TG_CHAT_ID,
        "text": tg_text,
        "parse_mode": "Markdown",
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