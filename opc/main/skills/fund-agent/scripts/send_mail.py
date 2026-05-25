#!/usr/bin/env python3
"""Fund-Agent 邮件发送脚本（凭证已加密）"""
import smtplib
import subprocess
import os
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import markdown

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENC_FILE = os.path.join(SCRIPT_DIR, "smtp.enc")
ENV_FILE = "/root/clawd/.env"

EMAIL_CSS = """
<style>
  body { font-family: -apple-system, Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; color: #333; }
  h1 { color: #1a1a1a; border-bottom: 2px solid #e74c3c; padding-bottom: 8px; }
  h2 { color: #2c3e50; margin-top: 24px; }
  h3 { color: #34495e; margin-top: 16px; }
  table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 14px; }
  th { background: #34495e; color: white; padding: 10px 12px; text-align: left; }
  td { padding: 8px 12px; border-bottom: 1px solid #ddd; }
  tr:nth-child(even) { background: #f8f9fa; }
  tr:hover { background: #eef2f7; }
  blockquote { border-left: 4px solid #e74c3c; margin: 12px 0; padding: 8px 16px; background: #fdf0ef; }
  hr { border: none; border-top: 1px solid #ddd; margin: 20px 0; }
  code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-size: 13px; }
  .green { color: #27ae60; font-weight: bold; }
  .red { color: #e74c3c; font-weight: bold; }
</style>
"""

def md_to_html(md_text):
    """Markdown → 带样式的 HTML 邮件"""
    html_body = markdown.markdown(md_text, extensions=['tables', 'fenced_code'])
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8">{EMAIL_CSS}</head>
<body>{html_body}</body>
</html>"""

def decrypt_creds():
    """解密 SMTP 凭证"""
    if not os.path.exists(ENC_FILE):
        raise FileNotFoundError("smtp.enc 未配置：公共模板默认不包含邮件凭证，请先为本容器单独配置后再发邮件")
    if not os.path.exists(ENV_FILE):
        raise FileNotFoundError("/root/clawd/.env 不存在，无法读取 SMTP_ENC_KEY")
    key = None
    with open(ENV_FILE) as f:
        for line in f:
            if line.startswith("SMTP_ENC_KEY="):
                key = line.split("=", 1)[1].strip()
                break
    if not key:
        raise ValueError("SMTP_ENC_KEY 未找到")
    
    result = subprocess.run(
        ["openssl", "enc", "-aes-256-cbc", "-d", "-pbkdf2", "-k", key, "-in", ENC_FILE],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"解密失败: {result.stderr}")
    
    parts = result.stdout.strip().split("|")
    return {
        "user": parts[0],
        "pass": parts[1],
        "receiver": parts[2],
        "host": parts[3],
        "port": int(parts[4]),
        "name": parts[5]
    }

def send_email(subject, body, html=False):
    """发送邮件"""
    creds = decrypt_creds()
    
    msg = MIMEMultipart('alternative')
    msg['From'] = f"{creds['name']} <{creds['user']}>"
    msg['To'] = creds['receiver']
    msg['Subject'] = subject
    
    if html:
        html_body = md_to_html(body)
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    else:
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    try:
        server = smtplib.SMTP_SSL(creds['host'], creds['port'])
        server.login(creds['user'], creds['pass'])
        server.send_message(msg)
        server.quit()
        print(f"✅ 邮件发送成功 → {creds['receiver']}")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

def generate_daily_report():
    """生成理财日报"""
    data_dir = os.path.join(SCRIPT_DIR, "../data")
    positions_file = os.path.join(data_dir, "positions.json")
    
    try:
        with open(positions_file) as f:
            data = json.load(f)
        
        total = data.get('total_market_value', 0)
        loss = data.get('total_cumulative_loss', 0)
        count = len(data.get('positions', []))
        
        risk_funds = []
        for p in data.get('positions', []):
            pct = p.get('holding_pct', 0)
            if pct < -3:
                risk_funds.append(f"⚠️ {p['name']}: {pct:+.2f}%")
        
        risk_html = "<br>".join(risk_funds) if risk_funds else "✅ 无触发止损线基金"
        
        subject = f"Fund-Agent 理财日报 | 总市值 ¥{total:,.0f}"
        body = f"""
<h2>⚡ Fund-Agent 理财日报</h2>
<p><b>总市值:</b> ¥{total:,.0f}</p>
<p><b>累计盈亏:</b> ¥{loss:,.0f}</p>
<p><b>持仓数:</b> {count} 只</p>
<hr>
<h3>⚠️ 风险提示</h3>
<p>{risk_html}</p>
<hr>
<p><i>Fund-Agent 自动推送</i></p>
"""
        return subject, body, True
    except Exception as e:
        return f"Fund-Agent 异常: {e}", f"生成日报失败: {e}", False

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        subject = sys.argv[1]
        body = sys.argv[2]
        html_mode = len(sys.argv) > 3 and sys.argv[3] == "--html"
    else:
        subject, body, html_mode = generate_daily_report()
    
    send_email(subject, body, html_mode)
