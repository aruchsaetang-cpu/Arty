"""Retention cuts (v2) of the case-board shorts: payoff first, ~15s, loops.

Same evidence style as topics.py; the first line is the most shocking fact, and the
last shot returns to the first piece of evidence so the short loops.
"""

V2 = {
    "005": {
        "hook": ["3 MEN", "*VANISHED* HERE."],
        "lines": [
            {"say": "Three lighthouse keepers vanished from this island, and one of them left his coat behind.",
             "item": {"type": "photo", "icon": "lighthouse", "label": "FLANNAN ISLES, 1900"}},
            {"say": "It was December nineteen hundred, off the coast of Scotland.",
             "cap": "It was December 1900, off the coast of Scotland.",
             "item": {"type": "note", "text": "DEC 1900", "sub": "Flannan Isles, Scotland"}},
            {"say": "The light was dark. The door and the gate were shut.",
             "item": {"type": "note", "text": "LIGHT: OUT", "sub": "door and gate closed"}},
            {"say": "Two oilskins were gone. The third still hung on its hook.",
             "item": {"type": "note", "text": "OILSKINS: 2 OF 3", "sub": "one left behind"}},
            {"say": "None of them were ever found.",
             "item": {"type": "note", "text": "3 KEEPERS · 0 FOUND", "sub": "case open"}},
        ],
        "question": "WHERE DID THEY GO?",
    },
    "006": {
        "hook": ["115 PEOPLE.", "*1* WORD LEFT."],
        "lines": [
            {"say": "A hundred and fifteen people vanished, and left one word carved into a post.",
             "cap": "115 people vanished, and left one word carved into a post.",
             "item": {"type": "photo", "icon": "post", "label": "THE ONLY CLUE"}},
            {"say": "Croatoan.",
             "item": {"type": "note", "text": "CROATOAN", "sub": "carved into the fort"}},
            {"say": "Roanoke Island, fifteen ninety. Their governor had been gone for three years.",
             "cap": "Roanoke Island, 1590. Their governor had been gone for three years.",
             "item": {"type": "map", "label": "ROANOKE ISLAND", "sub": "1590"}},
            {"say": "The houses were taken down. No bodies. No sign of a fight.",
             "item": {"type": "note", "text": "NO BODIES", "sub": "no sign of a fight"}},
            {"say": "No one knows where they went.",
             "item": {"type": "note", "text": "THE LOST COLONY", "sub": "never found"}},
        ],
        "question": "WHERE DID THEY GO?",
    },
    "007": {
        "hook": ["HE JUMPED", "WITH *$200,000.*"],
        "lines": [
            {"say": "This man jumped out of a plane with two hundred thousand dollars, and vanished.",
             "cap": "This man jumped out of a plane with $200,000, and vanished.",
             "item": {"type": "photo", "icon": "parachute", "label": "INTO THE NIGHT"}},
            {"say": "In nineteen seventy one, he hijacked a jet, saying his briefcase held a bomb.",
             "cap": "In 1971, he hijacked a jet, saying his briefcase held a bomb.",
             "item": {"type": "photo", "icon": "jet", "label": "FLIGHT 305, 1971"}},
            {"say": "He took the cash and four parachutes, then jumped into the dark.",
             "item": {"type": "note", "text": "$200,000", "sub": "+ 4 parachutes"}},
            {"say": "Nine years later, a boy found some of the money by a river.",
             "item": {"type": "note", "text": "$5,800 FOUND", "sub": "Columbia River, 1980"}},
            {"say": "He has never been identified.",
             "item": {"type": "note", "text": "D.B. COOPER", "sub": "identity unknown"}},
        ],
        "question": "WHO WAS HE?",
    },
    "008": {
        "hook": ["NO ONE", "CAN *READ* THIS."],
        "lines": [
            {"say": "No one on Earth can read this book.",
             "item": {"type": "photo", "icon": "book", "label": "THE VOYNICH MANUSCRIPT"}},
            {"say": "It's about six hundred years old.",
             "item": {"type": "note", "text": "~600 YEARS", "sub": "carbon dated 1404–1438"}},
            {"say": "Plants that don't exist. Star charts no one can match.",
             "item": {"type": "note", "text": "~240 PAGES", "sub": "plants, stars, baths"}},
            {"say": "The world's best codebreakers have tried for a century.",
             "item": {"type": "note", "text": "100+ YEARS", "sub": "of codebreaking"}},
            {"say": "No one has ever proven they can read it.",
             "item": {"type": "note", "text": "DECODED: 0", "sub": "case open"}},
        ],
        "question": "WHAT DOES IT SAY?",
    },
    "009": {
        "hook": ["6 PLANES.", "*27* MEN. GONE."],
        "lines": [
            {"say": "Five Navy planes vanished, and then the plane sent to find them vanished too.",
             "item": {"type": "photo", "icon": "bomber", "label": "FLIGHT 19, 1945"}},
            {"say": "December nineteen forty five, off the coast of Florida.",
             "cap": "December 1945, off the coast of Florida.",
             "item": {"type": "note", "text": "DEC 5, 1945", "sub": "Fort Lauderdale"}},
            {"say": "The leader radioed that both of his compasses had failed.",
             "item": {"type": "note", "text": "COMPASSES: OUT", "sub": "last radio calls"}},
            {"say": "Twenty seven men. Six aircraft. In one evening.",
             "item": {"type": "note", "text": "27 MEN · 6 PLANES", "sub": "one evening"}},
            {"say": "No wreckage was ever found.",
             "item": {"type": "map", "label": "BERMUDA TRIANGLE", "sub": "no wreckage"}},
        ],
        "question": "WHAT TOOK THEM?",
    },
}
