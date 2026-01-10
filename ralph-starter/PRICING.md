# Ralph Mode - Pricing Strategy

## The Business Model

### What's Free (Open Source)
- Basic Ralph pattern (bash loop)
- Local Ollama integration
- Simple prd.json structure
- Documentation

**This is the "car without the engine."** It works, but it's basic.

---

### What's Paid (Subscription)
The MAGIC happens on your hosted infrastructure:

| Feature | Free (Local) | Paid (Subscription) |
|---------|--------------|---------------------|
| Basic coding loop | Yes | Yes |
| Local AI responses | Yes | Yes |
| **Voice input** | No | Yes |
| **Translation layer** (speech → theatrical scene) | No | Yes |
| **Character voices** (Simpsons personalities) | No | Yes |
| **Scene generation** (atmosphere, weather, immersion) | No | Yes |
| **Broadcast-safe mode** (secret filtering) | No | Yes |
| **Multi-user tiers** (Mr. Worms, Power Users, Viewers) | No | Yes |
| **Hidden admin commands** | No | Yes |
| **GIF intelligence** (no repeats, trending) | No | Yes |
| **Response freshness** (never repetitive) | No | Yes |
| **Family dynamics** (workers have lives) | No | Yes |
| **Feedback submission** | No | Builder+ only |
| **Priority feedback** | No | Priority tier only |
| **Shape the product (RLHF)** | No | Builder+ only |

---

## Subscription Tiers (Primary Model)

| Tier | Price | What You Get |
|------|-------|--------------|
| **Trial** | FREE | 7-day trial, 1 group, no feedback |
| **Viewer** | $5/month | Watch stream, use bot, NO feedback rights |
| **Builder** | $10/month | Full access + submit feedback + shape the product |
| **Priority** | $20/month | Feedback weighted 2x, features built faster, direct line |

### Why Subscription?

**The RLHF Gate**: Only ACTIVE paying subscribers can submit feedback. This ensures:

1. **Quality Signal**: Paying users = serious users = better feedback
2. **No Zombie Accounts**: Can't pollute feedback queue with abandoned accounts
3. **Skin in the Game**: Monthly commitment filters for people who actually use it
4. **Continuous Revenue**: Predictable MRR for higher valuation multiple
5. **Natural Churn**: Low-quality contributors naturally leave

### The RLHF Loop

```
User pays $10/month → User can submit feedback → Feedback shapes product
        ↑                                              ↓
        └──────── Better product → More users ←────────┘
```

**The cream rises to the top.** Only paying, active users influence development.

---

## Tier Details

### Viewer ($5/month)
- Use the bot in your Telegram groups
- Watch the live build stream
- Access to stable releases
- Community Discord access
- **Cannot submit feedback**
- Good for: Teams who just want the tool, viewers of the stream

### Builder ($10/month) - RECOMMENDED
- Everything in Viewer
- **Submit bug reports and feature requests**
- **Your feedback influences development**
- Access to beta releases
- Vote on feature priorities
- Good for: Active users who want to shape the product

### Priority ($20/month)
- Everything in Builder
- **Feedback weighted 2x in priority algorithm**
- **Features you request get built faster**
- Direct channel to development
- Access to alpha/nightly builds
- First to try new features
- Name in credits
- Good for: Power users, agencies, companies relying on Ralph

---

## Why This Works (IP Protection)

### The Server-Side Secret Sauce
Users connect their Telegram to YOUR server. The following never leaves your infrastructure:

1. **Translation Prompts** - The exact prompts that turn speech into theatrical scenes
2. **Character Definitions** - The personality matrices for each character
3. **Sanitization Regex** - The patterns that catch secrets
4. **Scene Generation Logic** - How atmosphere is created
5. **Freshness Algorithms** - How we prevent repetition
6. **Admin Command Parser** - The hidden command system
7. **Feedback Screening System** - How we filter and prioritize

### What Users See
- They download a Telegram bot that connects to your API
- They never see the prompts, logic, or secret sauce
- Even if they reverse-engineer the client, the magic is server-side

### The Moat
- Open source the basic pattern = free marketing
- Everyone can try Ralph = viral potential
- But the FULL experience requires your server
- Network effects: More users = better feedback = better product
- RLHF flywheel: Paying users make it better for everyone

---

## Revenue Projections (Subscription Model)

### Conservative (Year 1)
- 500 Viewers at $5/month = $2,500/month = $30,000/year
- 300 Builders at $10/month = $3,000/month = $36,000/year
- 50 Priority at $20/month = $1,000/month = $12,000/year
- **Total: $78,000/year | $6,500 MRR**

### Moderate (Year 1)
- 2,000 Viewers at $5/month = $10,000/month = $120,000/year
- 1,000 Builders at $10/month = $10,000/month = $120,000/year
- 200 Priority at $20/month = $4,000/month = $48,000/year
- **Total: $288,000/year | $24,000 MRR**

### Optimistic (Year 1)
- 5,000 Viewers at $5/month = $25,000/month = $300,000/year
- 3,000 Builders at $10/month = $30,000/month = $360,000/year
- 500 Priority at $20/month = $10,000/month = $120,000/year
- **Total: $780,000/year | $65,000 MRR**

### Target: $1M Valuation
- $65,000 MRR × 12 = $780,000 ARR
- 10-15x revenue multiple (SaaS) = $7.8M - $11.7M valuation
- Even conservative $24,000 MRR × 10x = $2.9M valuation

---

## Payment Integration

### Stripe (Primary)
- Industry standard
- Easy subscription management
- Handles upgrades/downgrades
- Webhooks for real-time status
- Works worldwide

### Telegram Payments (Secondary)
- Built into Telegram
- Users never leave the app
- Good for impulse purchases
- Limited subscription support

### Integration Flow
```python
# Pseudocode for subscription check
def can_submit_feedback(user_id: int) -> bool:
    subscription = get_user_subscription(user_id)

    if not subscription:
        return False

    if subscription.tier == "viewer":
        return False  # Viewers can't submit feedback

    if subscription.status != "active":
        return False  # Must be actively paying

    return True  # Builder or Priority can submit

def get_feedback_weight(user_id: int) -> float:
    subscription = get_user_subscription(user_id)

    if subscription.tier == "priority":
        return 2.0  # Priority feedback weighted 2x

    return 1.0  # Standard weight
```

---

## Subscription Unlock Flow

```
User: /start
Bot: Welcome! You're on a 7-day free trial.

[7 days later]

Bot: Your trial has ended! Choose your tier:
     [Viewer $5/mo] [Builder $10/mo] [Priority $20/mo]

User: [Clicks Builder]
Bot: [Stripe Checkout opens]

[After payment]

Bot: *The office lights flicker on. Ralph looks up from his desk.*
     "Oh hey! The boss is back. What are we building today?"

     You're now a Builder! You can submit feedback that shapes Ralph's future.
     Use /feedback to report bugs or request features.
```

---

## Feedback Gating in Practice

### What Viewers See
```
User: /feedback I want dark mode!
Bot: *Ralph scratches his head*
     "Ooh, feedback! But my boss says only Builders can tell us what to build."

     [Upgrade to Builder - $10/mo]
```

### What Builders See
```
User: /feedback I want dark mode!
Bot: *Ralph writes it down on a sticky note*
     "Dark mode! Got it! I'll tell the team."

     Your feedback has been logged. Current priority: calculating...
     You'll be notified when we start building this!
```

### What Priority Users See
```
User: /feedback I want dark mode!
Bot: *Ralph writes it down in big letters*
     "DARK MODE! VIP request! Moving to the front!"

     Priority feedback received! This will be weighted 2x in our queue.
     Estimated: Next build cycle (24-48 hours)
```

---

## Protecting the IP

### Legal
- Terms of Service prohibiting reverse engineering
- DMCA for any leaked prompts
- Trademark "Ralph Mode" and "Mr. Worms"

### Technical
- All magic is server-side API calls
- Client only sends requests, receives formatted responses
- Prompts never transmitted to client
- Rate limiting prevents scraping
- Subscription verification on every API call

### Practical
- Even if someone copies the concept, your implementation is ahead
- Network effects create moat (your feedback database, trained behaviors)
- Brand recognition matters
- RLHF data is proprietary and valuable

---

## Recommended Approach

### Phase 1: Build the Audience
- Open source the basic pattern
- Free trial for everyone
- Build viral content (live streams, demos)

### Phase 2: Launch Subscriptions
- $5/$10/$20 tiers as described
- Gate feedback behind Builder+
- Start collecting RLHF data

### Phase 3: The Flywheel
- Feedback improves product
- Better product attracts users
- More users = more feedback
- Repeat forever

### Phase 4: Scale & Exit
- Hit $50k+ MRR
- Attract acquisition interest
- Or keep running the money printer

---

## Notes

- The Simpsons is copyrighted by Fox - may need to genericize characters for commercial use
- Consider "inspired by" characters rather than direct Simpsons names
- "Ralph Mode" as brand, characters could be "The Intern", "The Veteran", etc.
- Or license / parody protection (consult lawyer)

---

*"The cream rises to the top, and that's what builds the bot."*
