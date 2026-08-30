from __future__ import annotations

import asyncio
import time
from dataclasses import asdict

try:
    from .models import Product
    from .providers.jd_union import JdUnionError, JdUnionProvider
except ImportError:
    from models import Product
    from providers.jd_union import JdUnionError, JdUnionProvider


class ShoppingService:
    def __init__(self, config: dict):
        self.config = dict(config or {})
        self.max_results = max(1, min(20, int(self.config.get("max_results", 8))))
        self.cache_ttl = max(0, int(self.config.get("cache_ttl_seconds", 300)))
        self._cache: dict[tuple[str, str], tuple[float, list[Product]]] = {}
        self.providers = self._build_providers()

    def _build_providers(self) -> dict[str, JdUnionProvider]:
        enabled = {str(value).lower() for value in self.config.get("enabled_platforms", ["jd"])}
        providers = {}
        if "jd" in enabled:
            providers["jd"] = JdUnionProvider(
                str(self.config.get("jd_app_key", "")),
                str(self.config.get("jd_app_secret", "")),
                str(self.config.get("jd_access_token", "")),
                int(self.config.get("request_timeout_seconds", 12)),
            )
        return providers

    async def search(self, keyword: str, platform: str = "jd", limit: int | None = None) -> list[Product]:
        platform = platform.lower().strip() or "jd"
        if platform == "all":
            platforms = list(self.providers)
        else:
            platforms = [platform]
        selected = [self.providers[name] for name in platforms if name in self.providers]
        if not selected:
            raise JdUnionError("未启用平台 `%s`。当前首版只支持 jd。" % platform)

        count = max(1, min(self.max_results, int(limit or self.max_results)))
        results = await asyncio.gather(*(self._search_one(provider, keyword, count) for provider in selected))
        return [product for group in results for product in group][:count]

    async def _search_one(self, provider: JdUnionProvider, keyword: str, limit: int) -> list[Product]:
        key = (provider.platform, keyword.strip().lower())
        cached = self._cache.get(key)
        if cached and time.monotonic() - cached[0] < self.cache_ttl:
            return cached[1][:limit]
        products = await asyncio.to_thread(provider.search, keyword, limit)
        self._cache[key] = (time.monotonic(), products)
        return products


def format_products(products: list[Product]) -> str:
    if not products:
        return "没有找到匹配商品。"
    chunks = []
    for index, product in enumerate(products, 1):
        price = "¥%s" % product.price if product.price else "价格未返回"
        detail = ["%d. [%s] %s" % (index, product.platform.upper(), product.title), "价格：%s" % price]
        if product.coupon:
            detail.append("优惠：%s" % product.coupon)
        if product.shop_name:
            detail.append("店铺：%s" % product.shop_name)
        if product.comments is not None:
            detail.append("评价：%s" % product.comments)
        if product.url:
            detail.append("链接：%s" % product.url)
        chunks.append("\n".join(detail))
    return "\n\n".join(chunks)


def products_as_dicts(products: list[Product]) -> list[dict]:
    return [asdict(product) for product in products]
