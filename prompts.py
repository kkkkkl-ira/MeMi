"""Prompt templates used by MeMi.

Keeping prompts separate makes them easy to edit without touching the UI code.
"""


QA_OUTPUT_TYPE = "Q&A cleaned transcript"
BULLET_OUTPUT_TYPE = "concise bullet-point meeting summary"


TERM_CHECK_INSTRUCTION = """While processing the transcript, check for potentially mistranscribed industry-specific proper nouns, product names, company names, technical terms, abbreviations, or professional terminology. Only flag a term when it appears inconsistent with the stated industry or surrounding context; do not flag a term merely because it is uncommon. For every suspicious term, preserve the timestamp shown in the transcript, quote the original term, briefly explain why it may be incorrect, and suggest one or two plausible corrections. If the transcript has no likely terminology errors and is clear and complete, return no term checks.

After the Markdown notes, always append the following hidden marker with a valid JSON array:
<!-- MEMI_TERM_CHECKS
[{"timestamp":"00:01:23","original_term":"原词","reason":"判断原因","suggestions":["候选词1","候选词2"]}]
-->

Use an empty array (`[]`) inside the marker when no terms need confirmation. Do not mention the terminology check anywhere else in the meeting notes."""


QA_INSTRUCTION = """Organize the transcript into multiple Q&A pairs grouped by discussion topic. Each question must have one corresponding paragraph answer. Preserve the original order of questions and discussion topics. Keep the original wording and logic as much as possible. Delete filler words, repeated words, and empty expressions such as “嗯”, “啊”, “就是”, “然后”, “对”, “这个”, “那个”, “这边”, “那边”, “这一块”, “那一块”. Merge repeated information within the relevant answer, but do not merge the entire meeting into one broad question. Do not over-summarize. Do not add information that is not in the transcript. If a term is unclear, mark it as 【待确认】. Format each pair as a Markdown heading in the form “### Q1: question”, followed by its answer paragraph, then continue with Q2, Q3, and so on."""


BULLET_SUMMARY_INSTRUCTION = """Organize the transcript into clear bullet points. Delete filler words and repeated expressions, but do not change the meaning. Cover company history, main business, revenue mix, customers, customer share, financial information, product/service details, competitive landscape, growth drivers, risks, and other important information if mentioned. Use the format “short conclusion: detailed explanation”. Merge repeated information. Do not invent missing information. If a term is unclear, mark it as 【待确认】."""


PROMPTS = {
    QA_OUTPUT_TYPE: QA_INSTRUCTION,
    BULLET_OUTPUT_TYPE: BULLET_SUMMARY_INSTRUCTION,
}

# The Streamlit dropdown imports this list, keeping its choices synchronized
# with the templates above.
OUTPUT_TYPES = tuple(PROMPTS.keys())


def get_prompt_template(output_type: str) -> str:
    """Return the instruction that belongs to the selected output type."""

    try:
        return PROMPTS[output_type]
    except KeyError as error:
        raise ValueError(f"Unsupported output type: {output_type}") from error


def build_prompt(
    transcript: str,
    output_type: str,
    company_name: str,
    main_business: str,
    discussion_topics: str,
    meeting_date: str = "",
    interviewer: str = "",
) -> str:
    """Combine the selected instruction, meeting context, and transcript."""

    instruction = get_prompt_template(output_type)
    return f"""You are an accurate meeting-notes editor.

Task:
{instruction}

Terminology verification:
{TERM_CHECK_INSTRUCTION}

Meeting context supplied by the user:
- Meeting date: {meeting_date or "Not provided"}
- Interviewer (company - title - name): {interviewer or "Not provided"}
- Company name: {company_name or "Not provided"}
- Main business: {main_business or "Not provided"}
- Main discussion topics: {discussion_topics or "Not provided"}

Required output header:
Begin the meeting notes with exactly these three plain-text lines, without bullets or Markdown headings. Use “未提供” when the corresponding context was not supplied. Do not infer or invent missing header information.
时间：{meeting_date or "未提供"}
采访人：{interviewer or "未提供"}
会议主题：{discussion_topics or "未提供"}

After these three lines, add one blank line and then write the meeting notes in the selected format.

Raw transcript:
---
{transcript}
---

Return the cleaned meeting notes in Markdown followed by the hidden terminology-check marker.
"""
