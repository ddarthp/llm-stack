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

**Funciona en Linux / SteamOS.** Windows y macOS son el siguiente objetivo, todavia no
soportados: ver [Portar a Windows y macOS](#portar-a-windows-y-macos).

## Que hay aqui

| | |
|---|---|
| `selector/` | El selector de modelos (`llm`) y su version a pantalla completa para Modo Juego |
| `runner/run-model` | El lanzador. Uno solo para todos los modelos, parametrizado por `model.conf` |
| `models/*/model.conf` | Lo unico que cambia entre modelos: pesos, contexto, sampling y flags propios |
| `models/` | Cinco modelos: gpt-oss 20B, Qwen A1 4B, Gemma 3n E4B, Gemma 3 12B y Bonsai 27B |
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
| Qwen A1 4B Q8_0 | 16.64 tok/s | **249.69 tok/s** | 9.6 GB |
| Gemma 3n E4B Q8_0 | 14.81 tok/s | 194.07 tok/s | **5.9 GB** |
| Gemma 3 12B QAT Q4_0 | 9.36 tok/s | 99.55 tok/s | 7.5 GB |
| Bonsai 27B Q2_0 | 4.51 tok/s | 43.81 tok/s | 10.7 GB |

Dos resultados que rompen la intuicion: **gpt-oss 20B genera mas rapido que un 4B denso**
porque es mezcla de expertos y activa pocos parametros por token; y **Bonsai 27B, el mas
comprimido, es el mas lento**, porque los kernels ternarios en Vulkan no estan tan
optimizados como los formatos comunes.

### Decodificacion especulativa: tres intentos, tres fracasos

Se probaron los tres metodos disponibles y **ninguno gana** en esta iGPU:

| Metodo | Modelo | Resultado |
|---|---|---|
| DSpark (MTP) | Bonsai 27B | 3.48 vs 4.37 tok/s, y **tumba el driver Vulkan** de forma reproducible con prompts de codigo |
| ngram (sin drafter) | Qwen A1 4B | 4.00 vs 4.35 tok/s, aceptacion 15% |
| eagle3 | gpt-oss 20B | 19.6 vs 23.8 tok/s, aceptacion 55% |

Tres modelos, tres arquitecturas de drafter distintas, mismo resultado: parece una
limitacion del backend Vulkan sobre esta GPU integrada, no de los modelos.

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

Lo que habria que cambiar, por orden de dificultad:

1. **Rutas fijas.** Los lanzadores tienen `/home/deck/...` incrustado. Hay que derivarlas
   de la ubicacion del script y de una carpeta de datos por sistema.
2. **El panel.** Es bash y lee `/proc/stat`, `/proc/meminfo` y `/sys/class/drm` para las
   estadisticas. Reescribirlo en Python (como ya esta el selector) con un backend por
   sistema: `psutil` para CPU y RAM, y para la GPU `nvidia-smi` / `powermetrics` /
   sysfs segun toque.
3. **Binarios de llama.cpp.** Ahora se descargan a mano. Hace falta un instalador que
   detecte sistema y backend (CUDA, Metal, Vulkan, ROCm, CPU) y baje la build correcta,
   mas los pesos desde Hugging Face.
4. **Integracion con Steam.** `shortcuts.vdf` es igual en los tres sistemas; solo cambia
   la ruta de `userdata`. `tools/steam-add` ya es Python y se porta facil.
5. **La terminal a pantalla completa.** `xterm` no existe en Windows ni macOS; habria que
   usar Windows Terminal y Terminal.app / iTerm.

Nada de eso es conceptualmente dificil, pero es una reescritura de los lanzadores, no un
retoque.

## Seguridad

La API key es fija y compartida (`PON-AQUI-TU-CLAVE`) porque esto es un servidor de red local de
uso ocasional y se prioriza que sea comoda de escribir. **Si haces publico este repositorio
o expones el servidor fuera de tu red, cambiala.** Cualquiera que la sepa y llegue al
puerto puede usar el modelo.
