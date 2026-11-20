# Eventor lokalt i ChatGPT

Bruk ChatGPTs skrivebordsapp med lokal datamaskintilgang. Serveren kjører som en
lokal stdio-prosess; ChatGPT starter og stopper den ved behov. Ingen offentlig
nettadresse, tunnel eller OpenAI API-nøkkel er nødvendig for denne tilkoblingen.

## Oppsett

1. Installer avhengighetene i prosjektmappen hvis `.venv` mangler:

   ```sh
   python3 -m venv .venv
   .venv/bin/pip install -e ".[dev]"
   ```

2. Kopier `.env.example` til `.env` hvis filen ikke finnes, og sett
   `EVENTOR_API_KEY` til organisasjonens Eventor-nøkkel. Behold
   `EVENTOR_API_KEY_HEADER=ApiKey`. Eksisterende `.env` skal ikke overskrives.
   Bearer-token og offentlig URL brukes bare av HTTP-transportene.

3. Registrer MCP-serveren (er allerede utført på denne maskinen):

   ```sh
   codex mcp add eventor -- /Users/jonarnes/tempDev/eventor-mcp/scripts/run-local.sh
   ```

   Alternativt: ChatGPT → Settings → MCP servers → Add server. Velg **STDIO**,
   navn `eventor` og kommandoen over fra `/Users/…` til `run-local.sh`, uten
   argumenter. Startskriptet finner prosjektmappen og `.env` uavhengig av hvor
   ChatGPT starter prosessen. Tilpass absolutt sti dersom prosjektet flyttes.
   Et TOML-eksempel finnes i `examples/chatgpt-local.toml`.

4. Velg **Restart** for serveren, eller start ChatGPT på nytt. Bruk `/mcp` for å
   kontrollere tilkoblingen. Åpne en samtale som kjører lokalt.

5. Prøv: «Bruk eventor_ping for å kontrollere tilkoblingen til Eventor», deretter
   «Finn orienteringsløp de neste 30 dagene». Verktøy for personlige resultater
   trenger Eventor-person-ID.

## Kontroller fra terminal

```sh
.venv/bin/python scripts/check-local.py
.venv/bin/python scripts/check-local.py --live
```

Første kommando tester MCP-oppstart og finner verktøyene uten et Eventor-kall.
`--live` utfører i tillegg ett lesende API-kall med den konfigurerte nøkkelen.
Kontrollen skriver ikke organisasjonsdata eller hemmeligheter til terminalen.

Oppsettet gjelder lokal skrivebordsbruk. ChatGPT i nettleseren trenger en separat
fjernforbindelse eller støttet tunnel; lokal stdio-konfigurasjon gjør ikke serveren
nettlesertilgjengelig.

Offisiell dokumentasjon: https://learn.chatgpt.com/docs/extend/mcp
