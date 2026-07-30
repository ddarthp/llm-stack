# llm-stack

Modelos de lenguaje en local sobre una **Lenovo Legion Go S (Ryzen Z1 Extreme, SteamOS)**,
lanzables desde la biblioteca de Steam como si fueran un juego.

Un solo icono abre un selector, eliges modelo, y arranca un servidor compatible con la API
de OpenAI en el puerto 8090 con un panel en vivo de tokens, CPU, GPU, RAM y VRAM.

```
  MODELOS LOCALES   puerto 8090 para todos
  ──────────────────────────────────────────────────────────────────

   ▸ gpt-oss 20B    24.3 tok/s · prefill 200 tok/s · 12.6 GB
     Qwen A1 4B     16.6 tok/s · prefill 250 tok/s · 9.6 GB
     Gemma 3n E4B   14.8 tok/s · prefill 194 tok/s · 5.9 GB
     Gemma 3 12B     9.4 tok/s · prefill 100 tok/s · 7.5 GB
     Bonsai 27B      4.5 tok/s · prefill  44 tok/s · 10.7 GB
  ──────────────────────────────────────────────────────────────────
```

## Estado

| Sistema | Estado |
|---|---|
| Linux / SteamOS | **Funcionando y medido** |
| macOS | Codigo escrito, **sin probar** en una maquina real |
| Windows | Codigo escrito, **sin probar**; falta el backend de GPU |

Lo que queda por rematar en cada sistema esta en [TODO.md](TODO.md), con casillas.

## Instalacion

```bash
git clone https://github.com/ddarthp/llm-stack.git
cd llm-stack
python3 install.py            # dice que detecta y que falta
python3 install.py qwen-a1    # runtime + pesos de un modelo (4.5 GB)
python3 -m llmstack           # selector
```

Necesita **Python 3.11+** (por `tomllib`). `pip install psutil` es opcional en Linux y
recomendable en macOS y Windows, donde si no no habra datos de CPU ni RAM.

## Que hay aqui

| | |
|---|---|
| `selector/` | El selector de modelos (`llm`) y su version a pantalla completa para Modo Juego |
| `llmstack/` | El paquete: rutas, estadisticas, panel, runner y selector |
| `llmstack/paths.py` · `sysinfo.py` | **Lo unico especifico de cada sistema** |
| `install.py` | Detecta sistema y backend, baja llama.cpp y los pesos |
| `models/*/model.toml` | Lo unico que cambia entre modelos: pesos, contexto, sampling |
| `models/` | Seis modelos: gpt-oss 20B, tres Gemma 4 (E4B, 12B, 26B-A4B), Qwen A1 4B y Bonsai 27B |
| `tools/steam-add` | Anade y quita atajos no-Steam escribiendo `shortcuts.vdf` directamente |
| `tools/bonsai-power` | Sube el TDP de la APU mientras corre el modelo (opcional, necesita root) |
| `extras/` | Caratulas de otras aplicaciones anadidas a Steam |

**Lo que no esta en el repositorio**: los pesos de los modelos (13 GB) y los binarios de
llama.cpp. Se descargan aparte; las instrucciones estan en el README de cada modelo.

## Rendimiento medido

Z1 Extreme con iGPU Radeon 780M, backend Vulkan, `llama-bench -p 512 -n 32 -r 3`:

| Modelo | Generacion | Prefill | VRAM |
|---|---|---|---|
| gpt-oss 20B MXFP4 | **24.27 tok/s** | 200.41 tok/s | 12.6 GB |
| Gemma 4 E4B QAT Q4 | 23.34 tok/s | **244.49 tok/s** | **4.9 GB** |
| Gemma 4 26B-A4B Q3 | 20.37 tok/s (con MTP) | 160.46 tok/s | 15.2 GB |
| Qwen A1 4B Q8_0 | 16.64 tok/s | 249.69 tok/s | 9.6 GB |
| Gemma 4 12B QAT Q4 | 9.62 tok/s | 92.43 tok/s | 6.8 GB |
| Bonsai 27B Q2_0 | 4.51 tok/s | 43.81 tok/s | 10.7 GB |

Lo que rompe la intuicion: **los modelos de mezcla de expertos y de activacion selectiva
ganan a los densos**. gpt-oss 20B y Gemma 4 26B generan mas rapido que un Gemma 4 12B
denso, y el Gemma 4 E4B casi iguala a gpt-oss ocupando un tercio. Y **Bonsai 27B, el mas
comprimido, es el mas lento**: sus kernels ternarios en Vulkan rinden peor que los formatos
comunes.

### Contexto por defecto

No es el maximo de cada modelo sino lo que cabe con margen, medido cargando cada uno:

| Modelo | Contexto | VRAM | % del carveout (16.4 GB) |
|---|---|---|---|
| Gemma 4 E4B | 128K | 6.4 GB | 39% |
| Gemma 4 12B | 128K | 10.1 GB | 61% |
| Qwen A1 4B | 128K | 9.6 GB | 59% |
| Bonsai 27B | 146K | 13.2 GB | 81% |
| gpt-oss 20B | 64K | 13.3 GB | 81% |
| Gemma 4 26B-A4B | 32K | 15.2 GB | 94% |

Los dos ultimos estan limitados por sus pesos, no por capricho: gpt-oss admite 128K pero
ahi sube al 90%, y el 26B ya va al 94% con solo 32K. Se puede forzar cualquiera con
`LLM_CTX=131072`, midiendo antes.

En esta maquina el techo real es el **carveout de 16 GB** que reserva la BIOS: lo que
quepa ahi no le quita nada al sistema. Vulkan puede direccionar 24 GB (carveout + GTT) y
subiendo `amdgpu.gttsize` llegaria a 28, pero el GTT sale de los 15.7 GB que ve Linux, asi
que no es memoria extra: es quitarsela al escritorio.

### Decodificacion especulativa: tres fracasos y un acierto

| Metodo | Modelo | Resultado |
|---|---|---|
| DSpark (MTP) | Bonsai 27B | 3.48 vs 4.37 tok/s, y **tumba el driver Vulkan** con prompts de codigo |
| ngram (sin drafter) | Qwen A1 4B | 4.00 vs 4.35 tok/s, aceptacion 15% |
| eagle3 | gpt-oss 20B | 19.6 vs 23.8 tok/s, aceptacion 55% |
| **MTP de Gemma 4** | **Gemma 4 26B-A4B** | **20.37 vs 18.85 tok/s (+8%)**, aceptacion 57% |

La diferencia del que gana esta en el diseno, no en el modelo: el drafter de Gemma 4
**comparte la KV del modelo principal** y cuesta ~320 MiB, mientras que dspark exigia su
propio contexto y se comia 2.7 GB para no aportar nada. En el Gemma 4 E4B el MTP queda en
empate (+1%, ruido), asi que solo va activado por defecto en el 26B.

## Notas del hardware

Cosas especificas de esta maquina que costaron encontrar y estan documentadas en detalle
en los README correspondientes:

- La BIOS reserva **16 GB fijos** para la iGPU, asi que Linux solo ve 15.7 GB de los 32.
  Hay dos bolsas de memoria distintas (carveout y GTT) y confundirlas provoca OOM.
- El puerto 8080 lo ocupa `steamwebhelper`, de ahi el 8090.
- En Modo Juego, Steam inyecta `LD_PRELOAD` con un overlay de 32 bits que hace que **cada
  proceso hijo** escupa un error; en una TUI que se refresca cada segundo, eso sepulta la
  pantalla. Se resuelve con `unset LD_PRELOAD` y minimizando forks.
- Konsole muestra una barra de herramientas que no se puede ocultar por linea de ordenes,
  por eso el lanzador usa `xterm`.

## Portar a Windows y macOS

El grueso ya esta hecho: las rutas se derivan del sistema en vez de estar incrustadas y las
estadisticas tienen un backend por plataforma. **Solo `llmstack/paths.py` y
`llmstack/sysinfo.py` contienen codigo especifico de un sistema**; el panel, el runner y la
configuracion son identicos en los tres.

Falta verificarlo en maquinas reales y cerrar los huecos conocidos: la GPU en Windows, la
terminal a pantalla completa en macOS y el mando fuera de Linux. Todo desglosado con
casillas en [TODO.md](TODO.md).

## Licencia

MIT — ver [LICENSE](LICENSE). Aplica al codigo de este repositorio: lanzadores, selector y
herramientas. **Los pesos de los modelos tienen sus propias licencias** y no se distribuyen
aqui; consulta cada uno en Hugging Face antes de usarlo, sobre todo si es para algo
comercial. llama.cpp es MIT; el fork de PrismML que usa Bonsai tiene su propia licencia.
