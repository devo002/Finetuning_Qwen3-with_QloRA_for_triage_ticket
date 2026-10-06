# Real tickets with proposed labels

Rows marked ⚠ are ambiguous; see the note under them.

## T-10001   (email)

**Subject:** rote LED am Wechselrichter!!!

**Body:** Hallo Empire, mein Wechselrichter (Huawei) blinkt rot und in der App steht Fehler 0x0001. Wir haben heute Morgen kurz keinen Strom gehabt im ganzen Haus. Was sollen wir tun? Liebe Grüße

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| 0x0001 | Huawei | high | fault | solar | de |

## T-10002 ⚠  (email)

**Subject:** solar inverter not working after heavy rain

**Body:** Hi — my Huawei inverter has been showing a yellow LED since yesterday afternoon. The app says Error 501 DC insulation fault. We had a heavy storm on Sunday. The panels look fine from the ground but something is clearly wrong. Can someone come and check it out?

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| 501 | Huawei | medium | fault | solar | en |

> Note: severity: no statement that the inverter is off; DC insulation faults often stop it (could be high)

## T-10003   (phone-transcript)

**Subject:** solar keeps cutting out around midday

**Body:** The system works fine in the morning and evening but between noon and 2pm it shuts off every single day. The app shows Error 602 Grid Voltage. We have a very long cable run to the meter box — about 30 meters. This has been happening all week and I'm losing a lot of generation time.

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| 602 | None | medium | fault | solar | en |

## T-10004   (email)

**Subject:** inverter making a grinding noise

**Body:** My SMA Sunny Boy has been making a loud grinding noise for the past few days, especially when it's sunny and output is high. The app shows Warning 410 which seems to be a fan issue. It's still producing power but I'm worried it might break down. Can someone take a look?

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| 410 | SMA | medium | fault | solar | en |

## T-10005   (email)

**Subject:** no hot water or heating — urgent!!

**Body:** Please help — the heat pump stopped working this morning. No hot water and the heating is completely cold. The display is showing F.22. We have two young children at home. Is there any way someone can come out today? This is really urgent for us.

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| F.22 | None | high | fault | heatpump, refrigerant, brazing | en |

## T-10006 ⚠  (email)

**Subject:** battery showing offline in app

**Body:** Hello, my hybrid solar system seems to be working fine for generation but the Goodwe app shows the battery as offline. It says Error 115. Solar is still feeding the grid normally. Not an emergency but I'd like to get it sorted — the whole point of the battery is to use overnight and right now I can't.

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| 115 | Goodwe | medium | fault | battery | en |

> Note: skills: 'hybrid' is also plausible

## T-10007 ⚠  (email)

**Subject:** inverter keeps restarting every few hours

**Body:** Our Fronius Symo inverter (6 years old) has been restarting itself every few hours since yesterday. It shows status code 1010 each time. The house lights flicker briefly when it happens. It's been going on all day and I'm worried something is seriously wrong.

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| 1010 | Fronius | medium | fault | solar | en |

> Note: severity: customer sounds worried, flickering lights; medium vs high

## T-10008   (phone-transcript)

**Subject:** Viessmann morgens Fehler A9

**Body:** Wärmepumpe Viessmann Vitocal zeigt morgens A9 wenn es kalt war. Nach ein paar Stunden geht sie wieder. Heizen tut sie aber dann doch normal.

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| A9 | Viessmann | medium | fault | heatpump | de |

## T-10009   (email)

**Subject:** battery won't charge past 90

**Body:** My LFP battery won't charge above 90 percent for the last week. No specific error in the app, just stops there. System is from 2023.

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| None | None | medium | fault | battery | en |

## T-10010 ⚠  (email)

**Subject:** Wallbox lädt nicht mehr

**Body:** Unsere Empire Wallbox lädt das Auto nicht mehr seit gestern Nacht. LED leuchtet aber blau (sollte grün sein). Auto ist ein VW ID.4.

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| None | None | medium | fault | commissioning | de |

> Note: no EV skill tag exists; 'commissioning' is a guess

## T-10011 ⚠  (email)

**Subject:** App keeps disconnecting

**Body:** The FusionSolar app keeps showing 'inverter offline' but the inverter itself is running. Maybe a wifi issue? Not really an emergency.

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| None | Huawei | low | fault | solar | en |

> Note: brand inferred from 'FusionSolar' app (not named); severity low since inverter runs

## T-10012 ⚠  (email)

**Subject:** Anlage produziert weniger als letztes Jahr

**Body:** Hallo, wir bekommen weniger Ertrag als letztes Jahr im April. Liegt es an Verschmutzung? Können sie einen Termin für Reinigung machen?

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| None | None | low | general | - | de |

> Note: cleaning appointment request; general vs fault

## T-10013   (email)

**Subject:** Vaillant Wärmepumpe sehr laut

**Body:** Die Wärmepumpe ist seit ein paar Tagen viel lauter geworden, besonders wenn sie startet. Nachbarn beschweren sich schon. Kein Fehlercode in der App.

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| None | Vaillant | medium | fault | heatpump | de |

## T-10014   (email)

**Subject:** RE: RE: error 602 still happening

**Body:** Hi - I reported error 602 last week, someone said you'd send a tech but no one came. Still happening every day around noon. This is the third time I'm writing.

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| 602 | None | medium | fault | solar | en |

## T-10015   (email)

**Subject:** neue Anlage komplett aus

**Body:** Anlage wurde letzten Monat installiert und produziert seit gestern 0 kWh. Wechselrichter zeigt Error 301 (SMA Sunny Boy). Display blinkt durchgehend.

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| 301 | SMA | high | fault | solar | de |

## T-10016 ⚠  (email)

**Subject:** Smoke smell from inverter cabinet??

**Body:** We just noticed a slight burning smell near the inverter in the basement. The inverter is still running. Should we turn something off? This feels urgent.

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| None | None | high | fault | solar | en |

> Note: training convention for smoke is ['solar','battery']; ticket only mentions the inverter

## T-10017   (email)

**Subject:** Frage zur Einspeisevergütung

**Body:** Hallo, wie lange dauert es bis die EEG-Anmeldung bestätigt ist? Habe vor 6 Wochen die Unterlagen geschickt aber noch nichts gehört.

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| None | None | low | general | - | de |

## T-10018 ⚠  (email)

**Subject:** F.22 wieder

**Body:** Wärmepumpe Vaillant aroTHERM zeigt schon wieder F.22, gleiches Problem wie im Januar. Es war damals ein Leck, vielleicht ist es wieder so?

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| F.22 | Vaillant | medium | fault | heatpump, refrigerant, brazing | de |

> Note: severity: no statement whether heating works; previous cause was a leak

## T-10019   (email)

**Subject:** Goodwe app login funktioniert nicht

**Body:** Komme nicht mehr in die Goodwe app rein, Passwort wurde abgelehnt. Wer kann das zurücksetzen?

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| None | Goodwe | low | general | - | de |

## T-10020 ⚠  (email)

**Subject:** Optimizer-Fehler einzelnes Modul

**Body:** FusionSolar zeigt einen einzelnen Optimizer auf dem Dach als 'kommunikationslos'. Anlage läuft sonst normal. Optimizer ist auf Modul 14 von 20.

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| None | Huawei | medium | fault | solar, optimizer | de |

> Note: brand inferred from 'FusionSolar'

## T-10021 ⚠  (email)

**Subject:** huawei error 501 after storm

**Body:** Big thunderstorm last night. This morning Huawei inverter shows yellow LED, error 501. PV cables on roof look ok from ground.

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| 501 | Huawei | medium | fault | solar | en |

> Note: same severity question as T-10002

## T-10022   (email)

**Subject:** Termin verschieben

**Body:** Können wir den Termin von übermorgen auf nächste Woche verschieben? Wir sind nicht zuhause.

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| None | None | low | reschedule | - | de |

## T-10023 ⚠  (email)

**Subject:** App zeigt 0 Watt obwohl Sonne

**Body:** App zeigt 0 Watt Erzeugung obwohl heute schöner sonniger Tag. Wechselrichter Display zeigt aber 3.2 kW. Welche Daten stimmen?

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| None | None | low | general | - | de |

> Note: monitoring data mismatch; general vs fault

## T-10024 ⚠  (email)

**Subject:** battery wrong reading

**Body:** The Goodwe app says battery is at 100% all the time, even at night. Pretty sure that's wrong since solar is the only source.

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| None | Goodwe | low | fault | battery | en |

> Note: wrong app reading; fault vs general, severity low

## T-10025 ⚠  (email)

**Subject:** Überspannungsschutz ausgelöst nach Blitz

**Body:** Letzte Nacht Blitzeinschlag in der Nähe. Heute morgen sehe ich dass der SPD im Sicherungskasten rot anzeigt (war grün). Anlage läuft, aber sollte das gewechselt werden?

| error_code | manufacturer | severity | intent | skills | language |
|---|---|---|---|---|---|
| None | None | medium | fault | solar | de |

> Note: SPD tripped, system runs; medium by convention
