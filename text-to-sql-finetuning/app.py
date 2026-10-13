"""Gradio UI for querying the fine-tuned text-to-SQL model (runs locally, Apple Silicon / CPU / CUDA).

Type a database schema (CREATE TABLE + optional INSERT rows) and a question; the model returns a SQLite
query plus an explanation, and the query is executed against the schema so you can see the actual result.
"Compare" runs the base model and the fine-tuned model side by side (same weights, LoRA switched off/on).

Usage:
  .venv/bin/python app.py                       # opens http://127.0.0.1:7860
  ADAPTER_DIR=path/to/adapter .venv/bin/python app.py
"""
import json
import os
import re
import sqlite3
import time

import gradio as gr
import pandas as pd
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from prepare_data import SYSTEM_PROMPT, build_user

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_ID = "Qwen/Qwen2.5-1.5B-Instruct"
ADAPTER_DIR = os.environ.get(
    "ADAPTER_DIR", os.path.join(HERE, "v2/outputs/qwen2.5-1.5b-instruct-text2sql-lora-v2/final_adapter"))
MAX_NEW_TOKENS = 384

FT, BASE, BOTH = "Fine-tuned (v2)", "Base (no fine-tuning)", "Compare both"

if torch.cuda.is_available():
    DEVICE, DTYPE = "cuda", torch.bfloat16
elif torch.backends.mps.is_available():
    DEVICE, DTYPE = "mps", torch.float16
else:
    DEVICE, DTYPE = "cpu", torch.float32

print(f"loading {BASE_ID} + {os.path.relpath(ADAPTER_DIR, HERE)} on {DEVICE} ...")
tokenizer = AutoTokenizer.from_pretrained(BASE_ID)   # LoRA does not change the tokenizer
model = AutoModelForCausalLM.from_pretrained(BASE_ID, dtype=DTYPE).to(DEVICE)
model = PeftModel.from_pretrained(model, ADAPTER_DIR).eval()


# ---------- same prompt / parsing as the evaluation notebooks ----------
def extract_sql(text):
    m = re.search(r"```(?:sql|sqlite)?\s*(.*?)```", text, re.S | re.I)
    if m:
        return m.group(1).strip()
    m = re.search(r"\b((?:SELECT|WITH)\b.*?)(?:;|\n\n|$)", text, re.S | re.I)
    return m.group(1).strip() if m else text.strip()


def extract_explanation(text):
    m = re.search(r"Explanation:\s*(.*)", text, re.S | re.I)
    if m:
        return m.group(1).strip()
    return re.sub(r"```.*?```", "", text, flags=re.S).strip()


@torch.no_grad()
def generate(context, question, use_adapter):
    msgs = [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user(context, question)}]
    prompt = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    enc = tokenizer(prompt, return_tensors="pt").to(DEVICE)
    kwargs = dict(max_new_tokens=MAX_NEW_TOKENS, do_sample=False, temperature=None, top_p=None, top_k=None,
                  pad_token_id=tokenizer.pad_token_id)
    if use_adapter:
        out = model.generate(**enc, **kwargs)
    else:
        with model.disable_adapter():
            out = model.generate(**enc, **kwargs)
    return tokenizer.decode(out[0, enc["input_ids"].shape[1]:], skip_special_tokens=True)


def execute(context, sql, max_ops=200_000):
    """Run schema + query in a fresh in-memory SQLite DB. Returns (DataFrame | None, status message)."""
    conn = sqlite3.connect(":memory:")
    steps = {"n": 0}

    def guard():
        steps["n"] += 1
        return 1 if steps["n"] > max_ops else 0

    conn.set_progress_handler(guard, 1000)
    try:
        conn.executescript(context)
    except Exception as e:
        return None, f"⚠️ Schema failed to load in SQLite: {e}"
    try:
        cur = conn.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        return pd.DataFrame(rows, columns=cols), f"✅ Ran in SQLite — {len(rows)} row(s)"
    except Exception as e:
        return None, f"❌ SQLite error: {e}"
    finally:
        conn.close()


def run_one(context, question, use_adapter):
    t0 = time.time()
    raw = generate(context, question, use_adapter)
    secs = time.time() - t0
    sql = extract_sql(raw)
    df, status = execute(context, sql)
    return sql, extract_explanation(raw), df, f"{status} · generated in {secs:.1f}s", raw


def answer(context, question, mode):
    if not context.strip() or not question.strip():
        raise gr.Error("Please enter both a schema and a question.")
    empty = ("", "", None, "", "")
    ft = run_one(context, question, True) if mode in (FT, BOTH) else empty
    base = run_one(context, question, False) if mode in (BASE, BOTH) else empty
    return (*ft, *base, gr.Column(visible=mode in (FT, BOTH)), gr.Column(visible=mode in (BASE, BOTH)))


# ---------- examples: test-set questions the base model gets wrong and the fine-tuned model gets right ----------
# (checked locally on Apple Silicon; picked from v2_epoch2 "fixed vs base" cases, one or two per complexity)
EXAMPLE_IDS = [1946, 3043, 1301, 206, 1000]


def load_examples():
    custom = [
        "CREATE TABLE employees (id INT, name TEXT, department TEXT, salary REAL, hire_date DATE);\n"
        "INSERT INTO employees VALUES (1, 'Alice', 'Engineering', 120000, '2021-03-15'), "
        "(2, 'Bob', 'Engineering', 95000, '2022-07-01'), (3, 'Carol', 'Sales', 70000, '2020-11-20'), "
        "(4, 'Dan', 'Sales', 82000, '2023-01-09'), (5, 'Eve', 'Marketing', 64000, '2022-05-30');",
        "What is the average salary in each department for employees hired after 2021?",
    ]
    try:
        test = {r["id"]: r for r in map(json.loads, open(os.path.join(HERE, "data/test.jsonl")))}
        return [custom] + [[test[i]["sql_context"], test[i]["sql_prompt"]] for i in EXAMPLE_IDS if i in test]
    except OSError:
        return [custom]


def result_column(title, visible=True):
    with gr.Column(visible=visible) as col:
        gr.Markdown(f"### {title}")
        status = gr.Markdown()
        sql = gr.Code(label="Generated SQL", language="sql", interactive=False, wrap_lines=True)
        expl = gr.Textbox(label="Explanation", lines=3, interactive=False)
        table = gr.Dataframe(label="Query result (executed in SQLite)", interactive=False, wrap=True)
        with gr.Accordion("Raw model output", open=False):
            raw = gr.Textbox(show_label=False, lines=8, interactive=False)
    return col, [sql, expl, table, status, raw]


with gr.Blocks(title="Text-to-SQL") as demo:
    gr.Markdown(
        "# Text-to-SQL with a fine-tuned Qwen2.5-1.5B\n"
        "Qwen2.5-1.5B-Instruct + LoRA, fine-tuned on Gretel `synthetic_text_to_sql` (SQLite-runnable subset). "
        "Enter a schema and a question → the model writes a SQLite query and explains it; the query is then "
        "run against your schema. Test-set execution accuracy: **64.3% base → 73.7% fine-tuned**.")
    with gr.Row():
        with gr.Column(scale=3):
            schema = gr.Code(label="Database schema (CREATE TABLE … ; INSERT INTO … ;)", language="sql",
                             lines=8, interactive=True)
            question = gr.Textbox(label="Question", placeholder="e.g. Which department has the highest average salary?")
        with gr.Column(scale=1):
            mode = gr.Radio([FT, BASE, BOTH], value=FT, label="Model")
            btn = gr.Button("Generate SQL", variant="primary")
    gr.Examples(load_examples(), inputs=[schema, question], label="Examples (click to fill)")
    with gr.Row():
        ft_col, ft_out = result_column("Fine-tuned (v2)")
        base_col, base_out = result_column("Base (no fine-tuning)", visible=False)

    io = dict(fn=answer, inputs=[schema, question, mode], outputs=ft_out + base_out + [ft_col, base_col])
    btn.click(**io)
    question.submit(**io)

if __name__ == "__main__":
    demo.launch(inbrowser=True)
