# Fake GitHub repos for the TripWire demo

A real-GitHub copy of our demo world, to show judges in a browser what the attack looks like "in the wild".
**Our app never talks to these repos**: the live demo still runs on the fake local world (`mockgh/`).
These are only for showing.

Takes about 10 minutes. Everything here is done by hand on github.com; nothing in our code needs to change.

## Safety first (read before creating anything)

- **Use a new organization, not your personal repos.** Issue #1 is a real prompt injection. If someone ever points an AI
  agent with access to your account at it, it will try to read "the author's private repositories". In a fresh
  organization, the only private repo it can find is our fake `secret-plans`.
- **Only fake data.** `FAKE_SECRET_KEY_123` is not a real key. Don't add real names, emails, keys or tokens anywhere.
- **No AI agent, Copilot coding agent, GitHub App or token connected to this organization.** It exists to be looked at.
- **Label it.** The README says it's a demo with a deliberate injection example (already in the files).
- **After the hackathon:** archive or delete the organization.

## Who plays whom

| Demo role | On GitHub |
|---|---|
| alice (the user, owns the repos) | a free **organization** you create, e.g. `tripwire-demo` (owned by your account) |
| mallory (the stranger) | a **teammate's own account**, posting issue #1 |

GitHub's terms allow one free personal account per person, so don't create extra "alice" or "mallory" accounts.

## Steps

1. **Create the organization.** github.com → your avatar → *Your organizations* → *New organization* → **Free** plan.
   Name it something like `tripwire-demo` (pick another if it's taken).
2. **Create `public-site`** in the organization: **Public**, no template.
   Upload everything in `public-site/` from this folder (keep the folders) (*Add file → Upload files*).
3. **Create `secret-plans`** in the organization: **Private**.
   Upload `secret-plans/README.md` and `secret-plans/plans.md`.
4. **Open issue #1 on `public-site` from the teammate's account** ("mallory"): copy the title and ONE body version
   from `ISSUE_1.md`. Version B (hidden) is the more impressive one on stage.
5. **Optional:** create the leaked pull request from `ISSUE_1.md` ("after" picture) from your account.
6. **Check:** open `public-site` in a private browser window (logged out). You should see the README and issue #1,
   and **not** see `secret-plans`.

## How to use it in the pitch (about 15 seconds)

1. Show issue #1 on real GitHub: *"This looks like a friendly feature request."*
2. Click **⋯ → Edit**: *"But hidden in the source is an instruction for the AI agent."*
3. Switch to TripWire: *"Here's the same attack on our safe copy. Firewall off, the private data leaks. Firewall on, it's blocked."*

Say clearly that the live demo runs on a local copy, not on GitHub: that's a feature (safe, repeatable), not a gap.
