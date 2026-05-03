# smart_meters_simulator.py
"""
Simulateur de compteurs intelligents
Generation de donnees + detection d'anomalies + alertes
"""

import random
import time
import csv
import os
import json
from datetime import datetime
from collections import deque

# ==================== CONFIGURATION ====================
NB_SMART_METERS = 50
INTERVALLE_SECONDES = 2
SEUIL_CONSOMMATION_MAX = 15.0
SEUIL_TENSION_MIN = 210.0
SEUIL_TENSION_MAX = 250.0
SEUIL_VARIATION_RAPIDE = 5.0

FICHIER_DONNEES = "donnees_smart_meters.csv"
FICHIER_ALERTES = "alertes_smart_meters.csv"
FICHIER_LOG = "logs_smart_meters.txt"
FICHIER_ETAT = "smart_meters_state.json"

ZONES = ["Zone A", "Zone B", "Zone C", "Zone D"]

TYPES_COMPTEURS = {
    "residentiel": {
        "plage_normale": (0.5, 3.0),
        "seuil_alerte": 5.0,
    },
    "commercial": {
        "plage_normale": (3.0, 10.0),
        "seuil_alerte": 15.0,
    },
    "industriel": {
        "plage_normale": (10.0, 30.0),
        "seuil_alerte": 45.0,
    },
}

# Codes ANSI simples pour console coloree
ANSI_VERT = "\033[92m"
ANSI_ROUGE = "\033[91m"
ANSI_BLEU = "\033[94m"
ANSI_RESET = "\033[0m"
ANSI_GRAS = "\033[1m"


# ==================== CLASS SmartMeter ====================
class SmartMeter:
    def __init__(self, meter_id, zone, type_consommateur):
        self.meter_id = meter_id
        self.zone = zone
        self.type_consommateur = type_consommateur
        self.last_consommation = random.uniform(*TYPES_COMPTEURS[type_consommateur]["plage_normale"])
        self.historique = deque(maxlen=20)

    def generer_consommation(self):
        plage_min, plage_max = TYPES_COMPTEURS[self.type_consommateur]["plage_normale"]

        # Consommation de base dans la plage normale
        base = random.uniform(plage_min, plage_max)

        # Inertie sur la valeur precedente pour un comportement plus realiste
        inertie = 0.65 * self.last_consommation + 0.35 * base

        # Bruit aleatoire borne
        variation = random.uniform(-1.2, 1.2)
        consommation = max(0.0, inertie + variation)

        # Injection rare de scenarios anormaux pour tester les alertes
        tirage = random.random()
        if tirage < 0.03:
            consommation += random.uniform(6.0, 18.0)
        elif tirage < 0.035 and self.type_consommateur != "residentiel":
            consommation = 0.0

        self.last_consommation = consommation
        return round(consommation, 3)

    def generer_tension(self):
        tension = random.uniform(218.0, 242.0)

        # Anomalie de tension occasionnelle
        tirage = random.random()
        if tirage < 0.02:
            tension = random.uniform(190.0, 208.0)
        elif tirage < 0.04:
            tension = random.uniform(251.0, 270.0)

        return round(tension, 2)

    def generer_courant(self, consommation, tension):
        if tension <= 0:
            return 0.0
        courant = (consommation * 1000.0) / tension
        return round(courant, 3)

    def detecter_anomalie(self, consommation, tension, historique):
        anomalies = []

        seuil_type = TYPES_COMPTEURS[self.type_consommateur]["seuil_alerte"]
        if consommation > seuil_type:
            anomalies.append("Surcharge")

        if tension < SEUIL_TENSION_MIN or tension > SEUIL_TENSION_MAX:
            anomalies.append("Tension hors norme")

        if historique:
            derniere_conso = historique[-1]
            if abs(consommation - derniere_conso) > SEUIL_VARIATION_RAPIDE:
                anomalies.append("Pic soudain")

        if self.type_consommateur in ("commercial", "industriel") and consommation == 0.0:
            anomalies.append("Consommation nulle suspecte")

        return anomalies

    def lire(self):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        consommation = self.generer_consommation()
        tension = self.generer_tension()
        courant = self.generer_courant(consommation, tension)

        anomalies = self.detecter_anomalie(consommation, tension, self.historique)
        self.historique.append(consommation)

        return {
            "timestamp": timestamp,
            "meter_id": self.meter_id,
            "zone": self.zone,
            "type": self.type_consommateur,
            "consommation_kw": consommation,
            "tension_v": tension,
            "courant_a": courant,
            "anomalies": anomalies,
        }


# ==================== CLASS SmartMeterSimulator ====================
class SmartMeterSimulator:
    def __init__(self, nb_meters):
        self.nb_meters = nb_meters
        self.meters = []
        self.iteration = 0
        self.nb_lectures = 0
        self.nb_alertes = 0
        self.somme_consommation = 0.0

        self._creer_meters()
        self._initialiser_fichiers()

    def _initialiser_fichiers(self):
        try:
            if not os.path.exists(FICHIER_DONNEES) or os.path.getsize(FICHIER_DONNEES) == 0:
                with open(FICHIER_DONNEES, mode="w", newline="", encoding="utf-8") as f_data:
                    writer = csv.writer(f_data)
                    writer.writerow(
                        [
                            "timestamp",
                            "meter_id",
                            "zone",
                            "type",
                            "consommation_kw",
                            "tension_v",
                            "courant_a",
                            "statut",
                            "anomalies",
                        ]
                    )

            if not os.path.exists(FICHIER_ALERTES) or os.path.getsize(FICHIER_ALERTES) == 0:
                with open(FICHIER_ALERTES, mode="w", newline="", encoding="utf-8") as f_alertes:
                    writer = csv.writer(f_alertes)
                    writer.writerow(
                        [
                            "timestamp",
                            "meter_id",
                            "zone",
                            "type",
                            "consommation_kw",
                            "tension_v",
                            "courant_a",
                            "alerte",
                        ]
                    )

            if not os.path.exists(FICHIER_LOG):
                with open(FICHIER_LOG, mode="w", encoding="utf-8") as f_log:
                    f_log.write("=== Demarrage du simulateur smart meters ===\n")
        except OSError as exc:
            print(f"Erreur initialisation fichiers: {exc}")

    def _creer_meters(self):
        # Repartition simple des types: 60% residentiel, 25% commercial, 15% industriel
        for index in range(1, self.nb_meters + 1):
            meter_id = f"SM_{index:04d}"
            zone = ZONES[(index - 1) % len(ZONES)]

            ratio = index / float(self.nb_meters)
            if ratio <= 0.60:
                type_consommateur = "residentiel"
            elif ratio <= 0.85:
                type_consommateur = "commercial"
            else:
                type_consommateur = "industriel"

            self.meters.append(SmartMeter(meter_id, zone, type_consommateur))

    def _afficher_statistiques(self):
        moyenne = self.somme_consommation / self.nb_lectures if self.nb_lectures else 0.0
        taux_alerte = (self.nb_alertes / self.nb_lectures) * 100.0 if self.nb_lectures else 0.0

        print("=" * 60)
        print(f"{ANSI_BLEU}{ANSI_GRAS}STATS ({self.iteration} iterations) - {datetime.now().strftime('%H:%M:%S')}{ANSI_RESET}")
        print(f"Consommation moyenne: {moyenne:.2f} kW")
        print(f"Alertes totales: {self.nb_alertes}")
        print(f"Taux d'alerte: {taux_alerte:.2f}%")
        print("=" * 60)

        self._ecrire_log(
            f"[STATS] iteration={self.iteration}, moyenne={moyenne:.3f}kW, "
            f"alertes={self.nb_alertes}, taux={taux_alerte:.2f}%"
        )

    def _sauvegarder_donnees(self, donnee):
        try:
            statut = "ALERTE" if donnee["anomalies"] else "NORMAL"
            anomalies_txt = " | ".join(donnee["anomalies"]) if donnee["anomalies"] else ""

            with open(FICHIER_DONNEES, mode="a", newline="", encoding="utf-8") as f_data:
                writer = csv.writer(f_data)
                writer.writerow(
                    [
                        donnee["timestamp"],
                        donnee["meter_id"],
                        donnee["zone"],
                        donnee["type"],
                        f"{donnee['consommation_kw']:.3f}",
                        f"{donnee['tension_v']:.2f}",
                        f"{donnee['courant_a']:.3f}",
                        statut,
                        anomalies_txt,
                    ]
                )
        except OSError as exc:
            self._ecrire_log(f"[ERREUR] echec sauvegarde donnees: {exc}")

    def _sauvegarder_alerte(self, alerte):
        try:
            with open(FICHIER_ALERTES, mode="a", newline="", encoding="utf-8") as f_alertes:
                writer = csv.writer(f_alertes)
                writer.writerow(
                    [
                        alerte["timestamp"],
                        alerte["meter_id"],
                        alerte["zone"],
                        alerte["type"],
                        f"{alerte['consommation_kw']:.3f}",
                        f"{alerte['tension_v']:.2f}",
                        f"{alerte['courant_a']:.3f}",
                        " | ".join(alerte["anomalies"]),
                    ]
                )
        except OSError as exc:
            self._ecrire_log(f"[ERREUR] echec sauvegarde alerte: {exc}")

    def _ecrire_log(self, message):
        try:
            horodatage = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(FICHIER_LOG, mode="a", encoding="utf-8") as f_log:
                f_log.write(f"[{horodatage}] {message}\n")
        except OSError:
            print(f"[LOG ERREUR] {message}")

    def _sauvegarder_etat(self, running: bool):
        etat = {
            "running": running,
            "timestamp": datetime.now().timestamp(),
            "iteration": self.iteration,
            "nb_lectures": self.nb_lectures,
            "nb_alertes": self.nb_alertes,
        }

        try:
            with open(FICHIER_ETAT, mode="w", encoding="utf-8") as f_etat:
                json.dump(etat, f_etat, ensure_ascii=False, indent=2)
        except OSError as exc:
            self._ecrire_log(f"[ERREUR] echec sauvegarde etat: {exc}")

    def demarrer(self):
        nb_res = sum(1 for meter in self.meters if meter.type_consommateur == "residentiel")
        nb_com = sum(1 for meter in self.meters if meter.type_consommateur == "commercial")
        nb_ind = sum(1 for meter in self.meters if meter.type_consommateur == "industriel")

        print(f"{ANSI_GRAS}SIMULATEUR DE COMPTEURS INTELLIGENTS{ANSI_RESET}")
        print("=" * 60)
        print(f"{ANSI_VERT}{self.nb_meters} compteurs intelligents crees{ANSI_RESET}")
        print(f"Residentiels: {nb_res}")
        print(f"Commerciaux: {nb_com}")
        print(f"Industriels: {nb_ind}")
        print("=" * 60)

        self._ecrire_log("Simulation demarree")
        self._sauvegarder_etat(True)

        while True:
            self.iteration += 1

            for meter in self.meters:
                lecture = meter.lire()

                self.nb_lectures += 1
                self.somme_consommation += lecture["consommation_kw"]

                self._sauvegarder_donnees(lecture)

                heure = datetime.now().strftime("%H:%M:%S")
                if lecture["anomalies"]:
                    self.nb_alertes += 1
                    self._sauvegarder_alerte(lecture)
                    msg_alerte = " | ".join(lecture["anomalies"])
                    print(
                        f"{ANSI_ROUGE}[{heure}] {lecture['meter_id']} | {lecture['zone']} | "
                        f"{lecture['type']} | {lecture['consommation_kw']:.2f} kW | "
                        f"{lecture['tension_v']:.1f} V | ALERTE: {msg_alerte}{ANSI_RESET}"
                    )
                    self._ecrire_log(
                        f"ALERTE meter={lecture['meter_id']} zone={lecture['zone']} "
                        f"type={lecture['type']} anomalies={msg_alerte}"
                    )
                else:
                    print(
                        f"{ANSI_VERT}[{heure}] {lecture['meter_id']} | {lecture['zone']} | "
                        f"{lecture['type']} | {lecture['consommation_kw']:.2f} kW | "
                        f"{lecture['tension_v']:.1f} V | NORMAL{ANSI_RESET}"
                    )

            if self.iteration % 10 == 0:
                self._afficher_statistiques()

            self._sauvegarder_etat(True)

            time.sleep(INTERVALLE_SECONDES)


# ==================== MAIN ====================
if __name__ == "__main__":
    simulateur = SmartMeterSimulator(NB_SMART_METERS)
    try:
        simulateur.demarrer()
    except KeyboardInterrupt:
        print("\nArret demande par l'utilisateur")
        simulateur._ecrire_log("Arret demande par l'utilisateur (Ctrl+C)")
        simulateur._sauvegarder_etat(False)
        simulateur._afficher_statistiques()
        print("Donnees sauvegardees")
    except Exception as exc:
        simulateur._ecrire_log(f"[ERREUR FATALE] {exc}")
        simulateur._sauvegarder_etat(False)
        print(f"Erreur fatale: {exc}")
    finally:
        simulateur._ecrire_log("Fin de simulation")
        simulateur._sauvegarder_etat(False)
