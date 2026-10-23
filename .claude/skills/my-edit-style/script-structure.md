# Script structure: ฮุก → บริบท → แต่ → เฉลย

From the slides "โครงสร้างคร่าวๆ" and "กรณีศึกษา 1" that the user sent (made by the same creator as
the reference). Use it to check or draft the script **before** cutting. The skill measures timing and
visuals; this file covers the content.

| Part | Length | Job | Colour on the creator's slide |
| --- | --- | --- | --- |
| **ฮุก** | 1 sentence | Make the viewer curious | red |
| **บริบท** | 3–4 sentences | Set up the character, the situation, or a belief many people hold | purple |
| **แต่** | 1 sentence | The sentence that flips the situation | blue |
| **เฉลย** | 3–4 sentences | Explain what actually happened, how it differs from what was expected | green |

## Example from the slide (กรณีศึกษา 1)

- **ฮุก:** เพื่อนๆรู้ไหมว่าในหนัง *Now You See Me* นักแสดงคนนี้เกือบจมน้ำเสียชีวิตในฉากนี้จริง ๆ
- **บริบท:** ในฉากนี้ เธอต้องแสดงเหมือนติดอยู่ในถังน้ำ
- **แต่:** แต่ไม่มีใครรู้เลยว่าเธอไม่ได้แสดง
- **เฉลย:** ที่เห็นคือกำลังจมน้ำจริง ๆ และร้องขอความช่วยเหลือ / ปัญหาคือทุกคนคิดว่าเป็นแค่การแสดง /
  โชคดีที่มีสตั้นท์แมนสังเกตเห็นความผิดปกติ และรีบเข้าไปช่วยเธอได้ทันเวลา

## Mapped onto the measured reference (the Avatar clip)

| Part | Time | Captions | Length |
| --- | --- | --- | --- |
| ฮุก | 0.00–4.47 s | เพื่อนๆ รู้มั้ยว่า ในหนัง Avatar ถ้าโทรศัพท์เผลอดังขึ้นมา เพื่อนๆ… เตรียมซื้อเครื่องใหม่ได้เลย | 4.5 s, 8 cards |
| บริบท | 4.47–10.77 s | ในเรื่องนี้ มีคนหลายร้อยชีวิตที่ต้องทำงานพร้อมกัน ทำให้การเสียเวลาแม้แต่นิดเดียวเป็นเรื่องใหญ่มาก | 6.3 s, 7 cards |
| แต่ / turn | 10.77–13.77 s | ผู้กำกับ James cameron จึงตั้งกฎเหล็กขึ้นมาว่า | 3.0 s. This clip uses **"จึง"** to turn instead of "แต่" [ไม่แน่ใจ whether the creator counts this as the "แต่" part] |
| เฉลย | 13.77– s | ถ้าโทรศัพท์ใครดังระหว่างถ่ายทำ เขาจะเอาปืนยิงตะปูตอนมันติดกำแพงให้ดูต่อหน้าทุกคน ซึ่งได้ผลดีมาก เพราะไม่มีใครพลาดเลย | ≥ 8 s (the recording cuts off) |

Things we saw in the reference that line up with the structure:
- The **ฮุก opens with "เพื่อนๆ รู้มั้ยว่า/รู้ไหมว่า + ในหนัง [ชื่อเรื่อง]"** in both examples.
- **B-roll changes when the part changes:** at the start of บริบท (4.83 s, behind-the-scenes footage), at the turn
  (11.00 s, cuts to James Cameron), and in เฉลย (13.77 s, on set).
- **The ending** uses a shot of the real person to back up the reveal.

## How to use it in the skill

1. Before running the edit, read the user's script (or the transcript from `transcribe.py`) and label each sentence
   ฮุก / บริบท / แต่ / เฉลย.
2. If a part is missing or too long (บริบท or เฉลย over 4 sentences, ฮุก over 1 sentence), **tell the user and
   suggest a fix**. Don't rewrite their words yourself.
3. In `broll.json`, give each part its own clips and set `keywords` to a noun in that part, so the B-roll cuts
   when the part changes.
4. The ฮุก should run about 3–5 s (reference 4.5 s). Use the clearest image of the topic as the first shot.
