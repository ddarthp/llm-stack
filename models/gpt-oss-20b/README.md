# gpt-oss 20B

Modelo abierto de OpenAI, en **MXFP4**, que es su formato nativo y no una cuantizacion
posterior. Es una mezcla de expertos: 20.9B parametros totales pero pocos activos por
token, y de ahi que sea el mas rapido generando pese a ser el segundo mas grande.

| | |
|---|---|
| Pesos | `ggml-org/gpt-oss-20b-GGUF` · `gpt-oss-20b-MXFP4.gguf` (12.11 GB) |
| Runtime | llama.cpp estandar (necesita soporte MXFP4) |
| Contexto | 32K configurado |

## Medido en esta maquina

| | |
|---|---|
| Generacion | **24.27 tok/s** — el mas rapido de los cinco |
| Prefill | 200.41 tok/s |
| VRAM | 12.6 GB de los 16 del carveout |

Es el que mas VRAM ocupa. A 32K de contexto deja margen (GTT en 226 MiB), pero subir mucho
el contexto lo acercaria al techo del carveout; ver "Presupuesto de memoria" en el README
de Bonsai.

## Ajustes

Su `generation_config.json` no fija sampling, asi que se usan los valores publicados por
OpenAI: `--temp 1.0 --top-p 1.0 --top-k 0`. Razona, y el razonamiento va en
`message.reasoning_content`.

## El drafter eagle3: probado y descartado

El repositorio incluye `eagle3-gpt-oss-20b-Q8_0.gguf` (921 MB) para decodificacion
especulativa. Medido aqui con un prompt de codigo y `temperature 0`:

| | |
|---|---|
| Sin eagle3 | **23.8 tok/s** |
| Con eagle3 | 19.6 tok/s, aceptacion 55% (155 de 281), longitud media 2.65 |

Pierde un 18%. Es el **tercer** metodo de especulacion que se prueba en esta maquina y
falla, despues de dspark en Bonsai y de las variantes ngram; parece un patron del backend
Vulkan sobre esta iGPU y no algo del modelo. A diferencia de dspark, al menos este no
tumba el driver.

## Descargar

```bash
cd /home/deck/gpt-oss-20b/models
curl -L -O https://huggingface.co/ggml-org/gpt-oss-20b-GGUF/resolve/main/gpt-oss-20b-MXFP4.gguf
```
