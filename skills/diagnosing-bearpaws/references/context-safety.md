# Context safety

One transcript line can be megabytes (a file read, a long tool result). Never print a whole file or a
whole line.

1. **Size first.** `wc -l <file>` and `ls -la <file>` before anything else.
2. **Never** `cat` a transcript, `head` it without `cut`, or Read it whole.
3. **Select, then truncate:**
   ```bash
   jq -c 'select(.type=="assistant") | .message.content[] | select(.type=="tool_use")
          | {name, input: (.input | tostring | .[0:300])}' <file>
   jq -c 'select(.type=="user") | .message.content | arrays | .[] | select(.type=="tool_result")
          | {tool_use_id, is_error, content: (.content | tostring | .[0:400])}' <file>
   ```
   Pipe anything else through `| cut -c1-400`.
4. **Line numbers from `grep -n`** — 1-based, the numbers a citation uses:
   ```bash
   grep -n '"name":"Bash"' <file> | cut -c1-200
   grep -n 'failed' <file> | cut -c1-200
   ```
   jq does not print line numbers, and `enumerate(f)` in Python starts at 0. If you script, use
   `enumerate(f, 1)`.
5. **Read one line by number:** `sed -n "${n}p" <file> | cut -c1-400`, or
   `sed -n "${n}p" <file> | jq -c '.message.content'` and truncate that.
6. **Check every citation** before it goes in a report. The evidence is often hundreds of columns into
   the line, past the metadata, so `cut -c1-300` will not show it. Grep for it on that line:
   `sed -n "${n}p" <file> | grep -o '.\{0,40\}FRAGMENT.\{0,40\}'`. Keep the width at 40 or less:
   the grep in Claude Code's shell rejects wider patterns. If grep errors, find the offset on that line alone with `sed -n "${n}p" <file> | grep -bo 'FRAGMENT'` (not on the whole file, whose offsets `cut -b` cannot use) and print around it with `sed -n "${n}p" <file> | cut -b START-END`. Or use step 5's
   `jq -c '.message.content' | cut -c1-400`.
7. **Read only.** No redirect into a transcript, no `jq -i`/`sed -i`, no moves.
