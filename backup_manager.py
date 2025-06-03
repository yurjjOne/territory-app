import os
import json
import boto3
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from botocore.exceptions import ClientError
import logging

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BackupManager:
    def __init__(self, db_url, bucket_name):
        self.db_url = db_url
        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        self.scheduler = BackgroundScheduler()

    def create_backup(self):
        """Створення резервної копії бази даних"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f'backup_{timestamp}.sql'
            
            # Створення дампу бази даних
            os.system(f'pg_dump {self.db_url} > {backup_filename}')
            
            # Завантаження на S3
            self.s3_client.upload_file(backup_filename, self.bucket_name, f'backups/{backup_filename}')
            
            # Видалення локального файлу
            os.remove(backup_filename)
            
            logger.info(f"Backup created successfully: {backup_filename}")
            
            # Видалення старих бекапів (залишаємо останні 7)
            self._cleanup_old_backups()
            
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")

    def _cleanup_old_backups(self):
        """Видалення старих резервних копій"""
        try:
            # Отримання списку всіх бекапів
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='backups/'
            )
            
            if 'Contents' in response:
                # Сортування за датою створення
                backups = sorted(response['Contents'], key=lambda x: x['LastModified'])
                
                # Видалення всіх крім останніх 7
                if len(backups) > 7:
                    for backup in backups[:-7]:
                        self.s3_client.delete_object(
                            Bucket=self.bucket_name,
                            Key=backup['Key']
                        )
                        logger.info(f"Deleted old backup: {backup['Key']}")
                        
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")

    def restore_latest_backup(self):
        """Відновлення з останньої резервної копії"""
        try:
            # Отримання списку всіх бекапів
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='backups/'
            )
            
            if 'Contents' in response:
                # Знаходження найновішого бекапу
                latest_backup = max(response['Contents'], key=lambda x: x['LastModified'])
                backup_filename = latest_backup['Key'].split('/')[-1]
                
                # Завантаження файлу
                self.s3_client.download_file(
                    self.bucket_name,
                    latest_backup['Key'],
                    backup_filename
                )
                
                # Відновлення бази даних
                os.system(f'psql {self.db_url} < {backup_filename}')
                
                # Видалення локального файлу
                os.remove(backup_filename)
                
                logger.info(f"Restored from backup: {backup_filename}")
                return True
                
        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            return False

    def start_scheduler(self):
        """Запуск планувальника резервного копіювання"""
        # Щоденне резервне копіювання о 3:00
        self.scheduler.add_job(self.create_backup, 'cron', hour=3)
        self.scheduler.start()
        logger.info("Backup scheduler started")

    def stop_scheduler(self):
        """Зупинка планувальника"""
        self.scheduler.shutdown()
        logger.info("Backup scheduler stopped") 