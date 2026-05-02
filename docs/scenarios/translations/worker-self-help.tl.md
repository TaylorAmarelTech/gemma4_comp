# OFW / migranteng manggagawa — sarili mong tulong sa sarili mong telepono

> ⚠ **TRANSLATION DRAFT — REVIEW BY NATIVE TAGALOG SPEAKER NEEDED.**
> This Tagalog draft is provided as a starting point so a Filipino
> caseworker / OFW community organizer can review + correct + ship.
> The English original at
> [`worker-self-help.md`](../worker-self-help.md) is the canonical
> version; this translation has not yet been reviewed for accuracy
> or for legal-phrasing precision. **Do not rely on it for actionable
> legal advice without checking against the English version + the
> source statutes.** Native-speaker editors please open a PR with
> corrections.
>
> ⚠ **DRAFT NG PAGSASALIN — KAILANGAN NG REVIEW NG NATIVE NA TAGAPAGSALITA NG TAGALOG.**
> Ang draft na ito ay ibinibigay bilang panimulang punto. Ang orihinal
> sa Ingles ay siyang opisyal; hindi pa naseguro ang katumpakan ng
> mga legal na termino dito. **Huwag asahan ito para sa mga aktwal
> na legal na payo nang hindi muna sumusuri sa orihinal na Ingles
> at sa mga batas na nasusulat doon.**

---

> **Sino ka.** Ikaw ay isang migranteng manggagawa — Pilipino,
> Indonesian, Nepali, Bangladeshi, o galing sa iba pang corridor.
> May recruiter na naniningil sa iyo ng bayad. May kontrata ka. Hindi
> mo alam kung legal ang mga bayad. Hindi mo nagtitiwala sa
> recruiter mo. Kailangan mo ng impormasyong masusuri mo sa sarili
> mong telepono, nang walang nakakakita kung ano ang itinatanong mo.
>
> **Anong ibinibigay nito sa iyo.** Isang libreng app sa Android na
> maaari mong i-install sa anumang modernong telepono. Lahat ng
> bagay nananatili sa telepono mo. Walang account, walang email,
> walang telemetry. Ginawa para sa mga migrante ng mga taong nag-aral
> ng recruitment-fee fraud at sapilitang trabaho sa loob ng maraming
> taon.
>
> **Ano ang HINDI ito.** Hindi ito abogado. Hindi nito maaaring
> ipaglaban ang kaso mo sa korte. Hindi nito kayang palitan ang
> labor regulator ng bansa mo o ang NGO sa destinasyon mo. Ang
> kaya nitong gawin ay tulungan kang mabilisang hanapin ang batas,
> i-document ang ebidensiya, at gumawa ng packet na maibibigay mo
> sa abogado o NGO.

## Plain-language paliwanag

Limang bagay ang ginagawa ng app:

1. **Chat** — magtanong tungkol sa kontrata mo, bayad, recruiter,
   employer. Iquote nito ang aktwal na batas na umaaplay sa bansa
   at corridor mo.
2. **Journal** — magtago ng pribadong rekord ng bawat pulong, bayad
   na binayaran, mensahe galing recruiter, larawan ng kontrata.
   Naka-encrypt sa telepono mo.
3. **Reports** — tingnan kung anong mga batas ang baka nilabag sa
   kaso mo, ano ang legal fee caps para sa corridor mo, at aling
   mga NGO ang tumutulong sa mga manggagawa sa destinasyong bansa
   mo.
4. **Refund claims** — kung ang isang bayad na binayaran mo ay
   illegal, mag-i-draft ang app ng cover letter para sa refund
   claim, na may tamang batas, tamang regulator, at tamang contact
   info.
5. **Panic wipe** — isang tap ay magbubura ng lahat. Para sa
   panahon na kailangan mong magmukhang malinis ang telepono.

Lahat nangyayari sa telepono mo. Walang ipinapadala sa anumang
kumpanya, kasama na ang mga taong gumawa ng app, hangga't hindi
ka nagpapasiyang i-share ng report mismo.

## I-install

1. Sa Android phone mo, buksan ang browser.
2. Pumunta sa: **https://github.com/TaylorAmarelTech/duecare-journey-android/releases**
3. I-tap ang pinakabagong `.apk` na file (e.g.,
   `duecare-journey-v0.9.0-twenty-corridors-new-rules.apk`).
4. Payagan ang "Install unknown apps" kung tinanong (kailangan ito
   dahil hindi pa nasa Play Store ang app — sinasadya ito, ang
   Play Store ay mangangailangan ng Google account; ayaw naming
   kailanganin mo nito).
5. Buksan ang app.

Sa unang pagbukas, dalawa ang itatanong:
- **Saan ka sa journey mo?** (Bago umalis, in transit, dumating,
  may trabaho, exit)
- **Anong corridor?** (e.g., Pilipinas → Hong Kong, Pilipinas →
  Italya, Pilipinas → Saudi)

Iyan lang ang setup. Walang account creation. Walang email field.
Hindi tinatanong ng app kung sino ka.

## Gamitin sa unang araw — quick guided intake

Buksan ang **Journal** tab. Makikita mo ang button sa itaas:
**Quick guided intake**. I-tap.

Gabayan ka ng app sa 10 tanong:

1. Sino ang recruiter mo? (Pangalan, ahensya, sino ang nag-introduce)
2. May lisensya ba sila? (POEA / DMW number)
3. Anong mga bayad ang binayaran mo? (Halaga, currency, ano ang tawag nila)
4. Kumuha ka ba ng utang? (Halaga, interest rate, sino ang nagpautang)
5. Pumirma ka ba ng kontrata? (Oo/hindi, anong wika)
6. Anong sahod ang ipinangako?
7. Nasaan ang passport mo ngayon?
8. Alam mo ba ang employer mo? (Pangalan, address)
9. Malaya ka bang tumawag sa pamilya mo? (Telepono, gaanong
   kadalas)
10. May nagpresure / nag-threaten ba sa iyo? (Recruiter, sub-agent,
    employer)

Lampasan ang tanong na hindi mo alam ang sagot. Bawat sagot ay
nagiging journal entry, awtomatikong na-tag sa mga pattern na
itinugma niya.

Pagkatapos, i-tap ang **Reports**.

## Anong ipinapakita ng Reports tab

- **Case overview** — ilang entries, ilang fee lines, ilang risk flags
- **ILO indicators** — alin sa 11 international forced-labor
  indicators ang nag-aaplay sa kaso mo (passport withholding, debt
  bondage, threats, atbp.)
- **Detailed findings** — para sa bawat pattern na nagprokurer, anong
  batas ang kaugnay nito at ano ang dapat mong gawin susunod
- **Fee table** — bawat bayad na nasubaybayan, may flag kung ang
  bayad ay illegal sa ilalim ng batas ng corridor mo
- **Refund claims** — para sa bawat illegal fee, isang button na
  "Start refund claim" na nag-i-draft ng paperwork

I-tap ang **Generate intake document**. Gagawa ang app ng isang
dokumento na pinagsasama-sama ang lahat ng nasa itaas — naka-format
bilang bagay na maipapakita mo sa isang abogado, NGO, o government
regulator.

## Anong i-share, kanino, kailan

| Gusto mong... | Anong i-share | Kanino |
|---|---|---|
| Tingnan kung lisensyado ang recruiter mo | Lisensiya number lang | Opisyal na regulator (DMW: dmw.gov.ph) |
| Alamin kung illegal ang isang bayad | Generated intake document | NGO na humahawak sa corridor mo |
| Mag-file ng refund claim | Drafted refund-claim cover letter | Origin-country labor regulator |
| Kumuha ng legal help | Generated intake document | Legal aid clinic sa destinasyon |
| Manatiling ligtas | Huwag pa magshare — patuloy na buuin ang record mo | n/a |
| Nasa aktibong panganib ka | Hotline number para sa destinasyon | Ipinapakita ng app ang tamang hotline |

**Hindi kailanman** awtomatikong nagsesend ang app ng anuman. Bawat
share ay desisyon mo.

## Privacy — anong inaasahan

- **Walang umaalis sa telepono mo maliban kung i-tap mo ang Share.**
  Hindi nagsesend ang app ng analytics. Hindi nagsesend ng crash
  reports. Ang tanging outbound network call sa default ay ang
  one-time download ng AI model.
- **Ang journal mo ay naka-encrypt sa telepono mo.** Kahit may
  makakuha ng telepono mo nang naka-unlock, kailangan nila ang
  secure-storage key ng telepono mo para mabasa ang journal mo.
  Pareho ng encryption na ginagamit ng mga banko.
- **Ang panic wipe ay nagbubura ng lahat sa isang tap.** Settings
  → Danger zone → Erase everything. Hindi na maibabalik.
- **Maaari kang gumamit ng peke na email kahit saan.** Hindi
  kailangan ng app. Kung gusto mong mag-share ng report,
  i-share via WhatsApp / Signal / SMS / print — pili mo.

## Anong HUWAG i-type sa app

Kahit lahat nananatili sa telepono mo:

- **Tunay na pangalan** — gamitin ang "Auntie L." sa halip ng
  buong pangalan ng recruiter. Itago sa labas ang tunay na pangalan.
- **Passport numbers** — sumulat ng "passport mula <bansa>" sa
  halip.
- **Bank account numbers** — sumulat ng "via bank transfer" sa
  halip.
- **Tukoy na address** — sumulat ng "lugar sa Causeway Bay" sa
  halip ng pangalan ng building.

Bakit: kung mawawala mo ang telepono mo, o pinilit kang i-unlock
ito, ang mga detalyeng iyon ay sensitibo. Magaling pa rin gumana
ang analysis ng app kahit walang ito.

## Ano ang HINDI kayang gawin ng app

- **Hindi ka nito mailalabas sa isang bansa.** Kung nasa
  kafala-style situation ka sa Saudi Arabia o Gulf, ipinapakita ng
  app ang contact ng embahada at lokal na NGO. Ang aktwal na
  paperwork ay nangyayari sa kanila.
- **Hindi ka kayang ipagtanggol sa korte.** Kung may legal case
  ka, tumutulong ang generated report sa abogado na mas mabilis na
  maintindihan, pero kailangan pa rin ng abogado na i-file ang
  kaso.
- **Hindi nito magagarantiyahan na tama ang sagot.** Nagkakamali
  ang AI. Laging suriin ang naka-cite na batas laban sa opisyal
  na source bago kumilos. Ipinapakita sa iyo ng app ang source
  para sa lahat ng sinasabi nito.
- **Hindi gagana nang walang internet sa UNANG install.** Ang
  one-time model download (~1.5 GB) ay nangangailangan ng Wi-Fi.
  Pagkatapos noon, gagana ang app nang ganap na offline.
- **Hindi nito mapapalitan ang common sense.** Kung may pakiramdam
  na may mali, magtiwala sa instinct mo. Makipag-usap sa taong
  pinagkakatiwalaan mo bago magbayad ng anumang bayad.

## Mga wika

Tinatanggap ng chat surface ang anumang wika na naiintindihan ng
Gemma 4, na kasama ang mga pangunahing migrant-corridor language:
English, Tagalog, Bahasa Indonesia, Bahasa Malaysia, Nepali, Bangla,
Hindi, Urdu, Tamil, Sinhala, Arabic, Vietnamese, Khmer, Thai,
Burmese, Mandarin, Cantonese, Korean, Japanese.

Ang interface labels ng app ay English-only sa ngayon (idadagdag ng
v1.0 ang multi-language UI). Maaari kang mag-chat sa wika mo; ang
mga buttons ay nananatili sa English.

## Anong gagawin kung nakita ng recruiter ang app sa telepono mo

Ang icon ng app ay **"Duecare Journey"** na may generic na asul na
libro. Hindi sinasabi sa kahit saan sa home screen ang
"anti-trafficking". Maaari mong ilipat ito sa folder kasama ang
ibang apps para hindi gaanong kapansin-pansin.

Kung pinipilit kang i-delete: **Settings → Panic wipe**. Maaaring
panoorin ng recruiter habang ginagawa mo ito; nagbubura ang app
agad-agad. I-install muli mamaya kapag ligtas na.

Kung kinukuha sa iyo ang telepono: ang journal ay naka-encrypt;
walang ipinapakita ang panic-wiped state na nag-install ka noon.
Nakikita ng recruiter ang isang telepono na walang Duecare app.

## Anong gastos

$0. Magpakailanman. Open source ang app. Hindi nagbebenta ng
anuman ang team na gumawa nito.

(May one-time data cost para sa model download — mga ₱350 sa Globe
prepaid, libre sa Wi-Fi. Magbabala sa iyo ang app tungkol dito
bago mag-download.)

## Kailan dapat kausap mo ang isang tao sa halip

- **Aktibong nasa pisikal na panganib ka** — tumawag sa 911 / 999
  (karamihan ng bansa) o sa emergency number ng destinasyong bansa.
- **Hindi binayaran ang sahod mo nang ilang buwan na** — ang
  destinasyong bansa ay may labour ministry tribunal na
  nakikinig ng wage claims kahit anong status ng immigration. May
  ipinapakita ang app na contact.
- **May kapamilya na hawak sa ibang bansa** — humawak ng kaso
  ang international NGO (Polaris Project, IJM, Anti-Slavery
  International). Ina-link sila ng app per corridor.

Ang app ay para sa **pagbuo ng iyong record + paghahanap ng
tamang taong kausapin**. Hindi ito kapalit ng taong iyon.

---

## Para sa native Tagalog speaker editors

Mga partikular na lugar na nangangailangan ng pag-review:

1. **Mga legal na termino** — naka-translate ba ang "placement
   fee," "recruitment fee," "training fee," "kafala," "huroob,"
   "absconder" sa paraang mauunawaan ng OFW na hindi pamilyar sa
   English legal vocabulary?
2. **NGO contact references** — ipinapanatili ba ang
   katumbas-pangalan o kailangan ng paliwanag (e.g., "Mission for
   Migrant Workers HK = isang NGO sa HK na tumutulong sa mga
   manggagawa")?
3. **Tono** — nasa katumbas na neutral / matter-of-fact tone tulad
   ng Ingles? O kailangan ng mas informal / kapatiran-style?
4. **Idiomatic adjustments** — may mga English phrases na nangangailangan
   ng totoong Filipino paraphrase, hindi literal translation
   (e.g., "harm reduction, not paternalism" — paano natin ito
   sasabihin sa Tagalog na maiintindihan ng OFW?)
5. **Regional variants** — kailangan ba natin ng Cebuano /
   Bisaya / Hiligaynon na variants?

PRs welcome via https://github.com/TaylorAmarelTech/gemma4_comp/issues
or email amarel.taylor.s@gmail.com (subject: `[duecare translation tagalog]`).
