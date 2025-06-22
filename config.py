# ======================================================================
#  CONFIG.PY - Configurare completă pentru sistemul de predicție ogari
# ======================================================================

# ----------------------------------------------------------------------
#  Fișiere implicite utilizate de aplicație
# ----------------------------------------------------------------------

# Fișierul implicit pentru salvarea/încărcarea participanților la cursă
PARTICIPANTS_FILE = 'last_participants.json'

# Fișierul implicit pentru salvarea/încărcarea setărilor GUI
GUI_SETTINGS_FILE = 'gui_settings.json'

# Fișierul CSV implicit cu istoricul curselor
DEFAULT_CSV_FILE = 'Towcester.csv'  # Asigurați-vă că acest fișier există în directorul aplicației

# ----------------------------------------------------------------------
#  Mapare CSV per pistă/arenă
# ----------------------------------------------------------------------

# Dicționar: nume pistă (din GUI) -> fișier CSV asociat
CSV_PER_ARENA = {
    'Towcester': 'Towcester.csv',
    'Romford': 'Romford.csv',
    'Harlow': 'Harlow.csv',
    'Monmore': 'Monmore.csv',
    'Sheffield': 'Sheffield.csv',
    # Adăugați aici alte arene și fișierele aferente dacă e cazul
}

# ----------------------------------------------------------------------
#  Mapare a numelor pistelor din GUI la denumirile din fișierul CSV
# ----------------------------------------------------------------------

TRACK_NAME_MAP_GUI_TO_CSV = {
    'Romford': 'ROM',
    'Towcester': 'Tow',
    'Harlow': 'Har',
    'Monmore': 'Monmr',
    'Sheffield': 'Sheff',
    # Adăugați aici alte piste din GUI și abrevierile lor din CSV
}

# ----------------------------------------------------------------------
#  Setări implicite pentru cursa nouă din GUI
# ----------------------------------------------------------------------

DEFAULT_CURSA_NOUA_GUI = {
    'pista': 'Towcester',     # Numele pistei (din cheile de mai sus)
    'distanta_m': 500,        # Distanța în metri
    'grad': 'A2',             # Gradul cursei (string, ex: 'A2')
    # Data cursei nu este specificată aici, se setează din GUI sau gui_settings.json
}

# ----------------------------------------------------------------------
#  Distanțe pentru puncte intermediare pe fiecare pistă și distanță
# ----------------------------------------------------------------------

DISTANTE_PUNCTE_SIMULARE = {
    'Tow': {   # Towcester
        500: [100, 250, 350, 450],
    },
    'Har': {   # Harlow
        415: [80, 120, 280, 320],
        592: [50, 150, 300, 450, 550],
    },
    'ROM': {   # Romford
        400: [50, 150, 250, 350],
        575: [50, 150, 300, 450, 525],
    },
    'Sheff': { # Sheffield
        400: [50, 150, 250, 350],
        500: [100, 250, 350, 450],
    },
    'Monmr': { # Monmore
        480: [80, 240, 320, 400],
    },
    # Adăugați aici alte piste/distanțe dacă apar
}

# ----------------------------------------------------------------------
#  Ajustări pe baza atribute ogar (vârstă, sex, box, grad, recență)
# ----------------------------------------------------------------------

# Praguri vârstă pentru ajustări
YOUNG_AGE_THRESHOLD = 2.5  # ani (sub această vârstă e considerat tânăr)
OLD_AGE_THRESHOLD   = 4.5  # ani (peste această vârstă e considerat bătrân)

# Ajustări de timp pe baza vârstei
YOUNG_AGE_ADJUSTMENT = 0.2  # secunde (ogarii tineri primesc penalizare)
OLD_AGE_ADJUSTMENT   = 0.1  # secunde (ogarii bătrâni primesc penalizare)

# Ajustări de timp pe baza sexului
SEX_ADJUSTMENTS = {
    'M': 0.0,    # Mascul
    'F': 0.1,    # Femelă
    'D': 0.0,    # Dog (mascul)
    'B': 0.1,    # Bitch (femelă)
    'N/A': 0.0   # Necunoscut
}

# Factor de ajustare pentru diferența dintre boxul ogarului și media boxurilor sale istorice
BOX_POSITION_ADJUSTMENT_FACTOR = 0.03  # secunde/box

# Ajustări pe baza gradului cursei curente (grad din fișierul CSV)
GRADE_ADJUSTMENTS = {
    'A1': 0.0,
    'A2': 0.1,
    'A3': 0.2,
    'A4': 0.3,
    'A5': 0.4,
    'A6': 0.5,
    'A7': 0.6,
    'A8': 0.7,
    'A9': 0.8,
    'A10': 0.9,
    'OPEN': 0.0,
    'STANDARD': 0.5,
    '': 0.5,     # Default pentru grad gol/necunoscut
    'N/A': 0.5,  # Default pentru grad N/A
    # Adăugați alte grade relevante dacă există în CSV
}

# Praguri recență (număr de zile)
RECENCY_THRESHOLD_RECENT_DAYS   = 30
RECENCY_THRESHOLD_MODERATE_DAYS = 90
RECENCY_THRESHOLD_OLD_DAYS      = 180

# Ajustări pe baza recenței
RECENCY_ADJUSTMENTS = {
    'Very Recent': 0.0,
    'Recent':      0.1,
    'Moderate':    0.2,
    'Old':         0.3,
    'No History':  0.5,
    'N/A Date':    0.5
}

# Timp maxim (folosit pentru a marca lipsă date sau ogari foarte slabi)
TIMP_MAX_NECUNOSCUT = 999.99

# ----------------------------------------------------------------------
#  REMARK: cuvinte cheie pentru probleme și alergare liberă
# ----------------------------------------------------------------------

# Listă completă de cuvinte cheie pentru probleme (trafic/incidente) din REMARK
PROBLEM_KEYWORDS = [
    # Abrevieri uzuale și variante britanice
    'Awk', 'Awkward', 'Bd', 'Bdly', 'Blk', 'Blocked', 'Bmp', 'Bumped', 'Ck', 'Ckd', 'Ckds', 'Checked', 'Ckd Sough',
    'CmOffLm', 'Crd', 'Crowded', 'Crmp', 'Cramped', 'DInt', 'Dist', 'Disq', 'dnf', 'Eased', 'Fcd-Ck', 'FcdWd',
    'Fcd', 'FcdW', 'Fd', 'Fdd', 'Imp', 'Impede', 'KO', 'Knocked Over', 'Lm', 'Lame', 'Lckd', 'Locked', 'MsdBk',
    'MsdBk', 'Missed Break', 'OutP', 'Outpaced', 'RnOff', 'Ran Off', 'SlAw', 'Slow Away', 'StkRl', 'Struck Rail',
    'Stmb', 'Stumbled', 'Stppd', 'Stopped', 'TndInTrps', 'Tangled In Traps', 'UpWthTrps', 'Up With Traps', 'Wtd', 'Weakened',
    # Variante de lower case și scrieri alternative
    "awk", "awkward", "bd", "bdly", "blk", "blocked", "bmp", "bumped", "ck", "ckd", "ckds", "checked", "ckd sough",
    "cmofflm", "crd", "crowded", "crmp", "cramped", "dint", "dist", "disq", "dnf", "eased", "fcd-ck", "fcdwd",
    "fcd", "fcdw", "fd", "fdd", "imp", "impede", "ko", "knocked over", "lm", "lame", "lckd", "locked", "msdbk",
    "missed break", "outp", "outpaced", "rnoff", "ran off", "slaw", "slow away", "stkrl", "struck rail",
    "stmb", "stumbled", "stppd", "stopped", "tndintrps", "tangled in traps", "upwthtrps", "up with traps", "wtd", "weakened",
    # Variante compuse și specifice
    "fcd-ck", "fcd-wd", "fcdwd", "bmp rnin", "bmpd rnin", "bmpdrnin", "crd rnin", "ckd rnin", "bmprnin", "bmprnup", "crdrnin", "crdstt",
    "bmpd", "bmprnin", "bmprnup", "crdrnin", "crdstt", "fcdck", "fcdw", "outpaced", "ran off", "stumbled", "tangled", "weakened"
]

# Listă completă de cuvinte cheie pentru alergare liberă (clear run, fără incidente), inclusiv variante și abrevieri
CLEAR_RUN_KEYWORDS = [
    'ALd', 'All Led', 'ClrRn', 'Clear Run', 'DrwClr', 'Drew Clear', 'EvAw', 'Even Away', 'EvCh', 'Even Chase', 'LftClr', 'Left Clear',
    'QAw', 'Quick Away', 'Rls', 'Rails', 'RnOn', 'Ran On', 'SnLd', 'Soon Led', 'StrFn', 'Strong Finish', 'Styd', 'Stayed', 'ThrOut', 'Throughout',
    'VQAw', 'Very Quick Away', 'FnWll', 'Finish Well', 'GdMiddle', 'Good Middle', 'HldOn', 'Held On', 'MsdTrbl', 'Missed Trouble',
    # Variante de lower case și scrieri alternative
    "ald", "all led", "clrrn", "clear run", "drwclr", "drew clear", "evaw", "even away", "evch", "even chase", "lftclr", "left clear",
    "qaw", "quick away", "rls", "rails", "rnon", "ran on", "snld", "soon led", "strfn", "strong finish", "styd", "stayed", "throut", "throughout",
    "vqaw", "very quick away", "fnwll", "finish well", "gdmiddle", "good middle", "hldon", "held on", "msdtrbl", "missed trouble",
    # Expresii cu pace/chase/lead
    "chl", "chased leader", "ep", "early pace", "ld", "led", "rnin", "run-in"
]

# ----------------------------------------------------------------------
#  Ponderi pentru REMARK (penalizare/bonus funcție de probleme/liber)
# ----------------------------------------------------------------------

COEFICIENT_PENALIZARE_PROBLEME_REMARK = 0.2   # +0.2s pentru 100% curse cu probleme
COEFICIENT_BONUS_LIBER_REMARK = 0.1           # -0.1s pentru 100% curse cu alergare liberă

# ----------------------------------------------------------------------
#  Ponderi pentru ajustarea pe baza indicatorilor de CURBA (curbe)
# ----------------------------------------------------------------------

COEFICIENT_BONUS_CURBA_FINISHER = 0.07   # -0.07s dacă ogarul recuperează >=2 poziții pe final ("Finisher")
COEFICIENT_PENALIZARE_CURBA_EARLY = 0.07 # +0.07s dacă ogarul pierde >=2 poziții pe final ("Early Pace")

# ----------------------------------------------------------------------
#  Alte opțiuni suplimentare (de extins la nevoie)
# ----------------------------------------------------------------------

# Exemplu: praguri suplimentare, setări de debug etc.

# ======================================================================
#                SFÂRȘIT CONFIG.PY EXTINS COMPLET
# ======================================================================