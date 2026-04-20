"""
hitokoto — 一言 daily quote (https://developer.hitokoto.cn/).

Free API, no key required. Designed for Chinese-language briefings.
Sentence type can be set via config: a=动画 b=漫画 c=游戏 d=文学 e=原创 f=来自网络 g=其他 h=影视 i=诗词 j=网易云 k=哲学 l=抖机灵
"""

import requests

from extensions.base import BaseExtension, FeedSection


class HitokotoExtension(BaseExtension):
    key = "hitokoto"
    title = "一言"
    icon = "✦"

    def fetch(self) -> list[dict]:
        sentence_type = self.config.get("type", "")
        params: dict = {}
        if sentence_type:
            params["c"] = sentence_type

        try:
            resp = requests.get(
                "https://v1.hitokoto.cn/",
                params=params,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return [
                {
                    "quote": data.get("hitokoto", ""),
                    "author": data.get("from_who") or data.get("from", ""),
                    "source": data.get("from", ""),
                    "category": data.get("type", ""),
                }
            ]
        except Exception as exc:
            print(f"  {self.title}: fetch failed — {exc}")
        return []

    def render(self, items: list[dict]) -> FeedSection:
        return self.build_section(items=items, meta={"count": len(items)})
