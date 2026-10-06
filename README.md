# IPHS 400 — Mini-Project #2 starter (Web CMS)

Click **Use this template** → name your repo **`iphs400-mp2-cms`** → make it **Public**.
Do not fork: a fork arrives without an Issues tab, and your tickets live in Issues.

## Start here

1. `docs/manual_iphs400_mp2-web-cms_20260922.md` — the manual. Read Part 0 and Part 1 first.
2. `docs/mp2-grading-rubric_20260922.md` — how you are graded. Read it **before** you build.
3. `docs/mp2-setup_context-threshold-hook_20260922.md` — Exercise A, in Part 4 of the manual.

## Run it

```bash
uv sync
cp .env.example .env
uv run cms serve        # then open http://localhost:8000/admin  -> "T00: hello admin"
```

## Run locally

uv sync  
cp .env.example .env   
uv run python scripts/seed_demo.py  
uv run cms serve  
uv run cms publish && uv run cms deploy  

## What is here

```text
.claude/hooks/     the context meter and usage ledger (Exercise A lives in ctx_guard.py)
scripts/           usage_report.py (Exercise B lives in spend()), check_submission.py, seed_demo.py
tests/             the exercise tests, plus helpers such as client_as("editor")
app/, templates/   the T00 skeleton — every CMS feature is yours to build
docs/adr/          two example decision records
```

Two functions are deliberately unfinished and their tests fail until you write them:
`decide()` in `.claude/hooks/ctx_guard.py` and `spend()` in `scripts/usage_report.py`.
Both are graded. Use `/tdd`, as the manual says.

## Deadlines

Stage 1 (`mp2-mvp` tag): Tue Sep 29, 2:40 pm Eastern (soft target).
Stage 2 (`mp2-final` tag): Tue Oct 6, 2:40 pm Eastern, grace until Wed Oct 7, 2:40 pm.

Run `uv run python scripts/check_submission.py --stage 2` before you submit.

## Generative AI Use Statement

This project has been created entirely using the Claude Code tool, specifically the Sonnet 5 model with Medium, High and Extra effort for thinking, and later Opus 5.5 High. Medium/High thinking effort was used from the start of the project up to the creation of the spec. Creating tickets and implementing them was all done using Sonnet 5 Extra effort. Then, at /code-review, I switched to the Opus 5.5 model with High thinking effort. Switching to have more capable models was a decision influenced by a discussion with Professor Chun that the token usage rates at Sonnet 5 Medium effort are very low, so bumping up the model's capability to be at High or Extra or just switching to Opus 5.5 High while compacting the context once it gets filled up to about 40% is only advantageous. Opus 5.5 High does burn tokens a lot, but it was essential in /code-review.

The skills used for this project are the Matt Pocock skills /grill-with-docs, /to-spec, /to-tickets, /implement, /code-review, /tdd. The model followed these skills well at every thinking effort: it generated a spec and also handled a project trajectory pivot well when I presented it a pivot from the original idea that would align better with the rubric and the project's requirements.

One prompt I gave the model, answering its questions and clarifying my previous answers during the /grill-with-docs skill running: "Q1 - Sorry yes, use that template on the github repo. Use the git commands to get that template. Q2 - Yes, make it me and faculty advisor are admin and editor is for officers. Admin - editor permissions + publish/unpublish + manage users. Editor - edit and create content. Q3 - Outlined in Q2. Q4 - Advisor is Doctor Diane Kahle, use placeholders for student officer names for now. Look up CSHS details in upper arlington high school. GPA req is 3.5 or above. Q5 - Add posts, pages and events and roster. Events and roster will be extra credit. Posts - dated, feed-like, announcements, meetings, events, pages - about/eligibility, events, roster, join, eligibility."
* Here I was answering its clarifying questions on how the project should look like. This is before pivoting from the idea of a client-specific CMS to a general CMS and a client-specific website built on top of it. The model correctly asked me about things that I was (intentionally) vague about, which allowed me to make things specific.

Second prompt I gave the model (during the pivot): "Hey, change of plans. We're building a CMS with no client in mind. I know the current grading rubric says we need a specific client, but we're pivoting now because professor updated it. Essentially, the goal is to make a Wordpress-style CMS but not specific to any client."
* I prompted the model this because initially I was steering it to develop a CMS with Admin/Editor roles specific to the organization I chose (the client, the Upper Arlington High School Computer Science Honor Society, UAHS CSHS). After a conversation with Professor Chun, I understood that the CMS should be general with no client specifically in mind, but then I need to use the CMS to create a custom website for a client. The model responded by actually asking questions about the implementation, which is good because it asked for clarifiation rather than guessing. I later clarified everything I meant in my prompt, saying that "client specificity" is still part of the project but only after the CMS is built separately.

One model failure occured during class, on the 1st of October. It wasn't a developmental failure, but rather a context management issue. This was in a different session from the one I had for this SWE Matt Pocock process. Since the context length fills up quickly in this SWE process, I prompted it to set up two hooks, where 1 hook warns me that Sonnet 5 is at 30% context fill, and the other runs /compact at 40%. As it turns out, it wasn't able to create the second hook and automatically run /compact at 40% context fill, so I told it to just change the hook just to block me out from sending messages. But then, Claude didn't check the context length limit for Sonnet 5 and just assumed it was 200k, which shut me out of my mini project session because the context length was already filled to 250k (approximately) tokens. To resolve this, I then had to manually go into the hooks in my global .claude folder and change the context window length to 1M because I couldn't prompt Claude to do so. Late I ended up just removing this second hook entirely, now relying only on the first "warning" hook so I compact the conversation, because the shut-off at 40% was inflexible.  
Another model failure I think is important to mention is the code it generated during the /implement phase. I switched to Opus 5.5 high at /code-review, and it flagged many bugs that it found in the project. It subsequently cleanly fixed them and successfully passed the code through a test suite, so this was more of an ephemeral and self-correcting issue, but I decided to mention it here anyway.

Backends: I only used Anthropic's models, specifically Sonnet 5 Medium, Sonnet 5 High, Sonnet 5 Extra High, Opus 5.5 High (/code-review and onwards). I used VS Code as my source code editor for this full project.

