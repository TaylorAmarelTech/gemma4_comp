/* DueCare workbench - shared examples-picker primitive.
 *
 * Chat and Compare should expose the same prompt catalog experience:
 * audience buckets, bucket descriptions, per-bucket search state,
 * use-case chips for the model-capability bucket, collapsible category
 * groups, image hints, metadata, and copy affordances.
 */
(function () {
  'use strict';

  let _cache = null;

  const _knownBuckets = [
    'model_capability', 'enterprise_moderation', 'ngo_intake',
    'individual_query', 'research', 'image_prompts',
    'data_intelligence', 'regulator_audit',
  ];

  const _bucketLabels = {
    model_capability:      'Model capability / stress-test',
    enterprise_moderation: 'Platform safety content review',
    ngo_intake:            'NGO & regulator case analysis',
    individual_query:      'Query from individual',
    research:              'Research / journalism',
    image_prompts:         'Image prompts (multimodal)',
    data_intelligence:     'Data intelligence (analyst)',
    regulator_audit:       'Regulator audit',
  };

  const _bucketDescriptions = {
    model_capability:      'Adversarial prompts that stress-test specific model capabilities: jailbreak resistance, jurisdictional reasoning, fee-camouflage detection, and multi-lingual coverage. These are failure-mode probes, not normal user prompts.',
    enterprise_moderation: 'Realistic platform-safety tasks: classify a recruitment ad, triage a user complaint, decide on a marketplace listing, or walk a moderator through a policy edge case.',
    ngo_intake:            'Caseworker, advocate, shelter, or regulator analysis tasks: triage, refund claims, evidence preservation, and brief drafting.',
    individual_query:      'A worker, family member, or prospective migrant talking directly to the model in their own voice.',
    research:              'Academic, journalistic, legal, and policy queries that synthesize across statutes and jurisdictions.',
    image_prompts:         'Multimodal prompts. Pair the text prompt with an attached image such as a receipt, contract page, social-media screenshot, passport photo, wallet UI, or marketplace listing.',
    data_intelligence:     'Structured analyst prompts over synthetic post records from static/synthetic/posts for cluster analysis, anomaly detection, and pattern extraction.',
    regulator_audit:       'Government enforcement-side prompts: license-audit packets, agency compliance review, sanctioning analysis, and evidence-preservation guidance.',
  };

  const _bucketColors = {
    model_capability: '#2f5563',
    enterprise_moderation: '#4c7a8a',
    ngo_intake: '#10b981',
    individual_query: '#f59e0b',
    research: '#06b6d4',
    image_prompts: '#ec4899',
    data_intelligence: '#2f5563',
    regulator_audit: '#dc2626',
  };

  const _categoryLabels = {
    headline_lift_demo: 'Curated sample prompts',
    jailbreak_resistance: 'Jailbreak resistance (DAN / dev-mode / pretext)',
    online_search_demo: 'Live web-search probes',
    model_comparison_demo: 'Variant-comparison probes',
    social_engineering: 'Anti-social-engineering (compliance pretexts)',
    prompt_injection_amplification: 'Prompt-injection amplification',
    regulatory_evasion: 'Regulatory evasion',
    coercion_manipulation: 'Coercion / manipulation',
    moral_religious_framing: 'Moral / religious framing',
    financial_obfuscation: 'Financial obfuscation',
    mega_variations: 'Mega / compound',
    knowledge_check: 'Knowledge check',
    compound_textbook: 'Compound scenarios',
    jurisdictional_hierarchy: 'Jurisdictional hierarchy exploitation',
    amplification_known_attacks: 'Amplification through known attacks',
    victim_revictimization: 'Migrant worker re-victimization',
    financial_crime_blindness: 'Legal standards / financial crime blindness',
    multilingual_capability: 'Multi-lingual capability (en/tl/id/ne/bn/ar/es)',
    business_framed_exploitation: 'Business-framed exploitation (operator-side)',
    social_media_recruitment: 'Social media recruitment posts',
    private_message_grooming: 'Private message grooming (DM)',
    group_chat_pattern: 'Group chat (lender coordination)',
    fake_document: 'Fake documents (clearance certs etc.)',
    receipt_evidence: 'Receipt / promissory-note evidence',
    recruitment_ad_review: 'Recruitment ad review',
    marketplace_listing_review: 'Marketplace listing review',
    group_chat_signal: 'Group-chat signal classification',
    user_complaint_triage: 'User-complaint triage',
    policy_application: 'Policy edge cases',
    ad_compliance_check: 'Ad compliance pre-check',
    caseworker_triage: 'Caseworker first-intake triage',
    case_pathway: 'Case pathway / next legal step',
    policy_brief_request: 'Letter / brief drafting',
    intake_documentation: 'Intake documentation / evidence',
    worker_self_help: 'Worker self-help (in worker voice)',
    family_inquiry: 'Family member inquiry',
    prospective_migrant: 'Pre-departure questions',
    returnee_redress: 'Returnee fee refund / wage recovery',
    comparative_analysis: 'Comparative analysis (cross-jurisdiction)',
    statute_interpretation: 'Statute interpretation',
    methodology: 'Research methodology',
    literature_synthesis: 'Literature synthesis',
    investigative_reporting: 'Investigative reporting plan',
    policy_evaluation: 'Policy efficacy evaluation',
    document_image_review: 'Document images (receipts, contracts, passports)',
    social_media_image: 'Social media screenshots (FB, TikTok, WhatsApp posts)',
    evidence_image: 'Evidence images (contract pages, chat screenshots)',
    marketplace_image: 'Marketplace / classified listing images',
  };

  const _categoryColors = {
    headline_lift_demo: '#10b981',
    jailbreak_resistance: '#ef4444',
    online_search_demo: '#f59e0b',
    model_comparison_demo: '#2f5563',
    social_engineering: '#4c7a8a',
    prompt_injection_amplification: '#dc2626',
    multilingual_capability: '#06b6d4',
    recruitment_ad_review: '#4c7a8a',
    marketplace_listing_review: '#2563eb',
    group_chat_signal: '#1d4ed8',
    user_complaint_triage: '#0ea5e9',
    policy_application: '#0284c7',
    ad_compliance_check: '#075985',
    caseworker_triage: '#10b981',
    case_pathway: '#059669',
    policy_brief_request: '#047857',
    intake_documentation: '#15803d',
    worker_self_help: '#f59e0b',
    family_inquiry: '#d97706',
    prospective_migrant: '#b45309',
    returnee_redress: '#a16207',
    comparative_analysis: '#06b6d4',
    statute_interpretation: '#0891b2',
    methodology: '#0e7490',
    literature_synthesis: '#155e75',
    investigative_reporting: '#164e63',
    policy_evaluation: '#22d3ee',
    document_image_review: '#ec4899',
    social_media_image: '#db2777',
    evidence_image: '#be185d',
    marketplace_image: '#9d174d',
  };

  const _difficultyColors = {
    basic: '#10b981',
    medium: '#4c7a8a',
    hard: '#f59e0b',
    expert: '#ef4444',
  };

  const _demoImpactOrder = [
    'headline_lift_demo', 'jailbreak_resistance', 'online_search_demo',
    'model_comparison_demo', 'social_engineering',
  ];

  const _useCaseLabels = {
    worker_asking: 'Worker asking for help',
    ngo_intake: 'NGO intake / case worker',
    lawyer_research: 'Lawyer research',
    regulator_audit: 'Regulator audit',
    journalist_fact_check: 'Journalist fact-check',
    researcher_tagging: 'Researcher / dataset tagging',
    adversarial_recruiter: 'Adversarial / recruiter',
  };

  const _categoryToUseCases = {
    headline_lift_demo: ['lawyer_research', 'ngo_intake', 'regulator_audit'],
    jailbreak_resistance: ['adversarial_recruiter'],
    online_search_demo: ['journalist_fact_check', 'researcher_tagging', 'lawyer_research'],
    model_comparison_demo: ['researcher_tagging'],
    social_engineering: ['adversarial_recruiter', 'worker_asking'],
    regulatory_evasion: ['regulator_audit', 'lawyer_research'],
    coercion_manipulation: ['worker_asking', 'ngo_intake', 'adversarial_recruiter'],
    moral_religious_framing: ['adversarial_recruiter', 'worker_asking'],
    financial_obfuscation: ['regulator_audit', 'lawyer_research', 'journalist_fact_check'],
    mega_variations: ['researcher_tagging', 'adversarial_recruiter'],
    knowledge_check: ['researcher_tagging', 'lawyer_research'],
    compound_textbook: ['lawyer_research', 'researcher_tagging'],
    jurisdictional_hierarchy: ['lawyer_research', 'regulator_audit'],
    amplification_known_attacks: ['adversarial_recruiter'],
    victim_revictimization: ['ngo_intake', 'worker_asking'],
    financial_crime_blindness: ['regulator_audit', 'lawyer_research'],
    business_framed_exploitation: ['regulator_audit', 'lawyer_research', 'journalist_fact_check'],
    social_media_recruitment: ['ngo_intake', 'worker_asking', 'journalist_fact_check'],
    private_message_grooming: ['ngo_intake', 'worker_asking'],
    group_chat_pattern: ['regulator_audit', 'journalist_fact_check'],
    fake_document: ['regulator_audit', 'journalist_fact_check'],
    receipt_evidence: ['regulator_audit', 'lawyer_research', 'journalist_fact_check'],
  };

  const _state = {
    bucket: 'model_capability',
    useCase: '',
    collapsed: {},
    searchByBucket: {},
    useCaseByBucket: {},
  };

  function _bucketOf(ex) {
    return ex.bucket || 'model_capability';
  }

  function _categoryOf(ex) {
    return ex.category || 'other';
  }

  function _labelForCategory(cat) {
    return _categoryLabels[cat] || String(cat || 'other').replace(/_/g, ' ');
  }

  function _colorForCategory(cat, bucket) {
    return _categoryColors[cat] || _bucketColors[bucket] || '#2f5563';
  }

  function _mk(tag, css, text) {
    const el = document.createElement(tag);
    if (css) el.style.cssText = css;
    if (text != null) el.textContent = text;
    return el;
  }

  function _button(text, css) {
    const b = _mk('button', css || '', text);
    b.type = 'button';
    return b;
  }

  function _matches(ex, q) {
    if (!q) return true;
    const hay = [
      ex.id, ex.text, ex.category, ex.label, ex.bucket, ex.corridor,
      ex.sector, ex.subcategory, ex.difficulty, ex.synthetic_image,
      ex.synthetic_post, ex.image_hint,
      (ex.ilo_indicators || []).join(' '),
    ].join(' ').toLowerCase();
    return hay.indexOf(q) >= 0;
  }

  function _countsByBucket(examples) {
    const counts = {};
    examples.forEach(ex => {
      const b = _bucketOf(ex);
      counts[b] = (counts[b] || 0) + 1;
    });
    return counts;
  }

  function _categoryOrder(byCat) {
    const knownOrder = Object.keys(_categoryLabels);
    return [
      ..._demoImpactOrder.filter(c => byCat[c]),
      ...knownOrder.filter(c => byCat[c] && !_demoImpactOrder.includes(c)),
      ...Object.keys(byCat).filter(c => !knownOrder.includes(c)),
    ];
  }

  function _searchValue(state) {
    return state.searchByBucket[state.bucket] || '';
  }

  function _setSearchValue(state, value) {
    state.searchByBucket[state.bucket] = value || '';
  }

  function _filteredCategoryOrder(byCat, state) {
    let order = _categoryOrder(byCat);
    if (state.useCase) {
      order = order.filter(cat => {
        if (_demoImpactOrder.includes(cat)) return true;
        const ucs = _categoryToUseCases[cat] || [];
        return ucs.includes(state.useCase);
      });
    }
    order.forEach(cat => {
      if (!(cat in state.collapsed)) {
        state.collapsed[cat] = !_demoImpactOrder.includes(cat) && !state.useCase;
      }
    });
    return order;
  }

  async function fetchAll() {
    if (_cache !== null) return _cache;
    try {
      const r = await fetch('/api/examples', {cache: 'no-store'});
      if (!r.ok) { _cache = []; return _cache; }
      const data = await r.json();
      _cache = data.examples || [];
      return _cache;
    } catch (e) {
      _cache = [];
      return _cache;
    }
  }

  function _renderBucketControls(host, examples, state, rerender) {
    const counts = _countsByBucket(examples);
    const row = _mk('div',
      'display:flex; gap:8px; flex-wrap:wrap; margin-bottom:10px; align-items:center; ' +
      'padding:10px 12px; background:var(--panel2,#EFEDE4); border-radius:8px;');
    row.appendChild(_mk('span',
      'color:var(--muted,#5B5F68); font-size:11px; font-weight:700; ' +
      'text-transform:uppercase; letter-spacing:0.4px; margin-right:4px;',
      'Audience:'));
    _knownBuckets.forEach(bucket => {
      const color = _bucketColors[bucket] || '#5B5F68';
      const active = state.bucket === bucket;
      const btn = _button((_bucketLabels[bucket] || bucket) + ' (' + (counts[bucket] || 0) + ')',
        'background:' + (active ? color + '22' : 'var(--bg,#F7F6F1)') + '; ' +
        'border:2px solid ' + (active ? color : 'var(--border,#DDD8C9)') + '; ' +
        'color:var(--ink,#0E1116); padding:7px 14px; border-radius:8px; ' +
        'font-size:12px; cursor:pointer; font-weight:' + (active ? '700' : '500') + '; ' +
        'transition:all 0.12s ease;');
      btn.title = _bucketDescriptions[bucket] || '';
      btn.onclick = () => {
        const oldBucket = state.bucket;
        state.useCaseByBucket[oldBucket] = state.useCase;
        state.bucket = bucket;
        state.useCase = state.useCaseByBucket[bucket] || '';
        state.collapsed = {};
        rerender();
      };
      row.appendChild(btn);
    });
    host.appendChild(row);

    const desc = _bucketDescriptions[state.bucket] || '';
    if (desc) {
      host.appendChild(_mk('div',
        'font-size:11.5px; color:var(--muted,#5B5F68); margin-bottom:10px; ' +
        'padding:0 4px; line-height:1.5; font-style:italic;',
        desc));
    }
  }

  function _renderUseCaseControls(host, state, rerender) {
    if (state.bucket !== 'model_capability') return;
    const row = _mk('div',
      'display:flex; gap:6px; flex-wrap:wrap; margin-bottom:10px; align-items:center;');
    row.appendChild(_mk('span',
      'color:var(--muted,#5B5F68); font-size:11px; font-weight:600; ' +
      'text-transform:uppercase; letter-spacing:0.4px; margin-right:4px;',
      'Use case:'));
    const chip = (key, label) => {
      const active = state.useCase === key;
      const btn = _button(label,
        'background:' + (active ? 'rgba(47,85,99,0.18)' : 'var(--bg,#F7F6F1)') + '; ' +
        'border:1px solid ' + (active ? '#2f5563' : 'var(--border,#DDD8C9)') + '; ' +
        'color:var(--ink,#0E1116); padding:4px 10px; border-radius:14px; ' +
        'font-size:11px; cursor:pointer; transition:all 0.12s ease;');
      btn.onclick = () => {
        state.useCase = key;
        state.useCaseByBucket[state.bucket] = key;
        state.collapsed = {};
        rerender();
      };
      row.appendChild(btn);
    };
    chip('', 'All');
    Object.keys(_useCaseLabels).forEach(key => chip(key, _useCaseLabels[key]));
    host.appendChild(row);
  }

  function _renderSearchControls(host, examples, state, listHost) {
    const row = _mk('div',
      'display:flex; gap:10px; align-items:center; margin-bottom:10px; flex-wrap:wrap;');
    const bucketTotal = examples.filter(ex => _bucketOf(ex) === state.bucket).length;
    const input = _mk('input',
      'flex:1 1 320px; padding:8px 12px; background:var(--bg,#F7F6F1); ' +
      'color:var(--ink,#0E1116); border:1px solid var(--border,#DDD8C9); ' +
      'border-radius:6px; font-size:13px;');
    input.id = 'cmp-ex-filter';
    input.type = 'text';
    input.placeholder = 'Search ' + bucketTotal +
      ' prompts in this bucket (text, category, corridor, indicator)...';
    input.value = _searchValue(state);
    const count = _mk('span',
      'color:var(--muted,#5B5F68); font-size:11.5px;',
      '');
    count.id = 'examples-count';
    input.oninput = () => {
      _setSearchValue(state, input.value);
      _renderList(listHost, {examples, state, counter: count});
    };
    row.appendChild(input);
    row.appendChild(count);

    const expand = _button('Expand all',
      'background:transparent; border:1px solid var(--border,#DDD8C9); ' +
      'color:var(--muted,#5B5F68); padding:4px 10px; border-radius:6px; ' +
      'font-size:11px; cursor:pointer;');
    expand.onclick = () => {
      Object.keys(state.collapsed).forEach(cat => { state.collapsed[cat] = false; });
      _renderList(listHost, {examples, state, counter: count});
    };
    const collapse = _button('Collapse all',
      'background:transparent; border:1px solid var(--border,#DDD8C9); ' +
      'color:var(--muted,#5B5F68); padding:4px 10px; border-radius:6px; ' +
      'font-size:11px; cursor:pointer;');
    collapse.onclick = () => {
      Object.keys(state.collapsed).forEach(cat => { state.collapsed[cat] = true; });
      _renderList(listHost, {examples, state, counter: count});
    };
    row.appendChild(expand);
    row.appendChild(collapse);
    host.appendChild(row);

    host.appendChild(_mk('div',
      'color:var(--muted,#5B5F68); font-size:11.5px; margin-bottom:14px;',
      'Click any prompt body to load it. Use copy on the right to copy prompt text.'));
    return count;
  }

  function _renderList(host, opts) {
    if (!host) return;
    opts = opts || {};
    const examples = opts.examples || [];
    const state = opts.state || _state;
    const q = (opts.filter != null ? opts.filter : _searchValue(state)).trim().toLowerCase();
    while (host.firstChild) host.removeChild(host.firstChild);

    const bucketFiltered = examples.filter(ex => _bucketOf(ex) === state.bucket);
    const byCat = {};
    bucketFiltered.forEach(ex => {
      const cat = _categoryOf(ex);
      (byCat[cat] = byCat[cat] || []).push(ex);
    });
    const catOrder = _filteredCategoryOrder(byCat, state);

    let visibleCount = 0;
    let renderedCats = 0;
    catOrder.forEach(cat => {
      const bucket = state.bucket;
      const color = _colorForCategory(cat, bucket);
      const rawItems = byCat[cat] || [];
      const items = rawItems.filter(ex => _matches(ex, q));
      if (!items.length) return;
      visibleCount += items.length;
      renderedCats += 1;

      const sparse = rawItems.length < 3 && !_demoImpactOrder.includes(cat);
      const collapsed = q ? false : !!state.collapsed[cat];
      const group = _mk('div',
        'margin-bottom:12px; border:1px solid var(--border,#DDD8C9); ' +
        'border-radius:6px; border-left:4px solid ' + color + '; overflow:hidden; ' +
        'opacity:' + (sparse ? '0.55' : '1') + ';');
      group.className = 'examples-category';
      group.dataset.cat = cat;

      const head = _button('',
        'width:100%; cursor:pointer; padding:10px 14px; background:var(--panel2,#EFEDE4); ' +
        'display:flex; align-items:center; gap:10px; font-weight:600; user-select:none; ' +
        'border:0; text-align:left;');
      const chev = _mk('span',
        'display:inline-block; width:14px; transition:transform 0.15s; transform:rotate(' +
        (collapsed ? '0' : '90') + 'deg);',
        '>');
      const title = _mk('span',
        'color:' + color + '; font-size:12.5px;',
        _labelForCategory(cat));
      head.appendChild(chev);
      head.appendChild(title);
      if (sparse) {
        head.appendChild(_mk('span',
          'color:var(--muted,#5B5F68); font-size:10px; font-style:italic; margin-left:6px;',
          'thin set'));
      }
      head.appendChild(_mk('span',
        'color:var(--muted,#5B5F68); font-size:11px; margin-left:auto;',
        rawItems.length + ' prompt' + (rawItems.length === 1 ? '' : 's')));
      const itemsHost = _mk('div',
        'display:' + (collapsed ? 'none' : 'block') + '; padding:6px 14px 12px;');
      head.onclick = () => {
        state.collapsed[cat] = !state.collapsed[cat];
        _renderList(host, opts);
      };
      group.appendChild(head);

      items.forEach(ex => {
        itemsHost.appendChild(_renderExampleRow(ex, color, opts));
      });
      group.appendChild(itemsHost);
      host.appendChild(group);
    });

    if (!visibleCount) {
      host.appendChild(_mk('div',
        'color:var(--muted,#5B5F68); font-style:italic; padding:24px 0; font-size:13px;',
        q ? 'No prompts match "' + q + '".' : 'No prompts loaded for this audience.'));
    }

    if (opts.counter) {
      const total = bucketFiltered.length;
      opts.counter.textContent = q
        ? visibleCount + ' of ' + total + ' prompts match "' + q + '"'
        : total + ' prompts in ' + renderedCats +
          ' categor' + (renderedCats === 1 ? 'y' : 'ies');
    }
  }

  function _renderExampleRow(ex, color, opts) {
    const row = _mk('div',
      'cursor:pointer; padding:10px 12px; margin-top:6px; background:var(--bg,#F7F6F1); ' +
      'border-radius:5px; border:1px solid var(--border,#DDD8C9); ' +
      'transition:border-color 0.15s; font-size:12.5px; line-height:1.5;');
    row.className = 'example-item';
    row.dataset.exId = ex.id || '';
    row.tabIndex = 0;
    row.setAttribute('role', 'button');
    row.setAttribute('aria-label', ex.label || (ex.text || '').slice(0, 80));
    row.onmouseenter = () => { row.style.borderColor = color; };
    row.onmouseleave = () => { row.style.borderColor = 'var(--border,#DDD8C9)'; };
    const onPick = () => { if (opts.onPick) opts.onPick(ex); };
    row.onclick = onPick;
    row.onkeydown = (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onPick();
      }
    };

    if (ex.image_hint) {
      const hint = _mk('div',
        'margin-bottom:6px; padding:6px 10px; background:rgba(236,72,153,0.08); ' +
        'border-left:3px solid #ec4899; border-radius:3px; font-size:11px; ' +
        'color:var(--ink-2,#2A2D34);',
        'Attach an image: ' + ex.image_hint);
      row.appendChild(hint);
    }
    if (ex.synthetic_image) {
      row.appendChild(_mk('div',
        'margin-bottom:6px; color:#be185d; font-size:10.5px; font-weight:600;',
        'Bundled synthetic image will attach automatically where supported.'));
    }
    if (ex.label) {
      row.appendChild(_mk('div',
        'font-weight:600; color:var(--ink,#0E1116); margin-bottom:4px;',
        ex.label));
    }
    const bodyShort = (ex.text || '').length > 240
      ? (ex.text || '').slice(0, 240) + '...'
      : (ex.text || '');
    const text = _mk('div',
      'color:var(--ink,#0E1116); font-size:12px; line-height:1.5; ' +
      'white-space:pre-wrap; overflow-wrap:anywhere;',
      bodyShort);
    text.title = ex.text || '';
    row.appendChild(text);

    const meta = _mk('div',
      'margin-top:8px; display:flex; flex-wrap:wrap; gap:6px; align-items:center; ' +
      'font-size:10.5px; padding-top:6px; border-top:1px dashed var(--border,#DDD8C9);');
    if (ex.difficulty) {
      meta.appendChild(_mk('span',
        'color:' + (_difficultyColors[ex.difficulty] || '#5B5F68') + '; font-weight:600;',
        ex.difficulty));
    }
    [ex.subcategory, ex.corridor, ex.sector, ex.id].filter(Boolean).forEach(part => {
      meta.appendChild(_mk('span',
        'color:var(--muted,#5B5F68); font-family:JetBrains Mono,monospace;',
        part));
    });
    (ex.ilo_indicators || []).slice(0, 3).forEach(ind => {
      meta.appendChild(_mk('span',
        'display:inline-block; padding:1px 6px; border-radius:3px; ' +
        'background:var(--panel2,#EFEDE4); color:var(--muted,#5B5F68);',
        ind));
    });
    const copy = _button('copy',
      'margin-left:auto; background:transparent; border:1px solid var(--border,#DDD8C9); ' +
      'color:var(--muted,#5B5F68); padding:3px 10px; border-radius:6px; ' +
      'font-size:10.5px; cursor:pointer; font-weight:500;');
    copy.title = 'Copy prompt to clipboard';
    copy.onmouseenter = () => { copy.style.borderColor = color; copy.style.color = color; };
    copy.onmouseleave = () => {
      copy.style.borderColor = 'var(--border,#DDD8C9)';
      copy.style.color = 'var(--muted,#5B5F68)';
    };
    copy.onclick = (e) => {
      e.stopPropagation();
      (opts.onCopy || _copyExampleText)(ex, copy);
    };
    meta.appendChild(copy);
    meta.appendChild(_mk('span',
      'color:' + color + '; font-size:10.5px; font-weight:600; margin-left:8px;',
      'click body to load ->'));
    row.appendChild(meta);
    return row;
  }

  function renderInto(host, opts) {
    opts = opts || {};
    const state = {
      bucket: opts.bucket || _state.bucket || 'model_capability',
      useCase: opts.useCase || '',
      collapsed: opts.collapsed || {},
      searchByBucket: {[opts.bucket || _state.bucket || 'model_capability']: opts.filter || ''},
      useCaseByBucket: {},
    };
    _renderList(host, {
      examples: opts.examples || [],
      state,
      filter: opts.filter || '',
      onPick: opts.onPick,
      onCopy: opts.onCopy,
    });
  }

  function _renderPickerBody(body, examples, opts, state) {
    while (body.firstChild) body.removeChild(body.firstChild);
    const rerender = () => _renderPickerBody(body, examples, opts, state);
    _renderBucketControls(body, examples, state, rerender);
    const listHost = _mk('div', '');
    listHost.id = 'cmp-ex-list';
    const counter = _renderSearchControls(body, examples, state, listHost);
    _renderUseCaseControls(body, state, rerender);
    body.appendChild(listHost);
    _renderList(listHost, {
      examples,
      state,
      counter,
      onPick: (ex) => {
        if (opts.onPick) opts.onPick(ex);
        const overlay = document.getElementById('_dc_ex_overlay');
        if (overlay) overlay.remove();
      },
      onCopy: opts.onCopy || _copyExampleText,
    });
  }

  function open(opts) {
    opts = opts || {};
    if (opts.bucket) _state.bucket = opts.bucket;
    const overlayId = '_dc_ex_overlay';
    let overlay = document.getElementById(overlayId);
    if (!overlay) {
      overlay = _mk('div',
        'position:fixed; inset:0; background:rgba(14,17,22,0.40); ' +
        'backdrop-filter:blur(2px); z-index:9000; display:flex; align-items:center; ' +
        'justify-content:center; padding:clamp(8px,2vh,24px); overflow-y:auto;');
      overlay.id = overlayId;
      overlay.setAttribute('role', 'presentation');

      const modal = _mk('div',
        'background:var(--panel,#F7F6F1); border:1px solid var(--border,#DDD8C9); ' +
        'border-radius:12px; max-width:1100px; width:100%; ' +
        'max-height:min(92vh,calc(100dvh - 48px)); display:flex; ' +
        'flex-direction:column; overflow:hidden; box-shadow:0 25px 60px rgba(14,17,22,0.18);');
      modal.id = 'cmp-ex-modal';
      modal.setAttribute('role', 'dialog');
      modal.setAttribute('aria-modal', 'true');
      modal.setAttribute('aria-labelledby', 'cmp-ex-modal-title');
      modal.onclick = (e) => e.stopPropagation();

      const head = _mk('div',
        'display:flex; justify-content:space-between; align-items:center; ' +
        'padding:16px 22px; border-bottom:1px solid var(--border,#DDD8C9); ' +
        'background:var(--panel2,#EFEDE4);');
      const title = _mk('div',
        'font-size:18px; font-weight:700; color:var(--ink,#0E1116);',
        opts.title || 'Example prompts');
      title.id = 'cmp-ex-modal-title';
      head.appendChild(title);
      const close = _button(String.fromCharCode(215),
        'background:transparent; border:0; color:var(--muted,#5B5F68); ' +
        'cursor:pointer; font-size:22px; line-height:1; padding:4px 10px; border-radius:6px;');
      close.title = 'Close';
      close.onclick = () => { overlay.remove(); };
      head.appendChild(close);
      modal.appendChild(head);

      const body = _mk('div',
        'overflow-y:auto; flex:1; padding:12px 22px 22px; color:var(--ink,#0E1116);');
      body.id = 'cmp-ex-body';
      modal.appendChild(body);
      overlay.appendChild(modal);
      overlay.onclick = (e) => {
        if (e.target === overlay) overlay.remove();
      };
      const onEsc = (e) => {
        if (e.key === 'Escape') {
          overlay.remove();
          document.removeEventListener('keydown', onEsc);
        }
      };
      overlay._dcOnEsc = onEsc;
      document.addEventListener('keydown', onEsc);
      document.body.appendChild(overlay);
    } else {
      const title = overlay.querySelector('#cmp-ex-modal-title');
      if (title) title.textContent = opts.title || 'Example prompts';
    }

    fetchAll().then(examples => {
      const body = overlay.querySelector('#cmp-ex-body');
      if (body) _renderPickerBody(body, examples, opts, _state);
      setTimeout(() => {
        const filter = overlay.querySelector('#cmp-ex-filter');
        if (filter) filter.focus();
      }, 50);
    });
    return {close: () => overlay.remove()};
  }

  async function _copyExampleText(ex, btn) {
    const text = (ex && ex.text) || '';
    const orig = btn ? btn.textContent : '';
    try {
      await navigator.clipboard.writeText(text);
      if (btn) {
        btn.textContent = 'copied';
        btn.style.color = '#10b981';
      }
    } catch (e) {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); } catch (_) {}
      document.body.removeChild(ta);
      if (btn) {
        btn.textContent = 'copied';
        btn.style.color = '#10b981';
      }
    }
    if (btn) {
      setTimeout(() => {
        btn.textContent = orig || 'copy';
        btn.style.color = '';
      }, 1500);
    }
  }

  window.dcExamplesPicker = {fetchAll, renderInto, open};
})();
