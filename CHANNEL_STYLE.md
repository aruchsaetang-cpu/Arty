# Channel style (applies to every new video)

Reference: **Sunnah Edit** Shorts (12M–149M views each). Our channel is now **heartbreaking /
emotional true-moment Shorts**.

## Hard rules

- **Length ~20s, like the reference.** Vertical 1080×1920. Only the real moment itself: no talking heads, no photo collages, no filler.
- **No voice.** No narration, no TTS. Emotion comes from picture, text and music only.
- **One story per video**, built as a three-act arc: setup (who is it, what's wrong) →
  the turn (the painful or kind moment) → payoff (the tears, the reunion, the reveal).
- **Original topics.** Pick angles that the big edit channels have *not* done to death
  (see the topic bank below). Skip "man feeds hungry dog" and "boy gets surprise bike";
  those are saturated.

## Editing style (copied from the reference)

| Element | Spec |
|---|---|
| Hook text | Appears at 0.0–0.5s, centred mid-frame, wrapped in asterisks: `*SAD MOMENT*`. Heavy condensed sans (Anton / Montserrat Black), ALL CAPS, black stroke + soft glow. |
| Colours | Neon green `#39FF14` for kindness/good, yellow `#FFE600` for danger/attention, white for neutral lines, red only for one word of loss. Two-tone lines are common: line 1 white, line 2 green. |
| Text entrance | Keyboard/typewriter: every caption types in letter by letter (~24 letters/s). No explosive scale-in or slam on captions. |
| Callouts | Yellow circle drawn around the subject + curved arrow pointing at it, with a short label: `GOOD MAN`, `HELPLESS DOG`, `REAL BIKE`, `POOR MAN`. Pops in with a scale bounce. |
| Year / place stamp | Big white `2016` or `INDIA, 2019` over the footage for "true story" weight. |
| Watermark | Channel name, semi-transparent white, centre, lower third, on for the whole video. |
| Grade | Punchy: high contrast, +saturation, slight sharpen, light vignette. |
| Motion | Punch-in zooms on the key moment, freeze-frame + slow-mo on the emotional beat, quick flash cut into the payoff. |
| Captions | 2–4 text beats per video, max 5 words each, every one in `*ASTERISKS*`. Last beat is the emotional verdict: `*SALUTE TO THIS BOND*`, `*THE LAST GOODBYE*`. |
| SFX (sparing, attention only) | Sound is for grabbing attention, never wall-to-wall. Use it in two places only: the **opening** (shutter + white flash at 0s, `keyboard-typing` under the hook caption, `pop` on the first circle callout) and the **ending impact** (shutter, `bell-ding` as the heart lands, `keyboard-typing` under the verdict). Everything else is silent. Clean effects live in `assets/sfx/` (song removed). |
| Ending (every video) | Signature close, from the reference: (1) IMPACT: shutter + the frame blows out (bright pink/orange flash, punch-in to ~1.45× with heavy blur), a ghost echo copy trails offset, decaying camera shake, settle in ~0.6s, (2) the mending-heart emoji sticker (`assets/stickers/mending-heart.png`) pops over the subject and pulses, (3) zoom-blur out + dip to black, (4) fade into the video's first frame so the Short loops seamlessly. Built in `videos/gallop-last-wish/index.html` (`#leak`, `#heart`, `#loop`). |
| Music | Sad piano / strings swell, quiet first 3s, peak on the payoff. Royalty-free or generated (vidIQ `generate_music`). |

## Footage

**Real footage only, of the actual event.** No AI-generated clips, no animation, no stock
"re-enactments". Every video uses the real recording of that real situation.

Workflow per video:

1. Claude picks the story and gives you the YouTube link(s) plus the exact minutes to clip.
2. You download those parts and send them (or drop them in `videos/<name>/assets/footage/`).
3. Claude cuts them to 25–30s in the editing style above.

Credit the original creator in the description, and ask for permission when you can:
reposting someone else's footage can get copyright claims or strikes.

## Topic bank (less-covered angles)

1. A guide dog's last night: a cheese party, then goodbye (source: Molly Burke, `ucEeH2LKdes`).
2. A janitor graduates from the university he cleaned for 20 years.
3. A mother with dementia only remembers her son when he hums her old lullaby.
4. A firefighter is invited to the graduation of the baby he carried out of a fire.
5. A street cat waits every night at the door of the old man who fed it, after he's gone.
6. A grandmother learns to text so she can message her grandson abroad: her first "I miss you."
7. A deaf father hears his daughter's voice for the first time, at her wedding.
8. A boy sells his toys to pay for his dog's surgery; the vet hands the money back.
9. A night-shift nurse who sleeps in her car; her patients' families secretly raise rent.
10. A retired lighthouse keeper's dog still walks the pier at dusk.
11. A soldier's horse/dog recognises him after two years away.
12. A delivery rider who stops every day to help the same old woman across the road; one day she isn't there.

## What is breaking out right now (vidIQ outliers, Shorts, Oct 2026)

Small channels getting far more views than their own average, with emotional stories:

- **Old animal's last visit**: "For nearly 16 years, he went to the cows every morning. Then his
  farmer took him back one last time" (160K, 11× its channel's average).
- **Sacrifice for family**: "Selling his beloved cow for his mother's medical treatment" (230K, 32×).
- **Animal loss**: "This poor mother dog lost all her puppies before they were born" (400K, 77×).
- **Dog loyalty**: "The most heartbreaking display of dog loyalty" (800K, 295×, only 8 seconds long).

Takeaway: animal loyalty and quiet sacrifice outperform. Topics 1, 5, 8, 10 and 11 above fit
this best and are still rare as polished edits.

## Channel description (paste into YouTube → Customise channel → Description)

> Real moments that break your heart, and the kindness that puts it back together.
> Short true stories about love, loss, loyalty and second chances, told in 30 seconds
> with no words, only feeling. New story every day.
> If one made you cry, share it with someone who needs it. 💔

## Per-video description template

```
*<HOOK TEXT>* 💔

<One sentence that sets up the story without spoiling the payoff.>
Watch till the end.

#shorts #emotional #heartbreaking #kindness #<topic> #<animal-or-person>
```
