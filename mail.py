from email.mime.text import MIMEText
import smtplib
 
# SMTP認証情報
account = "rikepop.chattest@gmail.com"
password = "fjiiiwjwkqasnsnp"
 
# 送受信先
to_email = "21nm750l@vc.ibaraki.ac.jp"
from_email = "rikepop.chattest@gmail.com"
 
# MIMEの作成
subject = "テストメール"
message = "テストメール"
msg = MIMEText(message, "html")
msg["Subject"] = subject
msg["To"] = to_email
msg["From"] = from_email
 
# メール送信処理
server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()
server.login(account, password)
server.send_message(msg)
server.quit()