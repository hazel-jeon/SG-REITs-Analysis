import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

def send_analysis_email(file_path):
    print("\n--- 📧 이메일 발송 디버깅 시작 ---")
    
    # 1. 환경 변수 로드 및 정제
    # Secrets에서 값을 가져올 때 생길 수 있는 공백을 완벽히 제거합니다.
    email_user = str(os.environ.get('EMAIL_USER', '')).strip()
    email_pass = str(os.environ.get('EMAIL_PASS', '')).strip()

    if not email_user or not email_pass:
        print("❌ 에러: EMAIL_USER 또는 EMAIL_PASS가 설정되지 않았습니다.")
        return

    # 2. 이메일 객체 구성
    msg = MIMEMultipart()
    msg['From'] = email_user
    msg['To'] = email_user
    msg['Subject'] = f"🇸🇬 SG-REITs Daily Report ({datetime.now().strftime('%Y-%m-%d')})"
    
    msg.attach(MIMEText("자동화 시스템에서 발송된 리츠 분석 리포트입니다.", 'plain'))

    # 3. 첨부파일 추가
    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(file_path)}")
                msg.attach(part)
            print(f"✅ 파일 첨부 완료: {file_path}")
        except Exception as e:
            print(f"❌ 파일 첨부 중 에러: {e}")
            return
    else:
        print(f"❌ 에러: 첨부할 파일이 없습니다.")
        return

    # 4. 발송 (가장 확실한 sendmail 방식)
    print(f"🚀 Gmail 서버 접속 시도 중... (수신자: {email_user})")
    try:
        # SSL 보안 연결 (465 포트)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            # 로그인 시도
            server.login(email_user, email_pass)
            print("🔑 로그인 성공!")
            
            # [중요] send_message 대신 sendmail을 사용하여 주소를 명시적으로 전달
            server.sendmail(email_user, [email_user], msg.as_string())
            
        print("🎉 [성공] 이메일 발송 완료!")
        
    except smtplib.SMTPAuthenticationError:
        print("❌ 에러: 로그인 실패. (앱 비밀번호 16자리를 다시 확인하세요)")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    send_analysis_email("SG_REITs_Analysis.pdf")