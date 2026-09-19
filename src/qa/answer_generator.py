"""答案生成器。

设计原则：
- 定义 ``LLMProvider`` 统一接口（generate(question, evidence, ...)）；
- ``RuleBasedProvider`` 为默认实现：基于检索证据做抽取式回答，无需任何 API；
- ``OptionalLLMProvider`` 仅当环境变量配置了模型时才启用（从环境读取密钥，
  绝不硬编码）；未配置时系统仍可完整运行。
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Any

from ..utils.logging import get_logger

log = get_logger("answer_generator")

# 用于抽取式回答的句子切分
_SENT_SPLIT = re.compile(r"[。；！？!?；\n]")


def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENT_SPLIT.split(text) if p.strip()]
    return parts


class LLMProvider:
    """统一 LLM 接口。"""

    name = "base"

    def generate(self, question: str, evidence: list[dict[str, Any]], question_type: str = "text") -> str:
        raise NotImplementedError


class RuleBasedProvider(LLMProvider):
    """基于证据的抽取式回答（默认，无外部依赖）。

    文本题：从检索到的证据中挑选与问题最相关的句子作为答案；
    多事实题（含"分别/两者"）返回前两条证据的句子，覆盖多个数值。
    """

    name = "rule-based"

    def generate(self, question: str, evidence: list[dict[str, Any]], question_type: str = "text") -> str:
        if question_type == "table":
            return ""  # 表格答案由 TableEngine 直接产出
        if not evidence:
            return "未找到足够证据"

        texts = [e.get("text", "") for e in evidence if e.get("text")]
        if not texts:
            return "未找到足够证据"

        multi = ("分别" in question) or ("两者" in question) or (
            "和" in question and ("多少" in question or "什么" in question)
        )
        n = 2 if multi else 1
        top_sentences: list[str] = []
        for text in texts[: n + 1]:
            sents = split_sentences(text)
            if sents:
                top_sentences.append(self._best_sentence(question, sents))
            if len(top_sentences) >= n:
                break

        if not top_sentences:
            return texts[0][:200]
        return "；".join(dict.fromkeys(top_sentences))  # 去重且保持顺序

    @staticmethod
    def _best_sentence(question: str, sentences: list[str]) -> str:
        """在句子中挑选与问题关键词重叠最多、且包含数字（当问题问数值时）的一句。"""
        q_words = _content_words(question)
        asks_number = any(w in question for w in ("多少", "比例", "期限", "几年", "几日", "何时", "多长"))
        best, best_score = sentences[0], -1.0
        for s in sentences:
            score = sum(1 for w in q_words if w in s)
            if asks_number and re.search(r"\d", s):
                score += 2.0
            # 更短的句子信息更聚焦，轻微加权
            score -= len(s) / 1000.0
            if score > best_score:
                best, best_score = s, score
        return best


class OptionalLLMProvider(LLMProvider):
    """可选 LLM：仅当环境配置了 OPENAI_API_KEY 时启用。

    使用标准库 urllib 调用 OpenAI 兼容接口，避免引入额外依赖。
    密钥仅从环境变量读取，不写入任何代码或提交材料。
    """

    name = "optional-llm"

    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        self.base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip()

    def enabled(self) -> bool:
        return bool(self.api_key)

    def generate(self, question: str, evidence: list[dict[str, Any]], question_type: str = "text") -> str:
        if not self.enabled():
            return ""
        system = (
            "你是一个基于证据回答问题的助手。你只能根据提供的 Evidence 回答。"
            "不得根据常识补充 Evidence 中不存在的事实。如果 Evidence 不足以支持答案，"
            '请回答"未找到足够证据"。涉及数字、日期、比例、金额、期限时必须严格引用'
            " Evidence 中的值，不要擅自修改单位。"
        )
        ev_text = "\n".join(
            f"[{i+1}] {e.get('text','')} (来源: {json.dumps(e.get('source', {}), ensure_ascii=False)})"
            for i, e in enumerate(evidence)
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": f"问题：{question}\n\nEvidence:\n{ev_text}"},
            ],
            "temperature": 0,
        }
        try:
            req = urllib.request.Request(
                f"{self.base_url.rstrip('/')}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:  # noqa: BLE001
            log.warning("LLM 调用失败，回退规则回答：%s", e)
            return ""


def get_provider() -> LLMProvider:
    """按环境配置返回答案生成器；未配置 LLM 时使用规则抽取式。"""
    llm = OptionalLLMProvider()
    if llm.enabled():
        return llm
    return RuleBasedProvider()


def _content_words(text: str) -> list[str]:
    """提取中文内容词（过滤停用词/虚词）。"""
    import jieba

    stop = {
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
        "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你",
        "会", "着", "没有", "看", "好", "自己", "这", "那", "多少", "什么",
        "哪些", "请", "问", "吗", "呢", "啊", "应", "该", "对于", "其中",
    }
    words = [w.strip() for w in jieba.lcut(text) if w.strip()]
    return [w for w in words if w not in stop and len(w) >= 2]
