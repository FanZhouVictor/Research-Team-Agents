"""The text of the example project smoke-plume, as plain data for build_smoke_plume.py.

PROJECT.md, questions, literature, knowledge and decisions are here, keyed by final id or file
name; the session logs and status texts are in smoke_plume_sessions.py. Provenance (who, which
agent, which day) is not: the builder takes it from the step that writes the text, so a file
never names another author than its commit. The papers, authors and DOIs are invented.
"""

from typing import Any

NAME = "Smoke Plume"
NOTICE = (
    "Illustrative example built by examples/build_smoke_plume.py in the framework repository: "
    "the papers in literature/, their authors and their DOIs (prefix 10.5555, used for "
    "examples) are invented."
)
FOUNDER: dict[str, Any] = {"person": "Fan", "email": "fan@x", "role": "PI",
                           "platforms": ["claude-code", "codex"]}
MEMBER: dict[str, Any] = {"person": "Lee", "email": "lee@x", "role": "PhD student",
                          "platforms": ["codex"]}
PROJECT: dict[str, Any] = {
    "subject": "filled in goals and phase; added member Lee",
    "goals": [
        ("Segment wildfire smoke plumes in GOES-16 ABI imagery and beat the published baselines "
         "on a held-out fire season."),
        "Settle which ABI bands the model needs, by day and by night.",
        "Keep every number we rely on traceable to a paper someone on the team read in full.",
    ],
    "phase": "Literature review",
}

QUESTIONS: dict[str, dict[str, str]] = {
    "Q-2026-10-25-plume-baselines": {
        "title": "What are the strongest published baselines for plume segmentation on GOES-16?",
        "context": "Any result we report has to beat the best published number on comparable "
        "GOES-16 data, so we need to know which models and test seasons those numbers come "
        "from. The answer also decides which baseline we re-implement first.",
        "note": "candidates so far are a 2024 transformer paper and the U-Net it compares "
        "against; both to be read in full.",
    },
    "Q-2026-10-25-abi-band-choice": {
        "title": "Which GOES-16 ABI bands should the model take as input?",
        "context": "Smoke shows in the visible bands by day, but at night only the infrared "
        "bands see it, and band 7 (3.9 µm) also picks up the fires that feed the plumes. Every "
        "extra band adds storage and resampling work, so we want the smallest set that keeps "
        "accuracy.",
        "note": "the band set of whichever baseline we adopt is the first candidate.",
    },
    "Q-2026-10-26-dataset-size": {
        "title": "Does one fire season of GOES-16 band-7 CONUS scans fit in the lab's 2 TB budget?",
        "context": "We want the June–October scans at the 5-minute CONUS cadence on disk before "
        "training starts. The size of a scene depends on the band-7 resolution, so the answer "
        "should come from knowledge/goes-abi.md, not from memory.",
        "note": "proposed while planning the download; one season is also what "
        "jones2023-plume-unet trains on.",
        "answered-by": "knowledge/goes-abi.md",
        "close note": "answered from knowledge/goes-abi.md. At 2 km a CONUS scene is about "
        "2500 × 1500 px (7.5 MB as 16-bit), so a season is about 330 GB; at the 1 km of the "
        "CONFLICT line it is about 1.3 TB. Both fit, so the answer holds whichever way the "
        "conflict is resolved.",
    },
}

LITERATURE: dict[str, dict[str, Any]] = {
    "smith2024-plume-goes": {
        "subject": "transformer smoke plume segmentation from GOES-16 imagery",
        "meta": {
            "title": "Transformer-based smoke plume segmentation from GOES-16 imagery",
            "authors": ["Smith J", "Patel R"], "year": 2024,
            "venue": "Remote Sensing of Environment",
            "doi": "10.5555/example.2024.1", "relevance": "core",
            "bears-on": ["Q-2026-10-25-plume-baselines", "Q-2026-10-25-abi-band-choice"],
        },
        "summary": "The paper segments wildfire smoke plumes in GOES-16 ABI scenes with a "
        "vision-transformer encoder and a light convolutional decoder. Inputs are ABI bands 1, "
        "3 and 7 over the CONUS sector, and labels are NOAA Hazard Mapping System (HMS) smoke "
        "polygons rasterised to the band-7 grid. The 2019 and 2020 fire seasons are used for "
        "training and the 2021 season is held out. On the held-out season the transformer "
        "beats a U-Net baseline by 4.2 mIoU, with the largest gains on thin plumes far from the "
        "fire. Accuracy is lower at night, when the visible bands carry no signal.",
        "why": "It is the strongest published result we know of for GOES-16 plume "
        "segmentation, so its Table 3 number is the bar for Q-2026-10-25-plume-baselines. Its "
        "band set (1, 3 and 7) and its night-time results are the starting point for "
        "Q-2026-10-25-abi-band-choice.",
        "claims": [
            {
                "claim": "A transformer segmenter beats the U-Net baseline by 4.2 mIoU on the "
                "held-out 2021 fire season",
                "where": "Table 3, p.7", "bears on": "Q-2026-10-25-plume-baselines — supports",
                "kind": "result", "basis": "stated by paper",
            },
            {
                "claim": "Inputs are ABI bands 1, 3 and 7, and band 7 (3.9 µm) has a 2 km nadir "
                "resolution",
                "where": "§2.1 p.3", "bears on": "Q-2026-10-25-abi-band-choice — supports",
                "kind": "dataset", "basis": "stated by paper",
            },
            {
                "claim": "Night-time scenes score 9.1 mIoU lower than daytime scenes",
                "where": "Fig. 6, p.9", "bears on": "Q-2026-10-25-abi-band-choice — supports",
                "kind": "limitation", "basis": "stated by paper",
            },
        ],
        "note": "read in full. Table 3 is the number to beat; the paper releases no code or "
        "labels.",
        "bibtex": "@article{smith2024-plume-goes,\n  author  = {Smith, J. and Patel, R.},\n"
        "  title   = {Transformer-based smoke plume segmentation from {GOES-16} imagery},\n"
        "  journal = {Remote Sensing of Environment},\n  year    = {2024},\n"
        "  doi     = {10.5555/example.2024.1}\n}",
    },
    "jones2023-plume-unet": {
        "subject": "U-Net baseline for smoke segmentation in GOES-16 imagery",
        "meta": {
            "title": "A U-Net baseline for wildfire smoke segmentation in GOES-16 ABI imagery",
            "authors": ["Jones M", "Alvarez T"], "year": 2023,
            "venue": "IEEE Geoscience and Remote Sensing Letters",
            "doi": "10.5555/example.2023.1", "relevance": "supporting",
            "bears-on": ["Q-2026-10-25-plume-baselines", "Q-2026-10-25-abi-band-choice"],
            "related": ["smith2024-plume-goes"],
        },
        "summary": "The paper trains a standard U-Net to segment smoke in GOES-16 ABI CONUS "
        "scenes and offers it as a baseline. Six ABI bands are stacked as input, and HMS smoke "
        "polygons from the 2019 fire season serve as labels, split by month into training and "
        "test sets. The U-Net is trained with Dice loss and reaches 0.61 mIoU on the test "
        "months, missing most thin plumes far from their fires. Other training details are "
        "brief.",
        "why": "It is the U-Net that smith2024-plume-goes compares against, so it sets the lower "
        "bar for Q-2026-10-25-plume-baselines and is the first baseline we re-implement. Its "
        "Table 1 gives band 7 a 1 km resolution, which disagrees with smith2024-plume-goes "
        "§2.1 p.3.",
        "claims": [
            {
                "claim": "A U-Net trained on HMS smoke labels reaches 0.61 mIoU on held-out "
                "months of the 2019 season",
                "where": "Table 2, p.4", "bears on": "Q-2026-10-25-plume-baselines — supports",
                "kind": "result", "basis": "stated by paper",
            },
            {
                "claim": "ABI band 7 (3.9 µm) has a nadir resolution of 1 km",
                "where": "Table 1", "bears on": "Q-2026-10-25-abi-band-choice — supports",
                "kind": "dataset", "basis": "stated by paper",
            },
        ],
        "note": "read in full. Table 1 gives band 7 at 1 km where smith2024-plume-goes §2.1 p.3 "
        "gives 2 km; it may be the resampled grid rather than the native resolution. Not taken "
        "to knowledge yet.",
        "bibtex": "@article{jones2023-plume-unet,\n  author  = {Jones, M. and Alvarez, T.},\n"
        "  title   = {A {U-Net} baseline for wildfire smoke segmentation in {GOES-16} {ABI} "
        "imagery},\n"
        "  journal = {IEEE Geoscience and Remote Sensing Letters},\n  year    = {2023},\n"
        "  doi     = {10.5555/example.2023.1}\n}",
    },
    "brown2022-cloud-masks": {
        "subject": "cloud masks for GOES-16 ABI",
        "meta": {
            "title": "Deep cloud masks for GOES-16 ABI",
            "authors": ["Brown A", "Nakamura H"], "year": 2022,
            "venue": "Journal of Atmospheric and Oceanic Technology",
            "doi": "10.5555/example.2022.1", "relevance": "not-useful",
        },
        "summary": "The paper trains a convolutional network to label GOES-16 ABI pixels as "
        "clear or cloudy, with co-located CALIPSO lidar profiles as the reference. Compared "
        "with the operational ABI clear-sky mask it agrees better with the lidar, most of all "
        "over land at night. Smoke has no class of its own: thick smoke is counted as cloud and "
        "thin smoke as clear, and neither case is evaluated.",
        "why": "Not useful here. It was read for Q-2026-10-25-plume-baselines in the hope of "
        "smoke labels or a smoke-aware cloud mask, and it has neither: smoke is folded into the "
        "cloud and clear classes and never evaluated. Do not re-read it for smoke; it matters "
        "only if we later need a plain cloud mask.",
        "claims": [],
        "note": "read in full. The label definitions (§2.2) have no smoke class; recorded as "
        "not-useful so nobody reads it again for smoke.",
        "bibtex": "@article{brown2022-cloud-masks,\n  author  = {Brown, A. and Nakamura, H.},\n"
        "  title   = {Deep cloud masks for {GOES-16} {ABI}},\n"
        "  journal = {Journal of Atmospheric and Oceanic Technology},\n  year    = {2022},\n"
        "  doi     = {10.5555/example.2022.1}\n}",
    },
}

# A second reader's full re-read: claim numbers (0-based) verified or disputed with a reason.
REREADS: dict[str, dict[str, Any]] = {
    "smith2024-plume-goes": {
        "verified": [0, 1],
        "disputed": {2: "9.1 mIoU is the twilight bin in Fig. 6, the night-time drop given in "
                     "§5.2 is 5.4 mIoU"},
        "summary": "The HMS polygons are drawn by analysts and tend to over-cover thin smoke, "
        "so the labels are least reliable at plume edges, which is where the reported gains "
        "are largest.",
        "revised": "added the label-noise caveat from §3.2",
        "note": "re-read in full. Verified the Table 3 and §2.1 claims; disputed the night-time "
        "number, which takes the twilight bin of Fig. 6 for the night.",
    },
}

TOPIC = {"name": "goes-abi", "scope": "GOES-16 ABI instrument facts"}
FACTS: dict[str, dict[str, str]] = {
    "band7-2km": {
        "text": "GOES-16 ABI band 7 is 3.9 µm with 2 km nadir resolution",
        "src": "smith2024-plume-goes §2.1 p.3",
        "fragment": "band 7 is 3.9 µm with 2 km nadir resolution",
    },
    "band7-1km": {
        "text": "GOES-16 ABI band 7 nadir resolution is 1 km",
        "src": "jones2023-plume-unet Table 1",
        "conflicts with": "band7-2km",
        "fragment": "band 7 nadir resolution is 1 km",
    },
}

# Section texts: a str is written as is, a list as one '- ' bullet per item.
DECISIONS: dict[str, dict[str, Any]] = {
    "D-2026-10-25-loss-function": {
        "title": "Train the segmentation models with Dice loss",
        "links": ["Q-2026-10-25-plume-baselines", "literature/jones2023-plume-unet.md"],
        "Decision": "Train every segmentation model in the project, baselines included, with "
        "soft Dice loss on the smoke class.",
        "Alternatives considered": [
            ("Pixel-wise binary cross-entropy: smoke covers only a few per cent of the pixels, "
             "so the background dominates the loss."),
            ("Focal loss: handles the imbalance too, but adds a hyperparameter to tune for "
             "every model."),
        ],
        "Rationale and evidence": "Smoke is a small fraction of each CONUS scene and Dice is "
        "insensitive to that imbalance. jones2023-plume-unet trains its U-Net with Dice, so "
        "re-implementing it under the same loss keeps our baseline faithful to the paper.",
        "Consequences": "Baselines and our model share one loss, so differences in results "
        "come from the architecture. Dice gives little gradient on tiles without smoke; watch "
        "the false-positive rate there.",
    },
    "D-2026-10-26-eval-metric": {
        "title": "Use mIoU as the primary segmentation metric",
        "links": ["Q-2026-10-25-plume-baselines", "literature/smith2024-plume-goes.md",
                  "literature/jones2023-plume-unet.md"],
        "Decision": "Report mean intersection-over-union (mIoU) over the smoke and background "
        "classes on a held-out fire season as the primary metric, with per-class IoU and smoke "
        "F1 alongside.",
        "Alternatives considered": [
            "Pixel accuracy: inflated by the background, which is most of every scene.",
            ("Smoke F1 alone: informative, but neither baseline reports it, so we could not "
             "compare."),
        ],
        "Rationale and evidence": "Both baselines report mIoU (smith2024-plume-goes Table 3, "
        "jones2023-plume-unet Table 2), so our numbers can stand directly beside theirs.",
        "Consequences": "Test sets are whole held-out seasons, as in smith2024-plume-goes. "
        "Other metrics are secondary and do not decide between models on their own.",
    },
    "D-2026-10-28-loss-function-v2": {
        "title": "Train the segmentation models with Dice plus binary cross-entropy",
        "supersedes": "D-2026-10-25-loss-function",
        "links": ["Q-2026-10-25-plume-baselines", "log/2026-10-27-lee-codex-0910.md",
                  "literature/smith2024-plume-goes.md"],
        "Decision": "Train every segmentation model with the sum of soft Dice loss and "
        "pixel-wise binary cross-entropy, weighted equally. This replaces "
        "D-2026-10-25-loss-function.",
        "Alternatives considered": [
            ("Keep Dice and drop the tiles without smoke: removes exactly the cases where the "
             "false positives appear."),
            ("Focal loss: no evidence that it beats Dice plus cross-entropy here, and it adds a "
             "hyperparameter."),
        ],
        "Rationale and evidence": "Lee's two-epoch smoke test with Dice alone "
        "(log/2026-10-27-lee-codex-0910.md, Tried and failed) labelled cloud edges as smoke "
        "on tiles without smoke, where Dice gives almost no gradient. Cross-entropy penalises "
        "every false-positive pixel. smith2024-plume-goes (§3.3) trains its transformer with "
        "the same combination.",
        "Consequences": "The U-Net baseline is retrained under the new loss before any "
        "comparison. Results trained with Dice alone are not comparable and are not reported.",
    },
}
