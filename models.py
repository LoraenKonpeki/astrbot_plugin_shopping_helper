from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    platform: str
    item_id: str
    title: str
    price: str | None = None
    original_price: str | None = None
    coupon: str | None = None
    shop_name: str | None = None
    url: str | None = None
    image_url: str | None = None
    comments: int | None = None
