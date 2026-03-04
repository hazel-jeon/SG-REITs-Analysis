import smtplib
import os
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def send_analysis_email(pdf_filename):
    sender_email = os.environ.get('EMAIL_USER')
    sender_password = os.environ.get('EMAIL_PASS')
    
    msg = MIMEMultipart()
    msg['Subject'] = f"Daily Report - {datetime.datetime.now().strftime('%Y-%m-%d')}"
    msg.attach(MIMEText("Report attached.", 'plain'))

    with open(pdf_filename, "rb") as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {pdf_filename}")
        msg.attach(part)

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)