"""
JustIA - Actividad 2: diccionario tecnico y funcion de prediccion
Caso practico Unidad 1 - IA aplicada al desarrollo de software
Autor: Stanly Leon Calle Samper

La funcion principal es predecir_categoria(texto). Recibe un texto libre
(pregunta del usuario, fragmento de sentencia, lo que sea) y devuelve la
categoria mas probable segun diccionario_juridico.json.

Decisiones importantes:
  * El texto y los terminos del diccionario pasan por EL MISMO preprocesamiento
    de la actividad 1. Si no, "despedido" del diccionario nunca coincide con
    "despedir" del texto lematizado.
  * Las expresiones de varias palabras ("violencia patrimonial") pesan el doble
    que una palabra suelta y se buscan primero; las palabras que ya hicieron
    parte de una expresion no se vuelven a contar.
  * La funcion NO decide sola: devuelve el puntaje de todas las categorias, los
    terminos que hicieron match y una bandera de "revision_humana" cuando el
    puntaje es bajo o cuando dos categorias quedan muy parejas.

Uso:
  python3 actividad2_clasificador.py                  -> evalua contra el corpus
  python3 actividad2_clasificador.py "texto a probar" -> clasifica ese texto
"""

import csv
import json
import sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

BASE = Path(__file__).resolve().parent
CARPETA_ACT1 = BASE.parent / "actividad1"
sys.path.insert(0, str(CARPETA_ACT1))  # reutiliza el preprocesamiento de la actividad 1

from actividad1_preprocesamiento import procesar  # noqa: E402

RUTA_DICCIONARIO = BASE / "diccionario_juridico.json"
RUTA_CORPUS = CARPETA_ACT1 / "corpus_original.csv"
RUTA_PRUEBA = BASE / "preguntas_prueba.csv"


def _lemas(texto):
    return procesar(texto, motor="reglas")["lemas"]


@lru_cache(maxsize=1)
def cargar_diccionario(ruta=str(RUTA_DICCIONARIO)):
    """Carga el JSON y convierte cada termino a su forma lematizada."""
    with open(ruta, encoding="utf-8") as f:
        crudo = json.load(f)

    categorias = {}
    for nombre, info in crudo["categorias"].items():
        palabras = {}
        for p in info["palabras_clave"]:
            lem = _lemas(p)
            if lem:
                palabras[lem[0]] = p          # lema -> termino original (para mostrar)
        expresiones = {}
        for e in info["expresiones"]:
            lem = tuple(_lemas(e))
            if lem:
                expresiones[lem] = e
        categorias[nombre] = {"palabras": palabras, "expresiones": expresiones}

    alertas = {}
    for nombre, info in crudo["alertas_terminologicas"].items():
        if nombre == "nota":
            continue
        alertas[nombre] = {
            "fuente": info["fuente"],
            "definicion": info["definicion"],
            "indicadores": [tuple(_lemas(i)) for i in info["indicadores"]],
        }

    return {
        "version": crudo["version"],
        "pesos": crudo["pesos"],
        "umbral": crudo["umbral_minimo"],
        "categorias": categorias,
        "alertas": alertas,
    }


def _buscar_secuencia(lemas, secuencia, usados):
    """Devuelve las posiciones donde aparece la secuencia sin pisar usados."""
    n = len(secuencia)
    hallazgos = []
    for i in range(len(lemas) - n + 1):
        if tuple(lemas[i:i + n]) == secuencia and not any(j in usados for j in range(i, i + n)):
            hallazgos.append(range(i, i + n))
    return hallazgos


def detectar_alertas(lemas, dic):
    """Revisa terminos sensibles (violencia economica vs patrimonial)."""
    encontradas = []
    for nombre, info in dic["alertas"].items():
        for ind in info["indicadores"]:
            if ind and _buscar_secuencia(lemas, ind, set()):
                encontradas.append({"tipo": nombre, "fuente": info["fuente"],
                                    "definicion": info["definicion"]})
                break
    return encontradas


def predecir_categoria(texto):
    """Clasifica un texto y devuelve un diccionario con el detalle.

    Retorna:
      categoria         -> la mas probable o "sin_clasificar"
      confianza         -> puntaje de la ganadora / suma de puntajes (0 a 1)
      puntajes          -> puntaje de cada categoria (para auditar)
      terminos          -> que terminos hicieron match en cada categoria
      revision_humana   -> True si el resultado no es confiable
      motivo_revision   -> por que se pide revision
      alertas           -> terminos sensibles detectados
    """
    dic = cargar_diccionario()
    lemas = _lemas(texto)
    w_pal, w_exp = dic["pesos"]["palabra_clave"], dic["pesos"]["expresion"]

    puntajes = defaultdict(float)
    terminos = defaultdict(list)

    for cat, info in dic["categorias"].items():
        usados = set()
        # 1) primero expresiones (son mas especificas)
        for secuencia, original in info["expresiones"].items():
            for pos in _buscar_secuencia(lemas, secuencia, usados):
                usados.update(pos)
                puntajes[cat] += w_exp
                terminos[cat].append(original)
        # 2) luego palabras sueltas que no hayan quedado dentro de una expresion
        for i, lema in enumerate(lemas):
            if i not in usados and lema in info["palabras"]:
                puntajes[cat] += w_pal
                terminos[cat].append(info["palabras"][lema])

    ranking = sorted(puntajes.items(), key=lambda x: x[1], reverse=True)
    total = sum(puntajes.values())

    resultado = {
        "categoria": "sin_clasificar",
        "confianza": 0.0,
        "puntajes": dict(ranking),
        "terminos": {k: sorted(set(v)) for k, v in terminos.items()},
        "revision_humana": True,
        "motivo_revision": "No se encontraron terminos del diccionario.",
        "alertas": detectar_alertas(lemas, dic),
        "version_diccionario": dic["version"],
    }
    if not ranking:
        return resultado

    mejor, p1 = ranking[0]
    p2 = ranking[1][1] if len(ranking) > 1 else 0.0
    resultado["confianza"] = round(p1 / total, 2)

    if p1 < dic["umbral"]:
        resultado["motivo_revision"] = f"Puntaje bajo ({p1}); muy poca evidencia en el texto."
        return resultado

    resultado["categoria"] = mejor
    if p2 >= 0.8 * p1:
        resultado["motivo_revision"] = (f"Empate tecnico con '{ranking[1][0]}' "
                                        f"({p1} vs {p2}); puede ser un caso mixto.")
    else:
        resultado["revision_humana"] = False
        resultado["motivo_revision"] = ""
    return resultado


def evaluar_corpus(ruta=RUTA_CORPUS, campo="texto"):
    """Mide que tan bien funciona el diccionario sobre un conjunto etiquetado.

    OJO: con el corpus original el resultado es optimista, porque el
    diccionario se construyo mirando esos mismos textos. Por eso tambien se
    evalua con preguntas_prueba.csv: 10 preguntas escritas como las
    haria un usuario real, que NO se usaron para armar el diccionario.
    """
    with open(ruta, encoding="utf-8") as f:
        filas = list(csv.DictReader(f))

    aciertos, revision = 0, 0
    por_categoria = defaultdict(lambda: [0, 0])
    errores = []
    for fila in filas:
        r = predecir_categoria(fila[campo])
        esperado = fila["categoria_esperada"]
        por_categoria[esperado][1] += 1
        if r["revision_humana"]:
            revision += 1
        if r["categoria"] == esperado:
            aciertos += 1
            por_categoria[esperado][0] += 1
        else:
            errores.append((fila["id"], esperado, r["categoria"], r["puntajes"]))

    n = len(filas)
    print(f"Fragmentos evaluados: {n}")
    print(f"Exactitud (accuracy): {aciertos}/{n} = {aciertos / n:.1%}")
    print(f"Marcados para revision humana: {revision}")
    print("\nPor categoria:")
    for cat, (ok, tot) in sorted(por_categoria.items()):
        print(f"  {cat:<20} {ok}/{tot}")
    print("\nErrores:")
    for e in errores:
        print("  ", e[0], "esperado:", e[1], "-> predijo:", e[2], dict(e[3]))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        texto = " ".join(sys.argv[1:])
        print(json.dumps(predecir_categoria(texto), ensure_ascii=False, indent=2))
    else:
        print("=== 1) Corpus original (mismos textos usados para el diccionario) ===")
        evaluar_corpus()
        print("\n=== 2) Preguntas de prueba en lenguaje coloquial (no vistas) ===")
        evaluar_corpus(RUTA_PRUEBA, "pregunta")
