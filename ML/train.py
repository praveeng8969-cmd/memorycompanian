"""Train and evaluate a small Random Forest on participant-separated synthetic data."""
import json, platform
from pathlib import Path
import joblib, pandas as pd, sklearn
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
ROOT=Path(__file__).parent
FEATURES=['activity','level','accuracy','hint_rate','paused']
def train():
    df=pd.read_csv(ROOT/'data/synthetic_sessions.csv')
    if df.isna().any().any(): raise ValueError('Missing training values')
    if not df.accuracy.between(0,1).all() or not df.hint_rate.between(0,1).all(): raise ValueError('Invalid feature range')
    tr,te=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=42).split(df,groups=df.participant_id))
    train_ids=set(df.iloc[tr].participant_id);test_ids=set(df.iloc[te].participant_id)
    assert not train_ids & test_ids
    prep=ColumnTransformer([('numeric',StandardScaler(),['level','accuracy','hint_rate','paused']),('category',OneHotEncoder(handle_unknown='ignore'),['activity'])])
    model=Pipeline([('prepare',prep),('forest',RandomForestClassifier(n_estimators=60,max_depth=7,class_weight='balanced',random_state=42,n_jobs=1))])
    model.fit(df.iloc[tr][FEATURES],df.iloc[tr].recommended_action)
    pred=model.predict(df.iloc[te][FEATURES]);labels=['advance','maintain','simplify','pause']
    report=dict(data_source='Synthetic rule-labelled demonstration data; not clinical validation',accuracy=accuracy_score(df.iloc[te].recommended_action,pred),classification_report=classification_report(df.iloc[te].recommended_action,pred,labels=labels,output_dict=True,zero_division=0),confusion_matrix_labels=labels,confusion_matrix=confusion_matrix(df.iloc[te].recommended_action,pred,labels=labels).tolist(),train_participants=sorted(map(int,train_ids)),test_participants=sorted(map(int,test_ids)),train_rows=len(tr),test_rows=len(te),features=FEATURES,python=platform.python_version(),sklearn=sklearn.__version__)
    out=ROOT/'artifacts';out.mkdir(exist_ok=True)
    joblib.dump(model,out/'model.joblib');(out/'evaluation.json').write_text(json.dumps(report,indent=2))
    print(f'Synthetic holdout accuracy: {report["accuracy"]:.2%}; train rows={len(tr)}, test rows={len(te)}')
    print('Saved ML/artifacts/model.joblib and evaluation.json. Restart backend after retraining.')
if __name__=='__main__': train()
