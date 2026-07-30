# Gemma 4 26B-A4B

Mezcla de expertos: 25B de parametros totales pero solo ~4B activos por token. Acepta
imagenes **y video**.

| | |
|---|---|
| Pesos | `unsloth/gemma-4-26B-A4B-it-GGUF` · UD-Q3_K_XL (12.91 GB) |
| Drafter MTP | activado por defecto |
| Contexto | 64K (KV a 4 bits) |

## Medido aqui

| | |
|---|---|
| Generacion | 16.8-19.8 tok/s segun el prompt, con MTP |
| Prefill | 160.46 tok/s |
| VRAM | 15.0 GB bajo carga (91% del carveout) |
| GTT | 301 MiB |

## Por que 64K y KV a 4 bits

opencode necesita 64K o mas para funcionar bien, y este modelo con KV en f16 ya ocupaba el
**98%** del carveout a 64K. Cuantizando la KV a `q4_0` baja al **91%**, con el GTT en
301 MiB y 12.8 GB de RAM libre. Incluso 128K entra (94%), pero la velocidad cae de 16.8 a
14.4 tok/s porque hay mas KV que recorrer por token.

Efecto secundario medido: la KV cuantizada **le resta precision al drafter MTP**, cuya
aceptacion baja del 56.6% al 35.5%. Aun asi sigue compensando (18.12 -> 19.78 tok/s, +9%),
asi que se queda activado.

## Por que Q3 y no la QAT Q4

La cuantizacion QAT oficial pesa **14.25 GB** y no cabe holgadamente: bajo carga este
Q3_K_XL ya ocupa 15.2 GB de los 16.4 del carveout de la Legion Go S (94%), con el GTT en
234 MiB y 13 GB de RAM libre. Con la QAT se derramaria a GTT, que sale de la RAM del
sistema y es lo que provoco un OOM en su dia.

**En una maquina con mas VRAM, cambia el `[download]` del `model.toml` a
`unsloth/gemma-4-26B-A4B-it-qat-GGUF`.** Tampoco subas el contexto por encima de 32K aqui
sin volver a medir.

## El MTP: el unico que ha ganado

Es la cuarta prueba de decodificacion especulativa en esta maquina y **la primera que sale
a cuenta**:

| | |
|---|---|
| Sin MTP | 18.85 tok/s |
| Con MTP | **20.37 tok/s** (+8%) |
| Aceptacion | 56.6% (207 de 366), longitud media 3.25 |
| Coste | ~320 MiB de VRAM |

La diferencia con los fracasos anteriores (dspark, ngram, eagle3) esta en el diseno: el
drafter de Gemma 4 **comparte la KV del modelo principal**, mientras que dspark exigia su
propio contexto y por eso costaba 2.7 GB para no aportar nada.
