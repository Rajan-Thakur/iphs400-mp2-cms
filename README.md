# IPHS 400 — Mini-Project #2 (Web CMS)

## Run it

```bash
uv sync
cp .env.example .env
uv run python scripts/seed_demo.py
uv run cms serve        # then open http://localhost:8000/admin 
```

## Run locally (run playwright install only once)

```
    uv sync  
    cp .env.example .env    
    uv run playwright install chromium  
    uv run python scripts/seed_demo.py    
    uv run cms serve
```

Run the following in a second terminal:
`uv run cms publish && uv run cms deploy` 

Go to http://localhost:8000/admin to log in  
Admin email and password: admin@example.test, change-me-admin
Editor email and password: editor@example.test, change-me-editor

## Deadlines

Stage 1 (`mp2-mvp` tag): Tue Sep 29, 2:40 pm Eastern (soft target).  

Early submission:  
Stage 2 (`mp2-final` tag): Tue Oct 6, 2:40 pm Eastern, grace until Wed Oct 7, 2:40 pm.

Final submission:  
Stage 2 (`mp2-final`): Thu Oct 15, 2:40 pm Eastern, grace until Fri Oct 16, 2:40

MP2 Plus submission: Tue Oct 20, 2:40 pm Eastern, grace until Wed 21, 2:40

Run `uv run python scripts/check_submission.py --stage 2` before you submit.

## Live URL

Running here: https://rajan-thakur.github.io/iphs400-mp2-cms/

## Generative AI Use Statement

This project has been created entirely using the Claude Code tool, specifically the Sonnet 5 model with Medium, High and Extra effort for thinking, and later Opus 5.5 High. Medium/High thinking effort was used from the start of the project up to the creation of the spec. Creating tickets and implementing them was all done using Sonnet 5 Extra effort. Then, at /code-review, I switched to the Opus 5.5 model with High thinking effort. Switching to have more capable models was a decision influenced by a discussion with Professor Chun that the token usage rates at Sonnet 5 Medium effort are very low, so bumping up the model's capability to be at High or Extra or just switching to Opus 5.5 High while compacting the context once it gets filled up to about 40% is only advantageous. Opus 5.5 High does burn tokens a lot, but it was essential in /code-review.

The skills used for this project are the Matt Pocock skills /grill-with-docs, /to-spec, /to-tickets, /implement, /tdd, /code-review. The model followed these skills well at every thinking effort: it generated a spec and also handled a project trajectory pivot well when I presented it a pivot from the original idea that would align better with the rubric and the project's requirements.

One prompt I gave the model, answering its questions and clarifying my previous answers during the /grill-with-docs skill running: "Q1 - Sorry yes, use that template on the github repo. Use the git commands to get that template. Q2 - Yes, make it me and faculty advisor are admin and editor is for officers. Admin - editor permissions + publish/unpublish + manage users. Editor - edit and create content. Q3 - Outlined in Q2. Q4 - Advisor is Doctor Diane Kahle, use placeholders for student officer names for now. Look up CSHS details on upper arlington high school. GPA req is 3.5 or above. Q5 - Add posts, pages and events and roster. Events and roster will be extra credit. Posts - dated, feed-like, announcements, meetings, events, pages - about/eligibility, events, roster, join, eligibility."
* Here I was answering its clarifying questions on how the project should look like. This is before pivoting from the idea of a client-specific CMS to a general CMS and a client-specific website built on top of it. The model correctly asked me about things that I was (intentionally) vague about, which allowed me to make things specific.

Second prompt I gave the model (during the pivot): "Hey, change of plans. We're building a CMS with no client in mind. I know the current grading rubric says we need a specific client, but we're pivoting now because professor updated it. Essentially, the goal is to make a Wordpress-style CMS but not specific to any client."
* I prompted the model this because initially I was steering it to develop a CMS with Admin/Editor roles specific to the organization I chose (the client, the Upper Arlington High School Computer Science Honor Society, UAHS CSHS). After a conversation with Professor Chun, I understood that the CMS should be general with no client specifically in mind, but then I need to use the CMS to create a custom website for a client. The model responded by actually asking questions about the implementation, which is good because it asked for clarifiation rather than guessing. I later clarified everything I meant in my prompt, saying that "client specificity" is still part of the project but only after the CMS is built separately.

One model failure occured during class, on the 1st of October. It wasn't a developmental failure, but rather a context management issue. This was in a different session from the one I had for this SWE Matt Pocock process. Since the context length fills up quickly in this SWE process, I prompted it to set up two hooks, where 1 hook warns me that Sonnet 5 is at 30% context fill, and the other runs /compact at 40%. As it turns out, it wasn't able to create the second hook and automatically run /compact at 40% context fill, so I told it to just change the hook just to block me out from sending messages. But then, Claude didn't check the context length limit for Sonnet 5 and just assumed it was 200k, which shut me out of my mini project session because the context length was already filled to 250k (approximately) tokens. To resolve this, I then had to manually go into the hooks in my global .claude folder and change the context window length to 1M because I couldn't prompt Claude to do so. Late I ended up just removing this second hook entirely, now relying only on the first "warning" hook so I compact the conversation, because the shut-off at 40% was inflexible.  
Another model failure I think is important to mention is the code it generated during the /implement phase. I switched to Opus 5.5 high at /code-review, and it flagged many bugs that it found in the project. It subsequently cleanly fixed them and successfully passed the code through a test suite, so this was more of an ephemeral and self-correcting issue, but I decided to mention it here anyway.

Note for new Oct 15 (16th grace) deadline: I now switched to Opus 5.5 xhigh for all of my tasks. This was worthwhile because it flagged many issues against the new rubric that went unnoticed previously. The model chews up tokens quickly but handoff documents and /compact deal with this fine.

Also, an important clarification. After miscommunication with the model during one of the early planning stages during the grill session, the model proceeded to write a token usage plan as follows: first Sonnet 5 high/xhigh for the planning stages (/grill-with-docs, /to-spec, /to-tickets), then Sonnet 5 Medium for the implementation (/implement) and then Sonnet 5 high again for /code-review. That was not my original intention. I originally intended to use a different set of thinking efforts and models for the stages. But the model had already written this different plan into the token budget plan document. After implementation, I had noticed this discrepancy, and decided to clarify what the original plan was with commit 16c61f2.

## Backends used

| Backend | Model(s) |
| ------- | -------- |
| Anthropic | Sonnet 5 Medium, Sonnet 5 High, Sonnet 5 xHigh, Opus 5.5 High, Opus 5.5 xHigh |

I only used Anthropic's models, specifically Sonnet 5 Medium, Sonnet 5 High, Sonnet 5 Extra High, Opus 5.5 High, Opus 5.5 xHigh. I used VS Code as my source code editor for this full project, with just a Windows command prompt open for Claude Code. I tried to set up and use Orca (agentic IDE), but I didn't find it as comfortable as VS Code.

