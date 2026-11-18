# Arty style: paper diorama shorts

Every short is a **handmade paper-cutout diorama filmed like a tabletop miniature**.
The look test is `lookdev/paper_diorama.py` and its renders are in `lookdev/renders/`.

This guide exists so our shorts never read as a copy of another channel, in particular the
bean-head, ink-outline, painted-3D-world look used by channels such as RicksClips3000.
We borrow storytelling *technique* only (see the end of this file), never the look.

## 1. Look

| Element | Arty does | Never |
|---|---|---|
| Material | Layered cardstock with visible paper fibre, uneven risograph-style ink density, real card thickness | Smooth painted 3D textures |
| Edges | An off-white **die-cut margin** (sticker edge) around characters and key props; soft contact shadows between layers | Black ink outlines |
| Depth | Flat cards stacked in depth (sky, hills, sea, set, foreground grass), lit so each layer casts a shadow on the one behind | Full 3D environments |
| Lens | Real miniature optics: shallow depth of field, a blurred foreground layer, focus on the eyes | Deep-focus wides |
| Grade | AgX "Punchy", exposure about −0.35, warm paper whites | Pure white or pure black anywhere |

## 2. Palette (muted risograph)

`cream #F3E6CC` · `navy #23324A` (replaces black) · `teal #2E6F73` · `sea #3F8C8C` · `deep #24566B` ·
`sage #8FB3A0` · `moss #5E9A86` · `grass #2F5A47` · `mustard #E3A72F` · `coral #E8664A` ·
`ochre #D49A4A` · `clay #B9773F` · `kraft #C49A6C`. Night sky: `#2A3B63`.

Skin tones are always coloured paper (`#C9825B`, plus darker or lighter variants per character),
**never white**.

## 3. Characters: paper puppets

- **Head:** a soft square (superellipse), not a round bean. Coloured skin paper.
- **Face:** punched-hole navy eyes with one cream glint, coral cheek circles, a triangle nose
  notch, a small arc mouth. Expressions come from swapping these small pieces (eye shape,
  mouth arc, brow strips).
- **Body:** separate paper parts joined by **brass split pins** at the shoulders (and hips if
  needed). Limbs rotate around the pins, like a real paper puppet. This is our signature.
- **Proportions:** head about 40 % of height, stubby legs, chunky boots.
- **Identity:** each recurring character gets one coloured accessory (the keeper's coral
  beanie with teal band) and one silhouette feature.
- **Never use:** a round white head, dot eyes on blank white, a chef hat, a pirate dog, or any
  design lifted from another creator.

## 4. Camera and motion

- **Tabletop camera:** slow dolly, truck and crane moves, as if a real camera moves past a
  real set. No whip pans and no fast crane drops (those belong to the reference style).
- **Stepped motion:** characters animate **on twos** (12 drawings per second inside 30 fps
  output), like stop-motion. The camera stays smooth. Mixing the two is the signature feel.
- **Puppet acting:** pin rotations, tiny hops, a paper flutter on landings. Something always
  moves (waves sliding sideways, clouds drifting on their layer).
- **Shot sizes:** hook close-up on face plus prop, then a wide reveal of the set, then
  inserts on props and signs.

## 5. Pivot device (our topic change)

The reference style changes topic with a spoken "see," or "imagine" plus a camera pull-back.
**Arty changes topic with a physical stage device:**

1. **Paper curtain** (default): coral curtains with a scalloped hem slide in from both sides.
   The stage behind them switches (day to night, place A to place B), then they open.
2. **Turntable:** the whole diorama rotates 180° to reveal a second set built on its back.
3. **Page flip:** a foreground card folds down like a pop-up book page.

Every pivot gets a recurring **sound motif**: a paper swish followed by a wooden *clack*.
The palette also shifts to a cool blue key light with warm practical lights (lanterns,
windows) for the explanation beat.

## 6. Text

- **No word-by-word captions.** If the user wants captions, use phrase-level text in a
  rounded cream paper tag with navy text, top third, like a label taped to the set.
- **Prefer diegetic text:** pinned paper tags, signs and labels inside the diorama
  ("KEEPER WANTED"). It must read correctly (not mirrored).

## 7. Sound

- Use the user's voice unchanged. Music and SFX sit at 50 % of the voice level (the
  `cartoon-audio-short` mix rules still apply).
- **Music:** a light music-box or marimba bed, not a march loop.
- **SFX:** made from paper and craft sounds (rustle, card flick, split-pin squeak, wooden
  clack, a felt "thump" on landings).

## 8. Story structure (technique, which is fine to share)

These patterns are general short-form craft and are used across the whole format. We use
them with our own topics and words:

1. **Hook (0–3 s):** say the paradox as a fact in the first sentence, over a close-up of one
   prop.
2. **Setting:** one line answering who, where and when.
3. **Escalation:** two to four beats, each bigger; others doubt or mock.
4. **Pivot:** the stage device from section 5 plus the real mechanism, explained with an
   everyday analogy.
5. **Payoff:** a short ironic last line, landing on a prop or sign reveal.

## 9. Originality checklist (run before every render)

- [ ] The topic is our own pick and was researched by us. It is not a topic another channel just
      posted, and the title is not built on their format ("Why X Don't Work").
- [ ] The script is written from scratch. No sentences paraphrased from another video.
- [ ] No round white bean heads, no black ink outlines, no word-by-word white captions.
- [ ] No characters, mascots, logos or channel marks from other creators.
- [ ] Shots are planned from our script, not traced from a reference video's cut list.
- [ ] The pivot uses an Arty stage device and the swish-clack motif.

## Rendering the look test

```bash
blender -b -P lookdev/paper_diorama.py -- hook 50
blender -b -P lookdev/paper_diorama.py -- wide 50
blender -b -P lookdev/paper_diorama.py -- pivot 50
```

`50` is the render scale in percent of 1080x1920. `SAMPLES=64` gives a fast preview. The apt Blender
build (4.0.2) has no OpenImageDenoise, so the script uses plain path tracing with more
samples. In a fresh cloud container, reinstall Blender with
`apt-get update && apt-get install -y blender`.
