"""Small reconstructed lists used ONLY by main.py's existing degree override.

The original four vocabularies live unchanged in liste.py (commit 23f5eb8).
These two lists were missing from the repository history. They are inferred
from their names, the existing BAC+2 / BAC+5-Master branches, and that vocabulary.
They are intentionally separate for review. Do not treat an inferred degree as
an explicit qualification: the existing matcher/override has known false positives.
"""

# 'technicien' follows the surrounding variable/branch name; the three diploma
# abbreviations already occur in niveaux_etudes. No generic IT role titles.
mots_technicien = ["technicien", "BTS", "DUT", "DTS"]

# Both terms already occur in niveaux_etudes. Deliberately omit numeric bac+N:
# partial_ratio('bac+5', 'bac+2') is 88.89, ABOVE this override's threshold 85.
# Numeric qualifications stay in the original vocabulary; adding them here
# would incorrectly force BAC+2/BAC+3 records to BAC+5-Master.
# No seniority, engineer-role, doctorate or broad higher-education synonyms.
niveaux_master = ["master", "MBA"]
