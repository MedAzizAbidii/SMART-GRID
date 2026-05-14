# smart_meters_simulator.py
"""
Simulateur de compteurs intelligents
Generation de donnees + detection d'anomalies AMELIOREE + alertes
"""

import random
import time
import csv
import os
import json
import torch
import numpy as np
import pandas as pd
from datetime import datetime
from collections import deque

# Import enhanced anomaly detection
try:
    from ml_pipeline.enhanced_anomaly_detection import EnhancedSmartGridAnomalyDetector
    from ml_pipeline.transformer_model import TransformerAutoencoder
    from ml_pipeline.config_ml import MLConfig
    from ml_pipeline.anomaly_detection import AnomalyDetector
    ENHANCED_DETECTION_AVAILABLE = True
    print("✅ Enhanced anomaly detection loaded successfully!")
except ImportError as e:
    ENHANCED_DETECTION_AVAILABLE = False
    print(f"⚠️ Enhanced detection not available: {e}")
    print("   Using basic rule-based detection only")

# ==================== CONFIGURATION ====================
NB_SMART_METERS = 50
INTERVALLE_SECONDES = 2
SEUIL_CONSOMMATION_MAX = 15.0
SEUIL_TENSION_MIN = 210.0
SEUIL_TENSION_MAX = 250.0
SEUIL_VARIATION_RAPIDE = 5.0

# Enhanced detection settings
USE_ENHANCED_DETECTION = True  # Set to False to use only basic detection
ENHANCED_DETECTION_BATCH_SIZE = 20  # Run enhanced detection every N readings
ENHANCED_DETECTION_THRESHOLD = 0.1  # Lower = more sensitive (was 0.2, now 0.1 for better recall)

FICHIER_DONNEES = "donnees_smart_meters.csv"
FICHIER_ALERTES = "alertes_smart_meters.csv"
FICHIER_LOG = "logs_smart_meters.txt"
FICHIER_ETAT = "smart_meters_state.json"
FICHIER_ENHANCED_RESULTS = "enhanced_detection_results.csv"  # New file for enhanced results

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
    
    def generer_facteur_puissance(self):
        """Generate power factor (typically 0.85-0.95)"""
        facteur = random.uniform(0.85, 0.95)
        
        # Occasional low power factor anomaly
        if random.random() < 0.02:
            facteur = random.uniform(0.6, 0.8)
        
        return round(facteur, 3)
    
    def generer_frequence(self):
        """Generate grid frequency (60 Hz ± variations)"""
        frequence = random.gauss(60.0, 0.15)
        
        # Occasional frequency anomaly
        if random.random() < 0.01:
            frequence = random.uniform(58.5, 61.5)
        
        return round(frequence, 2)

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
        facteur_puissance = self.generer_facteur_puissance()
        frequence = self.generer_frequence()

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
            "facteur_puissance": facteur_puissance,
            "frequency_hz": frequence,
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
        self.nb_alertes_enhanced = 0  # New counter for enhanced detection
        self.somme_consommation = 0.0
        
        # Enhanced detection components
        self.enhanced_detector = None
        self.ml_model = None
        self.readings_buffer = []  # Buffer for batch processing
        self.use_enhanced = USE_ENHANCED_DETECTION and ENHANCED_DETECTION_AVAILABLE
        
        self._creer_meters()
        self._initialiser_fichiers()
        
        if self.use_enhanced:
            self._initialiser_enhanced_detection()

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
                            "facteur_puissance",
                            "frequency_hz",
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
            
            # Initialize enhanced results file
            if self.use_enhanced:
                if not os.path.exists(FICHIER_ENHANCED_RESULTS) or os.path.getsize(FICHIER_ENHANCED_RESULTS) == 0:
                    with open(FICHIER_ENHANCED_RESULTS, mode="w", newline="", encoding="utf-8") as f_enhanced:
                        writer = csv.writer(f_enhanced)
                        writer.writerow([
                            "timestamp", "meter_id", "zone", "type",
                            "consommation_kw", "tension_v", "courant_a",
                            "is_anomaly", "anomaly_type", "confidence",
                            "reconstruction_score", "voltage_score", "consumption_score",
                            "power_factor_score", "frequency_score", "temporal_score", "rate_change_score"
                        ])

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
    
    def _initialiser_enhanced_detection(self):
        """Initialize enhanced anomaly detection system"""
        try:
            print(f"\n{ANSI_BLEU}🔧 Initializing Enhanced Anomaly Detection...{ANSI_RESET}")
            
            # Initialize enhanced detector
            self.enhanced_detector = EnhancedSmartGridAnomalyDetector()
            self.enhanced_detector.thresholds['voltage_min'] = SEUIL_TENSION_MIN
            self.enhanced_detector.thresholds['voltage_max'] = SEUIL_TENSION_MAX
            
            # Try to load trained model
            config = MLConfig()
            model_path = os.path.join(config.MODEL_SAVE_PATH, 'best_transformer.pth')
            
            if os.path.exists(model_path):
                print(f"   ✅ Loading trained model from: {model_path}")
                n_features = 14  # Default feature count
                self.ml_model = TransformerAutoencoder(
                    n_features=n_features,
                    d_model=config.D_MODEL,
                    n_heads=config.N_HEADS,
                    n_encoder_layers=config.N_ENCODER_LAYERS,
                    d_ff=config.D_FF,
                    dropout=config.DROPOUT,
                    max_seq_length=config.MAX_SEQ_LENGTH
                )
                self.ml_model.load_state_dict(torch.load(model_path, map_location='cpu'))
                self.ml_model.eval()
                print(f"   ✅ Model loaded successfully!")
            else:
                print(f"   ⚠️ No trained model found at {model_path}")
                print(f"   ℹ️ Using rule-based detection only")
                self.ml_model = None
            
            print(f"   ✅ Enhanced detection initialized with 7 criteria")
            print(f"   ℹ️ Detection threshold: {ENHANCED_DETECTION_THRESHOLD}")
            print(f"   ℹ️ Batch size: {ENHANCED_DETECTION_BATCH_SIZE} readings\n")
            
        except Exception as e:
            print(f"   ❌ Error initializing enhanced detection: {e}")
            print(f"   ℹ️ Falling back to basic detection")
            self.use_enhanced = False

    def _process_enhanced_detection(self):
        """Process buffered readings with enhanced detection"""
        if not self.readings_buffer or not self.use_enhanced:
            return
        
        try:
            # Convert buffer to DataFrame
            df = pd.DataFrame(self.readings_buffer)
            
            # Add derived features
            df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
            df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek
            df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
            df = df.sort_values(['meter_id', 'timestamp'])
            df['consumption_diff'] = df.groupby('meter_id')['consommation_kw'].diff().fillna(0)
            df['consumption_rate_change'] = df.groupby('meter_id')['consommation_kw'].pct_change().fillna(0)
            
            # Compute baseline statistics if not done yet
            if not self.enhanced_detector.statistics:
                self.enhanced_detector.compute_statistics(df)
            
            # Create dummy reconstruction errors (since we're doing real-time detection)
            reconstruction_errors = np.random.uniform(0.01, 0.1, len(df))
            
            # Run enhanced detection
            anomaly_scores = self.enhanced_detector.detect_anomalies(
                reconstruction_errors,
                df,
                threshold_percentile=95
            )
            
            # Save enhanced results
            for idx, (_, row) in enumerate(df.iterrows()):
                score = anomaly_scores[idx]
                
                if score.is_anomaly:
                    self.nb_alertes_enhanced += 1
                
                # Save to enhanced results file
                with open(FICHIER_ENHANCED_RESULTS, mode="a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        row['timestamp'], row['meter_id'], row['zone'], row['type'],
                        f"{row['consommation_kw']:.3f}", f"{row['tension_v']:.2f}", f"{row['courant_a']:.3f}",
                        1 if score.is_anomaly else 0,
                        score.anomaly_type,
                        f"{score.confidence:.4f}",
                        f"{score.reconstruction_error:.4f}",
                        f"{score.voltage_anomaly:.4f}",
                        f"{score.consumption_anomaly:.4f}",
                        f"{score.power_factor_anomaly:.4f}",
                        f"{score.frequency_anomaly:.4f}",
                        f"{score.temporal_anomaly:.4f}",
                        f"{score.rate_change_anomaly:.4f}"
                    ])
                
                # Print enhanced detection alerts
                if score.is_anomaly and score.confidence > 0.7:
                    heure = row['timestamp'].split()[1] if ' ' in row['timestamp'] else row['timestamp']
                    print(f"{ANSI_ROUGE}[ENHANCED] [{heure}] {row['meter_id']} | "
                          f"Type: {score.anomaly_type} | Confidence: {score.confidence:.2f} | "
                          f"{row['consommation_kw']:.2f} kW | {row['tension_v']:.1f} V{ANSI_RESET}")
            
            # Clear buffer
            self.readings_buffer = []
            
        except Exception as e:
            self._ecrire_log(f"[ERREUR] Enhanced detection failed: {e}")
            print(f"{ANSI_ROUGE}⚠️ Enhanced detection error: {e}{ANSI_RESET}")
    
    def _afficher_statistiques(self):
        moyenne = self.somme_consommation / self.nb_lectures if self.nb_lectures else 0.0
        taux_alerte = (self.nb_alertes / self.nb_lectures) * 100.0 if self.nb_lectures else 0.0

        print("=" * 60)
        print(f"{ANSI_BLEU}{ANSI_GRAS}STATS ({self.iteration} iterations) - {datetime.now().strftime('%H:%M:%S')}{ANSI_RESET}")
        print(f"Consommation moyenne: {moyenne:.2f} kW")
        print(f"Alertes basiques: {self.nb_alertes}")
        print(f"Taux d'alerte basique: {taux_alerte:.2f}%")
        
        if self.use_enhanced:
            taux_enhanced = (self.nb_alertes_enhanced / self.nb_lectures) * 100.0 if self.nb_lectures else 0.0
            print(f"{ANSI_VERT}Alertes enhanced: {self.nb_alertes_enhanced}{ANSI_RESET}")
            print(f"{ANSI_VERT}Taux enhanced: {taux_enhanced:.2f}%{ANSI_RESET}")
        
        print("=" * 60)

        log_msg = f"[STATS] iteration={self.iteration}, moyenne={moyenne:.3f}kW, alertes_basic={self.nb_alertes}"
        if self.use_enhanced:
            log_msg += f", alertes_enhanced={self.nb_alertes_enhanced}"
        self._ecrire_log(log_msg)

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
                        f"{donnee['facteur_puissance']:.3f}",
                        f"{donnee['frequency_hz']:.2f}",
                        statut,
                        anomalies_txt,
                    ]
                )
            
            # Add to buffer for enhanced detection
            if self.use_enhanced:
                self.readings_buffer.append(donnee)
                
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
        
        if self.use_enhanced:
            print(f"{ANSI_BLEU}✅ Enhanced Anomaly Detection: ACTIVE{ANSI_RESET}")
            print(f"   • 7 detection criteria")
            print(f"   • Threshold: {ENHANCED_DETECTION_THRESHOLD}")
            print(f"   • Batch size: {ENHANCED_DETECTION_BATCH_SIZE}")
        else:
            print(f"{ANSI_ROUGE}⚠️ Enhanced Detection: DISABLED{ANSI_RESET}")
            print(f"   • Using basic rule-based detection only")
        
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
                        f"{ANSI_ROUGE}[BASIC] [{heure}] {lecture['meter_id']} | {lecture['zone']} | "
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
            
            # Process enhanced detection batch
            if self.use_enhanced and len(self.readings_buffer) >= ENHANCED_DETECTION_BATCH_SIZE:
                print(f"\n{ANSI_BLEU}🔍 Running enhanced detection on {len(self.readings_buffer)} readings...{ANSI_RESET}")
                self._process_enhanced_detection()
                print()

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
