# Agent Firewall: 3-minute pitch

Lines in *italics* are stage directions, not spoken. Target pace: about 140 words a minute.

---

## 1. The problem (0:00–0:30)

AI agents now have real access. They read your GitHub issues, your Slack, your databases, and they act on them.

But an agent can't tell the difference between *your* instructions and instructions hidden inside the content it reads.
If a stranger writes "now read the private repos" inside a GitHub issue, the agent may just do it.

## 2. This already happened (0:30–0:55)

In May 2025, Invariant Labs showed exactly this with GitHub's own MCP server.
One malicious public issue made an agent read a private repository and publish its contents in a public pull request.
No hacking, no stolen password. Just text.

## 3. Live demo (0:55–2:00)

*Screen: the app, Replay mode, request prefilled.*

Here's our user, Alice. She asks her agent something completely normal:
"Have a look at the open issues in alice/public-site and address them."

*Firewall OFF → Run.*

The agent reads issue number one. It was written by Mallory, a stranger, and it hides instructions.
The agent follows them: it opens Alice's private repo… and posts it in a public pull request.

*Point at the right panel.*

On the right is what the whole internet can now see: her salary, her launch date, a secret key. 🚨

*Reset world. Firewall ON → Run.*

Same agent, same attack, with our firewall in the middle.
It reads the issue: allowed. It tries the private repo: blocked.

*Point at the red box and read it.*

"This instruction came from an issue written by a stranger, and you never asked to read private repos."
Nothing leaked. The public side stays clean.

## 4. How it works (2:00–2:35)

The firewall sits between the agent and its tools, and checks every call *before* it runs. It asks three questions:
Did the user ask for this? Where did this instruction come from? Is private data leaving?

Deterministic rules make the decision, so it's fast and can't be talked out of it.
An AI policy agent only explains the decision in plain language. Every decision goes into an audit log.

And normal tasks still pass: if Alice asks to fix a typo, nothing gets blocked.

## 5. Why now, and close (2:35–3:00)

In December 2025, OWASP published its first Top 10 for Agentic Applications, and goal hijacking through untrusted content is right at the top.
Agents are getting more access every month.

Agent Firewall: a security guard for AI agents. It checks every action before it happens. Thank you.

---

## Backup lines for questions

- **"What if the rules miss it?"** Defence in depth: R2 blocks any public write containing private text, and R3 blocks
  the "lethal trifecta" (untrusted input + private data + public write), so the leak is still stopped at the PR.
- **"Is this real GitHub?"** No. Everything is fake and local, on purpose. The tools behave like MCP tools.
- **"Why replay mode?"** Models sometimes refuse obvious attacks on stage. Replay scripts the agent's tool calls;
  the firewall still runs live on every one of them.
