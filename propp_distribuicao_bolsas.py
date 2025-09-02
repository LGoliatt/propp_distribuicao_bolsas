import pandas as pd

# ------------------------------
# 1. Ler o arquivo CSV da linha 4
# ------------------------------
file_path = "./data/AF 150824.csv"
df = pd.read_csv(file_path, skiprows=3, encoding="latin-1", sep=';')

# ------------------------------
# 2. Listar colunas
# ------------------------------
print("Colunas disponíveis no arquivo:")
print(df.columns.tolist())

# ------------------------------
# 3. Preparar dados
# ------------------------------
# Normalizar nomes das colunas relevantes
df.columns = df.columns.str.strip()

col_orientador = "Orientador"
col_comite = "Área do Comitê"
col_prod = "Bolsista de Produtividade?"

# Contagem de projetos por área
area_counts = df[col_comite].value_counts()

print("\nNúmero de projetos por área:")
print(area_counts)

# ------------------------------
# 4. Distribuição das bolsas
# ------------------------------
N_PIBIC = 24
N_BIC = 60

# Controle das bolsas alocadas
df["PIBIC"] = 0
df["BIC"] = 0
df["Total_Bolsas"] = 0

# 4.1 Primeira rodada: garantir 1 bolsa PIBIC por bolsista de produtividade
produtores = df[df[col_prod].str.upper() == "SIM"]

for idx in produtores.index:
    if N_PIBIC > 0:
        df.loc[idx, "PIBIC"] += 1
        df.loc[idx, "Total_Bolsas"] += 1
        N_PIBIC -= 1

# 4.2 Rodadas subsequentes
# ordem: cada projeto pode receber até 1 bolsa por rodada, máximo 3 por orientador
while (N_PIBIC + N_BIC) > 0:
    for idx, row in df.iterrows():
        if df.loc[idx, "Total_Bolsas"] < 3:
            if N_PIBIC > 0:
                df.loc[idx, "PIBIC"] += 1
                df.loc[idx, "Total_Bolsas"] += 1
                N_PIBIC -= 1
            elif N_BIC > 0:
                df.loc[idx, "BIC"] += 1
                df.loc[idx, "Total_Bolsas"] += 1
                N_BIC -= 1
        if (N_PIBIC + N_BIC) == 0:
            break

# ------------------------------
# 5. Resultados finais
# ------------------------------
print("\nBolsas restantes após distribuição:")
print("PIBIC:", N_PIBIC, " | BIC:", N_BIC)

# Agrupar por área para ver distribuição
area_dist = df.groupby(col_comite)[["PIBIC", "BIC", "Total_Bolsas"]].sum()

print("\nDistribuição final por área:")
print(area_dist)

# Salvar em arquivo para conferência
output_path = "/mnt/data/distribuicao_bolsas.csv"
df.to_csv(output_path, index=False)
print(f"\nArquivo final salvo em: {output_path}")


#%%
import pandas as pd
from collections import defaultdict

# ================== 1. LEITURA DO ARQUIVO ==================
file_path = "./data/AF 150824.csv"
df_raw = pd.read_csv(file_path, sep=';', skiprows=3, encoding="latin-1", engine='python', dtype=str, on_bad_lines='skip')

# Ajustar nomes de colunas
df_raw.columns = [col.strip() for col in df_raw.columns]

# Filtrar apenas projetos AVALIADOS
df = df_raw[df_raw['Situação'] == 'AVALIADO'].copy()

# Converter colunas numéricas
df['Nota Final'] = pd.to_numeric(df['Nota Final'], errors='coerce').fillna(0)
df['Bolsas Solicitadas'] = pd.to_numeric(df['Bolsas Solicitadas'], errors='coerce').fillna(0)
df['Bolsas Recomendadas'] = pd.to_numeric(df['Bolsas Recomendadas'], errors='coerce').fillna(0)

# ================== 2. INICIALIZAÇÃO DE VARIÁVEIS ==================
PIBIC_TOTAL = 31
BIC_TOTAL = 50

# Dicionários para controle
orientador_bolsas = defaultdict(int)  # quantas bolsas o orientador já recebeu
orientador_pq = set(df[df['Bolsista de Produtividade?'] == 'SIM']['Orientador'].unique())

# Armazenar resultado final
df['Bolsas Alocadas'] = 0

# ================== 3. PRIMEIRA RODADA: PIBIC PARA PESQUISADORES PQ ==================
# Ordenar por nota para desempate
df = df.sort_values(by='Nota Final', ascending=False).reset_index(drop=True)

pibic_remaining = PIBIC_TOTAL

# Alocar 1 bolsa PIBIC para cada orientador PQ (até 1 por projeto, limite 3 por orientador)
for idx, row in df.iterrows():
    orientador = row['Orientador']
    if orientador not in orientador_pq:
        continue
    if orientador_bolsas[orientador] >= 3:
        continue
    if row['Bolsas Alocadas'] >= row['Bolsas Recomendadas']:
        continue
    if pibic_remaining <= 0:
        break

    # Alocar 1 bolsa PIBIC
    df.loc[idx, 'Bolsas Alocadas'] += 1
    orientador_bolsas[orientador] += 1
    pibic_remaining -= 1

# ================== 4. DISTRIBUIÇÃO DAS BOLSAS RESTANTES (PIBIC não usadas + BIC) ==================
total_bolsas_restantes = pibic_remaining + BIC_TOTAL

while total_bolsas_restantes > 0:
    # Filtrar projetos com demanda e respeitando limite de 3 bolsas por orientador
    remaining_projects = df[
        (df['Bolsas Alocadas'] < df['Bolsas Recomendadas']) &
        (df['Orientador'].map(lambda x: orientador_bolsas[x]) < 3)
    ].copy()

    if remaining_projects.empty:
        break

    # Prioridade: primeiro projetos de orientadores SEM bolsa PQ, depois com PQ
    remaining_projects['EhSemPQ'] = remaining_projects['Orientador'].apply(lambda x: x not in orientador_pq)

    # Ordenar por:
    # 1. Sem PQ (True primeiro)
    # 2. Nota Final (decrescente)
    remaining_projects = remaining_projects.sort_values(
        by=['EhSemPQ', 'Nota Final'], 
        ascending=[False, False]
    )

    allocated_in_round = False
    for idx, row in remaining_projects.iterrows():
        orientador = row['Orientador']
        if orientador_bolsas[orientador] >= 3:
            continue
        if row['Bolsas Alocadas'] >= row['Bolsas Recomendadas']:
            continue
        if total_bolsas_restantes <= 0:
            break

        # Alocar 1 bolsa (agora é PIBIC restante ou BIC — não diferenciamos mais)
        df.loc[idx, 'Bolsas Alocadas'] += 1
        orientador_bolsas[orientador] += 1
        total_bolsas_restantes -= 1
        allocated_in_round = True

    if not allocated_in_round:
        break

# ================== 5. RESULTADO FINAL ==================
print(f"Bolsas PIBIC não distribuídas (incorporadas ao BIC): {pibic_remaining}")
print(f"Bolsas BIC restantes: {total_bolsas_restantes}")
print(f"Bolsas totais alocadas: {PIBIC_TOTAL + BIC_TOTAL - total_bolsas_restantes}")

# Salvar resultado
df.to_csv('resultado_distribuicao_bolsas.csv', index=False, sep=';')

# ================== 6. RESUMO POR ÁREA ==================
print("\n=== RESUMO POR ÁREA DO COMITÊ ===")
resumo_area = df.groupby('Área do Comitê').agg(
    Projetos=('Nº Inscrição', 'count'),
    Bolsas_Alocadas=('Bolsas Alocadas', 'sum'),
    Pesquisadores_PQ=('Bolsista de Produtividade?', lambda x: (x == 'SIM').sum())
).reset_index()
print(resumo_area.to_string(index=False))

# ================== 7. RESUMO GERAL ==================
print(f"\n=== RESUMO GERAL ===")
print(f"Total de bolsas alocadas: {df['Bolsas Alocadas'].sum()}")
print(f"Projetos contemplados com pelo menos 1 bolsa: {(df['Bolsas Alocadas'] > 0).sum()}")
print(f"Orientadores com bolsa de produtividade: {len(orientador_pq)}")
print(f"Orientadores que receberam bolsa: {len([k for k, v in orientador_bolsas.items() if v > 0])}")