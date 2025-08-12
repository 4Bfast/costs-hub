# app/services.py

import boto3
from botocore.exceptions import ClientError
import pandas as pd
from io import BytesIO
from datetime import datetime

from . import db
from .models import AWSAccount, DailyFocusCosts

def process_focus_data_for_account(aws_account_id: int):
    """
    [VERSÃO CORRIGIDA]
    Busca e processa os dados de custo de uma conta AWS específica,
    usando os nomes de coluna oficiais do FOCUS exportado pela AWS.
    """
    account = AWSAccount.query.get(aws_account_id)
    if not account:
        print(f"Error: AWS Account with ID {aws_account_id} not found.")
        return

    print(f"Starting cost data processing for: {account.account_name} (ID: {account.id})")

    try:
        s3_client = boto3.client('s3')

        s3_path = account.focus_s3_bucket_path
        bucket_name = s3_path.split('/')[2]
        prefix = '/'.join(s3_path.split('/')[3:])
        
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        
        if 'Contents' not in response:
            print(f"No files found at path: {s3_path}")
            return

        for obj in response['Contents']:
            file_key = obj['Key']
            if file_key.endswith(('.parquet', '.snappy.parquet')):
                print(f"  -> Processing file: {file_key}")
                
                s3_object = s3_client.get_object(Bucket=bucket_name, Key=file_key)
                file_content = s3_object['Body'].read()
                df = pd.read_parquet(BytesIO(file_content))

                # --- LÓGICA DE MAPEAMENTO CORRIGIDA ---
                # Renomeia as colunas oficiais para os nomes que nosso script espera
                # Adicionamos um filtro para pegar apenas o que tem custo faturado > 0
                df = df.rename(columns={
                    'ChargePeriodStart': 'UsageDate',
                    'ServiceName': 'Service',
                    'ServiceCategory': 'ServiceCategory',
                    'BilledCost': 'BilledCost'
                })

                # Filtra apenas por linhas que têm as colunas necessárias e custo > 0
                required_cols = ['UsageDate', 'Service', 'ServiceCategory', 'BilledCost']
                df = df[df.columns.intersection(required_cols)] # Mantém apenas as colunas que nos interessam
                df = df.dropna(subset=required_cols) # Remove linhas onde qualquer um desses valores é nulo
                df = df[df['BilledCost'] > 0] # Filtra custos zerados

                if df.empty:
                    print(f"    - No billable data found in {file_key}. Skipping.")
                    continue

                # Agrega os custos por dia, categoria de serviço e serviço
                aggregation_cols = ['UsageDate', 'ServiceCategory', 'Service']
                daily_costs = df.groupby(aggregation_cols)['BilledCost'].sum().reset_index()

                for index, row in daily_costs.iterrows():
                    # Converte a data (que é datetime) para apenas o objeto date
                    usage_date_obj = row['UsageDate'].date()

                    existing_record = DailyFocusCosts.query.filter_by(
                        aws_account_id=account.id,
                        usage_date=usage_date_obj,
                        service_category=row['ServiceCategory'],
                        aws_service=row['Service']
                    ).first()

                    if existing_record:
                        existing_record.cost = row['BilledCost']
                    else:
                        new_cost_entry = DailyFocusCosts(
                            aws_account_id=account.id,
                            usage_date=usage_date_obj,
                            service_category=row['ServiceCategory'],
                            aws_service=row['Service'],
                            cost=row['BilledCost']
                        )
                        db.session.add(new_cost_entry)
        
        db.session.commit()
        print(f"Successfully processed cost data for {account.account_name}")

    except ClientError as e:
        print(f"AWS Error processing account {account.id}: {e}")
        db.session.rollback()
    except KeyError as e:
        print(f"A critical column was not found in the file. Please check the FOCUS export settings. Missing column: {e}")
        db.session.rollback()
    except Exception as e:
        print(f"An unexpected error occurred processing account {account.id}: {e}")
        db.session.rollback()