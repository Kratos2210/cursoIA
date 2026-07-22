# Guion · Ruta 1 — Fundamentos (5–6 min)

**Se publica en:** c00 · **Demo:** primer modelo respondiendo en terminal

## Gancho (0:00–0:30)

> Todos los cursos de IA te prometen agentes. Casi ninguno te cuenta que el 80%
> de los que abandonan, abandonan ANTES del primer `print`: instalando Python,
> peleando con la terminal, sin saber qué es una API key. Esta ruta existe para
> que tú no seas de esos. En seis minutos te muestro el plan — y un modelo de
> lenguaje respondiéndote desde TU terminal.

## Qué vas a poder hacer al terminar la ruta (0:30–1:15)

- Correr cualquier ejemplo del curso con `uv run python archivo.py`, entendiendo qué hace cada línea.
- Hablar con un modelo desde Python — con TU llave gratis, sin pagar nada.
- Leer un error (traceback) sin pánico y saber a qué línea ir.

## Demo (1:15–4:00)

En pantalla, desde cero real (terminal limpia):

```bash
# 1. instalar uv (una línea, la del c00)
curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. traerse el curso
git clone https://github.com/Kratos2210/cursoIA.git
cd cursoIA/curso_ejemplos
# 3. la llave gratis de aistudio.google.com (mostrar la página, tapar la llave)
cp .env.example .env        # abrir en el editor y pegar la llave
# 4. instalar y COMPROBAR que todo quedó bien
uv sync
uv run python env_utils.py  # ✔ Entorno listo.
# 5. el primer modelo (pegar el código del c01 en mi_01.py)
uv run python mi_01.py
```

Puntos de guion durante la demo:
- En el `env_utils.py`: enseñar la lista de ✔ y decir «esto es lo que quiero que
  veas ANTES de escribir una línea de código: si algo falta, te lo dice con el
  arreglo debajo, en vez de reventar a mitad del primer ejemplo».
- Cuando aparezca la respuesta del modelo: pausa de 2 segundos. «Eso que acaba
  de pasar es TODO el curso en miniatura: texto entra, texto sale. Lo demás es
  ingeniería alrededor.»
- Mostrar el `429` real si sale (o simularlo): «esto no es un error tuyo, es la
  cuota gratis — el curso entero está diseñado para sobrevivirlo, hay 7
  ejemplos que corren sin gastar nada.»

## Recorrido de la ruta (4:00–5:00)

- **c00** prepara tu máquina (lo que acabas de ver, paso a paso y con troubleshooting).
- **c0b** el Python mínimo — solo lo que el curso usa, nada más.
- **c01** tu primer modelo, línea por línea.
- **c03** invoke / batch / stream: las tres formas de llamar a cualquier modelo.

## Cierre (5:00–5:30)

> Si sabes abrir una terminal, puedes con esto. Y si no sabes, el c00 también
> te enseña eso. Empieza ahí — el enlace está abajo. Nos vemos dentro.

**CTA:** `/concepto/00-preparar-el-terreno`
