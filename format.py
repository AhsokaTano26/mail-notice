import json
from datetime import datetime


def format_time(ts: str):
    if not ts:
        return "N/A"
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
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