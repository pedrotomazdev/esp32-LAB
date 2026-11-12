import gc


def medir_memoria(etapa, flash=False, coletar=True):
    if coletar:
        gc.collect()
    print("[MEM]", etapa, "RAM livre:", gc.mem_free(), "RAM usada:", gc.mem_alloc())
    if flash:
        import os
        fs = os.statvfs("/")
        print("[MEM] Flash livre:", fs[0] * fs[3])
