# AI Supervisor V5 Connector 5.0.0b1

Connector sukuria privatų Home Assistant snapshot, perduoda jį Windows Engine ir vienintelis valdo galimą įrašymą į Home Assistant.

Beta1 ilgas operacijas vykdo foninėmis, `/data/background_jobs.json` faile išsaugomomis užduotimis. Sąsaja periodiškai tikrina jų būseną, todėl snapshot, analizė ar preflight nepriklauso nuo vienos ilgai atidarytos ingress užklausos.

Klaidos saugiai perduodamos Windows Engine autonominei laboratorijai. Laboratorija neveikia Home Assistant failuose ir negali apeiti Connector preflight, backup, validacijos ar rollback apsaugų.
