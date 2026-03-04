import smtplib
import os
from email.message import EmailMessage
from datetime import datetime

def send_analysis_email(file_path):
    # 1. 값 가져오기 및 공백 제거
    email_user = os.environ.get('EMAIL_USER', '').strip()
    email_pass = os.environ.get('EMAIL_PASS', '').strip()

    print(f"DEBUG: EMAIL_USER value is -> '{email_user}'")

    # 2. 필수 값 체크
    if not email_user or "@" not in email_user:
        print("❌ ERROR: EMAIL_USER is missing or invalid!")
        return 
    if not email_pass:
        print("❌ ERROR: EMAIL_PASS is missing!")
        return

    # 3. 이메일 구성 (들여쓰기 주의!)
    msg = EmailMessage()
    msg['Subject'] = f"Daily SG-REITs Report ({datetime.now().strftime('%Y-%m-%d')})"
    msg['From'] = email_user
    msg['To'] = email_user
    msg.set_content("Please find the attached daily REITs analysis report.")

    # 4. 첨부파일 확인 및 추가
    if not os.path.exists(file_path):
        print(f"❌ ERROR: File not found at {file_path}")
        return

    try:
        with open(file_path, 'rb') as f:
            file_data = f.read()
            msg.add_attachment(
                file_data, 
                maintype='application', 
                subtype='pdf', 
                filename=os.path.basename(file_path)
            )
    except Exception as e:
        print(f"❌ Attachment Error: {e}")
        return

    # 5. 발송
    try:
        print(f"Attempting to send email via SMTP_SSL...")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(email_user, email_pass)
            server.send_message(msg)
        print("✅ SUCCESS: Email sent successfully!")
    except Exception as e:
        print(f"❌ SMTP ERROR: {e}")