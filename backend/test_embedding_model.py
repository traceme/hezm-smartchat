import requests
import json

# 获取文本嵌入
def get_embedding(text, model="Qwen3-Embedding-8B"):
    url = "http://10.2.0.16:8085/v1/embeddings"
    
    headers = {
        "Content-Type": "application/json",
    }
    
    data = {
        "model": model,
        "input": text,
        "encoding_format": "float"
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        result = response.json()
        return result['data'][0]['embedding']
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None

# 使用示例
text = "这是一个测试文本"
embedding = get_embedding(text)
print(f"Embedding dimension: {len(embedding)}")