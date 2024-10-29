from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import requests
import os
from dotenv import load_dotenv
line_router = APIRouter()

# LINE APIの設定
load_dotenv()
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# LINE Webhookのエンドポイント
@line_router.post("/webhook")
async def callback(request: Request, background_tasks: BackgroundTasks):
    signature = request.headers["X-Line-Signature"]
    body = await request.body()
    print(body)
    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Webhookリクエストに早く応答
    return "OK"


# LINE Botのメッセージ受信と処理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event, background_tasks: BackgroundTasks):
    user_message = event.message.text
    try:
        racecourse, count, race_date, race_num = user_message.split(",")
    except ValueError:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="入力形式が間違っています。例: 京都,05,06,11")
        )
        return

    # FastAPI 競馬APIへのリクエストをバックグラウンドで実行
    background_tasks.add_task(send_race_result, event.reply_token, racecourse, count, race_date, race_num)

async def send_race_result(reply_token, racecourse, count, race_date, race_num):
    url = "http://localhost:8000/api/race_result"
    response = requests.post(url, json={
        "racecourse": racecourse,
        "count": count,
        "race_date": race_date,
        "race_num": race_num
    })

    if response.status_code == 200:
        result_text = "\n".join([f"{r['rank']}: {r['name']} (人気: {r['ninki']}, オッズ: {r['odds']})" for r in response.json()])
        line_bot_api.reply_message(reply_token, TextSendMessage(text=result_text))
    else:
        line_bot_api.reply_message(reply_token, TextSendMessage(text="結果が取得できませんでした。"))
