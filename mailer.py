import smtplib
import os
from email.message import EmailMessage
from datetime import datetime

def send_analysis_email(file_path):
    # 1. 값 가져오기
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASS')

    # [중요] 디버깅 로그: 이 값이 Actions 로그에 찍혀야 합니다.
    print(f"DEBUG: EMAIL_USER value is -> '{email_user}'")

    # 2. 만약 값이 비어있다면 강제로 에러를 내서 중단시킵니다.
    if not email_user or "@" not in email_user:
        print("❌ ERROR: EMAIL_USER is missing or invalid in GitHub Secrets!")
        # 비밀번호가 없는 경우도 체크
        if not email_pass:
            print("❌ ERROR: EMAIL_PASS is missing in GitHub Secrets!")
        return 

    # 3. 이메일 구성
    msg = EmailMessage()
    msg['Subject'] = f"Daily SG-REITs Report ({datetime.now().strftime('%Y-%m-%d')})"
    msg['From'] = email_user
    msg['To'] = email_user  # 받는 사람을 명시적으로 내 메일로 지정
    msg.set_content("Attached is the daily REITs analysis.")

    # 4. 첨부파일 확인
    if not os.path.exists(file_path):
        print(f"❌ ERROR: File not found at {file_path}")
        return

    with open(file_path, 'rb') as f:
        msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename=os.path.basename(file_path))

    # 5. 발송
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(email_user, email_pass)
            server.send_message(msg)
        print("✅ SUCCESS: Email sent successfully!")
    except Exception as e:
        print(f"❌ SMTP ERROR: {e}")