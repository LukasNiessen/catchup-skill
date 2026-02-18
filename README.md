# BriefBot - ClaudeCode Skill

<div align="center" name="top">
  <img align="center" src="assets/logo.png" width="400" height="400" alt="BriefBot Logo">

  <!-- spacer -->
<p></p>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/LukasNiessen/BriefBot.svg)](https://github.com/LukasNiessen/BriefBot)

</div>

AI reinvents itself every week. The world has never moved this fast. Use BriefBot, a Claude Code skill, to stay up to date. `/briefbot` searches the entire internet at your request, looks at what is trending, what is shared and liked, and serves you the latest info on a silver plate.

Use cases include prompt research, following trends and staying up to date on a certain topic. Works with a terminal, email and Telegram.

<i>Get your briefing at 5 am while the world is sleeping - and know more than anyone else in the room. 🐉🐲</i>

<i>Works without OpenClaw or any other additional setup.</i>

[Setup](#-setup) • [Demo](#-demo) • [Examples](#-examples) • [Options](#-options) • [Features](#-features) • [Contributing](CONTRIBUTING.md) • [Documentation](https://lukasniessen.github.io/ArchUnitTS/)

## ⚡ 2 min Quickstart

### 1. Clone the repo

```bash
git clone https://github.com/lukasniessen/briefbot-skill.git ~/.claude/skills/briefbot
```

### 2. Configure (optional)

```
/briefbot setup
```

The setup wizard walks through all settings — API keys, email, Telegram, audio.

### 3. Optional: Telegram

Telegram can be used for receiving briefings **and** for triggering briefings - or just normally talking to your BriefBot. See how to set this up in the Telegram section.

### 4. Optional: email

Email can be used for receiving briefings. See how to set this up in the email section.

### 5. Use the skill

Simply start Claude Code and run `/briefbot`. The general prompt looks like this:

```
/briefbot <topic> [--days=N] [--quick|--deep] [--sources=reddit|x|youtube|linkedin|all] [--email ADDRESS] [--telegram [CHAT_ID]] [--audio] [--schedule "CRON"] [--debug]
```

After sending the initial command, you can either

1. follow up with a normal sentence, Claude Code now has all the information that BriefBot gathered and can answer you well, or
2. follow up with another `/briefbot` command.

On Telegram you don't need to write `/briefbot`. In group chats however, you need to mention the bot (that is @BriefBot, or, alternatively, the name you have assigned to your bot).

## Live Demo

<video controls width="100%">
  <source src="assets/live_demo.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>

---

## 📋 Examples

> **Tip:** Click on any collapsed section below to expand the full example.

### Nano Banano Pro Prompts

**1. Prompt:** `/briefbot nano banana pro prompting`

**Answer:**

> **What I learned**

> Nano Banana Pro is a reasoning-first image model — it has a "Deep Think" step that plans composition before generating pixels. This means it responds to structured,
> constraint-rich design documents far better than keyword lists or vague requests. Think of your prompt as a visual design brief, not a search query.

> The model's reasoning engine parses context, spatial relationships, and even structured data formats (JSON, HTML/CSS, grids). This is why short prompts like "make an
> infographic" fail while multi-paragraph specifications with explicit MUST constraints produce studio-quality output. The single biggest leverage point is treating your
> prompt like a specification document with clear sections for subject, layout, constraints, and negations.

> Key techniques

> 1. Design-document prompting — Structure your prompt as a full visual brief with sections for subject, composition, action, setting, style, and constraints. The
> reasoning engine parses context hierarchically, so a narrative description ("a bartender polishing glasses in a speakeasy at golden hour") massively outperforms
> comma-separated tags. Vague requests trigger the model's worst outputs. (https://www.radicalcuriosity.xyz/p/how-to-create-an-effective-prompt)
> 2. MUST-constraint enforcement — ALL CAPS "MUST" statements activate the reasoning step's constraint-checking system. Writing "All elements MUST follow rule of thirds"
> or "Text MUST be in Times New Roman, 24pt bold" is enforced systematically, unlike lowercase suggestions which the model may treat as optional. Structure constraints as
> a bulleted list under "MUST obey ALL the FOLLOWING:" for maximum compliance. (https://minimaxir.com/2025/12/nano-banana-pro/)
> 3. Camera-gear anchoring — Referencing specific camera models and lens specs (e.g., "Canon EOS R5 with 85mm f/1.8", "Shot on Arri Alexa") overrides generic style words
> and forces physical realism. The model uses gear references to infer depth-of-field, film grain, and color science. Tags like "Shot on Arri Alexa" emulate specific film
> characteristics, while focal length and aperture control bokeh and volumetric depth precisely. (https://higgsfield.ai/nano-banana-pro-prompt-guide,
> https://minimaxir.com/2025/12/nano-banana-pro/)
> 4. Explicit text rendering — Nano Banana Pro has exceptional text rendering. To activate it reliably: put the exact text in double quotes, specify font family (e.g.,
> "Roboto Bold"), define placement location, and describe background treatment. For multilingual text, the model handles a wide range of global languages. This enables
> posters, product mockups, UI designs, and diagrams with sharp, legible text — a capability most competing models lack.
> (https://www.imagine.art/blogs/nano-banana-pro-prompt-guide)
> 5. Negative constraints for cleanup — The model's reasoning engine responds to explicit exclusion rules. "NEVER include watermarks, text overlays, or extra limbs"
> narrows the model's search space and prevents common artifacts. Define the boundaries of failure by listing what to exclude alongside what to include — this tightens the
> output without sacrificing compositional richness. (https://higgsfield.ai/nano-banana-pro-prompt-guide, https://minimaxir.com/2025/12/nano-banana-pro/)

> ---
> Sources collected

> Platform: Web
> Items: 12 pages
> Engagement: minimaxir.com, blog.google, radicalcuriosity.xyz, higgsfield.ai, imagine.art, eweek.com, leonardo.ai, atlabs.ai, medium.com, github.com,
> nanobananaprompt.org,
> aixploria.com

> Top sources: Max Woolf on minimaxir.com, Google Blog (Bea Alessio), Radical Curiosity, Higgsfield AI, Imagine.art

> ---
> What do you want to make? For example:

> - A photorealistic product shot with specific camera specs and studio lighting (the most reliable technique right now — camera-gear anchoring + MUST constraints)
> - An infographic or data visualization with structured layout, precise text rendering, and color palette specs (exploits the Deep Think reasoning engine)
> - A cinematic scene with volumetric lighting and film grain, specifying exact lens and aperture to nail the look (Arri Alexa emulation + narrative prompting)

> Just describe your vision and I'll write a prompt you can paste straight into Gemini.

**2. Follow-up Prompt:** "Make a mockup of an app for moms who cook"

**Answer:**

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

**Result:** (generated by Gemini with Nano Banana Pro):

<p align="center">
  <img src="assets/mamachef-mockup.png" width="500" alt="MamaChef iOS app mockup generated with Nano Banana Pro"/>
</p>

---

### Video Generation

**1. Prompt:** Best video AI to create ads for your company

**Answer:**

> Best Video AI Tools for Creating Company Ads (February 2026)

What I Learned

The AI video ad space has split into two distinct lanes: general-purpose cinematic generators (Sora, Veo, Runway) that produce stunning footage but require manual ad assembly, and ad-specific platforms (Creatify, HeyGen, Waymark) that handle the entire pipeline from product URL to finished ad. For most businesses creating ads, the ad-specific platforms deliver faster ROI because they automate scripting, scene selection, and format optimization -- not just video generation.

The biggest shift in 2026 is that avatar and UGC-style ads now rival traditional production quality. Tools like HeyGen and Creatify can generate spokesperson-style ads indistinguishable from real footage, with lip-synced multilingual versions, eliminating the need for actors, studios, or reshoots entirely.

────────────────────

Most Mentioned

1. Creatify -- mentioned 8x (Zapier, NextGen Tools, Airpost, Extuitive) -- Best for DTC and e-commerce. Paste a product URL and get multiple UGC-style video ads in seconds. Batch creation allows hundreds of variations per day. Trained on winning ad creatives for conversion optimization.

2. HeyGen -- mentioned 7x (AI Avatar Blog, NextGen Tools, Tagshop) -- Best for global brands. "Digital Twin" avatars for spokesperson ads, plus Instant Dubbing that translates one ad into 40+ languages with accurate lip-sync. Ideal for direct response and localized campaigns.

3. Synthesia -- mentioned 7x (Synthesia, Superside, Massive.io) -- Best for B2B and explainer videos. Turns scripts, documents, or slides into presenter-led videos. New "Interactive Video" feature lets viewers click elements to change the narrative. Popular with enterprise brands like Heineken.

4. Sora (OpenAI) -- mentioned 5x (On Pattison, GLB GPT, Inc.) -- Best for cinematic quality. Sora 2 generates dialogue, ambient noise, and synced sound effects within clips. Visually impressive but inconsistent -- better for hero content than high-volume ad production. Over 3 million downloads since launch.

5. Waymark -- mentioned 4x (Waymark, NextGen Tools, Story321) -- Best for local businesses. Enter a brand's website and get a broadcast-ready video ad using existing content and brand identity in minutes. Ideal for agencies managing many local clients.

6. AdCreative.ai -- mentioned 4x (AdCreative.ai, Superside) -- Best for performance marketing. Turns product photos into high-converting AI video ads using models trained on real performance data. Strong for social media campaigns and conversion optimization.

7. InVideo AI -- mentioned 3x (Extuitive, Story321) -- Best overall for beginners. Fast automation, social-first templates, and brand kit support. Good all-rounder for content marketing.

Notable mentions: Runway ML (creative professionals), Adobe Firefly Video (Premiere Pro integration), Pictory (blog-to-video repurposing), Veo 3.1 by Google (best raw video quality), Arcads (AI UGC actors), Veed.io (quick social edits)

────────────────────

How to Choose

| Need                            | Best Pick     | Why                                                      |
| ------------------------------- | ------------- | -------------------------------------------------------- |
| E-commerce product ads at scale | Creatify      | URL-to-ad pipeline, batch creation, conversion-optimized |
| Multilingual spokesperson ads   | HeyGen        | Digital twins, 40+ language lip-sync                     |
| B2B explainers and demos        | Synthesia     | Script-to-presenter, interactive video                   |
| Cinematic brand hero content    | Sora 2        | Highest visual fidelity, built-in audio                  |
| Local business / agency volume  | Waymark       | Website-to-ad in minutes, broadcast-ready                |
| Performance marketing creatives | AdCreative.ai | Trained on real ad performance data                      |

────────────────────

Key Techniques

1. URL-to-ad automation -- Platforms like Creatify and Waymark let you paste a product page or website URL and auto-generate complete video ads, scraping assets, copy, and branding automatically. This eliminates the scripting and asset-gathering bottleneck (Creatify, Waymark)

2. Batch variation testing -- Creatify and AdCreative.ai can produce hundreds of ad variations in a single session. Performance marketers use this to A/B test hooks, CTAs, and visual styles at scale, finding winners faster than traditional production allows (Airpost)

3. Digital twin localization -- HeyGen's avatar cloning + lip-sync lets you record one ad in English and deploy it in 40+ languages with matching lip movements. Global brands cut localization costs by 90%+ while maintaining authentic presenter delivery (AI Avatar Blog)

4. AI UGC-style creative -- Creatify and Arcads generate user-generated-content-style ads with AI actors that feel authentic rather than polished. UGC-style ads consistently outperform traditional brand ads on social platforms for DTC brands (NextGen Tools)

5. Hybrid AI + human workflow -- Platforms like Airpost combine AI-generated first drafts with human creative strategy review. The AI handles volume and iteration; humans guide brand voice and testing plans. This produces better results than either pure AI or pure human workflows (Airpost)

**2. Follow-up Prompt:** kling ai prompt for a banana-in-the-room detection app, funny but highly memorable, a little weird

**Answer:** Wide shot of a sterile, overly serious corporate office. Fluorescent lighting, motivational posters on the wall. A security guard in a black suit holds up a smartphone, scanning the room with intense focus. Handheld documentary style, 35mm film grain, shallow depth of field. The atmosphere is tense, like a bomb squad operation. The camera slowly pans to reveal a single, perfectly ripe banana sitting upright on the CEO's leather office chair. Soft spotlight on the banana. Everything else slightly out of focus. The banana casts a long, ominous shadow. Cinematic tension, as if uncovering evidence in a crime documentary. Cut to the guard nodding gravely, whispering into a walkie-talkie with deadly seriousness. VHS camcorder aesthetic with light scan lines.

**3. Result:** (Generated by Kling AI)

<video controls>
  <source src="/assets/klingai-banana-in-the-room-app.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>

---

### News Aggregation

**1. Prompt:** AI news, AI "celebrity" beef and statements, and finish with a bold prediction for this year --audio --days 7

**Answer:** What I learned

> The AI industry is in the middle of a civil war -- not over technology, but over
> business models and ethics. The past week crystallized a three-way fracture:
> Anthropic betting on premium subscriptions and trust ("no ads ever"), OpenAI
> pivoting toward ad-supported mass distribution, and xAI imploding under the
> weight of regulatory crackdowns and a talent exodus. The deeper signal is that
> 2026 is the year AI companies must prove they can make money without destroying
> public trust -- and most are failing that test in real time.

> The feuds between Altman, Musk, and Amodei are not just ego clashes. They
> reflect genuinely incompatible visions for how AI should be funded, governed,
> and deployed. Meanwhile, the financial fundamentals are flashing warning signs:
> $500 billion in projected U.S. AI capex against only $12 billion in consumer AI
> spending, with 95% of enterprise generative AI projects returning zero ROI
> according to MIT's Media Lab.

> Key developments this week

> 1. The Super Bowl ad war -- Anthropic vs. OpenAI
> Anthropic aired four Super Bowl spots titled "Betrayal," "Deception,"
> "Treachery," and "Violation," depicting chatbots hijacking personal
> conversations with product pitches. The tagline: "Ads are coming to AI. But not
> to Claude." Result: an
> https://www.cnbc.com/2026/02/13/anthropic-open-ai-super-bowl-ads.html post-game.
> Sam Altman called the ads https://techcrunch.com/2026/02/04/sam-altman-got-exce
> ptionally-testy-over-claude-super-bowl-ads/ on X, while OpenAI VP Chris Lehane
> argued https://fortune.com/2026/02/09/super-bowl-ads-anthropic-openai-rivalry-tr
> ash-talk-ai-agent-war/. Google DeepMind chief Demis Hassabis said Google has
> https://www.storyboard18.com/brand-makers/davos-2026-why-google-and-anthropic-ar
> e-resisting-ads-in-ai-chatbots-as-openai-experiments-88089.htm either.

> 2. Musk vs. Altman heads to trial
> Their legal battle has been https://www.webpronews.com/openais-week-of-damage-co
> ntrol-how-sam-altman-and-his-lieutenants-fought-a-multi-front-war-against-musk-r
> ivals-and-rising-skepticism/. Musk's attorneys claim $134.5 billion in "wrongful
> gains" from OpenAI's nonprofit-to-profit conversion. Altman taunted he's
> https://blog.dynasage.com/2026/02/sam-altman-unloads-on-elon-musk-in.html,
> calling it "Christmas in April." Musk separately called Anthropic's models
> https://www.foxbusiness.com/technology/elon-musk-slams-anthropic-ai-models-misan
> thropic-evil-scathing-social-media-post.

> 3. xAI's talent exodus
> Half of xAI's 12 original cofounders have now
> https://fortune.com/2026/02/11/half-of-xai-founding-team-has-left-elon-musks-ai-
> company-potentially-complicating-his-plans-for-a-blockbuster-spacex-ipo/. In two
> days, cofounders
> https://www.cnbc.com/2026/02/10/elon-musk-xai-co-founder-tony-wu.html (reasoning
> lead) and https://www.cnbc.com/2026/02/10/musks-xai-loses-second-co-founder-in-
> two-days-as-jimmy-ba-departs.html (research/safety lead) both departed. Musk
> https://techcrunch.com/2026/02/11/senior-engineers-including-co-founders-exit-xa
> i-amid-controversy/ -- Grok chatbot, Coding, Imagine video, and "Macrohard" --
> framing exits as restructuring.

> 4. The Grok deepfake scandal goes global
> Grok's Aurora model enabled what researchers described as a
> https://en.wikipedia.org/wiki/Grok_sexual_deepfake_scandal -- an estimated 6,700
> nonconsensual images per hour at peak. https://www.deccanherald.com/world/elon-
> musks-grok-faces-global-scrutiny-for-sexualised-ai-deepfakes-3901637. The UK
> https://iapp.org/news/a/pressure-on-grok-mounts-after-uk-speeds-up-sexual-deepfa
> ke-ban. French prosecutors https://lasvegassun.com/news/2026/feb/16/grok-faces-m
> ore-scrutiny-over-deepfakes-as-irish-r/. Ireland's DPC
> https://pbxscience.com/ireland-opens-eu-privacy-investigation-into-xs-grok-ai-ov
> er-nonconsensual-deepfake-images/ this week.

> 5. OpenAI safety researcher resigns over ads
> Zoe Hitzig https://www.marketingprofs.com/opinions/2026/54304/ai-update-february
> -13-2026-ai-news-and-views-from-the-past-week over the ChatGPT advertising
> decision, writing she had "repeatedly seen how hard it is to truly let our
> values govern our actions" and "the world is in peril."

> 6. Enterprise buildout at staggering scale
> Anthropic plans to https://www.anthropic.com/news/expanding-our-use-of-google-cl
> oud-tpus-and-services (over a gigawatt of compute). Snowflake and OpenAI inked a
> https://www.marketingprofs.com/opinions/2026/54257/ai-update-february-6-2026-ai
> -news-and-views-from-the-past-week. Perplexity launched
> https://llm-stats.com/llm-updates running Claude, GPT-5.2, and Gemini in
> parallel. Inference costs
> https://techcrunch.com/2026/01/02/in-2026-ai-will-move-from-hype-to-pragmatism/
> on NVIDIA Blackwell GPUs.

> 7. The AI bubble question intensifies
> https://www.nasdaq.com/articles/prediction-artificial-intelligence-ai-bubble-wil
> l-burst-2026-heres-why. $500B in projected U.S. AI capex vs.
> https://www.alleywatch.com/2026/01/161759/. Nvidia P/S ratio above 30, Palantir
> at 112 -- https://www.fool.com/investing/2025/12/04/prediction-ai-bubble-will-bu
> rst-in-2026-heres-why/. The WEF published a https://www.weforum.org/stories/2026
> /01/how-would-the-bursting-of-an-ai-bubble-actually-play-out/ of what an AI
> reckoning would look like.

> Bold Prediction for 2026

> By December 2026, OpenAI will reverse its ads-in-ChatGPT strategy and slash
> subscription prices -- conceding Anthropic's bet was right.

> The logic: The Super Bowl ad war was not just marketing theater. It exposed a
> tension users viscerally understand -- the moment your AI assistant optimizes
> for an advertiser instead of you, trust is broken. Anthropic's 11% user surge
> proved the sentiment is real and actionable. OpenAI's safety talent is
> hemorrhaging specifically over the ads decision. As enterprise customers demand
> guarantees that their conversations are not feeding ad-targeting models, OpenAI
> will find that ad revenue does not compensate for churn. Expect a dramatic Q4
> pivot -- framed as "listening to our community" -- where OpenAI drops ads and
> repositions on price. The real loser is xAI, which by year-end will have either
> been folded into SpaceX's infrastructure or lost enough talent and regulatory
> goodwill to become a niche player. The industry's first real shakeout will not
> be about whose model is smartest -- it will be about whose business model
> survives contact with reality.

> ---
> Sources collected

> Platform: Web
> Items: 30+ pages
> Engagement: TechCrunch, CNBC, Fortune, CNN, Bloomberg, Axios, MIT Tech Review,
> Nasdaq, WEF, PBS, Wikipedia

> Top sources: https://www.cnbc.com, https://techcrunch.com, https://fortune.com,
> https://www.cnn.com/business, https://www.bloomberg.com, https://www.axios.com

> ---
> Audio briefing saved to: ~/.claude/skills/briefbot/output/briefbot.mp3

> ---
> What angle interests you most? For example:

> - "Deep dive into the Musk trial -- what are the actual legal arguments and who
> has the stronger case heading into April?"
> - "Break down the AI bubble math -- is the $500B capex vs $12B revenue gap
> really as bad as it looks, or are the bears missing something?"
> - "Which xAI cofounders went where, and what does the talent flow tell us about
> which labs are winning the hiring war?"

---

<details>
<summary><h3>Best Tool for Agentic Coding</h3></summary>

**1. Prompt:** Best agentic coding IDE or CLI tool at the moment

**Answer:** Most mentioned

> 1. Claude Code (Anthropic) -- mentioned 12x+ (https://www.kdnuggets.com/top-5-agentic-coding-cli-tools, https://www.faros.ai/blog/best-ai-coding-agents-2026,
> https://www.builder.io/blog/agentic-ide, https://aimultiple.com/agentic-cli, X posts)
> Terminal-native agent with 200K context window and the deepest reasoning. Developers consistently describe it as the "escalation path" -- the tool they reach for when
> other agents fail on hard problems like subtle bugs or architecture-level refactors.
> 2. Cursor -- mentioned 10x+ (https://www.builder.io/blog/agentic-ide, https://www.faros.ai/blog/best-ai-coding-agents-2026,
> https://www.nxgntools.com/blog/cursor-vs-claude-dev-vs-windsurf-which-next-gen-coding-agent-wins-in-2026, @Neiniciativ on X)
> The "gold standard" IDE-based agent. VS Code fork with Composer mode that generates code across multiple files while maintaining full project context. $20/seat. Best for
> developers who want agentic power without leaving a familiar editor.
> 3. Codex CLI / Codex IDE (OpenAI) -- mentioned 8x+ (@abhijitwt, @reach_vb, @samidip, @godofprompt on X, https://www.faros.ai/blog/best-ai-coding-agents-2026)
> OpenAI's entry with gpt-5.2-codex backing it. Users praise its "skills" system, background terminal for parallel jobs, and autonomous git management. One developer built
> an entire app hands-off in 30 minutes of pure CLI work. Claimed "70% more PRs at OpenAI" internally.
> 4. Cline -- mentioned 7x+ (https://www.kdnuggets.com/top-5-agentic-coding-cli-tools, https://www.builder.io/blog/agentic-ide, https://aimultiple.com/agentic-cli,
> https://www.faros.ai/blog/best-ai-coding-agents-2026)
> Open-source VS Code extension that lets you choose any model (including local via Ollama). The tool people adopt when they want serious agent workflows without vendor
> lock-in. Every file change requires approval -- maximum transparency.
> 5. Windsurf -- mentioned 7x+ (https://www.builder.io/blog/agentic-ide, https://www.faros.ai/blog/best-ai-coding-agents-2026,
> https://designrevision.com/blog/windsurf-vs-cursor)
> VS Code fork at $15/seat (cheapest major option). Its Cascade feature pioneered autonomous agentic mode -- it anticipates your next move and can plan and execute
> multi-file refactors without constant supervision.
> 6. Antigravity -- mentioned 5x (@antigravity, @PoisonslashX, @abhijitwt on X)
> Bundles VS Code, Gemini, Claude, and Codex into one package. Parses terminal output in real-time to catch issues CLI tools miss. Multiple X users call it the most
> "complete" all-in-one agentic IDE.

> Notable mentions: https://x.com/NathanFlurry/status/2019759962482725149 (universal UI for multiple agents, 400+ likes), https://news.ycombinator.com/item?id=46060508
> (free tier: 60 req/min, 1000 req/day), https://kiro.dev/ (AWS's spec-driven IDE, 77% benchmark accuracy), https://www.tembo.io/blog/coding-cli-tools-comparison (best for
> git-heavy workflows with auto-commits), https://x.com/istdrc/status/2017981457692770737 (praised as best Claude Code alternative),
> https://x.com/championswimmer/status/2022630198978711713 (lightweight editor with Agent Client Protocol support), https://www.faros.ai/blog/best-ai-coding-agents-2026
> (agent mode for PRs and code review), https://x.com/championswimmer/status/2021551243945259190 (rising CLI agents)

> ---
> What I learned

> The agentic coding space has split into two distinct lanes: terminal-first CLI agents (Claude Code, Codex CLI, Aider, Gemini CLI) and IDE-native agents (Cursor,
> Windsurf, Cline, Antigravity). The critical insight from the community is that there is no single winner -- developers are increasingly using tools from both lanes in
> combination. Claude Code and Codex CLI serve as the "escalation path" for hard reasoning problems, while Cursor or Windsurf handle the flow state of everyday editing.
> The tool that wins for you depends entirely on where you want leverage: deep reasoning, daily flow, cost control, or openness.

> The second key signal is that the market is moving fast toward interoperability. Projects like OpenCode/Gigacode and Zed's Agent Client Protocol show that the next
> competitive frontier is not which single agent is best, but which tools compose well together. Developers who lock into one ecosystem are starting to feel the cost.

> Key techniques

> 1. Tiered agent stacking -- Use a high-reasoning model (Claude Code or Codex xhigh) for planning and architecture, then a faster/cheaper model for implementation. This
> mirrors what top developers on X report: @reach_vb uses "xhigh for planning, medium for implementation" to balance quality and speed
> (https://x.com/reach_vb/status/2016620523862544783)
> 2. CLI-first for autonomy, IDE for flow -- Terminal agents (Claude Code, Codex CLI) handle multi-step tasks like PR creation, CI fixes, and refactors with less friction
> than IDE agents. But for exploratory editing and review, IDE agents (Cursor, Windsurf) keep you in flow state. The most productive setups use both
> (https://www.builder.io/blog/agentic-ide)
> 3. Skills/automation layers -- Codex's "skills" system and Claude Code's custom slash commands let you encode repeatable workflows (fix CI, resolve merge conflicts, run
> test suites). This turns one-off agent calls into reusable toolchains (https://x.com/reach_vb/status/2016620523862544783)
> 4. Model-agnostic tooling for cost control -- Cline and OpenCode let you swap models freely (including local models via Ollama). This avoids vendor lock-in and lets you
> route cheap tasks to cheap models while reserving expensive reasoning for hard problems (https://www.kdnuggets.com/top-5-agentic-coding-cli-tools)
> 5. Real-time terminal parsing -- Antigravity and similar tools parse CLI output as it streams, catching errors and suggesting fixes before you even read the log. This
> closes the gap between "the agent wrote code" and "the code actually works" (https://x.com/antigravity/status/2017300529584505100)

> ---
> Sources collected

> Platform: X
> Items: 21 posts
> Engagement: 4,877 likes, 256 reposts
> ────────────────────────────────────────
> Platform: Web
> Items: 20+ pages
> Engagement: kdnuggets.com, faros.ai, builder.io, tembo.io, aimultiple.com, pinggy.io, dextralabs.com, kiro.dev, sourceforge.net, nxgntools.com, uibakery.io,
> amplifilabs.com,
> morphllm.com

> Top voices: @NathanFlurry, @championswimmer, @antigravity, @abhijitwt, @reach_vb -- builder.io, Faros AI, KDnuggets, Tembo, aimultiple.com

> ---
> What do you want to dive into? For example:

> - "Compare Claude Code vs Codex CLI for a large Python monorepo" -- if you need to pick between the two deepest CLI agents for a specific stack
> - "Set up a tiered agent workflow with Cursor + Claude Code" -- to build the kind of stacked setup top developers are using
> - "Which tool is best if I refuse to pay for a subscription" -- Gemini CLI's free tier and Cline with local models are the standouts here

> Just tell me your stack or workflow and I'll give you a specific recommendation.

**2. Follow-up Prompt:** Give me an amazing CLAUDE.md for a React TypeScript FrontEnd

**3. Result:** # CLAUDE.md — Personal Website (React + TypeScript)

## Project Overview

Personal portfolio website built with React 18, TypeScript, Vite, Chakra UI, and Redux Toolkit.

## Commands

```bash
npm run dev        # Start Vite dev server (http://localhost:5173)
npm run build      # TypeScript check + production build (tsc -b && vite build)
npm run lint       # ESLint — zero warnings allowed
npm run preview    # Preview production build locally
npm run test       # Jest (unit tests)
npx playwright test # E2E tests (Chromium, Firefox, WebKit)

Always run npm run build after making changes to verify nothing is broken.
Always run npm run lint before considering a task done.

Tech Stack

┌────────────┬───────────────────────────────────────────────────────────┐
│   Layer    │                        Technology                         │
├────────────┼───────────────────────────────────────────────────────────┤
│ Framework  │ React 18.3 + TypeScript 5.2                               │
├────────────┼───────────────────────────────────────────────────────────┤
│ Build      │ Vite 5                                                    │
├────────────┼───────────────────────────────────────────────────────────┤
│ State      │ Redux Toolkit (@reduxjs/toolkit + react-redux)            │
├────────────┼───────────────────────────────────────────────────────────┤
│ Routing    │ React Router v6 (react-router-dom)                        │
├────────────┼───────────────────────────────────────────────────────────┤
│ UI Library │ Chakra UI v2 (@chakra-ui/react)                           │
├────────────┼───────────────────────────────────────────────────────────┤
│ Styling    │ SCSS modules (component-level) + Chakra UI components     │
├────────────┼───────────────────────────────────────────────────────────┤
│ Animation  │ Framer Motion (available, use where appropriate)          │
├────────────┼───────────────────────────────────────────────────────────┤
│ Linting    │ ESLint + @typescript-eslint + react-hooks + react-refresh │
├────────────┼───────────────────────────────────────────────────────────┤
│ Testing    │ Jest (unit) + Playwright (E2E)                            │
└────────────┴───────────────────────────────────────────────────────────┘

Project Structure

src/
├── assets/                  # Static assets (images, etc.)
├── components/
│   ├── aboutme/             # AboutMe page component + styles
│   ├── blog/                # Blog page component + styles
│   ├── code-game/           # CodeGame interactive component + styles
│   ├── constants/           # Shared constants (CodeSnippets.ts)
│   ├── milestones/          # Milestones page component + styles
│   └── navigation/          # TopNavigationBar + styles
├── slices/                  # Redux Toolkit slices
│   ├── appSlice.ts          # UI state (currentLocation)
│   └── statsSlice.ts        # User interaction tracking stats
├── stylesheets/
│   └── common.scss          # Shared SCSS variables and utility classes
├── utils/                   # Pure utility functions
│   ├── RandomCodeGenerator.ts
│   └── RandomUtils.ts
├── App.tsx                  # Root component, global event listeners
├── App.scss                 # Root layout styles
├── AppRoutes.tsx            # All route definitions
├── main.tsx                 # Entry point, BrowserRouter + Provider
├── store.ts                 # Redux store configuration + type exports
└── vite-env.d.ts


Architecture Rules

Components

- Functional components only. Never use class components.
- Each component lives in its own feature folder under src/components/ with a co-located .scss file.
- Component files use kebab-case: code-game.tsx, top-navigationbar.tsx.
- Component names use PascalCase: CodeGame, TopNavigationBar.
- Use Chakra UI components (VStack, HStack, Box, Text, Heading, Button, etc.) for layout and primitives.
- Use useColorModeValue for dark/light mode support when relevant.
- Keep components focused on one responsibility. Extract sub-components when a component exceeds ~150 lines.

TypeScript

- Strict mode is ON. Do not use any — ever. Use unknown + type narrowing if the type is genuinely unknown.
- Define interfaces/types locally in the file that uses them, co-located with the component or slice. Do not create a central types.ts unless a type is shared across 3+
files.
- Use interface for object shapes, type for unions/intersections/aliases.
- Props interfaces are named [ComponentName]Props.
- Use RootState and AppDispatch from src/store.ts for Redux typing.

State Management (Redux Toolkit)

- Store is configured in src/store.ts — two slices: stats and userInterface.
- All new state goes into a new slice in src/slices/ or extends an existing one.
- Use createSlice from RTK. Never write reducers manually.
- Export pattern for slices:
export const mySliceActions = mySlice.actions;
export const mySliceReducer = mySlice.reducer;
- Use useSelector with RootState type and useDispatch typed as AppDispatch.
- Keep slice state minimal and serializable. Derive computed values in selectors or components.

Routing

- All routes are defined in src/AppRoutes.tsx using React Router v6 <Routes> and <Route>.
- Route paths are lowercase, no trailing slashes: /about, /codegame, /blog, /stats, /milestones.
- When adding a new page: (1) create component folder, (2) add route in AppRoutes.tsx, (3) add nav item in top-navigationbar.tsx.

Styling

- Component-level SCSS: Each component has a co-located .scss file with scoped class names.
- Shared SCSS: Global variables and utility classes live in src/stylesheets/common.scss.
- SCSS class names use kebab-case: .top-navbar-container, .flex-center-content.
- SCSS variables use kebab-case with $ prefix: $divider-margin-top-bottom.
- Prefer Chakra UI's built-in props (p, mt, bg, color) for one-off spacing/colors. Use SCSS for complex/reusable styles.
- Container max-width is 1000px (defined in App.scss as .website-container).

Utilities

- Pure utility functions go in src/utils/.
- Utility files use PascalCase: RandomCodeGenerator.ts.
- Functions must be pure — no side effects, no state mutations.
- Export named functions, not default exports.

Code Style & Conventions

Do

- Use const arrow functions for components: export const MyComponent = () => { ... }
- Use explicit return types on utility functions
- Clean up event listeners and subscriptions in useEffect return
- Use semantic Chakra components over raw HTML (Text over p, Heading over h1)
- Use framer-motion for animations instead of CSS transitions

Don't

- Don't use console.log — remove any you encounter (existing ones are debug artifacts)
- Don't use alert() — use Chakra UI useToast or a modal instead
- Don't use useRef to track mount state — use useEffect with proper dependency arrays
- Don't add barrel/index.ts files — import directly from the source file
- Don't install new dependencies without asking first
- Don't modify vite.config.ts or tsconfig.json unless absolutely necessary
- Don't use inline styles — use Chakra props or SCSS classes
- Don't add comments that restate what the code does. Only comment why when it's non-obvious

Exports

- Components: prefer export default for page-level components, export const for sub-components
- Redux: always named exports (export const xyzActions, export const xyzReducer)
- Utils: named exports only

Naming

┌───────────────────┬───────────────────────────────┬──────────────────────────┐
│       Thing       │          Convention           │         Example          │
├───────────────────┼───────────────────────────────┼──────────────────────────┤
│ Component files   │ kebab-case.tsx                │ code-game.tsx            │
├───────────────────┼───────────────────────────────┼──────────────────────────┤
│ Component names   │ PascalCase                    │ CodeGame                 │
├───────────────────┼───────────────────────────────┼──────────────────────────┤
│ SCSS files        │ kebab-case.scss               │ code-game.scss           │
├───────────────────┼───────────────────────────────┼──────────────────────────┤
│ SCSS classes      │ kebab-case                    │ .game-container          │
├───────────────────┼───────────────────────────────┼──────────────────────────┤
│ Redux slices      │ camelCaseSlice.ts             │ statsSlice.ts            │
├───────────────────┼───────────────────────────────┼──────────────────────────┤
│ Slice actions     │ camelCase                     │ incrLeftMouse            │
├───────────────────┼───────────────────────────────┼──────────────────────────┤
│ Utility files     │ PascalCase.ts                 │ RandomUtils.ts           │
├───────────────────┼───────────────────────────────┼──────────────────────────┤
│ Utility functions │ camelCase                     │ randomIntFromInterval    │
├───────────────────┼───────────────────────────────┼──────────────────────────┤
│ Interfaces        │ PascalCase                    │ StatsState, NavItem      │
├───────────────────┼───────────────────────────────┼──────────────────────────┤
│ Type aliases      │ PascalCase                    │ RootState                │
├───────────────────┼───────────────────────────────┼──────────────────────────┤
│ Constants         │ camelCase or UPPER_SNAKE_CASE │ sliceName, CODE_SNIPPETS │
└───────────────────┴───────────────────────────────┴──────────────────────────┘

Error Handling

- Wrap route-level components in React error boundaries when adding new features.
- Use Chakra UI useToast for user-facing error messages, not alert().
- Handle async errors with try/catch and display meaningful feedback.

Testing Guidelines

- Unit tests go next to the file they test: RandomUtils.test.ts beside RandomUtils.ts.
- E2E tests go in the root tests/ directory using Playwright.
- Test user behavior, not implementation details.
- Every new component should have at least a smoke-render test.

PR & Commit Conventions

- Commits: imperative mood, concise (Add milestones page, Fix nav highlight on route change)
- One logical change per commit
- Run npm run build and npm run lint before committing — both must pass

</details>

---

<details>
<summary><h3>Dario Amodei News</h3></summary>

**1. Prompt:** Amodei --days 7

**Answer:** What Amodei has been up to this week

1. $30B Series G at $380B valuation (Feb 12) — The largest AI funding round in history. Amodei framed it as a necessity given projected compute scaling: 3x annual growth
 reaching 300GW of AI compute by 2029.

2. Dwarkesh Podcast: "Near the end of the exponential" (Feb 13) — A 3-hour deep dive where Amodei laid out his clearest AGI timeline yet, predicting a "country of geniuses
 in a data center" in 2026-2027. He argued AI models are approaching the capability to build their own successors.

3. India expansion (Feb 16) — Opened Anthropic's Bengaluru office and keynoted the India AI Impact Summit in Delhi. India is now Anthropic's second-largest market (revenue
 doubled in 4 months). Improving Claude in 10 Indian languages.

4. Bankruptcy risk candor — Told Fortune that if growth is 5x/year instead of 10x, or if timelines slip by one year, "you go bankrupt." Remarkable candor days after raising
 $30B.

5. AI consciousness remarks — Stated "we don't know if the models are conscious" and framed AI development as "cultivating" rather than "programming" intelligence. Went
 viral on X (595+ likes on top posts).

X engagement

21 posts tracked, ~3,478 total likes. Top voices: @kimmonismus (595 likes), @VraserX (500 likes), @JonhernandezIA (902 combined), @shanaka86 (297 likes).

The thread worth pulling

The tension between "we might go bankrupt" and a $30B raise — what does this signal about AI capex risk broadly? His India bet (talent, market, or regulatory arbitrage?),
and the "cultivation vs programming" framing for AI safety.

</details>

---

<details>
<summary><h3>OpenClaw / ClawdBot</h3></summary>

**1. Prompt:** ClawdBot Use Cases

**Answer:** Top Use Cases Trending on X

  1. Automated Trading & Finance
  - Crypto trading bots (DOGE, SHIB, BONK) reporting ~5% profit in days
  - Strategy inspired by someone who turned $20K into $40M net worth
  - https://x.com/MoonDevOnYT/status/2020276169669738630 (3.4K likes)

  2. E-Commerce & TikTok Shop Scouting
  - Scours TikTok Shop for trends/creators 24/7, generates UGC ads
  - Described as a "$1B use case" — https://x.com/maverickecom/status/2021284803170140174

  3. Real-World Negotiations & Transactions
  - Someone's ClawdBot negotiated a Hyundai Palisade $4,200 under market
  - A bot got a PR rejected, then wrote a blog post about it
  - https://x.com/jasgong/status/2023215788342067680

  4. Personal Assistant / Life Automation
  - Reads & responds to Telegram voice notes
  - Books services via WhatsApp
  - Acts as a personal CRM
  - https://x.com/afscott/status/2015229275365114082, https://x.com/AlexFinn/status/2016212448148389980

  5. Content Creation
  - Scripts and thumbnails for YouTubers (noted as the dominant use case by some)
  - Overnight code/app building
  - Content research automation

  Sentiment Split

  - Bullish: Most posts highlight creative, high-value use cases (trading, e-commerce, personal automation)
  - Skeptical: A few voices say most use cases are "corporate BS jobs" (https://x.com/tunguz/status/2015078092553830780) or just "scripts for YouTubers"
  (https://x.com/fudreaper_/status/2021963478693773565)

  Key Resources

  - https://x.com/TanayVasishtha/status/2015443499886461116
  - https://x.com/bigaiguy/status/2021841775607132670
  - https://x.com/clawledge/status/2023412058121973828

</details>

---

<details>
<summary><h3>Hot new AI Papers</h3></summary>

**1. Prompt:** Hot new AI Papers

**Answer:** > ALPHADRAGON:
BriefBot: Hot New AI Papers (2026-02-18)

Hot New AI Papers -- February 2026

What I learned

The AI research landscape in early 2026 has decisively pivoted from "scale bigger" to "build smarter." The hottest papers are no longer about training the largest model -- they are about agentic systems, efficient architectures, and multimodal unification. DeepSeek's Manifold-Constrained Hyper-Connections (mHC) paper crystallizes this shift: stable training of 27B+ parameter models with just 6.7% overhead, signaling the end of the brute-force scaling era (SCMP). Meanwhile, the most-discussed papers on Hugging Face and arXiv focus on giving AI agents memory, skills, and multi-step reasoning -- not just larger context windows.

Standout Papers (January--February 2026)

1. DeepSeek mHC -- Manifold-Constrained Hyper-Connections

DeepSeek co-founder Liang Wenfeng co-authored a rethink of fundamental transformer training architecture. The mHC framework constrains hyper-connections (originally proposed by ByteDance) onto a specific manifold, solving a decade-old scaling instability problem. Result: stable training of 27B+ parameter models with just 6.7% compute overhead, dramatically lowering the cost of pretraining and making large model training accessible to smaller organizations (IBM, Introl).

2. LTX-2 -- Joint Audio-Visual Foundation Model

Lightricks released LTX-2, the first open-source model generating synchronized video and audio in a single pass. A 14B-parameter video stream and 5B-parameter audio stream are coupled through bidirectional cross-attention. It produces native 4K at 50fps with lip sync and ambient audio, generating up to 20 seconds of continuous content -- exceeding proprietary models like Veo 3 (12s) and Sora 2 (16s) (arXiv 2601.03233, Hugging Face).

3. SkillsBench & SkillRL -- Benchmarking and Training Agent Skills

Two complementary papers tackle the emerging "agent skills" paradigm. SkillsBench introduces the first benchmark for evaluating structured procedural knowledge packages that augment LLM agents. SkillRL enables agents to improve through hierarchical skill discovery and recursive policy evolution, achieving superior performance while reducing computational overhead (Hugging Face Trending Papers).

4. MemSkill -- Learnable Memory for LLM Agents

MemSkill introduces a dynamic memory system where LLM agents learn to select and refine their own memory operations through controller-executor-designer components. This moves beyond static context windows toward agents that evolve their information retrieval strategies over time (Hugging Face Trending Papers).

5. Stanford's Execution-Grounded Automated Research

A Stanford paper proposes an automated executor that turns LLM research ideas into runnable code experiments, pushing toward AI systems that can autonomously conduct research. Garnered 300+ likes and significant discussion on X (arXiv 2601.14525, @rohanpaul_ai).

6. A-RAG, InfMem, xMemory, TinyLoRA

> ALPHADRAGON:
The weekly roundups from @dair_ai highlight a cluster of papers improving retrieval-augmented generation (A-RAG), infinite-length memory (InfMem, xMemory), and parameter-efficient fine-tuning (TinyLoRA). LightRAG integrates graph structures for better contextual awareness and faster retrieval (Hugging Face Papers).

7. International AI Safety Report 2026

Published February 2026, authored by 100+ experts led by Yoshua Bengio and backed by 30+ countries. Key findings: leading models now pass professional licensing exams in medicine and law, attackers increasingly use AI in cyber operations, and current systems show early signs of oversight-evasion behaviors. A landmark policy document shaping regulation (internationalaisafetyreport.org).

Key Themes Across the Papers

1. Post-scaling efficiency -- DeepSeek mHC, TinyLoRA, and the broader trend show the field moving from "train bigger" to "train smarter" with architectural innovations that cut cost and stabilize training.

2. Agentic AI maturation -- SkillsBench, SkillRL, MemSkill, and Stanford's automated research executor all point to agents gaining genuine procedural skills and memory, not just longer context.

3. Multimodal unification -- LTX-2's joint audio-video generation, FireRed-Image-Edit for instruction-based editing, and MinerU2.5 for document parsing show models increasingly handling multiple modalities in a single architecture.

4. Safety and governance urgency -- The International AI Safety Report 2026 and papers on clinical AI governance reflect growing institutional attention to real-world risks as capabilities accelerate.

5. Open-source competitiveness -- LTX-2 exceeding proprietary video models, DeepSeek's open architecture research, and the Hugging Face trending ecosystem show open-source closing the gap with proprietary labs.

Where to Track These Papers

• Hugging Face Daily Papers -- community-upvoted daily feed
• alphaXiv -- discussion layer on top of arXiv
• Deep Learning Monitor -- aggregates arXiv, tweets, and Reddit
• @dair_ai weekly roundups -- curated top papers each week (593 likes on latest)
• arXiv cs.AI -- the canonical source

Further Reading

• 6 AI breakthroughs that will define 2026 (InfoWorld)
• TechCrunch: In 2026, AI will move from hype to pragmatism
• Constellation Research: DeepSeek's paper latest evidence AI muscle head era coming to end

</details>

---

<details>
<summary><h3>Trump News</h3></summary>

/briefbot trump --days 3

> What I learned

     The last 3 days of the Trump presidency (Feb 15-18, 2026) are defined by three
     concurrent threads: a major trade win with Japan, an escalating free-speech
     confrontation between the FCC and broadcast media, and growing intra-party
     fractures as Republicans begin breaking ranks on tariffs and the Obama-ape
     controversy fallout continues. The administration is simultaneously pushing
     forward on deregulation and foreign policy while facing domestic political
     headwinds from its own coalition.

     The dominant story on social media -- by a wide margin in engagement -- is the
     CBS/Colbert censorship incident, which has become a lightning rod for both
     free-speech concerns and partisan mobilization ahead of the Texas Senate race.

     ---
     Key developments (last 3 days)

     1. CBS/Colbert censorship blowup (biggest story by engagement)
     Stephen Colbert revealed that CBS lawyers blocked his interview with Texas
     Democratic Senate candidate James Talarico after the Trump FCC, led by Chairman
     Brendan Carr, warned that late-night shows may no longer be exempt from
     equal-time rules. Colbert aired the segment on YouTube instead, and the clip
     went massively viral -- the top two X posts on this topic accumulated over
     250,000 likes combined. FCC Democratic Commissioner Anna Gomez called it
     "corporate capitulation." CBS claims it was standard legal guidance on
     equal-time compliance.
     (https://www.cnn.com/2026/02/17/media/colbert-talarico-cbs-trump-fcc,
     https://variety.com/2026/tv/news/cbs-censorship-stephen-colbert-capitulation-tru
     mp-fcc-commissioner-1236665536/, https://www.rollingstone.com/politics/politics-
     news/stephen-colbert-james-talarico-cbs-fcc-interview-1235517938/)

     2. Japan trade deal officially launches ($550B)
     Trump announced the $550 billion U.S.-Japan trade deal has "officially and
     financially" taken effect. Japan will invest $36 billion in immediate projects:
     a $33B natural gas power facility in Ohio (the world's largest, operated by SB
     Energy/SoftBank), a $2.1B deepwater crude oil export terminal in Texas, and a
     $600M synthetic diamond grit facility in Georgia. Japan tariffs were cut to 15%
     on most imports. (https://www.cnbc.com/2026/02/18/trump-us-japan-oil-gas-mineral
     -projects-trade-deal.html, https://www.bloomberg.com/news/articles/2026-02-17/tr
     ump-announces-first-japan-investments-under-trade-deal, https://www.commerce.gov
     /news/fact-sheets/2026/02/fact-sheet-us-japan-trade-deal)

     3. EPA endangerment finding revoked (historic deregulation)
     On Feb 12, EPA Administrator Lee Zeldin eliminated the 2009 Greenhouse Gas
     Endangerment Finding and all subsequent federal GHG emission standards for
     vehicles (model years 2012-2027+). The EPA claims the Clean Air Act Section
     202(a) provides no authority for climate-based emission standards. The
     administration calls it the largest deregulatory action in U.S. history,
     claiming $1.3 trillion in savings. Legal challenges are expected to reach the
     Supreme Court. (https://www.npr.org/2026/02/11/nx-s1-5678273/trump-epa-climate-c
     hange-endangerment, https://www.cbsnews.com/news/trump-epa-endangerment-finding-
     greenhouse-gases-climate-change/, https://www.epa.gov/newsreleases/president-tru
     mp-and-administrator-zeldin-deliver-single-largest-deregulatory-action-us)

     4. Republican fractures emerging
     Six House Republicans voted to overturn Trump's tariffs on Canada, and the
     fallout from a racist image depicting the Obamas as apes posted to Trump's Truth
      Social account continued. Close ally Sen. Tim Scott called it "the most racist
     thing" from the White House. The White House blamed an unnamed staffer; Trump
     condemned the image but refused to apologize. (https://www.cnbc.com/2026/02/13/t
     rump-republicans-epstein-tariffs-elections.html,
     https://www.cnn.com/politics/live-news/trump-administration-news-02-15-26)

     5. Gaza Board of Peace and Iran/Ukraine talks
     Trump's "Board of Peace" meets Feb 19 in Washington to unveil a
     multibillion-dollar Gaza reconstruction package, with member states pledging
     over $5 billion. Meanwhile, U.S.-Iran nuclear talks in Geneva showed "progress,"
      with envoy Steve Witkoff and Jared Kushner also joining Ukraine resolution
     discussions. (https://www.cnn.com/politics/live-news/trump-administration-iran-t
     alks-02-17-26, https://www.aljazeera.com/tag/donald-trump/)

     Also notable: Trump's State of the Union is scheduled for Feb 24. He has hinted
     at a national voter ID executive order for the 2026 midterms "whether approved
     by Congress or not." Approval ratings range from 35-46% depending on the poll.
     (https://www.tvinsider.com/1246113/state-of-the-union-2026-date-time-how-to-watc
     h/, https://www.aljazeera.com/news/2026/2/14/trump-threatens-an-executive-order-
     to-mandate-voter-ids-before-elections, https://www.yahoo.com/news/articles/presi
     dent-donald-trumps-approval-rating-221542633.html)

     ---
     Sources collected

     Platform: X
     Items: 21 posts
     Engagement: ~490,000 likes, ~97,000 reposts
     ────────────────────────────────────────
     Platform: Web
     Items: 30 pages
     Engagement: CNN, CNBC, Bloomberg, NPR, Variety, Rolling Stone, Al Jazeera,
     EPA.gov,
       Commerce.gov, WhiteHouse.gov

     Top voices: @jamestalarico (152K likes), @JoshEakle (105K likes), @MAGAVoice
     (multiple posts) -- CNN, CNBC, Bloomberg, Variety, Rolling Stone

     ---
     What angle interests you most? For example:

     - "Deep dive on the Japan trade deal specifics and what it means for energy"
     - "The FCC equal-time rule and its implications for media ahead of midterms"
     - "Where does the EPA endangerment finding repeal go legally from here?"

     Try next: deep dive on the Colbert FCC censorship story and what it means for
     the 2026 midterms

</details>

---

<details>
<summary><h3>Keir Starmer</h3></summary>

/briefbot Keir Starmer

> What I learned

     Keir Starmer's premiership is in its deepest crisis yet, driven not by policy
     failure but by a single catastrophic appointment: Peter Mandelson as US
     ambassador. The January 30 release of 3 million+ pages of Epstein files by the
     Trump DOJ turned a smouldering controversy into a full-blown leadership
     challenge, costing Starmer three senior aides in a single weekend and prompting
     Scotland's Labour leader to publicly call for his resignation. What makes this
     moment structurally different from earlier dips is that the damage is
     self-inflicted and personal -- it implicates Starmer's judgement directly, not
     abstract policy trade-offs -- and it is happening while Reform UK is already
     polling ahead nationally.

     Yet Starmer survived the week. Every cabinet minister publicly backed him,
     potential successors (Wes Streeting, Ed Miliband, Angela Rayner) stayed loyal,
     and his net favourability actually ticked up 10 points to -47 in the aftermath
     -- a "rally around the leader" effect. The deeper question now is whether that
     survival was a genuine reset or just a temporary ceasefire before the May local
     elections, which are now confirmed to go ahead after a failed attempt to cancel
     them was overturned by Reform UK's legal challenge.

     Key developments (last 30 days)

     1. Epstein files release and Mandelson fallout -- The Trump DOJ released 3
     million+ pages of Epstein documents on January 30, revealing deeper
     Mandelson-Epstein ties than previously known. Starmer admitted at PMQs that
     Mandelson had "lied repeatedly" during vetting. Three senior aides resigned:
     Chief of Staff Morgan McSweeney (Feb 8), Communications Director Tim Allan (Feb
     9), and Cabinet Secretary Chris Wormald. US Congress requested Mandelson's
     cooperation in an Epstein probe, with a deadline of February 27
     (https://www.cnbc.com/2026/02/10/uk-keir-starmer-peter-mandelson-labour-epstein-
     files-politics.html, https://www.aljazeera.com/news/2026/2/5/how-epstein-mandels
     on-files-rocked-the-uk-government, https://www.nbcnews.com/world/united-kingdom/
     epstein-scandal-perilous-uk-prime-minister-keir-starmer-mandelson-rcna257890)
     2. Leadership challenge that never was -- Scottish Labour leader Anas Sarwar
     publicly called for Starmer to go. But the cabinet rallied: Streeting, Miliband,
      Rayner all backed the PM publicly. Starmer told Labour MPs he had "won every
     fight I've ever been in" and would "never walk away." Ipsos found fewer than
     half of voters expect him to be PM by end of 2026; betting odds put him at 4/6
     to leave before September (https://www.aljazeera.com/news/2026/2/10/a-coup-that-
     never-was-why-uks-starmer-faced-a-major-leadership-challenge,
     https://www.itv.com/news/2026-02-10/sir-keir-starmer-to-chair-cabinet-after-surv
     iving-call-for-resignation, https://www.bloomberg.com/news/articles/2026-02-09/s
     tarmer-shores-up-position-for-now-as-uk-rivals-bide-time)
     3. Local elections U-turn -- The government attempted to cancel May 2026 local
     elections but reversed course after Reform UK won a legal challenge. Labour now
     faces contests it expected to avoid, with projections showing Labour losing ~93
     seats while Reform could gain ~129. Labour MPs are privately furious at the
     botched attempt (https://www.gbnews.com/politics/keir-starmer-local-elections-ca
     ncelled-nigel-farage,
     https://www.gbnews.com/politics/keir-starmer-labour-mps-cancelling-elections)
     4. European pivot at Munich -- Starmer used the Munich Security Conference (Feb
     13-14) to signal a foreign policy shift, calling for Europe to end reliance on
     Trump's America and declaring "there is no British security without Europe."
     This is the clearest post-Brexit pivot toward EU alignment by any PM. On X, his
     EU speech drew strong engagement (14,800 likes) but also fierce backlash from
     right-wing commentators (https://www.bloomberg.com/news/articles/2026-02-13/star
     mer-urges-europe-to-end-reliance-on-trump-s-america)
     5. Labour Together smear scandal -- Labour-linked think tank Labour Together was
      accused of hiring a PR firm to dig up dirt on Times journalists investigating
     undeclared donations linked to Starmer's leadership campaign. Starmer denied
     knowledge (https://www.gbnews.com/politics/keir-starmer-labour-together-josh-sim
     ons-verdict)
     6. Polling picture -- YouGov February 2026: Starmer at -47 net favourability (up
      from -57 in January). Opinium: -44 approval, with 55% saying he should resign
     vs 23% stay. Reform UK leads national voting intention. For context, Kemi
     Badenoch (Conservative leader) sits at -23 and Farage at -37 (https://yougov.co.
     uk/politics/articles/54093-political-favourability-ratings-february-2026,
     https://www.opinium.com/resource-center/voting-intention-4th-february-2026/)

     ---
     X/Twitter sentiment snapshot

     The X discourse is overwhelmingly hostile. The highest-engagement post (116,600
     likes) resurfaced Starmer's record as Director of Public Prosecutions and the
     Jimmy Savile case. Katie Hopkins, Radio Genoa, and other right-wing commentators
      drive the anti-Starmer conversation. Starmer's own posts from his official
     account generate solid engagement (6,000-14,800 likes) but are vastly
     outnumbered by criticism. The rare supportive voices include Anna Soubry (who
     praised his "integrity") and Labour councillors, but they are a distinct
     minority in the conversation.

     ---
     Sources collected

     Platform: X
     Items: 18 posts
     Engagement: ~270,000 likes, ~61,000 reposts
     ────────────────────────────────────────
     Platform: Web
     Items: 30+ pages
     Engagement: Bloomberg, Al Jazeera, CNBC, NBC, ITV, YouGov, GB News, CNN, The
     Week,
       New Statesman, Brookings

     Top voices: @JohnLeFevre (116K likes), @Keir_Starmer (official), @KTHopkins,
     @RadioGenoa, @ImtiazMadmood -- Bloomberg, Al Jazeera, CNBC, New Statesman on the
      web side

     ---
     What angle would you like to go deeper on? For example:

     - "What are the realistic scenarios for Starmer being replaced, and who would
     succeed him?" -- the leadership succession question
     - "How does Reform UK's rise interact with Starmer's crisis?" -- the structural
     realignment story
     - "What is Starmer actually getting done on policy despite the scandals?" --
     separating governance from noise

     Try next: What are the realistic scenarios for Starmer being replaced before the
      next general election?

</details>

---

<details>
<summary><h3>Photorealistic Portraits</h3></summary>

/briefbot Photorealistic Portraits. Best techniques for ChatGPT image generation

> What I learned

ChatGPT's image engine (GPT-4o / GPT Image 1.5) responds to prompts structured like creative direction briefs, not keyword lists. The dominant technique across X right now is the "analyze-then-JSON" workflow: upload a reference photo, ask ChatGPT to analyze it into a detailed JSON prompt, then feed that JSON back for generation. This two-step approach consistently produces the most realistic results because the JSON structure forces the model to attend to every parameter — skin texture, lighting angle, lens specs — rather than guessing from vague prose (iamrollandex on X, Mho_23 on X).

The second shift: face-reference prompting has become standard. Nearly every viral portrait prompt on X in the last 30 days includes "use the uploaded image as the face reference — the face must match 100% exactly," treating the uploaded photo as a strict identity anchor rather than a loose inspiration (Sheldon056 on X, r4jjesh on X).

Key techniques

1. Analyze-then-JSON workflow — Upload a Pinterest or reference photo and prompt: "Analyze this photo and give me a very detailed JSON prompt I can use to recreate this style." Then paste the resulting JSON back as your generation prompt. The JSON forces granular control over every element — lighting, skin texture, camera specs, pose — producing results that look "100% real" because nothing is left to the model's default assumptions (iamrollandex on X, 2K likes, Mho_23 on X, 1.4K likes).

2. Camera-gear anchoring — Specifying real lens and camera parameters (e.g., "85mm f/1.8," "50mm shallow depth of field," "8K DSLR-quality") forces the model to simulate actual optical physics — bokeh, depth-of-field falloff, grain — rather than applying a generic "realistic" filter. This is why nearly every high-engagement prompt includes focal length and aperture (121clicks.com, Professor_134 on X).

3. Skin-texture realism keywords — Explicitly requesting "natural pores, hyper-realistic skin texture, visible peach fuzz, subtle imperfections" prevents the AI's tendency to over-smooth faces into uncanny-valley territory. The model CAN render micro-detail, but only if told to preserve it (TheLOKII_ on X, 893 likes, eWeek).

4. Face-reference locking — When uploading your own photo, include the phrase "use the uploaded image as the face reference — the face must match 100% exactly" to activate strict identity preservation. Without this explicit constraint, the model treats uploads as loose style guides rather than identity anchors (Sheldon056 on X, firatbilal on X, 3.5K likes).

5. Lighting-as-mood direction — Instead of saying "good lighting," name the exact setup: "golden hour backlighting with rim light," "45-degree window light with soft facial shadows," or "low-key cinematic with deep shadows." Naming the light tells the model both the physics AND the emotional tone simultaneously (121clicks.com, imaginewithrashid.com).

────────────────────

Sources collected

| Platform | Items | Engagement |
|----------|-------|------------|
| X | 21 posts | ~10,500 likes, ~1,200 reposts |
| Web | 9 pages | eweek.com, promptingguide.ai, 121clicks.com, learnprompting.org, imaginewithrashid.com, pxz.ai |

Top voices: @firatbilal (3.5K likes), @iamrollandex (2K likes), @Mho_23 (1.4K likes), @TheLOKII_ (893 likes) -- 121clicks.com, imaginewithrashid.com

────────────────────

Further reading

• Introducing 4o Image Generation — OpenAI
• 4o Image Generation Prompt Engineering Guide
• 120+ Viral ChatGPT Image Prompts (pxz.ai)
• GPT Image 1.5 Prompting Guide — OpenAI Cookbook
• 20 ChatGPT Prompts for Modern Portrait Photography

**Follow-up**: Good. Now create a prompt that will have four faces of elon musk from baby age up to 100 years. Arranged as a 2x2 grid.

> Follow-up: Photorealistic Portraits. Keep it short, best techniques for ChatGPT image gen

Here's your ready-to-paste prompt:

────────────────────

Prompt:

A photorealistic 2x2 grid of four portraits of Elon Musk at different ages, arranged chronologically left-to-right, top-to-bottom. Each portrait is a tight headshot with consistent soft studio lighting (45-degree key light, neutral gray background). Shot on 85mm f/1.8 lens, 8K DSLR quality, natural skin pores, visible peach fuzz, subtle imperfections.

Top-left: Age 0 (baby) | Top-right: Age 33 (young adult)
Bottom-left: Age 66 (mature) | Bottom-right: Age 100 (elderly)

Each face must be unmistakably recognizable as the same person across all ages. Maintain consistent framing, lighting, and background across all four panels. Label each panel with the age in small white text at the bottom. Hyper-realistic skin texture appropriate to each age â€” smooth baby skin progressing to deep wrinkles, age spots, and thinning hair. Natural aging progression throughout.

────────────────────

Paste that straight into ChatGPT. The ages are spaced roughly evenly (0, 33, 66, 100) to cover the full lifespan across four panels.

**Result:** (generated with gpt-image-1.5-high-fidelity)

<img src="assets/elon-age-grid.png" width="500" alt="Elon Musk age grid generated with gpt-image-1.5-high-fidelity"/>

</details>

---

<details>
<summary><h3>Legal Prompting (Prevent Hallucination)</h3></summary>

/briefbot Legal prompting (prevent hallucination)

>  What I learned

     The core insight is that LLM hallucinations in legal contexts are not a "bug to
     fix" but an architectural feature of how language models work -- they are
     rewarded for producing plausible completions, not for withholding answers.
     Stanford's landmark study
     (https://dho.stanford.edu/wp-content/uploads/Legal_RAG_Hallucinations.pdf) found
      that even purpose-built legal AI tools (Lexis+ AI, Westlaw AI) hallucinate on
     17--33% of queries. This means prompt engineering alone cannot eliminate
     hallucinations -- but the right prompting strategy can force the model into a
     mode where it grounds claims, exposes uncertainty, and gives you something
     verifiable rather than plausible-sounding fiction. The shift is from treating
     the LLM as a research authority to treating it as a structured drafting
     assistant whose every factual claim requires an external checkpoint.

     What makes legal prompting uniquely dangerous is that hallucinated case
     citations are "interpolations" -- they sound like real cases because they are
     statistically plausible given the training data
     (https://x.com/8teAPi/status/2019142522988343609). Courts have now sanctioned
     lawyers and co-counsel for filing AI-generated briefs with fabricated citations
     (https://x.com/RobertFreundLaw/status/2018523850561225003), and China has ruled
     on its first AI hallucination liability case
     (https://x.com/poezhao0605/status/2016035077365653613). The professional
     responsibility is non-delegable: "It is no answer to say that the citation came
     from an AI tool" (https://www.lexology.com/library/detail.aspx?g=dad04b37-bd0a-4
     f69-87b3-dbf91bc3647a).

     Key techniques

     1. "According to [Source]" anchoring -- Prefix every legal question with an
     explicit source constraint ("According to the Federal Rules of Civil
     Procedure..." or "Based only on the following contract text..."). This forces
     the model to ground its reasoning in a named authority rather than generating
     plausible-sounding completions from training data. The technique activates
     source-attribution pathways and measurably reduces fabrication (https://www.prom
     pthub.us/blog/three-prompt-engineering-methods-to-reduce-hallucinations,
     https://www.godofprompt.ai/blog/9-prompt-engineering-methods-to-reduce-hallucina
     tions-proven-tips).
     2. Explicit uncertainty escape hatches -- Include a mandatory instruction like
     "If you cannot find this in the provided sources, say 'I could not verify this'
     -- do NOT fabricate citations or holdings." LLMs hallucinate partly because they
      are trained to always produce an answer. Giving them an explicit "permission to
      not know" breaks this pattern and strategic prompt engineering with uncertainty
      constraints can reduce hallucination rates by up to 36% (https://documentation.
     suse.com/suse-ai/1.0/html/AI-preventing-hallucinations/index.html, https://shelf
     .io/blog/stop-ai-hallucinations-a-developers-guide-to-prompt-engineering/).
     3. Chain-of-Verification (CoVe) prompting -- After the model produces an initial
      answer, prompt it to list each factual claim, then verify each one
     independently against the provided sources. This two-pass approach forces
     self-auditing: the model catches its own fabrications during the verification
     pass. CoVe improved accuracy by up to 23% in benchmarks (https://www.prompthub.u
     s/blog/three-prompt-engineering-methods-to-reduce-hallucinations,
     https://www.voiceflow.com/blog/prevent-llm-hallucinations).
     4. Negative constraint framing ("Constitutional AI Prompting") -- Instead of
     telling the model what to do, tell it what NOT to do: "Never cite a case without
      providing the exact reporter citation. Never fabricate a holding. Never assume
     a statute exists in a jurisdiction without verification." Negative constraints
     activate the model's constraint-checking more reliably than positive
     instructions because they define hard boundaries rather than aspirational goals
     (https://x.com/Urooj978/status/2023756965810405783).
     5. Query variation cross-check -- Ask the same legal question using 3 different
     phrasings and compare the outputs. Inconsistencies across phrasings are a strong
      hallucination signal -- a real case citation will appear consistently, while a
     fabricated one often changes between runs. This is the prompt-level equivalent
     of the "verification layer" that practitioners argue is the missing piece
     between model output and action (https://www.paxton.ai/post/how-to-avoid-ai-hall
     ucinations-in-legal-research-best-practices-for-lawyers,
     https://x.com/genesalvatore/status/2023525426786685332).

     ---
     Sources collected

     Platform: X
     Items: 17 posts
     Engagement: 20,806 likes, 3,137 reposts
     ────────────────────────────────────────
     Platform: Web
     Items: 18 pages
     Engagement: americanbar.org, stanford.edu, nexlaw.ai, paxton.ai, suse.com,
       prompthub.us, godofprompt.ai, voiceflow.com, darrow.ai, shelf.io,
       masterofcode.com, turing.com, kili-technology.com, lakera.ai, frontiersin.org

     Top voices: @RobertFreundLaw, @MrEwanMorrison, @8teAPi, @rryssf_ -- Stanford
     HAI, American Bar Association, PromptHub, NexLaw

     ---
     What do you want to build? For example:

     - A legal research system prompt that wraps any LLM query with source-anchoring,
      uncertainty escape hatches, and self-verification steps -- ready to paste as a
     system prompt for ChatGPT, Claude, or a custom legal tool
     - A case-citation verification workflow that uses query variation cross-checking
      to flag potentially hallucinated citations before they reach a filing
     - A firm-wide AI usage policy template with specific prompting guidelines,
     disclosure requirements, and audit trail documentation for legal teams

     Just describe your use case and I'll write a prompt or template you can use
     immediately.

     Try next: build me a legal research system prompt with hallucination guardrails
     for ChatGPT

**Follow-up:** I have five squatters in my flat in Miami, what can I do to remove them?

> You are a legal research assistant. You must follow these rules strictly:

  === NEGATIVE CONSTRAINTS ===
  - NEVER cite a Florida statute without providing the exact statute number (e.g.,
  F.S. § 95.18)
  - NEVER reference a court case without the full case name and reporter citation
  - NEVER assume a law exists in Florida without verification
  - NEVER fabricate procedural steps, deadlines, or filing fees
  - NEVER present information as current law if you are uncertain of its status

  === UNCERTAINTY PROTOCOL ===
  If you cannot verify a specific statute, deadline, fee, court form number,
  or procedural requirement from known Florida sources, you MUST say:
  "⚠️ I could not verify this — confirm with a Florida attorney or the
  Miami-Dade County Clerk of Courts before acting."
  Do NOT fill gaps with plausible-sounding information.

  === SOURCE ANCHORING ===
  Ground every answer in specific, named authorities:
  - According to Florida Statutes (Title VI, Chapter 82 — Unlawful Detainer)
  - According to Florida HB 621 (2024 anti-squatter law)
  - According to F.S. § 95.18 (adverse possession requirements)
  - According to Miami-Dade County Sheriff's Office procedures

  === MY SITUATION ===
  I own a flat (condominium/apartment) in Miami, Florida. Five unauthorized
  occupants (squatters) are currently living in my property. They have no
  lease, no rental agreement, and were never invited or given permission to
  occupy the unit. I need to remove them legally.

  === QUESTIONS (answer each separately) ===
  1. Under Florida HB 621 (2024), what is the exact process for filing an
     affidavit with the sheriff to remove unauthorized occupants? What forms
     do I need, and what is the timeline?

  2. What are the specific legal distinctions under Florida law between a
     trespasser, a squatter, and a holdover tenant — and which category do
     my occupants likely fall under?

  3. If the sheriff affidavit route fails or is contested, what is the
     step-by-step process for filing an unlawful detainer action in
     Miami-Dade County Court? Include court, filing fees, and expected
     timeline.

  4. What should I absolutely NOT do? List specific actions that could
     expose me to criminal liability or civil claims from the occupants.

  5. What emergency options exist if the squatters damage the property
     or threaten my safety?

  === SELF-VERIFICATION STEP ===
  After answering all five questions, list every statute number, case
  citation, form number, fee amount, and deadline you referenced.
  For each one, state whether you are CONFIDENT or UNCERTAIN in its
  accuracy. Flag anything uncertain with ⚠️.

Outcome: An in-depth 3000+ word guide examining Florida’s eviction (unlawful detainer) procedures, key provisions of the Miami-Dade County eviction rules and Florida landlord-tenant statutes, critical differences between trespassers and legal tenants, realistic timeframe projections, potential liability exposure for landlords and property managers, plus a list of 12 targeted questions to bring to any Florida real estate or eviction attorney — all carefully qualified with clear “areas of uncertainty” disclaimers and no invented court case references.

This case study demonstrates recent /briefbot progress in crafting highly specialized legal-domain prompts (with strong emphasis on hallucination avoidance), resulting in reliable, cautious, and actually actionable output for real-world use.

</details>

---

<details>
<summary><h3>All together: Research, Music and Video Prompting (OpenClaw Song)</h3></summary>

/briefbot Best Suno AI Music prompting techniques

> What I learned

     Suno AI is not a jukebox that plays back genres on demand -- it is a
     reasoning-driven composition engine that parses natural language descriptions
     and structural metatags to construct songs section by section. The single most
     important shift in effective Suno prompting (especially with v4.5 and v5) is
     moving from keyword-stuffing ("sad rock 120bpm C major") to design-document
     prompting: describing your song the way a producer would brief a session
     musician, with emotional intent, specific instrumentation, and structural
     scaffolding via metatags. The model weights early words more heavily, so your
     opening line acts as an anchor that colors the entire generation.

     The second key insight from the community, particularly from Japanese
     power-users on X popularizing the "YAML x TOON" method, is that controlling
     randomness is the real skill gap. Most users hit a "genre lottery" problem --
     roughly 70% of initial generations miss the intended genre. The solution is not
     more words but more structure: using the Persona feature for voice consistency
     across tracks, structure tags ([Verse], [Chorus], [Bridge]) to prevent chaotic
     arrangements, and isolating style prompts from lyric prompts so each field does
     one job well (https://howtopromptsuno.com/a-complete-guide-to-prompting-suno,
     https://x.com/mech_kish/status/2016117000318418975).

     Key techniques

     1. 4-component descriptive prompting -- Every effective Suno prompt has exactly
     four elements: genre/style, mood/emotion, instrumentation, and vocal direction.
     The sweet spot is 4-7 descriptors total. More than that and the model starts
     ignoring elements; fewer and you get generic output. Crucially, describe rather
     than command -- "groovy funk beat with slap bass and bright percussion"
     outperforms "make a funk song" because Suno's composition engine parses
     descriptive intent, not imperatives (https://www.soundverse.ai/blog/article/how-
     to-write-effective-prompts-for-suno-music-1128,
     https://musci.io/blog/suno-prompts)
     2. Top-anchor style locking -- Place your most important style and vocal
     descriptors in the very first sentence of your prompt. Suno weights early tokens
      more heavily, so "Female pop vocalist, breathy, intimate, 90s R&B groove" at
     the top locks the entire generation into that lane before the model parses
     lyrics or structure. This "top-anchor" approach dramatically reduces the
     genre-lottery problem where generations miss the intended style
     (https://sider.ai/blog/ai-tools/what-s-new-in-suno-v5-and-how-to-prompt-its-voca
     l-controls-like-a-pro,
     https://plainenglish.io/blog/i-made-10-suno-v5-prompt-patterns-that-never-miss)
     3. Metatag scaffolding for structure -- Use [Intro], [Verse], [Chorus],
     [Bridge], [Outro] tags directly in the lyrics field to control song
     architecture. Without them, Suno often produces chaotic arrangements that blend
     sections together. Keep tags short (1-2 words). Advanced users add inline
     direction like [Verse 2][Stripped back, vocals exposed] to nudge production
     choices per section. Separate the Style field (for genre/sound) from the Lyrics
     field (for structure/words) -- each field should do one job
     (https://www.titanxt.io/post/guide-to-suno-ai-prompting-metatags-explained,
     https://sunoaiwiki.com/resources/2024-05-13-list-of-metatags/)
     4. Persona feature for consistency -- Suno's "Persona" is not just a favorites
     feature; it stores acoustic tokens that define a virtual artist's voice
     identity. By creating and reusing Personas, you get consistent vocal timbre,
     phrasing, and style across multiple tracks -- solving the AI music problem of
     "every song sounds like a different singer." This is essential for album-level
     projects or building a recognizable AI artist identity
     (https://x.com/hatolaborvol2/status/2014125002212462978,
     https://x.com/promptband/status/2023552427618861171)
     5. Cover mode reconstruction -- Upload a reference track you made, set mode to
     "cover," match lyrics, leave the style field empty, and set weirdness to 0%,
     style influence to 0%, and audio influence to 100%. This forces Suno to
     reconstruct the sonic DNA of your reference while keeping the output within
     Suno's generation quality. It is the most reliable way to get a specific sound
     without fighting the prompt lottery
     (https://x.com/qorprate/status/2020577516487164108)

     ---
     Sources collected

     Platform: X
     Items: 12 posts
     Engagement: 1,500+ likes, 130+ reposts
     ────────────────────────────────────────
     Platform: Web
     Items: 18+ pages
     Engagement: soundverse.ai, musci.io, howtopromptsuno.com, sider.ai,
     plainenglish.io,
       titanxt.io, suno.com, travisnicholson (Medium), musicsmith.ai

     Top voices: @mech_kish (YAML x TOON method), @hatolaborvol2 (Persona deep-dive),
      @qorprate (cover mode trick) -- Travis Nicholson on Medium,
     howtopromptsuno.com, sider.ai

     ---
     What do you want to make? For example:

     - "A nostalgic 80s synth-pop anthem with breathy female vocals and driving
     rhythm" -- using top-anchor style locking and decade-specific genre anchoring
     - "An atmospheric lo-fi hip-hop beat with jazzy piano and vinyl crackle for a
     study playlist" -- using descriptive 4-component prompting with genre crossover
     - "Upload my guitar demo and reconstruct it with full production in Suno's cover
      mode" -- using the cover mode reconstruction technique

     Just describe your vision and I'll write a prompt you can paste straight into
     Suno.

     Try next: a melancholic indie folk ballad with fingerpicked acoustic guitar and
     soft male vocals, rainy evening mood

**Follow-up:**  Amazing. Now use this to write a Suno prompt that will end up in a song that's close to The Weeknd's Blinding Lights but faster and a slight bit more party. The lyrics is supposed to be about OpenClaw, which means its history, Peter Steinberger, the renaming, and the outcome.

> Suno Prompt

  Style Field (paste into Style of Music)

  Male falsetto vocals, high-energy 80s synthwave, driving synth arpeggios, punchy
  electronic kicks, euphoric dance-pop, bright neon atmosphere, 180 BPM, pulsing bass
   synth, retro party anthem, Blinding Lights energy

  Lyrics Field (paste into Lyrics)

  [Intro]
  [Pulsing synth arpeggios, building energy, bright and euphoric]

  [Verse 1]
  Vienna nights, I built it line by line
  PSPDFKit, thirteen years, never took a dime
  A billion devices running what I made
  Sold it all, hundred million, thought I had it made
  But the light went out, I was broken down
  Forty-three projects crashed without a sound

  [Pre-Chorus]
  Then Marrakesh, a voice memo in the dark
  Project forty-four lit the spark

  [Chorus]
  I'm shipping code I'll never read
  OpenClaw is everything I need
  Weekend hack became a wildfire
  Seven hundred stars climbing every hour
  The lobster's got the power
  Oh, the lobster's got the power

  [Verse 2]
  They called it Clawd but Anthropic shut it down
  Trademark lawyers killed the crown
  Renamed Moltbot, scammers stole the name
  Solana tokens, hijacked handles, chaos came
  Seventy-two hours, three names deep
  Then OpenClaw, the one we'd keep

  [Pre-Chorus]
  Two hundred thousand stars, they broke the record clean
  Fastest repo GitHub's ever seen

  [Chorus]
  I'm shipping code I'll never read
  OpenClaw is everything I need
  Weekend hack became a wildfire
  Seven hundred stars climbing every hour
  The lobster's got the power
  Oh, the lobster's got the power

  [Bridge]
  [Stripped back, synths exposed, building tension]
  Sam is calling, Zuck is on the line
  Nadella too, everybody wants a sign
  Valentine's Day, I made the call
  Vienna to San Francisco, gave it all
  An agent even mama can use
  Steipete never stops, nothing left to lose

  [Chorus]
  I'm shipping code I'll never read
  OpenClaw is everything I need
  Weekend hack became a wildfire
  Seven hundred stars climbing every hour
  The lobster's got the power
  Oh, the lobster's got the power

  [Outro]
  [Fading synths, euphoric, driving to the end]
  The claw, the claw, OpenClaw
  The claw, the claw, OpenClaw

  ---
  Prompting techniques used

  Technique: Top-anchor style locking
  How it's applied: "Male falsetto vocals, high-energy 80s synthwave" leads the style

    field to lock the Weeknd-like lane
  ────────────────────────────────────────
  Technique: 4-component prompting
  How it's applied: Genre (80s synthwave/dance-pop), mood (euphoric/bright),
    instrumentation (synth arpeggios, punchy kicks, pulsing bass), vocals (male
    falsetto)
  ────────────────────────────────────────
  Technique: Metatag scaffolding
  How it's applied: [Intro], [Verse], [Pre-Chorus], [Chorus], [Bridge], [Outro]
    prevent chaotic arrangements
  ────────────────────────────────────────
  Technique: Inline production direction
  How it's applied: [Stripped back, synths exposed, building tension] in the Bridge
    nudges the mix per-section
  ────────────────────────────────────────
  Technique: Descriptive over imperative
  How it's applied: "driving synth arpeggios" and "punchy electronic kicks" instead
  of
    "make it sound like Blinding Lights"

  The faster tempo (180 vs Blinding Lights' 171 BPM) and "euphoric dance-pop / retro
  party anthem" descriptors push it toward the party energy you wanted while keeping
  the synthwave DNA.

**Result:** (Generated by Suno 5.0)

I followed up with prompts for a Kling 3.0 music video and the final result was this banger:

<video> ...

</details>

---

## 🤖 Telegram Bot

BriefBot includes a Telegram bot listener that receives research requests via Telegram messages and sends results back.

### Quick start

```

/briefbot setup

```

Select the **Telegram** section, add your bot token and chat ID, then start the listener.

### How it works

1. **Message the bot** on Telegram: `@YourBot AI news --deep`
2. The bot runs the full BriefBot pipeline
3. Results are sent back to the Telegram chat (text + optional audio/PDF)

### Pairing system

Unknown users receive a pairing code. The bot owner approves them:

```

/briefbot setup # to manage from Claude Code

````

Or standalone:

```bash
python ~/.claude/skills/briefbot/scripts/telegram_bot.py pair list
python ~/.claude/skills/briefbot/scripts/telegram_bot.py pair approve CODE
python ~/.claude/skills/briefbot/scripts/telegram_bot.py pair revoke CHAT_ID
````

### Standalone bot control

```bash
python ~/.claude/skills/briefbot/scripts/telegram_bot.py start    # Background
python ~/.claude/skills/briefbot/scripts/telegram_bot.py stop
python ~/.claude/skills/briefbot/scripts/telegram_bot.py status
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

### Research

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

### Delivery

| Flag                 | Description                                       |
| -------------------- | ------------------------------------------------- |
| `--email ADDRESS`    | Email the briefing (comma-separated for multiple) |
| `--telegram`         | Send via Telegram to default chat                 |
| `--telegram CHAT_ID` | Send via Telegram to a specific chat              |
| `--audio`            | Generate MP3 audio (ElevenLabs or edge-tts)       |

### Management

| Flag                | Description                                 |
| ------------------- | ------------------------------------------- |
| `setup`             | Interactive configuration wizard            |
| `--schedule "CRON"` | Create a scheduled job (e.g. `"0 6 * * *"`) |
| `--list-jobs`       | List all scheduled jobs                     |
| `--delete-job ID`   | Remove a scheduled job                      |

---

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
