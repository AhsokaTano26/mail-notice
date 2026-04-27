import os
import requests
from fastapi import FastAPI, HTTPException, Request, Query

app = FastAPI()

# 环境变量
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
TG_TOPIC_ID = os.getenv("TG_TOPIC_ID")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")  # 这里的 SECRET 将作为 URL 中的 token


@app.get("/")
def health_check():
    return {"status": "ok", "info": "Zeabur TG Bot is running"}


@app.post("/webhook")
async def handle_webhook(
        request: Request,
        token: str = Query(None)  # 从 URL 参数中获取 token
):
    # 1. 验证 URL 中的 token 是否与环境变量一致
    if not token or token != WEBHOOK_SECRET:
        print(f"DEBUG: Invalid token received: {token}")
        raise HTTPException(status_code=403, detail="Invalid Token")

    try:
        body = await request.json()
        message = body.get("message", "No content")

        # 2. 组装发送到 TG 的内容
        payload = {
            "chat_id": TG_CHAT_ID,
            "text": f"🚀 **Zeabur 通知**\n\n{message}",
            "parse_mode": "Markdown"
        }
        if TG_TOPIC_ID:
            payload["message_thread_id"] = TG_TOPIC_ID

        resp = requests.post(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage", json=payload)
        resp.raise_for_status()

        return {"status": "success"}
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return {"status": "error", "detail": str(e)}, 400


if __name__ == "__main__":
    import uvicorn

    # 运行在 8080 端口
    uvicorn.run(app, host="0.0.0.0", port=8080)