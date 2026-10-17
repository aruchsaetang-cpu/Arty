---
name: animation
description: One entry point for making an animation, video or short film in this repo. Routes to the installed HyperFrames skills or the Lemo-Opuscar film library, and covers the "one take" screencast and collage B-roll looks. Use when the user types /animation or asks for an animation, video, short, promo, explainer or motion graphic.
argument-hint: "[what to make] [optional: one take | collage b-roll | <lemo style>]"
---

# /animation

Make what the user asked for with the skills installed next to this one. Pick one route, load that skill with the Skill tool, and follow it from there. If the request says nothing about look or framework, ask once: "HyperFrames (product, UI, motion graphics) or a Lemo-Opuscar film style?"

## Routes

| The user wants | Load |
|---|---|
| A film in a named art style (watercolor, ukiyo-e, pixel RPG, silent film, …), or help picking one | `lemo-opuscar` |
| **One take**: a continuous screen-recording walkthrough where Clawd, the Claude Code mascot, acts out the product | `lemo-opuscar`, style `living-screencast` |
| **Collage B-roll**: cut-out photos, tape, paper scraps and footage layered as B-roll between or under the main shots | `hyperframes` (see below) |
| Product promo or launch from a URL or brief | `product-launch-video` |
| Explainer from text, no footage | `faceless-explainer` |
| Short motion graphic, kinetic type, logo sting, chart hit | `motion-graphics` |
| Beat-synced video from a music track | `music-to-video` |
| Video from a GitHub PR | `pr-to-video` |
| Captions or graphic overlays on existing footage | `embedded-captions` / `talking-head-recut` |
| Anything else, or unsure | `hyperframes` |

## Collage B-roll

There is no dedicated skill for this, so build it in HyperFrames:

1. Load `hyperframes`; it hands off to `general-video` for the composition.
2. Get the pieces with `media-use` (images, cut-outs via background removal, footage, paper and tape textures). Use the user's own media first.
3. Search `hyperframes-registry` for paper, grain, tape or scrapbook blocks before drawing any.
4. Animate with `hyperframes-animation` and `hyperframes-keyframes`: pieces drop in with a little overshoot and rotation, slow Ken Burns drift on photos, quick stop-motion style holds (2–3 frames), and layers that slide off to reveal the next shot.
5. Keep B-roll on its own track under the narration or main shot, per `hyperframes-studio`.

## Lemo-Opuscar setup

The first Lemo-Opuscar film runs `.claude/skills/lemo-opuscar/scripts/setup.sh`, which downloads the style library to `~/lemo-opuscar` and installs its Node and Python packages. Tell the user before it runs; it takes a few minutes.
