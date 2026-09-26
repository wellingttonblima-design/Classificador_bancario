from datetime import datetime
import sqlite3
from flask import Flask, render_template_string, request
import pandas as pd
import spacy

# Nome do arquivo de banco de dados unificado
DB_NAME = "banco.db"

# ------------------------------------------------------------------------------
# 1. MODEL & NLP (Processamento de Linguagem Natural com spaCy e SQLite)
# ------------------------------------------------------------------------------

nlp = spacy.load("pt_core_news_sm")


def init_db():
    """Inicializa a tabela de histórico no banco de dados SQLite."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Cria a tabela logs com as colunas texto, intencao e data_hora
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            texto TEXT NOT NULL,
            intencao TEXT NOT NULL,
            data_hora TEXT NOT NULL
        )
    """
    )
    conn.commit()
    conn.close()


def classificar_texto(texto):
    """Classifica a intenção e salva com a data e hora atual no SQLite."""
    doc = nlp(texto.lower())
    lemmas = [token.lemma_ for token in doc]

    # Regras de correspondência por palavras-chave/lemas
    if any(
        p in lemmas for p in ["bloquear", "bloqueio", "perda", "roubo", "cartao"]
    ):
        intencao = "bloquear_cartao"
    elif any(
        p in lemmas
        for p in ["boleto", "segunda", "via", "pagamento", "fatura", "codigo"]
    ):
        intencao = "segunda_via_boleto"
    else:
        intencao = "desconhecido"

    # Captura a data e hora atual no formato brasileiro
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # Salva no banco de dados usando a constante DB_NAME
    conn = sqlite3.connect(DB_NAME)
    df = pd.DataFrame(
        [{"texto": texto, "intencao": intencao, "data_hora": agora}]
    )
    df.to_sql("logs", conn, if_exists="append", index=False)
    conn.close()

    return intencao


def obter_historico():
    """Recupera os últimos 10 registros salvos no SQLite."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM logs ORDER BY id DESC LIMIT 10", conn)
    conn.close()
    return df.to_dict(orient="records")


# ------------------------------------------------------------------------------
# 2. VIEW (Template HTML e Estilos CSS Embutidos)
# ------------------------------------------------------------------------------

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Classificador NLP - Banco Digital</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f6f9; padding: 20px; }
        .container { max-width: 700px; margin: auto; background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        textarea { width: 100%; height: 80px; padding: 10px; margin-bottom: 10px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
        button { width: 100%; padding: 10px; background-color: #0066cc; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
        button:hover { background-color: #0052a3; }
        .result-box { margin-top: 15px; padding: 12px; border-radius: 4px; background: #e8f4fd; border-left: 4px solid #0066cc; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 14px; }
        .badge { padding: 3px 8px; border-radius: 12px; font-size: 12px; color: white; background: #888; font-weight: bold; }
        .badge.bloquear_cartao { background: #d9534f; }
        .badge.segunda_via_boleto { background: #5cb85c; }
        .badge.desconhecido { background: #f0ad4e; }
        .timestamp { font-size: 12px; color: #666; white-space: nowrap; }
    </style>
</head>
<body>
    <div class="container">
        2. Classificador de Solicitações</h2>
        <form method="POST">
            <textarea name="texto" placeholder="Digite sua solicitação... ex: 'Perdi meu cartão e preciso bloquear'" required>{{ texto }}</textarea>
            <button type="submit">Classificar Solicitação</button>
        </form>

        {% if resultado %}
        <div class="result-box">
            <strong>Intenção Identificada:</strong> 
            <span class="badge {{ resultado }}">{{ resultado }}</span>
        </div>
        {% endif %}

        <h3>Histórico Recente (SQLite)</h3>
        <table>
            <tr>
                <th>Data / Hora</th>
                <th>Texto</th>
                <th>Intenção</th>
            </tr>
            {% for item in historico %}
            <tr>
                <td class="timestamp">{{ item.data_hora }}</td>
                <td>{{ item.texto }}</td>
                <td><span class="badge {{ item.intencao }}">{{ item.intencao }}</span></td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

# ------------------------------------------------------------------------------
# 3. CONTROLLER & APLICAÇÃO FLASK
# ------------------------------------------------------------------------------

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    resultado = None
    texto_digitado = ""

    if request.method == "POST":
        texto_digitado = request.form.get("texto", "")
        if texto_digitado:
            resultado = classificar_texto(texto_digitado)

    historico = obter_historico()
    return render_template_string(
        HTML_TEMPLATE,
        resultado=resultado,
        texto=texto_digitado,
        historico=historico,
    )


# Inicializa o banco ao carregar o servidor
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)