"""Reserva sem consultar KPI; seis GEOs por semana e balanço por mercado."""
import numpy as np
import pandas as pd
from .data_contract import CHANNELS, MEDIA, SPEND, require

def make_holdout(keys, seed=20261026, per_week=6):
    keys = keys[['geo', 'time']].copy()
    require(not keys.duplicated().any(), 'Chaves repetidas no split')
    geos, times = sorted(keys.geo.unique()), sorted(keys.time.unique())
    n = len(geos)
    require(0 < per_week < n, 'Fração inválida')
    require(len(keys) == n*len(times), 'Split requer painel completo')
    rng = np.random.Generator(np.random.PCG64(seed))
    order = rng.permutation(n)
    weeks = rng.permutation(len(times))
    mask = np.zeros((n, len(times)), dtype=bool)
    for j, week in enumerate(weeks):
        mask[order[(np.arange(per_week)+j*per_week) % n], week] = True
    return pd.DataFrame([(g,t,bool(mask[i,j])) for i,g in enumerate(geos)
                         for j,t in enumerate(times)], columns=['geo','time','is_holdout'])

def aligned_mask(split, geos, times):
    require(split.is_holdout.dtype == bool, 'Máscara deve conter booleanos reais')
    require(not split[['geo','time']].duplicated().any(), 'Split duplicado')
    idx = pd.MultiIndex.from_product([list(geos), list(times)], names=['geo','time'])
    s = split.set_index(['geo','time']).is_holdout
    require(set(s.index) == set(idx), 'Split e InputData têm coordenadas diferentes')
    return s.reindex(idx).to_numpy().reshape(len(geos),len(times))

def coverage(df, split):
    z = df.merge(split, on=['geo','time'], validate='one_to_one')
    require(len(z)==len(df) and len(split)==len(df), 'Split incompleto')
    result = {}
    for key in ['geo','time']:
        a = z.groupby(key).is_holdout.agg(['sum','count','mean']).reset_index()
        a.columns = [key,'holdout_n','total_n','holdout_fraction']
        result[key] = a
    rows=[]
    for channel,m,s in zip(CHANNELS,MEDIA,SPEND):
        for label, part in z.groupby('is_holdout'):
            rows.append(dict(channel=channel, subset='test' if label else 'train',
                             cells=len(part), active_cells=int(part[m].gt(0).sum()),
                             activity_fraction=float(part[m].gt(0).mean()),
                             exposure=float(part[m].sum()), spend=float(part[s].sum())))
    result['channels']=pd.DataFrame(rows)
    local=[]
    for (geo,h),part in z.groupby(['geo','is_holdout']):
        local.append(dict(geo=geo,subset='test' if h else 'train',cells=len(part),
                          channel2_active=int(part.Channel2_impression.gt(0).sum())))
    result['channel2_geo']=pd.DataFrame(local)
    return result
