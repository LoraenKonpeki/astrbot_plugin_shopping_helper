import hashlib

from providers.jd_union import _parse_products, make_sign


def test_jos_signature_is_sorted_and_uppercase():
    params = {"b": "2", "a": "1"}
    expected = hashlib.md5(b"secreta1b2secret").hexdigest().upper()
    assert make_sign(params, "secret") == expected


def test_parse_jd_response_result_string():
    body = {
        "jd_union_open_goods_query_responce": {
            "result": '{"data":[{"skuId":123,"skuName":"Keyboard","materialUrl":"https://item.jd.com/123.html","priceInfo":{"price":99.9,"originalPrice":129.9},"couponInfo":{"couponList":[{"quota":100,"discount":10}]},"shopInfo":{"shopName":"JD Shop"},"imageInfo":{"imageList":[{"url":"https://img.example/1.jpg"}]},"comments":42}]}'
        }
    }
    products = _parse_products(body)
    assert len(products) == 1
    assert products[0].item_id == "123"
    assert products[0].price == "99.9"
    assert products[0].coupon == "满100减10"
    assert products[0].shop_name == "JD Shop"
