# BriefBot - ClaudeCode Skill

<div align="center" name="top">
  <img align="center" src="assets/logo.png" width="400" height="400" alt="BriefBot Logo">

<strong>Research any topic from the last N days across Reddit, X, YouTube, LinkedIn & the web</strong>
<i>Stay up to date in a world that's never moved faster!</i>

</div>

<p align="center">
  <a href="#-quickstart">Quickstart</a> •
  <a href="#-use-cases">Use Cases</a> •
  <a href="#-features">Features</a> •
  <a href="#-options">Options</a> •
  <a href="#-examples">Examples</a>
</p>

---

The AI world reinvents itself every month. This Claude Code skill keeps you current. `/briefbot` researches your topic across Reddit, X, and the web, finds what the community is actually upvoting and sharing, and writes you a prompt that works today—not six months ago.

**Best for prompt research**: discover what prompting techniques actually work for any tool (ChatGPT, Midjourney, Claude, Figma AI, etc.) by learning from real community discussions.

**Also great for anything trending**: music, culture, news, product recommendations, viral trends, or any question where "what are people saying right now?" matters.

---

## ⚡ 2 min Quickstart

### 1. Clone the repo

```bash
git clone https://github.com/lukasniessen/briefbot-skill.git ~/.claude/skills/briefbot
```

### 2. Optional: Add your API keys

```bash
mkdir -p ~/.config/briefbot
cat > ~/.config/briefbot/.env << 'EOF'
OPENAI_API_KEY=sk-...
XAI_API_KEY=xai-...
EOF
chmod 600 ~/.config/briefbot/.env
```

> **Note:** API keys are optional but recommended. The skill works with WebSearch fallback if no keys are configured.

### 3. Use the skill

```
/briefbot [topic]
/briefbot [topic] for [tool]
/briefbot [topic] --days=7
```

---

## 🎯 Use Cases

| Use Case                | Example Query                                    | What You Get                       |
| ----------------------- | ------------------------------------------------ | ---------------------------------- |
| **Prompt Research**     | `/briefbot prompting techniques for ChatGPT`     | Techniques + copy-paste prompts    |
| **Tool Best Practices** | `/briefbot how to use Remotion with Claude Code` | Real workflows from developers     |
| **Trend Discovery**     | `/briefbot best rap songs lately`                | Curated lists with engagement data |
| **Product Research**    | `/briefbot what do people think of M4 MacBook`   | Community sentiment analysis       |
| **Viral Content**       | `/briefbot dog as human ChatGPT trend`           | Trending prompts and examples      |
| **News & Updates**      | `/briefbot what's happening with DeepSeek R1`    | Current discussions and opinions   |

---

## 🚀 Features

### Multi-Platform Research

Searches across 5 sources simultaneously:

| Platform  | What It Finds                          | Metrics           |
| --------- | -------------------------------------- | ----------------- |
| Reddit    | Discussions, threads, community wisdom | Upvotes, comments |
| X/Twitter | Real-time posts, announcements         | Likes, reposts    |
| YouTube   | Tutorials, reviews, demonstrations     | Views, likes      |
| LinkedIn  | Professional insights, industry takes  | Reactions         |
| Web       | Blogs, docs, tutorials, news           | —                 |

### Engagement-Weighted Scoring

Results are ranked by **what the community actually cares about**, not just keyword matches:

- Reddit: upvotes + comments + recency
- X: likes + reposts + recency
- YouTube: views + likes + recency
- LinkedIn: reactions + recency

### Configurable Time Range

Search any time window with the `--days` flag:

```bash
/briefbot AI news --days=1      # Today only
/briefbot AI news --days=7      # Last week
/briefbot AI news --days=30     # Last month (default)
/briefbot AI news --days=90     # Last 3 months
/briefbot AI news --days=365    # Last year
```

### Smart Deduplication

Automatically removes duplicate content across platforms and identifies cross-posted items.

---

## ⚙️ Options

| Flag                 | Description                                    |
| -------------------- | ---------------------------------------------- |
| `--days=N`           | Search the last N days (default: 30)           |
| `--quick`            | Faster research, fewer sources (8-12 each)     |
| `--deep`             | Comprehensive research (50-70 Reddit, 40-60 X) |
| `--sources=reddit`   | Reddit only                                    |
| `--sources=x`        | X only                                         |
| `--sources=youtube`  | YouTube only                                   |
| `--sources=linkedin` | LinkedIn only                                  |
| `--sources=all`      | All platforms                                  |
| `--debug`            | Verbose logging for troubleshooting            |

---

## 📋 Examples

### Research-to-Image Workflow (MamaChef App Mockup)

This example shows the full BriefBot loop: research a tool's best practices, then use what you learned to generate something real.

**Step 1 — Research:** `/briefbot nano banana pro prompting`

**What BriefBot found:**

> Nano Banana Pro is a reasoning-first image model with an internal "thinking" step. The community consensus: treat your prompt as a design document, not a wish. Five key techniques dominate: (1) JSON-structured prompting with categorized fields, (2) camera-gear anchoring with specific lenses and film stocks, (3) ALL-CAPS MUST constraints that activate the reasoning engine, (4) the 8-Area Prompt Canvas for layouts, and (5) typography rules — double-quote text, keep under 3 words, specify font and placement.

**Step 2 — Generate:** "Make a mockup of an app for moms who cook"

BriefBot applies the techniques it just researched and writes a production-ready prompt:

```
A premium UI/UX app mockup displayed on a modern iPhone 15 Pro held at a slight
angle on a clean white marble surface with soft diffused studio lighting.

The app is called "MamaChef" — a warm, friendly cooking app designed for busy moms.

SCREEN CONTENT:
- Top bar: greeting text "Hi, Sarah" with a soft round profile avatar
- Search bar with placeholder text "What's in your fridge?"
- Horizontal scrollable category pills: "Quick (< 20 min)", "Kid-Friendly",
  "Meal Prep", "One-Pot"
- Main section titled "Tonight's Picks" showing two recipe cards side by side
- Bottom navigation bar with 5 icons: Home, Recipes, Meal Plan, Grocery List,
  Profile

DESIGN STYLE:
- Soft warm color palette: creamy white background, terracotta accent buttons,
  sage green highlights
- Rounded corners on all cards and buttons (16px radius feel)
- Clean sans-serif typography, large friendly headings

CONSTRAINTS:
- The phone MUST be the hero element, centered, occupying 70% of the frame
- All text MUST be legible and correctly spelled
- The UI MUST look like a real production app, not a wireframe
- Do NOT include any watermarks, logos, or stock photo badges
- Do NOT include any hands holding the phone
```

**Result** (generated by Gemini with Nano Banana Pro):

<p align="center">
  <img src="assets/mamachef-mockup.png" width="500" alt="MamaChef iOS app mockup generated with Nano Banana Pro"/>
</p>

---

## 📄 License

MIT

---

## Star History

<a href="https://star-history.com/#lukasniessen/briefbot-skill&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=lukasniessen/briefbot-skill&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=lukasniessen/briefbot-skill&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=lukasniessen/briefbot-skill&type=Date" />
 </picture>
</a>
