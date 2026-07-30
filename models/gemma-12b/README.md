# Gemma 3 12B (QAT)

Modelo de Google con vision, en su version **QAT** (quantization-aware training): se
entreno teniendo en cuenta que iba a cuantizarse, asi que a 4 bits conserva bastante mas
calidad que una cuantizacion posterior del mismo tamano.

| | |
|---|---|
| Pesos | `ggml-org/gemma-3-12b-it-qat-GGUF` · `gemma-3-12b-it-qat-Q4_0.gguf` (7.13 GB) |
| Vision | `mmproj-model-f16-12B.gguf` (854 MB) |
| Runtime | llama.cpp estandar |
| Contexto | 32K |

## Medido en esta maquina

`llama-bench -p 512 -n 32 -r 3`, Vulkan sobre Radeon 780M:

| | |
|---|---|
| Generacion | 9.36 tok/s |
| Prefill | 99.55 tok/s |
| VRAM | 7.5 GB |

## Ajustes

`--temp 1.0 --top-k 64 --top-p 0.95 --min-p 0.0`, que son los documentados para la familia
Gemma 3. No es un modelo de razonamiento, asi que no lleva presupuesto de reflexion.

## Descargar

```bash
cd /home/deck/gemma-12b/models
curl -L -O https://huggingface.co/ggml-org/gemma-3-12b-it-qat-GGUF/resolve/main/gemma-3-12b-it-qat-Q4_0.gguf
curl -L -O https://huggingface.co/ggml-org/gemma-3-12b-it-qat-GGUF/resolve/main/mmproj-model-f16-12B.gguf
```
