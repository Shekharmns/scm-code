import boto3

def lambda_handler(event, context):
    ec2_client = boto3.client('ec2')
    rds_client = boto3.client('rds')
    cloudwatch_client = boto3.client('cloudwatch')
    
    account_id = context.invoked_function_arn.split(":")[4]
    region = context.invoked_function_arn.split(":")[3]
    
    sns_topic_name = 'YOUR_SNS_TOPIC_NAME'
    sns_topic_arn = f'arn:aws:sns:{region}:{account_id}:{sns_topic_name}'
    print(f"SNS Topic ARN: {sns_topic_arn}")
    
    ec2_instances = []
    rds_instances = []
    
    # List EC2 instances
    ec2_response = ec2_client.describe_instances()
    for reservation in ec2_response['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            has_cloudwatch_alarm = check_cloudwatch_alarm(cloudwatch_client, 'InstanceId', instance_id)
            ec2_instances.append({
                'InstanceId': instance_id,
                'HasCloudWatchAlarm': has_cloudwatch_alarm
            })
            if not has_cloudwatch_alarm:
                create_cpu_utilization_alarm(cloudwatch_client, instance_id, sns_topic_arn)
            else:
                print(f"Skipping CPU Utilization Alarm creation for EC2 instance {instance_id} as it already has an alarm.")

    # List RDS instances
    rds_response = rds_client.describe_db_instances()
    for instance in rds_response['DBInstances']:
        db_instance_identifier = instance['DBInstanceIdentifier']
        has_cloudwatch_alarm = check_cloudwatch_alarm(cloudwatch_client, 'DBInstanceIdentifier', db_instance_identifier)
        rds_instances.append({
            'DBInstanceIdentifier': db_instance_identifier,
            'HasCloudWatchAlarm': has_cloudwatch_alarm
        })
        if not has_cloudwatch_alarm:
            create_free_storage_space_alarm(cloudwatch_client, db_instance_identifier, sns_topic_arn)
        else:
            print(f"Skipping Free Storage Space Alarm creation for RDS instance {db_instance_identifier} as it already has an alarm.")

    return {
        "EC2Instances": ec2_instances,
        "RDSInstances": rds_instances
    }

def check_cloudwatch_alarm(client, dimension_name, dimension_value):
    alarms = client.describe_alarms(AlarmNamePrefix=dimension_value)
    for alarm in alarms['MetricAlarms']:
        for dimension in alarm['Dimensions']:
            if dimension['Name'] == dimension_name and dimension['Value'] == dimension_value:
                return True
    return False
    
def create_cpu_utilization_alarm(client, instance_id, sns_topic_arn):
    client.put_metric_alarm(
        AlarmName=f"EC2_CPU_Utilization_{instance_id}",
        ComparisonOperator='GreaterThanThreshold',
        EvaluationPeriods=1,
        MetricName='CPUUtilization',
        Namespace='AWS/EC2',
        Period=60,
        Statistic='Average',
        Threshold=70.0,
        ActionsEnabled=False,
        AlarmDescription=f"Alarm for EC2 instance {instance_id} CPU utilization exceeding 70%",
        Dimensions=[
            {
                'Name': 'InstanceId',
                'Value': instance_id
            },
        ],
        AlarmActions=[
            sns_topic_arn,
        ]
    )
    print(f"Created CPU Utilization Alarm for EC2 instance {instance_id}")

def create_free_storage_space_alarm(client, db_instance_identifier, sns_topic_arn):
    client.put_metric_alarm(
        AlarmName=f"RDS_Free_Storage_Space_{db_instance_identifier}",
        ComparisonOperator='LessThanOrEqualToThreshold',
        EvaluationPeriods=1,
        MetricName='FreeStorageSpace',
        Namespace='AWS/RDS',
        Period=60,
        Statistic='Average',
        Threshold=5000000000,  # 5 GB in bytes
        ActionsEnabled=False,
        AlarmDescription=f"Alarm for RDS instance {db_instance_identifier} free storage space less than 5 GB",
        Dimensions=[
            {
                'Name': 'DBInstanceIdentifier',
                'Value': db_instance_identifier
            },
        ],
        AlarmActions=[
            sns_topic_arn,
        ]
    )
    print(f"Created Free Storage Space Alarm for RDS instance {db_instance_identifier}")
