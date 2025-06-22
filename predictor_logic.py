# --- Modul principal de logică pentru predicția curselor de ogari ---
# Include procesare istoric, calcul indicatori, predicție, simulare, testare ponderi, REMARK, ajustare ponderi REMARK și indicatori CURBA

import csv
import re
import os
import json
from datetime import datetime, timedelta
from statistics import mean
import logging

# --- Funcție pentru normalizare nume ogar (spații, diacritice, majuscule/minuscule) ---
import unicodedata
def normalize_name(name):
    if not name or not isinstance(name, str):
        return ''
    name = name.strip().lower()
    name = unicodedata.normalize('NFD', name)
    name = ''.join(ch for ch in name if unicodedata.category(ch) != 'Mn')
    return name

# Inițializează logging simplu (în fișier și în consolă)
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("greyhound_predictor.log", mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Importă toate constantele și setările de configurare
from config import (
    TIMP_MAX_NECUNOSCUT,
    TRACK_NAME_MAP_GUI_TO_CSV,
    DISTANTE_PUNCTE_SIMULARE,
    DEFAULT_CSV_FILE,
    DEFAULT_CURSA_NOUA_GUI,
    YOUNG_AGE_THRESHOLD,
    OLD_AGE_THRESHOLD,
    YOUNG_AGE_ADJUSTMENT,
    OLD_AGE_ADJUSTMENT,
    SEX_ADJUSTMENTS,
    BOX_POSITION_ADJUSTMENT_FACTOR,
    GRADE_ADJUSTMENTS,
    RECENCY_THRESHOLD_RECENT_DAYS,
    RECENCY_THRESHOLD_MODERATE_DAYS,
    RECENCY_THRESHOLD_OLD_DAYS,
    RECENCY_ADJUSTMENTS,
    PROBLEM_KEYWORDS,
    CLEAR_RUN_KEYWORDS,
    COEFICIENT_PENALIZARE_PROBLEME_REMARK,
    COEFICIENT_BONUS_LIBER_REMARK,
    # ---- ADĂUGAT pentru opțiunea curbe parametrizabilă ----
    COEFICIENT_BONUS_CURBA_FINISHER,
    COEFICIENT_PENALIZARE_CURBA_EARLY,
)

# --- Funcție pentru extragere indicatori din coloana CURBA ---
def extrage_indicatori_curba(curba_string):
    """
    Primește string de tip '1222', '5432', '' etc.
    Returnează:
      - lista pozițiilor (int)
      - media pozițiilor (float)
      - poziția la ultima curbă (int)
      - diferența între prima și ultima curbă (int: negativ = ogarul a câștigat poziții)
    """
    pozitii = [int(c) for c in str(curba_string).strip() if c.isdigit()]
    if not pozitii:
        return [], None, None, None
    media = mean(pozitii)
    poz_ultima = pozitii[-1]
    diferenta = pozitii[-1] - pozitii[0]
    return pozitii, media, poz_ultima, diferenta

def determina_stil_curba(diff):
    if diff is None:
        return "N/A"
    if diff < -1:
        return "Finisher"
    elif diff > 1:
        return "EarlyPace"
    else:
        return "Constant"

# --- Funcție pentru procesarea unui rând din fișierul CSV cu istoric ---
def proceseaza_rand_istoric(rand, nume_coloane, mapare_intern_csv):
    """
    Procesează un rând din CSV, aplicând maparea și conversiile de tip,
    returnează dict cu toate valorile normalizate.
    """
    rand_procesat = {}
    for nume_intern, nume_csv in mapare_intern_csv.items():
        if nume_csv in nume_coloane:
            valoare = rand.get(nume_csv)
            rand_procesat[nume_intern] = valoare.strip() if isinstance(valoare, str) else valoare
        else:
            rand_procesat[nume_intern] = None

        # Adăugăm și numele normalizat pentru potriviri robuste
        nume_ogar = rand_procesat.get('Nume Ogar')
        if nume_ogar:
            rand_procesat['Nume Ogar Normalizat'] = normalize_name(nume_ogar)
        else:
            rand_procesat['Nume Ogar Normalizat'] = ''

    # Conversie distanță la întreg
    valoare_distanta = rand_procesat.get('Distanta Cursei (m)')
    try:
        if valoare_distanta is not None and str(valoare_distanta).strip() != '':
            potrivire_distanta = re.match(r'^\d+', str(valoare_distanta).strip())
            if potrivire_distanta:
                rand_procesat['Distanta Cursei (m)'] = int(potrivire_distanta.group(0))
            else:
                rand_procesat['Distanta Cursei (m)'] = None
        else:
            rand_procesat['Distanta Cursei (m)'] = None
    except (ValueError, TypeError):
        rand_procesat['Distanta Cursei (m)'] = None

    # Conversie timp final la float
    try:
        timp_final_str = rand_procesat.get('FINAL')
        if isinstance(timp_final_str, str):
            timp_final_str = timp_final_str.replace(',', '.')
        rand_procesat['Timp Final (s)'] = float(timp_final_str) if timp_final_str is not None and str(timp_final_str).strip() != '' else None
    except (ValueError, TypeError):
        rand_procesat['Timp Final (s)'] = None

    # Conversie poziție finală la întreg
    pozitie_str = rand_procesat.get('Pozitie Finala')
    if isinstance(pozitie_str, str):
        pozitie_curata = re.sub(r'\D', '', pozitie_str).strip()
        try:
            rand_procesat['Pozitie Finala'] = int(pozitie_curata) if pozitie_curata != '' else None
        except (ValueError, TypeError):
            rand_procesat['Pozitie Finala'] = None
    else:
        rand_procesat['Pozitie Finala'] = None

    # Conversie timp secțional la float
    try:
        sectional_str = rand_procesat.get('Timp Secțional 1 (s)')
        if isinstance(sectional_str, str):
            potrivire = re.match(r'^\d*\.?\d*', sectional_str)
            if potrivire and potrivire.group(0).strip() != '':
                rand_procesat['Timp Secțional 1 (s)'] = float(potrivire.group(0).replace(',', '.'))
            else:
                rand_procesat['Timp Secțional 1 (s)'] = None
        else:
            rand_procesat['Timp Secțional 1 (s)'] = None
    except (ValueError, TypeError):
        rand_procesat['Timp Secțional 1 (s)'] = None

    # Extrage corect boxa din orice format (ex: '[3]', 'box 3', '3')
    valoare_box = rand_procesat.get('Numar Box (Trap)')
    try:
        if valoare_box is not None:
            box_str = str(valoare_box).strip()
            potrivire = re.search(r'(\d+)', box_str)
            if potrivire:
                rand_procesat['Numar Box (Trap)'] = int(potrivire.group(1))
            else:
                rand_procesat['Numar Box (Trap)'] = None
        else:
            rand_procesat['Numar Box (Trap)'] = None
    except (ValueError, TypeError):
        rand_procesat['Numar Box (Trap)'] = None

    # Conversie vârstă la float (sau string dacă nu e posibil)
    valoare_varsta = rand_procesat.get('Varsta')
    rand_procesat['Varsta'] = None
    if valoare_varsta is not None:
        try:
            rand_procesat['Varsta'] = float(valoare_varsta)
        except (ValueError, TypeError):
            if isinstance(valoare_varsta, str) and valoare_varsta.strip() != '':
                rand_procesat['Varsta'] = valoare_varsta.strip()
            pass

    # Normalizează gradul cursei
    valoare_grad = rand_procesat.get('Grad Cursa')
    if isinstance(valoare_grad, str):
        rand_procesat['Grad Cursa'] = valoare_grad.strip()

    # Parsează data
    valoare_data = rand_procesat.get('Data Cursei')
    rand_procesat['Data Cursei Parsata'] = None
    if isinstance(valoare_data, str) and valoare_data.strip() != '':
        try:
            rand_procesat['Data Cursei Parsata'] = datetime.strptime(valoare_data.strip(), '%d/%m/%Y')
        except ValueError:
            pass
        except Exception:
            pass

    # Citire REMARK dacă există în rând
    if 'REMARK' in rand:
        rand_procesat['REMARK'] = rand.get('REMARK', '').strip()
    else:
        rand_procesat['REMARK'] = ''

    # Adaugă și coloana CURBA dacă există
    if 'CURBA' in rand:
        rand_procesat['CURBA'] = rand.get('CURBA', '').strip()
    else:
        rand_procesat['CURBA'] = ''

    # Returnează doar dacă există nume ogar valid
    if rand_procesat.get('Nume Ogar') and str(rand_procesat.get('Nume Ogar')).strip() != '':
        return rand_procesat
    else:
        return None

# --- Funcție pentru citirea și parsarea completă a fișierului CSV ---
def citeste_si_parseaza_istoric(cale_fisier, lista_erori):
    """
    Citește fișierul CSV și parsează datele istorice, rând cu rând.
    """
    istoric_complet = []
    try:
        with open(cale_fisier, mode='r', encoding='utf-8', newline="") as fisier_csv:
            try:
                mostra = fisier_csv.readline()
                if not mostra or mostra.strip() == '':
                    lista_erori.append(f"Avertisment: Fisierul '{os.path.basename(cale_fisier)}' pare gol sau are doar un rând antet fara date.")
                    return []
                fisier_csv.seek(0)

                try:
                    dialect = csv.Sniffer().sniff(mostra, delimiters=',;')
                except csv.Error:
                    dialect = 'excel'
                fisier_csv.seek(0)
                reader = csv.DictReader(fisier_csv, dialect=dialect)

            except Exception as eroare_dictreader:
                lista_erori.append(f"Eroare FATALA la initializarea cititorului CSV: {eroare_dictreader}. Verificati formatul si antetul fisierului '{os.path.basename(cale_fisier)}'.")
                return []

            if reader.fieldnames:
                reader.fieldnames = [(nume.strip() if nume else '') for nume in reader.fieldnames]
            else:
                lista_erori.append(f"Eroare FATALA: Fisierul CSV '{os.path.basename(cale_fisier)}' nu are antet (header).")
                return []

            mapare_intern_csv = {
                'Data Cursei': 'DATA',
                'Pista': 'PISTA',
                'Distanta Cursei (m)': 'DISTANTA',
                'Grad Cursa': 'GRAD',
                'Numar Box (Trap)': 'BOXA',
                'Timp Secțional 1 (s)': 'SECTIONAL',
                'Pozitie Finala': 'POZITIE',
                'FINAL': 'FINAL',
                'Varsta': 'VARSTA',
                'Sex': 'SEX'
            }

            nume_ogar_csv = None
            campuri_posibile_nume = ['NUME', '\ufeffNUME', 'NAME', '\ufeffNAME']
            for camp in (reader.fieldnames if reader.fieldnames else []):
                if camp and camp.strip().upper() in [f.strip().upper() for f in campuri_posibile_nume]:
                    nume_ogar_csv = camp
                    break

            if nume_ogar_csv:
                mapare_intern_csv['Nume Ogar'] = nume_ogar_csv
            else:
                lista_erori.append(f"Eroare FATALA: Coloana cu numele ogarului ('NUME' sau 'NAME') nu a fost gasita in antetul fisierului CSV '{os.path.basename(cale_fisier)}'. Verificati numele EXACT al coloanei NUME/NAME.")
                return []

            # Detectează și coloana REMARK dacă există
            if 'REMARK' in reader.fieldnames:
                mapare_intern_csv['REMARK'] = 'REMARK'
            if 'CURBA' in reader.fieldnames:
                mapare_intern_csv['CURBA'] = 'CURBA'

            nume_coloane_curatate = reader.fieldnames

            for rand in reader:
                rand_procesat = proceseaza_rand_istoric(rand, nume_coloane_curatate, mapare_intern_csv)
                if rand_procesat:
                    istoric_complet.append(rand_procesat)

        if not istoric_complet and not [eroare for eroare in lista_erori if "FATALA" not in eroare]:
            lista_erori.append(f"Avertisment: Fisierul '{os.path.basename(cale_fisier)}' are antet, dar nu contine randuri de date parsabile.")

    except FileNotFoundError:
        lista_erori.append(f"Eroare FATALA: Fisierul '{os.path.basename(cale_fisier)}' nu a fost gasit la calea specificata.")
        return []
    except Exception as eroare:
        lista_erori.append(f"A aparut o eroare neasteptata la citirea si parsarea fisierului CSV: {eroare}")
        return []

    return istoric_complet

# --- Funcție principală pentru calculul indicatorilor unui ogar ---
def calculeaza_indicatori_ogar(istoric_ogar, pista_cursa, distanta_cursa, box_curent, data_cursa_curenta):
    """
    Calculează indicatori statistici relevanți pentru un ogar pe baza istoricului său.
    Include și procentele pentru probleme și alergare liberă REMARK și indicatorii de curbe.
    """
    cel_mai_bun_timp = TIMP_MAX_NECUNOSCUT
    timp_mediu = TIMP_MAX_NECUNOSCUT
    timp_mediu_box = TIMP_MAX_NECUNOSCUT
    cel_mai_bun_sectional = TIMP_MAX_NECUNOSCUT
    timp_mediu_sectional = TIMP_MAX_NECUNOSCUT
    medie_box_start = None
    timpi_medii_per_box = {}

    varsta = None
    sex = None
    grad_istoric = None

    ultima_data_relevanta = None
    zile_de_la_ultima_cursa = None
    status_recent = 'No History'

    gasit_istoric_general = False
    gasit_istoric_box = False
    gasit_istoric_sectional = False
    gasit_istoric_sectional_avg = False
    gasit_istoric_box_start = False
    gasit_istoric_varsta = False
    gasit_istoric_sex = False
    gasit_istoric_timpi_per_box = False
    gasit_istoric_grad = False
    gasit_istoric_recenta = False

    # Statistici pentru probleme și alergare liberă
    total_curse_remark = 0
    curse_cu_probleme = 0
    curse_alergare_libera = 0

    # Statistici pentru curbe
    medii_curba = []
    pozitii_ultima_curba = []
    diferente_prima_ultima = []

    if not istoric_ogar:
        return {
            'Cel_Mai_Bun_Timp': cel_mai_bun_timp,
            'Timp_Mediu': timp_mediu,
            'Timp_Mediu_Box_Specific': timp_mediu_box,
            'Cel_Mai_Bun_Sectional': cel_mai_bun_sectional,
            'Timp_Mediu_Sectional': timp_mediu_sectional,
            'Medie_Box_Start': medie_box_start,
            'Varsta': varsta,
            'Sex': sex,
            'Grad Istoric': grad_istoric,
            'Recency Status': status_recent,
            'Days Since Last Race': zile_de_la_ultima_cursa,
            'Are Istoric Relevant General': gasit_istoric_general,
            'Are Istoric Relevant Box': gasit_istoric_box,
            'Are Istoric Relevant Sectional': gasit_istoric_sectional,
            'Are Istoric Relevant Sectional Avg': gasit_istoric_sectional_avg,
            'Are Istoric Relevant Box Start': gasit_istoric_box_start,
            'Are Istoric Varsta': gasit_istoric_varsta,
            'Are Istoric Sex': gasit_istoric_sex,
            'Are Istoric Grad': gasit_istoric_grad,
            'Are Istoric Recenta': gasit_istoric_recenta,
            'Timpi_Medii_Per_Box': timpi_medii_per_box,
            'Are Istoric Timpi Per Box': gasit_istoric_timpi_per_box,
            'Box Nou': box_curent,
            'Prob_Probleme': None,
            'Prob_Liber': None,
            'Media_Curba': None,
            'Pozitie_Ultima_Curba': None,
            'Diferenta_Prima_Ultima_Curba': None,
            'Stil_Curba': None
        }

    istoric_relevant = [
        r for r in istoric_ogar
        if r.get('Pista') == pista_cursa and
           r.get('Distanta Cursei (m)') == distanta_cursa
    ]

    # Calcul probabilitate probleme și alergare liberă din REMARK & colectare curbe
    for r in istoric_relevant:
        # REMARK
        remark = r.get('REMARK', '')
        if remark is not None:
            remark_l = remark.lower()
            total_curse_remark += 1
            if any(cuvant.lower() in remark_l for cuvant in PROBLEM_KEYWORDS):
                curse_cu_probleme += 1
            if any(cuvant.lower() in remark_l for cuvant in CLEAR_RUN_KEYWORDS):
                curse_alergare_libera += 1
        # CURBA
        pozitii, media, poz_ultima, diff = extrage_indicatori_curba(r.get('CURBA', r.get('Curba', '')))
        if media is not None:
            medii_curba.append(media)
        if poz_ultima is not None:
            pozitii_ultima_curba.append(poz_ultima)
        if diff is not None:
            diferente_prima_ultima.append(diff)

    probabilitate_probleme = (curse_cu_probleme / total_curse_remark) if total_curse_remark > 0 else None
    probabilitate_liber = (curse_alergare_libera / total_curse_remark) if total_curse_remark > 0 else None

    if medii_curba:
        media_curba_ogar = mean(medii_curba)
    else:
        media_curba_ogar = None

    if pozitii_ultima_curba:
        poz_ultima_curba_ogar = mean(pozitii_ultima_curba)
    else:
        poz_ultima_curba_ogar = None

    if diferente_prima_ultima:
        diferenta_prima_ultima_curba_ogar = mean(diferente_prima_ultima)
    else:
        diferenta_prima_ultima_curba_ogar = None

    stil_curba_ogar = determina_stil_curba(diferenta_prima_ultima_curba_ogar)

    if istoric_relevant:
        ultimul_rand = None
        ultima_data = None

        for r in istoric_relevant:
            if varsta is None and r.get('Varsta') is not None:
                varsta = r.get('Varsta')
                if varsta is not None:
                    gasit_istoric_varsta = True

            if sex is None and r.get('Sex') is not None and str(r.get('Sex')).strip() != '':
                sex = str(r.get('Sex')).strip()
                gasit_istoric_sex = True

            data_rand = r.get('Data Cursei Parsata')
            if data_rand is not None and isinstance(data_rand, datetime):
                gasit_istoric_recenta = True
                if ultima_data is None or data_rand > ultima_data:
                    ultima_data = data_rand
                    ultimul_rand = r

        if ultimul_rand and ultimul_rand.get('Grad Cursa') is not None and str(ultimul_rand.get('Grad Cursa')).strip() != '':
            grad_istoric = str(ultimul_rand.get('Grad Cursa')).strip()
            gasit_istoric_grad = True

        if data_cursa_curenta is not None and gasit_istoric_recenta and ultima_data is not None:
            ultima_data_relevanta = ultima_data
            if ultima_data_relevanta <= data_cursa_curenta:
                diferenta = data_cursa_curenta - ultima_data_relevanta
                zile_de_la_ultima_cursa = diferenta.days
                if zile_de_la_ultima_cursa is not None:
                    if zile_de_la_ultima_cursa <= RECENCY_THRESHOLD_RECENT_DAYS:
                        status_recent = 'Very Recent'
                    elif zile_de_la_ultima_cursa <= RECENCY_THRESHOLD_MODERATE_DAYS:
                        status_recent = 'Recent'
                    elif zile_de_la_ultima_cursa <= RECENCY_THRESHOLD_OLD_DAYS:
                        status_recent = 'Moderate'
                    else:
                        status_recent = 'Old'
                else:
                    status_recent = 'N/A Date'
            else:
                status_recent = 'N/A Date'
                zile_de_la_ultima_cursa = None
        else:
            status_recent = 'N/A Date'

        if not istoric_relevant:
            status_recent = 'No History'
            gasit_istoric_recenta = False
        elif data_cursa_curenta is None or not gasit_istoric_recenta or ultima_data is None:
            status_recent = 'N/A Date'

        timpi_finali_validi = [r['Timp Final (s)'] for r in istoric_relevant
                               if r.get('Timp Final (s)') is not None and r.get('Timp Final (s)') > 0.0]

        if timpi_finali_validi:
            gasit_istoric_general = True
            cel_mai_bun_timp = min(timpi_finali_validi)
            timp_mediu = sum(timpi_finali_validi) / len(timpi_finali_validi)

        timpi_per_box_raw = {}
        for r in istoric_relevant:
            box = r.get('Numar Box (Trap)')
            timp = r.get('Timp Final (s)')
            if box is not None and isinstance(box, int) and 1 <= box <= 6 and timp is not None and timp > 0.0:
                if box not in timpi_per_box_raw:
                    timpi_per_box_raw[box] = []
                timpi_per_box_raw[box].append(timp)

        if timpi_per_box_raw:
            gasit_istoric_timpi_per_box = True
            timpi_medii_per_box = {box: sum(timpi) / len(timpi) for box, timpi in timpi_per_box_raw.items()}
            if box_curent is not None and box_curent in timpi_medii_per_box:
                gasit_istoric_box = True
                timp_mediu_box = timpi_medii_per_box[box_curent]

        istoric_cu_sectional_valid = [
            r for r in istoric_relevant
            if r.get('Timp Secțional 1 (s)') is not None and r.get('Timp Secțional 1 (s)') > 0.0
        ]

        if istoric_cu_sectional_valid:
            gasit_istoric_sectional = True
            gasit_istoric_sectional_avg = True
            timpi_sectionali_validi = [r['Timp Secțional 1 (s)'] for r in istoric_cu_sectional_valid]
            if timpi_sectionali_validi:
                cel_mai_bun_sectional = min(timpi_sectionali_validi)
                timp_mediu_sectional = sum(timpi_sectionali_validi) / len(timpi_sectionali_validi)

        boxe_start_valide = [r['Numar Box (Trap)'] for r in istoric_relevant
                             if r.get('Numar Box (Trap)') is not None and isinstance(r.get('Numar Box (Trap)'), int) and 1 <= r.get('Numar Box (Trap)') <= 6]

        if boxe_start_valide:
            gasit_istoric_box_start = True
            medie_box_start = sum(boxe_start_valide) / len(boxe_start_valide)

    return {
        'Cel_Mai_Bun_Timp': cel_mai_bun_timp,
        'Timp_Mediu': timp_mediu,
        'Timp_Mediu_Box_Specific': timp_mediu_box,
        'Cel_Mai_Bun_Sectional': cel_mai_bun_sectional,
        'Timp_Mediu_Sectional': timp_mediu_sectional,
        'Medie_Box_Start': medie_box_start,
        'Varsta': varsta,
        'Sex': sex,
        'Grad Istoric': grad_istoric,
        'Recency Status': status_recent,
        'Days Since Last Race': zile_de_la_ultima_cursa,
        'Are Istoric Relevant General': gasit_istoric_general,
        'Are Istoric Relevant Box': gasit_istoric_box,
        'Are Istoric Relevant Sectional': gasit_istoric_sectional,
        'Are Istoric Relevant Sectional Avg': gasit_istoric_sectional_avg,
        'Are Istoric Relevant Box Start': gasit_istoric_box_start,
        'Are Istoric Varsta': gasit_istoric_varsta,
        'Are Istoric Sex': gasit_istoric_sex,
        'Are Istoric Grad': gasit_istoric_grad,
        'Are Istoric Recenta': gasit_istoric_recenta,
        'Timpi_Medii_Per_Box': timpi_medii_per_box,
        'Are Istoric Timpi Per Box': gasit_istoric_timpi_per_box,
        'Box Nou': box_curent,
        'Prob_Probleme': probabilitate_probleme,
        'Prob_Liber': probabilitate_liber,
        'Media_Curba': media_curba_ogar,
        'Pozitie_Ultima_Curba': poz_ultima_curba_ogar,
        'Diferenta_Prima_Ultima_Curba': diferenta_prima_ultima_curba_ogar,
        'Stil_Curba': stil_curba_ogar
    }

# ------------------- FUNCȚII PREDICȚIE, SIMULARE, TESTARE PONDERI -------------------

def calculeaza_timp_prezis_combinat(indicatori_ogar, greutati_timp_final_aplicate):
    """
    Calculează timpul prezis combinat pentru un ogar, incluzând ajustările pentru box, vârstă, sex, poziție, grad, recență, REMARK și CURBA.
    Adaugă validări și logging pentru valori neobișnuite, inclusiv numele ogarului și detalierea ajustărilor.
    """
    timp_prezis_combinat_baza = TIMP_MAX_NECUNOSCUT

    weight_best = greutati_timp_final_aplicate.get('best', 0)
    weight_avg = greutati_timp_final_aplicate.get('average', 0)
    weight_trap = greutati_timp_final_aplicate.get('average_trap', 0)
    total_weight = weight_best + weight_avg + weight_trap
    if weight_best < 0 or weight_avg < 0 or weight_trap < 0:
        logging.warning("[WARN] Ponderile nu pot fi negative! best=%.2f, avg=%.2f, trap=%.2f", weight_best, weight_avg, weight_trap)
    if total_weight <= 0:
        logging.warning("[WARN] Suma ponderilor <= 0 – rezultatele pot fi aberante! best=%.2f, avg=%.2f, trap=%.2f", weight_best, weight_avg, weight_trap)

    indicatori_pentru_baza_ponderata_doar_general = []
    if indicatori_ogar.get('Cel_Mai_Bun_Timp', TIMP_MAX_NECUNOSCUT) < TIMP_MAX_NECUNOSCUT:
        indicatori_pentru_baza_ponderata_doar_general.append(('best', indicatori_ogar['Cel_Mai_Bun_Timp']))
    if indicatori_ogar.get('Timp_Mediu', TIMP_MAX_NECUNOSCUT) < TIMP_MAX_NECUNOSCUT:
        indicatori_pentru_baza_ponderata_doar_general.append(('average', indicatori_ogar['Timp_Mediu']))

    applicable_weights_sum_baza_generala = 0
    for tip_indicator, valoare_indicator in indicatori_pentru_baza_ponderata_doar_general:
        if tip_indicator in greutati_timp_final_aplicate and greutati_timp_final_aplicate[tip_indicator] > 0:
            applicable_weights_sum_baza_generala += greutati_timp_final_aplicate[tip_indicator]

    suma_ponderata_baza_generala = 0
    if applicable_weights_sum_baza_generala > 0:
        for tip_indicator, valoare_indicator in indicatori_pentru_baza_ponderata_doar_general:
            if tip_indicator in greutati_timp_final_aplicate:
                normalized_weight = greutati_timp_final_aplicate[tip_indicator] / applicable_weights_sum_baza_generala
                suma_ponderata_baza_generala += valoare_indicator * normalized_weight
        timp_prezis_combinat_baza = suma_ponderata_baza_generala

    ajustare_box_specifica = 0.0
    timp_mediu_general = indicatori_ogar.get('Timp_Mediu')
    timp_mediu_box_curent = indicatori_ogar.get('Timp_Mediu_Box_Specific')
    if timp_mediu_general is not None and timp_mediu_general < TIMP_MAX_NECUNOSCUT and \
        timp_mediu_box_curent is not None and timp_mediu_box_curent < TIMP_MAX_NECUNOSCUT:
        ajustare_box_specifica = timp_mediu_box_curent - timp_mediu_general

    ajustare_varsta = 0.0
    varsta = indicatori_ogar.get('Varsta')
    if isinstance(varsta, (int, float)):
        if varsta < YOUNG_AGE_THRESHOLD:
            ajustare_varsta = YOUNG_AGE_ADJUSTMENT
        elif varsta > OLD_AGE_THRESHOLD:
            ajustare_varsta = OLD_AGE_ADJUSTMENT

    ajustare_sex = 0.0
    sex = indicatori_ogar.get('Sex')
    if sex is not None and isinstance(sex, str):
        sex_upper = sex.strip().upper()
        if sex_upper not in SEX_ADJUSTMENTS:
            logging.warning("Sex necunoscut '%s' pentru ogarul %s. Folosesc ajustarea default.", sex_upper, indicatori_ogar.get('Nume Ogar', '<FĂRĂ NUME>'))
        ajustare_sex = SEX_ADJUSTMENTS.get(sex_upper, SEX_ADJUSTMENTS.get('N/A', 0.0))
    else:
        logging.warning("Sex lipsă pentru ogarul %s. Folosesc ajustarea default.", indicatori_ogar.get('Nume Ogar', '<FĂRĂ NUME>'))

    ajustare_box_pozitie = 0.0
    medie_box_start = indicatori_ogar.get('Medie_Box_Start')
    box_curent = indicatori_ogar.get('Box Nou')
    if medie_box_start is not None and isinstance(medie_box_start, (int, float)) and box_curent is not None and isinstance(box_curent, int):
        diferenta_box = box_curent - medie_box_start
        ajustare_box_pozitie = diferenta_box * BOX_POSITION_ADJUSTMENT_FACTOR

    ajustare_grad = 0.0
    race_grade = indicatori_ogar.get('Grad Cursa Curenta')
    if race_grade is not None and isinstance(race_grade, str) and race_grade.strip() != '':
        grad_upper = race_grade.strip().upper()
        if grad_upper not in GRADE_ADJUSTMENTS:
            logging.warning("Grad necunoscut '%s' pentru ogarul %s. Folosesc ajustarea default.", grad_upper, indicatori_ogar.get('Nume Ogar', '<FĂRĂ NUME>'))
        ajustare_grad = GRADE_ADJUSTMENTS.get(grad_upper, GRADE_ADJUSTMENTS.get('', GRADE_ADJUSTMENTS.get('N/A', 0.0)))
    else:
        logging.warning("Grad lipsă pentru ogarul %s. Folosesc ajustarea default.", indicatori_ogar.get('Nume Ogar', '<FĂRĂ NUME>'))

    ajustare_recency = 0.0
    recency_status = indicatori_ogar.get('Recency Status')
    if recency_status is not None and isinstance(recency_status, str):
        if recency_status not in RECENCY_ADJUSTMENTS:
            logging.warning("Recency status necunoscut '%s' pentru ogarul %s. Folosesc ajustarea default.", recency_status, indicatori_ogar.get('Nume Ogar', '<FĂRĂ NUME>'))
        ajustare_recency = RECENCY_ADJUSTMENTS.get(recency_status, 0.0)
    else:
        logging.warning("Recency status lipsă pentru ogarul %s. Folosesc ajustarea default.", indicatori_ogar.get('Nume Ogar', '<FĂRĂ NUME>'))

    prob_probleme = indicatori_ogar.get('Prob_Probleme', 0)
    prob_liber = indicatori_ogar.get('Prob_Liber', 0)

    ajustare_remark = 0.0
    if prob_probleme is not None:
        ajustare_remark += prob_probleme * COEFICIENT_PENALIZARE_PROBLEME_REMARK
    if prob_liber is not None:
        ajustare_remark -= prob_liber * COEFICIENT_BONUS_LIBER_REMARK

    ajustare_curba = 0.0
    diff_curba = indicatori_ogar.get('Diferenta_Prima_Ultima_Curba')
    if diff_curba is not None:
        if diff_curba < -1.0:
            ajustare_curba = -COEFICIENT_BONUS_CURBA_FINISHER
        elif diff_curba > 1.0:
            ajustare_curba = COEFICIENT_PENALIZARE_CURBA_EARLY

    ajustare_totala = sum([
        ajustare_box_specifica, ajustare_varsta, ajustare_sex, ajustare_box_pozitie,
        ajustare_grad, ajustare_recency, ajustare_remark, ajustare_curba
    ])

    nume_ogar = indicatori_ogar.get('Nume Ogar', '')
    if not nume_ogar or not isinstance(nume_ogar, str) or not nume_ogar.strip():
        nume_ogar = "<FĂRĂ NUME>"

    if abs(ajustare_totala) > 1.0:
        logging.warning(
            "Ajustare totală foarte mare (%.2fs) pentru ogarul %s! Verifică datele istorice.",
            ajustare_totala, nume_ogar
        )
        logging.warning(
            "Detaliu ajustări pentru %s: box_specific=%.2f, varsta=%.2f, sex=%.2f, box_pozitie=%.2f, grad=%.2f, recency=%.2f, remark=%.2f, curba=%.2f",
            nume_ogar,
            ajustare_box_specifica, ajustare_varsta, ajustare_sex, ajustare_box_pozitie,
            ajustare_grad, ajustare_recency, ajustare_remark, ajustare_curba
        )

    timp_prezis_final = timp_prezis_combinat_baza
    if timp_prezis_combinat_baza < TIMP_MAX_NECUNOSCUT:
        timp_prezis_final += ajustare_box_specifica
        timp_prezis_final += ajustare_varsta
        timp_prezis_final += ajustare_sex
        timp_prezis_final += ajustare_box_pozitie
        timp_prezis_final += ajustare_grad
        timp_prezis_final += ajustare_recency
        timp_prezis_final += ajustare_remark
        timp_prezis_final += ajustare_curba

    return timp_prezis_final

# --- Funcția principală de Predicție ---
def prezice_cursa_combinata(fisier_path, detalii_cursa, greutati_timp_final_override=None):
    erori_predictie = []
    istoric_complet = citeste_si_parseaza_istoric(fisier_path, erori_predictie)

    if [err for err in erori_predictie if "FATALA" in err]:
        return [], istoric_complet, erori_predictie

    if not detalii_cursa.get('ogari_participanti'):
        erori_predictie.append("Eroare: Nu au fost introdusi ogari participanți pentru cursa nouă.")
        return [], istoric_complet, erori_predictie

    pista_cursa_curenta = detalii_cursa.get('pista')
    distanta_cursa_curenta = detalii_cursa.get('distanta_m')
    grad_cursa_curenta = detalii_cursa.get('grad', '').strip()
    data_cursa_str = detalii_cursa.get('data_cursa')

    current_race_date = None
    if data_cursa_str:
        try:
            current_race_date = datetime.strptime(data_cursa_str.strip(), '%d/%m/%Y')
        except ValueError:
            erori_predictie.append(f"Avertisment: Formatul datei cursei curente '{data_cursa_str}' nu este valid (așteptat DD/MM/YYYY). Ajustarea Recenței nu poate fi calculată pentru această cursă.")
        except Exception as e:
            erori_predictie.append(f"Avertisment: Eroare neasteptata la parsarea datei cursei curente '{data_cursa_str}': {e}. Ajustarea Recenței nu poate fi calculată.")
    else:
        if data_cursa_str is not None and data_cursa_str.strip() == '':
            erori_predictie.append("Avertisment: Data cursei curente nu a fost introdusă. Ajustarea Recenței nu poate fi calculată.")

    if greutati_timp_final_override is None:
        greutati_timp_final_aplicate = {
            'best': 0.33,
            'average': 0.34,
            'average_trap': 0.33
        }
    else:
        greutati_timp_final_aplicate = greutati_timp_final_override

    predictie_rezultate = []

    for ogar_participanti_noua_cursa, box_nou in detalii_cursa['ogari_participanti']:
            nume_ogar_nou_normalizat = normalize_name(ogar_participanti_noua_cursa)
            istoric_ogas_curent = [
                r for r in istoric_complet
                if r.get('Nume Ogar Normalizat', '') == nume_ogar_nou_normalizat
            ]

        indicatori_ogar = calculeaza_indicatori_ogar(
            istoric_ogas_curent,
            pista_cursa_curenta,
            distanta_cursa_curenta,
            box_nou,
            current_race_date
        )

        indicatori_ogar['Grad Cursa Curenta'] = grad_cursa_curenta

        timp_prezis_combinat = calculeaza_timp_prezis_combinat(
            indicatori_ogar,
            greutati_timp_final_aplicate
        )

        indicatori_ogar['Timp_Prezis_Combinat'] = timp_prezis_combinat
        indicatori_ogar['Nume Ogar'] = ogar_participanti_noua_cursa

        predictie_rezultate.append(indicatori_ogar)

    predictie_sortata = sorted(predictie_rezultate, key=lambda x: x.get('Timp_Prezis_Combinat', TIMP_MAX_NECUNOSCUT))

    return predictie_sortata, istoric_complet, erori_predictie

# --- Funcția de Simulare ---
def simuleaza_cursa(predictie_sortata, detalii_cursa, istoric_complet):
    """
    Simulează desfășurarea cursei la punctele intermediare și la finish, pe baza timpilor prezisi și secționali.
    """
    output_simulare = ""

    distanta_totala = detalii_cursa.get('distanta_m', 0)
    pista_cursa = detalii_cursa.get('pista', 'necunoscută')

    distante_specifice_cursa = None
    if pista_cursa in DISTANTE_PUNCTE_SIMULARE and \
       isinstance(distanta_totala, int) and distanta_totala > 0 and \
       distanta_totala in DISTANTE_PUNCTE_SIMULARE[pista_cursa]:

        distante_specifice_cursa = DISTANTE_PUNCTE_SIMULARE[pista_cursa].get(distanta_totala)

    if distante_specifice_cursa is None:
        output_simulare += f"\nSimulare: Nu am distanțe definite pentru punctele intermediare pentru pista '{pista_cursa}', distanța {distanta_totala}m.\n"
        output_simulare += "Simularea la punctele intermediare nu poate rula detaliat. Afișez doar Start și Finish (bazat pe timpii prezisi).\n"
        puncte_simulare = [0, distanta_totala]
        nume_puncte_afisare = ["Start", "Finish"]
    else:
        puncte_simulare = sorted(list(set([0] + distante_specifice_cursa + [distanta_totala])))
        nume_puncte_map = {0: "Start", distanta_totala: "Finish"}
        distante_intermediare_sortate = sorted([d for d in puncte_simulare if d > 0 and d < distanta_totala])
        for i, dist in enumerate(distante_intermediare_sortate):
            if i == 0:
                nume_puncte_map[dist] = f"Primul Punct (~{dist}m)"
            elif i == len(distante_intermediare_sortate) - 1:
                nume_puncte_map[dist] = f"Ultimul Punct Interm. (~{dist}m)"
            else:
                nume_puncte_map[dist] = f"Punct Interm. (~{dist}m)"

        nume_puncte_afisare = [nume_puncte_map.get(d, f"{d}m") for d in puncte_simulare]

    output_simulare += f"\n--- Simularea Cursei la '{pista_cursa}', {distanta_totala}m ---\n"

    simulare_ogari = []
    for rez in predictie_sortata:
        ogar_nume = rez.get('Nume Ogar', 'N/A')
        ogar_box = rez.get('Box Nou', 'N/A')
        timp_final_prezis = rez.get('Timp_Prezis_Combinat', TIMP_MAX_NECUNOSCUT)
        cel_mai_bun_sectional = rez.get('Cel_Mai_Bun_Sectional', TIMP_MAX_NECUNOSCUT)

        timpi_estimati = {}
        timpi_estimati[0] = 0.0

        if timp_final_prezis >= TIMP_MAX_NECUNOSCUT:
            for dist in puncte_simulare:
                timpi_estimati[dist] = TIMP_MAX_NECUNOSCUT
        else:
            timpi_estimati[distanta_totala] = timp_final_prezis

            viteza_medie_totala = TIMP_MAX_NECUNOSCUT
            if distanta_totala > 0 and timp_final_prezis is not None and timp_final_prezis > 0:
                viteza_medie_totala = distanta_totala / timp_final_prezis

            if distante_specifice_cursa is not None and viteza_medie_totala < TIMP_MAX_NECUNOSCUT:
                timp_estimat_primul_punct = TIMP_MAX_NECUNOSCUT
                distante_simulare_sortate_non_zero = sorted([d for d in puncte_simulare if d > 0])
                distanta_primul_punct_sim = distante_simulare_sortate_non_zero[0] if distante_simulare_sortate_non_zero else None

                if distanta_primul_punct_sim is not None and distanta_primul_punct_sim > 0:
                    sectional_valid = False
                    if cel_mai_bun_sectional is not None and cel_mai_bun_sectional < TIMP_MAX_NECUNOSCUT and cel_mai_bun_sectional > 0:
                        timp_est_total_pe_viteza_medie = timp_final_prezis
                        if timp_est_total_pe_viteza_medie is not None and cel_mai_bun_sectional < timp_est_total_pe_viteza_medie:
                            timp_estimat_primul_punct = cel_mai_bun_sectional
                            sectional_valid = True
                        else:
                            pass
                    if not sectional_valid:
                        if distanta_totala > 0 and viteza_medie_totala > 0:
                            timp_estimat_primul_punct = distanta_primul_punct_sim / viteza_medie_totala
                        else:
                            timp_estimat_primul_punct = TIMP_MAX_NECUNOSCUT

                    if timp_estimat_primul_punct is not None and timp_estimat_primul_punct < TIMP_MAX_NECUNOSCUT:
                        timpi_estimati[distanta_primul_punct_sim] = timp_estimat_primul_punct

                if distanta_primul_punct_sim is not None and timp_estimat_primul_punct is not None and timp_estimat_primul_punct < TIMP_MAX_NECUNOSCUT:
                    distanta_ramasa = distanta_totala - distanta_primul_punct_sim
                    timp_ramas = timp_final_prezis - timp_estimat_primul_punct

                    viteza_dupa_primul_punct = TIMP_MAX_NECUNOSCUT
                    if distanta_ramasa > 0 and timp_ramas is not None and timp_ramas > 0:
                        viteza_dupa_primul_punct = distanta_ramasa / timp_ramas

                    if viteza_dupa_primul_punct < TIMP_MAX_NECUNOSCUT and viteza_dupa_primul_punct > 0:
                        for dist_punct_curent in puncte_simulare:
                            if dist_punct_curent > distanta_primul_punct_sim and dist_punct_curent < distanta_totala:
                                timp_estimat = timp_estimat_primul_punct + (dist_punct_curent - distanta_primul_punct_sim) / viteza_dupa_primul_punct
                                timpi_estimati[dist_punct_curent] = timp_estimat
                            elif dist_punct_curent not in timpi_estimati:
                                timpi_estimati[dist_punct_curent] = TIMP_MAX_NECUNOSCUT

                elif viteza_medie_totala < TIMP_MAX_NECUNOSCUT and viteza_medie_totala > 0:
                    for dist_punct_curent in puncte_simulare:
                        if dist_punct_curent > 0 and dist_punct_curent < distanta_totala:
                            timp_estimat = dist_punct_curent / viteza_medie_totala
                            timpi_estimati[dist_punct_curent] = timp_estimat
                        elif dist_punct_curent not in timpi_estimati:
                            timpi_estimati[dist_punct_curent] = TIMP_MAX_NECUNOSCUT

        simulare_ogari.append({
            'Nume Ogar': ogar_nume,
            'Box': ogar_box,
            'TimpiEstimati': timpi_estimati
        })

    all_sim_points = sorted(list(set(point for ogar in simulare_ogari for point in ogar['TimpiEstimati'].keys())))
    for ogar in simulare_ogari:
        for point in all_sim_points:
            if point not in ogar['TimpiEstimati']:
                ogar['TimpiEstimati'][point] = TIMP_MAX_NECUNOSCUT

    for distanta_simulare in all_sim_points:
        nume_punct_afisare = f"{distanta_simulare}m"
        if distante_specifice_cursa is not None:
            puncte_generale_mapare_nume = sorted(list(set([0] + distante_specifice_cursa + [distanta_totala])))
            nume_puncte_map = {0: "Start", distanta_totala: "Finish"}
            distante_intermediare_sortate_nume = sorted([d for d in puncte_generale_mapare_nume if d > 0 and d < distanta_totala])

            for i, dist in enumerate(distante_intermediare_sortate_nume):
                if i == 0:
                    nume_puncte_map[dist] = f"Primul Punct (~{dist}m)"
                elif i == len(distante_intermediare_sortate_nume) - 1:
                    nume_puncte_map[dist] = f"Ultimul Punct Interm. (~{dist}m)"
                else:
                    nume_puncte_map[dist] = f"Punct Interm. (~{dist}m)"

            nume_punct_afisare = nume_puncte_map.get(distanta_simulare, f"{distanta_simulare}m")

        output_simulare += f"\nLa {nume_punct_afisare} ({distanta_simulare}m):\n"
        output_simulare += "-" * 30 + "\n"

        ogari_la_punct = sorted(
            simulare_ogari,
            key=lambda x: x['TimpiEstimati'].get(distanta_simulare, TIMP_MAX_NECUNOSCUT)
        )

        for j, ogar in enumerate(ogari_la_punct):
            timp_estimat = ogar['TimpiEstimati'].get(distanta_simulare, TIMP_MAX_NECUNOSCUT)
            timp_afisat = f"{timp_estimat:.2f}s" if timp_estimat is not None and timp_estimat < TIMP_MAX_NECUNOSCUT else "N/A"
            output_simulare += f"{j+1:<5}{ogar['Box']:<5}{ogar['Nume Ogar']:<20} ({timp_afisat})\n"

    output_simulare += "\n--- Sfârșitul Simulării ---\n"

    return output_simulare

# --- Funcția pentru Testarea Sistematică a Ponderilor ---
def test_ponderi_sistematizat(csv_path, detalii_cursa_base):
    """
    Testează sistematic diverse seturi de ponderi și afișează rezultatele pentru fiecare.
    """
    seturi_ponderi_test = [
        {'best': 0.33, 'average': 0.34, 'average_trap': 0.33},
        {'best': 0.25, 'average': 0.45, 'average_trap': 0.30},
        {'best': 0.5, 'average': 0.25, 'average_trap': 0.25},
        {'best': 0.25, 'average': 0.5, 'average_trap': 0.25},
        {'best': 0.25, 'average': 0.25, 'average_trap': 0.5},
        {'best': 0.4, 'average': 0.3, 'average_trap': 0.3},
        {'best': 0.3, 'average': 0.4, 'average_trap': 0.3},
    ]

    print("\n--- Rulare Sistemata Test Ponderi si Factori (Include Grad, Recență, REMARK, Curba) ---")
    print(f"Testarea pe cursa: Pista='{detalii_cursa_base.get('pista', 'N/A')}', Distanta={detalii_cursa_base.get('distanta_m', 'N/A')}m (Grad: {detalii_cursa_base.get('grad', 'N/A')}, Data: {detalii_cursa_base.get('data_cursa', 'N/A')})")
    print(f"Ogari: {[name for name, box in detalii_cursa_base.get('ogari_participanti', [])]}")

    _, istoric_complet_initial_check, erori_citire_initiala = prezice_cursa_combinata(
        csv_path,
        detalii_cursa_base,
        greutati_timp_final_override=seturi_ponderi_test[0],
    )

    if erori_citire_initiala and any("FATALA" in err for err in erori_citire_initiala):
        print("\nErori fatale la citirea fisierului istoric. Testarea ponderilor nu poate continua.")
        for err in erori_citire_initiala:
            print(f"- {err}")
        return

    found_test_participants_with_relevant_history = False
    if istoric_complet_initial_check and detalii_cursa_base.get('ogari_participanti'):
        pista_test = detalii_cursa_base.get('pista')
        distanta_test = detalii_cursa_base.get('distanta_m')
        test_participant_names = {name for name, box in detalii_cursa_base['ogari_participanti']}

        for row in istoric_complet_initial_check:
        # Folosește potrivire normalizată!
        if (
        +   normalize_name(row.get('Nume Ogar', '')) in {normalize_name(n) for n in test_participant_names} and
        +   row.get('Pista') == pista_test and
        +   row.get('Distanta Cursei (m)') == distanta_test
        +   ):
        +       found_test_participants_with_relevant_history = True
        +   break   

    if not found_test_participants_with_relevant_history:
        print("\nNu s-au gasit date istorice RELEVANTE (Pista+Distanta) pentru niciun ogar din cursa de testare. Testarea ponderilor nu poate continua.")
        if istoric_complet_initial_check:
            print(f"Total rânduri procesate din istoric: {len(istoric_complet_initial_check)}")
            print(f"Pista/Distanta test: '{detalii_cursa_base.get('pista', 'N/A')}' / {detalii_cursa_base.get('distanta_m', 'N/A')}m")
            print("Verificați dacă numele ogarilor, pista și distanța din cursa de testare se potrivesc EXACT cu datele din fișierul istoric.")

        return

    for ponderi_curente in seturi_ponderi_test:
        print("\n========================================")
        print(f"Testare cu ponderi Timp Final: {ponderi_curente}")
        print("========================================")

        predictie_sortata, istoric_complet_rulare, erori_predictie_rulare = prezice_cursa_combinata(
            csv_path,
            detalii_cursa_base,
            greutati_timp_final_override=ponderi_curente,
        )

        if predictie_sortata:
            print(f"\nPredictie pentru cursa la '{detalii_cursa_base.get('pista', 'N/A')}', {detalii_cursa_base.get('distanta_m', 'N/A')}m (Grad: {detalii_cursa_base.get('grad', 'N/A')}, Data: {detalii_cursa_base.get('data_cursa', 'N/A')})")
            print("-" * 260)
            print(f"{'Loc':<5}{'Box':<5}{'Nume Ogar':<20}{'Sex':<6}{'Varsta':<8}{'Recenta':<10}{'Best Timp':<12}{'Avg Timp':<12}{'Avg Box Time':<12}{'Best Sect':<12}{'Avg Sect':<12}{'Avg Start Pos':<15}{'Timp Prezisa (Comb)':<20}{'%Probleme':<10}{'%Liber':<10}{'Istoric':<15}{'Zile':<8}{'Curba':<8}{'UltCurba':<8}{'Δ1-Ult':<8}{'Stil':<10}")
            print("-" * 260)
            for i, rez in enumerate(predictie_sortata):
                timp_prezis = f"{rez.get('Timp_Prezis_Combinat', TIMP_MAX_NECUNOSCUT):.2f}" if rez.get('Timp_Prezis_Combinat', TIMP_MAX_NECUNOSCUT) < TIMP_MAX_NECUNOSCUT else "N/A"
                best_timp = f"{rez.get('Cel_Mai_Bun_Timp', TIMP_MAX_NECUNOSCUT):.2f}" if rez.get('Cel_Mai_Bun_Timp', TIMP_MAX_NECUNOSCUT) < TIMP_MAX_NECUNOSCUT else "N/A"
                avg_timp = f"{rez.get('Timp_Mediu', TIMP_MAX_NECUNOSCUT):.2f}" if rez.get('Timp_Mediu', TIMP_MAX_NECUNOSCUT) < TIMP_MAX_NECUNOSCUT else "N/A"
                avg_box_time = f"{rez.get('Timp_Mediu_Box_Specific', TIMP_MAX_NECUNOSCUT):.2f}" if rez.get('Timp_Mediu_Box_Specific', TIMP_MAX_NECUNOSCUT) < TIMP_MAX_NECUNOSCUT else "N/A"
                best_sectional = f"{rez.get('Cel_Mai_Bun_Sectional', TIMP_MAX_NECUNOSCUT):.2f}" if rez.get('Cel_Mai_Bun_Sectional', TIMP_MAX_NECUNOSCUT) < TIMP_MAX_NECUNOSCUT else "N/A"
                avg_sectional = f"{rez.get('Timp_Mediu_Sectional', TIMP_MAX_NECUNOSCUT):.2f}" if rez.get('Timp_Mediu_Sectional', TIMP_MAX_NECUNOSCUT) < TIMP_MAX_NECUNOSCUT else "N/A"
                sex_afisat = str(rez.get('Sex', 'N/A')).strip()
                varsta_raw = rez.get('Varsta')
                varsta_afisata = f"{varsta_raw:.1f}" if isinstance(varsta_raw, (int, float)) else (str(varsta_raw).strip() if varsta_raw is not None else "N/A")
                avg_start_pos_raw = rez.get('Medie_Box_Start')
                avg_start_pos_afisata = f"{avg_start_pos_raw:.2f}" if isinstance(avg_start_pos_raw, (int, float)) else "N/A"
                recency_status = rez.get('Recency Status', 'N/A')
                zile_afisate = rez.get('Days Since Last Race')
                zile_str = str(zile_afisate) if zile_afisate is not None else "N/A"
                prob_probleme = rez.get('Prob_Probleme')
                prob_liber = rez.get('Prob_Liber')
                procent_probleme = f"{100*prob_probleme:.0f}%" if prob_probleme is not None else "N/A"
                procent_liber = f"{100*prob_liber:.0f}%" if prob_liber is not None else "N/A"
                istoric_flags = ""
                if rez.get('Are Istoric Relevant General'): istoric_flags += "G"
                if rez.get('Are Istoric Relevant Box'): istoric_flags += "B"
                if rez.get('Are Istoric Relevant Sectional'): istoric_flags += "S"
                if rez.get('Are Istoric Relevant Sectional Avg'): istoric_flags += "A"
                if rez.get('Are Istoric Relevant Box Start'): istoric_flags += "P"
                if rez.get('Are Istoric Varsta'): istoric_flags += "V"
                if rez.get('Are Istoric Sex'): istoric_flags += "X"
                if rez.get('Are Istoric Timpi Per Box'): istoric_flags += "T"
                if rez.get('Are Istoric Grad'): istoric_flags += "R"
                if rez.get('Are Istoric Recenta'): istoric_flags += "D"
                if not istoric_flags: istoric_flags = "Niciun"
                media_curba = rez.get('Media_Curba', None)
                poz_ult = rez.get('Pozitie_Ultima_Curba', None)
                diff_curba = rez.get('Diferenta_Prima_Ultima_Curba', None)
                stil_curba = rez.get('Stil_Curba', "N/A")
                print(f"{i+1:<5}{rez.get('Box Nou', 'N/A'):<5}{rez.get('Nume Ogar', 'N/A'):<20}{sex_afisat:<6}{varsta_afisata:<8}{recency_status:<10}{best_timp:<12}{avg_timp:<12}{avg_box_time:<12}{best_sectional:<12}{avg_sectional:<12}{avg_start_pos_afisata:<15}{timp_prezis:<20}{procent_probleme:<10}{procent_liber:<10}{istoric_flags:<15}{zile_str:<8}{(f'{media_curba:.2f}' if media_curba is not None else 'N/A'):<8}{(f'{poz_ult:.2f}' if poz_ult is not None else 'N/A'):<8}{(f'{diff_curba:.2f}' if diff_curba is not None else 'N/A'):<8}{stil_curba:<10}")
            print("-" * 260)

    print("\n--- Sfarsitul Testarii Sistemice a Ponderilor si Factorilor ---\n")
