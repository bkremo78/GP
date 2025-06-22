import csv
import re
from config import PROBLEM_KEYWORDS, CLEAR_RUN_KEYWORDS

def extrage_cuvinte_remark(text):
    if not text:
        return set()
    # Extrage cuvinte și abrevieri, ignoră cifre și semne de punctuație
    return set(re.findall(r"[a-zA-Z]+", text.lower()))

def verifica_remark_unknowns(csv_file, encoding="utf-8"):
    unique_terms = set()
    with open(csv_file, encoding=encoding, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            remark = row.get("REMARK", "")
            unique_terms.update(extrage_cuvinte_remark(remark))

    # Normalizează la litere mici
    problem_words = set([w.lower() for w in PROBLEM_KEYWORDS])
    clear_words = set([w.lower() for w in CLEAR_RUN_KEYWORDS])

    unknown_terms = unique_terms - problem_words - clear_words

    print("Termeni/abrevieri din REMARK neacoperiți de cheile definite:")
    for term in sorted(unknown_terms):
        print(term)

if __name__ == "__main__":
    # Înlocuiește cu calea ta reală către fișierul CSV istoric!
    verifica_remark_unknowns("Towcester.csv")