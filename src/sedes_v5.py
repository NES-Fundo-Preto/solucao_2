import pandas as pd
import json
import random
import unicodedata

#Arquivos
arquivo_distancia = 'C:/prog/fundo_preto/dist_test.csv'
arquivo_contrato = "C:/prog/fundo_preto/Analise cidades  - CEMEAI - Base de dados - CONSIDERAR ESTA .csv"
arquivo_concorrentes = 'C:/prog/fundo_preto/Concorrentes.csv'
arquivo_correcao = 'C:/prog/fundo_preto/correcoes_cidades.json'

#Variaveis
# as variaveis com uma # do lado são as mais interessantes de se alterar o valor
# a depender do problema, o resto não mude
raio           = 49
n_inicio       = 700 #
n_iteracao     = 300 #
n_pertubacao   = 100 #
n_vizinhos     = 25
n_restarts     = 20 #
dic_distancias = {}

def normalizar(nome):
    nome = str(nome).strip().lower()
    nome = unicodedata.normalize('NFKD', nome)
    return ''.join(c for c in nome if not unicodedata.combining(c))

#matrix (Dataframe) com distancia entre as estradas
dist_matrix = pd.read_csv(arquivo_distancia, index_col=0)
dist_matrix.index   = [normalizar(i) for i in dist_matrix.index]
dist_matrix.columns = [normalizar(c) for c in dist_matrix.columns]

for c1 in dist_matrix.index:
    for c2 in dist_matrix.columns:
        val = dist_matrix.loc[c1, c2]
        if pd.notna(val):
            dic_distancias[(c1, c2)] = float(val)
            dic_distancias[(c2, c1)] = float(val)

#lista das cidades da bahia
cidades_bahia = sorted(dist_matrix.index.tolist())

def distancia(c1, c2):
    return 0.0 if c1 == c2 else dic_distancias.get((c1, c2), 9999.0)

#concorrentes por produto e por cidade (dataframe)
conc_df = pd.read_csv(arquivo_concorrentes, header=0, index_col=0)
conc_df.index   = [normalizar(i) for i in conc_df.index]
conc_df.columns = [normalizar(c) for c in conc_df.columns]

# dicionario de produtos com cidades e quantidades de concorrentes
concorrentes = {}
for produto in conc_df.index:
    concorrentes[produto] = []
    for cidade in conc_df.columns:
        qtd = int(conc_df.loc[produto, cidade])
        if qtd > 0:
            concorrentes[produto].append((cidade, qtd))

#leitura de outros arquivos
df = pd.read_csv(arquivo_contrato, header=11)
df = df[df['ID '].notna()].copy()
df.columns = [
    'id', 'sedes', 'produto', 'empate_49km', 'dist_oficial',
    'segunda_dist', 'cep', 'cidade_contrato', 'cidade_rodizio',
    'dist_google', 'cidades_concorrentes',
    'c11', 'c12', 'c13', 'c14', 'c15'
]
df['produto'] = df['produto'].apply(normalizar)
df['cidade_contrato'] = df['cidade_contrato'].apply(normalizar)

with open(arquivo_correcao, encoding='utf-8') as f:
    correcoes = json.load(f)
df['cidade_contrato'] = df['cidade_contrato'].map(lambda c: correcoes.get(c, c))
df = df[df['cidade_contrato'].notna()].copy()

cidades_validas = set(c1 for (c1, _) in dic_distancias)
contratos_filtrados = df[df['cidade_contrato'].isin(cidades_validas)].copy()
contratos = contratos_filtrados.to_dict('records')

vizinhos = {}
for cidade in cidades_bahia:
    ds = [(o, distancia(cidade, o)) for o in cidades_bahia if o != cidade]
    ds.sort(key=lambda x: x[1])
    vizinhos[cidade] = [c for c, _ in ds[:n_vizinhos]]

#_dist_concs repete a distância conforme a quantidade de concorrentes
for c in contratos:
    lista = []
    for cidade_conc, qtd in concorrentes.get(c['produto'], []):
        d = distancia(c['cidade_contrato'], cidade_conc)
        lista.extend([d] * qtd)
    c['_dist_concs'] = lista

SEDE1_PRODUTOS = {'fpi', 'fpe', 'fpm', 'fpv', 'fpia', 'fpp'}
SEDE2_PRODUTOS = {'fpm', 'fpia'}

def pontuar_contrato(contrato, dist_s1, dist_s2, s1_eleg, s2_eleg):
    todos = (
        [('empresa', dist_s1)] * s1_eleg +
        [('empresa', dist_s2)] * s2_eleg +
        [('concorrente', d) for d in contrato['_dist_concs']]
    )
    if not todos:
        return 0.0

    dentro_raio = [(tipo, d) for tipo, d in todos if d <= raio]
    if dentro_raio:
        return sum(1 for tipo, _ in dentro_raio if tipo == 'empresa') / len(dentro_raio)
    dist_min = min(d for _, d in todos)
    empatados = [(tipo, d) for tipo, d in todos if d == dist_min]
    return sum(1 for tipo, _ in empatados if tipo == 'empresa') / len(empatados)

def pontuacao_total(s1, s2):
    total = 0.0
    for c in contratos:
        s1_eleg = c['produto'] in SEDE1_PRODUTOS
        s2_eleg = c['produto'] in SEDE2_PRODUTOS
        if not s1_eleg and not s2_eleg:
            continue
        dist_s1 = distancia(s1, c['cidade_contrato']) if s1_eleg else 9999
        dist_s2 = distancia(s2, c['cidade_contrato']) if s2_eleg else 9999
        total += pontuar_contrato(c, dist_s1, dist_s2, s1_eleg, s2_eleg)
    return total

def pontuacao_produto(s1, s2, produto):
    total = 0.0
    s1_eleg = produto in SEDE1_PRODUTOS
    s2_eleg = produto in SEDE2_PRODUTOS
    for c in contratos:
        if c['produto'] != produto:
            continue
        dist_s1 = distancia(s1, c['cidade_contrato']) if s1_eleg else 9999
        dist_s2 = distancia(s2, c['cidade_contrato']) if s2_eleg else 9999
        total += pontuar_contrato(c, dist_s1, dist_s2, s1_eleg, s2_eleg)
    return total

def perturbar(s1, s2):
    if random.random() < 0.4:
        nova_s1 = random.choice(cidades_bahia)
        nova_s2 = random.choice(cidades_bahia)
        return nova_s1, nova_s2
    alvo = random.choice([0, 1])
    cidade_atual = s1 if alvo == 0 else s2
    nova = random.choice(vizinhos[cidade_atual])
    return (nova, s2) if alvo == 0 else (s1, nova)

def restart_sede_atual(fn_score, label=''):
    melhor_par   = (normalizar('Feira de Santana'), normalizar('Catolandia'))
    melhor_score = fn_score(*melhor_par)
    print(f"  {label}Inicial (sedes atuais): {melhor_par[0].title()} + {melhor_par[1].title()} -> {melhor_score:.2f}")
    for i in range(n_iteracao):
        scores = [(par, fn_score(*par)) for par in [perturbar(*melhor_par) for _ in range(n_pertubacao)]]
        melhor_cand, sc = max(scores, key=lambda x: x[1])
        if sc > melhor_score:
            melhor_score, melhor_par = sc, melhor_cand
            print(f"  {label}[{i+1:3d}] {melhor_par[0].title()} + {melhor_par[1].title()} = {melhor_score:.2f}")
    return melhor_par, melhor_score

def um_restart(fn_score, label=''):
    melhor_score, melhor_par = -1, None
    for _ in range(n_inicio):
        s1, s2 = random.choice(cidades_bahia), random.choice(cidades_bahia)
        sc = fn_score(s1, s2)
        if sc > melhor_score:
            melhor_score, melhor_par = sc, (s1, s2)
    print(f"  {label}Inicial: {melhor_par[0].title()} + {melhor_par[1].title()} -> {melhor_score:.2f}")
    for i in range(n_iteracao):
        scores = [(par, fn_score(*par)) for par in [perturbar(*melhor_par) for _ in range(n_pertubacao)]]
        melhor_cand, sc = max(scores, key=lambda x: x[1])
        if sc > melhor_score:
            melhor_score, melhor_par = sc, melhor_cand
            print(f"  {label}[{i+1:3d}] {melhor_par[0].title()} + {melhor_par[1].title()} = {melhor_score:.2f}")
    return melhor_par, melhor_score

def imprimir_ranking(resultados, score_ref, titulo):
    vistos = set()
    ranking = []

    ordenado = sorted(resultados, key=lambda x: (-x[1], tuple(sorted(x[0]))))

    i = 0
    while len(ranking) < 10 and i < len(ordenado):
        par, score = ordenado[i]
        chave = tuple(sorted(par))

        if chave not in vistos:
            vistos.add(chave)
            ranking.append((par, score))

        i += 1

    print(f"\n{'='*70}")
    print(f"  {titulo}")
    print(f"{'='*70}")
    print(f"{'#':<4} {'Sede 1':<25} {'Sede 2':<25} {'Score':>8} {'vs atual':>10}")
    print(f"{'-'*70}")

    for i, (par, score) in enumerate(ranking, 1):
        ganho = score - score_ref
        sinal = '+' if ganho >= 0 else ''
        print(f"{i:<4} {par[0].title():<25} {par[1].title():<25} {score:>8.2f} {sinal}{ganho:.2f}")

    print(f"  Referencia (Feira + Catolandia): {score_ref:.2f}")
    print(f"  Referencia (Feira + Catolandia): {score_ref:.2f}")

if __name__ == '__main__':
    ref_s1 = normalizar('Feira de Santana')
    ref_s2 = normalizar('Catolandia')

    #ranking geral
    score_geral_atual = pontuacao_total(ref_s1, ref_s2)
    print(f"Referencia (Feira + Catolandia): {score_geral_atual:.2f}\n")

    resultados_geral = []

    par, score = restart_sede_atual(pontuacao_total)
    resultados_geral.append((par, score))

    for _ in range(n_restarts):
        par, score = um_restart(pontuacao_total)
        resultados_geral.append((par, score))

    imprimir_ranking(resultados_geral, score_geral_atual, "RANKING GERAL - TOP 10")

    #ranking por produto
    produtos_presentes = sorted({c['produto'] for c in contratos
                                 if c['produto'] in SEDE1_PRODUTOS | SEDE2_PRODUTOS})

    for produto in produtos_presentes:
        fn = lambda s1, s2, p=produto: pontuacao_produto(s1, s2, p)
        score_prod_atual = fn(ref_s1, ref_s2)

        print(f"  OTIMIZACAO - PRODUTO: {produto.upper()}")
        print(f"  Referencia (Feira + Catolandia): {score_prod_atual:.2f}\n")

        resultados_prod = [restart_sede_atual(fn, label=f'[{produto.upper()}] ')]
        for r in range(n_restarts):
            resultados_prod.append(um_restart(fn, label=f'[{produto.upper()}] '))

        imprimir_ranking(resultados_prod, score_prod_atual,
                         f"RANKING {produto.upper()} - TOP 10")
