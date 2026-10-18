# The 3-minute pitch

Slides: `OASIS-pitch.pptx` (or `.pdf`). Live demo: https://oasis.eklavyagoyal.com

**0:00 · Slide 1, Oasis.** "Every counter-drone system learns from data where someone knows the right answer. For drones over Ukraine, that data barely exists. We built Oasis to generate it."

**0:15 · Slide 2, the gap.** "Real recordings are scarce, classified and unlabelled. Nobody can tell you which radio burst came from which drone. And they never contain the cases that matter most: a fibre-optic drone, a jammer, spoofed GPS."

**0:30 · Slide 3, what it makes.** "Oasis builds one true world over real terrain: every drone, pilot and decoy on one clock. Then it records what ten sensors would physically capture. At the core is the signal trace: radio bearings shaped by terrain and jamming. When a ridge hides the drone, the receiver goes silent. Crossed bearings locate the pilot, and everything exports to TAK. And every record comes with an answer key: which object caused it, and why."

**1:00 · Slide 4, the proof.** "Why not just ask an LLM? We did: same scenario, same ten minutes, same ten independent checks. Its timestamps run backwards and its bearings are off by tens of degrees. It passes one of the four checks it can even be tested on. Oasis passes all nine that apply, with eight thousand records against forty. And the auditor never uses our physics, so it can't simply agree with us."

**1:25 · Slide 5, live demo.** Click the link, then **Enter simulation**, then **Hero day**.
- "At 14:02:07 this Mavic sits exactly on the brief's example point. The amber lines are the bearings two masts recorded; where they cross is our fix, and this line is its error against the truth."
- Switch to **Operator**: "this is all a defender sees." Then **God mode**: "and this is what really happened."
- Scrub to **14:10**: "A fibre-optic drone launches. No radio link, so no electronic sensor records it; only civilians report it. That is the case real data never contains."
- Open **Scenarios**: "Eleven scenarios, every one generated and audited the same way. The world stays fixed; the seed changes only what flies."

**2:50 · Close.** "That's Oasis. Every record has an answer. Thank you."
