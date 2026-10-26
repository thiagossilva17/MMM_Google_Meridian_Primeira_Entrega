"""Execute com python -m src.run_design na raiz. Nenhuma inferência."""
import datetime
import hashlib
import importlib.metadata
import json
import platform
import numpy as np
import yaml
from .data_source import ROOT, retrieve, check_provenance
from .data_contract import load_panel,audit,eda_comparison
from .validation_design import make_holdout,coverage,aligned_mask

def save_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')

def main():
    source=retrieve(); check_provenance(); df=load_panel(source)
    tables=ROOT/'outputs/tables'; logs=ROOT/'outputs/logs'
    tables.mkdir(parents=True,exist_ok=True); logs.mkdir(parents=True,exist_ok=True)
    audit(df).to_csv(tables/'data_audit.csv',index=False)
    comparison=eda_comparison(df); comparison.to_csv(tables/'eda_comparison.csv',index=False)
    cfg=yaml.safe_load((ROOT/'configs/validation_design.yaml').read_text())['H_GEO']
    split=make_holdout(df,seed=cfg['seed'],per_week=cfg['per_week'])
    destination=ROOT/'data/splits/holdout_geo.csv'
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():
        import pandas as pd
        pd.testing.assert_frame_equal(pd.read_csv(destination),split)
    else: split.to_csv(destination,index=False)
    c=coverage(df,split)
    for name,tab in c.items(): tab.to_csv(tables/f'holdout_{name}.csv',index=False)
    channels=c['channels'].pivot(index='channel',columns='subset',values='activity_fraction')
    coverage_ok=bool(c['channel2_geo'].channel2_active.ge(1).all() and (channels.test-channels.train).abs().le(.10).all())
    result={'data_ready':'PASS' if comparison.status.eq('PASS').all() else 'REVIEW',
            'holdout_coverage':'PASS' if coverage_ok else 'REVIEW','api':'BLOCKED',
            'spec_scientific':'REVIEW','H_COMP':'PENDING_METHOD_DECISION','hosted_colab':'NOT_TESTED_IN_HOSTED_COLAB',
            'posterior_sampled':False,'prior_sampled':False,'optimization_executed':False}
    try:
        from .meridian_setup import build_input,build_spec,inspect_input,inspect_priors
        from meridian.model import model
        data=build_input(df)
        tensors=inspect_input(data,df)
        spec=build_spec(data,split)
        mmm=model.Meridian(input_data=data,model_spec=spec)
        np.testing.assert_array_equal(np.asarray(mmm.holdout_id),aligned_mask(split,data.geo.values,data.time.values))
        save_json(logs/'api_inspection.json',{'status':'PASS','tensors':tensors,'holdout_resolved_sum':int(np.asarray(mmm.holdout_id).sum()),'model_initialized':True,'sampling':False})
        save_json(tables/'prior_parameters.json',inspect_priors(spec))
        result['api']='PASS'
    except (ImportError,ValueError,AttributeError,AssertionError) as exc:
        save_json(logs/'api_inspection.json',{'status':'BLOCKED','error':str(exc),'type':type(exc).__name__})
    versions={}
    for package in ['google-meridian','tensorflow','tf-keras','tfp-nightly','jax','jaxlib','numpy','pandas','xarray','PyYAML','pytest']:
        try: versions[package]=importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError: versions[package]='NOT_INSTALLED'
    manifest={'executed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':platform.python_version(),
              'versions':versions,'rows':len(df),'columns':len(df.columns),'holdout_cells':int(split.is_holdout.sum()),
              'split_sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'result':result}
    save_json(logs/'run_manifest.json',manifest)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if result['api']=='BLOCKED': raise SystemExit(1)
    return manifest

if __name__=='__main__': main()
