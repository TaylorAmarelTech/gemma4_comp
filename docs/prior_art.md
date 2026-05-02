# Prior Art and Adjacent Work — Duecare Journey

Related projects, datasets, and academic work in the conceptual neighborhood of
Duecare Journey (on-device Gemma 4 E2B Android app for migrant-worker legal
advice + encrypted journey journal + complaint-packet generator). Items flagged
with **(cite)** are close enough that we should reference them in the writeup;
**(build-on)** means we may directly extend or interoperate.

## 1. Migrant-worker advice apps and helplines

- **Just Good Work** — https://justgood.work/. Free multi-language mobile app
  for job-seekers covering recruitment-to-return journey. Versions for Kenya->Qatar
  and Malaysia (with ETI + Our Journey NGO). Static content, no LLM/chatbot,
  no on-device AI. **Duecare differs:** generative legal Q&A grounded in 26
  ILO/national-statute RAG corpus; corridors are PH/ID/NP/BD->HK/SG/Saudi/Gulf,
  not Kenya->Qatar. **(cite)**
- **Migrasia** — https://www.migrasia.org/migration-support. NGO with case-
  handling system spanning PH/ID/Kenya across 26 sectors and 55 jurisdictions.
  Web-based, human-staffed, not an app. **Duecare differs:** offline app,
  no human in the loop, single-user device.
- **Ami Probashi (BMET, Bangladesh)** — https://amiprobashi.com/download-bmet.html.
  Government app for BMET registration, recruiter directory, career consultancy.
  No legal-advice AI, requires connectivity, account-bound. **Duecare differs:**
  no account, no telemetry, generative advice with citations.
- **Mission for Migrant Workers (MFMW HK)** — https://www.migrants.net/.
  Long-running NGO for Filipino/Indonesian DHs in Hong Kong; hotline + drop-in
  centre, no public app. **Duecare differs:** software complement to NGO
  intake, not a replacement.
- **DoFE FEIMS (Nepal)** — https://feims.dofe.gov.np/. Government grievance
  portal + companion app for tracking complaints already filed. **Duecare
  differs:** generates the complaint packet *before* filing, on-device.

## 2. Trafficking-aware LLM benchmarks and red-team datasets

- **HarmBench (CAIS)** — https://github.com/centerforaisafety/HarmBench;
  paper https://arxiv.org/abs/2402.04249. 400 harmful behaviors across
  chemical/bio, illegal activities (incl. trafficking as one row), 18 red-team
  methods x 33 LLMs. General-purpose; trafficking is not deeply specified.
  **Duecare differs:** 21K migrant-worker-specific tests with worst->best
  graded responses, plus quantified harness-off vs harness-on lift
  (+87.5/+51.2/+34.1 pp on three rubric axes). **(cite)**
- **AILuminate v1.0 / v1.1 (MLCommons)** — https://mlcommons.org/benchmarks/ailuminate/;
  paper https://arxiv.org/abs/2503.05731. 12 hazard categories incl. labor
  trafficking under "Non-Violent Crimes" and sex trafficking under "Sex-Related
  Crimes". Industry-standard but very shallow per-category. **Duecare differs:**
  one domain at full depth instead of 12 at the surface. **(cite)**
- **Polaris National Hotline data + 2017 Typology of Modern Slavery** —
  https://polarisproject.org/research-and-intelligence/. 25 trafficking
  types, 120 standardized fields. Used as taxonomy reference, not a
  benchmark. **Duecare differs:** Polaris is the upstream taxonomy we map
  onto; we cite it for definitions. **(cite)**
- **Counter-Trafficking Data Collaborative (CTDC, IOM + Polaris)** —
  https://www.ctdatacollaborative.org/. Public victim-case dataset; not
  designed for LLM eval. Useful for grounding. **(cite)**
- No prior work found that quantifies harness-off vs harness-on lift on a
  trafficking-specific evaluation rubric. This is our novel contribution.

## 3. On-device LLM apps for legal/safety advice

- **Cactus** — https://cactuscompute.com/, https://docs.cactuscompute.com/v1.12/blog/gemma4/.
  Y Combinator-backed cross-platform on-device runtime; supports Gemma 4,
  React Native/Flutter/Kotlin bindings. Sub-50 ms TTFT. **Duecare differs:**
  Cactus is the runtime category; Duecare is one possible app on top, with
  domain-specific RAG + complaint-packet workflow. We could potentially
  port to Cactus. **(build-on)**
- **Google AI Edge Gallery** — https://ai.google.dev/edge/mediapipe/solutions/genai/llm_inference/android.
  Google's reference Android app for LiteRT-LM + Gemma 4. Generic chat,
  no domain. **Duecare differs:** domain-loaded with 37 GREP rules,
  26-doc RAG corpus, 4 lookup tools. **(build-on)** — same stack.
- **OfflineLLM (jegly)** — https://github.com/jegly/OfflineLLM. Kotlin +
  Compose + llama.cpp ARM NEON. MIT-licensed reference for the runtime
  pattern. **Duecare differs:** legal-advice domain, encrypted journal,
  complaint generator. **(build-on)**
- **local-llms-on-android (dineshsoudagar)** —
  https://github.com/dineshsoudagar/local-llms-on-android. Reference for
  Gemma + LiteRT + ONNX Runtime side-by-side; useful as a baseline for
  benchmarking E2B latency on T4-class device CPUs. **(build-on)**

## 4. Documentation / evidence-collection apps for vulnerable populations

- **Tella by Horizontal** — https://tella-app.org/,
  https://github.com/Horizontal-org/Tella-Android. Open-source, encrypts
  photos/videos/audio at capture, hidden from gallery. Designed for
  HRDs/journalists in repressive environments. **Duecare differs:** Tella
  documents *what happened to others*; Duecare documents the worker's
  *own* journey + generates a structured complaint packet. SQLCipher
  pattern, panic features, and threat model are direct references.
  **(build-on)**
- **eyeWitness to Atrocities (IBA)** — https://www.eyewitness.global/.
  Encrypts media + uploads to secure evidence repository for ICC-grade
  chain of custody. **Duecare differs:** no upload — fully offline by
  design. We borrow the chain-of-custody framing. **(cite)**
- **Polaris BeFree Textline** — https://polarisproject.org/blog/2016/03/celebrating-three-years-of-the-befree-textline/.
  SMS shortcode (233733); 23% of textline conversations were from
  survivors vs 11% on phone hotline. Validates "discreet text >
  voice call" insight that motivates our Android-app form factor.
  **(cite)**
- **WITNESS Should-I-Use-This-App framework** — https://blog.witness.org/2020/02/use-documentation-app/.
  Decision tree for vulnerable-population doc apps; we should self-audit
  against it.

## 5. Academic publications on AI safety for migrant-worker contexts

- **Janie Chuang, "Exploitation Creep and the Unmaking of Human
  Trafficking Law"** — https://www.iilj.org/wp-content/uploads/2016/07/ChuangIILJColloq2014.pdf.
  Foundational legal scholarship on the labor-trafficking continuum
  Duecare's rubric implements. **(cite)**
- **GLAA Webinar, "Emerging Technology and Labour Exploitation: The
  Role of Artificial Intelligence" (Jan 2026)** —
  https://www.gla.gov.uk/publications/resources/glaa-webinars/emerging-technology-and-labour-exploitation-the-role-of-artificial-intelligence-january-2026.
  UK Gangmasters and Labour Abuse Authority; AI mostly framed as a *risk*
  to migrant workers. Duecare reframes AI as a worker-side defensive tool.
  **(cite)**
- **HRW, "The Gig Trap: Algorithmic, Wage and Labor Exploitation"
  (May 2025)** — https://www.hrw.org/report/2025/05/12/the-gig-trap/.
  Frames algorithmic systems as exploiters of vulnerable workers.
  Same diagnosis, different prescription.
- **ILO, "International Labour Migration: A Rights-Based Approach"** —
  https://ilo.org/wcmsp5/groups/public/---ed_protect/---protrav/---migrant/documents/publication/wcms_208594.pdf.
  Source for the rights-based framing in our writeup. **(cite)**
- **FAccT 2025 CRAFT, "AI Workers' Inquiry"** — https://ai-workers-inquiry.github.io/.
  No paper found at FAccT 2025 specifically on AI *for* migrant workers'
  defense; closest adjacent is workers-vs-algorithmic-control. Confirms
  Duecare sits in an under-explored niche.

## 6. Kaggle notebooks and HuggingFace Spaces in adjacent space

- **Kaggle "Global Human Trafficking" dataset (andrewmvd)** —
  https://www.kaggle.com/datasets/andrewmvd/global-human-trafficking.
  Most-trafficked Kaggle dataset for the topic; classification notebooks
  exist but no LLM-evaluation work. **Duecare differs:** generative
  evaluation + domain RAG.
- **litert-community/Gemma3-1B-IT** —
  https://huggingface.co/litert-community/Gemma3-1B-IT. Reference Gemma
  in LiteRT format (the format Duecare ships). **(build-on)**
- No HuggingFace Space found combining ILO citation + migrant-worker Q&A.
  Closest is general-purpose legal-Q&A spaces using Llama variants. Open
  niche to claim.

## 7. Refund-claim and consumer-rights automation tools

- **DoNotPay** — https://www.donotpay.com (and cited reviews). AI-powered
  consumer-rights automation: dispute letters, parking tickets, subscription
  cancellations, small-claims filings. Subscription model, US-centric, settled
  with FTC for unsubstantiated "robot lawyer" claims (FTC complaint
  https://www.ftc.gov/system/files/ftc_gov/pdf/DoNotPayInc-Complaint.pdf).
  **Duecare differs:** non-commercial, on-device, jurisdiction is PH/ID/NP/BD
  recruitment law not US consumer law, packet is filed by the worker with
  POEA/BMET/BP2MI/DoFE not auto-submitted.
- **Resolver (UK)** — https://www.resolver.co.uk/. Free complaint platform
  with templated letters and regulator-escalation paths. UK consumer law
  scope. **Duecare differs:** trafficking/recruitment not consumer goods;
  evidence collection from the worker's journey not from a single
  transaction.
- **Citizens Advice digital tools (UK)** — template letters and
  step-by-step workflows for consumer issues; human-curated. **Duecare
  differs:** generative + RAG-grounded, multi-jurisdiction.
- The "demand-letter generator" / "complaint-letter generator" pattern is
  well-established in the consumer-rights space. Duecare's novelty is
  porting the pattern to (a) labor-recruitment violations, (b) the
  PH/ID/NP/BD->HK/SG/Saudi/Gulf corridor specifically, (c) on-device with
  no cloud upload of evidence.

## Net positioning

Duecare Journey sits at the intersection of three under-served niches:

1. Migrant-worker apps that include *generative legal AI* (Just Good Work,
   Migrasia, Ami Probashi, MFMW, DoFE all stop short of this).
2. On-device LLM apps with *load-bearing domain RAG* (Cactus, AI Edge
   Gallery, OfflineLLM are runtimes/demos; Duecare is a domain product).
3. Evidence-collection apps for *the worker's own journey* (Tella,
   eyeWitness document atrocities-by-others; Duecare documents
   process-against-self for refund/complaint pursuit).

The harness-off vs harness-on quantified ablation (+87.5/+51.2/+34.1 pp) is
the technical contribution with no clear precedent in the trafficking-LLM
benchmark literature.
