from flask import *   # Flaskのなかみを全部持ってくる
import sqlite3  # sqliteつかいます
import uuid #idを生成します
import hashlib #ハッシュ関数を使います
from cryptography.fernet import Fernet
import random #乱数を生成する
#メール関係
import smtplib, ssl
from email.mime.text import MIMEText
app = Flask(__name__)  # アプリの設定
from datetime import datetime

app.secret_key = 'o6fJH4Yyx7E9DJ28KV7fashaT8LTX7hNb35sz1lf2iE='  # 鍵の設定

@app.route("/")

def jump():
    return redirect("/openlist")


# ユーザーを全て表示
@app.route("/userlist")
def userlist():
    if "user_id" in session:
        #自分のIDを取得
        my_id = session["user_id"]
    else:
        #非ログイン時、Noneにすることで、userlist.htmlでチャットするボタンを表示しない準備
        my_id = None
    conn = sqlite3.connect('chattest.db')
    c = conn.cursor()
    #名無し以外の情報を取得
    c.execute("select id, name from user where id <> 'nanashi'")
    user_info = c.fetchall()
    conn.close()
    return render_template("userlist.html", tpl_user_info=user_info, tpl_my_id=my_id)


# /userlistで「チャットする」ボタンを押したときに動くプログラム。チャットルームがなければ(まだチャットしたことのない相手であれば)新規作成。
@app.route("/chatroom/<string:other_id>", methods=["POST"])
def chatroom_post(other_id):
    if "user_id" in session:
        # まずはチャットルームがあるかchatidをとってくる
        my_id = session["user_id"]
        print(my_id)
        conn = sqlite3.connect('chattest.db')
        c = conn.cursor()
        c.execute(
            "select id from chat where (user_id1 = ? and user_id2 = ?) or (user_id1 = ? and user_id2 = ?)", (my_id, other_id, other_id, my_id))
        chat_id = c.fetchone()

        #idがNoneであれば作成、それ以外(数字が入っていれば)スルー
        if chat_id == None:
            # 作ったチャットルームのidを取得
            room_id = str(uuid.uuid4())

            c.execute("select name from user where id = ?", (my_id,))
            myname = c.fetchone()[0]
            c.execute("select name from user where id = ?", (other_id,))
            othername = c.fetchone()[0]
            # ルーム名を作る
            room = myname + "と" + othername + "のチャット"
            c.execute("insert into chat values(?,?,?,?)",
                      (room_id, my_id, other_id, room))
            conn.commit()
            c.execute(
                "select id from chat where (user_id1 = ? and user_id2 = ?) or (user_id1 = ? and user_id2 = ?)", (my_id, other_id, other_id, my_id))
            chat_id = c.fetchone()
            conn.commit()

        conn.close()
        return redirect(url_for('chat_get', chatid=chat_id[0]))
    else:
        return redirect("/login")


# 自分のチャットルーム一覧を表示するプログラム
@app.route("/chatroom")
def chatroom_get():
    if "user_id" in session:
        my_id = session["user_id"]
        conn = sqlite3.connect('chattest.db')
        c = conn.cursor()
        # ここにチャットルーム一覧をDBからとって、表示するプログラム
        c.execute(
            "select id, room from chat where user_id1 = ? or user_id2 = ?", (my_id, my_id))
        chat_list = c.fetchall()
        return render_template("/chatroom.html", tpl_chat_list=chat_list)
    else:
        return redirect("/login")


# チャットルーム表示
@app.route("/chat/<string:chatid>")
def chat_get(chatid):
    if "user_id" in session:
        my_id = session["user_id"]
        # ここにチャットをDBからとって、表示するプログラム
        conn = sqlite3.connect('chattest.db')
        c = conn.cursor()
        c.execute(
            "select chatmess.to_user, chatmess.from_user, chatmess.message, user.name from chatmess inner join user on chatmess.from_user = user.id where chat_id = ?", (chatid,))
        chat_fetch = c.fetchall()
        chat_info = []
        for chat in chat_fetch:
            chat_info.append(
                {"to": chat[0], "from": chat[1], "message": chat[2], "fromname": chat[3]})
        c.execute("select room from chat where id = ?", (chatid,))
        room_name = c.fetchone()[0]
        c.close()
        return render_template("chat.html", chat_list=chat_info, link_chatid=chatid, tpl_room_name=room_name, tpl_my_id=my_id)
    else:
        return redirect("/login")


# チャット送信時のプログラム
@app.route("/chat/<string:chatid>", methods=["POST"])
def chat_post(chatid):
    if "user_id" in session:
        # ここにチャットの送信ボタンが押されたときにDBに格納するプログラム
        my_id = session["user_id"]
        chat_message = request.form.get("input_message")
        conn = sqlite3.connect('chattest.db')
        c = conn.cursor()
        c.execute(
            "select user_id1, user_id2 from chat where id = ?", (chatid,))
        chat_user = c.fetchone()
        print(chat_user)
        if my_id != chat_user[0]:
            to_id = chat_user[0]
        else:
            to_id = chat_user[1]
        print(to_id)
        c.execute("insert into chatmess values(null,?,?,?,?)",
                  (chatid, to_id, my_id, chat_message))
        conn.commit()
        c.close()

        return redirect("/chat/{}".format(chatid))
    else:
        return redirect("/login")

# オープンチャット一覧を表示するプログラム
@app.route("/openlist")
def openroom_get():
    conn = sqlite3.connect('chattest.db')
    c = conn.cursor()
    # ここにチャットルーム一覧をDBからとって、表示するプログラム
    #部屋のIDと名前を取得
    c.execute(
        "select id, room from open")
    open_list = c.fetchall()
    c.close()
    return render_template("/openlist.html", tpl_open_list=open_list)

#オープンチャットの部屋を作成する
@app.route("/makeopen",methods=['POST'])
def openroom_make():
    #htmlの入力からroom名を取得
    room_name = request.form['room']
    #idを生成
    room_id = str(uuid.uuid4())
    conn = sqlite3.connect('chattest.db')
    c = conn.cursor()
    #ルームIDとルーム名を登録
    c.execute("insert into open values(?,?)", (room_id, room_name))
    conn.commit()
    conn.close()
    print(room_name)
    return render_template("openchat.html",link_openid=room_id, tpl_room_name=room_name)   


# オープンチャットルーム表示
@app.route("/open/<string:openid>")
def open_get(openid):
    if "user_id" in session:
        #自分のIDを取得
        my_id = session["user_id"]
    else:
        my_id = None
    conn = sqlite3.connect('chattest.db')
    c = conn.cursor()
    #部屋のIDからユーザーID、メッセージ、ユーザーネームを取得
    c.execute(
        "select openmess.user_id, openmess.message, user.name from openmess inner join user on openmess.user_id = user.id where openmess.id = ?", (openid,))
    chat_fetch = c.fetchall()
    chat_info = []
    #chat_infoに取得した情報を代入していく
    for chat in chat_fetch:
        chat_info.append(
            {"user_id": chat[0], "message": chat[1], "user_name": chat[2]})
        print(chat_info)  
    #部屋名を取得
    c.execute("select room from open where id = ?", (openid,))
    room_name = c.fetchone()[0]
    print(room_name,chat_info)
    c.close()
    #チャットの内容、部屋のID、部屋名
    return render_template("openchat.html", chat_list=chat_info, link_openid=openid, tpl_room_name=room_name, tpl_my_id=my_id)



# オープンチャット送信時のプログラム
@app.route("/open/<string:openid>", methods=["POST"])
def open_post(openid):
    if "user_id" in session:
        # ログイン時
        my_id = session["user_id"]
        chat_message = request.form.get("input_message")
        conn = sqlite3.connect('chattest.db')
        c = conn.cursor()
        c.execute("insert into openmess values(?,?,?)",
                  (openid, my_id, chat_message))
        conn.commit()
        c.close()
        return redirect("/open/{}".format(openid))
    else:
        # 非ログイン時
        #事前に名無しさん（id:nanashi）というアカウントをデータベースに入れておく
        my_id = "nanashi"
        chat_message = request.form.get("input_message")
        conn = sqlite3.connect('chattest.db')
        c = conn.cursor()
        c.execute("insert into openmess values(?,?,?)",
                  (openid, my_id, chat_message))
        conn.commit()
        c.close()
        return redirect("/open/{}".format(openid))        


# ログイン画面表示
@app.route("/login")
def login_get():
    return render_template("login.html")

# 新規登録画面表示
@app.route("/goregister")
def go_register():
    return render_template("register.html",result=None)


# ログインするプログラム。
@app.route("/login", methods=["POST"])
def login():
    name = request.form.get("name")
    password = request.form.get("password")
    hashpass = hashlib.sha256(password.encode()).hexdigest()
    conn = sqlite3.connect('chattest.db')
    c = conn.cursor()
    c.execute(
        "select id from user where name = ? and password = ?", (name, hashpass))
    user_id = c.fetchone()
    conn.close()
    print(type(user_id))
    if user_id is None:
        return render_template("login.html")
    else:
        session['user_id'] = user_id[0]
        return redirect("/openlist")


# アカウント作成(新規ユーザー登録)プログラム
@app.route("/regist", methods=["POST"])
def regist():
    data = request.form
    user_id = data.get("id")
    name = data.get("name")
    password = data.get("password")
    passveri = data.get("passveri")   
    mail_address = data.get("mail_address")

    #必須項目チェック
    if not mail_address or \
            not name or \
            not password or \
            not passveri or \
            password != passveri:
        flash('エラーです')
        # パスワードは明示的に削除する
        del password
        del passveri
        return render_template("register.html",result=data)

    #パスワードをハッシュ化する
    hashpass = hashlib.sha256(password.encode()).hexdigest()

    #IDが使用中かDBを確認
    conn = sqlite3.connect('chattest.db')
    c = conn.cursor()
    c.execute(
        'select id from user where id = ?', (id))
    db_check = c.fetchone()
    conn.close()

    #IDが登録済みの場合
    if db_check != None:
        conn.close()
        #パスワードを明示的に削除する
        del password
        del passveri
        del hashpass
        return render_template("register.html",result=data)
    else:
        conn = sqlite3.connect('chattest.db')
        c = conn.cursor()
        c.execute("insert into user values(?,?,?,?)", (user_id, name, hashpass, mail_address))
        conn.commit()
        conn.close()
        #パスワードを明示的に削除する
        del password
        del passveri
        del hashpass
        return redirect("/login")

# パスワードを忘れた人
@app.route("/forget_password")
def forget_password():
    return render_template("forget_password.html")

#メールにコードを送信
@app.route("/send_code", methods=["POST"])
def send_code():
    id = request.form.get("id")
    conn = sqlite3.connect('chattest.db')
    c = conn.cursor()
    c.execute(
        'select mail_address from user where id = ?', (id,))
    mail_address = c.fetchone()
    print(mail_address[0])
    conn.close()
    if mail_address is None:
        return render_template("forget_password.html")
    else:
        passcode = '%06d' % random.randint(0, 1000000)
        print(passcode)
        # SMTP認証情報
        account = "rikepop.chattest@gmail.com"
        password = "fjiiiwjwkqasnsnp"
        
        # 送受信先
        to_email = mail_address[0]
        from_email = account
        
        # MIMEの作成
        subject = "パスワード再設定用の確認コード"
        message = "確認コードは  " + passcode + "  です。"
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
 
        return render_template("reset_password.html",passcode=passcode,id=id)

@app.route("/reset_password", methods=["POST"])
def reset_password():
    data = request.form
    id = data.get("id")
    passcode = data.get("passcode")
    codeveri = data.get("codeveri")
    password = data.get("password")
    passveri = data.get("passveri")
    #必須項目チェック
    if not passcode or \
            not codeveri or \
            not password or \
            not passveri or \
            password != passveri or \
            passcode != codeveri:
        flash('エラーです')
        # パスワードは明示的に削除する
        del password
        del passveri
        return render_template("reset_password.html",passcode=passcode,id=id)

    hashpass = hashlib.sha256(password.encode()).hexdigest()
    del password
    del passveri
    
    conn = sqlite3.connect('chattest.db')
    c = conn.cursor()
    c.execute("update user set password = ? where id = ?", (hashpass, id))
    conn.commit()
    conn.close()
    return render_template("login.html")

@app.route("/forget_ID")
def forget_ID():
    return render_template("forget_id.html")

#メールにIDを送信
@app.route("/send_id", methods=["POST"])
def send_id():
    mail_address = request.form.get("mail_address")
    conn = sqlite3.connect('chattest.db')
    c = conn.cursor()
    c.execute(
        'select id from user where mail_address = ?', (mail_address,))
    id = c.fetchone()
    conn.close()
    if id is None:
        return render_template("forget_id.html")
    else:

        # SMTP認証情報
        account = "rikepop.chattest@gmail.com"
        password = "fjiiiwjwkqasnsnp"
        
        # 送受信先
        to_email = mail_address
        from_email = account
        
        # MIMEの作成
        subject = "IDの確認メール"
        message = "このメールアドレスに登録されているIDは  " + id[0] + "  です。"
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
 
        return render_template("login.html")


# ログアウト
@app.route("/logout")
def logout():
    session.pop('user_id', None)
    return redirect("/login")


if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=3000)