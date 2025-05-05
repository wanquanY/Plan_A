from openai import OpenAI
import json
import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

# 从环境变量中获取配置
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")
model = os.getenv("OPENAI_MODEL")

print(f"从.env加载的配置 - API KEY: {api_key[:5]}*****")
print(f"BASE URL(原始值): '{base_url}'")
print(f"BASE URL(长度): {len(base_url) if base_url else 0}")
print(f"MODEL: '{model}'")

# 确保base_url以/v1结尾
if base_url and not base_url.endswith('/v1'):
    base_url = base_url.rstrip() + '/v1'
    print(f"修正后的BASE URL: '{base_url}'")

# 配置客户端
client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

try:
    print("开始测试API调用...")
    print(f"API基本URL: {client.base_url}")
    
    # 尝试调用API
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": "Say hi"}
        ]
    )
    
    print("API调用成功!")
    print(f"响应类型: {type(response)}")
    print(f"是否为字符串: {isinstance(response, str)}")
    
    if isinstance(response, str):
        print(f"字符串响应: {response[:200]}...")
    else:
        print(f"响应对象内容: {response}")
        print(f"生成的内容: {response.choices[0].message.content}")
    
except Exception as e:
    print(f"API调用失败: {str(e)}") 