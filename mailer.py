import smtplib
import os
from email.message import EmailMessage
from datetime import datetime  # datetime 모듈 추가

def send_analysis_email(file_path):
    # 1. GitHub Secrets에서 환경 변수 가져오기
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASS')

    # 디버깅용: 변수가 비어있는지 체크 (비밀번호는 보안상 출력 금지)
    if not email_user:
        print("Error: EMAIL_USER environment variable is missing.")
        return

    # 2. 이메일 내용 구성
    msg = EmailMessage()
    today_str = datetime.now().strftime("%Y-%m-%d")
    msg['Subject'] = f"Daily SG-REITs Analysis Report ({today_str})"
    msg['From'] = email_user
    msg['To'] = email_user  # 본인에게 발송
    msg.set_content("Please find the attached daily REITs analysis report.")

    # 3. PDF 첨부
    try:
        with open(file_path, 'rb') as f:
            file_data = f.read()
            msg.add_attachment(
                file_data, 
                maintype='application', 
                subtype='pdf', 
                filename=os.path.basename(file_path)
            )
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        return

    # 4. 이메일 발송
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(email_user, email_pass)
            server.send_message(msg)
        print(f"Email sent successfully to {email_user}!")
    except Exception as e:
        print(f"Failed to send email: {e}")