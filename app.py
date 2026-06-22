"""MeMi: a simple Streamlit MVP for cleaning meeting transcripts."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import re
import time

import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI, OpenAIError

from prompts import OUTPUT_TYPES, QA_OUTPUT_TYPE, build_prompt


# Page configuration must be the first Streamlit command in the app.
st.set_page_config(page_title="MeMi", page_icon="📝", layout="centered")

# MeMi's visual system: warm white, blue-violet glow, and soft white cards.
st.markdown(
    """
    <style>
    :root {
        --memi-blue: #2f8ff5;
        --memi-blue-dark: #1979dd;
        --memi-ink: #202536;
        --memi-muted: #6f7585;
        --memi-line: rgba(47, 143, 245, 0.14);
        --memi-card: rgba(255, 255, 255, 0.92);
    }

    .stApp {
        background:
            radial-gradient(circle at 12% 4%, rgba(111, 179, 255, 0.20), transparent 26rem),
            radial-gradient(circle at 88% 2%, rgba(170, 139, 255, 0.16), transparent 24rem),
            linear-gradient(180deg, #fffefa 0%, #fffdf9 58%, #fffaf4 100%);
        color: var(--memi-ink);
    }

    /* Let the page gradient continue behind Streamlit's fixed toolbar. */
    header[data-testid="stHeader"],
    div[data-testid="stToolbar"] {
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
    }

    header[data-testid="stHeader"]::before,
    header[data-testid="stHeader"]::after {
        display: none !important;
    }

    [data-testid="stAppViewContainer"] > .main {
        background: transparent;
    }

    .block-container {
        max-width: 860px;
        padding-top: 2.4rem;
        padding-bottom: 5rem;
    }

    .memi-hero {
        position: relative;
        display: flex;
        align-items: center;
        gap: 1.15rem;
        margin-bottom: 1.5rem;
        padding: 0.4rem 0.2rem 0.65rem;
    }

    .memi-logo {
        display: grid;
        place-items: center;
        width: 68px;
        height: 68px;
        flex: 0 0 68px;
        border: 1px solid rgba(255, 255, 255, 0.72);
        border-radius: 22px;
        background: linear-gradient(145deg, #79c4ff 0%, #398ff6 48%, #806cf5 100%);
        color: white;
        font-size: 1.45rem;
        font-weight: 800;
        letter-spacing: -0.08em;
        box-shadow: 0 16px 36px rgba(57, 143, 246, 0.28);
        transform: rotate(-3deg);
    }

    .memi-eyebrow {
        display: inline-flex;
        align-items: center;
        margin-bottom: 0.25rem;
        padding: 0.22rem 0.6rem;
        border: 1px solid rgba(47, 143, 245, 0.16);
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.68);
        color: #397fc7;
        font-size: 0.68rem;
        font-weight: 750;
        letter-spacing: 0.13em;
    }

    .memi-hero h1 {
        margin: 0;
        color: var(--memi-ink);
        font-size: clamp(2.35rem, 7vw, 3.4rem);
        line-height: 1;
        letter-spacing: -0.055em;
    }

    .memi-hero p {
        margin: 0.45rem 0 0;
        color: var(--memi-muted);
        font-size: 0.98rem;
    }

    div[data-testid="stForm"] {
        padding: 1.5rem 1.6rem 1.7rem;
        border: 1px solid rgba(47, 143, 245, 0.13);
        border-radius: 24px;
        background: var(--memi-card);
        box-shadow: 0 22px 70px rgba(57, 86, 128, 0.10);
        backdrop-filter: blur(16px);
    }

    div[data-testid="stForm"] h3,
    div[data-testid="stVerticalBlockBorderWrapper"] h3 {
        margin-top: 0.25rem;
        color: var(--memi-ink);
        font-size: 1.18rem;
        letter-spacing: -0.02em;
    }

    .output-format-help {
        margin: -0.2rem 0 0.9rem;
        padding: 0 0.15rem;
        color: #858b98;
        font-size: 0.82rem;
        line-height: 1.65;
    }

    .output-format-help .example {
        color: #9aa0ac;
    }

    .stTextInput input,
    .stDateInput input,
    .stTextArea textarea,
    div[data-baseweb="select"] > div {
        border-color: rgba(47, 143, 245, 0.13) !important;
        border-radius: 12px !important;
        background: #ffffff !important;
        box-shadow: 0 2px 10px rgba(50, 77, 113, 0.04) !important;
    }

    .stTextInput input:focus,
    .stDateInput input:focus,
    .stTextArea textarea:focus {
        border-color: rgba(47, 143, 245, 0.50) !important;
        box-shadow: 0 0 0 3px rgba(47, 143, 245, 0.10) !important;
    }

    div[data-testid="stFileUploaderDropzone"] {
        border: 1px dashed rgba(47, 143, 245, 0.30);
        border-radius: 16px;
        background: linear-gradient(135deg, rgba(242, 249, 255, 0.96), rgba(249, 247, 255, 0.96));
    }

    details {
        border: 1px solid rgba(47, 143, 245, 0.13) !important;
        border-radius: 14px !important;
        background: rgba(249, 252, 255, 0.72) !important;
    }

    div[data-testid="stAlert"] {
        border-radius: 14px;
    }

    div[data-testid="stFormSubmitButton"] {
        display: flex;
        justify-content: center;
        padding-top: 0.8rem;
    }

    /* Streamlit shrink-wraps submit-button containers to the button width.
       Expand that outer container first so centering affects the whole form. */
    div[data-testid="stElementContainer"]:has(
        button[data-testid="stBaseButton-primaryFormSubmit"]
    ) {
        display: flex;
        justify-content: center;
        width: 100% !important;
    }

    div[data-testid="stFormSubmitButton"] button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 180px;
        min-height: 44px;
        border: none;
        border-radius: 999px;
        background: linear-gradient(135deg, #35a0ff 0%, #2f8ff5 62%, #5879ef 100%);
        color: #ffffff;
        font-weight: 600;
        box-shadow: 0 10px 24px rgba(47, 143, 245, 0.28);
        transition: box-shadow 0.15s ease, transform 0.15s ease;
    }

    div[data-testid="stFormSubmitButton"] button:hover {
        border: none;
        background: linear-gradient(135deg, #2d97f5 0%, #247fdc 65%, #4f6de3 100%);
        color: #ffffff;
        transform: translateY(-1px);
        box-shadow: 0 13px 28px rgba(47, 143, 245, 0.34);
    }

    div[data-testid="stFormSubmitButton"] button:focus {
        border: none;
        background: #2f9bff;
        color: #ffffff;
        box-shadow: 0 0 0 3px rgba(47, 155, 255, 0.22);
    }

    div[data-testid="stFormSubmitButton"] button p {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        margin: 0;
        text-align: center;
    }

    /* The main Generate button is outside a form so dropdown help can update
       immediately. Give it the same centered pill styling. */
    div[data-testid="stElementContainer"]:has(
        button[data-testid="stBaseButton-primary"]
    ) {
        display: flex;
        justify-content: center;
        width: 100% !important;
        padding-top: 0.8rem;
    }

    button[data-testid="stBaseButton-primary"] {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 180px;
        min-height: 44px;
        border: none;
        border-radius: 999px;
        background: linear-gradient(135deg, #35a0ff 0%, #2f8ff5 62%, #5879ef 100%);
        color: #ffffff;
        font-weight: 600;
        box-shadow: 0 10px 24px rgba(47, 143, 245, 0.28);
        transition: box-shadow 0.15s ease, transform 0.15s ease;
    }

    button[data-testid="stBaseButton-primary"]:hover {
        border: none;
        background: linear-gradient(135deg, #2d97f5 0%, #247fdc 65%, #4f6de3 100%);
        color: #ffffff;
        transform: translateY(-1px);
        box-shadow: 0 13px 28px rgba(47, 143, 245, 0.34);
    }

    button[data-testid="stBaseButton-primary"] p {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        margin: 0;
        text-align: center;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: rgba(47, 143, 245, 0.13) !important;
        border-radius: 20px !important;
        background: rgba(255, 255, 255, 0.94);
        box-shadow: 0 18px 55px rgba(57, 86, 128, 0.08);
    }

    div[data-testid="stDownloadButton"] button {
        min-height: 42px;
        border: 1px solid rgba(47, 143, 245, 0.25);
        border-radius: 12px;
        background: #ffffff;
        color: #247fdc;
        font-weight: 650;
    }

    div[data-testid="stDownloadButton"] button:hover {
        border-color: #2f8ff5;
        background: #f4f9ff;
        color: #1979dd;
    }

    /* Replace Streamlit's tiny running indicator with MeMi's own status card. */
    div[data-testid="stStatusWidget"] {
        visibility: hidden;
    }

    .memi-thinking {
        position: fixed;
        top: 4.25rem;
        right: 1.5rem;
        z-index: 999999;
        padding: 0.7rem 1rem;
        border: 1px solid rgba(47, 155, 255, 0.22);
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.96);
        color: #1677d2;
        font-size: 0.9rem;
        font-weight: 600;
        box-shadow: 0 8px 24px rgba(24, 119, 210, 0.14);
        animation: memi-float 1.6s ease-in-out infinite;
    }

    .memi-thinking::before {
        content: "✨";
        display: inline-block;
        margin-right: 0.45rem;
        animation: memi-spin 1.8s linear infinite;
    }

    @keyframes memi-float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-4px); }
    }

    @keyframes memi-spin {
        0% { transform: rotate(0deg) scale(1); }
        50% { transform: rotate(180deg) scale(1.18); }
        100% { transform: rotate(360deg) scale(1); }
    }

    @media (max-width: 640px) {
        .block-container {
            padding-top: 1.4rem;
        }

        .memi-logo {
            width: 58px;
            height: 58px;
            flex-basis: 58px;
            border-radius: 18px;
        }

        div[data-testid="stForm"] {
            padding: 1.1rem 1rem 1.35rem;
            border-radius: 20px;
        }

        .memi-thinking {
            top: 3.5rem;
            right: 0.75rem;
            max-width: calc(100vw - 1.5rem);
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def read_uploaded_text(uploaded_file) -> str:
    """Read a UTF-8 .txt upload and return its text.

    utf-8-sig also handles files saved with a UTF-8 byte order mark (BOM).
    """

    return uploaded_file.getvalue().decode("utf-8-sig")


def generate_mock_notes(
    transcript: str,
    output_type: str,
    company_name: str,
    main_business: str,
    discussion_topics: str,
    meeting_date: str,
    interviewer: str,
) -> str:
    """Return a short demo result when no OpenAI API key is available."""

    company = company_name.strip() or "未提供公司名称"
    business = main_business.strip() or "未提供主营业务"
    topics = discussion_topics.strip() or "未提供讨论主题"
    header = (
        f"时间：{meeting_date.strip() or '未提供'}\n"
        f"采访人：{interviewer.strip() or '未提供'}\n"
        f"会议主题：{discussion_topics.strip() or '未提供'}\n\n"
    )
    preview = " ".join(transcript.split())[:240]
    if len(" ".join(transcript.split())) > 240:
        preview += "…"

    if output_type == QA_OUTPUT_TYPE:
        return header + (
            f"# {company} 会议纪要（演示输出）\n\n"
            "## Q&A\n\n"
            "### Q1：公司的主营业务是什么？\n\n"
            f"公司的主营业务为{business}。\n\n"
            "### Q2：本次会议讨论了哪些主题？\n\n"
            f"会议围绕{topics}展开。原始记录片段：{preview}\n\n"
            "> 这是本地 mock 输出。接入 AI API 后，将按完整提示词清理全文。"
        )

    return header + (
        f"# {company} 会议纪要（演示输出）\n\n"
        f"- **主营业务：** {business}\n"
        f"- **讨论主题：** {topics}\n"
        f"- **记录预览：** {preview}\n\n"
        "> 这是本地 mock 输出。接入 AI API 后，将按完整提示词生成全文摘要。"
    )


def generate_notes(
    transcript: str,
    output_type: str,
    company_name: str,
    main_business: str,
    discussion_topics: str,
    meeting_date: str,
    interviewer: str,
    api_key: str | None,
) -> tuple[str, bool]:
    """Generate notes with OpenAI, or use mock output when the key is missing.

    The boolean in the return value tells the interface whether mock mode was
    used, so it can show the correct status message to the user.
    """

    if not api_key:
        mock_notes = generate_mock_notes(
            transcript,
            output_type,
            company_name,
            main_business,
            discussion_topics,
            meeting_date,
            interviewer,
        )
        return mock_notes, True

    # build_prompt() selects the matching template and includes all context.
    complete_prompt = build_prompt(
        transcript=transcript,
        output_type=output_type,
        company_name=company_name,
        main_business=main_business,
        discussion_topics=discussion_topics,
        meeting_date=meeting_date,
        interviewer=interviewer,
    )

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=complete_prompt,
    )
    return response.output_text, False


def parse_generation_output(output_text: str) -> tuple[str, list[dict]]:
    """Separate the visible notes from the model's hidden term-check data."""

    marker_pattern = re.compile(
        r"<!--\s*MEMI_TERM_CHECKS\s*(\[.*?\])\s*-->",
        re.DOTALL,
    )
    marker = marker_pattern.search(output_text)
    notes = marker_pattern.sub("", output_text).strip()
    if not marker:
        return notes, []

    try:
        raw_checks = json.loads(marker.group(1))
    except (json.JSONDecodeError, TypeError):
        return notes, []

    # Ignore malformed entries so one bad item does not break the interface.
    valid_checks = []
    if isinstance(raw_checks, list):
        for item in raw_checks:
            if not isinstance(item, dict):
                continue
            original_term = str(item.get("original_term", "")).strip()
            suggestions = item.get("suggestions", [])
            if original_term and isinstance(suggestions, list):
                valid_checks.append(
                    {
                        "timestamp": str(item.get("timestamp", "未提供时间点")).strip(),
                        "original_term": original_term,
                        "reason": str(item.get("reason", "结合上下文可能有误")).strip(),
                        "suggestions": [
                            str(suggestion).strip()
                            for suggestion in suggestions[:2]
                            if str(suggestion).strip()
                        ],
                    }
                )
    return notes, valid_checks


def apply_term_corrections(notes: str, corrections: dict[str, str]) -> str:
    """Apply the user's confirmed terminology to the generated notes."""

    revised_notes = notes
    for original_term, confirmed_term in corrections.items():
        if confirmed_term == original_term:
            continue
        revised_notes = revised_notes.replace(
            f"{original_term}【待确认】", confirmed_term
        ).replace(original_term, confirmed_term)
    return revised_notes


def generate_with_progress(
    transcript: str,
    output_type: str,
    company_name: str,
    main_business: str,
    discussion_topics: str,
    meeting_date: str,
    interviewer: str,
    api_key: str | None,
) -> tuple[str, bool]:
    """Run generation while showing approximate, friendly progress updates."""

    stages = [
        (12, "MeMi 正在阅读会议记录…"),
        (30, "MeMi 正在梳理讨论主题…"),
        (50, "MeMi 正在检查行业专有名词…"),
        (68, "MeMi 冥思苦想中…"),
        (82, "MeMi CPU 烧烤中…"),
        (92, "MeMi 正在给纪要排版…"),
    ]
    status_placeholder = st.empty()
    progress_placeholder = st.empty()

    # The API does not expose exact completion progress. Running it in a worker
    # lets the main page show honest, approximate stages while it waits.
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                generate_notes,
                transcript,
                output_type,
                company_name,
                main_business,
                discussion_topics,
                meeting_date,
                interviewer,
                api_key,
            )
            stage_index = 0
            while not future.done():
                progress_value, message = stages[min(stage_index, len(stages) - 1)]
                status_placeholder.markdown(
                    f'<div class="memi-thinking">{message}</div>',
                    unsafe_allow_html=True,
                )
                progress_placeholder.progress(
                    progress_value,
                    text=f"大致进度 · {message}",
                )
                stage_index += 1
                time.sleep(1.1)

            result = future.result()
    except Exception:
        status_placeholder.empty()
        progress_placeholder.empty()
        raise

    status_placeholder.empty()
    progress_placeholder.progress(100, text="完成 · MeMi 已整理好会议纪要")
    time.sleep(0.25)
    progress_placeholder.empty()
    return result


def show_copy_button(text: str) -> None:
    """Render a small browser-side button that copies notes to the clipboard."""

    # json.dumps safely turns the notes into a JavaScript string.
    notes_as_javascript = json.dumps(text)
    components.html(
        f"""
        <button id="copy-button" style="
            width: 100%;
            min-height: 42px;
            border: 1px solid rgba(47, 143, 245, 0.25);
            border-radius: 12px;
            background: white;
            color: #247fdc;
            cursor: pointer;
            font: 600 14px sans-serif;
            padding: 8px 14px;
        ">复制纪要</button>
        <span id="copy-status" style="font: 13px sans-serif; margin-left: 8px;"></span>
        <script>
            const button = document.getElementById("copy-button");
            const status = document.getElementById("copy-status");
            button.addEventListener("click", async () => {{
                try {{
                    await navigator.clipboard.writeText({notes_as_javascript});
                    status.textContent = "已复制";
                    status.style.color = "#067647";
                }} catch (error) {{
                    status.textContent = "请使用纪要区域的复制功能";
                    status.style.color = "#b54708";
                }}
            }});
        </script>
        """,
        height=48,
    )


def clear_session_api_key() -> None:
    """Remove the user's API key from this Streamlit browser session."""

    st.session_state["user_openai_api_key"] = ""


st.markdown(
    """
    <section class="memi-hero">
        <div class="memi-logo">Me</div>
        <div>
            <span class="memi-eyebrow">AI MEETING NOTES</span>
            <h1>MeMi</h1>
            <p>把杂乱的会议记录，变成清晰、可信、可以直接使用的纪要。</p>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

with st.expander(
    "🔑 使用你自己的 OpenAI API Key",
    expanded=not bool(st.session_state.get("user_openai_api_key")),
):
    st.caption(
        "Key 仅保存在你当前的会话内存中，用于直接调用 OpenAI。"
        "MeMi 不会把它写入文件或数据库。"
    )
    openai_api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        key="user_openai_api_key",
        placeholder="sk-…",
        help="请使用你自己的 API Key，不要把 Key 发给别人或放进截图。",
    ).strip()

    if openai_api_key:
        status_column, clear_column = st.columns([3, 1])
        with status_column:
            st.success("已为本次会话设置 API Key。使用费用计入你自己的 OpenAI 账户。")
        with clear_column:
            st.button(
                "清除 Key",
                on_click=clear_session_api_key,
                use_container_width=True,
            )
    else:
        st.info("没有填写 Key 时，MeMi 会使用 mock 演示输出。")

if not openai_api_key:
    st.warning(
        "当前没有会话 API Key，MeMi 正在使用演示模式，不会把会议记录发送给 OpenAI。"
    )

with st.container(border=True):
    st.subheader("1. 添加会议记录")
    transcript_input = st.text_area(
        "粘贴原始会议记录",
        height=240,
        placeholder="把未经整理的会议记录粘贴到这里…",
    )
    uploaded_file = st.file_uploader(
        "或者上传 .txt 文件",
        type=["txt"],
        help="同时提供文件和粘贴文本时，MeMi 会优先使用上传的文件。",
    )

    st.subheader("2. 选择纪要形式")
    output_type = st.selectbox(
        "输出形式",
        OUTPUT_TYPES,
        format_func=lambda option: (
            "Q&A 清理版" if option == QA_OUTPUT_TYPE else "精简要点摘要"
        ),
    )

    if output_type == QA_OUTPUT_TYPE:
        st.markdown(
            """
            <div class="output-format-help">
                会议内容会按照原始讨论顺序整理成多组“一问一答”，每个问题对应一段清理后的回答。<br>
                <span class="example">示例：Q1：公司的主要业务是什么？　A：公司目前主要提供医药内容营销服务。</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="output-format-help">
                会议内容会合并重复信息并提炼为清晰要点，使用“简短结论：详细说明”的结构。<br>
                <span class="example">示例：客户结构：外资药企约占五成，国内创新药企的占比正在提升。</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.subheader("3. 补充会议背景")
    with st.expander("可选：补充背景信息可以提高准确性"):
        meeting_date_input = st.date_input(
            "会议日期",
            value=None,
            help="用于纪要开头的时间信息。",
        )
        interviewer = st.text_input(
            "采访人",
            placeholder="例如：MeMi资本 - 投资经理 - 张三",
            help="建议格式：公司 - 职位 - 姓名。",
        )
        company_name = st.text_input(
            "被访公司", placeholder="例如：优佳传媒"
        )
        main_business = st.text_input(
            "主营业务", placeholder="例如：医药内容营销与医生 IP 运营"
        )
        discussion_topics = st.text_area(
            "会议主题",
            height=90,
            placeholder="例如：业务模式、客户结构、财务表现与增长计划",
        )

    meeting_date = meeting_date_input.isoformat() if meeting_date_input else ""

    submitted = st.button(
        "✨ Generate Notes",
        type="primary",
        key="generate_notes_button",
    )

if submitted:
    try:
        uploaded_text = read_uploaded_text(uploaded_file) if uploaded_file else ""
    except UnicodeDecodeError:
        st.error("无法读取这个文件，请将它保存为 UTF-8 编码后重试。")
        uploaded_text = ""

    transcript = uploaded_text.strip() or transcript_input.strip()
    if not transcript:
        st.error("请先粘贴会议记录或上传一个 .txt 文件。")
    else:
        try:
            raw_output, used_mock = generate_with_progress(
                transcript=transcript,
                output_type=output_type,
                company_name=company_name,
                main_business=main_business,
                discussion_topics=discussion_topics,
                meeting_date=meeting_date,
                interviewer=interviewer,
                api_key=openai_api_key,
            )
            notes, term_checks = parse_generation_output(raw_output)
            st.session_state["generated_notes"] = notes
            st.session_state["used_mock"] = used_mock
            st.session_state["term_checks"] = term_checks
            st.session_state.pop("revision_success", None)
        except OpenAIError as error:
            st.error(f"OpenAI 暂时无法生成纪要：{error}")

if notes := st.session_state.get("generated_notes"):
    st.divider()
    st.subheader("生成的会议纪要")
    with st.container(border=True):
        st.markdown(notes)

    term_checks = st.session_state.get("term_checks", [])
    if term_checks:
        st.warning(
            "发现可能需要确认的行业术语。请结合录音和上下文逐项确认；"
            "确认后 MeMi 会更新会议纪要。"
        )
        with st.form("term_confirmation_form"):
            selected_terms = []
            for index, check in enumerate(term_checks):
                st.markdown(
                    f"**{index + 1}. `{check['timestamp']}` · "
                    f"原词：`{check['original_term']}`**"
                )
                st.caption(check["reason"])

                unselected_option = "请选择…"
                original_option = f"原词正确：{check['original_term']}"
                custom_option = "其他（请在下方填写）"
                options = [
                    unselected_option,
                    original_option,
                    *check["suggestions"],
                    custom_option,
                ]
                choice = st.selectbox(
                    "请选择正确术语",
                    options,
                    key=f"term_choice_{index}",
                )
                custom_term = st.text_input(
                    "如果候选项都不正确，请填写正确术语",
                    key=f"custom_term_{index}",
                )
                selected_terms.append(
                    (check, choice, custom_term, custom_option, unselected_option)
                )

            confirm_terms = st.form_submit_button("确认并更新", type="primary")

        if confirm_terms:
            corrections = {}
            missing_custom_term = False
            missing_selection = False
            for (
                check,
                choice,
                custom_term,
                custom_option,
                unselected_option,
            ) in selected_terms:
                if choice == unselected_option:
                    missing_selection = True
                    continue
                if choice == custom_option:
                    if not custom_term.strip():
                        missing_custom_term = True
                        continue
                    confirmed_term = custom_term.strip()
                elif choice.startswith("原词正确："):
                    confirmed_term = check["original_term"]
                else:
                    confirmed_term = choice
                corrections[check["original_term"]] = confirmed_term

            if missing_selection:
                st.error("请确认每一个疑似术语后再更新会议纪要。")
            elif missing_custom_term:
                st.error("选择“其他”时，请填写正确术语。")
            else:
                st.session_state["generated_notes"] = apply_term_corrections(
                    notes, corrections
                )
                st.session_state["term_checks"] = []
                st.session_state["revision_success"] = True
                st.rerun()

    if st.session_state.pop("revision_success", False):
        st.success("已根据你的确认更新会议纪要。")

    copy_column, download_column = st.columns(2)
    with copy_column:
        show_copy_button(notes)
    with download_column:
        st.download_button(
            "下载 Markdown",
            data=notes,
            file_name="memi-meeting-notes.md",
            mime="text/markdown",
            use_container_width=True,
        )

    if st.session_state.get("used_mock"):
        st.info("演示模式：这是模拟输出，会议记录没有发送给 OpenAI。")
    else:
        st.success("纪要已通过 OpenAI API 生成。")
