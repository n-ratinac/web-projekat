## Timovi

| Tim A     | Tim B    |
| --------- | -------- |
| Mina      | Pavle    |
| Todor     | Aritonovic|
| Varagic   | Zarije   |
| Lajzer    | Velickovic |
| Ilic      | Andjela    |

## Podešavanje projekta

U powershell-u, otići u neki direktorijum gde imate pune permisije i izvršiti sledeće.

```sh
git clone https://github.com/n-ratinac/web-projekat.git
code web-projekat
```

## Pokretanje Agar.io Multiplayer Igre

1. Instaliraj dependencies:
   ```sh
   npm install
   ```

2. Pokreni server:
   ```sh
   npm start
   ```

3. Otvori preglednik i idi na: `http://localhost:3000`

4. Unesi ime i klikni "PLAY"

## Features

- **Multiplayer sinhronizacija**: Igra se sinhronizuje preko više tabova/klijenata
- **Botovi**: AI botovi koji se kreću i jedu hranu
- **Leaderboard**: Prikazuje top 10 igrača po masi
- **Minimap**: Prikazuje cijelu mapu sa pozicijama svih igrača
- **Kamera**: Slijedi igrača sa zoom-om baziranim na masi
- **Hrana**: Male čestice koje povećavaju masu
- **Kretanje**: Mišem kontroliraš pravac kretanja

## Kontrole

- **Miš**: Pomicanje kursora mijenja pravac kretanja
- **Zoom**: Automatski se prilagođava veličini tvog kruga

## Tehničke detalji

- Server: Node.js sa WebSocket-ima
- Front-end: HTML5 Canvas sa JavaScript-om
- Sinhronizacija: Real-time preko WebSocket protokola
- Svijet: 4000x4000 jedinica
- 60 FPS game loop
