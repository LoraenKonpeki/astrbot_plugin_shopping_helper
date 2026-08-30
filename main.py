from __future__ import annotations

from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

try:
    from .service import ShoppingService, format_products, products_as_dicts
    from .providers.jd_union import JdUnionError
except ImportError:
    from service import ShoppingService, format_products, products_as_dicts
    from providers.jd_union import JdUnionError


@register("shopping_helper", "Loraen_Konpeki", "京东联盟商品搜索与比价助手", "0.1.0")
class ShoppingHelperPlugin(Star):
    def __init__(self, context: Context, config=None):
        super().__init__(context)
        self.service = ShoppingService(config or {})

    @filter.command_group("购", alias={"shopping", "shop"})
    def shopping(self, event: AstrMessageEvent):
        pass

    @shopping.command("搜", alias={"search", "s"})
    async def search_command(self, event: AstrMessageEvent, keyword: str = ""):
        if not keyword.strip():
            yield event.plain_result("用法：/购 搜 <商品关键词>，例如：/购 搜 静音机械键盘")
            return
        try:
            products = await self.service.search(keyword)
            yield event.plain_result(format_products(products))
        except JdUnionError as exc:
            yield event.plain_result(str(exc))

    @shopping.command("帮助", alias={"help", "h"})
    async def help_command(self, event: AstrMessageEvent):
        yield event.plain_result("/购 搜 <关键词>\n例如：/购 搜 机械键盘\n\n需要在插件配置中填入京东联盟 App Key 与 App Secret。")

    @filter.llm_tool(name="shopping_search")
    async def shopping_search(self, event, keyword: str, platform: str = "jd", limit: int = 8):
        """通过官方联盟接口搜索电商商品。只返回接口实际返回的价格、优惠和链接；可用于按关键词、预算或使用场景推荐商品。

        Args:
            keyword(string): 商品关键词，应包含用户明确的品类、用途、预算或关键规格；例如“静音机械键盘 300元以内”。
            platform(string): 数据平台。首版只支持 jd；填写 all 等价于已启用来源的合并搜索。
            limit(number): 最多返回几件商品，默认 8，最大 20。
        """
        try:
            products = await self.service.search(keyword, platform, limit)
            return {"products": products_as_dicts(products), "source_note": "价格、优惠和库存可能变化，请以打开链接后的页面为准。"}
        except JdUnionError as exc:
            return {"error": str(exc)}
