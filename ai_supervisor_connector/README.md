# AI Supervisor V5 Connector 5.0.0-alpha13

Connector sukuria privatų Home Assistant snapshot ir perduoda jį Windows Engine.

Alpha13 naudoja vienkryptį proceso žemėlapį, komponentu paremtus struktūrinius YAML pakeitimus ir privalomą preflight patikrą prieš įrašymą. Engine planą sukuria vieną kartą, operacijų etape apdoroja po vieną failą ir kiekvieną kelią pririša prie konkretaus `automation`, `script`, `scene` arba root komponento. Connector izoliuotoje `/data` srityje paruošia dabartines bei siūlomas failų kopijas, dar kartą tikrina visus packages YAML failus ir tik tada gali atrakinti įrašymą.