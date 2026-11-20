"""English-to-Chinese evidence translation through the local Hy-MT2 server."""

import http.client
import json
import re


MODEL = "Hy-MT2-1.8B-Q4_K_M"
DEFAULT_PORT = 8088
MAX_EXCERPT = 2400
MAX_TRANSLATION = 4000
GLOSSARY = {
    "garden variety": "园艺品种",
    "double flower": "重瓣花",
    "Galanthus nivalis": "Galanthus nivalis",
    "dwarf sunflower": "矮秆向日葵",
    "tall sunflower": "高秆向日葵",
    "Sunflower, Dwarf": "矮秆向日葵",
    "Sunflower, Tall": "高秆向日葵",
    "Haughtiness": "傲慢",
}


class TranslationError(RuntimeError):
    pass


def translate(excerpt, port=DEFAULT_PORT):
    if not excerpt.strip() or len(excerpt) > MAX_EXCERPT:
        raise TranslationError(f"请选择不超过 {MAX_EXCERPT} 字符的原文摘录。")
    terms = [f"{original} 翻译成 {target}" for original, target in GLOSSARY.items()
             if original.casefold() in excerpt.casefold()]
    if re.search(r"Sunflower, Dwarf\s*[—–-]\s*Adoration", excerpt, re.IGNORECASE):
        terms.append("Adoration 翻译成 爱慕")
    glossary = ("参考下面的翻译：\n" + "\n".join(terms) + "\n") if terms else ""
    prompt = glossary + "将以下文本翻译为简体中文，注意只需要输出翻译后的结果，不要额外解释：\n" + excerpt
    body = json.dumps({
        "model": MODEL, "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7, "top_p": 0.6, "top_k": 20, "repeat_penalty": 1.05,
        "max_tokens": 1500, "stream": False, "seed": 42,
    }).encode("utf-8")
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=120)
    try:
        connection.request("POST", "/v1/chat/completions", body, {"Content-Type": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            raise TranslationError("本机翻译服务未能完成翻译，请检查 Hy-MT2 是否已加载。")
        data = json.loads(response.read(131072))
        choice = data["choices"][0]
        result = choice["message"]["content"].strip()
        if (data.get("model") != MODEL or choice["finish_reason"] != "stop"
                or len(result) > MAX_TRANSLATION or not re.search(r"[\u3400-\u9fff]", result)):
            raise TranslationError("译文为空、不完整或模型不匹配，请检查本机翻译服务。")
        return result
    except (OSError, http.client.HTTPException, ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        raise TranslationError("本机翻译服务暂不可用，请确认 Hy-MT2 已启动。") from exc
    finally:
        connection.close()
