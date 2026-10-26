"""The session texts of the example project smoke-plume, as plain data for build_smoke_plume.py.

One entry per working session: its log (the five headings of spec §11) and the PROJECT.md
"Current status" written at its end, both keyed by the log's file name. As in
smoke_plume_content.py, provenance comes from the builder's steps, not from here.
"""

from typing import Any

# Section texts: a list is written as one '- ' bullet per item.
LOGS: dict[str, dict[str, Any]] = {
    "2026-10-25-fan-claude-code-1432": {
        "start": "14:32", "end": "16:05",
        "Done": [
            ("Proposed Q-2026-10-25-plume-baselines and Q-2026-10-25-abi-band-choice; Fan "
             "approved both."),
            ("Added smith2024-plume-goes (core, 3 claims) and jones2023-plume-unet (supporting, "
             "2 claims), each read in full."),
            ("Started knowledge/goes-abi.md with the band-7 resolution from smith2024-plume-goes "
             "§2.1 p.3, approved by Fan."),
            "Proposed D-2026-10-25-loss-function (Dice loss); Fan accepted it.",
        ],
        "Tried and failed": [
            ("Looked for released code or labels of smith2024-plume-goes: the paper names none, "
             "so Table 3 cannot be reproduced yet."),
        ],
        "Unfinished": [
            ("jones2023-plume-unet Table 1 gives band 7 at 1 km, against the 2 km fact in "
             "knowledge/goes-abi.md. Not proposed as a fact yet: it needs a second look at both "
             "PDFs."),
        ],
        "Suggested next step": [
            ("A second reader re-reads smith2024-plume-goes in full, then compares "
             "jones2023-plume-unet Table 1 with knowledge/goes-abi.md."),
        ],
        "Files touched": [
            "questions/Q-2026-10-25-plume-baselines.md, questions/Q-2026-10-25-abi-band-choice.md",
            "literature/smith2024-plume-goes.md and its PDF",
            "literature/jones2023-plume-unet.md and its PDF",
            "knowledge/goes-abi.md, knowledge/README.md",
            "decisions/D-2026-10-25-loss-function.md",
        ],
    },
    "2026-10-26-fan-claude-code-1005": {
        "start": "10:05", "end": "10:50",
        "Done": [
            ("Proposed Q-2026-10-26-dataset-size (storage for one fire season of band-7 scans); "
             "Fan approved it."),
            "Proposed D-2026-10-26-eval-metric (mIoU as the primary metric); Fan accepted it.",
        ],
        "Tried and failed": [
            ("Looked for per-class IoU in jones2023-plume-unet to set beside ours: Table 2 gives "
             "only mIoU, so only the primary metric of D-2026-10-26-eval-metric compares."),
        ],
        "Unfinished": [
            ("Q-2026-10-26-dataset-size is open: the estimate needs the band-7 resolution, and "
             "jones2023-plume-unet Table 1 (1 km) still disagrees with knowledge/goes-abi.md."),
        ],
        "Suggested next step": [
            ("A second reader settles the band-7 resolution (smith2024-plume-goes §2.1 p.3 "
             "against jones2023-plume-unet Table 1); then Q-2026-10-26-dataset-size can close."),
        ],
        "Files touched": [
            "questions/Q-2026-10-26-dataset-size.md",
            "decisions/D-2026-10-26-eval-metric.md",
        ],
    },
    "2026-10-27-lee-codex-0910": {
        "start": "09:10", "end": "11:40",
        "Done": [
            ("Re-read smith2024-plume-goes in full: verified the Table 3 and §2.1 p.3 claims, "
             "disputed the night-time claim (Fig. 6, p.9) and added a label-noise caveat to the "
             "summary."),
            ("Opened jones2023-plume-unet at Table 1: it does give band 7 at 1 km. Added that "
             "fact to knowledge/goes-abi.md beside the 2 km fact and marked the two as a "
             "CONFLICT pair; Lee approved."),
        ],
        "Tried and failed": [
            ("Trained the U-Net baseline for two epochs with Dice loss alone "
             "(D-2026-10-25-loss-function) on 200 tiles: on tiles without smoke it labelled "
             "cloud edges as smoke."),
        ],
        "Unfinished": [
            ("jones2023-plume-unet needs a full re-read: only Table 1 was opened, so its two "
             "claims are still unverified."),
        ],
        "Suggested next step": [
            ("A human resolves the band-7 CONFLICT in knowledge/goes-abi.md, for example "
             "against the GOES-R ABI product user guide."),
            "Fan decides whether the false positives call for a new loss decision.",
            ("Fan checks whether Q-2026-10-26-dataset-size can be answered now that "
             "knowledge/goes-abi.md holds both resolutions."),
        ],
        "Files touched": ["literature/smith2024-plume-goes.md", "knowledge/goes-abi.md"],
    },
    "2026-10-28-fan-codex-1000": {
        "start": "10:00", "end": "10:45",
        "Done": [
            ("Proposed D-2026-10-28-loss-function-v2 (Dice plus binary cross-entropy) after "
             "Lee's smoke test; Fan accepted it, and it supersedes D-2026-10-25-loss-function."),
            ("Closed Q-2026-10-26-dataset-size as answered by knowledge/goes-abi.md: a season "
             "fits the 2 TB budget at either band-7 resolution."),
            ("Read brown2022-cloud-masks in full and recorded it as not-useful: it has no smoke "
             "class."),
        ],
        "Tried and failed": [
            ("Looked in brown2022-cloud-masks for a smoke or aerosol label to reuse: thick "
             "smoke is labelled cloud and thin smoke clear, so its masks cannot separate smoke "
             "from cloud."),
        ],
        "Unfinished": [
            "The band-7 CONFLICT in knowledge/goes-abi.md is still open.",
            "jones2023-plume-unet still has no second reader.",
        ],
        "Suggested next step": [
            ("Resolve the band-7 CONFLICT, then retrain the U-Net baseline under "
             "D-2026-10-28-loss-function-v2."),
        ],
        "Files touched": [
            "decisions/D-2026-10-28-loss-function-v2.md, decisions/D-2026-10-25-loss-function.md",
            "questions/Q-2026-10-26-dataset-size.md",
            "literature/brown2022-cloud-masks.md and its PDF",
        ],
    },
}

# PROJECT.md "Current status" after each session, keyed by the session's log file.
STATUS: dict[str, list[str]] = {
    "2026-10-25-fan-claude-code-1432": [
        ("Literature review under way: smith2024-plume-goes (core) and jones2023-plume-unet "
         "(supporting) are in; neither has a second reader yet."),
        "Open questions: Q-2026-10-25-plume-baselines, Q-2026-10-25-abi-band-choice.",
        "Accepted: D-2026-10-25-loss-function (Dice loss).",
        ("Watch: jones2023-plume-unet Table 1 (band 7 at 1 km) disagrees with "
         "knowledge/goes-abi.md (2 km)."),
    ],
    "2026-10-26-fan-claude-code-1005": [
        ("Literature review under way: smith2024-plume-goes (core) and jones2023-plume-unet "
         "(supporting); neither has a second reader yet."),
        ("Open questions: Q-2026-10-25-plume-baselines, Q-2026-10-25-abi-band-choice, "
         "Q-2026-10-26-dataset-size."),
        "Accepted: D-2026-10-25-loss-function (Dice loss) and D-2026-10-26-eval-metric (mIoU).",
        ("Watch: jones2023-plume-unet Table 1 (band 7 at 1 km) disagrees with "
         "knowledge/goes-abi.md (2 km); Q-2026-10-26-dataset-size depends on it."),
    ],
    "2026-10-27-lee-codex-0910": [
        ("smith2024-plume-goes re-read by Lee: two claims verified, the night-time claim "
         "disputed."),
        ("knowledge/goes-abi.md: the band-7 resolution is a CONFLICT pair (2 km and 1 km) "
         "waiting for a human."),
        ("Open questions: Q-2026-10-25-plume-baselines, Q-2026-10-25-abi-band-choice, "
         "Q-2026-10-26-dataset-size."),
        "Accepted: D-2026-10-25-loss-function (Dice) and D-2026-10-26-eval-metric (mIoU).",
        ("A Dice-only smoke test gave false positives on tiles without smoke (Lee's log of "
         "2026-10-27)."),
    ],
    "2026-10-28-fan-codex-1000": [
        ("Literature: smith2024-plume-goes (core), jones2023-plume-unet (supporting), "
         "brown2022-cloud-masks (not-useful)."),
        ("One disputed claim (smith2024-plume-goes, Fig. 6); the two jones2023-plume-unet "
         "claims are unverified."),
        "knowledge/goes-abi.md: the band-7 resolution CONFLICT (2 km and 1 km) is still open.",
        ("Open questions: Q-2026-10-25-plume-baselines, Q-2026-10-25-abi-band-choice; "
         "Q-2026-10-26-dataset-size is answered."),
        ("Accepted: D-2026-10-26-eval-metric (mIoU) and D-2026-10-28-loss-function-v2 (Dice "
         "plus cross-entropy), which supersedes D-2026-10-25-loss-function."),
    ],
}
