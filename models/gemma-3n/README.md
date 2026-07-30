# Gemma 3n E4B

Variante "n" de Gemma 3, con activacion selectiva: el modelo tiene ~6.9B parametros pero
solo activa una parte en cada paso, de ahi la "E4B" (4B efectivos).

| | |
|---|---|
| Pesos | `ggml-org/gemma-3n-E4B-it-GGUF` · `gemma-3n-E4B-it-Q8_0.gguf` (7.35 GB) |
| Runtime | llama.cpp estandar |
| Contexto | 32K |

## Medido en esta maquina

| | |
|---|---|
| Generacion | 14.81 tok/s |
| Prefill | 194.07 tok/s |
| VRAM | 5.9 GB |

**El que menos memoria ocupa de los cinco**, y aun asi el tercero mas rapido. Buena opcion
si quieres dejar RAM libre para otras cosas.

## Ajustes

`--temp 1.0 --top-k 64 --top-p 0.95 --min-p 0.0`, tal como indica su ficha en Hugging Face.

## Descargar

```bash
cd /home/deck/gemma-3n/models
curl -L -O https://huggingface.co/ggml-org/gemma-3n-E4B-it-GGUF/resolve/main/gemma-3n-E4B-it-Q8_0.gguf
```
