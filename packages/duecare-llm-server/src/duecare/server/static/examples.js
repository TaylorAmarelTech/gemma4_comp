// Curated example library used across the demo pages. Click an example
// card to populate the input above. Examples chosen to show:
//   - clearly suspicious (severity 7-10)
//   - subtly suspicious (severity 3-6)
//   - clearly legitimate (severity 0-2)
//   - non-English locales (Tagalog, Indonesian, Hindi)
//   - file-style content (chat logs, contract clauses)
//
// Each entry: { title, severity_hint, locale, text }

window.DUECARE_EXAMPLES = {
  enterprise: [
    { title: "Suspicious recruitment post (English)",
      severity_hint: "block", locale: "en",
      text: "Pacific Coast Manpower Inc. is hiring 50 domestic workers " +
            "for Riyadh, Saudi Arabia. USD 5,000 placement fee payable " +
            "to account TEST-9988-7766-5544. We will keep your passport " +
            "until you finish 2 years. Send your passport copy to " +
            "recruitment@pacificcoast.demo." },
    { title: "Subtle scam (English)",
      severity_hint: "review", locale: "en",
      text: "URGENT: 30 caregivers needed in Hong Kong. Free placement " +
            "(small processing fee USD 800). Trust me, the agency boss " +
            "will help you with everything. Send your NBI clearance and " +
            "passport scan to whatsapp +85295551234." },
    { title: "Tagalog recruitment ad (suspicious)",
      severity_hint: "block", locale: "ph",
      text: "URGENT! Kailangan ng 100 OFW para sa Saudi Arabia. " +
            "Walang placement fee pero magdedeposit lang kayo ng USD " +
            "5,000 deposit muna. Ihahawak ang passport namin until " +
            "matapos ang contract. Bawal lumabas without permission. " +
            "Mag-message kay Mama-san." },
    { title: "Legitimate POEA-licensed posting",
      severity_hint: "pass", locale: "ph",
      text: "Pacific Source Manpower Corp. (POEA-LIC-067, valid until " +
            "2027) is recruiting for caregiving positions in Singapore. " +
            "No placement fee per RA 8042. Free PDOS. Official receipt " +
            "for all transactions. Contact us at +63-2-8888-1234 or visit " +
            "deg.com/job/PCS-2026-08." },
    { title: "Indonesian recruitment scam",
      severity_hint: "block", locale: "id",
      text: "PENTING: Lowongan kerja di UAE untuk pembantu rumah " +
            "tangga. Bayar deposit USD 3,000 dulu, paspor akan " +
            "disimpan oleh agensi sampai kontrak selesai. Tidak boleh " +
            "keluar sendirian. Hubungi WhatsApp +9715551234567." },
    { title: "Job ad with passport-confiscation language",
      severity_hint: "block", locale: "en",
      text: "Filipino domestic helper needed for Riyadh family. " +
            "Salary SAR 1,500/month. We hold the passport for " +
            "safekeeping during the 2-year contract. Worker lives " +
            "with the employer, no day off, alone in the house. " +
            "Sponsor visa under kafala system." },
    { title: "Borderline: small fee, vague licence",
      severity_hint: "review", locale: "en",
      text: "Looking to hire 5 Filipino housekeepers for the UAE. " +
            "Just a small documentation fee of USD 200. We are an " +
            "official agency, do not worry. Send your passport copy " +
            "to start the process." },
    { title: "Clearly safe job posting",
      severity_hint: "pass", locale: "en",
      text: "Hospitality vacancies in Singapore (cooks, waiters). " +
            "Direct hiring by Marina Hotel Group, no agency fee. " +
            "Apply via the Singapore MOM jobs portal. POEA-LIC-101 " +
            "verified. Tax-paid official receipts for all transactions." },
  ],

  individual: [
    { title: "Mama-san wants my passport (English)",
      severity_hint: "high", locale: "ph",
      text: "Mama-san said I must pay USD 5,000 deposit and she will " +
            "keep my passport until I finish 2 years. She said the " +
            "agency boss will help me, but I cannot leave the house " +
            "alone." },
    { title: "Tagalog -- threatening recruiter",
      severity_hint: "high", locale: "ph",
      text: "Sabi ng recruiter, kailangan kong magbayad ng PHP " +
            "250,000 muna bago mag-fly. Sabi niya ihahawak ang " +
            "passport ko, at hindi pwede tumawag sa pamilya ko hangga't " +
            "hindi ako nagsisimula sa trabaho." },
    { title: "Hindi -- agency demanding deposit",
      severity_hint: "high", locale: "in",
      text: "Agency aunty said I must deposit INR 2,00,000 and they " +
            "will keep my passport until 2 years. They will send me " +
            "to UAE for housekeeping. They said no contact with my " +
            "family until I finish." },
    { title: "Suspicious WhatsApp recruiter",
      severity_hint: "high", locale: "en",
      text: "Hi sister! I have urgent placement for you in Saudi. " +
            "Just send your passport copy to me on WhatsApp +9665551234. " +
            "Pay USD 3,000 release fee and we book your flight. We " +
            "will hold the passport at the agency office for safekeeping." },
    { title: "Already deployed -- needing help",
      severity_hint: "high", locale: "hk",
      text: "I am Sita from Nepal. I came to Hong Kong as a domestic " +
            "worker. The employer took my passport and I cannot leave " +
            "the house. They make me work 18 hours and pay me only " +
            "HKD 2,000 a month. I owe HKD 25,000 to the agency." },
    { title: "Contract terms with red flags",
      severity_hint: "high", locale: "en",
      text: "The contract says: salary withheld for first 3 months as " +
            "training fee. Worker not allowed to leave employer's " +
            "home alone. Passport deposited with agency for " +
            "safekeeping during contract term. Termination penalty " +
            "USD 8,000." },
    { title: "Borderline -- some warning signs",
      severity_hint: "medium", locale: "en",
      text: "The agency wants USD 800 for documentation. They asked " +
            "me to send passport copy and NBI clearance via WhatsApp. " +
            "They said it is a normal process and I should trust them." },
    { title: "Looks safe (POEA-licensed)",
      severity_hint: "low", locale: "ph",
      text: "Kausap ko si Atty. Cruz from Pacific Source Manpower " +
            "Corp (POEA-LIC-067). Free training, walang placement " +
            "fee, may official receipt. POEA-licensed, ratified by " +
            "DEG, ILO C181 compliant." },
    { title: "Indonesian -- fee request",
      severity_hint: "high", locale: "id",
      text: "Boss agen bilang aku harus bayar deposit USD 5,000 dulu, " +
            "dan paspor akan disimpan agensi sampai kontrak selesai. " +
            "Aku tidak boleh keluar sendirian dari rumah majikan." },
    { title: "Innocent question",
      severity_hint: "low", locale: "en",
      text: "I am thinking about working as a caregiver in Canada. " +
            "What are the legitimate steps? How do I verify if an " +
            "agency is licensed?" },
  ],

  knowledge: [
    "What is the average illicit fee?",
    "How many complaints does Pacific Coast Manpower have?",
    "Has there been changes in how fees are collected recently?",
    "Show me the top suspected bad actors",
    "What worrisome trends are occurring?",
    "Which documents mention Pacific Coast Manpower?",
    "Which agencies have the most complaints?",
    "What are the most common scheme patterns?",
    "Show me fee trends over time",
    "Find all flagged forced-labor indicators",
  ],
};
