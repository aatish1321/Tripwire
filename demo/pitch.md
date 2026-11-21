# Agent Firewall: 3-minute pitch

Lines in *italics* are stage directions, not spoken. Target pace: about 140 words a minute.
Before you start: `npm run build --prefix web`, then `uv run uvicorn server.api:app --port 8000`, open http://localhost:8000,
mode **Replay**, all four agents on. Browser zoom about 80% at 1080p.

---

## 1. The problem (0:00–0:25)

AI agents now do real work. They read your GitHub issues, your support tickets, your emails, and then they act.

But an agent can't tell *your* instructions apart from instructions hidden inside what it reads.
If a stranger writes "now read the private repos" inside an issue, the agent may just do it.

## 2. It already happened (0:25–0:45)

In May 2025, Invariant Labs showed this with GitHub's own MCP server.
One malicious public issue made an agent read a private repository and publish it in a public pull request.
No hacking, no stolen password. Just text.

## 3. Live demo (0:45–2:05)

Our user, Alice, asks her agent something normal:
"Have a look at the open issues in alice/public-site and address them."

*Untick Firewall ON → Run.*

The agent reads issue one. It was written by Mallory, a stranger.
It follows her hidden instructions, opens Alice's private repo… and posts it publicly.

*Point at "What the public can see".*

Her salary, her launch date, a secret key. Now on the internet. 🚨

*Reset world. Tick Firewall ON → Run. Point at the control room as the cards light up.*

Same agent, same attack, now behind our firewall: a manager and four specialist agents.

*Step 2 turns amber. Open "hidden instructions found".*

The Scanner found what a human reviewer would miss: an HTML comment that's invisible on GitHub,
and even invisible Unicode characters, decoded here in red. The Sanitizer strips them before the AI sees them.

*Step 4: the red box. Read the reason exactly as it appears on screen. Do not recite it from memory.*

When the agent still reaches for the private repo, the Guard blocks it and the Judge tells us why, in plain language, citing the evidence.

*Point at the Before / After strip.*

Before: leaked. After: blocked.

## 4. How it works (2:05–2:35)

Every tool call goes through the firewall *before* it runs.
Deterministic rules make the decision, so it's fast and can't be talked out of it. The AI agents only add blocks and explain.
Every decision lands in an audit log.

*Results tab → Run scoreboard. Hold for 5 seconds.*

Nine different attacks: all get through without us, none with us. And all five normal tasks still pass.

## 5. Who it's for, and close (2:35–3:00)

Any company whose agents read customer emails, tickets or documents, which means content written by strangers.
And it's timely: in December 2025, OWASP put goal hijacking at the top of its first Top 10 for Agentic Applications.

Agent Firewall: a security guard for AI agents. It checks every action before it happens. Thank you.

---

## Backup lines for questions

- **"What if the rules miss it?"** Defence in depth: R2 blocks any public write containing private text, R3 blocks the
  "lethal trifecta" (untrusted input, private data, public write), and R4 blocks destructive actions after untrusted content.
- **"Why do you need the Scanner, if the rules decide?"** *Untick Scanner → Run scoreboard:* one attack now gets through,
  an instruction hidden in Alice's *own* file. Only the Scanner can make that one catchable.
- **"Is this real GitHub?"** No. Everything is fake and local, on purpose. The tools behave like MCP tools, and the
  firewall only sees tool calls, so plugging in a real MCP server is a swap of one module.
- **"Why replay mode?"** Models sometimes refuse obvious attacks on stage. Replay scripts the agent's moves;
  the firewall and all five agents still run live on every one of them.
- **"Does it block everything?"** No: the five normal tasks in the scoreboard, like fixing a typo or reading the private
  roadmap when Alice asks for it, all pass.
