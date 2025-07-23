import json
import os
from dotenv import load_dotenv
from lambda_function import lambda_handler  # 把 your_lambda_file 替換成你的檔名（不含 .py）

# 模擬 event/context
with open('test_event.json') as f:
    event = json.load(f)

context = {}  # 可留空或放一些 mock context

# 設定環境變數(僅在本地開發時載入 .env)
if os.environ.get("AWS_EXECUTION_ENV") is None:
    load_dotenv()

result = lambda_handler(event, context)
print(result)
