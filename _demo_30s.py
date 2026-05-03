import time
import smart_meters_simulator as s

sim = s.SmartMeterSimulator(s.NB_SMART_METERS)
start = time.time()
end_time = start + 30
cycles = 0

print(f"DEMO_START nb_meters={sim.nb_meters} interval={s.INTERVALLE_SECONDES}s duration=30s")

while time.time() < end_time:
    cycles += 1
    sim.iteration = cycles
    cycle_lectures = 0
    cycle_alertes = 0

    for m in sim.meters:
        lecture = m.lire()
        sim.nb_lectures += 1
        sim.somme_consommation += lecture["consommation_kw"]
        sim._sauvegarder_donnees(lecture)
        cycle_lectures += 1

        if lecture["anomalies"]:
            sim.nb_alertes += 1
            cycle_alertes += 1
            sim._sauvegarder_alerte(lecture)

    elapsed = time.time() - start
    msg = f"CYCLE {cycles:02d} elapsed={elapsed:5.1f}s lectures+={cycle_lectures} alertes+={cycle_alertes} total_lectures={sim.nb_lectures} total_alertes={sim.nb_alertes}"
    print(msg)

    if time.time() + s.INTERVALLE_SECONDES > end_time:
        break
    time.sleep(s.INTERVALLE_SECONDES)

sim._afficher_statistiques()
sim._ecrire_log("Demo 30s terminee")

moyenne = sim.somme_consommation / sim.nb_lectures if sim.nb_lectures else 0.0
taux = (sim.nb_alertes / sim.nb_lectures) * 100.0 if sim.nb_lectures else 0.0
print(f"DEMO_END cycles={cycles} lectures={sim.nb_lectures} alertes={sim.nb_alertes} moyenne={moyenne:.3f} taux={taux:.2f}%")
