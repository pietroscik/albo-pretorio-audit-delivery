import pandas as pd
df_feat = pd.read_csv('data/albo_download/documenti_features.csv')
df_all = pd.read_csv('data/albo_download/allegati_parsed.csv')
if 'text_preview' in df_feat.columns:
    df_all['text_preview'] = df_feat['text_preview']
    df_all.to_csv('data/albo_download/allegati_parsed.csv', index=False)
