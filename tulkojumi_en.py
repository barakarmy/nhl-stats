"""
Angļu tulkojumi NHL stats lietotnei: {"latviešu teksts": "English text"}. Izmanto i18n.py (sk. paskaidrojumu tur).

- Atslēga ir latviešu teksts tieši tāds, kāds tas ir kodā (atstarpes un rindu pārnesumi nav svarīgi).
- {} – mainīga daļa (skaitlis, komanda, vārds). Angliski var lietot {0}, {1}, ja secība mainās.
- {:%d.%m} u.tml. – datums; angliski tas automātiski kļūst "Nov 12" (laiks paliek Rīgas laikā).
- Ja latviešu teksts kodā tiek mainīts, jāmaina arī atslēga šeit (citādi angliski paliks latviskais teksts).
- Jauns teksts lietotnē → pievieno rindu. Neiztulkotie teksti: atver lapu ar ?i18n=1 (saraksts lapas apakšā).
"""

EN = {
    # ===== app.py =====
    'Parole nav iestatīta. Streamlit Cloud → App settings → Secrets pievieno rindu: APP_PASSWORD = "tava_parole" un spied Save changes (izmaiņas stājas spēkā aptuveni minūtes laikā).':
        'Password is not set. In Streamlit Cloud → App settings → Secrets add the line: APP_PASSWORD = "your_password" and press Save changes (it takes effect in about a minute).',
    'Karstākie spēlētāji':
        'Hot players',
    'Komandas':
        'Teams',
    'Līgas pārskats':
        'Standings',
    'Salīdzināt komandas':
        'Compare teams',
    'Komandas statistika':
        'Team stats',
    'Periodi':
        'Periods',
    'Forma un vārti':
        'Form & goals',
    'Vairāk / Mazāk':
        'Over / Under',
    'Vairākums':
        'Power play',
    'Mazākums':
        'Penalty kill',
    'Noraidījumi':
        'Penalties',
    'Back to Back':
        'Back to Back',
    'back-to-back':
        'back-to-back',
    'Spēlētāji un tiesneši':
        'Players & referees',
    'Spēlētāji':
        'Players',
    'Tiesneši':
        'Referees',
    'Kalendārs':
        'Schedule',
    'Rezultāti':
        'Results',
    'vidējais ({})':
        'average ({})',
    'Iepriekšējā ielādē: {}':
        'Previous load: {}',
    'Koeficienti · {} · pamatlaiks{}':
        'Odds · {} · regulation{}',
    'Pamatlaika 1X2 koeficientu vēl nav':
        'No regulation 1X2 odds yet',
    'Pinnacle šai līnijai nav – vidējais no bukmeikeriem':
        'No Pinnacle line for this market – bookmaker average',
    'vid.':
        'avg.',
    '{} pamatlaikā':
        '{} in regulation',
    'Neizšķirts':
        'Draw',
    '{} ar OT':
        '{} incl. OT',
    'Paslēpt ▴':
        'Hide ▴',
    'Vairāk līniju ▾':
        'More lines ▾',
    'Labākais':
        'Best',
    '±1.5 un totāli parasti ietver papildlaiku. Taisnīgās varbūtības – bez bukmeikera uzcenojuma.':
        '±1.5 and totals usually include overtime. Fair probabilities – without the bookmaker margin.',
    'repozitorijā ir vecs tiesnesi_planotie.py (augšupielādē jauno), tiešsaistes pārbaude nedarbojas':
        'the repository has an old tiesnesi_planotie.py (upload the new one), the live check does not work',
    'Scouting The Refs neatbildēja laikā, rādīti tiesneši no datu faila':
        'Scouting The Refs did not respond in time, showing referees from the data file',
    'Scouting The Refs nav sasniedzams ({} pieprasījumi neizdevās)':
        'Scouting The Refs is unreachable ({} requests failed)',
    'Ielādēju datus…':
        'Loading data…',
    "Nav atrasts datu fails 'sezonas/speles.csv' (vai vecais 'nhl_sezona.csv'). Palaid nhl_dati.py un ieliec CSV failus repozitorijā.":
        "Data file 'sezonas/speles.csv' (or the old 'nhl_sezona.csv') not found. Run nhl_dati.py and add the CSV files to the repository.",
    'Visa sezona':
        'Full season',
    'Pēdējās 5':
        'Last 5',
    'Pēdējās 10':
        'Last 10',
    'Izbraukumā':
        'Away',
    'Viesos':
        'Away',
    'Nospēlētās spēles':
        'Games played',
    'loss (pamatlaikā)':
        'loss (in regulation)',
    'OT loss vai SO loss (komanda saņem 1 punktu)':
        'OT loss or SO loss (team gets 1 point)',
    'Punkti':
        'Points',
    'Tabulas punkti: win 2, OT loss / SO loss 1, loss 0':
        'Standings points: win 2, OT loss / SO loss 1, loss 0',
    'Punkti %':
        'Points %',
    'Iegūto punktu daļa no iespējamajiem: punkti / (2 × spēles)':
        'Share of possible points earned: points / (2 × games)',
    'Vārti/sp':
        'Goals/gm',
    'Vidēji gūtie vārti spēlē pamatlaikā (bez papildlaika un pēcspēles metieniem)':
        'Average goals scored per game in regulation (excluding overtime and shootouts)',
    'Ielaisti/sp':
        'Against/gm',
    'Vidēji ielaistie vārti spēlē pamatlaikā':
        'Average goals allowed per game in regulation',
    'Starpība':
        'Difference',
    'Gūto un ielaisto vārtu starpība pamatlaikā':
        'Goal difference in regulation (scored minus allowed)',
    'Metieni/sp':
        'Shots/gm',
    'Vidēji metieni vārtos (SOG) spēlē pamatlaikā (bez papildlaika)':
        'Average shots on goal (SOG) per game in regulation (excluding overtime)',
    'Metienu daļa %':
        'Shot share %',
    'Komandas metienu daļa pamatlaikā: SOG par / (SOG par + SOG pret), bez papildlaika':
        "Team's share of shots in regulation: SOG for / (SOG for + SOG against), excluding overtime",
    'Vairākuma (Power Play) efektivitāte pamatlaikā: vārti vairākumā / vairākuma iespējas, bez papildlaika':
        'Power play efficiency in regulation: power-play goals / power-play opportunities, excluding overtime',
    'Mazākuma (Penalty Kill) efektivitāte pamatlaikā: neielaisto vārtu daļa, kad komanda spēlē mazākumā, bez papildlaika':
        'Penalty kill efficiency in regulation: share of penalty kills without a goal allowed, excluding overtime',
    'Vidēji noraidījumu skaits spēlē (tikai minor sodi pamatlaikā; dubultais minor = 2; bez major, 10 min disciplinārajiem un kautiņiem)':
        'Average penalties per game (minor penalties in regulation only; double minor = 2; excluding majors, 10-min misconducts and fights)',
    'Forma (5)':
        'Form (5)',
    'Pēdējās 5 spēles (vecākā → jaunākā): zaļa = win, sarkana = loss, ar oranžu daļu = OT win / SO win vai OT loss / SO loss. Uzved uz bumbiņas, lai redzētu rezultātu un pretinieku':
        'Last 5 games (oldest → newest): green = win, red = loss, with an orange part = OT win / SO win or OT loss / SO loss. Hover over a ball to see the score and opponent',
    'Forma':
        'Form',
    'Pēdējās spēles (vecākā → jaunākā): zaļa = win, sarkana = loss, ar oranžu daļu = OT win / SO win vai OT loss / SO loss. Uzved uz bumbiņas, lai redzētu rezultātu un pretinieku':
        'Recent games (oldest → newest): green = win, red = loss, with an orange part = OT win / SO win or OT loss / SO loss. Hover over a ball to see the score and opponent',
    'Gūti vārti':
        'Goals for',
    'Pēdējās izvēlētajās spēlēs gūtie vārti pamatlaikā (kopā)':
        'Goals scored in regulation in the selected recent games (total)',
    'Ielaisti vārti':
        'Goals against',
    'Pēdējās izvēlētajās spēlēs ielaistie vārti pamatlaikā (kopā)':
        'Goals allowed in regulation in the selected recent games (total)',
    'Gūti':
        'For',
    'Šajā periodā gūtie vārti (kopā)':
        'Goals scored in this period (total)',
    'Ielaisti':
        'Against',
    'Šajā periodā ielaistie vārti (kopā)':
        'Goals allowed in this period (total)',
    'Spēļu daļa (%), kurās abu komandu vārtu summa pamatlaikā pārsniedza izvēlēto līniju':
        'Share of games (%) where the combined goals of both teams in regulation exceeded the selected line',
    'Spēļu daļa (%), kurās abu komandu vārtu summa pamatlaikā bija zemāka par izvēlēto līniju':
        'Share of games (%) where the combined goals of both teams in regulation were below the selected line',
    'Vid. vārti spēlē':
        'Avg. goals per game',
    'Vidējā abu komandu vārtu summa spēlē pamatlaikā':
        'Average combined goals of both teams per game in regulation',
    'PP vārti':
        'PP goals',
    'Vairākumā pamatlaikā gūtie vārti (bez papildlaika)':
        'Power-play goals in regulation (excluding overtime)',
    'PP iespējas':
        'PP opportunities',
    'Vairākuma iespējas pamatlaikā (reizes, kad komanda spēlēja vairākumā), bez papildlaika':
        'Power-play opportunities in regulation (times the team played with the man advantage), excluding overtime',
    'PP metieni':
        'PP shots',
    'Metieni vārtos vairākumā pamatlaikā (bez papildlaika)':
        'Power-play shots on goal in regulation (excluding overtime)',
    'Ielaisti PP':
        'PP against',
    'Pretinieka vairākumā pamatlaikā gūtie vārti pret šo komandu':
        "Goals allowed to the opponent's power play in regulation",
    'Izcīnīti − saņemti':
        'Drawn − taken',
    'Izcīnīto un saņemto noraidījumu starpība spēlē; pozitīvs skaitlis = komanda izcīna vairāk, nekā saņem':
        'Penalties drawn minus penalties taken per game; positive = the team draws more than it takes',
    'Metieni':
        'Shots',
    'Metieni vārtos visā spēlē (arī papildlaikā, tikai informācijai): komanda–pretinieks':
        'Shots on goal for the whole game (incl. overtime, for information only): team–opponent',
    'Komandas noraidījumu skaits spēlē (tikai minor sodi pamatlaikā; dubultais minor = 2; bez major, 10 min disciplinārajiem un kautiņiem)':
        'Team penalties per game (minor penalties in regulation only; double minor = 2; excluding majors, 10-min misconducts and fights)',
    'Minor sodu minūtes spēlē (pamatlaikā; bez major, 10 min disciplinārajiem un kautiņiem)':
        'Minor penalty minutes per game (in regulation; excluding majors, 10-min misconducts and fights)',
    'Mājās':
        'Home',
    'Vārtu starpība šajā periodā mājas spēlēs':
        'Goal difference in this period in home games',
    'Vārtu starpība šajā periodā viesu spēlēs':
        'Goal difference in this period in away games',
    'Vārtu starpība šajā periodā pēdējās 10 spēlēs':
        'Goal difference in this period in the last 10 games',
    '🔥🔥 = ļoti karsts (indekss ≥ 3), 🔥 = karsts (indekss ≥ 2)':
        '🔥🔥 = very hot (index ≥ 3), 🔥 = hot (index ≥ 2)',
    'Sp. logā':
        'GP in window',
    'Spēļu skaits izvēlētajā logā (pēdējās N spēles; ja spēlētājs nospēlējis mazāk, visas viņa spēles)':
        'Games in the selected window (last N games; if the player has played fewer, all of his games)',
    'Sērija':
        'Streak',
    'Spēles pēc kārtas (skaitot no jaunākās), kurās spēlētājs guvis vismaz vienu izvēlēto rādītāju':
        'Consecutive games (counting from the most recent) in which the player recorded at least one of the selected stat',
    'Sezona īsumā':
        'Season at a glance',
    'Sezonas kopsavilkums: spēles, vārti (G), piespēles (A), punkti (P), metieni vārtos':
        'Season summary: games, goals (G), assists (A), points (P), shots on goal',
    'Kāpēc karsts':
        'Why hot',
    'Automātisks īss paskaidrojums: rezultāts logā, sērija, metieni un šaušanas %, laiks laukumā':
        'Automatic short explanation: output in the window, streak, shots and shooting %, ice time',
    'Laiks (Rīga)':
        'Time (Riga)',
    'Spēles sākuma laiks pēc Rīgas laika':
        'Game start time, Riga time',
    'Galvenie tiesneši':
        'Referees',
    'Spēlei piešķirtie galvenie tiesneši (NHL tos paziņo dažas stundas pirms spēles)':
        'Referees assigned to the game (the NHL announces them a few hours before the game)',
    'Spēles šosezon':
        'Games this season',
    'Spēles, kurās tiesnesis šosezon ir strādājis':
        'Games the referee has worked this season',
    'Kombinētais':
        'Combined',
    'Kombinētais rādītājs: 60% iepriekšējās sezonas (DB) + 40% šī sezona (svarus var mainīt iestatījumos); katra daļa tiek pievilkta pie līgas vidējā, ja spēļu ir maz':
        'Combined rating: 60% previous seasons (DB) + 40% this season (weights can be changed in the settings); each part is pulled toward the league average when there are few games',
    'Pret līgu':
        'Vs league',
    'Kombinētā rādītāja starpība pret kombinēto līgas vidējo; pozitīvs = tiesnesis soda vairāk par vidējo':
        'Combined rating minus the combined league average; positive = the referee calls more than average',
    'Mājas komanda':
        'Home team',
    'Kombinētie noraidījumi mājas komandai spēlē':
        'Combined penalties per game for the home team',
    'Viesu komanda':
        'Away team',
    'Kombinētie noraidījumi viesu komandai spēlē':
        'Combined penalties per game for the away team',
    'Noraid. mājas':
        'Pen. home',
    'Mājas komandas noraidījumi spēlē':
        'Home team penalties in the game',
    'Viesu komandas noraidījumi spēlē':
        'Away team penalties in the game',
    'Kopā':
        'Total',
    'Abu komandu noraidījumi kopā spēles pamatlaikā':
        'Penalties of both teams combined in regulation',
    'Periods (OT = papildlaiks, SO = pēcspēles metieni)':
        'Period (OT = overtime, SO = shootout)',
    'Laiks periodā, kad gūti vārti':
        'Time in the period when the goal was scored',
    'Piespēles':
        'Assists',
    'Piespēļu autori':
        'Assisted by',
    'Situācija':
        'Situation',
    'EV = vienāds sastāvs, PP = vairākums, SH = mazākums':
        'EV = even strength, PP = power play, SH = shorthanded',
    'Rez. pēc vārtiem':
        'Score after goal',
    'Rezultāts pēc šiem vārtiem (viesi–mājinieki)':
        'Score after this goal (away–home)',
    'Vārti':
        'Goals',
    'Punkti (vārti + piespēles)':
        'Points (goals + assists)',
    'TOI spēlē':
        'TOI',
    'Laiks laukumā šajā spēlē (mm:ss)':
        'Time on ice in this game (mm:ss)',
    'Atvairīti':
        'Saves',
    'Atvairītie metieni':
        'Shots saved',
    'Metieni pret':
        'Shots against',
    'Metieni pret vārtsargu šajā spēlē':
        'Shots against the goalie in this game',
    'Atvairīto metienu procents: atvairītie / metieni pret':
        'Save percentage: saves / shots against',
    'Iznākums':
        'Outcome',
    'Pozīcija: C centrs, L/R spārni, D aizsargs':
        'Position: C center, L/R wings, D defenseman',
    'Plus/mīnus: komandas gūtie mīnus ielaistie vārti, kamēr spēlētājs bija laukumā vienāda sastāva spēlē':
        'Plus/minus: team goals for minus goals against while the player was on the ice at even strength',
    'Sodu minūtes':
        'Penalty minutes',
    'Metieni vārtos':
        'Shots on goal',
    'Bloķētie pretinieka metieni':
        'Opponent shots blocked',
    'Vārti vairākumā':
        'Power-play goals',
    'Vidējais laiks laukumā spēlē (minūtes)':
        'Average time on ice per game (minutes)',
    'TOI_kopa':
        'TOI_kopa',
    'Kopējais laiks laukumā (minūtes)':
        'Total time on ice (minutes)',
    'Punkti spēlē':
        'Points per game',
    'Spēles sākuma sastāvā':
        'Games started',
    'win (arī OT win un SO win)':
        'win (incl. OT win and SO win)',
    'Metieni pret vārtsargu':
        'Shots against the goalie',
    'Ielaistie vārti':
        'Goals allowed',
    'Ielaisto vārtu vidējais skaits 60 minūtēs':
        'Average goals allowed per 60 minutes',
    'lielāka':
        'higher',
    'mazāka':
        'lower',
    'Spēles, kurās abu komandu vārtu summa pamatlaikā bija {} par {}':
        'Games where the combined goals of both teams in regulation were {} than {}',
    'Nav datu šim skatam.':
        'No data for this view.',
    'Komanda':
        'Team',
    '{} {} ✓ apstiprināts':
        '{} {} ✓ confirmed',
    '{} {} (gaidāms)':
        '{} {} (expected)',
    '{} {} ~{}% pēc rotācijas':
        '{} {} ~{}% by rotation',
    'vārtsargi: {}':
        'goalies: {}',
    'vārtsargu ietekme: {} vārti {}, {} vārti {}':
        'goalie impact: {} goals {}, {} goals {}',
    '{}: otrā spēle pēc kārtas':
        '{}: second game in a row',
    '{}: garš ceļš':
        '{}: long trip',
    'tiesneši: noraidījumi {}':
        'referees: penalties {}',
    'Vidēja':
        'Medium',
    'Mazākais šīs sezonas spēļu skaits abām komandām: {}':
        'Fewest games played this season by either team: {}',
    '{:%d.%m(%H:%M)} ·':
        '{} ·',
    'ticamība: {}':
        'confidence: {}',
    'Pamatlaikā':
        'Regulation',
    'Uzvarētājs ar OT':
        'Winner incl. OT',
    'Gaidāmie vārti':
        'Expected goals',
    'kopā {}':
        'total {}',
    'Totāls 5.5':
        'Total 5.5',
    'Totāls {}':
        'Total {}',
    'Papildlaiks (jā / nē)':
        'Overtime (yes / no)',
    '{}. periods':
        'Period {}',
    'periodi':
        'periods',
    'Noraidījumi (minor, pamatlaiks)':
        'Penalties (minor, regulation)',
    'Gaidāmie:':
        'Expected:',
    '({} {} · {} {}; līgā šosezon vidēji {} spēlē){}':
        '({} {} · {} {}; league average this season {} per game){}',
    'Noraidījumi {}':
        'Penalties {}',
    'Visi tirgi ▾':
        'All markets ▾',
    'Vārti (pamatlaiks)':
        'Goals (regulation)',
    'Neizšķirts pamatlaikā':
        'Draw in regulation',
    'Ticamākie rezultāti: {}':
        'Most likely scores: {}',
    'Periodi: over (gaidāmie vārti)':
        'Periods: over (expected goals)',
    'Tirgus pamatlaikā: {}':
        'Market, regulation: {}',
    'Over {} (ar OT): tirgus {}%, modelis {}%':
        'Over {} (incl. OT): market {}%, model {}%',
    'Tirgus varbūtības no Pinnacle koeficientiem bez uzcenojuma; iekavās – modelis mīnus tirgus, procentpunktos':
        'Market probabilities from Pinnacle odds without the margin; in brackets – model minus market, in percentage points',
    'Arhīvs vēl ir tukšs. Tas sāks krāties pēc koeficientu ielādēm (3× dienā): katrā ielādē tiek saglabātas modeļa prognozes un tā brīža koeficienti, lai vēlāk godīgi salīdzinātu ar rezultātiem.':
        "The archive is still empty. It will start filling after odds loads (3× a day): each load saves the model's predictions and the odds at that moment, so they can later be compared fairly with the results.",
    'Arhīvā: {} spēles ar prognozēm, no tām aizvadītas un novērtējamas: {}.':
        'In the archive: {} games with predictions, of which finished and gradable: {}.',
    'Tikai {} spēles – rezultāti vēl ir ļoti nejauši. Ticamus secinājumus var izdarīt pēc ~200–300 spēlēm.':
        'Only {} games – the results are still very random. Reliable conclusions can be drawn after ~200–300 games.',
    '**Precizitāte 1X2 pamatlaikā** (log loss, mazāk = labāk): modelis **{}** · tirgus rītā (Pinnacle vai labākie ES koef.) **{}** · tirgus pirms spēles **{}** · modelis un tirgus uz pusēm **{}**.':
        '**Regulation 1X2 accuracy** (log loss, lower = better): model **{}** · morning market (Pinnacle or best EU odds) **{}** · market before the game **{}** · model and market 50/50 **{}**.',
    'Tirgus':
        'Market',
    'Starpība ≥':
        'Edge ≥',
    'Likmes':
        'Bets',
    'Uzvaras %':
        'Win %',
    'ROI labākais %':
        'ROI best %',
    'Pārspēj noslēgumu %':
        'Beats closing %',
    'Simulētā likme tiek “likta”, ja modeļa varbūtība × rīta koeficients − 1 ir vismaz tik liela':
        'A simulated bet is “placed” if model probability × morning odds − 1 is at least this large',
    'Peļņa uz likmi (vienādas likmes) ar Pinnacle rīta koeficientiem (1X2 – labākie ES koeficienti, jo Pinnacle 1X2 nedod)':
        'Profit per bet (flat stakes) at Pinnacle morning odds (1X2 – best EU odds, as Pinnacle does not offer 1X2)',
    'Tas pats ar labāko rīta koeficientu starp ES bukmeikeriem':
        'The same at the best morning odds among EU bookmakers',
    'Cik rīta koeficients bija labāks par pēdējo zināmo pirms spēles: + nozīmē, ka tirgus pēc tam pagājās modeļa virzienā':
        "How much better the morning odds were than the last known before the game: + means the market later moved in the model's direction",
    'Cik % likmju rīta koeficients bija augstāks par pēdējo pirms spēles':
        'Share of bets (%) where the morning odds were higher than the last before the game',
    'Svarīgākais rādītājs ir CLV: ja tas ilgtermiņā ir pozitīvs, modelis atrod informāciju, ko tirgus vēl nav ievērtējis. ROI uz maziem paraugiem ir ļoti nejaušs. Tā ir simulācija, nevis ieteikums likt likmes.':
        'The most important metric is CLV: if it is positive in the long run, the model finds information the market has not yet priced in. ROI on small samples is very random. This is a simulation, not a betting recommendation.',
    'labākais (ES)':
        'best (EU)',
    'Algoritma iestatījumi (tikai šim skatam)':
        'Algorithm settings (this view only)',
    'Likme tiek ieteikta tikai, ja sagaidāmā vērtība ir vismaz tik liela (p × koef − 1). Ja nepārvieto – katram tirgum tiek lietots vēsturiskajā pārbaudē izvēlētais slieksnis':
        'A bet is suggested only if the expected value is at least this large (p × odds − 1). If not moved – each market uses the threshold chosen in the historical backtest',
    'Min. varbūtība %':
        'Min. probability %',
    'Izslēdz “brīnumus”: izvēles ar mazu modeļa varbūtību (liela dispersija)':
        'Excludes “miracles”: picks with a low model probability (high variance)',
    'Max. atšķirība no tirgus (pp)':
        'Max. difference from market (pp)',
    'Ja modelis ļoti nesaskan ar asāko tirgu (Pinnacle bez uzcenojuma), visticamāk modelis kaut ko nezina':
        'If the model strongly disagrees with the sharpest market (Pinnacle without margin), the model most likely does not know something',
    'Kelly daļa':
        'Kelly fraction',
    'Daļa no pilnā Kelly (¼ = 0.25 – profesionāļu standarts, mazina svārstības un modeļa kļūdu ietekmi)':
        'Fraction of full Kelly (¼ = 0.25 – the professional standard, reduces swings and the impact of model errors)',
    'Max. likme % bankrola':
        'Max. stake % of bankroll',
    'Ja nepārvieto – katram tirgum tiek lietots vēsturiskās pārbaudes limits (novērošanas režīmā 2 %)':
        'If not moved – each market uses the backtest limit (2 % in observation mode)',
    'Max. picks vienā spēlē':
        'Max. picks per game',
    '1X2, ar OT un ±1.5 uz to pašu komandu ir korelētas likmes – parasti tikai viena katrā spēlē':
        '1X2, incl. OT and ±1.5 on the same team are correlated bets – usually only one per game',
    'Modeļa svars (uzvarētājs)':
        'Model weight (winner)',
    '1X2, uzvarētājs ar OT un ±1.5: lēmuma varbūtība = svars × modelis + (1 − svars) × tirgus. 1.0 = tikai modelis, 0.5 = puse modelis, puse tirgus. Ja nepārvieto – tiek lietots vēsturiskajā pārbaudē izvēlētais svars katram tirgum':
        '1X2, winner incl. OT and ±1.5: decision probability = weight × model + (1 − weight) × market. 1.0 = model only, 0.5 = half model, half market. If not moved – the weight chosen in the backtest is used for each market',
    'Noklusējumā – tirgi, kas vēsturiskajā pārbaudē bija pelnoši (ja pārbaude veikta)':
        'By default – markets that were profitable in the historical backtest (if a backtest was run)',
    'Tikai ar paziņotiem sākuma vārtsargiem':
        'Only with announced starting goalies',
    'Pick tiek atlasīts tikai, kad abu komandu vārtsargi ir Confirmed / Expected (tā strādā arī vēsture)':
        "A pick is selected only when both teams' goalies are Confirmed / Expected (the history works the same way)",
    '(nav paziņots)':
        '(not announced)',
    '(gaidāms)':
        '(expected)',
    'Vārtsargi: {}':
        'Goalies: {}',
    'Varbūtība, pēc kuras rēķināts EV un likme: tikai modelis':
        'Probability used for EV and stake: model only',
    'Varbūtība, pēc kuras rēķināts EV un likme: {}% modelis + {}% tirgus':
        'Probability used for EV and stake: {}% model + {}% market',
    'Expected Value: p × (koef − 1) − (1 − p)':
        'Expected Value: p × (odds − 1) − (1 − p)',
    'Puasona modeļa varbūtība':
        'Poisson model probability',
    'Tirgus taisnīgā varbūtība ({} bez uzcenojuma)':
        'Market fair probability ({} without margin)',
    '¼ Kelly × ticamība, robežās 1–5 % bankrola':
        '¼ Kelly × confidence, within 1–5 % of bankroll',
    'Modelis':
        'Model',
    'Lēmums':
        'Decision',
    'Likme':
        'Stake',
    'Implied {}% · ticamība: {} · Kelly (pilns) {}% · {} no {} vien.{}':
        'Implied {}% · confidence: {} · Kelly (full) {}% · {} of {} u.{}',
    '· ✓ saglabāts vēsturē':
        '· ✓ saved to history',
    'Vēsturiskajā pārbaudē neviens tirgus nebija pelnošs – algoritms šobrīd picks neiesaka (skat. Vēsture → Vēsturiskā pārbaude).':
        'No market was profitable in the historical backtest – the algorithm does not suggest picks right now (see History → Historical backtest).',
    'Šobrīd nav nesāktu spēļu ar koeficientiem. Koeficienti tiek ielādēti 3× dienā (~09:00, ~16:30, ~23:00) 3 dienas uz priekšu.':
        'There are currently no upcoming games with odds. Odds are loaded 3× a day (~09:00, ~16:30, ~23:00) for 3 days ahead.',
    'der, bet gaida':
        'qualifies, but waiting',
    '· koeficienti: {:%d.%m %H:%M}':
        '· odds: {}',
    'Spēles ar koeficientiem':
        'Games with odds',
    'novērtētas {} izvēles{}':
        '{} picks evaluated{}',
    'Ar pietiekamu vērtību':
        'With enough value',
    'izturēja visus filtrus · vēl {} gaida vārtsargus':
        'passed all filters · {} more waiting for goalies',
    'izturēja visus filtrus':
        'passed all filters',
    'pēc korelācijas filtra (spēlē)':
        'after the correlation filter (per game)',
    'Kopējā likme':
        'Total stake',
    'bankrola · {} no {} vien.':
        'of bankroll · {} of {} u.',
    'Šobrīd neviena izvēle neiztur filtrus – tas ir normāli: profesionāls spēlētājs liek likmes tikai tad, kad ir vērtība. Iemeslus var redzēt zemāk.':
        'Right now no pick passes the filters – that is normal: a professional bettor only bets when there is value. The reasons are shown below.',
    'Visas novērtētās izvēles ({}) un kāpēc tās netika izvēlētas':
        'All evaluated picks ({}) and why they were not selected',
    'der (cits pick šajā spēlē)':
        'qualifies (another pick in this game)',
    'Spēle':
        'Game',
    'Izvēle':
        'Pick',
    'Koef.':
        'Odds',
    'Modelis %':
        'Model %',
    'Lēmums %':
        'Decision %',
    'Tirgus %':
        'Market %',
    'Taisnīgā varbūtība no Pinnacle (vai vidējiem) koeficientiem bez uzcenojuma':
        'Fair probability from Pinnacle (or average) odds without the margin',
    '✓ pick – ieteiktā likme; citādi – kāpēc izvēle netika ieteikta':
        '✓ pick – suggested bet; otherwise – why the pick was not suggested',
    'Varbūtība, pēc kuras rēķināts EV: 1X2, ar OT un ±1.5 – modelis pievilkts pie tirgus (svars iestatījumos), totāliem – modelis':
        'Probability used for EV: 1X2, incl. OT and ±1.5 – model pulled toward the market (weight in settings), totals – model',
    'Sagaidāmā vērtība ar labāko derīgo koeficientu: p × (koef − 1) − (1 − p), p – lēmuma varbūtība':
        'Expected value at the best available odds: p × (odds − 1) − (1 − p), p – decision probability',
    'Kā tiek atlasīti picks':
        'How picks are selected',
    '1. **Implied probability** = 1 / koeficients – ko paredz bukmeikers (ar uzcenojumu). **Tirgus taisnīgā varbūtība** – Pinnacle (asākais tirgus) koeficienti bez uzcenojuma; ja Pinnacle nav – vidējais.\n2. **Koeficients likmei** – labākais ES bukmeikeru koeficients, bet ne vairāk kā +10 % virs Pinnacle (lielāka atšķirība parasti ir novecojis koeficients).\n3. **Lēmuma varbūtība** p = svars × modelis + (1 − svars) × tirgus: uzvarētāja tirgiem (1X2, ar OT, ±1.5) svars {} (modelis sistemātiski vērtē autsaiderus augstāk par tirgu; visi trīs nāk no tā paša vārtu sadalījuma), totāliem – tikai modelis. **EV** = p × (koef − 1) − (1 − p).\n4. **Filtri:** EV ≥ {}, varbūtība ≥ {}%, koeficients ≤ {}, modelis nedrīkst atšķirties no tirgus vairāk par {} pp (tad visticamāk modelis kaut ko nezina – traumas, sastāvs) un tam jābūt optimistiskākam par taisnīgo tirgu.\n5. **Vārtsargi:** pick tiek atlasīts tikai, kad abu komandu sākuma vārtsargi ir paziņoti (Confirmed / Expected). Kad vārtsargi tiek paziņoti, darbplūsma ielādē jaunus koeficientus un picks tiek pārrēķināti.\n6. **Korelācija:** vienā spēlē tikai viena izvēle (ar lielāko EV).\n7. **Likme:** Kelly f* = (p × koef − 1) / (koef − 1); tiek likts ¼ Kelly × ticamība (Augsta 1 / Vidēja 0.75 / Zema 0.5), robežās {}–{}% bankrola (novērošanas režīmā esošam tirgum max {}%); vienā dienā kopā ne vairāk par {}%.\n\nVēsture tiek krāta automātiski (darbplūsma “NHL Odds”, 3× dienā) ar standarta iestatījumiem; iestatījumi augstāk maina tikai šo skatu.':
        "1. **Implied probability** = 1 / odds – what the bookmaker predicts (with margin). **Market fair probability** – Pinnacle (the sharpest market) odds without the margin; if Pinnacle is missing – the average.\n2. **Odds for the bet** – the best EU bookmaker odds, but no more than +10 % above Pinnacle (a bigger gap is usually stale odds).\n3. **Decision probability** p = weight × model + (1 − weight) × market: for winner markets (1X2, incl. OT, ±1.5) the weight is {} (the model systematically rates underdogs higher than the market; all three come from the same goal distribution), for totals – model only. **EV** = p × (odds − 1) − (1 − p).\n4. **Filters:** EV ≥ {}, probability ≥ {}%, odds ≤ {}, the model must not differ from the market by more than {} pp (then the model most likely does not know something – injuries, lineup) and it must be more optimistic than the fair market.\n5. **Goalies:** a pick is selected only when both teams' starting goalies are announced (Confirmed / Expected). When goalies are announced, the workflow loads new odds and the picks are recalculated.\n6. **Correlation:** only one pick per game (the one with the highest EV).\n7. **Stake:** Kelly f* = (p × odds − 1) / (odds − 1); the stake is ¼ Kelly × confidence (High 1 / Medium 0.75 / Low 0.5), within {}–{}% of the bankroll (max {}% for a market in observation mode); no more than {}% in total per day.\n\nThe history is collected automatically (workflow “NHL Odds”, 3× a day) with the standard settings; the settings above only change this view.",
    'Picks ir matemātisks novērtējums, nevis garantija vai ieteikums likt likmes. Ticamus secinājumus par algoritmu var izdarīt tikai pēc vairākiem simtiem likmju (skat. Vēsture – īpaši CLV).':
        'Picks are a mathematical estimate, not a guarantee or a recommendation to bet. Reliable conclusions about the algorithm can only be drawn after several hundred bets (see History – especially CLV).',
    'Bankrola līkne':
        'Bankroll curve',
    'Zaudējums':
        'Loss',
    'SĀKUMS':
        'START',
    '#{} · {:%d.%m %H:%M}':
        '#{} · {}',
    '@ {} · likme {}%':
        '@ {} · stake {}%',
    '{} · {} vien.':
        '{} · {} u.',
    'Vēsture vēl ir tukša. Picks tiek saglabāti automātiski pēc katras koeficientu ielādes (3× dienā), un rezultāti tiem tiek pievienoti, tiklīdz spēle ir aizvadīta.':
        'The history is still empty. Picks are saved automatically after every odds load (3× a day), and results are added as soon as the game is over.',
    'Visi':
        'All',
    'Izšķirti':
        'Settled',
    'Picks (izšķirti)':
        'Picks (settled)',
    'Trāpījumi':
        'Hits',
    'vidēji lēmuma varbūtība {}% · koef. {}':
        'average decision probability {}% · odds {}',
    'ROI (vienādas likmes)':
        'ROI (flat stakes)',
    '{} vien. · vidējais EV {}%':
        '{} u. · average EV {}%',
    'no {} · {} vien. ({}% no likmēm)':
        'of {} · {} u. ({}% of stakes)',
    'pozitīvs {}% picks · koef. pret tirgu pirms spēles':
        'positive in {}% of picks · odds vs market before the game',
    'Tikai {} izšķirtas likmes – ROI vēl ir ļoti nejaušs (svārstības ±{}%). Ticamākais agrīnais rādītājs ir CLV: vai mūsu koeficients bija labāks par tirgus taisnīgo koeficientu tieši pirms spēles.':
        "Only {} settled bets – ROI is still very random (swings ±{}%). The most reliable early indicator is CLV: whether our odds were better than the market's fair odds right before the game.",
    'Izšķirtu picks vēl nav · gaida rezultātu: {}':
        'No settled picks yet · waiting for a result: {}',
    'Vid. EV %':
        'Avg. EV %',
    'Šajā atlasē picks nav.':
        'No picks in this selection.',
    'Likme %':
        'Stake %',
    'Rezultāts':
        'Result',
    'Peļņa (vien.)':
        'Profit (u.)',
    'Likme, ko algoritms atlasīja (saglabāta pirms spēles, vēlāk netiek mainīta)':
        'The bet the algorithm selected (saved before the game, not changed later)',
    'Koeficients atlases brīdī (labākais derīgais ES bukmeikeru koeficients)':
        'Odds at the time of selection (best available EU bookmaker odds)',
    'Varbūtība, pēc kuras tika rēķināts EV un likme (1X2, ar OT, ±1.5 – modelis pievilkts pie tirgus)':
        'Probability used for EV and stake (1X2, incl. OT, ±1.5 – model pulled toward the market)',
    'Sagaidāmā vērtība atlases brīdī':
        'Expected value at the time of selection',
    'Bankrola daļa (¼ Kelly × ticamība, 1–5 %)':
        'Share of bankroll (¼ Kelly × confidence, 1–5 %)',
    'W – uzvara, L – zaudējums, P – naudas atgriešana; totāli un ±1.5 – pilnā spēle ar OT/SO, 1X2 – pamatlaiks':
        'W – win, L – loss, P – push (stake returned); totals and ±1.5 – full game incl. OT/SO, 1X2 – regulation',
    'Spēles gala rezultāts (mājinieki:viesi); saite uz protokolu':
        'Final score (home:away); link to the game summary',
    'Peļņa vienībās ar Kelly likmi (bankrols {})':
        'Profit in units with the Kelly stake (bankroll {})',
    'Mūsu koeficients pret tirgus taisnīgo koeficientu pēdējā ielādē pirms spēles: + = pārspējām noslēguma līniju':
        "Our odds vs the market's fair odds at the last load before the game: + = we beat the closing line",
    'Lejupielādēt vēsturi (CSV)':
        'Download history (CSV)',
    'Vēsturiskā pārbaude vēl nav veikta. Lokāli: `python vesturiskie_koef.py` (iepriekšējo sezonu koeficienti), tad `python picks.py --parbaude` → `sezonas/vesture/picks_parametri.json` (augšupielādē GitHub). Līdz tam tiek lietoti noklusējuma iestatījumi, kas nav pārbaudīti pret vēsturi.':
        "The historical backtest has not been run yet. Locally: `python vesturiskie_koef.py` (previous seasons' odds), then `python picks.py --parbaude` → `sezonas/vesture/picks_parametri.json` (upload to GitHub). Until then default settings are used that have not been tested against history.",
    'Parametri izvēlēti uz **{}**, godīgi pārbaudīti uz **{}** (katra spēle prognozēta tikai no datiem pirms tās). Koeficienti: {}. Izveidots: {}.':
        'Parameters chosen on **{}**, tested out-of-sample on **{}** (each game predicted only from data before it). Odds: {}. Created: {}.',
    'Bez noplūdes: modeļa iestatījumi – {}; xG modelis – {}. Pārbaudes sezona netika izmantota ne parametru izvēlē, ne modeļa kalibrēšanā.':
        'No leakage: model settings – {}; xG model – {}. The test season was used neither for parameter selection nor for model calibration.',
    '⚠ Pārbaudes sezona var būt daļēji izmantota modeļa kalibrēšanā ({}; xG – {}).':
        '⚠ The test season may have been partly used in model calibration ({}; xG – {}).',
    'izslēgts':
        'off',
    'izslēgts – {}':
        'off – {}',
    'novērošana':
        'observation',
    '✓ ieslēgts':
        '✓ on',
    '◐ novērošana (max 2 % likme)':
        '◐ observation (max 2 % stake)',
    'Modeļa svars':
        'Model weight',
    'Apmācība: likmes':
        'Training: bets',
    'Apmācība: ROI %':
        'Training: ROI %',
    'Pārbaude: likmes':
        'Test: bets',
    'Pārbaude: ROI %':
        'Test: ROI %',
    'Kopā: ROI %':
        'Total: ROI %',
    'Lēmuma varbūtība = svars × modelis + (1 − svars) × tirgus':
        'Decision probability = weight × model + (1 − weight) × market',
    'Vienādas likmes ar noslēguma koeficientiem sezonās, uz kurām izvēlēti parametri':
        'Flat stakes at closing odds in the seasons used to choose the parameters',
    'Tas pats jaunākajā sezonā, kas parametru izvēlē netika izmantota (godīgais rezultāts)':
        'The same in the latest season, which was not used for parameter selection (the honest result)',
    'Standartkļūda: ROI nejaušības robeža – ja ROI ir mazāks par to, rezultāts var būt nejaušs':
        'Standard error: the ROI randomness margin – if ROI is smaller than this, the result may be random',
    'Visas sezonas kopā (informācijai; optimistisks, jo apmācības daļā iestatījumi izvēlēti kā labākie)':
        'All seasons together (for information; optimistic, because the settings were chosen as the best on the training part)',
    '✓ ieslēgts – pelnošs abos posmos un pārbaudes sezonā ROI > 1 standartkļūda; ◐ novērošana – pelnošs abos posmos, bet vēl ne drošs, likmes max 2 %':
        '✓ on – profitable in both stages and test-season ROI > 1 standard error; ◐ observation – profitable in both stages but not yet reliable, stakes max 2 %',
    'Pilns algoritms pārbaudes sezonā (1 pick spēlē, ¼ Kelly): bankrols {} → {}, {} likmes, lielākais kritums {}%. 1X2 pamatlaikā vēsturē nav koeficientu – tas seko tirgum “Uzvarētājs (ar OT)”.':
        'Full algorithm in the test season (1 pick per game, ¼ Kelly): bankroll {} → {}, {} bets, max drawdown {}%. Regulation 1X2 has no historical odds – it follows the “Winner (incl. OT)” market.',
    'Vēsturiskajā pārbaudē neviens tirgus nebija pelnošs pret noslēguma koeficientiem – Picks vēsturē netiek krāti. Iestatījumos tirgus var ieslēgt skatam, bet ilgtermiņā tas nozīmē zaudējumu.':
        'No market was profitable against closing odds in the historical backtest – Picks are not being recorded in the history. A market can be switched on for this view in the settings, but in the long run that means a loss.',
    'Šai sadaļai vajag failu picks.py.':
        'This section needs the file picks.py.',
    'Vēsture':
        'History',
    'Aktuālie':
        'Current',
    'Vēsturiskā pārbaude (iepriekšējās sezonas)':
        'Historical backtest (previous seasons)',
    'Modelim vēl nav datu (ne šīs sezonas, ne DB).':
        'The model has no data yet (neither this season nor DB).',
    'Sadaļa':
        'Section',
    'Kā modelis strādā un cik tas precīzs':
        'How the model works and how accurate it is',
    '- **Komandu stiprums:** uzbrukums un aizsardzība no visām spēlēm, ņemot vērā pretinieku (svērta Puasona regresija). Šīs sezonas spēles sver vairāk, iepriekšējās sezonas (DB) – mazāk; sezonas sākumā prognoze balstās galvenokārt uz DB.\n- **Korekcijas:** mājas priekšrocība, otrā spēle pēc kārtas, garš ceļš, play-off, H2H (ja pārbaude rāda, ka tā uzlabo), tiesneši – noraidījumiem.\n- **xG (paredzamie vārti):** ja kalibrēšana to izvēlas, komandu stiprums tiek rēķināts no vārtu un paredzamo vārtu sajaukuma (metienu vieta, leņķis, veids, atlēcieni), un vārtsarga kvalitāte – kā ielaistie vārti pret paredzamajiem (GSAx).\n- **Sākuma vārtsargs:** kad komanda paziņo vārtsargu (✓ apstiprināts, “gaidāms” – ļoti ticams; pārbaude ik 30 min vakarā), modelis izmanto viņu; līdz tam – ticamo vārtsargu pēc rotācijas (komandas pēdējās 10 spēles; otrajā spēlē pēc kārtas biežāk sāk otrs vārtsargs) un viņa glābšanas % vienādos sastāvos (pievilkts pie līgas vidējā) salīdzinājumā ar komandas parasto vārtsargu sajaukumu. Ietekmes stiprumu nosaka kalibrēšana.\n- **Neizšķirti:** neizšķirtu iespēja pamatlaikā tiek pielāgota šīs sezonas līdzšinējam līmenim (ja kalibrēšana to izvēlas); no tās izriet arī tirgus “Papildlaiks jā/nē”.\n- **Visi tirgi** ir no vienas pamatlaika rezultātu matricas (ar neizšķirtu korekciju; gaidāmo vārtu kopsumma piesardzīgi pievilkta pie līgas vidējā, ja pārbaude to rāda); “ar OT” – neizšķirta gadījumā pēc vēstures. Koeficients = 1 / varbūtība (taisnīgais, bez bukmeikera uzcenojuma).':
        "- **Team strength:** attack and defense from all games, adjusted for the opponent (weighted Poisson regression). This season's games weigh more, previous seasons (DB) less; early in the season the prediction relies mainly on DB.\n- **Adjustments:** home advantage, second game in a row, long trip, playoffs, H2H (if the backtest shows it helps), referees – for penalties.\n- **xG (expected goals):** if calibration selects it, team strength is computed from a mix of goals and expected goals (shot location, angle, type, rebounds), and goalie quality – as goals allowed vs expected (GSAx).\n- **Starting goalie:** when a team announces its goalie (✓ confirmed, “expected” – very likely; checked every 30 min in the evening), the model uses him; until then – the likely goalie by rotation (the team's last 10 games; in the second game in a row the backup starts more often) and his even-strength save % (pulled toward the league average) compared with the team's usual goalie mix. The strength of the effect is set by calibration.\n- **Draws:** the chance of a draw in regulation is adjusted to this season's level so far (if calibration selects it); the “Overtime yes/no” market follows from it.\n- **All markets** come from one regulation score matrix (with the draw adjustment; the expected goal total is cautiously pulled toward the league average if the backtest shows it); “incl. OT” – in case of a draw, based on history. Odds = 1 / probability (fair, without the bookmaker margin).",
    '**Pārbaude pret vēsturi** ({}/{}, {} spēles, katra prognozēta tikai no datiem pirms tās): log loss 1X2 **{}** (bāze no iepriekšējo sezonu biežumiem {}; mazāk = labāk), totāls 5.5 **{}** (bāze {}); neizšķirti pamatlaikā {} prognoze / {} fakts; vidēji vārti {} / {}. H2H korekcija: {}. Kalibrēts: {}.':
        "**Backtest against history** ({}/{}, {} games, each predicted only from data before it): log loss 1X2 **{}** (baseline from previous seasons' frequencies {}; lower = better), total 5.5 **{}** (baseline {}); regulation draws {} predicted / {} actual; average goals {} / {}. H2H adjustment: {}. Calibrated: {}.",
    'tiek lietota':
        'in use',
    'Mājinieku uzvara (prognoze)':
        'Home win (prediction)',
    'Spēles':
        'Games',
    'Vidēji prognoze':
        'Avg. prediction',
    'Cik % no šīm spēlēm mājinieki tiešām uzvarēja pamatlaikā – jo tuvāk prognozei, jo labāk kalibrēts modelis':
        'Share of these games (%) the home team actually won in regulation – the closer to the prediction, the better calibrated the model',
    'Modelis vēl nav kalibrēts pret vēsturi (python modelis.py --kalibret), tiek lietoti noklusējuma iestatījumi.':
        'The model has not been calibrated against history yet (python modelis.py --kalibret), default settings are used.',
    'Modelis pret tirgu (reālās spēles)':
        'Model vs market (real games)',
    'Nav atrasts kalendārs (sezonas/nhl_kalendars.csv).':
        'Schedule not found (sezonas/nhl_kalendars.csv).',
    'Cik tuvākās spēles rādīt':
        'How many upcoming games to show',
    'Kalendārā šobrīd nav nākamo spēļu.':
        'There are no upcoming games in the schedule right now.',
    'Tiesneši: {}':
        'Referees: {}',
    'tiesneši vēl nav paziņoti':
        'referees not announced yet',
    'Prognozes ir matemātisks novērtējums no pieejamajiem datiem (pamatlaiks), nevis garantija.':
        'Predictions are a mathematical estimate from the available data (regulation), not a guarantee.',
    'Visas':
        'All',
    'PPG_pret':
        'PPG_pret',
    'W = win (arī OT win un SO win), L = loss, OTL = OT loss vai SO loss. Visi statistikas rādītāji (vārti, metieni, noraidījumi, vairākums) ir pamatlaika, bez papildlaika un pēcspēles metieniem. Win, loss un punkti ir oficiālie rezultāti. Tabulu var kārtot, klikšķinot uz kolonnas virsraksta.':
        'W = win (incl. OT win and SO win), L = loss, OTL = OT loss or SO loss. All stats (goals, shots, penalties, power play) are for regulation, excluding overtime and shootouts. Wins, losses and points are official results. The table can be sorted by clicking a column header.',
    'Rezultativitāte':
        'Scoring',
    'Vārti spēlē':
        'Goals per game',
    'Vidēji spēlē (pamatlaikā)':
        'Average per game (regulation)',
    'Ielaisti spēlē':
        'Allowed per game',
    '% – spēļu daļa, kurās abu komandu vārtu summa pamatlaikā ir lielāka par 6.5':
        '% – share of games where the combined goals of both teams in regulation exceed 6.5',
    '% – spēļu daļa, kurās abu komandu vārtu summa pamatlaikā ir lielāka par 5.5':
        '% – share of games where the combined goals of both teams in regulation exceed 5.5',
    'Metieni vārtos spēlē':
        'Shots on goal per game',
    'Pretinieka metieni spēlē':
        'Opponent shots per game',
    'Vairākums un noraidījumi':
        'Power play and penalties',
    'Vairākums PP':
        'Power play PP',
    '% – kopā izvēlētajās spēlēs: vairākumā gūtie vārti / vairākuma iespējas':
        '% – total in the selected games: power-play goals / power-play opportunities',
    'Mazākums PK':
        'Penalty kill PK',
    '% – kopā izvēlētajās spēlēs: mazākumā nosargātās reizes':
        '% – total in the selected games: share of penalties killed',
    'Noraidījumi spēlē':
        'Penalties per game',
    'Vidēji spēlē (saņemtie, pamatlaikā)':
        'Average per game (taken, regulation)',
    'Izcīnītie noraidījumi spēlē':
        'Penalties drawn per game',
    'Vidēji spēlē (pretinieka noraidījumi)':
        'Average per game (opponent penalties)',
    'Gūtie vārti pa periodiem':
        'Goals scored by period',
    'Vidēji spēlē':
        'Average per game',
    '1. periods':
        '1st period',
    '2. periods':
        '2nd period',
    '3. periods':
        '3rd period',
    'Ielaistie vārti pa periodiem':
        'Goals allowed by period',
    'Savstarpējās':
        'Head-to-head',
    'Nospēlētās spēles kopā: {} · šajā skatā: {}':
        'Games played total: {} · in this view: {}',
    'Nospēlētās spēles kopā: {}':
        'Games played total: {}',
    'Atvērt komandas statistiku':
        'Open team stats',
    '({:%H:%M})':
        '({})',
    'visas':
        'all',
    'Šī sezona':
        'This season',
    'Visas sezonas':
        'All seasons',
    'nākamā spēle {:%d.%m(%H:%M)} · {}':
        'next game {} · {}',
    'beigas':
        'end',
    '{} · vārti {}:{}':
        '{} · goals {}:{}',
    'Šī sezona: {}':
        'This season: {}',
    'Šī sezona: vēl nav spēlējušas':
        'This season: have not played yet',
    'Visas sezonas ({}): {}':
        'All seasons ({}): {}',
    'Ar šo vietas izvēli savstarpējo spēļu nav – izvēlies otru komandu mājās vai noņem izvēli.':
        'With this venue selection there are no head-to-head games – select the other team at home or clear the selection.',
    'Statistika pēc {} savstarpēj{} – izlase ir maza, procenti un vidējie ir mazāk droši nekā sezonas dati. Iepriekšējās sezonās komandu sastāvi bija citādi.':
        'Stats from {} head-to-head {} – a small sample, percentages and averages are less reliable than season data. In previous seasons the rosters were different.',
    'Statistika pēc {} savstarpēj{} – izlase ir maza, procenti un vidējie ir mazāk droši nekā sezonas dati.':
        'Stats from {} head-to-head {} – a small sample, percentages and averages are less reliable than season data.',
    'ās spēles':
        'game',
    'ām spēlēm':
        'games',
    'SEZONA':
        'SEASON',
    '· šī sezona':
        '· this season',
    'Savstarpējās spēles (play-off)':
        'Head-to-head games (playoffs)',
    'Savstarpējās spēles':
        'Head-to-head games',
    'Ar šādu atlasi spēļu nav':
        'No games with this selection',
    'Pēdējās 5 spēles':
        'Last 5 games',
    'Nav spēļu':
        'No games',
    '· laika joslu starpība {} h':
        '· time zone difference {} h',
    'CEĻOJUMS':
        'TRAVEL',
    'Savstarpējas spēles tuvāko 2 dienu kalendārā nav':
        'No head-to-head game in the schedule for the next 2 days',
    'otrā spēle pēc kārtas un ceļš {} km':
        'second game in a row and {} km of travel',
    'otrā spēle pēc kārtas':
        'second game in a row',
    'garš ceļš īsā laikā':
        'long trip in a short time',
    'laika joslu maiņa {} h':
        'time zone change {} h',
    '{}. spēle 7 dienās':
        'game {} in 7 days',
    'mājās':
        'home',
    'Nav jāceļo':
        'No travel',
    'pēdējā spēle šeit pat':
        'last game here as well',
    '{} {} · {} → {} (no mājām)':
        '{} {} · {} → {} (from home)',
    'spēle otro dienu pēc kārtas':
        'game on the second day in a row',
    'atpūta {} d.':
        'rest {} d.',
    'pirmā spēle':
        'first game',
    'Paredzēta spēle {:%d.%m(%H:%M)} · {} {} ({})':
        'Scheduled game {} · {} {} ({})',
    'Jāņem vērā: {}':
        'Note: {}',
    'viesos':
        'away',
    'Kopš iepriekšējās spēles beigām (~)':
        'Since the end of the previous game (~)',
    'Spēle {:%d.%m.} plkst. {:%H:%M} · {} ({} mājās)':
        'Game {} at {} · {} ({} at home)',
    'Pirmā komanda':
        'First team',
    'Otrā komanda':
        'Second team',
    'Izvēlies divas dažādas komandas.':
        'Choose two different teams.',
    'Salīdzināt':
        'Compare',
    'Salīdzināt citas komandas':
        'Compare other teams',
    '{} ({} · kopā {})':
        '{} ({} · total {})',
    'Nav spēlējušas ne šosezon, ne iepriekšējās sezonās · {}':
        'Have not played this season or in previous seasons · {}',
    'Nav spēlējušas ne šosezon, ne iepriekšējās sezonās':
        'Have not played this season or in previous seasons',
    'Šosezon {}, iepriekšējās sezonās {} savstarpējās spēles':
        'This season {}, previous seasons {} head-to-head games',
    'Savstarpējās: šosezon vēl nav spēlējušas{}{}':
        'Head-to-head: have not played this season yet{}{}',
    '· iepriekšējās sezonās {} spēles':
        '· previous seasons {} games',
    '{} mājās':
        '{} at home',
    '/results?spele={}&t={}':
        '/results?spele={}&t={}',
    '/results?spele={}':
        '/results?spele={}',
    '· mājās':
        '· home',
    '· viesos':
        '· away',
    '⇅  Kārtot':
        '⇅  Sort',
    'Kārtot pēc':
        'Sort by',
    'Secība':
        'Order',
    '↓ No lielākā':
        '↓ Highest first',
    '↑ No mazākā':
        '↑ Lowest first',
    '✕ Noklusējums':
        '✕ Default',
    'Hokeja periods':
        'Hockey period',
    '{}. periods – vidēji gūti':
        'Period {} – average scored',
    'Pamatlaikā kopā – vidēji gūti':
        'Regulation total – average scored',
    '{}. periodā gūtie vārti (kopā izvēlētajās spēlēs)':
        'Goals scored in period {} (total in the selected games)',
    '{}. periodā ielaistie vārti (kopā izvēlētajās spēlēs)':
        'Goals allowed in period {} (total in the selected games)',
    'Gūto un ielaisto vārtu starpība {}. periodā (kopā izvēlētajās spēlēs)':
        'Goal difference in period {} (total in the selected games)',
    'Gūti/v.':
        'GF/gm',
    'Vidēji gūtie vārti {}. periodā vienā spēlē':
        'Average goals scored in period {} per game',
    'Ielaisti/v.':
        'GA/gm',
    'Vidēji ielaistie vārti {}. periodā vienā spēlē':
        'Average goals allowed in period {} per game',
    'Metieni/v.':
        'Shots/gm',
    'Vidēji metieni vārtos {}. periodā vienā spēlē':
        'Average shots on goal in period {} per game',
    'Metieni pret/v.':
        'Shots against/gm',
    'Pretinieka vidējie metieni vārtos pret šo komandu {}. periodā vienā spēlē':
        'Average opponent shots on goal against this team in period {} per game',
    '{}. periods · pēdējās {} spēles{} (komanda:pretinieks)':
        'Period {} · last {} games{} (team:opponent)',
    'Pēdējās spēles':
        'Recent games',
    'Pēdējās {} spēles · pamatlaika vārti (komanda:pretinieks)':
        'Last {} games · regulation goals (team:opponent)',
    'Līnija':
        'Line',
    'Vid_kopa':
        'Vid_kopa',
    'Pēdējās {} spēles{} · pamatlaika vārti (komanda:pretinieks)':
        'Last {} games{} · regulation goals (team:opponent)',
    'Šim skatam datu nav.':
        'No data for this view.',
    'Punkti vairākumā':
        'Power-play points',
    'Piespēles vairākumā':
        'Power-play assists',
    'PP % (komandas)':
        'PP % (teams)',
    '{} vārti no {} vairākumiem':
        '{} goals on {} power plays',
    'PP vārti (komandas)':
        'PP goals (teams)',
    'Pēdējās {} spēles{} · vairākuma vārti (par:pret)':
        'Last {} games{} · power-play goals (for:against)',
    'Noraidījumi spēlē (komandas)':
        'Penalties per game (teams)',
    '1. periodā (komandas, vidēji)':
        '1st period (teams, average)',
    '2. periodā (komandas, vidēji)':
        '2nd period (teams, average)',
    '3. periodā (komandas, vidēji)':
        '3rd period (teams, average)',
    'speletaji':
        'speletaji',
    'Noraidījumi vidēji spēlē (spēlētājs)':
        'Penalties per game (player)',
    '{} noraidījumi {} spēlēs':
        '{} penalties in {} games',
    'Visvairāk noraidījumu (spēlētājs)':
        'Most penalties (player)',
    'Visvairāk sodu minūšu (spēlētājs)':
        'Most penalty minutes (player)',
    'Visi periodi':
        'All periods',
    'Rādītājs':
        'Stat',
    'Noraidījumu skaits':
        'Number of penalties',
    'Vērtība':
        'Value',
    'Saņemtie':
        'Taken',
    'Izcīnītie':
        'Drawn',
    'noraidījumu skaits':
        'number of penalties',
    'sodu minūtes':
        'penalty minutes',
    'vidēji vienā spēlē':
        'average per game',
    'kopā izvēlētajās spēlēs':
        'total in the selected games',
    'pamatlaikā (1.–3. periods kopā, bez papildlaika)':
        'in regulation (periods 1–3 combined, excluding overtime)',
    '1. periodā':
        'in the 1st period',
    '2. periodā':
        'in the 2nd period',
    '3. periodā':
        'in the 3rd period',
    'komandas saņemtie (paša sodi)':
        'taken by the team (own penalties)',
    'komandas izcīnītie (pretinieka sodi pret šo komandu)':
        'drawn by the team (opponent penalties against this team)',
    '{}_kopa':
        '{}_kopa',
    'Izcīnīto un saņemto starpība ({}, {}, {}); pozitīvs skaitlis = komanda izcīna vairāk, nekā saņem':
        'Drawn minus taken ({}, {}, {}); positive = the team draws more than it takes',
    'Metropolitēna':
        'Metropolitan',
    'Centrālā':
        'Central',
    'Klusā okeāna':
        'Pacific',
    'Gūtie vārti':
        'Goals scored',
    'Vārtu starpība':
        'Goal difference',
    'Vārti pa periodiem (vidēji spēlē)':
        'Goals by period (average per game)',
    'Gūti 1. periodā':
        'Scored in 1st period',
    'Gūti 2. periodā':
        'Scored in 2nd period',
    'Gūti 3. periodā':
        'Scored in 3rd period',
    'Ielaisti 1. periodā':
        'Allowed in 1st period',
    'Ielaisti 2. periodā':
        'Allowed in 2nd period',
    'Ielaisti 3. periodā':
        'Allowed in 3rd period',
    'Metieni spēlē':
        'Shots per game',
    'xG (paredzamie vārti, vidēji spēlē)':
        'xG (expected goals, average per game)',
    'xG spēlē':
        'xG per game',
    'xG pret spēlē':
        'xG against per game',
    'xG daļa %':
        'xG share %',
    'Vairākums un mazākums':
        'Power play and penalty kill',
    'Vairākums PP %':
        'Power play PP %',
    'Vairākuma vārti':
        'Power-play goals',
    'Vairākuma iespējas':
        'Power-play opportunities',
    'Vairākuma metieni':
        'Power-play shots',
    'Mazākums PK %':
        'Penalty kill PK %',
    'Ielaisti mazākumā':
        'Shorthanded goals allowed',
    'PP_opp_pret':
        'PP_opp_pret',
    'Mazākuma reizes':
        'Times shorthanded',
    'Sodu minūtes spēlē':
        'Penalty minutes per game',
    'Noraidījumu starpība spēlē':
        'Penalty difference per game',
    'Spēles stils (vidēji spēlē)':
        'Playing style (average per game)',
    'Bloķētie metieni':
        'Blocked shots',
    'Ripas zaudējumi':
        'Giveaways',
    'Ripas atņemšanas':
        'Takeaways',
    'Šai komandai vēl nav datu.':
        'No data for this team yet.',
    'Spēlētāju statistika':
        'Player stats',
    'Aizvadītās spēles':
        'Past games',
    'Nākamās spēles':
        'Upcoming games',
    'Padziļināta statistika':
        'Advanced stats',
    'Par komandu':
        'About the team',
    '{}. vieta līgā':
        '#{} in the league',
    'Bilance (W-L-OTL)':
        'Record (W-L-OTL)',
    '{} punkti · {}%':
        '{} points · {}%',
    '{} spēlēs':
        'in {} games',
    'gūti {} ({} pret xG)':
        'scored {} ({} vs xG)',
    'Paredzamie vārti (expected goals) vidēji spēlē: cik vārtus komanda “būtu pelnījusi” gūt pēc savu metienu kvalitātes (attālums, leņķis, metiena veids, atlēciens). Gūti vairāk nekā xG = laba realizācija vai veiksme':
        'Expected goals per game: how many goals the team “deserved” to score based on the quality of its shots (distance, angle, shot type, rebound). Scoring more than xG = good finishing or luck',
    'ielaisti {} ({} pret xG)':
        'allowed {} ({} vs xG)',
    'Paredzamie vārti, ko komanda pieļauj pretiniekam vidēji spēlē (mazāk = labāka aizsardzība). Ielaisti mazāk nekā xG = labs vārtsargs vai veiksme':
        'Expected goals the team allows the opponent per game (lower = better defense). Allowing fewer than xG = a good goalie or luck',
    'xG {} : {} kopā':
        'xG {} : {} total',
    'Komandas xG / (komandas xG + pretinieku xG). Virs 50% = komanda rada bīstamākas iespējas nekā pieļauj – labs ilgtermiņa formas rādītājs':
        'Team xG / (team xG + opponent xG). Above 50% = the team creates more dangerous chances than it allows – a good long-term indicator of form',
    '{}/{} vārti':
        '{}/{} goals',
    'ielaisti {}':
        'allowed {}',
    'izcīnīti {}':
        'drawn {}',
    'papildlaikā izšķirtas: {}':
        'decided in overtime: {}',
    'metienu sērijas: {}':
        'shootouts: {}',
    'Nākamā spēle':
        'Next game',
    '{:%d.%m(%H:%M)} · {} · uzspied, lai salīdzinātu':
        '{} · {} · click to compare',
    'Forma (pēdējās 5)':
        'Form (last 5)',
    '← vecākā':
        '← oldest',
    'jaunākā →':
        'newest →',
    'Šai komandai spēlētāju datu vēl nav.':
        'No player data for this team yet.',
    'Rādīt top 7 ▾':
        'Show top 7 ▾',
    'Laiks laukumā (vidēji)':
        'Time on ice (average)',
    'Laukuma spēlētāji':
        'Skaters',
    'Atvairīto metienu %':
        'Save %',
    'Ielaisti vidēji (GAA)':
        'Goals against average (GAA)',
    'Vārtsargi':
        'Goalies',
    '{} h pret Rīgu':
        '{} h vs Riga',
    'Saīsinājums':
        'Abbreviation',
    'Divīzija':
        'Division',
    'Pilsēta':
        'City',
    'Arēna':
        'Arena',
    'Sezonā aizvadītas':
        'Games played this season',
    '{} spēles':
        '{} games',
    'Bilance mājās':
        'Home record',
    'Bilance viesos':
        'Away record',
    'Atvērt spēles protokolu':
        'Open the game summary',
    'metieni {}:{}':
        'shots {}:{}',
    'Parādītas {} no {} spēlēm':
        'Showing {} of {} games',
    'Ielādēt vēl':
        'Load more',
    'kom_sp_vel_{}':
        'kom_sp_vel_{}',
    'kom_sp_visas_{}':
        'kom_sp_visas_{}',
    'Kalendārā nav atrastu nākamo spēļu.':
        'No upcoming games found in the schedule.',
    'Komandas vērtība · līgas vidējais · vieta starp {} komandām (':
        'Team value · league average · rank among {} teams (',
    'zaļa':
        'green',
    '= labākā ceturtdaļa,':
        '= top quarter,',
    '= sliktākā)':
        '= bottom quarter)',
    'līgā {}':
        'league {}',
    'varti':
        'varti',
    'Šai sadaļai vajag failu fakti.py un vārtu datus (sezonas/varti.csv).':
        'This section needs the file fakti.py and goal data (sezonas/varti.csv).',
    '· {} no {}':
        '· {} of {}',
    'Lielākie comebacks':
        'Biggest comebacks',
    '{} pret {}':
        '{} vs {}',
    '· {:%d.%m.} · {}{}':
        '· {} · {}{}',
    'Uzvara pēc {} vārtu deficīta ({}. periodā {})':
        'Win after a {}-goal deficit ({} in period {})',
    'Gūst pirmie → win %':
        'Scores first → win %',
    'spēlēs, kurās guva pirmos vārtus':
        'in games where they scored first',
    'Ielaiž pirmie → win %':
        'Allows first → win %',
    'spēlēs, kurās ielaida pirmos vārtus':
        'in games where they allowed the first goal',
    '3. perioda karaļi (win %)':
        '3rd period kings (win %)',
    '{} win no {} spēlēm, kurās pēc 2. perioda bija iedzinējos':
        'won {} of {} games trailing after the 2nd period',
    'Noturīgākie līderi (win %)':
        'Most reliable leaders (win %)',
    '{} win no {} spēlēm, kurās pēc 2. perioda vadīja':
        'won {} of {} games leading after the 2nd period',
    'Izlīdzinājumi beigās':
        'Late equalizers',
    '· {} no tām win':
        '· {} of them won',
    'Visvairāk comebacks':
        'Most comebacks',
    '· lielākais −{}':
        '· biggest −{}',
    'Izlaistas 2+ vārtu vadības':
        'Blown 2+ goal leads',
    'Situācijas':
        'Situations',
    'Brīdis':
        'Moment',
    'Pirmie vārti':
        'First goal',
    'Pēc 1. perioda':
        'After 1st period',
    'Pēc 2. perioda':
        'After 2nd period',
    'Gūst pirmie':
        'Scores first',
    'Ielaiž pirmie':
        'Allows first',
    'Kurš guva pirmos':
        'Who scored first',
    'Vadībā':
        'Leading',
    'Iedzinējos':
        'Trailing',
    'Stāvoklis':
        'State',
    '1 vārts':
        '1 goal',
    '2 vārti':
        '2 goals',
    '3+ vārti':
        '3+ goals',
    'Izlīdzinājumi 3. perioda pēdējās 2 minūtēs: kopā {} (no tām {} beidzās ar win)':
        'Equalizers in the last 2 minutes of the 3rd period: {} in total ({} of them ended in a win)',
    'Izlīdzināja':
        'Equalized',
    'No tām win':
        'Of them won',
    'Pret to izlīdzināja':
        'Equalized against',
    'Vārti 3. perioda pēdējās 2 minūtēs, kas izlīdzināja rezultātu':
        'Goals in the last 2 minutes of the 3rd period that tied the game',
    'Spēles, kuras pēc izlīdzinājuma komanda arī uzvarēja (OT/SO)':
        'Games the team also won after the equalizer (OT/SO)',
    'Reizes, kad pretinieks izlīdzināja pēdējās 2 minūtēs':
        'Times the opponent equalized in the last 2 minutes',
    'Izlīdzinājums 3. periodā':
        'Equalizer in the 3rd period',
    'ar {}+ vārtu':
        'by {}+ goals',
    'ar {} vārtu':
        'by {} goals',
    'guva pirmos vārtus':
        'scored the first goal',
    'ielaida pirmos vārtus':
        'allowed the first goal',
    '{} vadīja{} pārsvaru':
        'led{1} {0}',
    '{} vadīja':
        'led {}',
    '{} bija iedzinējos{} deficītu':
        'trailed{1} {0}',
    '{} bija iedzinējos':
        'trailed {}',
    '{} bija neizšķirts':
        'was tied {}',
    'Šādā situācijā vēl nav nevienas spēles.':
        'No games in this situation yet.',
    'Spēles, kurās komanda {}: kopā {} · līgā vidēji':
        'Games in which the team {}: total {} · league average',
    'Spēles, kurās komanda {}':
        'Games in which the team {}',
    'OT loss vai SO loss':
        'OT loss or SO loss',
    'Uzvaru daļa šajās spēlēs':
        'Win share in these games',
    'Izcīnīto punktu daļa (win 2, OT/SO loss 1)':
        'Share of points earned (win 2, OT/SO loss 1)',
    'Comebacks · {} {} (uzvara pēc ≥ {} vārtu deficīta)':
        'Comebacks · {} {} (win after a ≥ {}-goal deficit)',
    'spēle':
        'game',
    'spēles':
        'games',
    'Visas komandas':
        'All teams',
    'Lielākais deficīts: {}:{}, {}. periodā {}':
        'Biggest deficit: {}:{}, in period {} {}',
    'Lapa {} no {} · spēles {}–{} no {}':
        'Page {} of {} · games {}–{} of {}',
    'SHUTOUT · {} {} (vārtsargs bez ielaistiem vārtiem ≥ 120 min)':
        'SHUTOUT · {} {} (goalie without a goal allowed ≥ 120 min)',
    'aktīva sērija':
        'active streak',
    'aktīvas sērijas':
        'active streaks',
    'Pašlaik nevienam vārtsargam nav sausās sērijas, kas ilgāka par 120 minūtēm.':
        'Right now no goalie has a shutout streak longer than 120 minutes.',
    'Sērija turpinās kopš {:%d.%m.}':
        'The streak has continued since {}',
    'sakums':
        'sakums',
    'aktīva · kopš {:%d.%m.}':
        'active · since {}',
    'aktīva':
        'active',
    'Sērija pārtraukta':
        'Streak ended',
    'pārtraukta {:%d.%m.} · {}':
        'ended {} · {}',
    'Signāls':
        'Signal',
    'Pagaidām neviena komanda būtiski neizceļas. Signālam vajag vismaz {} spēles situācijā un vismaz {} procentpunktu atšķirību no līgas vidējā.':
        'For now no team stands out significantly. A signal needs at least {} games in the situation and at least a {} percentage point difference from the league average.',
    'Lejupielādēt datus (JSON)':
        'Download data (JSON)',
    'Rādīt top {} ▾':
        'Show top {} ▾',
    'W_kopa':
        'W_kopa',
    'L_kopa':
        'L_kopa',
    'Kopa_bil':
        'Kopa_bil',
    '· bilance {}':
        '· record {}',
    'Visbiežāk līdz papildlaikam':
        'Most often to overtime',
    '· {}% spēļu':
        '· {}% of games',
    '{} win no {} spēlēm līdz papildlaikam':
        'won {} of {} games that went to overtime',
    'Vārti papildlaikā':
        'Overtime goals',
    'Punkti papildlaikā':
        'Overtime points',
    'Līdz papildl.':
        'To OT',
    'Kopā W-L':
        'Total W-L',
    'Gūti OT':
        'OT goals for',
    'Ielaisti OT':
        'OT goals against',
    'Metieni OT':
        'OT shots',
    'Pret. metieni OT':
        'Opp. OT shots',
    'Spēles, kas pēc pamatlaika bija neizšķirtas (papildlaiks un/vai metienu sērija)':
        'Games tied after regulation (overtime and/or shootout)',
    'Cik % spēļu aizgāja līdz papildlaikam':
        'Share of games (%) that went to overtime',
    'OT win – OT loss (spēles, kas izšķīrās papildlaikā)':
        'OT win – OT loss (games decided in overtime)',
    'SO win – SO loss (pēcspēles metienu sērijas)':
        'SO win – SO loss (shootouts)',
    'OT win un SO win daļa spēlēs, kas aizgāja līdz papildlaikam':
        'Share of OT wins and SO wins in games that went to overtime',
    'Papildlaikā gūtie vārti':
        'Goals scored in overtime',
    'Papildlaikā ielaistie vārti':
        'Goals allowed in overtime',
    'Metieni vārtos papildlaikā':
        'Shots on goal in overtime',
    'Pretinieka metieni papildlaikā':
        'Opponent shots in overtime',
    '**Kas ir xG (expected goals, paredzamie vārti)?** Katram metienam, kas nav bloķēts (vārtos, garām vai vārti), modelis piešķir varbūtību\nkļūt par vārtiem – pēc tā, **no kurienes un kā** metiens izdarīts: attālums un leņķis pret vārtiem, metiena veids (plaukstas, uzsitiens,\npārmetiens u.c.), vai tas ir atlēciens, ātrais uzbrukums un sastāvs (5 pret 5, vairākums, mazākums). Piemēram, metiens no zilās līnijas ≈ 0.03,\natlēciens no vārtu priekšas ≈ 0.25–0.35. Saskaitot visus komandas metienus, iegūst, **cik vārtus komanda “būtu pelnījusi” gūt** pēc savu iespēju kvalitātes.\nModelis apmācīts uz iepriekšējo 3 sezonu metieniem (~240 000 metienu). Tukšie vārti un metienu sērijas netiek skaitīti, tikai pamatlaiks.\n\n**Kāpēc tas noder?** Vārti hokejā ir reti un ļoti nejauši (rikošets, vārtsarga kļūda, stabiņš). xG mēra to, kas ir komandas kontrolē – **cik\nlabas iespējas tā rada un cik daudz pieļauj**. Tāpēc xG ir stabilāks un labāk paredz nākamās spēles nekā vārti: komanda ar labu xG, bet sliktiem\nrezultātiem, parasti uzlabojas, un otrādi.\n\n| Rādītājs | Ko nozīmē | Kā lasīt |\n|---|---|---|\n| **xG/sp** | Radīto iespēju kvalitāte vidēji spēlē | Vairāk = bīstamāks uzbrukums. Līgā ~2.8–3.0 |\n| **xG pret/sp** | Pretiniekam pieļauto iespēju kvalitāte vidēji spēlē | Mazāk = labāka aizsardzība |\n| **xG %** | Komandas xG / (komandas xG + pretinieku xG) | Virs 50% – komanda kontrolē spēli; viens no labākajiem formas rādītājiem |\n| **xG ±/sp** | xG/sp mīnus xG pret/sp | Cik iespēju ziņā komanda ir pārāka par pretiniekiem vidēji spēlē |\n| **Vārti − xG** | Gūtie vārti mīnus xG (kopā) | + = realizē labāk nekā “vajadzētu” (labi metēji vai veiksme), − = neveiksme/slikta realizācija; lieli skaitļi parasti izlīdzinās |\n| **Vārtsargi (xG − ielaisti)** | Pretinieku xG mīnus ielaistie vārti (kopā) | + = vārtsargi ielaiž mazāk nekā gaidāms (labi vārtsargi vai veiksme) |\n| **xG/metiens** | Vidējā viena metiena kvalitāte | Augstāks = komanda met no labākām pozīcijām, nevis “visu pēc kārtas” |\n| **Bīstami/sp** | Metieni ar xG ≥ 0.09 vidēji spēlē (un pret) – ~ceturtā daļa metienu, ≈ katrs 7. kļūst par vārtiem | Īstas vārtu iespējas – atlēcieni, metieni no vārtu priekšas ("high-danger") |\n| **PDO** | Metienu realizācija % + atvairīto metienu % (vārtos) | Līgā ≈ 100. Virs ~102 – komandai “veicas” (visticamāk kritīsies), zem ~98 – “neveicas” (visticamāk uzlabosies) |\n\n**Spēlētājiem:** *ixG* – spēlētāja paša metienu xG; *Vārti − ixG* – vai viņš realizē vairāk vai mazāk nekā vidējs spēlētājs no tām pašām pozīcijām\n(ilgstoši + ir labiem snaiperiem). **Vārtsargiem:** *GSAx* (goals saved above expected) = xG pret viņu − ielaistie vārti: + = atvairījis vairāk\nnekā vidējs vārtsargs tādos pašos metienos – labākais vārtsarga kvalitātes rādītājs.\n\nMazs spēļu skaits (sezonas sākumā) – rādītāji vēl ļoti svārstās. Sastāva filtrs: *Vairākums* – komandas metieni vairākumā un pretinieka metieni\nmazākumā tajās pašās situācijās (un otrādi *Mazākumam*).':
        '**What is xG (expected goals)?** For every shot that is not blocked (on goal, missed or a goal), the model assigns a probability\nof becoming a goal – based on **where and how** the shot was taken: distance and angle to the net, shot type (wrist,\nslap, backhand, etc.), whether it is a rebound, a rush, and the strength (5 on 5, power play, shorthanded). For example, a shot from the blue line ≈ 0.03,\na rebound in front of the net ≈ 0.25–0.35. Adding up all of a team\'s shots gives **how many goals the team “deserved” to score** based on the quality of its chances.\nThe model is trained on shots from the previous 3 seasons (~240,000 shots). Empty-net goals and shootouts are not counted, regulation only.\n\n**Why is it useful?** Goals in hockey are rare and very random (deflections, goalie mistakes, posts). xG measures what the team controls – **how\ngood the chances it creates are and how many it allows**. That is why xG is more stable and predicts future games better than goals: a team with good xG but poor\nresults usually improves, and vice versa.\n\n| Stat | What it means | How to read it |\n|---|---|---|\n| **xG/gm** | Quality of chances created per game | More = a more dangerous attack. League ~2.8–3.0 |\n| **xGA/gm** | Quality of chances allowed to the opponent per game | Less = better defense |\n| **xG %** | Team xG / (team xG + opponent xG) | Above 50% – the team controls the game; one of the best indicators of form |\n| **xG ±/gm** | xG/gm minus xGA/gm | How much better the team is than its opponents in chances per game |\n| **Goals − xG** | Goals scored minus xG (total) | + = finishing better than “expected” (good shooters or luck), − = bad luck/poor finishing; large numbers usually even out |\n| **Goalies (xG − allowed)** | Opponent xG minus goals allowed (total) | + = the goalies allow fewer than expected (good goalies or luck) |\n| **xG/shot** | Average quality of one shot | Higher = the team shoots from better positions rather than “everything it can” |\n| **Danger/gm** | Shots with xG ≥ 0.09 per game (and against) – ~a quarter of shots, ≈ every 7th becomes a goal | Real scoring chances – rebounds, shots from in front of the net ("high-danger") |\n| **PDO** | Shooting % + save % (on goal) | League ≈ 100. Above ~102 – the team is “lucky” (will most likely drop), below ~98 – “unlucky” (will most likely improve) |\n\n**Players:** *ixG* – xG of the player\'s own shots; *Goals − ixG* – whether he finishes more or less than an average player from the same positions\n(consistently + for good snipers). **Goalies:** *GSAx* (goals saved above expected) = xG against him − goals allowed: + = saved more\nthan an average goalie on the same shots – the best measure of goalie quality.\n\nSmall number of games (early season) – the stats still swing a lot. Strength filter: *Power play* – the team\'s shots on the power play and the opponent\'s shots\nshorthanded in the same situations (and the other way round for *Penalty kill*).',
    'xG – paredzamie vārti':
        'xG – expected goals',
    'xG datiem vajag metienu datus (sezonas/metieni.csv) un xG modeli (sezonas/vesture/xg_modelis.json).':
        'xG needs shot data (sezonas/metieni.csv) and the xG model (sezonas/vesture/xg_modelis.json).',
    'Kas ir xG un kā lasīt šo sadaļu':
        'What is xG and how to read this section',
    'Sastāvs':
        'Strength',
    'Labākā xG %':
        'Best xG %',
    'xG {} radīti, {} pieļauti {} spēlēs':
        'xG {} created, {} allowed in {} games',
    'Bīstamākais uzbrukums (xG/sp)':
        'Most dangerous attack (xG/gm)',
    '· gūti {}/sp':
        '· scored {}/gm',
    'Labākā aizsardzība (xG pret/sp)':
        'Best defense (xGA/gm)',
    '· ielaisti {}/sp':
        '· allowed {}/gm',
    'Realizē virs xG':
        'Finishing above xG',
    '· {} vārti no {} xG':
        '· {} goals from {} xG',
    'Gūti vairāk nekā paredzēts – labi metēji vai veiksme (bieži izlīdzinās)':
        'Scored more than expected – good shooters or luck (often evens out)',
    'Realizē zem xG (var uzlaboties)':
        'Finishing below xG (may improve)',
    'Gūti mazāk nekā paredzēts – nākotnē parasti tuvojas xG':
        'Scored less than expected – usually moves toward xG in the future',
    'Visvairāk “veicas” (PDO)':
        'Luckiest (PDO)',
    'Realizācija % + atvairīto metienu %. Virs ~102 – rezultāti labāki par spēli, visticamāk kritīsies':
        'Shooting % + save %. Above ~102 – results better than the play, will most likely drop',
    'Bīstamākais uzbrukums':
        'Most dangerous attack',
    'Bīstamākais vairākums':
        'Most dangerous power play',
    'Labākā aizsardzība':
        'Best defense',
    'Labākais mazākums':
        'Best penalty kill',
    'xG pret/sp':
        'xGA/gm',
    'Vārti − xG':
        'Goals − xG',
    'Vārtsargi (xG − ielaisti)':
        'Goalies (xG − allowed)',
    'xG/metiens':
        'xG/shot',
    'Bīstami/sp':
        'Danger/gm',
    'Bīstami pret/sp':
        'Danger against/gm',
    'Spēles ar metienu datiem izvēlētajā atlasē':
        'Games with shot data in the selected filter',
    'Paredzamie vārti vidēji spēlē – cik bīstamas iespējas komanda rada (vairāk = labāk)':
        'Expected goals per game – how dangerous the chances the team creates are (more = better)',
    'Pretinieku paredzamie vārti vidēji spēlē – cik bīstamas iespējas komanda pieļauj (mazāk = labāk)':
        "Opponents' expected goals per game – how dangerous the chances the team allows are (less = better)",
    'Komandas xG daļa no visiem xG tās spēlēs. Virs 50% – komanda kontrolē spēli':
        "Team's share of all xG in its games. Above 50% – the team controls the game",
    'xG/sp mīnus xG pret/sp':
        'xG/gm minus xGA/gm',
    'Faktiski gūtie vārti vidēji spēlē (no metieniem, bez tukšajiem vārtiem)':
        'Actual goals scored per game (from shots, excluding empty-net goals)',
    'Gūti mīnus paredzētie (kopā): + realizē virs gaidītā (labi metēji vai veiksme), − zem gaidītā':
        'Scored minus expected (total): + finishing above expectation (good shooters or luck), − below expectation',
    'Pretinieku xG mīnus ielaistie vārti (kopā): + vārtsargi ielaiž mazāk nekā gaidāms':
        'Opponent xG minus goals allowed (total): + the goalies allow fewer than expected',
    'Vidējā metiena kvalitāte (xG uz vienu neblokētu metienu)':
        'Average shot quality (xG per unblocked shot)',
    'Metieni ar xG ≥ {} vidēji spēlē – īstas vārtu iespējas':
        'Shots with xG ≥ {} per game – real scoring chances',
    'Pretinieka metieni ar xG ≥ {} vidēji spēlē':
        'Opponent shots with xG ≥ {} per game',
    'Realizācija % + atvairīto metienu % (vārtos). Līgā ≈ 100; virs ~102 – veicas, zem ~98 – neveicas':
        'Shooting % + save % (on goal). League ≈ 100; above ~102 – lucky, below ~98 – unlucky',
    '{} Vairāk paskaidrojumu – “Kas ir xG un kā lasīt šo sadaļu”.':
        '{} More explanation – “What is xG and how to read this section”.',
    'Secība: xG/sp vairākumā (bīstamākais vairākums augšā). xG % un PDO speciālajās situācijās nav jēgpilni.':
        'Order: xG/gm on the power play (most dangerous power play on top). xG % and PDO are not meaningful in special teams situations.',
    'Secība: xG pret/sp mazākumā (mazāk = labāk). xG % un PDO speciālajās situācijās nav jēgpilni.':
        'Order: xGA/gm on the penalty kill (less = better). xG % and PDO are not meaningful in special teams situations.',
    'Secība: xG %; vienādiem – xG ±/sp, tad komandas punkti sezonā.':
        "Order: xG %; ties – xG ±/gm, then the team's season points.",
    'Spēlētājs':
        'Player',
    'Vārtos':
        'On goal',
    'Vārti − ixG':
        'Goals − ixG',
    'Bīstami':
        'Danger',
    'Spēles, kurās spēlētājs izdarījis vismaz vienu metienu (izvēlētajā atlasē)':
        'Games in which the player took at least one shot (in the selected filter)',
    'Neblokētie metieni (vārtos, garām un vārti), pamatlaikā':
        'Unblocked shots (on goal, missed and goals), regulation',
    'Metieni vārtos (ieskaitot vārtus)':
        'Shots on goal (including goals)',
    'Spēlētāja paša metienu paredzamie vārti – cik vārtus viņš “būtu pelnījis” gūt':
        "Expected goals from the player's own shots – how many goals he “deserved” to score",
    '+ realizē labāk nekā vidējs spēlētājs no tām pašām pozīcijām (snaiperis vai veiksme), − sliktāk':
        '+ finishes better than an average player from the same positions (sniper or luck), − worse',
    'ixG vidēji spēlē':
        'ixG per game',
    'Vidējā metiena kvalitāte – augstāks = met no bīstamākām vietām':
        'Average shot quality – higher = shoots from more dangerous areas',
    'Metieni ar xG ≥ {}':
        'Shots with xG ≥ {}',
    'Top 60 pēc ixG. Kārtot var ar pogu “Kārtot”.':
        'Top 60 by ixG. Sort with the “Sort” button.',
    'Vārtsargs':
        'Goalie',
    'xG pret':
        'xG against',
    'Atvairīti %':
        'Save %',
    'Bīstami pret':
        'Danger against',
    'Paredzamie vārti no visiem metieniem pret šo vārtsargu':
        'Expected goals from all shots against this goalie',
    'Goals saved above expected = xG pret − ielaisti. + atvairījis vairāk nekā vidējs vārtsargs tādos pašos metienos':
        'Goals saved above expected = xG against − goals allowed. + saved more than an average goalie on the same shots',
    'GSAx vidēji spēlē':
        'GSAx per game',
    'Faktiskais atvairīto metienu % (metieni vārtos)':
        'Actual save % (shots on goal)',
    'Metieni pret vārtsargu ar xG ≥ {}':
        'Shots against the goalie with xG ≥ {}',
    'Secība: GSAx (vārtsargs, kas atvairījis visvairāk virs gaidītā, augšā).':
        'Order: GSAx (the goalie who saved the most above expectation on top).',
    '2. spēle (bez atpūtas)':
        '2nd game (no rest)',
    '1. spēle':
        '1st game',
    'Atpūties':
        'Rested',
    'Jebkurš':
        'Any',
    'Arī B2B':
        'Also B2B',
    '2. spēlē (bez atpūtas dienas)':
        'in the 2nd game (no day of rest)',
    '1. spēlē (nākamajā dienā vēl spēle)':
        'in the 1st game (another game the next day)',
    'B2B {}: kopā {} spēles · līgā':
        'B2B {}: {} games in total · league',
    'punktu (citās spēlēs {}%) · win {}%':
        'points (in other games {}%) · win {}%',
    'Šādu spēļu vēl nav.':
        'No such games yet.',
    'Punkti % B2B spēlēs':
        'Points % in B2B games',
    '{} win, {} loss, {} OT/SO loss {} B2B spēlēs':
        '{} win, {} loss, {} OT/SO loss in {} B2B games',
    'Visvairāk B2B spēļu':
        'Most B2B games',
    '· {}% punktu':
        '· {}% of points',
    'Vislabāk tiek galā (pret citām spēlēm)':
        'Handles it best (vs other games)',
    '· {}% pret {}%':
        '· {}% vs {}%',
    'Punkti % B2B spēlēs mīnus punkti % citās spēlēs (procentpunkti)':
        'Points % in B2B games minus points % in other games (percentage points)',
    'Lielākais kritums (pret citām spēlēm)':
        'Biggest drop (vs other games)',
    'Punkti % citās':
        'Points % other',
    'B2B pret citām':
        'B2B vs other',
    'Gūti/sp':
        'GF/gm',
    'Vārtu ±':
        'Goal ±',
    'Pret. metieni/sp':
        'Opp. shots/gm',
    'Cik B2B spēles komanda aizvadījusi ({}); uzved, lai redzētu spēles':
        'Number of B2B games the team has played ({}); hover to see the games',
    'Uzvaras šajās B2B spēlēs (arī OT win un SO win)':
        'Wins in these B2B games (incl. OT win and SO win)',
    'Zaudējumi pamatlaikā šajās B2B spēlēs':
        'Regulation losses in these B2B games',
    'Zaudējumi papildlaikā vai metienu sērijā (dod 1 punktu)':
        'Losses in overtime or a shootout (worth 1 point)',
    'Cik % no iespējamajiem punktiem komanda izcīnīja B2B spēlēs (win = 2, OT/SO loss = 1). Piem., 1-1-0 = 50%':
        'Share of possible points (%) the team earned in B2B games (win = 2, OT/SO loss = 1). E.g. 1-1-0 = 50%',
    'Tas pats rādītājs visās pārējās šīs sezonas spēlēs (ne B2B) – ar ko salīdzināt':
        'The same stat in all other games this season (not B2B) – for comparison',
    'Punkti % B2B spēlēs mīnus Punkti % citās (procentpunkti). +20 = B2B spēlēs komanda spēlē labāk nekā parasti; −30 = B2B spēlēs ievērojami sliktāk (nogurums)':
        'Points % in B2B games minus Points % other (percentage points). +20 = the team plays better than usual in B2B games; −30 = considerably worse in B2B games (fatigue)',
    'Vidēji gūtie vārti B2B spēlē (pamatlaikā)':
        'Average goals scored per B2B game (regulation)',
    'Vidēji ielaistie vārti B2B spēlē (pamatlaikā)':
        'Average goals allowed per B2B game (regulation)',
    'Gūto un ielaisto vārtu starpība visās šīs B2B spēlēs kopā (pamatlaikā)':
        'Goal difference in all these B2B games combined (regulation)',
    'Vidēji metieni vārtos B2B spēlē (pamatlaikā)':
        'Average shots on goal per B2B game (regulation)',
    'Pretinieka vidējie metieni vārtos B2B spēlē':
        'Average opponent shots on goal per B2B game',
    'Secība: Punkti % B2B spēlēs; ja vienāds – vairāk uzvaru, labāka vārtu starpība, tad komandas punkti un uzvaras visā sezonā. Mazs spēļu skaits (1–2) ir nejaušs – skaties uz “Sp.” un “B2B pret citām”.':
        "Order: Points % in B2B games; if equal – more wins, better goal difference, then the team's points and wins for the whole season. A small number of games (1–2) is random – look at “GP” and “B2B vs other”.",
    'Nākamās B2B (7 dienas)':
        'Upcoming B2B (7 days)',
    'arī B2B':
        'also B2B',
    'atpūties {} d.':
        'rested {} d.',
    '2. spēle':
        '2nd game',
    'Pretinieks 2. spēlē':
        'Opponent in 2nd game',
    'Pirmā spēle (laiks pēc Rīgas)':
        'First game (Riga time)',
    'Otrā spēle nākamajā dienā (pēc ASV laika) – bez atpūtas':
        'Second game the next day (US time) – no rest',
    'Vai pretinieks pirms šīs spēles ir atpūties (dienas bez spēles) vai arī spēlē B2B':
        'Whether the opponent is rested before this game (days without a game) or also playing a B2B',
    'Tuvāko 7 dienu kalendārā B2B spēļu nav.':
        'No B2B games in the schedule for the next 7 days.',
    'B2B (back to back) – komanda spēlē divās dienās pēc kārtas (pēc ASV austrumu laika, kā to skaita NHL). Vārti un metieni ir pamatlaika; win, loss un punkti – oficiālie rezultāti.':
        'B2B (back to back) – the team plays on two days in a row (by US Eastern time, as the NHL counts it). Goals and shots are for regulation; wins, losses and points are official results.',
    'Nosargāti':
        'Killed',
    'Gūti mazākumā':
        'Shorthanded goals',
    'Nosargāto mazākumu daļa (pamatlaikā)':
        'Share of penalties killed (regulation)',
    'Cik reizes komanda spēlēja mazākumā (pamatlaikā)':
        'Times the team played shorthanded (regulation)',
    'Mazākumi bez ielaistiem vārtiem':
        'Penalty kills without a goal allowed',
    'Mazākumā ielaistie vārti':
        'Goals allowed while shorthanded',
    'Mazākumā gūtie vārti (pamatlaikā)':
        'Goals scored while shorthanded (regulation)',
    'Vidēji saņemtie noraidījumi spēlē (pamatlaikā)':
        'Average penalties taken per game (regulation)',
    'PK % (komandas)':
        'PK % (teams)',
    '{} no {} mazākumiem izturēti':
        '{} of {} penalties killed',
    'Gūti mazākumā (komandas)':
        'Shorthanded goals (teams)',
    'Punkti mazākumā':
        'Shorthanded points',
    'Vārti mazākumā':
        'Shorthanded goals',
    'Spēļu kalendārs':
        'Game schedule',
    "Kalendāra fails 'sezonas/nhl_kalendars.csv' nav atrasts (palaid kalendars.py).":
        "Schedule file 'sezonas/nhl_kalendars.csv' not found (run kalendars.py).",
    'Tiesneši pārbaudīti {:%d.%m. %H:%M} · ⚠️ {}. Nākamā pārbaude: {}.':
        'Referees checked {} · ⚠️ {}. Next check: {}.',
    'Tiesneši pārbaudīti {:%d.%m. %H:%M}. Nākamā pārbaude: {}.':
        'Referees checked {}. Next check: {}.',
    'Cik dienas uz priekšu':
        'How many days ahead',
    'Šajā periodā spēļu nav.':
        'No games in this period.',
    'rmb_kal_{:%Y%m%d}':
        'rmb_kal_{}',
    '**{}, {:%d.%m.%Y}** · {} spēles':
        '**{}, {}** · {} games',
    'Tiesneši nav paziņoti':
        'Referees not announced',
    'Mājinieki':
        'Home',
    '⇄ Salīdzināt komandas':
        '⇄ Compare teams',
    'Salīdzināt komandas: {} @ {}':
        'Compare teams: {} @ {}',
    'Pēdējā atjaunošana: {} · Rezultāti līdz {:%d.%m.} ({} spēles)':
        'Last update: {} · Results through {} ({} games)',
    'Rezultāti līdz {:%d.%m.} ({} spēles)':
        'Results through {} ({} games)',
    '{} · Nākamā atjaunošana: {}.':
        '{} · Next update: {}.',
    'Spēļu rezultāti':
        'Game results',
    'spele':
        'spele',
    '❮ Iepriekšējā diena':
        '❮ Previous day',
    'Nākamā diena ❯':
        'Next day ❯',
    '#### {}, {:%d.%m.%Y}':
        '#### {}, {}',
    'Šajā datumā nav noslēgušos spēļu.':
        'No completed games on this date.',
    'Metieni {}':
        'Shots {}',
    'Noraidījumi {}–{}':
        'Penalties {}–{}',
    'PP vārti {}':
        'PP goals {}',
    '(viesi–mājinieki)':
        '(away–home)',
    'metieni {}':
        'shots {}',
    'noraidījumi {}':
        'penalties {}',
    'Papildlaiks ({}, tikai informācijai):':
        'Overtime ({}, for information only):',
    'Spēles zvaigznes:':
        'Three stars:',
    'Tiesneši:':
        'Referees:',
    'Labākie spēlētāji':
        'Top players',
    'Sākums {:%d.%m. %H:%M} · {}':
        'Start {} · {}',
    'Sākums {:%d.%m. %H:%M}':
        'Start {}',
    'Detaļu vēl nav.':
        'No details yet.',
    'Spēlētāju dati (sezonas/speletaji.csv un sezonas/vartsargi.csv) vēl nav pieejami.':
        'Player data (sezonas/speletaji.csv and sezonas/vartsargi.csv) is not available yet.',
    'Nav datu.':
        'No data.',
    'Pozīcija':
        'Position',
    'Uzbrucēji':
        'Forwards',
    'Aizsargi':
        'Defensemen',
    'Sausās spēles: uzvaras bez ielaistiem vārtiem, nostāvot visu spēli vienam':
        'Shutouts: wins without a goal allowed, playing the whole game alone',
    'Tiesnešu dati vēl nav pieejami. Tie parādīsies pēc nākamās datu atjaunināšanas (sezonas/tiesnesi.csv); iepriekšējo sezonu dati – sezonas/vesture/':
        "Referee data is not available yet. It will appear after the next data update (sezonas/tiesnesi.csv); previous seasons' data – sezonas/vesture/",
    '/tiesnesi.csv.':
        '/tiesnesi.csv.',
    'Aprēķina iestatījumi':
        'Calculation settings',
    'DB = iepriekšējās sezonas kopā ({})':
        'DB = previous seasons combined ({})',
    'Līgas vidējā korekcija K (spēles)':
        'League average adjustment K (games)',
    'Kombinētais rādītājs = {} × DB ({}) + {} × šī sezona. Katra sezonas komponente tiek pievilkta pie līgas vidējā, kas vienāds ar {} spēlēm: jaunam tiesnesim vai ar maz spēlēm rādītājs ir tuvu līgas vidējam.':
        'Combined rating = {} × DB ({}) + {} × this season. Each season component is pulled toward the league average with a weight of {} games: for a new referee or one with few games the rating is close to the league average.',
    'Nav tiesnešu datu.':
        'No referee data.',
    'Iepriekšējo sezonu dati (sezonas/vesture/':
        "Previous seasons' data (sezonas/vesture/",
    '/tiesnesi.csv) nav atrasti, tāpēc tiek lietota tikai šī sezona.':
        '/tiesnesi.csv) not found, so only this season is used.',
    'Līgas vidējais šosezon':
        'League average this season',
    'Līgas vidējais DB':
        'League average DB',
    'Iepriekšējās sezonas kopā: {}':
        'Previous seasons combined: {}',
    'Tiesneši datubāzē':
        'Referees in the database',
    'Spēles ar tiesnešiem šosezon':
        'Games with referees this season',
    'Tiesnešu tabula':
        'Referee table',
    'Gaidāmie noraidījumi spēlei':
        'Expected penalties for a game',
    'Tiesneša spēles':
        "Referee's games",
    'Rādīt tiesnešus ar vismaz tik spēlēm (šī sezona + DB kopā)':
        'Show referees with at least this many games (this season + DB combined)',
    'Spēles DB':
        'Games DB',
    'Noraid. vid. šosezon':
        'Pen. avg. this season',
    'Noraid. vid. DB':
        'Pen. avg. DB',
    'Dati':
        'Data',
    'Spēles iepriekšējās sezonās kopā ({})':
        'Games in previous seasons combined ({})',
    'Vidēji noraidījumi spēlē šosezon (abām komandām kopā)':
        'Average penalties per game this season (both teams combined)',
    'Vidēji noraidījumi spēlē iepriekšējās sezonās kopā ({})':
        'Average penalties per game in previous seasons combined ({})',
    'Šīs sezonas un DB vidējais, pievilkts pie līgas vidējā (sk. Aprēķina iestatījumi)':
        'Average of this season and DB, pulled toward the league average (see Calculation settings)',
    'Kombinētais mīnus līgas vidējais: + = vairāk noraidījumu nekā vidēji':
        'Combined minus league average: + = more penalties than average',
    'Spēļu skaits (šī sezona + DB): Maz < 8 spēles, Vidēji 8–19, OK 20+':
        'Number of games (this season + DB): Low < 8 games, Medium 8–19, OK 20+',
    'Noraidījumi = abu komandu minor sodu skaits spēles pamatlaikā (dubultais minor = 2; bez major, 10 min disciplinārajiem un kautiņiem), ko pieskaita katram spēles tiesnesim. DB = iepriekšējās sezonas kopā ({}).':
        'Penalties = the number of minor penalties of both teams in regulation (double minor = 2; excluding majors, 10-min misconducts and fights), credited to each referee of the game. DB = previous seasons combined ({}).',
    'Spēles tiesneši (parasti divi)':
        'Game referees (usually two)',
    'Nav izvēlēts neviens tiesnesis, tāpēc rādīts līgas kombinētais vidējais.':
        'No referee selected, so the league combined average is shown.',
    'Noraidījumi spēlē kopā':
        'Total penalties per game',
    '{} pret līgu':
        '{} vs league',
    'Mājas komandai':
        'Home team',
    '{}. periodā':
        'Period {}',
    'Šo vērtību vēlāk var padot modelim (da.tiesnesu_prognoze), lai koriģētu noraidījumu prognozi.':
        'This value can later be fed to the model (da.tiesnesu_prognoze) to adjust the penalty prediction.',
    'Šosezon vēl nav tiesnešu spēļu.':
        'No referee games this season yet.',
    'Spēlētāju dati (sezonas/speletaji.csv) vēl nav pieejami.':
        'Player data (sezonas/speletaji.csv) is not available yet.',
    'Kā tiek noteikts, ka spēlētājs ir karsts?':
        'How do we decide that a player is hot?',
    '**Logs.** Vienmēr tiek skatītas spēlētāja pēdējās 5 spēles (ja nospēlēts mazāk – visas). Rādītājs – punkti, vārti vai piespēles (punkti = vārti + piespēles). Pozīcijas filtrs atdala uzbrucējus un aizsargus, jo aizsargiem līgas vidējais ir daudz zemāks.\n\n**Kārtot: Karstākie kopā** (noklusējums) – kopējais **karstums 0–100** no četrām daļām:\n1. **Forma pret līgu – 40 %.** Cik logā iegūts vairāk par līgas vidējo savā pozīcijā (ņemot vērā spēļu skaitu). Šī daļa atbild uz jautājumu “vai viņš tagad spēlē augstā līmenī”, tāpēc augšā ir arī zvaigznes (piem., McDavid), kas spēlē labi visu laiku.\n2. **Virs savas normas – 30 %.** Indekss z (sk. zemāk): cik spēlētājs pārspēj pats sevi. Ja viņš spēlē zem savas normas, šī daļa nedaudz atņem.\n3. **Sērija – 20 %.** Spēles pēc kārtas ar rādītāju; pilnu svaru dod ~10 spēļu sērija (līdz 15 – vēl nedaudz vairāk).\n4. **Pamatotība – 10 %.** Vai metienu skaits logā audzis pret sezonas vidējo (līdz ±50 %). Vairāk metienu nozīmē, ka forma nav tikai veiksme. Piespēlēm metieni neko nepasaka, tāpēc tur šī daļa visiem ir vienāda.\n\nLīmeņi: **70+** ļoti karsts {}, **50–69** karsts {}, **30–49** silts, zem 30 – parasti.\n\n**Kārtot: Virs savas normas** – tikai indekss **z** = (faktiskais − gaidāmais) / √gaidāmais. Gaidāmais = spēlētāja iepriekšējo spēļu vidējais (pirms loga), pievilkts pie līgas vidējā ar 10 spēlēm, lai jaunam vai maz spēlējušam spēlētājam tas būtu tuvu līgas vidējam; reizināts ar spēlēm logā. 0 = parasts līmenis, **1+** silts, **2+** karsts {}, **3+** ļoti karsts {}. Šajā režīmā augšā ir tie, kas pēkšņi spēlē daudz labāk nekā parasti (arī vidējie spēlētāji), bet zvaigzne, kas spēlē savā ierastajā augstajā līmenī, ir zemāk.\n\n**Kas tiek sarakstā.** Vismaz izvēlētais spēļu skaits logā (slīdnis) un rādītājs vismaz **2 dažādās** spēlēs – viena “uzspridzināta” spēle nepadara karstu. Papildus tiek iekļauti spēlētāji ar rādītāju **{}+ mājas** {} vai **izbraukuma** {} spēlēs pēc kārtas (skaitot tikai attiecīgās vietas spēles), pat ja kopējā forma nav izcila. Rāda līdz 50 spēlētājiem.\n\n**Simboli un kolonnas**\n- Zem vārda: {} ļoti karsts, {} karsts; {} / {} – rādītājs tik mājas / izbraukuma spēlēs pēc kārtas (krāsas kā formas stabiņiem). Uzvedot peli uz ikonas – paskaidrojums.\n- **Forma:** 5 stabiņi – katra loga spēle no vecākās (pa kreisi) uz jaunāko; augstums = rādītājs spēlē, zils – mājās, violets – izbraukumā, zems pelēks – 0. Uzvedot peli uz stabiņa – datums, pretinieks, G un A. Zīmīte labajā pusē – karstums (vai z režīmā “Virs savas normas”), krāsa: sarkana – ļoti karsts, oranža – karsts, dzeltena – silts, pelēka – parasti.\n- **Logā:** vārti, piespēles un punkti logā; zem tiem – vidēji spēlē un spēļu skaits.\n- **Sērija:** spēles pēc kārtas ar rādītāju (no jaunākās). **Sezonā:** vidēji spēlē visā sezonā.\n- **Nāk. sp.:** gaidāmais nākamajā spēlē = 75 % sezonas vidējais + 25 % loga vidējais (abi pievilkti pie līgas vidējā). Hokejā forma saglabājas tikai nedaudz – liela daļa uzliesmojumu ir veiksme, tāpēc prognoze ir piesardzīga.\n- **Sezona īsumā:** sezonas spēles, G, A, P un metieni. Uzvedot peli (telefonā – pieskaroties) – **“Kāpēc karsts”**: cik iegūts logā, sērijas, vai auguši metieni (pamatots) vai ļoti augsts šaušanas % (var būt veiksme), un vai audzis laiks laukumā (+1 min un vairāk).\n\n**Ņem vērā.** Sezonas sākumā izlase ir maza, tāpēc vietas var strauji mainīties. Pretinieku stiprums netiek ņemts vērā. Tā ir statistikas indikācija, nevis garantija.':
        "**Window.** We always look at the player's last 5 games (if he has played fewer – all of them). Stat – points, goals or assists (points = goals + assists). The position filter separates forwards and defensemen, because the league average for defensemen is much lower.\n\n**Sort: Hottest overall** (default) – an overall **heat score 0–100** made of four parts:\n1. **Form vs league – 40 %.** How much more the player produced in the window than the league average for his position (taking the number of games into account). This part answers “is he playing at a high level right now”, so stars who play well all the time (e.g. McDavid) are also near the top.\n2. **Above his norm – 30 %.** The z index (see below): how much the player outperforms himself. If he plays below his norm, this part takes a little away.\n3. **Streak – 20 %.** Consecutive games with the stat; a ~10-game streak gives the full weight (up to 15 – slightly more).\n4. **Substance – 10 %.** Whether the number of shots in the window has grown compared to the season average (up to ±50 %). More shots mean the form is not just luck. For assists shots say nothing, so this part is the same for everyone.\n\nLevels: **70+** very hot {}, **50–69** hot {}, **30–49** warm, below 30 – normal.\n\n**Sort: Above his norm** – only the index **z** = (actual − expected) / √expected. Expected = the player's average in earlier games (before the window), pulled toward the league average with 10 games, so that for a new player or one with few games it is close to the league average; multiplied by the games in the window. 0 = normal level, **1+** warm, **2+** hot {}, **3+** very hot {}. In this mode the top shows players who suddenly play much better than usual (including average players), while a star playing at his usual high level is lower.\n\n**Who is on the list.** At least the selected number of games in the window (slider) and the stat in at least **2 different** games – one “explosive” game does not make a player hot. Players with the stat in **{}+ home** {} or **away** {} games in a row (counting only games at that venue) are also included, even if their overall form is not outstanding. Up to 50 players are shown.\n\n**Symbols and columns**\n- Under the name: {} very hot, {} hot; {} / {} – the stat in this many home / away games in a row (colors as in the form bars). Hover over an icon for an explanation.\n- **Form:** 5 bars – each game in the window from oldest (left) to newest; height = the stat in the game, blue – home, purple – away, low gray – 0. Hover over a bar – date, opponent, G and A. The badge on the right – heat score (or z in the “Above his norm” mode), color: red – very hot, orange – hot, yellow – warm, gray – normal.\n- **In window:** goals, assists and points in the window; below them – per game and the number of games.\n- **Streak:** consecutive games with the stat (from the most recent). **Season:** average per game for the whole season.\n- **Next gm:** expected in the next game = 75 % season average + 25 % window average (both pulled toward the league average). In hockey form persists only a little – much of a hot streak is luck, so the prediction is cautious.\n- **Season at a glance:** season games, G, A, P and shots. Hover (on a phone – tap) – **“Why hot”**: what he produced in the window, streaks, whether shots have grown (justified) or the shooting % is very high (may be luck), and whether ice time has grown (+1 min or more).\n\n**Keep in mind.** Early in the season the sample is small, so positions can change quickly. Opponent strength is not taken into account. This is a statistical indication, not a guarantee.",
    'Minimālais spēļu skaits logā':
        'Minimum games in window',
    'Viena spēle nekad netiek ņemta vērā; agrā sezonā logā var būt mazāk spēļu':
        'A single game is never counted; early in the season the window may contain fewer games',
    'Kārtot':
        'Sort',
    'Karstākie kopā':
        'Hottest overall',
    'punkti':
        'points',
    'piespeles':
        'piespeles',
    'vārti':
        'goals',
    'piespēles':
        'assists',
    'Nav spēlētāju, kas atbilst nosacījumiem (nepietiek spēļu vai rādītājs bijis tikai vienā spēlē). Pamēģini samazināt minimālo spēļu skaitu vai izvēlēties garāku logu.':
        'No players match the criteria (not enough games or the stat came in only one game). Try lowering the minimum number of games or choosing a longer window.',
    'punktu':
        'a point',
    'vārtiem':
        'a goal',
    'piespēli':
        'an assist',
    'ļoti karsts':
        'very hot',
    '{} mājas spēles pēc kārtas ar {}':
        '{} home games in a row with {}',
    '{} izbraukuma spēles pēc kārtas ar {}':
        '{} away games in a row with {}',
    '{:%d.%m} · {} vs {} · {}G {}A':
        '{} · {} vs {} · {}G {}A',
    'izbr.':
        'away',
    'virs savas normas (z): 1+ silts, 2+ karsts, 3+ ļoti karsts':
        'above his norm (z): 1+ warm, 2+ hot, 3+ very hot',
    'karstums 0–100: 30+ silts, 50+ karsts, 70+ ļoti karsts':
        'heat score 0–100: 30+ warm, 50+ hot, 70+ very hot',
    'Logā':
        'In window',
    'Sezonā':
        'Season',
    'Nāk. sp.':
        'Next gm',
    '{} sp · {}G {}A {}P · {} metieni':
        '{} GP · {}G {}A {}P · {} shots',
    'Zem vārda: divas sarkanas liesmas – ļoti karsts, oranža liesma – karsts; zila māja / violeta lidmašīna ar skaitli – rādītājs tik mājas / izbraukuma spēlēs pēc kārtas (no {})':
        'Under the name: two red flames – very hot, an orange flame – hot; a blue house / purple plane with a number – the stat in this many home / away games in a row (from {})',
    'Stabiņi – {} katrā loga spēlē (vecākā → jaunākā; zils = mājās, violets = izbraukumā; uzvedot peli – spēle). Zīmīte – indekss virs savas normas (z): 1+ silts, 2+ karsts, 3+ ļoti karsts.':
        'Bars – {} in each game of the window (oldest → newest; blue = home, purple = away; hover – the game). Badge – index above his norm (z): 1+ warm, 2+ hot, 3+ very hot.',
    'Stabiņi – {} katrā loga spēlē (vecākā → jaunākā; zils = mājās, violets = izbraukumā; uzvedot peli – spēle). Zīmīte – kopējais karstums 0–100 (forma pret līgu 40 %, virs savas normas 30 %, sērija 20 %, metieni 10 %): 30+ silts, 50+ karsts, 70+ ļoti karsts.':
        'Bars – {} in each game of the window (oldest → newest; blue = home, purple = away; hover – the game). Badge – overall heat score 0–100 (form vs league 40 %, above his norm 30 %, streak 20 %, shots 10 %): 30+ warm, 50+ hot, 70+ very hot.',
    'Vārti, piespēles un punkti pēdējās {} spēlēs; zem – {} spēlē logā':
        'Goals, assists and points in the last {} games; below – {} per game in the window',
    'Spēles pēc kārtas ar {}':
        'Consecutive games with {}',
    'Vidēji {} spēlē visā sezonā':
        'Average {} per game for the whole season',
    'Gaidāmie {} nākamajā spēlē: 75% sezonas vidējais + 25% pēdējo spēļu vidējais (abi pievilkti pie līgas vidējā)':
        'Expected {} in the next game: 75% season average + 25% recent games average (both pulled toward the league average)',
    'Sezonas kopsavilkums. Uzvedot peli (telefonā – pieskaroties): kāpēc spēlētājs ir karsts':
        'Season summary. Hover (on a phone – tap): why the player is hot',
    'Punkti logā':
        'Points in window',
    'Vārti logā':
        'Goals in window',
    'Piespēles logā':
        'Assists in window',
    'Kārtots pēc kopējā karstuma (forma, sērija, virs savas normas, metieni). Logs: {} (ja spēlētājs nospēlējis mazāk, tiek ņemtas visas viņa spēles). Sezonas sākumā izlase ir maza, tāpēc rangs var strauji mainīties. Tā ir statistikas indikācija, nevis garantija.':
        'Sorted by overall heat score (form, streak, above his norm, shots). Window: {} (if the player has played fewer games, all of his games are used). Early in the season the sample is small, so the ranking can change quickly. This is a statistical indication, not a guarantee.',
    'Kārtots pēc tā, cik spēlētājs pārspēj savu līdzšinējo līmeni. Logs: {} (ja spēlētājs nospēlējis mazāk, tiek ņemtas visas viņa spēles). Sezonas sākumā izlase ir maza, tāpēc rangs var strauji mainīties. Tā ir statistikas indikācija, nevis garantija.':
        'Sorted by how much the player outperforms his own level so far. Window: {} (if the player has played fewer games, all of his games are used). Early in the season the sample is small, so the ranking can change quickly. This is a statistical indication, not a guarantee.',
    'Latviešu':
        'Latviešu',
    'Gaišais motīvs':
        'Light theme',
    'Gaišais / tumšais motīvs':
        'Light / dark theme',
    'Tumšais motīvs':
        'Dark theme',
    'Regulārā sezona':
        'Regular season',
    'Līgas tabula: tikai regulārā sezona':
        'League table: regular season only',
    'šīs sezonas spēles no {:%d.%m.%Y} līdz {:%d.%m.%Y} ({} spēles)':
        "this season's games from {} to {} ({} games)",
    'šīs sezonas aizvadītās spēles':
        "this season's completed games",
    '; datubāzē arī iepriekšējās sezonas ({}), kas lapās netiek rādītas, bet tiek izmantotas tiesnešu statistikā':
        '; the database also contains previous seasons ({}), which are not shown on the pages but are used in the referee stats',
    'Kā tiek rēķināts.':
        'How it is calculated.',
    'Visi rādītāji (vārti, metieni, noraidījumi, vairākums, periodi) ir tikai par pamatlaiku – papildlaiks\nun pēcspēles metienu sērijas netiek ieskaitīti; tās ir apkopotas atsevišķi sadaļā OT / SO. Vidējie ir kopsumma, dalīta ar\nizvēlēto spēļu skaitu (visa sezona, pēdējās 5 vai pēdējās 10, visas vai tikai mājās / viesos). Noraidījumi ir minor sodi\n(dubultais minor = 2), bez lielajiem un disciplinārajiem sodiem. Bilance (win, loss, OT loss) un punkti ir oficiālie rezultāti.':
        'All stats (goals, shots, penalties, power play, periods) are for regulation only – overtime\nand shootouts are not included; they are summarized separately in the OT / SO section. Averages are the total divided by\nthe selected number of games (full season, last 5 or last 10, all or only home / away). Penalties are minor penalties\n(double minor = 2), excluding major and misconduct penalties. The record (win, loss, OT loss) and points are official results.',
    'Pieejamie dati.':
        'Available data.',
    '{}; nākamo spēļu kalendārs uz priekšu.':
        '{}; the schedule of upcoming games ahead.',
    'Datu avoti.':
        'Data sources.',
    'NHL oficiālā statistika (rezultāti, spēlētāji, vārtsargi, notikumi, kalendārs, tiesneši pēc spēles)\nun Scouting The Refs (pirms spēlēm paziņotie tiesneši). Dati tiek atjaunināti automātiski katru dienu.':
        'Official NHL stats (results, players, goalies, events, schedule, referees after the game)\nand Scouting The Refs (referees announced before games). The data is updated automatically every day.',
    'Visa informācija ir tikai informatīva un balstīta uz matemātiskiem aprēķiniem no pieejamajiem datiem.\nTā nav garantija un nav ieteikums.':
        'All information is for informational purposes only and based on mathematical calculations from the available data.\nIt is not a guarantee and not a recommendation.',
    # ===== datu_apstrade.py =====
    'Trešdiena':
        'Wednesday',
    'Svētdiena':
        'Sunday',
    'Vidēji':
        'Average',
    '{} {} {} spēlēs ({} spēlē; sezonā {})':
        '{} {} in {} games ({} per game; season {})',
    'rādītājs {} no {} spēlēm':
        'the stat in {} of {} games',
    'sērija {} spēles pēc kārtas':
        'streak of {} games in a row',
    'mājas':
        'home',
    '{} {} spēles pēc kārtas ar rādītāju (tikai {} spēļu secībā)':
        '{} {} games in a row with the stat (counting only {} games)',
    'metienu skaits audzis ({} pret {} spēlē), tāpēc rezultāts pamatots':
        'shots up ({} vs {} per game), so the output is justified',
    'šaušanas % ļoti augsts, daļa var būt veiksme':
        'very high shooting %, part of it may be luck',
    'laiks laukumā +{} min':
        'ice time +{} min',
    # ===== fakti.py =====
    'komandas':
        'teams',
    'gūstot pirmos vārtus':
        'when scoring first',
    'ielaižot pirmos vārtus':
        'when allowing the first goal',
    'vadot pēc 1. perioda':
        'when leading after the 1st period',
    'esot iedzinējos pēc 1. perioda':
        'when trailing after the 1st period',
    'vadot pēc 2. perioda':
        'when leading after the 2nd period',
    'esot iedzinējos pēc 2. perioda':
        'when trailing after the 2nd period',
    'ar neizšķirtu pēc 2. perioda':
        'when tied after the 2nd period',
    '{} win no {} spēlēm {} ({}%; līgā vidēji {}%)':
        'won {} of {} games {} ({}%; league average {}%)',
    '{} reizes izlīdzinājusi 3. perioda pēdējās 2 minūtēs':
        '{} times equalized in the last 2 minutes of the 3rd period',
    '. periods':
        '. periods',
    # ===== lokacijas.py =====
    'Kanāda':
        'Canada',
    'Elmont (Ņujorka)':
        'Elmont (New York)',
    'Ņujorka':
        'New York',
    'Vašingtona':
        'Washington',
    'Čikāga':
        'Chicago',
    'Losandželosa':
        'Los Angeles',
    'Našvila':
        'Nashville',
    'Sanhosē':
        'San Jose',
    'Vankūvera':
        'Vancouver',
    'Nezināma komanda: {}':
        'Unknown team: {}',
    # ===== modelis.py =====
    'Pamatlaikā {}':
        'Regulation {}',
    'Uzvarētājs ar OT {}':
        'Winner incl. OT {}',
    'Totāls {} (ar OT)':
        'Total {} (incl. OT)',
    # ===== picks.py =====
    'Uzvarētājs (ar OT)':
        'Winner (incl. OT)',
    'Totāls (ar OT)':
        'Total (incl. OT)',
    '±1.5 (ar OT)':
        '±1.5 (incl. OT)',
    '{} uzvara pamatlaikā':
        '{} win in regulation',
    '{} uzvara (ar OT)':
        '{} win (incl. OT)',
    'vidējais':
        'average',
    'nav tirgus atsauces (trūkst pretējā iznākuma koeficienta)':
        "no market reference (the opposite outcome's odds are missing)",
    'varbūtība {}% < {}%':
        'probability {}% < {}%',
    'koeficients {} > {}':
        'odds {} > {}',
    'modelis pret tirgu {} pp – pārāk liela atšķirība':
        'model vs market {} pp – difference too large',
    'modelis nav optimistiskāks par tirgu':
        'the model is not more optimistic than the market',
    'der, bet gaida paziņotus sākuma vārtsargus':
        'qualifies, but waiting for announced starting goalies',
    'prognožu arhīvs':
        'prediction archive',
    'lietotnes (kalibrēti arī uz pārbaudes sezonas)':
        'app settings (also calibrated on the test season)',
    'parametri_parbaudei (kalibrēti uz {}, bez {})':
        'parametri_parbaudei (calibrated on {}, without {})',
    'apmācīts uz metieniem pirms {}':
        'trained on shots before {}',
    'apmācīts':
        'trained',
    'par maz likmju apmācības sezonās':
        'too few bets in the training seasons',
    'pelnošs abos posmos, bet pārbaudes sezonas ROI nav drošs (± 1 SE) – mazākas likmes, līdz to apstiprina reālā vēsture':
        'profitable in both stages, but the test-season ROI is not reliable (± 1 SE) – smaller stakes until real history confirms it',
    'nav pelnošs apmācības sezonās':
        'not profitable in the training seasons',
    'nav pelnošs pārbaudes sezonā':
        'not profitable in the test season',
    'SportsbookReview – ASV bukmeikeru noslēguma koeficienti (vidējais bez uzcenojuma = tirgus; labākais = likmei)':
        "SportsbookReview – US bookmakers' closing odds (average without margin = market; best = for the bet)",
    # ===== vērtības no datiem un tekstu daļas, ko lietotne saliek izpildes laikā =====
    'Pirmdiena':
        'Monday',
    'Otrdiena':
        'Tuesday',
    'Ceturtdiena':
        'Thursday',
    'Piektdiena':
        'Friday',
    'Sestdiena':
        'Saturday',
    'Austrumu':
        'Eastern',
    'Rietumu':
        'Western',
    'Atlantijas':
        'Atlantic',
    'Nosaukums':
        'Name',
    'Konference':
        'Conference',
    'ASV':
        'USA',
    'Filadelfija':
        'Philadelphia',
    'Pitsburga':
        'Pittsburgh',
    'Denvera':
        'Denver',
    'Dalasa':
        'Dallas',
    'Edmontona':
        'Edmonton',
    'Sentpola (Minesota)':
        'Saint Paul (Minnesota)',
    'Sietla':
        'Seattle',
    'Sentluisa':
        'St. Louis',
    'Soltleiksitija':
        'Salt Lake City',
    'Lasvegasa':
        'Las Vegas',
    'Vinipega':
        'Winnipeg',
    'pēc 1. perioda':
        'after the 1st period',
    'pēc 2. perioda':
        'after the 2nd period',
    'Prognozes':
        'Predictions',
    'Fakti':
        'Facts',
    'Statistika':
        'Stats',
    'versija {}':
        'version {}',
    'sarkana':
        'red',
    '⇅  {}  {}':
        '⇅  {}  {}',
    '{} · {}':
        '{} · {}',
    'Detaļas':
        'Details',
    'pēdējās 5':
        'last 5',
    'pēdējās 10':
        'last 10',
    'English':
        'English',
    'nav':
        'none',
    '{} win, {} OT/SO loss, {} loss {}':
        '{} win, {} OT/SO loss, {} loss {}',
    'Veids':
        'Type',
    'Notika':
        'Actual',
    'Virs savas normas':
        'Above his norm',
    'Karstums':
        'Heat score',
    'Viesi':
        'Away',
    'Laika posms':
        'Period',
    'Papildl. %':
        'OT %',
    'Noraid/v.':
        'Pen/gm',
    'Noraid./sp':
        'Pen./gm',
    'DB svars (%)':
        'DB weight (%)',
    'Tiesnesis':
        'Referee',
    'Maz':
        'Low',
    'Datums':
        'Date',
    'Noraid. viesi':
        'Pen. away',
    'Laiks':
        'Time',
    'Pamatlaiks':
        'Regulation',
    'Viesu komandai':
        'Away team',
    'Laika josla':
        'Time zone',
    'Pretinieks':
        'Opponent',
    'karsts':
        'hot',
    'silts':
        'warm',
    'Sitieni pretiniekam (hits)':
        'Hits on opponents',
    '· {}':
        '· {}',
    '{} ⓘ':
        '{} ⓘ',
    'netiek lietota':
        'not used',
    'Iemetieni % {}':
        'Faceoffs % {}',
    'Hits {}':
        'Hits {}',
    'Iemetieni %':
        'Faceoffs %',
    'play-off':
        'playoffs',
    'H2H ({} sp.): {} {}, {} {}':
        'H2H ({} gm): {} {}, {} {}',
    'netiek lietota (neuzlaboja prognozes)':
        'not used (did not improve the predictions)',
    'xG pret spēlē ⓘ':
        'xG against per game ⓘ',
    'iepriekšējās sezonās {} spēles':
        'previous seasons {} games',
    '{} ↔ {} · {}':
        '{} ↔ {} · {}',
    '✈️ lidojums {}':
        '✈️ flight {}',
    '🚌 autobuss {}':
        '🚌 bus {}',
    '✈️ lidojums':
        '✈️ flight',
    '🚌 autobuss':
        '🚌 bus',
    'laika joslu starpība {} h':
        'time zone difference {} h',
    '· laika josla {}{} h':
        '· time zone {}{} h',
    'Virs normas (z)':
        'Above norm (z)',
    'viesu':
        'away',
    'Tirgi':
        'Markets',
    'Gaida':
        'Pending',
    'Statuss':
        'Status',
    '{}-{}-{} (W-L-P) · gaida {}':
        '{}-{}-{} (W-L-P) · pending {}',
    'Bankrols (Kelly)':
        'Bankroll (Kelly)',
    'Bankrols {}':
        'Bankroll {}',
    '· {} · {} vien.':
        '· {} · {} u.',
    '· {} vien.':
        '· {} u.',
    'Uzvara':
        'Win',
    'Atgriezta':
        'Push',
    'Gala':
        'Final',
    'Augsta':
        'High',
    'Zema':
        'Low',
    'Sitieni':
        'Hits',
    'Bukmeikers':
        'Bookmaker',
    'Bīstamākais vairākums (xG/sp)':
        'Most dangerous power play (xG/gm)',
    'Labākais mazākums (xG pret/sp)':
        'Best penalty kill (xGA/gm)',
    'der':
        'qualifies',
    'Topi':
        'Top lists',
    'Skats':
        'View',
    'Autors':
        'Scorer',
    'Speletajs':
        'Player',
    'Vartsargs':
        'Goalie',
    'Poz':
        'Pos',
    'pretinieki {}':
        'opponents {}',
    'Sp.':
        'GP',
    'GSAx/sp':
        'GSAx/gm',
    'ixG/sp':
        'ixG/gm',
    'xG ±/sp':
        'xG ±/gm',
    'xG/sp':
        'xG/gm',
    'Krāsa – vieta šajā tabulā: zaļa – labākā ceturtdaļa, zila – virs vidējā, dzeltena – zem vidējā, sarkana – sliktākā ceturtdaļa.':
        'Color – rank in this table: green – top quarter, blue – above the middle, yellow – below the middle, red – bottom quarter.',
}
