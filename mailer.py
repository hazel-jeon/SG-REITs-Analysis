import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

def send_analysis_email(file_path):
    # 환경 변수 가져오기 (양쪽 공백 완벽 제거)
    email_user = str(os.environ.get('EMAIL_USER', '')).strip()
    email_pass = str(os.environ.get('EMAIL_PASS', '')).strip()

    print(f"DEBUG: Trying to send email to [{email_user}]")

    if not email_user or "@" not in email_user:
        print("❌ ERROR: Invalid EMAIL_USER")
        return

    # 메시지 객체 생성
    msg = MIMEMultipart()
    msg['From'] = email_user
    msg['To'] = email_user
    msg['Subject'] = f"Daily SG-REITs Report ({datetime.now().strftime('%Y-%m-%d')})"
    
    msg.attach(MIMEText("Please find the attached report.", 'plain'))

    # 파일 첨부
    try:
        with open(file_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename= {os.path.basename(file_path)}")
            msg.attach(part)
    except Exception as e:
        print(f"❌ Attachment Error: {e}")
        return

    # 발송 (sendmail 메서드 사용)
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(email_user, email_pass)
            # send_message 대신 sendmail을 사용하여 주소를 명시적으로 전달
            server.sendmail(email_user, email_user, msg.as_string())
        print("✅ SUCCESS: Email sent!")
    except Exception as e:
        print(f"❌ SMTP ERROR: {e}")