# OFW / migrant worker — self-help on your own phone

> **Persona.** You're a migrant worker — Filipino, Indonesian,
> Nepali, Bangladeshi, or any other corridor. A recruiter is
> charging you fees. You have a contract. You don't know if the
> fees are legal. You don't trust your recruiter. You need
> information you can verify, on your phone, without anyone else
> seeing what you ask.
>
> **What this gives you.** A free Android app you can install on
> any modern phone. Everything stays on your phone. No account,
> no email, no telemetry. Built for migrants by people who have
> spent years studying recruitment-fee fraud and forced labor.
>
> **What it is NOT.** It's not a lawyer. It can't fight your case
> in court. It cannot replace your country's labor regulator or
> your destination country's NGO. What it can do is help you look
> up the law fast, document evidence, and produce a packet you
> can hand to a lawyer or NGO.

## Plain-language explanation

The app does five things:

1. **Chat** — ask any question about your contract, fees, recruiter,
   employer. It cites the actual law that applies to your country
   and corridor.
2. **Journal** — keep a private record of every meeting, fee paid,
   message from your recruiter, photo of your contract. Encrypted
   on your phone.
3. **Reports** — see which laws may have been broken in your case,
   what the legal fee caps are for your corridor, and which NGOs
   help workers in your destination country.
4. **Refund claims** — if a fee you paid was illegal, the app drafts
   the cover letter for a refund claim, with the right statute,
   the right regulator, and the right contact info.
5. **Panic wipe** — one tap erases everything. For when you need
   the phone to look clean.

Everything happens on your phone. Nothing is sent to any company,
including the people who built the app, unless you choose to share
a report yourself.

## Install

1. On your Android phone, open the browser.
2. Go to: **https://github.com/TaylorAmarelTech/duecare-journey-android/releases**
3. Tap the latest `duecare-journey-v0.7.0-quality-and-claims.apk`.
4. Allow "Install unknown apps" if prompted (it's needed because
   the app is not in the Play Store yet — that's deliberate, the
   Play Store would require a Google account; we don't want you
   to need one).
5. Open the app.

The first time you open it, it asks two questions:
- **Where are you in your journey?** (Pre-departure, in transit,
  arrived, employed, exit)
- **Which corridor?** (e.g., Philippines → Hong Kong)

That's the only setup. There's no account creation. There's no
email field. The app never asks who you are.

## Use it on day 1 — quick guided intake

Open the **Journal** tab. You'll see a button at the top: **Quick
guided intake**. Tap it.

The app walks you through 10 questions:

1. Who is your recruiter? (Name, agency, who introduced you)
2. Do they have a license? (POEA / BMET / BP2MI / DoFE number)
3. What fees have you paid? (Amount, currency, what they called it)
4. Did you take a loan? (Amount, interest rate, who lent it)
5. Did you sign a contract? (Yes/no, what language)
6. What wage was promised?
7. Where is your passport now?
8. Do you know your employer? (Name, address)
9. Are you free to call your family? (Phone, frequency)
10. Has anyone threatened you? (Recruiter, sub-agent, employer)

Skip any question you don't know the answer to. Each answer becomes
a journal entry, automatically tagged with the patterns it matches.

When you finish, tap **Reports**.

## What the Reports tab shows you

- **Case overview** — how many entries, how many fee lines, how
  many risk flags
- **ILO indicators** — which of the 11 international forced-labor
  indicators apply to your case (passport withholding, debt bondage,
  threats, etc.)
- **Detailed findings** — for each pattern that fired, what statute
  it relates to and what your next step should be
- **Fee table** — every fee tracked, with a flag if the fee is
  illegal under your corridor's law
- **Refund claims** — for each illegal fee, a "Start refund claim"
  button that drafts the paperwork

Tap **Generate intake document**. The app makes a single document
combining all of the above — formatted as something you can show
to a lawyer, NGO, or government regulator.

## What to share, with whom, when

| You want to... | What to share | With whom |
|---|---|---|
| Check if your recruiter is licensed | Just the license number | The official regulator (POEA: dmw.gov.ph, BMET: bmet.gov.bd, BP2MI: bp2mi.go.id) |
| Know if a fee is illegal | Generated intake document | NGO that handles your corridor (the app shows you which) |
| File a refund claim | Drafted refund-claim cover letter | Origin-country labor regulator |
| Get legal help | Generated intake document | Legal aid clinic in your destination country |
| Stay safe | Don't share anything yet — keep building your record | n/a |
| Are in active danger | Hotline number for your destination country | The app shows the right hotline based on your corridor |

The app **never** auto-sends anything. Every share is your decision.

## Privacy — what to expect

- **Nothing leaves your phone unless you tap Share.** The app
  doesn't send analytics. It doesn't send crash reports. The only
  outbound network call by default is the one-time download of
  the AI model.
- **Your journal is encrypted on your phone.** Even if someone
  gets your phone unlocked, they need your phone's secure storage
  key to read your journal. The encryption is the same kind banks
  use.
- **Panic wipe erases everything in one tap.** Settings → Danger
  zone → Erase everything. Cannot be recovered.
- **You can use a fake email everywhere.** The app doesn't need
  one. If you want to share a report, share it via WhatsApp /
  Signal / SMS / print — your choice.

## What to NEVER type into the app

Even though everything stays on your phone:

- **Real names** — use "Auntie L." instead of the recruiter's full
  name. Keep the real name written down somewhere offline.
- **Passport numbers** — note "passport from <country>" instead.
- **Bank account numbers** — note "via bank transfer" instead.
- **Specific addresses** — note "Causeway Bay area" instead of
  the building name.

Why: if you ever lose your phone, or someone forces you to unlock
it, those details are sensitive. The app's analysis works fine
without them.

## What the app cannot do

- **Cannot get you out of a country.** If you're in a kafala-style
  situation in Saudi Arabia or the Gulf, the app shows you the
  embassy contact and the local NGO. The actual paperwork happens
  with them.
- **Cannot represent you in court.** If you have a legal case,
  the generated report helps a lawyer get up to speed faster, but
  a lawyer still has to file the case.
- **Cannot guarantee its answers are correct.** AI makes mistakes.
  Always check the cited law against the official source before
  acting. The app shows you the source for everything it says.
- **Cannot work without internet for the FIRST install.** The
  one-time model download (~1.5 GB) needs Wi-Fi. After that, the
  app works fully offline.
- **Cannot replace common sense.** If something feels wrong, trust
  your instincts. Talk to someone you trust before paying any fee.

## Languages

The chat surface accepts any language Gemma 4 understands, which
includes the major migrant-corridor languages: English, Tagalog,
Bahasa Indonesia, Bahasa Malaysia, Nepali, Bangla, Hindi, Urdu,
Tamil, Sinhala, Arabic, Vietnamese, Khmer, Thai, Burmese, Mandarin,
Cantonese, Korean, Japanese.

The app's interface labels are English-only for now (v0.8 will
add multi-language UI). You can chat in your own language; the
buttons stay in English.

## What to do if the recruiter sees the app on your phone

The app's icon is **"Duecare Journey"** with a generic blue book.
It does not say "anti-trafficking" anywhere on the home screen.
You can move it into a folder with other apps to make it less
prominent.

If pressured to delete it: **Settings → Panic wipe**. The recruiter
can watch you do this; the app erases instantly. Re-install later
when safe.

If your phone is taken from you: the journal is encrypted; nothing
in your panic-wiped state reveals it was ever installed. The
recruiter sees a phone with no Duecare app.

## What it costs

$0. Forever. The app is open source. The team that built it is
not selling anything.

(There's a one-time data cost for the model download — about ₱350
on Globe prepaid, free on Wi-Fi. The app warns you about this
before downloading.)

## When you'd benefit from talking to someone instead

- **You're in active physical danger** — call 911 / 999 (most
  countries) or the destination country's emergency number.
- **Your wages are months overdue** — your destination country's
  labour ministry has a tribunal that hears wage claims regardless
  of immigration status. The app shows you the contact.
- **A family member is being held in another country** — an
  international NGO (Polaris Project, IJM, Anti-Slavery
  International) handles this. The app links to them by corridor.

The app is for **building your record + finding the right person
to talk to**. It's not a replacement for that person.

## Adjacent reads

- For the people who help you: [`docs/scenarios/caseworker_workflow.md`](./caseworker_workflow.md)
- For the NGO that runs the office: [`docs/scenarios/ngo-office-deployment.md`](./ngo-office-deployment.md)
- The Android app's source code: https://github.com/TaylorAmarelTech/duecare-journey-android
- The latest APK download: https://github.com/TaylorAmarelTech/duecare-journey-android/releases
