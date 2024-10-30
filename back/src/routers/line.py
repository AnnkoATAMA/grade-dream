from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
from dotenv import load_dotenv

from .keiba import get_race_results
line_router = APIRouter()

racecourse_codes = {
    "札幌": "01", "函館": "02", "福島": "03", "新潟": "04",
    "東京": "05", "中山": "06", "中京": "07", "京都": "08",
    "阪神": "09", "小倉": "10"
}

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
        background_tasks.add_task(
            handler.handle, body.decode("utf-8"), signature
        )
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Webhookリクエストに早く応答
    return "OK"


# LINE Botのメッセージ受信と処理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    print(user_message)
    try:
        racecourse, count, race_date, race_num = user_message.replace(" ", "").split(",")
        racecourse_code = racecourse_codes.get(racecourse)
        print(racecourse, count, race_date, race_num)
    except ValueError:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="入力形式が間違っています。例: 京都,05,06,11")
        )
        return

    send_race_result(event.reply_token, racecourse_code, count, race_date, race_num)

def send_race_result(reply_token, racecourse_code, count, race_date, race_num):
    result = get_race_results(racecourse_code, count, race_date, race_num)
    print(result)

    if result:
        result_text = "\n".join([f"{r['rank']}着 {r['name']} ({r['ninki']}番人気, オッズ: {r['odds']})" for r in result])
        line_bot_api.reply_message(reply_token, TextSendMessage(text=result_text))
    else:
        line_bot_api.reply_message(reply_token, TextSendMessage(text="結果が取得できませんでした。"))
