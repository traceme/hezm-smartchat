import pytest
import json
from unittest.mock import patch, MagicMock
import requests

# 获取文本嵌入的辅助函数
def _get_embedding(text: str, model: str = "Qwen3-Embedding-8B"):
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

def test_get_embedding_success():
    """测试成功获取嵌入"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [{"embedding": [0.1, 0.2, 0.3]}],
        "model": "Qwen3-Embedding-8B",
        "usage": {"prompt_tokens": 5, "total_tokens": 5}
    }

    with patch('requests.post', return_value=mock_response) as mock_post:
        text = "这是一个测试文本"
        embedding = _get_embedding(text)
        
        mock_post.assert_called_once_with(
            "http://10.2.0.16:8085/v1/embeddings",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "model": "Qwen3-Embedding-8B",
                "input": text,
                "encoding_format": "float"
            })
        )
        assert embedding == [0.1, 0.2, 0.3]
        assert len(embedding) == 3

def test_get_embedding_api_error():
    """测试嵌入API返回错误"""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch('requests.post', return_value=mock_response) as mock_post:
        text = "这是一个测试文本"
        embedding = _get_embedding(text)
        
        mock_post.assert_called_once()
        assert embedding is None

def test_get_embedding_empty_text():
    """测试空文本输入"""
    # 对于空文本，_get_embedding 应该返回 None 或抛出错误，取决于实际实现
    # 在当前 _get_embedding 实现中，它会发送请求，然后返回 None
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [{"embedding": []}], # 假设空文本返回空嵌入列表
        "model": "Qwen3-Embedding-8B",
        "usage": {"prompt_tokens": 0, "total_tokens": 0}
    }
    with patch('requests.post', return_value=mock_response) as mock_post:
        text = ""
        embedding = _get_embedding(text)
        mock_post.assert_called_once()
        assert embedding == [] # 根据假设，空文本返回空列表