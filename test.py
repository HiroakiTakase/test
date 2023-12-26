# openaiのテスト用。ローカルで単体実行
import os
from dotenv import load_dotenv
import openai

load_dotenv()
openai.api_type = "azure"
openai.api_version = "2023-05-15"
openai.api_key = os.environ["OPENAI_API_KEY"]
openai.api_base = "https://slackchatbot.openai.azure.com/"

# ChatCompletionリクエスト（会話型リクエスト）の作成
response = openai.ChatCompletion.create(
    deployment_id="slack_bot",  # デプロイメントの指定
    messages=[  # 会話内容のリスト
        {
            "role": "system",
            "content": "具志堅用高について教えて"
        }
    ],
    temperature=0.7,  # クリエイティビティレベル
    max_tokens=800,  # 返信文の最大文字数
    top_p=0.95,  # 上位トークンの確率
    frequency_penalty=0,  # 頻度ペナルティ
    presence_penalty=0,  # 存在ペナルティ
    stop=None  # 停止条件
)
# レスポンスの表示
print(response)
