"""
test_indexado_rbac_postgres.py · Las MISMAS dos promesas, contra Postgres real
==============================================================================
`test_indexado_rbac_sql.py` prueba la lógica PURA y lo dice en su cabecera: que
el id sea estable y que el filtro tenga la forma correcta. Pero las dos
afirmaciones que de verdad importan son sobre POSTGRES, no sobre Python:

  1) "reindexar ACTUALIZA en vez de insertar"  → es una promesa del UPSERT.
  2) "lo restringido NO SALE de la base"       → es una promesa del WHERE.

Un id estable no sirve de nada si `add_documents` lo ignora, y un dict con `$in`
perfecto no protege nada si nadie se lo pasa al retriever. Ese hueco es el que
cierra este archivo, y por eso cuesta un Postgres levantado.

CÓMO CORRERLO:
    PYTEST_PG_DSN=postgresql://gobdata:gobdata@localhost:5440/gobdata \\
        uv run pytest proyecto_llmops/tests/test_indexado_rbac_postgres.py

Sin `PYTEST_PG_DSN` los tests se SALTAN (no pasan: se saltan), igual que
`TestPostgres` en test_metrics_backends.py. La CI offline sigue verde y estos
tests siguen siendo honestos sobre lo que NO han verificado.

⭐ LOS EMBEDDINGS SON UN DOBLE, Y ES DELIBERADO. No es por ahorrar los 220 MB del
   modelo real (que también): es que aquí se prueba el ALMACÉN, no la calidad
   semántica. Con vectores deterministas el test controla QUIÉN es el vecino más
   cercano, y puede por tanto colocar el fragmento restringido en el puesto nº1
   — que es justo el caso en el que un RBAC roto se nota.
"""
import os
import uuid

import psycopg
import pytest

pytestmark = pytest.mark.offline

PG_DSN = os.environ.get("PYTEST_PG_DSN")

# El corpus mínimo que hace falta para demostrar las dos cosas: un fragmento de
# cada nivel. Las marcas ("[público]", "confidencial", "HSM") son las que lee
# `rag.clasificar_confidencialidad`; si se tocan, cambia la etiqueta y el test
# deja de probar lo que dice probar.
CORPUS = """[público] Regla 1 — Cifrado en reposo: los datos de clientes se cifran con AES-256.

Regla 4 — Control de acceso: todo acceso a datos queda registrado en el log de auditoría.

Anexo confidencial: la clave maestra se custodia en el HSM del centro de datos de Lima.
"""

# Lo que la heurística debe sacar del corpus de arriba. Se afirma en un test
# aparte: si la clasificación cambiara sin avisar, los demás tests seguirían en
# verde probando otra cosa.
NIVELES_ESPERADOS = {"public", "internal", "restricted"}

# La pregunta apunta A PROPÓSITO al fragmento restringido: se parece más al
# anexo del HSM que a las dos reglas. Un RBAC que no filtra se delata aquí.
PREGUNTA_SENSIBLE = "¿dónde se custodia la clave maestra del HSM?"


class EmbeddingsDeterministas:
    """Bolsa de palabras normalizada. Sin red, sin modelo, sin sorpresas.

    Cumple la interfaz Embeddings de LangChain (`embed_documents` + `embed_query`)
    porque es lo único que PGVector le pide. La dimensión es fija, que es la otra
    condición: pgvector guarda la columna con un tamaño y no admite mezclas.

    El `1.0` final es un término constante y no un adorno: garantiza que ningún
    vector sea el vector nulo. La distancia coseno divide por la norma, y un cero
    ahí produce NaN — el fragmento quedaría fuera de todo ranking y el test
    fallaría por una razón que no tiene nada que ver con lo que prueba.
    """

    VOCABULARIO = ("cifrado", "clave", "hsm", "acceso", "auditor",
                   "publico", "maestra", "dato")

    def embed_query(self, texto: str) -> list[float]:
        minuscula = texto.lower()
        crudo = [float(minuscula.count(p)) for p in self.VOCABULARIO] + [1.0]
        norma = sum(x * x for x in crudo) ** 0.5
        return [x / norma for x in crudo]

    def embed_documents(self, textos: list[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in textos]


@pytest.fixture
def corpus(tmp_path):
    """El corpus en un archivo temporal.

    `leer_normativa(ruta=...)` existe justo para esto: el test decide qué se
    indexa, en vez de heredar la normativa real del proyecto (que crece y
    cambiaría los conteos sin que nadie tocara un test).
    """
    ruta = tmp_path / "normativa_de_prueba.txt"
    ruta.write_text(CORPUS, encoding="utf-8")
    return ruta


@pytest.fixture
def coleccion(monkeypatch):
    """Una colección con nombre único, y su limpieza garantizada.

    Único porque dos corridas simultáneas (o una anterior que petó a la mitad)
    compartirían filas y los conteos mentirían. Y se borra en el teardown: la
    misma disciplina que `TestPostgres.backend`, que llama a `limpiar()` antes y
    después de cada test.
    """
    import app.rag as rag
    from app.config import settings

    # langchain-postgres va por SQLAlchemy, que elige driver según el esquema:
    # hay que nombrarle psycopg (la v3) explícitamente. Ver `pg_dsn_sqlalchemy`.
    dsn_sqlalchemy = PG_DSN.replace("postgresql://", "postgresql+psycopg://", 1)
    monkeypatch.setattr(type(settings), "pg_dsn_sqlalchemy",
                        property(lambda self: dsn_sqlalchemy))
    # El doble de embeddings entra por el mismo sitio por el que entraría el
    # real: el nombre que `construir_retriever_pgvector` resuelve en su módulo.
    monkeypatch.setattr(rag, "crear_embeddings", lambda: EmbeddingsDeterministas())

    nombre = f"test_normativa_{uuid.uuid4().hex[:12]}"
    yield nombre

    from langchain_postgres import PGVector
    PGVector(embeddings=EmbeddingsDeterministas(), connection=dsn_sqlalchemy,
             collection_name=nombre, use_jsonb=True).delete_collection()


def filas_indexadas(nombre_coleccion: str) -> list[str]:
    """Los ids realmente guardados en pgvector para esa colección.

    Se consulta con psycopg a pelo, y no a través del vector store, a propósito:
    preguntarle a la misma capa que escribió si escribió bien es hacer trampa.
    """
    with psycopg.connect(PG_DSN) as conexion:
        with conexion.cursor() as cur:
            cur.execute(
                "SELECT e.id FROM langchain_pg_embedding e "
                "JOIN langchain_pg_collection c ON c.uuid = e.collection_id "
                "WHERE c.name = %s", (nombre_coleccion,))
            return [f[0] for f in cur.fetchall()]


@pytest.mark.skipif(not PG_DSN, reason="sin PYTEST_PG_DSN: no hay Postgres al que conectarse")
class TestIndexadoIdempotenteEnPostgres:
    """La promesa del upsert: indexar dos veces no deja dos copias."""

    def test_el_corpus_de_prueba_cubre_los_tres_niveles(self, corpus):
        # Guardia del resto del archivo. Los tests de abajo dan por hecho que hay
        # material restringido que ocultar; si la heurística dejara de marcarlo,
        # el test del RBAC pasaría sin haber filtrado nada.
        from app.rag import leer_normativa, trocear_con_metadata

        fragmentos = trocear_con_metadata(leer_normativa(corpus))
        assert len(fragmentos) == 3
        assert {f.metadata["confidentiality"] for f in fragmentos} == NIVELES_ESPERADOS

    def test_reindexar_el_mismo_corpus_no_duplica_filas(self, corpus, coleccion):
        """⭐ EL TEST QUE FALTABA. Antes esto se afirmaba, no se comprobaba.

        Con `ids=None`, cada arranque del servicio INSERTABA otra copia de la
        normativa entera: el retriever devolvía el mismo párrafo tres veces y el
        contexto del prompt se llenaba de repeticiones. Contar filas es la única
        forma de saber que el upsert hace upsert.
        """
        from app.rag import construir_retriever_pgvector

        construir_retriever_pgvector(ruta=corpus, tabla=coleccion, k=3)
        assert len(filas_indexadas(coleccion)) == 3

        construir_retriever_pgvector(ruta=corpus, tabla=coleccion, k=3)
        assert len(filas_indexadas(coleccion)) == 3, (
            "la segunda indexación insertó filas nuevas en vez de actualizar las "
            "existentes: el upsert por id no está funcionando")

    def test_la_segunda_pasada_escribe_sobre_las_MISMAS_filas(self, corpus, coleccion):
        # Que el conteo no suba podría lograrse también borrando y reinsertando.
        # Esto afirma lo que de verdad se prometió: los ids son los mismos, así
        # que las filas son las mismas y lo ya vectorizado se reutiliza.
        from app.rag import construir_retriever_pgvector

        construir_retriever_pgvector(ruta=corpus, tabla=coleccion, k=3)
        primera = set(filas_indexadas(coleccion))

        construir_retriever_pgvector(ruta=corpus, tabla=coleccion, k=3)
        assert set(filas_indexadas(coleccion)) == primera

    def test_los_ids_guardados_son_los_de_id_de_fragmento(self, corpus, coleccion):
        # El puente entre el test de lógica pura y este: lo que hay en la columna
        # `id` de pgvector es EXACTAMENTE lo que devuelve la función pura. Si
        # alguien dejara de pasar `ids=`, langchain generaría uuid4 y esto se cae.
        from app.rag import (construir_retriever_pgvector, id_de_fragmento,
                             leer_normativa, trocear_con_metadata)

        construir_retriever_pgvector(ruta=corpus, tabla=coleccion, k=3)
        esperados = {id_de_fragmento(f)
                     for f in trocear_con_metadata(leer_normativa(corpus))}
        assert set(filas_indexadas(coleccion)) == esperados


@pytest.mark.skipif(not PG_DSN, reason="sin PYTEST_PG_DSN: no hay Postgres al que conectarse")
class TestRbacEmpujadoAlWhereDePgvector:
    """La promesa del WHERE: lo restringido no sale de la base de datos."""

    def _retriever(self, corpus, coleccion, rol):
        # k=10 sobre un corpus de 3: sin filtro caben TODOS. Así, si algo falta
        # del resultado, es porque el WHERE lo dejó fuera — no porque el ranking
        # se quedara sin huecos.
        from app.rag import construir_retriever_pgvector
        return construir_retriever_pgvector(ruta=corpus, tabla=coleccion,
                                            k=10, rol=rol)

    def test_el_fragmento_restringido_es_el_vecino_mas_cercano(self, corpus, coleccion):
        """⭐ LA GUARDIA QUE HACE HONESTO AL TEST SIGUIENTE.

        Si el anexo del HSM no fuera el resultado más parecido a la pregunta, que
        un 'analyst' no lo reciba no probaría nada: podría estar quedándose fuera
        por poco relevante. Aquí se comprueba con un rol que SÍ puede verlo que
        el fragmento está indexado y que encabeza el ranking. Solo entonces
        significa algo que desaparezca para otro rol.
        """
        docs = self._retriever(corpus, coleccion, "compliance").invoke(PREGUNTA_SENSIBLE)

        assert docs[0].metadata["confidentiality"] == "restricted"
        assert "HSM" in docs[0].page_content

    def test_un_analyst_NO_recibe_fragmentos_restringidos(self, corpus, coleccion):
        """⭐ EL TEST QUE FALTABA. La afirmación central del ADR, comprobada.

        Ojo a lo que se invoca: `retriever.invoke`, NO `rag.recuperar`. Y es toda
        la diferencia. `recuperar` pasa después por `filtrar_por_rol`, que en
        Python quitaría el fragmento igualmente — el test pasaría con el WHERE
        completamente roto, que es exactamente el fallo que se quiere detectar.
        Preguntándole al retriever a secas, lo que se lee es lo que POSTGRES
        decidió devolver.
        """
        docs = self._retriever(corpus, coleccion, "analyst").invoke(PREGUNTA_SENSIBLE)

        niveles = [d.metadata["confidentiality"] for d in docs]
        assert "restricted" not in niveles, (
            f"Postgres devolvió material restringido a un 'analyst': {niveles}. "
            "El filtro de rbac.filtro_sql no llegó al WHERE de la consulta")

    def test_el_analyst_sigue_recibiendo_lo_que_SÍ_puede_ver(self, corpus, coleccion):
        # La otra mitad, y no es menos importante: un filtro que no devuelve nada
        # también "protege" y además rompe el producto. Ya pasó una vez con la
        # heurística de clasificación (ver el comentario en app/rag.py).
        docs = self._retriever(corpus, coleccion, "analyst").invoke(PREGUNTA_SENSIBLE)

        assert {d.metadata["confidentiality"] for d in docs} == {"public", "internal"}

    def test_compliance_ve_el_corpus_entero(self, corpus, coleccion):
        docs = self._retriever(corpus, coleccion, "compliance").invoke(PREGUNTA_SENSIBLE)

        assert {d.metadata["confidentiality"] for d in docs} == NIVELES_ESPERADOS

    def test_sin_rol_no_se_filtra_nada_en_la_base(self, corpus, coleccion):
        # `rol=None` es el default y significa "no empujes nada al WHERE": el
        # retriever genérico lo trae todo y quien lo use filtrará en Python.
        # Documentarlo con un test evita que alguien lo tome por un fallo del
        # RBAC — y deja constancia de que ESE camino sí saca de la base material
        # restringido, que es justo el motivo por el que existe `filtro_sql`.
        docs = self._retriever(corpus, coleccion, None).invoke(PREGUNTA_SENSIBLE)

        assert {d.metadata["confidentiality"] for d in docs} == NIVELES_ESPERADOS
