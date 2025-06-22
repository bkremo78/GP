import csv
import sys
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import json
from collections import Counter

# Importă toate constantele și funcțiile necesare din fișierele de configurare și logică
try:
    from config import (
        DEFAULT_CSV_FILE,
        DEFAULT_CURSA_NOUA_GUI,
        TRACK_NAME_MAP_GUI_TO_CSV,
        DISTANTE_PUNCTE_SIMULARE,
        TIMP_MAX_NECUNOSCUT,
        PARTICIPANTS_FILE,
        GUI_SETTINGS_FILE,
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
        CSV_PER_ARENA,
    )
    from predictor_logic import (
        prezice_cursa_combinata,
        simuleaza_cursa,
        test_ponderi_sistematizat,
    )

except ImportError as e:
    messagebox.showerror("Eroare Fatala de Import", f"Nu pot importa modulele necesare: {e}. Asigurați-vă că fișierele 'config.py' și 'predictor_logic.py' există și sunt în același director cu 'predictor_simplu.py' și că nu conțin erori de sintaxă (ex: indentare).")
    sys.exit(1)


class GreyhoundPredictorGUI:
    def __init__(self, master):
        self.master = master
        master.title("Greyhound Predictor Simplu (Include Ajustări Box, Vârstă, Sex, Poziție, Grad, Recență)")
        master.geometry("750x980")

        master.option_add('*tearOff', False)
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.csv_file_path = tk.StringVar(value=DEFAULT_CSV_FILE)
        self.pista_gui = tk.StringVar(value=DEFAULT_CURSA_NOUA_GUI['pista'])
        self.distanta_m_gui = tk.IntVar(value=DEFAULT_CURSA_NOUA_GUI['distanta_m'])
        self.grad_cursa_gui = tk.StringVar(value="")
        self.data_cursa_gui = tk.StringVar(value="")

        self.box_name_vars = [tk.StringVar() for _ in range(6)]

        self.weight_best_timp = tk.DoubleVar(value=0.25)
        self.weight_avg_timp = tk.DoubleVar(value=0.45)
        self.weight_avg_trap = tk.DoubleVar(value=0.30)

        self.load_gui_settings()

        s = ttk.Style()
        s.configure('Placeholder.TEntry', foreground='gray')

        self.input_frame = ttk.LabelFrame(master, text="Date Cursă și Istoric")
        self.input_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.input_frame.columnconfigure(0, weight=0)
        self.input_frame.columnconfigure(1, weight=1)
        self.input_frame.columnconfigure(2, weight=0)

        self.csv_label = ttk.Label(self.input_frame, text="Fișier CSV Istoric:")
        self.csv_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.csv_entry = ttk.Entry(self.input_frame, textvariable=self.csv_file_path, width=50)
        self.csv_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.browse_button = ttk.Button(self.input_frame, text="Browse", command=self.browse_csv_file)
        self.browse_button.grid(row=0, column=2, padx=5, pady=5, sticky="e")

        self.pista_label = ttk.Label(self.input_frame, text="Pistă (GUI Name):")
        self.pista_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.pista_combobox = ttk.Combobox(self.input_frame, textvariable=self.pista_gui,
                                           values=list(TRACK_NAME_MAP_GUI_TO_CSV.keys()))
        self.pista_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.pista_combobox.bind("<<ComboboxSelected>>", self.on_pista_changed)

        self.distanta_label = ttk.Label(self.input_frame, text="Distanță (m):")
        self.distanta_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.distanta_entry = ttk.Entry(self.input_frame, textvariable=self.distanta_m_gui, width=10)
        self.distanta_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        self.grad_label = ttk.Label(self.input_frame, text="Grad Cursă (ex: A1, B2):")
        self.grad_label.grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.grad_entry = ttk.Entry(self.input_frame, textvariable=self.grad_cursa_gui, width=10)
        self.grad_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        self.data_label = ttk.Label(self.input_frame, text="Data Cursă (DD/MM/YYYY):")
        self.data_label.grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.data_entry = ttk.Entry(self.input_frame, textvariable=self.data_cursa_gui, width=15)
        self.data_entry.grid(row=4, column=1, padx=5, pady=5, sticky="w")

        self.boxes_frame = ttk.LabelFrame(master, text="Participanți după Box")
        self.boxes_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.boxes_frame.columnconfigure(0, weight=0)
        self.boxes_frame.columnconfigure(1, weight=1)

        for i in range(6):
            box_number = i + 1
            label = ttk.Label(self.boxes_frame, text=f"Box {box_number}:")
            label.grid(row=i, column=0, padx=5, pady=2, sticky="w")
            entry = ttk.Entry(self.boxes_frame, textvariable=self.box_name_vars[i], width=40)
            entry.grid(row=i, column=1, padx=5, pady=2, sticky="ew")

        self.clear_boxes_button = ttk.Button(self.boxes_frame, text="Golire Boxuri", command=self.clear_all_boxes)
        self.clear_boxes_button.grid(row=6, column=0, columnspan=2, padx=5, pady=5)

        self.load_participants()

        self.weights_frame = ttk.LabelFrame(master, text="Ponderi Calcul Timp Prezisa (Bază - Timpi Finali)")
        self.weights_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.weights_frame.columnconfigure(0, weight=0)
        self.weights_frame.columnconfigure(1, weight=1)

        self.label_weight_best = ttk.Label(self.weights_frame, text="Pondere Best Timp:")
        self.label_weight_best.grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.entry_weight_best = ttk.Entry(self.weights_frame, textvariable=self.weight_best_timp, width=8)
        self.entry_weight_best.grid(row=0, column=1, padx=5, pady=2, sticky="w")

        self.label_weight_avg = ttk.Label(self.weights_frame, text="Pondere Avg Timp:")
        self.label_weight_avg.grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.entry_weight_avg = ttk.Entry(self.weights_frame, textvariable=self.weight_avg_timp, width=8)
        self.entry_weight_avg.grid(row=1, column=1, padx=5, pady=2, sticky="w")

        self.label_weight_trap = ttk.Label(self.weights_frame, text="Pondere Avg Box Timp:")
        self.label_weight_trap.grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.entry_weight_trap = ttk.Entry(self.weights_frame, textvariable=self.weight_avg_trap, width=8)
        self.entry_weight_trap.grid(row=2, column=1, padx=5, pady=2, sticky="w")

        self.run_button = ttk.Button(master, text="Rulează Predicție & Simulare", command=self.run_prediction)
        self.run_button.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        self.output_frame = ttk.LabelFrame(master, text="Rezultate Predicție și Simulare (Include Ajustări Box, Vârstă, Sex, Poziție, Grad, Recență)")
        self.output_frame.grid(row=4, column=0, padx=10, pady=10, sticky="nsew")
        self.output_frame.columnconfigure(0, weight=1)
        self.output_frame.rowconfigure(0, weight=1)

        self.output_text = tk.Text(self.output_frame, wrap="word", height=20)
        self.output_text.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.output_scrollbar = ttk.Scrollbar(self.output_frame, orient=tk.VERTICAL, command=self.output_text.yview)
        self.output_text['yscrollcommand'] = self.output_scrollbar.set
        self.output_scrollbar.grid(row=0, column=1, sticky='ns')

        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=0)
        master.rowconfigure(1, weight=0)
        master.rowconfigure(2, weight=0)
        master.rowconfigure(3, weight=0)
        master.rowconfigure(4, weight=1)

    def browse_csv_file(self):
        filename = filedialog.askopenfilename(
            initialdir=".",
            title="Selectați Fișierul CSV Istoric",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*"))
        )
        if filename:
            self.csv_file_path.set(filename)

    def clear_all_boxes(self):
        for var in self.box_name_vars:
            var.set("")

    def save_participants(self):
        participants_data = [var.get() for var in self.box_name_vars]
        try:
            with open(PARTICIPANTS_FILE, 'w') as f:
                json.dump(participants_data, f)
        except Exception as e:
            print(f"Error saving participants to {PARTICIPANTS_FILE}: {e}")

    def load_participants(self):
        try:
            with open(PARTICIPANTS_FILE, 'r') as f:
                participants_data = json.load(f)
            if isinstance(participants_data, list) and len(participants_data) == 6:
                for i in range(6):
                    loaded_value = participants_data[i]
                    self.box_name_vars[i].set(str(loaded_value).strip() if loaded_value is not None else "")
            else:
                print(f"Warning: Data in {PARTICIPANTS_FILE} is not the expected format (expected list of 6). Starting with empty fields.")
                self.clear_all_boxes()
            pass
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {PARTICIPANTS_FILE}. File might be corrupted. Starting with empty fields.")
            self.clear_all_boxes()
        except Exception as e:
            print(f"An unexpected error occurred while loading participants: {e}")
            self.clear_all_boxes()

    def save_gui_settings(self):
        settings = {
            'csv_file_path': self.csv_file_path.get(),
            'pista_gui': self.pista_gui.get(),
            'distanta_m_gui': self.distanta_m_gui.get(),
            'grad_cursa_gui': self.grad_cursa_gui.get(),
            'data_cursa_gui': self.data_cursa_gui.get(),
            'weight_best_timp': self.weight_best_timp.get(),
            'weight_avg_timp': self.weight_avg_timp.get(),
            'weight_avg_trap': self.weight_avg_trap.get(),
        }
        try:
            with open(GUI_SETTINGS_FILE, 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Error saving GUI settings to {GUI_SETTINGS_FILE}: {e}")

    def load_gui_settings(self):
        try:
            with open(GUI_SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
            if 'csv_file_path' in settings:
                self.csv_file_path.set(settings.get('csv_file_path', DEFAULT_CSV_FILE))
            if 'pista_gui' in settings:
                loaded_pista = settings.get('pista_gui', DEFAULT_CURSA_NOUA_GUI['pista'])
                if loaded_pista in TRACK_NAME_MAP_GUI_TO_CSV:
                    self.pista_gui.set(loaded_pista)
                else:
                    print(f"Warning: Could not load invalid track name '{loaded_pista}' from settings file. Using default.")
                    self.pista_gui.set(DEFAULT_CURSA_NOUA_GUI['pista'])
            if 'distanta_m_gui' in settings:
                try:
                    self.distanta_m_gui.set(int(settings.get('distanta_m_gui', DEFAULT_CURSA_NOUA_GUI['distanta_m'])))
                except (ValueError, tk.TclError):
                    print(f"Warning: Could not load invalid distance value '{settings.get('distanta_m_gui')}' from settings file. Using default.")
                    self.distanta_m_gui.set(DEFAULT_CURSA_NOUA_GUI['distanta_m'])
            if 'grad_cursa_gui' in settings:
                self.grad_cursa_gui.set(settings.get('grad_cursa_gui', ""))
            if 'data_cursa_gui' in settings:
                self.data_cursa_gui.set(settings.get('data_cursa_gui', ""))
            if 'weight_best_timp' in settings:
                try:
                    self.weight_best_timp.set(float(settings.get('weight_best_timp', 0.25)))
                except (ValueError, tk.TclError):
                    print(f"Warning: Could not load invalid weight value '{settings.get('weight_best_timp')}' for best time. Using default.")
                    self.weight_best_timp.set(0.25)
            if 'weight_avg_timp' in settings:
                try:
                    self.weight_avg_timp.set(float(settings.get('weight_avg_timp', 0.45)))
                except (ValueError, tk.TclError):
                    print(f"Warning: Could not load invalid weight value '{settings.get('weight_avg_timp')}' for average time. Using default.")
                    self.weight_avg_timp.set(0.45)
            if 'weight_avg_trap' in settings:
                try:
                    self.weight_avg_trap.set(float(settings.get('weight_avg_trap', 0.30)))
                except (ValueError, tk.TclError):
                    print(f"Warning: Could not load invalid weight value '{settings.get('weight_avg_trap')}' for average trap time. Using default.")
                    self.weight_avg_trap.set(0.30)

        except FileNotFoundError:
            pass
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {GUI_SETTINGS_FILE}. File might be corrupted. Starting with default settings.")
        except Exception as e:
            print(f"An unexpected error occurred while loading GUI settings: {e}")

    def on_closing(self):
        self.save_participants()
        self.save_gui_settings()
        self.master.destroy()

    def on_pista_changed(self, event=None):
        pista = self.pista_gui.get()
        if pista in CSV_PER_ARENA:
            self.csv_file_path.set(CSV_PER_ARENA[pista])

    def run_prediction(self):
        csv_path = self.csv_file_path.get()
        pista_gui_name = self.pista_gui.get()
        distanta_m = self.distanta_m_gui.get()
        grad_cursa = self.grad_cursa_gui.get().strip()
        data_cursa_str = self.data_cursa_gui.get().strip()

        try:
            weight_best = self.weight_best_timp.get()
            weight_avg = self.weight_avg_timp.get()
            weight_trap = self.weight_avg_trap.get()

            if weight_best < 0 or weight_avg < 0 or weight_trap < 0:
                messagebox.showwarning("Ponderi Invalide", "Ponderile timpilor finali nu pot fi negative.")
                return

            greutati_input_gui = {
                'best': weight_best,
                'average': weight_avg,
                'average_trap': weight_trap
            }

            total_weight_sum = weight_best + weight_avg + weight_trap
            if total_weight_sum <= 0:
                messagebox.showwarning("Ponderi Invalide", "Suma ponderilor timpilor finali trebuie să fie mai mare decât zero pentru a calcula o medie ponderată. Predicția poate fi N/A.")

        except tk.TclError:
            messagebox.showwarning("Input Invalid", "Asigurați-vă că ponderile introduse sunt numere valide.")
            return
        except Exception as e:
            messagebox.showerror("Eroare Citire Input", f"A aparut o eroare la citirea ponderilor: {e}")
            return

        if not os.path.exists(csv_path):
            messagebox.showerror("Eroare Fișier", f"Fișierul CSV '{os.path.basename(csv_path)}' nu a fost găsit.")
            return

        pista_csv_name = pista_gui_name
        if pista_gui_name in TRACK_NAME_MAP_GUI_TO_CSV:
            pista_csv_name = TRACK_NAME_MAP_GUI_TO_CSV[pista_gui_name]
        else:
            messagebox.showwarning("Pistă Necunoscută", f"Numele pistei '{pista_gui_name}' nu este mapat în configurație ('TRACK_NAME_MAP_GUI_TO_CSV'). Folosesc numele din GUI ('{pista_gui_name}') pentru căutare în CSV. Asigurați-vă că se potrivește exact cu abrevierile din coloana PISTA din CSV.")

        if distanta_m is None or distanta_m <= 0:
            messagebox.showwarning("Distanță Invalidă", "Distanța cursei trebuie să fie un număr pozitiv.")
            return

        ogari_participanti_list = []
        found_at_least_one_ogar = False
        for i in range(6):
            ogar_name = self.box_name_vars[i].get().strip()
            box_number = i + 1
            if ogar_name:
                ogari_participanti_list.append((ogar_name, box_number))
                found_at_least_one_ogar = True

        if not found_at_least_one_ogar:
            messagebox.showwarning("Lista Ogarilor Goala", "Adăugați ogari participanți în boxuri.")
            return

        detalii_cursa_noua = {
            'pista': pista_csv_name,
            'distanta_m': distanta_m,
            'grad': grad_cursa,
            'data_cursa': data_cursa_str,
            'ogari_participanti': ogari_participanti_list
        }

        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, "Rulează...\n")
        self.output_text.update_idletasks()

        predictie_sortata, istoric_complet_gui, erori_predictie = prezice_cursa_combinata(
            csv_path,
            detalii_cursa_noua,
            greutati_timp_final_override=greutati_input_gui,
        )

        simulation_output = simuleaza_cursa(predictie_sortata, detalii_cursa_noua, istoric_complet_gui)

        def curba_emoji(stil):
            if stil == "Finisher":
                return "🏁"
            elif stil == "EarlyPace":
                return "🚀"
            elif stil == "Constant":
                return "➖"
            else:
                return "❓"

        def stil_text_scurt(stil):
            if stil == "Finisher":
                return "FP"
            elif stil == "EarlyPace":
                return "EP"
            elif stil == "Constant":
                return "CP"
            else:
                return "??"

        if predictie_sortata:
            self.output_text.insert(
                tk.END,
                f"\nPredictie pentru cursa la '{self.pista_gui.get()}', {detalii_cursa_noua.get('distanta_m', 'N/A')}m (Grad: {detalii_cursa_noua.get('grad', 'N/A')}, Data: {detalii_cursa_noua.get('data_cursa', 'N/A')}):\n"
            )
            self.output_text.insert(tk.END, "-" * 220 + "\n")
            # HEADER - cu "Stil" și Emoji după "Sex"
            self.output_text.insert(
                tk.END,
                f"{'Loc':<5}{'Box':<5}{'Nume Ogar':<20}{'Sex':<6}{'Stil':<3}{'':<4}{'Varsta':<8}{'Best Timp':<12}{'Avg Timp':<12}{'Avg Box Time':<12}{'Best Sect':<12}{'Avg Sect':<12}{'Avg Start Pos':<15}{'Timp Prezisa (Comb)':<20}{'%Probleme':<10}{'%Liber':<10}{'Zile':<8}\n"
            )
            self.output_text.insert(tk.END, "-" * 220 + "\n")

            for i, rez in enumerate(predictie_sortata):
                timp_prezis = f"{rez.get('Timp_Prezis_Combinat', TIMP_MAX_NECUNOSCUT):.2f}" if rez.get('Timp_Prezis_Combinat', TIMP_MAX_NECUNOSCUT) < TIMP_MAX_NECUNOSCUT else "N/A"
                best_timp = f"{rez.get('Cel_Mai_Bun_Timp', TIMP_MAX_NECUNOSCUT):.2f}" if rez.get('Cel_Mai_Bun_Timp', TIMP_MAX_NECUNOSCUT) < TIMP_MAX_NECUNOSCUT else "N/A"
                avg_timp = f"{rez.get('Timp_Mediu', TIMP_MAX_NECUNOSCUT):.2f}" if rez.get('Timp_Mediu', TIMP_MAX_NECUNOSCUT) < TIMP_MAX_NECUNOSCUT else "N/A"
                avg_box_time = f"{rez.get('Timp_Mediu_Box_Specific', TIMP_MAX_NECUNOSCUT):.2f}" if rez.get('Timp_Mediu_Box_Specific', TIMP_MAX_NECUNOSCUT) < TIMP_MAX_NECUNOSCUT else "N/A"
                best_sectional = f"{rez.get('Cel_Mai_Bun_Sectional', TIMP_MAX_NECUNOSCUT):.2f}" if rez.get('Cel_Mai_Bun_Sectional', TIMP_MAX_NECUNOSCUT) < TIMP_MAX_NECUNOSCUT else "N/A"
                avg_sectional = f"{rez.get('Timp_Mediu_Sectional', TIMP_MAX_NECUNOSCUT):.2f}" if rez.get('Timp_Mediu_Sectional', TIMP_MAX_NECUNOSCUT) < TIMP_MAX_NECUNOSCUT else "N/A"
                sex_afisat = str(rez.get('Sex', 'N/A')).strip()
                stil_curba = rez.get('Stil_Curba', "N/A")
                stil_scurt = stil_text_scurt(stil_curba)
                emoji = curba_emoji(stil_curba)
                varsta_raw = rez.get('Varsta')
                varsta_afisata = f"{varsta_raw:.1f}" if isinstance(varsta_raw, (int, float)) else (str(varsta_raw).strip() if varsta_raw is not None else "N/A")
                avg_start_pos_raw = rez.get('Medie_Box_Start')
                avg_start_pos_afisata = f"{avg_start_pos_raw:.2f}" if isinstance(avg_start_pos_raw, (int, float)) else "N/A"
                # Variabile fundal (NU se afișează dar se pot folosi ulterior)
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
                # Afișare tabel cu Stil (scurt) și Emoji după Sex:
                self.output_text.insert(
                    tk.END,
                    f"{i+1:<5}{rez.get('Box Nou', 'N/A'):<5}{rez.get('Nume Ogar', 'N/A'):<20}{sex_afisat:<6}{stil_scurt:<3}{emoji:<4}{varsta_afisata:<8}{best_timp:<12}{avg_timp:<12}{avg_box_time:<12}{best_sectional:<12}{avg_sectional:<12}{avg_start_pos_afisata:<15}{timp_prezis:<20}{procent_probleme:<10}{procent_liber:<10}{zile_str:<8}\n"
                )

            self.output_text.insert(tk.END, "-" * 220 + "\n")
            self.output_text.insert(
                tk.END,
                "Stil: FP = Finisher 🏁, EP = EarlyPace 🚀, CP = Constant ➖, ?? = necunoscut/altul\n"
            )

            if any(rez.get('Timp_Prezis_Combinat', TIMP_MAX_NECUNOSCUT) < TIMP_MAX_NECUNOSCUT for rez in predictie_sortata):
                simulation_output = simuleaza_cursa(predictie_sortata, detalii_cursa_noua, istoric_complet_gui)
                self.output_text.insert(tk.END, simulation_output)
            else:
                self.output_text.insert(tk.END, "\nSimularea nu poate rula din cauza lipsei datelor de predicție valide pentru timpul final.\n")

        else:
            self.output_text.insert(tk.END, "\nNu s-au putut genera rezultate de predicție. Verificați fișierul CSV, datele introduse și erorile de mai sus.\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = GreyhoundPredictorGUI(root)
    root.mainloop()

    # # Pentru a rula TESTUL SISTEMATIC al ponderilor (fara GUI), COMENTEAZA liniile de mai sus
    # # si DECOMNTEAZA liniile de mai jos:
    # csv_file = DEFAULT_CSV_FILE
    # cursa_test_base = {
    #     'pista': TRACK_NAME_MAP_GUI_TO_CSV[DEFAULT_CURSA_NOUA_GUI['pista']],
    #     'distanta_m': DEFAULT_CURSA_NOUA_GUI['distanta_m'],
    #     'grad': DEFAULT_CURSA_NOUA_GUI.get('grad', ''),
    #     'data_cursa': '03/05/2024', # Data de test in format DD/MM/YYYY
    #     'ogari_participanti': [
    #         ('Doohoma Princess', 1),
    #         ('Orange Sydney', 2),
    #         ('Sehnsa Mac', 3),
    #         ('Rattytatty', 4),
    #         ('Doohoma Roxie', 5),
    #         ('Spiridon Zelus', 6)
    #     ]
    # }
    # test_ponderi_sistematizat(csv_file, cursa_test_base)