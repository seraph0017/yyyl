"""
HTML 安全过滤工具
使用 nh3 库对富文本内容进行 sanitize
"""

import nh3

# 白名单标签
ALLOWED_TAGS = {
    "p", "br", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "a", "img", "strong", "em", "span", "div",
    "table", "thead", "tbody", "tr", "td", "th",
    "blockquote", "pre", "code",
}

# 允许的属性
ALLOWED_ATTRIBUTES = {
    "a": {"href", "target", "rel"},
    "img": {"src", "alt", "width", "height"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
    "span": {"style"},
    "div": {"style"},
}

# 允许的 URL 协议
ALLOWED_URL_SCHEMES = {"http", "https"}


def sanitize_html(html: str) -> str:
    """过滤 HTML 内容，移除危险标签和属性"""
    return nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_URL_SCHEMES,
        link_rel="noopener noreferrer",
    )


def sanitize_cms_config(config: dict) -> dict:
    """遍历 CMS 配置 JSON，对所有 rich_text 组件的内容进行 sanitize"""
    if not config or "components" not in config:
        return config

    import copy
    sanitized = copy.deepcopy(config)

    for comp in sanitized.get("components", []):
        if comp.get("type") == "rich_text":
            html_content = comp.get("props", {}).get("content", "")
            if html_content:
                # 长度校验：50KB
                if len(html_content.encode("utf-8")) > 50 * 1024:
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=413,
                        detail={"code": "CMS_RICHTEXT_TOO_LARGE", "message": "富文本内容超过50KB限制"},
                    )
                comp["props"]["content"] = sanitize_html(html_content)

    return sanitized
