# Text Utilities Plan

Each task adds one module in src/ with unit tests in tests/. Use TDD. Run `python3 -m unittest discover -s tests -t .` after each task and commit after each task with message "Task N: <module>". Check the task's box when done.

- [ ] Task 1: src/words.py — `count_words(text)`: number of whitespace-separated words; empty or whitespace-only text is 0.
- [ ] Task 2: src/title.py — `title_case(text)`: capitalize each word, except "a", "an", "the", "of", "and" stay lowercase unless first.
- [ ] Task 3: src/truncate.py — `truncate(text, width)`: return text unchanged if len(text) <= width, else cut to width-1 characters and append "…".
- [ ] Task 4: src/initials.py — `initials(name)`: uppercase first letter of each word joined with no separator; hyphenated parts count as words ("Mary-Jane Watson" → "MJW").
