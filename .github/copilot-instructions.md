---
applyTo: "commit-message"
---

Follow the most recent Conventional Commits specification.

---
applyTo: "**/*"
---
The code is a home assistant custom integration component for controlling covers (i.e., garage doors and gates produced by Sommer and controlled through their SOMweb device).

Currently the component is published through Hacs and must adhere to any publishing guidelines defined by them at https://www.hacs.xyz/docs/publish/. The future plan is to make the component an official Home Assistant component so all and any guidelines defined by the Home Assistant developer doucmentation as https://developers.home-assistant.io/ must be followed. The integration quality must target Platinum or, if not possible, as a minimum Gold as specified by Home Assistant.

Use context7 or web search to get the most recent documentation and guidelines for creating home assistant components deployed through hacs.

Do not create any markdown documentation on inplemented changes unless requested to do so.

---
applyTo: "**/*.py"
---
Before making any code changes, you must first use reasoning to analyze the problem and plan your approach. Choose the simplest, most standard solution. If there are multiple ways to solve something, pick the cleanest and most stable approach that follows the guidelines and the adheres to the defined quality requirements. Explain why you chose the approach.

When advicing or coding, you should:
- State uncertainty clearly: "I'm not certain, but...", "This should be verified against..."
- Cite sources: "According to the HA docs at...", "Based on the quality scale rules..."
- Acknowledge when I'm inferring: "This seems like it would be...", "Typically the pattern is..."
- Admit gaps: "I don't have enough context on...", "You should verify this in the docs..."
- Reason through edge cases: Consider counter-arguments before stating advice
