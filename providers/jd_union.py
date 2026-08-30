from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    from ..models import Product
except ImportError:
    from models import Product


JOS_URL = "https://api.jd.com/routerjson"


class JdUnionError(RuntimeError):
    pass


class JdUnionProvider:
    """Small client for the official JD Union JOS API."""

    platform = "jd"

    def __init__(self, app_key: str, app_secret: str, access_token: str = "", timeout: int = 12):
        self.app_key = app_key.strip()
        self.app_secret = app_secret.strip()
        self.access_token = access_token.strip()
        self.timeout = max(1, int(timeout))

    @property
    def configured(self) -> bool:
        return bool(self.app_key and self.app_secret)

    def search(self, keyword: str, page_size: int = 8) -> list[Product]:
        keyword = keyword.strip()
        if not keyword:
            raise JdUnionError("请输入商品关键词。")
        if not self.configured:
            raise JdUnionError("京东联盟尚未配置 jd_app_key 和 jd_app_secret。")

        payload = {
            "goodsReq": {
                "keyword": keyword,
                "pageIndex": 1,
                "pageSize": max(1, min(20, int(page_size))),
                "sortName": "price",
                "sort": "asc",
            }
        }
        response = self._request("jd.union.open.goods.query", payload)
        return _parse_products(response)

    def _request(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        params = {
            "method": method,
            "app_key": self.app_key,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "format": "json",
            "v": "1.0",
            "360buy_param_json": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        }
        if self.access_token:
            params["access_token"] = self.access_token
        params["sign"] = make_sign(params, self.app_secret)
        request = Request(JOS_URL, data=urlencode(params).encode(), method="POST")
        request.add_header("Content-Type", "application/x-www-form-urlencoded")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise JdUnionError("京东联盟请求失败：%s" % exc) from exc
        if "error_response" in body:
            message = body["error_response"].get("zh_desc") or body["error_response"].get("en_desc") or "未知错误"
            raise JdUnionError("京东联盟接口返回错误：%s" % message)
        return body


def make_sign(params: dict[str, str], secret: str) -> str:
    source = secret + "".join("%s%s" % (key, params[key]) for key in sorted(params)) + secret
    return hashlib.md5(source.encode("utf-8")).hexdigest().upper()


def _parse_products(body: dict[str, Any]) -> list[Product]:
    response = next((value for key, value in body.items() if key.endswith("_responce") or key.endswith("_response")), {})
    result = response.get("result", {}) if isinstance(response, dict) else {}
    if isinstance(result, str):
        result = json.loads(result)
    data = result.get("data", []) if isinstance(result, dict) else []
    return [_parse_product(item) for item in data if isinstance(item, dict)]


def _parse_product(item: dict[str, Any]) -> Product:
    price_info = item.get("priceInfo") or {}
    coupon_list = (item.get("couponInfo") or {}).get("couponList") or []
    coupon = None
    if coupon_list:
        first = coupon_list[0]
        coupon = "满%s减%s" % (first.get("quota"), first.get("discount"))
    images = (item.get("imageInfo") or {}).get("imageList") or []
    return Product(
        platform="jd",
        item_id=str(item.get("skuId") or ""),
        title=str(item.get("skuName") or "未命名商品"),
        price=_string_or_none(price_info.get("price")),
        original_price=_string_or_none(price_info.get("originalPrice")),
        coupon=coupon,
        shop_name=_string_or_none((item.get("shopInfo") or {}).get("shopName")),
        url=_string_or_none(item.get("materialUrl")),
        image_url=_string_or_none((images[0] or {}).get("url")) if images else None,
        comments=_int_or_none(item.get("comments")),
    )


def _string_or_none(value: Any) -> str | None:
    return str(value) if value is not None and value != "" else None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
