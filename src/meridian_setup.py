"""Construção e inspeção reais da API 2.1.0, sem qualquer amostragem."""
import dataclasses
import importlib.metadata
import numpy as np
import yaml
from .data_source import ROOT
from .data_contract import CHANNELS, MEDIA, SPEND, CONTROLS, ORGANIC, validate, require
from .validation_design import aligned_mask

def api():
    version = importlib.metadata.version('google-meridian')
    require(version == '2.1.0', f'Versão não validada: {version}')
    from meridian.data import load
    from meridian.model import spec
    return load, spec

def build_input(df):
    validate(df)
    load, _ = api()
    mapping = load.CoordToColumns(geo='geo', time='time', kpi='conversions', population='population',
                                 media=MEDIA, media_spend=SPEND, controls=CONTROLS,
                                 organic_media=ORGANIC, non_media_treatments=['Promo'])
    # Receita unitária é preservada no CSV; não ativa a análise monetária principal.
    return load.DataFrameDataLoader(df=df.copy(), coord_to_columns=mapping, kpi_type='non_revenue',
                                    media_to_channel=dict(zip(MEDIA,CHANNELS)),
                                    media_spend_to_channel=dict(zip(SPEND,CHANNELS))).load()

def build_spec(input_data, split=None):
    _, spec = api()
    config = yaml.safe_load((ROOT/'configs/baseline_geo.yaml').read_text())
    kwargs = {key:value['value'] for key,value in config['parameters'].items()}
    if split is not None:
        geos, times = list(input_data.geo.values), list(input_data.time.values)
        mask = aligned_mask(split, geos, times)
        kwargs['holdout'] = spec.HoldoutSpec([
            spec.GeoHoldoutSpec([g], [spec.DateRange(str(times[j]),str(times[j]))
                                     for j in np.flatnonzero(mask[i])]) for i,g in enumerate(geos)])
    return spec.ModelSpec(**kwargs)

def inspect_input(data, df):
    geos, times = list(data.geo.values), list(data.time.values)
    ordered = df.set_index(['geo','time']).reindex(__import__('pandas').MultiIndex.from_product([geos,times]))
    expected = {'kpi':(40,156), 'population':(40,), 'media':(40,156,5),
                'media_spend':(40,156,5), 'controls':(40,156,2),
                'organic_media':(40,156,1), 'non_media_treatments':(40,156,1)}
    report={}
    for name, shape in expected.items():
        a=getattr(data,name)
        require(a.shape==shape, f'Dimensão incorreta em {name}: {a.shape}')
        require(np.isfinite(a.values).all(), f'Tensor não finito: {name}')
        report[name]={'shape':list(a.shape),'dims':list(a.dims)}
    require(list(data.media_channel.values)==CHANNELS, 'Ordem dos canais incorreta')
    np.testing.assert_allclose(data.kpi.values,ordered.conversions.to_numpy().reshape(40,156),rtol=1e-6)
    for j,c in enumerate(CHANNELS):
        for attr,col in [('media',f'{c}_impression'),('media_spend',f'{c}_spend')]:
            np.testing.assert_allclose(getattr(data,attr).values[:,:,j],ordered[col].to_numpy().reshape(40,156),rtol=1e-6)
    require(data.revenue_per_kpi is None,'Conversão monetária indevidamente ativada')
    report['geos']=geos
    report['times']=times
    return report

def inspect_priors(model_spec):
    result={}
    for field in dataclasses.fields(model_spec.prior):
        dist=getattr(model_spec.prior,field.name)
        params={}
        for k,v in dist.parameters.items():
            if k in ['loc','scale','low','high','concentration1','concentration0']:
                params[k]=np.asarray(v).tolist()
        result[field.name]={'distribution':type(dist).__name__,'parameters':params}
    return result
