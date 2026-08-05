# Third Party Licenses

This document lists the open source software dependencies used in DueCare and their respective licenses.

## Core Dependencies

### FastAPI (MIT License)
- **Package**: fastapi
- **License**: MIT
- **Copyright**: Copyright (c) 2018 Sebastián Ramírez
- **Use**: Web framework for the demo application API
- **License URL**: https://github.com/tiangolo/fastapi/blob/master/LICENSE

### Pydantic (MIT License)
- **Package**: pydantic
- **License**: MIT
- **Copyright**: Copyright (c) 2017 to present Pydantic Contributors
- **Use**: Data validation and settings management
- **License URL**: https://github.com/pydantic/pydantic/blob/main/LICENSE

### Transformers (Apache 2.0 License)
- **Package**: transformers
- **License**: Apache License 2.0
- **Copyright**: Copyright 2018- The Hugging Face team
- **Use**: Model adapters and tokenizers
- **License URL**: https://github.com/huggingface/transformers/blob/main/LICENSE

### PyTorch (BSD-3-Clause License)
- **Package**: torch
- **License**: BSD-3-Clause
- **Copyright**: Copyright (c) 2016-present, Facebook Inc
- **Use**: Deep learning framework
- **License URL**: https://github.com/pytorch/pytorch/blob/master/LICENSE

### Uvicorn (BSD-3-Clause License)
- **Package**: uvicorn
- **License**: BSD-3-Clause
- **Copyright**: Copyright © 2017-present, Tom Christie
- **Use**: ASGI server for FastAPI
- **License URL**: https://github.com/encode/uvicorn/blob/master/LICENSE.md

## Model and Training Dependencies

### Unsloth (Apache 2.0 License)
- **Package**: unsloth
- **License**: Apache License 2.0
- **Copyright**: Copyright 2023 Unsloth AI
- **Use**: Fine-tuning framework for efficient model training
- **License URL**: https://github.com/unslothai/unsloth/blob/main/LICENSE

### Accelerate (Apache 2.0 License)
- **Package**: accelerate
- **License**: Apache License 2.0
- **Copyright**: Copyright 2021 The HuggingFace Inc. team
- **Use**: Distributed training support
- **License URL**: https://github.com/huggingface/accelerate/blob/main/LICENSE

### BitsAndBytes (MIT License)
- **Package**: bitsandbytes
- **License**: MIT
- **Copyright**: Copyright (c) Facebook, Inc. and its affiliates
- **Use**: Quantization for memory-efficient training
- **License URL**: https://github.com/TimDettmers/bitsandbytes/blob/main/LICENSE

## Utility Dependencies

### Requests (Apache 2.0 License)
- **Package**: requests
- **License**: Apache License 2.0
- **Copyright**: Copyright 2019 Kenneth Reitz
- **Use**: HTTP client library
- **License URL**: https://github.com/psf/requests/blob/main/LICENSE

### Jinja2 (BSD-3-Clause License)
- **Package**: jinja2
- **License**: BSD-3-Clause
- **Copyright**: Copyright 2007 Pallets
- **Use**: Template engine for report generation
- **License URL**: https://github.com/pallets/jinja/blob/main/LICENSE.rst

### AIOFiles (Apache 2.0 License)
- **Package**: aiofiles
- **License**: Apache License 2.0
- **Copyright**: Copyright 2016 Tin Tvrtković
- **Use**: Asynchronous file operations
- **License URL**: https://github.com/Tinche/aiofiles/blob/main/LICENSE

### python-multipart (Apache 2.0 License)
- **Package**: python-multipart
- **License**: Apache License 2.0
- **Copyright**: Copyright 2019 Andrew Dunham
- **Use**: Multipart form data parsing
- **License URL**: https://github.com/andrew-d/python-multipart/blob/master/LICENSE.txt

## Model Family

### Gemma 4 (Apache License 2.0)
- **Model**: Gemma 4 — E2B / E4B / 26B-A4B / 31B variants
- **License**: Apache License, Version 2.0
- **Copyright**: Copyright 2026 Google LLC
- **Use**: Base language model for safety evaluation and LoRA fine-tuning
- **License URL**: https://ai.google.dev/gemma/apache_2
- **Prohibited use policy**: https://ai.google.dev/gemma/prohibited_use_policy
- **Intended use statement**: https://ai.google.dev/gemma/intended_use_statement
- **Note**: Gemma 4 is Apache 2.0, not the older "Gemma Terms of Use" that
  govern earlier Gemma generations — Google's terms page directs Gemma 4 to
  the Apache 2.0 license. The Prohibited Use Policy still applies. DueCare
  redistributes no base weights; the LoRA adapters it does publish are
  Derivative Works and are covered in the root `NOTICE` file.

## Optional Dependencies

### LLaMA.cpp (MIT License)
- **Package**: llama-cpp-python
- **License**: MIT
- **Copyright**: Copyright (c) 2023 Andrei Betlen
- **Use**: CPU/GPU inference engine
- **License URL**: https://github.com/abetlen/llama-cpp-python/blob/main/LICENSE.md

### Ollama Integration (MIT License)
- **Package**: httpx (for Ollama API)
- **License**: BSD-3-Clause
- **Copyright**: Copyright © 2019, Tom Christie
- **Use**: HTTP client for Ollama API integration
- **License URL**: https://github.com/encode/httpx/blob/master/LICENSE.md

### OpenAI Integration (Apache 2.0 License)
- **Package**: openai
- **License**: Apache License 2.0
- **Copyright**: Copyright 2020 OpenAI
- **Use**: OpenAI API client
- **License URL**: https://github.com/openai/openai-python/blob/main/LICENSE

### Anthropic Integration (MIT License)
- **Package**: anthropic
- **License**: MIT
- **Copyright**: Copyright (c) 2023 Anthropic PBC
- **Use**: Anthropic Claude API client
- **License URL**: https://github.com/anthropics/anthropic-sdk-python/blob/main/LICENSE

### Google AI Integration (Apache 2.0 License)
- **Package**: google-generativeai
- **License**: Apache License 2.0
- **Copyright**: Copyright 2023 Google LLC
- **Use**: Google Gemini API client
- **License URL**: https://github.com/google/generative-ai-python/blob/main/LICENSE

## Development Dependencies

### Hugging Face Hub (Apache 2.0 License)
- **Package**: huggingface_hub
- **License**: Apache License 2.0
- **Copyright**: Copyright 2020 The HuggingFace Inc. team
- **Use**: Model and dataset publishing
- **License URL**: https://github.com/huggingface/huggingface_hub/blob/main/LICENSE

### SentencePiece (Apache 2.0 License)
- **Package**: sentencepiece
- **License**: Apache License 2.0
- **Copyright**: Copyright 2018 Google Inc.
- **Use**: Tokenization for Gemma models
- **License URL**: https://github.com/google/sentencepiece/blob/master/LICENSE

### Tokenizers (Apache 2.0 License)
- **Package**: tokenizers
- **License**: Apache License 2.0
- **Copyright**: Copyright 2019 The HuggingFace Inc. team
- **Use**: Fast tokenization library
- **License URL**: https://github.com/huggingface/tokenizers/blob/main/LICENSE

## License Compatibility

All dependencies use MIT, Apache 2.0, or BSD-3-Clause licenses, which are compatible with this project's MIT license. The Gemma Terms of Use allow for the specific use case of safety evaluation and research.

## Attribution Requirements

- Apache 2.0 licensed components require preservation of copyright notices and license text
- MIT and BSD licensed components require preservation of copyright notices
- All requirements are satisfied by this attribution file

## License Texts

Full license texts for all dependencies are available in their respective repositories linked above. The most common license texts are also available at:

- Apache 2.0: https://www.apache.org/licenses/LICENSE-2.0.txt
- MIT: https://opensource.org/licenses/MIT
- BSD-3-Clause: https://opensource.org/licenses/BSD-3-Clause
- Gemma 4 license (Apache 2.0): https://ai.google.dev/gemma/apache_2
- Gemma prohibited use policy: https://ai.google.dev/gemma/prohibited_use_policy

---

Generated on: 2026-05-09
Project: DueCare - Agentic Safety Harness for LLMs
Repository: https://github.com/TaylorAmarelTech/gemma4_comp