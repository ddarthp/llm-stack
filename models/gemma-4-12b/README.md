# Gemma 4 12B

Modelo denso, cuantizacion QAT a 4 bits, con vision y drafter MTP.

| | |
|---|---|
| Pesos | `unsloth/gemma-4-12B-it-qat-GGUF` · UD-Q4_K_XL (6.72 GB) |
| Contexto | 32K |

## Medido aqui

| | |
|---|---|
| Generacion | 9.62 tok/s |
| Prefill | 92.43 tok/s |
| VRAM | 6.8 GB |

Es el mas lento de los Gemma 4 porque es **denso**: activa todos sus parametros en cada
token, al contrario que el E4B y el 26B-A4B. A cambio da la calidad de un 12B completo.

MTP desactivado por defecto; activable con `LLM_MTP=on`.
