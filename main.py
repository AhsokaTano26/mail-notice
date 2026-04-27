import hmac
import hashlib
import json
from fastapi import FastAPI, Request, HTTPException, Header
import requests
import os
app = FastAPI()

# --- 配置区 ---
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
TG_TOPIC_ID = os.getenv("TG_TOPIC_ID")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")


# --------------

def send_to_telegram(text: str):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "message_thread_id": TG_TOPIC_ID
    }
    try:
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
    except Exception as e:
        print(f"发送 TG 失败: {e}")


@app.post("/webhook")
async def handle_webhook(
        request: Request,
        x_zeabur_secret: str = Header(None)  # 假设密钥放在 Header 的 X-Zeabur-Secret 中
):
    # 1. 验证密钥 (简单比对方式)
    # 如果 Zeabur 允许在 URL 后加参数，也可以用 request.query_params 获取
    if x_zeabur_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid Secret")

    # 2. 解析 Body
    try:
        body = await request.json()
        msg_type = body.get("type", "Unknown")
        message = body.get("message", "No message content")
        timestamp = body.get("timestamp", "N/A")

        # 3. 格式化并转发
        tg_text = (
            f"🔔 *Zeabur Webhook 通知*\n\n"
            f"👤 **类型**: {msg_type}\n"
            f"📝 **内容**: {message}\n"
            f"⏰ **时间**: `{timestamp}`"
        )

        send_to_telegram(tg_text)
        return {"status": "success"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing JSON: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    # 运行在 8080 端口
    uvicorn.run(app, host="0.0.0.0", port=8080)