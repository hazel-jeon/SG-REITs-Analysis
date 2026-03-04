import smtplib
import os
from email.message import EmailMessage

def send_analysis_email(file_path):
    # GitHub Secrets에서 이메일 주소와 비밀번호를 가져옴
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASS')

    # 이메일 내용 구성
    msg = EmailMessage()
    msg['Subject'] = f"Daily SG-REITs Analysis Report ({os.date.today() if hasattr(os, 'date') else 'Today'})"
    msg['From'] = email_user
    msg['To'] = email_user  # <-- 이 부분이 비어있거나 잘못되면 에러가 납니다!
    msg.set_content("Please find the attached daily REITs analysis report.")

    # PDF 첨부
    with open(file_path, 'rb') as f:
        file_data = f.read()
        msg.add_attachment(file_data, maintype='application', subtype='pdf', filename=file_path)

    # 이메일 발송
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(email_user, email_pass)
        server.send_message(msg)
    print("Email sent successfully!")