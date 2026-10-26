from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import pytest
from src.data_source import retrieve, verify_bytes, check_provenance, ROOT
from src.data_contract import load_panel, validate, audit, MEDIA, SPEND, CONTROLS
from src.validation_design import make_holdout, coverage, aligned_mask

@pytest.fixture
def df():
    return load_panel(retrieve())

def test_panel_and_provenance(df):
    assert validate(df)
    assert df.shape == (6240,19)
    assert check_provenance()['rows'] == len(df)

def test_corrupt_bytes_rejected():
    with pytest.raises(ValueError): verify_bytes(b'conteudo alterado')

@pytest.mark.parametrize('fault',['duplicate','missing','negative','population','pair','date','infinite'])
def test_invalid_panel_rejected(df,fault):
    if fault=='duplicate': df.loc[1,['geo','time']]=df.loc[0,['geo','time']].values
    if fault=='missing': df.loc[0,'conversions']=np.nan
    if fault=='negative': df.loc[0,MEDIA[0]]=-1
    if fault=='population': df.loc[0,'population']+=1
    if fault=='pair': df.loc[0,SPEND[0]]=0
    if fault=='date': df.loc[0,'time']='2021-01-26'
    if fault=='infinite': df.loc[0,'Promo']=np.inf
    with pytest.raises(ValueError): validate(df)

def test_zero_and_signed_indices_preserved(df):
    assert all(df[c].lt(0).any() and df[c].gt(0).any() for c in CONTROLS)
    assert df.Promo.eq(0).any() and df.Promo.mod(1).ne(0).any()
    assert df.conversions.mod(1).ne(0).any()
    for m,s in zip(MEDIA,SPEND): assert df[m].eq(0).equals(df[s].eq(0))

def test_bad_export_index(tmp_path):
    raw=pd.read_csv(retrieve()); raw.loc[0,'Unnamed: 0']=900
    path=tmp_path/'bad.csv'; raw.to_csv(path,index=False)
    with pytest.raises(ValueError): load_panel(path)

def test_split_deterministic_order_and_kpi_independent(df):
    first=make_holdout(df)
    altered=df.sample(frac=1,random_state=9); altered['conversions']=-100
    pd.testing.assert_frame_equal(first,make_holdout(altered))
    assert not first.equals(make_holdout(df,seed=1))
    assert first.is_holdout.sum()==936
    assert first.groupby('time').is_holdout.sum().eq(6).all()
    assert first.groupby('geo').is_holdout.sum().between(23,24).all()

def test_coverage(df):
    c=coverage(df,make_holdout(df))
    assert c['channel2_geo'].channel2_active.min()>0
    assert c['channels'].active_cells.gt(0).all()
    for channel in range(5):
        np.testing.assert_allclose(c['channels'].query('channel == @name',local_dict={'name':f'Channel{channel}'}).spend.sum(), df[SPEND[channel]].sum())

def test_mask_alignment(df):
    split=make_holdout(df); gs=list(reversed(sorted(df.geo.unique()))); ts=sorted(df.time.unique())
    mask=aligned_mask(split,gs,ts)
    assert mask.shape==(40,156)
    for i,g in enumerate(gs):
        assert mask[i,0]==split.query('geo==@g and time==@t',local_dict={'g':g,'t':ts[0]}).is_holdout.iloc[0]
    with pytest.raises(ValueError): aligned_mask(split.iloc[:-1],gs,ts)

def test_audit(df):
    a=audit(df)
    assert len(a)==17 and a.status.eq('PASS').all()

def test_meridian_objects_and_resolved_holdout(df):
    pytest.importorskip('meridian')
    from src.meridian_setup import build_input,build_spec,inspect_input
    from meridian.model import model
    data=build_input(df); inspect_input(data,df)
    split=make_holdout(df); spec=build_spec(data,split)
    mmm=model.Meridian(input_data=data,model_spec=spec)
    np.testing.assert_array_equal(np.asarray(mmm.holdout_id),aligned_mask(split,data.geo.values,data.time.values))
    assert spec.media_prior_type=='contribution'
    assert spec.max_lag==8 and spec.hill_before_adstock is False

def test_no_sampling_calls():
    import ast
    for p in (ROOT/'src').glob('*.py'):
        tree=ast.parse(p.read_text())
        assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
                       and n.func.attr in ['sample_posterior','sample_prior','optimize'] for n in ast.walk(tree))
