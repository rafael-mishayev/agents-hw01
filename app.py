import gradio as gr

from loop import NO_APPROVED_MESSAGE, TECH_ERROR_MESSAGE, answer_question

STATUS_MESSAGES = (NO_APPROVED_MESSAGE, TECH_ERROR_MESSAGE)


def to_text(content):
    """Gradio may deliver message content as a string or as a list of content blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(block.get("text", "") for block in content if isinstance(block, dict))
    return str(content)


def clean_history(history):
    """Keep only role/content, and drop turns that did not end with an approved answer
    (status messages and the user question they replied to), so that only
    user messages and approved final answers reach the Actor and the Critic."""
    messages = [{"role": h["role"], "content": to_text(h["content"])} for h in history]
    cleaned = []
    for m in messages:
        if m["role"] == "assistant" and m["content"] in STATUS_MESSAGES:
            if cleaned and cleaned[-1]["role"] == "user":
                cleaned.pop()  # the question that got no approved answer
            continue
        cleaned.append(m)
    return cleaned


def chat(message, history):
    history = clean_history(history)
    text, log = answer_question(message, history, scenario_id="chat")
    return text  # an approved answer, or a status message (never a rejected draft)


if __name__ == "__main__":
    gr.ChatInterface(
        chat,
        title="הצ'אט האישי של דנה לוי",
        description="פרופיל לדוגמה (דמיוני). אפשר לשאול על לימודים, ניסיון, מיומנויות ופרויקטים.",
        chatbot=gr.Chatbot(show_label=False, rtl=True, placeholder="שאלו אותי כל דבר על הקריירה שלי"),
        textbox=gr.Textbox(placeholder="הקלידו שאלה בעברית...", rtl=True),
        examples=[
            "איפה למדת?",
            "באיזה פרויקט עבדת על צ'אטבוט?",
            "אילו שפות תכנות את מכירה?",
        ],
    ).launch()
