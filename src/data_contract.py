"""Contrato estrutural e semântico do painel sintético; não refaz a EDA."""
import numpy as np
import pandas as pd

CHANNELS = [f'Channel{i}' for i in range(5)]
MEDIA = [f'{c}_impression' for c in CHANNELS]
SPEND = [f'{c}_spend' for c in CHANNELS]
CONTROLS = ['competitor_sales_control', 'sentiment_score_control']
ORGANIC = ['Organic_channel0_impression']
NUMERIC = MEDIA + SPEND + CONTROLS + ORGANIC + ['Promo', 'conversions', 'revenue_per_conversion', 'population']
EXPECTED = ['geo', 'time'] + NUMERIC

def require(condition, message):
    if not condition:
        raise ValueError(message)

def load_panel(path):
    df = pd.read_csv(path)
    if 'Unnamed: 0' in df:
        require(np.array_equal(df['Unnamed: 0'].values, np.arange(len(df))), 'Índice exportado não sequencial')
        df = df.drop(columns='Unnamed: 0')
    validate(df)
    return df.sort_values(['geo', 'time'], kind='stable').reset_index(drop=True)

def validate(df):
    require(set(df.columns) == set(EXPECTED), 'Colunas diferentes do contrato')
    require(len(df) == 6240, 'Painel deve conter 6.240 células')
    require(not df[['geo', 'time']].duplicated().any(), 'Chave GEO/tempo duplicada')
    require(set(df.geo) == {f'Geo{i}' for i in range(40)}, 'Mercados inesperados')
    expected_dates = pd.date_range('2021-01-25', '2024-01-15', freq='7D').strftime('%Y-%m-%d').tolist()
    require(set(df.time) == set(expected_dates), 'Datas incompatíveis com calendário semanal')
    require(df.groupby('geo').time.nunique().eq(156).all(), 'Painel desbalanceado')
    require(all(pd.api.types.is_numeric_dtype(df[c]) for c in NUMERIC), 'Tipo numérico inválido')
    require(np.isfinite(df[NUMERIC].to_numpy()).all(), 'Missing ou infinito')
    nonnegative = [c for c in NUMERIC if c not in CONTROLS]
    require(df[nonnegative].ge(0).all().all(), 'Valor negativo fora dos controles')
    require(df.population.gt(0).all(), 'População não positiva')
    require(df.groupby('geo').population.nunique().eq(1).all(), 'População varia dentro de GEO')
    require(df.revenue_per_conversion.gt(0).all(), 'Receita unitária não positiva')
    for m, s in zip(MEDIA, SPEND):
        require(df[m].eq(0).equals(df[s].eq(0)), f'Zero impressão/gasto desalinhado: {m}')
    return True

def audit(df):
    validate(df)
    return pd.DataFrame([dict(variable=c, minimum=float(df[c].min()), maximum=float(df[c].max()),
                              zeros=int(df[c].eq(0).sum()), negatives=int(df[c].lt(0).sum()),
                              total=float(df[c].sum()), status='PASS') for c in NUMERIC])

def eda_comparison(df):
    checks = [('Channel2_zero_fraction', float(df.Channel2_impression.eq(0).mean()), .643, .001),
              ('Channel3_zero_fraction', float(df.Channel3_impression.eq(0).mean()), .027, .001),
              ('Promo_zero_fraction', float(df.Promo.eq(0).mean()), .47, .01),
              ('Channel2_spend_share', float(df.Channel2_spend.sum()/df[SPEND].sum().sum()), .055, .002),
              ('Channel3_spend_share', float(df.Channel3_spend.sum()/df[SPEND].sum().sum()), .40, .01)]
    return pd.DataFrame([dict(metric=m, observed=v, eda_rounded=e, tolerance=t,
                              status='PASS' if abs(v-e)<=t else 'REVIEW') for m,v,e,t in checks])
