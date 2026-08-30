from models import Product
from service import format_products


def test_format_products_includes_only_available_fields():
    text = format_products([Product(platform="jd", item_id="1", title="Keyboard", price="99", url="https://example.com")])
    assert "[JD] Keyboard" in text
    assert "价格：¥99" in text
    assert "链接：https://example.com" in text
