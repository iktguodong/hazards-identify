from openai import OpenAI
import base64
import os
import gradio as gr
import psycopg2  # PostgreSQL客户端
from datetime import datetime

# API 基础 URL
API_BASE = "https://api.lingyiwanwu.com/v1"

# 初始化 OpenAI 客户端
client = OpenAI(
    api_key=os.getenv("_01_API_KEY"),
    base_url=API_BASE
)

# 初始化 PostgreSQL 数据库连接
def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )

# 读取本地图像并将其编码为 Base64
def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        image_data = image_file.read()
    image_type = image_path.split('.')[-1]
    return f"data:image/{image_type};base64,{base64.b64encode(image_data).decode('utf-8')}"

# 设置系统指令
SYSTEM_INSTRUCTION = """
你的名字叫“小安”，是一名专业的安全生产隐患排查治理专家，擅长隐患识别，熟悉安全生产法律法规、标准规范以及实际管理经验，
能够提供专业的建议和答案，包括但不限于安全隐患内容描述、隐患依据、整改建议等内容。
隐患依据可以是法律、法规、国家标准、行业标准、规范性文件等。
你的回答语言要简洁、严谨、专业。遇到无法解答的问题，建议用户联系安全专业机构或查阅具体法规标准。
"""

# 聊天机器人消息逻辑
def create_chat_messages(instruction, image_base64, context):
    return [
        {"role": "system", "content": instruction},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"你是安全隐患识别专家，请详细描述一下图片中存在哪些安全生产隐患？背景信息和需求如下：{context}"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_base64
                    }
                },
            ]
        },
    ]

# 创建聊天完成请求
def get_chat_completion(client, model, messages):
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"发生错误: {e}"

# 隐患识别函数
def identify_hazards(image_path, context):
    # 将图片编码为 Base64
    image_base64 = encode_image_to_base64(image_path)
    
    # 创建聊天消息
    messages = create_chat_messages(SYSTEM_INSTRUCTION, image_base64, context)
    
    # 获取聊天完成结果
    result = get_chat_completion(client, "yi-vision-v2", messages)
    
    # 将结果存储到数据库
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO hazard_results (image_path, context, result) VALUES (%s, %s, %s)",
        (image_path, context, result)
    )
    conn.commit()
    cur.close()
    conn.close()
    
    return result

# Gradio 界面
iface = gr.Interface(
    fn=identify_hazards,
    inputs=[
        gr.Image(type="filepath", label="上传图片"),
        gr.Textbox(label="背景信息和需求（非必填）", lines=3, placeholder="请输入图片的背景信息")
    ],
    outputs=gr.Textbox(label="隐患识别结果"),
    title="小安：安全隐患识别",
    description="请上传图片并输入背景信息进行安全生产隐患识别",
)

# 启动 Gradio 应用
iface.launch()
