# Drive waterfall analysis report

- Candidates: 1500 text-bearing files
- Text-extracted: 249
- Errors (download / parse): 0
- Distinct entities: 1330
- Hypothesis edges (cross-bundle, >= 2): 128
- Doc embedding clusters: 37

## Top org by cross-bundle reach

| bundles | files | value |
|---:|---:|---|
| 5 | 7 | `CORPORATE GOVERNANCE AND FINANCE` |
| 5 | 7 | `ONE COMPLAINT FORM PER RESPONDENT COMPANY` |
| 4 | 6 | `PHILIPPINE OVERSEAS EMPLOYMENT` |
| 2 | 5 | `SUSPECTED ILLEGAL LENDING` |
| 2 | 3 | `BY THE DEPARTMENT OF LABOR AND EMPLOYMENT` |
| 2 | 3 | `GOLD AND GREEN MANPOWER` |
| 2 | 3 | `SAGE INTERNATIONAL DEVELOPMENT COMPANY` |
| 2 | 3 | `INTERNATIONAL MANPOWER` |
| 2 | 3 | `HOYA LENDING INVESTOR CORPORATION` |
| 2 | 2 | `OLM FINANCING CORPORATION` |

## Top person by cross-bundle reach

| bundles | files | value |
|---:|---:|---|
| 2 | 2 | `CHAN, Mr` |
| 2 | 2 | `David Bishop Global Migration Legal` |
| 2 | 2 | `LAW, Mr` |
| 2 | 2 | `Loremay Sayo` |
| 2 | 2 | `Loremay Sayo This` |

## Top email by cross-bundle reach

| bundles | files | value |
|---:|---:|---|
| 7 | 9 | `epd@sec.gov.ph` |
| 5 | 45 | `info@jemhk.org` |
| 4 | 15 | `dbishop@hku.hk` |
| 4 | 7 | `pcc@malacanang.gov.ph` |
| 4 | 4 | `ea-ee@labour.gov.hk` |
| 3 | 7 | `cgfd_md@sec.gov.ph` |
| 3 | 4 | `poea.prosecution@gmail.com` |
| 3 | 4 | `polo.hongkong@yahoo.com` |
| 2 | 9 | `gmlc.hku@gmail.com` |
| 2 | 3 | `imessagemo@sec.gov.ph` |
| 2 | 3 | `complaints@privacy.gov.ph` |
| 2 | 3 | `globalmigrationassistance@gmail.com` |
| 2 | 3 | `secretariat@amlc.gov.ph` |
| 2 | 2 | `bspmail@bsp.gov.ph` |
| 2 | 2 | `cp@police.gov.hk` |
| 2 | 2 | `kittytsui@cr.gov.hk` |
| 2 | 2 | `sfst@fstb.gov.hk` |
| 2 | 2 | `cl_office@labour.gov.hk` |
| 2 | 2 | `dennis@denniskwok.hk` |
| 2 | 2 | `hilary_tl_lung@customs.gov.hk` |

## Top financial_account by cross-bundle reach

| bundles | files | value |
|---:|---:|---|

## Top phone by cross-bundle reach

| bundles | files | value |
|---:|---:|---|
| 2 | 2 | `+85256297700` |

## Top gov_ref by cross-bundle reach

| bundles | files | value |
|---:|---:|---|
| 10 | 20 | `POEA` |
| 9 | 22 | `POLO` |
| 8 | 82 | `SEC` |
| 5 | 11 | `PCG` |
| 3 | 3 | `DOLE` |
| 2 | 3 | `NLRC` |
| 2 | 2 | `IOM` |

## Top 40 hypothesis edges

| bundles | docs | relation | a | b |
|---:|---:|---|---|---|
| 7 | 10 | co_occurs | `gov_ref:POEA` | `gov_ref:POLO` |
| 6 | 8 | co_occurs | `email:epd@sec.gov.ph` | `gov_ref:SEC` |
| 5 | 7 | org_has_email | `email:epd@sec.gov.ph` | `org:CORPORATE GOVERNANCE AND FIN` |
| 5 | 7 | org_has_email | `email:epd@sec.gov.ph` | `org:ONE COMPLAINT FORM PER RESPO` |
| 5 | 7 | orgs_co_appear | `org:CORPORATE GOVERNANCE AND FIN` | `org:ONE COMPLAINT FORM PER RESPO` |
| 5 | 7 | org_regulated_by_agency | `gov_ref:SEC` | `org:CORPORATE GOVERNANCE AND FIN` |
| 5 | 7 | org_regulated_by_agency | `gov_ref:SEC` | `org:ONE COMPLAINT FORM PER RESPO` |
| 5 | 6 | co_occurs | `gov_ref:PCG` | `gov_ref:POLO` |
| 4 | 6 | org_regulated_by_agency | `gov_ref:POEA` | `org:PHILIPPINE OVERSEAS EMPLOYME` |
| 4 | 4 | co_occurs | `gov_ref:PCG` | `gov_ref:POEA` |
| 3 | 4 | co_occurs | `email:pcc@malacanang.gov.ph` | `email:poea.prosecution@gmail.com` |
| 3 | 4 | co_occurs | `email:pcc@malacanang.gov.ph` | `email:polo.hongkong@yahoo.com` |
| 3 | 4 | co_occurs | `email:poea.prosecution@gmail.com` | `email:polo.hongkong@yahoo.com` |
| 3 | 3 | co_occurs | `gov_ref:DOLE` | `gov_ref:POEA` |
| 3 | 3 | co_occurs | `email:dbishop@hku.hk` | `email:ea-ee@labour.gov.hk` |
| 2 | 6 | co_occurs | `email:info@jemhk.org` | `gov_ref:PCG` |
| 2 | 5 | co_occurs | `email:cgfd_md@sec.gov.ph` | `gov_ref:SEC` |
| 2 | 5 | org_has_email | `email:info@jemhk.org` | `org:SUSPECTED ILLEGAL LENDING` |
| 2 | 5 | org_regulated_by_agency | `gov_ref:PCG` | `org:SUSPECTED ILLEGAL LENDING` |
| 2 | 4 | co_occurs | `email:gmlc.hku@gmail.com` | `gov_ref:SEC` |
| 2 | 3 | co_occurs | `email:pcc@malacanang.gov.ph` | `gov_ref:POLO` |
| 2 | 3 | co_occurs | `email:poea.prosecution@gmail.com` | `gov_ref:POLO` |
| 2 | 3 | co_occurs | `email:polo.hongkong@yahoo.com` | `gov_ref:POLO` |
| 2 | 3 | orgs_co_appear | `org:BY THE DEPARTMENT OF LABOR A` | `org:PHILIPPINE OVERSEAS EMPLOYME` |
| 2 | 3 | org_regulated_by_agency | `gov_ref:POEA` | `org:BY THE DEPARTMENT OF LABOR A` |
| 2 | 3 | org_regulated_by_agency | `gov_ref:POLO` | `org:BY THE DEPARTMENT OF LABOR A` |
| 2 | 3 | orgs_co_appear | `org:GOLD AND GREEN MANPOWER` | `org:PHILIPPINE OVERSEAS EMPLOYME` |
| 2 | 3 | orgs_co_appear | `org:GOLD AND GREEN MANPOWER` | `org:SAGE INTERNATIONAL DEVELOPME` |
| 2 | 3 | org_regulated_by_agency | `gov_ref:NLRC` | `org:GOLD AND GREEN MANPOWER` |
| 2 | 3 | org_regulated_by_agency | `gov_ref:POEA` | `org:GOLD AND GREEN MANPOWER` |
| 2 | 3 | orgs_co_appear | `org:PHILIPPINE OVERSEAS EMPLOYME` | `org:SAGE INTERNATIONAL DEVELOPME` |
| 2 | 3 | org_regulated_by_agency | `gov_ref:NLRC` | `org:PHILIPPINE OVERSEAS EMPLOYME` |
| 2 | 3 | org_regulated_by_agency | `gov_ref:POLO` | `org:PHILIPPINE OVERSEAS EMPLOYME` |
| 2 | 3 | org_regulated_by_agency | `gov_ref:NLRC` | `org:SAGE INTERNATIONAL DEVELOPME` |
| 2 | 3 | org_regulated_by_agency | `gov_ref:POEA` | `org:SAGE INTERNATIONAL DEVELOPME` |
| 2 | 3 | co_occurs | `gov_ref:NLRC` | `gov_ref:POEA` |
| 2 | 3 | co_occurs | `email:cgfd_md@sec.gov.ph` | `email:imessagemo@sec.gov.ph` |
| 2 | 3 | co_occurs | `email:imessagemo@sec.gov.ph` | `gov_ref:SEC` |
| 2 | 3 | co_occurs | `gov_ref:POEA` | `gov_ref:SEC` |
| 2 | 3 | co_occurs | `email:cgfd_md@sec.gov.ph` | `email:complaints@privacy.gov.ph` |

## Top 10 doc clusters (by size)

| cluster | size |
|---:|---:|
| 0 | 98 |
| 2 | 32 |
| 11 | 7 |
| 4 | 6 |
| 1 | 3 |
| 5 | 3 |
| 23 | 3 |
| 25 | 3 |
| 26 | 3 |
| 3 | 2 |
