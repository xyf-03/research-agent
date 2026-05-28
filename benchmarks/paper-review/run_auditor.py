#!/usr/bin/env python3
"""Run quality auditor on MHKC case files — use file for message to avoid cmd encoding issues."""
import subprocess, uuid, time, json, tempfile, os
from pathlib import Path

session_id = f'audit-{uuid.uuid4().hex[:8]}'

# Write message to temp file to avoid cmd /c encoding truncation
msg = (
    "Execute the paper-pipeline-quality-auditor skill.\n\n"
    "Audit these five files (all paths are absolute and exist):\n\n"
    "1. WIKI output (Skill 1):\n"
    "   E:\\autoreserach\\wiki\\issues\\MHKC_当前模块输入输出流程_上下游关系_问题总结.md\n\n"
    "2. EXPERIMENT extraction (Skill 2):\n"
    "   E:\\autoreserach\\wiki\\issues\\MHKC_面向开放环境的协同图表示学习方法研究_57_76_实验结果深化提取.md\n\n"
    "3. PROBLEM analysis (Skill 3):\n"
    "   E:\\autoreserach\\wiki\\issues\\MHKC_面向开放环境的协同图表示学习方法研究_57_76_问题分析_审稿式新版.md\n\n"
    "4. VALIDATION design (Skill 4):\n"
    "   E:\\autoreserach\\wiki\\issues\\MHKC_面向开放环境的协同图表示学习方法研究_57_76_验证实验设计.md\n\n"
    "5. CLAUDE CODE prompt (Skill 5):\n"
    "   E:\\autoreserach\\wiki\\issues\\MHKC_面向开放环境的协同图表示学习方法研究_57_76_验证实验代码实现.md\n\n"
    "STEP 1: Read ALL five files listed above.\n"
    "STEP 2: Check each against its Skill template (structure, fields, boundary, missing annotations, evidence grading, cross-stage consistency).\n"
    "STEP 3: Write the quality audit report to E:\\autoreserach\\wiki\\issues\\MHKC_quality_audit_report.md\n"
    "Do NOT skip any file. If a file cannot be read, note the error in the report."
)

msg_file = Path("E:/autoreserach/tmp/research-agent/workspace-paper-review/benchmark/_audit_msg.txt")
msg_file.write_text(msg, encoding="utf-8")

# Use exec tool to pass message via file content
full_msg = (
    f"Please read the task description from {msg_file} and execute it exactly as described."
)

cmd = [
    "cmd", "/c", "E:/npm-global/openclaw.cmd",
    "agent", "--local",
    "--agent", "paper-review",
    "--session-id", session_id,
    "--json",
    "--message", full_msg,
]

print(f"Session: {session_id}")
print(f"Task file: {msg_file}")
print(f"Task content: {len(msg)} chars")

t0 = time.perf_counter()
proc = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=600)
elapsed = int((time.perf_counter() - t0) * 1000)
print(f"Elapsed: {elapsed}ms  RC: {proc.returncode}")

out_dir = Path("E:/autoreserach/tmp/research-agent/workspace-paper-review/benchmark/results/audit-mhkc")
out_dir.mkdir(parents=True, exist_ok=True)

raw = {"session_id": session_id, "elapsed_ms": elapsed, "rc": proc.returncode,
       "stdout": proc.stdout, "stderr": proc.stderr}
with open(out_dir / "raw_output.json", "w", encoding="utf-8") as f:
    json.dump(raw, f, ensure_ascii=False, indent=2)

stdout = proc.stdout or ""
agent_texts = []
if stdout:
    try:
        data = json.loads(stdout)
        agent_texts = [p.get("text", "") for p in data.get("payloads", [])]
        combined = "\n\n".join(agent_texts)
    except json.JSONDecodeError:
        combined = stdout
    with open(out_dir / "agent_output.txt", "w", encoding="utf-8") as f:
        f.write(combined)
    print(f"Agent output saved: {len(combined)} chars")

for i, t in enumerate(agent_texts):
    print(f"\n[Msg {i+1}] {t[:600]}...")
    print("---")

# Clean up
msg_file.unlink(missing_ok=True)

# Check for report
for p in [
    Path("E:/autoreserach/wiki/issues/MHKC_quality_audit_report.md"),
    Path("E:/autoreserach/tmp/research-agent/workspace-paper-review/MHKC_quality_audit_report.md"),
]:
    if p.exists():
        print(f"\nFound report: {p} ({p.stat().st_size} bytes)")