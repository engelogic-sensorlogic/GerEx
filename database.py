"""
GerEx - Módulo de banco de dados SQLite
"""
import sqlite3
import os
import sys
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent

if getattr(sys, "frozen", False):
    # Rodando como executavel compilado (PyInstaller): a pasta de instalacao
    # (ex.: C:\Program Files (x86)\GerEx) costuma ser somente leitura
    # para usuarios sem privilegio de administrador, entao os dados do
    # aplicativo (banco SQLite) ficam numa pasta gravavel do usuario.
    _DATA_ROOT = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "GerEx"
else:
    _DATA_ROOT = BASE_DIR

DB_PATH = _DATA_ROOT / "data" / "gerex.db"

# ---------------------------------------------------------------------------
# Dados padrão do checklist (10 itens – Área Classificada, poeiras combustíveis)
# ---------------------------------------------------------------------------
_OBS_OK = "Nenhuma ação necessária, a instalação atende ao requisito da norma."
_OBS_NA = "Item não verificado nesta inspeção ou não aplicável a esta área."

# Valores sugeridos no cadastro da área (os campos continuam editáveis).
# As colunas do banco mantem os nomes herdados do GerLauNR10:
#   tipo_painel = zona, tensao_forca = material/poeira,
#   tensao_comando = grupo da poeira, num_fases = estudo de classificacao
ZONAS = ["Zona 21", "Zona 22", "Zonas 21 e 22"]
GRUPOS_POEIRA = [
    "IIIB - Poeira não condutiva",
    "IIIA - Fibras combustíveis",
    "IIIC - Poeira condutiva",
    "Não informado",
]

_NBR_14 = "ABNT NBR IEC 60079-14 – Projeto, seleção e montagem de instalações elétricas em atmosferas explosivas."
_NBR_17 = "ABNT NBR IEC 60079-17 – Inspeção e manutenção de instalações elétricas em atmosferas explosivas."
_NBR_31 = "ABNT NBR IEC 60079-31 – Proteção de equipamentos contra ignição de poeira por invólucro \"t\"."
_NR10_92 = ("NR-10, item 10.9.2 – Os materiais, peças, dispositivos, equipamentos e sistemas destinados à "
            "aplicação em instalações elétricas de ambientes com atmosferas potencialmente explosivas devem "
            "ser avaliados quanto à sua conformidade, no âmbito do Sistema Brasileiro de Certificação.")


def _opcoes(obs_falha, ac_nao, ac_parcial):
    """As quatro respostas do checklist: Sim, Não, Atende Parcial e Não avaliado."""
    return [
        ("Sim", 1.0, _OBS_OK, ""),
        ("Não", 0.0, obs_falha, ac_nao),
        ("Atende Parcial", 0.5, obs_falha, ac_parcial),
        ("Não avaliado", None, _OBS_NA, ""),
    ]


CHECKLIST_DEFAULT = [
    {
        "numero": 1,
        "questao": "Todos os equipamentos instalados (conduletes, luminárias e caixas) possuem plaqueta legível com selo Inmetro e marcação Ex para poeira (ex.: Ex tb IIIC Db)?",
        "justificativa": _NR10_92 + "\nPortaria Inmetro nº 115/2022 – Requisitos de avaliação da conformidade para equipamentos elétricos para atmosferas explosivas.\nABNT NBR IEC 60079-0 – Requisitos gerais e marcação dos equipamentos.",
        "opcoes": _opcoes(
            "Equipamentos instalados em área classificada devem possuir certificação Inmetro e marcação Ex compatível com atmosfera de poeira combustível, permitindo verificar o tipo de proteção, o grupo de poeira e o nível de proteção (EPL).",
            "Substituir os equipamentos sem certificação ou sem marcação Ex para poeira por equipamentos certificados (proteção por invólucro \"t\", grupo III, EPL Db para Zona 21 ou Dc/Db para Zona 22) e arquivar os certificados no dossiê da instalação.",
            "Identificar os equipamentos com plaqueta ilegível, danificada ou ausente e providenciar a recomposição da identificação junto ao fabricante ou a substituição do equipamento. Conferir se a marcação dos conduletes à prova de explosão inclui proteção para poeira (Ex tb), e não apenas para gases (Ex d)."),
    },
    {
        "numero": 2,
        "questao": "Não restou na área nenhum material comum (não Ex), como tomadas, interruptores, caixas de passagem, luminárias ou trechos de eletrocalha?",
        "justificativa": _NR10_92 + "\n" + _NBR_14,
        "opcoes": _opcoes(
            "Qualquer material elétrico comum remanescente na área classificada constitui fonte potencial de ignição e invalida a conformidade do conjunto da instalação.",
            "Remover ou substituir todos os materiais e equipamentos elétricos comuns remanescentes na área por equipamentos certificados para Zona 21/22, ou relocá-los para fora dos limites da área classificada.",
            "Concluir a substituição dos materiais comuns ainda existentes, identificados nas fotos deste item, por equipamentos certificados Ex, ou relocá-los para fora da área classificada."),
    },
    {
        "numero": 3,
        "questao": "Os cabos estão integralmente protegidos por eletroduto pesado, sem trechos expostos e sem emendas fora de invólucros?",
        "justificativa": _NBR_14 + "\nOs sistemas de fiação em áreas com poeira combustível devem impedir o acúmulo de poeira e proteger os condutores contra danos mecânicos; emendas e derivações devem ficar contidas em invólucros adequados à zona.",
        "opcoes": _opcoes(
            "Cabos expostos ou emendas fora de invólucros permitem o contato da poeira com partes energizadas e ficam sujeitos a danos mecânicos, criando risco de faísca e aquecimento.",
            "Providenciar a proteção integral dos cabos por eletroduto metálico pesado e a transferência de todas as emendas e derivações para conduletes ou caixas certificadas Ex.",
            "Completar a proteção dos trechos de cabo ainda expostos e transferir as emendas remanescentes para invólucros certificados Ex."),
    },
    {
        "numero": 4,
        "questao": "Os eletrodutos e conexões estão corretamente montados (rosca com no mínimo 5 fios engajados, luvas e uniões apertadas, fixação firme, sem amassados ou corrosão)?",
        "justificativa": _NBR_14 + "\n" + _NBR_17 + "\nAs juntas roscadas devem garantir a integridade e a vedação do sistema de eletrodutos, mantendo a continuidade elétrica e impedindo a entrada de poeira.",
        "opcoes": _opcoes(
            "Conexões frouxas, roscas com engajamento insuficiente, deformações ou corrosão comprometem a vedação contra poeira e a continuidade elétrica do sistema de eletrodutos.",
            "Refazer as conexões roscadas com engajamento mínimo de 5 fios, apertar luvas e uniões, substituir trechos amassados ou corroídos e completar a fixação dos eletrodutos com suportes adequados.",
            "Corrigir os pontos de montagem indicados nas fotos deste item (roscas, uniões, fixação ou trechos danificados)."),
    },
    {
        "numero": 5,
        "questao": "Os conduletes e caixas estão completos e fechados (tampas apertadas, todos os parafusos no lugar, vedações íntegras e nenhum furo aberto)?",
        "justificativa": _NBR_31 + "\n" + _NBR_17 + "\nA proteção por invólucro depende da integridade do conjunto: tampas, parafusos, juntas de vedação e entradas fechadas mantêm o grau de proteção IP6X.",
        "opcoes": _opcoes(
            "Tampas soltas, parafusos faltantes, vedações danificadas ou furos abertos anulam o grau de proteção do invólucro e permitem a entrada de poeira combustível.",
            "Recompor todos os invólucros: instalar os parafusos faltantes com o torque indicado pelo fabricante, substituir as juntas de vedação danificadas e fechar os furos abertos com bujões certificados Ex.",
            "Recompor os invólucros indicados nas fotos deste item (parafusos, tampas, vedações ou furos)."),
    },
    {
        "numero": 6,
        "questao": "As entradas dos invólucros utilizam prensa-cabos, adaptadores e bujões certificados Ex, e as entradas não utilizadas estão fechadas com bujão Ex?",
        "justificativa": _NBR_14 + "\n" + _NBR_31 + "\nOs dispositivos de entrada de cabos e os elementos de fechamento devem ser certificados e manter o tipo de proteção e o grau de proteção do invólucro.",
        "opcoes": _opcoes(
            "Entradas sem dispositivos certificados ou sem fechamento adequado comprometem a proteção do invólucro, mesmo quando o equipamento em si é certificado.",
            "Substituir os prensa-cabos, adaptadores e bujões não certificados por componentes certificados Ex compatíveis com a rosca e o tipo de proteção do invólucro, e fechar todas as entradas não utilizadas com bujão Ex.",
            "Substituir os componentes de entrada não certificados identificados nas fotos deste item e fechar as entradas não utilizadas remanescentes com bujão Ex."),
    },
    {
        "numero": 7,
        "questao": "Há unidades seladoras nos pontos exigidos (passagem entre zonas e saída para área não classificada), preenchidas com massa seladora?",
        "justificativa": _NBR_14 + "\nO sistema de eletrodutos deve impedir a migração de poeira e de atmosfera explosiva entre zonas e para áreas não classificadas, por meio de unidades seladoras devidamente preenchidas.",
        "opcoes": _opcoes(
            "A ausência de selagem nas fronteiras da área classificada permite que a poeira migre pelo interior dos eletrodutos para outras zonas ou para a área não classificada.",
            "Instalar unidades seladoras certificadas nos pontos de passagem entre zonas e de saída para a área não classificada, preenchendo-as com fibra e massa seladora conforme instruções do fabricante.",
            "Completar a instalação ou o preenchimento das unidades seladoras nos pontos indicados nas fotos deste item."),
    },
    {
        "numero": 8,
        "questao": "As luminárias Ex estão bem fixadas, sem danos no vidro ou difusor, com vedações íntegras e sem acúmulo de poeira?",
        "justificativa": _NBR_17 + "\n" + _NBR_31 + "\nO acúmulo de camada de poeira sobre os equipamentos eleva sua temperatura de superfície e reduz a margem de segurança em relação à temperatura de ignição da poeira.",
        "opcoes": _opcoes(
            "Luminárias com vidro danificado, vedação comprometida, fixação deficiente ou camada de poeira acumulada perdem a proteção contra ignição e podem atingir temperaturas acima do limite seguro.",
            "Substituir os vidros, difusores ou vedações danificados por peças originais do fabricante, refazer a fixação das luminárias e implantar rotina de limpeza para evitar acúmulo de poeira.",
            "Corrigir as luminárias indicadas nas fotos deste item e implantar rotina de limpeza periódica da área."),
    },
    {
        "numero": 9,
        "questao": "Eletrodutos, conduletes, luminárias e estruturas metálicas estão ligados ao sistema de aterramento, com condutores e terminais visíveis e firmes?",
        "justificativa": "NR-10, item 10.9.3 – Os processos ou equipamentos susceptíveis de gerar ou acumular eletricidade estática devem dispor de proteção específica e dispositivos de descarga elétrica.\n" + _NBR_14 + "\nABNT NBR 5410 – Instalações elétricas de baixa tensão (aterramento e equipotencialização).",
        "opcoes": _opcoes(
            "Partes metálicas sem ligação ao aterramento podem acumular eletricidade estática ou ficar energizadas em caso de falha, gerando faíscas capazes de inflamar a poeira em suspensão.",
            "Providenciar a equipotencialização de eletrodutos, conduletes, luminárias e estruturas metálicas ao sistema de aterramento, com condutores identificados (verde ou verde-amarelo) e terminais apropriados, e registrar a medição de continuidade.",
            "Completar as ligações ao aterramento nos pontos indicados nas fotos deste item e reapertar os terminais soltos."),
    },
    {
        "numero": 10,
        "questao": "Há placas de sinalização da área classificada (Zona 21/22, risco de explosão por poeira) nos acessos ao setor?",
        "justificativa": "NR-10, item 10.10.1 – Nas instalações e serviços em eletricidade deve ser adotada sinalização adequada de segurança, destinada à advertência e à identificação, obedecendo ao disposto na NR-26, incluindo restrições e impedimentos de acesso e delimitações de áreas.\nNR-26 – Sinalização de Segurança.",
        "opcoes": _opcoes(
            "Os acessos à área classificada devem informar a todos a zona e o risco de explosão por poeira, para que sejam observadas as restrições de uso de equipamentos, ferramentas e fontes de ignição.",
            "Providenciar placas de sinalização em todos os acessos ao setor, indicando a área classificada, a zona (21/22), o risco de explosão por poeira combustível e as restrições aplicáveis.",
            "Completar a sinalização nos acessos ainda sem placa ou substituir as placas ilegíveis ou danificadas."),
    },
]


# ---------------------------------------------------------------------------
# Inicialização
# ---------------------------------------------------------------------------
def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Cria todas as tabelas e popula checklist padrão se necessário."""
    conn = get_connection()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            razao_social TEXT NOT NULL,
            cnpj TEXT,
            filial TEXT,
            endereco TEXT,
            cep TEXT,
            cidade TEXT,
            estado TEXT,
            telefone TEXT,
            logo_path TEXT,
            criado_em TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS participantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
            nome TEXT NOT NULL,
            empresa TEXT,
            cargo TEXT,
            setor TEXT,
            email TEXT,
            telefone TEXT
        );

        CREATE TABLE IF NOT EXISTS profissionais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            empresa TEXT,
            habilitacao TEXT,
            crea TEXT,
            email TEXT,
            telefone TEXT
        );

        CREATE TABLE IF NOT EXISTS laudos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
            numero TEXT,
            titulo TEXT,
            periodo_inicio TEXT,
            periodo_fim TEXT,
            cidade_laudo TEXT,
            art_pdf_path TEXT,
            conclusoes TEXT,
            consideracoes TEXT,
            status TEXT DEFAULT 'Em andamento',
            criado_em TEXT DEFAULT (datetime('now')),
            atualizado_em TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS laudo_profissionais (
            laudo_id INTEGER NOT NULL REFERENCES laudos(id) ON DELETE CASCADE,
            profissional_id INTEGER NOT NULL REFERENCES profissionais(id) ON DELETE CASCADE,
            PRIMARY KEY (laudo_id, profissional_id)
        );

        CREATE TABLE IF NOT EXISTS laudo_participantes (
            laudo_id INTEGER NOT NULL REFERENCES laudos(id) ON DELETE CASCADE,
            participante_id INTEGER NOT NULL REFERENCES participantes(id) ON DELETE CASCADE,
            PRIMARY KEY (laudo_id, participante_id)
        );

        CREATE TABLE IF NOT EXISTS paineis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            laudo_id INTEGER NOT NULL REFERENCES laudos(id) ON DELETE CASCADE,
            formulario_num INTEGER,
            tag TEXT,
            setor TEXT,
            tipo_painel TEXT,
            tensao_forca TEXT,
            tensao_comando TEXT,
            num_fases TEXT,
            descricao TEXT,
            data_avaliacao TEXT,
            nivel_aderencia REAL DEFAULT 0.0,
            observacoes_gerais TEXT,
            foto_frontal TEXT,
            foto_lateral_dir TEXT,
            foto_lateral_esq TEXT,
            foto_traseira TEXT,
            criado_em TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS avaliacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            painel_id INTEGER NOT NULL REFERENCES paineis(id) ON DELETE CASCADE,
            item_numero INTEGER NOT NULL,
            opcao_id INTEGER REFERENCES checklist_opcoes(id),
            peso REAL,
            observacoes TEXT,
            acao_corretiva TEXT,
            UNIQUE(painel_id, item_numero)
        );

        CREATE TABLE IF NOT EXISTS fotos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            painel_id INTEGER NOT NULL REFERENCES paineis(id) ON DELETE CASCADE,
            item_numero INTEGER,
            caminho TEXT NOT NULL,
            legenda TEXT,
            criado_em TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS checklist_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero INTEGER NOT NULL UNIQUE,
            questao TEXT NOT NULL,
            justificativa TEXT,
            ativo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS checklist_opcoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL REFERENCES checklist_items(id) ON DELETE CASCADE,
            descricao TEXT NOT NULL,
            peso REAL,
            observacao_padrao TEXT,
            acao_corretiva_padrao TEXT
        );
    """)
    conn.commit()

    # Migration: adiciona colunas de fotos de identificacao se nao existirem
    for col, tipo in [
        ("foto_frontal", "TEXT"),
        ("foto_lateral_dir", "TEXT"),
        ("foto_lateral_esq", "TEXT"),
        ("foto_traseira", "TEXT"),
    ]:
        try:
            conn.execute("ALTER TABLE paineis ADD COLUMN %s %s" % (col, tipo))
            conn.commit()
        except Exception:
            pass  # coluna ja existe

    # Migration: adiciona colunas de textos padrao de observacao/acao corretiva
    # nas opcoes do checklist, se nao existirem
    for col in ("observacao_padrao", "acao_corretiva_padrao"):
        try:
            conn.execute("ALTER TABLE checklist_opcoes ADD COLUMN %s TEXT" % col)
            conn.commit()
        except Exception:
            pass  # coluna ja existe

    # Popula checklist padrão se vazio
    count = c.execute("SELECT COUNT(*) FROM checklist_items").fetchone()[0]
    if count == 0:
        for item in CHECKLIST_DEFAULT:
            c.execute(
                "INSERT INTO checklist_items (numero, questao, justificativa) VALUES (?,?,?)",
                (item["numero"], item["questao"], item["justificativa"])
            )
            item_id = c.lastrowid
            for desc, peso, obs_pad, ac_pad in item["opcoes"]:
                c.execute(
                    """INSERT INTO checklist_opcoes
                       (item_id, descricao, peso, observacao_padrao, acao_corretiva_padrao)
                       VALUES (?,?,?,?,?)""",
                    (item_id, desc, peso, obs_pad, ac_pad)
                )
        conn.commit()
    else:
        # Backfill: bancos criados antes da existencia dos textos padrao tem
        # as opcoes do checklist ja populadas, mas sem observacao_padrao/
        # acao_corretiva_padrao. Preenche apenas onde ainda estiver vazio,
        # sem sobrescrever eventual customizacao feita pelo usuario.
        for item in CHECKLIST_DEFAULT:
            row = c.execute(
                "SELECT id FROM checklist_items WHERE numero=?", (item["numero"],)
            ).fetchone()
            if not row:
                continue
            item_id = row["id"]
            for desc, peso, obs_pad, ac_pad in item["opcoes"]:
                c.execute(
                    """UPDATE checklist_opcoes
                       SET observacao_padrao=COALESCE(NULLIF(observacao_padrao, ''), ?),
                           acao_corretiva_padrao=COALESCE(NULLIF(acao_corretiva_padrao, ''), ?)
                       WHERE item_id=? AND descricao=?
                         AND (observacao_padrao IS NULL OR observacao_padrao=''
                              OR acao_corretiva_padrao IS NULL OR acao_corretiva_padrao='')""",
                    (obs_pad, ac_pad, item_id, desc)
                )
        conn.commit()

    conn.close()


# ---------------------------------------------------------------------------
# CLIENTES
# ---------------------------------------------------------------------------
def listar_clientes():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM clientes ORDER BY razao_social").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def salvar_cliente(dados: dict) -> int:
    conn = get_connection()
    c = conn.cursor()
    if dados.get("id"):
        c.execute("""UPDATE clientes SET razao_social=?, cnpj=?, filial=?, endereco=?,
                     cep=?, cidade=?, estado=?, telefone=?, logo_path=?
                     WHERE id=?""",
                  (dados["razao_social"], dados.get("cnpj"), dados.get("filial"),
                   dados.get("endereco"), dados.get("cep"), dados.get("cidade"),
                   dados.get("estado"), dados.get("telefone"), dados.get("logo_path"),
                   dados["id"]))
        cid = dados["id"]
    else:
        c.execute("""INSERT INTO clientes (razao_social, cnpj, filial, endereco,
                     cep, cidade, estado, telefone, logo_path) VALUES (?,?,?,?,?,?,?,?,?)""",
                  (dados["razao_social"], dados.get("cnpj"), dados.get("filial"),
                   dados.get("endereco"), dados.get("cep"), dados.get("cidade"),
                   dados.get("estado"), dados.get("telefone"), dados.get("logo_path")))
        cid = c.lastrowid
    conn.commit()
    conn.close()
    return cid


def excluir_cliente(cliente_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM clientes WHERE id=?", (cliente_id,))
    conn.commit()
    conn.close()


def buscar_cliente(cliente_id: int) -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM clientes WHERE id=?", (cliente_id,)).fetchone()
    conn.close()
    return dict(row) if row else {}


# ---------------------------------------------------------------------------
# PARTICIPANTES
# ---------------------------------------------------------------------------
def listar_participantes(cliente_id: int):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM participantes WHERE cliente_id=? ORDER BY nome",
                        (cliente_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def salvar_participante(dados: dict) -> int:
    conn = get_connection()
    c = conn.cursor()
    if dados.get("id"):
        c.execute("""UPDATE participantes SET nome=?, empresa=?, cargo=?, setor=?,
                     email=?, telefone=? WHERE id=?""",
                  (dados["nome"], dados.get("empresa"), dados.get("cargo"),
                   dados.get("setor"), dados.get("email"), dados.get("telefone"),
                   dados["id"]))
        pid = dados["id"]
    else:
        c.execute("""INSERT INTO participantes (cliente_id, nome, empresa, cargo, setor, email, telefone)
                     VALUES (?,?,?,?,?,?,?)""",
                  (dados["cliente_id"], dados["nome"], dados.get("empresa"),
                   dados.get("cargo"), dados.get("setor"), dados.get("email"), dados.get("telefone")))
        pid = c.lastrowid
    conn.commit()
    conn.close()
    return pid


def excluir_participante(pid: int):
    conn = get_connection()
    conn.execute("DELETE FROM participantes WHERE id=?", (pid,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# PROFISSIONAIS
# ---------------------------------------------------------------------------
def listar_profissionais():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM profissionais ORDER BY nome").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def salvar_profissional(dados: dict) -> int:
    conn = get_connection()
    c = conn.cursor()
    if dados.get("id"):
        c.execute("""UPDATE profissionais SET nome=?, empresa=?, habilitacao=?,
                     crea=?, email=?, telefone=? WHERE id=?""",
                  (dados["nome"], dados.get("empresa"), dados.get("habilitacao"),
                   dados.get("crea"), dados.get("email"), dados.get("telefone"), dados["id"]))
        pid = dados["id"]
    else:
        c.execute("""INSERT INTO profissionais (nome, empresa, habilitacao, crea, email, telefone)
                     VALUES (?,?,?,?,?,?)""",
                  (dados["nome"], dados.get("empresa"), dados.get("habilitacao"),
                   dados.get("crea"), dados.get("email"), dados.get("telefone")))
        pid = c.lastrowid
    conn.commit()
    conn.close()
    return pid


def excluir_profissional(pid: int):
    conn = get_connection()
    conn.execute("DELETE FROM profissionais WHERE id=?", (pid,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# LAUDOS
# ---------------------------------------------------------------------------
def listar_laudos(cliente_id: int):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM laudos WHERE cliente_id=? ORDER BY criado_em DESC", (cliente_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def salvar_laudo(dados: dict) -> int:
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    if dados.get("id"):
        c.execute("""UPDATE laudos SET numero=?, titulo=?, periodo_inicio=?, periodo_fim=?,
                     cidade_laudo=?, art_pdf_path=?, conclusoes=?, consideracoes=?,
                     status=?, atualizado_em=? WHERE id=?""",
                  (dados.get("numero"), dados.get("titulo"), dados.get("periodo_inicio"),
                   dados.get("periodo_fim"), dados.get("cidade_laudo"), dados.get("art_pdf_path"),
                   dados.get("conclusoes"), dados.get("consideracoes"), dados.get("status", "Em andamento"),
                   now, dados["id"]))
        lid = dados["id"]
    else:
        c.execute("""INSERT INTO laudos (cliente_id, numero, titulo, periodo_inicio, periodo_fim,
                     cidade_laudo, art_pdf_path, conclusoes, consideracoes, status)
                     VALUES (?,?,?,?,?,?,?,?,?,?)""",
                  (dados["cliente_id"], dados.get("numero"), dados.get("titulo"),
                   dados.get("periodo_inicio"), dados.get("periodo_fim"),
                   dados.get("cidade_laudo"), dados.get("art_pdf_path"),
                   dados.get("conclusoes"), dados.get("consideracoes"),
                   dados.get("status", "Em andamento")))
        lid = c.lastrowid
    conn.commit()
    conn.close()
    return lid


def buscar_laudo(laudo_id: int) -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM laudos WHERE id=?", (laudo_id,)).fetchone()
    conn.close()
    return dict(row) if row else {}


def excluir_laudo(laudo_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM laudos WHERE id=?", (laudo_id,))
    conn.commit()
    conn.close()


def vincular_profissional_laudo(laudo_id: int, profissional_id: int):
    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO laudo_profissionais VALUES (?,?)",
                 (laudo_id, profissional_id))
    conn.commit()
    conn.close()


def desvincular_profissional_laudo(laudo_id: int, profissional_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM laudo_profissionais WHERE laudo_id=? AND profissional_id=?",
                 (laudo_id, profissional_id))
    conn.commit()
    conn.close()


def profissionais_do_laudo(laudo_id: int):
    conn = get_connection()
    rows = conn.execute("""SELECT p.* FROM profissionais p
                           JOIN laudo_profissionais lp ON lp.profissional_id=p.id
                           WHERE lp.laudo_id=?""", (laudo_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def vincular_participante_laudo(laudo_id: int, participante_id: int):
    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO laudo_participantes VALUES (?,?)",
                 (laudo_id, participante_id))
    conn.commit()
    conn.close()


def desvincular_participante_laudo(laudo_id: int, participante_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM laudo_participantes WHERE laudo_id=? AND participante_id=?",
                 (laudo_id, participante_id))
    conn.commit()
    conn.close()


def sincronizar_participantes_laudo(laudo_id: int) -> int:
    """Garante que todos os participantes do cliente estejam vinculados ao laudo.

    O vinculo era feito uma unica vez, na criacao do laudo, com os participantes
    que existiam naquele instante -- quem fosse cadastrado depois nunca aparecia
    no item 1.3 nem na folha de assinaturas do PDF. Retorna quantos vinculos
    novos foram criados.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("""INSERT OR IGNORE INTO laudo_participantes (laudo_id, participante_id)
                 SELECT ?, p.id FROM participantes p
                 JOIN laudos l ON l.cliente_id = p.cliente_id
                 WHERE l.id = ?""", (laudo_id, laudo_id))
    novos = c.rowcount
    conn.commit()
    conn.close()
    return novos


def participantes_do_laudo(laudo_id: int):
    conn = get_connection()
    rows = conn.execute("""SELECT p.* FROM participantes p
                           JOIN laudo_participantes lp ON lp.participante_id=p.id
                           WHERE lp.laudo_id=? ORDER BY p.id""", (laudo_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# PAINEIS
# ---------------------------------------------------------------------------
def listar_paineis(laudo_id: int):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM paineis WHERE laudo_id=? ORDER BY formulario_num",
                        (laudo_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def salvar_painel(dados: dict) -> int:
    conn = get_connection()
    c = conn.cursor()
    if dados.get("id"):
        atual = c.execute("SELECT nivel_aderencia, observacoes_gerais FROM paineis WHERE id=?",
                           (dados["id"],)).fetchone()
        nivel_aderencia = dados["nivel_aderencia"] if "nivel_aderencia" in dados \
            else (atual["nivel_aderencia"] if atual else 0.0)
        observacoes_gerais = dados["observacoes_gerais"] if "observacoes_gerais" in dados \
            else (atual["observacoes_gerais"] if atual else None)
        c.execute("""UPDATE paineis SET formulario_num=?, tag=?, setor=?, tipo_painel=?,
                     tensao_forca=?, tensao_comando=?, num_fases=?, descricao=?,
                     data_avaliacao=?, nivel_aderencia=?, observacoes_gerais=?
                     WHERE id=?""",
                  (dados.get("formulario_num"), dados.get("tag"), dados.get("setor"),
                   dados.get("tipo_painel"), dados.get("tensao_forca"), dados.get("tensao_comando"),
                   dados.get("num_fases"), dados.get("descricao"), dados.get("data_avaliacao"),
                   nivel_aderencia, observacoes_gerais, dados["id"]))
        pid = dados["id"]
    else:
        c.execute("""INSERT INTO paineis (laudo_id, formulario_num, tag, setor, tipo_painel,
                     tensao_forca, tensao_comando, num_fases, descricao, data_avaliacao,
                     nivel_aderencia, observacoes_gerais) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (dados["laudo_id"], dados.get("formulario_num"), dados.get("tag"),
                   dados.get("setor"), dados.get("tipo_painel"), dados.get("tensao_forca"),
                   dados.get("tensao_comando"), dados.get("num_fases"), dados.get("descricao"),
                   dados.get("data_avaliacao"), dados.get("nivel_aderencia", 0.0),
                   dados.get("observacoes_gerais")))
        pid = c.lastrowid
    conn.commit()
    conn.close()
    return pid


def salvar_fotos_identificacao(painel_id: int, frontal: str = "", lateral_dir: str = "",
                                lateral_esq: str = "", traseira: str = ""):
    """Salva os caminhos das 4 fotos de identificacao visual do painel."""
    conn = get_connection()
    conn.execute("""UPDATE paineis SET foto_frontal=?, foto_lateral_dir=?,
                    foto_lateral_esq=?, foto_traseira=? WHERE id=?""",
                 (frontal or None, lateral_dir or None, lateral_esq or None,
                  traseira or None, painel_id))
    conn.commit()
    conn.close()


def buscar_fotos_identificacao(painel_id: int) -> dict:
    """Retorna dict com caminhos das fotos de identificacao do painel."""
    conn = get_connection()
    row = conn.execute(
        "SELECT foto_frontal, foto_lateral_dir, foto_lateral_esq, foto_traseira "
        "FROM paineis WHERE id=?", (painel_id,)
    ).fetchone()
    conn.close()
    if not row:
        return {}
    return {
        "frontal":     row["foto_frontal"] or "",
        "lateral_dir": row["foto_lateral_dir"] or "",
        "lateral_esq": row["foto_lateral_esq"] or "",
        "traseira":    row["foto_traseira"] or "",
    }


def buscar_painel(painel_id: int) -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM paineis WHERE id=?", (painel_id,)).fetchone()
    conn.close()
    return dict(row) if row else {}


def excluir_painel(painel_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM paineis WHERE id=?", (painel_id,))
    conn.commit()
    conn.close()


def calcular_nivel_aderencia(painel_id: int) -> float:
    """Calcula o nível de aderência com base nas avaliações (exclui 'Não avaliado')."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT peso FROM avaliacoes WHERE painel_id=? AND peso IS NOT NULL",
        (painel_id,)
    ).fetchall()
    conn.close()
    if not rows:
        return 0.0
    total = sum(r["peso"] for r in rows)
    return round(total / len(rows), 4)


def atualizar_nivel_aderencia(painel_id: int):
    nivel = calcular_nivel_aderencia(painel_id)
    conn = get_connection()
    conn.execute("UPDATE paineis SET nivel_aderencia=? WHERE id=?", (nivel, painel_id))
    conn.commit()
    conn.close()
    return nivel


# ---------------------------------------------------------------------------
# AVALIAÇÕES
# ---------------------------------------------------------------------------
def listar_avaliacoes(painel_id: int):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM avaliacoes WHERE painel_id=? ORDER BY item_numero", (painel_id,)
    ).fetchall()
    conn.close()
    return {r["item_numero"]: dict(r) for r in rows}


def salvar_avaliacao(painel_id: int, item_numero: int, opcao_id, peso, observacoes: str, acao_corretiva: str):
    conn = get_connection()
    conn.execute("""INSERT INTO avaliacoes (painel_id, item_numero, opcao_id, peso, observacoes, acao_corretiva)
                    VALUES (?,?,?,?,?,?)
                    ON CONFLICT(painel_id, item_numero) DO UPDATE SET
                    opcao_id=excluded.opcao_id, peso=excluded.peso,
                    observacoes=excluded.observacoes, acao_corretiva=excluded.acao_corretiva""",
                 (painel_id, item_numero, opcao_id, peso, observacoes, acao_corretiva))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# FOTOS
# ---------------------------------------------------------------------------
def listar_fotos(painel_id: int, item_numero: int = None):
    conn = get_connection()
    if item_numero is not None:
        rows = conn.execute(
            "SELECT * FROM fotos WHERE painel_id=? AND item_numero=?", (painel_id, item_numero)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM fotos WHERE painel_id=? ORDER BY item_numero", (painel_id,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def adicionar_foto(painel_id: int, item_numero: int, caminho: str, legenda: str = "") -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO fotos (painel_id, item_numero, caminho, legenda) VALUES (?,?,?,?)",
              (painel_id, item_numero, caminho, legenda))
    fid = c.lastrowid
    conn.commit()
    conn.close()
    return fid


def excluir_foto(foto_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM fotos WHERE id=?", (foto_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# CHECKLIST ITEMS
# ---------------------------------------------------------------------------
def listar_checklist_items():
    conn = get_connection()
    items = conn.execute(
        "SELECT * FROM checklist_items WHERE ativo=1 ORDER BY numero"
    ).fetchall()
    result = []
    for item in items:
        opcoes = conn.execute(
            "SELECT * FROM checklist_opcoes WHERE item_id=?", (item["id"],)
        ).fetchall()
        d = dict(item)
        d["opcoes"] = [dict(o) for o in opcoes]
        result.append(d)
    conn.close()
    return result


def salvar_checklist_item(dados: dict) -> int:
    """Salva um item do checklist e suas opcoes.

    As opcoes sao atualizadas "no lugar" (casando pela descricao) em vez de
    apagar e recriar tudo -- avaliacoes ja registradas referenciam
    checklist_opcoes.id via FOREIGN KEY, entao recriar as opcoes quebraria
    essas avaliacoes (ou falharia com IntegrityError, ja que a FK impede
    apagar uma opcao ainda referenciada).
    """
    conn = get_connection()
    c = conn.cursor()
    if dados.get("id"):
        c.execute("""UPDATE checklist_items SET numero=?, questao=?, justificativa=?, ativo=?
                     WHERE id=?""",
                  (dados["numero"], dados["questao"], dados.get("justificativa"), dados.get("ativo", 1), dados["id"]))
        iid = dados["id"]
        existentes = c.execute(
            "SELECT id, descricao FROM checklist_opcoes WHERE item_id=?", (iid,)
        ).fetchall()
        existentes_por_desc = {row["descricao"]: row["id"] for row in existentes}
    else:
        c.execute("INSERT INTO checklist_items (numero, questao, justificativa) VALUES (?,?,?)",
                  (dados["numero"], dados["questao"], dados.get("justificativa")))
        iid = c.lastrowid
        existentes_por_desc = {}

    descricoes_novas = set()
    for opc in dados.get("opcoes", []):
        desc = opc["descricao"]
        descricoes_novas.add(desc)
        if desc in existentes_por_desc:
            c.execute(
                """UPDATE checklist_opcoes
                   SET peso=?, observacao_padrao=?, acao_corretiva_padrao=?
                   WHERE id=?""",
                (opc.get("peso"), opc.get("observacao_padrao"), opc.get("acao_corretiva_padrao"),
                 existentes_por_desc[desc]))
        else:
            c.execute(
                """INSERT INTO checklist_opcoes
                   (item_id, descricao, peso, observacao_padrao, acao_corretiva_padrao)
                   VALUES (?,?,?,?,?)""",
                (iid, desc, opc.get("peso"),
                 opc.get("observacao_padrao"), opc.get("acao_corretiva_padrao")))

    # Remove opcoes que nao estao mais na lista -- se alguma ja tiver
    # avaliacoes vinculadas, a FK impede a exclusao; nesse caso a opcao
    # antiga fica orfa (nao aparece mais no formulario, mas preserva o
    # historico de avaliacoes ja registradas).
    for desc, opc_id in existentes_por_desc.items():
        if desc not in descricoes_novas:
            try:
                c.execute("DELETE FROM checklist_opcoes WHERE id=?", (opc_id,))
            except sqlite3.IntegrityError:
                pass

    conn.commit()
    conn.close()
    return iid


# ---------------------------------------------------------------------------
# ESTATÍSTICAS
# ---------------------------------------------------------------------------
def estatisticas_laudo(laudo_id: int) -> dict:
    """Retorna dados consolidados para gráficos do laudo."""
    conn = get_connection()
    paineis = conn.execute(
        "SELECT id, tag, setor, nivel_aderencia FROM paineis WHERE laudo_id=?", (laudo_id,)
    ).fetchall()

    items = conn.execute(
        "SELECT numero, questao FROM checklist_items WHERE ativo=1 ORDER BY numero"
    ).fetchall()

    # Por item: média dos pesos (excluindo None)
    item_stats = {}
    for item in items:
        num = item["numero"]
        rows = conn.execute("""
            SELECT a.peso FROM avaliacoes a
            JOIN paineis p ON p.id=a.painel_id
            WHERE p.laudo_id=? AND a.item_numero=? AND a.peso IS NOT NULL
        """, (laudo_id, num)).fetchall()
        if rows:
            scores = [r["peso"] for r in rows]
            item_stats[num] = {
                "questao": item["questao"],
                "media": sum(scores) / len(scores),
                "contagens": {
                    "Sim": sum(1 for s in scores if s == 1.0),
                    "Parcial": sum(1 for s in scores if 0 < s < 1.0),
                    "Não": sum(1 for s in scores if s == 0.0),
                }
            }
        else:
            item_stats[num] = {"questao": item["questao"], "media": 0.0, "contagens": {}}

    conn.close()
    return {
        "paineis": [dict(p) for p in paineis],
        "item_stats": item_stats,
        "total_paineis": len(paineis),
        "media_geral": (
            sum((p["nivel_aderencia"] or 0.0) for p in paineis) / len(paineis) if paineis else 0.0
        )
    }
