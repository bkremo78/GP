import csv

GRADE_VALIDE = {
    'A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9', 'A10', 'OPEN',
    'D3', 'D4', 'S4', 'T1', 'T2', 'T3'
}

def gaseste_cheie_nume(fieldnames):
    for cheie in fieldnames:
        if cheie and cheie.strip().replace('\ufeff', '').upper() in ['NUME', 'NAME']:
            return cheie
    return None

def verifica_date_istoric(
    cale_csv,
    coloana_grad='GRAD',
    afiseaza_linii_max=20
):
    with open(cale_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        cheie_nume = gaseste_cheie_nume(reader.fieldnames)
        if not cheie_nume:
            print("!!! Nu s-a detectat nicio coloană pentru numele ogarului (NUME sau NAME) în CSV! Header găsit:", reader.fieldnames)
        fara_nume = []
        grad_necunoscut = []
        for i, row in enumerate(reader, start=2):  # start=2 pentru a ține cont de header ca linia 1
            nume = row.get(cheie_nume, '').strip() if cheie_nume else ''
            grad = row.get(coloana_grad, '').strip()
            if not nume:
                fara_nume.append(i)
            if not grad or grad.upper() not in GRADE_VALIDE:
                grad_necunoscut.append((i, grad))
    print("=" * 60)
    print(f"Rânduri fără nume ogar: {len(fara_nume)}")
    if fara_nume:
        print("Primele linii fără nume:", fara_nume[:afiseaza_linii_max])
    print("=" * 60)
    print(f"Rânduri cu grad necunoscut/lipsă: {len(grad_necunoscut)}")
    if grad_necunoscut:
        print("Primele cazuri (linie, grad):")
        for linie, grad in grad_necunoscut[:afiseaza_linii_max]:
            print(f"  Linie {linie}: grad='{grad}'")
    print("=" * 60)
    if len(fara_nume) > afiseaza_linii_max:
        print(f"... {len(fara_nume) - afiseaza_linii_max} alte linii fără nume nescrise aici ...")
    if len(grad_necunoscut) > afiseaza_linii_max:
        print(f"... {len(grad_necunoscut) - afiseaza_linii_max} alte cazuri cu grad necunoscut nescrise aici ...")

if __name__ == "__main__":
    cale_csv = "Monmore.csv"  # modifică aici cu calea corectă!
    verifica_date_istoric(cale_csv)