# Qwen A1 4B en la Legion Go S

Segunda instalacion, **independiente de Bonsai**: otro modelo, otro llama.cpp, otro puerto.
Replica la configuracion del video de Nichonauta
([youtu.be/IDoL_A1VixA](https://www.youtube.com/watch?v=IDoL_A1VixA)).

## Uso

```bash
qwen              # arranca + panel en vivo. Ctrl+C = apagado total
```

```bash
QWEN_THINK=512 qwen     # acotar el razonamiento (por defecto va sin limite)
QWEN_THINK=off qwen     # sin razonar
QWEN_CTX=262144 qwen    # el modelo admite hasta 262144
QWEN_PORT=8092 qwen     # otro puerto
```

Puede convivir con Bonsai en la configuracion (8091 vs 8090), pero **no cargues los dos a
la vez**: entre ambos se comerian la memoria.

## Conectarse

| | |
|---|---|
| WebUI | `http://TU-IP-LOCAL:8091` |
| API | `http://TU-IP-LOCAL:8091/v1` (compatible OpenAI) |
| API key | `PON-AQUI-TU-CLAVE` (compartida, en `/home/deck/llm/apikey`) |

## Rendimiento medido (Z1 Extreme, Vulkan)

Mismo test que se uso con Bonsai (`llama-bench -p 512 -n 32 -r 3`):

| | Bonsai 27B Q2_0 | **Qwen A1 4B Q8_0** | mejora |
|---|---|---|---|
| Generacion (tg32) | 4.51 t/s | **16.64 t/s** | **3.7x** |
| Prefill (pp512) | 43.81 t/s | **249.69 t/s** | **5.7x** |
| VRAM en uso | 10659 MiB | **9589 MiB** | menos |
| GTT | 561 MiB | **338 MiB** | menos |

Para trabajar con un agente (opencode) la diferencia es enorme: el prefill es lo que se
paga en cada turno, y ahi va casi 6 veces mas rapido.

## Configuracion, y por que es la del video

| Ajuste | Motivo |
|---|---|
| llama.cpp **estandar** (b10195) | El video usa "el llama CPP normal", no el fork de PrismML. Este modelo es Q8_0 corriente y no necesita kernels especiales |
| `Agents-A1-4B-Q8_0.gguf` (4.48 GB) | El video descarga "4B a 8 bits"; el tamano coincide exacto con el que menciona |
| **Sin MTP** | En el video falla el arranque justamente por eso: *"desgraciadamente no tiene MTP"*. Quito esos parametros |
| **Sin cuantizar el KV** | El video lo retira al ver que sobra memoria. Aqui tambien sobra: 9.6 GB de 16 |
| **Sin vision** | El video no descarga el mmproj. Si lo pones en `models/`, el lanzador lo detecta y lo usa |
| `-c 131072` | El video mantiene "la misma ventana de contexto" que su Bonsai, que eran 131K |
| `temp 0.85 · top_p 0.95 · top_k 20 · min_p 0 · presence_penalty 1.1` | El video avisa de que este fine-tune *"requiere otros ajustes de temperatura"*; estos son los de la ficha de `InternScience/Agents-A1-4B` |

Modelo: [InternScience/Agents-A1-4B](https://huggingface.co/InternScience/Agents-A1-4B) -
fine-tune de Qwen 3.5 4B orientado a agentes (llama.cpp lo identifica como `qwen35 4B`).

## Desde Steam

No tiene atajo propio: se lanza desde **"Modelos locales"**, el selector en
`/home/deck/llm`, que comparte puerto y clave entre todos los modelos.

## Que hay instalado

```
/home/deck/qwen-a1/
├── qwen                   lanzador (enlazado en ~/.local/bin/qwen)
├── qwen-steam             version a pantalla completa para Modo Juego
├── bin/                   llama.cpp estandar b10195, build Vulkan
├── models/Agents-A1-4B-Q8_0.gguf   4.48 GB
├── qwen.png, art/         icono y caratulas de Steam
└── logs/server.log
```

Normalmente no se lanza suelto sino desde el selector `llm` (/home/deck/llm), que usa el
puerto **8090** para todos los modelos para que opencode no tenga que cambiar de
configuracion segun cual este cargado.
