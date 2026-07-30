# Gemma 4 E4B

Variante de activacion selectiva: ~7.5B parametros de los que solo una parte actua en
cada paso, de ahi la "E4B" (4B efectivos). Cuantizacion **QAT**: entrenada sabiendo que
iba a cuantizarse, asi que a 4 bits conserva mas calidad que una cuantizacion posterior.

| | |
|---|---|
| Pesos | `unsloth/gemma-4-E4B-it-qat-GGUF` · UD-Q4_K_XL (4.22 GB) |
| Vision | `mmproj-F16.gguf` |
| Drafter MTP | `mtp-gemma-4-E4B-it.gguf` (60 MB) |
| Contexto | 32K |

## Medido aqui

| | |
|---|---|
| Generacion | 23.34 tok/s |
| Prefill | 244.49 tok/s |
| VRAM | 4.9 GB |

**La mejor relacion velocidad/memoria de los seis**: casi tan rapido como gpt-oss 20B
ocupando poco mas de un tercio.

El MTP esta desactivado por defecto: medido da 24.44 frente a 24.16 tok/s, una diferencia
dentro del ruido. Se activa con `LLM_MTP=on`.
