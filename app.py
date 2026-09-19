"""可选 Web UI（Streamlit）。

启动（需先安装 streamlit）：
    streamlit run app.py

页面展示：问题输入框、答案、Evidence、Source、Confidence。
Text 与 Table 证据分开展示。
"""
from __future__ import annotations

import sys
from pathlib import Path

# 确保可以导入 src 包
sys.path.insert(0, str(Path(__file__).resolve().parent))


def get_pipeline():
    from src.indexer import Indexer
    from src.qa.pipeline import Pipeline

    indexer = Indexer()
    retriever, table_engine, _ = indexer.build()
    return Pipeline(retriever, table_engine)


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="可信 RAG 问答系统", layout="wide")
    st.title("面向监管制度与统计报表的可信 RAG 问答系统")

    @st.cache_resource
    def load_pipeline():
        return get_pipeline()

    pipeline = load_pipeline()
    question = st.text_input("请输入问题", placeholder="例如：2024年一季度商业银行营业收入是多少亿元？")

    if question:
        res = pipeline.answer(question)
        st.subheader("答案")
        st.markdown(f"**{res.answer}**")
        st.caption(f"类型：{res.question_type} | 置信度：{res.confidence:.3f} | 状态：{res.status}")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Evidence（证据）")
            for i, ev in enumerate(res.evidence, 1):
                if "indicator" in ev:
                    st.markdown(f"**证据 {i}（表格）**")
                    st.markdown(
                        f"- 指标：{ev.get('indicator','')}\n- 期间：{ev.get('period','')}\n"
                        f"- 值：{ev.get('value','')}\n- 单位：{ev.get('unit','')}"
                    )
                else:
                    st.markdown(f"**证据 {i}**\n\n{ev.get('text','')}")
        with col2:
            st.subheader("Source（来源）")
            for i, src in enumerate(res.sources, 1):
                if "cell" in src:
                    st.markdown(f"**来源 {i}**\n\n{src.get('source_file','')} | Sheet: {src.get('sheet','')} | Cell: {src.get('cell','')}")
                else:
                    parts = [src.get("source_file", "")]
                    if src.get("page") is not None:
                        parts.append(f"Page: {src.get('page')}")
                    if src.get("article"):
                        parts.append(f"Article: {src.get('article')}")
                    if src.get("section"):
                        parts.append(f"Section: {src.get('section')}")
                    st.markdown(f"**来源 {i}**\n\n{' | '.join(parts)}")


if __name__ == "__main__":
    main()
