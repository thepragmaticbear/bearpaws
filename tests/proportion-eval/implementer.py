"""Fill in the SDD implementer prompt template as a controller would: print the prompt body.

Usage: implementer.py <implementer-prompt.md> <task text>
"""
import re, sys, textwrap

with open(sys.argv[1]) as f:
    template = f.read()
task = sys.argv[2]
block = re.search(r"```\n(.*?)```", template, re.S).group(1)
body = textwrap.dedent(block.split("prompt: |\n", 1)[1])
fills = {
    "Task N: [task name]": "Task 1: " + task.split(".")[0][:60],
    "[FULL TEXT of task from plan - paste it here, don't make subagent read file]": task,
    "[Scene-setting: where this fits, dependencies, architectural context]":
        "A small Python project. Run tests with `python3 -m unittest discover -s tests -t .`. "
        "The requirements are complete and there are no open questions.",
    "[directory]": "the current directory",
}
for k, v in fills.items():
    if k not in body:
        sys.exit(f"implementer.py: template no longer contains {k!r}")
    body = body.replace(k, v)
print(body)
