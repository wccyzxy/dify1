import os
from urllib.parse import urlparse
import requests
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class LinyanService:
    def __init__(self):
        self.url = os.getenv("LINYAN_URL", "")
        self.base_url = urlparse(self.url).scheme + "://" + urlparse(self.url).netloc
        self.headers = {
            "Content-Type": "application/json",
            "X-SS-API-KEY": os.getenv("LINYAN_API_KEY", "")
        }

    def query_fagui(self, query):
        payload = {
            "siteId": 135,
            "wheres": [
                {
                    "column": "ChannelId",
                    "operator": "=",
                    "value": "1307"
                },
                {
                    "column": "title",
                    "operator": "Like",
                    "value": f"%{query}%"
                }
            ],
            "page": "1",
            "orders": [
                {
                    "column": "EffectiveDate",
                    "desc": True
                }
            ],
            "perPage": 20
        }
        response = requests.post(self.url, headers=self.headers, json=payload)
        contents = response.json().get("contents", [])
        result = []
        for content in contents:
            result.append({
                "url": self.base_url + content.get("navigationUrl", ""),
                "title": content.get("title", "")
            })
        return result

