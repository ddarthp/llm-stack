# Bonsai 27B en la Legion Go S (SteamOS)

Servidor local de IA bajo demanda. Se enciende y se apaga con una terminal.

## Uso

```bash
bonsai            # arranca + panel en vivo. Ctrl+C (o cerrar la terminal) = apagado total
```

No hay servicio de fondo ni autoarranque: si no lo lanzas tú, no consume nada.

### Variantes

```bash
BONSAI_THINK=off bonsai     # sin razonamiento: respuestas casi inmediatas
BONSAI_THINK=2048 bonsai    # razona mas (mejor en problemas dificiles, ~7 min por respuesta)
BONSAI_THINK=max bonsai     # sin limite
BONSAI_IMG=0 bonsai         # imagenes sin recortar: mejor OCR, mucho mas lento
BONSAI_CTX=32768 bonsai     # contexto corto: arranca antes y usa ~6 GB menos de VRAM
BONSAI_PORT=8091 bonsai     # otro puerto
BONSAI_NGL=0 bonsai         # CPU pura (mas lento: 1.7 t/s frente a 4.5)
BONSAI_MTP=on bonsai        # DSpark / multi-token prediction. MEDIDO: PIERDE aqui (ver abajo)
```

## Desde Steam

Ya no tiene atajo propio: se lanza desde **"Modelos locales"**, el selector en
`/home/deck/llm`, que ofrece este modelo y Qwen A1 en el mismo puerto. Los detalles
de Modo Juego (xterm, `unset LD_PRELOAD`, tipografia) estan en `/home/deck/llm/README.md`.

El lanzador suelto `bonsai-steam` sigue existiendo si lo quieres directo.

## Conectarse

| | |
|---|---|
| WebUI | `http://TU-IP-LOCAL:8090` |
| API | `http://TU-IP-LOCAL:8090/v1` (compatible OpenAI) |
| Modelo | cualquier nombre, se ignora |
| API key | `PON-AQUI-TU-CLAVE` (compartida, en `/home/deck/llm/apikey`) |

```bash
curl http://TU-IP-LOCAL:8090/v1/chat/completions \
  -H "Authorization: Bearer PON-AQUI-TU-CLAVE" \
  -H 'Content-Type: application/json' \
  -d '{"model":"bonsai","messages":[{"role":"user","content":"hola"}]}'
```

El modelo **razona antes de responder**: el texto final va en `message.content` y el
razonamiento en `message.reasoning_content`. La reflexion esta acotada a 512 tokens por
defecto; la WebUI permite cambiarlo por conversacion con el selector de esfuerzo.

Acepta imagenes (multimodal, mmproj cargado) por el campo `image_url` estandar de OpenAI.

La WebUI viene con los servidores MCP de **Hugging Face** y **DeepWiki** disponibles en el
selector de herramientas, y un system message propio. Se configura en `webui-config.json`.

## Usar con opencode

Plantilla en `/home/deck/llm/opencode.json`, ya con la clave y el puerto correctos:

```bash
mkdir -p ~/.config/opencode && cp /home/deck/llm/opencode.json ~/.config/opencode/opencode.json
```

`baseURL` **debe** ir dentro de `options`; si lo pones en la raiz, opencode manda las
peticiones a `undefined/chat/completions`.

Lo que hace usable un agente aqui es la **cache de prompts**: sin ella cada turno
re-procesa toda la conversacion a ~45 t/s de prefill (una sesion de 20k tokens serian
7 minutos por turno). Por eso el lanzador reserva 4 GB (`BONSAI_CACHE_RAM`) y por eso
**no** hay que activar el MTP, que la desactiva (ver abajo).

Para un agente conviene bajar la reflexion, porque cada ida y vuelta de herramienta la
paga entera:

```bash
BONSAI_THINK=off bonsai     # respuestas directas, ideal para bucles de herramientas
BONSAI_THINK=256 bonsai     # un poco de razonamiento sin disparar la latencia
```

## Configuracion aplicada y por que

Todo esto sale de la documentacion de PrismML (`AGENTS.md`, `KV-CACHE.md`, `SPECULATIVE.md`)
mas mediciones propias en esta maquina.

| Ajuste | Motivo |
|---|---|
| `--temp 0.7 --top-p 0.95 --top-k 20 --min-p 0` | Sampling recomendado para el 27B. Los defaults de llama.cpp (`top-k 40`, `min-p 0.05`) dan peor calidad |
| `--image-min-tokens 1024` | Qwen-VL lo necesita o degrada el *grounding* (el propio servidor avisa) |
| `--image-max-tokens 1024` | Default de PrismML en Vulkan/Metal/CPU: sin tope, una captura grande son ~90 s solo de prefill |
| `--reasoning-budget 512` | A 4.5 t/s, razonar sin limite se va a 5-7 min por respuesta |
| `-ub 512` | 2048 daba +4% de prefill pero ~500 MiB extra de GTT. Ver "Presupuesto de memoria" |
| `--cache-ram 1024` | Cache de prompts. Con 4096 se provoco un OOM global. Ver abajo |
| `-c 150000` | A 262144 la VRAM roza el 85% del carveout y se derrama a GTT |
| `-ctk q4_0 -ctv q4_0` | Imprescindible para 256K (en FP16 el KV serian 16 GiB). Medido: cuesta solo un 0.7% |
| `--kv-mean-center` | Recupera precision del KV de 4 bits a coste cero. Exige `LLAMA_ATTN_ROT_DISABLE=1` |
| `-fa on` | Neutro en velocidad aqui, pero el KV cuantizado lo requiere |
| `-ngl 99` (Vulkan) | Medido: 4.5 t/s frente a 1.7 t/s en CPU pura |

### El sesgo del KV (mean-centering)

`models/Ternary-Bonsai-27B-kv-bias.gguf` se genero con `llama-kv-mean-center` sobre
`kv-corpus.txt`, un corpus de calibracion con espanol conversacional, texto tecnico y codigo,
representativo del uso real. Regeneralo si cambias de modelo:

```bash
cd /home/deck/bonsai && LD_LIBRARY_PATH=bin ./bin/llama-kv-mean-center \
  -m models/Ternary-Bonsai-27B-Q2_0.gguf -f kv-corpus.txt \
  -o models/Ternary-Bonsai-27B-kv-bias.gguf -ngl 99 -c 1024
```

El servidor **rechaza el sesgo por diseno** si la rotacion de K no coincide entre
calibracion e inferencia; el lanzador ya exporta `LLAMA_ATTN_ROT_DISABLE=1` por eso.

## Rendimiento medido (Z1 Extreme, Vulkan/RADV)

| | |
|---|---|
| Generacion | 4.5 tok/s |
| Prefill | 45.8 tok/s (con `-ub 2048`) |
| Carga | 5-12 s |
| VRAM | 13.2 GB con 256K de contexto |

Barridos hechos: `-fa 0/1` (sin diferencia: 43.81 en ambos), KV `f16` vs `q4_0`
(4.53 vs 4.50 t/s), `-ub 256/512/1024/2048` (43.6 / 44.0 / 44.7 / 45.8 t/s).

El prefill a ~45 tok/s es el techo del hardware con estos kernels ternarios: llenar los
262 144 tokens de contexto llevaria mas de una hora. El contexto grande sirve para
conversaciones largas, no para volcar un corpus de golpe.

## Presupuesto de memoria (importante)

Esta maquina tiene **dos bolsas de memoria distintas** y es facil confundirlas:

- **Carveout de 16 GB**: reservado por la BIOS para la iGPU. Invisible para Linux. Aqui
  viven el modelo, el KV y los buffers de computo.
- **15.7 GB visibles**: lo que ve el sistema. De aqui salen el escritorio, la
  **cache de prompts** (`--cache-ram`) y el **GTT**, que es lo que la GPU pide prestado
  cuando no le cabe algo en el carveout.

El fallo a evitar: si el carveout se llena, el exceso se derrama a GTT y compite con el
escritorio. Con `-c 262144 --cache-ram 4096 -ub 2048` la VRAM llegaba al 85% del carveout,
el GTT subia a 1494 MiB y la cache de prompts crecia hasta 4 GB de RAM: **OOM global**
que se llevo por delante el navegador y la sesion de escritorio.

Medido con 5 prompts distintos y 177 muestras:

| Configuracion | VRAM | GTT | RAM libre minima |
|---|---|---|---|
| `262144` · cache 4G · ub 2048 | 13870 (85%) | 1494 MiB | OOM |
| **`150000` · cache 1G · ub 512** | **10659 (65%)** | **561 MiB** | **11048 MiB** |
| `131072` · cache 1G · ub 512 | 10263 (63%) | 538 MiB | - |

Bajar de `-ub 2048` a `512` **no cuesta generacion** (4.3 t/s en ambos), solo un 4% de
prefill. Si algun dia amplias la RAM visible (UMA en Auto), se pueden volver a subir.

## Energia: TDP y governor

El equipo viene a **15 W sostenidos** de un maximo de 40 W, y el governor en `powersave`.
El lanzador sube la APU al arrancar y la devuelve a su estado previo al salir, pero eso
necesita root, asi que hay una instalacion unica:

```bash
sudo install -m 755 -o root -g root /home/deck/bonsai/bonsai-power /etc/bonsai-power
sudo install -m 440 -o root -g root /home/deck/bonsai/sudoers-bonsai-power /etc/sudoers.d/bonsai-power
```

Va en `/etc` y no en `/usr/local` porque en SteamOS `/etc` es un overlay que sobrevive a
las actualizaciones del sistema; `/usr/local` se pierde.

El helper toca `ppt_pl1_spl` / `ppt_pl2_sppt` / `ppt_pl3_fppt` (WMI de Lenovo), el
governor de las 16 CPUs y `power_dpm_force_performance_level` de la GPU. Guarda los
valores previos en `/run` y los restaura al salir; si el equipo se apaga de golpe,
al reiniciar vuelven los defaults de la BIOS igualmente.

```bash
BONSAI_TDP=0  bonsai        # no tocar la energia (bateria)
BONSAI_TDP=25 bonsai        # punto intermedio
sudo /etc/bonsai-power status   # ver el estado actual
```

La regla de sudoers solo permite ese binario concreto, que es root:root y no editable
por el usuario.

## MTP (DSpark) - medido y descartado

Probado con el mismo prompt, `temperature 0` y 250 tokens:

| Configuracion | Generacion |
|---|---|
| Sin MTP, 256K ctx | **4.50 t/s** |
| Sin MTP, 32K ctx | **4.37 t/s** |
| Con MTP (dspark n=4), 32K ctx | **3.48 t/s** - 20% mas lento |

La especulacion se activaba de verdad, con **62.7%** de aceptacion (178 de 284 tokens).
Aun asi pierde: verificar un bloque de 4 tokens cuesta ~0.82 s frente a 0.229 s de un token
suelto, o sea **3.6x** - los kernels ternarios en Vulkan/RADV no amortizan el lote. La propia
`SPECULATIVE.md` de PrismML dice que la ruta es rapida y estable **solo en CUDA**.

No hay nada que ajustar: `--spec-draft-n-max` **debe** valer 4, el `block_size` del drafter.
Ademas es incompatible con los 256K: el drafter se entreno a 4096 y al escalarlo falla con
`failed to allocate compute pp buffers`, quedandose cargado pero inactivo.

Y con carga de **codigo** es peor que lento: tumba el driver de forma **reproducible**
(`vk::DeviceLostError: ErrorDeviceLost`, dos de dos intentos). La GPU se recupera sola,
pero el servidor muere a mitad de respuesta.

Tercer motivo, decisivo para agentes: activar especulacion **desactiva la reutilizacion
de la cache de prompts entre peticiones**, o sea que cada turno de opencode re-procesaria
la conversacion entera a 45 t/s. Es justo lo contrario de lo que necesita un agente.

### Sobre el video de Nichonauta

El video (`youtube.com/watch?v=VnAT1ucIApw`) **no usa MTP**. La unica mencion esta en el
minuto 04:51, listando los ficheros del repo de HuggingFace: "tambien tenemos DSpark para
speculative decoding y tambien tenemos vision". En su configuracion real de ejecucion
(06:39-07:20) enumera build de CUDA, todas las capas en GPU, ventana de contexto y KV en
Q4 - sin ningun flag de especulacion. Y usa **131.000 tokens de contexto, no 262.144**,
con 9.6 GB de VRAM: practicamente lo mismo que medimos aqui a 131072 (10.2 GB con el
proyector de vision cargado).

`Ternary-Bonsai-27B-dspark-Q4_1.gguf` (1.9 GB) se puede borrar sin consecuencias.

## Que hay instalado

```
/home/deck/bonsai/
├── bonsai                 lanzador (enlazado en ~/.local/bin/bonsai)
├── bin/                   llama.cpp fork de PrismML b9596, build Vulkan
├── models/
│   ├── Ternary-Bonsai-27B-Q2_0.gguf         6.7 GB
│   ├── Ternary-Bonsai-27B-mmproj-Q8_0.gguf  601 MB (vision)
│   ├── Ternary-Bonsai-27B-kv-bias.gguf       65 KB (sesgo del KV)
│   └── Ternary-Bonsai-27B-dspark-Q4_1.gguf  1.9 GB (MTP, sin uso)
├── kv-corpus.txt          corpus de calibracion del sesgo
├── webui-config.json      MCP + system message de la WebUI
└── logs/server.log        log de la ultima sesion
```

Se necesita el fork de PrismML: la cuantizacion ternaria `Q2_0` no la lee un llama.cpp normal.

## Notas del sistema

- El puerto **8080 esta ocupado por `steamwebhelper`** (Steam), por eso se usa el 8090.
- Firewalld ya abre `1024-65535/tcp` en la zona `public`, asi que la LAN llega sin sudo.
- La BIOS tiene **UMA fijo en 16 GB**: de los 32 GB fisicos, Linux solo ve 15.7 GB y los
  otros 16 GB son carveout de la iGPU. Con esa reserva el modelo entra entero en VRAM y
  los 256K de contexto caben. Si pones UMA en *Auto* ganas ~15 GB de RAM para el sistema,
  pero el heap de la GPU pasa a depender del GTT (~la mitad de la RAM) y conviene anadir
  `amdgpu.gttsize=24576` al arranque para que los 256K sigan cabiendo.
