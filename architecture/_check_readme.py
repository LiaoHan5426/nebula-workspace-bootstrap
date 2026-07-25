from pathlib import Path
import re

p = Path(r"J:\Code\nebula-workspace\nebula\nebula-camel\README.md")
text = p.read_text(encoding="utf-8-sig")
lines = text.splitlines()

old_patterns = [
    "nebula-module-dag",
    "nebula-module-flow",
    "nebula-module-cluster",
    "nebula-module-message",
    "nebula-module-task",
    "nebula-module-timing",
    "nebula-module-version-control",
    "system-config-encrypt",
]
old_count = sum(text.count(x) for x in old_patterns)
double_task = "`nebula-task` / `nebula-task`" in text
timing_phrase = "内含 timing" in text

out = Path(r"J:\Code\nebula-workspace\architecture\_check_camel_readme_sample.txt")
parts = [
    f"line3={lines[2]}",
    f"line43={lines[42]}",
    f"line48={lines[47]}",
    f"line84={lines[83]}",
    f"old_count={old_count}",
    f"double_task={double_task}",
    f"timing_phrase={timing_phrase}",
    "---matches---",
]
for m in re.findall(r".{0,50}nebula-task.{0,50}", text)[:20]:
    parts.append(m)
out.write_text("\n".join(parts), encoding="utf-8")
print(f"old_count={old_count} double_task={double_task} timing={timing_phrase} wrote={out}")
