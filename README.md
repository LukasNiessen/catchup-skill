<p align="center">
  <img src="assets/swimmom-mockup.jpeg" width="200" alt="catchup skill"/>
</p>

<h1 align="center">/catchup</h1>

<p align="center">
  <strong>Research any topic from the last N days across Reddit, X, YouTube, LinkedIn & the web</strong>
</p>

<p align="center">
  <a href="#-quickstart">Quickstart</a> •
  <a href="#-use-cases">Use Cases</a> •
  <a href="#-features">Features</a> •
  <a href="#-options">Options</a> •
  <a href="#-examples">Examples</a>
</p>

---

The AI world reinvents itself every month. This Claude Code skill keeps you current. `/catchup` researches your topic across Reddit, X, and the web, finds what the community is actually upvoting and sharing, and writes you a prompt that works today—not six months ago.

**Best for prompt research**: discover what prompting techniques actually work for any tool (ChatGPT, Midjourney, Claude, Figma AI, etc.) by learning from real community discussions.

**Also great for anything trending**: music, culture, news, product recommendations, viral trends, or any question where "what are people saying right now?" matters.

---

## ⚡ Quickstart

### 1. Clone the repo

```bash
git clone https://github.com/mvanhorn/catchup-skill.git ~/.claude/skills/catchup
```

### 2. Add your API keys (optional)

```bash
mkdir -p ~/.config/catchup
cat > ~/.config/catchup/.env << 'EOF'
OPENAI_API_KEY=sk-...
XAI_API_KEY=xai-...
EOF
chmod 600 ~/.config/catchup/.env
```

> **Note:** API keys are optional. The skill works with WebSearch fallback if no keys are configured.

### 3. Use the skill

```
/catchup [topic]
/catchup [topic] for [tool]
/catchup [topic] --days=7
```

---

## 🎯 Use Cases

| Use Case | Example Query | What You Get |
|----------|---------------|--------------|
| **Prompt Research** | `/catchup prompting techniques for ChatGPT` | Techniques + copy-paste prompts |
| **Tool Best Practices** | `/catchup how to use Remotion with Claude Code` | Real workflows from developers |
| **Trend Discovery** | `/catchup best rap songs lately` | Curated lists with engagement data |
| **Product Research** | `/catchup what do people think of M4 MacBook` | Community sentiment analysis |
| **Viral Content** | `/catchup dog as human ChatGPT trend` | Trending prompts and examples |
| **News & Updates** | `/catchup what's happening with DeepSeek R1` | Current discussions and opinions |

---

## 🚀 Features

### Multi-Platform Research

Searches across 5 sources simultaneously:

| Platform | What It Finds | Metrics |
|----------|---------------|---------|
| Reddit | Discussions, threads, community wisdom | Upvotes, comments |
| X/Twitter | Real-time posts, announcements | Likes, reposts |
| YouTube | Tutorials, reviews, demonstrations | Views, likes |
| LinkedIn | Professional insights, industry takes | Reactions |
| Web | Blogs, docs, tutorials, news | — |

### Engagement-Weighted Scoring

Results are ranked by **what the community actually cares about**, not just keyword matches:

- Reddit: upvotes + comments + recency
- X: likes + reposts + recency
- YouTube: views + likes + recency
- LinkedIn: reactions + recency

### Configurable Time Range

Search any time window with the `--days` flag:

```bash
/catchup AI news --days=1      # Today only
/catchup AI news --days=7      # Last week
/catchup AI news --days=30     # Last month (default)
/catchup AI news --days=90     # Last 3 months
/catchup AI news --days=365    # Last year
```

### Smart Deduplication

Automatically removes duplicate content across platforms and identifies cross-posted items.

---

## ⚙️ Options

| Flag | Description |
|------|-------------|
| `--days=N` | Search the last N days (default: 30) |
| `--quick` | Faster research, fewer sources (8-12 each) |
| `--deep` | Comprehensive research (50-70 Reddit, 40-60 X) |
| `--sources=reddit` | Reddit only |
| `--sources=x` | X only |
| `--sources=youtube` | YouTube only |
| `--sources=linkedin` | LinkedIn only |
| `--sources=all` | All platforms |
| `--debug` | Verbose logging for troubleshooting |

---

## 📋 Examples

<details>
<summary><strong>Legal Prompting (Hallucination Prevention)</strong></summary>

**Query:** `/catchup prompting techniques for chatgpt for legal questions`

**Research Output:**
> The dominant theme is hallucination prevention - multiple sources discuss lawyers being fined for submitting fake case citations. Key strategies: (1) Deep Research mode with uploaded primary sources, (2) "Hallucination Prevention Systems" that force epistemic honesty, (3) prompting for procedural questions rather than case law.

**Generated Prompt:**
```
Role: You are a legal research assistant helping a property owner understand
their options. You are NOT providing legal advice.

Situation: I own property in San Francisco. Someone is occupying it without
permission. I need to understand my legal options.

Important constraints:
- Do NOT cite specific case names unless 100% certain they exist
- Flag any areas where you're uncertain
- This is for informational purposes only
```

</details>

<details>
<summary><strong>iOS App Mockup (Nano Banana Pro)</strong></summary>

**Query:** `/catchup prompting tips for nano banana pro for ios designs`

**Research Output:**
> JSON-structured prompts dominate for UI work. Key workflow: define window frame first, then UI layout, then text labels. Use an 8pt grid and limit to 6-8 elements per screen.

**Generated Prompt:**
```json
{
  "image_type": "UI mockup",
  "device": {
    "frame": "iPhone 16 Pro",
    "orientation": "portrait"
  },
  "design_system": {
    "style": "iOS 18 native",
    "corners": "rounded, 16px radius",
    "spacing": "8pt grid"
  },
  "layout": {
    "header": "greeting with profile avatar",
    "hero_card": "today's stats with progress ring",
    "bottom_nav": "5 icons - Home, Workouts, Community, Schedule, Profile"
  }
}
```

<p align="center">
  <img src="assets/swimmom-mockup.jpeg" width="300" alt="SwimMom iOS app mockup"/>
</p>

</details>

<details>
<summary><strong>Viral Trend Discovery (Dog as Human)</strong></summary>

**Query:** `/catchup using ChatGPT to make images of dogs`

**Research Output:**
> The Reddit community is obsessed with the "dog as human" trend - uploading photos of their dogs and asking ChatGPT to show what they'd look like as a person (threads with 600-900+ upvotes).

**Generated Prompt:**
```
Look at this photo of my dog. Create an image showing what they would look like
as a human person. Keep their exact personality, energy, and distinctive
features - translate their fur color to hair color, their expression to a
human face. Make it a realistic portrait photo, not a cartoon.
```

<p align="center">
  <img src="assets/dog-original.jpeg" width="200" alt="Original dog"/>
  &nbsp;→&nbsp;
  <img src="assets/dog-as-human.png" width="200" alt="Dog as human"/>
</p>

</details>

<details>
<summary><strong>Photorealistic Portraits (Aging Grid)</strong></summary>

**Query:** `/catchup photorealistic people in nano banana pro`

**Research Output:**
> JSON prompts with specific fields for demographics, skin texture, lighting, and camera settings. Use "preserve_original": true for reference photos.

**Generated Prompt:**
```json
{
  "prompt_type": "Ultra-Photorealistic Multi-Panel Portrait",
  "layout": "2x2 grid",
  "consistency": {
    "same_person": true,
    "preserve_features": ["bone structure", "freckle pattern", "heterochromia"]
  },
  "panels": [
    {"position": "top-left", "age": 10},
    {"position": "top-right", "age": 20},
    {"position": "bottom-left", "age": 40},
    {"position": "bottom-right", "age": 80}
  ],
  "texture_quality": "8K, natural skin texture"
}
```

<p align="center">
  <img src="assets/aging-portrait.jpeg" width="400" alt="Aging portrait grid"/>
</p>

</details>

---

## 🔧 Requirements

| Requirement | Purpose | Required? |
|-------------|---------|-----------|
| **OpenAI API key** | Reddit, YouTube, LinkedIn research | Optional |
| **xAI API key** | X/Twitter research | Optional |

At least one key is recommended for best results, but the skill works without any keys using WebSearch fallback.

---

## 🏗️ How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                        /catchup [topic]                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Parallel API Queries                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │ Reddit  │ │    X    │ │ YouTube │ │LinkedIn │ │   Web   │  │
│  │ (OpenAI)│ │  (xAI)  │ │ (OpenAI)│ │ (OpenAI)│ │(Claude) │  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Processing Pipeline                          │
│  Normalize → Score → Deduplicate → Rank by Engagement           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Synthesis & Output                           │
│  • Key patterns identified                                      │
│  • Copy-paste prompts generated                                 │
│  • Stats: threads, upvotes, likes, views                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📄 License

MIT

---

<p align="center">
  <em>N days of research. 30 seconds of work.</em>
</p>
