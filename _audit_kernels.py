import json, os, subprocess, tempfile

mapping = json.load(open('_kernel_mapping.json'))
results = []
for kdir, slug in mapping.items():
    with tempfile.TemporaryDirectory() as td:
        r = subprocess.run(['kaggle', 'kernels', 'pull', f'taylorsamarel/{slug}', '-p', td, '-m'],
                           capture_output=True, text=True, timeout=30)
        meta_path = os.path.join(td, 'kernel-metadata.json')
        if not os.path.exists(meta_path):
            results.append({'kdir': kdir, 'slug': slug, 'error': (r.stderr or r.stdout).strip()[:120]})
            continue
        live = json.load(open(meta_path))
        local_path = f'kaggle/kernels/{kdir}/kernel-metadata.json'
        local = json.load(open(local_path)) if os.path.exists(local_path) else {}
        results.append({
            'kdir': kdir, 'slug': slug,
            'live_private': live.get('is_private'),
            'local_private': local.get('is_private'),
            'live_title': live.get('title', ''),
            'local_title': local.get('title', ''),
        })

priv_m = [r for r in results if 'error' not in r and r['live_private'] != r['local_private']]
title_m = [r for r in results if 'error' not in r and r['live_title'] != r['local_title']]
errors = [r for r in results if 'error' in r]

print(f'Audited: {len(results)}   privacy mismatches: {len(priv_m)}   title mismatches: {len(title_m)}   errors: {len(errors)}')
print()
if priv_m:
    print('--- PRIVACY MISMATCHES ---')
    for m in priv_m:
        print(f"  {m['kdir']}  live={m['live_private']}  local={m['local_private']}")
print()
if title_m:
    print('--- TITLE MISMATCHES ---')
    for m in title_m:
        print(f"  {m['kdir']}")
        print(f"    live:  {m['live_title']!r}")
        print(f"    local: {m['local_title']!r}")
if errors:
    print()
    print('--- ERRORS ---')
    for e in errors:
        print(f"  {e['kdir']}: {e['error']}")

json.dump(results, open('_audit_results.json', 'w'), indent=2)
